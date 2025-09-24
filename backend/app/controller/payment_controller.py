from flask import Blueprint, jsonify, request
from app.model.payment import Payment
from app.utils.user_service import UserService
from flask_jwt_extended import jwt_required,get_jwt_identity

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