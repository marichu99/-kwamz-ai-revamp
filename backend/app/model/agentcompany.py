from app import db
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import event
from typing import Optional, Dict, Any

class AgentCompany(db.Model):
    __tablename__ = 'agentcompanies'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    agentcompany_code = db.Column(db.String(120), nullable=True)
    established_date = db.Column(db.Date, nullable=True)
    float_balance = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'), nullable=True)
    fraud_risk_level = db.Column(db.String(20), default='low', nullable=True)  
    fraud_risk_description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=True)  
    agent_number = db.Column(db.String(20), unique=True, nullable=True)  
    store_number = db.Column(db.String(20), unique=True, nullable=True)  
    till_number = db.Column(db.String(20), unique=True, nullable=True)  
    location_details = db.Column(db.Text, nullable=True)  
    daily_transaction_limit = db.Column(db.Numeric(precision=15, scale=2), default=Decimal('0.00'), nullable=True)
    commission_rate = db.Column(db.Numeric(precision=5, scale=2), default=Decimal('0.00'), nullable=True)
    last_audit_date = db.Column(db.Date, nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    accounts = db.relationship(
        'AgentAccount',
        back_populates='agent_company',
        cascade='all, delete-orphan'
    )
    
    # New fields from scraped data
    identity_model = db.Column(db.String(100), nullable=True)
    hierarchy_level = db.Column(db.String(50), nullable=True)
    top_organization = db.Column(db.String(200), nullable=True)
    organization_name = db.Column(db.String(200), nullable=True)  # Alias for company_name
    short_code = db.Column(db.String(50), unique=True, nullable=True)  # Business short code
    identity_status = db.Column(db.String(50), nullable=True)
    segment = db.Column(db.String(100), nullable=True)
    charge_profile = db.Column(db.String(200), nullable=True)  # Increased from 100 to 200
    rule_profile = db.Column(db.String(200), nullable=True)  # Increased from 100 to 200
    trust_level = db.Column(db.String(100), nullable=True)  # Increased from 50 to 100
    data_source = db.Column(db.String(50), default='portal', nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    registration_date = db.Column(db.Date, nullable=True)
    parent_short_code = db.Column(db.String(50), nullable=True)  # Parent organization's short code
    portal_status = db.Column(db.String(50), nullable=True)  # Status from portal
    business_short_code = db.Column(db.String(50), nullable=True)  # Original business short code used for scraping
    commission_account_status = db.Column(db.String(50), nullable=True)  # e.g. pending, active, rejected

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scraped_at = db.Column(db.DateTime, nullable=True)  # When data was last scraped
    verification_date = db.Column(db.DateTime, nullable=True)  # When verified

    # Additional fields from your scraped data output
    scraped_at = db.Column(db.DateTime, nullable=True)  # When this record was scraped
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active_on_portal = db.Column(db.Boolean, default=True, nullable=True)  # Derived from identity_status
    
    # New indexes for better query performance
    __table_args__ = (
        db.Index('idx_short_code', 'short_code'),
        db.Index('idx_parent_short_code', 'parent_short_code'),
        db.Index('idx_business_short_code', 'business_short_code'),
        db.Index('idx_registration_number', 'registration_number'),
        db.Index('idx_user_id', 'user_id'),
        db.Index('idx_identity_status', 'identity_status'),
        db.Index('idx_hierarchy_level', 'hierarchy_level'),
        db.Index('idx_top_organization', 'top_organization'),
        db.Index('idx_identity_model', 'identity_model'),
        db.Index('idx_scraped_at', 'scraped_at'),
    )

    def __init__(
    self,
    company_name,
    registration_number,
    location,
    contact_phone=None,
    email=None,
    agentcompany_code=None,
    established_date=None,
    float_balance=Decimal('0.00'),
    fraud_risk_level='low',
    fraud_risk_description=None,
    status='active',
    till_number=None,
    location_details=None,
    store_number=None,
    agent_number=None,
    daily_transaction_limit=Decimal('0.00'),
    commission_rate=Decimal('0.00'),
    last_audit_date=None,
    company_id=None,
    user_id=None,

    # Identity / hierarchy
    identity_model=None,
    hierarchy_level=None,
    top_organization=None,
    organization_name=None,
    short_code=None,
    identity_status=None,
    segment=None,
    charge_profile=None,
    rule_profile=None,
    trust_level=None,
    data_source='portal',
    is_verified=False,
    registration_date=None,
    parent_short_code=None,
    portal_status=None,
    business_short_code=None,
    commission_account_status=None,

    # Timestamps
    created_at=None,
    verification_date=None,
    last_scraped_at=None,
    scraped_at=None,
    is_active_on_portal=None,
    last_updated=None,
    **kwargs
):
        # Core info
        self.company_name = company_name
        self.organization_name = organization_name or company_name
        self.registration_number = registration_number
        self.location = location
        self.contact_phone = contact_phone
        self.email = email
        self.agentcompany_code = agentcompany_code
        self.established_date = established_date
        self.status = status

        # Financial / risk
        self.float_balance = float_balance
        self.daily_transaction_limit = daily_transaction_limit
        self.commission_rate = commission_rate
        self.fraud_risk_level = fraud_risk_level
        self.fraud_risk_description = fraud_risk_description
        self.last_audit_date = last_audit_date

        # Identifiers
        self.agent_number = agent_number
        self.store_number = store_number
        self.till_number = till_number
        self.short_code = short_code
        self.business_short_code = business_short_code
        self.parent_short_code = parent_short_code
        self.commission_account_status = commission_account_status

        # Relationships
        self.company_id = company_id
        self.user_id = user_id

        # Identity / hierarchy
        self.identity_model = identity_model
        self.hierarchy_level = hierarchy_level
        self.top_organization = top_organization
        self.identity_status = identity_status
        self.portal_status = portal_status or identity_status
        self.segment = segment
        self.charge_profile = charge_profile
        self.rule_profile = rule_profile
        self.trust_level = trust_level
        self.data_source = data_source
        self.is_verified = is_verified
        self.registration_date = registration_date

        # Portal / scraping
        self.last_scraped_at = last_scraped_at
        self.scraped_at = scraped_at

        if is_active_on_portal is None and identity_status:
            self.is_active_on_portal = identity_status.lower() == 'active'
        else:
            self.is_active_on_portal = True if is_active_on_portal is None else is_active_on_portal

        # Timestamps
        self.created_at = created_at or datetime.utcnow()
        self.verification_date = verification_date
        self.last_updated = last_updated or datetime.utcnow()

    def __repr__(self):
        return f'<AgentCompany {self.company_name} ({self.short_code})>'
    
    @property
    def is_active(self):
        """Check if the agent is active based on portal status"""
        if self.identity_status:
            return self.identity_status.lower() == 'active'
        return self.status.lower() == 'active'
    
    @property
    def full_hierarchy_info(self):
        """Get full hierarchy information as string"""
        parts = []
        if self.identity_model:
            parts.append(f"Model: {self.identity_model}")
        if self.hierarchy_level:
            parts.append(f"Level: {self.hierarchy_level}")
        if self.trust_level:
            parts.append(f"Trust: {self.trust_level}")
        return " | ".join(parts) if parts else "No hierarchy info"
    def to_dict(self) -> Dict[str, Any]:
        return {
            # Core
            'id': self.id,
            'company_name': self.company_name,
            'organization_name': self.organization_name,
            'short_code': self.short_code,
            'business_short_code': self.business_short_code,
            'registration_number': self.registration_number,
            'location': self.location,
            'location_details': self.location_details,
            'contact_phone': self.contact_phone,
            'email': self.email,
            'status': self.status,

            # Identifiers
            'agent_number': self.agent_number,
            'store_number': self.store_number,
            'till_number': self.till_number,
            'agentcompany_code': self.agentcompany_code,

            # Financial / risk
            'float_balance': str(self.float_balance) if self.float_balance is not None else None,
            'daily_transaction_limit': str(self.daily_transaction_limit) if self.daily_transaction_limit is not None else None,
            'commission_rate': str(self.commission_rate) if self.commission_rate is not None else None,
            'fraud_risk_level': self.fraud_risk_level,
            'fraud_risk_description': self.fraud_risk_description,
            'last_audit_date': self.last_audit_date.isoformat() if self.last_audit_date else None,

            # Identity / hierarchy
            'identity_model': self.identity_model,
            'hierarchy_level': self.hierarchy_level,
            'top_organization': self.top_organization,
            'identity_status': self.identity_status,
            'portal_status': self.portal_status,
            'segment': self.segment,
            'charge_profile': self.charge_profile,
            'rule_profile': self.rule_profile,
            'trust_level': self.trust_level,
            'parent_short_code': self.parent_short_code,
            'commission_account_status': self.commission_account_status,
            'is_verified': self.is_verified,
            'data_source': self.data_source,

            # Flags / derived
            'is_active': self.is_active,
            'is_active_on_portal': self.is_active_on_portal,
            'full_hierarchy_info': self.full_hierarchy_info,

            # Dates
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'last_scraped_at': self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }
