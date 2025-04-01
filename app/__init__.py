"""MOAD AI Query Application."""
import os
from flask import Flask
from dotenv import load_dotenv
from app import routes

__version__ = '1.0.0'

def create_app(test_config=None):
    """Create and configure the Flask application."""
    # Load environment variables
    load_dotenv()

    app = Flask(__name__, 
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')
    
    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'dev_key'),
        CACHE_MAX_AGE=float(os.environ.get('CACHE_MAX_AGE_HOURS', 24)),
        DEBUG=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )
    
    # Load test config if passed in
    if test_config is not None:
        app.config.from_mapping(test_config)
    
    # Register blueprints
    routes.init_app(app)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    return app

# Export the create_app function
__all__ = ['create_app']

# app package 