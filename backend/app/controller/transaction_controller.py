from flask import Blueprint, request, jsonify, current_app, send_file, render_template, make_response
from datetime import datetime
from app.service.transaction_service import TransactionService
from app.service.reports.commissions_report_service import CommissionReportService
from app.service.reports.fraud_report_service import FraudReportService
from app.service.reports.agent_performance_report_service import AgentPerformanceReportService
from app.service.export_service import ExportService
from app.utils.user_service import UserService
from app.model.company import Company
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import io
import os

FRAUD_TYPE_LABELS = {
    'split_transaction':          'Split Transaction',
    'rollover_fraud':             'Rollover Fraud',
    'rapid_back_forth':           'Rapid Back & Forth',
    'deposit_withdrawal_recovery':'Deposit-Withdrawal Recovery',
    'high_frequency_daily':       'High Frequency Daily',
}



transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

transaction_service = TransactionService()

commission_report_service = CommissionReportService()
fraud_report_service = FraudReportService()
agent_performance_report_service = AgentPerformanceReportService()
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
        company_id = request.args.get('company_id', type=int)

        # Generate report
        report = commission_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            transaction_type=transaction_type,
            reason_type=reason_type,
            transaction_status=transaction_status,
            company_id=company_id
        )
        
        return jsonify({'success': True, 'report': report})
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating commission report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@transaction_bp.route('/export-commissions-pdf', methods=['GET'])
def export_commissions_report_pdf():
    """Generate and stream a WeasyPrint PDF of the commissions report."""
    try:
        from weasyprint import HTML

        start_date       = request.args.get('start_date')
        end_date         = request.args.get('end_date')
        date_range       = request.args.get('date_range', 'custom')
        transaction_type = request.args.get('transaction_type', 'commission')
        reason_type      = request.args.get('reason_type')
        transaction_status = request.args.get('transaction_status')
        company_id       = request.args.get('company_id', type=int)

        report = commission_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            transaction_type=transaction_type,
            reason_type=reason_type,
            transaction_status=transaction_status,
            company_id=company_id,
        )

        html_string = render_template(
            'commissions_report_pdf.html',
            report=report,
            generated_at=datetime.now().strftime('%d %b %Y %H:%M'),
        )

        pdf_bytes = HTML(string=html_string).write_pdf()

        filename = f"commissions_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating commissions PDF: {str(e)}")
        import traceback; traceback.print_exc()
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

@transaction_bp.route('/fraud-report', methods=['GET'])
def get_fraud_report():
    """Generate a historical fraud report (split, rollover, rapid back-forth) for a date range."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        date_range = request.args.get('date_range', 'custom')
        company_id = request.args.get('company_id', type=int)

        report = fraud_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            company_id=company_id,
        )

        return jsonify({'success': True, 'report': report})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating fraud report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/fraud-report-pdf', methods=['GET'])
def export_fraud_report_pdf():
    """Generate and stream a WeasyPrint PDF of the fraud report."""
    try:
        from weasyprint import HTML, CSS

        start_date  = request.args.get('start_date')
        end_date    = request.args.get('end_date')
        date_range  = request.args.get('date_range', 'custom')
        company_id  = request.args.get('company_id', type=int)

        report = fraud_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            company_id=company_id,
        )

        html_string = render_template(
            'fraud_report_pdf.html',
            report=report,
            generated_at=datetime.now().strftime('%d %b %Y %H:%M'),
            fraud_type_labels=FRAUD_TYPE_LABELS,
        )

        pdf_bytes = HTML(string=html_string).write_pdf()

        filename = f"fraud_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating fraud report PDF: {str(e)}")
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/agent-performance-report', methods=['GET'])
def get_agent_performance_report():
    """Return JSON agent performance report."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        date_range = request.args.get('date_range', 'custom')
        company_id = request.args.get('company_id', type=int)
        commission_threshold = request.args.get('commission_threshold', type=float, default=5000.0)
        float_threshold = request.args.get('float_threshold', type=float, default=50000.0)

        report = agent_performance_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            company_id=company_id,
            commission_threshold=commission_threshold,
            float_threshold=float_threshold,
        )
        return jsonify({'success': True, 'report': report})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating agent performance report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/agent-performance-report-pdf', methods=['GET'])
