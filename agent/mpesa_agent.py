"""
mpesa_agent.py — Standalone Mpesa portal scraping agent.

Polls the Kwamz AI backend for pending scrape jobs, runs Playwright
automation on the local machine (headless=False, real display required),
and reports all results back to the backend via HTTP API.

No Flask, no SQLAlchemy, no Celery — pure Python.
Package with PyInstaller to produce a distributable executable.

Configuration (edit the CONFIG block below or set environment variables):
  BACKEND_URL   — Base URL of the Kwamz AI backend
  AGENT_SECRET  — Shared secret (must match AGENT_SECRET in server .env)
  POLL_INTERVAL — Seconds between polls when idle (default: 30)
"""

import os
import subprocess
import sys
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

def _ensure_chromium():
    """Install Playwright's Chromium on first run if not already present."""

    # Determine base path — different when frozen by PyInstaller
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        # Playwright bundles its own Node-based CLI inside _internal/
        if os.name == 'nt':
            playwright_cli = os.path.join(base_path, '_internal', 'playwright', 'driver', 'playwright.cmd')
        else:
            playwright_cli = os.path.join(base_path, '_internal', 'playwright', 'driver', 'playwright.sh')
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        playwright_cli = None  # use python -m playwright when not frozen

    # Store browsers next to the executable so they survive restarts
    browsers_path = os.path.join(base_path, 'browsers')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browsers_path

    # Check if chromium is already installed
    chromium_exists = (
        os.path.isdir(browsers_path) and
        any('chromium' in d for d in os.listdir(browsers_path))
    )

    if not chromium_exists:
        print('[SETUP] Chromium not found — installing now (one-time, ~150MB)...')
        if playwright_cli and os.path.exists(playwright_cli):
            subprocess.run([playwright_cli, 'install', 'chromium'], check=True)
        else:
            # Not frozen — standard python -m playwright works fine
            subprocess.run(
                [sys.executable, '-m', 'playwright', 'install', 'chromium'],
                check=True
            )
        print('[SETUP] Chromium installed successfully.')

_ensure_chromium()

from playwright.sync_api import sync_playwright, Page, Locator, Download, TimeoutError as PlaywrightTimeoutError
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple
import pandas as pd
import requests
import base64
import tempfile
import re
import time
import random
import traceback
import sys

# ── Configuration ─────────────────────────────────────────────────────────────

BACKEND_URL   = os.getenv('BACKEND_URL',  'https://kwamz-ai.org')
AGENT_SECRET  = os.getenv('AGENT_SECRET', '')          # MUST be set
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '30'))  # seconds


# ── Backend API client ────────────────────────────────────────────────────────

