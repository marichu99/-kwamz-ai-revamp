from app import db
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import event
from typing import Optional, Dict, Any

class AgentAccountBalance(db.Model):
    __tablename__ = 'agent_account_balances'

    id = db.Column(db.Integer, primary_key=True)
    agent_account_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_accounts.id'),
        nullable=False
    )

    current_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'))
    available_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'))
    reserved_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'))
    unclear_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'))

    snapshot_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship('AgentAccount')

    __table_args__ = (
        db.Index('idx_balance_snapshot', 'snapshot_at'),
    )
    def __init__(self, agent_account_id, current_balance=Decimal('0.00'), available_balance=Decimal('0.00'),
                 reserved_balance=Decimal('0.00'), unclear_balance=Decimal('0.00'),
                 snapshot_at=None):
        self.agent_account_id = agent_account_id
        self.current_balance = current_balance
        self.available_balance = available_balance
        self.reserved_balance = reserved_balance
        self.unclear_balance = unclear_balance
        if snapshot_at:
            self.snapshot_at = snapshot_at
    def __repr__(self):
        return f'<AgentAccountBalance AccountID: {self.agent_account_id} Balance: {self.current_balance}>'
    