import hashlib
import json
import logging
import os
import io
import redis

from flask import Blueprint, request, jsonify, current_app, send_file, render_template, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime

from app.service.transaction_service import TransactionService
from app.service.reports.commissions_report_service import CommissionReportService
from app.service.reports.fraud_report_service import FraudReportService
from app.service.reports.agent_performance_report_service import AgentPerformanceReportService
from app.service.reports.monthly_commission_report_service import MonthlyCommissionReportService
from app.service.reports.float_health_report_service import FloatHealthReportService
from app.service.export_service import ExportService
from app.utils.user_service import UserService
from app.model.company import Company
from app.model.agentcompany import AgentCompany

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


FRAUD_REPORT_CACHE_TTL = 3600  # 1 hour


def _fraud_report_cache_key(user_id, company_id, company_ids, date_range, start_date, end_date):
    # When a specific company is requested, scope to that company.
    # Otherwise, scope to all company_ids owned by the logged-in user.
    if company_id:
        scope = str(company_id)
    else:
        scope = ','.join(str(i) for i in sorted(company_ids or []))
    parts = [str(user_id), scope, str(date_range), str(start_date or ''), str(end_date or '')]
    digest = hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]
    return f'fraud_report:{digest}'

logger = logging.getLogger(__name__)

FRAUD_TYPE_LABELS = {
    'split_transaction':          'Split Transaction',
    'rollover_fraud':             'Rollover Fraud',
    'rapid_back_forth':           'Rapid Back & Forth',
    'deposit_withdrawal_recovery':'Deposit-Withdrawal Recovery',
    'high_frequency_daily':       'High Frequency Daily',
    'structuring':                'Structuring',
    'float_cycling':              'Float Cycling',
    'split_deposit':              'Split Deposit',
    'continuous_rapid_activity':  'Continuous Rapid Activity',
}



transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

transaction_service = TransactionService()

commission_report_service = CommissionReportService()
fraud_report_service = FraudReportService()
agent_performance_report_service = AgentPerformanceReportService()
monthly_commission_report_service = MonthlyCommissionReportService()
float_health_report_service = FloatHealthReportService()
export_service = ExportService()


def _get_user_company_scope():
    """
    Returns (role, company_ids) for the current JWT user.
    company_ids is None for admins (no restriction), list for everyone else.
    """
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user:
        return None, None
    role = (current_user.role or 'user').lower()
    if role in ('admin', 'administrator'):
        return role, None
    if role == 'agent':
        company_ids = [c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()]
    else:
        company_ids = [c.id for c in Company.query.filter_by(user_id=current_user_id).all()]
    return role, company_ids


def _resolve_company_id(requested_id, company_ids):
    """
    Validate the requested company_id belongs to the user.
    Returns (company_id, error_response) — error_response is None on success.
    """
    if not requested_id:
        return None, None
    if company_ids is not None and requested_id not in company_ids:
        return None, (jsonify({'error': 'Unauthorized'}), 403)
    return requested_id, None


@transaction_bp.route('/commissions-report', methods=['GET'])
@jwt_required()
def get_commissions_report():
    """Get commission report data"""
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = commission_report_service.generate_report(
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            date_range=request.args.get('date_range', 'custom'),
            transaction_type=request.args.get('transaction_type', 'commission'),
            reason_type=request.args.get('reason_type'),
            transaction_status=request.args.get('transaction_status'),
            company_id=company_id,
            company_ids=company_ids if not company_id else None,
        )
        return jsonify({'success': True, 'report': report})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating commission report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/export-commissions-pdf', methods=['GET'])
