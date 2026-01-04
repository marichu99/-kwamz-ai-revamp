from app import db
from datetime import datetime

class EmailOutbox(db.Model):
    __tablename__ = 'email_outbox'

    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(120), nullable=True)
    receiver = db.Column(db.String(120), nullable=True)
    reason = db.Column(db.String(120), nullable=True)
    business_short_code = db.Column(db.String(120), nullable=True)
    sent_times = db.Column(db.Integer, nullable=True)
    
    time_generated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, sender, receiver, reason, business_short_code, sent_times, time_generated=None):
        self.sender = sender
        self.receiver = receiver
        self.reason = reason
        self.business_short_code = business_short_code
        self.sent_times = sent_times
        self.time_generated = time_generated or datetime.utcnow()

    def __repr__(self):
        return (
            f"<EmailOutbox id={self.id} "
            f"sender={self.sender} "
            f"receiver={self.receiver} "
            f"sent_times={self.sent_times}>"
        )

