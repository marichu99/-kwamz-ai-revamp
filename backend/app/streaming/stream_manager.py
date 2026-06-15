import queue
import threading
import logging
import time

logger = logging.getLogger(__name__)


def _ts() -> str:
    """Current time as HH:MM:SS.mmm for log correlation."""
    t = time.time()
    ms = int((t % 1) * 1000)
    return time.strftime('%H:%M:%S', time.localtime(t)) + f'.{ms:03d}'


class StreamManager:
    """
    Thread-safe registry of per-job MJPEG frame queues.

    The scraper thread pushes JPEG bytes via push_frame().
    The Flask request thread consumes them via consume().
    """

    def __init__(self):
        self._streams: dict = {}
        self._lock = threading.Lock()

    def create(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._streams:
                self._streams[job_id] = queue.Queue(maxsize=60)
                logger.info(f"[STREAM {_ts()}] QUEUE CREATED  job={job_id}")
            else:
                logger.info(f"[STREAM {_ts()}] queue already exists (idempotent) job={job_id}")

    def push_frame(self, job_id: str, jpeg_bytes: bytes) -> None:
        with self._lock:
            q = self._streams.get(job_id)
        if q is None:
            logger.warning(f"[STREAM {_ts()}] push_frame: NO QUEUE for job={job_id} — frame dropped")
            return
        try:
            q.put_nowait(jpeg_bytes)
        except queue.Full:
            try:
                q.get_nowait()
                q.put_nowait(jpeg_bytes)
            except (queue.Empty, queue.Full):
                pass

    def consume(self, job_id: str):
        """
        Generator that yields JPEG frames for the given job.
        Exits when the stream is closed (sentinel None) or after a 120 s idle timeout.
        """
        with self._lock:
            q = self._streams.get(job_id)

        if q is None:
            # ── RACE CONDITION PROOF ──────────────────────────────────────────
            # The browser connected to /api/stream/<job_id> BEFORE the scraper
            # thread called stream_manager.create().  Without the pre-create in
            # the controller this path fires every time, causing a blank stream.
            logger.error(
                f"[STREAM {_ts()}] CONSUMER ARRIVED BUT QUEUE IS MISSING — "
                f"race condition! job={job_id}"
            )
            return

        logger.info(f"[STREAM {_ts()}] CONSUMER CONNECTED  job={job_id}")
        frames_sent = 0
        while True:
            try:
                frame = q.get(timeout=120)
                if frame is None:
                    logger.info(
                        f"[STREAM {_ts()}] SENTINEL received — stream done "
                        f"(sent {frames_sent} frames) job={job_id}"
                    )
                    break
                frames_sent += 1
                if frames_sent == 1:
                    logger.info(f"[STREAM {_ts()}] FIRST FRAME yielded  job={job_id}")
                yield frame
            except queue.Empty:
                logger.warning(
                    f"[STREAM {_ts()}] IDLE TIMEOUT after {frames_sent} frames — "
                    f"closing stream job={job_id}"
                )
                break

    def close(self, job_id: str) -> None:
        with self._lock:
            q = self._streams.pop(job_id, None)
        if q:
            try:
                q.put_nowait(None)
            except queue.Full:
                pass
        logger.info(f"[STREAM {_ts()}] QUEUE CLOSED  job={job_id}")


stream_manager = StreamManager()
