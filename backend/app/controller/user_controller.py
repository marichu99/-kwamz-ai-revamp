from flask import Blueprint, jsonify,current_app, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.model.user import User
from app.model.otp import Otp
from werkzeug.utils import secure_filename
from app import db,bcrypt
from datetime import datetime,timedelta
from app.model.company import Company
from app.utils.email_utils import send_otp_email,send_welcome_email,send_agent_new_clients_email
from sqlalchemy import or_
import random
import os
import re


user_bp = Blueprint('users', __name__, url_prefix='/users')

@user_bp.route('', methods=['OPTIONS'])
@user_bp.route('/', methods=['OPTIONS'])
def handle_options():
    return jsonify({'message': 'OK'}), 200


# Get all users (protected)
@user_bp.route('/', methods=['GET','OPTIONS'])
@jwt_required()
def get_users():
    current_user_id = get_jwt_identity()
    print(f"Current user ID: {current_user_id}")
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'role': user.role or "user",
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
        role=form_data['user_role'] or 'user',  
        phone_number=phone_number,  
        date_of_birth=date_of_birth  
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
        'image_loc': user.image_loc,
        'message': 'User created successfully'
    }), 201
    

@user_bp.route('/agents/assign-companies/<int:agent_id>', methods=['POST'])
@jwt_required()
def assign_agent_companies(agent_id):
    # try:
        data = request.get_json()
        company_ids = data.get('company_ids', [])
        
        agent = User.query.get_or_404(agent_id)
        if agent.role != 'agent':
            return jsonify({'error': 'User is not an agent'}), 400

        # # Get companies that are BEING ASSIGNED now (newly assigned)
        # previously_assigned = {
        #     c.id for c in Company.query.filter(Company.agent_user_id == agent_id).all()
        # }
        # newly_assigned_ids = [cid for cid in company_ids if cid not in previously_assigned]

        # Perform assignment updates (your existing logic)
        Company.query.filter(Company.id.in_(company_ids)).update(
            {Company.agent_user_id: agent_id,
             Company.agent_assigned_at: datetime.utcnow()},
            synchronize_session=False
        )
        
        # Company.query.filter(
        #     Company.agent_user_id == agent_id,
        #     ~Company.id.in_(company_ids)
        # ).update(
        #     {Company.agent_user_id: None},
        #     synchronize_session=False
        # )
        
        db.session.commit()

        # === SEND EMAIL ONLY IF THERE ARE NEWLY ASSIGNED COMPANIES ===
        # if newly_assigned_ids:
        #     newly_assigned_companies = Company.query.filter(Company.id.in_(newly_assigned_ids)).all()
        newly_assigned_companies = Company.query.filter(Company.id.in_(company_ids)).all()
            
        # Reuse your existing get_companies logic or format here
        companies_data = [{
            'company_name': c.company_name,
            'company_number': c.registration_number,
            'registration_date': c.registration_date.strftime('%d %B %Y') if c.registration_date else 'N/A',
            'primary_owner_name': c.primary_owner_name,
            'primary_owner_email': c.primary_owner_email,
        } for c in newly_assigned_companies]

        send_agent_new_clients_email(
            agent_email=agent.email,
            agent_name=agent.username or agent.email.split('@')[0],
            newly_assigned_companies=companies_data
        )

        return jsonify({
            'message': f'Successfully assigned {len(company_ids)} companies to agent',
            'agent_id': agent_id,
            'assigned_companies': company_ids
            # 'newly_assigned': len(newly_assigned_ids)
        })

    # except Exception as e:
    #     db.session.rollback()
    #     return jsonify({'error': str(e)}), 500
    
