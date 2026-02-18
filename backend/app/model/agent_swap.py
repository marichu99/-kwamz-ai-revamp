from app import db
from datetime import datetime
from decimal import Decimal


class AgentSwap(db.Model):
    __tablename__ = 'agent_swaps'

    id = db.Column(db.Integer, primary_key=True)
    agent_company_id = db.Column(
        db.Integer,
        db.ForeignKey('agentcompanies.id'),
        nullable=False,
        index=True
    )
    initiated_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    swap_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    float_balance_at_swap = db.Column(
        db.Numeric(precision=15, scale=2),
        default=Decimal('0.00')
    )
    commission_balance_at_swap = db.Column(
        db.Numeric(precision=15, scale=2),
        default=Decimal('0.00')
    )
    previous_agents = db.Column(db.JSON, default=list)
    new_agents = db.Column(db.JSON, default=list)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='completed', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    agent_company = db.relationship('AgentCompany', backref=db.backref('swaps', lazy='dynamic'))
    initiator = db.relationship('User', backref=db.backref('initiated_swaps', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_swap_date', 'swap_date'),
        db.Index('idx_swap_company', 'agent_company_id', 'swap_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'agent_company_id': self.agent_company_id,
            'agent_company_name': self.agent_company.company_name if self.agent_company else None,
            'initiated_by': self.initiated_by,
            'initiator_name': self.initiator.username if self.initiator else None,
            'swap_date': self.swap_date.isoformat() if self.swap_date else None,
            'float_balance_at_swap': str(self.float_balance_at_swap or 0),
            'commission_balance_at_swap': str(self.commission_balance_at_swap or 0),
            'previous_agents': self.previous_agents or [],
            'new_agents': self.new_agents or [],
            'notes': self.notes,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
