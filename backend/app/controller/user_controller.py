from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.model.user import User
from app.model.otp import Otp
from app import db,bcrypt
from datetime import datetime,timedelta
from app.utils.email_utils import send_otp_email,send_welcome_email
import random


user_bp = Blueprint('user', __name__)

# Get all users (protected)
@user_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    current_user_id = get_jwt_identity()
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None
    } for user in users])

# Get a single user by ID (protected)
@user_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_user(id):
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None
    })
# Create a new user
@user_bp.route('/', methods=['POST'])
def create_user():
    form_data = request.get_json()
    print(f"the data is {form_data}")
    
    if not form_data:
        return jsonify({'error': 'Missing formData'}), 400
        
    required_fields = ['username', 'email', 'password']
    if not all(field in form_data for field in required_fields):
        return jsonify({'error': 'Username, email, and password are required'}), 400

    # Check for existing username or email
    if User.query.filter_by(username=form_data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
        
    if User.query.filter_by(email=form_data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    existing_otp = Otp.query.filter_by(otp=form_data['otp']).first()
    if existing_otp == None:
        return jsonify({'error': 'Invalid OTP'}), 400

    # Handle phone number - check both possible field names
    phone_number = form_data.get('phoneNumber') or form_data.get('phone_number')
    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return jsonify({'error': 'Phone number already exists'}), 400

    # Parse date_of_birth if provided (handle both field names)
    date_of_birth = None
    dob_value = form_data.get('dateOfBirth') or form_data.get('date_of_birth')
    if dob_value:
        try:
            date_of_birth = datetime.fromisoformat(dob_value).date()
        except ValueError:
            return jsonify({'error': 'Invalid dateOfBirth format. Use YYYY-MM-DD'}), 400

    user = User(
        username=form_data['username'],
        email=form_data['email'],
        password=form_data['password'],
        phone_number=phone_number,  # Use the extracted phone number
        date_of_birth=date_of_birth  # Use the parsed date
    )
    
    db.session.add(user)
    db.session.commit()

    try:
        send_welcome_email(user.email, user.username)
    except Exception as e:
        print(f"Welcome email failed to send: {e}")

    # Generate JWT token for auto-login
    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
        'access_token': access_token,
        'message': 'User created successfully'
    }), 201

# Update a user (protected)
@user_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_user(id):
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(id)
    if user.id != current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    user.phone_number = data.get('phone_number', user.phone_number)
    if data.get('date_of_birth'):
        try:
            user.date_of_birth = datetime.fromisoformat(data['date_of_birth']).date()
        except ValueError:
            return jsonify({'error': 'Invalid date_of_birth format. Use YYYY-MM-DD'}), 400
    if data.get('password'):
        user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    db.session.commit()
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None
    })

# Delete a user (protected)
@user_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_user(id):
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(id)
    if user.id != current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 204

# Login route
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'access_token': access_token,
            'message': 'Login successful'
        }), 200
    return jsonify({'error': 'Invalid username or password'}), 401
    
@user_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'username': user.username,
        'id': user.id,
        'email': user.email,
        'phone_number': user.phone_number,
        'date_of_birth': str(user.date_of_birth) if user.date_of_birth else None
    }), 200

@user_bp.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    # Generate a random 6-digit OTP
    otp = str(random.randint(100000, 999999))
    expiration_time = datetime.utcnow() + timedelta(minutes=5)

    # Save or update OTP in the database
    existing_otp = Otp.query.filter_by(email=email).first()
    if existing_otp:
        return jsonify({'message': 'Email is already exists'}), 400
    else:
        new_otp = Otp(email=email, otp=otp, time_generated=datetime.utcnow())
        db.session.add(new_otp)

    db.session.commit()

    # Send OTP via email
    email_sent = send_otp_email(email, otp)

    if not email_sent:
        return jsonify({'message': 'Failed to send OTP email'}), 500

    return jsonify({'message': 'OTP sent successfully!'}), 200

@user_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    # Generate a random 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Look for an existing OTP entry
    existing_otp = Otp.query.filter_by(email=email).first()

    if existing_otp:
        existing_otp.otp = otp
        existing_otp.time_generated = datetime.utcnow()
    else:
        new_otp = Otp(email=email, otp=otp, time_generated=datetime.utcnow())
        db.session.add(new_otp)

    db.session.commit()

    email_sent = send_otp_email(email, otp)

    if not email_sent:
        return jsonify({'message': 'Failed to send OTP email'}), 500

    return jsonify({'message': 'OTP sent successfully!'}), 200
