from playwright.sync_api import sync_playwright,Page,Locator,Download, TimeoutError as PlaywrightTimeoutError
from flask import current_app
from app.utils.script import fill_login_form, capture_and_solve_captcha
from app.utils.email_utils import generate_scraping_report_email, send_scraping_report_email,send_session_timeout_email,send_not_active_short_code_
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
import traceback
import numpy as np


transaction_service = TransactionService()
agent_company_service = AgentCompanyService()
email_outbox_service = EmailOutboxService()
company_shortcode = None
user_id = None
user = None
till_scraping_shortfall = {}
context = None
browser = None
MAX_SEND_ATTEMPTS=3

# Load environment variables
load_dotenv()

def login_to_mpesa(password: str = None, username: str = None, short_code: str = None, user_id_passed: str = None) -> None:
    global company_shortcode, user_id, user,till_scraping_shortfall,context,browser
    password = password 
    # or os.getenv("AGENT_COMPANY_PASSWORD")
    username = username 
    # or os.getenv("AGENT_COMPANY_USERNAME")
    user_id = user_id_passed
    user = User.query.filter_by(id=user_id)
    
    short_code = short_code 
    # or os.getenv("AGENT_COMPANY_SHORTCODE")
    company_shortcode = short_code

    till_scraping_shortfall = transaction_service.get_last_scraped_per_shortcode()
    url = "https://org.ke.m-pesa.com/#/login?transaction_service=https%3A%2F%2Forg.ke.m-pesa.com%2Forgportal%2Fv1%2Fsso%2Fhome"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']  # Use --start-maximized instead
        )
        
        # Create context with no default viewport to use full screen
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        page.goto(url, timeout=600000)
        time.sleep(3)
        wait_after_click = 5  # seconds
        
        # Solve captcha initially — ensure solution looks valid (<= 4 chars)
        captcha_solution = capture_and_solve_captcha(page)
        fill_login_form(page, short_code, username, password)
        print("[INFO] Login form filled")
        print(f"[DEBUG] Initial captcha solution: {captcha_solution}")

        while not _is_valid_captcha(captcha_solution):
            captcha_solution = retry_captcha_login(page)
            fill_login_form(page, short_code, username, password)
            print(f"[DEBUG] Retried captcha solution (validity fix): {captcha_solution}")

        # Submit loop: retry captcha if the server says it's wrong
        MAX_CAPTCHA_RETRIES = 5
        logged_in = False

        for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
            # Guard: ensure exactly 4 digits before every login click
            while not _is_valid_captcha(captcha_solution):
                print(f"[DEBUG] Invalid captcha '{captcha_solution}' on attempt {attempt}, re-solving...")
                captcha_solution = retry_captcha_login(page)

            print(f"[INFO] Login attempt {attempt}/{MAX_CAPTCHA_RETRIES} with captcha: {captcha_solution}")

            page.fill("//input[@id='verifyCode']", captcha_solution)
            page.click("//button[@id='loginBtn']")
            print("[INFO] Login button clicked; waiting for response...")

            # Brief pause to let error message appear before checking
            time.sleep(3)

            if has_verification_error_regex(page):
                print(f"[WARN] Captcha wrong on attempt {attempt}, re-solving...")
                captcha_solution = retry_captcha_login(page)
                while not _is_valid_captcha(captcha_solution):
                    captcha_solution = retry_captcha_login(page)
                    print(f"[DEBUG] Captcha re-solve (validity fix): {captcha_solution}")
                continue

            # No error shown — wait for the post-login dashboard element
            try:
                search = page.wait_for_selector(
                    "(//i[@class='el-icon el-sub-menu__icon-arrow'])[1]",
                    timeout=60000
                )
                search.click()
                print("[SUCCESS] Logged in successfully!")
                logged_in = True
                break
            except PlaywrightTimeoutError:
                # Dashboard didn't appear — check if error crept in after the sleep
                if has_verification_error_regex(page):
                    print(f"[WARN] Captcha error detected after waiting (attempt {attempt}), retrying...")
                    captcha_solution = retry_captcha_login(page)
                    while not _is_valid_captcha(captcha_solution):
                        captcha_solution = retry_captcha_login(page)
                else:
                    raise

        if not logged_in:
            raise Exception(f"[ERROR] Failed to log in after {MAX_CAPTCHA_RETRIES} captcha attempts.")

        print("[INFO] Navigating to child organization page...")
        navigate_to_child_organization(page)

        print("[INFO] Browser will remain open for inspection. Press ENTER to close.")
        # input()



def _is_valid_captcha(solution: str) -> bool:
    """Return True only when the captcha solution is exactly 4 numeric digits."""
    return bool(re.match(r'^\d{4}$', solution.strip()))

def has_verification_error_regex(page) -> bool:
    """Checks if the page contains a verification code error using regex."""
    body_text = page.locator("body").inner_text()
    pattern = re.compile(r"verification\s+code\s+is\s+incorrect\s+or\s+has\s+expired", re.IGNORECASE)
    return bool(pattern.search(body_text))

def retry_captcha_login(page:Page) -> str:
    """
    Retries the captcha login process until successful or max attempts reached.
    
    Args:
        page: Playwright Page object
    """
    # Predict the captcha that is currently displayed before refreshing
    captcha_solution = capture_and_solve_captcha(page)
    print(f"[DEBUG] Captcha predicted (pre-refresh): {captcha_solution}")

    if _is_valid_captcha(captcha_solution):
        return captcha_solution

    # Prediction invalid — refresh the captcha image, then solve the new one
    svg_element = page.query_selector("//div[@class='img-part']//*[name()='svg']")
    if svg_element:
        svg_element.click()
        print("[INFO] Clicked SVG element to refresh captcha")
        time.sleep(1)  # wait for new image to render
        captcha_solution = capture_and_solve_captcha(page)
        print(f"[DEBUG] Captcha predicted (post-refresh): {captcha_solution}")
    else:
        print("[ERROR] SVG element not found")
        raise Exception("Failed to locate SVG element for captcha refresh")

    return captcha_solution
    
def maximize_page(page: Page) -> None:
    """
    Maximizes the page by setting the viewport to a large size (e.g., 1920x1080).
    
    Args:
        page: Playwright Page object
    """
    try:
        # Set viewport to a large size (can adjust based on your needs)
        page.set_viewport_size({"width": 1920, "height": 1080})
        print("[SUCCESS] Page maximized to 1920x1080")
    except Exception as e:
        print(f"[ERROR] Failed to maximize page: {e}")
        
def _navigate_to_child_org_list(page) -> None:
    """Navigate to the Child Organisation list without starting row processing."""
    close_portal_tabs(page)
    print("[INFO] Hovering on the index icon...")
    svg_icon = page.wait_for_selector(
        "(//*[name()='svg'][@class='svg-icon'])[2]",
        timeout=60000
    )
    svg_icon.hover()
    print("[INFO] Hover successful, waiting for 'My Organization'...")

    my_org_button = page.wait_for_selector(
        "//span[normalize-space()='My Organization']",
        timeout=60000
    )
    my_org_button.click()
    print("[INFO] 'My Organization' clicked.")
    page.wait_for_timeout(2000)
    page.mouse.click(10, 10)

    child_org_btn = page.wait_for_selector(
        "//button[normalize-space()='Child Organization']",
        timeout=60000
    )
    child_org_btn.click()
    print("[INFO] 'Child Organization' clicked. Waiting for page to load...")
    page.wait_for_timeout(2000)

def navigate_to_child_organization(page):
    """
    Navigates after login: hover on the index icon, click 'My Organization',
    then click 'Child Organization' and start processing rows.
    """
    _navigate_to_child_org_list(page)
    process_organization_rows(page)

def select_first_float_option_by_index(page) -> bool:
    """Selects the first 'Float Account/XXXXX' option from dropdown."""
    try:
        print("[INFO] Looking for Float Account option...")
        page.wait_for_timeout(1000)
        
        float_pattern = re.compile(r'Float Account/\d+', re.IGNORECASE)
        
        # Use locator instead of query_selector_all for better reliability
        options = page.locator("//ul[contains(@class, 'el-select-dropdown__list')]//li")
        option_count = options.count()
        
        print(f"[DEBUG] Found {option_count} dropdown options")
        
        for i in range(option_count):
            try:
                opt = options.nth(i)
                opt_text = opt.inner_text().strip()
                
                if float_pattern.search(opt_text):
                    print(f"[INFO] Found Float Account: {opt_text}")
                    opt.click()
                    page.wait_for_timeout(1000)
                    return True
                    
            except Exception as e:
                print(f"[WARN] Error reading option {i + 1}: {e}")
                continue
        
        print("[ERROR] No Float Account option found")
        return False
        
    except Exception as exc:
        print(f"[ERROR] Float option selection failed: {exc}")
        return False

def scroll_to_top(page: Page) -> None:
    """
    Scrolls to the top of the page.
    
    Args:
        page: Playwright Page object
    """
    try:
        page.evaluate("window.scrollTo(0, 0);")
        print("[SUCCESS] Scrolled to top of page")
        time.sleep(0.5)  
    except Exception as e:
        print(f"[ERROR] Failed to scroll to top: {e}")

def scroll_to_bottom(page: Page) -> None:
    """
    Scrolls to the bottom of the page.
    
    Args:
        page: Playwright Page object
    """
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        print("[SUCCESS] Scrolled to bottom of page")
        time.sleep(1.5)  
    except Exception as e:
        print(f"[ERROR] Failed to scroll to bottom: {e}")

def extract_extra_till_info(page: Page, extra_info: dict) -> Dict[str, Any]:
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
                print(f"[WARNING] Error processing card: {card_error}")
                continue
        
        # Now merge with the existing extra_info
        if extracted_data:
            print(f"[INFO] Extracted {len(extracted_data)} account details:")
            
            for key, value in extracted_data.items():
                if(key == "status" and value !="Active"):
                    send_alert_on_non_active_("martinmaati31@gmail.com",
                                              business_name=extra_info.get('company_name'),
                                              business_short_code=extra_info.get("short_code"),
                                              status=value)
                    
                print(f"  {key}: {value}")
            
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
            
        save_results = agent_company_service.save_or_update_scraped_agent_company(mapped_data=extra_info,user_id=user_id)
        
        print(f"[DEBUG] Saved results: {save_results}")
        return save_results
        
    except Exception as e:
        print(f"[ERROR] Failed to extract extra till info: {e}")
        # Return the original extra_info dict without modifications
        return extra_info

def send_alert_on_non_active_(
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
        if email_outbox and (email_outbox.sent_times or 0) >= MAX_SEND_ATTEMPTS:
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
                sender=user.email,
                receiver=recipient_email,
                reason="NON_ACTIVE_AGENT",
                business_short_code=business_short_code,
                sent_times=1
            )

    except Exception as e:
        print(f"[ERROR] An error occurred: {str(e)}")
     
       
