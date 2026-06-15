import logging
from flask import Blueprint, Response, stream_with_context

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
