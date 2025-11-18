from flask import Blueprint, jsonify, request,redirect,current_app
from app.model.payment import Payment
from app.utils.user_service import UserService
from flask_jwt_extended import jwt_required,get_jwt_identity
from datetime import datetime,timedelta

import os

payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/get-payments', methods=['GET'])
@jwt_required()
def get_payments():
    try:
        user_id = get_jwt_identity()
        payments = current_app.payment_service.get_user_payments(user_id=user_id)

        print(f"The payments size is {len(payments)}")
        
        return jsonify({
            'success': True,
            'payments': [payment.to_dict() for payment in payments],
            'count': len(payments)
        }), 200
        
    except Exception as e:
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