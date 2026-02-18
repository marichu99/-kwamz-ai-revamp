# app/models/fraud_alert.py
from datetime import datetime
from decimal import Decimal
from app import db
import json

class FraudAlert(db.Model):
    __tablename__ = 'fraud_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fraud_type = db.Column(db.String(50), nullable=False)  # split_transaction, rollover_fraud, rapid_back_forth
    account_phone = db.Column(db.String(20), nullable=True)
    account_name = db.Column(db.String(100), nullable=True)
    transaction_count = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    fraud_score = db.Column(db.Integer, default=0)
    risk_level = db.Column(db.String(20), default='MEDIUM')  # HIGH, MEDIUM, LOW
    receipt_nos = db.Column(db.Text, nullable=True)  # Comma-separated receipt numbers
    transaction_ids = db.Column(db.Text, nullable=True)  # Comma-separated transaction IDs
    receipt_hash = db.Column(db.BigInteger, nullable=True, index=True)  # Hash for deduplication
    detection_details = db.Column(db.JSON, nullable=True)  # Full detection details
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='fraud_alerts', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'fraud_type': self.fraud_type,
            'account_phone': self.account_phone,
            'account_name': self.account_name,
            'transaction_count': self.transaction_count,
            'total_amount': str(self.total_amount),
            'fraud_score': self.fraud_score,
            'risk_level': self.risk_level,
            'receipt_nos': self.receipt_nos.split(',') if self.receipt_nos else [],
            'transaction_ids': [int(id) for id in self.transaction_ids.split(',')] if self.transaction_ids else [],
            'detection_details': self.detection_details,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if self.resolved_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

class FraudReportHistory(db.Model):
    __tablename__ = 'fraud_report_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # 'historical' for the one-time full scan, 'periodic' for recurring checks
    report_type = db.Column(db.String(20), nullable=True, default='historical')
    analysis_period_days = db.Column(db.Integer, nullable=True)
    total_transactions = db.Column(db.Integer, default=0)
    suspicious_patterns = db.Column(db.Integer, default=0)
    accounts_flagged = db.Column(db.Integer, default=0)
    report_data = db.Column(db.JSON, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='fraud_reports', lazy=True)