class BackendClient:
    """Thin wrapper around requests for all backend calls."""

    def __init__(self, base_url: str, secret: str):
        self.base = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'X-Agent-Secret': secret,
        }

    def get(self, path: str, **kwargs) -> dict:
        resp = requests.get(self.base + path, headers=self.headers, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, payload: dict = None, **kwargs) -> dict:
        resp = requests.post(
            self.base + path,
            json=payload or {},
            headers=self.headers,
            timeout=60,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Job lifecycle ──────────────────────────────────────────────────────

    def poll_job(self) -> Optional[dict]:
        data = self.get('/api/agent/scrape-job/pending')
        return data.get('job')

    def heartbeat(self, job_id: str):
        try:
            self.post(f'/api/agent/scrape-job/{job_id}/heartbeat')
        except Exception:
            pass  # non-fatal

    def complete_job(self, job_id: str):
        self.post(f'/api/agent/scrape-job/{job_id}/complete')

    def fail_job(self, job_id: str, error: str):
        try:
            self.post(f'/api/agent/scrape-job/{job_id}/failed', {'error': error})
        except Exception:
            pass

    # ── Data reporting ─────────────────────────────────────────────────────

    def get_last_scraped(self) -> dict:
        """Returns {shortcode: [days, receipt_no]}."""
        try:
            return self.get('/api/agent/last-scraped').get('data', {})
        except Exception as e:
            print(f'[WARN] Could not fetch last-scraped: {e}')
            return {}

    def post_transactions_df(
        self,
        df: pd.DataFrame,
        transaction_type: str,
        company_shortcode: str,
        business_shortcode: str,
    ) -> dict:
        """Send a DataFrame as JSON rows to the backend."""
        try:
            payload = {
                'rows': df.to_dict(orient='records'),
                'columns': list(df.columns),
                'transaction_type': transaction_type,
                'company_shortcode': company_shortcode,
                'business_shortcode': str(business_shortcode),
            }
            return self.post('/api/agent/transactions', payload)
        except Exception as e:
            print(f'[ERROR] post_transactions_df failed: {e}')
            return {'success': False, 'error': str(e)}

    def post_transactions_file(
        self,
        file_path: str,
        transaction_type: str,
        company_shortcode: str,
        business_shortcode: str,
    ) -> dict:
        """Send an Excel file (base64-encoded) to the backend."""
        try:
            with open(file_path, 'rb') as f:
                file_b64 = base64.b64encode(f.read()).decode()
            payload = {
                'file_b64': file_b64,
                'transaction_type': transaction_type,
                'company_shortcode': company_shortcode,
                'business_shortcode': str(business_shortcode),
            }
            return self.post('/api/agent/transactions/file', payload)
        except Exception as e:
            print(f'[ERROR] post_transactions_file failed: {e}')
            return {'success': False, 'error': str(e)}

    def post_organization(self, mapped_data: dict, user_id: str) -> dict:
        try:
            return self.post('/api/agent/organization', {'mapped_data': mapped_data, 'user_id': user_id})
        except Exception as e:
            print(f'[ERROR] post_organization failed: {e}')
            return {'success': False, 'error': str(e)}

    def solve_captcha_vision(self, image_path: str) -> str:
        """Send captcha image to backend; returns the solved text."""
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode()
        result = self.post('/api/agent/captcha/solve-vision', {'image_b64': image_b64})
        return result.get('answer', '')

    def alert_non_active(
        self,
        recipient_email: str,
        business_name: str,
        business_short_code: str,
        status: str,
        sender_email: str = '',
    ):
        try:
            self.post('/api/agent/alert/non-active', {
                'recipient_email': recipient_email,
                'business_name': business_name,
                'business_short_code': str(business_short_code),
                'status': status,
                'sender_email': sender_email,
            })
        except Exception as e:
            print(f'[WARN] alert_non_active failed: {e}')

    def alert_session_timeout(self, user_id: str):
        try:
            self.post('/api/agent/alert/session-timeout', {'user_id': user_id})
        except Exception as e:
            print(f'[WARN] alert_session_timeout failed: {e}')

    def send_report(self, user_id: str, company_shortcode: str):
        try:
            self.post('/api/agent/report/send', {
                'user_id': user_id,
                'company_shortcode': company_shortcode,
            })
        except Exception as e:
            print(f'[WARN] send_report failed: {e}')

    def trigger_fraud_detection(self, user_id: str):
        try:
            self.post('/api/agent/fraud-detection/trigger', {'user_id': user_id})
        except Exception as e:
            print(f'[WARN] trigger_fraud_detection failed: {e}')


# ── Global agent state (scoped per job run) ───────────────────────────────────

api: BackendClient = None
company_shortcode: str = None
user_id: str = None
till_scraping_shortfall: dict = {}
context = None
browser = None
MAX_SEND_ATTEMPTS = 3


# ── Login / captcha helpers ───────────────────────────────────────────────────

def wait_for_login_page_ready(page: Page, timeout: float = 30000):
    page.wait_for_selector("//input[@id='shortCode']", state='visible', timeout=timeout)
    page.wait_for_selector("//input[@id='userAccount']", state='visible', timeout=timeout)
    page.wait_for_selector("//input[@id='password']", state='visible', timeout=timeout)
    page.wait_for_function(
        """() => {
            const s = document.querySelector('#shortCode');
            const u = document.querySelector('#userAccount');
            const p = document.querySelector('#password');
            return s && !s.disabled && u && !u.disabled && p && !p.disabled;
        }""",
        timeout=timeout,
    )


def fill_login_form(page: Page, short_code: str, username: str, password: str):
    wait_for_login_page_ready(page)
    page.fill("//input[@id='shortCode']", short_code)
    page.fill("//input[@id='userAccount']", username)
    page.fill("//input[@id='password']", password)
    print('[INFO] Login form fields filled.')


def capture_and_solve_captcha(page: Page) -> str:
    captcha_selector = "//img[@class='verifyCode-img-item']"
    captcha_path = os.path.join(tempfile.gettempdir(), 'captcha.png')
    max_retries = 3

    for attempt in range(max_retries):
        try:
            page.wait_for_selector(captcha_selector, state='visible', timeout=10000)
            time.sleep(1)
            captcha_locator = page.locator(captcha_selector).first
            captcha_locator.wait_for(state='visible', timeout=5000)
            captcha_locator.screenshot(path=captcha_path)
            solution = api.solve_captcha_vision(captcha_path)
            print(f'[INFO] CAPTCHA solved: {solution}')
            return str(solution)
        except Exception as e:
            print(f'[WARN] CAPTCHA attempt {attempt + 1}/{max_retries} failed: {e}')
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise


def has_verification_error_regex(page: Page) -> bool:
    body_text = page.locator('body').inner_text()
    pattern = re.compile(r'verification\s+code\s+is\s+incorrect\s+or\s+has\s+expired', re.IGNORECASE)
    return bool(pattern.search(body_text))


def retry_captcha_login(page: Page) -> str:
    svg_element = page.query_selector("//div[@class='img-part']//*[name()='svg']")
    if svg_element:
        svg_element.click()
        return capture_and_solve_captcha(page)
    raise Exception('Failed to locate SVG element for captcha refresh')


# ── Navigation helpers ────────────────────────────────────────────────────────

def maximize_page(page: Page) -> None:
    try:
        page.set_viewport_size({'width': 1920, 'height': 1080})
    except Exception as e:
        print(f'[ERROR] maximize_page: {e}')


def scroll_to_top(page: Page) -> None:
    try:
        page.evaluate('window.scrollTo(0, 0);')
        time.sleep(0.5)
    except Exception as e:
        print(f'[ERROR] scroll_to_top: {e}')


def scroll_to_bottom(page: Page) -> None:
    try:
        page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
        time.sleep(1.5)
    except Exception as e:
        print(f'[ERROR] scroll_to_bottom: {e}')


def click_random_spot(page: Page, padding: int = 50) -> None:
    viewport = page.viewport_size
    if not viewport:
        return
    rand_x = random.randint(padding, viewport['width'] - padding)
    rand_y = random.randint(padding, viewport['height'] - padding)
    page.mouse.click(rand_x, rand_y)


def close_irritative_dialog_box(page: Page) -> bool:
    try:
        close_btn = page.locator("button.el-dialog__headerbtn").first
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(0.5)
            return True
        return False
    except Exception:
        return False


def wait_for_table_load(page: Page, timeout: int = 15000) -> None:
    page.wait_for_load_state('networkidle', timeout=timeout)
    time.sleep(0.5)


def get_total_from_pagination(page: Page) -> int:
    locator = page.locator("//div[@id='pagination']/span[contains(text(), 'Total')]").first
    try:
        if locator.count() == 0:
            return 0
        text = locator.inner_text().strip()
        return int(''.join(filter(str.isdigit, text)))
    except Exception as e:
        print(f'[ERROR] get_total_from_pagination: {e}')
        return 0


def go_forth_on_organization(page: Page, row_count: int) -> bool:
    next_btn = page.locator("//button[@aria-label='Go to next page']").first
    try:
        if next_btn.is_enabled():
            next_btn.click()
            page.wait_for_load_state('networkidle', timeout=20000)
            time.sleep(0.5)
            return True
        return False
    except Exception as e:
        print(f'[WARNING] go_forth_on_organization: {e}')
        api.alert_session_timeout(user_id)
        page.screenshot(path='pagination_error.png')
        return False


def go_previous_on_organisation(page: Page) -> bool:
    prev_btn = page.locator("//button[@aria-label='Go to previous page']").first
    try:
        if prev_btn.is_enabled():
            prev_btn.click()
            page.wait_for_load_state('networkidle', timeout=20000)
            time.sleep(0.5)
            return True
        return False
    except Exception as e:
        print(f'[WARNING] go_previous_on_organisation: {e}')
        page.screenshot(path='pagination_error.png')
        return False


def click_search_button(page: Page) -> bool:
    try:
        search_btn = page.locator("//div[@class='section-content']//button").first
        search_btn.wait_for(state='visible', timeout=10000)
        search_btn.click(force=True)
        return True
    except Exception as e:
        print(f'[ERROR] click_search_button: {e}')
        return False


def select_pagination_size(page: Page, down_presses: int = 3, timeout: int = 20000) -> bool:
    try:
        size_selector = page.locator("//div[@id='pagination']//span[contains(@class,'el-select')]").first
        size_selector.wait_for(state='visible', timeout=timeout)
        size_selector.click()
        for _ in range(down_presses):
            page.keyboard.press('ArrowDown')
            time.sleep(0.2)
        page.keyboard.press('Enter')
        time.sleep(1)
        return True
    except Exception as e:
        print(f'[WARN] select_pagination_size: {e}')
        return False


def does_transaction_exist_for_period_(page: Page) -> bool:
    try:
        no_data = page.locator("//div[contains(@class,'el-table__empty-text')]").first
        return not no_data.is_visible()
    except Exception:
        return True


def close_detail_panel(page: Page):
    try:
        close_btn = page.locator("//button[contains(@class,'portal-collapse-close')]").first
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(0.5)
    except Exception:
        pass


def return_to_organization_list(page: Page) -> bool:
    try:
        back_btn = page.locator("//button[contains(@class,'back-btn') or contains(text(),'Back')]").first
        if back_btn.is_visible():
            back_btn.click()
            page.wait_for_load_state('networkidle', timeout=15000)
            time.sleep(1)
            return True
        page.go_back(timeout=15000)
        page.wait_for_load_state('networkidle', timeout=15000)
        return True
    except Exception as e:
        print(f'[ERROR] return_to_organization_list: {e}')
        return False


# ── Till / org extraction ─────────────────────────────────────────────────────

def extract_till_info(inner_html: str) -> dict:
    soup = BeautifulSoup(inner_html, 'html.parser')
    till_info = {}
    for item in soup.find_all('div', class_='list-item'):
        label_div = item.find('div', class_='content-item-label')
        if not label_div:
            continue
        label = label_div.get_text(strip=True)
        value_div = item.find('div', class_='list-item__content-text')
        value = value_div.get_text(strip=True) if value_div else ''
        till_info[label] = None if value == '-' else value
    return till_info


def clean_label_for_db(label: str) -> str:
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
        'registration_date': 'registration_date',
    }
    cleaned = label.lower().strip().replace(' ', '_').replace('-', '_').replace(':', '').replace('.', '')
    return label_mapping.get(cleaned, cleaned)


