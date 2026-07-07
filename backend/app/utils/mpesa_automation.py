import logging
from playwright.sync_api import sync_playwright, Page, Locator, Download, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from flask import current_app
from app.utils.script import fill_login_form
from app.utils.email_utils import generate_scraping_report_email, send_scraping_report_email,send_session_timeout_email,send_not_active_short_code_,send_swaps_scraped_email
from app.tasks.fraud_detection_tasks import run_fraud_detection_for_user
from app.service.transaction_service import TransactionService
from app.service.agentcompany_service import AgentCompanyService
from app.service.email_outbox_service import EmailOutboxService
from app import db
from app.model.user import User
from app.model.email_outbox import EmailOutbox
from app.model.useragent import UserAgent
# from script import fill_login_form, capture_and_solve_captcha
from PIL import Image, ImageFilter, ImageOps
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from decimal import Decimal
import pandas as pd
import re
import base64
import os
import time
import random
import asyncio
import threading
import traceback
import numpy as np

logger = logging.getLogger(__name__)

# Dedicated scraper log. Path can be overridden via SCRAPER_LOG_PATH env var
# so it works both on bare metal and inside Docker.
_default_log_path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs', 'scraper.log')
)
_scraper_log_path = os.environ.get('SCRAPER_LOG_PATH', _default_log_path)
try:
    os.makedirs(os.path.dirname(_scraper_log_path), exist_ok=True)
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(_scraper_log_path)
               for h in logger.handlers):
        _fh = logging.FileHandler(_scraper_log_path, encoding='utf-8')
        _fh.setLevel(logging.INFO)
        _fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(_fh)
except (PermissionError, OSError):
    pass  # fall back to stdout/Docker logs only
logger.propagate = True


transaction_service = TransactionService()
agent_company_service = AgentCompanyService()
email_outbox_service = EmailOutboxService()

# Load environment variables
load_dotenv()

# Module-level job registry: job_id -> MpesaScraper instance (for kill_stream)
_job_registry: dict = {}


