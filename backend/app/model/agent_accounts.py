from app import db
from datetime import date, datetime

class AgentAccount(db.Model):
    __tablename__ = 'agent_accounts'

    id = db.Column(db.Integer, primary_key=True)

    agent_company_id = db.Column(
        db.Integer,
        db.ForeignKey('agentcompanies.id', ondelete='CASCADE'),
        nullable=False
    )

    account_number = db.Column(db.String(50), nullable=False)
    account_type = db.Column(
        db.String(30),
        nullable=False
    )  
    # examples: FLOAT, COMMISSION, ESCROW, SETTLEMENT

    account_alias = db.Column(db.String(100))
    currency = db.Column(db.String(10), default='KES')
    relationship = db.Column(db.String(50))  # Owned, Managed, Custodian
    status = db.Column(db.String(50), default='ACTIVE')
    is_hot_account = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_scraped_at = db.Column(db.DateTime)

    agent_company = db.relationship(
        'AgentCompany',
        back_populates='accounts'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'agent_company_id',
            'account_number',
            name='uq_agent_account'
        ),
        db.Index('idx_account_type', 'account_type'),
        db.Index('idx_account_number', 'account_number'),
    )
