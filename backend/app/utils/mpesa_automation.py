from playwright.sync_api import sync_playwright,Page, TimeoutError as PlaywrightTimeoutError
from app.utils.script import fill_login_form, capture_and_solve_captcha
#from script import fill_login_form, capture_and_solve_captcha
from PIL import Image, ImageFilter, ImageOps
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import re
import base64
import os
import time
import random
import traceback


# Load environment variables
load_dotenv()

def login_to_mpesa():
    password = os.getenv("AGENT_COMPANY_PASSWORD")
    username = os.getenv("AGENT_COMPANY_USERNAME")
    short_code = os.getenv("AGENT_COMPANY_SHORTCODE")
    url = "https://org.ke.m-pesa.com/#/login?service=https%3A%2F%2Forg.ke.m-pesa.com%2Forgportal%2Fv1%2Fsso%2Fhome"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']  # Use --start-maximized instead
        )
        
        # Create context with no default viewport to use full screen
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        page.goto(url, timeout=600000)
        wait_after_click = 5  # seconds
        # Fill login fields once
        fill_login_form(page, short_code, username, password)
        print("[INFO] Login form filled")

        # Solve captcha initially
        captcha_solution = capture_and_solve_captcha(page)
        print(f"[DEBUG] Initial captcha solution: {captcha_solution}")
        if(len(captcha_solution) > 4):
            svg_element = page.query_selector("//div[@class='img-part']//*[name()='svg']")
            if svg_element:
                svg_element.click()
                print("[INFO] Clicked SVG element to refresh captcha")
                captcha_solution = capture_and_solve_captcha(page)
            else:
                print("[ERROR] SVG element not found")
                last_error = "SVG element not found"
                raise Exception("Failed to locate SVG element for captcha refresh")

        # Fill verification code input and submit
        page.fill("//input[@id='verifyCode']", captcha_solution)
        page.click("//button[@id='loginBtn']")
        print("[INFO] Login button clicked; waiting for response...")

        error_text = "the Verification Code is incorrect or has expired."
        error_text_ = "Must be not greater than 4 characters."
        last_error = None

        try:
            # Wait for either success or error
            start = time.time()
            timeout_seconds = 10
            found_success = False
            found_error = False
            error_message = None

            while time.time() - start < timeout_seconds:
                locator = page.locator(".hlds-error-tip-content")
                error_element = page.query_selector("//div[@class='el-form-item__error']")
                if page.query_selector(f"text={error_text}") or page.query_selector(f"text={error_text_}"):
                    found_error = True
                    error_message = error_text if page.query_selector(f"text={error_text}") else error_text_
                    print(f"[DEBUG] Detected error message: '{error_message}'")
                elif error_element and error_element.is_visible():
                    found_error = True
                    error_message = error_element.inner_text().strip()
                    print(f"[DEBUG] Detected el-form-item__error message: '{error_message}'")
                elif locator.is_visible():
                    found_error = True
                    error_message = locator.inner_text().strip()
                    print(f"[DEBUG] Detected hlds-error-tip-content message: '{error_message}'")
                else:
                    found_success = True
                time.sleep(0.5)

                if found_error or found_success:
                    break

            if found_success:
                print("[INFO] Login appears successful (no error detected).")
            elif found_error:
                print(f"[WARN] Detected error: '{error_message}' — retrying captcha.")
                # Click the SVG element to refresh captcha
                svg_element = page.query_selector("//div[@class='img-part']//*[name()='svg']")
                if svg_element:
                    svg_element.click()
                    print("[INFO] Clicked SVG element to refresh captcha")
                else:
                    print("[ERROR] SVG element not found")
                    last_error = "SVG element not found"
                    raise Exception("Failed to locate SVG element for captcha refresh")

                # Re-solve captcha
                captcha_solution = capture_and_solve_captcha(page)
                print(f"[DEBUG] New captcha solution: {captcha_solution}")

                # Refill captcha input
                page.fill("//input[@id='verifyCode']", captcha_solution)
                page.click("//button[@id='loginBtn']")
                print("[INFO] Login button clicked again after captcha refresh")

                # Check for errors again
                start = time.time()
                found_success = False
                found_error = False
                while time.time() - start < timeout_seconds:
                    locator = page.locator(".hlds-error-tip-content")
                    error_element = page.query_selector("//div[@class='el-form-item__error']")
                    if page.query_selector(f"text={error_text}") or page.query_selector(f"text={error_text_}"):
                        found_error = True
                        error_message = error_text if page.query_selector(f"text={error_text}") else error_text_
                        print(f"[DEBUG] Detected error message after retry: '{error_message}'")
                    elif error_element and error_element.is_visible():
                        found_error = True
                        error_message = error_element.inner_text().strip()
                        print(f"[DEBUG] Detected el-form-item__error message after retry: '{error_message}'")
                    elif locator.is_visible():
                        found_error = True
                        error_message = locator.inner_text().strip()
                        print(f"[DEBUG] Detected hlds-error-tip-content message after retry: '{error_message}'")
                    else:
                        found_success = True
                    time.sleep(0.5)

                if found_success:
                    print("[INFO] Login successful after captcha retry")
                else:
                    last_error = error_message
                    print(f"[ERROR] Login failed after retry: '{error_message}'")

            # Wait for navigation or further page load
            try:
                page.wait_for_timeout(wait_after_click * 1000)
            except PlaywrightTimeoutError:
                pass

        except Exception as exc:
            last_error = str(exc)
            print(f"[ERROR] Exception during login process: {exc}")

        # Save page content
        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        with open("login.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        if last_error:
            print(f"[RESULT] Login process completed. Last error: {last_error}")
        else:
            print("[RESULT] Login likely successful and HTML saved to login.html")

        print("[INFO] Navigating to child organization page...")
        navigate_to_child_organization(page)

        print("[INFO] Browser will remain open for inspection. Press ENTER to close.")
        # input()

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
    page.wait_for_timeout(1500)


    print("[INFO] Browser will remain open for inspection. Press ENTER to continue.")
    process_organization_rows(page)
    #input()

def select_first_float_option_by_index(page, parent_xpath: str = None):
    """
    Selects the first 'float' option from a dropdown.
    
    Args:
        page: Playwright page object
        parent_xpath: Optional XPath to the parent container. If None, searches globally.
    """
    try:
        print(f"[INFO] Looking for Float Account option...")
        
        # Wait for the dropdown menu to appear after clicking the dropdown icon
        page.wait_for_timeout(1500)
        
        # Pattern to match "Float Account/" followed by any digits
        float_pattern = re.compile(r'Float Account/\d+', re.IGNORECASE)
        
        # Get all dropdown options
        all_options = page.query_selector_all("//ul[contains(@class, 'el-select-dropdown__list')]//li")
        print(f"[DEBUG] Found {len(all_options)} total options, searching for Float Account pattern...")
        
        # Search through all options and find the first match
        for i, opt in enumerate(all_options, 1):
            try:
                opt_text = opt.inner_text().strip()
                
                # Check if the option matches the Float Account pattern
                if float_pattern.search(opt_text):
                    print(f"[INFO] Option {i}: {opt_text} *** MATCH ***")
                    print(f"[INFO] Clicking first Float Account option: {opt_text}")
                    opt.click()
                    print("[SUCCESS] Selected Float Account option.")
                    page.wait_for_timeout(1000)
                    return True
                else:
                    # Optional: print non-matching options for debugging
                    # print(f"[DEBUG] Option {i}: {opt_text}")
                    pass
            except Exception as e:
                print(f"[WARN] Error reading option {i}: {e}")
                continue
        
        # If no match found, print all options for debugging
        print("[ERROR] No Float Account option found matching pattern 'Float Account/XXXXX'")
        print("[DEBUG] All available options:")
        for i, opt in enumerate(all_options, 1):
            try:
                opt_text = opt.inner_text().strip()
                print(f"  Option {i}: {opt_text}")
            except:
                pass
        return False
    except Exception as exc:
        print(f"[ERROR] Function failed: {exc}")
        import traceback
        traceback.print_exc()
        return False

def scroll_to_bottom(page: Page) -> None:
    """
    Scrolls to the bottom of the page.
    
    Args:
        page: Playwright Page object
    """
    time.sleep(3)  # Wait for page to settle before scrolling
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)
        print("[SUCCESS] Scrolled to bottom of page")
    except Exception as e:
        print(f"[ERROR] Failed to scroll to bottom: {e}")

