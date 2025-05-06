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
        
        rows = []
        try:
            # Query raw readings for this device, but LIMIT to a reasonable number
            # to avoid overwhelming the charts - just get last 24 hours
            cursor.execute(
                "SELECT ts, metric, value FROM readings "
                "WHERE device_id=? AND ts >= datetime('now', '-24 hours') "
                "ORDER BY ts DESC "
                "LIMIT 100", # Reasonable limit to prevent too many data points
                (device_id,)
            )
            rows = list(cursor.fetchall())
            print(f"Found {len(rows)} readings for {device_id}")
            
            # If no rows, check if the device exists in the database
            if not rows:
                cursor.execute("SELECT DISTINCT device_id FROM readings")
                devices = [r[0] for r in cursor.fetchall()]
                print(f"No readings for {device_id}. Available devices: {devices}")
        except Exception as e:
            print(f"Database error: {e}")
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
        # For chart display, we need chronological ordering (oldest to newest)
        history = [data_map[ts] for ts in sorted(data_map.keys())]
        
        # Handle empty data case
        if not history:
            print(f"No data found for device {device_id}")
            # Create an empty current record with placeholders for all configured metrics
            current = {"ts": "No data", "data_available": False}
            # Add null placeholder for each metric
            for metric in metric_keys:
                current[metric] = None
        else:
            current = history[0] if history else {}
            current["data_available"] = True
        
        # Limit history to reasonable number of points for charting
        if len(history) > 30:
            # Sample down to 30 points for charts - take every Nth point
            step = len(history) // 30
            history = history[::step]
            print(f"Reduced history to {len(history)} points")
        
        # Ensure numeric values for JavaScript
        for record in history:
            for metric in metric_keys:
                if metric in record:
                    record[metric] = float(record[metric])
                    
        return {
            "metrics": metrics_cfg,
            "current": current,
            "history": history,
            "has_data": len(history) > 0
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