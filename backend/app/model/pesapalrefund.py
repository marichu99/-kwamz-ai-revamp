from app import db
from datetime import datetime


class PesapalRefund(db.Model):
    """Stores Pesapal refund transactions"""
    __tablename__ = 'pesapal_refunds'

    id = db.Column(db.Integer, primary_key=True)
    
    # Link to original payment
    payment_id = db.Column(db.Integer, db.ForeignKey('pesapal_payments.id'), nullable=False, index=True)
    
    # Refund details
    confirmation_code = db.Column(db.String(100), nullable=False, index=True)
    refund_amount = db.Column(db.Float, nullable=False)
    refund_type = db.Column(db.String(20), default='FULL', nullable=False)  # FULL or PARTIAL
    
    # Refund status
    refund_status = db.Column(db.String(20), default='PENDING', nullable=False, index=True)
    refund_reference = db.Column(db.String(100), nullable=True)
    
    # User who initiated refund
    initiated_by = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    
    # Pesapal response
    response_data = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    payment = db.relationship('PesapalPayment', backref=db.backref('refunds', lazy=True))

    def __repr__(self):
        return (f"<PesapalRefund id={self.id} payment_id={self.payment_id} "
                f"amount={self.refund_amount} status={self.refund_status}>")

    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'confirmation_code': self.confirmation_code,
            'refund_amount': self.refund_amount,
            'refund_type': self.refund_type,
            'refund_status': self.refund_status,
            'initiated_by': self.initiated_by,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }

