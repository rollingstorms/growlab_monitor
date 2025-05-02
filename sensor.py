# sensor.py

import yaml
import sqlite3
from datetime import datetime
import sht40

# Load configuration
cfg = yaml.safe_load(open('config.yaml'))
DB = cfg.get('DATABASE', 'data.db')

def init_db():
    """
    Create the readings table if it doesn’t exist yet.
    """
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings(
            ts   TEXT PRIMARY KEY,
            temp REAL,
            hum  REAL
        )
    """)
    conn.commit()
    conn.close()

def store_reading():
    """
    Read the SHT40 sensor once and append the result to readings.
    Returns (temperature, humidity).
    """
    # Initialize I2C and sensor
    temperature, humidity = sht40.read()

    # Timestamp in ISO format
    ts = datetime.utcnow().isoformat()

    # Insert into SQLite
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT OR REPLACE INTO readings(ts, temp, hum) VALUES (?, ?, ?)",
        (ts, temperature, humidity)
    )
    conn.commit()
    conn.close()
    return temperature, humidity