@jwt_required()
def export_commissions_report_pdf():
    """Generate and stream a WeasyPrint PDF of the commissions report."""
    try:
        from weasyprint import HTML
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = commission_report_service.generate_report(
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            date_range=request.args.get('date_range', 'custom'),
            transaction_type=request.args.get('transaction_type', 'commission'),
            reason_type=request.args.get('reason_type'),
            transaction_status=request.args.get('transaction_status'),
            company_id=company_id,
            company_ids=company_ids if not company_id else None,
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
        current_app.logger.error(f"Error generating commissions PDF: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/export-commissions', methods=['GET'])
@jwt_required()
def export_commissions_report():
    """Export commission report in various formats"""
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        export_data = export_service.export_commission_report(
            format_type=request.args.get('format', 'csv'),
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            date_range=request.args.get('date_range', 'custom'),
            transaction_type=request.args.get('transaction_type', 'commission'),
            reason_type=request.args.get('reason_type'),
            transaction_status=request.args.get('transaction_status'),
        )
        return export_data

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error exporting commission report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/fraud-report', methods=['GET'])
@jwt_required()
def get_fraud_report():
    """Generate a historical fraud report scoped to the current user's companies."""
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        user_id = get_jwt_identity()
        date_range = request.args.get('date_range', 'custom')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        cache_key = _fraud_report_cache_key(user_id, company_id, company_ids, date_range, start_date, end_date)
        try:
            cached = _get_redis().get(cache_key)
            if cached:
                logger.info(f"[FraudReport] Cache HIT for key {cache_key}")
                return jsonify({'success': True, 'report': json.loads(cached), 'cached': True})
        except Exception as redis_err:
            logger.warning(f"[FraudReport] Redis read failed, proceeding without cache: {redis_err}")

        report = fraud_report_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            company_id=company_id,
            company_ids=company_ids if not company_id else None,
        )

        try:
            _get_redis().setex(cache_key, FRAUD_REPORT_CACHE_TTL, json.dumps(report))
            logger.info(f"[FraudReport] Cached result under key {cache_key} (TTL {FRAUD_REPORT_CACHE_TTL}s)")
        except Exception as redis_err:
            logger.warning(f"[FraudReport] Redis write failed: {redis_err}")

        return jsonify({'success': True, 'report': report})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating fraud report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/fraud-report-pdf', methods=['GET'])
@jwt_required()
def export_fraud_report_pdf():
    """Generate and stream a WeasyPrint PDF of the fraud report."""
    try:
        from weasyprint import HTML
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = fraud_report_service.generate_report(
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            date_range=request.args.get('date_range', 'custom'),
            company_id=company_id,
            company_ids=company_ids if not company_id else None,
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
        current_app.logger.error(f"Error generating fraud report PDF: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/agent-performance-report', methods=['GET'])
@jwt_required()
def get_agent_performance_report():
    """Return JSON agent performance report scoped to the current user's companies."""
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = agent_performance_report_service.generate_report(
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            date_range=request.args.get('date_range', 'custom'),
            company_id=company_id,
            commission_threshold=request.args.get('commission_threshold', type=float, default=5000.0),
            float_threshold=request.args.get('float_threshold', type=float, default=50000.0),
            company_ids=company_ids if not company_id else None,
        )
        return jsonify({'success': True, 'report': report})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating agent performance report: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/agent-performance-report-pdf', methods=['GET'])
@jwt_required()
def get_agent_performance_report_pdf():
    """Generate and stream agent performance report as PDF."""
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = agent_performance_report_service.generate_report(
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            date_range=request.args.get('date_range', 'custom'),
            company_id=company_id,
            commission_threshold=request.args.get('commission_threshold', type=float, default=5000.0),
            float_threshold=request.args.get('float_threshold', type=float, default=50000.0),
            company_ids=company_ids if not company_id else None,
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
        current_app.logger.error(f"Error generating agent performance PDF: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/monthly-commission-report', methods=['GET'])
@jwt_required()
def get_monthly_commission_report():
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        now = datetime.now()
        year  = request.args.get('year',  type=int, default=now.year)
        month = request.args.get('month', type=int, default=now.month)
        if not (1 <= month <= 12):
            return jsonify({'success': False, 'error': 'month must be 1–12'}), 400
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = monthly_commission_report_service.generate_report(
            year, month, company_id, company_ids=company_ids if not company_id else None
        )
        return jsonify({'success': True, 'data': report})
    except Exception as e:
        current_app.logger.error(f"Monthly commission report error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/monthly-commission-report-pdf', methods=['GET'])
@jwt_required()
def get_monthly_commission_report_pdf():
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        now = datetime.now()
        year  = request.args.get('year',  type=int, default=now.year)
        month = request.args.get('month', type=int, default=now.month)
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = monthly_commission_report_service.generate_report(
            year, month, company_id, company_ids=company_ids if not company_id else None
        )
        generated_at = now.strftime('%d %b %Y, %H:%M')
        html = render_template('monthly_commission_report_pdf.html', report=report, generated_at=generated_at)

        from weasyprint import HTML as WeasyHTML
        pdf_bytes = WeasyHTML(string=html).write_pdf()

        filename = f"monthly_commission_{report['label'].replace(' ', '_')}_{now.strftime('%Y%m%d%H%M%S')}.pdf"
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        current_app.logger.error(f"Monthly commission PDF error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/monthly-commission-report-excel', methods=['GET'])
@jwt_required()
def get_monthly_commission_report_excel():
    try:
        import io
        import pandas as pd
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        now = datetime.now()
        year  = request.args.get('year',  type=int, default=now.year)
        month = request.args.get('month', type=int, default=now.month)
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = monthly_commission_report_service.generate_report(
            year, month, company_id, company_ids=company_ids if not company_id else None
        )
        tills = report.get('tills', [])

        rows = [
            {
                'Shortcode':        t['shortcode'],
                'Company Name':     t['company_name'],
                'Location':         t['location'],
                'Rolled Up (KES)':  round(t['amount'], 2),
                'Prev Month (KES)': round(t['prev_amount'], 2),
                'MoM Change (KES)': round(t['mom_change'], 2),
                'MoM %':            round(t['mom_pct'], 2) if t['mom_pct'] is not None else '',
                'Receipt No':       t['receipt_no'],
                'Rollup Date':      t['completion_time'],
            }
            for t in tills
        ]

        s = report['summary']
        summary_rows = [
            {'Metric': 'Commission Month',    'Value': report['label']},
            {'Metric': 'Total Rolled Up',     'Value': round(s['total_amount'], 2)},
            {'Metric': 'Prev Month Total',    'Value': round(s['prev_total_amount'], 2)},
            {'Metric': 'MoM Change (KES)',    'Value': round(s['mom_change'], 2)},
            {'Metric': 'MoM %',               'Value': round(s['mom_pct'], 2) if s['mom_pct'] is not None else ''},
            {'Metric': 'Number of Tills',     'Value': s['till_count']},
            {'Metric': 'Generated At',        'Value': now.strftime('%d %b %Y %H:%M')},
        ]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name='Rollup by Till', index=False)
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Summary', index=False)
        output.seek(0)

        filename = f"monthly_commission_{report['label'].replace(' ', '_')}_{now.strftime('%Y%m%d%H%M%S')}.xlsx"
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=filename)
    except Exception as e:
        current_app.logger.error(f"Monthly commission Excel error: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@transaction_bp.route('/float-health-report', methods=['GET'])
@jwt_required()
def get_float_health_report():
    """Return per-till float health metrics scoped to the current user's companies."""
    try:
        role, company_ids = _get_user_company_scope()
        if role is None:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        company_id, err = _resolve_company_id(request.args.get('company_id', type=int), company_ids)
        if err:
            return err

        report = float_health_report_service.generate_report(
            period_type=request.args.get('period_type', 'monthly'),
            year=request.args.get('year', type=int),
            month=request.args.get('month', type=int),
            quarter=request.args.get('quarter', type=int),
            half=request.args.get('half', type=int),
            week=request.args.get('week', type=int),
            start_date=request.args.get('start_date'),
            end_date=request.args.get('end_date'),
            company_id=company_id,
            company_ids=company_ids if not company_id else None,
            low_float_threshold=request.args.get('low_float_threshold', type=float, default=20000.0),
            critical_float_threshold=request.args.get('critical_float_threshold', type=float, default=5000.0),
        )
        return jsonify({'success': True, 'report': report})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating float health report: {str(e)}")
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
        current_app.logger.error(f"Error exporting transactions: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# Handle OPTIONS requests separately
@transaction_bp.route('', methods=['OPTIONS'])
@transaction_bp.route('/', methods=['OPTIONS'])
def handle_options():
    return jsonify({'message': 'OK'}), 200

@transaction_bp.route('', methods=['GET'])
@transaction_bp.route('/', methods=['GET'])
@jwt_required()
def get_transactions():
    """
    Get transactions with filtering and pagination.
    Results are scoped to the current user's companies unless the user is an admin.
    """
    try:
        current_user_id = get_jwt_identity()
        logger.info(f"[TXN] get_transactions called — user_id={current_user_id} args={dict(request.args)}")

        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            logger.warning(f"[TXN] user not found: {current_user_id}")
            return jsonify({"error": "User not found"}), 404

        role = (current_user.role or 'user').lower()
        logger.info(f"[TXN] user role={role}")

        # Get query parameters
        filters = {
            'agent_id': request.args.get('agent_id', type=int),
            'company_id': request.args.get('company_id', type=int),
            'start_date': request.args.get('startDate'),
            'end_date': request.args.get('endDate'),
            'reasonType': request.args.get('reasonType'),
            'transaction_status': request.args.get('transaction_status'),
            'transaction_type': request.args.get('transaction_type', 'float'),
            'float_scope': request.args.get('float_scope'),
            'search': request.args.get('search', '')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        logger.info(f"[TXN] filters after cleanup: {filters}")

        # Scope results to the current user's companies for non-admin roles
        if role not in ('admin', 'administrator'):
            if role == 'agent':
                company_ids = [
                    c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()
                ]
            else:
                company_ids = [
                    c.id for c in Company.query.filter_by(user_id=current_user_id).all()
                ]

            logger.info(f"[TXN] scoped to company_ids={company_ids}")

            if filters.get('company_id'):
                if filters['company_id'] not in company_ids:
                    logger.warning(f"[TXN] unauthorized company_id={filters['company_id']} for user={current_user_id}")
                    return jsonify({"error": "Unauthorized"}), 403
            else:
                filters['company_ids'] = company_ids

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        logger.info(f"[TXN] querying page={page} per_page={per_page} final_filters={filters}")

        result = transaction_service.get_transactions(filters, page, per_page)

        logger.info(f"[TXN] service result success={result.get('success')} "
                    f"count={len(result.get('data', []))} error={result.get('error')}")

        if result['success']:
            resp = jsonify(result)
            resp.headers['Cache-Control'] = 'no-store'
            return resp, 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.exception(f"[TXN] unhandled exception in get_transactions: {e}")
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
            try:
                r = _get_redis()
                keys = list(r.scan_iter('fraud_report:*'))
                if keys:
                    r.delete(*keys)
                    logger.info(f"[FraudReport] Cache invalidated {len(keys)} key(s) after upload")
            except Exception as redis_err:
                logger.warning(f"[FraudReport] Cache invalidation failed: {redis_err}")
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
            try:
                r = _get_redis()
                keys = list(r.scan_iter('fraud_report:*'))
                if keys:
                    r.delete(*keys)
                    logger.info(f"[FraudReport] Cache invalidated {len(keys)} key(s) after scrape-process")
            except Exception as redis_err:
                logger.warning(f"[FraudReport] Cache invalidation failed: {redis_err}")
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
            'transaction_type': request.args.get('transaction_type', 'float'),
            'float_scope': request.args.get('float_scope')
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
        elif role == 'agent':
            # Mirror transactions page: agents see only their agented companies
            agented = Company.query.filter_by(agent_user_id=current_user_id).all()
            filters['commission_company_ids'] = list({c.id for c in agented})
        else:
            # Mirror transactions page: owners see only their owned companies
            owned = Company.query.filter_by(user_id=current_user_id).all()
            filters['commission_company_ids'] = list({c.id for c in owned})
        

        
        result = transaction_service.get_dashboard_analytics(filters)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard analytics: {str(e)}")
        return jsonify({"error": f"Failed to fetch dashboard analytics: {str(e)}"}), 500


@transaction_bp.route('/clawbacks', methods=['GET'])
@jwt_required()
def get_clawbacks():
    """Return commission clawback transactions scoped to the current user's companies."""
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()

        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
        }
        filters = {k: v for k, v in filters.items() if v}

        if role not in ('admin', 'administrator'):
            if role == 'agent':
                company_ids = [c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()]
            else:
                company_ids = [c.id for c in Company.query.filter_by(user_id=current_user_id).all()]
            filters['company_ids'] = company_ids

        result = transaction_service.get_clawbacks(filters)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        current_app.logger.error(f"Error fetching clawbacks: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/export-clawbacks-pdf', methods=['GET'])
@jwt_required()
def export_clawbacks_pdf():
    """Generate and stream a WeasyPrint PDF of commission clawback records."""
    try:
        from weasyprint import HTML
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        role = (current_user.role or 'user').lower()
        filters = {
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
        }
        filters = {k: v for k, v in filters.items() if v}

        if role not in ('admin', 'administrator'):
            if role == 'agent':
                company_ids = [c.id for c in Company.query.filter_by(agent_user_id=current_user_id).all()]
            else:
                company_ids = [c.id for c in Company.query.filter_by(user_id=current_user_id).all()]
            filters['company_ids'] = company_ids

        result = transaction_service.get_clawbacks(filters)
        data = result.get('data', [])

        total_amount = sum(abs(r.get('withdrawn') or 0) for r in data)
        companies_affected = len({r.get('company_name') for r in data if r.get('company_name')})
        unique_shortcodes = len({r.get('business_shortcode') for r in data if r.get('business_shortcode')})
        avg_amount = total_amount / len(data) if data else 0

        html_string = render_template(
            'clawback_report_pdf.html',
            data=data,
            total=len(data),
            total_amount=total_amount,
            companies_affected=companies_affected,
            unique_shortcodes=unique_shortcodes,
            avg_amount=avg_amount,
            period_start=filters.get('start_date', ''),
            period_end=filters.get('end_date', ''),
            generated_at=datetime.now().strftime('%d %b %Y %H:%M'),
        )
        pdf_bytes = HTML(string=html_string).write_pdf()
        filename = f"clawback_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        current_app.logger.error(f"Error generating clawbacks PDF: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@transaction_bp.route('/export-commission-tills', methods=['GET'])
@jwt_required()
def export_commission_tills():
    """Export commission till balances grouped by company with color-coded styling."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
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

        # Shortcode → balance row lookups
        sc_map = {r['shortcode']: r for r in result['data']}
        no_data_map = {r['shortcode']: r for r in result.get('no_commission_tills', [])}

        # Company → tills hierarchy
        if company_ids is not None:
            companies = Company.query.filter(Company.id.in_(company_ids)).order_by(Company.company_name).all()
        else:
            companies = Company.query.order_by(Company.company_name).all()

        # Same 6 palettes as Swap History Excel
        PALETTES = [
            {'company': '1F3864', 'sub': 'BDD7EE', 'even': 'DEEAF1', 'odd': 'FFFFFF'},
            {'company': '375623', 'sub': 'C6EFCE', 'even': 'EBF5EC', 'odd': 'FFFFFF'},
            {'company': '833C00', 'sub': 'FCE4D6', 'even': 'FFF2CC', 'odd': 'FFFFFF'},
            {'company': '4B2981', 'sub': 'E2CFFF', 'even': 'F4EFFF', 'odd': 'FFFFFF'},
            {'company': '004B4B', 'sub': 'C6E0E0', 'even': 'E2F0F0', 'odd': 'FFFFFF'},
            {'company': '2E4057', 'sub': 'D0D8E4', 'even': 'EEF1F6', 'odd': 'FFFFFF'},
        ]

        COLS = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        HEADERS = ['Company', 'Till Name', 'Short Code', 'Current Balance (KES)', 'Available Balance (KES)', 'Last Updated', 'Status']
        COL_WIDTHS = [32, 42, 14, 24, 26, 20, 20]
        NUM_COLS = len(COLS)

        thin = Side(style='thin', color='D0D0D0')
        bdr = Border(left=thin, right=thin, top=thin, bottom=thin)

        def mk_fill(hex_color):
            return PatternFill(fill_type='solid', fgColor=hex_color)

        def mk_font(color='000000', bold=False, size=9):
            return Font(color=color, bold=bold, size=size)

        wb = Workbook()
        ws = wb.active
        ws.title = 'Commission Till Balances'

        # Column header row
        for c, (h, w) in enumerate(zip(HEADERS, COL_WIDTHS), 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = mk_fill('1F3864')
            cell.font = Font(bold=True, color='FFFFFF', size=10)
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = bdr
            ws.column_dimensions[get_column_letter(c)].width = w
        ws.row_dimensions[1].height = 20
        ws.freeze_panes = 'A2'

        r = 1  # 0-indexed data row counter (row 1 = header)

        for ci, company in enumerate(companies):
            palette = PALETTES[ci % NUM_COLS]
            tills = AgentCompany.query.filter_by(company_id=company.id).order_by(AgentCompany.company_name).all()
            if not tills:
                continue

            # Company header — dark accent, merged
            r += 1
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NUM_COLS)
            cell = ws.cell(row=r, column=1, value=f'  {company.company_name or "Unknown Company"}')
            cell.fill = mk_fill(palette['company'])
            cell.font = Font(bold=True, color='FFFFFF', size=11)
            cell.alignment = Alignment(vertical='center')
            ws.row_dimensions[r].height = 18

            # Till sub-header — lighter tint, merged
            r += 1
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NUM_COLS)
            cell = ws.cell(row=r, column=1, value=f'    Tills ({len(tills)})')
            cell.fill = mk_fill(palette['sub'])
            cell.font = Font(bold=True, color='000000', size=9)
            cell.alignment = Alignment(vertical='center')
            ws.row_dimensions[r].height = 14

            for ti, ac in enumerate(tills):
                sc = ac.business_short_code or ac.short_code
                row_data = sc_map.get(sc) or no_data_map.get(sc)
                no_data = (row_data is None) or row_data.get('no_commission_data', False)

                bg = palette['even'] if ti % 2 == 0 else palette['odd']
                row_fill = mk_fill(bg)

                cur_bal = float(row_data['current_balance'] or 0) if row_data and row_data.get('current_balance') is not None else None
                avail_bal = float(row_data['available_balance'] or 0) if row_data and row_data.get('available_balance') is not None else None
                last_upd = None
                if row_data and row_data.get('last_updated'):
                    last_upd = row_data['last_updated'][:16].replace('T', ' ')

                values = [
                    company.company_name or '',
                    ac.company_name or ac.organization_name or '',
                    sc or '',
                    cur_bal,
                    avail_bal,
                    last_upd,
                    'No commission data' if no_data else 'Active',
                ]

                r += 1
                for c_idx, val in enumerate(values, 1):
                    cell = ws.cell(row=r, column=c_idx, value=val)
                    cell.fill = row_fill
                    cell.border = bdr
                    cell.alignment = Alignment(vertical='center')
                    if c_idx in (4, 5):
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                    if no_data and c_idx == 7:
                        cell.font = Font(color='C00000', bold=True, size=9)

            # Blank spacer row between companies
            r += 1
            ws.row_dimensions[r].height = 6

        output = _io.BytesIO()
        wb.save(output)
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
        shortcode = request.args.get('shortcode', None)
        view_all = request.args.get('view_all', 'false').lower() == 'true'

        result = transaction_service.get_commission_till_balances(
            company_ids=company_ids, page=page, per_page=per_page,
            updated_after=updated_after, shortcode=shortcode, view_all=view_all
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        current_app.logger.error(f"Error fetching commission till balances: {e}")
        return jsonify({'error': str(e)}), 500


@transaction_bp.route('/sync-commission-balances', methods=['POST'])
@jwt_required()
def sync_commission_balances():
    """Bulk-sync AgentAccountBalance from the latest COMM- snapshots."""
    try:
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

        result = transaction_service.sync_all_commission_balances(company_ids=company_ids)
        return jsonify({'success': True, **result}), 200
    except Exception as e:
        current_app.logger.error(f"Error syncing commission balances: {e}")
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

        # Prefer Company.commission_balance — written directly from portal CSV export.
        from app.model.company import Company
        company = Company.query.filter_by(shortcode=shortcode).first()
        if company and company.commission_balance is not None:
            return jsonify({
                'success': True,
                'data': {
                    'balance': float(company.commission_balance),
                    'as_of': company.commission_balance_at.strftime('%Y-%m-%d %H:%M:%S') if company.commission_balance_at else None,
                    'source': 'portal_snapshot',
                }
            }), 200

        # Fallback: latest transaction ledger balance
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
                'as_of': row.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'transaction_ledger',
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

        # Use portal snapshot (commission_balance) when available per company,
        # fall back to the latest transaction ledger balance otherwise.
        if role in ('admin', 'administrator'):
            companies = Company.query.all()
        elif role == 'agent':
            companies = Company.query.filter_by(agent_user_id=current_user_id).all()
        else:
            companies = Company.query.filter_by(user_id=current_user_id).all()

        if not companies:
            return jsonify({'success': True, 'data': {'balance': 0.0, 'company_count': 0}}), 200

        shortcodes_needing_ledger = [
            c.shortcode for c in companies
            if c.commission_balance is None and c.shortcode
        ]

        snapshot_total = sum(
            float(c.commission_balance)
            for c in companies
            if c.commission_balance is not None
        )

        ledger_total = 0.0
        if shortcodes_needing_ledger:
            ledger_row = db.session.execute(
                text("""
                    SELECT COALESCE(SUM(latest.balance), 0) AS total
                    FROM (
                        SELECT DISTINCT ON (t.business_shortcode)
                            t.balance
                        FROM transactions t
                        WHERE t.transaction_type = 'commission'
                          AND t.business_shortcode = ANY(:shortcodes)
                          AND t.receipt_no NOT LIKE 'COMM-%'
                        ORDER BY t.business_shortcode, t.completion_time DESC, t.id DESC
                    ) latest
                """),
                {'shortcodes': shortcodes_needing_ledger}
            ).fetchone()
            ledger_total = float(ledger_row.total) if ledger_row else 0.0

        return jsonify({
            'success': True,
            'data': {
                'balance': snapshot_total + ledger_total,
                'company_count': len(companies),
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