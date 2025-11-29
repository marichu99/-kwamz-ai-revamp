from app import db
from datetime import datetime
from typing import Optional
from app.enums.paymentstatus import PaymentStatus
class PesapalPayment(db.Model):
    """Stores Pesapal payment transactions"""
    __tablename__ = 'pesapal_payments'

    id = db.Column(db.Integer, primary_key=True)
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Pesapal specific fields
    merchant_reference = db.Column(db.String(100), unique=True, nullable=False, index=True)
    order_tracking_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    confirmation_code = db.Column(db.String(100), unique=True, nullable=True, index=True)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='KES', nullable=False)
    description = db.Column(db.String(500), nullable=True)
    
    # Customer details
    customer_email = db.Column(db.String(255), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    customer_first_name = db.Column(db.String(100), nullable=True)
    customer_last_name = db.Column(db.String(100), nullable=True)
    
    # Payment status
    payment_status = db.Column(db.String(20), default='PENDING', nullable=False, index=True)
    payment_method = db.Column(db.String(50), nullable=True)
    
    # Pesapal response data
    status_code = db.Column(db.Integer, nullable=True)
    payment_status_description = db.Column(db.String(255), nullable=True)
    redirect_url = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Additional metadata
    callback_data = db.Column(db.JSON, nullable=True)
    ipn_data = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('pesapal_payments', lazy=True))

    def __repr__(self):
        return (f"<PesapalPayment id={self.id} merchant_ref={self.merchant_reference} "
                f"status={self.payment_status} amount={self.amount}>")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'merchant_reference': self.merchant_reference,
            'order_tracking_id': self.order_tracking_id,
            'confirmation_code': self.confirmation_code,
            'amount': self.amount,
            'currency': self.currency,
            'description': self.description,
            'customer_email': self.customer_email,
            'customer_first_name': self.customer_first_name,
            'customer_last_name': self.customer_last_name,
            'customer_phone': self.customer_phone,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'status_code': self.status_code,
            'payment_status_description': self.payment_status_description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }

    @property
    def is_paid(self):
        """Check if payment is completed"""
        return self.payment_status == PaymentStatus.COMPLETED.value

    @property
    def is_pending(self):
        """Check if payment is pending"""
        return self.payment_status == PaymentStatus.PENDING.value

    def mark_as_paid(self, confirmation_code: str, payment_method: Optional[str] = None):
        """Mark payment as completed"""
        self.payment_status = PaymentStatus.COMPLETED.value
        self.confirmation_code = confirmation_code
        self.paid_at = datetime.utcnow()
        if payment_method:
            self.payment_method = payment_method

    def mark_as_failed(self, error_message: str):
        """Mark payment as failed"""
        self.payment_status = PaymentStatus.FAILED.value
        self.error_message = error_message

