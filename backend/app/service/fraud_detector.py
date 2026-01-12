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
import logging

from app import db

logger = logging.getLogger(__name__)

class FraudDetectionService:
    """Service for detecting fraud patterns in transactions."""
    
    def __init__(self, user: User = None, config: Dict = None):
        self.user = user
        self.default_config = {
            'time_window_minutes': 5,
            'amount_variance': 0.1,
            'min_transactions_rollover': 3,
            'split_threshold': 2,
            'rapid_back_forth_threshold': 2,
            'high_risk_score': 50,
            'medium_risk_score': 30,
            'max_alerts_per_group': 3,  # Limit alerts for same transaction group
            'analysis_period_days': 30,  # Days to analyze for historical report
            'recent_transactions_limit': 100,  # Recent transactions to check per shortcode
        }
        self.config = {**self.default_config, **(config or {})}
        self.email_templates = self._load_email_templates()
    
    def _load_email_templates(self) -> Dict:
        """Load email templates for different fraud types."""
        return {
            'split_transaction': {
                'subject': 'Split Transaction Fraud Detected',
                'template': """
                <html><body>
                <h2>🚨 Split Transaction Fraud Alert</h2>
                <p><strong>Detection Time:</strong> {detection_time}</p>
                <p><strong>Account:</strong> {account_phone}</p>
                <p><strong>Transactions Found:</strong> {transaction_count}</p>
                <p><strong>Total Amount:</strong> KES {total_amount:,.2f}</p>
                <p><strong>Fraud Score:</strong> {fraud_score}/100</p>
                <hr>
                <p>Please review these transactions immediately.</p>
                </body></html>
                """
            },
            'rollover_fraud': {
                'subject': 'Roll-over Fraud Pattern Detected',
                'template': """
                <html><body>
                <h2>🔄 Roll-over Fraud Alert</h2>
                <p><strong>Detection Time:</strong> {detection_time}</p>
                <p><strong>Account:</strong> {account_phone}</p>
                <p><strong>Pattern Type:</strong> {pattern_type}</p>
                <p><strong>Transactions:</strong> {transaction_count}</p>
                <p><strong>Risk Level:</strong> {risk_level}</p>
                </body></html>
                """
            },
            'rapid_back_forth': {
                'subject': 'Rapid Deposit-Withdrawal Pattern Detected',
                'template': """
                <html><body>
                <h2>⚡ Rapid Transaction Alert</h2>
                <p><strong>Detection Time:</strong> {detection_time}</p>
                <p><strong>Account:</strong> {account_phone}</p>
                <p><strong>Transactions:</strong> {transaction_count} in {time_window}min</p>
                <p><strong>Net Flow:</strong> KES {net_flow:,.2f}</p>
                </body></html>
                """
            },
            'historical_report': {
                'subject': 'Historical Fraud Analysis Report',
                'template': """
                <html><body>
                <h2>📊 Historical Fraud Analysis Report</h2>
                <p><strong>Report Date:</strong> {report_date}</p>
                <p><strong>Analysis Period:</strong> {analysis_period} days</p>
                <p><strong>Total Transactions Analyzed:</strong> {total_transactions}</p>
                <p><strong>Suspicious Patterns Found:</strong> {suspicious_patterns}</p>
                <p><strong>Top Risk Accounts:</strong> {top_accounts}</p>
                <hr>
                <p>This is your historical fraud analysis report. Review attached details.</p>
                </body></html>
                """
            }
        }
    
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
    
    def detect_split_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Detect split transactions."""
        if not transactions or len(transactions) < self.config['split_threshold']:
            return []
        
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
                if time_diff <= self.config['time_window_minutes']:
                    window_txns.append((j, txn))
                j += 1
            
            # Group by similar amounts
            if len(window_txns) >= self.config['split_threshold']:
                amount_groups = defaultdict(list)
                for idx, txn in window_txns:
                    amount = abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0))
                    
                    # Find similar amount group
                    found = False
                    for group_amount in amount_groups:
                        if abs(amount - group_amount) / max(group_amount, 1) <= self.config['amount_variance']:
                            amount_groups[group_amount].append((idx, txn))
                            found = True
                            break
                    
                    if not found:
                        amount_groups[amount].append((idx, txn))
                
                # Check each group
                for amount, group in amount_groups.items():
                    if len(group) >= self.config['split_threshold']:
                        # Create detection result
                        result = {
                            'fraud_type': 'split_transaction',
                            'account_phone': phone,
                            'account_name': current.get('name'),
                            'transaction_count': len(group),
                            'total_amount': sum(abs(float(txn.get('paid_in') or txn.get('withdrawn') or 0)) 
                                               for _, txn in group),
                            'avg_amount': amount,
                            'time_window': self.config['time_window_minutes'],
                            'receipt_nos': [txn['receipt_no'] for _, txn in group],
                            'transaction_ids': [txn['id'] for _, txn in group],
                            'detection_time': datetime.now(),
                            'fraud_score': min(30 + len(group) * 10, 100)
                        }
                        results.append(result)
            
            i = j  # Move to next account
        
        return results
    
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
        
        return {
            'fraud_type': 'rollover_fraud',
            'account_phone': phone,
            'account_name': name,
            'pattern_type': pattern_type,
            'transaction_count': len(transactions),
            'total_amount': sum(amounts),
            'avg_amount': sum(amounts) / len(amounts) if amounts else 0,
            'time_window': self.config['time_window_minutes'],
            'receipt_nos': [t['receipt_no'] for t in transactions],
            'transaction_ids': [t['id'] for t in transactions],
            'detection_time': datetime.now(),
            'fraud_score': min(50 + len(transactions) * 5, 100)
        }
    
    def detect_rapid_back_forth(self, transactions: List[Dict]) -> List[Dict]:
        """Detect rapid deposit-withdrawal patterns."""
        if not transactions:
            return []
        
        # Sort by time
        sorted_txns = sorted(transactions, key=lambda x: x['completion_time'])
        
        results = []
        i = 0
        
        while i < len(sorted_txns) - 1:
            current = sorted_txns[i]
            next_txn = sorted_txns[i + 1]
            
            if current.get('phone_number') != next_txn.get('phone_number'):
                i += 1
                continue
            
            time_diff = (next_txn['completion_time'] - current['completion_time']).total_seconds() / 60
            
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
                        
                        result = {
                            'fraud_type': 'rapid_back_forth',
                            'account_phone': current.get('phone_number'),
                            'account_name': current.get('name'),
                            'transaction_count': 2,
                            'total_amount': current_amount + next_amount,
                            'net_flow': net_flow,
                            'time_window': time_diff,
                            'receipt_nos': [current['receipt_no'], next_txn['receipt_no']],
                            'transaction_ids': [current['id'], next_txn['id']],
                            'detection_time': datetime.now(),
                            'fraud_score': 40
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
            'detection_time': datetime.now()
        }
        
        return {
            'summary': summary,
            'detections': all_results,
            'account_summary': account_results
        }
    
    def send_fraud_notification(self, detection_result: Dict, fraud_type: str):
        """Send fraud notification email."""
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
        
        # Fill template
        if fraud_type == 'split_transaction':
            body = template['template'].format(
                detection_time=detection_result['detection_time'].strftime('%Y-%m-%d %H:%M:%S'),
                account_phone=detection_result.get('account_phone', 'Unknown'),
                transaction_count=detection_result.get('transaction_count', 0),
                total_amount=detection_result.get('total_amount', 0),
                fraud_score=detection_result.get('fraud_score', 0)
            )
        elif fraud_type == 'rollover_fraud':
            body = template['template'].format(
                detection_time=detection_result['detection_time'].strftime('%Y-%m-%d %H:%M:%S'),
                account_phone=detection_result.get('account_phone', 'Unknown'),
                pattern_type=detection_result.get('pattern_type', 'Unknown'),
                transaction_count=detection_result.get('transaction_count', 0),
                risk_level=detection_result.get('risk_level', 'MEDIUM')
            )
        elif fraud_type == 'rapid_back_forth':
            body = template['template'].format(
                detection_time=detection_result['detection_time'].strftime('%Y-%m-%d %H:%M:%S'),
                account_phone=detection_result.get('account_phone', 'Unknown'),
                transaction_count=detection_result.get('transaction_count', 0),
                time_window=detection_result.get('time_window', 0),
                net_flow=detection_result.get('net_flow', 0)
            )
        else:
            return
        
        # Send email
        try:
            _send_email(
                subject=f"[Fraud Alert] {template['subject']}",
                body=body,
                recipient=self.user.email,
                is_html=True
            )
            logger.info(f"Sent {fraud_type} alert to {self.user.email}")
            
            # Record alert
            self._record_fraud_alert(detection_result, fraud_type)
            
        except Exception as e:
            logger.error(f"Failed to send fraud notification: {str(e)}")
    
    def send_historical_report(self, report_data: Dict):
        """Send historical fraud analysis report."""
        if not self.user or not self.user.email:
            return
        
        template = self.email_templates['historical_report']
        
        body = template['template'].format(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            analysis_period=self.config['analysis_period_days'],
            total_transactions=report_data.get('total_transactions_analyzed', 0),
            suspicious_patterns=report_data.get('suspicious_patterns_found', 0),
            top_accounts=min(5, report_data.get('accounts_flagged', 0))
        )
        
        try:
            _send_email(
                subject=f"Historical Fraud Analysis Report - {datetime.now().strftime('%Y-%m-%d')}",
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
    
    def _record_report_history(self, report_data: Dict):
        """Record report history in database."""
        
        try:
            history = FraudReportHistory(
                user_id=self.user.id,
                analysis_period_days=self.config['analysis_period_days'],
                total_transactions=report_data.get('total_transactions_analyzed', 0),
                suspicious_patterns=report_data.get('suspicious_patterns_found', 0),
                accounts_flagged=report_data.get('accounts_flagged', 0),
                report_data=report_data
            )
            db.session.add(history)
            db.session.commit()
            logger.info("Recorded fraud report history")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record report history: {str(e)}")