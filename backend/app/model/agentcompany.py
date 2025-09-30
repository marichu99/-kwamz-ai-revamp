from app import db
from datetime import date, datetime
from decimal import Decimal

class AgentCompany(db.Model):
    __tablename__ = 'agentcompanies'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    agentcompany_code = db.Column(db.String(120), nullable=True)
    established_date = db.Column(db.Date, nullable=True)
    float_balance = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'), nullable=False)
    fraud_risk_level = db.Column(db.String(20), default='low', nullable=False)  # e.g., 'low', 'medium', 'high'
    fraud_risk_description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # e.g., 'active', 'inactive'
    till_number = db.Column(db.String(20), unique=True, nullable=True)  # M-Pesa till number
    daily_transaction_limit = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'), nullable=True)
    commission_rate = db.Column(db.Numeric(precision=5, scale=2), default=Decimal('0.00'), nullable=True)
    last_audit_date = db.Column(db.Date, nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    agents = db.relationship('UserAgent', backref='agent_company', lazy=True)

    def __init__(self, company_name, registration_number, location, contact_phone=None, email=None,agentcompany_code=None, 
                 established_date=None, float_balance=Decimal('0.00'), fraud_risk_level='low', 
                 fraud_risk_description=None, status='active', till_number=None, 
                 daily_transaction_limit=Decimal('0.00'), commission_rate=Decimal('0.00'), 
                 last_audit_date=None, company_id=None):
        self.company_name = company_name
        self.registration_number = registration_number
        self.location = location
        self.contact_phone = contact_phone
        self.email = email
        self.agentcompany_code = agentcompany_code
        self.established_date = established_date
        self.float_balance = float_balance
        self.fraud_risk_level = fraud_risk_level
        self.fraud_risk_description = fraud_risk_description
        self.status = status
        self.till_number = till_number
        self.daily_transaction_limit = daily_transaction_limit
        self.commission_rate = commission_rate
        self.last_audit_date = last_audit_date
        self.company_id = company_id

    def __repr__(self):
        return f'<AgentCompany {self.company_name}>'