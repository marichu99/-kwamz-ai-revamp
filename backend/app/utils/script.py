from playwright.sync_api import sync_playwright
from PIL import Image
from app import db
from app.model.document import Document
from app.model.useragent import UserAgent
import pytesseract
from openai import OpenAI
import re
import sys
import time
import base64
import os

def solve_arithmetic_captcha(captcha_image_path):
    """
    Extract and solve arithmetic CAPTCHA from the image.
    """
    captcha_image = Image.open(captcha_image_path)
    captcha_text = pytesseract.image_to_string(captcha_image, config="--psm 7")
    print(f"Extracted CAPTCHA text: {captcha_text}")

    # Solve the arithmetic question
    match = re.match(r"(\d+)\s*([\+\-\*/])\s*(\d+)", captcha_text.strip())
    if not match:
        print("An error occurred while solving the captcha")
        solve_arithmetic_captcha(captcha_image_path)
        # raise ValueError("Invalid CAPTCHA format")
    num1, operator, num2 = match.groups()
    num1, num2 = int(num1), int(num2)

    print(f"The operator is {operator}")
    print(f"The num 1 {num1}")
    print(f"The num2 is {num2}")

    if operator == "+":
        return num1 + num2
    elif operator == "-":
        return num1 - num2
    elif operator == "*":
        return num1 * num2
    elif operator == "/":
        return num1 // num2 
    else:
        raise ValueError("Unsupported operator")

def authenticate_dci(page, police_clearance, id_number):
    page.goto("https://dci.ecitizen.go.ke/verify", timeout=60000)
    # Locate the dropdown by its ID
    dropdown = page.locator("#q_service_id")

    # Select the first non-placeholder option
    dropdown.select_option("1")
    page.fill("#q_ref_number", police_clearance)
    page.fill("#q_security_question", id_number)
    page.click(".btn.btn-primary.btn-sm")

    page.evaluate("window.scrollBy(0, 300)")
    
    try:
        valid_keyword = page.locator("table h1").inner_text(timeout=5000)
        print(f"Police Clearance Status: {valid_keyword}")
        return valid_keyword
    except Exception:
        print("Police Clearance is invalid.")
        return "Invalid"

