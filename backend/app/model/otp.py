from app import db
from datetime import datetime

class Otp(db.Model):
    __tablename__ = 'otp'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    time_generated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, email, otp, time_generated=None):
        self.email = email
        self.otp = otp
        self.time_generated = time_generated or datetime.utcnow()

    def __repr__(self):
        return f'<Otp email={self.email} otp={self.otp}>'
