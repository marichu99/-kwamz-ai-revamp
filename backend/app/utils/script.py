from playwright.sync_api import sync_playwright
from PIL import Image
from app import db
from app.model.document import Document
import pytesseract
import re
import sys
import time

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
        browser = p.chromium.launch(headless=True, slow_mo=2000)  # 2000ms (1 second) delay per action
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

