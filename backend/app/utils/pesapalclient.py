import requests
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import base64
import hashlib
import hmac
from urllib.parse import urlencode
from dotenv import load_dotenv
from app.utils.flaskipnstorage import FlaskIPNStorage
import os

# Load environment variables
load_dotenv()

class PesapalConfig:
    """Pesapal configuration class"""
    
    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        base_url: str = "https://pay.pesapal.com/v3",
        callback_url: Optional[str] = None,
        ipn_url: Optional[str] = None,
        environment: str = "SANDBOX"
    ):
        self.consumer_key = consumer_key or os.getenv('PESAPAL_CONSUMER_KEY')
        if not self.consumer_key:
            raise ValueError("PESAPAL_CONSUMER_KEY is required")
        self.consumer_secret = consumer_secret or os.getenv('PESAPAL_CONSUMER_SECRET')
        if not self.consumer_secret:
            raise ValueError("PESAPAL_CONSUMER_SECRET is required")
        self.base_url = base_url
        self.callback_url = callback_url or "https://5f148dc78026.ngrok-free.app/payment/callback"
        self.ipn_url = ipn_url or "https://5f148dc78026.ngrok-free.app/payment/ipn"
        self.environment = environment
        self._access_token = None
        self._token_expiry = None

class PaymentService:
    """Handles payment operations"""
    
    def __init__(self, client: 'PesapalClient'):
        self.client = client
    
    def submit_order(
        self,
        merchant_reference: str,
        amount: float,
        currency: str,
        description: str,
        customer_email: str,
        customer_phone: Optional[str] = None,
        customer_first_name: Optional[str] = None,
        customer_last_name: Optional[str] = None,
        callback_url: Optional[str] = None,
        cancellation_url: Optional[str] = None,
        notification_id: Optional[str] = None,
        branch: Optional[str] = None,
        billing_address: Optional[Dict] = None
    ) -> Dict:
        """
        Submit order to Pesapal
        
        Args:
            merchant_reference: Unique order reference
            amount: Payment amount
            currency: Currency code (KES, USD, etc.)
            description: Order description
            customer_email: Customer email
            customer_phone: Customer phone number
            customer_first_name: Customer first name
            customer_last_name: Customer last name
            callback_url: Callback URL after payment
            cancellation_url: Cancellation URL
            notification_id: IPN notification ID
            branch: Branch information
            billing_address: Billing address details
        
        Returns:
            Dict: Response from Pesapal API
        """
        # Use default callback URL if not provided
        if not callback_url and self.client.config.callback_url:
            callback_url = self.client.config.callback_url
        
        # Use registered IPN if no notification_id provided
        if not notification_id and self.client.ipn_storage:
            print("No notification ID provided, checking registered IPNs...")
            ipn_configs = self.client.ipn_storage.list_ipn_configs()
            if ipn_configs:
                print(f"Found {len(ipn_configs)} registered IPN configurations.")
                for config in ipn_configs:
                    print(f"Found IPN config: {config}")
                    print(f"IPN URL: {config.get('ipn_url')}")
                    print(f"IPN ID: {config.get('notification_id')}")
                notification_id = ipn_configs[0].get('notification_id')
        
        print("We are trying to make a payment with the following details:")
        print(f"The callback URL is: {callback_url}")
        print(f"The notification id is: {notification_id}")
        
        order_data = {
            "id": merchant_reference,
            "currency": currency,
            "amount": amount,
            "description": description,
            "callback_url": callback_url,
            "notification_id": notification_id,
            "cancellation_url": cancellation_url or callback_url,
            "branch": branch,
            "billing_address": billing_address or {
                "email_address": customer_email,
                "phone_number": customer_phone or "",
                "first_name": customer_first_name or "",
                "last_name": customer_last_name or ""
            }
        }
        
        
        # Remove None values
        order_data = {k: v for k, v in order_data.items() if v is not None}
        
        return self.client._make_request("POST", "/api/Transactions/SubmitOrderRequest", order_data)
    
    def get_transaction_status(self, order_tracking_id: str) -> Dict:
        """
        Get transaction status from Pesapal
        
        Args:
            order_tracking_id: Pesapal order tracking ID
        
        Returns:
            Dict: Transaction status details
        """
        return self.client._make_request(
            "GET", 
            f"/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
        )
    
    def get_transaction_status_by_merchant_ref(self, merchant_reference: str) -> Dict:
        """
        Get transaction status by merchant reference
        
        Args:
            merchant_reference: Merchant reference ID
        
        Returns:
            Dict: Transaction status details
        """
        return self.client._make_request(
            "GET", 
            f"/api/Transactions/GetTransactionStatus?merchantReference={merchant_reference}"
        )
    
    def refund_transaction(
        self,
        confirmation_code: str,
        amount: float,
        username: str,
        remarks: Optional[str] = None
    ) -> Dict:
        """
        Refund a transaction
        
        Args:
            confirmation_code: Transaction confirmation code
            amount: Refund amount
            username: Username initiating refund
            remarks: Refund remarks
        
        Returns:
            Dict: Refund response
        """
        refund_data = {
            "confirmationCode": confirmation_code,
            "amount": amount,
            "username": username,
            "remarks": remarks or f"Refund initiated by {username}"
        }
        
        return self.client._make_request("POST", "/api/Transactions/RefundRequest", refund_data)

