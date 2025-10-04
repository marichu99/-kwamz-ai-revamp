from datetime import date, datetime
from decimal import Decimal

from app import db

class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    registration_date = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(200), nullable=False)
    company_code = db.Column(db.String(100), nullable=False)
    compliance_status = db.Column(db.String(20), default='compliant', nullable=False)  # e.g., 'compliant', 'under_review', 'suspended'
    total_float_balance = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'), nullable=False)
    file_location = db.Column(db.Text, nullable=True)  # Storage path for CR12 document
    last_compliance_audit = db.Column(db.Date, nullable=True)

    # Relationships
    shareholders = db.relationship('Shareholder', backref='company', lazy=True, cascade='all, delete-orphan')
    directors = db.relationship('Director', backref='company', lazy=True, cascade='all, delete-orphan')
    agent_companies = db.relationship('AgentCompany', backref='company', lazy=True)

    def __init__(self, company_name, registration_number, address, company_code, registration_date=None,
                 compliance_status='compliant', total_float_balance=Decimal('0.00'), file_location=None,
                 last_compliance_audit=None, shareholders=None, directors=None):
        self.company_name = company_name
        self.registration_number = registration_number
        self.registration_date = registration_date
        self.address = address
        self.company_code = company_code
        self.compliance_status = compliance_status
        self.total_float_balance = total_float_balance
        self.file_location = file_location
        self.last_compliance_audit = last_compliance_audit
        if shareholders:
            self.shareholders = shareholders
        if directors:
            self.directors = directors

    def __repr__(self):
        return f'<Company {self.company_name}>'