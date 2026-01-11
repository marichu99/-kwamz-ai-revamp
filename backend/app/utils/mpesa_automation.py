from playwright.sync_api import sync_playwright,Page,Locator,Download, TimeoutError as PlaywrightTimeoutError
from flask import current_app
from app.utils.script import fill_login_form, capture_and_solve_captcha
from app.utils.email_utils import generate_scraping_report_email, send_scraping_report_email,send_session_timeout_email,send_not_active_short_code_
from app.service.transaction_service import TransactionService
from app.service.agentcompany_service import AgentCompanyService
from app.service.email_outbox_service import EmailOutboxService
from app.model.user import User
from app.model.email_outbox import EmailOutbox
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
        # Fill login fields once
        fill_login_form(page, short_code, username, password)
        print("[INFO] Login form filled")
        
        # Solve captcha initially
        captcha_solution = capture_and_solve_captcha(page)
        print(f"[DEBUG] Initial captcha solution: {captcha_solution}")
        while(len(captcha_solution) > 4):
            captcha_solution = retry_captcha_login(page)
            
        if(has_verification_error_regex(page)):
            captcha_solution = retry_captcha_login(page)

        # Fill verification code input and submit
        page.fill("//input[@id='verifyCode']", captcha_solution)
        page.click("//button[@id='loginBtn']")
        print("[INFO] Login button clicked; waiting for response...")
        
        # Wait for navigation or error indication
        search = page.wait_for_selector("(//i[@class='el-icon el-sub-menu__icon-arrow'])[1]", timeout=60000)
        search.click()
        print("[SUCCESS] Logged in successfully!")
        
        
        print("[INFO] Navigating to child organization page...")
        navigate_to_child_organization(page)

        print("[INFO] Browser will remain open for inspection. Press ENTER to close.")
        # input()

def has_verification_error_regex(page) -> bool:
    """Checks if the page contains a verification code error using regex."""
    # with open("debug_page.html", "w", encoding="utf-8") as f:
    #     f.write(page.content())
    body_text = page.locator("body").inner_text()
    pattern = re.compile(r"verification\s+code\s+is\s+incorrect\s+or\s+has\s+expired", re.IGNORECASE)
    return bool(pattern.search(body_text))

def retry_captcha_login(page:Page) -> str:
    """
    Retries the captcha login process until successful or max attempts reached.
    
    Args:
        page: Playwright Page object
    """
    captcha_solution = ""
    svg_element = page.query_selector("//div[@class='img-part']//*[name()='svg']")
    if svg_element:
        svg_element.click()
        print("[INFO] Clicked SVG element to refresh captcha")
        captcha_solution = capture_and_solve_captcha(page)
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
        
