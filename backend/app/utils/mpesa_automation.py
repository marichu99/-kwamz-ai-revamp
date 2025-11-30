from playwright.sync_api import sync_playwright,Page, TimeoutError as PlaywrightTimeoutError
# from app.utils.script import fill_login_form, capture_and_solve_captcha
from script import fill_login_form, capture_and_solve_captcha
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
        while(len(captcha_solution) > 4):
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

def scroll_to_bottom(page: Page) -> None:
    """
    Scrolls to the bottom of the page.
    
    Args:
        page: Playwright Page object
    """
    time.sleep(1.5)  # Wait for page to settle before scrolling
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        print("[SUCCESS] Scrolled to bottom of page")
    except Exception as e:
        print(f"[ERROR] Failed to scroll to bottom: {e}")

def save_table_to_dataframe_(page: Page, row_index: int) -> tuple:
    """Extract all rows from paginated table and save to CSV."""
    try:
        print("[INFO] Starting table extraction...")

        headers = []
        all_data_rows = []

        # Set pagination to maximum
        print("[INFO] Setting pagination size...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_load_state("networkidle", timeout=10000)
        
        pagination_dropdown = "//span[@class='el-pagination__sizes']//i[@class='el-icon el-select__caret el-select__icon']"
        dropdown = page.locator(pagination_dropdown).first
        
        if dropdown.is_visible():
            dropdown.click()
            time.sleep(0.5)
            
            for _ in range(3):
                page.keyboard.press("ArrowDown")
                # time.sleep(0.3)
            
            page.keyboard.press("Enter")
        else:
            print("[WARN] Pagination size dropdown not visible")

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
        while True:
            time.sleep(1)  
            print(f"\n[INFO] Extracting page {page_no}...")
            
            page.wait_for_load_state("networkidle", timeout=10000)
            body_tbl = page.wait_for_selector(
                "//table[@class='el-table__body']",
                timeout=10000
            )
            
            if not body_tbl.is_visible():
                break
            
            soup = BeautifulSoup(body_tbl.inner_html(), "html.parser")
            tbody = soup.find("tbody")
            
            if tbody:
                for tr in tbody.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(cells) == len(headers):
                        all_data_rows.append([row_index] + cells)
            
            # Check for next page
            next_btn = page.locator("//button[@aria-label='Go to next page']//i[@class='el-icon']").first
            
            try:
                if next_btn.is_visible() and next_btn.is_enabled():
                    close_irritative_dialog_box(page)
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page_no += 1
                    time.sleep(5)  # Small buffer
                else:
                    break
            except:
                break

        # Create DataFrame
        if not all_data_rows:
            print("[WARN] No data rows extracted")
            df = pd.DataFrame(columns=["OrganizationRowIndex"] + headers)
        else:
            df = pd.DataFrame(all_data_rows, columns=["OrganizationRowIndex"] + headers)
            print(f"[SUCCESS] Extracted {len(df)} total rows")

        # Save to CSV
        csv_path = f"row_{row_index}_float_data.csv"
        df.to_csv(csv_path, index=False)
        print(f"[SUCCESS] Saved to {csv_path}")

        return df, headers

    except Exception as exc:
        print(f"[ERROR] Table extraction failed: {exc}")
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

def get_organizational_rows(page: Page, row_count: int, re_iterate: bool) -> int:
    """
    Extracts all organizational rows from the current page by selecting 'All' in dropdown 
    and counting across pages if needed.
    
    Returns:
        int: Updated total row count
    """
    try:
        elem = page.locator("(//i[@class='el-icon el-select__caret el-select__icon'])").first
        if not elem.is_visible():
            print("[ERROR] Dropdown icon not visible, cannot proceed.")
            return row_count

        print("[INFO] Clicking dropdown icon to expand options...")
        elem.click()

        # Select "All" option (assuming it's the 3rd or 4th ArrowDown + Enter works)
        for _ in range(3):
            page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")

        # Now count rows with optional pagination traversal
        row_count, re_iterate = count_rows_organization(page, row_count, re_iterate)

        if not re_iterate:
            print(f"[INFO] No re-iteration needed, final row count: {row_count}")
        
        return row_count  # ← ALWAYS return the count

    except Exception as e:
        print(f"[ERROR] in get_organizational_rows: {e}")
        return row_count  # ← Even on exception, return current count


def count_rows_organization(page: Page, row_count: int, re_iterate: bool) -> tuple[int, bool]:
    try:
        total_items = get_total_from_pagination(page)
        if total_items is not None:
            print(f"Total = {total_items}")

        print("Table HTML saved to table_debug.html")
        current_page_rows = page.locator("//tbody//tr[@class='el-table__row childTableRow']").count()
        row_count += current_page_rows
        print(f"[INFO] Found {current_page_rows} organizational rows on this page. Total so far: {row_count}")

        if re_iterate:
            print("[INFO] Re-iterating to check for more pages...")
            return go_forth_and_back(page, row_count, re_iterate)
        else:
            return row_count, False

    except Exception as e:
        print(f"[ERROR] Failed to count organizational rows: {e}")
        return row_count, False

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

def go_forth_and_back(page: Page, row_count: int, re_iterate: bool) -> tuple[int, bool]:
    next_page_btn = page.locator("//button[@aria-label='Go to next page']").first
    back_page_btn = page.locator("//button[@aria-label='Go to previous page']").first

    try:
        if re_iterate and next_page_btn.is_visible(timeout=5000) and next_page_btn.is_enabled(timeout=5000):
            print("[INFO] Navigating to next page...")
            next_page_btn.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)  # Small buffer

            # Recursively count on next page
            new_count, should_continue = count_rows_organization(page, row_count, re_iterate=True)
            return new_count, should_continue
        else:
            # No more pages forward → go back to original
            while back_page_btn.is_visible(timeout=5000) and back_page_btn.is_enabled(timeout=5000):
                print("[INFO] Navigating back to previous page...")
                back_page_btn.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(1)

            print(f"[INFO] Finished scanning all pages. Final row count: {row_count}")
            return row_count, False

    except Exception as e:
        print(f"[WARNING] Exception in pagination handling: {e}")
        # Even if something fails, try to return to first page
        try:
            while back_page_btn.is_visible(timeout=5000) and back_page_btn.is_enabled(timeout=5000):
                back_page_btn.click()
                page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        return row_count, False

