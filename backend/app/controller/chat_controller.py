import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.service.chat_service import chat
from app import limiter

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/message', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def send_message():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'message is required'}), 400

    history = data.get('history') or []
    if not isinstance(history, list):
        history = []

    # Validate history shape — keep last 20 turns to cap token usage
    clean_history = [
        h for h in history
        if isinstance(h, dict) and h.get('role') in ('user', 'assistant') and isinstance(h.get('content'), str)
    ][-20:]

    try:
        result = chat(user_id=user_id, message=message, history=clean_history)
        return jsonify({'reply': result['reply'], 'data': result.get('data')})
    except Exception as e:
        logger.error(f"[CHAT] Error for user {user_id}: {e}", exc_info=True)
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500
