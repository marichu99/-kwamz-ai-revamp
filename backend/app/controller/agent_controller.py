"""
agent_controller.py — API endpoints consumed by the desktop Mpesa scraping agent.

Authentication: static shared secret sent in the X-Agent-Secret header.
Set AGENT_SECRET in the server .env.  The agent reads the same value from its
own config so no user-level token management is needed.
"""

from flask import Blueprint, jsonify, request, send_from_directory
from app import db
from app.model.mpesa_scrape_job import MpesaScrapeJob
from app.model.verification_job import VerificationJob
from app.controller.verification_controller import _sync_authenticity
from app.service.transaction_service import TransactionService
from app.service.agentcompany_service import AgentCompanyService
from app.service.email_outbox_service import EmailOutboxService
from app.utils.email_utils import (
    send_not_active_short_code_,
    send_session_timeout_email,
    send_scraping_report_email,
)
from app.tasks.fraud_detection_tasks import run_fraud_detection_for_user
from datetime import datetime
from functools import wraps
from openai import OpenAI
import anthropic
from PIL import Image
import pytesseract
import pandas as pd
import base64
import tempfile
import re
import os

agent_bp = Blueprint('agent', __name__)

transaction_service = TransactionService()
agent_company_service = AgentCompanyService()
email_outbox_service = EmailOutboxService()

MAX_SEND_ATTEMPTS = 3


# ── Auth decorator ────────────────────────────────────────────────────────────

def agent_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        expected = os.getenv('AGENT_SECRET', '')
        if not expected:
            return jsonify({'error': 'AGENT_SECRET not configured on server'}), 500
        provided = request.headers.get('X-Agent-Secret', '')
        if not provided or provided != expected:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Job polling ───────────────────────────────────────────────────────────────

@agent_bp.route('/scrape-job/pending', methods=['GET'])
@agent_auth_required
def get_pending_job():
    """
    Returns the oldest pending scrape job and marks it as running.
    Uses skip_locked so multiple agent instances don't double-claim.
    """
    job = (
        MpesaScrapeJob.query
        .filter_by(status='pending')
        .order_by(MpesaScrapeJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not job:
        return jsonify({'job': None}), 200

    job.status = 'running'
    job.started_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'job': {
            'job_id': job.id,
            'short_code': job.short_code,
            'username': job.username,
            'password': job.password,
            'user_id': job.user_id,
        }
    }), 200


@agent_bp.route('/scrape-job/<job_id>/heartbeat', methods=['POST'])
@agent_auth_required
def job_heartbeat(job_id):
    job = MpesaScrapeJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    job.last_heartbeat = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True}), 200


@agent_bp.route('/scrape-job/<job_id>/complete', methods=['POST'])
@agent_auth_required
def job_complete(job_id):
    job = MpesaScrapeJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    job.status = 'completed'
    job.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True}), 200


@agent_bp.route('/scrape-job/<job_id>/failed', methods=['POST'])
@agent_auth_required
def job_failed(job_id):
    job = MpesaScrapeJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    data = request.json or {}
    job.status = 'failed'
    job.error_message = data.get('error', '')
    job.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True}), 200


# ── Data endpoints ────────────────────────────────────────────────────────────

