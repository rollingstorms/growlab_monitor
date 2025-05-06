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

        # Query raw metric/value pairs for last 24h
        conn = sqlite3.connect(db_path)
        # Enable column name access by name
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Use a simpler query without the datetime function to avoid format issues
        cursor.execute(
            "SELECT ts, metric, value FROM readings "
            "WHERE device_id=? "
            "ORDER BY ts DESC "
            "LIMIT 1000",  # Get more data to ensure we have enough
            (device_id,)
        )
        rows = cursor.fetchall()
        print(f"Found {len(rows)} readings for device {device_id}")
        
        if not rows:
            # Debug: check if any data exists for this device
            cursor.execute("SELECT COUNT(*) FROM readings WHERE device_id=?", (device_id,))
            count = cursor.fetchone()[0]
            print(f"Total records for device {device_id}: {count}")
            
            # Get sample of any records that exist
            cursor.execute("SELECT ts, metric, value FROM readings LIMIT 5")
            samples = cursor.fetchall()
            if samples:
                print(f"Sample records in database: {[dict(r) for r in samples]}")
        
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
            rec[metric] = value

        # Build sorted history and current
        history = [data_map[ts] for ts in sorted(data_map)]
        current = history[-1] if history else {}

        print(f"Returning {len(history)} history records, current: {current}")
        
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