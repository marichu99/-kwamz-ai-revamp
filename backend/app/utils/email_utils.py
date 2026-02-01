import resend
import os
from flask import render_template
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Email configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_ADDRESS = os.getenv("SMTP_EMAIL", "noreply@kwamz-ai.org")
DASHBOARD_URL = os.getenv("DASHBOARD_URL")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _send_email(subject: str, html: str, recipient: str, attachments=None):
    """Core email sending function using Resend API."""
    try:
        params = {
            "from": EMAIL_ADDRESS,
            "to": [recipient],
            "subject": subject,
            "html": html,
        }
        if attachments:
            params["attachments"] = attachments

        result = resend.Emails.send(params)
        print(f"Email sent: {subject} -> {recipient} (id: {result.get('id', 'unknown')})")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def send_otp_email(recipient_email, otp):
    """Send OTP verification email."""
    try:
        html_content = render_template(
            'otp_email.html',
            otp=otp,
            year=datetime.now(timezone.utc).year
        )
        return _send_email(
            "Your Kwamz-AI Verification Code",
            html_content,
            recipient_email
        )
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False


def send_welcome_email(user_email, username):
    """Send welcome email to new users."""
    try:
        html_content = render_template(
            'welcome_email.html',
            username=username,
            year=datetime.now(timezone.utc).year,
            dashboard_url=DASHBOARD_URL,
            terms_url="https://kwamz-ai.com/terms",
        )
        return _send_email(
            f"Welcome to Kwamz-AI, {username}!",
            html_content,
            user_email
        )
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")
        return False


def send_welcome_pack_email(recipient_email, recipient_name, role, company_data, cr12_file_path):
    """Send welcome pack email to directors and shareholders with CR12 details and attachment."""
    try:
        SUPPORT_EMAIL = "support@kwamz-ai.com"
        TERMS_URL = "https://kwamz-ai.com/terms"
        PRIVACY_URL = "https://kwamz-ai.com/privacy"

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
            'year': datetime.now(timezone.utc).year
        }

        html_content = render_template('company_welcome_pack.html', **template_data)

        attachments = None
        if cr12_file_path and os.path.exists(cr12_file_path):
            with open(cr12_file_path, 'rb') as f:
                file_content = f.read()
            attachments = [{
                "filename": os.path.basename(cr12_file_path),
                "content": list(file_content),
            }]

        return _send_email(
            f"Welcome to {company_data.get('company_name', 'Company')} - Your Welcome Pack",
            html_content,
            recipient_email,
            attachments=attachments
        )
    except Exception as e:
        print(f"Failed to send welcome pack email: {str(e)}")
        return False


def send_email_notification(subject, body, recipient_email):
    """Send a plain text email notification."""
    try:
        html = f"<pre>{body}</pre>"
        return _send_email(subject, html, recipient_email)
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_agent_new_clients_email(agent_email, agent_name, newly_assigned_companies):
    """Send email to agent when new companies are assigned."""
    try:
        total_companies = len(newly_assigned_companies)
        html_content = render_template(
            'agent_new_clients_email.html',
            agent_name=agent_name.split()[0] if agent_name else "Agent",
            total_companies=total_companies,
            companies=newly_assigned_companies,
            dashboard_url=DASHBOARD_URL,
            year=datetime.now(timezone.utc).year
        )
        return _send_email(
            f"{total_companies} New Client(s) Assigned to You!",
            html_content,
            agent_email
        )
    except Exception as e:
        print(f"Failed to send agent new clients email: {str(e)}")
        return False


