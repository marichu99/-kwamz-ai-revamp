from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from decimal import Decimal

db = SQLAlchemy()
class Shareholder(db.Model):
    __tablename__ = 'shareholders'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    id_number = db.Column(db.String(50), nullable=True)
    shareholder_type = db.Column(db.String(20), nullable=False)  # e.g., 'primary', 'director', 'secondary'
    shares = db.Column(db.Numeric(precision=5, scale=2), default=Decimal('0.00'), nullable=False)

    def __init__(self, company_id, name, shareholder_type, shares=Decimal('0.00'), email=None, id_number=None):
        self.company_id = company_id
        self.name = name
        self.email = email
        self.id_number = id_number
        self.shareholder_type = shareholder_type
        self.shares = shares

    def __repr__(self):
        return f'<Shareholder {self.name} ({self.shareholder_type})>'