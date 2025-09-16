import re
from PyPDF2 import PdfReader

def extract_taxpayer_details(pdf_path):
    # Open the PDF file
    reader = PdfReader(pdf_path)
    text = ""

    # Extract text from each page of the PDF
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted

    # Define required file identifier
    file_definition_pattern = r"PIN Certificate"
    
    # Check for expected file content early
    if not re.search(file_definition_pattern, text, re.IGNORECASE):
        return {"error": "Invalid document. Kindly upload a valid Tax PIN Certificate."}

    # Define regex patterns
    pin_pattern = r"[A-Z0-9]{11}"  # Pattern for PIN
    name_pattern = r"Taxpayer Name\s+([A-Z ]+)"  # Pattern for Taxpayer Name
    email_pattern = r"Email Address\s+([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"  # Pattern for Email Address

    # Extract data using regex
    pin_match = re.search(pin_pattern, text)
    name_match = re.search(name_pattern, text, re.IGNORECASE)
    email_match = re.search(email_pattern, text, re.IGNORECASE)

    # Store extracted data in a dictionary
    data = {
        "PIN": pin_match.group(0) if pin_match else "Not found",
        "Taxpayer Name": name_match.group(1).strip() if name_match else "Not found",
        "Email Address": email_match.group(1).strip() if email_match else "Not found"
    }

    return data



