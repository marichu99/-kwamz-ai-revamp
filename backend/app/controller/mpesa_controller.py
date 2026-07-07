import logging
from flask import Flask,Blueprint, jsonify, request
from app.service.mpesa_service import MpesaService
from app.service.payments_service import PaymentService
from app.service.b2c_payout_service import B2CPayoutService
from app.model.payment import Payment
from flask_cors import CORS
from flask_jwt_extended import jwt_required,get_jwt_identity
from datetime import datetime
import time
from app import db, limiter

logger = logging.getLogger(__name__)

mpesa_bp = Blueprint('mpesa', __name__)
app = Flask(__name__)


CORS(app)  # Enable CORS for all routes

@mpesa_bp.route('/stkpush', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def stkpush():
    user_id = get_jwt_identity()
    logger.info(f"The logged in user id is {user_id}")
    data = request.get_json()
    phone = data.get('phone_number')
    amount = data.get('amount')
    mpesa = MpesaService()
    response = mpesa.stk_push_simulation(phone_number=phone, amount=int(amount),user_id=user_id)
    # time.sleep(6)
    
    return jsonify(response)

@mpesa_bp.route('/path', methods=['POST'])
def path():
    mpesa = MpesaService()
    data = request.get_json()
    checkout_request_id = data.get('checkoutRequestID')
    token = data.get('token')

    if not checkout_request_id or not token:
        return jsonify({"error": "Missing required parameters"}), 400

    response = mpesa.path(checkout_request_id, token)
    return jsonify(response)

@mpesa_bp.route("/transaction-status/<checkout_id>", methods=["GET"])
@jwt_required()
def transaction_status(checkout_id):
    payments = PaymentService.getByCriteria(checkout_id=checkout_id)
    user_id = get_jwt_identity()

    updated_payments = []
    for payment in payments:
        payment.user_id = user_id
        db.session.add(payment)
        updated_payments.append({
            "result_desc": payment.result_desc,
            "result_code": payment.result_code,
            "user_id": payment.user_id
        })
    
    db.session.commit()

    return jsonify(updated_payments),200


@mpesa_bp.route("/callback", methods=["POST"])
@limiter.limit("60 per minute")
def mpesa_callback():
    data = request.json

    stk_callback = data["Body"]["stkCallback"]

    # Default values
    amount = None
    phone_number = None
    reference_code = None
    time_paid = None

    # Only present on successful payment (ResultCode == 0)
    metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
    if metadata:
        parsed = {item["Name"]: item.get("Value") for item in metadata}
        amount = parsed.get("Amount")
        phone_number = parsed.get("PhoneNumber")
        reference_code = parsed.get("MpesaReceiptNumber")
        transaction_date = parsed.get("TransactionDate")

        if transaction_date:
            time_paid = datetime.strptime(str(transaction_date), "%Y%m%d%H%M%S")
    if reference_code ==None:
        reference_code ="PAY_FAILED"

    logger.info(f"he reference code is {reference_code}")

    # Save to DB anyway (even if cancelled/failed)
    payment = Payment(
        checkout_id=stk_callback["CheckoutRequestID"],
        result_code=stk_callback["ResultCode"],
        result_desc=stk_callback["ResultDesc"],
        amount=amount or 0,  # fallback to 0 if missing
        phone_number=phone_number,
        reference_code=reference_code,
        time_paid=time_paid
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({"status": "ok"}), 200


# ─── B2C Payout Endpoints ───────────────────────────────────────────

@mpesa_bp.route('/b2c/payout', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def initiate_b2c_payout():
    user_id = get_jwt_identity()
    data = request.get_json()
    swap_id = data.get('swap_id')

    if not swap_id:
        return jsonify({"error": "swap_id is required"}), 400

    try:
        service = B2CPayoutService()
        payouts = service.initiate_swap_payout(swap_id=swap_id, user_id=user_id)
        return jsonify({"message": "Payout initiated", "payouts": payouts}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"B2C payout error: {e}")
        return jsonify({"error": "Failed to initiate payout"}), 500


@mpesa_bp.route('/b2c/result', methods=['POST'])
@limiter.limit("60 per minute")
def b2c_result_callback():
    data = request.json

    try:
        service = B2CPayoutService()
        service.process_b2c_result(data)
    except Exception as e:
        logger.error(f"B2C result processing error: {e}")

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


@mpesa_bp.route('/b2c/timeout', methods=['POST'])
@limiter.limit("60 per minute")
def b2c_timeout_callback():
    data = request.json

    try:
        service = B2CPayoutService()
        service.process_b2c_timeout(data)
    except Exception as e:
        logger.error(f"B2C timeout processing error: {e}")

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


@mpesa_bp.route('/b2c/payouts/<int:swap_id>', methods=['GET'])
@jwt_required()
def get_swap_payouts(swap_id):
    try:
        service = B2CPayoutService()
        payouts = service.get_payouts_by_swap(swap_id)
        return jsonify(payouts), 200
    except Exception as e:
        logger.error(f"Error fetching payouts: {e}")
        return jsonify({"error": "Failed to fetch payouts"}), 500

