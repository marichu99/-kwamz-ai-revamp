from app import db
from enum import Enum
import json
from app.model.bank_models import BankConnectionType
class BankConfig(db.Model):
    __tablename__ = 'bank_configs'
    
    id = db.Column(db.String(36), primary_key=True)
    bank_id = db.Column(db.String(36), db.ForeignKey('banks.id'), nullable=False)
    connection_type = db.Column(db.Enum(BankConnectionType), nullable=False)
    host = db.Column(db.String(255))
    port = db.Column(db.Integer)
    username = db.Column(db.String(255))
    password_encrypted = db.Column(db.Text)
    api_key_encrypted = db.Column(db.Text)
    base_url = db.Column(db.String(500))
    sftp_directory = db.Column(db.String(500))
    file_naming_convention = db.Column(db.String(255))
    supported_formats = db.Column(db.Text)  # JSON string
    timezone = db.Column(db.String(50), default='UTC')
    retry_attempts = db.Column(db.Integer, default=3)
    timeout_seconds = db.Column(db.Integer, default=30)
    additional_config = db.Column(db.Text)  # JSON string
    time_created = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'bank_id': self.bank_id,
            'connection_type': self.connection_type.value,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'base_url': self.base_url,
            'sftp_directory': self.sftp_directory,
            'file_naming_convention': self.file_naming_convention,
            'supported_formats': json.loads(self.supported_formats) if self.supported_formats else [],
            'timezone': self.timezone,
            'retry_attempts': self.retry_attempts,
            'timeout_seconds': self.timeout_seconds,
            'additional_config': json.loads(self.additional_config) if self.additional_config else {}
        }