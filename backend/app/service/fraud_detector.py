import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Tuple, Optional, Union
from app.utils.email_utils import _send_email
from app.model.user import User
import json

class FraudDetectionSystem:
    """
    Comprehensive fraud detection system for transaction monitoring
    with email notification capabilities.
    """
    
    def __init__(self, config: Dict = None, user: User = None):
        """
        Initialize the fraud detection system.
        
        Args:
            config: Configuration dictionary with email settings and detection parameters
        """
        # Default configuration
        self.default_config = {
            'time_window_minutes': 5,
            'amount_variance': 0.1,  # 10%
            'min_transactions_rollover': 3,
            'split_threshold': 2,
            'rapid_back_forth_threshold': 2,
            'high_risk_score': 50,
            'medium_risk_score': 30,
            
            # Email configuration
            'email_enabled': False,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': '',
            'sender_password': '',
            'recipient_emails': [],
            'email_subject_prefix': '[Fraud Alert] ',
            
            # Notification thresholds
            'notify_high_risk': True,
            'notify_medium_risk': False,
            'notify_split_transactions': True,
            'notify_rollover_fraud': True,
            'notify_rapid_patterns': True
        }
        
        # Update with provided config
        self.config = {**self.default_config, **(config or {})}
        
        # Data storage
        self.df = None
        self.detected_fraud = None
        self.report = None
        self.user = user
        
        # Template cache
        self.email_templates = self._load_email_templates()
        
    def _load_email_templates(self) -> Dict:
        """Load email templates for different fraud types."""
        return {
            'split_transaction': {
                'subject': 'Split Transaction Fraud Detected',
                'template': """
                <html>
                <body>
                <h2>🚨 Split Transaction Fraud Alert</h2>
                <p><strong>Detection Time:</strong> {detection_time}</p>
                <p><strong>Transaction Period:</strong> {period}</p>
                
                <h3>📊 Summary</h3>
                <ul>
                <li><strong>Account:</strong> {account_phone} ({account_name})</li>
                <li><strong>Number of Split Transactions:</strong> {transaction_count}</li>
                <li><strong>Total Amount Involved:</strong> KES {total_amount:,.2f}</li>
                <li><strong>Time Window:</strong> {time_window} minutes</li>
                <li><strong>Fraud Score:</strong> {fraud_score}/100</li>
                </ul>
                
                <h3>🔍 Transaction Details</h3>
                <table border="1" cellpadding="5" cellspacing="0">
                <tr style="background-color: #f2f2f2;">
                    <th>Receipt No.</th>
                    <th>Time</th>
                    <th>Amount (KES)</th>
                    <th>Type</th>
                </tr>
                {transaction_rows}
                </table>
                
                <h3>📈 Pattern Analysis</h3>
                <p>{pattern_analysis}</p>
                
                <h3>⚠️ Recommended Actions</h3>
                <ol>
                <li>Review account transaction history</li>
                <li>Contact customer for verification</li>
                <li>Temporarily restrict account if suspicious</li>
                <li>Report to compliance department</li>
                </ol>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                This is an automated fraud detection alert. Please investigate promptly.
                </p>
                </body>
                </html>
                """
            },
            
            'rollover_fraud': {
                'subject': 'Roll-over Fraud Pattern Detected',
                'template': """
                <html>
                <body>
                <h2>🔄 Roll-over Fraud Alert</h2>
                <p><strong>Detection Time:</strong> {detection_time}</p>
                <p><strong>Pattern Period:</strong> {period}</p>
                
                <h3>📊 Summary</h3>
                <ul>
                <li><strong>Account:</strong> {account_phone} ({account_name})</li>
                <li><strong>Number of Transactions:</strong> {transaction_count}</li>
                <li><strong>Transaction Type:</strong> {transaction_type}s</li>
                <li><strong>Average Amount:</strong> KES {avg_amount:,.2f}</li>
                <li><strong>Time Window:</strong> {time_window} minutes</li>
                <li><strong>Risk Level:</strong> {risk_level}</li>
                </ul>
                
                <h3>🔍 Transaction Pattern</h3>
                <table border="1" cellpadding="5" cellspacing="0">
                <tr style="background-color: #f2f2f2;">
                    <th>Receipt No.</th>
                    <th>Time</th>
                    <th>Amount (KES)</th>
                    <th>Interval (mins)</th>
                </tr>
                {transaction_rows}
                </table>
                
                <h3>🎯 Pattern Characteristics</h3>
                <ul>
                <li><strong>Frequency:</strong> {frequency}</li>
                <li><strong>Consistency:</strong> {consistency}</li>
                <li><strong>Total Volume:</strong> KES {total_volume:,.2f}</li>
                </ul>
                
                <h3>⚠️ Risk Assessment</h3>
                <p>{risk_assessment}</p>
                
                <h3>🛡️ Recommended Actions</h3>
                <ol>
                <li>Immediate account review required</li>
                <li>Enhanced customer due diligence</li>
                <li>Consider transaction limits</li>
                <li>Report to AML compliance team</li>
                </ol>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                Roll-over fraud may indicate structuring or money laundering activities.
                </p>
                </body>
                </html>
                """
            },
            
            'rapid_back_forth': {
                'subject': 'Rapid Deposit-Withdrawal Pattern Detected',
                'template': """
                <html>
                <body>
                <h2>⚡ Rapid Back-Forth Transaction Alert</h2>
                <p><strong>Detection Time:</strong> {detection_time}</p>
                
                <h3>📊 Activity Summary</h3>
                <ul>
                <li><strong>Account:</strong> {account_phone} ({account_name})</li>
                <li><strong>Number of Transactions:</strong> {transaction_count}</li>
                <li><strong>Time Frame:</strong> {time_frame} minutes</li>
                <li><strong>Net Flow:</strong> KES {net_flow:,.2f}</li>
                <li><strong>Velocity:</strong> {velocity} transactions/minute</li>
                </ul>
                
                <h3>🔍 Transaction Sequence</h3>
                <table border="1" cellpadding="5" cellspacing="0">
                <tr style="background-color: #f2f2f2;">
                    <th>#</th>
                    <th>Receipt No.</th>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Amount (KES)</th>
                    <th>Cumulative</th>
                </tr>
                {transaction_rows}
                </table>
                
                <h3>🎯 Pattern Indicators</h3>
                <ul>
                <li><strong>Circular Flow:</strong> {circular_flow}</li>
                <li><strong>Speed:</strong> {speed_indicator}</li>
                <li><strong>Amount Consistency:</strong> {amount_consistency}</li>
                </ul>
                
                <h3>⚠️ Potential Risks</h3>
                <p>{risk_description}</p>
                
                <h3>🛡️ Immediate Actions</h3>
                <ol>
                <li>Freeze account for investigation</li>
                <li>Review for possible account takeover</li>
                <li>Check for related suspicious accounts</li>
                <li>File suspicious activity report</li>
                </ol>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                Rapid back-forth patterns may indicate account testing or money laundering.
                </p>
                </body>
                </html>
                """
            },
            
            'daily_summary': {
                'subject': 'Daily Fraud Detection Summary Report',
                'template': """
                <html>
                <body>
                <h2>📊 Daily Fraud Detection Summary</h2>
                <p><strong>Report Date:</strong> {report_date}</p>
                <p><strong>Analysis Period:</strong> {analysis_period}</p>
                
                <h3>📈 Executive Summary</h3>
                <table border="1" cellpadding="8" cellspacing="0" style="width: 100%;">
                <tr style="background-color: #4CAF50; color: white;">
                    <th>Metric</th>
                    <th>Count</th>
                    <th>Amount (KES)</th>
                </tr>
                <tr>
                    <td>Total Transactions Analyzed</td>
                    <td style="text-align: center;">{total_transactions}</td>
                    <td style="text-align: right;">{total_amount:,.2f}</td>
                </tr>
                <tr style="background-color: #ffeb3b;">
                    <td>⚠️ Flagged Transactions</td>
                    <td style="text-align: center;">{flagged_transactions}</td>
                    <td style="text-align: right;">{flagged_amount:,.2f}</td>
                </tr>
                <tr style="background-color: #ff9800;">
                    <td>🔴 High Risk Transactions</td>
                    <td style="text-align: center;">{high_risk_count}</td>
                    <td style="text-align: right;">{high_risk_amount:,.2f}</td>
                </tr>
                </table>
                
                <h3>🎯 Fraud Type Breakdown</h3>
                <table border="1" cellpadding="8" cellspacing="0" style="width: 100%;">
                <tr style="background-color: #2196F3; color: white;">
                    <th>Fraud Type</th>
                    <th>Cases Detected</th>
                    <th>Transactions Involved</th>
                    <th>Total Amount</th>
                </tr>
                {fraud_type_rows}
                </table>
                
                <h3>🏆 Top 5 Suspicious Accounts</h3>
                <table border="1" cellpadding="8" cellspacing="0" style="width: 100%;">
                <tr style="background-color: #9C27B0; color: white;">
                    <th>Account</th>
                    <th>Name</th>
                    <th>Fraud Score</th>
                    <th>Suspicious Txns</th>
                    <th>Total Amount</th>
                </tr>
                {top_accounts_rows}
                </table>
                
                <h3>📋 Action Items</h3>
                <ol>
                <li>Review {high_priority_count} high priority cases</li>
                <li>Investigate {suspicious_account_count} suspicious accounts</li>
                <li>Complete {pending_reviews} pending reviews</li>
                <li>Update fraud detection rules if needed</li>
                </ol>
                
                <h3>📊 Trend Analysis</h3>
                <p>{trend_analysis}</p>
                
                <hr>
                <p style="color: #666; font-size: 12px;">
                Generated by Fraud Detection System v2.0
                </p>
                </body>
                </html>
                """
            }
        }
    
    def parse_transaction_data(self, data_text: str) -> pd.DataFrame:
        """Parse transaction data from text into DataFrame."""
        lines = data_text.strip().split('\n')
        
        data = []
        for line in lines[1:]:  # Skip header
            parts = line.split('\t')
            if len(parts) >= 13:
                try:
                    data.append({
                        'Receipt No.': parts[0],
                        'Completion Time': datetime.strptime(parts[1], '%d-%m-%Y %H:%M:%S'),
                        'Initiation Time': datetime.strptime(parts[2], '%d-%m-%Y %H:%M:%S'),
                        'Details': parts[3],
                        'Transaction Status': parts[4],
                        'Paid In': float(parts[5]) if parts[5] else 0,
                        'Withdrawn': float(parts[6]) if parts[6] else 0,
                        'Balance': float(parts[7]) if parts[7] else 0,
                        'Balance Confirmed': parts[8],
                        'Reason Type': parts[9],
                        'Other Party Info': parts[10],
                        'Linked Transaction ID': parts[11],
                        'A/C No.': parts[12]
                    })
                except Exception as e:
                    print(f"Error parsing line: {line[:50]}... Error: {e}")
                    continue
        
        self.df = pd.DataFrame(data)
        self._enrich_data()
        return self.df
    
    def _enrich_data(self):
        """Enrich DataFrame with additional derived columns."""
        if self.df is None:
            return
        
        # Extract phone number and name
        self.df['Phone Number'] = self.df['Other Party Info'].apply(self._extract_phone_number)
        self.df['Name'] = self.df['Other Party Info'].apply(self._extract_name)
        
        # Calculate net amount and transaction type
        self.df['Net Amount'] = self.df['Paid In'] - self.df['Withdrawn']
        self.df['Transaction Type'] = self.df.apply(
            lambda x: 'DEPOSIT' if x['Withdrawn'] > 0 else 'WITHDRAWAL' if x['Paid In'] > 0 else 'UNKNOWN',
            axis=1
        )
        
        # Calculate absolute amount for pattern matching
        self.df['Absolute Amount'] = self.df['Net Amount'].abs()
        
        # Add day and hour for time-based analysis
        self.df['Date'] = self.df['Completion Time'].dt.date
        self.df['Hour'] = self.df['Completion Time'].dt.hour
        
    @staticmethod
    def _extract_phone_number(info: str) -> Optional[str]:
        """Extract masked phone number from Other Party Info."""
        if pd.isna(info):
            return None
        match = re.search(r'(\d{3}\*{3}\d{3}|\d{5}\*{3}\d{3})', str(info))
        return match.group(1) if match else None
    
    @staticmethod
    def _extract_name(info: str) -> Optional[str]:
        """Extract name from Other Party Info."""
        if pd.isna(info):
            return None
        parts = str(info).split(' - ')
        return parts[1].strip() if len(parts) > 1 else None
    
    def detect_split_transactions(self) -> pd.DataFrame:
        """Detect split transactions with similar amounts within time window."""
        if self.df is None:
            raise ValueError("No data loaded. Call parse_transaction_data first.")
        
        df = self.df.copy()
        df['Split Flag'] = False
        df['Split Group'] = None
        df['Split Details'] = ''
        
        # Sort by phone number and time
        df_sorted = df.sort_values(['Phone Number', 'Completion Time'])
        
        split_groups = defaultdict(list)
        group_counter = 1
        
        for i in range(len(df_sorted)):
            current = df_sorted.iloc[i]
            current_phone = current['Phone Number']
            
            if pd.isna(current_phone):
                continue
            
            window_transactions = []
            
            # Find transactions within time window
            for j in range(i, len(df_sorted)):
                compare = df_sorted.iloc[j]
                compare_phone = compare['Phone Number']
                
                if pd.isna(compare_phone) or compare_phone != current_phone:
                    break
                
                time_diff = (compare['Completion Time'] - current['Completion Time']).total_seconds() / 60
                if time_diff <= self.config['time_window_minutes']:
                    window_transactions.append((j, compare))
            
            # Analyze for split patterns
            if len(window_transactions) >= self.config['split_threshold']:
                # Group by similar amounts
                amount_groups = defaultdict(list)
                for idx, row in window_transactions:
                    amount = row['Absolute Amount']
                    # Find existing group with similar amount
                    found_group = None
                    for group_amount in amount_groups:
                        if abs(amount - group_amount) / max(group_amount, 1) <= self.config['amount_variance']:
                            found_group = group_amount
                            break
                    
                    if found_group is not None:
                        amount_groups[found_group].append((idx, row))
                    else:
                        amount_groups[amount].append((idx, row))
                
                # Check each amount group for split pattern
                for amount, transactions in amount_groups.items():
                    if len(transactions) >= self.config['split_threshold']:
                        split_group_id = f"SPLIT_{group_counter}"
                        
                        # Flag all transactions in the group
                        for idx, row in transactions:
                            df_sorted.loc[df_sorted.index[idx], 'Split Flag'] = True
                            df_sorted.loc[df_sorted.index[idx], 'Split Group'] = split_group_id
                            
                            details = (f"Split of {amount:.2f} with {len(transactions)-1} other "
                                      f"transactions within {self.config['time_window_minutes']}min")
                            df_sorted.loc[df_sorted.index[idx], 'Split Details'] = details
                        
                        group_counter += 1
        
        return df_sorted
    
    def detect_rollover_fraud(self) -> pd.DataFrame:
        """Detect roll-over fraud patterns."""
        if self.df is None:
            raise ValueError("No data loaded. Call parse_transaction_data first.")
        
        df = self.df.copy()
        df['Rollover Flag'] = False
        df['Rollover Group'] = None
        df['Rollover Details'] = ''
        
        # Sort by phone number and time
        df_sorted = df.sort_values(['Phone Number', 'Completion Time'])
        
        rollover_groups = defaultdict(list)
        group_counter = 1
        
        i = 0
        while i < len(df_sorted):
            current = df_sorted.iloc[i]
            current_phone = current['Phone Number']
            
            if pd.isna(current_phone):
                i += 1
                continue
            
            # Collect transactions for this account
            account_transactions = []
            while i < len(df_sorted) and df_sorted.iloc[i]['Phone Number'] == current_phone:
                account_transactions.append((i, df_sorted.iloc[i]))
                i += 1
            
            # Analyze account transactions for roll-over patterns
            self._analyze_account_rollover(account_transactions, df_sorted, rollover_groups, group_counter)
            group_counter += len(rollover_groups)
        
        return df_sorted
    
    def _analyze_account_rollover(self, transactions, df_sorted, rollover_groups, base_counter):
        """Analyze roll-over patterns for a single account."""
        # Group by transaction type
        deposits = [(idx, row) for idx, row in transactions if row['Transaction Type'] == 'DEPOSIT']
        withdrawals = [(idx, row) for idx, row in transactions if row['Transaction Type'] == 'WITHDRAWAL']
        
        # Check for frequent deposits
        if len(deposits) >= self.config['min_transactions_rollover']:
            self._check_frequency_pattern(deposits, df_sorted, rollover_groups, base_counter, 'DEPOSIT')
        
        # Check for frequent withdrawals
        if len(withdrawals) >= self.config['min_transactions_rollover']:
            self._check_frequency_pattern(withdrawals, df_sorted, rollover_groups, base_counter, 'WITHDRAWAL')
    
    def _check_frequency_pattern(self, transactions, df_sorted, rollover_groups, base_counter, trans_type):
        """Check for frequent transaction patterns."""
        # Sort by time
        transactions.sort(key=lambda x: x[1]['Completion Time'])
        
        # Look for clusters in time
        clusters = []
        current_cluster = [transactions[0]]
        
        for i in range(1, len(transactions)):
            prev_time = current_cluster[-1][1]['Completion Time']
            curr_time = transactions[i][1]['Completion Time']
            time_diff = (curr_time - prev_time).total_seconds() / 60
            
            if time_diff <= self.config['time_window_minutes'] * 2:  # Slightly larger window for roll-over
                current_cluster.append(transactions[i])
            else:
                if len(current_cluster) >= self.config['min_transactions_rollover']:
                    clusters.append(current_cluster)
                current_cluster = [transactions[i]]
        
        # Check last cluster
        if len(current_cluster) >= self.config['min_transactions_rollover']:
            clusters.append(current_cluster)
        
        # Create roll-over groups
        for cluster in clusters:
            if len(cluster) >= self.config['min_transactions_rollover']:
                group_id = f"ROLLOVER_{base_counter + len(rollover_groups)}"
                
                # Calculate average amount
                amounts = [row['Absolute Amount'] for _, row in cluster]
                avg_amount = np.mean(amounts)
                
                # Flag transactions
                for idx, row in cluster:
                    df_sorted.loc[df_sorted.index[idx], 'Rollover Flag'] = True
                    df_sorted.loc[df_sorted.index[idx], 'Rollover Group'] = group_id
                    
                    details = (f"{trans_type} roll-over: {len(cluster)} transactions, "
                              f"avg KES {avg_amount:.2f}")
                    df_sorted.loc[df_sorted.index[idx], 'Rollover Details'] = details
    
    def detect_rapid_back_forth(self) -> pd.DataFrame:
        """Detect rapid deposit-withdrawal patterns."""
        if self.df is None:
            raise ValueError("No data loaded. Call parse_transaction_data first.")
        
        df = self.df.copy()
        df['RapidBackForth Flag'] = False
        df['RapidBackForth Group'] = None
        df['RapidBackForth Details'] = ''
        
        df_sorted = df.sort_values(['Phone Number', 'Completion Time'])
        
        group_counter = 1
        
        for i in range(len(df_sorted) - 1):
            current = df_sorted.iloc[i]
            next_row = df_sorted.iloc[i + 1]
            
            if pd.isna(current['Phone Number']) or pd.isna(next_row['Phone Number']):
                continue
            
            if current['Phone Number'] != next_row['Phone Number']:
                continue
            
            time_diff = (next_row['Completion Time'] - current['Completion Time']).total_seconds() / 60
            
            if time_diff <= self.config['time_window_minutes']:
                # Check for opposite transaction types
                current_type = current['Transaction Type']
                next_type = next_row['Transaction Type']
                
                if current_type != next_type:
                    # Check amount similarity
                    current_amount = current['Absolute Amount']
                    next_amount = next_row['Absolute Amount']
                    
                    if abs(current_amount - next_amount) / max(current_amount, 1) <= 0.3:  # 30% variance
                        group_id = f"RAPID_{group_counter}"
                        
                        df_sorted.loc[df_sorted.index[i], 'RapidBackForth Flag'] = True
                        df_sorted.loc[df_sorted.index[i + 1], 'RapidBackForth Flag'] = True
                        
                        df_sorted.loc[df_sorted.index[i], 'RapidBackForth Group'] = group_id
                        df_sorted.loc[df_sorted.index[i + 1], 'RapidBackForth Group'] = group_id
                        
                        details = (f"Rapid {current_type.lower()}/{next_type.lower()}: "
                                  f"KES {current_amount:.2f} ↔ KES {next_amount:.2f} "
                                  f"in {time_diff:.1f} min")
                        
                        df_sorted.loc[df_sorted.index[i], 'RapidBackForth Details'] = details
                        df_sorted.loc[df_sorted.index[i + 1], 'RapidBackForth Details'] = details
                        
                        group_counter += 1
        
        return df_sorted
    
    def run_detection(self) -> pd.DataFrame:
        """Run all fraud detection algorithms."""
        print("Starting fraud detection...")
        
        # Run individual detection methods
        df_split = self.detect_split_transactions()
        df_rollover = self.detect_rollover_fraud()
        df_rapid = self.detect_rapid_back_forth()
        
        # Combine results
        self.detected_fraud = df_split.copy()
        
        # Merge flags from other detections
        for col in ['Rollover Flag', 'Rollover Group', 'Rollover Details',
                   'RapidBackForth Flag', 'RapidBackForth Group', 'RapidBackForth Details']:
            if col in df_rollover.columns:
                self.detected_fraud[col] = df_rollover[col]
            if col in df_rapid.columns:
                self.detected_fraud[col] = df_rapid[col]
        
        # Calculate overall fraud score
        self._calculate_fraud_scores()
        
        # Generate report
        self.report = self._generate_detailed_report()
        
        print(f"Detection complete. Found {self.detected_fraud['Fraud Score'].sum() > 0} suspicious transactions.")
        
        # Send email notifications if enabled
        if self.config['email_enabled']:
            self.send_notifications()
        
        return self.detected_fraud
    
    def _calculate_fraud_scores(self):
        """Calculate fraud scores for each transaction."""
        if self.detected_fraud is None:
            return
        
        self.detected_fraud['Fraud Score'] = 0
        
        # Split transactions: 30 points
        self.detected_fraud.loc[self.detected_fraud['Split Flag'], 'Fraud Score'] += 30
        
        # Roll-over fraud: 50 points
        self.detected_fraud.loc[self.detected_fraud['Rollover Flag'], 'Fraud Score'] += 50
        
        # Rapid back-forth: 40 points
        self.detected_fraud.loc[self.detected_fraud['RapidBackForth Flag'], 'Fraud Score'] += 40
        
        # Multiple fraud types: additional points
        fraud_counts = (
            self.detected_fraud['Split Flag'].astype(int) +
            self.detected_fraud['Rollover Flag'].astype(int) +
            self.detected_fraud['RapidBackForth Flag'].astype(int)
        )
        self.detected_fraud.loc[fraud_counts >= 2, 'Fraud Score'] += 20
        
        # Cap at 100
        self.detected_fraud['Fraud Score'] = self.detected_fraud['Fraud Score'].clip(0, 100)
        
        # Risk level categorization
        conditions = [
            self.detected_fraud['Fraud Score'] >= self.config['high_risk_score'],
            self.detected_fraud['Fraud Score'] >= self.config['medium_risk_score'],
            self.detected_fraud['Fraud Score'] > 0
        ]
        choices = ['HIGH', 'MEDIUM', 'LOW']
        self.detected_fraud['Risk Level'] = np.select(conditions, choices, default='NONE')
    
    def _generate_detailed_report(self) -> Dict:
        """Generate comprehensive fraud detection report."""
        if self.detected_fraud is None:
            return {}
        
        # Group flagged transactions
        flagged_df = self.detected_fraud[
            (self.detected_fraud['Split Flag']) |
            (self.detected_fraud['Rollover Flag']) |
            (self.detected_fraud['RapidBackForth Flag'])
        ]
        
        # Summary statistics
        summary = {
            'total_transactions': len(self.detected_fraud),
            'total_amount': self.detected_fraud['Absolute Amount'].sum(),
            'flagged_transactions': len(flagged_df),
            'flagged_amount': flagged_df['Absolute Amount'].sum(),
            'high_risk_count': len(self.detected_fraud[self.detected_fraud['Risk Level'] == 'HIGH']),
            'medium_risk_count': len(self.detected_fraud[self.detected_fraud['Risk Level'] == 'MEDIUM']),
            'low_risk_count': len(self.detected_fraud[self.detected_fraud['Risk Level'] == 'LOW']),
            'split_cases': self.detected_fraud['Split Flag'].sum(),
            'rollover_cases': self.detected_fraud['Rollover Flag'].sum(),
            'rapid_cases': self.detected_fraud['RapidBackForth Flag'].sum()
        }
        
        # Group by account
        account_summary = flagged_df.groupby(['Phone Number', 'Name']).agg({
            'Receipt No.': 'count',
            'Absolute Amount': 'sum',
            'Fraud Score': 'mean',
            'Risk Level': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'LOW'
        }).sort_values('Fraud Score', ascending=False)
        
        # Group by fraud type for detailed analysis
        split_groups = self._analyze_split_groups(flagged_df)
        rollover_groups = self._analyze_rollover_groups(flagged_df)
        rapid_groups = self._analyze_rapid_groups(flagged_df)
        
        return {
            'summary': summary,
            'account_summary': account_summary,
            'split_analysis': split_groups,
            'rollover_analysis': rollover_groups,
            'rapid_analysis': rapid_groups,
            'flagged_transactions': flagged_df.sort_values(['Fraud Score', 'Completion Time'], 
                                                          ascending=[False, False]),
            'detection_time': datetime.now()
        }
    
    def _analyze_split_groups(self, flagged_df: pd.DataFrame) -> List[Dict]:
        """Analyze and structure split transaction groups."""
        split_df = flagged_df[flagged_df['Split Flag']]
        if split_df.empty:
            return []
        
        groups = []
        for group_id in split_df['Split Group'].dropna().unique():
            group_data = split_df[split_df['Split Group'] == group_id]
            
            first_trans = group_data.iloc[0]
            groups.append({
                'group_id': group_id,
                'account_phone': first_trans['Phone Number'],
                'account_name': first_trans['Name'],
                'transaction_count': len(group_data),
                'total_amount': group_data['Absolute Amount'].sum(),
                'avg_amount': group_data['Absolute Amount'].mean(),
                'time_range': (group_data['Completion Time'].max() - 
                              group_data['Completion Time'].min()).total_seconds() / 60,
                'transactions': group_data[['Receipt No.', 'Completion Time', 
                                           'Absolute Amount', 'Transaction Type']].to_dict('records')
            })
        
        return sorted(groups, key=lambda x: x['transaction_count'], reverse=True)
    
    def _analyze_rollover_groups(self, flagged_df: pd.DataFrame) -> List[Dict]:
        """Analyze and structure roll-over fraud groups."""
        rollover_df = flagged_df[flagged_df['Rollover Flag']]
        if rollover_df.empty:
            return []
        
        groups = []
        for group_id in rollover_df['Rollover Group'].dropna().unique():
            group_data = rollover_df[rollover_df['Rollover Group'] == group_id]
            
            first_trans = group_data.iloc[0]
            # Determine transaction type (should be consistent within group)
            trans_type_counts = group_data['Transaction Type'].value_counts()
            main_type = trans_type_counts.index[0] if len(trans_type_counts) > 0 else 'UNKNOWN'
            
            groups.append({
                'group_id': group_id,
                'account_phone': first_trans['Phone Number'],
                'account_name': first_trans['Name'],
                'transaction_count': len(group_data),
                'transaction_type': main_type,
                'total_amount': group_data['Absolute Amount'].sum(),
                'avg_amount': group_data['Absolute Amount'].mean(),
                'time_range': (group_data['Completion Time'].max() - 
                              group_data['Completion Time'].min()).total_seconds() / 60,
                'frequency': len(group_data) / max(1, 
                    (group_data['Completion Time'].max() - 
                     group_data['Completion Time'].min()).total_seconds() / 3600),
                'transactions': group_data[['Receipt No.', 'Completion Time', 
                                           'Absolute Amount', 'Transaction Type']].to_dict('records')
            })
        
        return sorted(groups, key=lambda x: x['transaction_count'], reverse=True)
    
    def _analyze_rapid_groups(self, flagged_df: pd.DataFrame) -> List[Dict]:
        """Analyze and structure rapid back-forth groups."""
        rapid_df = flagged_df[flagged_df['RapidBackForth Flag']]
        if rapid_df.empty:
            return []
        
        groups = []
        for group_id in rapid_df['RapidBackForth Group'].dropna().unique():
            group_data = rapid_df[rapid_df['RapidBackForth Group'] == group_id]
            
            first_trans = group_data.iloc[0]
            # Calculate net flow
            net_flow = group_data['Net Amount'].sum()
            
            groups.append({
                'group_id': group_id,
                'account_phone': first_trans['Phone Number'],
                'account_name': first_trans['Name'],
                'transaction_count': len(group_data),
                'net_flow': net_flow,
                'total_volume': group_data['Absolute Amount'].sum(),
                'time_range': (group_data['Completion Time'].max() - 
                              group_data['Completion Time'].min()).total_seconds() / 60,
                'transaction_pairs': len(group_data) // 2,
                'transactions': group_data[['Receipt No.', 'Completion Time', 
                                           'Net Amount', 'Transaction Type']].to_dict('records')
            })
        
        return sorted(groups, key=lambda x: x['transaction_pairs'], reverse=True)
    
    def send_notifications(self):
        """Send email notifications for detected fraud."""
        if not self.config['email_enabled'] or self.report is None:
            return
        
        # Send individual fraud alerts
        self._send_split_transaction_alerts()
        self._send_rollover_fraud_alerts()
        self._send_rapid_pattern_alerts()
        
        # Send daily summary
        self._send_daily_summary()
    
    def _send_split_transaction_alerts(self):
        """Send alerts for split transaction fraud."""
        if not self.config['notify_split_transactions']:
            return
        
        for group in self.report['split_analysis']:
            # Prepare email content
            template = self.email_templates['split_transaction']
            
            # Create transaction rows HTML
            transaction_rows = ""
            for i, trans in enumerate(group['transactions'], 1):
                transaction_rows += f"""
                <tr>
                    <td>{trans['Receipt No.']}</td>
                    <td>{trans['Completion Time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td style="text-align: right;">{trans['Absolute Amount']:,.2f}</td>
                    <td>{trans['Transaction Type']}</td>
                </tr>
                """
            
            # Fill template
            email_body = template['template'].format(
                detection_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                period=f"{group['time_range']:.1f} minutes",
                account_phone=group['account_phone'],
                account_name=group['account_name'],
                transaction_count=group['transaction_count'],
                total_amount=group['total_amount'],
                time_window=self.config['time_window_minutes'],
                fraud_score=min(30 + group['transaction_count'] * 10, 100),
                transaction_rows=transaction_rows,
                pattern_analysis=f"{group['transaction_count']} transactions of ~KES {group['avg_amount']:,.2f} each"
            )
            
            # Send email
            _send_email(
                subject=f"{self.config['email_subject_prefix']}{template['subject']} - {group['account_phone']}",
                body=email_body,
                recipient=self.user.email or "martinmaati31@gmail.com",
                is_html=True
            )
    
    def _send_rollover_fraud_alerts(self):
        """Send alerts for roll-over fraud."""
        if not self.config['notify_rollover_fraud']:
            return
        
        for group in self.report['rollover_analysis']:
            template = self.email_templates['rollover_fraud']
            
            # Create transaction rows HTML
            transaction_rows = ""
            prev_time = None
            for trans in group['transactions']:
                interval = ""
                if prev_time:
                    interval = f"{(trans['Completion Time'] - prev_time).total_seconds() / 60:.1f}"
                prev_time = trans['Completion Time']
                
                transaction_rows += f"""
                <tr>
                    <td>{trans['Receipt No.']}</td>
                    <td>{trans['Completion Time'].strftime('%H:%M:%S')}</td>
                    <td style="text-align: right;">{trans['Absolute Amount']:,.2f}</td>
                    <td>{interval}</td>
                </tr>
                """
            
            # Determine risk level
            risk_level = "HIGH" if group['transaction_count'] >= 5 else "MEDIUM"
            
            email_body = template['template'].format(
                detection_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                period=f"{group['time_range']:.1f} minutes",
                account_phone=group['account_phone'],
                account_name=group['account_name'],
                transaction_count=group['transaction_count'],
                transaction_type=group['transaction_type'],
                avg_amount=group['avg_amount'],
                time_window=self.config['time_window_minutes'],
                risk_level=risk_level,
                transaction_rows=transaction_rows,
                frequency=f"Every {group['time_range']/group['transaction_count']:.1f} minutes on average",
                consistency="High" if group['transaction_count'] >= 4 else "Moderate",
                total_volume=group['total_amount'],
                risk_assessment=f"Pattern suggests possible {group['transaction_type'].lower()} structuring"
            )
            
            _send_email(
                subject=f"{self.config['email_subject_prefix']}{template['subject']} - {group['account_phone']}",
                body=email_body,
                recipient=self.user.email or "martinmaati31@gmail.com",
                is_html=True
            )
    
    def _send_rapid_pattern_alerts(self):
        """Send alerts for rapid back-forth patterns."""
        if not self.config['notify_rapid_patterns']:
            return
        
        for group in self.report['rapid_analysis']:
            template = self.email_templates['rapid_back_forth']
            
            # Create transaction rows HTML
            transaction_rows = ""
            cumulative = 0
            for i, trans in enumerate(group['transactions'], 1):
                cumulative += trans['Net Amount']
                transaction_rows += f"""
                <tr>
                    <td>{i}</td>
                    <td>{trans['Receipt No.']}</td>
                    <td>{trans['Completion Time'].strftime('%H:%M:%S')}</td>
                    <td>{trans['Transaction Type']}</td>
                    <td style="text-align: right;">{trans['Net Amount']:,.2f}</td>
                    <td style="text-align: right;">{cumulative:,.2f}</td>
                </tr>
                """
            
            # Calculate velocity
            velocity = group['transaction_count'] / max(group['time_range'], 0.1)
            
            email_body = template['template'].format(
                detection_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                account_phone=group['account_phone'],
                account_name=group['account_name'],
                transaction_count=group['transaction_count'],
                time_frame=f"{group['time_range']:.1f}",
                net_flow=group['net_flow'],
                velocity=f"{velocity:.2f}",
                transaction_rows=transaction_rows,
                circular_flow="Yes" if abs(group['net_flow']) < group['total_volume'] * 0.1 else "No",
                speed_indicator="Very High" if velocity > 2 else "High",
                amount_consistency="High" if group['transaction_pairs'] >= 2 else "Moderate",
                risk_description="Possible account testing or money laundering activity"
            )
            
            _send_email(
                subject=f"{self.config['email_subject_prefix']}{template['subject']} - {group['account_phone']}",
                body=email_body,
                recipient=self.user.email or "martinmaati31@gmail.com",
                is_html=True
            )
    
    def _send_daily_summary(self):
        """Send daily summary report."""
        template = self.email_templates['daily_summary']
        
        # Create fraud type rows
        fraud_type_rows = ""
        fraud_types = [
            ('Split Transactions', self.report['summary']['split_cases'], 
             len(self.report['split_analysis']), 0),
            ('Roll-over Fraud', self.report['summary']['rollover_cases'], 
             len(self.report['rollover_analysis']), 0),
            ('Rapid Patterns', self.report['summary']['rapid_cases'], 
             len(self.report['rapid_analysis']), 0)
        ]
        
        for name, txn_count, case_count, amount in fraud_types:
            fraud_type_rows += f"""
            <tr>
                <td>{name}</td>
                <td style="text-align: center;">{case_count}</td>
                <td style="text-align: center;">{txn_count}</td>
                <td style="text-align: right;">{amount:,.2f}</td>
            </tr>
            """
        
        # Create top accounts rows
        top_accounts_rows = ""
        top_accounts = self.report['account_summary'].head(5)
        for (phone, name), row in top_accounts.iterrows():
            top_accounts_rows += f"""
            <tr>
                <td>{phone}</td>
                <td>{name}</td>
                <td style="text-align: center;">{row['Fraud Score']:.1f}</td>
                <td style="text-align: center;">{row['Receipt No.']}</td>
                <td style="text-align: right;">{row['Absolute Amount']:,.2f}</td>
            </tr>
            """
        
        email_body = template['template'].format(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            analysis_period=f"{self.detected_fraud['Date'].min()} to {self.detected_fraud['Date'].max()}",
            total_transactions=self.report['summary']['total_transactions'],
            total_amount=self.report['summary']['total_amount'],
            flagged_transactions=self.report['summary']['flagged_transactions'],
            flagged_amount=self.report['summary']['flagged_amount'],
            high_risk_count=self.report['summary']['high_risk_count'],
            high_risk_amount=0,  # You can calculate this from flagged transactions
            fraud_type_rows=fraud_type_rows,
            top_accounts_rows=top_accounts_rows,
            high_priority_count=self.report['summary']['high_risk_count'],
            suspicious_account_count=len(self.report['account_summary']),
            pending_reviews=self.report['summary']['flagged_transactions'],
            trend_analysis="Review trends and adjust detection thresholds as needed."
        )
        
        _send_email(
            subject=f"{self.config['email_subject_prefix']}Daily Summary - {datetime.now().strftime('%Y-%m-%d')}",
            body=email_body,
            recipient=self.user.email or "martinmaati31@gmail.com",
            is_html=True
        )

    def save_results(self, output_dir: str = './fraud_reports'):
        """Save detection results to files."""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save flagged transactions
        if self.detected_fraud is not None:
            csv_path = os.path.join(output_dir, f'fraud_analysis_{timestamp}.csv')
            self.detected_fraud.to_csv(csv_path, index=False)
            print(f"Saved transactions to: {csv_path}")
        
        # Save report
        if self.report is not None:
            json_path = os.path.join(output_dir, f'fraud_report_{timestamp}.json')
            with open(json_path, 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                report_copy = self.report.copy()
                if 'flagged_transactions' in report_copy:
                    report_copy['flagged_transactions'] = report_copy['flagged_transactions'].to_dict('records')
                json.dump(report_copy, f, default=str, indent=2)
            print(f"Saved report to: {json_path}")
        
        # Save summary
        summary_path = os.path.join(output_dir, f'fraud_summary_{timestamp}.txt')
        with open(summary_path, 'w') as f:
            f.write(self._generate_text_summary())
        print(f"Saved summary to: {summary_path}")
    
    def _generate_text_summary(self) -> str:
        """Generate a text summary of the fraud detection results."""
        if self.report is None:
            return "No detection results available."
        
        summary = self.report['summary']
        
        text = f"""
        {'='*80}
        FRAUD DETECTION SUMMARY REPORT
        {'='*80}
        
        Detection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Analysis Period: {self.df['Date'].min()} to {self.df['Date'].max()}
        
        📊 TRANSACTION STATISTICS
        {'-'*40}
        Total Transactions Analyzed: {summary['total_transactions']:,}
        Total Transaction Value: KES {summary['total_amount']:,.2f}
        
        ⚠️ FRAUD DETECTION RESULTS
        {'-'*40}
        Flagged Transactions: {summary['flagged_transactions']:,}
        Flagged Amount: KES {summary['flagged_amount']:,.2f}
        
        🎯 FRAUD TYPE BREAKDOWN
        {'-'*40}
        Split Transaction Cases: {summary['split_cases']:,}
        Roll-over Fraud Cases: {summary['rollover_cases']:,}
        Rapid Pattern Cases: {summary['rapid_cases']:,}
        
        🔴 RISK LEVEL DISTRIBUTION
        {'-'*40}
        High Risk Transactions: {summary['high_risk_count']:,}
        Medium Risk Transactions: {summary['medium_risk_count']:,}
        Low Risk Transactions: {summary['low_risk_count']:,}
        
        🏆 TOP SUSPICIOUS ACCOUNTS
        {'-'*40}
        """
        
        # Add top accounts
        top_accounts = self.report['account_summary'].head(5)
        for i, ((phone, name), row) in enumerate(top_accounts.iterrows(), 1):
            text += f"\n{i}. {phone} ({name}):"
            text += f"\n   • Fraud Score: {row['Fraud Score']:.1f}/100"
            text += f"\n   • Suspicious Txns: {row['Receipt No.']:,}"
            text += f"\n   • Total Amount: KES {row['Absolute Amount']:,.2f}"
            text += f"\n   • Risk Level: {row['Risk Level']}"
        
        text += f"\n\n{'='*80}"
        text += "\n⚠️ ACTION REQUIRED"
        text += f"\n{'='*80}"
        text += f"\n1. Review {summary['high_risk_count']} high-risk transactions"
        text += f"\n2. Investigate {len(self.report['account_summary'])} suspicious accounts"
        text += f"\n3. Complete {summary['flagged_transactions']} transaction reviews"
        
        return text
    
    def get_high_risk_transactions(self) -> pd.DataFrame:
        """Get high-risk transactions for immediate review."""
        if self.detected_fraud is None:
            return pd.DataFrame()
        
        return self.detected_fraud[
            self.detected_fraud['Risk Level'] == 'HIGH'
        ].sort_values('Fraud Score', ascending=False)
    
    def get_suspicious_accounts(self, min_score: int = 30) -> pd.DataFrame:
        """Get suspicious accounts above a minimum fraud score."""
        if self.report is None or 'account_summary' not in self.report:
            return pd.DataFrame()
        
        return self.report['account_summary'][
            self.report['account_summary']['Fraud Score'] >= min_score
        ]