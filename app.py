import yaml
from flask import Flask, render_template
import importlib
from sensor import init_db, store_reading
from controller import set_fan, set_light

app = Flask(__name__)

def load_config():
    with open('config.yaml') as f:
        return yaml.safe_load(f)

config = load_config()

# Dynamically instantiate widgets
widgets = []
for dev in config['devices']:
    wcfg = config['widgets'][dev['widget']]
    module = importlib.import_module(wcfg['module'])
    cls = getattr(module, wcfg['class'])
    widget = cls(app, wcfg, device_info=dev)
    widgets.append(widget)

@app.route('/')
def dashboard():
    # render base.html, passing each widget.render() output
    rendered = [w.render() for w in widgets]
    return render_template('base.html', widgets=rendered)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
