from .base_widget import BaseWidget
import sqlite3
import threading
import time
from flask import jsonify, request, current_app as app

class ControlWidget(BaseWidget):
    """
    Widget for automated control of a device based on sensor readings.
    Allows setting target values and control logic for sensor-driven automation.
    """
    def __init__(self, app, config, device_info=None):
        super().__init__(app, config, device_info)
        # Start the control loop in a background thread
        self.running = True
        self.thread = threading.Thread(target=self.control_loop)
        self.thread.daemon = True  # Thread will exit when main program exits
        self.thread.start()
        
    def register_routes(self):
        control_id = self.device_info['id']
        
        # Get current configuration
        def _get_config():
            return jsonify(self.get_config())
        self.app.add_url_rule(
            f"/api/{control_id}/config",
            endpoint=f"{control_id}_config",
            view_func=_get_config
        )
        
        # Update configuration
        def _update_config():
            payload = request.get_json()
            self.update_config(payload)
            return jsonify({"status": "ok", "config": self.get_config()})
        self.app.add_url_rule(
            f"/api/{control_id}/config",
            endpoint=f"{control_id}_config_update",
            view_func=_update_config,
            methods=["POST"]
        )
        
        # Manual override
        def _manual_control():
            payload = request.get_json()
            action = payload.get("action")
            device_id = payload.get("device_id")
            success = self.control_device(device_id, action == "on")
            return jsonify({"status": "ok" if success else "error", "action": action})
        self.app.add_url_rule(
            f"/api/{control_id}/manual",
            endpoint=f"{control_id}_manual",
            view_func=_manual_control,
            methods=["POST"]
        )

    def get_config(self):
        """Get the current control configuration from database"""
        db_path = app.config.get("DATABASE", "data.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_configs(
                control_id TEXT PRIMARY KEY,
                sensor_id TEXT,
                device_id TEXT,
                metric TEXT,
                operator TEXT,
                target_value REAL,
                enabled INTEGER
            )
        """)
        
        # Get config for this control
        cursor.execute("""
            SELECT * FROM control_configs WHERE control_id = ?
        """, (self.device_info["id"],))
        
        row = cursor.fetchone()
        
        # If no config exists yet, create default from device_info
        if not row:
            # Extract default values from device_info
            sensor_id = self.device_info.get("sensor_id", "")
            device_id = self.device_info.get("device_id", "")
            metric = self.device_info.get("metric", "")
            operator = self.device_info.get("operator", ">")
            target_value = self.device_info.get("target_value", 0.0)
            enabled = self.device_info.get("enabled", 0)
            
            # Insert default config
            cursor.execute("""
                INSERT INTO control_configs(
                    control_id, sensor_id, device_id, metric, 
                    operator, target_value, enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.device_info["id"], sensor_id, device_id, metric, 
                operator, target_value, enabled
            ))
            conn.commit()
            
            # Get the newly inserted config
            cursor.execute("""
                SELECT * FROM control_configs WHERE control_id = ?
            """, (self.device_info["id"],))
            row = cursor.fetchone()
        
        result = dict(row) if row else {}
        conn.close()
        
        return result

    def update_config(self, config):
        """Update the control configuration in the database"""
        db_path = app.config.get("DATABASE", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update all fields
        cursor.execute("""
            UPDATE control_configs
            SET sensor_id = ?,
                device_id = ?,
                metric = ?,
                operator = ?,
                target_value = ?,
                enabled = ?
            WHERE control_id = ?
        """, (
            config.get("sensor_id", ""),
            config.get("device_id", ""),
            config.get("metric", ""),
            config.get("operator", ">"),
            config.get("target_value", 0.0),
            1 if config.get("enabled", False) else 0,
            self.device_info["id"]
        ))
        
        conn.commit()
        conn.close()

    def control_device(self, device_id, on):
        """Control a device using the DeviceWidget instance"""
        # Find the DeviceWidget instance for this device
        for widget in app.config.get("_widgets", []):
            if (hasattr(widget, 'device_info') and 
                widget.device_info.get('id') == device_id):
                if hasattr(widget, 'set_device_state'):
                    return widget.set_device_state(on)
        
        # Fallback to controller module
        try:
            from controller import set_device
            set_device(device_id, on)
            return True
        except Exception as e:
            print(f"Error controlling device {device_id}: {e}")
            return False

    def get_latest_reading(self, sensor_id, metric):
        """Get the most recent reading for a sensor metric"""
        db_path = app.config.get("DATABASE", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value
            FROM readings
            WHERE device_id = ? AND metric = ?
            ORDER BY ts DESC
            LIMIT 1
        """, (sensor_id, metric))
        
        row = cursor.fetchone()
        conn.close()
        
        return float(row[0]) if row else None

    def control_loop(self):
        """Background thread that checks conditions and controls devices"""
        while self.running:
            try:
                config = self.get_config()
                
                # Skip if not enabled or missing required config
                if not config or not config.get("enabled"):
                    time.sleep(10)
                    continue
                
                sensor_id = config.get("sensor_id")
                device_id = config.get("device_id")
                metric = config.get("metric")
                operator = config.get("operator")
                target_value = float(config.get("target_value", 0))
                
                if not sensor_id or not device_id or not metric:
                    time.sleep(10)
                    continue
                
                # Get latest reading
                current_value = self.get_latest_reading(sensor_id, metric)
                if current_value is None:
                    time.sleep(10)
                    continue
                
                # Evaluate condition
                should_turn_on = False
                if operator == ">":
                    should_turn_on = current_value > target_value
                elif operator == ">=":
                    should_turn_on = current_value >= target_value
                elif operator == "<":
                    should_turn_on = current_value < target_value
                elif operator == "<=":
                    should_turn_on = current_value <= target_value
                elif operator == "=":
                    should_turn_on = abs(current_value - target_value) < 0.01
                
                # Control the device based on condition
                self.control_device(device_id, should_turn_on)
                
            except Exception as e:
                print(f"Error in control loop: {e}")
            
            # Check every minute
            time.sleep(60)
    
    def render(self):
        """Render the control widget template"""
        template = self.app.jinja_env.get_template('widgets/control.html')
        
        # Get all available sensors and devices
        sensors = []
        devices = []
        
        for widget in app.config.get("_widgets", []):
            if hasattr(widget, 'device_info'):
                device_type = widget.device_info.get('type')
                if device_type == 'sensor':
                    sensors.append({
                        'id': widget.device_info.get('id'),
                        'name': widget.device_info.get('name'),
                        'metrics': widget.device_info.get('metrics', [])
                    })
                elif device_type == 'device':
                    devices.append({
                        'id': widget.device_info.get('id'),
                        'name': widget.device_info.get('name')
                    })
        
        # Get current configuration
        config = self.get_config()
        
        return template.render(
            device=self.device_info,
            config=config,
            sensors=sensors,
            devices=devices,
            operators=[">", ">=", "<", "<=", "="]
        )