from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Config(db.Model):
    """Configuration model for fraud detection settings"""
    __tablename__ = 'configs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # SMTP Configuration Group
    smtp_server = db.Column(db.String(255), default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, default=587)
    sender_email = db.Column(db.String(255), default='')
    sender_password = db.Column(db.String(255), default='')
    recipient_emails = db.Column(db.Text, default='fraud-team@company.com')
    
    # Detection Parameters Group
    time_window_minutes = db.Column(db.Integer, default=5)
    amount_variance = db.Column(db.Float, default=0.1)
    min_transactions_rollover = db.Column(db.Integer, default=3)
    split_threshold = db.Column(db.Integer, default=2)
    rapid_back_forth_threshold = db.Column(db.Integer, default=2)
    
    # Risk Thresholds Group
    high_risk_score = db.Column(db.Integer, default=50)
    medium_risk_score = db.Column(db.Integer, default=30)
    
    # Notification Settings Group
    email_enabled = db.Column(db.Boolean, default=False)
    notify_high_risk = db.Column(db.Boolean, default=True)
    notify_medium_risk = db.Column(db.Boolean, default=False)
    notify_split_transactions = db.Column(db.Boolean, default=True)
    notify_rollover_fraud = db.Column(db.Boolean, default=True)
    notify_rapid_patterns = db.Column(db.Boolean, default=True)
    
    # Email Settings Group
    email_subject_prefix = db.Column(db.String(100), default='[Fraud Alert] ')
    
    # System Settings
    name = db.Column(db.String(100), default='Default Configuration')
    description = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Config {self.name}>'
    
    def to_dict(self):
        """Convert config to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            
            # SMTP Configuration
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'sender_email': self.sender_email,
            'sender_password': self.sender_password,
            'recipient_emails': self.recipient_emails,
            
            # Detection Parameters
            'time_window_minutes': self.time_window_minutes,
            'amount_variance': self.amount_variance,
            'min_transactions_rollover': self.min_transactions_rollover,
            'split_threshold': self.split_threshold,
            'rapid_back_forth_threshold': self.rapid_back_forth_threshold,
            
            # Risk Thresholds
            'high_risk_score': self.high_risk_score,
            'medium_risk_score': self.medium_risk_score,
            
            # Notification Settings
            'email_enabled': self.email_enabled,
            'notify_high_risk': self.notify_high_risk,
            'notify_medium_risk': self.notify_medium_risk,
            'notify_split_transactions': self.notify_split_transactions,
            'notify_rollover_fraud': self.notify_rollover_fraud,
            'notify_rapid_patterns': self.notify_rapid_patterns,
            
            # Email Settings
            'email_subject_prefix': self.email_subject_prefix,
            
            # System Settings
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_recipient_list(self):
        """Parse recipient emails from text field"""
        if not self.recipient_emails:
            return []
        return [email.strip() for email in self.recipient_emails.split(',') if email.strip()]


class DetectionLog(db.Model):
    """Model for logging fraud detection runs"""
    __tablename__ = 'detection_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('configs.id'), nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Results
    total_transactions = db.Column(db.Integer, default=0)
    flagged_transactions = db.Column(db.Integer, default=0)
    split_cases = db.Column(db.Integer, default=0)
    rollover_cases = db.Column(db.Integer, default=0)
    rapid_cases = db.Column(db.Integer, default=0)
    high_risk_count = db.Column(db.Integer, default=0)
    
    # File paths
    result_file = db.Column(db.String(500), nullable=True)
    report_file = db.Column(db.String(500), nullable=True)
    log_messages = db.Column(db.Text, default='')
    
    # Metadata
    initiated_by = db.Column(db.String(100))
    
    # Relationships
    config = db.relationship('Config', backref=db.backref('logs', lazy=True))
    
    def __repr__(self):
        return f'<DetectionLog {self.id} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'config_id': self.config_id,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_transactions': self.total_transactions,
            'flagged_transactions': self.flagged_transactions,
            'split_cases': self.split_cases,
            'rollover_cases': self.rollover_cases,
            'rapid_cases': self.rapid_cases,
            'high_risk_count': self.high_risk_count,
            'initiated_by': self.initiated_by
        }


class SuspiciousAccount(db.Model):
    """Model for storing suspicious accounts from detection runs"""
    __tablename__ = 'suspicious_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    detection_log_id = db.Column(db.Integer, db.ForeignKey('detection_logs.id'), nullable=False)
    
    # Account details
    phone_number = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(255))
    
    # Risk assessment
    fraud_score = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(10), nullable=False)  # HIGH, MEDIUM, LOW
    suspicious_transactions = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Fraud types detected
    split_detected = db.Column(db.Boolean, default=False)
    rollover_detected = db.Column(db.Boolean, default=False)
    rapid_detected = db.Column(db.Boolean, default=False)
    
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    detection_log = db.relationship('DetectionLog', backref=db.backref('suspicious_accounts', lazy=True))
    
    def __repr__(self):
        return f'<SuspiciousAccount {self.phone_number} - {self.risk_level}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'account_name': self.account_name,
            'fraud_score': self.fraud_score,
            'risk_level': self.risk_level,
            'suspicious_transactions': self.suspicious_transactions,
            'total_amount': self.total_amount,
            'split_detected': self.split_detected,
            'rollover_detected': self.rollover_detected,
            'rapid_detected': self.rapid_detected,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }