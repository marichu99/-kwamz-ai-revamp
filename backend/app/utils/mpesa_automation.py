from playwright.sync_api import sync_playwright,Page,Locator,Download, TimeoutError as PlaywrightTimeoutError
from flask import current_app
from app.utils.script import fill_login_form, capture_and_solve_captcha
from app.service.transaction_service import TransactionService
# from script import fill_login_form, capture_and_solve_captcha
from PIL import Image, ImageFilter, ImageOps
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import re
import base64
import os
import time
import random
import traceback


transaction_service = TransactionService()
company_shortcode = None

# Load environment variables
load_dotenv()

def login_to_mpesa(password: str = None, username: str = None, short_code: str = None) -> None:
    global company_shortcode
    password = password or os.getenv("AGENT_COMPANY_PASSWORD")
    username = username or os.getenv("AGENT_COMPANY_USERNAME")
    short_code = short_code or os.getenv("AGENT_COMPANY_SHORTCODE")
    company_shortcode = short_code
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

def save_table_to_dataframe_(page: Page, business_shortcode: int,category:str) -> tuple:
    """Extract all rows from paginated table and save to CSV."""
    try:
        print("[INFO] Starting table extraction...")

        page_no = 1
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
        
        exit(0)

    except Exception as exc:
        print(f"[ERROR] Table extraction failed: {exc}")
        traceback.print_exc()
        return None, None

# def save_table_to_dataframe_download(page: Page, max_wait: int = 30_000):
#     print("[EXPORT] Starting Excel export...")

#     # 1. Find the export button (more resilient selector)
#     export_trigger = page.locator("div.el-dropdown.padding-export >> span").first
#     export_trigger.wait_for(state="visible", timeout=max_wait)
#     export_trigger.scroll_into_view_if_needed()

#     # 2. Force hover + small delay to let Vue react
#     export_trigger.hover(force=True, timeout=10_000)
#     print("[EXPORT] Hovered successfully")

#     # THIS IS THE KEY FIX:
#     # Instead of waiting for the <ul> to be "visible", wait for it to have a client rectangle (i.e. positioned)
#     # page.wait_for_function("() => !!document.querySelector('ul.el-dropdown-menu[style*=\"display: block\"]') || !!document.querySelector('ul.el-dropdown-menu[x-placement]')", timeout=10000)

#     print("[EXPORT] Dropdown menu is actually open and positioned")
#     time.sleep(5)

#     # 3. Now safely find the 3rd Excel item
#     excel_items = page.get_by_role("menuitem", name="Excel", exact=True)
#     excel_count = excel_items.count()
#     print(f"[EXPORT] Found {excel_count} Excel options")
    
#     if(int(excel_count)>0):
#         try:
#             excel_items[-1].click()
#         except Exception as e:
#             print(f"We hit a snag {str(e)}")
#             exit(0)

#     if excel_count < 3:
#         # Fallback: list all menu items with text
#         items = page.locator("ul.el-dropdown-menu >> li.el-dropdown-menu__item").all()
#         excel_items = [item for item in items if item.inner_text().strip() == "Excel"]
#         if len(excel_items) < 3:
#             raise Exception(f"Only found {len(excel_items)} Excel items, expected at least 3")

#     target_excel = excel_items.nth(2) if excel_count >= 3 else excel_items[2]
#     target_excel.scroll_into_view_if_needed()

#     # 4. Click with expect_download
#     with page.expect_download(timeout=60_000) as download_info:
#         # Try normal click first
#         try:
#             target_excel.click(timeout=15_000)
#         except:
#             # Final fallback: click via JavaScript (bypasses visibility checks)
#             print("[EXPORT] Using JS click as last resort...")
#             target_excel.evaluate("node => node.click()")

#     download = download_info.value
#     filename = f"float_export_{int(time.time())}.xlsx"
#     download_path = f"./downloads/{filename}"
#     download.save_as(download_path)
#     print(f"[SUCCESS] Excel saved: {download_path}")

#     df = pd.read_excel(download_path)
#     return df, df.columns

