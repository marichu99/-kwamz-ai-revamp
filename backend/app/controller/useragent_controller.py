import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from app.service.user_agent_service import UserAgentService

logger = logging.getLogger(__name__)

user_agent_bp = Bluelogger.info('user_agent', __name__, url_prefix='/useragent')

@user_agent_bp.route('', methods=['POST', 'OPTIONS'])
@user_agent_bp.route('/', methods=['POST', 'OPTIONS'])
@jwt_required()
def create_user_agent():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    current_user_id = get_jwt_identity()
    service = UserAgentService()
    user, error = service.create_user_agent(request.form, request.files, current_user_id)
    if error:
        return jsonify({'error': error}), 400 if 'Invalid' in error or 'Missing' in error else 500
    return jsonify({
        'message': 'User created successfully',
        'user': user
    }), 201

@user_agent_bp.route('/', methods=['GET', 'OPTIONS'])
@user_agent_bp.route('', methods=['GET', 'OPTIONS'])
@jwt_required()
@cross_origin()
def get_all_users():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    service = UserAgentService()
    current_user_id = get_jwt_identity()
    users, error = service.get_all_users_by_userid(user_id=current_user_id)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(users), 200

@user_agent_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    service = UserAgentService()
    user, error = service.get_user(user_id)
    if error:
        return jsonify({'error': error}), 404 if 'not found' in error.lower() else 500
    return jsonify(user), 200

@user_agent_bp.route('/<int:user_id>/scrape-status', methods=['GET'])
@jwt_required()
def get_scrape_status(user_id):
    service = UserAgentService()
    result, error = service.get_scrape_status(user_id)
    if error:
        return jsonify({'error': error}), 404 if 'not found' in error.lower() else 500
    return jsonify(result), 200

@user_agent_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    service = UserAgentService()
    user, error = service.update_user(user_id, request.form, request.files)
    if error:
        return jsonify({'error': error}), 400 if 'Invalid' in error or 'empty' in error else 500
    return jsonify({
        'message': 'User updated successfully',
        'user': user
    }), 200

@user_agent_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    service = UserAgentService()
    success, error = service.delete_user(user_id)
    if error:
        return jsonify({'error': error}), 500
    return jsonify({'message': f'User deleted successfully'}), 200

@user_agent_bp.route('/validate-batch', methods=['POST', 'OPTIONS'])
@jwt_required()
def validate_batch():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    service = UserAgentService()
    valid_users, invalid_users, error = service.validate_batch(file)
    if error:
        return jsonify({'error': error}), 400 if 'Invalid' in error or 'No file' in error else 500
    return jsonify({
        'validUsers': valid_users,
        'invalidUsers': invalid_users
    }), 200

@user_agent_bp.route('/batch', methods=['POST', 'OPTIONS'])
@jwt_required()
def batch_create_useragents():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    service = UserAgentService()
    created_users, successful_count, error = service.batch_create_useragents(file)
    if error:
        return jsonify({'error': error}), 400 if 'Invalid' in error or 'No file' in error else 500
    return jsonify({
        'message': f'{successful_count} users created successfully',
        'createdUsers': created_users,
        'errors': error if error else None
    }), 200