import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import render_template
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

# Email configuration
EMAIL_ADDRESS = "marichufx@gmail.com"
EMAIL_PASSWORD = os.getenv("APP_PASSWORD")
DASHBOARD_URL = os.getenv("DASHBOARD_URL")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_otp_email(recipient_email, otp):
    """
    Send a beautiful magenta/purple-pink themed OTP email
    """
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Your Kwamz-AI Verification Code"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email

        # Render HTML template with dynamic content
        html_content = render_template(
            'otp_email.html',
            otp=otp,
            year=datetime.utcnow().year
        )
        
        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"OTP email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_welcome_email(user_email, username):
    """
    Send a beautiful welcome email to new users
    """
    try:
        # Email configuration (replace with your actual credentials)
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Welcome to Kwamz-AI, {username}! 🎉"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = user_email
        
        # Render HTML template with dynamic content
        html_content = render_template(
            'welcome_email.html',
            username=username,
            year=datetime.utcnow().year,
            dashboard_url=DASHBOARD_URL,
            terms_url="https://kwamz-ai.com/terms",
        )
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"Welcome email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
        return False

def send_email_notification(subject, body,recipient_email):
    try:
        # Set up the MIME
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Attach the email body
        msg.attach(MIMEText(body, "plain"))

        # Connect to the server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Notification email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
