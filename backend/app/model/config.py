from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Config(db.Model):
    """Configuration model for fraud detection settings"""
    __tablename__ = 'configs'

    # Default per-fraud-type configurations
    FRAUD_TYPE_DEFAULTS = {
        'split_transaction': {
            'enabled': True,
            'time_window_minutes': 5,
            'amount_variance': 0.1,
            'split_threshold': 5,
            'split_min_amount': 100.0,
            'split_max_amount': 50000.0,
            'split_total_amount_threshold': 10000.0,
        },
        'rollover_fraud': {
            'enabled': True,
            'time_window_minutes': 5,
            'min_transactions_rollover': 3,
        },
        'rapid_back_forth': {
            'enabled': True,
            'time_window_minutes': 5,
            'amount_variance': 0.1,
            'rapid_back_forth_threshold': 2,
        },
    }

    # Fraud type metadata for display in the UI
    FRAUD_TYPE_INFO = {
        'split_transaction': {
            'display_name': 'Split Transaction Detection',
            'description': (
                'Detects when a large transaction is broken into multiple smaller transactions '
                'to avoid detection thresholds. Monitors for rapid sequences of similar-amount '
                'transactions from the same account within a short time window.'
            ),
            'parameters': {
                'time_window_minutes': {'label': 'Time Window (minutes)', 'type': 'integer', 'min': 1, 'max': 240},
                'amount_variance': {'label': 'Amount Variance', 'type': 'float', 'min': 0.01, 'max': 1.0},
                'split_threshold': {'label': 'Min Split Transactions', 'type': 'integer', 'min': 2, 'max': 50},
                'split_min_amount': {'label': 'Min Amount (KES)', 'type': 'float', 'min': 0},
                'split_max_amount': {'label': 'Max Amount (KES)', 'type': 'float', 'min': 0},
                'split_total_amount_threshold': {'label': 'Total Amount Threshold (KES)', 'type': 'float', 'min': 0},
            },
        },
        'rollover_fraud': {
            'display_name': 'Rollover Fraud Detection',
            'description': (
                'Identifies repeated deposit or withdrawal clusters \u2014 when an account makes many '
                'consecutive transactions of the same type (all deposits or all withdrawals) in rapid '
                'succession, suggesting money laundering or float manipulation.'
            ),
            'parameters': {
                'time_window_minutes': {'label': 'Time Window (minutes)', 'type': 'integer', 'min': 1, 'max': 60},
                'min_transactions_rollover': {'label': 'Min Consecutive Transactions', 'type': 'integer', 'min': 2, 'max': 50},
            },
        },
        'rapid_back_forth': {
            'display_name': 'Rapid Back-and-Forth Detection',
            'description': (
                'Flags accounts that rapidly alternate between deposits and withdrawals of similar '
                'amounts, which may indicate money laundering, testing stolen credentials, or '
                'unauthorized float movement.'
            ),
            'parameters': {
                'time_window_minutes': {'label': 'Time Window (minutes)', 'type': 'integer', 'min': 1, 'max': 60},
                'amount_variance': {'label': 'Amount Variance', 'type': 'float', 'min': 0.01, 'max': 1.0},
                'rapid_back_forth_threshold': {'label': 'Rapid Pattern Threshold', 'type': 'integer', 'min': 2, 'max': 20},
            },
        },
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship
    user = db.relationship('User', backref=db.backref('configs', lazy=True))

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
    split_threshold = db.Column(db.Integer, default=5)  # Min number of transactions to flag as split
    rapid_back_forth_threshold = db.Column(db.Integer, default=2)

    # Split Transaction Thresholds
    split_min_amount = db.Column(db.Float, default=100.0)  # Min amount per transaction to consider (e.g., 100 KES)
    split_max_amount = db.Column(db.Float, default=50000.0)  # Max amount per transaction to consider (e.g., 50000 KES)
    split_total_amount_threshold = db.Column(db.Float, default=10000.0)  # Total amount threshold that triggers suspicion

    # Per-fraud-type configuration (JSON) — overrides flat columns when present
    fraud_type_configs = db.Column(db.JSON, nullable=True)

    # Risk Thresholds Group
    high_risk_score = db.Column(db.Integer, default=50)
    medium_risk_score = db.Column(db.Integer, default=30)

    # Periodic Check Settings (configurable time intervals for fraud detection)
    periodic_check_interval_minutes = db.Column(db.Integer, default=30)  # How often to run periodic fraud checks and send notifications (in minutes)
    analysis_period_days = db.Column(db.Integer, default=30)  # Days to analyze for historical reports
    max_transactions_per_check = db.Column(db.Integer, default=100)  # Max transactions per shortcode check

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
            'user_id': self.user_id,
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

            # Split Transaction Thresholds
            'split_min_amount': self.split_min_amount,
            'split_max_amount': self.split_max_amount,
            'split_total_amount_threshold': self.split_total_amount_threshold,

            # Per-fraud-type configs
            'fraud_type_configs': self.fraud_type_configs or self._build_fraud_type_configs_from_flat(),
            'fraud_type_info': self.FRAUD_TYPE_INFO,

            # Risk Thresholds
            'high_risk_score': self.high_risk_score,
            'medium_risk_score': self.medium_risk_score,

            # Periodic Check Settings
            'periodic_check_interval_minutes': self.periodic_check_interval_minutes,
            'analysis_period_days': self.analysis_period_days,
            'max_transactions_per_check': self.max_transactions_per_check,

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
    
    def _build_fraud_type_configs_from_flat(self):
        """Build fraud_type_configs dict from legacy flat columns for backward compatibility."""
        return {
            'split_transaction': {
                'enabled': True,
                'time_window_minutes': self.time_window_minutes or 5,
                'amount_variance': self.amount_variance or 0.1,
                'split_threshold': self.split_threshold or 5,
                'split_min_amount': self.split_min_amount or 100.0,
                'split_max_amount': self.split_max_amount or 50000.0,
                'split_total_amount_threshold': self.split_total_amount_threshold or 10000.0,
            },
            'rollover_fraud': {
                'enabled': True,
                'time_window_minutes': self.time_window_minutes or 5,
                'min_transactions_rollover': self.min_transactions_rollover or 3,
            },
            'rapid_back_forth': {
                'enabled': True,
                'time_window_minutes': self.time_window_minutes or 5,
                'amount_variance': self.amount_variance or 0.1,
                'rapid_back_forth_threshold': self.rapid_back_forth_threshold or 2,
            },
        }

    def get_recipient_list(self):
        """Parse recipient emails from text field"""
        if not self.recipient_emails:
            return []
        return [email.strip() for email in self.recipient_emails.split(',') if email.strip()]


class SmtpConfig(db.Model):
    """Global SMTP configuration — singleton table, admin-only."""
    __tablename__ = 'smtp_configs'

    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(255), default='smtp.gmail.com')
    smtp_port = db.Column(db.Integer, default=587)
    sender_email = db.Column(db.String(255), default='')
    sender_password = db.Column(db.String(255), default='')
    recipient_emails = db.Column(db.Text, default='')
    email_subject_prefix = db.Column(db.String(100), default='[Fraud Alert] ')
    email_enabled = db.Column(db.Boolean, default=False)
    trial_days = db.Column(db.Integer, default=30)
    rate_per_till = db.Column(db.Numeric(10, 2), default=200.00)
    pesapal_callback_url = db.Column(db.String(500), nullable=True)
    pesapal_environment = db.Column(db.String(20), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    @classmethod
    def get_global(cls):
        """Return the single global SMTP config row, creating one if needed."""
        row = cls.query.first()
        if not row:
            row = cls()
            db.session.add(row)
            db.session.commit()
        return row

    def to_dict(self):
        return {
            'id': self.id,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'sender_email': self.sender_email,
            'sender_password': self.sender_password,
            'recipient_emails': self.recipient_emails,
            'email_subject_prefix': self.email_subject_prefix,
            'email_enabled': self.email_enabled,
            'trial_days': self.trial_days if self.trial_days is not None else 30,
            'rate_per_till': float(self.rate_per_till) if self.rate_per_till is not None else 200.0,
            'pesapal_callback_url': self.pesapal_callback_url,
            'pesapal_environment': self.pesapal_environment,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }

    def from_dict(self, data):
        """Update fields from a dictionary."""
        allowed = [
            'smtp_server', 'smtp_port', 'sender_email', 'sender_password',
            'recipient_emails', 'email_subject_prefix', 'email_enabled',
            'trial_days', 'rate_per_till', 'pesapal_callback_url', 'pesapal_environment',
        ]
        for key in allowed:
            if key in data:
                setattr(self, key, data[key])


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