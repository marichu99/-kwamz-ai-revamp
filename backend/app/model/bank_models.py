from datetime import datetime
from enum import Enum

from app import db
class BankConnectionType(Enum):
    SFTP = "sftp"
    API = "api"
    SWIFT = "swift"
    FTP = "ftp"
    AS2 = "as2"

class BankStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    TESTING = "testing"

class Bank(db.Model):
    __tablename__ = 'banks'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(db.Enum(BankStatus), default=BankStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(255), nullable=False)
    
    # Relationship
    config = db.relationship('BankConfig', backref='bank', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'country': self.country,
            'currency': self.currency,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'config': self.config.to_dict() if self.config else None
        }
