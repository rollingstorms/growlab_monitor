from .base_widget import BaseWidget
import sqlite3
from flask import jsonify, request, current_app as app
from controller import set_fan, set_light  # adjust imports per your controller module

class DeviceWidget(BaseWidget):
    """
    Widget for displaying and controlling a device (e.g., fan or light).
    Exposes API endpoints for status and control, and renders a template.
    """
    def register_routes(self):
        # Endpoint to fetch current and historical status
        @self.app.route(f"/api/{self.device_info['id']}/status")
        def api_device_status():
            data = self.get_data()
            return jsonify(data)

        # Endpoint to send control commands (expects JSON {"action": "on"/"off"})
        @self.app.route(f"/api/{self.device_info['id']}/control", methods=["POST"])
        def api_device_control():
            payload = request.get_json()
            action = payload.get("action")
            dev_id = self.device_info["id"]
            # Map device ID to controller functions
            if action == "on":
                if dev_id == "fan":
                    set_fan(True)
                else:
                    set_light(True)
            elif action == "off":
                if dev_id == "fan":
                    set_fan(False)
                else:
                    set_light(False)
            return jsonify({"result": "ok", "action": action})

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
        return self.app.jinja_env.get_template(
            'widgets/device.html',
            device=self.device_info
        ).render(device=self.device_info)
