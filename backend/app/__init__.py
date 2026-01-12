from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from google.cloud import storage
from app.config.celery_config import celery
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
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['GCP_BUCKET'] = os.getenv('GCP_BUCKET', 'trovana-docs')
    app.config['SECRET_KEY']   = 'my-secret-key'
    app.config['DEBUG']        = False
    app.config['DATABASE_URI']  = os.getenv('DATABASE_URL','postgresql://user:pass@localhost/db')
    app.config['REDIS_URL']    = os.getenv('REDIS_URL','redis://localhost:6379/0')
    app.config['CELERY_BROKER_URL']  =os.getenv('CELERY_BROKER_URL','redis://localhost:6379/0')
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)
    
    # Import models here so they are always registered
    from app.model.company import Company
    from app.model.agentcompany import AgentCompany
    from app.model.agent_accounts import AgentAccount
    from app.model.agent_account_balances import AgentAccountBalance
    from app.model.useragent import UserAgent
    from app.model.director import Director
    from app.model.shareholder import Shareholder
    from app.model.document import Document
    from app.model.user import User
    from app.model.payment import Payment
    from app.model.otp import Otp
    from app.model.pesalpalpayment import PesapalPayment
    from app.model.pesapalipnconfig import PesapalIPNConfig
    from app.model.pesapalrefund import PesapalRefund
    from app.model.bank_config import BankConfig
    from app.model.bank_models import Bank
    from app.model.email_outbox import EmailOutbox
    from app.model.transaction import Transaction, TransactionStats
    from app.model.fraud_alert import FraudAlert,FraudReportHistory
    from app.model.config import Config,DetectionLog,SuspiciousAccount
    
    # Initialize Pesapal Client and Payment Service
    from app.utils.pesapalclient import PesapalClient, PesapalConfig, FlaskIPNStorage
    from app.utils.pesapalutils import PesapalPaymentService
    from app.service.transaction_service import TransactionService
    
    flaskipn_storage = FlaskIPNStorage()
    pesapal_config = PesapalConfig()
    pesapal_client = PesapalClient(config=pesapal_config,ipn_storage=flaskipn_storage)
    payment_service = PesapalPaymentService(pesapal_client=pesapal_client)
    
    # initialize Google Cloud Storage client
    from app.service.document_service import DocumentProcessingService
    storage_client = storage.Client.from_service_account_json(
                    os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                    )
    bucket_name = os.getenv('GCP_BUCKET', 'trovana-docs')
    document_service = DocumentProcessingService(storage_client=storage_client, bucket_name=bucket_name)        
    transaction_service = TransactionService()
    
    with app.app_context():
        db.create_all()
        pesapal_client.initialize()
        
    # Attach to app for access in blueprints
    app.payment_service = payment_service
    app.pesapal_client = pesapal_client
    app.document_service = document_service        
    app.transaction_service = transaction_service

    # Register blueprints
    from app.controller.user_controller import user_bp
    from app.controller.bank_controller import bank_bp
    from app.controller.document_controller import document_bp
    from app.controller.mpesa_controller import mpesa_bp
    from app.controller.payment_controller import payment_bp
    from app.controller.useragent_controller import user_agent_bp
    from app.controller.agentcompany_controller import agent_company_bp
    from app.controller.company_controller import company_bp
    from app.controller.transaction_controller import transaction_bp

    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(bank_bp, url_prefix='/banks')
    app.register_blueprint(document_bp, url_prefix='/document')
    app.register_blueprint(mpesa_bp, url_prefix='/mpesa')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(user_agent_bp, url_prefix='/useragent')
    app.register_blueprint(agent_company_bp, url_prefix='/agentcompany')
    app.register_blueprint(company_bp, url_prefix='/company')
    app.register_blueprint(transaction_bp, url_prefix='/transactions')

    return app

