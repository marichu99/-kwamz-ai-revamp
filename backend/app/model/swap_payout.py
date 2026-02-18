from app import db
from datetime import datetime
from decimal import Decimal


class SwapPayout(db.Model):
    __tablename__ = 'swap_payouts'

    id = db.Column(db.Integer, primary_key=True)
    swap_id = db.Column(
        db.Integer,
        db.ForeignKey('agent_swaps.id'),
        nullable=False,
        index=True
    )
    agent_name = db.Column(db.String(255), nullable=False)
    agent_idnumber = db.Column(db.String(100))
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(precision=15, scale=2), nullable=False, default=Decimal('0.00'))
    conversation_id = db.Column(db.String(255))
    originator_conversation_id = db.Column(db.String(255))
    mpesa_receipt = db.Column(db.String(255))
    result_code = db.Column(db.Integer)
    result_desc = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending', nullable=False)
    initiated_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    swap = db.relationship('AgentSwap', backref=db.backref('payouts', lazy='dynamic'))
    initiator = db.relationship('User', backref=db.backref('initiated_payouts', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'swap_id': self.swap_id,
            'agent_name': self.agent_name,
            'agent_idnumber': self.agent_idnumber,
            'phone_number': self.phone_number,
            'amount': str(self.amount or 0),
            'conversation_id': self.conversation_id,
            'originator_conversation_id': self.originator_conversation_id,
            'mpesa_receipt': self.mpesa_receipt,
            'result_code': self.result_code,
            'result_desc': self.result_desc,
            'status': self.status,
            'initiated_by': self.initiated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