def navigate_to_child_organization(page):
    """
    Navigates after login: hover on the index icon, click 'My Organization',
    then click 'Child Organization' and save the resulting page HTML.
    """
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

    # Wait for transition
    page.wait_for_timeout(2000)
    
    page.mouse.click(10, 10)
    print("[INFO] Clicked on a neutral area to close any open dropdowns.")

    print("[INFO] Clicking 'Child Organization' button...")
    child_org_btn = page.wait_for_selector(
        "//button[normalize-space()='Child Organization']",
        timeout=60000
    )
    # //button[@aria-label='Go to next page']
    child_org_btn.click()
    print("[INFO] 'Child Organization' clicked. Waiting for page to load...")

    # Wait for page load


    print("[INFO] Browser will remain open for inspection. Press ENTER to continue.")
    process_organization_rows(page)
    #input()

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
        
        # Debug: Save HTML for inspection
        # html_content = page.content()
        # with open("extra_info_debug.html", "w", encoding="utf-8") as f:
        #     f.write(html_content)

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
                                              status=key)
                    
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
        
        with open(f"page_{business_shortcode}_content.html", "w", encoding="utf-8") as f:
            f.write(trs.prettify())
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
    try:
        print("[INFO] Starting table extraction...")
        
        success = click_search_button(page=page)        
        
        if not success:
            print(f"[ERROR] Can not select the search button")
        
        select_pagination_size(page=page)
        # Get the latest receipt number for this shortcode
        print(f"The till scraping shortfall {till_scraping_shortfall}")
                
        try:                
            # Wait for page to load
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Wait for table to be visible
            body_tbl = page.wait_for_selector(
                "//table[@class='el-table__body']",
                timeout=10000
            )
            
            if not body_tbl.is_visible():
                print("[WARN] Table body not visible, ending extraction.")
                return None, None

            # Parse the table directly
            html_content = body_tbl.inner_html()
            
            # Save raw HTML (optional)
            with open(f"transactions_{business_shortcode}.html", "w", encoding="utf8") as f:
                f.write(BeautifulSoup(html_content, "html.parser").prettify())
            
            # Convert to DataFrame
            df,columns = parse_element_plus_transactions(html_content,transaction_type=additional_category,business_shortcode=business_shortcode)
            
            if df.empty:
                print("[WARN] No transactions found in table.")
                return None, None
                
            return df, columns

        except Exception as e:
            print(f"[ERROR] Failed to extract table: {e}")
            return None, None
        
        # Find the matching receipt and click all from that point to latest
        # print(f"[INFO] Looking for receipt {latest_receipt_number} and transactions from match point...")
        
        # try:
        #     # Find all receipt links on the page
        #     receipt_links = page.locator("span.receipt-link")
        #     receipt_count = receipt_links.count()
            
        #     if receipt_count == 0:
        #         print("[WARN] No receipt links found on the page.")
        #         return None, None
                
        #     print(f"[INFO] Found {receipt_count} receipt links on the page.")
            
        #     # First pass: Find all matching receipts and the latest receipt
        #     matching_indices = []
        #     latest_receipt_index = -1
            
        #     for i in range(receipt_count):
        #         try:
        #             link_text = receipt_links.nth(i).inner_text(timeout=3000).strip()
                    
        #             # Check if this link matches the latest receipt number
        #             if link_text == latest_receipt_number or latest_receipt_number in link_text:
        #                 latest_receipt_index = i
        #                 matching_indices.append(i)
        #                 print(f"[INFO] Latest receipt found at position {i}")
        #                 print(f"[INFO] Matching receipt found at position {i}: {link_text}")
                        
        #         except Exception as e:
        #             print(f"[WARN] Could not read link at position {i}: {e}")
        #             continue
            
        #     if not matching_indices and latest_receipt_index == -1:
        #         print(f"[ERROR] No matching receipts found for {latest_receipt_number}")
        #         return None, None
            
        #     # Determine the starting point for clicking
        #     # Option 1: Start from the earliest matching receipt
        #     # start_index = min(matching_indices) if matching_indices else latest_receipt_index
            
        #     # Option 2: Start from the latest matching receipt (uncomment if needed)
        #     start_index = max(matching_indices) if matching_indices else latest_receipt_index
            
        #     print(f"[INFO] Starting to click receipts from position {start_index} to {receipt_count-1}")
            
        #     # Click all receipts from the starting point to the end
        #     for i in range(start_index, receipt_count):
        #         try:
        #             # Get link text
        #             link_text = receipt_links.nth(i).inner_text(timeout=5000).strip()
        #             print(f"[INFO] Clicking receipt {i+1}/{receipt_count}: {link_text}")
                    
        #             # Store the original page context for returning
        #             original_page = page
                    
        #             # Click the receipt link
        #             receipt_links.nth(i).click()
        #             print(f"[INFO] Clicked transaction: {link_text}")
                    
        #             # Wait for the receipt page to load
        #             time.sleep(2)  # Initial wait
        #             page.wait_for_load_state("networkidle", timeout=10000)
                    
        #             # Check if we're on a new tab
        #             current_page = page
        #             if len(page.context.pages) > 1:
        #                 # Switch to the new tab
        #                 new_page = page.context.pages[-1]
        #                 new_page.bring_to_front()
        #                 current_page = new_page
                    
        #             # Extract details from the receipt
        #             extract_success = extract_extra_details_on_receipt(current_page, link_text)
                    
        #             # Close the receipt tab if it was opened in a new tab
        #             if current_page != original_page:
        #                 current_page.close()
        #                 original_page.bring_to_front()
        #                 page = original_page  # Reset page reference
                    
        #             # If we navigated in the same tab, go back to the main table
        #             elif i < receipt_count - 1:  # Don't go back after the last one
        #                 try:
        #                     page.go_back()
        #                     page.wait_for_load_state("networkidle", timeout=10000)
        #                     # Re-locate elements after navigation
        #                     receipt_links = page.locator("span.receipt-link")
        #                     print(f"[INFO] Navigated back to main table")
        #                 except Exception as nav_error:
        #                     print(f"[WARN] Could not navigate back: {nav_error}")
                    
        #             # Wait a bit before processing next link
        #             if i < receipt_count - 1:
        #                 time.sleep(1)
                    
        #         except Exception as e:
        #             print(f"[WARN] Failed to process link at position {i}: {e}")
        #             # Try to recover and continue
        #             try:
        #                 page.bring_to_front()
        #                 receipt_links = page.locator("span.receipt-link")
        #             except:
        #                 pass
        #             continue
            
        #     print(f"[INFO] Successfully processed {receipt_count - start_index} receipts from position {start_index}")
                
        # except Exception as e:
        #     print(f"[ERROR] Failed to locate or process receipt links: {e}")
        #     traceback.print_exc()
        #     return None, None

    except Exception as exc:
        print(f"[ERROR] Table extraction failed: {exc}")
        traceback.print_exc()
        return None, None
    
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

