import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, func
from app.model.fraud_alert import FraudAlert
from app.service.agentcompany_service import AgentCompanyService

logger = logging.getLogger(__name__)

fraud_alert_bp = Bluelogger.info('fraud_alert', __name__, url_prefix='/alerts')

agent_company_service = AgentCompanyService()


@fraud_alert_bp.route('/by-agent-company', methods=['GET'])
@jwt_required()
def get_alerts_by_agent_company():
    """Get fraud alerts grouped by agent company with their latest N alerts."""
    user_id = get_jwt_identity()
    limit = min(int(request.args.get('limit', 5)), 20)

    # try:
    companies_list, error = agent_company_service.get_all_agent_companies_by_userid(user_id)

    if error:
        return jsonify({'success': False, 'error': error}), 500

    results = []
    for company in companies_list:
        # Get shortcodes to match against detection_details
        shortcodes = set()
        sc = company.get('short_code')
        if sc:
            shortcodes.add(str(sc))
        bsc = company.get('business_short_code')
        if bsc:
            shortcodes.add(str(bsc))

        if not shortcodes:
            continue

        # Query fraud alerts matching any of this company's shortcodes
        # Use PostgreSQL json_extract_path_text for JSON (not JSONB) columns
        shortcode_filters = []
        for code in shortcodes:
            shortcode_filters.append(
                func.json_extract_path_text(
                    FraudAlert.detection_details, 'business_shortcode'
                ) == code
            )

        alerts_query = (
            FraudAlert.query
            .filter(FraudAlert.user_id == user_id)
            .filter(or_(*shortcode_filters))
            .order_by(FraudAlert.created_at.desc())
        )

        total_alerts = alerts_query.count()
        alerts = alerts_query.limit(limit).all()

        # Determine highest risk level across alerts
        risk_levels = [a.risk_level for a in alerts]
        if 'HIGH' in risk_levels:
            company_risk = 'HIGH'
        elif 'MEDIUM' in risk_levels:
            company_risk = 'MEDIUM'
        elif risk_levels:
            company_risk = 'LOW'
        else:
            company_risk = None

        results.append({
            'agent_company': {
                'id': company.get('id'),
                'company_name': company.get('company_name'),
                'short_code': company.get('short_code'),
                'business_short_code': company.get('business_short_code'),
                'location': company.get('location'),
                'status': company.get('status'),
                'user_agents': company.get('user_agents', []),
            },
            'fraud_alerts': [a.to_dict() for a in alerts],
            'total_alerts': total_alerts,
            'fraud_risk': company_risk,
        })

    # Sort by total_alerts descending so most-alerted companies appear first
    results.sort(key=lambda x: x['total_alerts'], reverse=True)

    return jsonify({
        'success': True,
        'data': results,
    })

    # except Exception as e:
    #     return jsonify({
    #         'success': False,
    #         'error': str(e),
    #     }), 500


@fraud_alert_bp.route('/', methods=['GET'])
@jwt_required()
def get_alerts():
    """Get paginated fraud alerts for the authenticated user."""
    user_id = get_jwt_identity()
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    risk_level = request.args.get('risk_level')
    fraud_type = request.args.get('fraud_type')

    try:
        query = FraudAlert.query.filter(FraudAlert.user_id == user_id)

        if risk_level:
            query = query.filter(FraudAlert.risk_level == risk_level.upper())
        if fraud_type:
            query = query.filter(FraudAlert.fraud_type == fraud_type)

        query = query.order_by(FraudAlert.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'success': True,
            'data': [a.to_dict() for a in pagination.items],
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
