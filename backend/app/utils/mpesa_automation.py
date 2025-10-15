from playwright.sync_api import sync_playwright
from app.utils.script import fill_login_form, capture_and_solve_captcha
from PIL import Image, ImageFilter, ImageOps
from dotenv import load_dotenv
from openai import OpenAI
import pytesseract
import cv2
import numpy as np
import base64
import os


# Load environment variables
load_dotenv()

def login_to_mpesa(short_code: str, username: str, password: str):
    url = "https://org.ke.m-pesa.com/#/login?service=https%3A%2F%2Forg.ke.m-pesa.com%2Forgportal%2Fv1%2Fsso%2Fhome"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, timeout=600000)

        # Fill the login form
        fill_login_form(page, short_code, username, password)

        # Solve the CAPTCHA
        captcha_solution = capture_and_solve_captcha(page)
        page.fill("//input[@id='verifyCode']", captcha_solution)

        # Submit the login form
        page.click("//button[@id='loginBtn']")
        print("[INFO] Login form submitted.")

        # Optional: wait for post-login navigation or validation
        page.wait_for_timeout(5000)
        browser.close()
        
def solveCaptchaXai():
    # Initialize client with your xAI key
    xai_key = os.getenv("XAI_API_KEY")
    print(f"The api key is {xai_key}")
    image_path="/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
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

# if __name__ == "__main__":
#     # solveCaptchaXai()
#     login_to_mpesa(short_code="600000", username="admin", password="Admin@123")