# Create a new user
@user_bp.route('/admin', methods=['POST'])
def create_admin():
    form_data = request.get_json()
    print(f"the data is {form_data}")
    
    if not form_data:
        return jsonify({'error': 'Missing formData'}), 400
        
    required_fields = ['username', 'password']
    if not all(field in form_data for field in required_fields):
        return jsonify({'error': 'Username and password are required'}), 400

    # Check for existing username or email
    if User.query.filter_by(username=form_data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    existing_otp = Otp.query.filter_by(otp=form_data['otp']).first()
    if existing_otp == None:
        return jsonify({'error': 'Invalid OTP'}), 400

    user = User(
        username=form_data['username'],
        email="marichufx@gmail.com",
        password=form_data['password'],
        role='admin'  # Set role to admin
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
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
        'access_token': access_token,
        'image_loc': user.image_loc,
        'message': 'User created successfully'
    }), 201

@user_bp.route('/<int:id>', methods=['PUT', 'OPTIONS'])     
@jwt_required()
def update_user(id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(id)

    if user.id != int(current_user_id):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.form.to_dict()  
        file = request.files.get('profileImage')  

        # Define allowed fields for update
        allowed_fields = ['username', 'email', 'phone_number', 'date_of_birth']
        
        # Only update fields that are present AND not empty
        for field in allowed_fields:
            if field in data and data[field].strip():  # Check if field exists and is not empty
                if field == 'date_of_birth':
                    try:
                        user.date_of_birth = datetime.fromisoformat(data['date_of_birth']).date()
                    except ValueError:
                        return jsonify({'error': 'Invalid date_of_birth format. Use YYYY-MM-DD'}), 400
                else:
                    setattr(user, field, data[field].strip())

        # Handle password update separately (requires both current and new password)
        if 'currentPassword' in data and 'newPassword' in data:
            if data['currentPassword'] and data['newPassword']:  # Both must be provided
                if not user.check_password(data['currentPassword']):
                    return jsonify({'error': 'Current password is incorrect'}), 400
                user.set_password(data['newPassword'])

        # Handle profile image upload (only if file is provided)
        if file and file.filename:  
           
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return jsonify({'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF allowed'}), 400
            
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            if file_length > 5 * 1024 * 1024:
                return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400

            profiles_dir = os.path.join(current_app.root_path, 'profiles')
            os.makedirs(profiles_dir, exist_ok=True)

            ext = os.path.splitext(secure_filename(file.filename))[1]
            filename = f"{user.id}{ext}"
            file_path = os.path.join(profiles_dir, filename)

            file.save(file_path)
            relative_path = os.path.join('profiles', filename)
            user.image_loc = relative_path

        db.session.commit()

        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'image_loc': user.image_loc
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
    
    if not data or not data.get('otp'):
        return jsonify({'error': 'OTP not supplied'}), 400
    
    user = User.query.filter(or_(User.username == data['username'], User.email == data['username'])).first()
    
    existing_otp = Otp.query.filter_by(otp=data.get('otp')).first()
    if existing_otp == None or existing_otp.email != user.email:
        return jsonify({'error': 'Invalid OTP'}), 400

    # user = User.query.filter(or_(User.email == data['username'])).first()
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'access_token': access_token,
            'image_loc': user.image_loc,
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

@user_bp.route('/role/<username>', methods=['GET'])
@jwt_required()
def get_user_role(username):
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'username': user.username,
            'role': user.role or "user"  
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/request-otp', methods=['POST'])
def request_otp():
    data = request.get_json()
    input_value = data.get('email')  # This can be either an email OR username

    if not input_value:
        return jsonify({'message': 'Email or username is required'}), 400

    # Regex to validate if the input is an email
    email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if re.match(email_regex, input_value):
        # Input is already a valid email
        email = input_value
    else:
        # Input is a username, look up the corresponding email
        user = User.query.filter(or_(User.username == input_value, User.email == input_value)).first()
        if not user or not user.email:
            return jsonify({'message': 'User not found or has no email on record'}), 404
        email = user.email

    # Generate a random 6-digit OTP
    otp = str(random.randint(100000, 999999))
    expiration_time = datetime.utcnow() + timedelta(minutes=5)

    # Save or update OTP in the database
    existing_otp = Otp.query.filter_by(email=email).first()
    if existing_otp:
        existing_otp.otp = otp
        existing_otp.time_generated = datetime.utcnow()
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