def save_table_to_dataframe_download(page: Page,business_shortcode:int,additional_category:str="") -> tuple:
    print("[EXPORT] Starting Excel export...")

    export_trigger = page.locator("div.el-dropdown.padding-export >> span").first
    export_trigger.wait_for(state="visible", timeout=30000)
    export_trigger.scroll_into_view_if_needed()

    export_trigger.hover(force=True, timeout=10_000)
    print("[EXPORT] Hovered successfully")
    time.sleep(2)  

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
        timeout=20_000
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
    
    df,columns = update_transactions_from_file(
        file_path=temp_path,
        business_shortcode=business_shortcode,
        transaction_type=additional_category,
        company_shortcode=company_shortcode,
        agent_id=None
    )

    print(f"[SUCCESS] Loaded DataFrame in-memory: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"   Columns: {list(df.columns)}")
    # exit(0)

    return df, columns

# Example of direct usage
def update_transactions_from_file(file_path, business_shortcode, transaction_type, company_shortcode, agent_id):
    """
    Update transactions directly from a file
    """
    
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
    
    if results.get('success', False):
        summary = results.get('summary', {})
        print(f"\n✅ Success!")
        print(f"   Updated: {summary.get('updated_count', 0)}")
        print(f"   Created: {summary.get('created_count', 0)}")
        print(f"   Total: {summary.get('total_processed', 0)}")
        print(f"   Success rate: {summary.get('success_rate', 0):.1f}%")
    else:
        print(f"\n❌ Failed: {results.get('error', 'Unknown error')}")
    
    # Save the processed file
    df.to_excel(f"{business_shortcode}_{transaction_type}.xlsx", index=False)
    print(f"💾 Saved to: {business_shortcode}_{transaction_type}.xlsx")
    
    return df, df.columns

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

def map_scraped_data_to_agent_company(scraped_data: dict, user_id: int = None) -> dict:
    """
    Map scraped data to AgentCompany model fields
    """
    mapped_data = {
        'company_name': scraped_data.get('organization_name'),
        'registration_number': f"SCRAPED-{scraped_data.get('short_code', 'UNKNOWN')}",
        'location': scraped_data.get('location', 'Unknown'),
        'identity_model': scraped_data.get('identity_model'),
        'hierarchy_level': scraped_data.get('hierarchy_level'),
        'top_organization': scraped_data.get('top_organization'),
        'organization_name': scraped_data.get('organization_name'),
        'short_code': scraped_data.get('short_code'),
        'identity_status': scraped_data.get('identity_status'),
        'segment': scraped_data.get('segment'),
        'charge_profile': scraped_data.get('charge_profile'),
        'rule_profile': scraped_data.get('rule_profile'),
        'trust_level': scraped_data.get('trust_level'),
        'data_source': 'portal',
        'is_verified': False,
        'user_id': user_id
    }
    
    # Handle registration date
    reg_date = scraped_data.get('registration_date')
    if reg_date:
        mapped_data['registration_date'] = parse_date_string(reg_date)
        mapped_data['established_date'] = parse_date_string(reg_date)
    
    # Handle parent short code (will be linked to company later)
    parent_short_code = scraped_data.get('parent_short_code')
    if parent_short_code:
        mapped_data['parent_short_code'] = parent_short_code
    
    return mapped_data

def scrape_till_details(page: Page, business_short_code: int, user_id: int = None) -> dict:
    """
    Scrape till details and return processed data
    """
    try:
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
        for key, value in till_info.items():
            print(f"  {key}: {value}")
        
        # Map to AgentCompany fields
        mapped_data = map_scraped_data_to_agent_company(till_info, user_id)
        
        return {
            'success': True,
            'scraped_data': till_info,
            'mapped_data': mapped_data,
            'business_short_code': business_short_code
        }
        
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
        return True
    except Exception as e:
        print(f"Error clicking receipt link: {e}")
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
    # exit(0) 
    
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
            time.sleep(2)
            return  False  # Continue processing
        else:
            print(f"[INFO] Next page disabled. Finished all {row_count} rows on last page.")
            return  False

    except Exception as e:
        print(f"[WARNING] Error clicking next page: {e}")
        page.screenshot(path="pagination_error.png")
        return False
        
def go_previous_on_organisation(page: Page, row_count: int):
    """
    Clicks 'Next Page' if available. Returns True/False indicating if more pages exist.
    """
    prev_page_btn = page.locator("//button[@aria-label='Go to previous page']").first

    try:
        if prev_page_btn.is_enabled():
            print("[INFO] Clicking 'Previous Page' button...")
            prev_page_btn.click()
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)
            return None  # Continue processing
        else:
            print(f"[INFO] Previous page disabled. Finished all {row_count} rows on last page.")
            return row_count, False

    except Exception as e:
        print(f"[WARNING] Error clicking previous page: {e}")
        page.screenshot(path="pagination_error.png")
        return row_count, False
    
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
                if not row.is_visible(timeout=2000):
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

                        time.sleep(1.5)

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

