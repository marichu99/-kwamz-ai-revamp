from app import db
from datetime import datetime
import uuid


class MpesaScrapeJob(db.Model):
    __tablename__ = 'mpesa_scrape_jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    short_code = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending/running/completed/failed
    # When true, skip the float/KYC pass and scrape swaps directly — for use once
    # till/sub-agent info is already up to date, so the run doesn't redo it.
    swaps_only = db.Column(db.Boolean, nullable=False, default=False)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<MpesaScrapeJob id={self.id} status={self.status} short_code={self.short_code}>"