def save_table_to_dataframe(page: Page, row_index: int) -> tuple[pd.DataFrame, list]:
    """
    Extracts **all** rows from a paginated Element-UI table.
    """
    try:
        print("[INFO] Starting full table extraction...")

        headers = []
        all_data_rows = []

        # ------------------- SELECTORS -------------------
        header_selector = (
            "//div[contains(@class,'el-table--fit') and contains(@class,'is-scrolling-none')]"
            "//table[@class='el-table__header']"
        )
        table_selector = (
            "//div[contains(@class,'el-table--fit') and contains(@class,'is-scrolling-none')]"
            "//table[@class='el-table__body']"
        )
        next_btn_xpath = "//button[@aria-label='Go to next page']"

        # ------------------- HEADERS -------------------
        page.wait_for_load_state("networkidle", timeout=10_000)
        header_tbl = page.wait_for_selector(header_selector, timeout=10_000)
        if not header_tbl or not header_tbl.is_visible():
            print("[ERROR] Header table not found.")
            return None, None

        soup = BeautifulSoup(header_tbl.inner_html(), "html.parser")
        tr = soup.find("thead").find("tr")
        headers = [th.get_text(strip=True) for th in tr.find_all("th")]
        if not headers:
            print("[ERROR] No header cells.")
            return None, None
        print(f"[SUCCESS] Headers ({len(headers)}): {headers}")

        # ------------------- PAGINATION LOOP -------------------
        page_no = 1
        while True:
            print(f"\n[INFO] --- Page {page_no} ---")

            # ---- wait for body table ----
            page.wait_for_load_state("networkidle", timeout=10_000)
            body_tbl = page.wait_for_selector(table_selector, timeout=10_000)
            if not body_tbl:
                print("[WARN] Body table missing – probably 'No Data'.")
                break
            if not body_tbl.is_visible():
                print("[ERROR] Body table not visible.")
                break
            print("[SUCCESS] Body table ready.")

            # ---- extract rows ----
            soup = BeautifulSoup(body_tbl.inner_html(), "html.parser")
            tbody = soup.find("tbody")
            page_has_rows = False

            if tbody:
                for tr in tbody.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(cells) == len(headers):
                        all_data_rows.append([row_index] + cells)
                        page_has_rows = True
                    else:
                        print(f"[WARN] Row skipped – {len(cells)} cells (expected {len(headers)})")
                print(f"[SUCCESS] {len(tbody.find_all('tr'))} rows from page {page_no}")
            else:
                print("[WARN] No <tbody> – empty page.")
                if page_no == 1 and "no data" in body_tbl.inner_html().lower():
                    print("[WARN] Table shows 'No Data'.")

            # ---- NEXT-PAGE BUTTON ----
            next_btn = page.locator(f"xpath={next_btn_xpath}").first

            # 1. scroll into view (makes hidden pagination visible)
            try:
                next_btn.scroll_into_view_if_needed(timeout=5_000)
            except Exception as e:
                print(f"[WARN] Scroll failed: {e}")

            # 2. check visibility + enabled state
            try:
                visible = next_btn.is_visible()      # no timeout argument
                enabled = not next_btn.is_disabled()  # no timeout argument
            except Exception as e:
                print(f"[WARN] Visibility check failed: {e}")
                visible = enabled = False

            if visible and enabled:
                print("[ACTION] Clicking next page...")
                next_btn.click()
                page.wait_for_load_state("networkidle", timeout=15_000)
                page_no += 1
                continue          # go to next iteration
            else:
                print("[INFO] Next button missing or disabled → **LAST PAGE**")
                break

        # ------------------- BUILD DATAFRAME -------------------
        if not all_data_rows:
            print("[WARN] No rows collected.")
            df = pd.DataFrame(columns=["OrganizationRowIndex"] + headers)
        else:
            df = pd.DataFrame(all_data_rows, columns=["OrganizationRowIndex"] + headers)
            print(f"[SUCCESS] Total {len(df)} rows from {page_no} page(s)")

        # ------------------- SAVE CSV -------------------
        csv_path = f"row_{row_index}_float_data.csv"
        df.to_csv(csv_path, index=False)
        print(f"[SUCCESS] Saved {csv_path}")

        return df, headers

    except Exception as exc:
        print(f"[FATAL] {exc}")
        traceback.print_exc()
        return None, None


