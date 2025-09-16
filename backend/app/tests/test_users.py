import unittest
from app import create_app, db
from app.model.user import User
from flask_jwt_extended import decode_token

class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create a test user
            user = User(username='testuser', email='test@example.com', password='testpassword')
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()

    def test_login_success(self):
        response = self.client.post('/users/login', json={
            'username': 'testuser',
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['message'], 'Login successful')
        self.assertEqual(response.json['username'], 'testuser')
        self.assertIn('access_token', response.json)
        # Verify token
        token = response.json['access_token']
        decoded = decode_token(token)
        self.assertEqual(decoded['sub'], 1)  # User ID

    def test_login_invalid_credentials(self):
        response = self.client.post('/users/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json['error'], 'Invalid username or password')

    def test_login_missing_fields(self):
        response = self.client.post('/users/login', json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], 'Username and password are required')

    def test_protected_route(self):
        # Get token
        login_response = self.client.post('/users/login', json={
            'username': 'testuser',
            'password': 'testpassword'
        })
        token = login_response.json['access_token']
        # Access protected route
        response = self.client.get('/users/', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['username'], 'testuser')

    def test_protected_route_no_token(self):
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Missing Authorization Header', response.json['msg'])

if __name__ == '__main__':
    unittest.main()