def process_detailed_receipt(page: Page, receipt_no: str, transaction_type: str = 'float'):
    try:
        # Wait for the detailed view
        page.wait_for_selector("//div[contains(@class, 'portal-collapse-content')]", timeout=15000)
        
        # Get HTML
        detailed_html = page.inner_html(selector="//div[contains(@class, 'portal-collapse-content')]")
        
        # Save for debugging
        with open(f"detailed_{receipt_no}.html", "w", encoding="utf-8") as f:
            f.write(detailed_html)
        
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
    df.to_excel(f"{business_shortcode}_{transaction_type}.xlsx", index=False)
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
        
        with open(f"transaction_{receipt_no}.html","w+",encoding="utf8") as f:
            f.write(soup.prettify())
        
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
            send_session_timeout_email("martinmaati31@gmail.com")
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
    # try:
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

    # except Exception as e:
    #     print(f"[ERROR] process_float_account_details failed: {e}")
    #     page.screenshot(path="float_error.png")
    #     return False

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

def _get_total_months_by_shortcode_shortfall(business_shortcode:str,till_scraping_shortfall: Dict) -> tuple:
    """
    Calculate the number of months to scrape based on shortfall
    """
    if not till_scraping_shortfall:
        return 6,180
    
    if business_shortcode not in  till_scraping_shortfall.keys():
        return 6,180
    
    # Get the maximum number of days since last scrape
    days = float(till_scraping_shortfall[business_shortcode][0])

    return np.ceil(days/30).astype(int), days

