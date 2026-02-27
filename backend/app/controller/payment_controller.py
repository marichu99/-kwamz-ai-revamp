from flask import Blueprint, jsonify, request, redirect, current_app
from app.model.payment import Payment
from app.utils.user_service import UserService
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.service.company_service import CompanyService
from app.service.billing_service import BillingService
from datetime import datetime, timedelta
from app.model.user import User
from app.model.company import Company
from app.model.pesalpalpayment import PesapalPayment
from app.model.pesapalipnconfig import PesapalIPNConfig
from app.model.subscription import Subscription
from app.model.config import SmtpConfig
from app import db

import os

payment_bp = Blueprint('payment', __name__)
company_service = CompanyService(db)


@payment_bp.route('/get-all-payments', methods=['GET'])
@jwt_required()
def get_all_payments():
    try:
        current_user_id = get_jwt_identity()
        current_user = UserService.get_user_by_id(user_id=current_user_id)

        payments_query = PesapalPayment.query.all()

        # Role-based filtering
        if current_user.role == 'admin':
            pass  # Admin sees all
        elif current_user.role == 'agent':
            companies_tied_to_agent = Company.query.filter_by(agent_user_id=current_user_id).all()
            company_user_ids = [company.user_id for company in companies_tied_to_agent if company.user_id is not None]
            payments_query = [x for x in payments_query if x.user_id in company_user_ids]
        else:
            # Regular user sees only their payments
            payments_query = [x for x in payments_query if x.user_id == current_user_id]

        if hasattr(PesapalPayment, 'created_at'):
            payments_query.sort(key=lambda x: x.created_at, reverse=True)
        else:
            payments_query.sort(key=lambda x: x.time_paid, reverse=True)

        payments_data = []
        for payment in payments_query:
            if hasattr(payment, 'to_dict'):
                payment_data = payment.to_dict()
            else:
                payment_data = {
                    'id': payment.id,
                    'user_id': payment.user_id,
                    'result_code': getattr(payment, 'result_code', None),
                    'time_paid': getattr(payment, 'time_paid', None).isoformat() if getattr(payment, 'time_paid', None) else None,
                    'amount': float(payment.amount) if payment.amount else 0.0,
                    'phone_number': getattr(payment, 'phone_number', None),
                    'checkout_id': getattr(payment, 'checkout_id', None),
                    'reference_code': getattr(payment, 'reference_code', None),
                    'result_desc': getattr(payment, 'result_desc', None),
                    'customer_email': getattr(payment, 'customer_email', None),
                    'customer_first_name': getattr(payment, 'customer_first_name', None),
                    'customer_last_name': getattr(payment, 'customer_last_name', None),
                    'currency': getattr(payment, 'currency', 'KES'),
                    'created_at': getattr(payment, 'created_at', getattr(payment, 'time_paid', None)).isoformat() if getattr(payment, 'created_at', getattr(payment, 'time_paid', None)) else None,
                    'checkout_request_id': getattr(payment, 'checkout_request_id', None),
                    'merchant_request_id': getattr(payment, 'merchant_request_id', None),
                    'confirmation_code': getattr(payment, 'confirmation_code', getattr(payment, 'reference_code', None)),
                    'payment_status': getattr(payment, 'payment_status', None),
                }

            if payment.user:
                companies, error = company_service.get_companies_by_userid(user_id=payment.user.id)

                user_data = {
                    'id': payment.user.id,
                    'username': payment.user.username,
                    'email': payment.user.email,
                    'companies': [{
                        'id': company["id"],
                        'company_name': company["company_name"],
                        'registration_number': company["company_number"],
                        'compliance_status': company["compliance_status"],
                        'total_float_balance': float(company["total_float_balance"]) if company["total_float_balance"] else 0.0,
                        'agent_user_id': company["agent_user_id"],
                    } for company in companies]
                }
                payment_data['user'] = user_data
            else:
                payment_data['user'] = None

            payments_data.append(payment_data)

        return jsonify({
            'success': True,
            'payments': payments_data,
            'count': len(payments_data),
            'user_role': current_user.role
        }), 200

    except Exception as e:
        import traceback
        print(f"Error in get_all_payments: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve payments',
            'error': str(e)
        }), 500


