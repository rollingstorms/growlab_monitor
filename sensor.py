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

# Sensor type registry for different sensor hardware
SENSOR_TYPES = {
    # Each type maps to a function that returns {metric_name: value} dict
    "SHT40": "read_sht40_sensor"
}

# I²C measurement constants for SHT40
MEAS_CMD = 0xFD    # high-repeatability measurement, no clock-stretch
DELAY_S  = 0.02    # 20 ms conversion delay

def read_sht40_sensor(bus_number, address):
    """
    Read from SHT40 temperature/humidity sensor.
    Returns dict with temperature and humidity values.
    """
    with SMBus(bus_number) as bus:
        # Send measure command
        write = i2c_msg.write(address, [MEAS_CMD])
        bus.i2c_rdwr(write)
        # Wait for conversion
        time.sleep(DELAY_S)
        # Read 6 bytes
        read = i2c_msg.read(address, 6)
        bus.i2c_rdwr(read)
        data = list(read)
    
    # Parse raw values
    t_raw = (data[0] << 8) | data[1]
    h_raw = (data[3] << 8) | data[4]
    
    # Convert per datasheet
    temperature = -45 + (175 * t_raw / 65535)
    humidity    = 100 * (h_raw / 65535)
    
    # Return dictionary with metric names as keys
    return {
        "temperature_C": temperature,
        "humidity_pct": humidity
    }

def read_sensor(device_config):
    """
    Read a sensor based on its configuration.
    Returns a dictionary of metric values.
    """
    # Get sensor parameters from device config 
    bus_num = cfg.get('sensor', {}).get('i2c_bus', 1)
    address = device_config.get('address', cfg.get('sensor', {}).get('address', 0x44))
    
    # Determine sensor type - default to SHT40 for backward compatibility
    sensor_type = device_config.get('sensor_type', 'SHT40')
    
    # Get and call the appropriate sensor reading function
    reader_func_name = SENSOR_TYPES.get(sensor_type)
    if not reader_func_name:
        raise ValueError(f"Unknown sensor type: {sensor_type}")
    
    # Call the sensor's read function dynamically
    reader_func = globals()[reader_func_name]
    return reader_func(bus_num, address)

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

    # For each sensor, read values and store one row per metric
    for dev in sensor_devs:
        try:
            # Read all metrics from this sensor
            metrics_data = read_sensor(dev)
            
            # Get the metrics defined in config for this device
            config_metrics = [m["name"] for m in dev.get("metrics", [])]
            
            # For each metric defined in config, store its value
            for metric in config_metrics:
                if metric in metrics_data:
                    rows.append((dev['id'], ts, metric, metrics_data[metric]))
        except Exception as e:
            print(f"Error reading sensor {dev['id']}: {e}")
            continue

    # Insert into SQLite with generic key-value schema
    conn = sqlite3.connect(DB)
    conn.executemany(
        "INSERT OR REPLACE INTO readings (device_id, ts, metric, value) VALUES (?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()

    return rows