def parse_date_string(date_str: str):
    if not date_str:
        return None
    for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def map_scraped_data_to_agent_company(scraped_data: dict) -> dict:
    def get_value(key):
        title_key = key.title().replace('_', ' ')
        for k in (title_key, key, key.lower().replace(' ', '_')):
            if k in scraped_data:
                return scraped_data[k]
        return None

    mapped = {
        'company_name': get_value('organization_name') or scraped_data.get('Organization Name'),
        'business_short_code': scraped_data.get('business_short_code'),
        'registration_number': f"SCRAPED-{get_value('short_code') or scraped_data.get('Short Code') or 'UNKNOWN'}",
        'location': get_value('location') or scraped_data.get('Location', 'Unknown'),
        'identity_model': get_value('identity_model'),
        'hierarchy_level': get_value('hierarchy_level'),
        'top_organization': get_value('top_organization'),
        'organization_name': get_value('organization_name'),
        'short_code': get_value('short_code'),
        'identity_status': get_value('identity_status'),
        'segment': get_value('segment'),
        'charge_profile': get_value('charge_profile'),
        'rule_profile': get_value('rule_profile'),
        'trust_level': get_value('trust_level'),
        'data_source': 'portal',
        'is_verified': False,
        'user_id': user_id,
    }

    reg_date = get_value('registration_date') or scraped_data.get('Registration Date')
    if reg_date:
        parsed = parse_date_string(reg_date)
        if parsed:
            mapped['registration_date'] = parsed
            mapped['established_date'] = parsed

    parent = get_value('parent_short_code') or scraped_data.get('Parent Short Code')
    if parent:
        mapped['parent_short_code'] = parent

    return mapped