def process_float_account_details(page: Page, business_short_code: int, pass_value: str) -> tuple:
    # try:
        print("[INFO] Processing Float Account Details")

        # Step 1: Select Float Account (usually 2nd or 3rd option)
        if not select_account_dropdown(page, "Float Account", arrow_down_count=2):
            return "dropdown",False
        
        print("We are checking whether a till is frozen or not")        
        if is_till_frozen(page):
            return "frozen",False

        print(f"This is the date and time selection")
        # Step 2: Set Start Time = 1st day of current month
        select_dates_and_submit_(page)

        time.sleep(4)  # Wait for table to load

        print("We are trying to save to the dataframe")
        # df, headers = save_table_to_dataframe_download(page, row_index=business_short_code, category="float")
        if(pass_value=="first"):
            df, headers = save_table_to_dataframe_download(page,business_shortcode=business_short_code,additional_category="float")
        else:
            df, headers = save_table_to_dataframe_(page,business_shortcode=business_short_code,category=pass_value)
        if df is not None:
            print("[SUCCESS] Float table extracted")
            return "dataframe",True
        else:
            print("[ERROR] Failed to extract float table")
            return "dataframe",False

    # except Exception as e:
    #     print(f"[ERROR] process_float_account_details failed: {e}")
    #     page.screenshot(path="float_error.png")
    #     return False

def process_commission_account_details(page: Page, business_short_code: int, pass_value: str) -> bool:
    try:
        print("[INFO] Processing Commission Account Details")
        scroll_to_top(page)
        time.sleep(1)

        # Step 1: Select Commission Account (usually 5th+ option)
        if not select_account_dropdown(page, "Commission Account", arrow_down_count=3):
            return False

        # Step 2: Click the Query/Search button
        query_button = page.locator("//div[@class='section-content']//button").first
        query_button.wait_for(state="visible", timeout=10000)
        query_button.click(force=True)
        print("[INFO] Query button clicked")

        time.sleep(4)

        # df, headers = save_table_to_dataframe_download(page, row_index=business_short_code, category="commission")
        if(pass_value=="first"):
            df, headers = save_table_to_dataframe_download(page,business_shortcode=business_short_code,additional_category="commission")
        else:
            df, headers = save_table_to_dataframe_(page,business_shortcode=business_short_code,additional_category=pass_value)
        if df is not None:
            print("[SUCCESS] Commission table extracted")
            return True
        else:
            print("[ERROR] Failed to extract commission table")
            return False

    except Exception as e:
        print(f"[ERROR] process_commission_account_details failed: {e}")
        page.screenshot(path="commission_error.png")
        return False

def process_float_commission(page: Page, business_short_code: int, pass_value: str) -> bool:
    """Main function – processes both float and commission sequentially"""
    
    trials = 3
    
    proc_type, success = process_float_account_details(page, business_short_code,pass_value)
    print(f"[DEBUG] Float Account processing result: {proc_type}, success: {success}")
    if not success and proc_type != "frozen":
        close_irritative_dialog_box(page)
        print(f"[ERROR] Failed at Float Account step {business_short_code} - Retrying...")
        while trials > 0:
            trials -= 1
            print(f"[INFO] Retrying Float Account step {business_short_code} ({3 - trials} attempts left)...")
            proc_type_inner, success_inner = process_float_account_details(page, business_short_code,pass_value)
            if success_inner:
                print("[SUCCESS] Float Account step completed")
                break
            time.sleep(2)  # Wait before retrying
        else:
            print("[ERROR] All retries failed for Float Account step")
            return False
        return False
    elif not success and proc_type == "frozen":
        print(f"[INFO] Till is frozen for business {business_short_code}, skipping further processing.")
        return False
        

    # Small pause to let page stabilize
    time.sleep(2)

    if not process_commission_account_details(page, business_short_code,pass_value):
        print(f"[ERROR] Failed at Commission Account step {business_short_code} - Retrying...")
        close_irritative_dialog_box(page)
        while trials > 0:
            trials -= 1
            print(f"[INFO] Retrying Commission Account step {business_short_code} ({3 - trials} attempts left)...")
            if process_commission_account_details(page, business_short_code,pass_value):
                print("[SUCCESS] Commission Account step completed")
                break
            time.sleep(2)  # Wait before retrying
        else:
            print("[ERROR] All retries failed for Commission Account step") 
            
        return False

    print(f"[SUCCESS] Completed processing business {business_short_code}")
    return True

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
            time.sleep(2)  # Wait for page to load results
        except Exception as e:
            print(f"[ERROR] Could not complete Tab/Enter submission: {e}")
            traceback.print_exc()
            return False

