from flask import Blueprint, request, jsonify, current_app, send_file
from datetime import datetime
from app.service.transaction_service import TransactionService
from app.service.reports.commissions_report_service import CommissionReportService
from app.service.export_service import ExportService
import os



transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

transaction_service = TransactionService()

commission_report_service = CommissionReportService()
export_service = ExportService()

@transaction_bp.route('/commissions-report', methods=['GET'])
def get_commissions_report():
    """Get commission report data"""
    try:
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        date_range = request.args.get('date_range', 'custom')
        transaction_type = request.args.get('transaction_type', 'commission')
        reason_type = request.args.get('reason_type')
        transaction_status = request.args.get('transaction_status')
        
        # Generate report
        report = commission_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            transaction_type=transaction_type,
            reason_type=reason_type,
            transaction_status=transaction_status
        )
        
        return jsonify({'success': True, 'report': report})
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating commission report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/export-commissions', methods=['GET'])
def export_commissions_report():
    """Export commission report in various formats"""
    try:
        # Get parameters
        format_type = request.args.get('format', 'csv')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        date_range = request.args.get('date_range', 'custom')
        transaction_type = request.args.get('transaction_type', 'commission')
        reason_type = request.args.get('reason_type')
        transaction_status = request.args.get('transaction_status')
        
        # Export report
        export_data = export_service.export_commission_report(
            format_type=format_type,
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            transaction_type=transaction_type,
            reason_type=reason_type,
            transaction_status=transaction_status
        )
        
        return export_data
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error exporting commission report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@transaction_bp.route('/export', methods=['GET'])
def export_transactions():
    """Export transactions"""
    try:
        # Get parameters
        company_id = request.args.get('company_id', type=int)
        transaction_type = request.args.get('transaction_type', 'float')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        reason_type = request.args.get('reason_type')
        transaction_status = request.args.get('transaction_status')
        
        # Export transactions
        export_data = export_service.export_transactions(
            company_id=company_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            reason_type=reason_type,
            transaction_status=transaction_status
        )
        
        return export_data
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error exporting transactions: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# Handle OPTIONS requests separately
@transaction_bp.route('', methods=['OPTIONS'])
@transaction_bp.route('/', methods=['OPTIONS'])
def handle_options():
    return jsonify({'message': 'OK'}), 200

