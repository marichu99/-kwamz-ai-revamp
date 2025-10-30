from app import db
from datetime import datetime
from typing import Optional, Dict
from app.enums.paymentstatus import PaymentStatus
from app.model.pesapalipnconfig import PesapalIPNConfig
from app.model.pesalpalpayment import PesapalPayment
from app.model.pesapalrefund import PesapalRefund
from app.utils.pesapalclient import PesapalClient

# ============================================================================
# Flask-SQLAlchemy Storage Implementation
# ============================================================================

from typing import Optional, Dict, List

# ============================================================================
# Integrated Payment Service
# ============================================================================

class PesapalPaymentService:
    """Service class to handle Pesapal payments with database integration"""
    
    def __init__(self, pesapal_client:Optional[PesapalClient] = None):
        """
        Initialize payment service
        
        Args:
            pesapal_client: Instance of PesapalClient from utils
        """
        self.client = pesapal_client
    
    def create_payment(
        self,
        user_id: Optional[int],
        amount: float,
        currency: str,
        description: str,
        customer_email: str,
        customer_phone: str,
        customer_first_name: str,
        customer_last_name: str,
        merchant_reference: Optional[str] = None
    ) -> PesapalPayment:
        """
        Create a new payment record and submit to Pesapal
        
        Returns:
            PesapalPayment: Created payment record with redirect_url
        """
        # Generate unique merchant reference if not provided
        if not merchant_reference:
            merchant_reference = f"ORDER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{user_id or 'GUEST'}"
        
        # Create payment record in database
        payment = PesapalPayment(
            user_id=user_id,
            merchant_reference=merchant_reference,
            amount=amount,
            currency=currency,
            description=description,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_first_name=customer_first_name,
            customer_last_name=customer_last_name,
            payment_status=PaymentStatus.PENDING.value
        )
        
        try:
            # Submit order to Pesapal
            response = self.client.payment.submit_order(
                merchant_reference=merchant_reference,
                amount=amount,
                currency=currency,
                description=description,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_first_name=customer_first_name,
                customer_last_name=customer_last_name
            )
            
            # Update payment record with Pesapal response
            payment.order_tracking_id = response.get('order_tracking_id')
            payment.redirect_url = response.get('redirect_url')
            payment.status_code = response.get('status')
            payment.callback_data = response
            
            db.session.add(payment)
            db.session.commit()
            
            return payment
            
        except Exception as e:
            payment.payment_status = PaymentStatus.FAILED.value
            payment.error_message = str(e)
            db.session.add(payment)
            db.session.commit()
            raise
    
    def update_payment_status(self, order_tracking_id: str) -> PesapalPayment:
        """
        Update payment status from Pesapal API
        
        Args:
            order_tracking_id: Pesapal order tracking ID
        
        Returns:
            PesapalPayment: Updated payment record
        """
        payment = PesapalPayment.query.filter_by(
            order_tracking_id=order_tracking_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment not found for order_tracking_id: {order_tracking_id}")
        
        try:
            # Get status from Pesapal
            status_response = self.client.payment.get_transaction_status(order_tracking_id)
            
            # Update payment record
            payment_status = status_response.get('payment_status_description', '').upper()
            
            if payment_status == 'COMPLETED':
                payment.mark_as_paid(
                    confirmation_code=status_response.get('confirmation_code'),
                    payment_method=status_response.get('payment_method')
                )
            elif payment_status == 'FAILED':
                payment.mark_as_failed(status_response.get('message', 'Payment failed'))
            else:
                payment.payment_status = payment_status
            
            payment.status_code = status_response.get('status_code')
            payment.payment_status_description = status_response.get('payment_status_description')
            payment.ipn_data = status_response
            
            db.session.commit()
            
            return payment
            
        except Exception as e:
            payment.error_message = str(e)
            db.session.commit()
            raise
    
    def process_ipn_callback(self, order_tracking_id: str) -> PesapalPayment:
        """
        Process IPN callback from Pesapal
        
        Args:
            order_tracking_id: Order tracking ID from IPN callback
        
        Returns:
            PesapalPayment: Updated payment record
        """
        return self.update_payment_status(order_tracking_id)
    
    def get_payment_by_merchant_reference(self, merchant_reference: str) -> Optional[PesapalPayment]:
        """Get payment by merchant reference"""
        return PesapalPayment.query.filter_by(
            merchant_reference=merchant_reference
        ).first()
    
    def get_payment_by_order_tracking_id(self, order_tracking_id: str) -> Optional[PesapalPayment]:
        """Get payment by order tracking ID"""
        return PesapalPayment.query.filter_by(
            order_tracking_id=order_tracking_id
        ).first()
    
    def get_user_payments(self, user_id: int, status: Optional[str] = None) -> List[PesapalPayment]:
        """Get all payments for a user"""
        query = PesapalPayment.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(payment_status=status)
        return query.order_by(PesapalPayment.created_at.desc()).all()
    
    def initiate_refund(
        self,
        payment_id: int,
        refund_amount: float,
        initiated_by: str,
        remarks: Optional[str] = None
    ) -> PesapalRefund:
        """
        Initiate a refund for a payment
        
        Args:
            payment_id: ID of the payment to refund
            refund_amount: Amount to refund
            initiated_by: Username of person initiating refund
            remarks: Optional refund remarks
        
        Returns:
            PesapalRefund: Created refund record
        """
        payment = PesapalPayment.query.get(payment_id)
        
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        
        if not payment.is_paid:
            raise ValueError("Cannot refund a payment that is not completed")
        
        if not payment.confirmation_code:
            raise ValueError("Payment has no confirmation code")
        
        # Determine refund type
        refund_type = 'FULL' if refund_amount >= payment.amount else 'PARTIAL'
        
        # Create refund record
        refund = PesapalRefund(
            payment_id=payment_id,
            confirmation_code=payment.confirmation_code,
            refund_amount=refund_amount,
            refund_type=refund_type,
            initiated_by=initiated_by,
            remarks=remarks,
            refund_status='PENDING'
        )
        
        try:
            # Submit refund to Pesapal
            response = self.client.payment.refund_transaction(
                confirmation_code=payment.confirmation_code,
                amount=refund_amount,
                username=initiated_by,
                remarks=remarks
            )
            
            refund.response_data = response
            refund.refund_status = 'COMPLETED'
            refund.processed_at = datetime.utcnow()
            
            # Update payment status if full refund
            if refund_type == 'FULL':
                payment.payment_status = PaymentStatus.REVERSED.value
            
            db.session.add(refund)
            db.session.commit()
            
            return refund
            
        except Exception as e:
            refund.refund_status = 'FAILED'
            refund.error_message = str(e)
            db.session.add(refund)
            db.session.commit()
            raise


# ============================================================================
# Usage Example
# ============================================================================

"""
# In your Flask app initialization (app/__init__.py or similar):

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pesapal_utils import PesapalClient, PesapalConfig

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/dbname'
db = SQLAlchemy(app)

# Initialize Pesapal client with storage
from models import FlaskIPNStorage

ipn_storage = FlaskIPNStorage()
pesapal_client = PesapalClient(ipn_storage=ipn_storage)

# Initialize IPN (do this once)
pesapal_client.initialize()

# Create payment service
payment_service = PesapalPaymentService(pesapal_client)


# In your routes (app/routes/payment.py):

from flask import request, jsonify, redirect
from models import payment_service

@app.route('/payment/create', methods=['POST'])
def create_payment():
    data = request.json
    
    try:
        payment = payment_service.create_payment(
            user_id=data.get('user_id'),
            amount=data['amount'],
            currency=data.get('currency', 'KES'),
            description=data['description'],
            customer_email=data['customer_email'],
            customer_phone=data['customer_phone'],
            customer_first_name=data['customer_first_name'],
            customer_last_name=data['customer_last_name']
        )
        
        # Redirect user to Pesapal payment page
        return jsonify({
            'success': True,
            'merchant_reference': payment.merchant_reference,
            'redirect_url': payment.redirect_url
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/payment/callback')
def payment_callback():
    # User is redirected here after payment
    order_tracking_id = request.args.get('OrderTrackingId')
    
    if order_tracking_id:
        try:
            payment = payment_service.update_payment_status(order_tracking_id)
            
            if payment.is_paid:
                return redirect(f'/payment/success?ref={payment.merchant_reference}')
            else:
                return redirect(f'/payment/failed?ref={payment.merchant_reference}')
        except Exception as e:
            return redirect('/payment/error')
    
    return redirect('/payment/error')


@app.route('/payment/ipn', methods=['GET'])
def payment_ipn():
    # Pesapal sends IPN notification here
    order_tracking_id = request.args.get('OrderTrackingId')
    
    if order_tracking_id:
        try:
            payment = payment_service.process_ipn_callback(order_tracking_id)
            return jsonify({'success': True, 'status': payment.payment_status})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    return jsonify({'success': False, 'error': 'Missing OrderTrackingId'}), 400


@app.route('/payment/status/<merchant_reference>')
def payment_status(merchant_reference):
    payment = payment_service.get_payment_by_merchant_reference(merchant_reference)
    
    if payment:
        return jsonify(payment.to_dict())
    
    return jsonify({'error': 'Payment not found'}), 404


@app.route('/payment/refund', methods=['POST'])
def refund_payment():
    data = request.json
    
    try:
        refund = payment_service.initiate_refund(
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
"""