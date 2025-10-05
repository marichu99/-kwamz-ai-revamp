from flask import Blueprint, request, jsonify
from app import db
from app.service.company_service import CompanyService
import json

company_bp = Blueprint('company', __name__, url_prefix='/company')

company_service = CompanyService(db)

@company_bp.route('/', methods=['GET', 'OPTIONS'])
@company_bp.route('', methods=['GET','OPTIONS'])
def get_companies():
    companies, error = company_service.get_companies()
    if error:
        return jsonify({'error': error}), 500
    return jsonify(companies), 200

@company_bp.route('/', methods=['POST', 'OPTIONS'])
@company_bp.route('/<int:company_id>', methods=['PUT'])
def create_or_update_company(company_id=None):
    try:
        data = request.form.to_dict()
        file = request.files.get('cr12_file')
        
        if file:
            data['cr12_file'] = file
        
        print(f"Raw form data: {data}")  # Debug log
        
        # Parse JSON strings for arrays
        if 'secondary_shareholders' in data:
            try:
                data['secondary_shareholders'] = json.loads(data['secondary_shareholders'])
                print(f"Parsed secondary_shareholders: {data['secondary_shareholders']}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse secondary_shareholders JSON: {e}")
                data['secondary_shareholders'] = []
        
        if 'directors' in data:
            try:
                data['directors'] = json.loads(data['directors'])
                print(f"Parsed directors: {data['directors']}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse directors JSON: {e}")
                data['directors'] = []
        
        # Convert numeric fields
        if 'primary_owner_shares' in data:
            try:
                data['primary_owner_shares'] = float(data['primary_owner_shares'])
            except (ValueError, TypeError):
                data['primary_owner_shares'] = 0.0
        
        print(f"Processed data for service: {data}")  # Debug log
        
        if company_id:
            # Update existing company
            company_id, message = company_service.update_company(company_id, data)
        else:
            # Create new company
            company_id, message = company_service.onboard_company(data)
            
        if company_id is None:
            return jsonify({'error': message}), 400
            
        return jsonify({'id': company_id, 'message': message, 'company': {'id': company_id}}), 201 if not company_id else 200
        
    except Exception as e:
        print(f"Error in create_or_update_company route: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to {"update" if company_id else "create"} company: {str(e)}'}), 500

@company_bp.route('/company/<int:id>', methods=['PUT'])
def update_company(id):
    data = request.form.to_dict()
    file = request.files.get('file')
    result, error = company_service.update_company(id, data, file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Company updated successfully', 'company': result}), 200

@company_bp.route('/company/<int:id>', methods=['DELETE'])
def delete_company(id):
    success, error = company_service.delete_company(id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Company deleted successfully'}), 200

@company_bp.route('/company/validate-batch', methods=['POST'])
def validate_batch_company():
    file = request.files.get('file')
    result, error = company_service.validate_batch_company(file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(result), 200

@company_bp.route('/company/batch', methods=['POST'])
def batch_create_company():
    file = request.files.get('file')
    result, error = company_service.batch_create_company(file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(result), 201