def go_forth_on_organization(page: Page, row_count: int):
    next_page_btn = page.locator("//button[@aria-label='Go to next page']").first
    back_page_btn = page.locator("//button[@aria-label='Go to previous page']").first

    try:
        if next_page_btn.is_visible() and next_page_btn.is_enabled():
            print("[INFO] Navigating to next page...")
            next_page_btn.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)  # Small buffer
            
        else:
            print(f"[INFO] No more pages forward. Final row count: {row_count}")
           
    except Exception as e:
        print(f"[WARNING] Exception in pagination handling: {e}")
        # Even if something fails, try to return to first page
        try:
            while back_page_btn.is_visible() and back_page_btn.is_enabled():
                back_page_btn.click()
                page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        return row_count, False

def process_float_account_details(page: Page,business_short_code: int):
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
            page.wait_for_timeout(3000)  # Wait for page to load results
            
            df,headers = save_table_to_dataframe_(page, row_index=business_short_code)
            
            if df is not None:
                print("[INFO] Table extracted after submission.")
                return True
            else:
                print("[ERROR] Table extraction failed after submission.")
                return False
            
        except Exception as e:
            print(f"[ERROR] Could not complete Tab/Enter submission: {e}")
            import traceback
            traceback.print_exc()
            return False
        
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

def process_float_selection(page, business_short_code: int) -> bool:
    """Handle float account selection and data extraction."""
    try:
        # Click dropdown
        # //div[@class='el-form-item is-required asterisk-left el-form-item--label-top none-margin-bottom']//i[@class='el-icon el-select__caret el-select__icon']
        # //div[@class='el-form-item is-required asterisk-left el-form-item--label-top none-margin-bottom']//div[@class='el-select__selection']
        # //div[@class='el-form-item is-required asterisk-left el-form-item--label-top none-margin-bottom']//div[@class='el-select__selection']
        dropdown_icon = page.locator(
            "//div[@class='el-form-item is-required asterisk-left el-form-item--label-top none-margin-bottom']//div[@class='el-select__selection']"
        ).first
        # dropdown_icon.click()
        
        if dropdown_icon.is_visible():
            dropdown_icon.click()
            print("[INFO] Dropdown clicked, waiting for options...")
        
            time.sleep(1)
            
            for _ in range(2):
                page.keyboard.press("ArrowDown")
                time.sleep(0.3)
            
            page.keyboard.press("Enter")

        # Process float account details
        if not process_float_account_details(page, business_short_code):
            print("[WARN] Failed to process float account details")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Float selection failed: {e}")
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
    try:
        # Try clicking "Organization Detail" tab to go back
        org_detail = page.locator("//div[@title='Organization Detail']").first
        if org_detail.is_visible(timeout=2000):
            org_detail.click()
            page.wait_for_timeout(1000)
            return True
    except:
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
    