def save_table_to_dataframe_(page: Page, row_index: int) -> tuple[pd.DataFrame, list]:
    """
    Extracts **all** rows from a paginated Element-UI table.
    Selects pagination size by clicking the dropdown, pressing down arrow 4 times, and pressing enter.
    Reads table data, navigates to the next page if clickable, and saves results to a CSV.
    """
    try:
        print("[INFO] Starting full table extraction...")

        headers = []
        all_data_rows = []

        # ------------------- SELECTORS -------------------
        header_selector = (
            "//div[contains(@class,'el-table--fit') and contains(@class,'is-scrolling-none')]"
            "//table[@class='el-table__header']"
        )
        table_selector = (
            "//div[contains(@class,'el-table--fit') and contains(@class,'is-scrolling-none')]"
            "//table[@class='el-table__body']"
        )
        dropdown_selector = (
            "//span[@class='el-pagination__sizes']//i[@class='el-icon el-select__caret el-select__icon']"
        )
        
        next_btn_xpath = "//button[@aria-label='Go to next page']//i[@class='el-icon']"

        # ------------------- SET PAGINATION SIZE -------------------
        print("[INFO] Setting pagination size...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)  # Wait for page to settle
        page.wait_for_load_state("networkidle", timeout=10_000)
        dropdown = page.wait_for_selector(f"xpath={dropdown_selector}", timeout=10_000)
        if not dropdown or not dropdown.is_visible():
            print("[ERROR] Pagination dropdown not found or not visible.")
            return None, None

        try:
            dropdown.click()
            print("[ACTION] Clicked pagination dropdown.")
            time.sleep(2)  # Wait for dropdown to open
            for _ in range(3):
                page.keyboard.press("ArrowDown")
                time.sleep(0.5)  # Wait for each key press to register
                print("[ACTION] Pressed ArrowDown.")
            page.keyboard.press("Enter")
            print("[ACTION] Pressed Enter to select pagination size.")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
            time.sleep(3)  # Wait for selection to apply
        
            # Save page HTML
            html_content = page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            with open("float_details.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
                
            time.sleep(10)  # Wait for selection to apply
            
        except Exception as e:
            print(f"[ERROR] Failed to set pagination size: {e}")
            return None, None

        # ------------------- HEADERS -------------------
        header_tbl = page.wait_for_selector(header_selector, timeout=10_000)
        if not header_tbl or not header_tbl.is_visible():
            print("[ERROR] Header table not found.")
            return None, None

        soup = BeautifulSoup(header_tbl.inner_html(), "html.parser")
        tr = soup.find("thead").find("tr")
        headers = [th.get_text(strip=True) for th in tr.find_all("th")]
        if not headers:
            print("[ERROR] No header cells.")
            return None, None
        print(f"[SUCCESS] Headers ({len(headers)}): {headers}")

        # ------------------- PAGINATION LOOP -------------------
        page_no = 1
        while True:
            print(f"\n[INFO] --- Page {page_no} ---")

            # ---- wait for body table ----
            page.wait_for_load_state("networkidle", timeout=10_000)
            body_tbl = page.wait_for_selector(table_selector, timeout=10_000)
            if not body_tbl:
                print("[WARN] Body table missing – probably 'No Data'.")
                break
            if not body_tbl.is_visible():
                print("[ERROR] Body table not visible.")
                break
            print("[SUCCESS] Body table ready.")

            # ---- extract rows ----
            soup = BeautifulSoup(body_tbl.inner_html(), "html.parser")
            tbody = soup.find("tbody")
            page_has_rows = False

            if tbody:
                for tr in tbody.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(cells) == len(headers):
                        all_data_rows.append([row_index] + cells)
                        page_has_rows = True
                    else:
                        print(f"[WARN] Row skipped – {len(cells)} cells (expected {len(headers)})")
                print(f"[SUCCESS] {len(tbody.find_all('tr'))} rows from page {page_no}")
            else:
                print("[WARN] No <tbody> – empty page.")
                if page_no == 1 and "no data" in body_tbl.inner_html().lower():
                    print("[WARN] Table shows 'No Data'.")

            # ---- NEXT-PAGE BUTTON ----
            next_btn = page.locator(f"xpath={next_btn_xpath}").first

            # 1. scroll into view
            try:
                next_btn.scroll_into_view_if_needed(timeout=5_000)
            except Exception as e:
                print(f"[WARN] Scroll failed: {e}")

            # 2. check visibility + enabled state
            try:
                visible = next_btn.is_visible()
                enabled = not next_btn.is_disabled()
            except Exception as e:
                print(f"[WARN] Visibility check failed: {e}")
                visible = enabled = False

            if visible and enabled:
                print("[ACTION] Clicking next page icon...")
                next_btn.click()
                page.wait_for_load_state("networkidle", timeout=15_000)
                page_no += 1
                continue
            else:
                print("[INFO] Next page icon missing or disabled → **LAST PAGE**")
                break

        # ------------------- BUILD DATAFRAME -------------------
        if not all_data_rows:
            print("[WARN] No rows collected.")
            df = pd.DataFrame(columns=["OrganizationRowIndex"] + headers)
        else:
            df = pd.DataFrame(all_data_rows, columns=["OrganizationRowIndex"] + headers)
            print(f"[SUCCESS] Total {len(df)} rows from {page_no} page(s)")

        # ------------------- SAVE CSV -------------------
        csv_path = f"row_{row_index}_float_data.csv"
        df.to_csv(csv_path, index=False)
        print(f"[SUCCESS] Saved {csv_path}")

        return df, headers

    except Exception as exc:
        print(f"[FATAL] {exc}")
        traceback.print_exc()
        return None, None
    
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
    
def process_float_account_details(page: Page):
    """
    Processes the float account details page:
    1. Finds the Start Time date picker input (first date picker)
    2. Finds the End Time date picker input (second date picker)
    3. Fills Start Time with first day of current month
    4. Presses Tab three times and Enter to submit
    5. Saves page content to output/float_details.html
    
    Args:
        page: Playwright page object
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("[INFO] Processing float account details...")
        
        # Step 1 & 2: Find date picker inputs using more stable selectors
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
            first_day_q = first_day_of_quarter()
            
            # Click the Start Time input to focus
            #start_time_input.click()
            start_time_icon = page.wait_for_selector(
                "//div[@aria-expanded='true']//div[@class='el-input__wrapper']", 
                timeout=5000
            )
            start_time_icon.click()
            
            # start_time_inner_input = page.wait_for_selector(
            #     "//div[@aria-expanded='true']//i[@class='el-icon el-input__icon']", 
            #     timeout=5000
            # )
                        
            start_time_input = page.locator('input.el-input__inner[placeholder*="Select Date"]').first
            page.wait_for_timeout(500)
            
            # Clear existing value using keyboard shortcuts
            start_time_input.press("Control+A")  # Select all
            page.wait_for_timeout(200)
            start_time_input.press("Backspace")  # Delete
            page.wait_for_timeout(500)
            
            # Type the new date
            start_time_input.type(first_day_q, delay=100)  # Type with delay for stability
            time.sleep(2)  # Wait for typing to complete
            page.keyboard.press("Enter")
            print(f"[✓] Set Start Time to {first_day_q}")
            page.wait_for_timeout(1000)
            click_random_spot(page, padding=50)
            
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
            page.wait_for_timeout(3000)  # Wait for page to load results
            
            save_table_to_dataframe_(page, row_index=1)
            
            # Debug: Verify if submission triggered a change
            if page.query_selector(".el-table__empty-text") or page.query_selector("text=No Data"):
                print("[WARN] Table shows 'No Data' after submission. Form may not have submitted correctly.")
            
        except Exception as e:
            print(f"[ERROR] Could not complete Tab/Enter submission: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 5: Save page content to output/float_details.html
        try:
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            
            os.makedirs("output", exist_ok=True)
            with open("output/float_details.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            
            print("[✅] Saved page content to output/float_details.html")
        except Exception as e:
            print(f"[ERROR] Could not save HTML file: {e}")
            return False
        
        print("[SUCCESS] Float account details processed successfully")
        return True
        
    except Exception as exc:
        print(f"[ERROR] process_float_account_details failed: {exc}")
        import traceback
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
                        "text": "Extract the exact digits from this CAPTCHA image. It's a 4-6 digit code with possible lines or distortions. Respond only with the number."
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
def process_organization_rows(page):
    """
    Processes each row in the organization table, performing actions for 'float' and 'commission' options,
    and navigates to the next page until no more pages are available.
    """
    while True:
        print("[INFO] Processing rows on current page...")
        
        time.sleep(2)  # Wait for page to load completely
        # Find all rows in the tbody with class 'childTableRow'
        rows = page.query_selector_all("//tbody//tr[@class='el-table__row childTableRow']")
        if not rows:
            print("[INFO] No rows found on this page. Exiting.")
            break

        for index, row in enumerate(rows, 1):
            try:
                # Click the row
                print(f"[INFO] Clicking row {index}/{len(rows)}...")
                row.click()
                page.wait_for_timeout(200)  # Wait for page to update

                # Click the first div in vertical-page-container
                first_div = page.wait_for_selector(
                    "//body/div[@id='app']/div[@class='layout-container']/main[@class='main-container hideMenu']/section[@class='main-content']/div[@class='center-content-container']/section[@class='app-main-container']/div[@class='vertical-page']/div[@class='vertical-page-container']/div[1]",
                    timeout=30000
                )
                first_div.click()
                print("[INFO] Clicked first div in vertical-page-container.")
                page.wait_for_timeout(2000)
                
                # Click the first div in vertical-page-container
                more_button = page.wait_for_selector(
                    "//button[@class='el-button el-button--primary is-link']",
                    timeout=30000
                )
                more_button.click()
                print("[INFO] Clicked more")
                page.wait_for_timeout(2000)

                # Click 'Review Transaction'
                review_btn = page.wait_for_selector(
                    "//div[contains(text(),'Review Transaction')]",
                    timeout=30000
                )
                review_btn.click()
                print("[INFO] Clicked 'Review Transaction'.")
                page.wait_for_timeout(2000)
                
                # Save page HTML
                html_content = page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, "html.parser")

                with open("organization.html", "w", encoding="utf-8") as f:
                    f.write(soup.prettify())

                print("[✅] Saved organization page HTML to organization.html")

                # Click the dropdown icon
                dropdown_icon = page.wait_for_selector(
                    "//div[@class='el-form-item is-required asterisk-left el-form-item--label-top none-margin-bottom']//i[@class='el-icon el-select__caret el-select__icon']//*[name()='svg']",
                    timeout=30000
                )
                dropdown_icon.click()
                print("[INFO] Clicked dropdown icon.")
                page.wait_for_timeout(1000)
                
                # Now select the float option (dropdown is already open)
                is_selected = select_first_float_option_by_index(page)
                
                if not is_selected:
                    print("[WARN] No 'float' option found in dropdown. Skipping this row.")
                    continue
                else:
                    process_float_account_details(page)

                # Continue with the rest of your processing...
                # (Uncomment and add your date picker, search, export logic here)

            except Exception as exc:
                print(f"[ERROR] Failed to process row {index}: {exc}")
                import traceback
                traceback.print_exc()
                continue

        # Check for 'Next Page' button and click if enabled
        next_page_btn = page.query_selector("(//button[@aria-label='Go to next page'])[1]")
        if next_page_btn and not next_page_btn.is_disabled():
            print("[INFO] Clicking 'Next Page' button...")
            next_page_btn.click()
            page.wait_for_timeout(5000)  # Wait for page to load
        else:
            print("[INFO] No more pages to process. Exiting.")
            break

    print("[INFO] Finished processing all rows and pages.")
    print("[INFO] Browser will remain open for inspection. Press ENTER to close.")
    
if __name__ == "__main__":
    # solveCaptchaXai()
    login_to_mpesa()