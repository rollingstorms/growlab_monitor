from .base_widget import BaseWidget
import sqlite3
import logging
from flask import jsonify, current_app as app

class SensorWidget(BaseWidget):
    """
    Generic sensor widget. Reads any number of metrics defined
    in config.yaml under each device's `metrics` list.
    """

    def register_routes(self):
        device_id = self.device_info["id"]
        endpoint = f"{device_id}_sensor_data"

        def _sensor_data():
            return jsonify(self.get_data())

        self.app.add_url_rule(
            f"/api/{device_id}/sensor_data",
            endpoint=endpoint,
            view_func=_sensor_data
        )

    def get_data(self):
        """
        Returns JSON with:
          - metrics: list of {name, label} from config
          - current: { ts, <metric>: value, ... }
          - history: list of { ts, <metric>: value, ... } for last 24h
        """
        db_path = app.config.get("DATABASE", "data.db")
        device_id = self.device_info["id"]
        metrics_cfg = self.device_info.get("metrics", [])

        # Extract metric keys from config
        metric_keys = [m["name"] for m in metrics_cfg]
        print(f"Looking for metrics: {metric_keys} for device: {device_id}")

        # Connect and enable row factory for easier column access
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Query raw readings for this device, with no time filter to ensure we get data
            cursor.execute(
                "SELECT ts, metric, value FROM readings WHERE device_id=? ORDER BY ts DESC LIMIT 500",
                (device_id,)
            )
            rows = list(cursor.fetchall())
            print(f"Found {len(rows)} readings for {device_id}")
            
            # Debug: Show first few records to check format
            if rows:
                print(f"First record: ts={rows[0]['ts']}, metric={rows[0]['metric']}, value={rows[0]['value']}")
                
            # If no rows, check if the device exists in the database
            if not rows:
                cursor.execute("SELECT DISTINCT device_id FROM readings")
                devices = [r[0] for r in cursor.fetchall()]
                print(f"Available devices in database: {devices}")
        except Exception as e:
            print(f"Database error: {e}")
            rows = []
        finally:
            conn.close()

        # Pivot into per-timestamp records
        data_map = {}
        for row in rows:
            ts = row['ts']
            metric = row['metric']
            value = row['value']
            
            if metric not in metric_keys:
                continue
                
            rec = data_map.setdefault(ts, {"ts": ts})
            rec[metric] = float(value)  # Ensure numeric format

        # Build sorted history and current data
        history = [data_map[ts] for ts in sorted(data_map.keys())]
        current = history[0] if history else {}  # Most recent should be first since we sorted DESC in query

        print(f"Returning {len(history)} history records")
        print(f"Current data: {current}")
        
        # Ensure numeric values for JavaScript
        for record in history:
            for metric in metric_keys:
                if metric in record:
                    record[metric] = float(record[metric])
                    
        return {
            "metrics": metrics_cfg,
            "current": current,
            "history": history
        }

    def render(self):
        """
        Render this sensor's widget template with both device info
        and metrics configuration.
        """
        template = self.app.jinja_env.get_template('widgets/sensor.html')
        return template.render(
            device=self.device_info,
            metrics=self.device_info.get("metrics", [])
        )