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
    Thread-safe registry of per-job MJPEG streams with per-viewer fan-out.

    The scraper thread pushes JPEG bytes via push_frame(); each connected
    viewer gets its own small queue, so two viewers of the same job no
    longer split frames between them.  The latest frame is cached per job
    so a newly connected viewer sees something immediately instead of
    waiting for the portal page to repaint.  wants_frame() lets the CDP
    frame callback skip decode/queue work entirely for unwatched streams.
    """

    # Refresh the cached preview frame this often while nobody is watching,
    # so a viewer who connects later doesn't see an ancient frame.
    IDLE_FRAME_INTERVAL = 5.0
    # Small per-viewer queue = fresh frames; overflow drops the oldest.
    CONSUMER_QUEUE_SIZE = 5

    def __init__(self):
        self._streams: dict = {}
        self._lock = threading.Lock()
        self._next_consumer_id = 0

    def create(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._streams:
                self._streams[job_id] = {
                    'consumers': {},      # consumer_id -> Queue
                    'last_frame': None,   # most recent JPEG for instant first paint
                    'last_frame_ts': 0.0,
                }
                logger.info(f"[STREAM {_ts()}] STREAM CREATED  job={job_id}")
            else:
                logger.info(f"[STREAM {_ts()}] stream already exists (idempotent) job={job_id}")

    def wants_frame(self, job_id: str) -> bool:
        """
        True when pushing a frame would be useful: a viewer is connected, or
        the cached preview frame is stale.  The CDP callback checks this
        before doing any base64 decoding so unwatched jobs cost ~nothing.
        """
        with self._lock:
            s = self._streams.get(job_id)
            if s is None:
                return False
            if s['consumers']:
                return True
            return (time.time() - s['last_frame_ts']) >= self.IDLE_FRAME_INTERVAL

    def push_frame(self, job_id: str, jpeg_bytes: bytes) -> None:
        with self._lock:
            s = self._streams.get(job_id)
            if s is None:
                logger.warning(f"[STREAM {_ts()}] push_frame: NO STREAM for job={job_id} — frame dropped")
                return
            s['last_frame'] = jpeg_bytes
            s['last_frame_ts'] = time.time()
            consumer_queues = list(s['consumers'].values())
        for q in consumer_queues:
            try:
                q.put_nowait(jpeg_bytes)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(jpeg_bytes)
                except (queue.Empty, queue.Full):
                    pass

    def consume(self, job_id: str, wait_timeout: float = 10.0):
        """
        Generator that yields JPEG frames for the given job.
        Exits when the stream is closed (sentinel None) or after a 120 s idle timeout.
        Waits up to `wait_timeout` seconds for the stream to be created.
        """
        deadline = time.time() + wait_timeout
        while time.time() < deadline:
            with self._lock:
                if job_id in self._streams:
                    break
            time.sleep(0.1)

        q = queue.Queue(maxsize=self.CONSUMER_QUEUE_SIZE)
        with self._lock:
            s = self._streams.get(job_id)
            if s is None:
                logger.error(
                    f"[STREAM {_ts()}] CONSUMER ARRIVED BUT STREAM IS MISSING after "
                    f"{wait_timeout}s — job={job_id}"
                )
                return
            self._next_consumer_id += 1
            consumer_id = self._next_consumer_id
            s['consumers'][consumer_id] = q
            last_frame = s['last_frame']

        logger.info(f"[STREAM {_ts()}] CONSUMER {consumer_id} CONNECTED  job={job_id}")
        frames_sent = 0
        try:
            # Serve the cached frame right away so the viewer isn't stuck on a
            # blank <img> until the (possibly static) portal page next repaints.
            if last_frame is not None:
                frames_sent += 1
                yield last_frame
            while True:
                try:
                    frame = q.get(timeout=120)
                except queue.Empty:
                    logger.warning(
                        f"[STREAM {_ts()}] IDLE TIMEOUT after {frames_sent} frames — "
                        f"closing consumer {consumer_id} job={job_id}"
                    )
                    break
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
        finally:
            # Runs on sentinel/timeout AND when the browser disconnects
            # (GeneratorExit) — the consumer never leaks.
            with self._lock:
                s = self._streams.get(job_id)
                if s is not None:
                    s['consumers'].pop(consumer_id, None)
            logger.info(
                f"[STREAM {_ts()}] CONSUMER {consumer_id} DISCONNECTED "
                f"(sent {frames_sent} frames) job={job_id}"
            )

    def close(self, job_id: str) -> None:
        with self._lock:
            s = self._streams.pop(job_id, None)
        if s:
            for q in s['consumers'].values():
                try:
                    q.put_nowait(None)
                except queue.Full:
                    try:
                        q.get_nowait()
                        q.put_nowait(None)
                    except (queue.Empty, queue.Full):
                        pass
        logger.info(f"[STREAM {_ts()}] STREAM CLOSED  job={job_id}")


stream_manager = StreamManager()


class OtpMailbox:
    """
    Per-job OTP channel.  The Flask request thread deposits an OTP via put();
    the Playwright scraper thread (which owns the page) collects it via get()
    and does the actual typing.  This avoids the greenlet cross-thread error
    that occurs when Flask tries to call Playwright's sync API directly.
    """

    def __init__(self):
        self._queues: dict = {}
        self._lock = threading.Lock()

    def register(self, job_id: str) -> None:
        with self._lock:
            self._queues[job_id] = queue.Queue(maxsize=1)
        logger.info(f"[OTP-MAILBOX] registered job={job_id}")

    def put(self, job_id: str, otp: str) -> bool:
        """Returns False if the job is unknown or the mailbox already has an OTP."""
        with self._lock:
            q = self._queues.get(job_id)
        if q is None:
            return False
        try:
            q.put_nowait(otp)
            logger.info(f"[OTP-MAILBOX] OTP deposited for job={job_id}")
            return True
        except queue.Full:
            logger.warning(f"[OTP-MAILBOX] mailbox full for job={job_id} — OTP dropped")
            return False

    def get(self, job_id: str, timeout: float = 120.0) -> str | None:
        """Block in the scraper thread until an OTP arrives or timeout expires."""
        with self._lock:
            q = self._queues.get(job_id)
        if q is None:
            return None
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    def unregister(self, job_id: str) -> None:
        with self._lock:
            self._queues.pop(job_id, None)
        logger.info(f"[OTP-MAILBOX] unregistered job={job_id}")


otp_mailbox = OtpMailbox()


class CaptchaMailbox:
    """
    Per-job captcha channel.  Works the same way as OtpMailbox but carries
    the 4-digit code the user types in the frontend CAPTCHA dock.
    The mailbox is drained before each new deposit so a stale value from
    a previous failed attempt is never re-used.
    """

    def __init__(self):
        self._queues: dict = {}
        self._lock = threading.Lock()

    def register(self, job_id: str) -> None:
        with self._lock:
            self._queues[job_id] = queue.Queue(maxsize=1)
        logger.info(f"[CAPTCHA-MAILBOX] registered job={job_id}")

    def put(self, job_id: str, code: str) -> bool:
        with self._lock:
            q = self._queues.get(job_id)
        if q is None:
            return False
        # Drain any stale entry so the scraper always sees the latest code.
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(code)
            logger.info(f"[CAPTCHA-MAILBOX] code deposited for job={job_id}")
            return True
        except queue.Full:
            logger.warning(f"[CAPTCHA-MAILBOX] mailbox full for job={job_id} — dropped")
            return False

    def get(self, job_id: str, timeout: float = 120.0) -> str | None:
        with self._lock:
            q = self._queues.get(job_id)
        if q is None:
            return None
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    def unregister(self, job_id: str) -> None:
        with self._lock:
            self._queues.pop(job_id, None)
        logger.info(f"[CAPTCHA-MAILBOX] unregistered job={job_id}")


captcha_mailbox = CaptchaMailbox()


class PromptManager:
    """
    Tracks what the frontend should currently be asking the user for.
    The scraper sets 'captcha' or 'otp' before blocking on the relevant
    mailbox, and clears it once input is received.  The frontend polls
    GET /stream/<job_id>/prompt to know which input dock to show.

    For captcha prompts an optional base64-encoded PNG of the captcha
    element can be stored so the frontend can render it directly — this
    avoids depending on the MJPEG stream to display the captcha image.
    """

    def __init__(self):
        self._data: dict = {}
        self._lock = threading.Lock()

    def set(self, job_id: str, prompt_type: str, captcha_b64: str = None) -> None:
        with self._lock:
            self._data[job_id] = {'type': prompt_type, 'captcha_b64': captcha_b64}
        logger.info(f"[PROMPT] job={job_id} prompt={prompt_type}")

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            return self._data.get(job_id)

    def clear(self, job_id: str) -> None:
        with self._lock:
            self._data.pop(job_id, None)
        logger.info(f"[PROMPT] job={job_id} prompt cleared")


prompt_manager = PromptManager()
