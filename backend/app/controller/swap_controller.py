from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.service.swap_service import SwapService

swap_bp = Blueprint('swap', __name__, url_prefix='/swaps')


@swap_bp.route('', methods=['OPTIONS'])
@swap_bp.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path=None):
    return jsonify({'message': 'OK'}), 200


@swap_bp.route('', methods=['POST'])
@jwt_required()
def initiate_swap():
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    agent_company_id = data.get('agent_company_id')
    new_agent_ids = data.get('new_agent_ids', [])
    notes = data.get('notes', '')

    if not agent_company_id:
        return jsonify({'error': 'agent_company_id is required'}), 400
    if not new_agent_ids:
        return jsonify({'error': 'new_agent_ids is required'}), 400

    service = SwapService()
    result, error = service.initiate_swap(agent_company_id, new_agent_ids, notes, current_user_id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Swap initiated successfully', 'swap': result}), 201


@swap_bp.route('', methods=['GET'])
@jwt_required()
def get_swaps():
    current_user_id = get_jwt_identity()
    filters = {
        'agent_company_id': request.args.get('agent_company_id'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v}

    service = SwapService()
    result, error = service.get_all_swaps(current_user_id, filters)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result), 200


@swap_bp.route('/<int:swap_id>/revert', methods=['POST'])
@jwt_required()
def revert_swap(swap_id):
    current_user_id = get_jwt_identity()
    service = SwapService()
    result, error = service.revert_swap(swap_id, current_user_id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Swap reverted successfully', 'swap': result}), 201


@swap_bp.route('/by-company', methods=['GET'])
@jwt_required()
def get_swaps_by_company():
    current_user_id = get_jwt_identity()
    filters = {
        'agent_company_id': request.args.get('agent_company_id'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
    }
    filters = {k: v for k, v in filters.items() if v}

    service = SwapService()
    result, error = service.get_swaps_grouped_by_company(current_user_id, filters)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result), 200


@swap_bp.route('/report', methods=['GET'])
@jwt_required()
def get_swap_report():
    current_user_id = get_jwt_identity()
    filters = {
        'agent_company_id': request.args.get('agent_company_id'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
    }
    filters = {k: v for k, v in filters.items() if v}

    service = SwapService()
    result, error = service.generate_swap_report(current_user_id, filters)
    if error:
        return jsonify({'error': error}), 500
    return jsonify(result), 200


@swap_bp.route('/report/export', methods=['GET'])
@jwt_required()
def export_swap_report():
    current_user_id = get_jwt_identity()
    export_format = request.args.get('format', 'csv')
    filters = {
        'agent_company_id': request.args.get('agent_company_id'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
    }
    filters = {k: v for k, v in filters.items() if v}

    service = SwapService()
    result, error = service.export_swap_report(current_user_id, filters, format=export_format)
    if error:
        return jsonify({'error': error}), 500

    return Response(
        result,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=swap_report.csv'}
    )
