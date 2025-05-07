from .base_widget import BaseWidget
import sqlite3
from flask import jsonify, request, current_app as app
from tinytuya import OutletDevice
from datetime import datetime

class DeviceWidget(BaseWidget):
    """
    Widget for displaying and controlling a device (e.g., fan or light).
    Supports Tuya smart plugs using tinytuya.
    """
    def register_routes(self):
        device_id = self.device_info['id']

        # STATUS endpoint
        def _status():
            return jsonify(self.get_data())
        self.app.add_url_rule(
            f"/api/{device_id}/status",       
            endpoint=f"{device_id}_status",   
            view_func=_status
        )

        # CONTROL endpoint
        def _control():
            payload = request.get_json()
            action = payload.get("action")
            # Call control method directly from the widget
            success = self.set_device_state(action == "on")
            return jsonify({"result": "ok" if success else "error", "action": action})
            
        self.app.add_url_rule(
            f"/api/{device_id}/control",
            endpoint=f"{device_id}_control",
            view_func=_control,
            methods=["POST"]
        )

    def set_device_state(self, on: bool):
        """Control the device based on its type (tuya, etc)"""
        device_id = self.device_info['id']
        device_type = self.device_info.get('device_type', 'generic')
        
        if device_type == 'tuya':
            try:
                dev_id = self.device_info.get('dev_id')
                ip = self.device_info.get('ip')
                local_key = self.device_info.get('local_key')
                version = self.device_info.get('version', 3.5)
                
                device = OutletDevice(
                    dev_id=dev_id,
                    address=ip,
                    local_key=local_key,
                    version=version
                )
                
                if on:
                    device.turn_on()
                else:
                    device.turn_off()
                
                # Log the device change to database
                self._log_device_state(device_id, 'on' if on else 'off')
                return True
            except Exception as e:
                print(f"Error controlling Tuya device: {e}")
                return False
        else:
            # For generic devices, use the controller module
            try:
                from controller import set_device
                set_device(device_id, on)
                return True
            except Exception as e:
                print(f"Error controlling device: {e}")
                return False
    
    def _log_device_state(self, device_id: str, state: str):
        """Log device state changes to database"""
        db_path = app.config.get("DATABASE", "data.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_logs(
                ts         TEXT,
                device_id  TEXT,
                state      TEXT
            )
        """)
        
        ts = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO device_logs(ts, device_id, state) VALUES (?, ?, ?)",
            (ts, device_id, state)
        )
        conn.commit()
        conn.close()

    def get_data(self):
        """
        Query the SQLite database for:
        - current: most recent on/off state
        - history: state changes in the last 24 hours
        """
        db_path = app.config.get("DATABASE", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch latest state
        cursor.execute("""
            SELECT ts, state
            FROM device_logs
            WHERE device_id = ?
            ORDER BY ts DESC
            LIMIT 1
        """, (self.device_info["id"],))
        row = cursor.fetchone()
        current = {"ts": row[0], "state": row[1]} if row else {}

        # Fetch historical states from last 24 hours
        cursor.execute("""
            SELECT ts, state
            FROM device_logs
            WHERE device_id = ?
              AND ts >= datetime('now', '-24 hours')
            ORDER BY ts
        """, (self.device_info["id"],))
        history = [{"ts": r[0], "state": r[1]} for r in cursor.fetchall()]

        conn.close()
        return {"current": current, "history": history}

    def render(self):
        """
        Render the device widget's HTML template with device metadata.
        """
        template = self.app.jinja_env.get_template('widgets/device.html')
        return template.render(device=self.device_info)
