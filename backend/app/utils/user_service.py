from app.model.user import User
from app import db

class UserService:
    def __init__(self):
        pass
    def get_user_by_id(user_id):
        user = db.session.get(User,user_id)
        return user