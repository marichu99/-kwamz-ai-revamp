from app import db
from datetime import datetime
import uuid


class VerificationJob(db.Model):
    __tablename__ = 'verification_jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kra_pin = db.Column(db.String(20), nullable=False)
    police_clearance = db.Column(db.String(50), nullable=False)
    id_number = db.Column(db.String(20), nullable=False)
    taxpayer_name = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending/running/completed/failed
    kra_result = db.Column(db.String(500), nullable=True)
    police_result = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<VerificationJob id={self.id} status={self.status} kra_pin={self.kra_pin}>"
