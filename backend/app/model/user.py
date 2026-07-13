from app import db, bcrypt
from datetime import date, datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  
    role = db.Column(db.String(128), nullable=True)  
    phone_number = db.Column(db.String(20), unique=True, nullable=True)  
    image_loc = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_active = db.Column(db.DateTime, nullable=True)

    # One-to-Many relationship with UserBank (user can have multiple bank accounts)
    # bank_details = db.relationship('UserBank', backref='user', uselist=True, cascade='all, delete-orphan')

    def __init__(self, username, email, password, phone_number=None, image_loc=None, date_of_birth=None, role=None):
        self.username = username
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.phone_number = phone_number
        self.image_loc = image_loc
        self.role = role
        self.date_of_birth = date_of_birth if date_of_birth else None
        self.created_at = datetime.utcnow()

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)
    
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def __repr__(self):
        return f'<User {self.username}>'