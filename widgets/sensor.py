

from .base_widget import BaseWidget
import sqlite3
from flask import jsonify, current_app as app

class SensorWidget(BaseWidget):
    """
    Widget for displaying current and historical SHT40 sensor data.
    Exposes an API endpoint for JSON and renders a template for the dashboard.
    """
    def register_routes(self):
        # API endpoint to fetch JSON data for this sensor
        @self.app.route(f"/api/{self.device_info['id']}/sensor_data")
        def api_sensor_data():
            data = self.get_data()
            return jsonify(data)

    def get_data(self):
        """
        Query the SQLite database for:
        - current: most recent temperature/humidity reading
        - history: readings from the last 24 hours
        """
        db_path = app.config.get("DATABASE", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch latest reading
        cursor.execute("""
            SELECT ts, temp, hum
            FROM readings
            ORDER BY ts DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        current = {"ts": row[0], "temp": row[1], "hum": row[2]} if row else {}

        # Fetch historical readings from last 24 hours
        cursor.execute("""
            SELECT ts, temp, hum
            FROM readings
            WHERE ts >= datetime('now', '-24 hours')
            ORDER BY ts
        """)
        history = [
            {"ts": r[0], "temp": r[1], "hum": r[2]}
            for r in cursor.fetchall()
        ]

        conn.close()
        return {"current": current, "history": history}

    def render(self):
        """
        Render the sensor widget's HTML template with device metadata.
        """
        return self.app.jinja_env.get_template(
            'widgets/sensor.html',
            device=self.device_info
        ).render(device=self.device_info)