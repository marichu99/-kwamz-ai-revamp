from flask import Blueprint, jsonify, request
from app.model.payment import Payment
from app.utils.user_service import UserService
from flask_jwt_extended import jwt_required,get_jwt_identity
from datetime import datetime,timedelta

import os

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/get-payments', methods=['GET'])
@jwt_required()
def get_kyc():
    user_id = get_jwt_identity()
    payments = Payment.query.filter(Payment.user_id == user_id).all()

    print(f"The payments size is {len(payments)}")    
    return jsonify([{
        'id': payment.id,
        'reference_code': payment.reference_code,
        'phone_number': payment.phone_number,
        'user_name': getattr(UserService.get_user_by_id(user_id=payment.user_id), "username", "") if payment.user_id else "",
        'time_paid': payment.time_paid.isoformat() if payment.time_paid else ""
    } for payment in payments])
    
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