def authenticate_kra_from_app (kra_pin,police_number,id_number,tax_payer_name):
    print(f"Received inputs - KRA PIN: {kra_pin}, Police Clearance: {police_number}, ID Number: {id_number}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=2000, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        kra_status = authenticate_kra(page, kra_pin)
        if kra_status is None or "Active" not in str(kra_status) or isinstance(kra_status,type(None)):
            # retry for kra
            kra_status = authenticate_kra(page, kra_pin)
        
        police_status = authenticate_dci(page, police_number, id_number)
        if police_status is None or "VALID" not in str(police_status) or isinstance(kra_status,type(None)):
            # retry for dci
            police_status = authenticate_dci(page, police_number, id_number)

        status = ""
        # Final output based on statuses
        if "Active" in kra_status and "VALID" in police_status:
            status = rf"Both KRA PIN and Police Clearance are valid for {tax_payer_name}."
            user = UserAgent.query.filter(id_number==id_number).first()
            
            # update user authenticated status
            if user:
                user.is_authentic = True
                db.session.add(user)
                db.session.commit()
                print(f"User {user.firstname} {user.lastname} authenticated status updated to True.")
            else:
                print(f"No user found with ID number {id_number}.")
                
            authenticated=True
            print(status)
            return status
        elif "Active" not in kra_status and "VALID" not in police_status:
            status = "Both KRA PIN and Police Clearance are invalid."
            authenticated=False
            print(status)
            return status
        elif "Active" in kra_status:
            status = "KRA PIN is valid, but Police Clearance is invalid."
            authenticated=False
            print(status)
            return status
        elif "VALID" in police_status:
            status = "Police Clearance is valid, but KRA PIN is invalid."
            authenticated=False
            print(status)
            return status
        
        document = Document(
        kra_pin=kra_pin,
        taxpayer_name=tax_payer_name,
        police_clearance_ref=police_number,
        id_number=id_number,
        auth_reason=status,
        authenticated=authenticated
        )
        db.session.add(document)
        db.session.commit()

        time.sleep(5)
        browser.close()

def authenticate_kra(page, kra_pin):
    page.goto("https://itax.kra.go.ke/KRA-Portal/pinChecker.htm", timeout=60000)
    page.fill("#vo\\.pinNo", kra_pin)
    page.wait_for_selector("#captcha_img")

    captcha_image_path = "captcha.png"
    captcha_element = page.query_selector("#captcha_img")
    captcha_element.screenshot(path=captcha_image_path)
    print(f"CAPTCHA image saved as {captcha_image_path}")

    captcha_solution = solve_arithmetic_captcha(captcha_image_path)
    print(f"CAPTCHA solution: {captcha_solution}")

    page.fill("#captcahText", str(captcha_solution))
    page.click("#consult")

    try:
        second_table = page.locator("table.tab3.whitepapartdBig").nth(1)
        rows = second_table.locator("tr")
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            row_data = [cells.nth(j).inner_text() for j in range(cells.count())]
            if row_data[0] == "PIN Status":
                print(f"KRA PIN Status: {row_data[1]}")
                return row_data[1]
    except Exception:
        print("KRA PIN is invalid.")
        return "Invalid"
    
def solve_arithmetic_captcha(captcha_image_path: str) -> int:
    """
    Extract and solve arithmetic CAPTCHA from the image.
    """
    captcha_image = Image.open(captcha_image_path)
    captcha_text = pytesseract.image_to_string(captcha_image, config="--psm 7").strip()
    print(f"[INFO] Extracted CAPTCHA text: {captcha_text}")

    match = re.match(r"(\d+)\s*([\+\-\*/xX])\s*(\d+)", captcha_text)
    if not match:
        raise ValueError(f"Invalid CAPTCHA format: {captcha_text}")

    num1, operator, num2 = match.groups()
    num1, num2 = int(num1), int(num2)

    if operator in ("+",):
        return num1 + num2
    elif operator in ("-",):
        return num1 - num2
    elif operator in ("*", "x", "X"):
        return num1 * num2
    elif operator == "/":
        return num1 // num2
    else:
        raise ValueError(f"Unsupported operator: {operator}")

def wait_for_login_page_ready(page, timeout: float = 30000):
    """
    Wait for the login page to be fully loaded and the form fields to be ready.
    """
    try:
        # Option 1: Wait for all three critical input fields to be visible and editable
        page.wait_for_selector("//input[@id='shortCode']", state="visible", timeout=timeout)
        page.wait_for_selector("//input[@id='userAccount']", state="visible", timeout=timeout)
        page.wait_for_selector("//input[@id='password']", state="visible", timeout=timeout)

        # Optional: Also ensure they are enabled (not disabled)
        page.wait_for_function(
            """() => {
                const shortCode = document.querySelector('#shortCode');
                const userAccount = document.querySelector('#userAccount');
                const password = document.querySelector('#password');
                return shortCode && !shortCode.disabled &&
                       userAccount && !userAccount.disabled &&
                       password && !password.disabled;
            }""",
            timeout=timeout
        )

        print("[INFO] Login page is fully loaded and form fields are ready.")
    except Exception as e:
        raise Exception("[ERROR] Timeout waiting for login page to load or form fields to become ready.")

def fill_login_form(page, short_code: str, username: str, password: str):
    """
    Wait for login page to be ready, then fill in the form fields.
    """
    wait_for_login_page_ready(page)

    page.fill("//input[@id='shortCode']", short_code)
    page.fill("//input[@id='userAccount']", username)
    page.fill("//input[@id='password']", password)

    print("[INFO] Login form fields filled successfully.")
    
        
def solveCaptchaXai(image_path):
    # Initialize client with your xAI key
    xai_key = os.getenv("XAI_API_KEY")
    print(f"The api key is {xai_key}")
    
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



def capture_and_solve_captcha(page) -> str:
    """
    Capture CAPTCHA image, solve it, and return the result.
    """
    captcha_selector = "//img[@class='verifyCode-img-item']"
    captcha_path = "captcha.png"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            # Wait for the element to be stable in the DOM
            page.wait_for_selector(captcha_selector, state="visible", timeout=10000)
            import time
            time.sleep(1)  # Allow the captcha image to fully render

            # Use locator (auto-waits and re-queries) instead of query_selector (stale handle)
            captcha_locator = page.locator(captcha_selector).first
            captcha_locator.wait_for(state="visible", timeout=5000)
            captcha_locator.screenshot(path=captcha_path)
            print(f"[INFO] CAPTCHA image saved at {captcha_path}")

            captcha_solution = solveCaptchaXai(captcha_path)
            print(f"[INFO] CAPTCHA solved: {captcha_solution}")
            return str(captcha_solution)
        except Exception as e:
            print(f"[WARN] CAPTCHA screenshot attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
            else:
                raise
