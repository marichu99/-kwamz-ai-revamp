import os
import uuid
import requests
from datetime import datetime
from decimal import Decimal
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.backends import default_backend
import base64
from dotenv import load_dotenv

from app import db
from app.model.swap_payout import SwapPayout
from app.model.agent_swap import AgentSwap
from app.service.mpesa_service import MpesaService

load_dotenv()


class B2CPayoutService:
    def __init__(self):
        self.mpesa_service = MpesaService()
        self.api_url = os.getenv('MPESA_API_URL', 'https://sandbox.safaricom.co.ke')
        self.b2c_shortcode = os.getenv('MPESA_B2C_SHORTCODE', '600000')
        self.initiator_name = os.getenv('MPESA_B2C_INITIATOR_NAME', 'testapi')
        self.initiator_password = os.getenv('MPESA_B2C_INITIATOR_PASSWORD', '')
        self.result_url = os.getenv('MPESA_B2C_RESULT_URL', '')
        self.timeout_url = os.getenv('MPESA_B2C_TIMEOUT_URL', '')
        self.certificate_path = os.getenv('MPESA_B2C_CERTIFICATE_PATH', 'certs/SandboxCertificate.cer')

    def _encrypt_security_credential(self):
        """RSA-encrypt the initiator password with the Safaricom certificate."""
        cert_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), self.certificate_path)

        with open(cert_path, 'rb') as cert_file:
            cert_data = cert_file.read()

        certificate = load_pem_x509_certificate(cert_data, default_backend())
        public_key = certificate.public_key()

        encrypted = public_key.encrypt(
            self.initiator_password.encode('utf-8'),
            PKCS1v15()
        )
        return base64.b64encode(encrypted).decode('utf-8')

    def send_b2c(self, phone_number, amount, remarks, occasion='SwapPayout'):
        """Call M-Pesa B2C API to send money to a phone number."""
        token = self.mpesa_service.authenticate()
        security_credential = self._encrypt_security_credential()
        originator_conversation_id = str(uuid.uuid4())

        url = f"{self.api_url}/mpesa/b2c/v3/paymentrequest"

        payload = {
            "OriginatorConversationID": originator_conversation_id,
            "InitiatorName": self.initiator_name,
            "SecurityCredential": security_credential,
            "CommandID": "BusinessPayment",
            "Amount": int(amount),
            "PartyA": self.b2c_shortcode,
            "PartyB": phone_number,
            "Remarks": remarks,
            "QueueTimeOutURL": self.timeout_url,
            "ResultURL": self.result_url,
            "Occasion": occasion,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers, verify=False)
        response_data = response.json()

        print(f"B2C response for {phone_number}: {response_data}")

        return {
            'originator_conversation_id': originator_conversation_id,
            'conversation_id': response_data.get('ConversationID'),
            'response_code': response_data.get('ResponseCode'),
            'response_description': response_data.get('ResponseDescription'),
            'raw': response_data,
        }

    def initiate_swap_payout(self, swap_id, user_id):
        """Look up swap, split commission among outgoing agents, send B2C per agent."""
        swap = AgentSwap.query.get(swap_id)
        if not swap:
            raise ValueError('Swap not found')

        previous_agents = swap.previous_agents or []
        if not previous_agents:
            raise ValueError('No outgoing agents found for this swap')

        # Check if payouts already exist for this swap
        existing = SwapPayout.query.filter_by(swap_id=swap_id).first()
        if existing:
            raise ValueError('Payouts have already been initiated for this swap')

        commission = Decimal(str(swap.commission_balance_at_swap or 0))
        if commission <= 0:
            raise ValueError('No commission balance to pay out')

        # Split commission evenly among outgoing agents
        agent_count = len(previous_agents)
        per_agent_amount = (commission / agent_count).quantize(Decimal('0.01'))

        payouts = []
        for agent in previous_agents:
            phone = agent.get('phone_number', '')
            if not phone:
                # Create a failed record if no phone number
                payout = SwapPayout(
                    swap_id=swap_id,
                    agent_name=agent.get('name', 'Unknown'),
                    agent_idnumber=agent.get('idnumber', ''),
                    phone_number='',
                    amount=per_agent_amount,
                    status='failed',
                    result_desc='No phone number on record',
                    initiated_by=user_id,
                )
                db.session.add(payout)
                payouts.append(payout)
                continue

            # Normalize phone number to 254 format
            normalized_phone = self._normalize_phone(phone)

            remarks = f"Commission payout - Swap #{swap_id}"

            try:
                result = self.send_b2c(
                    phone_number=normalized_phone,
                    amount=per_agent_amount,
                    remarks=remarks,
                    occasion='SwapPayout',
                )

                payout = SwapPayout(
                    swap_id=swap_id,
                    agent_name=agent.get('name', 'Unknown'),
                    agent_idnumber=agent.get('idnumber', ''),
                    phone_number=normalized_phone,
                    amount=per_agent_amount,
                    conversation_id=result.get('conversation_id'),
                    originator_conversation_id=result.get('originator_conversation_id'),
                    status='pending' if result.get('response_code') == '0' else 'failed',
                    result_desc=result.get('response_description', ''),
                    initiated_by=user_id,
                )
            except Exception as e:
                payout = SwapPayout(
                    swap_id=swap_id,
                    agent_name=agent.get('name', 'Unknown'),
                    agent_idnumber=agent.get('idnumber', ''),
                    phone_number=normalized_phone,
                    amount=per_agent_amount,
                    status='failed',
                    result_desc=str(e),
                    initiated_by=user_id,
                )

            db.session.add(payout)
            payouts.append(payout)

        db.session.commit()
        return [p.to_dict() for p in payouts]

    def process_b2c_result(self, data):
        """Handle B2C result callback from Safaricom."""
        result = data.get('Result', {})
        conversation_id = result.get('ConversationID')
        originator_conversation_id = result.get('OriginatorConversationID')
        result_code = result.get('ResultCode')
        result_desc = result.get('ResultDesc')

        payout = SwapPayout.query.filter_by(
            originator_conversation_id=originator_conversation_id
        ).first()

        if not payout:
            payout = SwapPayout.query.filter_by(
                conversation_id=conversation_id
            ).first()

        if not payout:
            print(f"B2C result: No payout found for ConversationID={conversation_id}")
            return False

        payout.result_code = result_code
        payout.result_desc = result_desc
        payout.conversation_id = conversation_id
        payout.completed_at = datetime.utcnow()

        if result_code == 0:
            payout.status = 'completed'
            # Extract receipt number from result parameters
            params = result.get('ResultParameters', {}).get('ResultParameter', [])
            for param in params:
                if param.get('Key') == 'TransactionReceipt':
                    payout.mpesa_receipt = param.get('Value')
                    break
        else:
            payout.status = 'failed'

        db.session.commit()
        print(f"B2C result processed: payout #{payout.id} -> {payout.status}")
        return True

    def process_b2c_timeout(self, data):
        """Handle B2C timeout callback — mark payout as failed."""
        result = data.get('Result', {})
        conversation_id = result.get('ConversationID')
        originator_conversation_id = result.get('OriginatorConversationID')

        payout = SwapPayout.query.filter_by(
            originator_conversation_id=originator_conversation_id
        ).first()

        if not payout:
            payout = SwapPayout.query.filter_by(
                conversation_id=conversation_id
            ).first()

        if not payout:
            print(f"B2C timeout: No payout found for ConversationID={conversation_id}")
            return False

        payout.status = 'failed'
        payout.result_desc = 'Request timed out'
        payout.completed_at = datetime.utcnow()
        db.session.commit()

        print(f"B2C timeout processed: payout #{payout.id} -> failed")
        return True

    def get_payouts_by_swap(self, swap_id):
        """Return all payout records for a given swap."""
        payouts = SwapPayout.query.filter_by(swap_id=swap_id).order_by(SwapPayout.created_at).all()
        return [p.to_dict() for p in payouts]

    @staticmethod
    def _normalize_phone(phone):
        """Normalize phone number to 254XXXXXXXXX format."""
        phone = phone.strip().replace(' ', '').replace('-', '').replace('+', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
        return phone
