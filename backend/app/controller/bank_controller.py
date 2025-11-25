
from app import db
from flask import Blueprint, request, jsonify
from app.service.bank_service import BankService
from app.utils.response_utils import success_response, error_response

bank_bp = Blueprint('banks', __name__, url_prefix='/')

bank_service = BankService()

@bank_bp.route('', methods=['OPTIONS'])
@bank_bp.route('/', methods=['OPTIONS'])
def handle_options():
    return jsonify({'message': 'OK'}), 200


@bank_bp.route('/', methods=['GET'])
def get_banks():
    try:
        banks = bank_service.get_all_banks()
        return success_response(
            data=[bank.to_dict() for bank in banks],
            message="Banks retrieved successfully"
        )
    except Exception as e:
        return error_response(str(e), 500)

@bank_bp.route('/<bank_id>', methods=['GET'])
def get_bank(bank_id):
    try:
        bank = bank_service.get_bank_by_id(bank_id)
        if not bank:
            return error_response("Bank not found", 404)
        return success_response(
            data=bank.to_dict(),
            message="Bank retrieved successfully"
        )
    except Exception as e:
        return error_response(str(e), 500)

@bank_bp.route('/', methods=['POST'])
def create_bank():
    try:
        data = request.get_json()
        bank = bank_service.create_bank(data)
        return success_response(
            data=bank.to_dict(),
            message="Bank created successfully",
            status_code=201
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)

@bank_bp.route('/<bank_id>', methods=['PUT'])
def update_bank(bank_id):
    try:
        data = request.get_json()
        bank = bank_service.update_bank(bank_id, data)
        return success_response(
            data=bank.to_dict(),
            message="Bank updated successfully"
        )
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(str(e), 500)

@bank_bp.route('/<bank_id>', methods=['DELETE'])
def delete_bank(bank_id):
    try:
        bank_service.delete_bank(bank_id)
        return success_response(
            message="Bank deleted successfully"
        )
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)

@bank_bp.route('/test-connection/<int:bank_id>', methods=['POST'])
def test_connection(bank_id):
    try:
        result = bank_service.test_bank_connection(bank_id)
        return success_response(
            data=result,
            message=result['message']
        )
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(str(e), 500)

@bank_bp.route('/search', methods=['GET'])
def search_banks():
    try:
        search_term = request.args.get('q', '')
        if not search_term:
            return error_response("Search term is required", 400)
        
        banks = bank_service.search_banks(search_term)
        return success_response(
            data=[bank.to_dict() for bank in banks],
            message="Search completed successfully"
        )
    except Exception as e:
        return error_response(str(e), 500)