# def process_float_account_details(page: Page,business_short_code: int):
#     """
#     Processes the float account details page:
#     1. Finds the Start Time date picker input (first date picker)
#     2. Finds the End Time date picker input (second date picker)
#     3. Fills Start Time with first day of current month
#     4. Presses Tab three times and Enter to submit
#     5. Saves page content to output/float_details.html
    
#     Args:
#         page: Playwright page object
    
#     Returns:
#         bool: True if successful, False otherwise
#     """
#     try:
#         print("[INFO] Processing float account details...")
        
#         # Click dropdown
#         dropdown_icon = page.locator(
#             "//div[@class='el-form-item is-required asterisk-left el-form-item--label-top none-margin-bottom']//div[@class='el-select__selection']"
#         ).first
#         # dropdown_icon.click()
        
#         if dropdown_icon.is_visible():
#             dropdown_icon.click()
#             print("[INFO] Dropdown clicked, waiting for options...")
        
#             # time.sleep(1)
            
#             for _ in range(2):
#                 page.keyboard.press("ArrowDown")
#                 time.sleep(0.3)
            
#             page.keyboard.press("Enter")

        
#         # Step 1 & 2: Find date picker inputs using more stable selectors
#         try:
#             # Find the Start Time input (first date picker with placeholder "Start Time")
#             start_time_input = page.wait_for_selector(
#                 "//input[@placeholder='Start Time']", 
#                 timeout=10000
#             )
#             print("[✓] Found Start Time date picker input")
            
#             # Find the End Time input (first date picker with placeholder "End Time")
#             end_time_input = page.wait_for_selector(
#                 "//input[@placeholder='End Time']", 
#                 timeout=10000
#             )
#             print("[✓] Found End Time date picker input")
            
#         except Exception as e:
#             print(f"[ERROR] Could not find date picker inputs: {e}")
            
#             # Fallback: Try finding by class and position
#             try:
#                 print("[INFO] Trying fallback selector for date pickers...")
#                 date_inputs = page.query_selector_all(
#                     "//div[@class='el-date-editor']//input[@class='el-input__inner']"
#                 )
#                 if len(date_inputs) >= 2:
#                     start_time_input = date_inputs[0]
#                     end_time_input = date_inputs[1]
#                     print(f"[✓] Found {len(date_inputs)} date picker inputs using fallback")
#                 else:
#                     print(f"[ERROR] Expected at least 2 date inputs, found {len(date_inputs)}")
#                     return False
#             except Exception as fallback_error:
#                 print(f"[ERROR] Fallback selector also failed: {fallback_error}")
#                 return False
        
#         # Step 3: Fill Start Time with first day of current month in dd/MM/yyyy format
#         try:
#             #first_day = datetime.now().replace(day=1).strftime("%d/%m/%Y")            
#             # Click the Start Time input to focus
#             start_time_input.click()
            
#             print(f"We have just clicked the start time")
#             previous_month_icon = page.wait_for_selector(
#                 "//div[@actualvisible='true']//button[@aria-label='Previous Month']", 
#                 timeout=5000
#             )
            
#             for i in range(3):
#                 previous_month_icon.click() 
            
#             print("The previous button has been clicked thrice .......")
            
#             for i in range(5):
#                 page.keyboard.press("Tab")
#                 print("Tab pressed")
            
#             page.keyboard.press("Enter")
            
#         except Exception as e:
#             print(f"[ERROR] Could not fill Start Time input: {e}")
#             return False
        
#         # Step 4: Press Tab three times and Enter to submit
#         try:
#             print("[INFO] Pressing Tab three times and Enter to submit...")
            
#             # Ensure Start Time input has focus
#             start_time_input.focus()
#             page.wait_for_timeout(500)
            
#             # Debug: Check current focused element
#             focused_element = page.evaluate_handle("() => document.activeElement")
#             focused_tag = page.evaluate("(elem) => elem.tagName", focused_element)
#             focused_id = page.evaluate("(elem) => elem.id || elem.placeholder || 'no-id'", focused_element)
#             print(f"[DEBUG] Current focused element: {focused_tag} (ID/Placeholder: {focused_id})")
            
#             # Press Tab three times
#             for i in range(4):
#                 page.keyboard.press("Tab")
#                 page.wait_for_timeout(500)
#                 # Debug: Check focused element after each Tab
#                 focused_element = page.evaluate_handle("() => document.activeElement")
#                 focused_tag = page.evaluate("(elem) => elem.tagName", focused_element)
#                 focused_id = page.evaluate("(elem) => elem.id || elem.placeholder || 'no-id'", focused_element)
#                 print(f"[DEBUG] After Tab {i+1}, focused element: {focused_tag} (ID/Placeholder: {focused_id})")
            