def get_agent_performance_report_pdf():
    """Generate and stream agent performance report as PDF."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        date_range = request.args.get('date_range', 'custom')
        company_id = request.args.get('company_id', type=int)
        commission_threshold = request.args.get('commission_threshold', type=float, default=5000.0)
        float_threshold = request.args.get('float_threshold', type=float, default=50000.0)

        report = agent_performance_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            company_id=company_id,
            commission_threshold=commission_threshold,
            float_threshold=float_threshold,
        )

        generated_at = datetime.now().strftime('%d %b %Y, %H:%M')
        html = render_template(
            'agent_performance_report_pdf.html',
            report=report,
            generated_at=generated_at,
            fraud_category_labels={
                'split_transaction':    'Split Transaction',
                'high_frequency_daily': 'High Frequency Daily',
                'rapid_back_forth':     'Rapid Back & Forth',
            },
        )

        from weasyprint import HTML as WeasyHTML
        pdf_bytes = WeasyHTML(string=html).write_pdf()

        filename = f"agent_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating agent performance PDF: {str(e)}")
        import traceback; traceback.print_exc()
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
@jwt_required()
def get_transactions():
    """
    Get transactions with filtering and pagination.
    Results are scoped to the current user's companies unless the user is an admin.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        role = (current_user.role or 'user').lower()

        # Get query parameters
        filters = {
            'agent_id': request.args.get('agent_id', type=int),
            'company_id': request.args.get('company_id', type=int),
            'start_date': request.args.get('startDate'),
            'end_date': request.args.get('endDate'),
            'reasonType': request.args.get('reasonType'),
            'transaction_status': request.args.get('transaction_status'),
            'transaction_type': request.args.get('transaction_type', 'float'),
            'search': request.args.get('search', '')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        # Scope results to the current user's companies for non-admin roles
        if role not in ('admin', 'administrator'):
            if role == 'agent':
                company_ids = [
                    c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()
                ]
            else:
                # Regular user: companies they own
                company_ids = [
                    c.id for c in Company.query.filter_by(user_id=current_user_id).all()
                ]

            # If a specific company_id was requested, ensure it belongs to this user
            if filters.get('company_id'):
                if filters['company_id'] not in company_ids:
                    return jsonify({"error": "Unauthorized"}), 403
            else:
                filters['company_ids'] = company_ids

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
@jwt_required()
def get_transaction_stats():
    """
    Get transaction statistics scoped to the current user's companies.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        role = (current_user.role or 'user').lower()

        filters = {
            'agent_id': request.args.get('agent_id', type=int),
            'company_id': request.args.get('company_id', type=int),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'transaction_type': request.args.get('transaction_type', 'float')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        if role not in ('admin', 'administrator'):
            if role == 'agent':
                company_ids = [c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()]
            else:
                company_ids = [c.id for c in Company.query.filter_by(user_id=current_user_id).all()]

            if filters.get('company_id'):
                if filters['company_id'] not in company_ids:
                    return jsonify({"error": "Unauthorized"}), 403
            else:
                filters['company_ids'] = company_ids

        result = transaction_service.get_transaction_stats(filters)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"Error fetching transaction stats: {str(e)}")
        return jsonify({"error": f"Failed to fetch statistics: {str(e)}"}), 500


@transaction_bp.route('/dashboard-analytics', methods=['GET'])
@jwt_required()
def get_dashboard_analytics():
    """
    Get comprehensive analytics data for the dashboard.
    Returns KPIs, trends, distribution, and recent activity.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        role = (current_user.role or 'user').lower() if current_user else 'user'

        filters = {
            'company_id': request.args.get('company_id', type=int),
            'agent_id': request.args.get('agent_id', type=int),
            'days': request.args.get('days', 30, type=int)
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        # Resolve company IDs for commission filtering (COMM-* records use company_id FK).
        # Collect all companies the user is linked to as owner (user_id) or agent (agent_user_id).
        if role in ('admin', 'administrator'):
            filters['commission_company_ids'] = None  # all companies
        else:
            owned = Company.query.filter_by(user_id=current_user_id).all()
            agented = Company.query.filter_by(agent_user_id=current_user_id).all()
            all_ids = list({c.id for c in owned + agented})
            filters['commission_company_ids'] = all_ids
        

        print(f"Dashboard analytics filters: {filters}")

        result = transaction_service.get_dashboard_analytics(filters)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard analytics: {str(e)}")
        return jsonify({"error": f"Failed to fetch dashboard analytics: {str(e)}"}), 500


@transaction_bp.route('/clawbacks', methods=['GET'])
def get_clawbacks():
    """Return commission clawback transactions."""
    try:
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
        }
        filters = {k: v for k, v in filters.items() if v}
        result = transaction_service.get_clawbacks(filters)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        current_app.logger.error(f"Error fetching clawbacks: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/export-commission-tills', methods=['GET'])
@jwt_required()
def export_commission_tills():
    """Export all commission till balances to an Excel file."""
    try:
        import pandas as pd
        import io as _io

        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()
        if role in ('admin', 'administrator'):
            company_ids = None
        elif role == 'agent':
            company_ids = [c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()]
        else:
            company_ids = [c.id for c in Company.query.filter_by(user_id=current_user_id).all()]

        updated_after = request.args.get('updated_after')

        result = transaction_service.get_commission_till_balances(
            company_ids=company_ids, page=1, per_page=10000, updated_after=updated_after
        )
        if not result['success']:
            return jsonify(result), 400

        rows = result['data']
        df = pd.DataFrame([{
            'Till Name': r['till_name'],
            'Shortcode': r['shortcode'],
            'Current Balance (KES)': float(r['current_balance'] or 0),
            'Available Balance (KES)': float(r['available_balance'] or 0),
            'Last Updated': r['last_updated'],
        } for r in rows])

        output = _io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Commission Till Balances', index=False)
        output.seek(0)

        from flask import Response
        filename = f"commission_till_balances_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            output.read(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        current_app.logger.error(f"Error exporting commission tills: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/commission-till-balances', methods=['GET'])
@jwt_required()
def get_commission_till_balances():
    """Return latest commission balance snapshot per child-org till."""
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()

        if role in ('admin', 'administrator'):
            company_ids = None  # all
        elif role == 'agent':
            company_ids = [c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()]
        else:
            company_ids = [c.id for c in Company.query.filter_by(user_id=current_user_id).all()]

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        updated_after = request.args.get('updated_after', None)

        result = transaction_service.get_commission_till_balances(
            company_ids=company_ids, page=page, per_page=per_page, updated_after=updated_after
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        current_app.logger.error(f"Error fetching commission till balances: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/user-companies', methods=['GET'])
@jwt_required()
def get_user_companies():
    """Return all companies linked to the current user."""
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()

        if role in ('admin', 'administrator'):
            companies = Company.query.filter(Company.shortcode.isnot(None)).all()
        elif role == 'agent':
            companies = Company.query.filter_by(agent_user_id=current_user_id).all()
        else:
            companies = Company.query.filter_by(user_id=current_user_id).all()

        return jsonify({
            'success': True,
            'data': [
                {'id': c.id, 'company_name': c.company_name, 'shortcode': c.shortcode}
                for c in companies
            ]
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching user companies: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/commission-closing-balance', methods=['GET'])
@jwt_required()
def get_commission_closing_balance():
    """Return the latest commission balance for a given shortcode."""
    try:
        from app import db
        from sqlalchemy import text

        shortcode = request.args.get('shortcode')
        if not shortcode:
            return jsonify({'error': 'shortcode is required'}), 400

        row = db.session.execute(
            text("""
                SELECT t.balance, t.completion_time
                FROM transactions t
                JOIN companies c ON t.company_id = c.id
                WHERE c.shortcode = :shortcode
                  AND t.transaction_type = 'commission'
                  AND t.business_shortcode = :shortcode
                  AND t.receipt_no NOT LIKE 'COMM-%'
                ORDER BY t.completion_time DESC, t.id DESC
                LIMIT 1
            """),
            {'shortcode': shortcode}
        ).fetchone()

        if row is None:
            return jsonify({'success': True, 'data': {'balance': None, 'as_of': None}}), 200

        return jsonify({
            'success': True,
            'data': {
                'balance': float(row.balance),
                'as_of': row.completion_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching commission closing balance: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/commission-closing-balance-total', methods=['GET'])
@jwt_required()
def get_commission_closing_balance_total():
    """Sum the latest commission balance across all companies linked to the current user."""
    try:
        from app import db
        from sqlalchemy import text

        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()

        base_type_filter = (
            "t.transaction_type = 'commission' "
            "AND t.business_shortcode = c.shortcode "
            "AND t.receipt_no NOT LIKE 'COMM-%'"
        )

        if role in ('admin', 'administrator'):
            company_filter = f"WHERE {base_type_filter}"
            params = {}
        elif role == 'agent':
            companies = Company.query.filter_by(agent_user_id=current_user_id).all()
            ids = [c.id for c in companies]
            if not ids:
                return jsonify({'success': True, 'data': {'balance': 0.0, 'company_count': 0}}), 200
            company_filter = f"WHERE c.id = ANY(:ids) AND {base_type_filter}"
            params = {'ids': ids}
        else:
            companies = Company.query.filter_by(user_id=current_user_id).all()
            ids = [c.id for c in companies]
            if not ids:
                return jsonify({'success': True, 'data': {'balance': 0.0, 'company_count': 0}}), 200
            company_filter = f"WHERE c.id = ANY(:ids) AND {base_type_filter}"
            params = {'ids': ids}

        row = db.session.execute(
            text(f"""
                SELECT
                    COALESCE(SUM(latest.balance), 0) AS total_balance,
                    COUNT(*) AS company_count
                FROM (
                    SELECT DISTINCT ON (c.id)
                        t.balance
                    FROM transactions t
                    JOIN companies c ON t.company_id = c.id
                    {company_filter}
                    ORDER BY c.id, t.completion_time DESC, t.id DESC
                ) latest
            """),
            params
        ).fetchone()

        return jsonify({
            'success': True,
            'data': {
                'balance': float(row.total_balance),
                'company_count': int(row.company_count)
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching total commission balance: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/commission-monthly-transfer-total', methods=['GET'])
@jwt_required()
def get_commission_monthly_transfer_total():
    """
    Sum all MMF commission transfers across every company the current user can see,
    for the given commission month (transfer lands in month+1).
    Query params: month (1-12), year
    """
    try:
        from app import db
        from sqlalchemy import text

        month = request.args.get('month', type=int)
        year  = request.args.get('year',  type=int)
        if not month or not year:
            return jsonify({'error': 'month and year are required'}), 400

        transfer_month = month + 1
        transfer_year  = year
        if transfer_month > 12:
            transfer_month = 1
            transfer_year += 1

        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()

        if role in ('admin', 'administrator'):
            company_filter = ""
            params = {'yr': transfer_year, 'mo': transfer_month}
        else:
            companies = Company.query.filter(
                db.or_(
                    Company.user_id == current_user_id,
                    Company.agent_user_id == current_user_id,
                )
            ).all()
            ids = [c.id for c in companies]
            if not ids:
                return jsonify({'success': True, 'data': {'amount': 0.0, 'company_count': 0}}), 200
            company_filter = "AND t.company_id = ANY(:ids)"
            params = {'yr': transfer_year, 'mo': transfer_month, 'ids': ids}

        row = db.session.execute(
            text(f"""
                SELECT
                    COALESCE(SUM(ABS(t.withdrawn)), 0) AS total_amount,
                    COUNT(*) AS company_count
                FROM transactions t
                JOIN companies c ON t.company_id = c.id
                WHERE t.transaction_type = 'commission'
                  AND t.reason_type LIKE '%Transfer of Commission to MMF%'
                  AND EXTRACT(YEAR  FROM t.completion_time) = :yr
                  AND EXTRACT(MONTH FROM t.completion_time) = :mo
                  {company_filter}
            """),
            params
        ).fetchone()

        return jsonify({
            'success': True,
            'data': {
                'amount': float(row.total_amount),
                'company_count': int(row.company_count),
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching total monthly commission transfer: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/commission-monthly-transfer', methods=['GET'])
@jwt_required()
def get_commission_monthly_transfer():
    """
    Return the head-office MMF transfer amount for a given commission month.
    The transfer always lands on the 1st of the FOLLOWING month, so we look
    in month+1 for the 'Agency H/O Transfer of Commission to MMF Account' row.
    Query params: shortcode, month (1-12), year
    """
    try:
        from app import db
        from sqlalchemy import text

        shortcode = request.args.get('shortcode')
        month = request.args.get('month', type=int)
        year  = request.args.get('year',  type=int)

        if not shortcode or not month or not year:
            return jsonify({'error': 'shortcode, month and year are required'}), 400

        # Transfer month = commission month + 1
        transfer_month = month + 1
        transfer_year  = year
        if transfer_month > 12:
            transfer_month = 1
            transfer_year += 1

        row = db.session.execute(
            text("""
                SELECT ABS(t.withdrawn) AS amount, t.completion_time, t.receipt_no
                FROM transactions t
                JOIN companies c ON t.company_id = c.id
                WHERE c.shortcode = :shortcode
                  AND t.transaction_type = 'commission'
                  AND t.reason_type LIKE '%Transfer of Commission to MMF%'
                  AND EXTRACT(YEAR  FROM t.completion_time) = :yr
                  AND EXTRACT(MONTH FROM t.completion_time) = :mo
                ORDER BY t.completion_time DESC
                LIMIT 1
            """),
            {'shortcode': shortcode, 'yr': transfer_year, 'mo': transfer_month}
        ).fetchone()

        if row is None:
            return jsonify({'success': True, 'data': {'amount': None, 'receipt_no': None, 'as_of': None}}), 200

        return jsonify({
            'success': True,
            'data': {
                'amount': float(row.amount),
                'receipt_no': row.receipt_no,
                'as_of': row.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching monthly commission transfer: {e}")
        return jsonify({'error': str(e)}), 500


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