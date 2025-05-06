from .base_widget import BaseWidget
import time
from flask import jsonify

class ClockWidget(BaseWidget):
    """
    Widget for displaying a live clock on the dashboard.
    Provides an API endpoint for current server time and renders a clock template.
    """
    def register_routes(self):
        # API endpoint to fetch the current server time
        @self.app.route("/api/clock")
        def api_clock():
            ts = time.time()
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            return jsonify({"ts": ts, "datetime": dt})

    def render(self):
        """
        Render the clock widget's HTML template.
        """
        template = self.app.jinja_env.get_template('widgets/clock.html')
        return template.render()
