from app import db
from datetime import date, datetime

class UserAgent(db.Model):
    __tablename__ = 'useragents'

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80), nullable=False)        
    lastname = db.Column(db.String(80), nullable=False)          
    idnumber = db.Column(db.String(80), unique=True, nullable=False)  
    phone_number = db.Column(db.String(20), unique=True, nullable=True) 
    is_authentic = db.Column(db.Boolean, default=False, nullable=False)  
    authenticity_desc = db.Column(db.String(255), nullable=True)       
    image_loc = db.Column(db.String(255), unique=True, nullable=True)   
    date_of_birth = db.Column(db.Date, nullable=True)

    def __init__(self, firstname, lastname, idnumber, phone_number=None,
                 is_authentic=False, authenticity_desc=None, image_loc=None, date_of_birth=None):
        self.firstname = firstname
        self.lastname = lastname
        self.idnumber = idnumber
        self.phone_number = phone_number
        self.is_authentic = is_authentic
        self.authenticity_desc = authenticity_desc
        self.image_loc = image_loc
        self.date_of_birth = date_of_birth

    def __repr__(self):
        return f'<UserAgent {self.firstname} {self.lastname}>'
