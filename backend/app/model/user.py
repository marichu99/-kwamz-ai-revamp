from app import db, bcrypt
from datetime import date,datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  
    phone_number = db.Column(db.String(20), unique=True, nullable=True)  # Optional phone number
    date_of_birth = db.Column(db.Date, nullable=True)  # Optional date of birth

    def __init__(self, username, email, password, phone_number=None, date_of_birth=None):
        self.username = username
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.phone_number = phone_number
        self.date_of_birth = date_of_birth

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.username}>'