def process_organization_rows(page):
    """
    Processes each row in the organization table, performing actions for 'float' and 'commission' options,
    and navigates to the next page until no more pages are available.
    
    Key improvements:
    - Re-queries rows on each iteration to avoid stale element references
    - Uses index-based selection instead of storing element handles
    - Better error handling and state management
    """
    
    # adjust the page size
    while True:
        print("[INFO] Processing rows on current page...")
        
        # Wait for page to stabilize
        page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(1)
        
        # Count total rows (don't store handles)
        # row_count = page.locator("//tbody//tr[@class='el-table__row childTableRow']").count()
        row_count = 0
        re_iterate = True

        row_count = get_total_from_pagination(page)

        if row_count == 0:
            print("[INFO] No rows found across pages.")
        else:
            print(f"[SUCCESS] Total organizational rows: {row_count}")
            
        print(f"[INFO] Found {row_count} rows to process.")

        # Process each row by index (re-query each time)
        for index in range(row_count):
            try:
                if(index > 1):
                    print(f"[INFO] Refreshing page to avoid stale element references...")
                    page.keyboard.press("Control+R")    
                
                if index % 10 == 1 and index > 1:
                    go_forth_on_organization(page, row_count)
                
                print(f"[INFO] Preparing to process row {index + 1}...")
                time.sleep(1)
                    
                # Re-query rows to get fresh element handles
                page.wait_for_load_state("networkidle", timeout=10000)
                rows = page.locator("//tbody//tr[@class='el-table__row childTableRow']")
                
                # Verify row still exists at this index
                if index >= rows.count():
                    print(f"[WARN] Row {index + 1} no longer exists, skipping...")
                    continue
                
                row = rows.nth(index)
                
                # Extract row text and business code
                row_text = row.text_content()
                print(f"\n[INFO] === Processing Row {index + 1}/{row_count} ===")
                print(f"[INFO] Row text: {row_text}")

                # Extract the first number (business short code)
                first_number = row_text.split()[0] if row_text else None
                match = re.match(r'^(\d+)', first_number) if first_number else None
                
                if not match:
                    print(f"[WARN] Could not extract business code from row {index + 1}, skipping...")
                    continue
                    
                business_short_code = int(match.group(1))
                print(f"[INFO] Business Code: {business_short_code}")
                
                # Click the row (use force=True to handle potential overlay issues)
                print(f"[INFO] Clicking row {index + 1}...")
                row.click(timeout=5000)
                page.wait_for_timeout(500)

                # Navigate through the detail page
                if not navigate_to_review_transaction(page):
                    print(f"[ERROR] Failed to navigate to review transaction for row {index + 1}")
                    close_detail_panel(page)
                    continue

                # Process float account
                if not process_float_selection(page, business_short_code):
                    print(f"[ERROR] Failed to process float account for row {index + 1}")
                    close_detail_panel(page)
                    continue

                # Return to organization list
                if not return_to_organization_list(page):
                    print(f"[WARN] Failed to return to organization list, attempting recovery...")
                    # Try to recover by refreshing
                    page.reload()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    break  # Exit inner loop to re-query rows
                
                print(f"[SUCCESS] Completed processing row {index + 1}")
                time.sleep(1)  # Brief pause between rows

            except Exception as exc:
                print(f"[ERROR] Failed to process row {index + 1}: {exc}")
                traceback.print_exc()
                # Try to recover and continue
                close_detail_panel(page)
                continue

        # Check for next page
        next_page_btn = page.locator("//button[@aria-label='Go to next page']").first
        
        try:
            if next_page_btn.is_visible() and next_page_btn.is_enabled():
                print("[INFO] Navigating to next page...")
                next_page_btn.click()
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(2)
            else:
                print("[INFO] No more pages to process. Exiting.")
                break
        except Exception as e:
            print(f"[INFO] No next page available: {e}")
            break

    print("[INFO] Finished processing all rows and pages.")
       
if __name__ == "__main__":
    # solveCaptchaXai()
    login_to_mpesa()