class IPNService:
    """Handles Instant Payment Notification operations"""
    
    def __init__(self, client: 'PesapalClient'):
        self.client = client
    
    def register_ipn(self, ipn_url: str, ipn_notification_type: str = "GET") -> Dict:
        """
        Register IPN URL with Pesapal
        
        Args:
            ipn_url: The IPN URL to register
            ipn_notification_type: GET or POST
        
        Returns:
            Dict: IPN registration response
        """
        ipn_data = {
            "url": ipn_url,
            "ipn_notification_type": ipn_notification_type
        }
        
        response = self.client._make_request("POST", "/api/URLSetup/RegisterIPN", ipn_data)
        
        # Save IPN config to storage if available
        if self.client.ipn_storage and response.get('ipn_id'):
            self.client.ipn_storage.save_ipn_config(
                url=ipn_url,
                notification_id=response['ipn_id'],
                response_data=response
            )
        
        return response
    
    def get_ipn_list(self) -> Dict:
        """Get list of registered IPNs"""
        return self.client._make_request("GET", "/api/URLSetup/GetIpnList")

class PesapalClient:
    """Main Pesapal API client"""
    
    def __init__(self, config: PesapalConfig, ipn_storage : Optional[FlaskIPNStorage] = None):
        """
        Initialize Pesapal client
        
        Args:
            config: Pesapal configuration
            ipn_storage: Storage implementation for IPN configs
        """
        self.config = config
        self.ipn_storage = ipn_storage
        self.payment = PaymentService(self)
        self.ipn = IPNService(self)
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def initialize(self, ipn_url: Optional[str] = None) -> None:
        """
        Initialize the client and register IPN if needed
        
        Args:
            ipn_url: IPN URL to register (uses config.ipn_url if not provided)
        """
        # Get access token
        self._authenticate()
        
        # Register IPN if URL is provided and storage is available
        if self.ipn_storage:
            ipn_url = ipn_url or self.config.ipn_url
            if ipn_url:
                # Check if IPN is already registered
                existing_config = self.ipn_storage.get_ipn_config(ipn_url)
                if not existing_config:
                    try:
                        self.ipn.register_ipn(ipn_url)
                        print(f"IPN registered successfully: {ipn_url}")
                    except Exception as e:
                        print(f"Failed to register IPN: {e}")
            else:
                print("No IPN URL provided, skipping registration.")
    
    def _authenticate(self) -> None:
        """Authenticate with Pesapal and get access token"""
        # Check if token is still valid
        if (self.config._access_token and self._token_expiry and 
            datetime.utcnow() < self._token_expiry):
            return
        
        print("Authenticating with Pesapal...")
        
        auth_url = f"{self.config.base_url}/api/Auth/RequestToken"
        
        auth_data = {
            "consumer_key": self.config.consumer_key,
            "consumer_secret": self.config.consumer_secret
        }
        
        try:
            response = self.session.post(auth_url, json=auth_data)
            response.raise_for_status()
                        
            auth_response = response.json()

            self.config._access_token = auth_response.get('token')
            
            # Set token expiry (typically 1 hour, but we'll use 55 minutes for safety)
            self._token_expiry = datetime.utcnow() + timedelta(minutes=55)
            
            # Update session headers with new token
            self.session.headers.update({
                "Authorization": f"Bearer {self.config._access_token}"
            })
            
        except requests.exceptions.RequestException as e:
            print(f"Authentication request failed: {str(e)}")
            raise Exception(f"Authentication failed: {str(e)}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make authenticated request to Pesapal API
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
        
        Returns:
            Dict: API response
        """
        # Ensure we're authenticated
        self._authenticate()
        
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            else:
                response = self.session.post(url, json=data)
            
            response.raise_for_status()
            print(f"Request to {url} successful with method {method}")
            print(f"Request data: {data}")
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.json()}")
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e}"
            try:
                error_detail = response.json()
                error_msg = f"{error_msg} - {error_detail}"
            except:
                pass
            raise Exception(error_msg)
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def verify_payment_webhook(self, payload: Dict, signature: str) -> bool:
        """
        Verify Pesapal webhook signature
        
        Args:
            payload: Webhook payload
            signature: Signature from header
        
        Returns:
            bool: True if signature is valid
        """
        # This is a simplified version - adjust based on Pesapal's webhook verification
        payload_str = json.dumps(payload, separators=(',', ':'))
        expected_signature = hmac.new(
            self.config.consumer_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

# ============================================================================
# Usage with your existing code
# ============================================================================
