from app import db
from datetime import date, datetime
from decimal import Decimal

user_agent_companies = db.Table('user_agent_companies',
    db.Column('user_agent_id', db.Integer, db.ForeignKey('useragents.id', ondelete='CASCADE'), primary_key=True),
    db.Column('agent_company_id', db.Integer, db.ForeignKey('agentcompanies.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class UserAgent(db.Model):
    __tablename__ = 'useragents'

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80), nullable=False)        
    lastname = db.Column(db.String(80), nullable=False)          
    idnumber = db.Column(db.String(80), unique=True, nullable=False)  
    phone_number = db.Column(db.String(20), unique=True, nullable=True) 
    is_authentic = db.Column(db.Boolean, default=False, nullable=False)  
    authenticity_desc = db.Column(db.String(255), nullable=True)       
    image_loc = db.Column(db.Text, nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    agent_company_id = db.Column(db.Integer, db.ForeignKey('agentcompanies.id'), nullable=True)

    agent_company = db.relationship('AgentCompany', foreign_keys=[agent_company_id])
    agent_companies = db.relationship('AgentCompany',
                                    secondary=user_agent_companies,
                                    backref=db.backref('user_agents', lazy='dynamic'),
                                    lazy='select')

    def __init__(self, firstname, lastname, idnumber, phone_number=None,
                 is_authentic=False, authenticity_desc=None, image_loc=None, date_of_birth=None, user_id=None, agent_company_id=None):
        self.firstname = firstname
        self.lastname = lastname
        self.idnumber = idnumber
        self.phone_number = phone_number
        self.is_authentic = is_authentic
        self.authenticity_desc = authenticity_desc
        self.image_loc = image_loc
        self.date_of_birth = date_of_birth
        self.user_id = user_id
        self.agent_company_id = agent_company_id

    def __repr__(self):
        return f'<UserAgent {self.firstname} {self.lastname}>'

    # Helper method to get agent company IDs as list
    def get_agent_company_ids(self):
        return [company.id for company in self.agent_companies]

    # Helper method to get agent company names
    def get_agent_company_names(self):
        return [company.company_name for company in self.agent_companies]