@transaction_bp.route('/', methods=['GET'])
def get_transactions():
    """
    Get transactions with filtering and pagination
    """
    try:
        print("we are here")
        # Get query parameters
        filters = {
            'agent_id': request.args.get('agent_id', type=int),
            'company_id': request.args.get('company_id', type=int),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'reasonType': request.args.get('reasonType'),
            'transaction_status': request.args.get('transaction_status'),
            'transaction_type': request.args.get('transaction_type', 'float'),
            'search': request.args.get('search', '')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = transaction_service.get_transactions(filters, page, per_page)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error fetching transactions: {str(e)}")
        return jsonify({"error": f"Failed to fetch transactions: {str(e)}"}), 500


@transaction_bp.route('/transaction/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """
    Get a specific transaction by ID
    """
    result = transaction_service.get_transaction(transaction_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404


@transaction_bp.route('/transaction', methods=['POST'])
def create_transaction():
    """
    Create a new transaction
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = transaction_service.create_transaction(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error creating transaction: {str(e)}")
        return jsonify({"error": f"Failed to create transaction: {str(e)}"}), 500


@transaction_bp.route('/transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """
    Update an existing transaction
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        result = transaction_service.update_transaction(transaction_id, data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error updating transaction: {str(e)}")
        return jsonify({"error": f"Failed to update transaction: {str(e)}"}), 500


@transaction_bp.route('/transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """
    Delete a transaction
    """
    result = transaction_service.delete_transaction(transaction_id)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@transaction_bp.route('/transactions/batch', methods=['DELETE'])
def delete_batch_transactions():
    """
    Delete multiple transactions
    """
    try:
        data = request.get_json()
        
        if not data or 'transaction_ids' not in data:
            return jsonify({"error": "No transaction IDs provided"}), 400
        
        transaction_ids = data['transaction_ids']
        
        if not isinstance(transaction_ids, list):
            return jsonify({"error": "transaction_ids must be a list"}), 400
        
        result = transaction_service.delete_batch_transactions(transaction_ids)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error deleting batch transactions: {str(e)}")
        return jsonify({"error": f"Failed to delete transactions: {str(e)}"}), 500


@transaction_bp.route('/transactions/upload', methods=['POST'])
def upload_transactions():
    """
    Upload transactions from file (CSV, Excel, JSON)
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        transaction_type = request.form.get('transaction_type', 'float')
        company_id = request.form.get('company_id', type=int)
        agent_id = request.form.get('agent_id', type=int)
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not transaction_service._allowed_file(file.filename):
            return jsonify({"error": "File type not allowed. Use CSV, Excel, or JSON"}), 400
        
        if not company_id:
            return jsonify({"error": "Company ID is required"}), 400
        
        result = transaction_service.upload_transactions_file(
            file=file,
            filename=file.filename,
            transaction_type=transaction_type,
            company_id=company_id,
            agent_id=agent_id
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error uploading transactions: {str(e)}")
        return jsonify({"error": f"Failed to upload transactions: {str(e)}"}), 500


@transaction_bp.route('/transactions/scrape-process', methods=['POST'])
def scrape_and_process_transactions():
    """
    Process scraped transaction data from M-Pesa portal
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        file_path = data.get('file_path')
        business_shortcode = data.get('business_shortcode')
        additional_category = data.get('additional_category')  # 'float' or 'commission'
        company_id = data.get('company_id')
        agent_id = data.get('agent_id')
        
        if not all([file_path, business_shortcode, additional_category, company_id]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        if additional_category not in ['float', 'commission']:
            return jsonify({"error": "additional_category must be 'float' or 'commission'"}), 400
        
        # Process the scraped data
        result = transaction_service.process_scraped_data(
            file_path=file_path,
            business_shortcode=business_shortcode,
            additional_category=additional_category,
            company_id=company_id,
            agent_id=agent_id
        )
        
        if result.get('success', False):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error processing scraped data: {str(e)}")
        return jsonify({"error": f"Failed to process scraped data: {str(e)}"}), 500


@transaction_bp.route('/stats', methods=['GET'])
def get_transaction_stats():
    """
    Get transaction statistics
    """
    try:
        filters = {
            'agent_id': request.args.get('agent_id', type=int),
            'company_id': request.args.get('company_id', type=int),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'transaction_type': request.args.get('transaction_type', 'float')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        result = transaction_service.get_transaction_stats(filters)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error fetching transaction stats: {str(e)}")
        return jsonify({"error": f"Failed to fetch statistics: {str(e)}"}), 500


@transaction_bp.route('/export', methods=['GET'])
def export_transactions_():
    """
    Export transactions to CSV or JSON
    """
    try:
        filters = {
            'agent_id': request.args.get('agent_id', type=int),
            'company_id': request.args.get('company_id', type=int),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'transaction_type': request.args.get('transaction_type', 'float')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        format_type = request.args.get('format', 'csv')
        
        result = transaction_service.export_transactions(filters, format_type)
        
        if result['success']:
            from flask import Response
            
            if format_type == 'csv':
                response = Response(
                    result['data'],
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={result["filename"]}'}
                )
                return response
            else:
                response = Response(
                    result['data'],
                    mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename={result["filename"]}'}
                )
                return response
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error exporting transactions: {str(e)}")
        return jsonify({"error": f"Failed to export transactions: {str(e)}"}), 500


@transaction_bp.route('/transactions/template', methods=['GET'])
def download_template():
    """
    Download template file for batch upload
    """
    try:
        transaction_type = request.args.get('type', 'float')
        
        import pandas as pd
        import io
        
        if transaction_type == 'float':
            # Float transactions template
            template_data = {
                'receipt_no': ['TLHJL17S6G', 'TLHHV18B1X'],
                'completion_time': ['17-12-2025 20:25:17', '17-12-2025 17:11:22'],
                'initiation_time': ['17-12-2025 20:25:17', '17-12-2025 17:11:22'],
                'details': ['Deposit of Funds to 075****482 - Julia **** Marete', 
                           'Customer Withdrawal At Agent Till by 25476****896 - Moses **** Thabuari'],
                'transaction_status': ['Completed', 'Completed'],
                'paid_in': ['', '250'],
                'withdrawn': ['-100', ''],
                'balance': ['24100', '24200'],
                'balance_confirmed': ['TRUE', 'TRUE'],
                'reason_type': ['Deposit at Agent Till', 'Customer Withdrawal at Agent Till'],
                'other_party_info': ['075****482 - Julia **** Marete', '25476****896 - Moses **** Thabuari'],
                'linked_transaction_id': ['', ''],
                'account_number': ['', ''],
                'currency': ['KES', 'KES']
            }
        else:
            # Commission transactions template
            template_data = {
                'receipt_no': ['TLHMK1AF00', 'TLHB31AIRT'],
                'completion_time': ['17-12-2025 21:24:52', '17-12-2025 21:11:16'],
                'initiation_time': ['17-12-2025 21:24:52', '17-12-2025 21:11:16'],
                'details': ['Deposit commission', 'Deposit commission'],
                'transaction_status': ['Completed', 'Completed'],
                'commission_amount': ['9.6', '3.2'],
                'commission_rate': ['1.2', '1.2'],
                'parent_transaction_id': ['', ''],
                'balance': ['9067.2', '9057.6'],
                'balance_confirmed': ['TRUE', 'TRUE'],
                'reason_type': ['Deposit at Agent Till', 'Deposit at Agent Till'],
                'other_party_info': ['SP', 'SP'],
                'linked_transaction_id': ['', ''],
                'account_number': ['', ''],
                'currency': ['KES', 'KES']
            }
        
        df = pd.DataFrame(template_data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Template', index=False)
        
        output.seek(0)
        
        from flask import Response
        filename = f"transaction_{transaction_type}_template.xlsx"
        
        response = Response(
            output.read(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error downloading template: {str(e)}")
        return jsonify({"error": f"Failed to download template: {str(e)}"}), 500