#             # Press Enter to submit
#             page.keyboard.press("Enter")
#             print("[✓] Pressed Enter to submit form")
#             # page.wait_for_timeout(3000)  # Wait for page to load results
#             time.sleep(2)  # Wait for page to load results
            
#             df,headers = save_table_to_dataframe_download(page,business_short_code)
            
#             if df is not None:
#                 print("[INFO] Table extracted after submission.")
#                 return True
#             else:
#                 print("[ERROR] Table extraction failed after submission.")
#                 return False
            
#         except Exception as e:
#             print(f"[ERROR] Could not complete Tab/Enter submission: {e}")
#             import traceback
#             traceback.print_exc()
#             return False
        
#     except Exception as exc:
#         print(f"[ERROR] process_float_account_details failed: {exc}")
#         import traceback
#         traceback.print_exc()
#         return False

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

    
def close_irritative_dialog_box(page):
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

    while True:
        print("\n[INFO] Starting new pagination page...")

        wait_for_table_load(page)

        total_in_list = get_total_from_pagination(page)
        if total_in_list == 0:
            print("[INFO] No organizations found.")
            break

        print(f"[INFO] This page shows {total_in_list} organizations")

        processed_on_this_page = process_page_rows(
            page=page,
            total_in_list=total_in_list,
            total_processed_so_far=total_processed,
            to_be_rerun=to_be_rerun
        )

        total_processed += processed_on_this_page

        if total_processed >= total_in_list and len(to_be_rerun) == 0:
            print(f"[SUCCESS] All {total_processed} organizations processed successfully!")
            break

        # Move to next pagination page
        if not go_forth_on_organization(page, total_in_list):
            print("[INFO] No more pages or navigation failed.")
            break

        time.sleep(2)  # Gentle pause between pages

    if to_be_rerun:
        print(f"[WARN] {len(to_be_rerun)} organizations failed and need reprocessing: {to_be_rerun}")
        if rerun_failed_codes(page, to_be_rerun):
            print("[SUCCESS] All failed organizations reprocessed successfully!")
            # get into the second pass
        else:
            print("[ERROR] Some organizations still failed after retries.")


def wait_for_table_load(page: Page, timeout: int = 15000) -> None:
    """Wait for network idle and allow lazy loading."""
    page.wait_for_load_state("networkidle", timeout=timeout)
    time.sleep(2)


def process_page_rows(
    page: Page,
    total_in_list: int,
    total_processed_so_far: int,
    to_be_rerun: list[int]
) -> int:
    """Process all visible rows on the current page with virtual scrolling support."""
    processed_on_page = 0
    rows_locator = page.locator("//tbody//tr[@class='el-table__row childTableRow']")

    while processed_on_page < total_in_list:
        visible_rows = get_visible_rows(rows_locator)
        
        if not visible_rows:
            print("[INFO] No visible rows — scrolling to load more...")
            page.mouse.wheel(0, 1200)
            time.sleep(2)
            continue

        print(f"[INFO] Found {len(visible_rows)} visible rows to process")

        for row in visible_rows:
            if processed_on_page >= total_in_list:
                break

            business_short_code = extract_business_short_code(row)
            if not business_short_code:
                processed_on_page += 1
                continue

            row.click(timeout=15000)
            page.wait_for_timeout(1000)

            success = process_single_row(page, business_short_code, total_processed_so_far + processed_on_page + 1)

            if success:
                print(f"[SUCCESS] Completed row {total_processed_so_far + processed_on_page + 1}")
                return_to_organization_list(page)
                
            else:
                to_be_rerun.append(business_short_code)
                return_to_organization_list(page)
                print(f"[WARN] Row {business_short_code} failed, added to rerun list")

            processed_on_page += 1
            time.sleep(1)

        # Scroll to load more rows if needed
        if processed_on_page < total_in_list:
            page.mouse.wheel(0, 1200)
            time.sleep(2)

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


def process_single_row(page: Page, business_short_code: int, row_number: int) -> bool:
    """Process one organization row end-to-end."""
    try:
        print(f"\n[SUCCESS] Processing Row {row_number} | Business Code: {business_short_code}")

        # Scrape basic till details
        scrape_till_details(page, business_short_code)

        # Navigate and process float/commission
        if not navigate_to_review_transaction(page):
            print("[ERROR] Failed to navigate to review transaction")
            return_to_organization_list(page)
            return False

        if not process_float_commission(page, business_short_code, pass_value="first"):
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

# if __name__ == "__main__":
#     # solveCaptchaXai()
#     login_to_mpesa()