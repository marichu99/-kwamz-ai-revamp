from flask import Blueprint, jsonify, request, send_file
from app import db
from app.model.verification_job import VerificationJob
from app.model.useragent import UserAgent
from flask_jwt_extended import jwt_required
from functools import wraps
from datetime import datetime
from PIL import Image
import pytesseract
import base64
import tempfile
import os
import re


def _sync_authenticity(job):
    """Set is_authentic on the matching UserAgent based on KRA + DCI results."""
    kra_valid = bool(job.kra_result and 'Active' in job.kra_result)
    dci_valid = bool(job.police_result and 'VALID' in job.police_result.upper())
    agent = UserAgent.query.filter_by(idnumber=job.id_number).first()
    if agent:
        agent.is_authentic = kra_valid and dci_valid

verification_bp = Blueprint('verification', __name__)

# ── Extension auth ────────────────────────────────────────────────────────────
# Extension-facing endpoints use a static shared secret instead of JWT so that
# users never have to manage tokens — they just install the extension.

def extension_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        expected = os.getenv('EXTENSION_SECRET', '')
        if not expected:
            return jsonify({'error': 'EXTENSION_SECRET not configured on server'}), 500
        provided = request.headers.get('X-Extension-Secret', '')
        if not provided or provided != expected:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Web app endpoints (JWT) ───────────────────────────────────────────────────

@verification_bp.route('/create', methods=['POST'])
@jwt_required()
def create_job():
    data = request.json or {}
    kra_pin = data.get('kraPin')
    police_clearance = data.get('policeClearance')
    id_number = data.get('idNumber')
    taxpayer_name = data.get('taxPayerName')

    if not all([kra_pin, police_clearance, id_number]):
        return jsonify({'error': 'kraPin, policeClearance, and idNumber are required'}), 400

    job = VerificationJob(
        kra_pin=kra_pin,
        police_clearance=police_clearance,
        id_number=id_number,
        taxpayer_name=taxpayer_name,
        status='pending'
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({
        'job_id': job.id,
        'kra_pin': job.kra_pin,
        'police_clearance': job.police_clearance,
        'id_number': job.id_number,
        'taxpayer_name': job.taxpayer_name
    }), 201


@verification_bp.route('/status/<job_id>', methods=['GET'])
@jwt_required()
def get_status(job_id):
    job = VerificationJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'job_id': job.id,
        'status': job.status,
        'kra_result': job.kra_result,
        'police_result': job.police_result,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None
    }), 200


# ── Extension endpoints (static secret) ──────────────────────────────────────

@verification_bp.route('/pending', methods=['GET'])
@extension_auth_required
def get_pending():
    # with_for_update() locks the row so two extensions polling at the same
    # time cannot both claim the same job — one waits until the other commits.
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
            'taxpayer_name': job.taxpayer_name
        }
    }), 200


@verification_bp.route('/solve-captcha', methods=['POST'])
@extension_auth_required
def solve_captcha():
    data = request.json or {}
    image_b64 = data.get('image')

    if not image_b64:
        return jsonify({'error': 'image (base64) is required'}), 400

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


@verification_bp.route('/result/<job_id>', methods=['POST'])
@extension_auth_required
def post_result(job_id):
    job = VerificationJob.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    data = request.json or {}
    job.kra_result = data.get('kra_result')
    job.police_result = data.get('police_result')
    job.status = data.get('status', 'completed')
    job.completed_at = datetime.utcnow()
    _sync_authenticity(job)
    db.session.commit()

    return jsonify({'success': True}), 200


@verification_bp.route('/download-extension', methods=['GET'])
def download_extension():
    """Serve the Chrome extension zip for direct download — no auth required."""
    zip_path = os.path.join(
        os.path.dirname(__file__),   # backend/app/controller/
        '..', '..', '..', 'extension'
    )
    zip_path = os.path.abspath(zip_path)
    out_path = os.path.join(tempfile.gettempdir(), 'kwamz-verifier.zip')

    import zipfile
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(zip_path):
            fpath = os.path.join(zip_path, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)

    return send_file(
        out_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name='kwamz-verifier.zip'
    )
