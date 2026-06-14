from playwright.sync_api import sync_playwright
import logging
from PIL import Image
from app import db
from app.model.document import Document
from app.model.useragent import UserAgent
import pytesseract
import anthropic
import re
import sys
import time
import base64
import os

logger = logging.getLogger(__name__)


def solve_arithmetic_captcha(captcha_image_path):
    """
    Extract and solve arithmetic CAPTCHA from the image.
    """
    captcha_image = Image.open(captcha_image_path)
    captcha_text = pytesseract.image_to_string(captcha_image, config="--psm 7")

    match = re.match(r"(\d+)\s*([\+\-\*/])\s*(\d+)", captcha_text.strip())
    if not match:
        solve_arithmetic_captcha(captcha_image_path)
        # raise ValueError("Invalid CAPTCHA format")
    num1, operator, num2 = match.groups()
    num1, num2 = int(num1), int(num2)

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
    dropdown = page.locator("#q_service_id")
    dropdown.select_option("1")
    page.fill("#q_ref_number", police_clearance)
    page.fill("#q_security_question", id_number)
    page.click(".btn.btn-primary.btn-sm")
    page.evaluate("window.scrollBy(0, 300)")

    try:
        valid_keyword = page.locator("table h1").inner_text(timeout=5000)
        return valid_keyword
    except Exception:
        return "Invalid"


def authenticate_kra_from_app(kra_pin, police_number, id_number, tax_payer_name):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=2000)
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        kra_status = authenticate_kra(page, kra_pin)
        if kra_status is None or "Active" not in str(kra_status) or isinstance(kra_status, type(None)):
            kra_status = authenticate_kra(page, kra_pin)

        police_status = authenticate_dci(page, police_number, id_number)
        if police_status is None or "VALID" not in str(police_status) or isinstance(kra_status, type(None)):
            police_status = authenticate_dci(page, police_number, id_number)

        status = ""
        if "Active" in kra_status and "VALID" in police_status:
            status = rf"Both KRA PIN and Police Clearance are valid for {tax_payer_name}."
            user = UserAgent.query.filter(UserAgent.idnumber == id_number).first()
            if user:
                user.is_authentic = True
                db.session.add(user)
                db.session.commit()
            authenticated = True
            return status
        elif "Active" not in kra_status and "VALID" not in police_status:
            status = "Both KRA PIN and Police Clearance are invalid."
            authenticated = False
            return status
        elif "Active" in kra_status:
            status = "KRA PIN is valid, but Police Clearance is invalid."
            authenticated = False
            return status
        elif "VALID" in police_status:
            status = "Police Clearance is valid, but KRA PIN is invalid."
            authenticated = False
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

    captcha_solution = solve_arithmetic_captcha(captcha_image_path)

    page.fill("#captcahText", str(captcha_solution))
    page.click("#consult")

    try:
        second_table = page.locator("table.tab3.whitepapartdBig").nth(1)
        rows = second_table.locator("tr")
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            row_data = [cells.nth(j).inner_text() for j in range(cells.count())]
            if row_data[0] == "PIN Status":
                return row_data[1]
    except Exception:
        return "Invalid"


def solve_arithmetic_captcha(captcha_image_path: str) -> int:
    """
    Extract and solve arithmetic CAPTCHA from the image.
    """
    captcha_image = Image.open(captcha_image_path)
    captcha_text = pytesseract.image_to_string(captcha_image, config="--psm 7").strip()

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
        page.wait_for_selector("//input[@id='shortCode']", state="visible", timeout=timeout)
        page.wait_for_selector("//input[@id='userAccount']", state="visible", timeout=timeout)
        page.wait_for_selector("//input[@id='password']", state="visible", timeout=timeout)
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
    except Exception:
        raise Exception("[ERROR] Timeout waiting for login page to load or form fields to become ready.")


def fill_login_form(page, short_code: str, username: str, password: str):
    """
    Wait for login page to be ready, then fill in the form fields.
    """
    wait_for_login_page_ready(page)
    page.fill("//input[@id='shortCode']", short_code)
    page.fill("//input[@id='userAccount']", username)
    page.fill("//input[@id='password']", password)


def solveCaptchaXai(image_path):
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    client = anthropic.Anthropic(api_key=anthropic_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": "Extract the exact digits from this CAPTCHA image. It's a 4-6 digit code with possible lines or distortions. Respond only with the digits, nothing else.",
                },
            ],
        }],
    )

    captcha_text = response.content[0].text.strip()
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
            page.wait_for_selector(captcha_selector, state="visible", timeout=10000)
            time.sleep(1)

            captcha_locator = page.locator(captcha_selector).first
            captcha_locator.wait_for(state="visible", timeout=5000)
            captcha_locator.screenshot(path=captcha_path)

            captcha_solution = solveCaptchaXai(captcha_path)
            return str(captcha_solution)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
