"""
base_widget.py

Defines the BaseWidget class that all dashboard widgets inherit from.
"""

class BaseWidget:
    """
    Base class for all dashboard widgets.
    Provides lifecycle hooks and common utilities.
    """

    def __init__(self, app, config, device_info=None):
        """
        :param app: The Flask application instance
        :param config: Widget-specific configuration dictionary
        :param device_info: Optional device metadata from config.yaml
        """
        self.app = app
        self.config = config
        self.device_info = device_info or {}
        # Register the widget's HTTP routes (API endpoints)
        self.register_routes()

    def register_routes(self):
        """
        Override in subclasses to attach Flask routes or API endpoints.
        Called once during initialization.
        """
        pass

    def get_data(self):
        """
        Override in subclasses to fetch data (current or historical).
        Should return a dict or list that can be JSON-serialized.
        """
        return {}

    def render(self):
        """
        Override in subclasses to render and return the widget's HTML.
        Must return a string of HTML, typically via Jinja2 template rendering.
        """
        raise NotImplementedError("render() not implemented for BaseWidget")
