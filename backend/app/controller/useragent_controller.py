from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from openpyxl import load_workbook
from io import BytesIO
from sqlalchemy.exc import IntegrityError
from app import db
from app.model.useragent import UserAgent
from datetime import datetime
import os
import re

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

ALLOWED_EXTENSIONS_XSL = {'xlsx','xls'}

def allowed_file_xls(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_XSL

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

@user_agent_bp.route('/batch', methods=['POST', 'OPTIONS'])
@jwt_required()
def batch_create_useragents():
    try:
        print("Batch upload endpoint hit")
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file_xls(file.filename):
            return jsonify({'error': 'Invalid file type. Only .xlsx files are allowed'}), 400

        # Read Excel file
        file_stream = BytesIO(file.read())
        workbook = load_workbook(file_stream)
        sheet = workbook.active

        # Extract headers and data
        headers = [cell.value.strip() for cell in next(sheet.iter_rows(min_row=1, max_row=1)) if cell.value]
        data_rows = [
            [cell.value for cell in row]
            for row in sheet.iter_rows(min_row=2)
            if any(cell.value for cell in row)  # Skip empty rows
        ]

        created_users = []
        errors = []

        for row in data_rows:
            if len(row) < 4:
                errors.append(f"Invalid row (too few columns): {row}")
                continue

            user_data = {
                'firstname': str(row[0] or ''),
                'lastname': str(row[1] or ''),
                'idnumber': str(row[2] or ''),
                'phone_number': str(row[3] or '') if row[3] else None,
                'is_authentic': False
            }

            # Validate required fields
            if not user_data['firstname'] or not user_data['lastname'] or not user_data['idnumber']:
                errors.append(f"Missing required fields in row: {user_data}")
                continue

            # Check for duplicate idnumber
            if UserAgent.query.filter_by(idnumber=user_data['idnumber']).first():
                errors.append(f"Duplicate ID number: {user_data['idnumber']}")
                continue

            try:
                new_user = UserAgent(**user_data)
                db.session.add(new_user)
                created_users.append(user_data)
            except Exception as e:
                errors.append(f"Error creating user {user_data['idnumber']}: {str(e)}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to save users: {str(e)}'}), 500

        return jsonify({
            'message': f'{len(created_users)} users created successfully',
            'createdUsers': created_users,
            'errors': errors if errors else None
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to process batch upload: {str(e)}'}), 500

def validate_users(data_rows):
    errors = []
    valid_users = []
    seen_idnumbers = set()
    seen_phones = set([u.phone_number for u in UserAgent.query.filter(UserAgent.phone_number.isnot(None)).all()])

    for row_index, row in enumerate(data_rows, start=2):
        if len(row) < 4:
            errors.append({
                'rowIndex': row_index,
                'firstname': row[0] if len(row) > 0 else None,
                'lastname': row[1] if len(row) > 1 else None,
                'idnumber': row[2] if len(row) > 2 else None,
                'phone_number': row[3] if len(row) > 3 else None,
                'reason': 'Incomplete row (requires firstname, lastname, idnumber, phone_number)'
            })
            continue

        user_data = {
            'firstname': str(row[0] or '').strip(),
            'lastname': str(row[1] or '').strip(),
            'idnumber': str(row[2] or '').strip(),
            'phone_number': str(row[3] or '').strip() if row[3] else None,
            'rowIndex': row_index
        }

        # Validate required fields
        if not user_data['firstname'] or not user_data['lastname'] or not user_data['idnumber']:
            errors.append({**user_data, 'reason': 'Missing required fields (firstname, lastname, idnumber)'})
            continue

        # Validate name format
        if not re.match(r'^[A-Za-z\s-]+$', user_data['firstname']) or not re.match(r'^[A-Za-z\s-]+$', user_data['lastname']):
            errors.append({**user_data, 'reason': 'Invalid name format (only letters, spaces, and hyphens allowed)'})
            continue

        # Validate phone number format (if provided)
        if user_data['phone_number']:
            print(f"Validating phone number: {user_data['phone_number']}")
            # Allow optional country code (+ followed by 1-3 digits) and 9-12 digits
            if not re.match(r'^\+?\d{1,3}?\d{9,12}$', user_data['phone_number']):
                errors.append({**user_data, 'reason': 'Invalid phone number format (must be 9-12 digits, optional + and 1-3 digit country code)'})
                continue

        # Check for duplicate idnumber within file
        if user_data['idnumber'] in seen_idnumbers:
            errors.append({**user_data, 'reason': 'Duplicate ID number within file'})
            continue
        seen_idnumbers.add(user_data['idnumber'])

        # Check for existing idnumber in database
        if UserAgent.query.filter_by(idnumber=user_data['idnumber']).first():
            errors.append({**user_data, 'reason': 'ID number already exists in database'})
            continue

        # Check for existing phone number in database (if provided)
        if user_data['phone_number'] and user_data['phone_number'] in seen_phones:
            errors.append({**user_data, 'reason': 'Phone number already exists in database'})
            continue
        seen_phones.add(user_data['phone_number'])

        valid_users.append(user_data)

    return valid_users, errors

@user_agent_bp.route('/validate-batch', methods=['POST', 'OPTIONS'])
@jwt_required()
def validate_batch():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        print("Validate batch endpoint hit")
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file_xls(file.filename):
            return jsonify({'error': 'Invalid file type. Only .xlsx and .xls files are allowed'}), 400

        # Read Excel file
        file_stream = BytesIO(file.read())
        workbook = load_workbook(file_stream)
        sheet = workbook.active

        # Extract headers and data
        headers = [cell.value.strip() for cell in next(sheet.iter_rows(min_row=1, max_row=1)) if cell.value]
        data_rows = [
            [cell.value for cell in row]
            for row in sheet.iter_rows(min_row=2)
            if any(cell.value for cell in row)
        ]

        valid_users, errors = validate_users(data_rows)

        return jsonify({
            'validUsers': valid_users,
            'invalidUsers': errors if errors else []
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to validate batch: {str(e)}'}), 500