# Main function to scrape 180 days month by month
def scrape_180_days_monthly(page:Page, business_short_code:int=0, pass_value:str="",additional_category=None) -> tuple:
    """
    Scrape data for the last 180 days, divided into 6 monthly chunks
    """
    all_data = []
    
    success_value_ : bool = False
            
    # 180 days divided into 6 chunks of 30 days each
    # if pass value is second, we need to refresh the till_scraping_shortfall
    total_months,days = None,None
    if(pass_value == "second"):
        till_scraping_shortfall_ = transaction_service.get_last_scraped_per_shortcode()
        total_months,days = _get_total_months_by_shortcode_shortfall(str(business_short_code),till_scraping_shortfall_)
    else:
        total_months,days = _get_total_months_by_shortcode_shortfall(str(business_short_code),till_scraping_shortfall)
    print(f"The pass value is {pass_value} and the days spent are {days}")
    if(days==0 and pass_value =="first"):
        return pd.DataFrame(),True
    elif days == 0 and pass_value == "second" and additional_category == "float":
        df, success_value = save_table_to_dataframe_latest_(
                    page,
                    business_shortcode=business_short_code,
                    pass_value=pass_value,
                    additional_category=additional_category
                )
    for month_offset in range(total_months):
        close_irritative_dialog_box(page)
        print(f"\n{'='*60}")
        print(f"Scraping month chunk {month_offset+1}/{total_months}")
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
        
        print("Saving data for this period to dataframe...")
        
        # Get data for this period
        try:
            if pass_value == "first" and additional_category == "float":
                if not does_transaction_exist_for_period_(page=page):
                    continue
                df, success_value = save_table_to_dataframe_latest_(
                    page, 
                    business_shortcode=business_short_code,
                    pass_value=pass_value,
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

def navigate_to_review_transaction(page) -> bool:
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

def select_pagination_size(page: Page, down_presses: int = 3, timeout: int = 8000) -> bool:
    """
    Opens the page size dropdown in Element Plus table pagination and selects
    an option by pressing down arrow the specified number of times + Enter.
    
    Most common use-case: down_presses=4 usually selects "50" if default is 10
    
    Returns:
        bool: True if operation succeeded, False otherwise
    """
    try:
        # 1. Locate the dropdown arrow button
        dropdown_arrow = page.locator(
            "//span[@class='el-pagination__sizes']//i[contains(@class, 'el-select__caret')]"
        )

        # Make sure it's visible
        dropdown_arrow.wait_for(state="visible", timeout=timeout)

        # 2. Click to open dropdown
        dropdown_arrow.click()

        # Small delay - Element Plus animation is sometimes a bit slow
        page.wait_for_timeout(300)

        # 3. Press down arrow multiple times
        for _ in range(down_presses):
            page.keyboard.press("ArrowDown")
            time.sleep(0.2)   # small delay between keypresses

        time.sleep(1)
        # 4. Confirm selection
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")

        # Optional: wait a tiny bit for UI to settle

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
    time.sleep(2)
    all_shortcodes = extract_all_business_short_codes(page,all_shortcodes_)
    print(f"[INFO] Extracted {len(all_shortcodes)} business short codes on all pages")
    
    priority_short_codes = _get_priority_shortcodes_(all_shortcodes)
    print(f"[INFO] {len(priority_short_codes)} priority short codes identified for processing")
    
    while go_previous_on_organisation(page):
        pass # Go back to first page

    while True:
        print("\n[INFO] Starting new pagination page...")

        wait_for_table_load(page)

        total_in_list = get_total_from_pagination(page)
        if total_in_list == 0:
            print("[INFO] No organizations found.")
            break

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
            # get into the second pass
        else:
            print("[ERROR] Some organizations still failed after retries.")

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
            
    # while processed_on_page < visible_rows_size:

    for row in visible_rows:
        if processed_on_page >= 10:
            break

        # I will think about this later
        business_short_code = extract_business_short_code(row)
        if not business_short_code or str(business_short_code) not in priority_short_codes:
            print(f"[INFO] Skipping row {business_short_code} as it's not a priority shortcode.")
            processed_on_page += 1
            continue

        row.click(timeout=15000)
        page.wait_for_timeout(1000)

        success = process_single_row(page, business_short_code, total_processed_so_far + processed_on_page + 1,pass_value=pass_value)

        if success:
            print(f"[SUCCESS] Completed row {total_processed_so_far + processed_on_page + 1}")
            # return_to_organization_list(page)
            
        else:
            to_be_rerun.append(business_short_code)
            return_to_organization_list(page)
            print(f"[WARN] Row {business_short_code} failed, added to rerun list")

        # processed_on_page += 1
        # time.sleep(1)

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

        # Navigate and process float/commission
        if not navigate_to_review_transaction(page):
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
