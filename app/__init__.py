from flask import Flask
from flask_cors import CORS
import os
from config.config import config

def create_app(config_name='default'):
    app = Flask(__name__)
    CORS(app)
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app