from app import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    result_code = db.Column(db.Integer, nullable=True)
    time_paid = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(15), nullable=True)
    checkout_id = db.Column(db.String(100), nullable=True)
    reference_code = db.Column(db.String(80), nullable=True)
    result_desc = db.Column(db.String(200), nullable=True)

    # Relationship (optional, enables access like `payment.user`)
    user = db.relationship('User', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f"<Payment id={self.id} user_id={self.user_id} amount={self.amount} time_paid={self.time_paid}>"