def generate_scraping_report_email(stats_data: dict):
    """Generate the scraping report email HTML using Jinja2 template."""
    session = stats_data['scraping_session']
    agent = stats_data['agent_stats']
    trans = stats_data['transaction_stats']
    comm = stats_data['commission_stats']

    avg_deposit = (
        trans['total_deposit_amount'] / trans['total_deposits']
        if trans['total_deposits'] > 0 else 0
    )
    avg_withdrawal = (
        trans['total_withdrawal_amount'] / trans['total_withdrawals']
        if trans['total_withdrawals'] > 0 else 0
    )

    context = {
        'period_str': f"{session['start_date'].strftime('%d/%m/%Y')} to {session['end_date'].strftime('%d/%m/%Y')}",
        'scraped_date': session['scraped_at'].strftime('%d/%m/%Y %H:%M'),
        'company_shortcode': session['company_shortcode'],
        'total_transactions': session['total_transactions'],
        'agent_company_count': session['agent_company_count'],
        'successful_scrapes': session['successful_scrapes'],
        'failed_scrapes': session['failed_scrapes'],
        'total_agents': agent['total_agents'],
        'active_agents': agent['active_agents'],
        'average_float': agent['average_float'],
        'agents_below_20000': agent['agents_below_20000'],
        'agents_below_5000': agent['agents_below_5000'],
        'agents_below_1000': agent['agents_below_1000'],
        'total_deposits': trans['total_deposits'],
        'total_withdrawals': trans['total_withdrawals'],
        'total_deposit_amount': trans['total_deposit_amount'],
        'total_withdrawal_amount': trans['total_withdrawal_amount'],
        'net_flow': trans['net_flow'],
        'average_transaction_value': trans['average_transaction_value'],
        'avg_deposit': avg_deposit,
        'avg_withdrawal': avg_withdrawal,
        'total_commission': comm['total_commission'],
        'commission_transactions': comm['commission_transactions'],
        'average_commission_rate': comm['average_commission_rate'],
        'current_year': datetime.now().year,
    }

    return render_template('scraping_report_email.html', **context)


def send_scraping_report_email(recipient_email: str, stats_data: dict):
    """Send the scraping report email."""
    try:
        email_html = generate_scraping_report_email(stats_data)
        company_code = stats_data['scraping_session']['company_shortcode']
        return _send_email(
            f"Data Scraping Report - {company_code} - {datetime.now().strftime('%d/%m/%Y')}",
            email_html,
            recipient_email
        )
    except Exception as e:
        print(f"Failed to send scraping report email: {str(e)}")
        return False


def send_session_timeout_email(recipient_email: str) -> bool:
    """Send session timeout notification email."""
    try:
        subject = f"Session Timed Out - Action Required ({datetime.now().strftime('%d/%m/%Y')})"
        body = (
            "Hello,\n\n"
            "This is to inform you that your current session has timed out due to inactivity "
            "or session expiry.\n\n"
            "For security reasons, the system automatically ends sessions after a defined "
            "period. As a result, you are no longer authenticated and cannot continue with "
            "the current session.\n\n"
            "Please log out (if applicable) and log in again to start a new session and "
            "continue using the system.\n\n"
            "If you continue to experience this issue after re-logging in, kindly contact "
            "the support team for assistance.\n\n"
            "Thank you for your understanding.\n\n"
            "Kind regards,\n"
            "System Administration Team"
        )
        return _send_email(subject, f"<pre>{body}</pre>", recipient_email)
    except Exception as e:
        print(f"Failed to send session timeout email: {str(e)}")
        return False


def send_not_active_short_code_(recipient_email: str, business_name: str, business_short_code: str, company_code: str, status: str) -> bool:
    """Send notification about non-active company."""
    try:
        subject = f"Detection of Non Active Company - Action Required ({datetime.now().strftime('%d/%m/%Y')})"
        body = f"""Hello,

This is to inform you that the agent {business_name} business with shortcode {business_short_code} and company shortcode {company_code} is of the status {status}.

It is standard procedure to inform you that the agent is not active as at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}.

Please ignore this if the necessary measures have been put in place about this specific agent.

Thank you for your support.

Kind regards,
System Administration Team"""

        return _send_email(subject, f"<pre>{body}</pre>", recipient_email)
    except Exception as e:
        print(f"Failed to send notification email: {str(e)}")
        return False