class MpesaScraper:
    """One instance per scrape job — all state is instance-local, safe for 50+ concurrent jobs."""

    MAX_SEND_ATTEMPTS = 3

    def __init__(self, password: str, username: str, short_code: str,
                 user_id_passed=None, job_id: str = None) -> None:
        self.password = password
        self.username = username
        self.short_code = short_code
        self._user_id_passed = user_id_passed
        self.job_id = job_id
        # Per-instance scraper state (was module-level globals)
        self.company_shortcode = None
        self.user_id = None
        self.user = None
        self.till_scraping_shortfall = {}
        self.context = None
        self.browser = None

    def _start_cdp_screencast(self, page, job_id: str):

        """
        Open a CDP session on `page` and start streaming JPEG frames into the
        StreamManager under `job_id`.  Returns the CDPSession so the caller can
        stop it later.

        IMPORTANT: `_on_frame` is invoked from Playwright's internal asyncio thread.
        The sync cdp.send() wraps a greenlet switch back to the scraper OS thread,
        which is blocked waiting for Playwright — deadlock.  We use asyncio.ensure_future()
        on the async impl directly so the ACK stays entirely inside the asyncio loop.
        """
        from app.streaming.stream_manager import stream_manager

        stream_manager.create(job_id)
        cdp = page.context.new_cdp_session(page)

        async def _ack_async(session_id):
            try:
                await cdp._impl_obj.send('Page.screencastFrameAck', {'sessionId': session_id})
            except Exception:
                pass

        def _on_frame(event):
            try:
                jpeg = base64.b64decode(event['data'])
                stream_manager.push_frame(job_id, jpeg)
                logger.debug(f"Screencast frame pushed for job {job_id} ({len(jpeg)} bytes)")
                # _on_frame is called from Playwright's internal asyncio thread.
                # We must NOT call the sync cdp.send() here (it would try to
                # greenlet-switch back to the scraper thread, which is blocked on
                # a different operation — causing a deadlock or greenlet error).
                # Instead, schedule the ACK coroutine directly on the running loop.
                asyncio.ensure_future(_ack_async(event['sessionId']))
            except PlaywrightError:
                pass  # self.browser already closed — frame drop is expected
            except Exception as exc:
                logger.warning(f"Screencast frame drop: {exc}")

        cdp.on('Page.screencastFrame', _on_frame)
        cdp.send('Page.startScreencast', {
            'format': 'jpeg',
            'quality': 75,
            'maxWidth': 1280,
            'maxHeight': 720,
            'everyNthFrame': 1,
        })
        logger.info(f"CDP screencast started for job {job_id}")
        return cdp


    def _capture_captcha_image(self, page) -> str | None:

        """
        Wait for the captcha <img> element to be fully loaded (img.complete +
        naturalWidth > 0, not just DOM-visible), then return a base64 PNG
        screenshot of that element.  Returns None on any failure.
        """
        try:
            captcha_selector = "//img[@class='verifyCode-img-item']"
            page.wait_for_selector(captcha_selector, state="visible", timeout=10000)
            # Block until the browser has finished decoding the image pixels.
            # 'visible' only means the element isn't hidden — the src may still
            # be in-flight.  We use a JS promise so we don't busy-wait.
            page.evaluate("""() => new Promise((resolve) => {
                const img = document.querySelector('img.verifyCode-img-item');
                if (!img) { resolve(); return; }
                if (img.complete && img.naturalWidth > 0) { resolve(); return; }
                img.addEventListener('load',  resolve, { once: true });
                img.addEventListener('error', resolve, { once: true });
                setTimeout(resolve, 5000);
            })""")
            captcha_bytes = page.locator(captcha_selector).first.screenshot()
            b64 = base64.b64encode(captcha_bytes).decode()
            logger.info(f"[CAPTCHA] Image captured ({len(captcha_bytes)} bytes)")
            return b64
        except Exception as e:
            logger.warning(f"[CAPTCHA] Could not capture image: {e}")
            return None


    def _get_captcha_from_user(self, job_id: str, captcha_b64: str = None, timeout: float = 120.0) -> str:

        """
        Signal the frontend to show the captcha dock (with the pre-captured image
        if available), then block until the self.user submits the 4-digit code.
        """
        from app.streaming.stream_manager import captcha_mailbox, prompt_manager
        prompt_manager.set(job_id, 'captcha', captcha_b64=captcha_b64)
        logger.info(f"[CAPTCHA] Waiting for self.user input (job={job_id}, timeout={timeout}s)…")
        code = captcha_mailbox.get(job_id, timeout=timeout)
        prompt_manager.clear(job_id)
        if not code:
            raise Exception(f"[CAPTCHA] Timed out waiting for self.user captcha input (job={job_id})")
        logger.info(f"[CAPTCHA] Received captcha from self.user for job={job_id}")
        return code


    def run(self) -> None:

        # Local aliases for params stored in __init__
        password = self.password
        username = self.username
        short_code = self.short_code
        user_id_passed = self._user_id_passed
        job_id = self.job_id
        if job_id:
            _job_registry[job_id] = self
        password = password
        # or os.getenv("AGENT_COMPANY_PASSWORD")
        username = username
        # or os.getenv("AGENT_COMPANY_USERNAME")
        self.user_id = user_id_passed
        self.user = User.query.filter_by(id=self.user_id).first()

        short_code = short_code
        # or os.getenv("AGENT_COMPANY_SHORTCODE")
        self.company_shortcode = short_code

        self.till_scraping_shortfall = transaction_service.get_last_scraped_per_shortcode()
        url = "https://org.ke.m-pesa.com/#/login?transaction_service=https%3A%2F%2Forg.ke.m-pesa.com%2Forgportal%2Fv1%2Fsso%2Fhome"

        from app.streaming.stream_manager import stream_manager
        _cdp = None

        try:
            with sync_playwright() as p:
                self.browser = p.chromium.launch(
                    headless=False,
                    args=['--window-size=1920,1080', '--no-sandbox', '--disable-dev-shm-usage']
                )

                # Create context with explicit viewport so it works on Xvfb and real displays
                self.context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
                page = self.context.new_page()

                # Start live screencast if a job_id was provided
                _cdp = self._start_cdp_screencast(page, job_id) if job_id else None
                if job_id:
                    from app.streaming.stream_manager import otp_mailbox, captcha_mailbox
                    otp_mailbox.register(job_id)
                    captcha_mailbox.register(job_id)

                page.goto(url, timeout=600000)
                time.sleep(3)

                # Capture the captcha on the clean page (no form interaction yet) so
                # nothing we do can trigger a portal-side captcha refresh before the
                # user sees the image.  Credentials are filled later, immediately before
                # clicking Login, to avoid the portal's Vue state resetting them while
                # the user is busy reading and typing the captcha.
                captcha_b64 = self._capture_captcha_image(page)
                captcha_solution = self._get_captcha_from_user(job_id, captcha_b64=captcha_b64)
                logger.info(f"[INFO] Captcha received from self.user: {captcha_solution}")

                # Submit loop: fill credentials fresh on every attempt (the portal can
                # reset Vue-bound fields during the captcha wait), then enter the captcha
                # and click Login.
                MAX_CAPTCHA_RETRIES = 5
                logged_in = False

                for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
                    logger.info(f"[INFO] Login attempt {attempt}/{MAX_CAPTCHA_RETRIES}")

                    # Always fill credentials right before submitting
                    fill_login_form(page, short_code, username, password)
                    logger.info("[INFO] Login form filled")

                    page.fill("//input[@id='verifyCode']", captcha_solution)
                    page.click("//button[@id='loginBtn']")
                    logger.info("[INFO] Login button clicked; waiting for response...")

                    # Brief pause to let the error message appear before checking
                    time.sleep(3)

                    if self.has_verification_error_regex(page):
                        logger.warning(f"[WARN] Captcha wrong on attempt {attempt}, asking self.user for new captcha…")
                        captcha_solution = self.retry_captcha_login(page, job_id)
                        continue

                    # Check for OTP/2FA form — portal may require it after a correct captcha
                    if self._has_otp_form(page):
                        logger.info("[INFO] OTP form detected after login click")
                        if job_id:
                            from app.streaming.stream_manager import prompt_manager
                            prompt_manager.set(job_id, 'otp')
                            self._type_otp_from_mailbox(page, job_id, timeout=120.0)
                            prompt_manager.clear(job_id)
                        else:
                            logger.warning("[WARN] OTP form visible but no job_id — cannot receive OTP from UI")

                    # No error shown — wait for the post-login dashboard element.
                    try:
                        search = page.wait_for_selector(
                            "(//i[@class='el-icon el-sub-menu__icon-arrow'])[1]",
                            timeout=60000
                        )
                        search.click()
                        logger.info("[SUCCESS] Logged in successfully!")
                        logged_in = True
                        break
                    except PlaywrightTimeoutError:
                        if self.has_verification_error_regex(page):
                            logger.error(f"[WARN] Captcha error detected after waiting (attempt {attempt}), retrying…")
                            captcha_solution = self.retry_captcha_login(page, job_id)
                        else:
                            raise
                    except PlaywrightError as exc:
                        logger.warning(f"[WARN] Browser target closed on attempt {attempt}, waiting for navigation to settle: {exc}")
                        time.sleep(2)
                        try:
                            search = page.wait_for_selector(
                                "(//i[@class='el-icon el-sub-menu__icon-arrow'])[1]",
                                timeout=60000
                            )
                            search.click()
                            logger.info("[SUCCESS] Logged in successfully (after navigation settle)!")
                            logged_in = True
                            break
                        except Exception as retry_exc:
                            logger.error(f"[ERROR] Still failed after navigation settle: {retry_exc}")
                            raise

                if not logged_in:
                    raise Exception(f"[ERROR] Failed to log in after {MAX_CAPTCHA_RETRIES} captcha attempts.")

                logger.info("[INFO] Navigating to child organization page...")
                self.navigate_to_child_organization(page)

                # ── Continuous scraping cycle ─────────────────────────────────────
                # After each full pass (float + swaps + retries), refresh the
                # shortfall cache and immediately start the next cycle.
                cycle = 1
                while True:
                    cycle += 1
                    logger.info(f"[CYCLE] Cycle {cycle} starting — refreshing shortfall data...")
                    self.till_scraping_shortfall = transaction_service.get_last_scraped_per_shortcode()
                    # process_organization_rows ends with the child org list loaded,
                    # so we can call it again without re-navigating.
                    self.process_organization_rows(page)

        finally:
            # Always close the stream — regardless of where an exception was raised
            if job_id:
                from app.streaming.stream_manager import otp_mailbox, captcha_mailbox, prompt_manager
                otp_mailbox.unregister(job_id)
                captcha_mailbox.unregister(job_id)
                prompt_manager.clear(job_id)
                _job_registry.pop(job_id, None)
            if _cdp:
                try:
                    _cdp.send('Page.stopScreencast')
                except (PlaywrightError, Exception):
                    pass  # self.browser already closed — safe to ignore
            if job_id:
                stream_manager.close(job_id)



    def _is_valid_captcha(self, solution: str) -> bool:

        """Return True only when the captcha solution is exactly 4 numeric digits."""
        return bool(re.match(r'^\d{4}$', solution.strip()))


    def _has_otp_form(self, page) -> bool:

        """Return True if the portal's OTP form is currently visible."""
        try:
            return page.locator('form#OTP-form').is_visible()
        except PlaywrightError:
            return False


    def _type_otp_from_mailbox(self, page, job_id: str, timeout: float = 120.0) -> bool:

        """
        Block (in the scraper thread) until an OTP arrives on the mailbox for
        this job, then type it digit-by-digit into the portal's OTP form.
        Returns True on success, False on timeout or missing form.
        """
        from app.streaming.stream_manager import otp_mailbox
        logger.info(f"[OTP] Waiting for OTP from frontend (job={job_id}, timeout={timeout}s)…")
        otp = otp_mailbox.get(job_id, timeout=timeout)
        if not otp:
            logger.error(f"[OTP] Timed out waiting for OTP (job={job_id})")
            return False
        logger.info(f"[OTP] OTP received for job={job_id}, typing into form…")
        try:
            for i, digit in enumerate(otp):
                loc = page.locator(f'form#OTP-form input[data-index="{i}"]')
                loc.wait_for(state='visible', timeout=5000)
                loc.click()
                loc.press_sequentially(digit, delay=50)
                time.sleep(0.05)
            logger.info(f"[OTP] OTP typed successfully for job={job_id}, clicking confirm…")
            confirm = page.locator("//button[@class='el-button el-button--primary']").first
            confirm.wait_for(state='visible', timeout=5000)
            confirm.click()
            logger.info(f"[OTP] Confirm button clicked for job={job_id}")
            return True
        except PlaywrightError as exc:
            logger.error(f"[OTP] Error typing OTP for job={job_id}: {exc}")
            return False

    def has_verification_error_regex(self, page) -> bool:

        """Checks if the page contains a verification code error using regex."""
        try:
            body_text = page.locator("body").inner_text()
            pattern = re.compile(r"verification\s+code\s+is\s+incorrect\s+or\s+has\s+expired", re.IGNORECASE)
            return bool(pattern.search(body_text))
        except PlaywrightError:
            # Page is navigating or the target closed — this means login succeeded
            # and the portal is redirecting to the dashboard.  No captcha error.
            return False

    def retry_captcha_login(self, page: Page, job_id: str = None) -> str:

        """
        Click the SVG refresh icon to get a new captcha, capture it, then ask
        the self.user to type the new code via the live-feed captcha dock.
        """
        svg_element = page.query_selector("//div[@class='img-part']//*[name()='svg']")
        if svg_element:
            svg_element.click()
            logger.info("[INFO] Clicked SVG element to refresh captcha")
            time.sleep(1)
        else:
            logger.warning("[WARN] SVG element not found — captcha image may not have refreshed")

        if not job_id:
            raise Exception("[CAPTCHA] Cannot prompt for captcha without a job_id (no live feed)")

        captcha_b64 = self._capture_captcha_image(page)
        return self._get_captcha_from_user(job_id, captcha_b64=captcha_b64)
    
    def maximize_page(self, page: Page) -> None:

        """
        Maximizes the page by setting the viewport to a large size (e.g., 1920x1080).
    
        Args:
            page: Playwright Page object
        """
        try:
            # Set viewport to a large size (can adjust based on your needs)
            page.set_viewport_size({"width": 1920, "height": 1080})
            logger.info("[SUCCESS] Page maximized to 1920x1080")
        except Exception as e:
            logger.error(f"[ERROR] Failed to maximize page: {e}")
        
    def _navigate_to_child_org_list(self, page) -> None:

        """Navigate to the Child Organisation list without starting row processing."""
        self.close_portal_tabs(page)
        logger.info("[INFO] Hovering on the index icon...")
        svg_icon = page.wait_for_selector(
            "(//*[name()='svg'][@class='svg-icon'])[2]",
            timeout=60000
        )
        svg_icon.hover()
        logger.info("[INFO] Hover successful, waiting for 'My Organization'...")

        my_org_button = page.wait_for_selector(
            "//span[normalize-space()='My Organization']",
            timeout=60000
        )
        my_org_button.click()
        logger.info("[INFO] 'My Organization' clicked.")
        page.wait_for_timeout(2000)
        page.mouse.click(10, 10)

        child_org_btn = page.wait_for_selector(
            "//button[normalize-space()='Child Organization']",
            timeout=60000
        )
        child_org_btn.click()
        logger.info("[INFO] 'Child Organization' clicked. Waiting for page to load...")
        page.wait_for_timeout(2000)

    def navigate_to_child_organization(self, page):

        """
        Navigates after login: hover on the index icon, click 'My Organization',
        then click 'Child Organization' and start processing rows.
        """
        self._navigate_to_child_org_list(page)
        self.process_organization_rows(page)

    def _scrap_swaps_(self, page: Page, shortcodes: Set[str]) -> None:

        """
        For each scraped agent-company shortcode, opens the Search → Organization Operator
        panel, queries the shortcode, and dumps the result table HTML to a debug file.

        Each shortcode is scraped at most once per calendar day. Shortcodes already
        logged in SwapScrapeLog for today are silently skipped. After all eligible
        shortcodes are processed the logged-in self.user receives an email notification.
        """
        from app.model.swap_scrape_log import SwapScrapeLog

        # ── Daily dedup: skip shortcodes already scraped today ───────────────────
        pending_shortcodes = {sc for sc in shortcodes if not SwapScrapeLog.already_scraped_today(sc)}
        skipped_count = len(shortcodes) - len(pending_shortcodes)
        if skipped_count:
            logger.warning(f"[SWAPS] {skipped_count} shortcode(s) already scraped today — skipping.")
        if not pending_shortcodes:
            logger.info("[SWAPS] All shortcodes have been scraped today. Nothing to do.")
            return

        # ── Step 1: open sidebar flyout, then hover over the active sub-menu ────
        logger.info("[SWAPS] Opening sidebar flyout...")
        sidebar_icon = page.wait_for_selector(
            "(//*[name()='svg'][@class='svg-icon'])[2]",
            timeout=30000,
        )
        sidebar_icon.hover()
        page.wait_for_timeout(800)

        # Only expand the sub-menu if 'Organization Operator' isn't already visible.
        # Clicking an already-expanded sub-menu collapses it, hiding its children.
        org_op_visible = page.evaluate("""() => {
            const spans = Array.from(document.querySelectorAll('span.number-title'));
            const el = spans.find(s => s.textContent.trim() === 'Organization Operator');
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }""")

        if org_op_visible:
            logger.info("[SWAPS] Sub-menu already open — 'Organization Operator' visible, skipping click.")
        else:
            logger.info("[SWAPS] Sub-menu not open — clicking to expand...")
            sub_menu = page.wait_for_selector(
                "//li[contains(@class,'el-sub-menu') and contains(@class,'is-active')]"
                "//div[contains(@class,'el-sub-menu__title')]",
                timeout=15000,
            )
            sub_menu.click()
            page.wait_for_timeout(1000)

        # ── Step 2: click the 'Organization Operator' tab ────────────────────────
        logger.info("[SWAPS] Clicking 'Organization Operator'...")
        org_op_tab = page.wait_for_selector(
            "//span[contains(@class,'number-title')][normalize-space()='Organization Operator']",
            timeout=30000,
            state="visible",
        )
        org_op_tab.click()
        page.wait_for_timeout(1500)

        # ── Step 3: re-query the input on every iteration — Vue re-renders the
        # component after each search result loads, detaching the old node.
        _INPUT_SEL = (
            "//div[@class='el-form-item asterisk-left el-form-item--label-top org-short-code']"
            "//div[@class='el-input__wrapper']//input"
        )
        _ORG_OP_TAB_SEL = (
            "//span[contains(@class,'number-title')][normalize-space()='Organization Operator']"
        )

        scraped_rows = int(0)
        preselected_pagination = False
        successfully_scraped: list[str] = []
        for num,shortcode in enumerate(sorted(pending_shortcodes)):
            logger.info(f"[SWAPS] Querying shortcode: {shortcode}")
            try:
                # From the 2nd shortcode onward, close_detail_panel_idx may have closed the
                # 'Organization Operator' portal tab.  Re-click it so the search form is
                # always active before we look for the shortcode input.
                if num > 0:
                    try:
                        org_op_tab = page.wait_for_selector(_ORG_OP_TAB_SEL, timeout=10000, state="visible")
                        org_op_tab.click()
                        page.wait_for_timeout(1000)
                        logger.info(f"[SWAPS] Re-navigated to 'Organization Operator' for shortcode {shortcode}")
                    except Exception as nav_err:
                        logger.warning(f"[SWAPS] Could not re-click 'Organization Operator' tab: {nav_err}")

                sc_input = page.wait_for_selector(_INPUT_SEL, timeout=15000)
                sc_input.fill('')
                sc_input.fill(shortcode)
                page.wait_for_timeout(500)

                # Click Search / Submit
                page.click("//button[@class='el-button el-button--primary']")
                page.wait_for_timeout(2000)
            
                if(not preselected_pagination):
                    self.select_pagination_size(page)
                    preselected_pagination = True

                # Grab the result table HTML
                table_el = page.wait_for_selector(
                    "//div[@class='el-table__inner-wrapper']", timeout=15000
                )
                raw_html = table_el.inner_html()

                soup = BeautifulSoup(raw_html, "html.parser")

                # Parse operator list from the table so we know each row's status
                scraped_ops = self._parse_swap_operators_from_soup(soup)

                # ── Drill into each row to capture basic-info + KYC detail ───────
                # swap_date  → Active operator's Registration Time
                # row_details → KYC id/phone/reg_time per row, keyed by table index
                swap_date: Optional[datetime] = None
                row_details: dict = {}
                rows = page.query_selector_all("//tr[@class='el-table__row']")
                logger.info(f"[SWAPS] {shortcode}: drilling into {len(rows)} row(s) for detail capture")

                for idx in range(len(rows)):
                    try:
                        # # Re-query rows each iteration so references stay live
                        rows = page.query_selector_all("//tr[@class='el-table__row']")
                        if idx >= len(rows):
                            break
                        row = rows[idx]

                        detail_btn = row.query_selector("button[type='button']")
                        if not detail_btn:
                            logger.warning(f"[SWAPS][WARN] No detail button on row {idx + 1}, skipping.")
                            continue

                        detail_btn.click()
                        page.wait_for_timeout(3000)

                        # Capture Basic Info section
                        basic_info_html = ""
                        try:
                            basic_info_el = page.wait_for_selector(
                                "//div[@class='el-row basic-info-collapse']",
                                timeout=10000
                            )
                            basic_info_html = basic_info_el.inner_html()
                            logger.info(f"[SWAPS] Row {idx + 1}: captured basic-info ({len(basic_info_html)} chars)")
                            reg_time = self._parse_registration_time_from_basic_info(basic_info_html)
                            row_details.setdefault(idx, {})["reg_time"] = reg_time
                            if reg_time:
                                logger.info(f"[SWAPS] Row {idx + 1}: Registration Time → {reg_time.date()}")
                            # Use Active operator's Registration Time as the swap date
                            if swap_date is None and idx < len(scraped_ops) and scraped_ops[idx]["is_active"] and reg_time:
                                swap_date = reg_time
                                logger.info(f"[SWAPS] Row {idx + 1}: swap_date set → {swap_date.date()}")
                        except Exception as bi_err:
                            logger.warning(f"[SWAPS][WARN] Row {idx + 1}: basic-info not found — {bi_err}")

                        # Capture KYC form section
                        kyc_html = ""
                        try:
                            kyc_panel = page.wait_for_selector(
                                "//div[@class='common-kyc-form common-kyc-form-review']",
                                timeout=10000
                            )
                            kyc_html = kyc_panel.inner_html()
                            logger.info(f"[SWAPS] Row {idx + 1}: captured KYC html ({len(kyc_html)} chars)")
                            kyc_detail = self._parse_kyc_details(kyc_html)
                            row_details.setdefault(idx, {}).update(kyc_detail)
                            logger.info(f"[SWAPS] Row {idx + 1}: id={kyc_detail.get('id_number')} phone={kyc_detail.get('phone_number')}")
                        except Exception as kyc_err:
                            logger.warning(f"[SWAPS][WARN] Row {idx + 1}: KYC panel not found — {kyc_err}")                        

                        page.go_back()
                        page.wait_for_selector(
                            "//div[@class='el-table__inner-wrapper']",
                            timeout=15000,
                        )
                        page.wait_for_timeout(1500)
                        self.close_detail_panel_idx(page)
                        rows = page.query_selector_all("//tr[@class='el-table__row']")
                    
                        scraped_rows += 1
                    

                    except Exception as row_exc:
                        logger.error(f"[SWAPS][ERROR] Row {idx + 1} detail failed: {row_exc}")
                        traceback.print_exc()
                        try:
                            self.close_detail_panel(page)
                            time.sleep(1)
                            rows = page.query_selector_all("//tr[@class='el-table__row']")
                        except Exception:
                            pass

                # ── Detect operator changes and record swap with the scraped data ─
                self._detect_and_record_swap_from_soup(soup, shortcode, swap_date=swap_date, row_details=row_details)

                # ── Mark shortcode as scraped today ──────────────────────────────
                SwapScrapeLog.log(shortcode, user_id=self.user_id)
                successfully_scraped.append(shortcode)

            except Exception as exc:
                logger.error(f"[SWAPS][ERROR] Failed for shortcode {shortcode}: {exc}")
                traceback.print_exc()

        # ── Notify the logged-in user by email ───────────────────────────────────
        if self.user and getattr(self.user, 'email', None):
            try:
                send_swaps_scraped_email(
                    recipient_email=self.user.email,
                    username=getattr(self.user, 'username', self.user.email),
                    total_shortcodes=len(successfully_scraped),
                    skipped_shortcodes=skipped_count,
                )
                logger.info(f"[SWAPS] Completion email sent to {self.user.email}.")
            except Exception as mail_exc:
                logger.warning(f"[SWAPS][WARN] Could not send completion email: {mail_exc}")


    def _parse_swap_operators_from_soup(self, soup: BeautifulSoup) -> List[Dict]:

        """
        Parse operator rows from the el-table__inner-wrapper soup.

        Column order (confirmed from debug HTML):
          0  Identity ID | 1  Org Short Code | 2  Org Name | 3  Operator ID
          4  Status      | 5  User Name(MSISDN) | 6  MSISDN | 7  Role
          8  First Name  | 9  Middle Name    | 10 Last Name | 11 DOB
          12 Suspended   | 13 Operation (button)
        """
        operators = []
        tbody = soup.find("tbody")
        if not tbody:
            return operators

        for row in tbody.find_all("tr", recursive=False):
            cells = row.find_all("td")
            if len(cells) < 13:
                continue

            def _cell(i):
                return cells[i].get_text(strip=True) if i < len(cells) else ""

            status = _cell(4)
            suspended = _cell(12)
            msisdn = _cell(5) or _cell(6)
            if msisdn in ("-", ""):
                msisdn = None

            operators.append({
                "identity_id": _cell(0),
                "shortcode":   _cell(1),
                "firstname":   _cell(8),
                "middlename":  _cell(9),
                "lastname":    _cell(10),
                "phone_number": msisdn,
                "role":        _cell(7),
                "status":      status,
                "date_of_birth": _cell(11),
                "is_active":   status.startswith("Active") and suspended != "Yes",
            })

        return operators


    def _upsert_swap_user_agent(self, op: Dict, agent_company) -> "UserAgent | None":

        """
        Find or create a UserAgent for a scraped operator row.
        Uses phone_number as primary key; falls back to identity_id stored
        as 'MPESA-{identity_id}' in the idnumber field.
        """
        from app.model.useragent import UserAgent, user_agent_companies

        ua = None
        if op.get("phone_number"):
            ua = UserAgent.query.filter_by(phone_number=op["phone_number"]).first()

        idnumber_fallback = f"MPESA-{op['identity_id']}"
        if ua is None:
            ua = UserAgent.query.filter_by(idnumber=idnumber_fallback).first()

        if ua is None:
            try:
                ua = UserAgent(
                    firstname=op["firstname"] or "Unknown",
                    lastname=op["lastname"] or "Unknown",
                    idnumber=idnumber_fallback,
                    phone_number=op.get("phone_number"),
                    operator_role=op.get("role"),
                    user_id=self.user_id,
                    agent_company_id=agent_company.id,
                )
                db.session.add(ua)
                db.session.flush()
            except Exception as e:
                logger.warning(f"[SWAPS] Could not create UserAgent for {op}: {e}")
                db.session.rollback()
                return None
        else:
            if op.get("role") and ua.operator_role != op["role"]:
                ua.operator_role = op["role"]

        # Ensure the M2M link to this AgentCompany exists
        existing_link = db.session.execute(
            db.select(user_agent_companies).where(
                (user_agent_companies.c.user_agent_id == ua.id) &
                (user_agent_companies.c.agent_company_id == agent_company.id)
            )
        ).first()
        if not existing_link:
            try:
                db.session.execute(
                    user_agent_companies.insert().values(
                        user_agent_id=ua.id,
                        agent_company_id=agent_company.id,
                        created_at=datetime.now(),
                    )
                )
            except Exception:
                pass  # duplicate key — already linked

        return ua


    def _parse_registration_time_from_basic_info(self, basic_info_html: str) -> Optional[datetime]:

        """Return the 'Registration Time' datetime parsed from a basic-info section HTML, or None."""
        from bs4 import NavigableString
        soup = BeautifulSoup(basic_info_html, "html.parser")
        for form_item in soup.find_all(class_="el-form-item"):
            label_div = form_item.find(class_="el-form-item__label")
            if not label_div or "Registration Time" not in label_div.get_text():
                continue
            content_div = form_item.find(class_="el-form-item__content")
            if not content_div:
                continue
            date_str = next(
                (t.strip() for t in content_div.children if isinstance(t, NavigableString) and t.strip()),
                "",
            )
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        return None


    def _parse_kyc_details(self, kyc_html: str) -> dict:

        """Extract ID number/type and preferred phone from a KYC form HTML section."""
        soup = BeautifulSoup(kyc_html, "html.parser")
        result: dict = {"id_number": None, "id_type": None, "phone_number": None}

        # ID Number from the ID Details table — first non-empty row
        for row in soup.find_all("tr", class_="el-table__row"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                id_type_text  = cells[0].get_text(strip=True)
                id_number_text = cells[1].get_text(strip=True)
                if id_number_text and id_number_text not in ("-", ""):
                    result["id_type"]   = id_type_text
                    result["id_number"] = id_number_text
                    break

        # Phone from "Preferred Contact Phone Number"
        for label_el in soup.find_all(class_="el-form-item__label"):
            if "Preferred Contact Phone Number" not in label_el.get_text():
                continue
            content = label_el.find_next_sibling(class_="el-form-item__content")
            if not content:
                # label is inside el-form-item; content is a sibling of label's parent
                parent = label_el.parent
                if parent:
                    content = parent.find(class_="el-form-item__content")
            if content:
                span = content.find("span", class_="view_span")
                phone = span.get_text(strip=True) if span else content.get_text(strip=True)
                if phone and phone not in ("-", ""):
                    result["phone_number"] = phone
            break

        return result


    def _detect_and_record_swap_from_soup(self, soup: BeautifulSoup, shortcode: str, swap_date: Optional[datetime] = None, row_details: Optional[dict] = None) -> None:

        """
        The table already encodes the full swap story:
          - Status == 'Active'  → current operators (new_agents)
          - Status == 'Closed'  → swapped-out operators (previous_agents)

        A swap record is created whenever there is at least one Closed operator.
        Duplicate suppression: skip if the most recent AgentSwap for this company
        already has the same set of Closed identity_ids.
        """
        from app.model.agent_swap import AgentSwap

        agent_company = agent_company_service.get_agent_company_by_shortcode_(str(shortcode))
        if not agent_company:
            logger.info(f"[SWAPS] No AgentCompany for shortcode {shortcode} — skipping.")
            return

        scraped = self._parse_swap_operators_from_soup(soup)

        # Enrich each operator with KYC details captured during the detail drill-down
        if row_details:
            for i, op in enumerate(scraped):
                detail = row_details.get(i, {})
                if detail.get("phone_number"):
                    op["phone_number"] = detail["phone_number"]
                if detail.get("id_number"):
                    op["kyc_id_number"] = detail["id_number"]
                    op["kyc_id_type"]   = detail.get("id_type")
                if detail.get("reg_time"):
                    op["registration_time"] = detail["reg_time"].isoformat()

        active_ops = [op for op in scraped if op["is_active"]]
        closed_ops = [op for op in scraped if op["status"] == "Closed"]


        if not closed_ops:
            logger.info(f"[SWAPS] {shortcode}: no closed operators, nothing to record.")
            return

        # ── Build JSON payloads (no UserAgent upsert — KYC scraper owns that) ────
        def _build_payload(ops):
            payload = []
            for op in ops:
                payload.append({
                    "identity_id":       op["identity_id"],
                    "name":              f"{op['firstname']} {op['middlename']} {op['lastname']}".strip(),
                    "phone_number":      op.get("phone_number"),
                    "role":              op.get("role"),
                    "idnumber":          op.get("kyc_id_number") or f"MPESA-{op['identity_id']}",
                    "kyc_id_number":     op.get("kyc_id_number"),
                    "kyc_id_type":       op.get("kyc_id_type"),
                    "registration_time": op.get("registration_time"),
                })
            return payload

        # ── Duplicate check against the most recent swap for this company ─────────
        closed_identity_ids = {op["identity_id"] for op in closed_ops}
        latest_swap = (
            AgentSwap.query
            .filter_by(agent_company_id=agent_company.id)
            .order_by(AgentSwap.swap_date.desc())
            .first()
        )
        if latest_swap:
            stored_prev_ids = {
                a.get("identity_id", "")
                for a in (latest_swap.previous_agents or [])
            }
            if stored_prev_ids == closed_identity_ids:
                # Duplicate detected — but if we have fresh KYC data, enrich the existing record
                if row_details:
                    all_stored = (latest_swap.previous_agents or []) + (latest_swap.new_agents or [])
                    needs_enrichment = any(
                        not a.get("kyc_id_number") and not a.get("registration_time")
                        for a in all_stored
                    )
                    if needs_enrichment:
                        try:
                            latest_swap.previous_agents = _build_payload(closed_ops)
                            latest_swap.new_agents = _build_payload(active_ops)
                            db.session.commit()
                            logger.info(f"[SWAPS] {shortcode}: enriched existing AgentSwap #{latest_swap.id} with KYC/reg data.")
                        except Exception as e:
                            db.session.rollback()
                            logger.error(f"[SWAPS][ERROR] {shortcode}: Failed to enrich swap #{latest_swap.id}: {e}")
                    else:
                        logger.info(f"[SWAPS] {shortcode}: duplicate — already enriched, skipping.")
                else:
                    logger.info(f"[SWAPS] {shortcode}: duplicate — same closed operators already recorded.")
                return

        previous_agents_data = _build_payload(closed_ops)
        new_agents_data      = _build_payload(active_ops)

        # ── Persist the AgentSwap record ─────────────────────────────────────────
        try:
            swap = AgentSwap(
                agent_company_id=agent_company.id,
                initiated_by=self.user_id,
                swap_date=swap_date or datetime.now(),
                previous_agents=previous_agents_data,
                new_agents=new_agents_data,
                notes=f"Auto-detected by scraper (shortcode {shortcode})",
                status="completed",
            )
            db.session.add(swap)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"[SWAPS][ERROR] {shortcode}: Failed to save AgentSwap: {e}")
            traceback.print_exc()


    def select_first_float_option_by_index(self, page) -> bool:

        """Selects the first 'Float Account/XXXXX' option from dropdown."""
        try:
            logger.info("[INFO] Looking for Float Account option...")
            page.wait_for_timeout(1000)
        
            float_pattern = re.compile(r'Float Account/\d+', re.IGNORECASE)
        
            # Use locator instead of query_selector_all for better reliability
            options = page.locator("//ul[contains(@class, 'el-select-dropdown__list')]//li")
            option_count = options.count()
        
            logger.info(f"[DEBUG] Found {option_count} dropdown options")
        
            for i in range(option_count):
                try:
                    opt = options.nth(i)
                    opt_text = opt.inner_text().strip()
                
                    if float_pattern.search(opt_text):
                        logger.info(f"[INFO] Found Float Account: {opt_text}")
                        opt.click()
                        page.wait_for_timeout(1000)
                        return True
                    
                except Exception as e:
                    logger.error(f"[WARN] Error reading option {i + 1}: {e}")
                    continue
        
            logger.error("[ERROR] No Float Account option found")
            return False
        
        except Exception as exc:
            logger.error(f"[ERROR] Float option selection failed: {exc}")
            return False

    def scroll_to_top(self, page: Page) -> None:

        """
        Scrolls to the top of the page.
    
        Args:
            page: Playwright Page object
        """
        try:
            page.evaluate("window.scrollTo(0, 0);")
            logger.info("[SUCCESS] Scrolled to top of page")
            time.sleep(0.5)  
        except Exception as e:
            logger.error(f"[ERROR] Failed to scroll to top: {e}")

    def scroll_to_bottom(self, page: Page) -> None:

        """
        Scrolls to the bottom of the page.
    
        Args:
            page: Playwright Page object
        """
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            logger.info("[SUCCESS] Scrolled to bottom of page")
            time.sleep(1.5)  
        except Exception as e:
            logger.error(f"[ERROR] Failed to scroll to bottom: {e}")

    def extract_extra_till_info(self, page: Page, extra_info: dict) -> Dict[str, Any]:

        """Extracts additional till information from the account details section."""
        try:
            # Wait for the account information section to load
            # Adjust the selector based on your actual page structure
            account_info_section = page.wait_for_selector(".el-col .basic-info-card", timeout=5000)
        
            # Get all the basic-info-card elements
            all_cards = page.query_selector_all(".el-col .basic-info-card")

            extracted_data = {}
        
            for card in all_cards:
                try:
                    # Extract label and value from each card
                    label_element = card.query_selector(".basic-info-card__label")
                    value_element = card.query_selector(".basic-info-card__value")
                
                    if label_element and value_element:
                        label = label_element.inner_text().strip().replace(':', '').replace('.', '')
                        value = value_element.inner_text().strip()
                    
                        # Convert label to snake_case for easier use as dictionary key
                        label_key = label.lower().replace(' ', '_').replace('.', '').replace(':', '')
                    
                        # Clean up the value (remove commas from numbers)
                        if label_key in ['current_balance', 'available_balance', 'reserved_balance', 'unclearbalance']:
                            # Remove commas and convert to Decimal
                            value = value.replace(',', '')
                            try:
                                value = Decimal(value)
                            except:
                                # Keep as string if conversion fails
                                pass
                    
                        # Handle special cases
                        if label_key == 'unclearbalance':
                            label_key = 'unclear_balance'  # Standardize naming
                        elif label_key == 'is_hot_account':
                            value = value.lower() == 'yes'  # Convert to boolean
                    
                        extracted_data[label_key] = value
                except Exception as card_error:
                    logger.error(f"[WARNING] Error processing card: {card_error}")
                    continue
        
            # Now merge with the existing extra_info
            if extracted_data:
                logger.info(f"[INFO] Extracted {len(extracted_data)} account details:")
            
                for key, value in extracted_data.items():
                    if(key == "status" and value !="Active"):
                        self.send_alert_on_non_active_(self.user.email,
                                                  business_name=extra_info.get('company_name'),
                                                  business_short_code=extra_info.get("short_code"),
                                                  status=value)
                    
                    logger.info(f"  {key}: {value}")
            
                # Add the extracted data to extra_info
                extra_info.update({
                    'account_details': extracted_data,
                    'account_number': extracted_data.get('account_no'),
                    'account_type': extracted_data.get('account_type'),
                    'account_alias': extracted_data.get('alias'),
                    'account_currency': extracted_data.get('currency'),
                    'account_relationship': extracted_data.get('account_relationship'),
                    'current_balance': extracted_data.get('current_balance'),
                    'available_balance': extracted_data.get('available_balance'),
                    'account_status': extracted_data.get('status'),
                    'is_hot_account': extracted_data.get('is_hot_account'),
                    'account_scraped_at': datetime.now()
                })
            
            save_results = agent_company_service.save_or_update_scraped_agent_company(mapped_data=extra_info,user_id=self.user_id)
        
            logger.info(f"[DEBUG] Saved results: {save_results}")
            return save_results
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to extract extra till info: {e}")
            # Return the original extra_info dict without modifications
            return extra_info

    def send_alert_on_non_active_(
        self,
        recipient_email: str,
        business_name: str,
        business_short_code: str,
        status: str
    ):
        try:
            # 1. Fetch existing outbox record
            email_outbox = EmailOutboxService.get_by_business_and_reason(
                business_short_code=business_short_code,
                reason="NON_ACTIVE_AGENT"
            )

            # Since service returns a list, get the first one for this receiver
            email_outbox = next(
                (e for e in email_outbox if e.receiver == recipient_email),
                None
            )

            # 2. Stop if max attempts reached
            if email_outbox and (email_outbox.sent_times or 0) >= self.MAX_SEND_ATTEMPTS:
                return

            # 3. Send the email
            send_not_active_short_code_(
                recipient_email=recipient_email,
                business_name=business_name,
                business_short_code=business_short_code,
                company_code=business_short_code,
                status=status
            )

            # 4. Update or create using the service
            if email_outbox:
                email_outbox_service.update(
                    email_outbox.id,
                    sent_times=(email_outbox.sent_times or 0) + 1
                )
            else:
                email_outbox_service.create(
                    sender=self.user.email,
                    receiver=recipient_email,
                    reason="NON_ACTIVE_AGENT",
                    business_short_code=business_short_code,
                    sent_times=1
                )

        except Exception as e:
            logger.error(f"[ERROR] An error occurred: {str(e)}")
     
       
    def save_table_to_dataframe_(self, page: Page, business_shortcode: int,category:str) -> tuple:

        """Extract all rows from paginated table and save to CSV."""
        try:
            logger.info("[INFO] Starting table extraction...")

            # get the latest receipt number for this shortcode
            latest_receipt_number = self.till_scraping_shortfall[business_shortcode][1]
            logger.info(f"The latest receipt number for {business_shortcode} is {latest_receipt_number}")
        
            try:                
                page.wait_for_load_state("networkidle", timeout=10000)
                body_tbl = page.wait_for_selector(
                    "//table[@class='el-table__body']",
                    timeout=10000
                )
        
                if not body_tbl.is_visible():
                    return None, None
            except Exception as e:
                logger.warning("[WARN] Table body not visible, ending extraction.")
                return None, None        
            soup = BeautifulSoup(body_tbl.inner_html(), "html.parser")
            tbody = soup.find("tbody")
        
            trs = tbody.find("tr") if tbody else None
            # first_tr = trs[0] if trs and len(trs) > 0 else None
        
            span = soup.find("span", class_="receipt-link")
            if span:
                transaction_id = span.get_text(strip=True)
                self.click_receipt_link(page,transaction_id)
                time.sleep(15)
            else:
                logger.warning("Not found")
        
        except Exception as exc:
            logger.error(f"[ERROR] Table extraction failed: {exc}")
            traceback.print_exc()
            return None, None

    def get_latest_receipt_no(self, page: Page, business_shortcode: int, pass_value: str) -> str:

        """Extract all rows from paginated table and process receipt links from match point to latest."""
        logger.info("[INFO] Starting table extraction...")

        # Add thread safety if needed (uncomment if multi-threaded)
        # with till_scraping_lock:
    
        # Check dictionary existence and structure
        if not isinstance(self.till_scraping_shortfall, dict):
            logger.error(f"[ERROR] self.till_scraping_shortfall is not a dictionary")
            return None
        
        logger.info(f"The till scraping shortfall has {len(self.till_scraping_shortfall)} entries")
    
        # Check if key exists
        if business_shortcode not in self.till_scraping_shortfall:
            # Try converting to string if business_shortcode is int but keys are strings
            if str(business_shortcode) in self.till_scraping_shortfall:
                business_shortcode = str(business_shortcode)
            else:
                logger.error(f"[ERROR] Business shortcode {business_shortcode} not found")
                logger.info(f"Available keys (first 10): {list(self.till_scraping_shortfall.keys())[:10]}")
                return None
    
        # Check value structure
        value = self.till_scraping_shortfall[business_shortcode]
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            logger.error(f"[ERROR] Invalid structure for {business_shortcode}: {value}")
            return None
        
        latest_receipt_number = str(value[1])
        logger.info(f"The latest receipt number for {business_shortcode} is {latest_receipt_number}")
        return latest_receipt_number

    def save_table_to_dataframe_latest_(self, page: Page, business_shortcode: int, pass_value: str, additional_category: str) -> tuple:

        """Extract all rows from paginated table and process receipt links from match point to latest."""
        # try:
        logger.info("[INFO] Starting table extraction...")
        headers = []
        all_data_rows = []
    
        success = self.click_search_button(page=page)        
    
        if not success:
            logger.error(f"[ERROR] Can not select the search button")
    
        self.select_pagination_size(page=page)
        # Get the latest receipt number for this shortcode
        # logger.info(f"The till scraping shortfall {till_scraping_shortfall}")
        
            # Extract headers
        header_tbl = page.wait_for_selector(
            "//table[@class='el-table__header']",
            timeout=10000
        )
    
        soup = BeautifulSoup(header_tbl.inner_html(), "html.parser")
        tr = soup.find("thead").find("tr")
        headers = [th.get_text(strip=True) for th in tr.find_all("th")]
        logger.info(f"[SUCCESS] Headers: {headers}")
    
        #
        self.scroll_to_bottom(page)
    
        # Paginate through all data
        page_no = 1
        time.sleep(1)  
        logger.info(f"\n[INFO] Extracting page {page_no}...")
    
        try:                
            page.wait_for_load_state("networkidle", timeout=10000)
            body_tbl = page.wait_for_selector(
                "//table[@class='el-table__body']",
                timeout=10000
            )
    
            if not body_tbl.is_visible():
                return None, None
        except Exception as e:
            logger.warning("[WARN] Table body not visible, ending extraction.")
            return None, None
        
        soup = BeautifulSoup(body_tbl.inner_html(), "html.parser")
        tbody = soup.find("tbody")

        if tbody:
            for tr in tbody.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(cells) == len(headers):
                    all_data_rows.append([business_shortcode] + cells)
    

        # Create DataFrame
        if not all_data_rows:
            logger.warning("[WARN] No data rows extracted")
            df = pd.DataFrame(columns=["OrganizationRowIndex"] + headers)
        else:
            df = pd.DataFrame(all_data_rows, columns=["OrganizationRowIndex"] + headers)
            logger.info(f"[SUCCESS] Extracted {len(df)} total rows")
    
            # Update transactions
        results = transaction_service.update_transactions_from_dataframe(
            df=df,
            transaction_type=additional_category,
            company_shortcode=self.company_shortcode,
            agent_id=None,
            business_shortcode=business_shortcode
        )
        success_value = results.get('success', False)
        if success_value:
            summary = results.get('summary', {})
            logger.info(f"\n Success!")
            logger.info(f"   Updated: {summary.get('updated_count', 0)}")
            logger.info(f"   Created: {summary.get('created_count', 0)}")
            logger.info(f"   Total: {summary.get('total_processed', 0)}")
            logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
        else:
            logger.error(f"\n Failed: {results.get('error', 'Unknown error')}")
        
        return df, success_value
    
    def parse_element_plus_transactions(self, html_content: str, transaction_type: str, business_shortcode: str) -> tuple:

        """
        Parse an Element Plus (el-table) transaction table HTML into a pandas DataFrame.

        Expected column order (9 cols):
          0 Receipt No. | 1 Initiation Time | 2 Details | 3 Opposite Party |
          4 Transaction Status | 5 Withdrawn | 6 Paid In | 7 Currency | 8 Operation
        """
        soup = BeautifulSoup(html_content, "html.parser")
        rows = soup.select("tbody tr.el-table__row")
        data = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue

            # Col 0 — Receipt No.: text inside <span class="el-link__inner">
            receipt_span = cells[0].find("span", class_="el-link__inner")
            receipt_no = receipt_span.get_text(strip=True) if receipt_span else cells[0].get_text(strip=True)

            # Col 1 — Initiation Time (also used as completion time; no separate field in this view)
            initiation_time = cells[1].get_text(strip=True)

            # Col 2 — Details
            details = cells[2].get_text(strip=True)

            # Col 3 — Opposite Party → stored as Other Party Info
            other_party = cells[3].get_text(strip=True)

            # Col 4 — Transaction Status: skip the status-circle span, take the text span
            status_spans = cells[4].find_all("span")
            status = next(
                (s.get_text(strip=True) for s in status_spans if "status-circle" not in s.get("class", [])),
                cells[4].get_text(strip=True)
            )

            # Col 5 — Withdrawn (values like "-634.60"; dash → 0)
            withdrawn_raw = cells[5].get_text(strip=True)
            withdrawn = withdrawn_raw.replace(",", "") if withdrawn_raw not in ("-", "") else "0.00"

            # Col 6 — Paid In (dash → 0)
            paid_in_raw = cells[6].get_text(strip=True)
            paid_in = paid_in_raw.replace(",", "") if paid_in_raw not in ("-", "") else "0.00"

            # Col 7 — Currency
            currency = cells[7].get_text(strip=True) if len(cells) > 7 else "KES"

            data.append({
                "Receipt No.": receipt_no,
                "Completion Time": initiation_time,
                "Initiation Time": initiation_time,
                "Details": details,
                "Transaction Status": status,
                "Paid In": paid_in,
                "Withdrawn": withdrawn,
                "Balance": "0.00",
                "Balance Confirmed": "",
                "Reason Type": details,
                "Other Party Info": other_party,
                "Linked Transaction ID": "",
                "A/C No.": "",
                "Currency": currency,
            })

        df = pd.DataFrame(data)

        numeric_cols = ["Paid In", "Withdrawn", "Balance"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
        # Update transactions
        results = transaction_service.update_transactions_from_dataframe(
            df=df,
            transaction_type=transaction_type,
            company_shortcode=self.company_shortcode,
            agent_id=None,
            business_shortcode=business_shortcode
        )
        success_value = results.get('success', False)
        if success_value:
            summary = results.get('summary', {})
            logger.info(f"\n Success!")
            logger.info(f"   Updated: {summary.get('updated_count', 0)}")
            logger.info(f"   Created: {summary.get('created_count', 0)}")
            logger.info(f"   Total: {summary.get('total_processed', 0)}")
            logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
        else:
            logger.error(f"\n Failed: {results.get('error', 'Unknown error')}")
    
        return df,df.columns

    def save_table_to_dataframe_download(self, page: Page, business_shortcode: int, additional_category: str = "", _retry_count: int = 0) -> tuple:

        max_retries = 3
        try:
            self.close_irritative_dialog_box(page)
            logger.info(f"[EXPORT] Starting Excel export... (attempt {_retry_count + 1}/{max_retries})")

            export_trigger = page.locator("div.el-dropdown.padding-export >> span").first
            export_trigger.wait_for(state="visible", timeout=30000)
            export_trigger.scroll_into_view_if_needed()

            export_trigger.hover(force=True, timeout=10_000)
            logger.info("[EXPORT] Hovered successfully")
            time.sleep(3)  

            # 2. Wait for ANY dropdown menu to actually appear in the viewport (not just DOM)
            page.wait_for_function(
                """() => {
                    const menus = document.querySelectorAll('ul.el-dropdown-menu');
                    for (const menu of menus) {
                        const rect = menu.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && rect.top >= 0) {
                            return true;
                        }
                    }
                    return false;
                }""",
                timeout=40000
            )
            logger.info("[EXPORT] Export dropdown menu is visually open")

            # 3. Get ALL menu items from ALL dropdown menus
            all_items = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")

            # Find all items that contain "Excel" (case-sensitive match as in your UI)
            excel_items = all_items.filter(has_text="Excel")

            excel_count = excel_items.count()
            logger.info(f"[EXPORT] Found {excel_count} visible 'Excel' options across all dropdowns")

            if excel_count < 3:
                raise Exception(f"Expected at least 3 Excel export options, found only {excel_count}")

            target_excel = excel_items.nth(2)

            logger.info(f"[EXPORT] Targeting the 3rd 'Excel' option (index 2 in filtered list)")

            # 4. Click + download
            with page.expect_download(timeout=60_000) as download_info:
                # First try normal click
                try:
                    target_excel.click(force=True, timeout=15_000)
                    logger.info("[EXPORT] Clicked 'Excel' (All Data) successfully")
                except Exception as e:
                    logger.error("[EXPORT] Normal click failed, falling back to JS click...")
                    target_excel.evaluate("el => el.click()")

            download: Download = download_info.value

            # THIS IS THE MAGIC: Read bytes directly into pandas
            logger.info(f"[EXPORT] Reading {download.suggested_filename} directly into pandas...")
            temp_path = download.path()  # Playwright saves it temporarily
        
            df,success_value = self.update_transactions_from_file(
                file_path=temp_path,
                business_shortcode=business_shortcode,
                transaction_type=additional_category,
                company_shortcode=self.company_shortcode,
                agent_id=None
            )

            logger.info(f"[SUCCESS] Loaded DataFrame in-memory: {df.shape[0]} rows × {df.shape[1]} columns")
            logger.info(f"   Columns: {list(df.columns)}")

            return df, success_value
        except Exception as e:
            logger.error(f"[ERROR] An error has occurred {e}")
            if _retry_count + 1 >= max_retries:
                logger.error(f"[ERROR] Export failed after {max_retries} attempts — sending session timeout email")
                send_session_timeout_email(self.user.email)
                return pd.DataFrame(), False
            return self.save_table_to_dataframe_download(page=page, business_shortcode=business_shortcode, additional_category=additional_category, _retry_count=_retry_count + 1)


    def save_table_to_dataframe_download_head_office(
        self,
        page: Page,
        business_shortcode: int,
        additional_category: str = "",
        filter_text: str = "Excel",          # ← pass "CSV" (or anything else) to override
        min_item_count: int = 3,             # ← keep the threshold configurable too
        target_index: int = 2,              # ← which nth match to click
    ) -> tuple:
        """
        Excel/CSV export for the Head Office Commission view.
        Uses JS viewport coordinates for hover since Playwright sees the trigger as hidden.
        Returns empty DataFrame (not an error) when the export button is disabled (no data).

        Args:
            filter_text:     Text to match against dropdown items (default "Excel", pass "CSV" for child views).
            min_item_count:  Minimum number of matching items expected before raising (default 3).
            target_index:    Zero-based index of the matching item to click (default 2).
        """
        try:
            self.close_irritative_dialog_box(page)
            logger.info(f"[EXPORT] Starting Head Office export (filter='{filter_text}')...")

            visible_dropdown = page.locator("div.el-dropdown.padding-export:visible")
            try:
                visible_dropdown.wait_for(state="visible", timeout=10000)
            except Exception:
                logger.info("[EXPORT] No visible export dropdown — no data for this period")
                return pd.DataFrame(), False

            visible_dropdown.scroll_into_view_if_needed()
            time.sleep(0.5)

            coords = page.evaluate("""() => {
                const el = document.querySelector('div.el-dropdown.padding-export:not(.is-disabled) button');
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            }""")
            if not coords:
                raise Exception("Could not resolve export button viewport coordinates")

            page.mouse.move(coords['x'], coords['y'])
            logger.info("[EXPORT] Hovered via mouse coordinates")
            time.sleep(2)

            # Also dispatch mouseenter/mouseover in case the pointer-events model
            # doesn't fire the El-UI trigger purely from mouse.move().
            page.evaluate("""(xy) => {
                const el = document.querySelector('div.el-dropdown.padding-export:not(.is-disabled) button');
                if (el) {
                    el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true, cancelable: true, clientX: xy.x, clientY: xy.y }));
                    el.dispatchEvent(new MouseEvent('mouseover',  { bubbles: true, cancelable: true, clientX: xy.x, clientY: xy.y }));
                }
            }""", coords)
            time.sleep(1.5)

            menu_open = False
            for _attempt in range(3):
                try:
                    page.wait_for_function(
                        """() => {
                            const menus = document.querySelectorAll('ul.el-dropdown-menu');
                            for (const menu of menus) {
                                const rect = menu.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    return true;
                                }
                            }
                            return false;
                        }""",
                        timeout=8000
                    )
                    menu_open = True
                    break
                except Exception:
                    logger.info(f"[EXPORT] Dropdown not open yet (attempt {_attempt + 1}/3), re-hovering...")
                    page.mouse.move(0, 0)
                    time.sleep(0.3)
                    page.mouse.move(coords['x'], coords['y'])
                    page.evaluate("""(xy) => {
                        const el = document.querySelector('div.el-dropdown.padding-export:not(.is-disabled) button');
                        if (el) {
                            el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true, cancelable: true, clientX: xy.x, clientY: xy.y }));
                            el.dispatchEvent(new MouseEvent('mouseover',  { bubbles: true, cancelable: true, clientX: xy.x, clientY: xy.y }));
                        }
                    }""", coords)
                    time.sleep(1.5)

            if not menu_open:
                # Last resort: debug what menus exist and their rects
                menu_debug = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('ul.el-dropdown-menu')).map(m => {
                        const r = m.getBoundingClientRect();
                        return { w: r.width, h: r.height, top: r.top, display: getComputedStyle(m).display };
                    });
                }""")
                logger.info(f"[EXPORT] Menu debug state: {menu_debug}")
                raise Exception("Export dropdown did not open after 3 hover attempts")

            logger.info("[EXPORT] Export dropdown menu is visually open")

            all_items = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")
            matched_items = all_items.filter(has_text=filter_text)          # ← dynamic
            matched_count = matched_items.count()
            logger.info(f"[EXPORT] Found {matched_count} visible '{filter_text}' options across all dropdowns")

            if matched_count < min_item_count:
                raise Exception(
                    f"Expected at least {min_item_count} '{filter_text}' export options, "
                    f"found only {matched_count}"
                )

            target_item = matched_items.nth(target_index)
            logger.info(f"[EXPORT] Targeting '{filter_text}' option at index {target_index}")

            # Resolve the item's viewport coordinates so we can click via raw mouse
            # movement — moving the mouse to an element coordinate keeps the El-UI
            # dropdown open, whereas Playwright's element .click() internally dispatches
            # focus/blur events that close the portal before the click lands.
            item_coords = target_item.evaluate("""el => {
                const r = el.getBoundingClientRect();
                return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
            }""")
            logger.info(f"[EXPORT] Item coords resolved: {item_coords}")

            with page.expect_download(timeout=60_000) as download_info:
                if item_coords and item_coords.get('x') and item_coords.get('y'):
                    # Slide mouse from trigger into menu item, then click — no element
                    # click events that would collapse the dropdown
                    page.mouse.move(item_coords['x'], item_coords['y'])
                    time.sleep(0.3)
                    page.mouse.click(item_coords['x'], item_coords['y'])
                    logger.info(f"[EXPORT] Clicked '{filter_text}' via mouse coordinates")
                else:
                    # Coords unavailable — try JS click as a last resort
                    logger.warning("[EXPORT] Could not resolve item coords, falling back to JS click...")
                    target_item.evaluate("el => el.click()")

            download: Download = download_info.value
            logger.info(f"[EXPORT] Reading {download.suggested_filename} directly into pandas...")
            temp_path = download.path()

            # M-PESA sometimes returns a JSON error payload instead of a spreadsheet.
            # Detect this before handing the file to pandas.
            try:
                import json as _json
                with open(temp_path, "rb") as _f:
                    _peek = _f.read(1024).lstrip()
                if _peek.startswith(b"{"):
                    _err = _json.loads(_peek + b"}")  # best-effort parse
                    _header = _err.get("header", _err)
                    _code = _header.get("responseCode", "?")
                    _desc = _header.get("responseDesc", "unknown")
                    logger.error(f"[EXPORT] M-PESA returned an error payload (code={_code}): {_desc}")
                    return pd.DataFrame(), False
            except Exception:
                pass  # not JSON — proceed normally

            # If the download is a CSV it's the Head Office Balance Overview (Level 1/2
            # hierarchy), not a transaction export. Parse and upsert commission balances.
            if (download.suggested_filename or '').lower().endswith('.csv'):
                logger.info("[EXPORT] CSV detected — parsing as Head Office commission balance overview")
                result = transaction_service.save_head_office_commission_balances(
                    csv_path=temp_path,
                    parent_shortcode=business_shortcode,
                )
                if result.get('success'):
                    s = result['summary']
                    logger.warning(f"[EXPORT] Commission balances saved: created={s['created']} updated={s['updated']} skipped={s['skipped']}")
                else:
                    logger.error(f"[EXPORT] Commission balance save failed: {result.get('error')}")
                return pd.DataFrame(), result.get('success', False)

            df, success_value = self.update_transactions_from_file(
                file_path=temp_path,
                business_shortcode=business_shortcode,
                transaction_type=additional_category,
                company_shortcode=self.company_shortcode,
                agent_id=None
            )

            logger.info(f"[SUCCESS] Head Office export loaded: {df.shape[0]} rows × {df.shape[1]} columns")
            return df, success_value

        except Exception as e:
            logger.error(f"[ERROR] Head Office export failed: {e}")
            return None, False
    def process_detailed_receipt(self, page: Page, receipt_no: str, transaction_type: str = 'float'):

        try:
            # Wait for the detailed view
            page.wait_for_selector("//div[contains(@class, 'portal-collapse-content')]", timeout=15000)
        
            # Get HTML
            detailed_html = page.inner_html(selector="//div[contains(@class, 'portal-collapse-content')]")
        
            # Update transaction
            result = transaction_service.update_transaction_with_detailed_info(
                receipt_no=receipt_no,
                detailed_html=detailed_html,
                transaction_type=transaction_type,
                commit=True
            )
        
            logger.info(f"[DETAIL] {result['message']}")
            return result["success"]
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to process detailed receipt {receipt_no}: {str(e)}")
            return False    

    def update_transactions_from_file(self, file_path, business_shortcode, transaction_type, company_shortcode, agent_id):

        """
        Update transactions directly from a file
        """
    
        success_value : bool = False
    
        logger.info(f"Processing file: {file_path}")
        logger.info(f"Business: {business_shortcode}")
        logger.info(f"Type: {transaction_type}")
    
        # Read the file
        df = pd.read_excel(file_path, skiprows=6)
    
        logger.info(f"Data shape: {df.shape}")
        logger.info(f"Sample data:")
    
        # Update transactions
        results = transaction_service.update_transactions_from_dataframe(
            df=df,
            transaction_type=transaction_type,
            company_shortcode=self.company_shortcode,
            agent_id=agent_id,
            business_shortcode=business_shortcode
        )
        success_value = results.get('success', False)
        if success_value:
            summary = results.get('summary', {})
            logger.info(f"\n Success!")
            logger.info(f"   Updated: {summary.get('updated_count', 0)}")
            logger.info(f"   Created: {summary.get('created_count', 0)}")
            logger.info(f"   Total: {summary.get('total_processed', 0)}")
            logger.info(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
        else:
            logger.error(f"\n Failed: {results.get('error', 'Unknown error')}")
    
        # Save the processed file
        logger.info(f"💾 Saved to: {business_shortcode}_{transaction_type}.xlsx")
    
        return df, success_value


    def is_till_frozen(self, page:Page)-> bool:

    
        try:
            div_frozen = page.wait_for_selector("//div[normalize-space()='Frozen']",timeout=1000)
            return div_frozen.is_visible()
        except Exception as e:
            logger.info(f"The till is not frozen {str(e)}")
            return False

    def clean_label_for_db(self, label: str) -> str:

        """
        Clean label string to be used as a database field identifier
        """
        # Convert to lowercase and replace spaces with underscores
        cleaned = label.lower().strip()
        cleaned = cleaned.replace(" ", "_")
        cleaned = cleaned.replace("-", "_")
        cleaned = cleaned.replace(":", "")
        cleaned = cleaned.replace(".", "")
    
        # Specific mappings for common labels
        label_mapping = {
            'parent_short_code': 'parent_short_code',
            'identity_model': 'identity_model',
            'hierarchy_level': 'hierarchy_level',
            'top_organization': 'top_organization',
            'organization_name': 'organization_name',
            'short_code': 'short_code',
            'identity_status': 'identity_status',
            'segment': 'segment',
            'charge_profile': 'charge_profile',
            'rule_profile': 'rule_profile',
            'trust_level': 'trust_level',
            'registration_date': 'registration_date'
        }
    
        return label_mapping.get(cleaned, cleaned)

    def parse_date_string(self, date_str: str) -> datetime.date:

        """
        Parse date string in various formats to datetime.date
        """
        if not date_str:
            return None
    
        # Try different date formats
        date_formats = [
            '%d-%m-%Y',  # 19-03-2025
            '%Y-%m-%d',  # 2025-03-19
            '%d/%m/%Y',  # 19/03/2025
            '%Y/%m/%d',  # 2025/03/19
            '%d.%m.%Y',  # 19.03.2025
        ]
    
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    
        return None

    def map_scraped_data_to_agent_company(self, scraped_data: dict) -> dict:

        """
        Map scraped data to AgentCompany model fields
        """
        # Based on your console output, the keys might be in Title Case
        # Let's try to handle both Title Case and lowercase versions
        def get_value(key):
            # Try title case first (from your print output)
            title_key = key.title().replace('_', ' ')
            if title_key in scraped_data:
                return scraped_data[title_key]
            # Try lowercase
            if key in scraped_data:
                return scraped_data[key]
            # Try with underscores
            underscore_key = key.lower().replace(' ', '_')
            if underscore_key in scraped_data:
                return scraped_data[underscore_key]
            return None
    
        mapped_data = {
            'company_name': get_value('organization_name') or scraped_data.get('Organization Name'),
            'business_short_code': scraped_data.get('business_short_code') or scraped_data.get('business_short_code'),
            'registration_number': f"SCRAPED-{get_value('short_code') or scraped_data.get('Short Code') or 'UNKNOWN'}",
            'location': get_value('location') or scraped_data.get('Location', 'Unknown'),
            'identity_model': get_value('identity_model') or scraped_data.get('Identity Model'),
            'hierarchy_level': get_value('hierarchy_level') or scraped_data.get('Hierarchy Level'),
            'top_organization': get_value('top_organization') or scraped_data.get('Top Organization'),
            'organization_name': get_value('organization_name') or scraped_data.get('Organization Name'),
            'short_code': get_value('short_code') or scraped_data.get('Short Code'),
            'identity_status': get_value('identity_status') or scraped_data.get('Identity Status'),
            'segment': get_value('segment') or scraped_data.get('Segment'),
            'charge_profile': get_value('charge_profile') or scraped_data.get('Charge Profile'),
            'rule_profile': get_value('rule_profile') or scraped_data.get('Rule Profile'),
            'trust_level': get_value('trust_level') or scraped_data.get('Trust Level'),
            'data_source': 'portal',
            'is_verified': False,
            'self.user_id': self.user_id
        }
    
        # Handle registration date
        reg_date = get_value('registration_date') or scraped_data.get('Registration Date')
        if reg_date:
            parsed_date = self.parse_date_string(reg_date)
            if parsed_date:
                mapped_data['registration_date'] = parsed_date
                mapped_data['established_date'] = parsed_date
    
        # Handle parent short code
        parent_short_code = get_value('parent_short_code') or scraped_data.get('Parent Short Code')
        if parent_short_code:
            mapped_data['parent_short_code'] = parent_short_code
    
        return mapped_data

    def scrape_till_details(self, page: Page, business_short_code: int) -> dict:

        """
        Scrape till details and return processed data
        """
        try:
            self.close_irritative_dialog_box(page)
            css_selector = ".portal-collapse .portal-collapse-content"
        
            # Wait for the selector to be available
            page.wait_for_selector(css_selector, state="attached", timeout=30000)
        
            # Get inner HTML
            inner_html = page.eval_on_selector(
                css_selector,
                "el => el.innerHTML"
            )
        
            # Extract till info
            till_info = self.extract_till_info(inner_html)
        
            logger.info(f"[INFO] Scraped till info for business short code {business_short_code}:")
            till_info['business_short_code'] = business_short_code
            for key, value in till_info.items():
                logger.info(f"  {key}: {value}")
        
            # Map to AgentCompany fields
            mapped_data = self.map_scraped_data_to_agent_company(till_info)
                        
            logger.info(f"[INFO] Map result for business short code {business_short_code}: {mapped_data}")

            return mapped_data
        
        except Exception as e:
            logger.error(f"[ERROR] Could not scrape till details: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'business_short_code': business_short_code
            }   


    def click_receipt_link(self, page:Page,transaction_id: str) -> bool:

        try:
            logger.info(f"Clicking receipt link for transaction ID: {transaction_id}")
            selector = f'span.receipt-link:has-text("{transaction_id}")'
            page.wait_for_selector(selector, state="visible",timeout=5000)
            page.click(selector)
            return self.extract_extra_details_on_receipt(page=page,receipt_no=transaction_id)
        except Exception as e:
            logger.error(f"Error clicking receipt link: {e}")
            return False


    def extract_extra_details_on_receipt(self, page:Page,receipt_no:str) -> bool:

        try:
            logger.info(f"[INFO] Trying to extract more details")
            transactions_div = page.wait_for_selector(selector="//div[@class='portal-collapse background-box section-box section-box-buttom bottom-radius']",
                                                      state="visible",
                                                      timeout=10000)
        
            transactions_div_html = transactions_div.inner_html()
        
            soup = BeautifulSoup(transactions_div_html,"html.parser")
        
            return True
        except Exception as e:
            logger.error(f"[ERROR] An error has occurred {str(e)}")                
            return False


    def extract_till_info(self, inner_html: str) -> dict:

        """
        Extracts till/organization information from the inner HTML of the portal-collapse-content div.
        Returns a dictionary with label → value pairs.
        """
        soup = BeautifulSoup(inner_html, "html.parser")
    
        till_info = {}
    
        # Each piece of information is in a .list-item
        for item in soup.find_all("div", class_="list-item"):
            # Label is in .content-item-label
            label_div = item.find("div", class_="content-item-label")
            if not label_div:
                continue
            label = label_div.get_text(strip=True)
        
            # Value is in .list-item__content-text inside .content-item
            value_div = item.find("div", class_="list-item__content-text")
            value = value_div.get_text(strip=True) if value_div else ""
        
            # Handle the "-" case as None or empty string if preferred
            if value == "-":
                value = None
            
            till_info[label] = value
    
        return till_info
    
    def save_table_to_dataframe_download_debug(self, page: Page, max_wait: int = 30_000):

        logger.info("[EXPORT] Starting Excel export...")

        export_trigger = page.locator("div.el-dropdown.padding-export >> span").first
        export_trigger.wait_for(state="visible", timeout=max_wait)
        export_trigger.scroll_into_view_if_needed()

        export_trigger.hover(force=True, timeout=10_000)
        logger.info("[EXPORT] Hovered successfully")

        # Give Vue time to open the dropdown
        time.sleep(2)  # or use wait_for_function as before

        logger.info("DROPDOWN MENU DEBUG INFO")

        # Method 1: Try get_by_role (what you were using)
        excel_by_role = page.get_by_role("menuitem", name="Excel", exact=True)
        logger.info(f"get_by_role('menuitem', name='Excel') → Found: {excel_by_role.count()} items")

        # Method 2: Raw locator for all menu items
        all_menu_items = page.locator("ul.el-dropdown-menu >> li.el-dropdown-menu__item")
        count = all_menu_items.count()
        logger.info(f"Total <li class='el-dropdown-menu__item'> found: {count}")

        # Print EVERY item with index + text + visibility
        for i in range(count):
            item = all_menu_items.nth(i)
            text = item.inner_text(timeout=5000).strip()
            is_visible = item.is_visible()
            is_enabled = item.is_enabled()
        
            logger.info(f"  [{i:2d}] '{text}' → visible={is_visible}, enabled={is_enabled}")

            # Highlight Excel ones
            if "excel" in text.lower():
                logger.info(f"     →→→ THIS IS AN EXCEL OPTION (index {i})")

        # Bonus: Show which one has the actual download behavior (usually the 3rd)
        excel_candidates = [i for i in range(count) if "excel" in all_menu_items.nth(i).inner_text().lower()]
        logger.info(f"\nExcel option indices: {excel_candidates}")
        logger.info(f"Recommended to click index: {excel_candidates[2] if len(excel_candidates) > 2 else 'Not enough!'}")

        logger.info("="*60 + "\n")

        # Stop here for debugging
        logger.info("Stopping for inspection. Comment out exit() when ready.")
    
    def first_day_of_quarter(self) -> str:

        """
        Returns the first calendar day of the current fiscal quarter
        in the format dd/MM/yyyy (e.g. 01/10/2025 for Q4 2025).
        """
        now = datetime.now()
        # Quarter number (1-based)
        quarter = (now.month - 1) // 3 + 1
        # First month of that quarter
        first_month = (quarter - 1) * 3 + 1
        # First day of that month, year unchanged
        first_day = now.replace(month=first_month, day=1)
        return first_day.strftime("%d/%m/%Y")

    def click_random_spot(self, page, padding: int = 50) -> None:

        """
        Clicks a random location inside the current viewport.
    
        Args:
            page: Playwright Page object
            padding: Minimum distance (px) from the edges to avoid clicking scrollbars, etc.
        """
        # 1. Get the current viewport size
        viewport = page.viewport_size
        if not viewport:
            raise RuntimeError("Viewport size not available – make sure the page is loaded.")

        width  = viewport["width"]
        height = viewport["height"]

        # 2. Calculate safe area (exclude padding from each side)
        x_min = padding
        x_max = width  - padding
        y_min = padding
        y_max = height - padding

        if x_max <= x_min or y_max <= y_min:
            raise ValueError(f"Padding {padding}px is too large for viewport {width}x{height}")

        # 3. Pick a random coordinate
        rand_x = random.randint(x_min, x_max)
        rand_y = random.randint(y_min, y_max)

        # 4. Click it
        page.mouse.click(rand_x, rand_y)
        logger.info(f"[Success] Clicked random spot at ({rand_x}, {rand_y})")

    def get_total_from_pagination(self, page) -> int | None:

        locator = page.locator("//div[@id='pagination']/span[contains(text(), 'Total')]").first
    
        try:
            if locator.count() == 0:
                logger.warning("[WARN] Total span not found in pagination")
                return None
            
            text = locator.inner_text().strip()          # e.g. "Total 103"
            number = int(''.join(filter(str.isdigit, text)))
            logger.info(f"[INFO] Detected total records: {number}")
            return number
        except Exception as e:
            logger.error(f"[ERROR] Could not parse total: {e}")
            return None
    
    def go_forth_on_organization(self, page: Page, row_count: int):

        """
        Clicks 'Next Page' if available. Returns True/False indicating if more pages exist.
        """
        next_page_btn = page.locator("//button[@aria-label='Go to next page']").first

        try:
            if next_page_btn.is_enabled():
                logger.info("[INFO] Clicking 'Next Page' button...")
                next_page_btn.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                time.sleep(0.5)
                return  True  # Continue processing
            else:
                logger.info(f"[INFO] Next page disabled. Finished all {row_count} rows on last page.")
                return  False

        except Exception as e:
            logger.error(f"[WARNING] Error clicking next page: {e}")
            self.user = User.query.filter_by(id=self.user_id).first()

            if self.user:
                # send_session_timeout_email(user.email, user.first_name)
                send_session_timeout_email(self.user.email)
            return False

    def go_previous_on_organisation(self, page: Page):

        """
        Clicks 'Next Page' if available. Returns True/False indicating if more pages exist.
        """
        prev_page_btn = page.locator("//button[@aria-label='Go to previous page']").first

        try:
            if prev_page_btn.is_enabled():
                logger.info("[INFO] Clicking 'Previous Page' button...")
                prev_page_btn.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                time.sleep(0.5)
                return True  # Continue processing
            else:
                logger.info(f"[INFO] Previous page disabled.")
                return False

        except Exception as e:
            logger.error(f"[WARNING] Error clicking previous page: {e}")
            return False

    def rerun_failed_codes(self, page: Page, failed_codes: List[int], max_retries: int = 2) -> bool:

        """
        Reprocess only the business_short_codes that previously failed.
        Navigates through all pages if needed to find and click the row.
        """
        from collections import defaultdict
        retry_count = defaultdict(int)  # Track retries per code
        original_failed = failed_codes.copy()

        for business_short_code in original_failed:
            retry_count[business_short_code] = 0

        remaining = set(original_failed)

        while remaining and max(retry_count.values()) < max_retries:
            logger.info(f"\n[RETRY] Retry attempt #{max(retry_count.values()) + 1} for {len(remaining)} items...")

            # Restart from first page for each retry pass
            self.go_previous_on_organisation(page)

            current_page = 1
            total_in_list = self.get_total_from_pagination(page)
            # Track which codes were actually encountered during this pass
            seen_this_pass: set = set()

            while True:
                self.wait_for_table_load(page)
                time.sleep(1)

                rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")

                for i in range(rows_locator.count()):
                    row = rows_locator.nth(i)
                    if not row.is_visible():
                        continue

                    current_code = None
                    try:
                        row_text = row.text_content(timeout=3000) or ""
                        match = re.search(r'^(\d+)', row_text.strip())
                        if not match:
                            continue
                        current_code = int(match.group(1))

                        if current_code not in remaining:
                            continue

                        seen_this_pass.add(current_code)
                        logger.error(f"[RETRY] Found failed row: {current_code} — reprocessing...")

                        row.click(timeout=15000)
                        page.wait_for_timeout(1000)

                        # Retried rows always come from _run_float_pass, so pass_value is "first"
                        success = self.process_single_row(page, current_code, row_number=f"RETRY-{current_code}", pass_value="first")

                        if success:
                            remaining.discard(current_code)
                            logger.info(f"[SUCCESS] Retry succeeded for {current_code}")
                        else:
                            retry_count[current_code] += 1
                            if retry_count[current_code] >= max_retries:
                                logger.error(f"[FAILED] Max retries reached for {current_code}")
                                remaining.discard(current_code)
                            else:
                                logger.info(f"[RETRY] Will retry {current_code} later (attempt {retry_count[current_code] + 1})")

                        time.sleep(1)

                    except Exception as e:
                        logger.error(f"[ERROR] Error during retry scan of row: {e}")
                        # Count the exception as a failed attempt to prevent an infinite loop
                        if current_code is not None and current_code in remaining:
                            seen_this_pass.add(current_code)
                            retry_count[current_code] += 1
                            if retry_count[current_code] >= max_retries:
                                logger.error(f"[FAILED] Max retries reached for {current_code} (exception path)")
                                remaining.discard(current_code)
                        continue

                if not remaining:
                    logger.error("[SUCCESS] All failed items successfully retried!")
                    break

                # Go to next page if we haven't scanned everything yet
                if self.go_forth_on_organization(page, total_in_list):
                    current_page += 1
                    logger.info(f"[INFO] Moving to page {current_page} for retry...")
                    time.sleep(2)
                else:
                    logger.info("[INFO] Reached last page during retry pass.")
                    break

            # Any codes still in `remaining` that were never seen on any page are
            # not in the table — count them as a failed attempt so the outer while
            # loop eventually terminates instead of spinning forever.
            not_found = remaining - seen_this_pass
            for code in list(not_found):
                retry_count[code] += 1
                logger.warning(f"[RETRY] Code {code} not found in table (attempt {retry_count[code]})")
                if retry_count[code] >= max_retries:
                    logger.error(f"[FAILED] Giving up on {code} — not found after {max_retries} passes")
                    remaining.discard(code)

            if not remaining:
                break

        # Final summary
        if remaining:
            logger.error(f"[WARNING] These codes failed even after {max_retries} retries: {remaining}")
        else:
            logger.error("[SUCCESS] All previously failed organizations were successfully recovered!")
            failed_codes.clear()
            return True
        
    def select_account_dropdown(self, page: Page, account_name: str, arrow_down_count: int) -> bool:

        """
        Generic function to select any account dropdown (Float or Commission)
        """
        try:
            logger.info(f"[INFO] Selecting account: {account_name}")

            # Best possible locator chain for Element UI dropdowns
            dropdown: Locator = (
                page.get_by_role("combobox")                           # All <input> that act as combobox
                    # .nth(0 if "Float" in account_name else 1)          # 0 = Float, 1 = Commission
                    .nth(2 )          # 0 = Float, 1 = Commission
                    .locator("..")                                      # Go up to the .el-select container
                    .locator(".el-select__caret")                       # The little arrow icon
            )

            # Alternative rock-solid fallback if above fails
            if dropdown.count() == 0:
                logger.info("[INFO] Falling back to CSS-based dropdown locator...")
                dropdown = page.locator(".el-select").nth(0) \
                               .locator("i.el-select__caret")

            # Wait for it to be visible and clickable
            dropdown.wait_for(state="visible", timeout=15000)
            dropdown.click(force=True)  # force=True helps with overlay issues
            logger.info(f"[INFO] {account_name} dropdown opened")

            # Navigate with ArrowDown + Enter
            for _ in range(arrow_down_count):
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
            page.keyboard.press("Enter")
            logger.info(f"[INFO] Selected option #{arrow_down_count + 1} in {account_name}")
            time.sleep(1)  # Let selection settle

            return True

        except Exception as e:
            logger.error(f"[ERROR] Failed to select {account_name} dropdown: {e}")
            page.screenshot(path=f"dropdown_error_{account_name.lower()}.png")
            return False

    def process_float_account_details(self, page: Page, business_short_code: int, mapped_data: Optional[dict], pass_value: str) -> tuple:

        try:
            logger.info("[INFO] Processing Float Account Details")

            # Step 1: Select Float Account (usually 2nd or 3rd option)
            if not self.select_account_dropdown(page, "Float Account", arrow_down_count=2):
                return "dropdown",False
        
            self.extract_extra_till_info(page, mapped_data)
        
            logger.info("We are checking whether a till is frozen or not")        
            if self.is_till_frozen(page):
                self.send_alert_on_non_active_(self.user.email,
                                            mapped_data.get("company_name","-"),
                                            business_short_code=business_short_code,
                                            status="FROZEN")
                # return "frozen",False

            time.sleep(1)  # Wait for table to load

            logger.info("We are trying to save to the dataframe")

            df,success_value = self.scrape_180_days_monthly(page,business_short_code=business_short_code,pass_value=pass_value,additional_category="float")
            if df is not None or success_value:
                logger.info("[SUCCESS] Float table extracted")
                return "dataframe",True
            else:
                logger.error("[ERROR] Failed to extract float table")
                return "dataframe",False

        except Exception as e:
            logger.error(f"[ERROR] process_float_account_details failed: {e}")
            page.screenshot(path="float_error.png")
            return False

    def click_search_button(self, page: Page) -> bool:

        try:
            logger.info("[INFO] Clicking Search button")
            search_button = page.locator("//div[@class='section-content']//button").first
            search_button.wait_for(state="visible", timeout=10000)
            search_button.click(force=True)
            logger.info("[INFO] Search button clicked")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to click Search button: {e}")
            return False

    def click_search_button_head_office(self, page: Page) -> bool:

        try:
            logger.info("[INFO] Clicking Search button")
            search_button = page.locator("//div[@id='pane-transactions']//form[@class='el-form el-form--default el-form--label-top form-flex-container']//button[1]").first
            search_button.wait_for(state="visible", timeout=10000)
            search_button.click(force=True)
            logger.info("[INFO] Search button clicked")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to click Search button: {e}")
            return False

    def process_commission_account_details(self, page: Page, business_short_code: int, mapped_data: Optional[dict], pass_value: str) -> bool:

        try:
            logger.info("[INFO] Processing Commission Account Details")
            self.scroll_to_top(page)
            time.sleep(1)

            # Step 1: Select Commission Account (usually 5th+ option)
            if not self.select_account_dropdown(page, "Commission Account", arrow_down_count=3):
                return False

            self.extract_extra_till_info(page, mapped_data)
        
            df,success_value = self.scrape_180_days_monthly(page,business_short_code=business_short_code,pass_value=pass_value,additional_category="commission")
            if df is not None or success_value:
                logger.info("[SUCCESS] Commission table extracted")
                return True
            else:
                logger.error("[ERROR] Failed to extract commission table")
                return False

        except Exception as e:
            logger.error(f"[ERROR] process_commission_account_details failed: {e}")
            page.screenshot(path="commission_error.png")
            return False

    def process_float_commission(self, page: Page, business_short_code: int , mapped_data:Optional[dict], pass_value: str) -> bool:

        """Main function – processes both float and commission sequentially"""
    
        trials = 3

        proc_type, success = self.process_float_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value)
        logger.info(f"[DEBUG] Float Account processing result: {proc_type}, success: {success}")
        if not success and proc_type != "frozen":
            self.close_irritative_dialog_box(page)
            logger.error(f"[ERROR] Failed at Float Account step {business_short_code} - Retrying...")
            while trials > 0:
                trials -= 1
                logger.info(f"[INFO] Retrying Float Account step {business_short_code} ({3 - trials} attempts left)...")
                proc_type_inner, success_inner = self.process_float_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value)
                if success_inner:
                    logger.info("[SUCCESS] Float Account step completed")
                    break
                time.sleep(1)  # Wait before retrying
            else:
                logger.error("[ERROR] All retries failed for Float Account step")
                return False
            return False
        elif not success and proc_type == "frozen":
            logger.info(f"[INFO] Till is frozen for business {business_short_code}, skipping further processing.")
            return False
        
        if pass_value == "first":                                                                                                       
            logger.info(f"[INFO] First pass — skipping commission for {business_short_code}")                                          
            return True  

        # Small pause to let page stabilize
        time.sleep(1)

        if not self.process_commission_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value):
            logger.error(f"[ERROR] Failed at Commission Account step {business_short_code} - Retrying...")
            self.close_irritative_dialog_box(page)
            while trials > 0:
                trials -= 1
                logger.info(f"[INFO] Retrying Commission Account step {business_short_code} ({3 - trials} attempts left)...")
                if self.process_commission_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value):
                    logger.info("[SUCCESS] Commission Account step completed")
                    break
                time.sleep(1)  # Wait before retrying
            else:
                logger.error("[ERROR] All retries failed for Commission Account step") 
            
            return False

        logger.info(f"[SUCCESS] Completed processing business {business_short_code}")
        return True

    def _find_visible_date_input(self, page: Page, placeholder: str, max_wait: int = 15):

        """
        Poll for up to max_wait seconds for a visible input with the given placeholder.
        Ignores hidden duplicates by checking each candidate with is_visible().
        Dumps a debug snapshot on failure.
        """
        deadline = time.time() + max_wait
        while time.time() < deadline:
            locator = page.locator(f"//input[@placeholder='{placeholder}']")
            count = locator.count()
            for i in range(count):
                inp = locator.nth(i)
                try:
                    if inp.is_visible():
                        logger.info(f"[✓] Found visible '{placeholder}' input (index {i} of {count})")
                        return inp
                except Exception:
                    continue
            logger.info(f"[WAIT] '{placeholder}' — none of {count} candidates visible yet, retrying...")
            time.sleep(1)

        # Dump page state for diagnosis
        try:
            with open("date_input_debug.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            logger.info("[DEBUG] Page HTML dumped to date_input_debug.html")
        except Exception:
            pass
        raise Exception(f"No visible input with placeholder '{placeholder}' found after {max_wait}s")


    def select_dates_and_submit_head_office_monthly(self, page: Page, month_offset: int = 0) -> bool:

        """
        Select exact calendar month boundaries for Head Office Commission scraping.
        month_offset=0: 1st of current month → today
        month_offset=1: 1st of last month → last day of last month
        month_offset=2..5: accordingly
        """
        try:
            start_time_input = self._find_visible_date_input(page, "Start Time")
            logger.info("[✓] Found Start Time date picker input")
            end_time_input = self._find_visible_date_input(page, "End Time")
            logger.info("[✓] Found End Time date picker input")

        except Exception as e:
            logger.error(f"[ERROR] Could not find date picker inputs: {e}")
            return False

        try:
            today = datetime.now()

            target_month = today.month - month_offset
            target_year = today.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            start_date = datetime(target_year, target_month, 1)

            if month_offset == 0:
                end_date = today
            elif target_month == 12:
                end_date = datetime(target_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(target_year, target_month + 1, 1) - timedelta(days=1)

            start_date_str = f"{start_date.strftime('%d/%m/%Y')} 00:00:00"
            end_date_str   = f"{end_date.strftime('%d/%m/%Y')} 23:59:59"

            logger.info(f"[INFO] Head Office Commission month {month_offset + 1}/6:")
            logger.info(f"[INFO]   From: {start_date_str}")
            logger.info(f"[INFO]   To:   {end_date_str}")

            page.click("body", position={"x": 10, "y": 10})
            time.sleep(1)

            start_time_input.click()
            start_time_input.fill("")
            time.sleep(0.2)
            start_time_input.type(start_date_str)
            start_time_input.press("Enter")
            time.sleep(0.5)

            end_time_input.click()
            end_time_input.fill("")
            time.sleep(0.5)
            end_time_input.type(end_date_str)
            end_time_input.press("Enter")

            # Search button lives in div.form-btns — use force=True as it sits hidden in DOM
            self.click_search_button_head_office(page)

            too_large_error = page.locator("//button[@aria-label='Close this dialog']").first
            if too_large_error.is_visible():
                self.close_irritative_dialog_box(page)
                return self.select_dates_and_submit_head_office_monthly(page, month_offset=month_offset)

            logger.info("[✓] Head Office Commission form submitted")
            return True

        except Exception as e:
            logger.error(f"[ERROR] Could not set Head Office Commission dates: {e}")
            traceback.print_exc()
            return False


    def scrape_head_office_commission_held_account(self, page: Page) -> bool:

        """
        Scrapes the Commission Held Account from the Account Statement tab.
        Called while already on the review-transaction page (after scrape_head_office_commission).
        Keeps only rows where Paid In > 0 before saving to the database.
        """
        try:
            logger.info("[INFO] ===== Starting Commission Held Account Scraping =====")

            # Step 1: Click Account Statement tab
            logger.info("[STEP 1] Clicking Account Statement tab...")
            acct_tab = page.wait_for_selector("//div[@id='tab-accountStatement']", timeout=30000)
            acct_tab.click()
            time.sleep(2)

            # Step 2: Open dropdown and select Commission Held Account (7 arrow-downs)
            # 8 lands on "Agency Commission Account"; 7 lands on "Commission Held Account"
            logger.info("[STEP 2] Selecting Commission Held Account (7 arrow-downs)...")
            dropdown_caret = page.locator(
                "//div[@class='el-form-item is-success is-required asterisk-left "
                "el-form-item--label-top none-margin-bottom']"
                "//i[@class='el-icon el-select__caret el-select__icon']"
            ).first
            dropdown_caret.wait_for(state="visible", timeout=15000)
            dropdown_caret.click(force=True)
            time.sleep(0.5)

            for _ in range(7):
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
            page.keyboard.press("Enter")
            time.sleep(2)
            logger.info("[INFO] Commission Held Account selected")

            # Step 3: Scrape last 6 calendar months
            all_data = []
            for month_offset in range(6):
                self.close_irritative_dialog_box(page)
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Commission Held Account - chunk {month_offset + 1}/6")

                # Find date inputs
                try:
                    start_time_input = self._find_visible_date_input(page, "Start Time")
                    end_time_input   = self._find_visible_date_input(page, "End Time")
                except Exception as e:
                    logger.error(f"[ERROR] Date inputs not found for month {month_offset + 1}: {e}")
                    continue

                # Calendar month boundaries
                today = datetime.now()
                target_month = today.month - month_offset
                target_year  = today.year
                while target_month <= 0:
                    target_month += 12
                    target_year  -= 1

                start_date = datetime(target_year, target_month, 1)
                if month_offset == 0:
                    end_date = today
                elif target_month == 12:
                    end_date = datetime(target_year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(target_year, target_month + 1, 1) - timedelta(days=1)

                start_date_str = f"{start_date.strftime('%d/%m/%Y')} 00:00:00"
                end_date_str   = f"{end_date.strftime('%d/%m/%Y')} 23:59:59"
                logger.info(f"[INFO] From: {start_date_str}  To: {end_date_str}")

                # Fill date inputs
                page.click("body", position={"x": 10, "y": 10})
                time.sleep(0.5)

                start_time_input.click()
                start_time_input.fill("")
                time.sleep(0.2)
                start_time_input.type(start_date_str)
                start_time_input.press("Enter")
                time.sleep(0.5)

                end_time_input.click()
                end_time_input.fill("")
                time.sleep(0.5)
                end_time_input.type(end_date_str)
                end_time_input.press("Enter")

                # Click search button
                try:
                    search_btn = page.locator("//div[@class='section-content']//button[1]").first
                    search_btn.click(force=True)
                    logger.info("[INFO] Search button clicked")
                except Exception as e:
                    logger.error(f"[ERROR] Search failed for month {month_offset + 1}: {e}")
                    continue
                time.sleep(2)

                if not self.does_transaction_exist_for_period_(page):
                    logger.info("[INFO] No data for this period — skipping")
                    continue

                # Download and filter (Paid In > 0 only)
                try:
                    visible_dropdown = page.locator("div.el-dropdown.padding-export:visible")
                    visible_dropdown.wait_for(state="visible", timeout=10000)
                    visible_dropdown.scroll_into_view_if_needed()
                    time.sleep(0.5)

                    coords = page.evaluate("""() => {
                        const el = document.querySelector('div.el-dropdown.padding-export:not(.is-disabled) button');
                        if (!el) return null;
                        const r = el.getBoundingClientRect();
                        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
                    }""")
                    if not coords:
                        logger.warning("[EXPORT] Could not resolve export button coordinates — skipping")
                        continue

                    page.mouse.move(coords['x'], coords['y'])
                    time.sleep(3)

                    page.wait_for_function(
                        """() => {
                            const menus = document.querySelectorAll('ul.el-dropdown-menu');
                            for (const menu of menus) {
                                const rect = menu.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0 && rect.top >= 0) return true;
                            }
                            return false;
                        }""",
                        timeout=40000
                    )

                    all_items  = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")
                    excel_items = all_items.filter(has_text="Excel")
                    if excel_items.count() < 3:
                        logger.info("[EXPORT] Not enough Excel options — skipping")
                        continue

                    with page.expect_download(timeout=60_000) as dl_info:
                        try:
                            excel_items.nth(2).click(force=True, timeout=15_000)
                        except Exception:
                            excel_items.nth(2).evaluate("el => el.click()")

                    temp_path = dl_info.value.path()

                    # Extract the company shortcode from the Excel header (row 1 = "Short Code: 462300")
                    # This attributes commission to the correct company, not the login shortcode
                    excel_shortcode = self.company_shortcode  # fallback
                    try:
                        df_header = pd.read_excel(temp_path, nrows=6, header=None)
                        for hi in range(len(df_header)):
                            row_str = ' '.join(df_header.iloc[hi].astype(str).tolist())
                            sc_match = re.search(r'Short\s*Code[:\s]+(\d{4,})', row_str, re.IGNORECASE)
                            if sc_match:
                                excel_shortcode = sc_match.group(1).strip()
                                logger.info(f"[INFO] Excel company shortcode: {excel_shortcode}")
                                break
                    except Exception as _hdr_err:
                        logger.warning(f"[WARN] Could not extract shortcode from Excel header: {_hdr_err}")

                    # Read and split by transaction kind
                    df_raw = pd.read_excel(temp_path, skiprows=6)
                    logger.info(f"[DEBUG] Raw columns: {list(df_raw.columns)}, rows: {len(df_raw)}")

                    # Identify clawback rows via the Details column
                    details_col = next(
                        (c for c in df_raw.columns if 'detail' in str(c).lower()), None
                    )
                    if details_col:
                        is_clawback = df_raw[details_col].astype(str).str.contains(
                            'clawback', case=False, na=False
                        )
                        df_clawback = df_raw[is_clawback].reset_index(drop=True)
                        df_held    = df_raw[~is_clawback].reset_index(drop=True)
                    else:
                        df_clawback = pd.DataFrame()
                        df_held = df_raw

                    # Save clawbacks as separate type (attributed to Excel's company)
                    if not df_clawback.empty:
                        r_cb = transaction_service.update_transactions_from_dataframe(
                            df=df_clawback,
                            transaction_type="commission_clawback",
                            company_shortcode=excel_shortcode,
                            agent_id=None,
                            business_shortcode=excel_shortcode
                        )
                        logger.info(f"[INFO] Clawback save result: {r_cb.get('success')} — {len(df_clawback)} row(s) for month {month_offset + 1}")

                    # Save commission held rows (non-clawback, attributed to Excel's company)
                    results = transaction_service.update_transactions_from_dataframe(
                        df=df_held,
                        transaction_type="commission_held",
                        company_shortcode=excel_shortcode,
                        agent_id=None,
                        business_shortcode=excel_shortcode
                    )
                    logger.info(f"[DEBUG] Commission held save result: success={results.get('success')}, "
                          f"created={results.get('created_count',0)}, updated={results.get('updated_count',0)}, "
                          f"errors={results.get('error_count',0)}, error={results.get('error','')}")
                    if results.get('success'):
                        df_raw['scrape_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        df_raw['month_offset'] = month_offset
                        all_data.append(df_raw)
                        logger.info(f"[SUCCESS] Commission Held: {len(df_held)} rows saved for month {month_offset + 1}")

                except Exception as exp_err:
                    logger.error(f"[ERROR] Export/save failed for month {month_offset + 1}: {exp_err}")
                    traceback.print_exc()

                if month_offset < 5:
                    time.sleep(1)

            if all_data:
                combined = pd.concat(all_data, ignore_index=True)
                logger.info(f"\n{'=' * 60}")
                logger.info(f"COMMISSION HELD TOTAL: {len(combined)} rows from {len(all_data)} periods")
            else:
                logger.info("[INFO] No Commission Held data scraped")

            logger.info("[INFO] ===== Commission Held Account Scraping Complete =====")
            return True

        except Exception as e:
            logger.error(f"[ERROR] scrape_head_office_commission_held_account failed: {e}")
            traceback.print_exc()
            return False


    def scrape_head_office_commission(self, page: Page) -> bool:

        """
        Scrapes the Head Office Commission account immediately after login.
        Clicks the dashboard Review Transaction card, navigates to the Transactions
        tab, selects the Head Office Commission dropdown option (7th caret, 6 arrow-downs),
        then scrapes the last 6 calendar months of data via Excel export.
        """
        try:
            logger.info("[INFO] ===== Starting Head Office Commission Scraping =====")

            # Step 1: Click the Review Transaction card button on the dashboard
            logger.info("[STEP 1] Clicking Review Transaction card button...")
            review_btn = page.wait_for_selector(
                "//div[@class='el-card is-always-shadow home-card portal-item review-transaction']"
                "//div[@class='el-card__header']"
                "//div[@class='home-card-header']"
                "//span[@class='handler']"
                "//span"
                "//button[@type='button']",
                timeout=30000
            )
            review_btn.click()
            time.sleep(2)
        

            # # Step 2: Click Transactions tab
            logger.info("[STEP 2] Clicking Transactions tab...")
            transactions_tab = page.wait_for_selector(
                "//div[@id='tab-transactions']",
                timeout=30000
            )
            transactions_tab.click()
            time.sleep(1)        

            # Step 3: Open the 7th account dropdown caret and arrow-down 6 times
            logger.info("[STEP 3] Selecting Head Office Commission account from dropdown...")
            dropdown = page.locator("(//i[@class='el-icon el-select__caret el-select__icon'])[7]")
            if dropdown.count() == 0:
                logger.warning("[INFO] Primary dropdown locator not found, trying positional fallback...")
                dropdown = page.locator(
                    "//div[5]//div[1]//div[1]//div[1]//div[1]//div[1]//div[2]//i[1]"
                )

            dropdown.wait_for(state="visible", timeout=15000)
            dropdown.click(force=True)
            time.sleep(0.5)

            for _ in range(6):
                page.keyboard.press("ArrowDown")
                time.sleep(0.2)
            page.keyboard.press("Enter")
            time.sleep(3)
            logger.info("[INFO] Head Office Commission account selected")

            # Step 4: Single date range — 1st of 2 months ago → today
            self.close_irritative_dialog_box(page)
            today = datetime.now()
            start_month = today.month - 2
            start_year = today.year
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            start_date_str = f"{datetime(start_year, start_month, 1).strftime('%d/%m/%Y')} 00:00:00"
            end_date_str   = f"{today.strftime('%d/%m/%Y')} 23:59:59"
            logger.info(f"[INFO] Head Office Commission date range: {start_date_str} → {end_date_str}")

            page.click("body", position={"x": 10, "y": 10})
            time.sleep(0.5)

            start_input = self._find_visible_date_input(page, "Start Time")
            start_input.click()
            start_input.fill("")
            time.sleep(0.2)
            start_input.type(start_date_str)
            start_input.press("Enter")
            time.sleep(0.5)

            end_input = self._find_visible_date_input(page, "End Time")
            end_input.click()
            end_input.fill("")
            time.sleep(0.5)
            end_input.type(end_date_str)
            end_input.press("Enter")
            time.sleep(0.5)

            self.click_search_button_head_office(page)
            time.sleep(2)

            # all_data = []
            # if not does_transaction_exist_for_period_(page):
            #     logger.info("[INFO] No Head Office Commission transactions found for this period")
            # else:
            #     df, success_value = save_table_to_dataframe_download_head_office(
            #         page,
            #         business_shortcode=company_shortcode,
            #         additional_category="commission"
            #     )
            #     if df is not None and len(df) > 0:
            #         df['scrape_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            #         all_data.append(df)
            #         logger.info(f"[SUCCESS] Head Office Commission: {len(df)} rows")
            #     else:
            #         logger.info("[INFO] No Head Office Commission data returned")

            # if all_data:
            #     combined_df = pd.concat(all_data, ignore_index=True)
            #     logger.info(f"HEAD OFFICE COMMISSION TOTAL: {len(combined_df)} rows")
            # else:
            #     logger.info("[INFO] No Head Office Commission data scraped")
        
            # Hover the visible export trigger (there are 2 in the DOM; :visible picks the right one)
            t = time.time()
            export_trigger = page.locator("div.el-dropdown.padding-export:visible >> span").first
            export_trigger.wait_for(state="visible", timeout=30000)
            export_trigger.scroll_into_view_if_needed()
            export_trigger.hover(force=True, timeout=10_000)
            logger.info(f"[TIMING] Export trigger hovered: {self._elapsed(t)}")
            time.sleep(3)

            page.wait_for_function(
                """() => {
                    const menus = document.querySelectorAll('ul.el-dropdown-menu');
                    for (const menu of menus) {
                        const rect = menu.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && rect.top >= 0) return true;
                    }
                    return false;
                }""",
                timeout=40000,
            )
            logger.info(f"[TIMING] Export dropdown open: {self._elapsed(t)}")

            all_items = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")
            excel_items = all_items.filter(has_text="Excel")
            excel_count = excel_items.count()
            logger.info(f"[EXPORT] Found {excel_count} Excel option(s)")

            if excel_count < 1:
                raise Exception(f"No Excel export options found (count={excel_count})")

            target_excel = excel_items.last

            t = time.time()
            with page.expect_download(timeout=60_000) as dl_info:
                try:
                    target_excel.click(force=True, timeout=15_000)
                    logger.info("[EXPORT] Clicked Excel option")
                except Exception:
                    logger.error("[EXPORT] Normal click failed — falling back to JS click")
                    target_excel.evaluate("el => el.click()")

            download = dl_info.value
            temp_path = download.path()
            logger.info(f"[TIMING] Excel downloaded: {self._elapsed(t)}")

            # Parse and persist directly from the Playwright temp file
            t = time.time()
            df, success = self.update_transactions_from_file(
                file_path=temp_path,
                business_shortcode=str(self.company_shortcode),
                transaction_type="commission",
                company_shortcode=self.company_shortcode,
                agent_id=None,
            )
            logger.info(f"[TIMING] DB upsert: {self._elapsed(t)} | success={success} | rows={len(df) if df is not None else 0}")

            logger.info("[INFO] ===== Head Office Commission Scraping Complete =====")

            # Immediately scrape Commission Held Account from the Account Statement tab
            self.scrape_child_org_commission(page, business_shortcode=self.company_shortcode)
            return True

        except Exception as e:
            logger.error(f"[ERROR] scrape_head_office_commission failed: {e}")
            traceback.print_exc()
            return False


    def select_dates_and_submit_monthly(self, page: Page, month_offset: int = 0) -> bool:

        """
        Select a specific month (month by month scraping)
        month_offset: 0 = current month, 1 = 30-60 days ago, 2 = 60-90 days ago, etc.
        Each offset represents approximately 30 days
        """
        try:
            # Find date picker inputs
            start_time_input = page.wait_for_selector(
                "//input[@placeholder='Start Time']", 
                timeout=30000
            )
            logger.info("[✓] Found Start Time date picker input")
        
            end_time_input = page.wait_for_selector(
                "//input[@placeholder='End Time']", 
                timeout=30000
            )
            logger.info("[✓] Found End Time date picker input")
        
        except Exception as e:
            logger.error(f"[ERROR] Could not find date picker inputs: {e}")
            self.user = User.query.filter_by(id=self.user_id).first()
            if self.user:
                send_session_timeout_email(self.user.email)
                # context.close()
                # browser.close()
            return False
    
        try:
            # Calculate dates for 180 days back, month by month
            today = datetime.now()
        
            # Each month_offset represents 30 days back
            # month_offset=0: 0-30 days ago
            # month_offset=1: 30-60 days ago
            # month_offset=2: 60-90 days ago
            # month_offset=3: 90-120 days ago
            # month_offset=4: 120-150 days ago
            # month_offset=5: 150-180 days ago
        
            # Calculate start date (days_ago_end of the range)
            days_to_go_back_end = month_offset * 30
            days_to_go_back_start = days_to_go_back_end + 30
        
            # Calculate the date range
            end_date = today - timedelta(days=days_to_go_back_end)
            start_date = today - timedelta(days=days_to_go_back_start)
        
            # Ensure we're within 180 days limit
            if days_to_go_back_start > 180:
                logger.info(f"[INFO] Month offset {month_offset} exceeds 180 days limit")
                return False
        
            # Format dates with time appended
            start_date_str = f"{start_date.strftime('%d/%m/%Y')} 00:00:00"
            end_date_str = f"{end_date.strftime('%d/%m/%Y')} 23:59:59"  # Changed to end of day
        
            logger.info(f"[INFO] Selecting date range {month_offset+1}/6:")
            logger.info(f"[INFO] From: {start_date_str}")
            logger.info(f"[INFO] To: {end_date_str}")
        
            # Close any open calendars first
            page.click("body", position={"x": 10, "y": 10})
            time.sleep(1)
        
            # --- SET START DATE WITH TIME ---
            logger.info("[STEP 1] Setting Start Date with time...")
        
            # Click to open calendar if needed
            start_time_input.click()
        
            # Clear input field
            start_time_input.fill("")
            time.sleep(0.2)
        
            # Type start date with time
            start_time_input.type(start_date_str)
        
            # Press Enter to confirm
            start_time_input.press("Enter")
            time.sleep(0.5)
        
            # --- SET END DATE WITH TIME ---
            logger.info("[STEP 2] Setting End Date with time...")
        
            # Click End Time input
            end_time_input.click()
        
            # Clear input field
            end_time_input.fill("")
            time.sleep(0.5)
        
            # Type end date with time
            end_time_input.type(end_date_str)
        
            # Press Enter to confirm
            end_time_input.press("Enter")
            # time.sleep(1)
        
            # --- SUBMIT THE FORM ---
            logger.info("[STEP 3] Submitting form...")
        
            # Try to find and click submit button if exists
            self.click_search_button(page)
                
            # Wait for results to load
            time.sleep(2)
            too_large_error = page.locator("//button[@aria-label='Close this dialog']").first
            if too_large_error.is_visible():
                self.close_irritative_dialog_box(page)
                self.select_dates_and_submit_monthly(page, month_offset=month_offset)
                logger.error("[ERROR] Date range too large error encountered")
            logger.info("[✓] Form submitted successfully")
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Could not set dates: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_total_months_by_shortcode_shortfall(self, business_shortcode: str, till_scraping_shortfall: Dict, transaction_type: str = None) -> tuple:

        """
        Calculate the number of months to scrape based on shortfall.

        Args:
            business_shortcode: The business shortcode to check
            self.till_scraping_shortfall: Dict with scraping data, can be:
                - Simple format: {shortcode: [days, receipt_no]}
                - Nested format: {shortcode: {'float': [days, receipt_no], 'commission': [days, receipt_no]}}
            transaction_type: Optional - 'float' or 'commission' for specific type lookup

        Returns:
            tuple: (number_of_months, days_since_last_scrape)
        """
        if not self.till_scraping_shortfall:
            return 6, 180

        if business_shortcode not in self.till_scraping_shortfall.keys():
            return 6, 180

        shortcode_data = self.till_scraping_shortfall[business_shortcode]

        # Check if it's nested format (dict) or simple format (list)
        if isinstance(shortcode_data, dict):
            # Nested format: {'float': [days, receipt_no], 'commission': [days, receipt_no]}
            if transaction_type and transaction_type in shortcode_data:
                days = float(shortcode_data[transaction_type][0])
            elif transaction_type:
                # Requested type has never been scraped — treat as full 6-month backfill.
                # Do NOT fall back to another type's days (e.g. commission=0 would
                # incorrectly suppress a float scrape that hasn't happened yet).
                return 6, 180
            else:
                # No specific type requested — use the max days across all types
                days_list = [float(v[0]) for v in shortcode_data.values() if isinstance(v, list)]
                days = max(days_list) if days_list else 180
        else:
            # Simple format: [days, receipt_no]
            days = float(shortcode_data[0])

        return np.ceil(days / 30).astype(int), days


    def get_days_for_transaction_type(self, business_shortcode: str, till_scraping_shortfall: Dict, transaction_type: str) -> int:

        """
        Get the number of days since last scrape for a specific transaction type.

        Args:
            business_shortcode: The business shortcode to check
            self.till_scraping_shortfall: Dict with scraping data (nested format expected)
            transaction_type: 'float' or 'commission'

        Returns:
            int: Days since last scrape for the specified type, or 180 if not found
        """
        if not self.till_scraping_shortfall:
            return 180

        if business_shortcode not in self.till_scraping_shortfall:
            return 180

        shortcode_data = self.till_scraping_shortfall[business_shortcode]

        if isinstance(shortcode_data, dict):
            if transaction_type in shortcode_data:
                return int(shortcode_data[transaction_type][0])
            else:
                # Transaction type not found - never scraped for this type
                return 180
        else:
            # Simple format - return the days
            return int(shortcode_data[0])

    # Main function to scrape 180 days month by month
    def scrape_180_days_monthly(self, page:Page, business_short_code:int=0, pass_value:str="",additional_category=None) -> tuple:

        """
        Scrape data for the last 180 days, divided into 6 monthly chunks.

        Args:
            page: Playwright page object
            business_short_code: The business shortcode to scrape
            pass_value: 'first' for float transactions, 'second' for commission transactions
            additional_category: Transaction type - 'float' or 'commission'

        The scraping strategy is determined by the number of days since last scrape for
        the specific transaction type:
            - days <= 2: Use save_table_to_dataframe_latest_ (gets just latest transactions)
            - days > 2: Use save_table_to_dataframe_download (downloads more historical data)
        """
        all_data = []

        success_value_ : bool = False

        # Determine transaction_type from additional_category or pass_value
        transaction_type = additional_category
        if not transaction_type:
            transaction_type = 'float' if pass_value == 'first' else 'commission'

        # Get scraping shortfall data - fetch fresh from DB for both passes
        # so in-session updates don't cause stale 0-day readings
        total_months, days = None, None
        fresh_shortfall = transaction_service.get_last_scraped_per_shortcode()
        if pass_value == "second":
            # Commission (second pass)
            days = self.get_days_for_transaction_type(str(business_short_code), fresh_shortfall, transaction_type)
            total_months = np.ceil(days / 30).astype(int) if days > 0 else 1
        else:
            # Float (first pass) — also uses fresh DB data
            total_months, days = self._get_total_months_by_shortcode_shortfall(
                str(business_short_code),
                fresh_shortfall,
                transaction_type=transaction_type
            )

        logger.info(f"[INFO] Transaction type: {transaction_type}, Pass value: {pass_value}, Days since last scrape: {days}")

        # Determine scraping strategy based on days since last scrape
        if days < 1 and pass_value == "first":
            force, reason = transaction_service.should_force_float_scrape(business_short_code)
            if force:
                logger.info(f"[INFO] Float transactions appear current (days={days}) but {reason} — forcing 1-month scrape.")
                total_months = max(1, total_months)
            else:
                logger.info(f"[INFO] {reason} — skipping float scrape.")
                return pd.DataFrame(), True
        elif days < 1 and pass_value == "second":
            # Commission was recently scraped - just get latest
            logger.info(f"[INFO] Commission transactions recently scraped ({days} days ago). Getting latest only.")
            df, success_value = self.save_table_to_dataframe_latest_(
                page,
                business_shortcode=business_short_code,
                pass_value=pass_value,
                additional_category=additional_category
            )
            return df, success_value
        # For both float (first) and commission (second) with days >= 1, proceed to monthly scraping
        logger.info(f"[INFO] Will scrape {total_months} month(s) of {transaction_type} data (last scraped {days} days ago).")
        logger.info(f"[INFO] Selecting date range for {transaction_type} download...")

        for month_offset in range(total_months):
            self.close_irritative_dialog_box(page)
            logger.info(f"\n{'='*60}")
            logger.info(f"Scraping {transaction_type} - month chunk {month_offset+1}/{total_months}")

            # Method 1: 30-day chunks
            success = self.select_dates_and_submit_monthly(page, month_offset=month_offset)

            # Method 2: Exact month boundaries (uncomment if preferred)
            # success = select_exact_month_back(page, months_back=month_offset)

            if not success:
                self.close_irritative_dialog_box(page)
                time.sleep(1)
                logger.info(f"[INFO] Retrying date selection for month offset {month_offset}...")
                success = self.select_dates_and_submit_monthly(page, month_offset=month_offset)
                if not success:
                    self.close_irritative_dialog_box(page)
                    logger.error(f"[ERROR] Failed to select dates for month offset {month_offset}")
                    break

            # Wait for table to load
            time.sleep(1)

            logger.info(f"Saving {transaction_type} data for this period to dataframe...")

            # Get data for this period
            try:
                if not self.does_transaction_exist_for_period_(page=page):
                    logger.info(f"[INFO] No {transaction_type} transactions found for this period. Skipping.")
                    continue

                # Use download method for both float and commission when days > 2
                df, success_value = self.save_table_to_dataframe_download(
                    page,
                    business_shortcode=business_short_code,
                    additional_category=additional_category
                )
            
                if len(df) > 0:
                    # Add period information
                    today = datetime.now()
                    days_ago_start = (month_offset + 1) * 30
                    days_ago_end = month_offset * 30
                
                    df['period_days_ago'] = f"{days_ago_start}-{days_ago_end} days ago"
                    df['scrape_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    df['month_offset'] = month_offset
                
                    all_data.append(df)
                
                    logger.info(f"[SUCCESS] Scraped {len(df)} rows for period {days_ago_start}-{days_ago_end} days ago")
                    success_value_ = success_value
                else:
                    logger.info("[INFO] No data found in dataframe")
                
            except Exception as e:
                logger.error(f"[ERROR] Failed to save data for month offset {month_offset}: {e}")
                success_value_ = False
        
            # Add delay between requests
            if month_offset < total_months - 1:
                logger.info("[INFO] Waiting before next period...")
                time.sleep(1)
    
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"\n{'='*60}")
            logger.info(f"TOTAL DATA: {len(combined_df)} rows from {len(all_data)} periods")
            return combined_df, True if all_data else []
    
        return pd.DataFrame(), success_value_

    def select_dates_and_submit_(self, page: Page) -> bool:

            try:
                # Find the Start Time input (first date picker with placeholder "Start Time")
                start_time_input = page.wait_for_selector(
                    "//input[@placeholder='Start Time']", 
                    timeout=10000
                )
                logger.info("[✓] Found Start Time date picker input")
            
                # Find the End Time input (first date picker with placeholder "End Time")
                end_time_input = page.wait_for_selector(
                    "//input[@placeholder='End Time']", 
                    timeout=10000
                )
                logger.info("[✓] Found End Time date picker input")
                self.user = User.query.filter_by(id=self.user_id).first()
                if self.user:
                    # send_session_timeout_email(user.email)
                    send_session_timeout_email(self.user.email)
                    # context.close()
                    # browser.close()
                

            except Exception as e:
                logger.error(f"[ERROR] Could not find date picker inputs: {e}")
            
                # Fallback: Try finding by class and position
                try:
                    logger.info("[INFO] Trying fallback selector for date pickers...")
                    date_inputs = page.query_selector_all(
                        "//div[@class='el-date-editor']//input[@class='el-input__inner']"
                    )
                    if len(date_inputs) >= 2:
                        start_time_input = date_inputs[0]
                        end_time_input = date_inputs[1]
                        logger.info(f"[✓] Found {len(date_inputs)} date picker inputs using fallback")
                    else:
                        logger.error(f"[ERROR] Expected at least 2 date inputs, found {len(date_inputs)}")
                        return False
                except Exception as fallback_error:
                    logger.error(f"[ERROR] Fallback selector also failed: {fallback_error}")
                    return False
        
            # Step 3: Fill Start Time with first day of current month in dd/MM/yyyy format
            try:
                #first_day = datetime.now().replace(day=1).strftime("%d/%m/%Y")            
                # Click the Start Time input to focus
                start_time_input.click()
            
                logger.info(f"We have just clicked the start time")
                previous_month_icon = page.wait_for_selector(
                    "//div[@actualvisible='true']//button[@aria-label='Previous Month']", 
                    timeout=5000
                )
            
                for i in range(3):
                    previous_month_icon.click() 
            
                logger.info("The previous button has been clicked thrice .......")
            
                for i in range(5):
                    page.keyboard.press("Tab")
                    logger.info("Tab pressed")
            
                page.keyboard.press("Enter")
            
            except Exception as e:
                logger.error(f"[ERROR] Could not fill Start Time input: {e}")
                return False
        
            # Step 4: Press Tab three times and Enter to submit
            try:
                logger.info("[INFO] Pressing Tab three times and Enter to submit...")
            
                # Ensure Start Time input has focus
                start_time_input.focus()
                page.wait_for_timeout(500)
            
                # Debug: Check current focused element
                focused_element = page.evaluate_handle("() => document.activeElement")
                focused_tag = page.evaluate("(elem) => elem.tagName", focused_element)
                focused_id = page.evaluate("(elem) => elem.id || elem.placeholder || 'no-id'", focused_element)
                logger.info(f"[DEBUG] Current focused element: {focused_tag} (ID/Placeholder: {focused_id})")
            
                # Press Tab three times
                for i in range(4):
                    page.keyboard.press("Tab")
                    page.wait_for_timeout(500)
                    # Debug: Check focused element after each Tab
                    focused_element = page.evaluate_handle("() => document.activeElement")
                    focused_tag = page.evaluate("(elem) => elem.tagName", focused_element)
                    focused_id = page.evaluate("(elem) => elem.id || elem.placeholder || 'no-id'", focused_element)
                    logger.info(f"[DEBUG] After Tab {i+1}, focused element: {focused_tag} (ID/Placeholder: {focused_id})")
            
                # Press Enter to submit
                page.keyboard.press("Enter")
                logger.info("[✓] Pressed Enter to submit form")
                # page.wait_for_timeout(3000)  # Wait for page to load results
                time.sleep(1)  # Wait for page to load results
            except Exception as e:
                logger.error(f"[ERROR] Could not complete Tab/Enter submission: {e}")
                traceback.print_exc()
                return False

    def solveCaptchaXai(self, image_path):

        # Initialize client with your xAI key
        xai_key = os.getenv("XAI_API_KEY")
    
        client = OpenAI(
            api_key=xai_key,  # Replace with your key
            base_url="https://api.x.ai/v1"
        )

        # Function to encode image to base64
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")

        # Your CAPTCHA image path (e.g., from Playwright screenshot)
        base64_image = encode_image(image_path)

        # Send request
        response = client.chat.completions.create(
            model="grok-2-vision-1212",
            messages=[
                {
                    "role": "self.user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the exact digits from this CAPTCHA image. It's a 4 digit code with possible lines or distortions. Respond only with the number."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"  # Use 'jpeg' if JPG
                            }
                        }
                    ]
                }
            ],
            max_tokens=50,  # Short output for just the number
            temperature=0.1  # Low for accurate extraction
        )

        # Print the extracted CAPTCHA
        captcha_text = response.choices[0].message.content.strip()
        logger.info(f"Extracted CAPTCHA: {captcha_text}")
        return captcha_text

    def extract_user_agent_kyc(self, short_code: str, page: Page) -> bool:

        """
        Extracts KYC information for each agent/till operator under a shortcode.

        Flow:
          1. Navigate to the "Organization Operator" section.
          2. For each row in the operator table, click its detail button.
          3. Grab the inner HTML of the KYC form panel.
          4. Parse and upsert UserAgent records.
        """
        try:
            # Step 1: Click the "Organization Operator" tab/section
            logger.info("[INFO] Navigating to Organization Operator section...")
            org_operator_tab = page.wait_for_selector(
                "//div[contains(text(),'Organization Operator')]",
                timeout=15000
            )
            org_operator_tab.click()
            time.sleep(1)

            # Step 2: Collect all operator rows
            rows = page.query_selector_all("//tr[@class='el-table__row']")
            logger.info(f"[INFO] Found {len(rows)} operator row(s) for short_code {short_code}")

            agent_company_service_local = AgentCompanyService()
            agent_company = agent_company_service_local.get_agent_company_by_shortcode_(str(short_code))

            for idx, row in enumerate(rows):
                try:
                    # Read the Role column from this row BEFORE clicking Detail.
                    # Table columns: Identity ID | Operator ID | MSISDN | Role | Identity Status | User Name | Operation
                    # Role is in the 4th <td> (index 3).
                    cells = row.query_selector_all("td")
                    operator_role = None
                    if len(cells) >= 4:
                        role_text = cells[3].inner_text().strip()
                        if role_text and role_text != "-":
                            operator_role = role_text
                    logger.info(f"[INFO] Row {idx + 1}/{len(rows)} — role: {operator_role}")

                    # Step 3: Click the Detail button on this row
                    detail_btn = row.query_selector("button[type='button']")
                    if not detail_btn:
                        logger.warning(f"[WARN] No button found on row {idx + 1}, skipping.")
                        continue

                    detail_btn.click()
                    time.sleep(3)

                    # Step 4: Wait for and capture the KYC form HTML
                    kyc_panel = page.wait_for_selector(
                        "//div[@class='common-kyc-form common-kyc-form-review']",
                        timeout=15000
                    )
                    kyc_html = kyc_panel.inner_html()
                    logger.info(f"[DEBUG] Captured KYC HTML for row {idx + 1} ({len(kyc_html)} chars)")

                    # Step 5: Parse and save the KYC form
                    self._parse_and_save_kyc(
                        kyc_html=kyc_html,
                        short_code=short_code,
                        agent_company=agent_company,
                        operator_role=operator_role
                    )

                    # Navigate back to the operator list for the next row
                    page.go_back()
                    self.close_detail_panel_idx(page)
                    time.sleep(1)

                    # Re-query rows after navigation
                    rows = page.query_selector_all("//tr[@class='el-table__row']")

                except Exception as row_err:
                    logger.error(f"[ERROR] Failed to process row {idx + 1}: {row_err}")
                    traceback.print_exc()
                    # Try to recover — go back to the list
                    try:
                        page.go_back()
                        time.sleep(1)
                        rows = page.query_selector_all("//tr[@class='el-table__row']")
                    except Exception:
                        pass
                    continue

            db.session.commit()
            logger.info(f"[INFO] Successfully processed KYC for short_code {short_code}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"[ERROR] extract_user_agent_kyc failed for {short_code}: {e}")
            traceback.print_exc()


    def _parse_and_save_kyc(self, kyc_html: str, short_code: str, agent_company, operator_role: str = None) -> None:

        """
        Parses the inner HTML of //div[@class='common-kyc-form common-kyc-form-review']
        and upserts a UserAgent record.

        HTML structure (confirmed from last_kyc_debug.html):
          - Label  : div.el-form-item__label
          - Value  : span.view_span  (sibling div.el-form-item__content inside same div.el-form-item)
          - ID Details use an el-table; values are also span.view_span in tbody td cells.
        """
        soup = BeautifulSoup(kyc_html, "html.parser")

        def get_field(label: str) -> str:
            """
            Find a div.el-form-item__label whose text matches `label`,
            then return the text of span.view_span inside the adjacent
            div.el-form-item__content.
            """
            for lbl_div in soup.find_all("div", class_="el-form-item__label"):
                if lbl_div.get_text(strip=True) == label:
                    parent = lbl_div.find_parent("div", class_="el-form-item")
                    if parent:
                        content = parent.find("div", class_="el-form-item__content")
                        if content:
                            val = content.find("span", class_="view_span")
                            if val:
                                return val.get_text(strip=True)
            return ""

        def val_or_none(v: str):
            """Return None for empty / dash values."""
            return v if v and v != "-" else None

        # ── Personal Details ──────────────────────────────────────────────
        first_name    = get_field("First Name")
        middle_name   = get_field("Middle Name")
        last_name     = get_field("Last Name")
        date_of_birth = get_field("Date of Birth")
        gender        = get_field("Gender")
        email         = get_field("Email")
        nationality   = get_field("Nationality")
        phone_number  = get_field("Preferred Contact Phone Number")

        # ── ID Details (table: two span.view_span per row) ────────────────
        id_number = ""
        id_rows = soup.select("div.array-kyc-group tbody tr.el-table__row")
        for id_row in id_rows:
            spans = id_row.select("span.view_span")
            if len(spans) >= 2:
                id_number = spans[1].get_text(strip=True)  # column 2 = ID Number
                break  # take the first ID row

        # ── Contact Details ───────────────────────────────────────────────
        notif_msisdn = get_field("Notification Receiving MSISDN")
        notif_email  = get_field("Notification Receiving E-mail")

        # ── Combine ───────────────────────────────────────────────────────
        lastname  = " ".join(filter(None, [middle_name, last_name])).strip() or last_name
        phone     = val_or_none(phone_number) or val_or_none(notif_msisdn)
        email_val = val_or_none(email) or val_or_none(notif_email)

        if not id_number or id_number == "-":
            logger.warning("[WARN] No ID number found in KYC form, skipping.")
            return


        # Look for an existing UserAgent scoped to this company with the same role (category).
        # If found → update; if different role or no match → create a new UserAgent for this company.
        existing = None
        if agent_company:
            existing = (
                UserAgent.query
                .filter_by(operator_role=operator_role)
                .filter(
                    db.or_(
                        UserAgent.agent_company_id == agent_company.id,
                        UserAgent.agent_companies.any(id=agent_company.id)
                    )
                )
                .first()
            )
        if existing:
            existing.firstname         = first_name or existing.firstname
            existing.lastname          = lastname   or existing.lastname
            existing.idnumber          = id_number
            existing.authenticity_desc = f"Scraped from KYC (short_code={short_code})"
            if phone:
                existing.phone_number = phone
            if self.user_id:
                existing.user_id = self.user_id
            if agent_company and not existing.agent_company_id:
                existing.agent_company_id = agent_company.id
            user_agent = existing
            logger.info(f"[INFO] Updated UserAgent id={existing.id} role={operator_role}")
        else:
            # Guard against idnumber uniqueness violation: if this ID number is already in the
            # system under a different company/role, we reuse that record rather than duplicating.
            id_conflict = UserAgent.query.filter_by(idnumber=id_number).first()
            if id_conflict:
                id_conflict.firstname         = first_name or id_conflict.firstname
                id_conflict.lastname          = lastname   or id_conflict.lastname
                id_conflict.authenticity_desc = f"Scraped from KYC (short_code={short_code})"
                if phone:
                    id_conflict.phone_number = phone
                if operator_role:
                    id_conflict.operator_role = operator_role
                if self.user_id:
                    id_conflict.user_id = self.user_id
                if agent_company and not id_conflict.agent_company_id:
                    id_conflict.agent_company_id = agent_company.id
                user_agent = id_conflict
            else:
                user_agent = UserAgent(
                    firstname=first_name,
                    lastname=lastname,
                    idnumber=id_number,
                    phone_number=phone,
                    is_authentic=False,
                    authenticity_desc=f"Scraped from KYC (short_code={short_code})",
                    operator_role=operator_role,
                    user_id=self.user_id,
                    agent_company_id=agent_company.id if agent_company else None
                )
                db.session.add(user_agent)
                db.session.flush()
                logger.info(f"[INFO] Created new UserAgent id={user_agent.id} role={operator_role}")

        if agent_company and agent_company not in user_agent.agent_companies:
            user_agent.agent_companies.append(agent_company)
            logger.info(f"[INFO] Linked UserAgent to AgentCompany {agent_company.company_name}")

    def navigate_to_review_transaction(self, business_short_code:str, page:Page) -> bool:

        """Navigate through detail panel to Review Transaction button."""
        try:
            self.close_irritative_dialog_box(page)
            # Click first div in vertical-page-container
            first_div = page.wait_for_selector(
                "//div[@class='vertical-page-container']/div[1]",
                timeout=10000
            )
            first_div.click()
            page.wait_for_timeout(1000)
        
            # Click "More" button
            more_button = page.wait_for_selector(
                "//button[@class='el-button el-button--primary is-link']",
                timeout=10000
            )
            more_button.click()
            page.wait_for_timeout(1000)
        
            self.extract_user_agent_kyc(short_code=business_short_code,page=page)

            # Click "Review Transaction"
            review_btn = page.wait_for_selector(
                "//div[contains(text(),'Review Transaction')]",
                timeout=10000
            )
            review_btn.click()
            page.wait_for_timeout(1500)
        
            return True
        except Exception as e:
            logger.error(f"[ERROR] Navigation failed: {e}")
            return False

    def select_pagination_size(self, page: Page, down_presses: int = 3, timeout: int = 20000) -> bool:

        """
        Opens the page size dropdown in Element Plus table pagination and selects
        an option by pressing down arrow the specified number of times + Enter.
    
        Most common use-case: down_presses=4 usually selects "50" if default is 10
    
        Returns:
            bool: True if operation succeeded, False otherwise
        """
        try:
        
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # page.wait_for_load_state("networkidle", timeout=10000)
        
            pagination_dropdown = "//span[@class='el-pagination__sizes']//i[@class='el-icon el-select__caret el-select__icon']"
            dropdown = page.locator(pagination_dropdown).first
            time.sleep(1)
        
            if dropdown.is_visible():
                dropdown.click()
            
                for _ in range(3):
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.2)
            
                page.keyboard.press("Enter")
            else:
                logger.warning("[WARN] Pagination size dropdown not visible")
                return False

            # Optional: wait a tiny bit for UI to settle
            time.sleep(1)

            return True

        except Exception as e:
            logger.error(f" Error while changing page size: {e}")
            return False
    
    

    def select_pagination_size_prev_press(self, page: Page, down_presses: int = 3, timeout: int = 20000, prev_presses: int = 0) -> bool:

        """
        Opens the page size dropdown in Element Plus table pagination and selects
        an option by pressing down arrow the specified number of times + Enter.
    
        Most common use-case: down_presses=4 usually selects "50" if default is 10
    
        Returns:
            bool: True if operation succeeded, False otherwise
        """
        try:
        
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # page.wait_for_load_state("networkidle", timeout=10000)
        
            pagination_dropdown = "//span[@class='el-pagination__sizes']//i[@class='el-icon el-select__caret el-select__icon']"
            dropdown = page.locator(pagination_dropdown).first
            time.sleep(1)
        
            if dropdown.is_visible():
                dropdown.click()
            
                if prev_presses > 0:
                    for _ in range(prev_presses):
                        page.keyboard.press("ArrowUp")
                        time.sleep(0.2)
            
                for _ in range(down_presses):
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.2)
            
                page.keyboard.press("Enter")
            else:
                logger.warning("[WARN] Pagination size dropdown not visible")
                return False

            # Optional: wait a tiny bit for UI to settle
            time.sleep(1)

            return True

        except Exception as e:
            logger.error(f" Error while changing page size: {e}")
            return False
    
    def close_irritative_dialog_box(self, page:Page) -> bool:

        """Close any irritative dialog boxes that may block interactions."""
        try:
            dialog_box = page.locator("//button[@aria-label='Close this dialog']").first
            if dialog_box.is_visible():
                dialog_box.click()
                page.wait_for_timeout(1000)
                return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to close irritative dialog box: {e}")
        return False

    def does_transaction_exist_for_period_(self, page:Page) -> bool:

        """Close any irritative dialog boxes that may block interactions."""
        try:
            org_detail = page.wait_for_selector(
                "//div[@class='el-table--fit el-table--border el-table--enable-row-hover el-table el-table--layout-fixed is-scrolling-none']//span[@class='el-table__empty-text'][normalize-space()='No records found.']",
                timeout=5000
            )
            return False
        except Exception as e:
            logger.warning(f"[WARN]: The transactions exists {e}")
            return True
    
    def close_portal_tabs(self, page: Page) -> None:

        """Click the last (//i[@class='el-icon']) icon to close the most recently opened portal tab."""
        try:
            icons = page.locator("//i[@class='el-icon']")
            count = icons.count()
            if count <= 2:
                return
            last_icon = icons.nth(count - 1)
            if last_icon.is_visible():
                logger.info(f"[INFO] Closing last portal tab via icon [{count}]")
                last_icon.click()
                page.wait_for_timeout(500)
            logger.info(f"[INFO] Total portal tabs (icons) found: {count}")
        except Exception as e:
            logger.warning(f"[WARN] close_portal_tabs: {e}")

    def close_detail_panel(self, page):

        """Attempt to close any open detail panels and return to list."""
        logger.info("[INFO] Attempting to close detail panel...")
        try:
            # Try clicking "Organization Detail" tab to go back
            # org_detail = page.locator("//div[@title='Organization Detail']").first
            org_detail = page.locator("(//i[@class='el-icon'])[3]")
            if org_detail.is_visible():
                org_detail.click()
                page.wait_for_timeout(1000)
                return True
        except:
            logger.warning("[WARN] 'Organization Detail' tab not found.")
            pass
    
        # Try ESC key
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            return True
        except:
            pass
    
        return False


    def close_detail_panel_idx(self, page:Page , idx: int = 4) -> bool:

        """Attempt to close any open detail panels and return to list."""
        logger.info("[INFO] Attempting to close detail panel...")
        try:
            # Try clicking "Organization Detail" tab to go back
            # org_detail = page.locator("//div[@title='Organization Detail']").first
            org_detail = page.locator(f"(//i[@class='el-icon'])[{idx}]")
            if org_detail.is_visible():
                org_detail.click()
                page.wait_for_timeout(1000)
                return True
            else:
                logger.warning(f"[WARN] Detail panel icon at index {idx} not visible.")
                return False
        except:
            logger.warning("[WARN] 'Organization Detail' tab not found.")
            return False

    def return_to_organization_list(self, page) -> bool:

        """Return to organization list view."""
        logger.info("[INFO] Returning to organization list...")
        for _ in range(3):
            self.close_detail_panel(page)
        try:
            org_detail = page.wait_for_selector(
                "//div[@title='Organization Detail']",
                timeout=5000
            )
            org_detail.click()
            page.wait_for_timeout(1000)
            self.close_portal_tabs(page)
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to return to organization list: {e}")
            return False

    def _scrape_head_office(self, page: Page) -> None:

        """Navigate to the dashboard and run head office + children commission scraping."""
        try:
            page.locator("(//*[name()='svg'][@class='svg-icon'])[1]").first.click()
            time.sleep(2)
        except Exception as _nav_err:
            logger.error(f"[WARN] Dashboard nav click failed: {_nav_err}")
        self.scrape_head_office_commission(page)


    def _run_float_pass(self, page: Page, active_short_codes: Set[str], to_be_rerun: list) -> int:

        """Run a float-only pagination loop for the given set of shortcodes. Returns total processed."""
        total = 0
        first = True
        while True:
            if first:
                time.sleep(0.5)
                first = False
            else:
                self.wait_for_table_load(page)

            total_in_list = self.get_total_from_pagination(page)
            if not total_in_list:
                break

            processed = self.process_page_rows(
                page=page,
                total_in_list=total_in_list,
                total_processed_so_far=total,
                priority_short_codes=active_short_codes,
                to_be_rerun=to_be_rerun,
                pass_value="first",
            )
            total += processed

            if not self.go_forth_on_organization(page, total_in_list):
                break
            time.sleep(1)
        return total


    def process_organization_rows(self, page: Page) -> None:

        """
        Main orchestrator: Processes all organization rows across pagination and virtual scrolling.
        """
        total_processed = 0
        to_be_rerun: list[int] = []
        self.close_irritative_dialog_box(page)
        all_shortcodes_: Set[str] = set()
        time.sleep(1)
        all_shortcodes = self.extract_all_business_short_codes(page, all_shortcodes_)
        logger.info(f"[INFO] Extracted {len(all_shortcodes)} business short codes on all pages")

        priority_short_codes = self._get_priority_shortcodes_(all_shortcodes)
        logger.info(f"[INFO] {len(priority_short_codes)} priority short codes identified for processing")
        has_priority_codes = bool(priority_short_codes)

        while self.go_previous_on_organisation(page):
            pass  # Go back to first page

        def _do_swaps_then_return(label: str) -> None:
            """Scrape swaps (dedup skips already-done shortcodes), then navigate back to child org list."""
            logger.info(f"[INFO] [{label}] Starting swaps scrape...")
            self._scrap_swaps_(page, all_shortcodes)
            logger.info(f"[INFO] [{label}] Swaps done. Navigating back to Child Organisation list...")
            self._navigate_to_child_org_list(page)
            self.wait_for_table_load(page)

        def _do_retries(label: str) -> None:
            """Run retry pass if anything failed, then scrape swaps and return to child org list."""
            if not to_be_rerun:
                return
            logger.info(f"[WARN] [{label}] {len(to_be_rerun)} organizations need reprocessing: {to_be_rerun}")
            self._navigate_to_child_org_list(page)
            self.wait_for_table_load(page)
            if self.rerun_failed_codes(page, to_be_rerun):
                logger.info(f"[SUCCESS] [{label}] All retries succeeded.")
            else:
                logger.error(f"[ERROR] [{label}] Some organizations still failed after retries.")
            to_be_rerun.clear()
            _do_swaps_then_return(f"{label} post-retry")

        if not has_priority_codes:
            # ── Case 1: no priority shortcodes ──────────────────────────────────
            logger.info("[INFO] No priority shortcodes — scraping Head Office Commission first...")
            self._scrape_head_office(page)
            logger.info("[INFO] Navigating back to Child Organisation list for float scraping...")
            self._navigate_to_child_org_list(page)
            self.wait_for_table_load(page)

            total_processed = self._run_float_pass(page, all_shortcodes, to_be_rerun)
            logger.info(f"[SUCCESS] Float pass complete — {total_processed} organizations processed.")

            # After pass: swaps → back to child list
            _do_swaps_then_return("Case1 pass1")
            # Retries → swaps → back to child list
            _do_retries("Case1")
        else:
            # ── Case 2: priority shortcodes exist ───────────────────────────────
            logger.info("[INFO] Scraping Head Office Commission and Children Commission...")
            self._scrape_head_office(page)

            # Pass 1: priority children float
            logger.info("[INFO] Starting priority float pass...")
            self._navigate_to_child_org_list(page)
            self.wait_for_table_load(page)
            total_processed = self._run_float_pass(page, priority_short_codes, to_be_rerun)
            logger.info("[INFO] Priority float pass complete.")

            # After pass 1: swaps → back to child list
            _do_swaps_then_return("Case2 pass1")
            # Retries for pass 1 failures → swaps → back to child list
            _do_retries("Case2 pass1")

            # Pass 2: all children float
            logger.info("[INFO] Starting all-children float pass...")
            all_pass_total = self._run_float_pass(page, all_shortcodes, to_be_rerun)
            logger.info(f"[SUCCESS] All-children float pass complete — {all_pass_total} organizations processed.")

            # After pass 2: swaps → back to child list
            _do_swaps_then_return("Case2 pass2")
            # Retries for pass 2 failures → swaps → back to child list
            _do_retries("Case2 pass2")

            stats = transaction_service.gather_scraping_statistics(
                start_date=datetime.now() - timedelta(days=180),
                end_date=datetime.now(),
                company_shortcode=self.company_shortcode,
            )
            send_scraping_report_email(self.user.email, stats)

    def scrape_child_org_commission(self, page:Page,business_shortcode:str=""):

        try:
            logger.info("[INFO] Scraping Child Organisation Commission...")
            commission_tab = page.wait_for_selector(
                "//div[@class='item_name item_num_active'][normalize-space()='Balance Overview']",
                timeout=10000
            )
            commission_tab.click()
            time.sleep(1)
            # Add any specific scraping logic for the commission tab here

            account_type_dropdown = page.wait_for_selector(
                "//div[@class='form-content__box']//i[@class='el-icon el-select__caret el-select__icon']",
                timeout=10000
            )
            account_type_dropdown.click()
            time.sleep(0.5)

            for _ in range(9):
                page.keyboard.press("ArrowDown")
                time.sleep(0.1)
            page.keyboard.press("Enter")
            time.sleep(2)

            #click on search 
            search_button = page.wait_for_selector(
                "//button[@class='el-button el-button--primary']",
                timeout=10000
            )
            search_button.click()
            time.sleep(0.5)

            self.save_table_to_dataframe_download_head_office(
                page, business_shortcode,
                filter_text="CSV",
                min_item_count=1,   # adjust if CSV has fewer menu entries than Excel
                target_index=1,
            )
        except Exception as e:
            logger.error(f"[ERROR] Failed to scrape child organization commission: {e}")

    def wait_for_table_load(self, page: Page, timeout: int = 15000) -> None:

        """Wait for network idle and allow lazy loading."""
        page.wait_for_load_state("networkidle", timeout=timeout)
        time.sleep(0.5)
    
    def extract_all_business_short_codes(
        self,
        page: Page,
        short_codes: Optional[Set[str]] = None
    ) -> Set[str]:

        if short_codes is None:
            short_codes = set()

        rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")
        logger.info(f"The length of the shortcodes is {len(short_codes)}")    

        for i in range(rows_locator.count()):
            row = rows_locator.nth(i)

            try:
                row_text = row.text_content(timeout=3000) or ""
                match = re.search(r'^(\d+)', row_text.strip())
                if match:
                    short_codes.add(match.group(1))  # set auto-deduplicates
            except Exception as e:
                logger.error(f"[ERROR] Error extracting short code from row: {e}")

        if self.go_forth_on_organization(page, self.get_total_from_pagination(page)):
            self.wait_for_table_load(page)
            # logger.info(f"From page {counter} We are passing {len(short_codes)}")
            self.extract_all_business_short_codes(page, short_codes)

        return short_codes

    def _get_stale_scrape_shortcodes_(self, all_shortcodes: Set[str], stale_days: int = 30) -> Set[str]:

        """
        Return shortcodes from all_shortcodes that have never been scraped OR whose
        AgentCompany.last_scraped_at is older than stale_days.  This catches agents
        who have been inactive (no new transactions) for a long period but have never
        been confirmed as inactive by a recent scrape run.
        """
        from app.model.agentcompany import AgentCompany
        from app import db

        stale: Set[str] = set()
        cutoff = datetime.now() - timedelta(days=stale_days)

        # Single query: find all AgentCompany rows matching any of the shortcodes
        # where last_scraped_at is NULL or older than the cutoff.
        matching = db.session.query(
            AgentCompany.short_code,
            AgentCompany.business_short_code,
            AgentCompany.agentcompany_code,
            AgentCompany.last_scraped_at,
        ).filter(
            db.or_(
                AgentCompany.short_code.in_(all_shortcodes),
                AgentCompany.business_short_code.in_(all_shortcodes),
                AgentCompany.agentcompany_code.in_(all_shortcodes),
            ),
            db.or_(
                AgentCompany.last_scraped_at == None,
                AgentCompany.last_scraped_at < cutoff,
            )
        ).all()

        for row in matching:
            for code in (row.short_code, row.business_short_code, row.agentcompany_code):
                if code and code in all_shortcodes:
                    stale.add(code)

        # Shortcodes not in AgentCompany at all (brand-new, never registered) are also stale.
        known_codes: Set[str] = set()
        all_known = db.session.query(
            AgentCompany.short_code,
            AgentCompany.business_short_code,
            AgentCompany.agentcompany_code,
        ).filter(
            db.or_(
                AgentCompany.short_code.in_(all_shortcodes),
                AgentCompany.business_short_code.in_(all_shortcodes),
                AgentCompany.agentcompany_code.in_(all_shortcodes),
            )
        ).all()
        for row in all_known:
            for code in (row.short_code, row.business_short_code, row.agentcompany_code):
                if code:
                    known_codes.add(code)

        unregistered = all_shortcodes - known_codes
        stale.update(unregistered)

        if stale:
            logger.info(f"[PRIORITY] {len(stale)} shortcode(s) stale by scrape-age (>{stale_days}d or never scraped): {sorted(stale)}")

        return stale


    def _get_priority_shortcodes_(self, all_shortcodes: Set[str]) -> Set[str]:

        """
        Return shortcodes that need a priority float scrape.  A shortcode qualifies if:
          1. Its newest float transaction is >= 1 day old  (data-staleness), OR
          2. It has never been scraped / not scraped in the last 30 days
             (scrape-coverage gap — catches inactive agents we haven't confirmed recently).
        """
        priority_shortcode_indexes: Set[str] = set()

        logger.info(f"All shortcodes are of length {len(all_shortcodes)}")

        for business_shortcode in all_shortcodes:
            total_months, days = self._get_total_months_by_shortcode_shortfall(
                business_shortcode,
                self.till_scraping_shortfall,
                transaction_type='float'
            )


            if days >= 1:
                priority_shortcode_indexes.add(business_shortcode)

        # Criterion 2: scrape-coverage gap
        stale_by_scrape_age = self._get_stale_scrape_shortcodes_(all_shortcodes, stale_days=30)
        priority_shortcode_indexes.update(stale_by_scrape_age)

        return priority_shortcode_indexes

    # def force_refresh_with_routing(page:Page):
    #     try:
    #         # Disable HTTP cache by enabling routing
    #         # The route handler simply continues the request without caching
    #         page.route('**', lambda route: route.continue())

    #         page.goto("https://example.com")
    #         logger.info("Page loaded the first time (cache disabled).")

    #         # Now, page.reload() will perform a hard refresh because the cache is disabled
    #         page.reload()
    #         logger.info("Page reloaded (hard refresh).")

    #         return True
    #     except Exception as e:
    #         logger.error(f"[ERROR] An error occurred {str(e)}")
    #         return False

    def _is_agent_company_scraped(self, business_short_code: int) -> bool:

        """Check if an agent company with this shortcode has already been scraped (till details + KYC saved)."""
        try:
            from app.model.agentcompany import AgentCompany
            company = AgentCompany.query.filter(
                db.or_(
                    AgentCompany.agentcompany_code == str(business_short_code),
                    AgentCompany.short_code == str(business_short_code),
                    AgentCompany.business_short_code == str(business_short_code)
                )
            ).first()
            if company and company.last_scraped_at is not None:
                return True
            return False
        except Exception as e:
            logger.warning(f"[WARN] Could not check scrape status for {business_short_code}: {e}")
            return False

    def process_single_row_kyc_only(self, page: Page, business_short_code: int, row_number: int) -> bool:

        """
        Lightweight scrape: only till details + KYC contacts.
        Skips transaction scraping (float/commission).
        Used for non-priority tills that haven't been scraped yet.
        """
        try:
            logger.info(f"\n[KYC-ONLY] Processing Row {row_number} | Business Code: {business_short_code} (lightweight)")
            self.close_irritative_dialog_box(page)

            # Scrape basic till details and save agent company
            mapped_data = self.scrape_till_details(page, business_short_code)

            # Save the scraped till details to DB
            save_results = agent_company_service.save_or_update_scraped_agent_company(
                mapped_data=mapped_data, user_id=self.user_id
            )
            logger.info(f"[KYC-ONLY] Saved till details: {save_results}")

            # Navigate to detail panel to extract KYC
            try:
                self.close_irritative_dialog_box(page)
                first_div = page.wait_for_selector(
                    "//div[@class='vertical-page-container']/div[1]",
                    timeout=10000
                )
                first_div.click()
                page.wait_for_timeout(1000)

                more_button = page.wait_for_selector(
                    "//button[@class='el-button el-button--primary is-link']",
                    timeout=10000
                )
                more_button.click()
                page.wait_for_timeout(1000)

                # Extract KYC user agents
                self.extract_user_agent_kyc(short_code=business_short_code, page=page)
                logger.info(f"[KYC-ONLY] KYC extraction complete for {business_short_code}")
            except Exception as kyc_err:
                logger.error(f"[KYC-ONLY] KYC extraction failed for {business_short_code}: {kyc_err}")

            # Return to org list
            if not self.return_to_organization_list(page):
                logger.error("[KYC-ONLY] Failed to return to list — attempting recovery")
                page.reload()
                self.wait_for_table_load(page)
                return False

            return True

        except Exception as e:
            logger.error(f"[ERROR] KYC-only processing failed for {business_short_code}: {e}")
            traceback.print_exc()
            self.close_irritative_dialog_box(page)
            self.close_detail_panel(page)
            return False

    def process_page_rows(
        self,
        page: Page,
        total_in_list: int,
        total_processed_so_far: int,
        priority_short_codes: set[str],
        to_be_rerun: list[int],
        pass_value: str
    ) -> int:
        """Process all visible rows on the current page with virtual scrolling support."""
        self.close_irritative_dialog_box(page)
        processed_on_page = 0
        rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")

        visible_rows = self.get_visible_rows(rows_locator)

        logger.info(f"The priority short codes are {priority_short_codes}")

        if not visible_rows:
            logger.info("[INFO] No visible rows — scrolling to load more...")
            page.mouse.wheel(0, 1200)
            time.sleep(2)

        visible_rows_size = len(visible_rows)
        logger.info(f"[INFO] Found {visible_rows_size} visible rows to process on this page")

        for row in visible_rows:
            if processed_on_page >= 10:
                break

            business_short_code = self.extract_business_short_code(row)
            if not business_short_code:
                processed_on_page += 1
                continue

            is_priority = str(business_short_code) in priority_short_codes
            already_scraped = self._is_agent_company_scraped(business_short_code)

            if not is_priority and already_scraped:
                # Non-priority AND already scraped — skip entirely
                logger.info(f"[INFO] Skipping row {business_short_code} — not priority and already scraped.")
                processed_on_page += 1
                continue

            row.click(timeout=15000)
            page.wait_for_timeout(1000)

            if is_priority:
                # Full scrape: till details + KYC + transactions
                success = self.process_single_row(page, business_short_code, total_processed_so_far + processed_on_page + 1, pass_value=pass_value)
            else:
                # Lightweight scrape: till details + KYC only (no transactions)
                logger.info(f"[INFO] Non-priority but unscraped — doing KYC-only scrape for {business_short_code}")
                success = self.process_single_row_kyc_only(page, business_short_code, total_processed_so_far + processed_on_page + 1)

            if success:
                logger.info(f"[SUCCESS] Completed row {total_processed_so_far + processed_on_page + 1}")
            else:
                if is_priority:
                    to_be_rerun.append(business_short_code)
                self.return_to_organization_list(page)
                logger.error(f"[WARN] Row {business_short_code} failed{', added to rerun list' if is_priority else ''}")

            processed_on_page += 1

        # Scroll to load more rows if needed
        if total_in_list and processed_on_page < total_in_list:
            page.mouse.wheel(0, 1200)
            time.sleep(0.5)

        return processed_on_page

    def get_visible_rows(self, rows_locator: Locator) -> list[Locator]:

        """Return only currently visible rows."""
        count = rows_locator.count()
        return [
            rows_locator.nth(i)
            for i in range(count)
            if rows_locator.nth(i).is_visible()
        ]

    def extract_business_short_code(self, row: Locator) -> int | None:

        """Extract the leading numeric business short code from the row text."""
        try:
            row.scroll_into_view_if_needed(timeout=10000)
            # page.wait_for_timeout(800)

            row_text = row.text_content(timeout=5000) or ""
            match = re.search(r'^(\d+)', row_text.strip())
            if not match:
                logger.warning(f"[WARN] Could not extract business short code from row: {row_text[:100]}...")
                return None

            return int(match.group(1))
        except Exception as e:
            logger.error(f"[ERROR] Failed to extract short code: {e}")
            return None

    _TRANSACTION_TYPE_DROPDOWN_XPATH = (
        "//body[1]/div[1]/div[1]/main[1]/section[1]/div[1]/section[1]/div[1]"
        "/div[2]/div[1]/div[1]/div[2]/div[1]/form[1]/div[1]/div[5]/div[1]"
        "/div[1]/div[1]/div[1]/div[1]/div[1]"
    )
    _TRANSACTION_TABLE_HEADER_XPATH = (
        "//div[@class='el-table--fit el-table--border el-table--enable-row-transition el-table el-table--layout-fixed"
        "table-page is-scrolling-none']//div[@class='el-table__inner-wrapper']"
    )


    def _elapsed(self, t0: float) -> str:

        return f"{time.time() - t0:.2f}s"


    def scrape_transaction_tab(self, page: Page, business_short_code: int) -> bool:

        """Navigate to the Transactions tab, set a single 2-month date range, filter to Commission, download Excel."""
        try:
            page.click("(//div[@id='tab-transactions'])[1]")
            time.sleep(2)
            self.close_irritative_dialog_box(page)

            # Build a single date range: first day 2 months ago → today
            today = datetime.now()
            three_months_ago_month = today.month - 2
            three_months_ago_year = today.year
            while three_months_ago_month <= 0:
                three_months_ago_month += 12
                three_months_ago_year -= 1
            start_date_str = f"{datetime(three_months_ago_year, three_months_ago_month, 1).strftime('%d/%m/%Y')} 00:00:00"
            end_date_str   = f"{today.strftime('%d/%m/%Y')} 23:59:59"

            logger.info(f"[INFO] Transactions tab scrape | {business_short_code} | {start_date_str} → {end_date_str}")

            page.click("body", position={"x": 10, "y": 10})
            time.sleep(0.5)

            start_input = self._find_visible_date_input(page, "Start Time")
            start_input.click()
            start_input.fill("")
            time.sleep(0.2)
            start_input.type(start_date_str)
            start_input.press("Enter")
            time.sleep(0.5)

            end_input = self._find_visible_date_input(page, "End Time")
            end_input.click()
            end_input.fill("")
            time.sleep(0.5)
            end_input.type(end_date_str)
            end_input.press("Enter")
            time.sleep(1.5)


            try:
                # Open transaction-type dropdown and navigate to the Commission option
                page.click(self._TRANSACTION_TYPE_DROPDOWN_XPATH)
                time.sleep(0.5)

                commission_found = False
                for _ in range(30):  # safety cap
                    active_text = page.evaluate("""() => {
                        const el = document.querySelector(
                            '.el-select-dropdown__item.hover, .el-select-dropdown__item.is-hovering'
                        );
                        return el ? el.textContent.trim() : '';
                    }""")
                    if re.search(r'commission', active_text, re.IGNORECASE):
                        page.keyboard.press("Enter")
                        commission_found = True
                        logger.info(f"[INFO] Selected dropdown option: '{active_text}'")
                        break
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.3)

                if not commission_found:
                    logger.warning("[WARN] Commission option not found in dropdown after 30 steps — proceeding anyway")
            except Exception as e:
                logger.error(f"[ERROR] Failed to select Commission from dropdown: {e}")
                logger.info("[INFO] Attempting fallback method to select Commission option...")
                # Open transaction-type dropdown and navigate to the Commission option
                page.click(self._TRANSACTION_TYPE_DROPDOWN_XPATH)
                time.sleep(0.5)

                commission_found = False
                for _ in range(30):  # safety cap
                    active_text = page.evaluate("""() => {
                        const el = document.querySelector(
                            '.el-select-dropdown__item.hover, .el-select-dropdown__item.is-hovering'
                        );
                        return el ? el.textContent.trim() : '';
                    }""")
                    if re.search(r'commission', active_text, re.IGNORECASE):
                        page.keyboard.press("Enter")
                        commission_found = True
                        logger.info(f"[INFO] Selected dropdown option: '{active_text}'")
                        break
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.3)

                if not commission_found:
                    logger.warning("[WARN] Commission option not found in dropdown after 30 steps — proceeding anyway")

            self.click_search_button_head_office(page)
            time.sleep(2)

            # Hover the visible export trigger (there are 2 in the DOM; :visible picks the right one)
            t = time.time()
            export_trigger = page.locator("div.el-dropdown.padding-export:visible >> span").first
            export_trigger.wait_for(state="visible", timeout=30000)
            export_trigger.scroll_into_view_if_needed()
            export_trigger.hover(force=True, timeout=10_000)
            logger.info(f"[TIMING] Export trigger hovered: {self._elapsed(t)}")
            time.sleep(3)

            page.wait_for_function(
                """() => {
                    const menus = document.querySelectorAll('ul.el-dropdown-menu');
                    for (const menu of menus) {
                        const rect = menu.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && rect.top >= 0) return true;
                    }
                    return false;
                }""",
                timeout=40000,
            )
            logger.info(f"[TIMING] Export dropdown open: {self._elapsed(t)}")

            all_items = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")
            excel_items = all_items.filter(has_text="Excel")
            excel_count = excel_items.count()
            logger.info(f"[EXPORT] Found {excel_count} Excel option(s)")

            if excel_count < 1:
                raise Exception(f"No Excel export options found (count={excel_count})")

            target_excel = excel_items.last

            t = time.time()
            with page.expect_download(timeout=60_000) as dl_info:
                try:
                    target_excel.click(force=True, timeout=15_000)
                    logger.info("[EXPORT] Clicked Excel option")
                except Exception:
                    logger.error("[EXPORT] Normal click failed — falling back to JS click")
                    target_excel.evaluate("el => el.click()")

            download = dl_info.value
            temp_path = download.path()
            logger.info(f"[TIMING] Excel downloaded: {self._elapsed(t)}")

            # Parse and persist directly from the Playwright temp file
            t = time.time()
            df, success = self.update_transactions_from_file(
                file_path=temp_path,
                business_shortcode=str(business_short_code),
                transaction_type="commission",
                company_shortcode=self.company_shortcode,
                agent_id=None,
            )
            logger.info(f"[TIMING] DB upsert: {self._elapsed(t)} | success={success} | rows={len(df) if df is not None else 0}")

            return True

        except Exception as e:
            logger.error(f"[ERROR] self.scrape_transaction_tab({business_short_code}): {e}")
            traceback.print_exc()
            return False


    def process_single_row(self, page: Page, business_short_code: int, row_number: int, pass_value: int) -> bool:

        """Process one organization row end-to-end."""
        try:
            logger.info(f"\n[SUCCESS] Processing Row {row_number} | Business Code: {business_short_code}")
            self.close_irritative_dialog_box(page)

            # Scrape basic till details
            mapped_data = self.scrape_till_details(page, business_short_code)

            # Persist the company now so extract_user_agent_kyc (called inside
            # navigate_to_review_transaction) can resolve it by short_code.
            # This is intentionally called again in extract_extra_till_info with
            # account details — save_or_update_scraped_agent_company is idempotent.
            agent_company_service.save_or_update_scraped_agent_company(
                mapped_data=mapped_data, user_id=self.user_id
            )

            # Navigate and process float/commission
            if not self.navigate_to_review_transaction(business_short_code=business_short_code,page=page):
                logger.error("[ERROR] Failed to navigate to review transaction")
                self.return_to_organization_list(page)
                return False

            if not self.process_float_commission(page, business_short_code, mapped_data=mapped_data, pass_value=pass_value):
                logger.error("[ERROR] Failed to process float/commission")
                # return_to_organization_list(page)
                return False

            if not self.scrape_transaction_tab(page, business_short_code):
                logger.error("[ERROR] Failed to scrape transaction tab")
                return False

            # Return safely
            if not self.return_to_organization_list(page):
                logger.error("[WARN] Failed to return to list — attempting recovery")
                page.reload()
                self.wait_for_table_load(page)
                return False

            return True

        except Exception as e:
            logger.error(f"[ERROR] Exception processing row {business_short_code}: {e}")
            traceback.print_exc()
            self.close_irritative_dialog_box(page)
            page.screenshot(path=f"error_row_{business_short_code}_{row_number}.png")
            self.close_detail_panel(page)
            return False



if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    short_code = os.getenv('TEST_SHORTCODE')
    username   = os.getenv('TEST_USERNAME')
    password   = os.getenv('TEST_PASSWORD')
    user_id    = os.getenv('TEST_USER_ID', '1')

    if not all([short_code, username, password]):
        logger.error('[ERROR] Set TEST_SHORTCODE, TEST_USERNAME, TEST_PASSWORD in your .env to run locally.')
        sys.exit(1)

    logger.info(f'[TEST] Running MpesaScraper for short_code={short_code}')
    MpesaScraper(
        password=password,
        username=username,
        short_code=short_code,
        user_id_passed=user_id,
    ).run()
