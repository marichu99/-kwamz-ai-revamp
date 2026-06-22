import logging
from flask import Blueprint, Response, stream_with_context, request, jsonify
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

stream_bp = Blueprint('stream', __name__)


@stream_bp.route('/<job_id>')
def mjpeg_stream(job_id: str):
    """
    MJPEG stream endpoint for a live Playwright screencast.
    The browser connects here with a plain <img src="..."> — no JS player needed.
    """
    import time as _time
    _ts = lambda: _time.strftime('%H:%M:%S', _time.localtime()) + f'.{int((_time.time()%1)*1000):03d}'
    logger.info(f"[STREAM-ENDPOINT {_ts()}] browser connected to stream for job={job_id}")
    from app.streaming.stream_manager import stream_manager

    def generate():
        for frame in stream_manager.consume(job_id):
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                frame +
                b'\r\n'
            )

    return Response(
        stream_with_context(generate()),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@stream_bp.route('/<job_id>', methods=['DELETE'])
@jwt_required()
def kill_stream(job_id: str):
    """
    Kill the running scraper for this job.
    Closes the Playwright browser (which crashes the scraper thread naturally)
    and sends a sentinel to the MJPEG queue so connected consumers disconnect.
    """
    import app.utils.mpesa_automation as auto
    from app.streaming.stream_manager import stream_manager

    try:
        if auto.browser:
            auto.browser.close()
            logger.info(f"[STREAM-KILL] Browser closed for job={job_id}")
    except Exception as e:
        logger.warning(f"[STREAM-KILL] Could not close browser for job={job_id}: {e}")

    stream_manager.close(job_id)
    logger.info(f"[STREAM-KILL] Stream queue closed for job={job_id}")
    return jsonify({'ok': True})


@stream_bp.route('/<job_id>/otp', methods=['POST'])
@jwt_required()
def submit_otp(job_id: str):
    """
    Deposit a 6-digit OTP into the mailbox for this job.
    The scraper thread (which owns the Playwright page) collects it and
    types it — this avoids the greenlet cross-thread restriction.
    """
    data = request.get_json(silent=True) or {}
    otp = str(data.get('otp', ''))

    if len(otp) != 6 or not otp.isdigit():
        return jsonify({'error': 'OTP must be exactly 6 digits'}), 400

    from app.streaming.stream_manager import otp_mailbox
    ok = otp_mailbox.put(job_id, otp)
    if not ok:
        return jsonify({'error': 'No active browser session for this job'}), 404

    logger.info(f"[STREAM-OTP] OTP deposited for job={job_id}")
    return jsonify({'ok': True})
