import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.service.agentcompany_service import AgentCompanyService

logger = logging.getLogger(__name__)

agent_company_bp = Blueprint('agent_company', __name__, url_prefix='/agentcompany')

# Handle OPTIONS requests separately
@agent_company_bp.route('', methods=['OPTIONS'])
@agent_company_bp.route('/', methods=['OPTIONS'])
def handle_options():
    return jsonify({'message': 'OK'}), 200

# Main GET endpoint with JWT protection
@agent_company_bp.route('', methods=['GET'])
@agent_company_bp.route('/', methods=['GET'])
@jwt_required()
def get_agent_companies():
    current_user_id = get_jwt_identity()
    service = AgentCompanyService()
    agent_companies, error = service.get_all_agent_companies_by_userid(user_id=current_user_id)
    if error:
        return jsonify({'error': 'An error occurred'}), 500
    return jsonify(agent_companies), 200

@agent_company_bp.route('/', methods=['POST'])
@jwt_required()
def create_agent_company():
    current_user_id = get_jwt_identity()
    data = request.form
    service = AgentCompanyService()
    agent_company, error = service.create_agent_company(data, current_user_id)
    if error:
        return jsonify({'error': 'An error has occurred'}), 400
    return jsonify({
        'message': 'Agent company created successfully',
        'agentCompany': agent_company
    }), 201

@agent_company_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_agent_company(id):
    current_user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or request.form or {}
    service = AgentCompanyService()
    agent_company, error = service.update_agent_company(id, data, current_user_id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({
        'message': 'Agent company updated successfully',
        'agentCompany': agent_company
    }), 200

@agent_company_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_agent_company(id):
    current_user_id = int(get_jwt_identity())
    service = AgentCompanyService()
    success, error = service.delete_agent_company(id, current_user_id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Agent company deleted successfully'}), 200

@agent_company_bp.route('/validate-batch', methods=['POST'])
@jwt_required()
def validate_batch_agent_company():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    service = AgentCompanyService()
    valid_agent_companies, invalid_agent_companies, error = service.validate_batch_agent_company(file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({
        'validAgentCompanies': valid_agent_companies,
        'invalidAgentCompanies': invalid_agent_companies
    }), 200

@agent_company_bp.route('/batch', methods=['POST'])
@jwt_required()
def batch_create_agent_company():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    service = AgentCompanyService()
    created_agent_companies, failed_count, error = service.batch_create_agent_company(file)
    if error:
        if failed_count > 0:
            return jsonify({
                'error': 'Failed to create some agent companies',
                'details': error,
                'successful_count': 0,
                'failed_count': failed_count
            }), 400
        return jsonify({'error': f'Batch upload failed: {error}'}), 400
    return jsonify({
        'message': f'{len(created_agent_companies)} agent companies created successfully',
        'createdAgentCompanies': created_agent_companies,
        'successful_count': len(created_agent_companies),
        'failed_count': 0
    }), 201