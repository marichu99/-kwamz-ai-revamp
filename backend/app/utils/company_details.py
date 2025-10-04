import re
from PyPDF2 import PdfReader


def extract_company_number(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    
    # Look for the pattern 'COMPANY NUMBER <number>'
    match = re.search(r'COMPANY\s+NUMBER\s+([A-Z0-9\-]+)', text,re.IGNORECASE)
    
    # Store extracted data in a dictionary
    data = {
        "PIN": match.group(1) if match else "Not found"
    }
    return data

