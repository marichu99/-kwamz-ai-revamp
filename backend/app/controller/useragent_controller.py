from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from sqlalchemy.exc import IntegrityError
from app import db
from app.model.useragent import UserAgent
from datetime import datetime
import os

user_agent_bp = Blueprint('user_agent', __name__, url_prefix='/useragent')

# Helper function to serialize a UserAgent
def serialize_user_agent(user):
    return {
        'id': user.id,
        'firstname': user.firstname,
        'lastname': user.lastname,
        'idnumber': user.idnumber,
        'phone_number': user.phone_number,
        'is_authentic': user.is_authentic,
        'authenticity_desc': user.authenticity_desc,
        'image_loc': user.image_loc,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None
    }

# Allowed file extensions for images
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to get the upload directory
def get_upload_dir():
    upload_dir = os.path.join(current_app.root_path, 'useragents', 'profiles')
    os.makedirs(upload_dir, exist_ok=True)  # Create directory if it doesn't exist
    return upload_dir

# ------------------------------
# CREATE: Add a new UserAgent with file upload
# ------------------------------
@user_agent_bp.route('/', methods=['POST', 'OPTIONS'])
@jwt_required()
def create_user_agent():

    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    current_user_id = get_jwt_identity()
    
    if not request.form:
        return jsonify({'error': 'Missing form data'}), 400

    required_fields = ['firstname', 'lastname', 'idnumber']
    missing_fields = [field for field in required_fields if not request.form.get(field)]
    if missing_fields:
        return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        # Parse date_of_birth if provided
        date_of_birth = None
        if request.form.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(request.form['date_of_birth'], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({'error': 'Invalid date_of_birth format. Use YYYY-MM-DD'}), 400

        # Handle file upload
        image_loc = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            if file and allowed_file(file.filename):
                if file.content_length > MAX_FILE_SIZE:
                    return jsonify({'error': 'File size exceeds 5MB limit'}), 400
                # Generate unique filename
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{current_user_id}.{ext}"
                upload_dir = get_upload_dir()
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                image_loc = os.path.abspath(file_path)
            else:
                return jsonify({'error': 'Invalid file type. Allowed types: jpg, jpeg, png, gif'}), 400

        new_user = UserAgent(
            firstname=request.form['firstname'],
            lastname=request.form['lastname'],
            idnumber=request.form['idnumber'],
            phone_number=request.form.get('phone_number'),
            is_authentic=request.form.get('is_authentic') == 'true', 
            authenticity_desc=request.form.get('authenticity_desc'),
            image_loc=image_loc,
            date_of_birth=date_of_birth
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'message': 'User created successfully',
            'user': serialize_user_agent(new_user)
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Duplicate entry detected. ID number, phone, or other unique fields must be unique.'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ------------------------------
# READ: Get all users
# ------------------------------
@user_agent_bp.route('/', methods=['GET', 'OPTIONS'])
@user_agent_bp.route('', methods=['GET', 'OPTIONS'])
@jwt_required()
@cross_origin()
def get_all_users():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    print("Fetching all users")
    users = UserAgent.query.all()
    return jsonify([serialize_user_agent(user) for user in users]), 200

# ------------------------------
# READ: Get a single user by ID
# ------------------------------
@user_agent_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = UserAgent.query.get_or_404(user_id)
    return jsonify(serialize_user_agent(user)), 200


@user_agent_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    user = UserAgent.query.get_or_404(user_id)

    if not request.form and 'image' not in request.files:
        return jsonify({'error': 'No data provided'}), 400

    try:
        # Validate and update fields
        if 'firstname' in request.form:
            firstname = request.form['firstname'].strip()
            if not firstname:
                return jsonify({'error': 'First name cannot be empty'}), 400
            user.firstname = firstname

        if 'lastname' in request.form:
            lastname = request.form['lastname'].strip()
            if not lastname:
                return jsonify({'error': 'Last name cannot be empty'}), 400
            user.lastname = lastname

        if 'idnumber' in request.form:
            idnumber = request.form['idnumber'].strip()
            if not idnumber:
                return jsonify({'error': 'ID number cannot be empty'}), 400
            user.idnumber = idnumber

        if 'phone_number' in request.form:
            user.phone_number = request.form['phone_number'] or None  # Allow empty string or None

        if 'is_authentic' in request.form:
            user.is_authentic = request.form['is_authentic'] == 'true'

        if 'authenticity_desc' in request.form:
            user.authenticity_desc = request.form['authenticity_desc'] or None  # Allow empty string or None

        if 'date_of_birth' in request.form:
            date_of_birth = request.form['date_of_birth']
            if date_of_birth:
                try:
                    user.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    return jsonify({'error': 'Invalid date_of_birth format. Use YYYY-MM-DD'}), 400
            else:
                user.date_of_birth = None

        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            if file and allowed_file(file.filename):
                if file.content_length > MAX_FILE_SIZE:
                    return jsonify({'error': 'File size exceeds 5MB limit'}), 400
                # Delete old image if it exists
                if user.image_loc and os.path.exists(user.image_loc):
                    os.remove(user.image_loc)
                # Save new image
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{user_id}.{ext}"
                upload_dir = get_upload_dir()
                os.makedirs(upload_dir, exist_ok=True)  # Ensure directory exists
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                # Store relative path for consistency with frontend
                user.image_loc = f"useragents/profiles/{filename}"
            else:
                return jsonify({'error': 'Invalid file type. Allowed types: jpg, jpeg, png, gif'}), 400

        db.session.commit()
        return jsonify({
            'message': 'User updated successfully',
            'user': serialize_user_agent(user)
        }), 200

    except IntegrityError as e:
        db.session.rollback()
        error_msg = str(e.orig).lower()
        if 'unique constraint' in error_msg or 'duplicate key' in error_msg:
            return jsonify({'error': 'Duplicate ID number or other unique field'}), 400
        return jsonify({'error': 'Database error occurred'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
# ------------------------------
# DELETE: Remove a user
# ------------------------------
@user_agent_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    user = UserAgent.query.get_or_404(user_id)

    try:
        # Delete image file if it exists
        if user.image_loc and os.path.exists(user.image_loc):
            os.remove(user.image_loc)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': f'User {user.firstname} {user.lastname} deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500