def is_till_frozen(page: Page) -> bool:
    try:
        div = page.wait_for_selector("//div[normalize-space()='Frozen']", timeout=1000)
        return div.is_visible()
    except Exception:
        return False


def extract_extra_till_info(page: Page, extra_info: dict) -> dict:
    try:
        page.wait_for_selector('.el-col .basic-info-card', timeout=5000)
        all_cards = page.query_selector_all('.el-col .basic-info-card')
        extracted = {}

        for card in all_cards:
            try:
                label_el = card.query_selector('.basic-info-card__label')
                value_el = card.query_selector('.basic-info-card__value')
                if label_el and value_el:
                    label = label_el.inner_text().strip().replace(':', '').replace('.', '')
                    label_key = label.lower().replace(' ', '_').replace('.', '').replace(':', '')
                    value = value_el.inner_text().strip()

                    if label_key in ('current_balance', 'available_balance', 'reserved_balance', 'unclearbalance'):
                        value = value.replace(',', '')
                        try:
                            value = float(value)
                        except Exception:
                            pass

                    if label_key == 'unclearbalance':
                        label_key = 'unclear_balance'
                    elif label_key == 'is_hot_account':
                        value = value.lower() == 'yes'

                    extracted[label_key] = value
            except Exception as card_err:
                print(f'[WARNING] card error: {card_err}')

        if extracted:
            status_val = extracted.get('status')
            if status_val and status_val != 'Active':
                api.alert_non_active(
                    recipient_email='martinmaati31@gmail.com',
                    business_name=extra_info.get('company_name', '-'),
                    business_short_code=extra_info.get('short_code', ''),
                    status=status_val,
                )

            extra_info.update({
                'account_details': extracted,
                'account_number': extracted.get('account_no'),
                'account_type': extracted.get('account_type'),
                'account_alias': extracted.get('alias'),
                'account_currency': extracted.get('currency'),
                'account_relationship': extracted.get('account_relationship'),
                'current_balance': extracted.get('current_balance'),
                'available_balance': extracted.get('available_balance'),
                'account_status': extracted.get('status'),
                'is_hot_account': extracted.get('is_hot_account'),
                'account_scraped_at': datetime.now().isoformat(),
            })

        save_result = api.post_organization(mapped_data=extra_info, user_id=user_id)
        print(f'[DEBUG] post_organization result: {save_result}')
        return save_result

    except Exception as e:
        print(f'[ERROR] extract_extra_till_info: {e}')
        return extra_info


def scrape_till_details(page: Page, business_short_code: int) -> dict:
    try:
        close_irritative_dialog_box(page)
        css_selector = '.portal-collapse .portal-collapse-content'
        page.wait_for_selector(css_selector, state='attached', timeout=30000)
        inner_html = page.eval_on_selector(css_selector, 'el => el.innerHTML')
        till_info = extract_till_info(inner_html)
        till_info['business_short_code'] = business_short_code
        mapped_data = map_scraped_data_to_agent_company(till_info)
        return mapped_data
    except Exception as e:
        print(f'[ERROR] scrape_till_details: {e}')
        return {'success': False, 'error': str(e), 'business_short_code': business_short_code}


# ── Transaction extraction ────────────────────────────────────────────────────

def get_latest_receipt_no(page: Page, business_shortcode: int, pass_value: str) -> str:
    if not isinstance(till_scraping_shortfall, dict):
        return None
    key = business_shortcode if business_shortcode in till_scraping_shortfall else str(business_shortcode)
    if key not in till_scraping_shortfall:
        return None
    value = till_scraping_shortfall[key]
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    return str(value[1])


