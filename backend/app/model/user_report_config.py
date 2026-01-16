from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from app import db


class UserReportConfig(db.Model):
    """User Report Configuration model for scheduling reports and fraud detection settings"""
    __tablename__ = 'user_report_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Configuration name
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')

    # Report Type: periodic_fraud, historical_fraud, daily_fraud, commissions
    report_type = db.Column(db.String(50), nullable=False)

    # Frequency Configuration
    frequency_value = db.Column(db.Integer, nullable=False, default=1)  # e.g., 30
    frequency_unit = db.Column(db.String(20), nullable=False, default='days')  # minutes, hours, days

    # Email Recipients (comma-separated)
    recipient_emails = db.Column(db.Text, nullable=False)

    # ========== FRAUD DETECTION PARAMETERS ==========
    # Time window for detecting patterns (in minutes)
    time_window_minutes = db.Column(db.Integer, default=5)

    # Amount variance tolerance (0.1 = 10%)
    amount_variance = db.Column(db.Float, default=0.1)

    # Minimum transactions for rollover fraud detection
    min_transactions_rollover = db.Column(db.Integer, default=3)

    # Split Transaction Thresholds
    split_threshold = db.Column(db.Integer, default=5)  # Min number of transactions to flag as split
    split_min_amount = db.Column(db.Float, default=100.0)  # Min amount per transaction (e.g., 100 KES)
    split_max_amount = db.Column(db.Float, default=50000.0)  # Max amount per transaction
    split_total_amount_threshold = db.Column(db.Float, default=10000.0)  # Total amount threshold

    # Rapid back-forth threshold
    rapid_back_forth_threshold = db.Column(db.Integer, default=2)

    # Risk Score Thresholds
    high_risk_score = db.Column(db.Integer, default=50)
    medium_risk_score = db.Column(db.Integer, default=30)

    # Analysis Settings
    analysis_period_days = db.Column(db.Integer, default=30)  # Days to analyze for historical reports
    max_transactions_per_check = db.Column(db.Integer, default=100)  # Max transactions per shortcode check

    # Notification Settings
    notify_high_risk = db.Column(db.Boolean, default=True)
    notify_medium_risk = db.Column(db.Boolean, default=False)
    notify_split_transactions = db.Column(db.Boolean, default=True)
    notify_rollover_fraud = db.Column(db.Boolean, default=True)
    notify_rapid_patterns = db.Column(db.Boolean, default=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)

    # Timestamps
    last_run_at = db.Column(db.DateTime, nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with User
    user = db.relationship('User', backref=db.backref('report_configs', lazy=True))

    def __repr__(self):
        return f'<UserReportConfig {self.name} - {self.report_type}>'

    def to_dict(self):
        """Convert config to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'report_type': self.report_type,
            'frequency_value': self.frequency_value,
            'frequency_unit': self.frequency_unit,
            'recipient_emails': self.recipient_emails,

            # Fraud Detection Parameters
            'time_window_minutes': self.time_window_minutes,
            'amount_variance': self.amount_variance,
            'min_transactions_rollover': self.min_transactions_rollover,
            'split_threshold': self.split_threshold,
            'split_min_amount': self.split_min_amount,
            'split_max_amount': self.split_max_amount,
            'split_total_amount_threshold': self.split_total_amount_threshold,
            'rapid_back_forth_threshold': self.rapid_back_forth_threshold,
            'high_risk_score': self.high_risk_score,
            'medium_risk_score': self.medium_risk_score,
            'analysis_period_days': self.analysis_period_days,
            'max_transactions_per_check': self.max_transactions_per_check,

            # Notification Settings
            'notify_high_risk': self.notify_high_risk,
            'notify_medium_risk': self.notify_medium_risk,
            'notify_split_transactions': self.notify_split_transactions,
            'notify_rollover_fraud': self.notify_rollover_fraud,
            'notify_rapid_patterns': self.notify_rapid_patterns,

            'is_active': self.is_active,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_fraud_detection_config(self):
        """Get fraud detection configuration as dictionary for FraudDetectionService"""
        return {
            'time_window_minutes': self.time_window_minutes or 5,
            'amount_variance': self.amount_variance or 0.1,
            'min_transactions_rollover': self.min_transactions_rollover or 3,
            'split_threshold': self.split_threshold or 5,
            'split_min_amount': self.split_min_amount or 100.0,
            'split_max_amount': self.split_max_amount or 50000.0,
            'split_total_amount_threshold': self.split_total_amount_threshold or 10000.0,
            'rapid_back_forth_threshold': self.rapid_back_forth_threshold or 2,
            'high_risk_score': self.high_risk_score or 50,
            'medium_risk_score': self.medium_risk_score or 30,
            'analysis_period_days': self.analysis_period_days or 30,
            'max_transactions_per_check': self.max_transactions_per_check or 100,
        }

    def get_recipient_list(self):
        """Parse recipient emails from text field"""
        if not self.recipient_emails:
            return []
        return [email.strip() for email in self.recipient_emails.split(',') if email.strip()]

    def get_frequency_in_minutes(self):
        """Convert frequency to minutes for scheduling"""
        unit_multipliers = {
            'minutes': 1,
            'hours': 60,
            'days': 1440
        }
        return self.frequency_value * unit_multipliers.get(self.frequency_unit, 1440)

    @staticmethod
    def get_report_type_display(report_type):
        """Get display name for report type"""
        report_types = {
            'periodic_fraud': 'Periodic Fraud Report',
            'historical_fraud': 'Historical Fraud Report',
            'daily_fraud': 'Daily Fraud Report',
            'commissions': 'Commissions Report'
        }
        return report_types.get(report_type, report_type)
