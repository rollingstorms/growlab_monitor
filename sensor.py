# sensor.py — Reading and storing sensor data for all configured sensors

import yaml
import sqlite3
import time
from datetime import datetime
from smbus2 import SMBus, i2c_msg

# Load configuration
cfg = yaml.safe_load(open('config.yaml'))
DB = cfg.get('DATABASE', 'data.db')

def init_db():
    """
    Create the readings table (with device_id) if it doesn’t exist yet.
    """
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
        device_id TEXT    NOT NULL,
        ts        TEXT    NOT NULL,   -- ISO timestamp
        metric    TEXT    NOT NULL,
        value     REAL,
        PRIMARY KEY (device_id, ts, metric)
        );
    """)
    conn.commit()
    conn.close()

# I²C measurement constants
MEAS_CMD = 0xFD    # high-repeatability measurement, no clock-stretch
DELAY_S  = 0.02    # 20 ms conversion delay

def read_sensor(bus_number=None, address=None):
    """
    Trigger a measurement on the SHT40 and return (temperature_C, humidity_%RH).
    Reads the bus/address from config if not provided.
    """
    bus_num = bus_number or cfg.get('sensor', {}).get('i2c_bus', 1)
    addr    = address  or cfg.get('sensor', {}).get('address', 0x44)
    with SMBus(bus_num) as bus:
        # Send measure command
        write = i2c_msg.write(addr, [MEAS_CMD])
        bus.i2c_rdwr(write)
        # Wait for conversion
        time.sleep(DELAY_S)
        # Read 6 bytes
        read = i2c_msg.read(addr, 6)
        bus.i2c_rdwr(read)
        data = list(read)
    # Parse raw values
    t_raw = (data[0] << 8) | data[1]
    h_raw = (data[3] << 8) | data[4]
    # Convert per datasheet
    temperature = -45 + (175 * t_raw / 65535)
    humidity    = 100 * (h_raw / 65535)
    return temperature, humidity

def store_reading():
    """
    Read all sensors listed in config.yaml and append results to readings.
    Returns list of inserted rows: [(device_id, ts, metric, value), ...].
    """
    # Find all configured sensor devices
    sensor_devs = [
        d for d in cfg.get('devices', [])
        if d.get('type') == 'sensor' and d.get('source', 'local') == 'local'
    ]
    ts = datetime.now().isoformat()
    rows = []

    # For each sensor, read values and append one row per metric
    for dev in sensor_devs:
        addr = dev.get('address', cfg.get('sensor', {}).get('address', 0x44))
        temp, hum = read_sensor(address=addr)
        # Append separate entries for temperature and humidity
        rows.append((dev['id'], ts, "temperature_C", temp))
        rows.append((dev['id'], ts, "humidity_pct", hum))

    # Insert into SQLite with generic key-value schema
    conn = sqlite3.connect(DB)
    conn.executemany(
        "INSERT OR REPLACE INTO readings (device_id, ts, metric, value) VALUES (?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()

    return rows