def save_table_to_dataframe_(page: Page, business_shortcode: int,category:str) -> tuple:
    """Extract all rows from paginated table and save to CSV."""
    try:
        print("[INFO] Starting table extraction...")

        # get the latest receipt number for this shortcode
        latest_receipt_number = till_scraping_shortfall[business_shortcode][1]
        print(f"The latest receipt number for {business_shortcode} is {latest_receipt_number}")
        
        try:                
            page.wait_for_load_state("networkidle", timeout=10000)
            body_tbl = page.wait_for_selector(
                "//table[@class='el-table__body']",
                timeout=10000
            )
        
            if not body_tbl.is_visible():
                return None, None
        except Exception as e:
            print("[WARN] Table body not visible, ending extraction.")
            return None, None        
        soup = BeautifulSoup(body_tbl.inner_html(), "html.parser")
        tbody = soup.find("tbody")
        
        trs = tbody.find("tr") if tbody else None
        # first_tr = trs[0] if trs and len(trs) > 0 else None
        
        span = soup.find("span", class_="receipt-link")
        if span:
            transaction_id = span.get_text(strip=True)
            print("Found transaction ID:", transaction_id)
            click_receipt_link(page,transaction_id)
            time.sleep(15)
        else:
            print("Not found")
        
    except Exception as exc:
        print(f"[ERROR] Table extraction failed: {exc}")
        traceback.print_exc()
        return None, None

def get_latest_receipt_no(page: Page, business_shortcode: int, pass_value: str) -> str:
    """Extract all rows from paginated table and process receipt links from match point to latest."""
    print("[INFO] Starting table extraction...")

    # Add thread safety if needed (uncomment if multi-threaded)
    # with till_scraping_lock:
    
    # Check dictionary existence and structure
    if not isinstance(till_scraping_shortfall, dict):
        print(f"[ERROR] till_scraping_shortfall is not a dictionary")
        return None
        
    print(f"The till scraping shortfall has {len(till_scraping_shortfall)} entries")
    
    # Check if key exists
    if business_shortcode not in till_scraping_shortfall:
        # Try converting to string if business_shortcode is int but keys are strings
        if str(business_shortcode) in till_scraping_shortfall:
            business_shortcode = str(business_shortcode)
        else:
            print(f"[ERROR] Business shortcode {business_shortcode} not found")
            print(f"Available keys (first 10): {list(till_scraping_shortfall.keys())[:10]}")
            return None
    
    # Check value structure
    value = till_scraping_shortfall[business_shortcode]
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        print(f"[ERROR] Invalid structure for {business_shortcode}: {value}")
        return None
        
    latest_receipt_number = str(value[1])
    print(f"The latest receipt number for {business_shortcode} is {latest_receipt_number}")
    return latest_receipt_number