def parse_element_plus_transactions(
    html_content: str,
    transaction_type: str,
    business_shortcode: str,
) -> Tuple[pd.DataFrame, Any]:
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.select('tbody tr.el-table__row')
    data = []

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 10:
            continue

        receipt_cell = cells[0].find('span', class_='receipt-link')
        receipt_no = receipt_cell.get_text(strip=True) if receipt_cell else ''
        completion_time = cells[1].get_text(strip=True)
        details = cells[2].get_text(strip=True)
        other_party = cells[3].get_text(strip=True)
        status = cells[4].get_text(strip=True)
        currency = cells[5].get_text(strip=True)

        withdrawn_raw = cells[6].get_text(strip=True)
        withdrawn = re.sub(r'[^0-9.]', '', withdrawn_raw) if withdrawn_raw.strip('-') else '0.00'

        paid_in_raw = cells[7].get_text(strip=True)
        paid_in = re.sub(r'[^0-9.]', '', paid_in_raw) if paid_in_raw.strip('-') else '0.00'

        balance_raw = cells[8].get_text(strip=True)
        balance = balance_raw.replace(',', '') if balance_raw else '0.00'

        data.append({
            'Receipt No.': receipt_no,
            'Completion Time': completion_time,
            'Initiation Time': '',
            'Details': details,
            'Transaction Status': status,
            'Paid In': paid_in,
            'Withdrawn': withdrawn,
            'Balance': balance,
            'Balance Confirmed': '',
            'Reason Type': '',
            'Other Party Info': other_party,
            'Linked Transaction ID': '',
            'A/C No.': '',
            'Currency': currency,
        })

    df = pd.DataFrame(data)
    for col in ('Paid In', 'Withdrawn', 'Balance'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    results = api.post_transactions_df(
        df=df,
        transaction_type=transaction_type,
        company_shortcode=company_shortcode,
        business_shortcode=str(business_shortcode),
    )
    _log_results(results)
    return df, df.columns


def save_table_to_dataframe_latest_(
    page: Page,
    business_shortcode: int,
    pass_value: str,
    additional_category: str,
) -> Tuple[Optional[pd.DataFrame], bool]:
    headers = []
    all_data_rows = []

    if not click_search_button(page=page):
        print('[ERROR] Cannot click search button')

    select_pagination_size(page=page)

    header_tbl = page.wait_for_selector("//table[@class='el-table__header']", timeout=10000)
    soup = BeautifulSoup(header_tbl.inner_html(), 'html.parser')
    tr = soup.find('thead').find('tr')
    headers = [th.get_text(strip=True) for th in tr.find_all('th')]

    scroll_to_bottom(page)
    time.sleep(1)

    try:
        page.wait_for_load_state('networkidle', timeout=10000)
        body_tbl = page.wait_for_selector("//table[@class='el-table__body']", timeout=10000)
        if not body_tbl.is_visible():
            return None, None
    except Exception:
        return None, None

    soup = BeautifulSoup(body_tbl.inner_html(), 'html.parser')
    tbody = soup.find('tbody')

    if tbody:
        for tr in tbody.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all('td')]
            if len(cells) == len(headers):
                all_data_rows.append([business_shortcode] + cells)

    if not all_data_rows:
        df = pd.DataFrame(columns=['OrganizationRowIndex'] + headers)
    else:
        df = pd.DataFrame(all_data_rows, columns=['OrganizationRowIndex'] + headers)

    results = api.post_transactions_df(
        df=df,
        transaction_type=additional_category,
        company_shortcode=company_shortcode,
        business_shortcode=str(business_shortcode),
    )
    success_value = results.get('success', False)
    _log_results(results)
    return df, success_value


def save_table_to_dataframe_download(
    page: Page,
    business_shortcode: int,
    additional_category: str = '',
) -> Tuple[Optional[pd.DataFrame], bool]:
    try:
        close_irritative_dialog_box(page)
        print('[EXPORT] Starting Excel export...')

        export_trigger = page.locator('div.el-dropdown.padding-export >> span').first
        export_trigger.wait_for(state='visible', timeout=30000)
        export_trigger.scroll_into_view_if_needed()
        export_trigger.hover(force=True, timeout=10_000)
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

        all_items = page.locator('ul.el-dropdown-menu li.el-dropdown-menu__item')
        excel_items = all_items.filter(has_text='Excel')
        if excel_items.count() < 3:
            raise Exception(f'Expected 3 Excel options, found {excel_items.count()}')

        target_excel = excel_items.nth(2)

        with page.expect_download(timeout=60_000) as download_info:
            try:
                target_excel.click(force=True, timeout=15_000)
            except Exception:
                target_excel.evaluate('el => el.click()')

        download: Download = download_info.value
        temp_path = download.path()

        results = api.post_transactions_file(
            file_path=temp_path,
            transaction_type=additional_category,
            company_shortcode=company_shortcode,
            business_shortcode=str(business_shortcode),
        )
        success_value = results.get('success', False)
        _log_results(results)

        # Read locally for return value
        df = pd.read_excel(temp_path, skiprows=6)
        return df, success_value

    except Exception as e:
        print(f'[ERROR] save_table_to_dataframe_download: {e}')
        return save_table_to_dataframe_download(page=page, business_shortcode=business_shortcode, additional_category=additional_category)


def _log_results(results: dict):
    if results.get('success'):
        s = results.get('summary', {})
        print(f'[SUCCESS] Updated={s.get("updated_count",0)}, Created={s.get("created_count",0)}, '
              f'Total={s.get("total_processed",0)}, Rate={s.get("success_rate",0):.1f}%')
    else:
        print(f'[FAILED] {results.get("error", "Unknown error")}')


# ── Dropdown / account selection ──────────────────────────────────────────────

def select_account_dropdown(page: Page, account_name: str, arrow_down_count: int) -> bool:
    try:
        dropdown: Locator = (
            page.get_by_role('combobox')
                .nth(2)
                .locator('..')
                .locator('.el-select__caret')
        )
        if dropdown.count() == 0:
            dropdown = page.locator('.el-select').nth(0).locator('i.el-select__caret')

        dropdown.wait_for(state='visible', timeout=15000)
        dropdown.click(force=True)

        for _ in range(arrow_down_count):
            page.keyboard.press('ArrowDown')
            time.sleep(0.2)
        page.keyboard.press('Enter')
        time.sleep(1)
        return True
    except Exception as e:
        print(f'[ERROR] select_account_dropdown({account_name}): {e}')
        page.screenshot(path=f'dropdown_error_{account_name.lower()}.png')
        return False


def select_first_float_option_by_index(page: Page) -> bool:
    try:
        time.sleep(1)
        float_pattern = re.compile(r'Float Account/\d+', re.IGNORECASE)
        options = page.locator("//ul[contains(@class, 'el-select-dropdown__list')]//li")
        for i in range(options.count()):
            try:
                opt = options.nth(i)
                opt_text = opt.inner_text().strip()
                if float_pattern.search(opt_text):
                    opt.click()
                    time.sleep(1)
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        print(f'[ERROR] select_first_float_option_by_index: {e}')
        return False


