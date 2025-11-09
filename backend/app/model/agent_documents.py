# app/models/document.py
from app import db
from datetime import datetime

class AgentDocuments(db.Model):
    __tablename__ = 'agent_documents'

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('useragents.id'), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Document type (e.g., kra_pin, cr12, police_clearance)
    doc_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Original filename
    filename = db.Column(db.String(255), nullable=False)
    
    # Full GCP path (e.g., companies/101/agents/789/kra_pin/doc.pdf)
    gcp_path = db.Column(db.String(512), nullable=False, unique=True)
    
    # Public URL (if made public) or placeholder for signed URL logic
    gcp_url = db.Column(db.String(512))
    
    # Extracted data stored as JSON
    extracted_data = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent = db.relationship('UserAgent', backref=db.backref('agent_documents', lazy='dynamic'))
    company = db.relationship('Company', backref=db.backref('agent_documents', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return f"<Document {self.doc_type.upper()} - Agent {self.agent_id}>"

    def to_dict(self):
        """Serialize for API responses"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "doc_type": self.doc_type,
            "filename": self.filename,
            "gcp_url": self.gcp_url,
            "extracted_data": self.extracted_data,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }