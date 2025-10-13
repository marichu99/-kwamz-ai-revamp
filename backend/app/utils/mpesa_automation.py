from playwright.sync_api import sync_playwright
from script import fill_login_form, capture_and_solve_captcha
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
        page.fill("//input[@placeholder='Please enter']", captcha_solution)

        # Submit the login form
        page.click("//button[contains(., 'Login')]")
        print("[INFO] Login form submitted.")

        # Optional: wait for post-login navigation or validation
        page.wait_for_timeout(5000)
        browser.close()

def solveCaptcha(image_path="/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"):
    # STEP 1 — Load & preprocess
    img = Image.open(image_path)
    gray = img.convert("L")
    inv = ImageOps.invert(gray)
    filtered = inv.filter(ImageFilter.MedianFilter())
    bw = filtered.point(lambda x: 0 if x < 140 else 255, '1')

    # Optional: upscale for better OCR
    upscale_factor = 2
    bw = bw.resize((bw.width * upscale_factor, bw.height * upscale_factor), Image.LANCZOS)

    # STEP 2 — Debug intermediate outputs (optional)
    bw.save("final_bw.png")

    # STEP 3 — OCR
    custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
    captcha_text = pytesseract.image_to_string(bw, config=custom_config)

    # STEP 4 — Clean up result
    result = captcha_text.strip().replace(" ", "")
    print(f"Extracted CAPTCHA: {repr(result)}")
    for psm in [6, 7, 8]:
        cfg = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(bw, config=cfg)
        print(f"PSM {psm} => {repr(text.strip())}")
    return result

def solveCaptcha4():
    image_path = "/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
    img = Image.open(image_path)

    # Upscale early
    upscale_factor = 3
    img = img.resize((img.width * upscale_factor, img.height * upscale_factor), Image.LANCZOS)

    # Grayscale
    gray = img.convert("L")

    # Optional invert (depends on background/foreground)
    inv = ImageOps.invert(gray)

    # Median filter to reduce line noise
    filtered = inv.filter(ImageFilter.MedianFilter(size=3))

    # Threshold — adjust carefully
    bw = filtered.point(lambda x: 0 if x < 130 else 255, '1')
    bw.save("final_debug_bw.png")

    # OCR with optimized config
    config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(bw, config=config)

    result = text.strip().replace(" ", "")
    print(f"Extracted CAPTCHA: {repr(result)}")
    return result
    
def solveCaptcha2():
    # Load the image
    image_path = "/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    _, thresh = cv2.threshold(img, 140, 255, cv2.THRESH_BINARY_INV)

    # Save temporary preprocessed image
    cv2.imwrite("clean_captcha.png", thresh)

    captcha_text = pytesseract.image_to_string(thresh, config="--psm 7 digits")
    print("Extracted CAPTCHA:", captcha_text.strip())

def solveCaptcha3():
    # Load the image
    image_path = "/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, (img.shape[1]*3, img.shape[0]*3), interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(img, 130, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((2,2), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    cv2.imwrite("final_debug_cv2.png", dilated)

    text = pytesseract.image_to_string(dilated, config='--psm 7 -c tessedit_char_whitelist=0123456789')
    print(f"OCR after dilation: {repr(text.strip())}")

def solve_captcha_improved():
    """
    Enhanced CAPTCHA solver with multiple preprocessing techniques
    """
    # Load image
    image_path="/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
    img = Image.open(image_path)
    
    # Step 1: Upscale for better OCR accuracy
    upscale_factor = 3
    img = img.resize((img.width * upscale_factor, img.height * upscale_factor), Image.LANCZOS)
    
    # Step 2: Convert to grayscale
    gray = img.convert("L")
    
    # Step 3: Apply aggressive contrast enhancement
    # Use histogram equalization via PIL
    gray_array = np.array(gray)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) using OpenCV
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray_array) if hasattr(cv2, 'createCLAHE') else gray_array
    
    # Step 4: Multiple thresholding attempts
    # Try different threshold values and pick the best one
    best_result = ""
    
    for threshold in [120, 140, 160, 180]:
        # Binary threshold
        _, thresh = cv2.threshold(enhanced, threshold, 255, cv2.THRESH_BINARY)
        
        # Noise removal
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Save debug image
        debug_img = Image.fromarray(cleaned)
        debug_img.save(f"debug_thresh_{threshold}.png")
        
        # Try multiple PSM modes
        for psm in [7, 8, 13]:
            config = f'--psm {psm} -c tessedit_char_whitelist=0123456789 tessedit_char_blacklist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            text = pytesseract.image_to_string(cleaned, config=config)
            clean_text = ''.join(filter(str.isdigit, text.strip()))
            
            # Prefer results with 4-6 digits (typical CAPTCHA length)
            if 4 <= len(clean_text) <= 6:
                print(f"Threshold {threshold}, PSM {psm}: {clean_text}")
                if len(clean_text) > len(best_result):
                    best_result = clean_text
    
    # If no good result found, try with inverted image
    if not best_result:
        print("Trying inverted image approach...")
        _, thresh_inv = cv2.threshold(enhanced, 128, 255, cv2.THRESH_BINARY_INV)
        config = '--psm 8 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(thresh_inv, config=config)
        best_result = ''.join(filter(str.isdigit, text.strip()))
    
    print(f"Final CAPTCHA result: {best_result}")
    return best_result

def solve_captcha_simple():
    """
    Simpler approach that often works well
    """
    # Read image
    image_path="/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # Upscale
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(img, (3,3), 0)
    
    # Adaptive threshold - works better than global threshold for uneven lighting
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 11, 2)
    
    # Invert if needed (white text on black background)
    thresh = cv2.bitwise_not(thresh)
    
    # Save for debugging
    cv2.imwrite("final_processed.png", thresh)
    
    # OCR with multiple PSM attempts
    results = []
    for psm in [7, 8, 13]:
        config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(thresh, config=config)
        clean_text = ''.join(filter(str.isdigit, text.strip()))
        if clean_text:
            results.append(clean_text)
            print(f"PSM {psm}: {clean_text}")
    
    # Return the most common result or the longest one
    if results:
        best = max(results, key=len)
        print(f"Selected: {best}")
        return best
    
    return ""

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

def solve_captcha_advanced():
    """
    Advanced CAPTCHA solver with segmentation for better accuracy on lined/noisy digit CAPTCHAs.
    """
    image_path=r"/home/mabera/workspace/personal/-kwamz-ai-revamp/backend/app/utils/captcha.png"
    # Load and upscale for better resolution
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Image not loaded properly.")
    upscale_factor = 3
    img = cv2.resize(img, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)

    # Apply Gaussian blur to reduce high-frequency noise
    blurred = cv2.GaussianBlur(img, (5, 5), 0)

    # Adaptive threshold for uneven lighting (better than global)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

    # Morphology: opening to remove small noise, then dilation to thicken digits if needed
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    dilated = cv2.dilate(cleaned, kernel, iterations=1)  # Helps connect broken digits

    # Optional: erode thin lines if they are prominent (tune iterations)
    eroded = cv2.erode(dilated, np.ones((2, 2), np.uint8), iterations=1)

    # Save intermediate for debugging
    cv2.imwrite("debug_preprocessed.png", eroded)

    # Find contours for segmentation
    contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    digit_boxes = []

    # Filter contours by size (approximate digit dimensions after upscale)
    img_height = img.shape[0]
    min_area = (img_height * 0.2) ** 2  # Rough estimate: 20% of height squared
    max_area = (img_height * 0.8) ** 2
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h)
        area = w * h
        if min_area < area < max_area and 0.2 < aspect_ratio < 1.0:  # Tune for digits (taller than wide)
            digit_boxes.append((x, y, w, h))

    # Sort boxes left-to-right by x-coordinate
    digit_boxes.sort(key=lambda box: box[0])

    # OCR each segmented digit
    captcha_text = ""
    config = r'--psm 10 -c tessedit_char_whitelist=0123456789'  # PSM 10 for single char
    for i, (x, y, w, h) in enumerate(digit_boxes):
        # Crop digit with padding to avoid edge issues
        padding = 5
        digit_img = eroded[max(0, y-padding):y+h+padding, max(0, x-padding):x+w+padding]
        
        # Resize to standard size for better OCR
        digit_img = cv2.resize(digit_img, (30, 50), interpolation=cv2.INTER_AREA)
        
        # Save individual digit for debug
        cv2.imwrite(f"debug_digit_{i}.png", digit_img)
        
        # OCR
        text = pytesseract.image_to_string(digit_img, config=config)
        digit = ''.join(filter(str.isdigit, text.strip()))
        if digit:  # If recognized, add; else skip or handle
            captcha_text += digit
        else:
            print(f"Failed to recognize digit {i} – may need tuning.")

    print(f"Segmented CAPTCHA: {captcha_text}")

    # Fallback: if segmentation fails (e.g., <4 digits), try whole-image OCR with multiple PSMs
    if len(captcha_text) < 4:
        print("Segmentation yielded short result; falling back to whole-image OCR.")
        results = []
        for psm in [7, 8, 13]:
            config = f'--psm {psm} -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(eroded, config=config)
            clean_text = ''.join(filter(str.isdigit, text.strip()))
            if 4 <= len(clean_text) <= 6:
                results.append(clean_text)
        
        if results:
            # Pick the longest or most common
            captcha_text = max(results, key=len)
            print(f"Fallback CAPTCHA: {captcha_text}")

    # Final validation: expect 4-6 digits; if not, return empty or retry logic in caller
    if 4 <= len(captcha_text) <= 6:
        return captcha_text
    else:
        print("No valid CAPTCHA found – check debug images and tune thresholds/kernel sizes.")
        return ""

# Updated main function
# if __name__ == "__main__":
#     # Try both methods
#     print("=== Method 1: Enhanced ===")
#     result1 = solve_captcha_improved()
    
#     print("\n=== Method 2: Simple ===")
#     result2 = solve_captcha_simple()
    
#     # Use the result with more digits, or fallback
#     final_result = result1 if len(result1) >= len(result2) else result2
#     print(f"\n🎯 Final CAPTCHA: {final_result}")

if __name__ == "__main__":
    # Replace with real credentials
    # login_to_mpesa(short_code="123456", username="testuser", password="secretpassword")
    solveCaptchaXai()
