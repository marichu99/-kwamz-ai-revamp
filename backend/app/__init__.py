from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    load_dotenv()

    # Load config
    app.config.from_pyfile('config.py', silent=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Change in production
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # Token expires in 1 hour

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)  # Enable CORS for React frontend

    # Register blueprints
    from app.controller.user_controller import user_bp
    from app.controller.document_controller import document_bp
    from app.controller.mpesa_controller import mpesa_bp
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(document_bp, url_prefix='/document')
    app.register_blueprint(mpesa_bp, url_prefix='/mpesa')

    return app