def save_table_to_dataframe_latest_(page: Page, business_shortcode: int, pass_value: str, additional_category: str) -> tuple:
    """Extract all rows from paginated table and process receipt links from match point to latest."""
    # try:
    print("[INFO] Starting table extraction...")
    headers = []
    all_data_rows = []
    
    success = click_search_button(page=page)        
    
    if not success:
        print(f"[ERROR] Can not select the search button")
    
    select_pagination_size(page=page)
    # Get the latest receipt number for this shortcode
    # print(f"The till scraping shortfall {till_scraping_shortfall}")
        
        # Extract headers
    header_tbl = page.wait_for_selector(
        "//table[@class='el-table__header']",
        timeout=10000
    )
    
    soup = BeautifulSoup(header_tbl.inner_html(), "html.parser")
    tr = soup.find("thead").find("tr")
    headers = [th.get_text(strip=True) for th in tr.find_all("th")]
    print(f"[SUCCESS] Headers: {headers}")
    
    #
    scroll_to_bottom(page)
    
    # Paginate through all data
    page_no = 1
    time.sleep(1)  
    print(f"\n[INFO] Extracting page {page_no}...")
    
    try:                
        page.wait_for_load_state("networkidle", timeout=10000)
        body_tbl = page.wait_for_selector(
            "//table[@class='el-table__body']",
            timeout=10000
        )
    
        if not body_tbl.is_visible():
            return None, None
    except Exception as e:
        print("[WARN] Table body not visible, ending extraction.")
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
        print("[WARN] No data rows extracted")
        df = pd.DataFrame(columns=["OrganizationRowIndex"] + headers)
    else:
        df = pd.DataFrame(all_data_rows, columns=["OrganizationRowIndex"] + headers)
        print(f"[SUCCESS] Extracted {len(df)} total rows")
        print(df.tail())
    
        # Update transactions
    results = transaction_service.update_transactions_from_dataframe(
        df=df,
        transaction_type=additional_category,
        company_shortcode=company_shortcode,
        agent_id=None,
        business_shortcode=business_shortcode
    )
    success_value = results.get('success', False)
    if success_value:
        summary = results.get('summary', {})
        print(f"\n Success!")
        print(f"   Updated: {summary.get('updated_count', 0)}")
        print(f"   Created: {summary.get('created_count', 0)}")
        print(f"   Total: {summary.get('total_processed', 0)}")
        print(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
    else:
        print(f"\n Failed: {results.get('error', 'Unknown error')}")
        
    return df, success_value
    
def parse_element_plus_transactions(html_content: str, transaction_type: str, business_shortcode: str) -> tuple:
    """
    Parse an Element Plus (el-table) transaction table HTML into a pandas DataFrame.
    
    Args:
        html_content (str): The HTML string containing <tbody> with transaction rows
        
    Returns:
        pd.DataFrame: DataFrame with the requested columns
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find all data rows
    rows = soup.select("tbody tr.el-table__row")
    
    data = []
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 10:  # We expect at least 10 columns
            continue
            
        # Extract values safely
        # Column 1: Receipt No.
        receipt_cell = cells[0].find("span", class_="receipt-link")
        receipt_no = receipt_cell.get_text(strip=True) if receipt_cell else ""
        
        # Column 2: Completion Time
        completion_time = cells[1].get_text(strip=True)
        
        # Column 3: Details
        details = cells[2].get_text(strip=True)
        
        # Column 4: Other Party Info
        other_party = cells[3].get_text(strip=True)
        
        # Column 5: Transaction Status
        status = cells[4].get_text(strip=True)
        
        # Column 6: Currency
        currency = cells[5].get_text(strip=True)
        
        # Column 7: Withdrawn (negative amount → positive value)
        withdrawn_raw = cells[6].get_text(strip=True)
        withdrawn = re.sub(r'[^0-9.]', '', withdrawn_raw) if withdrawn_raw.strip("-") else "0.00"
        
        # Column 8: Paid In (positive amount)
        paid_in_raw = cells[7].get_text(strip=True)
        paid_in = re.sub(r'[^0-9.]', '', paid_in_raw) if paid_in_raw.strip("-") else "0.00"
        
        # Column 9: Balance
        balance_raw = cells[8].get_text(strip=True)
        balance = balance_raw.replace(",", "") if balance_raw else "0.00"
        
        # Columns not present in this table view
        initiation_time = ""      # Not shown in your HTML
        balance_confirmed = ""    # Not shown
        reason_type = ""          # Not shown
        linked_txn_id = ""        # Not shown
        account_no = ""           # Not shown
        
        data.append({
            "Receipt No.": receipt_no,
            "Completion Time": completion_time,
            "Initiation Time": initiation_time,
            "Details": details,
            "Transaction Status": status,
            "Paid In": paid_in,
            "Withdrawn": withdrawn,
            "Balance": balance,
            "Balance Confirmed": balance_confirmed,
            "Reason Type": reason_type,
            "Other Party Info": other_party,
            "Linked Transaction ID": linked_txn_id,
            "A/C No.": account_no,
            "Currency": currency
        })
    
    df = pd.DataFrame(data)
    
    # Optional: Convert numeric columns to proper types
    numeric_cols = ["Paid In", "Withdrawn", "Balance"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    # Update transactions
    results = transaction_service.update_transactions_from_dataframe(
        df=df,
        transaction_type=transaction_type,
        company_shortcode=company_shortcode,
        agent_id=None,
        business_shortcode=business_shortcode
    )
    success_value = results.get('success', False)
    if success_value:
        summary = results.get('summary', {})
        print(f"\n Success!")
        print(f"   Updated: {summary.get('updated_count', 0)}")
        print(f"   Created: {summary.get('created_count', 0)}")
        print(f"   Total: {summary.get('total_processed', 0)}")
        print(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
    else:
        print(f"\n Failed: {results.get('error', 'Unknown error')}")
    
    return df,df.columns

def save_table_to_dataframe_download(page: Page,business_shortcode:int,additional_category:str="") -> tuple:
    try:
        close_irritative_dialog_box(page)
        print("[EXPORT] Starting Excel export...")

        export_trigger = page.locator("div.el-dropdown.padding-export >> span").first
        export_trigger.wait_for(state="visible", timeout=30000)
        export_trigger.scroll_into_view_if_needed()

        export_trigger.hover(force=True, timeout=10_000)
        print("[EXPORT] Hovered successfully")
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
        print("[EXPORT] Export dropdown menu is visually open")

        # 3. Get ALL menu items from ALL dropdown menus
        all_items = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")

        # Find all items that contain "Excel" (case-sensitive match as in your UI)
        excel_items = all_items.filter(has_text="Excel")

        excel_count = excel_items.count()
        print(f"[EXPORT] Found {excel_count} visible 'Excel' options across all dropdowns")

        if excel_count < 3:
            raise Exception(f"Expected at least 3 Excel export options, found only {excel_count}")

        target_excel = excel_items.nth(2)

        print(f"[EXPORT] Targeting the 3rd 'Excel' option (index 2 in filtered list)")

        # 4. Click + download
        with page.expect_download(timeout=60_000) as download_info:
            # First try normal click
            try:
                target_excel.click(force=True, timeout=15_000)
                print("[EXPORT] Clicked 'Excel' (All Data) successfully")
            except Exception as e:
                print("[EXPORT] Normal click failed, falling back to JS click...")
                target_excel.evaluate("el => el.click()")

        download: Download = download_info.value

        # THIS IS THE MAGIC: Read bytes directly into pandas
        print(f"[EXPORT] Reading {download.suggested_filename} directly into pandas...")
        temp_path = download.path()  # Playwright saves it temporarily
        
        df,success_value = update_transactions_from_file(
            file_path=temp_path,
            business_shortcode=business_shortcode,
            transaction_type=additional_category,
            company_shortcode=company_shortcode,
            agent_id=None
        )

        print(f"[SUCCESS] Loaded DataFrame in-memory: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"   Columns: {list(df.columns)}")

        return df, success_value
    except Exception as e:
        print(f"[ERROR] An error has occurred {e}")
        save_table_to_dataframe_download(page=page,business_shortcode=business_shortcode,additional_category=additional_category)

def save_table_to_dataframe_download_head_office(
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
        close_irritative_dialog_box(page)
        print(f"[EXPORT] Starting Head Office export (filter='{filter_text}')...")

        visible_dropdown = page.locator("div.el-dropdown.padding-export:visible")
        try:
            visible_dropdown.wait_for(state="visible", timeout=10000)
        except Exception:
            print("[EXPORT] No visible export dropdown — no data for this period")
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
        print("[EXPORT] Hovered via mouse coordinates")
        time.sleep(3)

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
        print("[EXPORT] Export dropdown menu is visually open")

        all_items = page.locator("ul.el-dropdown-menu li.el-dropdown-menu__item")
        matched_items = all_items.filter(has_text=filter_text)          # ← dynamic
        matched_count = matched_items.count()
        print(f"[EXPORT] Found {matched_count} visible '{filter_text}' options across all dropdowns")

        if matched_count < min_item_count:
            raise Exception(
                f"Expected at least {min_item_count} '{filter_text}' export options, "
                f"found only {matched_count}"
            )

        target_item = matched_items.nth(target_index)
        print(f"[EXPORT] Targeting '{filter_text}' option at index {target_index}")

        # Resolve the item's viewport coordinates so we can click via raw mouse
        # movement — moving the mouse to an element coordinate keeps the El-UI
        # dropdown open, whereas Playwright's element .click() internally dispatches
        # focus/blur events that close the portal before the click lands.
        item_coords = target_item.evaluate("""el => {
            const r = el.getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        }""")
        print(f"[EXPORT] Item coords resolved: {item_coords}")

        with page.expect_download(timeout=60_000) as download_info:
            if item_coords and item_coords.get('x') and item_coords.get('y'):
                # Slide mouse from trigger into menu item, then click — no element
                # click events that would collapse the dropdown
                page.mouse.move(item_coords['x'], item_coords['y'])
                time.sleep(0.3)
                page.mouse.click(item_coords['x'], item_coords['y'])
                print(f"[EXPORT] Clicked '{filter_text}' via mouse coordinates")
            else:
                # Coords unavailable — try JS click as a last resort
                print("[EXPORT] Could not resolve item coords, falling back to JS click...")
                target_item.evaluate("el => el.click()")

        download: Download = download_info.value
        print(f"[EXPORT] Reading {download.suggested_filename} directly into pandas...")
        temp_path = download.path()

        # Save a debug copy so we can inspect the raw file if parsing fails
        try:
            import shutil, datetime as _dt
            debug_dir = os.path.join(os.path.dirname(__file__), "..", "..", "debug_exports")
            os.makedirs(debug_dir, exist_ok=True)
            ext = os.path.splitext(download.suggested_filename)[1] or ".xlsx"
            ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = os.path.join(debug_dir, f"head_office_{business_shortcode}_{ts}{ext}")
            shutil.copy2(temp_path, debug_path)
            print(f"[DEBUG] Raw export saved to: {debug_path}")
        except Exception as _e:
            print(f"[DEBUG] Could not save debug copy: {_e}")

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
                print(f"[EXPORT] M-PESA returned an error payload (code={_code}): {_desc}")
                return pd.DataFrame(), False
        except Exception:
            pass  # not JSON — proceed normally

        # If the download is a CSV it's the Head Office Balance Overview (Level 1/2
        # hierarchy), not a transaction export. Parse and upsert commission balances.
        if (download.suggested_filename or '').lower().endswith('.csv'):
            print("[EXPORT] CSV detected — parsing as Head Office commission balance overview")
            result = transaction_service.save_head_office_commission_balances(
                csv_path=temp_path,
                parent_shortcode=business_shortcode,
            )
            if result.get('success'):
                s = result['summary']
                print(f"[EXPORT] Commission balances saved: created={s['created']} updated={s['updated']} skipped={s['skipped']}")
            else:
                print(f"[EXPORT] Commission balance save failed: {result.get('error')}")
            return pd.DataFrame(), result.get('success', False)

        df, success_value = update_transactions_from_file(
            file_path=temp_path,
            business_shortcode=business_shortcode,
            transaction_type=additional_category,
            company_shortcode=company_shortcode,
            agent_id=None
        )

        print(f"[SUCCESS] Head Office export loaded: {df.shape[0]} rows × {df.shape[1]} columns")
        return df, success_value

    except Exception as e:
        print(f"[ERROR] Head Office export failed: {e}")
        return None, False
def process_detailed_receipt(page: Page, receipt_no: str, transaction_type: str = 'float'):
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
        
        print(f"[DETAIL] {result['message']}")
        return result["success"]
        
    except Exception as e:
        print(f"[ERROR] Failed to process detailed receipt {receipt_no}: {str(e)}")
        return False    

def update_transactions_from_file(file_path, business_shortcode, transaction_type, company_shortcode, agent_id):
    """
    Update transactions directly from a file
    """
    
    success_value : bool = False
    
    print(f"Processing file: {file_path}")
    print(f"Business: {business_shortcode}")
    print(f"Type: {transaction_type}")
    
    # Read the file
    df = pd.read_excel(file_path, skiprows=6)
    
    print(f"Data shape: {df.shape}")
    print(f"Sample data:")
    print(df.tail())
    
    # Update transactions
    results = transaction_service.update_transactions_from_dataframe(
        df=df,
        transaction_type=transaction_type,
        company_shortcode=company_shortcode,
        agent_id=agent_id,
        business_shortcode=business_shortcode
    )
    success_value = results.get('success', False)
    if success_value:
        summary = results.get('summary', {})
        print(f"\n Success!")
        print(f"   Updated: {summary.get('updated_count', 0)}")
        print(f"   Created: {summary.get('created_count', 0)}")
        print(f"   Total: {summary.get('total_processed', 0)}")
        print(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
    else:
        print(f"\n Failed: {results.get('error', 'Unknown error')}")
    
    # Save the processed file
    print(f"💾 Saved to: {business_shortcode}_{transaction_type}.xlsx")
    
    return df, success_value


def is_till_frozen(page:Page)-> bool:
    
    try:
        div_frozen = page.wait_for_selector("//div[normalize-space()='Frozen']",timeout=1000)
        return div_frozen.is_visible()
    except Exception as e:
        print(f"The till is not frozen {str(e)}")
        return False

def clean_label_for_db(label: str) -> str:
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

def parse_date_string(date_str: str) -> datetime.date:
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

def map_scraped_data_to_agent_company(scraped_data: dict) -> dict:
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
        'user_id': user_id
    }
    
    # Handle registration date
    reg_date = get_value('registration_date') or scraped_data.get('Registration Date')
    if reg_date:
        parsed_date = parse_date_string(reg_date)
        if parsed_date:
            mapped_data['registration_date'] = parsed_date
            mapped_data['established_date'] = parsed_date
    
    # Handle parent short code
    parent_short_code = get_value('parent_short_code') or scraped_data.get('Parent Short Code')
    if parent_short_code:
        mapped_data['parent_short_code'] = parent_short_code
    
    return mapped_data

def scrape_till_details(page: Page, business_short_code: int) -> dict:
    """
    Scrape till details and return processed data
    """
    try:
        close_irritative_dialog_box(page)
        css_selector = ".portal-collapse .portal-collapse-content"
        
        # Wait for the selector to be available
        page.wait_for_selector(css_selector, state="attached", timeout=30000)
        
        # Get inner HTML
        inner_html = page.eval_on_selector(
            css_selector,
            "el => el.innerHTML"
        )
        
        # Extract till info
        till_info = extract_till_info(inner_html)
        
        print(f"[INFO] Scraped till info for business short code {business_short_code}:")
        till_info['business_short_code'] = business_short_code
        for key, value in till_info.items():
            print(f"  {key}: {value}")
        
        # Map to AgentCompany fields
        mapped_data = map_scraped_data_to_agent_company(till_info)
                        
        print(f"[INFO] Map result for business short code {business_short_code}: {mapped_data}")

        return mapped_data
        
    except Exception as e:
        print(f"[ERROR] Could not scrape till details: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'business_short_code': business_short_code
        }   


def click_receipt_link(page:Page,transaction_id: str) -> bool:
    try:
        print(f"Clicking receipt link for transaction ID: {transaction_id}")
        selector = f'span.receipt-link:has-text("{transaction_id}")'
        page.wait_for_selector(selector, state="visible",timeout=5000)
        page.click(selector)
        return extract_extra_details_on_receipt(page=page,receipt_no=transaction_id)
    except Exception as e:
        print(f"Error clicking receipt link: {e}")
        return False


def extract_extra_details_on_receipt(page:Page,receipt_no:str) -> bool:
    try:
        print(f"[INFO] Trying to extract more details")
        transactions_div = page.wait_for_selector(selector="//div[@class='portal-collapse background-box section-box section-box-buttom bottom-radius']",
                                                  state="visible",
                                                  timeout=10000)
        
        transactions_div_html = transactions_div.inner_html()
        
        soup = BeautifulSoup(transactions_div_html,"html.parser")
        
        return True
    except Exception as e:
        print(f"[ERROR] An error has occurred {str(e)}")                
        return False


def extract_till_info(inner_html: str) -> dict:
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
    
def save_table_to_dataframe_download_debug(page: Page, max_wait: int = 30_000):
    print("[EXPORT] Starting Excel export...")

    export_trigger = page.locator("div.el-dropdown.padding-export >> span").first
    export_trigger.wait_for(state="visible", timeout=max_wait)
    export_trigger.scroll_into_view_if_needed()

    export_trigger.hover(force=True, timeout=10_000)
    print("[EXPORT] Hovered successfully")

    # Give Vue time to open the dropdown
    time.sleep(2)  # or use wait_for_function as before

    print("\n" + "="*60)
    print("DROPDOWN MENU DEBUG INFO")
    print("="*60)

    # Method 1: Try get_by_role (what you were using)
    excel_by_role = page.get_by_role("menuitem", name="Excel", exact=True)
    print(f"get_by_role('menuitem', name='Excel') → Found: {excel_by_role.count()} items")

    # Method 2: Raw locator for all menu items
    all_menu_items = page.locator("ul.el-dropdown-menu >> li.el-dropdown-menu__item")
    count = all_menu_items.count()
    print(f"Total <li class='el-dropdown-menu__item'> found: {count}")

    # Print EVERY item with index + text + visibility
    for i in range(count):
        item = all_menu_items.nth(i)
        text = item.inner_text(timeout=5000).strip()
        is_visible = item.is_visible()
        is_enabled = item.is_enabled()
        
        print(f"  [{i:2d}] '{text}' → visible={is_visible}, enabled={is_enabled}")

        # Highlight Excel ones
        if "excel" in text.lower():
            print(f"     →→→ THIS IS AN EXCEL OPTION (index {i})")

    # Bonus: Show which one has the actual download behavior (usually the 3rd)
    excel_candidates = [i for i in range(count) if "excel" in all_menu_items.nth(i).inner_text().lower()]
    print(f"\nExcel option indices: {excel_candidates}")
    print(f"Recommended to click index: {excel_candidates[2] if len(excel_candidates) > 2 else 'Not enough!'}")

    print("="*60 + "\n")

    # Stop here for debugging
    print("Stopping for inspection. Comment out exit() when ready.")
    
def first_day_of_quarter() -> str:
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

def click_random_spot(page, padding: int = 50) -> None:
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
    print(f"[Success] Clicked random spot at ({rand_x}, {rand_y})")

def get_total_from_pagination(page) -> int | None:
    locator = page.locator("//div[@id='pagination']/span[contains(text(), 'Total')]").first
    
    try:
        if locator.count() == 0:
            print("[WARN] Total span not found in pagination")
            return None
            
        text = locator.inner_text().strip()          # e.g. "Total 103"
        number = int(''.join(filter(str.isdigit, text)))
        print(f"[INFO] Detected total records: {number}")
        return number
    except Exception as e:
        print(f"[ERROR] Could not parse total: {e}")
        return None
    
def go_forth_on_organization(page: Page, row_count: int):
    """
    Clicks 'Next Page' if available. Returns True/False indicating if more pages exist.
    """
    next_page_btn = page.locator("//button[@aria-label='Go to next page']").first

    try:
        if next_page_btn.is_enabled():
            print("[INFO] Clicking 'Next Page' button...")
            next_page_btn.click()
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(0.5)
            return  True  # Continue processing
        else:
            print(f"[INFO] Next page disabled. Finished all {row_count} rows on last page.")
            return  False

    except Exception as e:
        print(f"[WARNING] Error clicking next page: {e}")
        user = User.query.filter_by(id=user_id).first()

        if user:
            # send_session_timeout_email(user.email, user.first_name)
            send_session_timeout_email(user.email)
            context.close()
            browser.close()
        page.screenshot(path="pagination_error.png")
        return False
        
def go_previous_on_organisation(page: Page):
    """
    Clicks 'Next Page' if available. Returns True/False indicating if more pages exist.
    """
    prev_page_btn = page.locator("//button[@aria-label='Go to previous page']").first

    try:
        if prev_page_btn.is_enabled():
            print("[INFO] Clicking 'Previous Page' button...")
            prev_page_btn.click()
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(0.5)
            return True  # Continue processing
        else:
            print(f"[INFO] Previous page disabled.")
            return False

    except Exception as e:
        print(f"[WARNING] Error clicking previous page: {e}")
        page.screenshot(path="pagination_error.png")
        return False
    
def rerun_failed_codes(page: Page, failed_codes: List[int], max_retries: int = 2) -> bool:
    """
    Reprocess only the business_short_codes that previously failed.
    Navigates through all pages if needed to find and click the row.
    """
    from collections import defaultdict
    retry_count = defaultdict(int)  # Track retries per code
    original_failed = failed_codes.copy()

    for business_short_code in original_failed:
        retry_count[business_short_code] = 0

    remaining = original_failed.copy()

    while remaining and max(retry_count.values()) < max_retries:
        print(f"\n[RETRY] Retry attempt #{max(retry_count.values()) + 1} for {len(remaining)} items...")

        # Restart from first page for each retry pass
        go_previous_on_organisation(page)

        current_page = 1
        total_in_list = get_total_from_pagination(page)

        while True:
            wait_for_table_load(page)
            time.sleep(1)

            # Look for any remaining failed code on this page
            found_any = False
            rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")

            for i in range(rows_locator.count()):
                row = rows_locator.nth(i)
                if not row.is_visible():
                    continue

                try:
                    row_text = row.text_content(timeout=3000) or ""
                    match = re.search(r'^(\d+)', row_text.strip())
                    if not match:
                        continue
                    code = int(match.group(1))

                    if code in remaining:
                        print(f"[RETRY] Found failed row: {code} — reprocessing...")
                        found_any = True
                        
                        row.click(timeout=15000)
                        page.wait_for_timeout(1000)

                        success = process_single_row(page, code, row_number=f"RETRY-{code}")

                        if success:
                            remaining.remove(code)
                            print(f"[SUCCESS] Retry succeeded for {code}")
                        else:
                            retry_count[code] += 1
                            if retry_count[code] >= max_retries:
                                print(f"[FAILED] Max retries reached for {code}")
                                remaining.remove(code)
                            else:
                                print(f"[RETRY] Will retry {code} later (attempt {retry_count[code] + 1})")

                        time.sleep(1)

                except Exception as e:
                    print(f"[ERROR] Error during retry scan of row: {e}")
                    continue

            if not remaining:
                print("[SUCCESS] All failed items successfully retried!")
                break

            # Go to next page if we didn't find everything
            if go_forth_on_organization(page, total_in_list):
                current_page += 1
                print(f"[INFO] Moving to page {current_page} for retry...")
                time.sleep(2)
            else:
                print("[INFO] Reached last page during retry pass.")
                break

        if not remaining:
            break

    # Final summary
    if remaining:
        print(f"[WARNING] These codes failed even after {max_retries} retries: {remaining}")
    else:
        print("[SUCCESS] All previously failed organizations were successfully recovered!")
        failed_codes.clear()
        return True
        
def select_account_dropdown(page: Page, account_name: str, arrow_down_count: int) -> bool:
    """
    Generic function to select any account dropdown (Float or Commission)
    """
    try:
        print(f"[INFO] Selecting account: {account_name}")

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
            print("[INFO] Falling back to CSS-based dropdown locator...")
            dropdown = page.locator(".el-select").nth(0) \
                           .locator("i.el-select__caret")

        # Wait for it to be visible and clickable
        dropdown.wait_for(state="visible", timeout=15000)
        dropdown.click(force=True)  # force=True helps with overlay issues
        print(f"[INFO] {account_name} dropdown opened")

        # Navigate with ArrowDown + Enter
        for _ in range(arrow_down_count):
            page.keyboard.press("ArrowDown")
            time.sleep(0.2)
        page.keyboard.press("Enter")
        print(f"[INFO] Selected option #{arrow_down_count + 1} in {account_name}")
        time.sleep(1)  # Let selection settle

        return True

    except Exception as e:
        print(f"[ERROR] Failed to select {account_name} dropdown: {e}")
        page.screenshot(path=f"dropdown_error_{account_name.lower()}.png")
        return False

def process_float_account_details(page: Page, business_short_code: int, mapped_data: Optional[dict], pass_value: str) -> tuple:
    try:
        print("[INFO] Processing Float Account Details")

        # Step 1: Select Float Account (usually 2nd or 3rd option)
        if not select_account_dropdown(page, "Float Account", arrow_down_count=2):
            return "dropdown",False
        
        extract_extra_till_info(page, mapped_data)
        
        print("We are checking whether a till is frozen or not")        
        if is_till_frozen(page):
            send_alert_on_non_active_(user.email,
                                        mapped_data.get("company_name","-"),
                                        business_short_code=business_short_code,
                                        status="FROZEN")
            # return "frozen",False

        print(f"This is the date and time selection")
        
        time.sleep(1)  # Wait for table to load

        print("We are trying to save to the dataframe")
        
        df,success_value = scrape_180_days_monthly(page,business_short_code=business_short_code,pass_value=pass_value,additional_category="float")
        if df is not None or success_value:
            print("[SUCCESS] Float table extracted")
            return "dataframe",True
        else:
            print("[ERROR] Failed to extract float table")
            return "dataframe",False

    except Exception as e:
        print(f"[ERROR] process_float_account_details failed: {e}")
        page.screenshot(path="float_error.png")
        return False

def click_search_button(page: Page) -> bool:
    try:
        print("[INFO] Clicking Search button")
        search_button = page.locator("//div[@class='section-content']//button").first
        search_button.wait_for(state="visible", timeout=10000)
        search_button.click(force=True)
        print("[INFO] Search button clicked")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to click Search button: {e}")
        return False

def click_search_button_head_office(page: Page) -> bool:
    try:
        print("[INFO] Clicking Search button")
        search_button = page.locator("//div[@id='pane-transactions']//form[@class='el-form el-form--default el-form--label-top form-flex-container']//button[1]").first
        search_button.wait_for(state="visible", timeout=10000)
        search_button.click(force=True)
        print("[INFO] Search button clicked")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to click Search button: {e}")
        return False

def process_commission_account_details(page: Page, business_short_code: int, mapped_data: Optional[dict], pass_value: str) -> bool:
    try:
        print("[INFO] Processing Commission Account Details")
        scroll_to_top(page)
        time.sleep(1)

        # Step 1: Select Commission Account (usually 5th+ option)
        if not select_account_dropdown(page, "Commission Account", arrow_down_count=3):
            return False

        extract_extra_till_info(page, mapped_data)
        
        df,success_value = scrape_180_days_monthly(page,business_short_code=business_short_code,pass_value=pass_value,additional_category="commission")
        if df is not None or success_value:
            print("[SUCCESS] Commission table extracted")
            return True
        else:
            print("[ERROR] Failed to extract commission table")
            return False

    except Exception as e:
        print(f"[ERROR] process_commission_account_details failed: {e}")
        page.screenshot(path="commission_error.png")
        return False

def process_float_commission(page: Page, business_short_code: int , mapped_data:Optional[dict], pass_value: str) -> bool:
    """Main function – processes both float and commission sequentially"""
    
    trials = 3

    proc_type, success = process_float_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value)
    print(f"[DEBUG] Float Account processing result: {proc_type}, success: {success}")
    if not success and proc_type != "frozen":
        close_irritative_dialog_box(page)
        print(f"[ERROR] Failed at Float Account step {business_short_code} - Retrying...")
        while trials > 0:
            trials -= 1
            print(f"[INFO] Retrying Float Account step {business_short_code} ({3 - trials} attempts left)...")
            proc_type_inner, success_inner = process_float_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value)
            if success_inner:
                print("[SUCCESS] Float Account step completed")
                break
            time.sleep(1)  # Wait before retrying
        else:
            print("[ERROR] All retries failed for Float Account step")
            return False
        return False
    elif not success and proc_type == "frozen":
        print(f"[INFO] Till is frozen for business {business_short_code}, skipping further processing.")
        return False
        
    if pass_value == "first":                                                                                                       
        print(f"[INFO] First pass — skipping commission for {business_short_code}")                                          
        return True  

    # Small pause to let page stabilize
    time.sleep(1)

    if not process_commission_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value):
        print(f"[ERROR] Failed at Commission Account step {business_short_code} - Retrying...")
        close_irritative_dialog_box(page)
        while trials > 0:
            trials -= 1
            print(f"[INFO] Retrying Commission Account step {business_short_code} ({3 - trials} attempts left)...")
            if process_commission_account_details(page, business_short_code,mapped_data=mapped_data, pass_value=pass_value):
                print("[SUCCESS] Commission Account step completed")
                break
            time.sleep(1)  # Wait before retrying
        else:
            print("[ERROR] All retries failed for Commission Account step") 
            
        return False

    print(f"[SUCCESS] Completed processing business {business_short_code}")
    return True

def _find_visible_date_input(page: Page, placeholder: str, max_wait: int = 15):
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
                    print(f"[✓] Found visible '{placeholder}' input (index {i} of {count})")
                    return inp
            except Exception:
                continue
        print(f"[WAIT] '{placeholder}' — none of {count} candidates visible yet, retrying...")
        time.sleep(1)

    # Dump page state for diagnosis
    try:
        with open("date_input_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("[DEBUG] Page HTML dumped to date_input_debug.html")
    except Exception:
        pass
    raise Exception(f"No visible input with placeholder '{placeholder}' found after {max_wait}s")


def select_dates_and_submit_head_office_monthly(page: Page, month_offset: int = 0) -> bool:
    """
    Select exact calendar month boundaries for Head Office Commission scraping.
    month_offset=0: 1st of current month → today
    month_offset=1: 1st of last month → last day of last month
    month_offset=2..5: accordingly
    """
    try:
        start_time_input = _find_visible_date_input(page, "Start Time")
        print("[✓] Found Start Time date picker input")
        end_time_input = _find_visible_date_input(page, "End Time")
        print("[✓] Found End Time date picker input")

    except Exception as e:
        print(f"[ERROR] Could not find date picker inputs: {e}")
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

        print(f"[INFO] Head Office Commission month {month_offset + 1}/6:")
        print(f"[INFO]   From: {start_date_str}")
        print(f"[INFO]   To:   {end_date_str}")

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
        click_search_button_head_office(page)

        too_large_error = page.locator("//button[@aria-label='Close this dialog']").first
        if too_large_error.is_visible():
            close_irritative_dialog_box(page)
            return select_dates_and_submit_head_office_monthly(page, month_offset=month_offset)

        print("[✓] Head Office Commission form submitted")
        return True

    except Exception as e:
        print(f"[ERROR] Could not set Head Office Commission dates: {e}")
        traceback.print_exc()
        return False


def scrape_head_office_commission_held_account(page: Page) -> bool:
    """
    Scrapes the Commission Held Account from the Account Statement tab.
    Called while already on the review-transaction page (after scrape_head_office_commission).
    Keeps only rows where Paid In > 0 before saving to the database.
    """
    try:
        print("[INFO] ===== Starting Commission Held Account Scraping =====")

        # Step 1: Click Account Statement tab
        print("[STEP 1] Clicking Account Statement tab...")
        acct_tab = page.wait_for_selector("//div[@id='tab-accountStatement']", timeout=30000)
        acct_tab.click()
        time.sleep(2)

        # Step 2: Open dropdown and select Commission Held Account (7 arrow-downs)
        # 8 lands on "Agency Commission Account"; 7 lands on "Commission Held Account"
        print("[STEP 2] Selecting Commission Held Account (7 arrow-downs)...")
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
        print("[INFO] Commission Held Account selected")

        # Step 3: Scrape last 6 calendar months
        all_data = []
        for month_offset in range(6):
            close_irritative_dialog_box(page)
            print(f"\n{'=' * 60}")
            print(f"Commission Held Account - chunk {month_offset + 1}/6")
            print("=" * 60)

            # Find date inputs
            try:
                start_time_input = _find_visible_date_input(page, "Start Time")
                end_time_input   = _find_visible_date_input(page, "End Time")
            except Exception as e:
                print(f"[ERROR] Date inputs not found for month {month_offset + 1}: {e}")
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
            print(f"[INFO] From: {start_date_str}  To: {end_date_str}")

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
                print("[INFO] Search button clicked")
            except Exception as e:
                print(f"[ERROR] Search failed for month {month_offset + 1}: {e}")
                continue
            time.sleep(2)

            if not does_transaction_exist_for_period_(page):
                print("[INFO] No data for this period — skipping")
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
                    print("[EXPORT] Could not resolve export button coordinates — skipping")
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
                    print("[EXPORT] Not enough Excel options — skipping")
                    continue

                with page.expect_download(timeout=60_000) as dl_info:
                    try:
                        excel_items.nth(2).click(force=True, timeout=15_000)
                    except Exception:
                        excel_items.nth(2).evaluate("el => el.click()")

                temp_path = dl_info.value.path()

                # Extract the company shortcode from the Excel header (row 1 = "Short Code: 462300")
                # This attributes commission to the correct company, not the login shortcode
                excel_shortcode = company_shortcode  # fallback
                try:
                    df_header = pd.read_excel(temp_path, nrows=6, header=None)
                    for hi in range(len(df_header)):
                        row_str = ' '.join(df_header.iloc[hi].astype(str).tolist())
                        sc_match = re.search(r'Short\s*Code[:\s]+(\d{4,})', row_str, re.IGNORECASE)
                        if sc_match:
                            excel_shortcode = sc_match.group(1).strip()
                            print(f"[INFO] Excel company shortcode: {excel_shortcode}")
                            break
                except Exception as _hdr_err:
                    print(f"[WARN] Could not extract shortcode from Excel header: {_hdr_err}")

                # Read and split by transaction kind
                df_raw = pd.read_excel(temp_path, skiprows=6)
                print(f"[DEBUG] Raw columns: {list(df_raw.columns)}, rows: {len(df_raw)}")

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
                    print(f"[INFO] Clawback save result: {r_cb.get('success')} — {len(df_clawback)} row(s) for month {month_offset + 1}")

                # Save commission held rows (non-clawback, attributed to Excel's company)
                results = transaction_service.update_transactions_from_dataframe(
                    df=df_held,
                    transaction_type="commission_held",
                    company_shortcode=excel_shortcode,
                    agent_id=None,
                    business_shortcode=excel_shortcode
                )
                print(f"[DEBUG] Commission held save result: success={results.get('success')}, "
                      f"created={results.get('created_count',0)}, updated={results.get('updated_count',0)}, "
                      f"errors={results.get('error_count',0)}, error={results.get('error','')}")
                if results.get('success'):
                    df_raw['scrape_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    df_raw['month_offset'] = month_offset
                    all_data.append(df_raw)
                    print(f"[SUCCESS] Commission Held: {len(df_held)} rows saved for month {month_offset + 1}")

            except Exception as exp_err:
                print(f"[ERROR] Export/save failed for month {month_offset + 1}: {exp_err}")
                traceback.print_exc()

            if month_offset < 5:
                time.sleep(1)

        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"\n{'=' * 60}")
            print(f"COMMISSION HELD TOTAL: {len(combined)} rows from {len(all_data)} periods")
            print("=" * 60)
        else:
            print("[INFO] No Commission Held data scraped")

        print("[INFO] ===== Commission Held Account Scraping Complete =====")
        return True

    except Exception as e:
        print(f"[ERROR] scrape_head_office_commission_held_account failed: {e}")
        traceback.print_exc()
        return False


def scrape_head_office_commission(page: Page) -> bool:
    """
    Scrapes the Head Office Commission account immediately after login.
    Clicks the dashboard Review Transaction card, navigates to the Transactions
    tab, selects the Head Office Commission dropdown option (7th caret, 6 arrow-downs),
    then scrapes the last 6 calendar months of data via Excel export.
    """
    try:
        print("[INFO] ===== Starting Head Office Commission Scraping =====")

        # Step 1: Click the Review Transaction card button on the dashboard
        print("[STEP 1] Clicking Review Transaction card button...")
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

        # Step 2: Click Transactions tab
        print("[STEP 2] Clicking Transactions tab...")
        transactions_tab = page.wait_for_selector(
            "//div[@id='tab-transactions']",
            timeout=30000
        )
        transactions_tab.click()
        time.sleep(1)

        # Step 3: Open the 7th account dropdown caret and arrow-down 6 times
        print("[STEP 3] Selecting Head Office Commission account from dropdown...")
        dropdown = page.locator("(//i[@class='el-icon el-select__caret el-select__icon'])[7]")
        if dropdown.count() == 0:
            print("[INFO] Primary dropdown locator not found, trying positional fallback...")
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
        print("[INFO] Head Office Commission account selected")

        # Step 4: Scrape last 6 calendar months
        all_data = []
        for month_offset in range(3):
            close_irritative_dialog_box(page)
            print(f"\n{'=' * 60}")
            print(f"Head Office Commission - chunk {month_offset + 1}/3")
            print("=" * 60)

            success = select_dates_and_submit_head_office_monthly(page, month_offset=month_offset)
            if not success:
                close_irritative_dialog_box(page)
                time.sleep(1)
                print(f"[INFO] Retrying date selection for month offset {month_offset}...")
                success = select_dates_and_submit_head_office_monthly(page, month_offset=month_offset)
                if not success:
                    print(f"[ERROR] Skipping month offset {month_offset} after retry failure")
                    continue

            time.sleep(1)

            if not does_transaction_exist_for_period_(page):
                print("[INFO] No transactions found for this period — skipping")
                continue

            df, success_value = save_table_to_dataframe_download_head_office(
                page,
                business_shortcode=company_shortcode,
                additional_category="commission"
            )

            if df is not None and len(df) > 0:
                df['scrape_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                df['month_offset'] = month_offset
                all_data.append(df)
                print(f"[SUCCESS] Head Office Commission: {len(df)} rows for month offset {month_offset}")
            else:
                print(f"[INFO] No data returned for month offset {month_offset}")

            if month_offset < 2:
                time.sleep(1)

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            print(f"\n{'=' * 60}")
            print(f"HEAD OFFICE COMMISSION TOTAL: {len(combined_df)} rows from {len(all_data)} periods")
            print("=" * 60)
        else:
            print("[INFO] No Head Office Commission data scraped across all periods")

        print("[INFO] ===== Head Office Commission Scraping Complete =====")

        # Immediately scrape Commission Held Account from the Account Statement tab
        scrape_child_org_commission(page, business_shortcode=company_shortcode)
        return True

    except Exception as e:
        print(f"[ERROR] scrape_head_office_commission failed: {e}")
        traceback.print_exc()
        return False


def select_dates_and_submit_monthly(page: Page, month_offset: int = 0) -> bool:
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
        print("[✓] Found Start Time date picker input")
        
        end_time_input = page.wait_for_selector(
            "//input[@placeholder='End Time']", 
            timeout=30000
        )
        print("[✓] Found End Time date picker input")
        
    except Exception as e:
        print(f"[ERROR] Could not find date picker inputs: {e}")
        user = User.query.filter_by(id=user_id).first()
        if user:
            send_session_timeout_email("martinmaati31@gmail.com")
            context.close()
            browser.close()
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
            print(f"[INFO] Month offset {month_offset} exceeds 180 days limit")
            return False
        
        # Format dates with time appended
        start_date_str = f"{start_date.strftime('%d/%m/%Y')} 00:00:00"
        end_date_str = f"{end_date.strftime('%d/%m/%Y')} 23:59:59"  # Changed to end of day
        
        print(f"[INFO] Selecting date range {month_offset+1}/6:")
        print(f"[INFO] From: {start_date_str}")
        print(f"[INFO] To: {end_date_str}")
        
        # Close any open calendars first
        page.click("body", position={"x": 10, "y": 10})
        time.sleep(1)
        
        # --- SET START DATE WITH TIME ---
        print("[STEP 1] Setting Start Date with time...")
        
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
        print("[STEP 2] Setting End Date with time...")
        
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
        print("[STEP 3] Submitting form...")
        
        # Try to find and click submit button if exists
        click_search_button(page)
                
        # Wait for results to load
        time.sleep(2)
        too_large_error = page.locator("//button[@aria-label='Close this dialog']").first
        if too_large_error.is_visible():
            close_irritative_dialog_box(page)
            select_dates_and_submit_monthly(page, month_offset=month_offset)
            print("[ERROR] Date range too large error encountered")
        print("[✓] Form submitted successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Could not set dates: {e}")
        import traceback
        traceback.print_exc()
        return False

def _get_total_months_by_shortcode_shortfall(business_shortcode: str, till_scraping_shortfall: Dict, transaction_type: str = None) -> tuple:
    """
    Calculate the number of months to scrape based on shortfall.

    Args:
        business_shortcode: The business shortcode to check
        till_scraping_shortfall: Dict with scraping data, can be:
            - Simple format: {shortcode: [days, receipt_no]}
            - Nested format: {shortcode: {'float': [days, receipt_no], 'commission': [days, receipt_no]}}
        transaction_type: Optional - 'float' or 'commission' for specific type lookup

    Returns:
        tuple: (number_of_months, days_since_last_scrape)
    """
    if not till_scraping_shortfall:
        return 6, 180

    if business_shortcode not in till_scraping_shortfall.keys():
        return 6, 180

    shortcode_data = till_scraping_shortfall[business_shortcode]

    # Check if it's nested format (dict) or simple format (list)
    if isinstance(shortcode_data, dict):
        # Nested format: {'float': [days, receipt_no], 'commission': [days, receipt_no]}
        if transaction_type and transaction_type in shortcode_data:
            days = float(shortcode_data[transaction_type][0])
        else:
            # If no transaction_type specified or not found, get the max days from all types
            days_list = [float(v[0]) for v in shortcode_data.values() if isinstance(v, list)]
            days = max(days_list) if days_list else 180
    else:
        # Simple format: [days, receipt_no]
        days = float(shortcode_data[0])

    return np.ceil(days / 30).astype(int), days


def get_days_for_transaction_type(business_shortcode: str, till_scraping_shortfall: Dict, transaction_type: str) -> int:
    """
    Get the number of days since last scrape for a specific transaction type.

    Args:
        business_shortcode: The business shortcode to check
        till_scraping_shortfall: Dict with scraping data (nested format expected)
        transaction_type: 'float' or 'commission'

    Returns:
        int: Days since last scrape for the specified type, or 180 if not found
    """
    if not till_scraping_shortfall:
        return 180

    if business_shortcode not in till_scraping_shortfall:
        return 180

    shortcode_data = till_scraping_shortfall[business_shortcode]

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
def scrape_180_days_monthly(page:Page, business_short_code:int=0, pass_value:str="",additional_category=None) -> tuple:
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

    # Get scraping shortfall data - now with transaction_type awareness
    total_months, days = None, None
    if pass_value == "second":
        # For commission (second pass), get fresh data with transaction_type filter
        till_scraping_shortfall_ = transaction_service.get_last_scraped_per_shortcode()
        # Get days specifically for the transaction type being scraped
        days = get_days_for_transaction_type(str(business_short_code), till_scraping_shortfall_, transaction_type)
        total_months = np.ceil(days / 30).astype(int) if days > 0 else 1
    else:
        # For float (first pass)
        total_months, days = _get_total_months_by_shortcode_shortfall(
            str(business_short_code),
            till_scraping_shortfall,
            transaction_type=transaction_type
        )

    print(f"[INFO] Transaction type: {transaction_type}, Pass value: {pass_value}, Days since last scrape: {days}")

    # Determine scraping strategy based on days since last scrape
    if days <= 2 and pass_value == "first":
        print(f"[INFO] Float transactions recently scraped ({days} days ago). Skipping.")
        return pd.DataFrame(), True
    elif days <= 2 and pass_value == "second":
        # Commission was recently scraped - just get latest
        print(f"[INFO] Commission transactions recently scraped ({days} days ago). Getting latest only.")
        df, success_value = save_table_to_dataframe_latest_(
            page,
            business_shortcode=business_short_code,
            pass_value=pass_value,
            additional_category=additional_category
        )
        return df, success_value
    # For both float (first) and commission (second) with days > 2, proceed to monthly scraping
    print(f"[INFO] Will scrape {total_months} month(s) of {transaction_type} data.")

    for month_offset in range(total_months):
        close_irritative_dialog_box(page)
        print(f"\n{'='*60}")
        print(f"Scraping {transaction_type} - month chunk {month_offset+1}/{total_months}")
        print('='*60)

        # Method 1: 30-day chunks
        success = select_dates_and_submit_monthly(page, month_offset=month_offset)

        # Method 2: Exact month boundaries (uncomment if preferred)
        # success = select_exact_month_back(page, months_back=month_offset)

        if not success:
            close_irritative_dialog_box(page)
            time.sleep(1)
            print(f"[INFO] Retrying date selection for month offset {month_offset}...")
            success = select_dates_and_submit_monthly(page, month_offset=month_offset)
            if not success:
                close_irritative_dialog_box(page)
                print(f"[ERROR] Failed to select dates for month offset {month_offset}")
                break

        # Wait for table to load
        time.sleep(1)

        print(f"Saving {transaction_type} data for this period to dataframe...")

        # Get data for this period
        try:
            if not does_transaction_exist_for_period_(page=page):
                print(f"[INFO] No {transaction_type} transactions found for this period. Skipping.")
                continue

            # Use download method for both float and commission when days > 2
            df, success_value = save_table_to_dataframe_download(
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
                
                print(f"[SUCCESS] Scraped {len(df)} rows for period {days_ago_start}-{days_ago_end} days ago")
                success_value_ = success_value
            else:
                print("[INFO] No data found in dataframe")
                
        except Exception as e:
            print(f"[ERROR] Failed to save data for month offset {month_offset}: {e}")
            success_value_ = False
        
        # Add delay between requests
        if month_offset < total_months - 1:
            print("[INFO] Waiting before next period...")
            time.sleep(1)
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\n{'='*60}")
        print(f"TOTAL DATA: {len(combined_df)} rows from {len(all_data)} periods")
        print('='*60)
        return combined_df, True if all_data else []
    
    return pd.DataFrame(), success_value_

def select_dates_and_submit_(page: Page) -> bool:
        try:
            # Find the Start Time input (first date picker with placeholder "Start Time")
            start_time_input = page.wait_for_selector(
                "//input[@placeholder='Start Time']", 
                timeout=10000
            )
            print("[✓] Found Start Time date picker input")
            
            # Find the End Time input (first date picker with placeholder "End Time")
            end_time_input = page.wait_for_selector(
                "//input[@placeholder='End Time']", 
                timeout=10000
            )
            print("[✓] Found End Time date picker input")
            user = User.query.filter_by(id=user_id).first()
            if user:
                # send_session_timeout_email(user.email)
                send_session_timeout_email("martinmaati31@gmail.com")
                context.close()
                browser.close()
                

        except Exception as e:
            print(f"[ERROR] Could not find date picker inputs: {e}")
            
            # Fallback: Try finding by class and position
            try:
                print("[INFO] Trying fallback selector for date pickers...")
                date_inputs = page.query_selector_all(
                    "//div[@class='el-date-editor']//input[@class='el-input__inner']"
                )
                if len(date_inputs) >= 2:
                    start_time_input = date_inputs[0]
                    end_time_input = date_inputs[1]
                    print(f"[✓] Found {len(date_inputs)} date picker inputs using fallback")
                else:
                    print(f"[ERROR] Expected at least 2 date inputs, found {len(date_inputs)}")
                    return False
            except Exception as fallback_error:
                print(f"[ERROR] Fallback selector also failed: {fallback_error}")
                return False
        
        # Step 3: Fill Start Time with first day of current month in dd/MM/yyyy format
        try:
            #first_day = datetime.now().replace(day=1).strftime("%d/%m/%Y")            
            # Click the Start Time input to focus
            start_time_input.click()
            
            print(f"We have just clicked the start time")
            previous_month_icon = page.wait_for_selector(
                "//div[@actualvisible='true']//button[@aria-label='Previous Month']", 
                timeout=5000
            )
            
            for i in range(3):
                previous_month_icon.click() 
            
            print("The previous button has been clicked thrice .......")
            
            for i in range(5):
                page.keyboard.press("Tab")
                print("Tab pressed")
            
            page.keyboard.press("Enter")
            
        except Exception as e:
            print(f"[ERROR] Could not fill Start Time input: {e}")
            return False
        
        # Step 4: Press Tab three times and Enter to submit
        try:
            print("[INFO] Pressing Tab three times and Enter to submit...")
            
            # Ensure Start Time input has focus
            start_time_input.focus()
            page.wait_for_timeout(500)
            
            # Debug: Check current focused element
            focused_element = page.evaluate_handle("() => document.activeElement")
            focused_tag = page.evaluate("(elem) => elem.tagName", focused_element)
            focused_id = page.evaluate("(elem) => elem.id || elem.placeholder || 'no-id'", focused_element)
            print(f"[DEBUG] Current focused element: {focused_tag} (ID/Placeholder: {focused_id})")
            
            # Press Tab three times
            for i in range(4):
                page.keyboard.press("Tab")
                page.wait_for_timeout(500)
                # Debug: Check focused element after each Tab
                focused_element = page.evaluate_handle("() => document.activeElement")
                focused_tag = page.evaluate("(elem) => elem.tagName", focused_element)
                focused_id = page.evaluate("(elem) => elem.id || elem.placeholder || 'no-id'", focused_element)
                print(f"[DEBUG] After Tab {i+1}, focused element: {focused_tag} (ID/Placeholder: {focused_id})")
            
            # Press Enter to submit
            page.keyboard.press("Enter")
            print("[✓] Pressed Enter to submit form")
            # page.wait_for_timeout(3000)  # Wait for page to load results
            time.sleep(1)  # Wait for page to load results
        except Exception as e:
            print(f"[ERROR] Could not complete Tab/Enter submission: {e}")
            traceback.print_exc()
            return False

def solveCaptchaXai(image_path):
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
                "role": "user",
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
    print(f"Extracted CAPTCHA: {captcha_text}")
    return captcha_text

def extract_user_agent_kyc(short_code: str, page: Page) -> bool:
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
        print("[INFO] Navigating to Organization Operator section...")
        org_operator_tab = page.wait_for_selector(
            "//div[contains(text(),'Organization Operator')]",
            timeout=15000
        )
        org_operator_tab.click()
        time.sleep(1)

        # Step 2: Collect all operator rows
        rows = page.query_selector_all("//tr[@class='el-table__row']")
        print(f"[INFO] Found {len(rows)} operator row(s) for short_code {short_code}")

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
                print(f"[INFO] Row {idx + 1}/{len(rows)} — role: {operator_role}")

                # Step 3: Click the Detail button on this row
                detail_btn = row.query_selector("button[type='button']")
                if not detail_btn:
                    print(f"[WARN] No button found on row {idx + 1}, skipping.")
                    continue

                detail_btn.click()
                time.sleep(3)

                # Step 4: Wait for and capture the KYC form HTML
                kyc_panel = page.wait_for_selector(
                    "//div[@class='common-kyc-form common-kyc-form-review']",
                    timeout=15000
                )
                kyc_html = kyc_panel.inner_html()
                print(f"[DEBUG] Captured KYC HTML for row {idx + 1} ({len(kyc_html)} chars)")

                # Step 5: Parse and save the KYC form
                _parse_and_save_kyc(
                    kyc_html=kyc_html,
                    short_code=short_code,
                    agent_company=agent_company,
                    operator_role=operator_role
                )

                # Navigate back to the operator list for the next row
                page.go_back()
                close_detail_panel(page)
                time.sleep(1)

                # Re-query rows after navigation
                rows = page.query_selector_all("//tr[@class='el-table__row']")

            except Exception as row_err:
                print(f"[ERROR] Failed to process row {idx + 1}: {row_err}")
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
        print(f"[INFO] Successfully processed KYC for short_code {short_code}")

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] extract_user_agent_kyc failed for {short_code}: {e}")
        traceback.print_exc()


def _parse_and_save_kyc(kyc_html: str, short_code: str, agent_company, operator_role: str = None) -> None:
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
        print("[WARN] No ID number found in KYC form, skipping.")
        return

    print(f"[INFO] KYC — name: {first_name} {lastname}, ID: {id_number}, "
          f"phone: {phone}, email: {email_val}, dob: {date_of_birth}, "
          f"gender: {gender}, nationality: {nationality}")

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
            print(f"[INFO] Found existing UserAgent id={existing.id} with same role={operator_role} "
                  f"for company {agent_company.short_code} — updating.")
        else:
            print(f"[INFO] No UserAgent with role={operator_role} for company {agent_company.short_code} "
                  f"— will create new.")

    if existing:
        existing.firstname         = first_name or existing.firstname
        existing.lastname          = lastname   or existing.lastname
        existing.idnumber          = id_number
        existing.authenticity_desc = f"Scraped from KYC (short_code={short_code})"
        if phone:
            existing.phone_number = phone
        if user_id:
            existing.user_id = user_id
        if agent_company and not existing.agent_company_id:
            existing.agent_company_id = agent_company.id
        user_agent = existing
        print(f"[INFO] Updated UserAgent id={existing.id} role={operator_role}")
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
            if user_id:
                id_conflict.user_id = user_id
            if agent_company and not id_conflict.agent_company_id:
                id_conflict.agent_company_id = agent_company.id
            user_agent = id_conflict
            print(f"[INFO] ID {id_number} already exists globally (id={id_conflict.id}), "
                  f"reused and updated role to {operator_role}.")
        else:
            user_agent = UserAgent(
                firstname=first_name,
                lastname=lastname,
                idnumber=id_number,
                phone_number=phone,
                is_authentic=False,
                authenticity_desc=f"Scraped from KYC (short_code={short_code})",
                operator_role=operator_role,
                user_id=user_id,
                agent_company_id=agent_company.id if agent_company else None
            )
            db.session.add(user_agent)
            db.session.flush()
            print(f"[INFO] Created new UserAgent id={user_agent.id} role={operator_role}")

    if agent_company and agent_company not in user_agent.agent_companies:
        user_agent.agent_companies.append(agent_company)
        print(f"[INFO] Linked UserAgent to AgentCompany {agent_company.company_name}")

def navigate_to_review_transaction(business_short_code:str, page:Page) -> bool:
    """Navigate through detail panel to Review Transaction button."""
    try:
        close_irritative_dialog_box(page)
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
        
        extract_user_agent_kyc(short_code=business_short_code,page=page)

        # Click "Review Transaction"
        review_btn = page.wait_for_selector(
            "//div[contains(text(),'Review Transaction')]",
            timeout=10000
        )
        review_btn.click()
        page.wait_for_timeout(1500)
        
        return True
    except Exception as e:
        print(f"[ERROR] Navigation failed: {e}")
        return False

def select_pagination_size(page: Page, down_presses: int = 3, timeout: int = 20000) -> bool:
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
            print("[WARN] Pagination size dropdown not visible")
            return False

        # Optional: wait a tiny bit for UI to settle
        time.sleep(1)

        return True

    except Exception as e:
        print(f" Error while changing page size: {e}")
        return False
    
def close_irritative_dialog_box(page:Page) -> bool:
    """Close any irritative dialog boxes that may block interactions."""
    try:
        dialog_box = page.locator("//button[@aria-label='Close this dialog']").first
        if dialog_box.is_visible():
            dialog_box.click()
            page.wait_for_timeout(1000)
            return True
    except Exception as e:
        print(f"[ERROR] Failed to close irritative dialog box: {e}")
    return False

def does_transaction_exist_for_period_(page:Page) -> bool:
    """Close any irritative dialog boxes that may block interactions."""
    try:
        org_detail = page.wait_for_selector(
            "//div[@class='el-table--fit el-table--border el-table--enable-row-hover el-table el-table--layout-fixed is-scrolling-none']//span[@class='el-table__empty-text'][normalize-space()='No records found.']",
            timeout=5000
        )
        return False
    except Exception as e:
        print(f"[WARN]: The transactions exists {e}")
        return True
    
def close_portal_tabs(page: Page) -> None:
    """Click the last (//i[@class='el-icon']) icon to close the most recently opened portal tab."""
    try:
        icons = page.locator("//i[@class='el-icon']")
        count = icons.count()
        if count <= 2:
            return
        last_icon = icons.nth(count - 1)
        if last_icon.is_visible():
            print(f"[INFO] Closing last portal tab via icon [{count}]")
            last_icon.click()
            page.wait_for_timeout(500)
    except Exception as e:
        print(f"[WARN] close_portal_tabs: {e}")

def close_detail_panel(page):
    """Attempt to close any open detail panels and return to list."""
    print("[INFO] Attempting to close detail panel...")
    try:
        # Try clicking "Organization Detail" tab to go back
        # org_detail = page.locator("//div[@title='Organization Detail']").first
        org_detail = page.locator("(//i[@class='el-icon'])[3]")
        if org_detail.is_visible():
            org_detail.click()
            page.wait_for_timeout(1000)
            return True
    except:
        print("[WARN] 'Organization Detail' tab not found.")
        pass
    
    # Try ESC key
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        return True
    except:
        pass
    
    return False

def return_to_organization_list(page) -> bool:
    """Return to organization list view."""
    print("[INFO] Returning to organization list...")
    close_detail_panel(page)
    try:
        org_detail = page.wait_for_selector(
            "//div[@title='Organization Detail']",
            timeout=5000
        )
        org_detail.click()
        page.wait_for_timeout(1000)
        close_portal_tabs(page)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to return to organization list: {e}")
        return False

def process_organization_rows(page: Page) -> None:
    """
    Main orchestrator: Processes all organization rows across pagination and virtual scrolling.
    """
    total_processed = 0
    to_be_rerun: list[int] = []
    close_irritative_dialog_box(page)
    all_shortcodes_ :Set[str] =set()
    time.sleep(1)
    all_shortcodes = extract_all_business_short_codes(page,all_shortcodes_)
    print(f"[INFO] Extracted {len(all_shortcodes)} business short codes on all pages")
    
    priority_short_codes = _get_priority_shortcodes_(all_shortcodes)
    print(f"[INFO] {len(priority_short_codes)} priority short codes identified for processing")
    
    while go_previous_on_organisation(page):
        pass # Go back to first page

    # Page is already settled — skip the networkidle re-wait on first iteration
    first_iteration = True

    while True:
        print("\n[INFO] Starting new pagination page...")

        if first_iteration:
            time.sleep(0.5)  # page already loaded, avoid redundant networkidle wait
            first_iteration = False
        else:
            wait_for_table_load(page)

        total_in_list = get_total_from_pagination(page)
        if total_in_list == 0:
            print("[INFO] No organizations found.")
            break

        # Try to queue fraud detection task, but don't fail if Redis/Celery is unavailable
        try:
            task = run_fraud_detection_for_user.delay(user_id)
            print(f"[INFO] Fraud detection task queued: {task.id}")
        except Exception as celery_err:
            print(f"[WARNING] Could not queue fraud detection task (Redis/Celery may be unavailable): {celery_err}")
            # Continue with the main flow even if Celery task queueing fails

        processed_on_this_page = process_page_rows(
            page=page,
            total_in_list=total_in_list,
            total_processed_so_far=total_processed,
            priority_short_codes=priority_short_codes,
            to_be_rerun=to_be_rerun,
            pass_value="first"
        )

        total_processed += processed_on_this_page


        # Move to next pagination page
        if not go_forth_on_organization(page, total_in_list):
            print("[INFO] No more pages or navigation failed.")
            print(f"[SUCCESS] All {total_processed} organizations processed successfully!")
            stats = transaction_service.gather_scraping_statistics(
                start_date=datetime.now() - timedelta(days=180),
                end_date=datetime.now(),
                company_shortcode=company_shortcode
            )
            
            # send_scraping_report_email(user.email, stats)
            send_scraping_report_email("martinmaati31@gmail.com", stats)

            # # === Head Office Commission (between float and commission passes) ===
            # print("[INFO] Children float complete. Scraping Head Office Commission...")
            # scrape_head_office_commission(page)  # also calls scrape_head_office_commission_held_account

            # # Navigate back to Child Organisation list for the commission pass
            # print("[INFO] Returning to Child Organisation list for commission pass...")
            # _navigate_to_child_org_list(page)
            # wait_for_table_load(page)

            while go_previous_on_organisation(page):
                pass

            # start the second pass
            start_second_pass(page=page,
                              total_in_list=total_in_list,
                              total_processed_so_far=total_processed,
                              priority_short_codes=all_shortcodes,
                              to_be_rerun=to_be_rerun,
                              pass_value="second")            

        time.sleep(1)  # Gentle pause between pages

    if to_be_rerun:
        print(f"[WARN] {len(to_be_rerun)} organizations failed and need reprocessing: {to_be_rerun}")
        if rerun_failed_codes(page, to_be_rerun):
            print("[SUCCESS] All failed organizations reprocessed successfully!")
        else:
            print("[ERROR] Some organizations still failed after retries.")

    # Scrape Head Office Commission after all rows are processed
    print("[INFO] All rows processed. Navigating to dashboard for Head Office Commission scraping...")
    try:
        page.locator("(//*[name()='svg'][@class='svg-icon'])[1]").first.click()
        time.sleep(2)
    except Exception as _nav_err:
        print(f"[WARN] Dashboard nav click failed: {_nav_err}")
    scrape_head_office_commission(page)

def start_second_pass(page:Page,total_in_list:int,total_processed_so_far:int,priority_short_codes:List[int],to_be_rerun:List[int],pass_value:str):
    while True:
        try:
            processed_on_this_page = process_page_rows(
                                        page=page,
                                        total_in_list=total_in_list,
                                        total_processed_so_far=total_processed_so_far,
                                        priority_short_codes=priority_short_codes,
                                        to_be_rerun=to_be_rerun,
                                        pass_value=pass_value
                                    )
        except Exception as e:
            print(f"[ERROR] An error has occured here {str(e)}")

def scrape_child_org_commission(page:Page,business_shortcode:str=""):
    try:
        print("[INFO] Scraping Child Organisation Commission...")
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

        save_table_to_dataframe_download_head_office(
            page, business_shortcode,
            filter_text="CSV",
            min_item_count=1,   # adjust if CSV has fewer menu entries than Excel
            target_index=1,
        )
    except Exception as e:
        print(f"[ERROR] Failed to scrape child organization commission: {e}")

def wait_for_table_load(page: Page, timeout: int = 15000) -> None:
    """Wait for network idle and allow lazy loading."""
    page.wait_for_load_state("networkidle", timeout=timeout)
    time.sleep(0.5)
    
def extract_all_business_short_codes(
    page: Page,
    short_codes: Optional[Set[str]] = None
) -> Set[str]:

    if short_codes is None:
        short_codes = set()

    rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")
    print(f"The length of the shortcodes is {len(short_codes)}")    

    for i in range(rows_locator.count()):
        row = rows_locator.nth(i)

        try:
            row_text = row.text_content(timeout=3000) or ""
            match = re.search(r'^(\d+)', row_text.strip())
            if match:
                short_codes.add(match.group(1))  # set auto-deduplicates
        except Exception as e:
            print(f"[ERROR] Error extracting short code from row: {e}")

    if go_forth_on_organization(page, get_total_from_pagination(page)):
        wait_for_table_load(page)
        # print(f"From page {counter} We are passing {len(short_codes)}")
        extract_all_business_short_codes(page, short_codes)

    return short_codes

def _get_priority_shortcodes_(all_shortcodes: Set[str]) -> Set[str]:
    """Return shortcodes with scraping priority."""
    priority_shortcode_indexes: Set[str] = set()

    print(f"All shortcodes are of length {len(all_shortcodes)}")

    for business_shortcode in all_shortcodes:
        total_months, days = _get_total_months_by_shortcode_shortfall(
            business_shortcode,
            till_scraping_shortfall
        )

        print(
            f"[INFO] Total months to scrape based on shortfall: "
            f"{total_months} for shortcode {business_shortcode} and {days} days"
        )

        if days != 0:
            priority_shortcode_indexes.add(business_shortcode)

    return priority_shortcode_indexes

# def force_refresh_with_routing(page:Page):
#     try:
#         # Disable HTTP cache by enabling routing
#         # The route handler simply continues the request without caching
#         page.route('**', lambda route: route.continue())

#         page.goto("https://example.com")
#         print("Page loaded the first time (cache disabled).")

#         # Now, page.reload() will perform a hard refresh because the cache is disabled
#         page.reload()
#         print("Page reloaded (hard refresh).")

#         return True
#     except Exception as e:
#         print(f"[ERROR] An error occurred {str(e)}")
#         return False

def _is_agent_company_scraped(business_short_code: int) -> bool:
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
        print(f"[WARN] Could not check scrape status for {business_short_code}: {e}")
        return False

def process_single_row_kyc_only(page: Page, business_short_code: int, row_number: int) -> bool:
    """
    Lightweight scrape: only till details + KYC contacts.
    Skips transaction scraping (float/commission).
    Used for non-priority tills that haven't been scraped yet.
    """
    try:
        print(f"\n[KYC-ONLY] Processing Row {row_number} | Business Code: {business_short_code} (lightweight)")
        close_irritative_dialog_box(page)

        # Scrape basic till details and save agent company
        mapped_data = scrape_till_details(page, business_short_code)

        # Save the scraped till details to DB
        save_results = agent_company_service.save_or_update_scraped_agent_company(
            mapped_data=mapped_data, user_id=user_id
        )
        print(f"[KYC-ONLY] Saved till details: {save_results}")

        # Navigate to detail panel to extract KYC
        try:
            close_irritative_dialog_box(page)
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
            extract_user_agent_kyc(short_code=business_short_code, page=page)
            print(f"[KYC-ONLY] KYC extraction complete for {business_short_code}")
        except Exception as kyc_err:
            print(f"[KYC-ONLY] KYC extraction failed for {business_short_code}: {kyc_err}")

        # Return to org list
        if not return_to_organization_list(page):
            print("[KYC-ONLY] Failed to return to list — attempting recovery")
            page.reload()
            wait_for_table_load(page)
            return False

        return True

    except Exception as e:
        print(f"[ERROR] KYC-only processing failed for {business_short_code}: {e}")
        traceback.print_exc()
        close_irritative_dialog_box(page)
        close_detail_panel(page)
        return False

def process_page_rows(
    page: Page,
    total_in_list: int,
    total_processed_so_far: int,
    priority_short_codes: set[str],
    to_be_rerun: list[int],
    pass_value: str
) -> int:
    """Process all visible rows on the current page with virtual scrolling support."""
    close_irritative_dialog_box(page)
    processed_on_page = 0
    rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")

    visible_rows = get_visible_rows(rows_locator)

    print(f"The priority short codes are {priority_short_codes}")

    if not visible_rows:
        print("[INFO] No visible rows — scrolling to load more...")
        page.mouse.wheel(0, 1200)
        time.sleep(2)

    visible_rows_size = len(visible_rows)
    print(f"[INFO] Found {visible_rows_size} visible rows to process on this page")

    for row in visible_rows:
        if processed_on_page >= 10:
            break

        business_short_code = extract_business_short_code(row)
        if not business_short_code:
            processed_on_page += 1
            continue

        is_priority = str(business_short_code) in priority_short_codes
        already_scraped = _is_agent_company_scraped(business_short_code)

        if not is_priority and already_scraped:
            # Non-priority AND already scraped — skip entirely
            print(f"[INFO] Skipping row {business_short_code} — not priority and already scraped.")
            processed_on_page += 1
            continue

        row.click(timeout=15000)
        page.wait_for_timeout(1000)

        if is_priority:
            # Full scrape: till details + KYC + transactions
            success = process_single_row(page, business_short_code, total_processed_so_far + processed_on_page + 1, pass_value=pass_value)
        else:
            # Lightweight scrape: till details + KYC only (no transactions)
            print(f"[INFO] Non-priority but unscraped — doing KYC-only scrape for {business_short_code}")
            success = process_single_row_kyc_only(page, business_short_code, total_processed_so_far + processed_on_page + 1)

        if success:
            print(f"[SUCCESS] Completed row {total_processed_so_far + processed_on_page + 1}")
        else:
            if is_priority:
                to_be_rerun.append(business_short_code)
            return_to_organization_list(page)
            print(f"[WARN] Row {business_short_code} failed{', added to rerun list' if is_priority else ''}")

        processed_on_page += 1

    # Scroll to load more rows if needed
    if processed_on_page < total_in_list:
        page.mouse.wheel(0, 1200)
        time.sleep(0.5)

    return processed_on_page

def get_visible_rows(rows_locator: Locator) -> list[Locator]:
    """Return only currently visible rows."""
    count = rows_locator.count()
    return [
        rows_locator.nth(i)
        for i in range(count)
        if rows_locator.nth(i).is_visible()
    ]

def extract_business_short_code(row: Locator) -> int | None:
    """Extract the leading numeric business short code from the row text."""
    try:
        row.scroll_into_view_if_needed(timeout=10000)
        # page.wait_for_timeout(800)

        row_text = row.text_content(timeout=5000) or ""
        match = re.search(r'^(\d+)', row_text.strip())
        if not match:
            print(f"[WARN] Could not extract business short code from row: {row_text[:100]}...")
            return None

        return int(match.group(1))
    except Exception as e:
        print(f"[ERROR] Failed to extract short code: {e}")
        return None

def process_single_row(page: Page, business_short_code: int, row_number: int, pass_value: int) -> bool:
    """Process one organization row end-to-end."""
    try:
        print(f"\n[SUCCESS] Processing Row {row_number} | Business Code: {business_short_code}")
        close_irritative_dialog_box(page)

        # Scrape basic till details
        mapped_data = scrape_till_details(page, business_short_code)

        # Persist the company now so extract_user_agent_kyc (called inside
        # navigate_to_review_transaction) can resolve it by short_code.
        # This is intentionally called again in extract_extra_till_info with
        # account details — save_or_update_scraped_agent_company is idempotent.
        agent_company_service.save_or_update_scraped_agent_company(
            mapped_data=mapped_data, user_id=user_id
        )

        # Navigate and process float/commission
        if not navigate_to_review_transaction(business_short_code=business_short_code,page=page):
            print("[ERROR] Failed to navigate to review transaction")
            return_to_organization_list(page)
            return False

        if not process_float_commission(page, business_short_code, mapped_data=mapped_data, pass_value=pass_value):
            print("[ERROR] Failed to process float/commission")
            # return_to_organization_list(page)
            return False

        # Return safely
        if not return_to_organization_list(page):
            print("[WARN] Failed to return to list — attempting recovery")
            page.reload()
            wait_for_table_load(page)
            return False

        return True

    except Exception as e:
        print(f"[ERROR] Exception processing row {business_short_code}: {e}")
        traceback.print_exc()
        close_irritative_dialog_box(page)
        page.screenshot(path=f"error_row_{business_short_code}_{row_number}.png")
        close_detail_panel(page)
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
        print('[ERROR] Set TEST_SHORTCODE, TEST_USERNAME, TEST_PASSWORD in your .env to run locally.')
        sys.exit(1)

    print(f'[TEST] Running login_to_mpesa for short_code={short_code}')
    login_to_mpesa(
        password=password,
        username=username,
        short_code=short_code,
        user_id_passed=user_id,
    )
