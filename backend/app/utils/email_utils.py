import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import render_template
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
from datetime import datetime
import os

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
        print(f"Failed to send welcome email: {str(e)}")
        return False
    
def send_welcome_pack_email(recipient_email, recipient_name, role, company_data, cr12_file_path):
    """
    Send a welcome pack email to directors and shareholders with CR12 details and attachment.
    """
    try:
        # Email configuration
        EMAIL_ADDRESS = "marichufx@gmail.com"
        EMAIL_PASSWORD = os.getenv("APP_PASSWORD")
        DASHBOARD_URL = os.getenv("DASHBOARD_URL")
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SUPPORT_EMAIL = "support@kwamz-ai.com"
        TERMS_URL = "https://kwamz-ai.com/terms"
        PRIVACY_URL = "https://kwamz-ai.com/privacy"

        # Prepare company data for template
        template_data = {
            'company_name': company_data.get('company_name', 'Company'),
            'shortcode': company_data.get('shortcode', 'N/A'),
            'company_number': company_data.get('company_number', 'N/A'),
            'registration_date': company_data.get('registration_date', ''),
            'address': company_data.get('address', 'N/A'),
            'primary_owner_name': company_data.get('primary_owner_name', 'N/A'),
            'primary_owner_shares': company_data.get('primary_owner_shares', 0),
            'secondary_shareholders': company_data.get('secondary_shareholders', []),
            'directors': company_data.get('directors', []),
            'cr12_file_location': company_data.get('file_location', ''),
            'recipient_name': recipient_name,
            'role': role,
            'shares': next((sh['shares'] for sh in company_data.get('secondary_shareholders', []) if sh['name'] == recipient_name), 0) if role == 'shareholder' else 0,
            'dashboard_url': DASHBOARD_URL,
            'support_email': SUPPORT_EMAIL,
            'terms_url': TERMS_URL,
            'privacy_url': PRIVACY_URL,
            'year': datetime.utcnow().year
        }

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Welcome to {company_data.get('company_name', 'Company')} - Your Welcome Pack"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email

        # Render HTML template
        html_content = render_template('company_welcome_pack.html', **template_data)
        msg.attach(MIMEText(html_content, 'html'))

        # Attach CR12 file if it exists
        if cr12_file_path and os.path.exists(cr12_file_path):
            with open(cr12_file_path, 'rb') as f:
                cr12_attachment = MIMEApplication(f.read(), _subtype="pdf")
                cr12_attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=os.path.basename(cr12_file_path)
                )
                msg.attach(cr12_attachment)

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"Welcome pack email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send welcome pack email: {str(e)}")
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

def send_agent_new_clients_email(agent_email, agent_name, newly_assigned_companies):
    """
    Send a beautiful green-themed email to an agent when new companies are assigned to them.
    
    :param agent_email: Email of the agent
    :param agent_name: First name or full name of the agent
    :param newly_assigned_companies: List of dicts with company details (from get_companies format)
    """
    try:
        total_companies = len(newly_assigned_companies)

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎉 {total_companies} New Client(s) Assigned to You!"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = agent_email

        # Render HTML template
        html_content = render_template(
            'agent_new_clients_email.html',
            agent_name=agent_name.split()[0] if agent_name else "Agent",  # Use first name
            total_companies=total_companies,
            companies=newly_assigned_companies,
            dashboard_url=DASHBOARD_URL,
            year=datetime.utcnow().year
        )

        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"New clients notification email sent to agent: {agent_email}")
        return True

    except Exception as e:
        print(f"Failed to send agent new clients email: {str(e)}")
        return False

def generate_scraping_report_email(stats_data: dict):
    """
    Generate the scraping report email HTML using Jinja2 template.
    
    Args:
        stats_data (dict): The full dictionary returned by gather_scraping_statistics()
    
    Returns:
        str: Rendered HTML email content
    """
    # Extract nested dicts for clarity
    session = stats_data['scraping_session']
    agent = stats_data['agent_stats']
    trans = stats_data['transaction_stats']
    comm = stats_data['commission_stats']

    # Pre-calculate average deposit/withdrawal to avoid template logic
    avg_deposit = (
        trans['total_deposit_amount'] / trans['total_deposits']
        if trans['total_deposits'] > 0 else 0
    )
    avg_withdrawal = (
        trans['total_withdrawal_amount'] / trans['total_withdrawals']
        if trans['total_withdrawals'] > 0 else 0
    )

    # Build context for the template
    context = {
        # Session info
        'period_str': f"{session['start_date'].strftime('%d/%m/%Y')} to {session['end_date'].strftime('%d/%m/%Y')}",
        'scraped_date': session['scraped_at'].strftime('%d/%m/%Y %H:%M'),
        'company_shortcode': session['company_shortcode'],
        'total_transactions': session['total_transactions'],
        'agent_company_count': session['agent_company_count'],
        'successful_scrapes': session['successful_scrapes'],
        'failed_scrapes': session['failed_scrapes'],

        # Agent stats
        'total_agents': agent['total_agents'],
        'active_agents': agent['active_agents'],
        'average_float': agent['average_float'],
        'agents_below_20000': agent['agents_below_20000'],
        'agents_below_5000': agent['agents_below_5000'],
        'agents_below_1000': agent['agents_below_1000'],

        # Transaction stats
        'total_deposits': trans['total_deposits'],
        'total_withdrawals': trans['total_withdrawals'],
        'total_deposit_amount': trans['total_deposit_amount'],
        'total_withdrawal_amount': trans['total_withdrawal_amount'],
        'net_flow': trans['net_flow'],
        'average_transaction_value': trans['average_transaction_value'],
        'avg_deposit': avg_deposit,
        'avg_withdrawal': avg_withdrawal,

        # Commission stats
        'total_commission': comm['total_commission'],
        'commission_transactions': comm['commission_transactions'],
        'average_commission_rate': comm['average_commission_rate'],

        # Extra
        'current_year': datetime.now().year,
    }

    # Render the Jinja2 template (assumes templates/scraping_report_email.html exists)
    return render_template('scraping_report_email.html', **context)

def send_scraping_report_email(recipient_email: str, stats_data: dict):
    """
    Send the scraping report email using the full stats dictionary.
    """
    try:
        # Generate HTML using the full stats data
        email_html = generate_scraping_report_email(stats_data)

        company_code = stats_data['scraping_session']['company_shortcode']

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🌿 Data Scraping Report - {company_code} - {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email

        msg.attach(MIMEText(email_html, 'html'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"Scraping report email sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"Failed to send scraping report email: {str(e)}")
        return False