@payment_bp.route('/get-latest-payment', methods=['GET'])
@jwt_required()
def get_latest_payment():
    user_id = get_jwt_identity()

    user = UserService.get_user_by_id(user_id=user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    billing_status = BillingService.get_billing_status(user_id)

    return jsonify({
        'status': billing_status['status'],
        'user_id': user.id,
        'user_name': getattr(user, "username", ""),
        'user_created_at': user.created_at.isoformat() if user.created_at else None,
        'trial_end_date': billing_status.get('trial_end_date'),
        'trial_days_remaining': billing_status.get('trial_days_remaining', 0),
        'active_tills_count': billing_status.get('active_tills_count', 0),
        'amount_due': billing_status.get('amount_due', 0),
        'rate_per_till': billing_status.get('rate_per_till', 200),
        'subscription': billing_status.get('subscription'),
        'today_date': datetime.utcnow().date().isoformat()
    }), 200


@payment_bp.route('/billing-summary', methods=['GET'])
@jwt_required()
def billing_summary():
    user_id = get_jwt_identity()
    summary = BillingService.get_billing_summary(user_id)
    if not summary:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(summary), 200


@payment_bp.route('/create', methods=['POST'])
@jwt_required()
def create_payment():
    data = request.json
    current_user_id = get_jwt_identity()
    user = UserService.get_user_by_id(user_id=current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        # Create or get the subscription for the current billing period
        subscription = BillingService.create_subscription_for_current_period(current_user_id)

        # Use the subscription amount if not explicitly provided
        amount = data.get('amount') or float(subscription.amount_due)

        payment = current_app.payment_service.create_payment(
            user_id=current_user_id,
            amount=amount,
            currency=data.get('currency', 'KES'),
            description=data.get('description', f'Monthly subscription - {subscription.active_tills_count} active tills'),
            customer_email=data.get("customer_email") or user.email,
            customer_phone=data.get("customer_phone") or user.phone_number,
            customer_first_name=data.get("customer_first_name") or user.username,
            customer_last_name=data.get("customer_last_name") or user.username
        )

        # Link payment to subscription
        subscription.pesapal_payment_id = payment.id
        db.session.commit()

        return jsonify({
            'success': True,
            'merchant_reference': payment.merchant_reference,
            'redirect_url': payment.redirect_url,
            'order_id': payment.order_tracking_id,
            'subscription_id': subscription.id,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@payment_bp.route('/callback', methods=['POST'])
@jwt_required()
def payment_callback():
    print(f"Payment callback received with args: {request.args}")
    print(f"Payment request obj: {request.json}")
    data = request.json
    order_tracking_id = data.get('order_id')
    print("The order tracking id is ", order_tracking_id)
    if not order_tracking_id:
        return jsonify({'error': 'Missing order_id'}), 400

    current_user_id = get_jwt_identity()
    user = UserService.get_user_by_id(user_id=current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        payment = current_app.payment_service.update_payment_status(order_tracking_id)

        # If payment is completed, mark the linked subscription as paid
        if payment.is_paid and hasattr(payment, 'subscription') and payment.subscription:
            payment.subscription.mark_as_paid(pesapal_payment_id=payment.id)
            db.session.commit()

        return jsonify({
            'success': True,
            'payment': payment.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@payment_bp.route('/ipn', methods=['POST'])
def payment_ipn():
    order_tracking_id = request.args.get('OrderTrackingId')

    if order_tracking_id:
        try:
            payment = current_app.payment_service.process_ipn_callback(order_tracking_id)

            # If payment is completed, mark the linked subscription as paid
            if payment.is_paid and hasattr(payment, 'subscription') and payment.subscription:
                payment.subscription.mark_as_paid(pesapal_payment_id=payment.id)
                db.session.commit()

            return jsonify({'success': True, 'status': payment.payment_status})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

    return jsonify({'success': False, 'error': 'Missing OrderTrackingId'}), 400


@payment_bp.route('/status/<merchant_reference>')
def payment_status(merchant_reference):
    payment = current_app.payment_service.get_payment_by_merchant_reference(merchant_reference)

    if payment:
        return jsonify(payment.to_dict())

    return jsonify({'error': 'Payment not found'}), 404


@payment_bp.route('/admin/billing-status/<int:target_user_id>', methods=['GET'])
@jwt_required()
def admin_get_billing_status(target_user_id):
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized'}), 403

    summary = BillingService.get_billing_summary(target_user_id)
    if not summary:
        return jsonify({'error': 'User not found'}), 404

    billing_status = BillingService.get_billing_status(target_user_id)
    target_user = UserService.get_user_by_id(user_id=target_user_id)

    return jsonify({
        'success': True,
        'user': {
            'id': target_user.id,
            'username': target_user.username,
            'email': target_user.email,
            'created_at': target_user.created_at.isoformat() if target_user.created_at else None,
        },
        'billing': billing_status,
        'summary': summary,
    }), 200


@payment_bp.route('/admin/update-status/<int:target_user_id>', methods=['PATCH'])
@jwt_required()
def admin_update_payment_status(target_user_id):
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role not in ('admin', 'administrator'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    new_status = data.get('status')  # PAID or PENDING

    if new_status not in ('PAID', 'PENDING'):
        return jsonify({'error': 'Status must be PAID or PENDING'}), 400

    target_user = UserService.get_user_by_id(user_id=target_user_id)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404

    try:
        subscription = BillingService.create_subscription_for_current_period(target_user_id)

        if new_status == 'PAID':
            subscription.mark_as_paid()
        else:
            subscription.status = 'PENDING'
            subscription.paid_at = None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Subscription status updated to {new_status}',
            'subscription': subscription.to_dict(),
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@payment_bp.route('/admin/ipn-configs', methods=['GET'])
@jwt_required()
def admin_list_ipn_configs():
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    configs = PesapalIPNConfig.query.order_by(PesapalIPNConfig.created_at.desc()).all()
    return jsonify({'success': True, 'configs': [c.to_dict() for c in configs]})


@payment_bp.route('/admin/ipn-configs/register', methods=['POST'])
@jwt_required()
def admin_register_ipn():
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    data = request.json or {}
    ipn_url = data.get('ipn_url', '').strip()
    ipn_notification_type = data.get('ipn_notification_type', 'GET')

    if not ipn_url:
        return jsonify({'success': False, 'error': 'ipn_url is required'}), 400

    try:
        response = current_app.pesapal_client.ipn.register_ipn(ipn_url, ipn_notification_type)
        return jsonify({'success': True, 'data': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@payment_bp.route('/admin/ipn-configs/<int:config_id>/activate', methods=['POST'])
@jwt_required()
def admin_activate_ipn_config(config_id):
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    config = PesapalIPNConfig.query.get(config_id)
    if not config:
        return jsonify({'success': False, 'error': 'IPN config not found'}), 404

    PesapalIPNConfig.query.filter(PesapalIPNConfig.id != config_id).update({'is_active': False})
    config.is_active = True
    db.session.commit()
    return jsonify({'success': True, 'data': config.to_dict()})


@payment_bp.route('/admin/ipn-configs/<int:config_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_ipn_config(config_id):
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    config = PesapalIPNConfig.query.get(config_id)
    if not config:
        return jsonify({'success': False, 'error': 'IPN config not found'}), 404

    config.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'IPN config deactivated'})


@payment_bp.route('/admin/pesapal-config', methods=['GET'])
@jwt_required()
def admin_get_pesapal_config():
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    smtp = SmtpConfig.get_global()
    live_client = current_app.pesapal_client
    return jsonify({
        'success': True,
        'data': {
            'callback_url': smtp.pesapal_callback_url or live_client.config.callback_url or '',
            'environment': smtp.pesapal_environment or live_client.config.environment or 'SANDBOX',
        }
    })


@payment_bp.route('/admin/pesapal-config', methods=['PUT'])
@jwt_required()
def admin_update_pesapal_config():
    current_user_id = get_jwt_identity()
    current_user = UserService.get_user_by_id(user_id=current_user_id)
    if not current_user or current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403

    data = request.json or {}
    smtp = SmtpConfig.get_global()

    if 'callback_url' in data:
        smtp.pesapal_callback_url = data['callback_url'].strip()
        current_app.pesapal_client.config.callback_url = smtp.pesapal_callback_url
    if 'environment' in data and data['environment'] in ('SANDBOX', 'PRODUCTION'):
        smtp.pesapal_environment = data['environment']
        current_app.pesapal_client.config.environment = smtp.pesapal_environment

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Pesapal configuration updated',
        'data': {
            'callback_url': smtp.pesapal_callback_url,
            'environment': smtp.pesapal_environment,
        }
    })


@payment_bp.route('/refund', methods=['POST'])
def refund_payment():
    data = request.json

    try:
        refund = current_app.payment_service.initiate_refund(
            payment_id=data['payment_id'],
            refund_amount=data['refund_amount'],
            initiated_by=data['initiated_by'],
            remarks=data.get('remarks')
        )

        return jsonify({
            'success': True,
            'refund_id': refund.id,
            'status': refund.refund_status
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
