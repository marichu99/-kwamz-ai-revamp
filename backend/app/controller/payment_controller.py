from flask import Blueprint, jsonify, request,redirect,current_app
from app.model.payment import Payment
from app.utils.user_service import UserService
from flask_jwt_extended import jwt_required,get_jwt_identity
from app.service.company_service import CompanyService
from datetime import datetime,timedelta
from app.model.user import User
from app.model.company import Company
from app.model.pesalpalpayment import PesapalPayment
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
        
        # Determine which payment model to use based on your needs
        # Option 1: Use Payment model (original)
        # payments_query = PesapalPayment.query.options(db.joinedload(PesapalPayment.user).joinedload(User.companies))
        
        # Option 2: Use PesapalPayment model (if that's your main payment table)
        payments_query = PesapalPayment.query.all()
        
        # Role-based filtering
        if current_user.role == 'admin':
            pass  # Admin sees all
        elif current_user.role == 'agent':
            
            companies_tied_to_agent = Company.query.filter_by(agent_user_id=current_user_id).all()
            company_user_ids = [company.user_id for company in companies_tied_to_agent if company.user_id is not None]
            
            # For PesapalPayment model (if using that instead):
            payments_query = [x for x in payments_query if x.user_id in company_user_ids] 
            # payments_query.filter(PesapalPayment.user_id.in_(agent_user_ids))
        else:
            # Regular user sees only their payments
            payments_query = payments_query.filter(PesapalPayment.user_id == current_user_id)
            # For PesapalPayment: payments_query = payments_query.filter(PesapalPayment.user_id == current_user_id)
        
        if hasattr(PesapalPayment, 'created_at'):
            payments_query.sort(key=lambda x: x.created_at, reverse=True)
        else:
            payments_query.sort(key=lambda x: x.time_paid, reverse=True)
        

        payments_data = []
        for payment in payments_query:
            # Handle both Payment and PesapalPayment models
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
                    'payment_status': getattr(payment, 'payment_status', None),  # For PesapalPayment
                }
            
            # Add user and company information
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

    # Get the logged-in user
    user = UserService.get_user_by_id(user_id=user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Get the latest payment for this user
    latest_payment = Payment.query.filter(
        Payment.user_id == user_id
    ).order_by(Payment.time_paid.desc()).first()

    today = datetime.utcnow().date()
    status = 'NOT_PAID'
    last_payment_date = None
    trial_end_date = None

    # --- Step 1: Handle the one-month free trial logic ---
    if hasattr(user, 'created_at') and user.created_at:
        user_creation_date = user.created_at.date()
        trial_end_date = user_creation_date + timedelta(days=30)

        # If user is within 30 days since account creation → free trial (PAID)
        if today <= trial_end_date:
            status = 'PAID'
    
    # --- Step 2: If not in free trial, check latest payment ---
    if status != 'PAID' and latest_payment:
        last_payment_date = latest_payment.time_paid.date() if latest_payment.time_paid else None
        if last_payment_date and last_payment_date == today:
            status = 'PAID'

    # --- Step 3: Build response payload ---
    return jsonify({
        'status': status,
        'user_id': user.id,
        'user_name': getattr(user, "username", ""),
        'user_created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
        'trial_end_date': trial_end_date.isoformat() if trial_end_date else None,
        'payment_id': latest_payment.id if latest_payment else None,
        'reference_code': getattr(latest_payment, "reference_code", None),
        'phone_number': getattr(latest_payment, "phone_number", None),
        'time_paid': latest_payment.time_paid.isoformat() if latest_payment and latest_payment.time_paid else None,
        'last_payment_date': last_payment_date.isoformat() if last_payment_date else None,
        'today_date': today.isoformat()
    }), 200
    
@payment_bp.route('/create', methods=['POST'])
@jwt_required()
def create_payment():
    data = request.json
    current_user_id = get_jwt_identity()
    user = UserService.get_user_by_id(user_id=current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        payment = current_app.payment_service.create_payment(
            user_id=current_user_id,
            amount=data['amount'],
            currency=data.get('currency', 'KES'),
            description=data['description'],
            customer_email=data["customer_email"] or user.email,
            customer_phone=data["customer_phone"] or user.phone_number,
            customer_first_name=data["customer_first_name"] or user.username,
            customer_last_name=data["customer_last_name"] or   user.username
        )
        
        # Redirect user to Pesapal payment page
        return jsonify({
            'success': True,
            'merchant_reference': payment.merchant_reference,
            'redirect_url': payment.redirect_url,
            'order_id': payment.order_tracking_id,
        })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@payment_bp.route('/callback', methods=['POST'])
@jwt_required()
def payment_callback():
    # User is redirected here after payment
    print(f"Payment callback received with args: {request.args}")
    print(f"Payment request obj: {request.json}")
    data = request.json
    order_tracking_id = data.get('order_id')
    print("The order tracking id is ",order_tracking_id)
    if not order_tracking_id:
        return jsonify({'error': 'User not found'}), 404
    
    current_user_id = get_jwt_identity()
    user = UserService.get_user_by_id(user_id=current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    else:
        try:
            payment = current_app.payment_service.update_payment_status(order_tracking_id)
            
            # if payment.is_paid:
            #     return redirect(f'/payment/success?ref={payment.merchant_reference}')
            # else:
            #     return redirect(f'/payment/failed?ref={payment.merchant_reference}')
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
                'success': True,
                'payment': payment.to_dict()                
            })


@payment_bp.route('/ipn', methods=['POST'])
def payment_ipn():
    # Pesapal sends IPN notification here
    order_tracking_id = request.args.get('OrderTrackingId')
    
    if order_tracking_id:
        try:
            payment = current_app.payment_service.process_ipn_callback(order_tracking_id)
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