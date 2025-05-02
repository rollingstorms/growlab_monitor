# controller.py

import yaml
import sqlite3
from datetime import datetime
from gosundpy.plug import Plug

# Load configuration
cfg = yaml.safe_load(open('config.yaml'))
DB = cfg.get('DATABASE', 'data.db')

# Initialize plugs from config
plugs_cfg = cfg.get('plugs', {})
_plugs = { name: Plug(info['ip']) for name, info in plugs_cfg.items() }

def log_device(device_id: str, state: str):
    """
    Append a record of each on/off event to the device_logs table.
    """
    conn = sqlite3.connect(DB)
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

def set_device(device_id: str, on: bool):
    """
    Turn the plug on or off based on device_id (e.g. 'fan1', 'light1').
    Assumes the alphabetic prefix of device_id matches a key in plugs_cfg.
    """
    # Derive the plug key by stripping trailing digits
    key = ''.join(filter(str.isalpha, device_id))
    plug = _plugs.get(key)
    if not plug:
        raise ValueError(f"No plug configured for device '{device_id}'")
    if on:
        plug.turn_on()
        log_device(device_id, 'on')
    else:
        plug.turn_off()
        log_device(device_id, 'off')

# Convenience aliases for the two main devices
def set_fan(on: bool):
    set_device('fan1', on)

def set_light(on: bool):
    set_device('light1', on)