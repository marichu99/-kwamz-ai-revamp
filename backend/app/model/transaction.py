from datetime import datetime
from decimal import Decimal
from app import db

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String(50), nullable=False, index=True)
    completion_time = db.Column(db.DateTime, nullable=False)
    initiation_time = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.Text, nullable=False)
    transaction_status = db.Column(db.String(50), nullable=False)
    paid_in = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    withdrawn = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    balance = db.Column(db.Numeric(precision=15, scale=2), nullable=False)
    balance_confirmed = db.Column(db.Boolean, default=False)
    reason_type = db.Column(db.String(100), nullable=False)
    other_party_info = db.Column(db.Text, nullable=True)
    linked_transaction_id = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    currency = db.Column(db.String(10), default='KES')
    
    # Transaction type: 'float' or 'commission'
    transaction_type = db.Column(db.String(20), default='float', nullable=False, index=True)
    
    # Commission specific fields (only for commission type)
    commission_rate = db.Column(db.Numeric(precision=5, scale=2), default=Decimal('0.00'))
    commission_amount = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    parent_transaction_id = db.Column(db.Integer, nullable=True)
    
    # Foreign keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    agent_id = db.Column(db.Integer, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='transactions', lazy=True)
    
    def to_dict(self):
        data = {
            'id': self.id,
            'receipt_no': self.receipt_no,
            'completion_time': self.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
            'initiation_time': self.initiation_time.strftime('%Y-%m-%d %H:%M:%S'),
            'details': self.details,
            'transaction_status': self.transaction_status,
            'paid_in': str(self.paid_in),
            'withdrawn': str(self.withdrawn),
            'balance': str(self.balance),
            'balance_confirmed': self.balance_confirmed,
            'reason_type': self.reason_type,
            'other_party_info': self.other_party_info,
            'linked_transaction_id': self.linked_transaction_id,
            'account_number': self.account_number,
            'currency': self.currency,
            'transaction_type': self.transaction_type,
            'company_id': self.company_id,
            'agent_id': self.agent_id,
            'company_name': self.company.company_name if self.company else None,
            'shortcode': self.company.shortcode if self.company else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
        
        # Add commission-specific fields for commission transactions
        if self.transaction_type == 'commission':
            data.update({
                'commission_rate': str(self.commission_rate),
                'commission_amount': str(self.commission_amount),
                'parent_transaction_id': self.parent_transaction_id,
                'is_commission': True
            })
        
        return data

class TransactionStats(db.Model):
    __tablename__ = 'transaction_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    agent_id = db.Column(db.Integer, nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    
    # Statistics
    total_transactions = db.Column(db.Integer, default=0)
    total_deposits = db.Column(db.Integer, default=0)
    total_withdrawals = db.Column(db.Integer, default=0)
    total_deposit_amount = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    total_withdrawal_amount = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    net_flow = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='transaction_stats', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('date', 'agent_id', 'company_id', name='unique_daily_stats'),
    )