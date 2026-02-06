from app import db
from datetime import datetime
from decimal import Decimal


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    billing_period_start = db.Column(db.Date, nullable=False)
    billing_period_end = db.Column(db.Date, nullable=False)
    active_tills_count = db.Column(db.Integer, nullable=False, default=0)
    amount_due = db.Column(db.Numeric(precision=10, scale=2), nullable=False, default=Decimal('0.00'))
    amount_paid = db.Column(db.Numeric(precision=10, scale=2), default=Decimal('0.00'))
    status = db.Column(db.String(20), default='PENDING', nullable=False, index=True)
    pesapal_payment_id = db.Column(db.Integer, db.ForeignKey('pesapal_payments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))
    pesapal_payment = db.relationship('PesapalPayment', backref=db.backref('subscription', uselist=False))

    RATE_PER_TILL = Decimal('200.00')

    def __repr__(self):
        return (f"<Subscription id={self.id} user={self.user_id} "
                f"period={self.billing_period_start}..{self.billing_period_end} "
                f"status={self.status}>")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'billing_period_start': self.billing_period_start.isoformat() if self.billing_period_start else None,
            'billing_period_end': self.billing_period_end.isoformat() if self.billing_period_end else None,
            'active_tills_count': self.active_tills_count,
            'amount_due': float(self.amount_due) if self.amount_due else 0.0,
            'amount_paid': float(self.amount_paid) if self.amount_paid else 0.0,
            'status': self.status,
            'pesapal_payment_id': self.pesapal_payment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }

    @property
    def is_paid(self):
        return self.status == 'PAID'

    def mark_as_paid(self, pesapal_payment_id=None):
        self.status = 'PAID'
        self.paid_at = datetime.utcnow()
        self.amount_paid = self.amount_due
        if pesapal_payment_id:
            self.pesapal_payment_id = pesapal_payment_id
