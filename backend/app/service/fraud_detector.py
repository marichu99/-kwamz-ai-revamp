# app/services/fraud_detection_service.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
from decimal import Decimal
from app.utils.email_utils import _send_email
from app.model.user import User
from app.model.fraud_alert import FraudAlert, FraudReportHistory
from app.model.agentcompany import AgentCompany
from app.model.useragent import UserAgent
from app.model.transaction import Transaction
import logging

from app import db
from app.model.company import Company

logger = logging.getLogger(__name__)

class FraudDetectionService:
    """Service for detecting fraud patterns in transactions."""
    
    def __init__(self, user: User = None, config: Dict = None):
        self.user = user
        self.default_config = {
            'time_window_minutes': 5,
            'amount_variance': 0.1,
            'min_transactions_rollover': 3,
            'split_threshold': 5,  # Min number of transactions to flag as split
            'rapid_back_forth_threshold': 2,
            'high_risk_score': 50,
            'medium_risk_score': 30,
            'max_alerts_per_group': 3,  # Limit alerts for same transaction group
            'analysis_period_days': 30,  # Days to analyze for historical report
            'recent_transactions_limit': 100,  # Recent transactions to check per shortcode
            # Split Transaction Thresholds
            'split_min_amount': 100.0,  # Min amount per transaction to consider
            'split_max_amount': 50000.0,  # Max amount per transaction to consider
            'split_total_amount_threshold': 10000.0,  # Total amount threshold that triggers suspicion
        }
        self.config = {**self.default_config, **(config or {})}
        self.email_templates = self._load_email_templates()
    
    def _load_email_templates(self) -> Dict:
        """Load email templates for different fraud types (plain text for CPU efficiency)."""
        return {
            'split_transaction': {
                'subject': 'Split Transaction Fraud Detected',
                'template': """
============================================================
SPLIT TRANSACTION FRAUD ALERT
============================================================

Detection Time: {detection_time}
Risk Level:     {risk_level}
Fraud Score:    {fraud_score}/100

ACCOUNT INFORMATION
-------------------
Account Phone:  {account_phone}
Account Name:   {account_name}

TRANSACTION SUMMARY
-------------------
Transactions Found: {transaction_count}
Total Amount:       KES {total_amount:,.2f}
Average Amount:     KES {avg_amount:,.2f}

RECEIPT NUMBERS
---------------
{receipt_numbers}

TRANSACTION DETAILS
-------------------
{transaction_details}

REASON FOR FLAG
---------------
{explanation}

============================================================
ACTION REQUIRED: Please review these transactions immediately.
============================================================
"""
            },
            'rollover_fraud': {
                'subject': 'Roll-over Fraud Pattern Detected',
                'template': """
============================================================
ROLLOVER FRAUD ALERT
============================================================

Detection Time: {detection_time}
Risk Level:     {risk_level}
Fraud Score:    {fraud_score}/100

ACCOUNT INFORMATION
-------------------
Account Phone:  {account_phone}
Account Name:   {account_name}
Pattern Type:   {pattern_type}

TRANSACTION SUMMARY
-------------------
Transactions Found: {transaction_count}
Total Amount:       KES {total_amount:,.2f}
Average Amount:     KES {avg_amount:,.2f}

RECEIPT NUMBERS
---------------
{receipt_numbers}

TRANSACTION DETAILS
-------------------
{transaction_details}

REASON FOR FLAG
---------------
{explanation}

============================================================
ACTION REQUIRED: Please review these transactions immediately.
============================================================
"""
            },
            'rapid_back_forth': {
                'subject': 'Rapid Deposit-Withdrawal Pattern Detected',
                'template': """
============================================================
RAPID BACK-FORTH TRANSACTION ALERT
============================================================

Detection Time: {detection_time}
Risk Level:     {risk_level}
Fraud Score:    {fraud_score}/100

ACCOUNT INFORMATION
-------------------
Account Phone:  {account_phone}
Account Name:   {account_name}

TRANSACTION SUMMARY
-------------------
Transactions Found: {transaction_count}
Time Window:        {time_window:.1f} minutes
Net Flow:           KES {net_flow:,.2f}

RECEIPT NUMBERS
---------------
{receipt_numbers}

TRANSACTION DETAILS
-------------------
{transaction_details}

REASON FOR FLAG
---------------
{explanation}

============================================================
ACTION REQUIRED: Please review these transactions immediately.
============================================================
"""
            },
            'historical_report': {
                'subject': 'Historical Fraud Analysis Report',
                'template': self._get_historical_report_template()
            }
        }

    def _get_historical_report_template(self) -> str:
        """Get the beautiful HTML template for historical fraud report."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fraud Detection Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f7fa;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 800px; margin: 0 auto; background-color: #ffffff;">
        <!-- Header -->
        <tr>
            <td style="background: linear-gradient(135deg, #1a237e 0%, #283593 100%); padding: 30px 40px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">
                    🛡️ Fraud Detection Report
                </h1>
                <p style="color: #b3e5fc; margin: 10px 0 0 0; font-size: 14px;">
                    Historical Analysis - {report_date}
                </p>
            </td>
        </tr>

        <!-- Summary Cards -->
        <tr>
            <td style="padding: 30px 40px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="50%" style="padding-right: 10px;">
                            <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 12px; padding: 20px; text-align: center;">
                                <p style="margin: 0; font-size: 32px; font-weight: 700; color: #1565c0;">{total_transactions}</p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #64b5f6; text-transform: uppercase; letter-spacing: 1px;">Transactions Analyzed</p>
                            </div>
                        </td>
                        <td width="50%" style="padding-left: 10px;">
                            <div style="background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-radius: 12px; padding: 20px; text-align: center;">
                                <p style="margin: 0; font-size: 32px; font-weight: 700; color: #c62828;">{suspicious_patterns}</p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #ef5350; text-transform: uppercase; letter-spacing: 1px;">Suspicious Patterns</p>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- Analysis Period Info -->
        <tr>
            <td style="padding: 0 40px 20px 40px;">
                <div style="background-color: #fafafa; border-left: 4px solid #1a237e; padding: 15px 20px; border-radius: 0 8px 8px 0;">
                    <p style="margin: 0; color: #424242; font-size: 14px;">
                        <strong>Analysis Period:</strong> {analysis_period} days |
                        <strong>Accounts Flagged:</strong> {accounts_flagged} |
                        <strong>High Risk:</strong> {high_risk_count}
                    </p>
                </div>
            </td>
        </tr>

        <!-- Agent Companies Section -->
        <tr>
            <td style="padding: 20px 40px;">
                <h2 style="color: #1a237e; font-size: 20px; margin: 0 0 20px 0; padding-bottom: 10px; border-bottom: 2px solid #e8eaf6;">
                    🏢 Agent Companies Involved
                </h2>
                {agent_companies_section}
            </td>
        </tr>

        <!-- User Agents Section -->
        <tr>
            <td style="padding: 20px 40px;">
                <h2 style="color: #1a237e; font-size: 20px; margin: 0 0 20px 0; padding-bottom: 10px; border-bottom: 2px solid #e8eaf6;">
                    👤 User Agents Responsible
                </h2>
                {user_agents_section}
            </td>
        </tr>

        <!-- Culpable Agents Section -->
        <tr>
            <td style="padding: 20px 40px;">
                <h2 style="color: #c62828; font-size: 20px; margin: 0 0 20px 0; padding-bottom: 10px; border-bottom: 2px solid #ffcdd2;">
                    ⚠️ Culpable Agents Analysis
                </h2>
                {culpable_agents_section}
            </td>
        </tr>

        <!-- Fraud Type Breakdown -->
        <tr>
            <td style="padding: 20px 40px;">
                <h2 style="color: #1a237e; font-size: 20px; margin: 0 0 20px 0; padding-bottom: 10px; border-bottom: 2px solid #e8eaf6;">
                    📊 Fraud Type Breakdown
                </h2>
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fafafa; border-radius: 8px; overflow: hidden;">
                    <tr style="background-color: #e8eaf6;">
                        <td style="padding: 12px 15px; font-weight: 600; color: #1a237e;">Fraud Type</td>
                        <td style="padding: 12px 15px; font-weight: 600; color: #1a237e; text-align: center;">Count</td>
                        <td style="padding: 12px 15px; font-weight: 600; color: #1a237e; text-align: center;">Risk Level</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 12px 15px; color: #424242;">🔀 Split Transactions</td>
                        <td style="padding: 12px 15px; color: #424242; text-align: center;">{split_transactions}</td>
                        <td style="padding: 12px 15px; text-align: center;"><span style="background-color: #ffcdd2; color: #c62828; padding: 4px 12px; border-radius: 12px; font-size: 12px;">High</span></td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 12px 15px; color: #424242;">🔄 Rollover Fraud</td>
                        <td style="padding: 12px 15px; color: #424242; text-align: center;">{rollover_fraud}</td>
                        <td style="padding: 12px 15px; text-align: center;"><span style="background-color: #fff3e0; color: #e65100; padding: 4px 12px; border-radius: 12px; font-size: 12px;">Medium</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 15px; color: #424242;">⚡ Rapid Patterns</td>
                        <td style="padding: 12px 15px; color: #424242; text-align: center;">{rapid_patterns}</td>
                        <td style="padding: 12px 15px; text-align: center;"><span style="background-color: #e3f2fd; color: #1565c0; padding: 4px 12px; border-radius: 12px; font-size: 12px;">Low</span></td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- Suspicious Transactions Details -->
        <tr>
            <td style="padding: 20px 40px;">
                <h2 style="color: #1a237e; font-size: 20px; margin: 0 0 20px 0; padding-bottom: 10px; border-bottom: 2px solid #e8eaf6;">
                    🔍 Suspicious Transaction Details
                </h2>
                {suspicious_transactions_section}
            </td>
        </tr>

        <!-- Footer -->
        <tr>
            <td style="background-color: #f5f5f5; padding: 25px 40px; text-align: center; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0; color: #757575; font-size: 12px;">
                    This report was generated automatically by the Fraud Detection System.
                </p>
                <p style="margin: 10px 0 0 0; color: #9e9e9e; font-size: 11px;">
                    Report ID: {report_id} | Generated: {report_date} {report_time}
                </p>
                <p style="margin: 15px 0 0 0; color: #1a237e; font-size: 13px; font-weight: 600;">
                    ⚠️ Please review flagged transactions and take appropriate action.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
        """

    def _get_agent_companies_from_transactions(self, transactions: List[Dict]) -> List[AgentCompany]:
        """Get agent companies associated with the transactions."""
        agent_companies = []
        seen_ids = set()

        for txn in transactions:
            # Try to find agent company by agent_id or business_shortcode
            agent_id = txn.get('agent_id')
            shortcode = txn.get('business_shortcode')

            if agent_id and agent_id not in seen_ids:
                agent = AgentCompany.query.get(agent_id)
                if agent:
                    agent_companies.append(agent)
                    seen_ids.add(agent_id)

            if shortcode:
                # Try to find by short_code or business_short_code
                agent = AgentCompany.query.filter(
                    db.or_(
                        AgentCompany.short_code == shortcode,
                        AgentCompany.business_short_code == shortcode
                    )
                ).first()
                if agent and agent.id not in seen_ids:
                    agent_companies.append(agent)
                    seen_ids.add(agent.id)

        return agent_companies

    def _get_user_agents_from_agent_companies(self, agent_companies: List[AgentCompany]) -> List[UserAgent]:
        """Get user agents associated with the agent companies."""
        user_agents = []
        seen_ids = set()

        for agent_company in agent_companies:
            for user_agent in agent_company.user_agents:
                if user_agent.id not in seen_ids:
                    user_agents.append(user_agent)
                    seen_ids.add(user_agent.id)

        return user_agents

    def _format_agent_companies_html(self, agent_companies: List[AgentCompany]) -> str:
        """Format agent companies section as HTML."""
        if not agent_companies:
            return '<p style="color: #757575; font-style: italic;">No agent companies identified in flagged transactions.</p>'

        html = ''
        for agent in agent_companies:
            risk_color = {
                'high': '#c62828',
                'medium': '#e65100',
                'low': '#2e7d32'
            }.get(agent.fraud_risk_level.lower() if agent.fraud_risk_level else 'low', '#757575')

            risk_bg = {
                'high': '#ffcdd2',
                'medium': '#fff3e0',
                'low': '#e8f5e9'
            }.get(agent.fraud_risk_level.lower() if agent.fraud_risk_level else 'low', '#f5f5f5')

            html += f'''
            <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                    <div>
                        <h3 style="margin: 0; color: #1a237e; font-size: 16px;">{agent.company_name or agent.organization_name or 'Unknown'}</h3>
                        <p style="margin: 5px 0 0 0; color: #757575; font-size: 13px;">Short Code: <strong>{agent.short_code or agent.business_short_code or 'N/A'}</strong></p>
                    </div>
                    <span style="background-color: {risk_bg}; color: {risk_color}; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                        {agent.fraud_risk_level or 'Unknown'} Risk
                    </span>
                </div>
                <table style="width: 100%; font-size: 13px; color: #424242;">
                    <tr>
                        <td style="padding: 5px 0;"><strong>📍 Location:</strong></td>
                        <td style="padding: 5px 0;">{agent.location or 'N/A'}</td>
                        <td style="padding: 5px 0;"><strong>📞 Contact:</strong></td>
                        <td style="padding: 5px 0;">{agent.contact_phone or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0;"><strong>🏷️ Agent No:</strong></td>
                        <td style="padding: 5px 0;">{agent.agent_number or 'N/A'}</td>
                        <td style="padding: 5px 0;"><strong>🏪 Store No:</strong></td>
                        <td style="padding: 5px 0;">{agent.store_number or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0;"><strong>📊 Status:</strong></td>
                        <td style="padding: 5px 0;">{agent.identity_status or agent.status or 'N/A'}</td>
                        <td style="padding: 5px 0;"><strong>🔒 Trust Level:</strong></td>
                        <td style="padding: 5px 0;">{agent.trust_level or 'N/A'}</td>
                    </tr>
                </table>
                {f'<p style="margin: 15px 0 0 0; padding: 10px; background-color: #fff8e1; border-radius: 4px; font-size: 13px; color: #f57c00;"><strong>⚠️ Risk Note:</strong> {agent.fraud_risk_description}</p>' if agent.fraud_risk_description else ''}
            </div>
            '''
        return html

    def _format_user_agents_html(self, user_agents: List[UserAgent]) -> str:
        """Format user agents section as HTML."""
        if not user_agents:
            return '<p style="color: #757575; font-style: italic;">No user agents identified in flagged transactions.</p>'

        html = '<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fafafa; border-radius: 8px; overflow: hidden;">'
        html += '''
            <tr style="background-color: #e8eaf6;">
                <td style="padding: 12px 15px; font-weight: 600; color: #1a237e;">Name</td>
                <td style="padding: 12px 15px; font-weight: 600; color: #1a237e;">ID Number</td>
                <td style="padding: 12px 15px; font-weight: 600; color: #1a237e;">Phone</td>
                <td style="padding: 12px 15px; font-weight: 600; color: #1a237e; text-align: center;">Verified</td>
                <td style="padding: 12px 15px; font-weight: 600; color: #1a237e;">Companies</td>
            </tr>
        '''

        for i, agent in enumerate(user_agents):
            bg_color = '#ffffff' if i % 2 == 0 else '#fafafa'
            verified_badge = '<span style="background-color: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 12px; font-size: 11px;">✓ Verified</span>' if agent.is_authentic else '<span style="background-color: #ffebee; color: #c62828; padding: 4px 10px; border-radius: 12px; font-size: 11px;">✗ Unverified</span>'
            companies = ', '.join(agent.get_agent_company_names()[:2]) or 'N/A'
            if len(agent.agent_companies) > 2:
                companies += f' +{len(agent.agent_companies) - 2} more'

            html += f'''
            <tr style="background-color: {bg_color}; border-bottom: 1px solid #e0e0e0;">
                <td style="padding: 12px 15px; color: #424242;">
                    <strong>{agent.firstname} {agent.lastname}</strong>
                </td>
                <td style="padding: 12px 15px; color: #424242; font-family: monospace;">{agent.idnumber}</td>
                <td style="padding: 12px 15px; color: #424242;">{agent.phone_number or 'N/A'}</td>
                <td style="padding: 12px 15px; text-align: center;">{verified_badge}</td>
                <td style="padding: 12px 15px; color: #757575; font-size: 12px;">{companies}</td>
            </tr>
            '''

        html += '</table>'
        return html

    def _format_suspicious_transactions_html(self, detections: List[Dict]) -> str:
        """Format suspicious transactions section as HTML with detailed transaction info."""
        if not detections:
            return '<p style="color: #757575; font-style: italic;">No suspicious transactions to display.</p>'

        html = ''
        for idx, detection in enumerate(detections[:15], 1):  # Limit to 15 detections
            fraud_type = detection.get('fraud_type', 'Unknown').replace('_', ' ').title()
            risk_level = detection.get('risk_level', 'MEDIUM')
            account_phone = detection.get('account_phone', 'Unknown')
            account_name = detection.get('account_name', 'Unknown')
            total_amount = detection.get('total_amount', 0)
            fraud_score = detection.get('fraud_score', 0)
            receipt_nos = detection.get('receipt_nos', [])
            explanation = detection.get('explanation', 'No detailed explanation available.')
            txn_details = detection.get('transaction_details', [])

            risk_color = {'HIGH': '#c62828', 'MEDIUM': '#e65100', 'LOW': '#2e7d32'}.get(risk_level, '#757575')
            risk_bg = {'HIGH': '#ffcdd2', 'MEDIUM': '#fff3e0', 'LOW': '#e8f5e9'}.get(risk_level, '#f5f5f5')

            html += f'''
            <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-left: 4px solid {risk_color}; border-radius: 0 8px 8px 0; padding: 15px; margin-bottom: 15px;">
                <!-- Detection Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <span style="font-weight: 700; color: #1a237e; font-size: 15px;">#{idx} {fraud_type}</span>
                    </div>
                    <span style="background-color: {risk_bg}; color: {risk_color}; padding: 5px 14px; border-radius: 15px; font-size: 11px; font-weight: 600;">{risk_level} RISK</span>
                </div>

                <!-- Account Info -->
                <div style="background-color: #fafafa; padding: 10px 12px; border-radius: 6px; margin-bottom: 12px;">
                    <p style="margin: 0 0 5px 0; font-size: 13px; color: #424242;">
                        <strong>📱 Account:</strong> {account_phone} ({account_name or 'Unknown'})
                    </p>
                    <p style="margin: 0; font-size: 13px; color: #424242;">
                        <strong>💰 Total Amount:</strong> KES {total_amount:,.2f} |
                        <strong>📊 Fraud Score:</strong> {fraud_score}/100
                    </p>
                </div>

                <!-- Receipt Numbers -->
                <div style="margin-bottom: 12px;">
                    <p style="margin: 0 0 5px 0; font-size: 12px; color: #757575; font-weight: 600;">RECEIPT NUMBERS:</p>
                    <p style="margin: 0; font-size: 12px; color: #424242; font-family: monospace; word-break: break-all;">
                        {', '.join(receipt_nos[:8])}{'...' if len(receipt_nos) > 8 else ''}
                    </p>
                </div>
            '''

            # Add transaction details table if available
            if txn_details:
                html += '''
                <div style="margin-bottom: 12px;">
                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #757575; font-weight: 600;">TRANSACTION DETAILS:</p>
                    <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                        <tr style="background-color: #e8eaf6;">
                            <th style="padding: 6px 8px; text-align: left; color: #1a237e;">Receipt</th>
                            <th style="padding: 6px 8px; text-align: left; color: #1a237e;">Amount</th>
                            <th style="padding: 6px 8px; text-align: left; color: #1a237e;">Type</th>
                            <th style="padding: 6px 8px; text-align: left; color: #1a237e;">Time</th>
                            <th style="padding: 6px 8px; text-align: left; color: #1a237e;">Party</th>
                        </tr>
                '''
                for i, txn in enumerate(txn_details[:5]):  # Limit to 5 transactions per detection
                    bg = '#ffffff' if i % 2 == 0 else '#fafafa'
                    html += f'''
                        <tr style="background-color: {bg}; border-bottom: 1px solid #e0e0e0;">
                            <td style="padding: 6px 8px; font-family: monospace;">{txn.get('receipt_no', 'N/A')}</td>
                            <td style="padding: 6px 8px;">KES {txn.get('amount', 0):,.2f}</td>
                            <td style="padding: 6px 8px;">{txn.get('type', 'N/A')}</td>
                            <td style="padding: 6px 8px;">{txn.get('time', 'N/A')}</td>
                            <td style="padding: 6px 8px;">{txn.get('party_name') or txn.get('party_phone') or 'N/A'}</td>
                        </tr>
                    '''
                html += '</table>'
                if len(txn_details) > 5:
                    html += f'<p style="margin: 5px 0 0 0; font-size: 11px; color: #757575; font-style: italic;">... and {len(txn_details) - 5} more transactions</p>'
                html += '</div>'

            # Add explanation/reason
            html += f'''
                <!-- Fraud Explanation -->
                <div style="background-color: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; padding: 10px 12px;">
                    <p style="margin: 0 0 5px 0; font-size: 11px; color: #f57c00; font-weight: 600;">⚠️ WHY THIS IS SUSPICIOUS:</p>
                    <p style="margin: 0; font-size: 12px; color: #5d4037; line-height: 1.4;">{explanation}</p>
                </div>
            </div>
            '''

        if len(detections) > 15:
            html += f'<p style="color: #757575; font-size: 13px; text-align: center; margin-top: 10px; font-style: italic;">... and {len(detections) - 15} more suspicious patterns detected</p>'

        return html

    def _parse_other_party_info(self, info: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract phone number and name from Other Party Info."""
        if not info:
            return None, None

        # Extract masked phone number
        phone_match = re.search(r'(\d{3}\*{3}\d{3}|\d{5}\*{3}\d{3})', str(info))
        phone = phone_match.group(1) if phone_match else None

        # Extract name
        name = None
        if ' - ' in str(info):
            name = str(info).split(' - ')[1].strip()

        return phone, name

    def analyze_culpable_agents(self, detections: List[Dict], transactions: List[Dict]) -> Dict:
        """
        Analyze which agents are associated with flagged transactions.
        Returns a dictionary with agent metrics and culpability information.
        """
        # Build a map of transaction_id/receipt_no to transaction details
        txn_map = {}
        for txn in transactions:
            txn_id = txn.get('id')
            receipt_no = txn.get('receipt_no')
            if txn_id:
                txn_map[txn_id] = txn
            if receipt_no:
                txn_map[receipt_no] = txn

        # Collect all flagged transaction IDs and receipt numbers
        flagged_txn_ids = set()
        flagged_receipts = set()
        for detection in detections:
            flagged_txn_ids.update(detection.get('transaction_ids', []))
            flagged_receipts.update(detection.get('receipt_nos', []))

        # Analyze agents involved
        agent_metrics = {}  # agent_id -> metrics
        shortcode_metrics = {}  # business_shortcode -> metrics

        for detection in detections:
            fraud_type = detection.get('fraud_type', 'unknown')
            risk_level = detection.get('risk_level', 'MEDIUM')
            total_amount = detection.get('total_amount', 0)
            txn_count = detection.get('transaction_count', 0)

            # Get transactions for this detection
            for txn_id in detection.get('transaction_ids', []):
                txn = txn_map.get(txn_id) or {}
                agent_id = txn.get('agent_id')
                shortcode = txn.get('business_shortcode')
                company_id = txn.get('company_id')

                # Track by agent_id
                if agent_id:
                    if agent_id not in agent_metrics:
                        agent_metrics[agent_id] = {
                            'agent_id': agent_id,
                            'company_id': company_id,
                            'shortcode': shortcode,
                            'total_fraud_amount': 0,
                            'fraud_count': 0,
                            'high_risk_count': 0,
                            'medium_risk_count': 0,
                            'low_risk_count': 0,
                            'fraud_types': set(),
                            'flagged_receipts': set(),
                            'detections': []
                        }
                    agent_metrics[agent_id]['total_fraud_amount'] += total_amount / max(txn_count, 1)
                    agent_metrics[agent_id]['fraud_count'] += 1
                    agent_metrics[agent_id]['fraud_types'].add(fraud_type)
                    agent_metrics[agent_id]['flagged_receipts'].add(txn.get('receipt_no', ''))
                    if risk_level == 'HIGH':
                        agent_metrics[agent_id]['high_risk_count'] += 1
                    elif risk_level == 'MEDIUM':
                        agent_metrics[agent_id]['medium_risk_count'] += 1
                    else:
                        agent_metrics[agent_id]['low_risk_count'] += 1

                # Track by shortcode
                if shortcode:
                    if shortcode not in shortcode_metrics:
                        shortcode_metrics[shortcode] = {
                            'shortcode': shortcode,
                            'company_id': company_id,
                            'total_fraud_amount': 0,
                            'fraud_count': 0,
                            'high_risk_count': 0,
                            'medium_risk_count': 0,
                            'low_risk_count': 0,
                            'fraud_types': set(),
                            'flagged_receipts': set(),
                            'agent_ids': set()
                        }
                    shortcode_metrics[shortcode]['total_fraud_amount'] += total_amount / max(txn_count, 1)
                    shortcode_metrics[shortcode]['fraud_count'] += 1
                    shortcode_metrics[shortcode]['fraud_types'].add(fraud_type)
                    shortcode_metrics[shortcode]['flagged_receipts'].add(txn.get('receipt_no', ''))
                    if agent_id:
                        shortcode_metrics[shortcode]['agent_ids'].add(agent_id)
                    if risk_level == 'HIGH':
                        shortcode_metrics[shortcode]['high_risk_count'] += 1
                    elif risk_level == 'MEDIUM':
                        shortcode_metrics[shortcode]['medium_risk_count'] += 1
                    else:
                        shortcode_metrics[shortcode]['low_risk_count'] += 1

        # Enrich with agent company details
        culpable_agents = []
        for agent_id, metrics in agent_metrics.items():
            agent_company = AgentCompany.query.get(agent_id)
            if agent_company:
                # Get user agents associated with this agent company
                user_agents_list = list(agent_company.user_agents)

                culpable_agents.append({
                    'agent_id': agent_id,
                    'company_name': agent_company.company_name or agent_company.organization_name,
                    'shortcode': agent_company.short_code or agent_company.business_short_code,
                    'location': agent_company.location,
                    'contact_phone': agent_company.contact_phone,
                    'agent_number': agent_company.agent_number,
                    'store_number': agent_company.store_number,
                    'fraud_risk_level': agent_company.fraud_risk_level,
                    'total_fraud_amount': metrics['total_fraud_amount'],
                    'fraud_count': metrics['fraud_count'],
                    'high_risk_count': metrics['high_risk_count'],
                    'medium_risk_count': metrics['medium_risk_count'],
                    'low_risk_count': metrics['low_risk_count'],
                    'fraud_types': list(metrics['fraud_types']),
                    'flagged_receipts': list(metrics['flagged_receipts'])[:10],  # Limit to 10
                    'user_agents': [
                        {
                            'name': f"{ua.firstname} {ua.lastname}",
                            'id_number': ua.idnumber,
                            'phone': ua.phone_number,
                            'is_verified': ua.is_authentic
                        } for ua in user_agents_list[:5]  # Limit to 5 user agents
                    ]
                })

        # Enrich shortcode metrics with company details
        culpable_shortcodes = []
        for shortcode, metrics in shortcode_metrics.items():
            # Find agent company by shortcode
            agent_company = AgentCompany.query.filter(
                db.or_(
                    AgentCompany.short_code == shortcode,
                    AgentCompany.business_short_code == shortcode
                )
            ).first()

            company_info = {}
            if agent_company:
                company_info = {
                    'company_name': agent_company.company_name or agent_company.organization_name,
                    'location': agent_company.location,
                    'contact_phone': agent_company.contact_phone,
                    'fraud_risk_level': agent_company.fraud_risk_level
                }

            culpable_shortcodes.append({
                'shortcode': shortcode,
                **company_info,
                'total_fraud_amount': metrics['total_fraud_amount'],
                'fraud_count': metrics['fraud_count'],
                'high_risk_count': metrics['high_risk_count'],
                'medium_risk_count': metrics['medium_risk_count'],
                'low_risk_count': metrics['low_risk_count'],
                'fraud_types': list(metrics['fraud_types']),
                'agent_count': len(metrics['agent_ids']),
                'flagged_receipts_count': len(metrics['flagged_receipts'])
            })

        # Sort by fraud amount (highest first)
        culpable_agents.sort(key=lambda x: x['total_fraud_amount'], reverse=True)
        culpable_shortcodes.sort(key=lambda x: x['total_fraud_amount'], reverse=True)

        return {
            'culpable_agents': culpable_agents,
            'culpable_shortcodes': culpable_shortcodes,
            'total_agents_involved': len(culpable_agents),
            'total_shortcodes_involved': len(culpable_shortcodes),
            'total_fraud_amount': sum(a['total_fraud_amount'] for a in culpable_agents)
        }

    def _format_culpable_agents_html(self, culpable_data: Dict) -> str:
        """Format culpable agents section as HTML for the report."""
        culpable_agents = culpable_data.get('culpable_agents', [])

        if not culpable_agents:
            return '<p style="color: #757575; font-style: italic;">No specific agents identified in flagged transactions.</p>'

        html = f'''
        <div style="background-color: #fff3e0; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
            <p style="margin: 0; color: #e65100; font-weight: 600;">
                ⚠️ {len(culpable_agents)} Agent(s) Associated with Suspicious Activity
                | Total Amount at Risk: KES {culpable_data.get('total_fraud_amount', 0):,.2f}
            </p>
        </div>
        '''

        for idx, agent in enumerate(culpable_agents[:10], 1):  # Limit to 10 agents
            risk_color = {
                'high': '#c62828',
                'medium': '#e65100',
                'low': '#2e7d32'
            }.get((agent.get('fraud_risk_level') or 'low').lower(), '#757575')

            risk_bg = {
                'high': '#ffcdd2',
                'medium': '#fff3e0',
                'low': '#e8f5e9'
            }.get((agent.get('fraud_risk_level') or 'low').lower(), '#f5f5f5')

            # Calculate culpability score (simplified)
            culpability_score = min(100, agent['high_risk_count'] * 30 + agent['medium_risk_count'] * 15 + agent['low_risk_count'] * 5)

            html += f'''
            <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-left: 4px solid {risk_color}; border-radius: 0 8px 8px 0; padding: 15px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <div>
                        <h4 style="margin: 0; color: #1a237e; font-size: 15px;">
                            #{idx} {agent.get('company_name', 'Unknown Agent')}
                        </h4>
                        <p style="margin: 3px 0 0 0; color: #757575; font-size: 12px;">
                            Shortcode: <strong>{agent.get('shortcode', 'N/A')}</strong>
                            | Agent #: {agent.get('agent_number', 'N/A')}
                            | Store #: {agent.get('store_number', 'N/A')}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <span style="background-color: {risk_bg}; color: {risk_color}; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                            {(agent.get('fraud_risk_level') or 'Unknown').upper()} RISK
                        </span>
                        <p style="margin: 5px 0 0 0; color: #c62828; font-size: 14px; font-weight: 700;">
                            KES {agent.get('total_fraud_amount', 0):,.2f}
                        </p>
                    </div>
                </div>

                <!-- Fraud Metrics -->
                <div style="display: flex; gap: 15px; margin-bottom: 12px;">
                    <div style="background-color: #ffebee; padding: 8px 12px; border-radius: 6px; text-align: center; flex: 1;">
                        <p style="margin: 0; font-size: 18px; font-weight: 700; color: #c62828;">{agent.get('high_risk_count', 0)}</p>
                        <p style="margin: 2px 0 0 0; font-size: 10px; color: #e57373;">HIGH RISK</p>
                    </div>
                    <div style="background-color: #fff3e0; padding: 8px 12px; border-radius: 6px; text-align: center; flex: 1;">
                        <p style="margin: 0; font-size: 18px; font-weight: 700; color: #e65100;">{agent.get('medium_risk_count', 0)}</p>
                        <p style="margin: 2px 0 0 0; font-size: 10px; color: #ffb74d;">MEDIUM RISK</p>
                    </div>
                    <div style="background-color: #e8f5e9; padding: 8px 12px; border-radius: 6px; text-align: center; flex: 1;">
                        <p style="margin: 0; font-size: 18px; font-weight: 700; color: #2e7d32;">{agent.get('low_risk_count', 0)}</p>
                        <p style="margin: 2px 0 0 0; font-size: 10px; color: #81c784;">LOW RISK</p>
                    </div>
                    <div style="background-color: #e3f2fd; padding: 8px 12px; border-radius: 6px; text-align: center; flex: 1;">
                        <p style="margin: 0; font-size: 18px; font-weight: 700; color: #1565c0;">{agent.get('fraud_count', 0)}</p>
                        <p style="margin: 2px 0 0 0; font-size: 10px; color: #64b5f6;">TOTAL FLAGS</p>
                    </div>
                </div>

                <!-- Fraud Types -->
                <div style="margin-bottom: 12px;">
                    <p style="margin: 0 0 5px 0; font-size: 11px; color: #757575; font-weight: 600;">FRAUD TYPES DETECTED:</p>
                    <div style="display: flex; gap: 5px; flex-wrap: wrap;">
            '''

            fraud_type_colors = {
                'split_transaction': '#9c27b0',
                'rollover_fraud': '#ff9800',
                'rapid_back_forth': '#2196f3'
            }
            for ft in agent.get('fraud_types', []):
                color = fraud_type_colors.get(ft, '#757575')
                html += f'<span style="background-color: {color}20; color: {color}; padding: 3px 8px; border-radius: 10px; font-size: 10px;">{ft.replace("_", " ").title()}</span>'

            html += '''
                    </div>
                </div>
            '''

            # User Agents (people) associated with this agent company
            user_agents = agent.get('user_agents', [])
            if user_agents:
                html += '''
                <div style="background-color: #fafafa; border-radius: 6px; padding: 10px; margin-bottom: 10px;">
                    <p style="margin: 0 0 8px 0; font-size: 11px; color: #757575; font-weight: 600;">👤 ASSOCIATED PERSONNEL:</p>
                    <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                        <tr style="background-color: #e8eaf6;">
                            <th style="padding: 5px 8px; text-align: left; color: #1a237e;">Name</th>
                            <th style="padding: 5px 8px; text-align: left; color: #1a237e;">ID Number</th>
                            <th style="padding: 5px 8px; text-align: left; color: #1a237e;">Phone</th>
                            <th style="padding: 5px 8px; text-align: center; color: #1a237e;">Status</th>
                        </tr>
                '''
                for i, ua in enumerate(user_agents):
                    bg = '#ffffff' if i % 2 == 0 else '#fafafa'
                    verified_badge = '<span style="color: #2e7d32;">✓ Verified</span>' if ua.get('is_verified') else '<span style="color: #c62828;">✗ Unverified</span>'
                    html += f'''
                        <tr style="background-color: {bg};">
                            <td style="padding: 5px 8px;">{ua.get('name', 'N/A')}</td>
                            <td style="padding: 5px 8px; font-family: monospace;">{ua.get('id_number', 'N/A')}</td>
                            <td style="padding: 5px 8px;">{ua.get('phone', 'N/A')}</td>
                            <td style="padding: 5px 8px; text-align: center;">{verified_badge}</td>
                        </tr>
                    '''
                html += '</table></div>'

            # Flagged Receipts
            flagged_receipts = agent.get('flagged_receipts', [])
            if flagged_receipts:
                html += f'''
                <div style="margin-top: 10px;">
                    <p style="margin: 0 0 5px 0; font-size: 11px; color: #757575; font-weight: 600;">FLAGGED RECEIPT NOS:</p>
                    <p style="margin: 0; font-size: 11px; color: #424242; font-family: monospace; word-break: break-all;">
                        {', '.join(flagged_receipts[:8])}{'...' if len(flagged_receipts) > 8 else ''}
                    </p>
                </div>
                '''

            html += '</div>'

        if len(culpable_agents) > 10:
            html += f'<p style="color: #757575; font-size: 12px; text-align: center; font-style: italic;">... and {len(culpable_agents) - 10} more agents with suspicious activity</p>'

        return html

    def _format_culpable_agents_plain_text(self, culpable_data: Dict) -> str:
        """Format culpable agents as plain text for periodic notifications."""
        culpable_agents = culpable_data.get('culpable_agents', [])

        if not culpable_agents:
            return "No specific agents identified in flagged transactions."

        lines = [
            "=" * 60,
            "CULPABLE AGENTS ANALYSIS",
            "=" * 60,
            f"Total Agents Involved: {len(culpable_agents)}",
            f"Total Amount at Risk: KES {culpable_data.get('total_fraud_amount', 0):,.2f}",
            "-" * 60,
            ""
        ]

        for idx, agent in enumerate(culpable_agents[:10], 1):
            lines.append(f"#{idx} {agent.get('company_name', 'Unknown Agent')}")
            lines.append(f"    Shortcode: {agent.get('shortcode', 'N/A')}")
            lines.append(f"    Agent/Store #: {agent.get('agent_number', 'N/A')} / {agent.get('store_number', 'N/A')}")
            lines.append(f"    Location: {agent.get('location', 'N/A')}")
            lines.append(f"    Contact: {agent.get('contact_phone', 'N/A')}")
            lines.append(f"    Fraud Amount: KES {agent.get('total_fraud_amount', 0):,.2f}")
            lines.append(f"    Risk Counts: HIGH={agent.get('high_risk_count', 0)}, MEDIUM={agent.get('medium_risk_count', 0)}, LOW={agent.get('low_risk_count', 0)}")
            lines.append(f"    Fraud Types: {', '.join(agent.get('fraud_types', []))}")

            # User agents
            user_agents = agent.get('user_agents', [])
            if user_agents:
                lines.append("    Associated Personnel:")
                for ua in user_agents[:3]:
                    verified = "Verified" if ua.get('is_verified') else "Unverified"
                    lines.append(f"      - {ua.get('name', 'N/A')} (ID: {ua.get('id_number', 'N/A')}, {verified})")

            lines.append("")

        if len(culpable_agents) > 10:
            lines.append(f"... and {len(culpable_agents) - 10} more agents with suspicious activity")

        return "\n".join(lines)
    
    def detect_split_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Detect split transactions with configurable thresholds."""
        if not transactions or len(transactions) < self.config['split_threshold']:
            return []

        # Get configurable thresholds
        split_threshold = self.config.get('split_threshold', 5)
        time_window = self.config.get('time_window_minutes', 5)
        split_min_amount = self.config.get('split_min_amount', 100.0)
        split_max_amount = self.config.get('split_max_amount', 50000.0)
        split_total_threshold = self.config.get('split_total_amount_threshold', 10000.0)
        amount_variance = self.config.get('amount_variance', 0.1)

        # Sort by time
        sorted_txns = sorted(transactions, key=lambda x: x['completion_time'])

        results = []
        i = 0

        while i < len(sorted_txns) - 1:
            current = sorted_txns[i]
            phone = current.get('phone_number')

            if not phone:
                i += 1
                continue

            # Find transactions in time window
            window_txns = []
            j = i
            while j < len(sorted_txns):
                txn = sorted_txns[j]
                if txn.get('phone_number') != phone:
                    break

                time_diff = (txn['completion_time'] - current['completion_time']).total_seconds() / 60
                if time_diff <= time_window:
                    # Filter by amount thresholds
                    txn_amount = abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0))
                    if split_min_amount <= txn_amount <= split_max_amount:
                        window_txns.append((j, txn))
                j += 1

            # Group by similar amounts
            if len(window_txns) >= split_threshold:
                amount_groups = defaultdict(list)
                for idx, txn in window_txns:
                    amount = abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0))

                    # Find similar amount group
                    found = False
                    for group_amount in amount_groups:
                        if abs(amount - group_amount) / max(group_amount, 1) <= amount_variance:
                            amount_groups[group_amount].append((idx, txn))
                            found = True
                            break

                    if not found:
                        amount_groups[amount].append((idx, txn))

                # Check each group
                for amount, group in amount_groups.items():
                    total_amount = sum(abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0)) for _, txn in group)

                    # Only flag if meets both count AND total amount thresholds
                    if len(group) >= split_threshold and total_amount >= split_total_threshold:
                        # Collect agent/company info from transactions
                        agent_info = self._extract_agent_info_from_transactions([txn for _, txn in group])

                        # Build transaction details list
                        transaction_details = []
                        for _, txn in group:
                            txn_amount = abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0))
                            txn_type = 'Deposit' if float(txn.get('paid_in') or 0) > 0 else 'Withdrawal'
                            txn_time = txn['completion_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(txn['completion_time'], 'strftime') else str(txn['completion_time'])
                            transaction_details.append({
                                'receipt_no': txn['receipt_no'],
                                'amount': txn_amount,
                                'type': txn_type,
                                'time': txn_time,
                                'party_phone': txn.get('phone_number'),
                                'party_name': txn.get('name'),
                                'other_party_info': txn.get('other_party_info', ''),
                                'business_shortcode': txn.get('business_shortcode'),
                                'agent_id': txn.get('agent_id')
                            })

                        time_span = (group[-1][1]['completion_time'] - group[0][1]['completion_time']).total_seconds() / 60 if len(group) > 1 else 0

                        # Build detailed explanation
                        explanation = (
                            f"SPLIT TRANSACTION FRAUD DETECTED: {len(group)} transactions of similar amounts "
                            f"(~KES {amount:,.2f} each) were made within {time_span:.1f} minutes. "
                            f"Total amount: KES {total_amount:,.2f}. "
                            f"This pattern suggests intentional splitting of a larger transaction to avoid detection thresholds."
                        )

                        # Create detection result with agent info
                        result = {
                            'fraud_type': 'split_transaction',
                            'account_phone': phone,
                            'account_name': current.get('name'),
                            'transaction_count': len(group),
                            'total_amount': total_amount,
                            'avg_amount': amount,
                            'time_window': time_window,
                            'receipt_nos': [txn['receipt_no'] for _, txn in group],
                            'transaction_ids': [txn['id'] for _, txn in group],
                            'transaction_details': transaction_details,
                            'explanation': explanation,
                            'detection_time': datetime.now(),
                            'fraud_score': min(30 + len(group) * 10, 100),
                            # Agent/Company info
                            'agent_info': agent_info,
                            'business_shortcode': current.get('business_shortcode'),
                        }
                        results.append(result)

            i = j  # Move to next account

        return results

    def _extract_agent_info_from_transactions(self, transactions: List[Dict]) -> Dict:
        """Extract agent and company information from transactions."""
        agent_info = {
            'agent_companies': [],
            'user_agents': [],
            'shortcodes': set()
        }

        for txn in transactions:
            shortcode = txn.get('business_shortcode')
            agent_id = txn.get('agent_id')

            if shortcode:
                agent_info['shortcodes'].add(shortcode)

            # Try to find agent company
            if shortcode or agent_id:
                try:
                    query = AgentCompany.query
                    if agent_id:
                        agent_company = query.filter_by(id=agent_id).first()
                    elif shortcode:
                        agent_company = query.filter(
                            db.or_(
                                AgentCompany.short_code == shortcode,
                                AgentCompany.business_short_code == shortcode
                            )
                        ).first()
                    else:
                        agent_company = None

                    if agent_company and agent_company.id not in [ac['id'] for ac in agent_info['agent_companies']]:
                        agent_info['agent_companies'].append({
                            'id': agent_company.id,
                            'company_name': agent_company.company_name,
                            'short_code': agent_company.short_code,
                            'location': agent_company.location,
                            'fraud_risk_level': agent_company.fraud_risk_level,
                            'agent_number': agent_company.agent_number,
                            'store_number': agent_company.store_number
                        })

                        # Get associated user agents
                        for user_agent in agent_company.user_agents:
                            if user_agent.id not in [ua['id'] for ua in agent_info['user_agents']]:
                                agent_info['user_agents'].append({
                                    'id': user_agent.id,
                                    'name': f"{user_agent.firstname} {user_agent.lastname}",
                                    'idnumber': user_agent.idnumber,
                                    'phone_number': user_agent.phone_number,
                                    'is_authentic': user_agent.is_authentic
                                })
                except Exception as e:
                    logger.warning(f"Could not fetch agent info: {e}")

        agent_info['shortcodes'] = list(agent_info['shortcodes'])
        return agent_info
    
    def detect_rollover_fraud(self, transactions: List[Dict]) -> List[Dict]:
        """Detect roll-over fraud patterns."""
        if not transactions:
            return []
        
        # Group by account
        account_txns = defaultdict(list)
        for txn in transactions:
            phone = txn.get('phone_number')
            if phone:
                account_txns[phone].append(txn)
        
        results = []
        
        for phone, txns in account_txns.items():
            # Sort by time
            sorted_txns = sorted(txns, key=lambda x: x['completion_time'])
            
            # Group by type
            deposits = [t for t in sorted_txns if float(t.get('paid_in') or 0) > 0]
            withdrawals = [t for t in sorted_txns if float(t.get('withdrawn') or 0) > 0]
            
            # Check deposit patterns
            if len(deposits) >= self.config['min_transactions_rollover']:
                cluster = self._find_time_cluster(deposits)
                if cluster and len(cluster) >= self.config['min_transactions_rollover']:
                    results.append(self._create_rollover_result(
                        phone, cluster, 'DEPOSIT', sorted_txns[0].get('name')
                    ))
            
            # Check withdrawal patterns
            if len(withdrawals) >= self.config['min_transactions_rollover']:
                cluster = self._find_time_cluster(withdrawals)
                if cluster and len(cluster) >= self.config['min_transactions_rollover']:
                    results.append(self._create_rollover_result(
                        phone, cluster, 'WITHDRAWAL', sorted_txns[0].get('name')
                    ))
        
        return results
    
    def _find_time_cluster(self, transactions: List[Dict]) -> List[Dict]:
        """Find clusters of transactions in time window."""
        if not transactions:
            return []
        
        sorted_txns = sorted(transactions, key=lambda x: x['completion_time'])
        clusters = []
        current_cluster = [sorted_txns[0]]
        
        for i in range(1, len(sorted_txns)):
            prev_time = current_cluster[-1]['completion_time']
            curr_time = sorted_txns[i]['completion_time']
            time_diff = (curr_time - prev_time).total_seconds() / 60
            
            if time_diff <= self.config['time_window_minutes'] * 2:
                current_cluster.append(sorted_txns[i])
            else:
                if len(current_cluster) >= self.config['min_transactions_rollover']:
                    clusters.append(current_cluster)
                current_cluster = [sorted_txns[i]]
        
        if len(current_cluster) >= self.config['min_transactions_rollover']:
            clusters.append(current_cluster)
        
        # Return largest cluster
        return max(clusters, key=len) if clusters else []
    
    def _create_rollover_result(self, phone: str, transactions: List[Dict],
                                pattern_type: str, name: str = None) -> Dict:
        """Create rollover fraud detection result."""
        amounts = [abs(float(t.get('paid_in') or t.get('withdrawn') or 0)) for t in transactions]

        # Build transaction details list
        transaction_details = []
        for txn in transactions:
            txn_amount = abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0))
            txn_type = 'Deposit' if float(txn.get('paid_in') or 0) > 0 else 'Withdrawal'
            txn_time = txn['completion_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(txn['completion_time'], 'strftime') else str(txn['completion_time'])
            transaction_details.append({
                'receipt_no': txn['receipt_no'],
                'amount': txn_amount,
                'type': txn_type,
                'time': txn_time,
                'party_phone': txn.get('phone_number'),
                'party_name': txn.get('name'),
                'other_party_info': txn.get('other_party_info', ''),
                'business_shortcode': txn.get('business_shortcode'),
                'agent_id': txn.get('agent_id')
            })

        # Extract agent info for the transactions
        agent_info = self._extract_agent_info_from_transactions(transactions)

        total_amount = sum(amounts)
        avg_amount = sum(amounts) / len(amounts) if amounts else 0

        # Calculate time span
        if len(transactions) > 1:
            time_span = (transactions[-1]['completion_time'] - transactions[0]['completion_time']).total_seconds() / 60
        else:
            time_span = 0

        # Get first transaction's shortcode
        first_shortcode = transactions[0].get('business_shortcode') if transactions else None

        # Build detailed explanation
        explanation = (
            f"ROLLOVER FRAUD DETECTED: {len(transactions)} consecutive {pattern_type.lower()} transactions "
            f"detected from the same account ({phone}) within {time_span:.1f} minutes. "
            f"Total amount: KES {total_amount:,.2f} (average KES {avg_amount:,.2f} per transaction). "
            f"This pattern indicates potential roll-over fraud where funds are repeatedly "
            f"{'deposited' if pattern_type == 'DEPOSIT' else 'withdrawn'} in quick succession, "
            f"possibly to generate fraudulent commissions or circumvent transaction limits."
        )

        return {
            'fraud_type': 'rollover_fraud',
            'account_phone': phone,
            'account_name': name,
            'pattern_type': pattern_type,
            'transaction_count': len(transactions),
            'total_amount': total_amount,
            'avg_amount': avg_amount,
            'time_window': self.config['time_window_minutes'],
            'receipt_nos': [t['receipt_no'] for t in transactions],
            'transaction_ids': [t['id'] for t in transactions],
            'transaction_details': transaction_details,
            'explanation': explanation,
            'detection_time': datetime.now(),
            'fraud_score': min(50 + len(transactions) * 5, 100),
            # Agent/Company info
            'agent_info': agent_info,
            'business_shortcode': first_shortcode,
        }
    
    def parse_datetime(self, date_str):
        """Parse datetime from string, handling multiple formats."""
        if date_str is None:
            return None
        
        # If it's already a datetime object, return it
        if isinstance(date_str, datetime):
            return date_str
        
        # If it's a string, parse it
        if isinstance(date_str, str):
            # Try different datetime formats
            formats = [
                '%Y-%m-%d %H:%M:%S',  # 2026-01-13 21:42:17
                '%Y-%m-%dT%H:%M:%S',  # 2026-01-13T21:42:17
                '%Y-%m-%d %H:%M:%S.%f',  # With microseconds
                '%d/%m/%Y %H:%M:%S',  # 13/01/2026 21:42:17
                '%d-%m-%Y %H:%M:%S',  # 13-01-2026 21:42:17
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # If none of the formats work, try to parse with dateutil (if available)
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except ImportError:
                pass
            
            logger.warning(f"Could not parse datetime: {date_str}")
            return None
        
        return None
    
    def detect_rapid_back_forth(self, transactions: List[Dict]) -> List[Dict]:
        """Detect rapid deposit-withdrawal patterns."""
        if not transactions:
            return []
        
        # Sort by time
        sorted_txns = sorted(transactions, key=lambda x: x.get('completion_time'))
        
        results = []
        i = 0
        
        while i < len(sorted_txns) - 1:
            current = sorted_txns[i]
            next_txn = sorted_txns[i + 1]
            
            if current.get('phone_number') != next_txn.get('phone_number'):
                i += 1
                continue
            
            # Parse dates safely
            current_time = self.parse_datetime(current.get('completion_time'))
            next_time = self.parse_datetime(next_txn.get('completion_time'))
            
            if not current_time or not next_time:
                i += 1
                continue
            
            time_diff = (next_time - current_time).total_seconds() / 60
            
            if time_diff <= self.config['time_window_minutes']:
                # Check for opposite types
                current_type = 'DEPOSIT' if float(current.get('paid_in') or 0) > 0 else 'WITHDRAWAL'
                next_type = 'DEPOSIT' if float(next_txn.get('paid_in') or 0) > 0 else 'WITHDRAWAL'
                
                if current_type != next_type:
                    current_amount = abs(float(current.get('paid_in') or current.get('withdrawn') or 0))
                    next_amount = abs(float(next_txn.get('paid_in') or next_txn.get('withdrawn') or 0))

                    # Check amount similarity (within 30%)
                    if abs(current_amount - next_amount) / max(current_amount, 1) <= 0.3:
                        net_flow = (float(current.get('paid_in') or 0) - float(current.get('withdrawn') or 0) +
                                   float(next_txn.get('paid_in') or 0) - float(next_txn.get('withdrawn') or 0))

                        # Build transaction details
                        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(current_time, 'strftime') else str(current_time)
                        next_time_str = next_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(next_time, 'strftime') else str(next_time)

                        transaction_details = [
                            {
                                'receipt_no': current['receipt_no'],
                                'amount': current_amount,
                                'type': current_type.capitalize(),
                                'time': current_time_str,
                                'party_phone': current.get('phone_number'),
                                'party_name': current.get('name'),
                                'other_party_info': current.get('other_party_info', ''),
                                'business_shortcode': current.get('business_shortcode'),
                                'agent_id': current.get('agent_id')
                            },
                            {
                                'receipt_no': next_txn['receipt_no'],
                                'amount': next_amount,
                                'type': next_type.capitalize(),
                                'time': next_time_str,
                                'party_phone': next_txn.get('phone_number'),
                                'party_name': next_txn.get('name'),
                                'other_party_info': next_txn.get('other_party_info', ''),
                                'business_shortcode': next_txn.get('business_shortcode'),
                                'agent_id': next_txn.get('agent_id')
                            }
                        ]

                        # Extract agent info for the transactions
                        agent_info = self._extract_agent_info_from_transactions([current, next_txn])

                        # Build detailed explanation
                        explanation = (
                            f"RAPID BACK-FORTH PATTERN DETECTED: A {current_type.lower()} of KES {current_amount:,.2f} "
                            f"followed by a {next_type.lower()} of KES {next_amount:,.2f} within {time_diff:.1f} minutes. "
                            f"Account: {current.get('phone_number')} ({current.get('name') or 'Unknown'}). "
                            f"Net flow: KES {net_flow:,.2f}. "
                            f"This rapid deposit-withdrawal pattern with similar amounts suggests potential "
                            f"money laundering, fraudulent commission generation, or testing of account limits."
                        )

                        result = {
                            'fraud_type': 'rapid_back_forth',
                            'account_phone': current.get('phone_number'),
                            'account_name': current.get('name'),
                            'transaction_count': 2,
                            'total_amount': current_amount + next_amount,
                            'net_flow': net_flow,
                            'time_window': time_diff,
                            'receipt_nos': [current['receipt_no'], next_txn['receipt_no']],
                            'transaction_ids': [current.get('id'), next_txn.get('id')],
                            'transaction_details': transaction_details,
                            'explanation': explanation,
                            'detection_time': datetime.now(),
                            'fraud_score': 40,
                            # Agent/Company info
                            'agent_info': agent_info,
                            'business_shortcode': current.get('business_shortcode'),
                        }
                        results.append(result)
            
            i += 1
        
        return results
    
    def run_detection(self, transactions: List[Dict]) -> Dict:
        """Run all fraud detection algorithms."""
        logger.info(f"Starting fraud detection on {len(transactions)} transactions")
        
        # Parse phone numbers and names
        for txn in transactions:
            phone, name = self._parse_other_party_info(txn.get('other_party_info', ''))
            txn['phone_number'] = phone
            txn['name'] = name
        
        # Run detections
        split_results = self.detect_split_transactions(transactions)
        rollover_results = self.detect_rollover_fraud(transactions)
        rapid_results = self.detect_rapid_back_forth(transactions)
        
        # Combine results
        all_results = split_results + rollover_results + rapid_results
        
        # Calculate risk levels
        for result in all_results:
            score = result.get('fraud_score', 0)
            if score >= self.config['high_risk_score']:
                result['risk_level'] = 'HIGH'
            elif score >= self.config['medium_risk_score']:
                result['risk_level'] = 'MEDIUM'
            else:
                result['risk_level'] = 'LOW'
        
        # Group by account
        account_results = defaultdict(list)
        for result in all_results:
            account_results[result['account_phone']].append(result)
        
        # Analyze culpable agents
        culpable_data = self.analyze_culpable_agents(all_results, transactions)

        # Create summary
        summary = {
            'total_transactions_analyzed': len(transactions),
            'suspicious_patterns_found': len(all_results),
            'accounts_flagged': len(account_results),
            'split_transactions': len(split_results),
            'rollover_fraud': len(rollover_results),
            'rapid_patterns': len(rapid_results),
            'high_risk_count': sum(1 for r in all_results if r.get('risk_level') == 'HIGH'),
            'medium_risk_count': sum(1 for r in all_results if r.get('risk_level') == 'MEDIUM'),
            'detection_time': datetime.now(),
            'culpable_agents_count': culpable_data.get('total_agents_involved', 0),
            'total_fraud_amount': culpable_data.get('total_fraud_amount', 0)
        }

        return {
            'summary': summary,
            'detections': all_results,
            'account_summary': account_results,
            'culpable_agents': culpable_data
        }
    
    def _format_transaction_details_plain_text(self, transaction_details: List[Dict]) -> str:
        """Format transaction details as plain text for notifications."""
        if not transaction_details:
            return "No transaction details available."

        lines = []
        for i, txn in enumerate(transaction_details, 1):
            receipt_no = txn.get('receipt_no', 'N/A')
            amount = txn.get('amount', 0)
            txn_type = txn.get('type', 'N/A')
            time = txn.get('time', 'N/A')
            party_phone = txn.get('party_phone', 'N/A')
            party_name = txn.get('party_name', 'Unknown')

            lines.append(f"{i}. Receipt: {receipt_no}")
            lines.append(f"   Amount: KES {amount:,.2f}")
            lines.append(f"   Type: {txn_type}")
            lines.append(f"   Time: {time}")
            lines.append(f"   Party: {party_name} ({party_phone})")
            lines.append("")

        return "\n".join(lines)

    def send_fraud_notification(self, detection_result: Dict, fraud_type: str):
        """Send fraud notification email (plain text for CPU efficiency)."""
        if not self.user or not self.user.email:
            logger.warning("No user or email configured for fraud notifications")
            return

        template = self.email_templates.get(fraud_type)
        if not template:
            logger.error(f"No template found for fraud type: {fraud_type}")
            return

        # Check alert limit for this receipt group
        receipt_nos = detection_result.get('receipt_nos', [])
        if self._should_limit_alerts(receipt_nos):
            logger.info(f"Alert limit reached for receipt group: {receipt_nos}")
            return

        # Format receipt numbers as plain text
        receipt_numbers_text = ", ".join(receipt_nos) if receipt_nos else "None"

        # Format transaction details as plain text
        transaction_details = detection_result.get('transaction_details', [])
        transaction_details_text = self._format_transaction_details_plain_text(transaction_details)

        # Get common fields
        detection_time = detection_result['detection_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(detection_result.get('detection_time'), 'strftime') else str(detection_result.get('detection_time', 'Unknown'))
        account_phone = detection_result.get('account_phone', 'Unknown')
        account_name = detection_result.get('account_name', 'Unknown')
        risk_level = detection_result.get('risk_level', 'MEDIUM')
        fraud_score = detection_result.get('fraud_score', 0)
        transaction_count = detection_result.get('transaction_count', 0)
        total_amount = detection_result.get('total_amount', 0)
        avg_amount = detection_result.get('avg_amount', total_amount / max(transaction_count, 1))
        explanation = detection_result.get('explanation', 'No detailed explanation available.')

        # Fill template based on fraud type
        if fraud_type == 'split_transaction':
            body = template['template'].format(
                detection_time=detection_time,
                risk_level=risk_level,
                fraud_score=fraud_score,
                account_phone=account_phone,
                account_name=account_name,
                transaction_count=transaction_count,
                total_amount=total_amount,
                avg_amount=avg_amount,
                receipt_numbers=receipt_numbers_text,
                transaction_details=transaction_details_text,
                explanation=explanation
            )
        elif fraud_type == 'rollover_fraud':
            body = template['template'].format(
                detection_time=detection_time,
                risk_level=risk_level,
                fraud_score=fraud_score,
                account_phone=account_phone,
                account_name=account_name,
                pattern_type=detection_result.get('pattern_type', 'Unknown'),
                transaction_count=transaction_count,
                total_amount=total_amount,
                avg_amount=avg_amount,
                receipt_numbers=receipt_numbers_text,
                transaction_details=transaction_details_text,
                explanation=explanation
            )
        elif fraud_type == 'rapid_back_forth':
            body = template['template'].format(
                detection_time=detection_time,
                risk_level=risk_level,
                fraud_score=fraud_score,
                account_phone=account_phone,
                account_name=account_name,
                transaction_count=transaction_count,
                time_window=detection_result.get('time_window', 0),
                net_flow=detection_result.get('net_flow', 0),
                receipt_numbers=receipt_numbers_text,
                transaction_details=transaction_details_text,
                explanation=explanation
            )
        else:
            return

        # Send email (plain text - not HTML)
        try:
            _send_email(
                subject=f"[Fraud Alert] {template['subject']}",
                body=body,
                recipient=self.user.email,
                is_html=False  # Plain text for CPU efficiency
            )
            logger.info(f"Sent {fraud_type} alert to {self.user.email}")

            # Record alert
            self._record_fraud_alert(detection_result, fraud_type)

        except Exception as e:
            logger.error(f"Failed to send fraud notification: {str(e)}")
    
    def send_historical_report(self, report_data: Dict, transactions: List[Dict] = None, detections: List[Dict] = None):
        """Send historical fraud analysis report with agent company, user agent, and culpable agents details."""
        if not self.user or not self.user.email:
            return

        # Get agent companies and user agents from transactions
        agent_companies = []
        user_agents = []
        if transactions:
            agent_companies = self._get_agent_companies_from_transactions(transactions)
            user_agents = self._get_user_agents_from_agent_companies(agent_companies)

        # Analyze culpable agents
        culpable_data = {}
        if detections and transactions:
            culpable_data = self.analyze_culpable_agents(detections, transactions)

        # Format HTML sections
        agent_companies_html = self._format_agent_companies_html(agent_companies)
        user_agents_html = self._format_user_agents_html(user_agents)
        suspicious_txns_html = self._format_suspicious_transactions_html(detections or [])
        culpable_agents_html = self._format_culpable_agents_html(culpable_data)

        template = self.email_templates['historical_report']
        now = datetime.now()

        body = template['template'].format(
            report_date=now.strftime('%Y-%m-%d'),
            report_time=now.strftime('%H:%M:%S'),
            report_id=f"FR-{now.strftime('%Y%m%d%H%M%S')}-{self.user.id}",
            analysis_period=self.config['analysis_period_days'],
            total_transactions=report_data.get('total_transactions_analyzed', 0),
            suspicious_patterns=report_data.get('suspicious_patterns_found', 0),
            accounts_flagged=report_data.get('accounts_flagged', 0),
            high_risk_count=report_data.get('high_risk_count', 0),
            split_transactions=report_data.get('split_transactions', 0),
            rollover_fraud=report_data.get('rollover_fraud', 0),
            rapid_patterns=report_data.get('rapid_patterns', 0),
            agent_companies_section=agent_companies_html,
            user_agents_section=user_agents_html,
            culpable_agents_section=culpable_agents_html,
            suspicious_transactions_section=suspicious_txns_html
        )

        try:
            _send_email(
                subject=f"🛡️ Fraud Detection Report - {now.strftime('%Y-%m-%d')}",
                body=body,
                recipient=self.user.email,
                is_html=True
            )
            logger.info(f"Sent historical report to {self.user.email}")

            # Record report history
            self._record_report_history(report_data)

        except Exception as e:
            logger.error(f"Failed to send historical report: {str(e)}")
    
    def _should_limit_alerts(self, receipt_nos: List[str]) -> bool:
        """Check if alerts should be limited for this receipt group."""        
        if not receipt_nos:
            return False
        
        # Sort and create hash
        receipt_hash = hash(tuple(sorted(receipt_nos)))
        
        # Check existing alerts for this group
        alert_count = FraudAlert.query.filter_by(
            receipt_hash=receipt_hash,
            created_at__gte=datetime.now() - timedelta(days=1)  # Last 24 hours
        ).count()
        
        return alert_count >= self.config['max_alerts_per_group']
    
    def _record_fraud_alert(self, detection_result: Dict, fraud_type: str):
        """Record fraud alert in database."""
        try:
            alert = FraudAlert(
                user_id=self.user.id,
                fraud_type=fraud_type,
                account_phone=detection_result.get('account_phone'),
                account_name=detection_result.get('account_name'),
                transaction_count=detection_result.get('transaction_count'),
                total_amount=Decimal(str(detection_result.get('total_amount', 0))),
                fraud_score=detection_result.get('fraud_score', 0),
                risk_level=detection_result.get('risk_level', 'MEDIUM'),
                receipt_nos=','.join(detection_result.get('receipt_nos', [])),
                transaction_ids=','.join(str(id) for id in detection_result.get('transaction_ids', [])),
                receipt_hash=hash(tuple(sorted(detection_result.get('receipt_nos', [])))),
                detection_details=detection_result
            )
            db.session.add(alert)
            db.session.commit()
            logger.info(f"Recorded fraud alert for {fraud_type}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record fraud alert: {str(e)}")
    
    def _serialize_for_json(self, obj):
        """Convert datetime and other non-serializable objects to JSON-safe format."""
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, tuple):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__') and not isinstance(obj, type):
            return str(obj)
        return obj

    def _record_report_history(self, report_data: Dict):
        """Record report history in database."""

        try:
            # Serialize report_data to handle datetime objects
            serialized_report = self._serialize_for_json(report_data)

            history = FraudReportHistory(
                user_id=self.user.id,
                analysis_period_days=self.config['analysis_period_days'],
                total_transactions=report_data.get('total_transactions_analyzed', 0),
                suspicious_patterns=report_data.get('suspicious_patterns_found', 0),
                accounts_flagged=report_data.get('accounts_flagged', 0),
                report_data=serialized_report
            )
            db.session.add(history)
            db.session.commit()
            logger.info("Recorded fraud report history")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record report history: {str(e)}")