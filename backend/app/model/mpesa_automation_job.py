from app import db
from datetime import datetime
import uuid


class MpesaAutomationJob(db.Model):
    __tablename__ = 'mpesa_automation_jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    short_code = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending/running/completed/failed
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<MpesaAutomationJob id={self.id} status={self.status} short_code={self.short_code}>"
