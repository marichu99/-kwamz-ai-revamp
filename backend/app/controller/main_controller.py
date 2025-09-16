from flask import Flask, render_template, request, jsonify
from utils.kra_pin_details import extract_taxpayer_details
import utils.mpesa_service as mpesa_service
from utils.police_clearance_details import extract_clearance_details
from backend.app.utils.script import authenticate_kra_from_app
from flask_cors import CORS
from app.model.payment import Payment
from app.model.user import User
import subprocess
from dotenv import load_dotenv
import os
import sys

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Route to serve the HTML form
@app.route('/')
def home():
    return render_template('index.html') 

# Endpoint to handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    kra_pin = data.get('kraPin')
    police_clearance = data.get('policeClearance')
    id_number = data.get('idNumber')

    res = authenticate_kra_from_app(kra_pin=kra_pin,police_number=police_clearance,id_number=id_number)

    print(f"the res is {res}")
    return jsonify({
        "success":res
    })

    
@app.route('/extract_kra_pin', methods=['POST'])
def extract_pin():
    file = request.files['file']
    
    file_path = file.filename
    file.save(file_path)

    try:
        extracted_details = extract_taxpayer_details(file_path)

        if "error" in extracted_details:
            return jsonify({"error": extracted_details["error"]})

        print(f"the extracted kra pin is {extracted_details['PIN']}")

        return jsonify({
            "kraPin": extracted_details["PIN"],
            "taxpayerName": extracted_details["Taxpayer Name"],
            "email": extracted_details["Email Address"]
        })

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route('/extract_police_clearance', methods=['POST'])
def extract_police_clearance():
    file = request.files['file']
    
    # Temporary save the uploaded file
    file_path = f"{file.filename}"
    file.save(file_path)

    # Extract KRA PIN from PDF
    extracted_details = extract_clearance_details(file_path)

    if "error" in extracted_details:
        return jsonify({"error": extracted_details["error"]})
    
    extract_police_clearance = extract_clearance_details(file_path)["Reference Number"]
    extract_id_number = extract_clearance_details(file_path)["ID Number"]

    print(f"the extracted police clearance is {extract_police_clearance} ")

    return jsonify({"refNo": extract_police_clearance, "idNo":extract_id_number})

@app.route('/test')
def test_imports():
    try:
        import playwright.sync_api
        from PIL import Image
        import pytesseract
        return "All imports work!"
    except ImportError as e:
        return str(e)
    
@app.route("/path", methods=["POST"])
def path():
    mpesa = mpesa_service.MpesaService()
    data = request.get_json()
    checkout_request_id = data.get("checkoutRequestID")
    token = data.get("token")

    if not checkout_request_id or not token:
        return jsonify({"error": "Missing required parameters"}), 400

    response = mpesa.path(checkout_request_id, token)
    return jsonify(response)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

