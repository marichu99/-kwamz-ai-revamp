from app import db
from datetime import date, datetime
from decimal import Decimal


class Director(db.Model):
    __tablename__ = 'directors'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    id_number = db.Column(db.String(50), nullable=True)

    def __init__(self, company_id, name, email=None, id_number=None):
        self.company_id = company_id
        self.name = name
        self.email = email
        self.id_number = id_number

    def __repr__(self):
        return f'<Director {self.name}>'