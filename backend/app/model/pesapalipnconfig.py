
from app import db
from datetime import datetime

class PesapalIPNConfig(db.Model):
    """Stores Pesapal IPN configurations"""
    __tablename__ = 'pesapal_ipn_configs'

    id = db.Column(db.Integer, primary_key=True)
    ipn_url = db.Column(db.String(500), unique=True, nullable=False, index=True)
    notification_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    environment = db.Column(db.String(20), nullable=False, default='SANDBOX')
    ipn_notification_type = db.Column(db.String(10), default='GET')
    response_data = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PesapalIPNConfig id={self.id} notification_id={self.notification_id} environment={self.environment}>"

    def to_dict(self):
        return {
            'id': self.id,
            'ipn_url': self.ipn_url,
            'notification_id': self.notification_id,
            'environment': self.environment,
            'ipn_notification_type': self.ipn_notification_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

