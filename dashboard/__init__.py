# dashboard/__init__.py
import os
from flask import Flask

def create_dashboard_app():
    # os.path.dirname(__file__) is explicitly the 'dashboard' folder.
    # The parent of 'dashboard' is your true project root directory.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir) 
    
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    from .service import service_bp
    from .devices import devices_bp
    from .logs import logs_bp
    from .stats import stats_bp
    from .users import users_bp

    # Note: Flask strictly requires the trailing slash behavior to match your endpoints.
    # Setting strict_slashes=False handles requests with or without trailing slashes.
    app.url_map.strict_slashes = False

    app.register_blueprint(service_bp, url_prefix="/service")
    app.register_blueprint(devices_bp, url_prefix="/devices")
    app.register_blueprint(logs_bp, url_prefix="/logs")
    app.register_blueprint(stats_bp, url_prefix="/stats")
    app.register_blueprint(users_bp, url_prefix="/users")

    return app
