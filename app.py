import yaml
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import importlib

from sensor import init_db, store_reading
from controller import set_fan, set_light

app = Flask(__name__)

# expose now() in templates
@app.context_processor
def inject_now():
    return {"now": datetime.utcnow}

def load_config():
    with open('config.yaml') as f:
        return yaml.safe_load(f)

# — apply config & init DB/scheduler —
config = load_config()
app.config.update(config)
init_db()

from apscheduler.schedulers.background import BackgroundScheduler
sched = BackgroundScheduler()
sched.add_job(store_reading, 'interval',
              seconds=config['schedule']['reading_interval_s'])
sched.start()

# Dynamically instantiate all widgets
widgets = []
# Which widget names are device-scoped?
device_widget_names = {dev['widget'] for dev in config['devices']}

# 1) Device-scoped widgets
for dev in config['devices']:
    wcfg   = config['widgets'][dev['widget']]
    module = importlib.import_module(wcfg['module'])
    cls    = getattr(module, wcfg['class'])
    widgets.append(cls(app, wcfg, device_info=dev))

# 2) Global widgets (not tied to any device)
for name, wcfg in config['widgets'].items():
    if name not in device_widget_names:
        module = importlib.import_module(wcfg['module'])
        cls    = getattr(module, wcfg['class'])
        widgets.append(cls(app, wcfg))

@app.route('/')
def dashboard():
    # Build a list of {id, html} so we know which widget this is
    widget_items = []
    for w in widgets:
        wid = getattr(w, 'device_info', {}).get('id', '')
        html = w.render()
        widget_items.append({'id': wid, 'html': html})
    return render_template('base.html', widgets=widget_items, config=config)

# — generic ingest endpoint —
@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    payload   = request.get_json(force=True)
    device_id = payload.get('device_id')
    ts        = payload.get('ts')

    if not device_id or not ts:
        return jsonify({"error": "device_id and ts required"}), 400

    # everything else is a measurement
    measurements = {
        k: v for k, v in payload.items()
        if k not in ('device_id', 'ts')
    }

    write_reading(device_id, ts, measurements)
    return jsonify({"status": "ok"}), 201

@app.route('/api/readings', methods=['GET'])
def api_readings():
    device_id = request.args.get('device_id')
    db        = app.config['DATABASE']
    conn      = sqlite3.connect(db)
    cur       = conn.cursor()
    cur.execute("""
      SELECT ts, metric, value
        FROM readings
       WHERE device_id = ?
       ORDER BY ts DESC
       LIMIT 100
    """, (device_id,))
    rows = cur.fetchall()
    conn.close()
    # return as JSON
    return jsonify([
      {"ts": ts, "metric": m, "value": v}
      for ts, m, v in rows
    ])

# NEW API: Diagnostic endpoint to inspect raw data 
@app.route('/api/diagnostic/readings')
def diagnostic_readings():
    """Get raw database readings for debugging"""
    limit = request.args.get('limit', 100, type=int)
    device_id = request.args.get('device_id')
    
    db = app.config['DATABASE']
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if device_id:
        cur.execute(
            "SELECT * FROM readings WHERE device_id=? ORDER BY ts DESC LIMIT ?", 
            (device_id, limit)
        )
    else:
        cur.execute("SELECT * FROM readings ORDER BY ts DESC LIMIT ?", (limit,))
    
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return jsonify({
        "count": len(rows),
        "readings": rows
    })

def write_reading(device_id, ts, measurements):
    """Insert one row per (device, timestamp, metric, value)."""
    db   = app.config['DATABASE']
    conn = sqlite3.connect(db)
    cur  = conn.cursor()

    ts_iso = datetime.utcfromtimestamp(ts).isoformat()

    for metric, value in measurements.items():
        cur.execute("""
            INSERT OR REPLACE INTO readings
              (device_id, ts, metric, value)
            VALUES (?, ?, ?, ?)
        """, (device_id, ts_iso, metric, value))

    conn.commit()
    conn.close()

@app.route('/widget/<device_id>')
def widget_detail(device_id):
    # Find the widget instance matching this device_id
    for w in widgets:
        if getattr(w, 'device_info', {}).get('id') == device_id:
            html = w.render()
            return render_template('widget_detail.html',
                                   widget_html=html,
                                   config=config)
    return "Widget not found", 404

if __name__ == "__main__":
    # Start the Flask development server; adjust host/port as needed
    app.run(host="0.0.0.0", port=5000)