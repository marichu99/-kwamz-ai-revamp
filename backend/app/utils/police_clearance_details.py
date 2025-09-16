import re
from PyPDF2 import PdfReader

def extract_clearance_details(pdf_path):
    # Open the PDF file
    reader = PdfReader(pdf_path)
    text = ""

    # Extract text from each page of the PDF
    for page in reader.pages:
        text += page.extract_text()

    # Preprocess text: Remove extra whitespace and normalize
    text = " ".join(text.split())

    # Define improved regex patterns
    file_definition_pattern = r"POLICE CLEARANCE CERTIFICATE"
    ref_no_pattern = r"Ref\. No\. (PCC-[A-Z0-9]+)"  # Pattern for Reference Number
    name_pattern = r"fingerprints recorded from\s+([A-Z ]+?)\s+holder of ID No"  # Improved pattern for Name
    id_no_pattern = r"ID No\. (\d+)"  # Pattern for ID Number

    # Extract data using regex
    ref_no_match = re.search(ref_no_pattern, text)
    name_match = re.search(name_pattern, text, re.IGNORECASE)
    id_no_match = re.search(id_no_pattern, text)

    if not re.search(file_definition_pattern, text, re.IGNORECASE):
        return {"error": "Invalid document. Kindly upload a valid Police Clearance Certificate."}

    # Store extracted data in a dictionary
    data = {
        "Reference Number": ref_no_match.group(1) if ref_no_match else "Not found",
        "Name": name_match.group(1).strip() if name_match else "Not found",
        "ID Number": id_no_match.group(1) if id_no_match else "Not found"
    }

    return data