# ── Date selection ────────────────────────────────────────────────────────────

def first_day_of_quarter() -> str:
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1
    first_month = (quarter - 1) * 3 + 1
    first_day = now.replace(month=first_month, day=1)
    return first_day.strftime('%d/%m/%Y')


def select_dates_and_submit_monthly(page: Page, month_offset: int = 0) -> bool:
    try:
        now = datetime.now()
        if month_offset == 0:
            start_date = now.replace(day=1)
            end_date = now
        else:
            first_of_current = now.replace(day=1)
            end_of_target = first_of_current - timedelta(days=1)
            for _ in range(month_offset - 1):
                end_of_target = end_of_target.replace(day=1) - timedelta(days=1)
            start_date = end_of_target.replace(day=1)
            end_date = end_of_target

        start_str = start_date.strftime('%d/%m/%Y')
        end_str = end_date.strftime('%d/%m/%Y')

        date_inputs = page.locator("input[placeholder*='date' i], input[placeholder*='Date' i]")
        if date_inputs.count() >= 2:
            date_inputs.nth(0).fill(start_str)
            date_inputs.nth(1).fill(end_str)
        else:
            print('[WARN] Could not locate date inputs')
            return False

        time.sleep(0.5)
        return True
    except Exception as e:
        print(f'[ERROR] select_dates_and_submit_monthly: {e}')
        return False