@agent_bp.route('/last-scraped', methods=['GET'])
@agent_auth_required
def last_scraped():
    """Returns {shortcode: [days_since_last_scrape, last_receipt_no]} for all tills."""
    try:
        data = transaction_service.get_last_scraped_per_shortcode()
        return jsonify({'data': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/transactions', methods=['POST'])
@agent_auth_required
def post_transactions():
    """
    Accepts transaction rows from the agent and persists them via TransactionService.

    Body:
    {
      "rows": [...],            # list of dicts — one per transaction row
      "columns": [...],         # column names (same order as rows)
      "transaction_type": "float" | "commission",
      "company_shortcode": "...",
      "business_shortcode": "...",
    }
    """
    data = request.json or {}
    rows = data.get('rows', [])
    columns = data.get('columns', [])
    transaction_type = data.get('transaction_type')
    company_shortcode = data.get('company_shortcode')
    business_shortcode = data.get('business_shortcode')

    if not rows or not transaction_type:
        return jsonify({'error': 'rows and transaction_type are required'}), 400

    try:
        df = pd.DataFrame(rows, columns=columns if columns else None)
        results = transaction_service.update_transactions_from_dataframe(
            df=df,
            transaction_type=transaction_type,
            company_shortcode=company_shortcode,
            agent_id=None,
            business_shortcode=business_shortcode,
        )
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/transactions/file', methods=['POST'])
@agent_auth_required
def post_transactions_file():
    """
    Accepts a base64-encoded Excel file and persists transactions from it.

    Body:
    {
      "file_b64": "...",
      "transaction_type": "float" | "commission",
      "company_shortcode": "...",
      "business_shortcode": "..."
    }
    """
    data = request.json or {}
    file_b64 = data.get('file_b64')
    transaction_type = data.get('transaction_type')
    company_shortcode = data.get('company_shortcode')
    business_shortcode = data.get('business_shortcode')

    if not file_b64 or not transaction_type:
        return jsonify({'error': 'file_b64 and transaction_type are required'}), 400

    tmp_path = None
    try:
        file_bytes = base64.b64decode(file_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        df = pd.read_excel(tmp_path, skiprows=6)
        results = transaction_service.update_transactions_from_dataframe(
            df=df,
            transaction_type=transaction_type,
            company_shortcode=company_shortcode,
            agent_id=None,
            business_shortcode=business_shortcode,
        )
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@agent_bp.route('/organization', methods=['POST'])
@agent_auth_required
def post_organization():
    """
    Saves or updates a scraped agent company record.

    Body: { "mapped_data": {...}, "user_id": "..." }
    """
    data = request.json or {}
    mapped_data = data.get('mapped_data')
    user_id = data.get('user_id')

    if not mapped_data:
        return jsonify({'error': 'mapped_data is required'}), 400

    try:
        result = agent_company_service.save_or_update_scraped_agent_company(
            mapped_data=mapped_data,
            user_id=user_id,
        )
        return jsonify({'success': True, 'result': str(result)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Captcha (vision) ──────────────────────────────────────────────────────────

@agent_bp.route('/captcha/solve-vision', methods=['POST'])
@agent_auth_required
def solve_captcha_vision():
    """
    Solves an image CAPTCHA using Anthropic Claude (claude-haiku-4-5).
    The agent sends the captcha as base64; we return the extracted text.

    Body: { "image_b64": "..." }
    """
    data = request.json or {}
    image_b64 = data.get('image_b64')
    if not image_b64:
        return jsonify({'error': 'image_b64 is required'}), 400

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    import logging
    logging.warning(f'[CAPTCHA] ANTHROPIC_API_KEY present: {bool(anthropic_key)}, value: {anthropic_key[:20] + "..." if anthropic_key else "None"}')
    if not anthropic_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not configured on server'}), 500

    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=50,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': 'image/png',
                            'data': image_b64,
                        },
                    },
                    {
                        'type': 'text',
                        'text': (
                            'Extract the exact digits from this CAPTCHA image. '
                            'It is a 4-6 digit code with possible lines or distortions. '
                            'Respond only with the digits, nothing else.'
                        ),
                    },
                ],
            }],
        )
        answer = response.content[0].text.strip()
        return jsonify({'answer': answer}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Alert / notification endpoints ────────────────────────────────────────────

@agent_bp.route('/alert/non-active', methods=['POST'])
@agent_auth_required
def alert_non_active():
    """
    Sends a non-active short code alert email (max MAX_SEND_ATTEMPTS times).

    Body:
    {
      "recipient_email": "...",
      "business_name": "...",
      "business_short_code": "...",
      "status": "...",
      "sender_email": "..."
    }
    """
    data = request.json or {}
    recipient_email = data.get('recipient_email')
    business_name = data.get('business_name', '-')
    business_short_code = data.get('business_short_code')
    status = data.get('status')
    sender_email = data.get('sender_email', '')

    if not all([recipient_email, business_short_code, status]):
        return jsonify({'error': 'recipient_email, business_short_code, and status are required'}), 400

    try:
        existing = EmailOutboxService.get_by_business_and_reason(
            business_short_code=business_short_code,
            reason='NON_ACTIVE_AGENT',
        )
        record = next((e for e in existing if e.receiver == recipient_email), None)

        if record and (record.sent_times or 0) >= MAX_SEND_ATTEMPTS:
            return jsonify({'skipped': True, 'reason': 'max attempts reached'}), 200

        send_not_active_short_code_(
            recipient_email=recipient_email,
            business_name=business_name,
            business_short_code=business_short_code,
            company_code=business_short_code,
            status=status,
        )

        if record:
            email_outbox_service.update(record.id, sent_times=(record.sent_times or 0) + 1)
        else:
            email_outbox_service.create(
                sender=sender_email,
                receiver=recipient_email,
                reason='NON_ACTIVE_AGENT',
                business_short_code=business_short_code,
                sent_times=1,
            )

        return jsonify({'sent': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/alert/session-timeout', methods=['POST'])
@agent_auth_required
def alert_session_timeout():
    """Body: { "user_id": "..." }  — looks up user email server-side."""
    from app.model.user import User
    data = request.json or {}
    user_id = data.get('user_id')
    try:
        user = User.query.get(user_id)
        if user:
            send_session_timeout_email(user.email)
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/report/send', methods=['POST'])
@agent_auth_required
def send_report():
    """
    Gathers scraping statistics and emails the report.

    Body: { "user_id": "...", "company_shortcode": "..." }
    """
    from app.model.user import User
    data = request.json or {}
    user_id = data.get('user_id')
    company_shortcode = data.get('company_shortcode')

    try:
        user = User.query.get(user_id)
        recipient = user.email if user else 'martinmaati31@gmail.com'
        from datetime import timedelta
        stats = transaction_service.gather_scraping_statistics(
            start_date=datetime.utcnow() - timedelta(days=180),
            end_date=datetime.utcnow(),
            company_shortcode=company_shortcode,
        )
        send_scraping_report_email(recipient, stats)
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/fraud-detection/trigger', methods=['POST'])
@agent_auth_required
def trigger_fraud_detection():
    """Body: { "user_id": "..." }"""
    data = request.json or {}
    user_id = data.get('user_id')
    try:
        task = run_fraud_detection_for_user.delay(user_id)
        return jsonify({'ok': True, 'task_id': task.id}), 200
    except Exception as e:
        # Celery may be unavailable — not fatal
        return jsonify({'ok': False, 'error': str(e)}), 200


# ── KRA / DCI verification job endpoints ──────────────────────────────────────

@agent_bp.route('/verification/pending', methods=['GET'])
@agent_auth_required
def get_pending_verification_job():
    """
    Returns the oldest pending verification job and marks it as running.
    Uses skip_locked so multiple agent instances don't double-claim.
    """
    job = (
        VerificationJob.query
        .filter_by(status='pending')
        .order_by(VerificationJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not job:
        return jsonify({'job': None}), 200

    job.status = 'running'
    db.session.commit()

    return jsonify({
        'job': {
            'job_id': job.id,
            'kra_pin': job.kra_pin,
            'police_clearance': job.police_clearance,
            'id_number': job.id_number,
            'taxpayer_name': job.taxpayer_name,
        }
    }), 200


@agent_bp.route('/verification/<job_id>/complete', methods=['POST'])
@agent_auth_required
def verification_complete(job_id):
    """Body: { "kra_result": "...", "police_result": "..." }"""
    job = VerificationJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    data = request.json or {}
    job.kra_result = data.get('kra_result')
    job.police_result = data.get('police_result')
    job.status = 'completed'
    job.completed_at = datetime.utcnow()
    _sync_authenticity(job)
    db.session.commit()
    return jsonify({'ok': True}), 200


@agent_bp.route('/verification/<job_id>/failed', methods=['POST'])
@agent_auth_required
def verification_failed(job_id):
    """Body: { "error": "..." }"""
    job = VerificationJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    data = request.json or {}
    job.status = 'failed'
    job.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True}), 200


@agent_bp.route('/captcha/solve-arithmetic', methods=['POST'])
@agent_auth_required
def solve_arithmetic_captcha():
    """
    Solves a math CAPTCHA image (e.g. "3 + 5") using pytesseract OCR.
    Used by the agent for KRA PIN checker captchas.

    Body: { "image_b64": "..." }
    """
    data = request.json or {}
    image_b64 = data.get('image_b64')
    if not image_b64:
        return jsonify({'error': 'image_b64 is required'}), 400

    tmp_path = None
    try:
        image_data = base64.b64decode(image_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        captcha_image = Image.open(tmp_path)
        captcha_text = pytesseract.image_to_string(captcha_image, config='--psm 7').strip()

        match = re.match(r'(\d+)\s*([\+\-\*/xX])\s*(\d+)', captcha_text)
        if not match:
            return jsonify({'error': f'Could not parse CAPTCHA: {captcha_text}'}), 422

        num1, operator, num2 = match.groups()
        num1, num2 = int(num1), int(num2)

        if operator == '+':
            result = num1 + num2
        elif operator == '-':
            result = num1 - num2
        elif operator in ('*', 'x', 'X'):
            result = num1 * num2
        elif operator == '/':
            result = num1 // num2
        else:
            return jsonify({'error': f'Unsupported operator: {operator}'}), 422

        return jsonify({'answer': str(result)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Agent binary downloads ─────────────────────────────────────────────────────

ALLOWED_DOWNLOADS = {'mpesa_agent-linux.zip', 'mpesa_agent-windows.zip'}


@agent_bp.route('/downloads/<filename>', methods=['GET'])
def download_agent(filename):
    """
    Serve pre-built agent binaries from AGENT_DOWNLOADS_DIR.
    No auth required — these are public downloads.

    Place zip files at:
      $AGENT_DOWNLOADS_DIR/mpesa_agent-linux.zip
      $AGENT_DOWNLOADS_DIR/mpesa_agent-windows.zip

    Accessible at:
      GET /api/agent/downloads/mpesa_agent-linux.zip
      GET /api/agent/downloads/mpesa_agent-windows.zip
    """
    if filename not in ALLOWED_DOWNLOADS:
        return jsonify({'error': 'File not found'}), 404

    downloads_dir = os.getenv('AGENT_DOWNLOADS_DIR', '/opt/kwamz-downloads')
    if not os.path.isdir(downloads_dir):
        return jsonify({'error': 'Downloads directory not configured on server'}), 503

    file_path = os.path.join(downloads_dir, filename)
    if not os.path.isfile(file_path):
        return jsonify({'error': 'File not yet available'}), 404

    return send_from_directory(downloads_dir, filename, as_attachment=True)