def _get_total_months_by_shortcode_shortfall(
    business_shortcode: str,
    till_scraping_shortfall_local: dict,
    transaction_type: str = None,
) -> tuple:
    key = str(business_shortcode)
    if key not in till_scraping_shortfall_local:
        return 6, None

    value = till_scraping_shortfall_local[key]
    if isinstance(value, dict):
        sub = value.get(transaction_type) if transaction_type else None
        if sub and isinstance(sub, (list, tuple)):
            days = sub[0] if sub[0] else 180
            return max(1, min(int(days) // 30, 6)), sub[1]
        return 6, None

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        days = value[0] if value[0] else 180
        return max(1, min(int(days) // 30, 6)), value[1]

    return 6, None


def scrape_180_days_monthly(
    page: Page,
    business_short_code: int = 0,
    pass_value: str = '',
    additional_category: str = None,
) -> tuple:
    try:
        total_months, latest_receipt = _get_total_months_by_shortcode_shortfall(
            str(business_short_code), till_scraping_shortfall, additional_category
        )
        print(f'[INFO] Scraping {total_months} months for {business_short_code}')

        combined_df = None
        overall_success = False

        for month_offset in range(total_months):
            print(f'[INFO] Processing month_offset={month_offset}')
            if not select_dates_and_submit_monthly(page, month_offset=month_offset):
                continue

            df, success = save_table_to_dataframe_download(
                page=page,
                business_shortcode=business_short_code,
                additional_category=additional_category or '',
            )
            if df is not None:
                combined_df = pd.concat([combined_df, df]) if combined_df is not None else df
            if success:
                overall_success = True

        return combined_df, overall_success

    except Exception as e:
        print(f'[ERROR] scrape_180_days_monthly: {e}')
        traceback.print_exc()
        return None, False


# ── Per-row processing ────────────────────────────────────────────────────────

def process_float_account_details(
    page: Page,
    business_short_code: int,
    mapped_data: Optional[dict],
    pass_value: str,
) -> tuple:
    try:
        if not select_account_dropdown(page, 'Float Account', arrow_down_count=2):
            return 'dropdown', False
        extract_extra_till_info(page, mapped_data)
        if is_till_frozen(page):
            api.alert_non_active(
                recipient_email='martinmaati31@gmail.com',
                business_name=mapped_data.get('company_name', '-'),
                business_short_code=str(business_short_code),
                status='FROZEN',
            )
        time.sleep(1)
        df, success = scrape_180_days_monthly(
            page, business_short_code=business_short_code,
            pass_value=pass_value, additional_category='float',
        )
        return ('dataframe', True) if df is not None or success else ('dataframe', False)
    except Exception as e:
        print(f'[ERROR] process_float_account_details: {e}')
        page.screenshot(path='float_error.png')
        return False, False


def process_commission_account_details(
    page: Page,
    business_short_code: int,
    mapped_data: Optional[dict],
    pass_value: str,
) -> bool:
    try:
        scroll_to_top(page)
        time.sleep(1)
        if not select_account_dropdown(page, 'Commission Account', arrow_down_count=3):
            return False
        extract_extra_till_info(page, mapped_data)
        df, success = scrape_180_days_monthly(
            page, business_short_code=business_short_code,
            pass_value=pass_value, additional_category='commission',
        )
        return df is not None or success
    except Exception as e:
        print(f'[ERROR] process_commission_account_details: {e}')
        page.screenshot(path='commission_error.png')
        return False


def process_float_commission(
    page: Page,
    business_short_code: int,
    mapped_data: Optional[dict],
    pass_value: str,
) -> bool:
    trials = 3
    proc_type, success = process_float_account_details(page, business_short_code, mapped_data, pass_value)
    if proc_type == 'dropdown' and not success:
        for _ in range(trials):
            proc_type, success = process_float_account_details(page, business_short_code, mapped_data, pass_value)
            if success:
                break
    commission_success = process_commission_account_details(page, business_short_code, mapped_data, pass_value)
    return success or commission_success


def _is_agent_company_scraped(business_short_code: int) -> bool:
    try:
        resp = api.get(f'/api/agentcompany/is-scraped/{business_short_code}')
        return resp.get('scraped', False)
    except Exception:
        return False


def _get_priority_shortcodes_(all_shortcodes: Set[str]) -> Set[str]:
    try:
        priority = set()
        for sc in all_shortcodes:
            if not _is_agent_company_scraped(int(sc)):
                priority.add(sc)
        return priority
    except Exception:
        return all_shortcodes


def extract_business_short_code(row: Locator) -> Optional[int]:
    try:
        text = row.text_content(timeout=3000) or ''
        match = re.search(r'^(\d+)', text.strip())
        return int(match.group(1)) if match else None
    except Exception:
        return None


def get_visible_rows(rows_locator: Locator) -> List[Locator]:
    visible = []
    for i in range(rows_locator.count()):
        row = rows_locator.nth(i)
        if row.is_visible():
            visible.append(row)
    return visible


def extract_all_business_short_codes(page: Page, all_shortcodes: Set[str]) -> Set[str]:
    while True:
        wait_for_table_load(page)
        rows = page.locator("//tbody//tr[@class='el-table__row childTableRow']")
        for i in range(rows.count()):
            row = rows.nth(i)
            code = extract_business_short_code(row)
            if code:
                all_shortcodes.add(str(code))
        if not go_forth_on_organization(page, len(all_shortcodes)):
            break
    return all_shortcodes


def process_single_row(
    page: Page,
    business_short_code: int,
    row_number: int,
    pass_value: int = 0,
) -> bool:
    try:
        close_irritative_dialog_box(page)
        mapped_data = scrape_till_details(page, business_short_code)
        success = process_float_commission(page, business_short_code, mapped_data, str(pass_value))
        return_to_organization_list(page)
        return success
    except Exception as e:
        print(f'[ERROR] process_single_row({business_short_code}): {e}')
        traceback.print_exc()
        return_to_organization_list(page)
        return False


def process_single_row_kyc_only(
    page: Page,
    business_short_code: int,
    row_number: int,
) -> bool:
    try:
        close_irritative_dialog_box(page)
        mapped_data = scrape_till_details(page, business_short_code)
        api.post_organization(mapped_data=mapped_data, user_id=user_id)
        extract_user_agent_kyc(str(business_short_code), page)
        return_to_organization_list(page)
        return True
    except Exception as e:
        print(f'[ERROR] process_single_row_kyc_only({business_short_code}): {e}')
        return_to_organization_list(page)
        return False


def extract_user_agent_kyc(short_code: str, page: Page) -> bool:
    try:
        navigate_to_review_transaction(short_code, page)
        return True
    except Exception as e:
        print(f'[ERROR] extract_user_agent_kyc({short_code}): {e}')
        return False


def navigate_to_review_transaction(business_short_code: str, page: Page) -> bool:
    try:
        review_btn = page.wait_for_selector(
            "//button[contains(normalize-space(),'Review Transaction')]",
            timeout=10000,
        )
        review_btn.click()
        page.wait_for_load_state('networkidle', timeout=15000)
        return True
    except Exception as e:
        print(f'[ERROR] navigate_to_review_transaction: {e}')
        return False


def process_page_rows(
    page: Page,
    total_in_list: int,
    total_processed_so_far: int,
    priority_short_codes: Set[str],
    to_be_rerun: List[int],
    pass_value: str,
) -> int:
    processed = 0
    rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")
    visible_rows = get_visible_rows(rows_locator)

    for row in visible_rows:
        code = extract_business_short_code(row)
        if not code:
            continue

        is_priority = str(code) in priority_short_codes
        if pass_value == 'first' and not is_priority:
            print(f'[SKIP] {code} — not in priority list, will process in second pass')
            continue

        try:
            row.click(timeout=15000)
            page.wait_for_timeout(1000)
            success = process_single_row(page, code, row_number=total_processed_so_far + processed + 1, pass_value=0)
            if success:
                processed += 1
            else:
                to_be_rerun.append(code)
        except Exception as e:
            print(f'[ERROR] Row {code}: {e}')
            to_be_rerun.append(code)

        time.sleep(1)

    return processed


def rerun_failed_codes(page: Page, failed_codes: List[int], max_retries: int = 2) -> bool:
    from collections import defaultdict
    retry_count = defaultdict(int)
    remaining = failed_codes.copy()
    for c in remaining:
        retry_count[c] = 0

    while remaining and max(retry_count.values(), default=0) < max_retries:
        go_previous_on_organisation(page)
        total_in_list = get_total_from_pagination(page)

        while True:
            wait_for_table_load(page)
            time.sleep(1)
            rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")
            for i in range(rows_locator.count()):
                row = rows_locator.nth(i)
                if not row.is_visible():
                    continue
                code = extract_business_short_code(row)
                if code not in remaining:
                    continue
                row.click(timeout=15000)
                page.wait_for_timeout(1000)
                success = process_single_row(page, code, row_number=0)
                if success:
                    remaining.remove(code)
                else:
                    retry_count[code] += 1
                    if retry_count[code] >= max_retries:
                        remaining.remove(code)
                time.sleep(1)

            if not remaining or not go_forth_on_organization(page, total_in_list):
                break

    return not remaining


def start_second_pass(
    page: Page,
    total_in_list: int,
    total_processed_so_far: int,
    priority_short_codes: Set[str],
    to_be_rerun: List[int],
    pass_value: str,
):
    while True:
        try:
            process_page_rows(
                page=page,
                total_in_list=total_in_list,
                total_processed_so_far=total_processed_so_far,
                priority_short_codes=priority_short_codes,
                to_be_rerun=to_be_rerun,
                pass_value=pass_value,
            )
        except Exception as e:
            print(f'[ERROR] start_second_pass: {e}')
            break


# ── Main orchestrator ─────────────────────────────────────────────────────────

def process_organization_rows(page: Page) -> None:
    global till_scraping_shortfall

    total_processed = 0
    to_be_rerun: List[int] = []
    close_irritative_dialog_box(page)
    all_shortcodes_: Set[str] = set()
    time.sleep(2)

    all_shortcodes = extract_all_business_short_codes(page, all_shortcodes_)
    print(f'[INFO] Extracted {len(all_shortcodes)} business short codes')

    priority_short_codes = _get_priority_shortcodes_(all_shortcodes)
    print(f'[INFO] {len(priority_short_codes)} priority short codes identified')

    while go_previous_on_organisation(page):
        pass

    while True:
        wait_for_table_load(page)
        total_in_list = get_total_from_pagination(page)
        if total_in_list == 0:
            break

        api.trigger_fraud_detection(user_id)

        processed_on_page = process_page_rows(
            page=page,
            total_in_list=total_in_list,
            total_processed_so_far=total_processed,
            priority_short_codes=priority_short_codes,
            to_be_rerun=to_be_rerun,
            pass_value='first',
        )
        total_processed += processed_on_page

        if not go_forth_on_organization(page, total_in_list):
            api.send_report(user_id=user_id, company_shortcode=company_shortcode)
            while go_previous_on_organisation(page):
                pass
            start_second_pass(
                page=page,
                total_in_list=total_in_list,
                total_processed_so_far=total_processed,
                priority_short_codes=all_shortcodes,
                to_be_rerun=to_be_rerun,
                pass_value='second',
            )
            break

        time.sleep(1)

    if to_be_rerun:
        print(f'[WARN] {len(to_be_rerun)} rows need retry: {to_be_rerun}')
        rerun_failed_codes(page, to_be_rerun)


def navigate_to_child_organization(page: Page) -> None:
    svg_icon = page.wait_for_selector(
        "(//*[name()='svg'][@class='svg-icon'])[2]",
        timeout=60000,
    )
    svg_icon.hover()

    my_org_button = page.wait_for_selector(
        "//span[normalize-space()='My Organization']",
        timeout=60000,
    )
    my_org_button.click()
    page.wait_for_timeout(2000)
    page.mouse.click(10, 10)

    child_org_btn = page.wait_for_selector(
        "//button[normalize-space()='Child Organization']",
        timeout=60000,
    )
    child_org_btn.click()
    process_organization_rows(page)


# ── Job runner ────────────────────────────────────────────────────────────────

def run_scrape_job(job: dict) -> None:
    global company_shortcode, user_id, till_scraping_shortfall, context, browser

    job_id      = job['job_id']
    short_code  = job['short_code']
    username    = job['username']
    password    = job['password']
    user_id     = job['user_id']
    company_shortcode = short_code

    print(f'[JOB] Starting job {job_id} for short_code={short_code}')

    till_scraping_shortfall = api.get_last_scraped()
    print(f'[INFO] Last-scraped data loaded: {len(till_scraping_shortfall)} entries')

    login_url = (
        'https://org.ke.m-pesa.com/#/login'
        '?transaction_service=https%3A%2F%2Forg.ke.m-pesa.com%2Forgportal%2Fv1%2Fsso%2Fhome'
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        page.goto(login_url, timeout=600000)
        time.sleep(3)

        captcha_solution = capture_and_solve_captcha(page)
        fill_login_form(page, short_code, username, password)

        while len(captcha_solution) > 4:
            captcha_solution = retry_captcha_login(page)
            fill_login_form(page, short_code, username, password)

        if has_verification_error_regex(page):
            captcha_solution = retry_captcha_login(page)

        page.fill("//input[@id='verifyCode']", captcha_solution)
        page.click("//button[@id='loginBtn']")

        search = page.wait_for_selector(
            "(//i[@class='el-icon el-sub-menu__icon-arrow'])[1]",
            timeout=60000,
        )
        search.click()
        print('[SUCCESS] Logged in successfully!')

        navigate_to_child_organization(page)

        context.close()
        browser.close()


# ── Polling loop ──────────────────────────────────────────────────────────────

def main():
    global api

    if not AGENT_SECRET:
        print('[ERROR] AGENT_SECRET is not set. Edit the CONFIG block or set the AGENT_SECRET env var.')
        sys.exit(1)

    api = BackendClient(BACKEND_URL, AGENT_SECRET)
    print(f'[INFO] Kwamz AI Mpesa Agent started — polling {BACKEND_URL} every {POLL_INTERVAL}s')

    while True:
        try:
            job = api.poll_job()
            if job:
                job_id = job['job_id']
                try:
                    run_scrape_job(job)
                    api.complete_job(job_id)
                    print(f'[JOB] {job_id} completed.')
                except Exception as e:
                    error_msg = traceback.format_exc()
                    print(f'[JOB] {job_id} failed:\n{error_msg}')
                    api.fail_job(job_id, str(e))
            else:
                print(f'[IDLE] No pending jobs. Sleeping {POLL_INTERVAL}s...')
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print('\n[INFO] Agent stopped by user.')
            sys.exit(0)
        except Exception as e:
            print(f'[ERROR] Polling error: {e}')
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
