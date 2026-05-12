import asyncio
import pandas as pd
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app import db
from app.model.transaction import Transaction, TransactionStats
from app.database.connection_pool import db_pool
from app.model.company import Company
from sqlalchemy import and_, extract, or_, func
import logging
from typing import Generator, List, Dict, Any, Optional, Tuple,Union
from werkzeug.utils import secure_filename
import json
import traceback
from datetime import datetime
from decimal import Decimal, InvalidOperation
import numpy as np
from flask import current_app
from concurrent.futures import ThreadPoolExecutor

from app.utils.email_utils import _send_email
from app.service.company_service import CompanyService
from app.service.agentcompany_service import AgentCompanyService
from app.model.agentcompany import AgentCompany
from app.model.agent_accounts import AgentAccount
from app.model.agent_account_balances import AgentAccountBalance
from app.service.fraud_detector import FraudDetectionService
from app.service.config_service import ConfigService
from app.model.fraud_alert import FraudAlert, FraudReportHistory
from app.model.user import User

logger = logging.getLogger(__name__)

company_service = CompanyService(db)
agent_company_service = AgentCompanyService()
executor = ThreadPoolExecutor(max_workers=5)

class TransactionService:
    def __init__(self):
        self.allowed_extensions = {'csv', 'xlsx', 'xls', 'json'}
        KENYA_TZ = timezone(timedelta(hours=3))
        self.kenya_tz = KENYA_TZ
    
    def process_scraped_data_and_update(self, file_path: str, business_shortcode: str, 
                                       additional_category: str, company_id: int, 
                                       agent_id: int) -> Dict:
        """
        Process scraped transaction data from Excel file and update existing records
        
        Args:
            file_path: Path to the downloaded Excel file
            business_shortcode: Business shortcode for identification
            additional_category: 'float' or 'commission'
            company_id: Company ID for association
            agent_id: Agent ID for association
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing and updating scraped data: {file_path}, category: {additional_category}")
            
            # Read the Excel file with the specified format
            df = pd.read_excel(file_path, skiprows=6)
            
            # Clean column names
            df.columns = [str(col).strip().lower().replace(' ', '_').replace('.', '') 
                         for col in df.columns]
            
            # Standardize column names to match our expected format
            column_mapping = {
                'receipt_no': 'receipt_no',
                'completion_time': 'completion_time',
                'initiation_time': 'initiation_time',
                'details': 'details',
                'transaction_status': 'transaction_status',
                'paid_in': 'paid_in',
                'withdrawn': 'withdrawn',
                'balance': 'balance',
                'balance_confirmed': 'balance_confirmed',
                'reason_type': 'reason_type',
                'other_party_info': 'other_party_info',
                'linked_transaction_id': 'linked_transaction_id',
                'a/c_no': 'account_number',
                'ac_no': 'account_number',
                'account_no': 'account_number',
                'currency': 'currency'
            }
            
            # Rename columns based on mapping
            df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, 
                     inplace=True)
            
            # Convert to list of dictionaries
            transactions_data = df.to_dict('records')
            
            print(f"📊 Processing {len(transactions_data)} {additional_category} transactions...")
            print(df.tail())  # Show last few rows for verification
            
            # Process and update transactions
            results = self._update_transactions_batch(
                transactions_data=transactions_data,
                transaction_type=additional_category,
                company_id=company_id,
                agent_id=agent_id,
                business_shortcode=business_shortcode
            )
            
            # Save processed file for reference
            processed_filename = f"{business_shortcode}_{additional_category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            processed_path = os.path.join('processed_transactions', processed_filename)
            os.makedirs(os.path.dirname(processed_path), exist_ok=True)
            df.to_excel(processed_path, index=False)
            
            # Also save with simple filename for easy access
            simple_filename = f"{business_shortcode}_{additional_category}.xlsx"
            simple_path = os.path.join('processed_transactions', simple_filename)
            df.to_excel(simple_path, index=False)
            
            results.update({
                'processed_file': processed_path,
                'simple_file': simple_path,
                'business_shortcode': business_shortcode,
                'transaction_type': additional_category,
                'total_records': len(transactions_data),
                'sample_data': df.tail().to_dict('records') if len(df) > 0 else []
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing scraped data: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to process scraped data: {str(e)}",
                "traceback": traceback.format_exc()
            }

    def _parse_decimal(self, value: Optional[Union[str, float, int, Decimal]]) -> Decimal:
        """
        Safely parse a value into a Decimal, handling common formats from M-Pesa statements.
        
        Handles:
            - None / np.nan / pd.NA
            - Strings with commas: '1,200.00', '-1,200.00'
            - Plain strings: '1200', '-1200.00'
            - Already parsed float/int/Decimal
            - Empty strings or whitespace
        
        Returns:
            Decimal('0.00') for None/nan/empty
            Properly parsed Decimal otherwise
        
        Raises:
            ValueError only if the value is clearly malformed and cannot be interpreted
        """
        # Handle null/empty values → return zero
        if value is None or value == '' or str(value).strip() == '':
            return Decimal('0.00')
        
        # Handle pandas NaN types
        if isinstance(value, (float, int)) and np.isnan(value):
            return Decimal('0.00')
        
        # If already a Decimal, return as-is
        if isinstance(value, Decimal):
            return value
        
        # Convert to string and clean
        try:
            # Handle float/int first (e.g., -1200.0)
            if isinstance(value, (int, float)):
                if isinstance(value, float) and np.isnan(value):
                    return Decimal('0.00')
                str_value = str(value).strip()
            else:
                str_value = str(value).strip()
            
            # Remove commas and any other whitespace
            cleaned = str_value.replace(',', '').strip()
            
            # Handle cases like '-1200.00' or '1200.00'
            if cleaned == '' or cleaned == '-':
                return Decimal('0.00')
            
            # Parse as Decimal
            return Decimal(cleaned)
            
        except (InvalidOperation, ValueError, TypeError) as e:
            raise ValueError(f"Unable to parse decimal value: '{value}' (cleaned: '{cleaned if 'cleaned' in locals() else 'N/A'}')") from e
    
    def _parse_decimal_to_float(self, value: Optional[Decimal]) -> Optional[float]:
        """Convert Decimal to float safely for JSON serialization."""
        return float(value) if value is not None else None

    def _parse_date_to_string(self, value: Optional[datetime]) -> Optional[str]:
        """Convert datetime to ISO string for safe JSON/API return."""
        return value.isoformat() if value else None

    def _clean_nullable_str(self, value) -> Optional[str]:
        """Return None for NaN/empty values, otherwise a stripped string."""
        import math
        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        s = str(value).strip()
        return None if s.lower() in ('nan', 'none', 'nat', '') else s
    
    def _parse_date(self, date_string):
        """Parse date string to datetime object, handling multiple formats"""
        if date_string is None:
            return None

        # Catch pandas / float NaN before converting to string
        if isinstance(date_string, float):
            import math
            if math.isnan(date_string):
                return None
            date_string = str(date_string)

        # Convert to string if it's not already
        if not isinstance(date_string, str):
            date_string = str(date_string)

        # Remove any whitespace
        date_string = date_string.strip()

        # Treat blank / nan / NaT strings as missing
        if date_string.lower() in ('', 'nan', 'none', 'nat'):
            return None
        
        # Try multiple date formats
        date_formats = [
            '%Y-%m-%d %H:%M:%S',    # 2025-10-13 14:59:47
            '%d-%m-%Y %H:%M:%S',    # 13-10-2025 14:59:47 
            '%Y/%m/%d %H:%M:%S',    # 2025/10/13 14:59:47
            '%d/%m/%Y %H:%M:%S',    # 13/10/2025 14:59:47
            '%Y-%m-%dT%H:%M:%S',    # 2025-10-13T14:59:47
            '%Y-%m-%d %H:%M',       # 2025-10-13 14:59
            '%d-%m-%Y %H:%M',       # 13-10-2025 14:59
            '%Y-%m-%d',             # 2025-10-13
            '%d-%m-%Y',             # 13-10-2025
            '%Y/%m/%d',             # 2025/10/13
            '%d/%m/%Y',             # 13/10/2025
            '%m/%d/%Y %H:%M:%S',    # 10/13/2025 14:59:47 (US format)
            '%m/%d/%Y',             # 10/13/2025 (US format)
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_string, date_format)
            except ValueError:
                continue
        
        # If no format works, try to extract date using regex
        try:
            # Try to find date pattern in string
            import re
            date_pattern = r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})'
            match = re.search(date_pattern, date_string)
            if match:
                day, month, year = match.groups()
                year = int(year)
                if year < 100:
                    year += 2000  # Convert 2-digit year to 4-digit
                day = int(day)
                month = int(month)
                
                # Also try to extract time
                time_pattern = r'(\d{1,2}):(\d{1,2}):(\d{1,2})'
                time_match = re.search(time_pattern, date_string)
                if time_match:
                    hour, minute, second = map(int, time_match.groups())
                    return datetime(year, month, day, hour, minute, second)
                else:
                    # Try without seconds
                    time_pattern = r'(\d{1,2}):(\d{1,2})'
                    time_match = re.search(time_pattern, date_string)
                    if time_match:
                        hour, minute = map(int, time_match.groups())
                        return datetime(year, month, day, hour, minute, 0)
                    else:
                        return datetime(year, month, day)
        except Exception:
            pass
        
        # Genuinely unparseable — return None so the caller can skip or default
        print(f"Warning: Could not parse date '{date_string}'. Storing as null.")
        return None
        
    def map_transaction_keys(self, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps the keys from the raw transaction data (e.g., from M-Pesa statement or scraped receipt)
        to the standardized keys expected by the Transaction model.

        Args:
            original_data: Dictionary with original keys (e.g., 'Receipt No.', 'Withdrawn', etc.)

        Returns:
            Dictionary with standardized lowercase snake_case keys used in transaction_data
        """
        key_mapping = {
            'Receipt No.': 'receipt_no',
            'Completion Time': 'completion_time',
            'Initiation Time': 'initiation_time',
            'Details': 'details',
            'Transaction Status': 'transaction_status',
            'Paid In': 'paid_in',
            'Withdrawn': 'withdrawn',
            'Balance': 'balance',
            'Balance Confirmed': 'balance_confirmed',
            'Reason Type': 'reason_type',
            'Other Party Info': 'other_party_info',
            'Linked Transaction ID': 'linked_transaction_id',
            'A/C No.': 'account_number',
            'Currency': 'currency',
        }

        mapped_data = {}
        
        for orig_key, value in original_data.items():
            # Find the standardized key
            standardized_key = key_mapping.get(orig_key.strip())
            if standardized_key:
                mapped_data[standardized_key] = value
            else:
                # Optionally preserve unknown keys or ignore them
                # Here we preserve them as-is (lowercase with underscores)
                standardized_key = orig_key.strip().lower().replace(' ', '_').replace('/', '_')
                mapped_data[standardized_key] = value

        return mapped_data
     
    def _update_transactions_batch(self, transactions_data: List[Dict], 
                                  transaction_type: str, company_shortcode: str, 
                                  agent_id: int, business_shortcode: str = None) -> Dict:
        """
        Update existing transactions or create new ones in batch
        
        Args:
            transactions_data: List of transaction dictionaries
            transaction_type: 'float' or 'commission'
            company_shortcode: Company Shortcode
            agent_id: Agent ID
            business_shortcode: Optional business shortcode for logging
            
        Returns:
            Dict with processing results
        """
        updated_count = 0
        created_count = 0
        error_count = 0
        skipped_count = 0
        errors = []
        updated_transactions = []
        created_transactions = []
        
        print(f"🔄 Starting batch update for {len(transactions_data)} transactions...")
        
        for idx, trans_data in enumerate(transactions_data):
            try:
                # Validate required fields
                trans_data = self.map_transaction_keys(trans_data)
                if not trans_data.get('receipt_no'):
                    error_count += 1
                    print(f"  ❌ Row {idx+1}: Missing receipt number")
                    errors.append(f"Row {idx+1}: Missing receipt number")
                    continue
                
                receipt_no = str(trans_data['receipt_no']).strip()
                
                # Check if transaction already exists
                existing = Transaction.query.filter_by(
                    receipt_no=receipt_no,
                    transaction_type=transaction_type
                ).first()
                
                # Parse dates — completion_time is NOT NULL so fall back to now() if unparseable
                completion_time = self._parse_date(trans_data.get('completion_time'))
                initiation_time = self._parse_date(trans_data.get('initiation_time', trans_data.get('completion_time')))
                completion_time = completion_time or initiation_time or datetime.now()
                initiation_time = initiation_time or completion_time
                
                # Parse balance confirmed
                balance_confirmed = trans_data.get('balance_confirmed', False)
                if isinstance(balance_confirmed, str):
                    balance_confirmed = balance_confirmed.upper() in ['TRUE', 'YES', '1', 'Y']
                    
                company_id = company_service.get_company_by_shortcode(company_shortcode).id
                balance_value = self._parse_decimal(trans_data.get('balance', '0'))
                if transaction_type == 'commission':
                    balance_value = balance_value * Decimal('0.25')
                
                # Prepare transaction data
                transaction_data = {
                    'receipt_no': receipt_no,
                    'completion_time': completion_time,
                    'initiation_time': initiation_time,
                    'details': trans_data.get('details', ''),
                    'transaction_status': trans_data.get('transaction_status', 'Completed'),
                    'paid_in': self._parse_decimal(trans_data.get('paid_in')),
                    'withdrawn': self._parse_decimal(trans_data.get('withdrawn')),
                    'balance': self._parse_decimal(trans_data.get('balance', '0')),
                    'balance_confirmed': balance_confirmed,
                    'reason_type': trans_data.get('reason_type', ''),
                    'other_party_info': self._clean_nullable_str(trans_data.get('other_party_info')),
                    'linked_transaction_id': self._clean_nullable_str(trans_data.get('linked_transaction_id')),
                    'account_number': self._clean_nullable_str(trans_data.get('account_number')),
                    'currency': trans_data.get('currency', 'KES'),
                    'transaction_type': transaction_type,
                    'company_id': company_id,
                    'agent_id': agent_id,
                    'business_shortcode': business_shortcode,
                    'updated_at': datetime.now()
                }
                
                # Add commission-specific fields for commission transactions
                if transaction_type == 'commission':
                    # Get commission rate, default to 0.25 if not provided or is 0
                    commission_rate = self._parse_decimal(trans_data.get('commission_rate', '0'))
                    if commission_rate is None or commission_rate == Decimal('0'):
                        commission_rate = Decimal('0.25')

                    # Calculate commission_amount = paid_in * commission_rate
                    paid_in_amount = self._parse_decimal(trans_data.get('paid_in')) or Decimal('0')
                    commission_amount = paid_in_amount * commission_rate

                    transaction_data.update({
                        'commission_rate': commission_rate,
                        'commission_amount': commission_amount,
                        'parent_transaction_id': trans_data.get('parent_transaction_id')
                    })
                
                if existing:
                    # Update existing transaction — protect business_shortcode so a receipt
                    # that appears in two tills' exports doesn't get reassigned
                    for key, value in transaction_data.items():
                        if key not in ['receipt_no', 'transaction_type', 'business_shortcode']:
                            setattr(existing, key, value)
                    
                    updated_transactions.append(existing)
                    updated_count += 1
                    
                    if updated_count % 50 == 0:
                        print(f"  ✅ Updated {updated_count} transactions...")
                        
                else:
                    # Create new transaction
                    transaction = Transaction(**transaction_data)
                    db.session.add(transaction)
                    created_transactions.append(transaction)
                    created_count += 1
                    
                    self.update_transaction_stats(transaction)
                    if created_count % 50 == 0:
                        print(f"  📝 Created {created_count} new transactions...")
                
                # Commit in batches of 100 to avoid memory issues
                if (updated_count + created_count) % 100 == 0:
                    db.session.commit()
                    print(f"  💾 Committed batch of 100 transactions...")
                
            except Exception as e:
                db.session.rollback()  # reset poisoned session so subsequent rows can proceed
                error_count += 1
                error_msg = f"Row {idx+1} (Receipt: {trans_data.get('receipt_no', 'N/A')}): {str(e)}"
                errors.append(error_msg)
                print(f"  ❌ Error: {error_msg}")
                continue
        
        # Final commit
        try:
            db.session.commit()
            
            # Log summary
            print(f"\n📊 Batch Update Summary:")
            print(f"   Total processed: {len(transactions_data)}")
            print(f"   Updated: {updated_count}")
            print(f"   Created: {created_count}")
            print(f"   Errors: {error_count}")
            print(f"   Business: {business_shortcode}")
            print(f"   Type: {transaction_type}")
            
            logger.info(f"Successfully processed {updated_count + created_count} transactions "
                       f"(updated: {updated_count}, created: {created_count}) for {business_shortcode}")
            
            return {
                "success": True,
                "message": f"Processed {len(transactions_data)} transactions successfully",
                "summary": {
                    "total_processed": len(transactions_data),
                    "updated_count": updated_count,
                    "created_count": created_count,
                    "error_count": error_count,
                    "skipped_count": skipped_count,
                    "success_rate": ((updated_count + created_count) / len(transactions_data)) * 100
                },
                "details": {
                    "updated_receipts": [t.receipt_no for t in updated_transactions[:50]],  # Limit to first 50
                    "created_receipts": [t.receipt_no for t in created_transactions[:50]],
                    "errors": errors[:20] if errors else []  # Limit to first 20 errors
                },
                "business_shortcode": business_shortcode,
                "transaction_type": transaction_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to commit transactions: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Database commit failed: {str(e)}",
                "summary": {
                    "total_processed": len(transactions_data),
                    "updated_count": 0,
                    "created_count": 0,
                    "error_count": len(transactions_data),
                    "skipped_count": 0
                },
                "errors": errors[:20] if errors else [],
                "traceback": traceback.format_exc()
            }

    def save_head_office_commission_balances(self, csv_path: str, parent_shortcode: str) -> Dict:
        """
        Parse a Head Office Balance Overview CSV (Level 1 = parent, Level 2 = children)
        and upsert one commission transaction per child shortcode per day.

        The receipt_no is COMM-{child_shortcode}-{YYYYMMDD} so re-running on the same
        day updates rather than duplicates the record.
        """
        import re, csv as _csv
        from datetime import date as _date

        try:
            parent_company = Company.query.filter_by(shortcode=str(parent_shortcode)).first()
            if not parent_company:
                return {'success': False, 'error': f'No company found for shortcode {parent_shortcode}'}
            company_id = parent_company.id

            today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
            date_tag = today.strftime('%Y%m%d')

            created = updated = skipped = 0
            errors = []

            def _parse_ksh(cell: str) -> Decimal:
                return Decimal(
                    str(cell).strip().strip('"').replace('KSH', '').replace(',', '').strip()
                )

            with open(csv_path, newline='', encoding='utf-8-sig') as f:
                reader = _csv.reader(f)
                next(reader, None)  # skip header row
                for row in reader:
                    if not row or len(row) < 6:
                        continue
                    level = str(row[0]).strip()
                    if level != '2':
                        continue

                    org_name = str(row[1]).strip().strip('"').strip()
                    # Shortcode is the leading digits before the first '-'
                    m = re.match(r'^(\d+)-', org_name)
                    if not m:
                        continue
                    child_shortcode = m.group(1)

                    # Parse all four balance columns (CSV layout):
                    # col 4 = Current Balance, col 5 = Avaliable Balance,
                    # col 6 = Reserved Balance, col 7 = Unclear Balance
                    try:
                        current_amount   = _parse_ksh(row[4])
                        available_amount = _parse_ksh(row[5])
                        reserved_amount  = _parse_ksh(row[6]) if len(row) > 6 else Decimal('0.00')
                        unclear_amount   = _parse_ksh(row[7]) if len(row) > 7 else Decimal('0.00')
                    except Exception as parse_err:
                        errors.append(f'Bad balance for {child_shortcode}: {parse_err}')
                        continue

                    # ── Transaction record (daily snapshot receipt) ──────────────────
                    receipt_no = f'COMM-{child_shortcode}-{date_tag}'
                    existing_txn = Transaction.query.filter_by(receipt_no=receipt_no).first()
                    if existing_txn:
                        existing_txn.paid_in = current_amount
                        existing_txn.balance = current_amount
                        existing_txn.commission_amount = available_amount
                        existing_txn.details = org_name
                        existing_txn.updated_at = datetime.utcnow()
                        updated += 1
                    elif current_amount > 0:
                        txn = Transaction(
                            receipt_no=receipt_no,
                            completion_time=today,
                            initiation_time=today,
                            details=org_name,
                            transaction_status='Completed',
                            paid_in=current_amount,
                            withdrawn=Decimal('0.00'),
                            balance=current_amount,
                            reason_type='Commission',
                            other_party_info=parent_company.company_name,
                            business_shortcode=child_shortcode,
                            currency='KES',
                            transaction_type='commission',
                            commission_amount=available_amount,
                            commission_rate=Decimal('0.00'),
                            company_id=company_id,
                        )
                        db.session.add(txn)
                        created += 1
                    else:
                        skipped += 1

                    # ── AgentAccount + AgentAccountBalance snapshot ──────────────────
                    # Find the parent AgentCompany by child shortcode
                    agent_company = AgentCompany.query.filter(
                        db.or_(
                            AgentCompany.short_code == child_shortcode,
                            AgentCompany.business_short_code == child_shortcode,
                            AgentCompany.agentcompany_code == child_shortcode,
                        )
                    ).first()
                    if not agent_company:
                        continue

                    # Find or create the COMMISSION AgentAccount for this company
                    commission_account = AgentAccount.query.filter(
                        AgentAccount.agent_company_id == agent_company.id,
                        AgentAccount.account_type == 'COMMISSION',
                    ).first()
                    if not commission_account:
                        commission_account = AgentAccount(
                            agent_company_id=agent_company.id,
                            account_number=f'COMM-{child_shortcode}',
                            account_type='COMMISSION',
                            account_alias='Commission Account',
                            currency='KES',
                            relationship='Owned',
                            status='ACTIVE',
                        )
                        db.session.add(commission_account)
                        db.session.flush()  # populate commission_account.id

                    commission_account.last_scraped_at = today

                    # Upsert today's balance snapshot — update if already exists, insert otherwise
                    day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                    day_end   = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                    existing_snapshot = AgentAccountBalance.query.filter(
                        AgentAccountBalance.agent_account_id == commission_account.id,
                        AgentAccountBalance.snapshot_at >= day_start,
                        AgentAccountBalance.snapshot_at <= day_end,
                    ).first()
                    if existing_snapshot:
                        existing_snapshot.current_balance   = current_amount
                        existing_snapshot.available_balance = available_amount
                        existing_snapshot.reserved_balance  = reserved_amount
                        existing_snapshot.unclear_balance   = unclear_amount
                        existing_snapshot.snapshot_at       = today
                    else:
                        db.session.add(AgentAccountBalance(
                            agent_account_id=commission_account.id,
                            current_balance=current_amount,
                            available_balance=available_amount,
                            reserved_balance=reserved_amount,
                            unclear_balance=unclear_amount,
                            snapshot_at=today,
                        ))

            db.session.commit()
            print(f'[COMM-BALANCE] created={created} updated={updated} skipped={skipped} errors={len(errors)}')
            return {
                'success': True,
                'summary': {'created': created, 'updated': updated, 'skipped': skipped, 'errors': errors}
            }

        except Exception as e:
            db.session.rollback()
            print(f'[COMM-BALANCE] Failed: {e}')
            return {'success': False, 'error': str(e)}

    def get_commission_till_balances(self, company_ids: list = None, page: int = 1, per_page: int = 10) -> dict:
        """
        Return the latest COMM-{shortcode}-{YYYYMMDD} snapshot per till, paginated.
        One row per business_shortcode, ordered by shortcode.
        """
        try:
            latest_sub = (
                db.session.query(
                    Transaction.business_shortcode,
                    func.max(Transaction.completion_time).label('latest_time'),
                )
                .filter(
                    Transaction.transaction_type == 'commission',
                    Transaction.receipt_no.like('COMM-%'),
                )
            )
            if company_ids is not None:
                latest_sub = latest_sub.filter(Transaction.company_id.in_(company_ids))
            latest_sub = latest_sub.group_by(Transaction.business_shortcode).subquery()

            base_query = (
                db.session.query(Transaction)
                .join(
                    latest_sub,
                    and_(
                        Transaction.business_shortcode == latest_sub.c.business_shortcode,
                        Transaction.completion_time == latest_sub.c.latest_time,
                    ),
                )
                .filter(
                    Transaction.transaction_type == 'commission',
                    Transaction.receipt_no.like('COMM-%'),
                )
                .order_by(Transaction.business_shortcode)
            )

            total = base_query.count()
            pages = max(1, (total + per_page - 1) // per_page)
            rows = base_query.offset((page - 1) * per_page).limit(per_page).all()

            data = []
            for t in rows:
                data.append({
                    'id': t.id,
                    'shortcode': t.business_shortcode,
                    'till_name': t.details or t.business_shortcode,
                    'current_balance': str(t.paid_in or '0.00'),
                    'available_balance': str(t.commission_amount or '0.00'),
                    'last_updated': t.completion_time.isoformat() if t.completion_time else None,
                    'receipt_no': t.receipt_no,
                })

            return {
                'success': True,
                'data': data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_next': page < pages,
                    'has_prev': page > 1,
                },
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_transactions_from_dataframe(self, df: pd.DataFrame, transaction_type: str,
                                          company_shortcode: int, agent_id: int,
                                          business_shortcode: str = None) -> Dict:
        """
        Update transactions directly from a pandas DataFrame
        
        Args:
            df: Pandas DataFrame with transaction data
            transaction_type: 'float' or 'commission'
            company_shortcode: Company Shortcode
            agent_id: Agent ID
            business_shortcode: Optional business shortcode
            
        Returns:
            Dict with processing results
        """
        try:
            # Convert DataFrame to list of dictionaries
            transactions_data = df.to_dict('records')
            
            return self._update_transactions_batch(
                transactions_data=transactions_data,
                transaction_type=transaction_type,
                company_shortcode=company_shortcode,
                agent_id=agent_id,
                business_shortcode=business_shortcode
            )
            
        except Exception as e:
            logger.error(f"Error updating from DataFrame: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update from DataFrame: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    
    def compare_and_update_transactions(self, file_path: str, transaction_type: str,
                                       company_id: int, agent_id: int) -> Dict:
        """
        Compare existing transactions with new data and update only changed records
        
        Args:
            file_path: Path to new transaction data file
            transaction_type: 'float' or 'commission'
            company_id: Company ID
            agent_id: Agent ID
            
        Returns:
            Dict with comparison and update results
        """
        try:
            # Read new data
            df = pd.read_excel(file_path, skiprows=6)
            
            # Clean column names
            df.columns = [str(col).strip().lower().replace(' ', '_').replace('.', '') 
                         for col in df.columns]
            
            # Get existing transactions for this company and type
            existing_transactions = Transaction.query.filter_by(
                company_id=company_id,
                transaction_type=transaction_type
            ).all()
            
            existing_dict = {t.receipt_no: t for t in existing_transactions}
            
            # Compare and prepare updates
            updates_needed = []
            new_transactions = []
            
            for idx, row in df.iterrows():
                receipt_no = str(row.get('receipt_no', '')).strip()
                
                if not receipt_no:
                    continue
                
                if(transaction_type == 'commission'):
                    row['balance']=row['balance']*0.25
                
                # Prepare transaction data from row
                _ct = self._parse_date(row.get('completion_time'))
                _it = self._parse_date(row.get('initiation_time', row.get('completion_time')))
                _ct = _ct or _it or datetime.now()
                _it = _it or _ct
                transaction_data = {
                    'receipt_no': receipt_no,
                    'completion_time': _ct,
                    'initiation_time': _it,
                    'details': str(row.get('details', '')),
                    'transaction_status': str(row.get('transaction_status', 'Completed')),
                    'paid_in': self._parse_decimal(row.get('paid_in')),
                    'withdrawn': self._parse_decimal(row.get('withdrawn')),
                    'balance': self._parse_decimal(row.get('balance', '0')),
                    'balance_confirmed': str(row.get('balance_confirmed', 'FALSE')).upper() in ['TRUE', 'YES', '1', 'Y'],
                    'reason_type': self._clean_nullable_str(row.get('reason_type')) or '',
                    'other_party_info': self._clean_nullable_str(row.get('other_party_info')),
                    'linked_transaction_id': self._clean_nullable_str(row.get('linked_transaction_id')),
                    'account_number': self._clean_nullable_str(row.get('account_number')),
                    'currency': str(row.get('currency', 'KES')),
                    'transaction_type': transaction_type,
                    'company_id': company_id,
                    'agent_id': agent_id
                }
                
                if transaction_type == 'commission':
                    # Get commission rate, default to 0.25 if not provided or is 0
                    commission_rate = self._parse_decimal(row.get('commission_rate', '0'))
                    if commission_rate is None or commission_rate == Decimal('0'):
                        commission_rate = Decimal('0.25')

                    # Calculate commission_amount = paid_in * commission_rate
                    paid_in_amount = self._parse_decimal(row.get('paid_in')) or Decimal('0')
                    commission_amount = paid_in_amount * commission_rate

                    transaction_data.update({
                        'commission_rate': commission_rate,
                        'commission_amount': commission_amount,
                        'parent_transaction_id': row.get('parent_transaction_id')
                    })
                
                if receipt_no in existing_dict:
                    # Check if update is needed
                    existing = existing_dict[receipt_no]
                    needs_update = False
                    
                    for key, new_value in transaction_data.items():
                        if key not in ['receipt_no', 'transaction_type']:
                            existing_value = getattr(existing, key)
                            if existing_value != new_value:
                                needs_update = True
                                break
                    
                    if needs_update:
                        updates_needed.append((existing, transaction_data))
                else:
                    # New transaction
                    new_transactions.append(transaction_data)
            
            # Apply updates and creates
            updated_count = 0
            created_count = 0
            error_count = 0
            
            # Update existing transactions
            for existing, new_data in updates_needed:
                try:
                    for key, value in new_data.items():
                        if key not in ['receipt_no', 'transaction_type']:
                            setattr(existing, key, value)
                    updated_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error updating transaction {existing.receipt_no}: {str(e)}")
            
            # Create new transactions
            for trans_data in new_transactions:
                try:
                    transaction = Transaction(**trans_data)
                    db.session.add(transaction)
                    created_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error creating transaction {trans_data.get('receipt_no')}: {str(e)}")
            
            db.session.commit()
            
            return {
                "success": True,
                "message": "Comparison and update completed",
                "summary": {
                    "total_existing": len(existing_transactions),
                    "total_new": len(df),
                    "updates_needed": len(updates_needed),
                    "new_transactions": len(new_transactions),
                    "updated_count": updated_count,
                    "created_count": created_count,
                    "error_count": error_count,
                    "unchanged_count": len(existing_transactions) - len(updates_needed)
                }
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in compare and update: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Comparison failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def bulk_update_transaction_field(self, transaction_ids: List[int], 
                                     field_name: str, field_value: Any) -> Dict:
        """
        Bulk update a specific field for multiple transactions
        
        Args:
            transaction_ids: List of transaction IDs to update
            field_name: Field name to update
            field_value: New value for the field
            
        Returns:
            Dict with update results
        """
        try:
            if not transaction_ids:
                return {
                    "success": False,
                    "error": "No transaction IDs provided"
                }
            
            # Get transactions
            transactions = Transaction.query.filter(Transaction.id.in_(transaction_ids)).all()
            
            if not transactions:
                return {
                    "success": False,
                    "error": "No transactions found with the provided IDs"
                }
            
            updated_count = 0
            errors = []
            
            for transaction in transactions:
                try:
                    # Check if field exists and is updatable
                    if hasattr(transaction, field_name) and field_name not in ['id', 'receipt_no', 'created_at']:
                        
                        # Handle special field types
                        if field_name in ['paid_in', 'withdrawn', 'balance', 'commission_amount', 'commission_rate']:
                            field_value = self._parse_decimal(field_value)
                        elif field_name in ['completion_time', 'initiation_time']:
                            field_value = self._parse_date(field_value)
                        elif field_name == 'balance_confirmed':
                            if isinstance(field_value, str):
                                field_value = field_value.upper() in ['TRUE', 'YES', '1', 'Y']
                        
                        setattr(transaction, field_name, field_value)
                        updated_count += 1
                    else:
                        errors.append(f"Field '{field_name}' not updatable for transaction {transaction.id}")
                        
                except Exception as e:
                    errors.append(f"Error updating transaction {transaction.id}: {str(e)}")
            
            db.session.commit()
            
            return {
                "success": True,
                "message": f"Updated {updated_count} transactions",
                "updated_count": updated_count,
                "error_count": len(errors),
                "errors": errors[:10] if errors else []
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Bulk update failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
      
    def get_transactions(self, filters: Dict[str, Any], page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        Fetch transactions with support for multiple filters, search, date range, and pagination.
        
        Args:
            filters: Dictionary of filters including:
                - agent_id (int)
                - company_id (int)
                - start_date (str: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')
                - end_date (str: same as above)
                - reason_type (str)
                - transaction_status (str)
                - transaction_type (str: 'float' or 'commission', default 'float')
                - search (str): free text search on receipt_no, details, or other_party_info
            
            page: Page number (1-indexed)
            per_page: Number of items per page
        
        Returns:
            Dict with success flag, data, pagination info, and summary
        """
        try:
            query = Transaction.query
            
            print("Applying filters:")
            print(filters)

            # Apply filters
            if filters.get('agent_id'):
                query = query.filter(Transaction.agent_id == filters['agent_id'])

            if filters.get('company_id'):
                query = query.filter(Transaction.company_id == filters['company_id'])
            elif filters.get('company_ids') is not None:
                # Scope to a specific list of company IDs (used for user-based access control)
                if len(filters['company_ids']) == 0:
                    # User has no companies — return nothing
                    query = query.filter(False)
                else:
                    query = query.filter(Transaction.company_id.in_(filters['company_ids']))

            if filters.get('transaction_type'):
                query = query.filter(Transaction.transaction_type == filters['transaction_type'])

            if filters.get('transaction_status'):
                query = query.filter(Transaction.transaction_status.ilike(f"%{filters['transaction_status']}%"))

            if filters.get('reasonType'):
                print("Filtering by reasonType:")
                print(filters['reasonType'])
                query = query.filter(Transaction.reason_type.ilike(f"%{filters['reasonType']}%"))

            # Date range filtering on completion_time
            if filters.get('start_date'):
                try:
                    start_dt = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                    # Include from start of day
                    query = query.filter(Transaction.completion_time >= start_dt)
                except ValueError:
                    try:
                        start_dt = datetime.strptime(filters['start_date'], '%Y-%m-%d %H:%M:%S')
                        query = query.filter(Transaction.completion_time >= start_dt)
                    except ValueError:
                        return {
                            "success": False,
                            "error": "Invalid start_date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
                        }

            if filters.get('end_date'):
                try:
                    end_dt = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                    # Include up to end of day
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    query = query.filter(Transaction.completion_time <= end_dt)
                except ValueError:
                    try:
                        end_dt = datetime.strptime(filters['end_date'], '%Y-%m-%d %H:%M:%S')
                        query = query.filter(Transaction.completion_time <= end_dt)
                    except ValueError:
                        return {
                            "success": False,
                            "error": "Invalid end_date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
                        }

            # Free text search across key fields
            if filters.get('search'):
                search_term = f"%{filters['search'].strip()}%"
                query = query.filter(
                    or_(
                        Transaction.receipt_no.ilike(search_term),
                        Transaction.details.ilike(search_term),
                        Transaction.other_party_info.ilike(search_term),
                        Transaction.reason_type.ilike(search_term),
                        Transaction.business_shortcode.ilike(search_term)
                    )
                )

            # Get total count before pagination
            total = query.count()

            # ORDER BY most recent first
            query = query.order_by(Transaction.completion_time.desc())

            # Pagination
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            transactions = pagination.items

            # Serialize transactions
            transactions_data : List = []
            for trans in transactions:
                append_dict = trans.to_dict()
                agent_company = agent_company_service.get_agent_company_by_shortcode_(trans.business_shortcode)
                if(agent_company):
                    append_dict["business_name"]=agent_company.company_name or ''
                
                transactions_data.append(append_dict)


            # Calculate summary totals FOR THE FILTERED RESULTS
            # Use a separate query with the same filters to calculate totals
            totals_query = Transaction.query
            
            # Re-apply all the same filters to the totals query
            if filters.get('agent_id'):
                totals_query = totals_query.filter(Transaction.agent_id == filters['agent_id'])

            if filters.get('company_id'):
                totals_query = totals_query.filter(Transaction.company_id == filters['company_id'])
            elif filters.get('company_ids') is not None:
                if len(filters['company_ids']) == 0:
                    totals_query = totals_query.filter(False)
                else:
                    totals_query = totals_query.filter(Transaction.company_id.in_(filters['company_ids']))
            
            if filters.get('transaction_type'):
                totals_query = totals_query.filter(Transaction.transaction_type == filters['transaction_type'])
            
            if filters.get('transaction_status'):
                totals_query = totals_query.filter(Transaction.transaction_status.ilike(f"%{filters['transaction_status']}%"))
            
            if filters.get('reasonType'):
                totals_query = totals_query.filter(Transaction.reason_type.ilike(f"%{filters['reasonType']}%"))
            
            # Date range filtering for totals query
            if filters.get('start_date'):
                try:
                    start_dt = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                    totals_query = totals_query.filter(Transaction.completion_time >= start_dt)
                except ValueError:
                    try:
                        start_dt = datetime.strptime(filters['start_date'], '%Y-%m-%d %H:%M:%S')
                        totals_query = totals_query.filter(Transaction.completion_time >= start_dt)
                    except ValueError:
                        pass
            
            if filters.get('end_date'):
                try:
                    end_dt = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    totals_query = totals_query.filter(Transaction.completion_time <= end_dt)
                except ValueError:
                    try:
                        end_dt = datetime.strptime(filters['end_date'], '%Y-%m-%d %H:%M:%S')
                        totals_query = totals_query.filter(Transaction.completion_time <= end_dt)
                    except ValueError:
                        pass
            
            # Apply search filter to totals as well
            if filters.get('search'):
                search_term = f"%{filters['search'].strip()}%"
                totals_query = totals_query.filter(
                    or_(
                        Transaction.receipt_no.ilike(search_term),
                        Transaction.details.ilike(search_term),
                        Transaction.other_party_info.ilike(search_term),
                        Transaction.reason_type.ilike(search_term),
                        Transaction.business_shortcode.ilike(search_term)
                    )
                )
            
            
            # Calculate all totals in a single query for better performance
            totals = totals_query.with_entities(
                func.sum(Transaction.paid_in).label('total_paid_in'),
                func.sum(Transaction.withdrawn).label('total_withdrawn'),
                func.sum(Transaction.commission_amount).label('total_commission'),
                func.count(Transaction.id).label('total_count')
            ).first()
            
            # Extract totals with proper default values
            total_paid_in = totals.total_paid_in or Decimal('0.00')
            total_withdrawn = totals.total_withdrawn or Decimal('0.00')
            total_commission = totals.total_commission or Decimal('0.00')
            
            # For float transactions, calculate net flow
            # For commission transactions, commission is positive income
            transaction_type = filters.get('transaction_type', 'float')
            
            if transaction_type == 'float':
                net_flow = total_paid_in + total_withdrawn  # withdrawn is negative
            else:
                # For commissions, net flow might be just commissions or include paid_in/withdrawn
                net_flow = total_commission  # or total_paid_in + total_withdrawn depending on your logic
            
            return {
                "success": True,
                "data": transactions_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev
                },
                "summary": {
                    "total_paid_in": str(total_paid_in),
                    "total_withdrawn": str(total_withdrawn),
                    "total_commission": str(total_commission),
                    "net_flow": str(net_flow),
                    "total_transactions": total
                },
                "filters_applied": filters
            }


        except Exception as e:
            current_app.logger.error(f"Error in get_transactions service: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to fetch transactions: {str(e)}"
            }
      
      
            
    def update_transaction_stats(self,transaction):
        """Update daily transaction statistics"""
        try:
            stats_date = transaction.completion_time.date()
            
            # Find or create stats record
            stats = TransactionStats.query.filter_by(
                date=stats_date,
                agent_id=transaction.agent_id,
                company_id=transaction.company_id
            ).first()
            
            if not stats:
                stats = TransactionStats(
                    date=stats_date,
                    agent_id=transaction.agent_id,
                    company_id=transaction.company_id
                )
                db.session.add(stats)
            
            # Update statistics
            if(not stats.total_transactions):
                stats.total_transactions = 0
            if(not stats.total_deposits):
                stats.total_deposits = 0
            if(not stats.total_withdrawals):
                stats.total_withdrawals = 0
            if(not stats.total_deposit_amount):
                stats.total_deposit_amount = Decimal('0.00')
            if(not stats.total_withdrawal_amount):
                stats.total_withdrawal_amount = Decimal('0.00')
                
            stats.total_transactions += 1
            
            if transaction.paid_in is not None and transaction.paid_in > 0:
                stats.total_deposits += 1
                stats.total_deposit_amount += Decimal(str(transaction.paid_in))

            if transaction.withdrawn is not None and transaction.withdrawn > 0:
                stats.total_withdrawals += 1
                stats.total_withdrawal_amount += Decimal(str(transaction.withdrawn))
            
            stats.net_flow = stats.total_deposit_amount - stats.total_withdrawal_amount
            
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error updating transaction stats: {str(e)}")
            db.session.rollback()
            
    def get_transaction_update_history(self, transaction_id: int) -> Dict:
        """
        Get update history for a transaction (requires audit table)
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Dict with update history
        """
        try:
            transaction = Transaction.query.get(transaction_id)
            
            if not transaction:
                return {
                    "success": False,
                    "error": f"Transaction with ID {transaction_id} not found"
                }
            
            # This would typically query an audit log table
            # For now, return basic info about updates
            return {
                "success": True,
                "transaction": transaction.to_dict(),
                "update_info": {
                    "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
                    "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
                    "update_count": 1 if transaction.updated_at else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting update history: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get update history: {str(e)}"
            }

    def get_transaction_stats(self, filters: Dict = None) -> Dict:
        """
        Get comprehensive transaction statistics using raw SQL
        
        Args:
            filters: Dictionary of filters including:
                - agent_id: Filter by agent ID
                - company_id: Filter by company ID
                - start_date: Start date (YYYY-MM-DD)
                - end_date: End date (YYYY-MM-DD)
                - transaction_type: 'float' or 'commission'
                - reason_type: Filter by transaction reason type
                - transaction_status: Filter by transaction status
                - group_by: Group by field ('day', 'week', 'month', 'year', 'reason_type', 'status')
                
        Returns:
            Dict with comprehensive statistics
        """
        try:
            # Set default filters
            filters = filters or {}
            transaction_type = filters.get('transaction_type', 'float')
            
            # Build base WHERE conditions
            conditions = ["transaction_type = %s"]
            params = [transaction_type]
            
            # Apply filters
            if 'agent_id' in filters:
                conditions.append("agent_id = %s")
                params.append(filters['agent_id'])
            
            if 'company_id' in filters:
                conditions.append("company_id = %s")
                params.append(filters['company_id'])
            elif 'company_ids' in filters:
                ids = filters['company_ids']
                if len(ids) == 0:
                    conditions.append("1 = 0")  # return nothing
                else:
                    placeholders = ', '.join(['%s'] * len(ids))
                    conditions.append(f"company_id IN ({placeholders})")
                    params.extend(ids)

            if 'reason_type' in filters:
                conditions.append("reason_type = %s")
                params.append(filters['reason_type'])
            
            if 'transaction_status' in filters:
                conditions.append("transaction_status = %s")
                params.append(filters['transaction_status'])
            
            # Date filtering
            if 'start_date' in filters:
                start_dt = self._parse_date(filters['start_date'])
                conditions.append("completion_time >= %s")
                params.append(start_dt)
            else:
                # Default to last 30 days if no start date
                start_dt = datetime.now() - timedelta(days=30)
                conditions.append("completion_time >= %s")
                params.append(start_dt)
            
            if 'end_date' in filters:
                end_dt = self._parse_date(filters['end_date'])
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                conditions.append("completion_time <= %s")
                params.append(end_dt)
            else:
                end_dt = datetime.now()
                conditions.append("completion_time <= %s")
                params.append(end_dt)
            
            # Combine all conditions
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Create database connection
            with db_pool.get_cursor() as cursor:
                # Get basic statistics
                basic_stats = self._get_basic_stats_raw(cursor, where_clause, params, transaction_type)
                
                # Get trend statistics
                trend_stats = self._get_trend_stats_raw(cursor, where_clause, params, filters, transaction_type)
                
                # Get category breakdown
                category_stats = self._get_category_stats_raw(cursor, where_clause, params, transaction_type)
                
                # Get top statistics
                top_stats = self._get_top_stats_raw(cursor, where_clause, params, transaction_type, filters)
                
                # Get performance metrics
                performance_metrics = self._get_performance_metrics_raw(cursor, where_clause, params, start_dt, end_dt, transaction_type)
                
                # Get comparison with previous period
                comparison_stats = self._get_comparison_stats_raw(filters, transaction_type)
                
                # Compile all statistics
                result = {
                    "success": True,
                    "stats": {
                        "summary": basic_stats,
                        "trends": trend_stats,
                        "categories": category_stats,
                        "top_performers": top_stats,
                        "performance": performance_metrics,
                        "comparison": comparison_stats,
                        "filters_applied": filters,
                        "date_range": {
                            "start_date": start_dt.strftime('%Y-%m-%d'),
                            "end_date": end_dt.strftime('%Y-%m-%d'),
                            "days_in_period": (end_dt - start_dt).days + 1
                        }
                    }
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting transaction stats: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get transaction statistics: {str(e)}"
            }
    
    def get_last_scraped_per_shortcode(self, transaction_type: str = None) -> Dict[str, int]:
        """
        Get the last scraped transaction info per business shortcode.

        Args:
            transaction_type: Optional - 'float', 'commission', or None for all types with breakdown

        Returns:
            If transaction_type specified: {shortcode: [days, receipt_no]}
            If transaction_type is None: {shortcode: {'float': [days, receipt_no], 'commission': [days, receipt_no]}}
        """
        try:
            print(f"Getting last scraped dictionary for transaction_type: {transaction_type or 'all'}")
            with db_pool.get_cursor() as cursor:
                return self._get_last_scraped_per_till(cursor, transaction_type=transaction_type)

        except Exception as e:
            logger.error(f"Error getting last scraped per shortcode: {str(e)}", exc_info=True)
            return {}
        
    # In app/services/transaction_service.py
    def run_fraud_detection_for_user_sync(self, user_id: int) -> Dict:
        """
        Synchronous version of fraud detection.
        Use this until async issues are resolved.
        """
        logger.info(f"Starting SYNC fraud detection for user_id: {user_id}")
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {'status': 'error', 'message': 'User not found'}
        
        # Load user's active fraud detection config
        config_obj = ConfigService.get_active_config(user.id)
        config_dict = config_obj.to_dict() if config_obj else {}

        # Initialize fraud detection service with user's config
        fraud_service = FraudDetectionService(user=user, config=config_dict)

        try:
            # Step 1: Historical analysis (first run only)
            historical_report, all_transactions = self._run_historical_analysis_sync(fraud_service, user)

            # Step 2: Recent transactions check
            recent_detections = self._check_recent_transactions_sync(user, fraud_service)

            # Step 3: Send summary to user with transactions for agent info
            self._send_detection_summary_sync(user, historical_report, recent_detections, transactions=all_transactions)

            logger.info(f"Completed fraud detection for user: {user.email}")
            
            return {
                'status': 'success',
                'user_id': user_id,
                'user_email': user.email,
                'historical_patterns': len(historical_report.get('detections', [])),
                'recent_detections': len(recent_detections),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in fraud detection: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

    def _run_historical_analysis_sync(self, fraud_service, user):
        """Synchronous historical analysis. Returns (result, transactions).

        Runs once per user — covers ALL historical transactions with no date or
        count limit, then records a 'historical' FraudReportHistory entry so
        it is never triggered again.
        """
        logger.info(f"Running historical analysis for {user.email}")

        # Check if user has already received the historical report.
        # NULL report_type rows are legacy records treated as 'historical'.
        already_sent = FraudReportHistory.query.filter(
            FraudReportHistory.user_id == user.id,
            db.or_(
                FraudReportHistory.report_type == 'historical',
                FraudReportHistory.report_type == None  # noqa: E711
            )
        ).count()

        if already_sent > 0:
            logger.info(f"User {user.email} already received historical report — skipping")
            return {'summary': {}, 'detections': []}, []

        # Get all shortcodes for this user
        shortcodes = self.get_all_shortcodes_in_txn_tbl(user)
        all_transactions = []

        # Fetch ALL historical transactions — no date cutoff, no row limit
        for shortcode in shortcodes:
            transactions = self._get_all_transactions_for_shortcode_sync(shortcode, user.id)
            all_transactions.extend(transactions)

        logger.info(
            f"Historical analysis: {len(all_transactions)} total transactions "
            f"across {len(shortcodes)} shortcodes for {user.email}"
        )

        if all_transactions:
            # Run all fraud-type detections
            result = fraud_service.run_detection(all_transactions)

            # Persist a FraudAlert record for EVERY detection (all types, all risk
            # levels) so the deduplication logic can exclude these transaction IDs
            # from all future periodic scans.
            detections = result.get('detections', [])
            recorded = 0
            for detection in detections:
                fraud_type = detection.get('fraud_type', 'unknown')
                if self._record_fraud_alert_sync(detection, fraud_type, user):
                    recorded += 1
            logger.info(
                f"Historical report: recorded {recorded}/{len(detections)} new "
                f"FraudAlert entries for user {user.email}"
            )

            # Send the one-time historical fraud report email
            fraud_service.send_historical_report(
                result['summary'],
                transactions=all_transactions,
                detections=detections,
            )

            # Persist the history record so we never re-send the historical report
            self._record_report_history_sync(user, result['summary'], report_type='historical')

            return result, all_transactions

        # No transactions found — still record the fact that we ran the historical check
        # so the periodic scan can start immediately when transactions arrive later.
        self._record_report_history_sync(user, {}, report_type='historical')
        return {'summary': {}, 'detections': []}, []

    def _send_detection_summary_sync(self, user, historical_report, recent_detections, transactions=None):
        """
        Send fraud detection summary as a formatted HTML email with tables.
        Includes: summary cards, detections table, culpable agents, historical analysis.
        """
        from app.utils.email_utils import _send_email
        from datetime import datetime

        now = datetime.now()
        report_id = f"PFR-{now.strftime('%Y%m%d%H%M%S')}-{user.id}"

        # Count detections by risk level
        high_risk_count = sum(1 for d in recent_detections if d.get('risk_level') == 'HIGH')
        medium_risk_count = sum(1 for d in recent_detections if d.get('risk_level') == 'MEDIUM')
        low_risk_count = len(recent_detections) - high_risk_count - medium_risk_count
        total_count = len(recent_detections)

        def risk_badge(level):
            colors = {'HIGH': '#dc2626', 'MEDIUM': '#ea580c', 'LOW': '#ca8a04'}
            bg = colors.get(level, '#6b7280')
            return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">{level}</span>'

        def fraud_badge(ftype):
            colors = {'SPLIT TRANSACTION': '#7c3aed', 'ROLLOVER FRAUD': '#0891b2', 'RAPID BACK FORTH': '#be185d'}
            label = (ftype or 'Unknown').replace('_', ' ').upper()
            bg = colors.get(label, '#4b5563')
            return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">{label}</span>'

        # --- Build HTML ---
        html = f'''
        <div style="font-family:Arial,Helvetica,sans-serif;max-width:1100px;margin:0 auto;background:#f8fafc;">
          <!-- Header Banner -->
          <div style="background:linear-gradient(135deg,#1e293b,#334155);padding:24px 32px;border-radius:8px 8px 0 0;">
            <h1 style="color:#fff;margin:0;font-size:22px;">&#128680; Periodic Fraud Detection Alert</h1>
            <p style="color:#94a3b8;margin:8px 0 0;font-size:13px;">
              Report Time: {now.strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; User: {user.email} &nbsp;|&nbsp; Report ID: {report_id}
            </p>
          </div>

          <div style="padding:24px 32px;background:#ffffff;">
            <!-- Summary Cards -->
            <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
              <tr>
                <td style="padding:4px;">
                  <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;border-radius:4px;">
                    <div style="font-size:11px;color:#991b1b;text-transform:uppercase;font-weight:600;">High Risk</div>
                    <div style="font-size:28px;font-weight:700;color:#dc2626;">{high_risk_count}</div>
                  </div>
                </td>
                <td style="padding:4px;">
                  <div style="background:#fff7ed;border-left:4px solid #ea580c;padding:12px 16px;border-radius:4px;">
                    <div style="font-size:11px;color:#9a3412;text-transform:uppercase;font-weight:600;">Medium Risk</div>
                    <div style="font-size:28px;font-weight:700;color:#ea580c;">{medium_risk_count}</div>
                  </div>
                </td>
                <td style="padding:4px;">
                  <div style="background:#fefce8;border-left:4px solid #ca8a04;padding:12px 16px;border-radius:4px;">
                    <div style="font-size:11px;color:#854d0e;text-transform:uppercase;font-weight:600;">Low Risk</div>
                    <div style="font-size:28px;font-weight:700;color:#ca8a04;">{low_risk_count}</div>
                  </div>
                </td>
                <td style="padding:4px;">
                  <div style="background:#eff6ff;border-left:4px solid #2563eb;padding:12px 16px;border-radius:4px;">
                    <div style="font-size:11px;color:#1e40af;text-transform:uppercase;font-weight:600;">Total</div>
                    <div style="font-size:28px;font-weight:700;color:#2563eb;">{total_count}</div>
                  </div>
                </td>
              </tr>
            </table>
        '''        

        # --- Detections Table ---
        if recent_detections:
            html += '''
            <h2 style="font-size:16px;color:#1e293b;margin:24px 0 12px;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">
            Fraudulent Transactions Detected
            </h2>
            <div style="overflow-x:auto;width:100%;">
            <table style="width:140%;border-collapse:collapse;font-size:12px;border:1px solid #e2e8f0;">
                <thead>
                <tr style="background:#f1f5f9;">
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:3%;">#</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:7%;">Fraud Type</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:5%;">Risk</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:10%;">Account</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:right;width:8%;">Amount (KES)</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:7%;">Shortcode</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:15%;">Agent Company / Location</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:25%;">Transactions</th>
                    <th style="padding:10px;border:1px solid #e2e8f0;text-align:left;width:20%;">Reason</th>
                </tr>
                </thead>
                <tbody>
            '''

            for idx, detection in enumerate(recent_detections[:20], 1):
                fraud_type = detection.get('fraud_type', 'Unknown')
                risk_level = detection.get('risk_level', 'UNKNOWN')
                account_phone = detection.get('account_phone', 'Unknown')
                account_name = detection.get('account_name', 'Unknown')
                total_amount = detection.get('total_amount', 0)
                business_shortcode = detection.get('business_shortcode', 'N/A')
                explanation = detection.get('explanation', 'No explanation available.')

                # Agent company info
                agent_info = detection.get('agent_info', {})
                agent_companies = agent_info.get('agent_companies', [])
                agent_col = ''
                if agent_companies:
                    for ac in agent_companies[:2]:
                        agent_col += f"<div style='margin-bottom:6px;'><strong>{ac.get('company_name', 'N/A')}</strong><br/>"
                        agent_col += f"<span style='color:#475569;'>SC: {ac.get('short_code', 'N/A')}</span><br/>"
                        agent_col += f"<span style='color:#475569;'>Loc: {ac.get('location', 'N/A')}</span><br/>"
                        agent_col += f"<span style='color:#475569;'>Agent/Store: {ac.get('agent_number', 'N/A')}/{ac.get('store_number', 'N/A')}</span></div>"
                else:
                    agent_col = '<span style="color:#64748b;">N/A</span>'

                # Transaction details mini-list
                txn_details = detection.get('transaction_details', [])
                txn_col = ''
                if txn_details:
                    for txn in txn_details[:5]:
                        party = ''
                        if txn.get('party_name') or txn.get('party_phone'):
                            party = f"<span style='color:#475569;'> → {txn.get('party_name', '')} ({txn.get('party_phone', '')})</span>"
                        txn_col += (
                            f"<div style='margin-bottom:6px;padding-bottom:4px;border-bottom:1px dashed #e2e8f0;'>"
                            f"<span style='font-weight:600;'>{txn.get('receipt_no', 'N/A')}</span> "
                            f"<span style='font-weight:600;color:#0f172a;'>KES {txn.get('amount', 0):,.2f}</span> "
                            f"<span style='background:#f1f5f9;padding:2px 6px;border-radius:4px;'>{txn.get('type', '')}</span> "
                            f"<span style='color:#64748b;display:block;margin-top:2px;'>{txn.get('time', '')}</span>"
                            f"{party}</div>"
                        )
                    if len(txn_details) > 5:
                        txn_col += f"<div style='color:#64748b;font-style:italic;background:#f8fafc;padding:4px;border-radius:4px;'>+{len(txn_details)-5} more transactions</div>"
                else:
                    receipt_nos = detection.get('receipt_nos', [])
                    txn_col = f"<span style='color:#0f172a;'>{', '.join(receipt_nos[:5])}</span>"
                    if len(receipt_nos) > 5:
                        txn_col += f'<span style="color:#64748b;display:block;margin-top:4px;">+{len(receipt_nos)-5} more</span>'

                row_bg = '#ffffff' if idx % 2 == 1 else '#f8fafc'
                html += f'''
                <tr style="background:{row_bg};">
                <td style="padding:12px 10px;border:1px solid #e2e8f0;text-align:center;font-weight:600;">{idx}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;">{fraud_badge(fraud_type)}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;">{risk_badge(risk_level)}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;">
                    <span style="font-weight:600;">{account_phone}</span><br/>
                    <span style="color:#475569;font-size:11px;">{account_name}</span>
                </td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;text-align:right;font-weight:700;font-size:13px;">KES {total_amount:,.2f}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;font-family:monospace;">{business_shortcode}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;font-size:11px;line-height:1.5;">{agent_col}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;font-size:11px;line-height:1.5;">{txn_col}</td>
                <td style="padding:12px 10px;border:1px solid #e2e8f0;font-size:11px;line-height:1.5;word-wrap:break-word;max-width:300px;">{explanation}</td>
                </tr>
                '''

            html += '</tbody></table></div>'

            if len(recent_detections) > 20:
                html += f'<p style="color:#64748b;font-size:12px;margin-top:12px;">... and {len(recent_detections) - 20} more detections not shown</p>'


        # --- Culpable Agents Table ---
        culpable_data = historical_report.get('culpable_agents', {})
        culpable_agents = culpable_data.get('culpable_agents', [])
        if culpable_agents:
            html += f'''
            <h2 style="font-size:16px;color:#1e293b;margin:28px 0 12px;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">
              Culpable Agents &mdash; {len(culpable_agents)} involved, KES {culpable_data.get('total_fraud_amount', 0):,.2f} at risk
            </h2>
            <table style="width:100%;border-collapse:collapse;font-size:12px;border:1px solid #e2e8f0;">
              <thead>
                <tr style="background:#f1f5f9;">
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">#</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Company</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Shortcode</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Location</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:right;">Fraud Amount (KES)</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:center;">High/Med/Low</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Fraud Types</th>
                  <th style="padding:8px;border:1px solid #e2e8f0;text-align:left;">Personnel</th>
                </tr>
              </thead>
              <tbody>
            '''

            for idx, agent in enumerate(culpable_agents[:10], 1):
                row_bg = '#ffffff' if idx % 2 == 1 else '#f8fafc'
                fraud_types = ', '.join(agent.get('fraud_types', []))
                personnel = ''
                for ua in agent.get('user_agents', [])[:3]:
                    verified = '&#10003;' if ua.get('is_verified') else '&#10007;'
                    personnel += f"{ua.get('name', 'N/A')} (ID: {ua.get('id_number', 'N/A')}, {verified})<br/>"

                html += f'''
                <tr style="background:{row_bg};">
                  <td style="padding:8px;border:1px solid #e2e8f0;text-align:center;">{idx}</td>
                  <td style="padding:8px;border:1px solid #e2e8f0;font-weight:600;">{agent.get('company_name', 'Unknown')}</td>
                  <td style="padding:8px;border:1px solid #e2e8f0;">{agent.get('shortcode', 'N/A')}</td>
                  <td style="padding:8px;border:1px solid #e2e8f0;">{agent.get('location', 'N/A')}</td>
                  <td style="padding:8px;border:1px solid #e2e8f0;text-align:right;font-weight:600;">{agent.get('total_fraud_amount', 0):,.2f}</td>
                  <td style="padding:8px;border:1px solid #e2e8f0;text-align:center;">
                    <span style="color:#dc2626;">{agent.get('high_risk_count', 0)}</span> /
                    <span style="color:#ea580c;">{agent.get('medium_risk_count', 0)}</span> /
                    <span style="color:#ca8a04;">{agent.get('low_risk_count', 0)}</span>
                  </td>
                  <td style="padding:8px;border:1px solid #e2e8f0;font-size:11px;">{fraud_types}</td>
                  <td style="padding:8px;border:1px solid #e2e8f0;font-size:11px;">{personnel or 'N/A'}</td>
                </tr>
                '''

            html += '</tbody></table>'

            if len(culpable_agents) > 10:
                html += f'<p style="color:#64748b;font-size:12px;margin-top:8px;">... and {len(culpable_agents) - 10} more agents with suspicious activity</p>'

        # --- Historical Analysis ---
        historical_patterns = len(historical_report.get('detections', []))
        if historical_patterns > 0:
            summary = historical_report.get('summary', {})
            html += f'''
            <h2 style="font-size:16px;color:#1e293b;margin:28px 0 12px;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">
              Historical Analysis
            </h2>
            <table style="border-collapse:collapse;font-size:13px;border:1px solid #e2e8f0;">
              <tr style="background:#f1f5f9;">
                <td style="padding:8px 16px;border:1px solid #e2e8f0;font-weight:600;">Patterns Found</td>
                <td style="padding:8px 16px;border:1px solid #e2e8f0;">{historical_patterns}</td>
              </tr>
              <tr>
                <td style="padding:8px 16px;border:1px solid #e2e8f0;font-weight:600;">Split Transactions</td>
                <td style="padding:8px 16px;border:1px solid #e2e8f0;">{summary.get('split_transactions', 0)}</td>
              </tr>
              <tr style="background:#f1f5f9;">
                <td style="padding:8px 16px;border:1px solid #e2e8f0;font-weight:600;">Rollover Fraud</td>
                <td style="padding:8px 16px;border:1px solid #e2e8f0;">{summary.get('rollover_fraud', 0)}</td>
              </tr>
              <tr>
                <td style="padding:8px 16px;border:1px solid #e2e8f0;font-weight:600;">Rapid Patterns</td>
                <td style="padding:8px 16px;border:1px solid #e2e8f0;">{summary.get('rapid_patterns', 0)}</td>
              </tr>
            </table>
            '''

        # --- Footer ---
        html += f'''
            <div style="margin-top:32px;padding:16px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;text-align:center;">
              <strong style="color:#991b1b;font-size:14px;">&#9888; ACTION REQUIRED: Please review flagged transactions</strong><br/>
              <span style="color:#64748b;font-size:12px;">Report ID: {report_id}</span>
            </div>
          </div>

          <div style="background:#1e293b;padding:16px 32px;border-radius:0 0 8px 8px;text-align:center;">
            <p style="color:#64748b;font-size:11px;margin:0;">Kwamz AI Fraud Detection System &mdash; Automated Report</p>
          </div>
        </div>
        '''

        # Send HTML email
        try:
            _send_email(
                subject=f"[FRAUD ALERT] Periodic Detection Report - {now.strftime('%Y-%m-%d %H:%M')}",
                html=html,
                recipient=user.email,
            )
            logger.info(f"Sent HTML fraud detection summary to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send summary email: {str(e)}")

    def _get_agent_companies_from_transactions(self, transactions):
        """Get agent companies from transactions."""
        from app.model.agentcompany import AgentCompany
        agent_companies = []
        seen_ids = set()

        for txn in transactions:
            agent_id = txn.get('agent_id')
            shortcode = txn.get('business_shortcode')

            if agent_id and agent_id not in seen_ids:
                agent = AgentCompany.query.get(agent_id)
                if agent:
                    agent_companies.append(agent)
                    seen_ids.add(agent_id)

            if shortcode:
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

    def _get_user_agents_from_agent_companies(self, agent_companies):
        """Get user agents from agent companies."""
        user_agents = []
        seen_ids = set()

        for agent_company in agent_companies:
            for user_agent in agent_company.user_agents:
                if user_agent.id not in seen_ids:
                    user_agents.append(user_agent)
                    seen_ids.add(user_agent.id)

        return user_agents

    def _format_agent_companies_for_email(self, agent_companies):
        """Format agent companies for email HTML."""
        if not agent_companies:
            return '<p style="color: #757575; font-style: italic; font-size: 13px;">No agent companies identified.</p>'

        html = ''
        for agent in agent_companies[:5]:  # Limit to 5
            risk_color = {'high': '#c62828', 'medium': '#e65100', 'low': '#2e7d32'}.get(
                (agent.fraud_risk_level or 'low').lower(), '#757575')
            risk_bg = {'high': '#ffcdd2', 'medium': '#fff3e0', 'low': '#e8f5e9'}.get(
                (agent.fraud_risk_level or 'low').lower(), '#f5f5f5')

            html += f'''
            <div style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td>
                            <strong style="color: #1a237e; font-size: 14px;">{agent.company_name or 'Unknown'}</strong>
                            <span style="background-color: {risk_bg}; color: {risk_color}; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 8px;">{agent.fraud_risk_level or 'Unknown'}</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding-top: 6px; font-size: 12px; color: #616161;">
                            📍 {agent.location or 'N/A'} | 📞 {agent.contact_phone or 'N/A'} | 🏷️ {agent.short_code or agent.business_short_code or 'N/A'}
                        </td>
                    </tr>
                </table>
            </div>
            '''
        if len(agent_companies) > 5:
            html += f'<p style="color: #757575; font-size: 12px; text-align: center;">+{len(agent_companies) - 5} more companies</p>'
        return html

    def _format_user_agents_for_email(self, user_agents):
        """Format user agents for email HTML."""
        if not user_agents:
            return '<p style="color: #757575; font-style: italic; font-size: 13px;">No user agents identified.</p>'

        html = '<table width="100%" cellpadding="0" cellspacing="0" style="font-size: 12px; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">'
        html += '''
            <tr style="background-color: #e8f5e9;">
                <td style="padding: 10px 12px; font-weight: 600; color: #2e7d32;">Name</td>
                <td style="padding: 10px 12px; font-weight: 600; color: #2e7d32;">ID Number</td>
                <td style="padding: 10px 12px; font-weight: 600; color: #2e7d32;">Phone</td>
                <td style="padding: 10px 12px; font-weight: 600; color: #2e7d32; text-align: center;">Status</td>
            </tr>
        '''
        for i, agent in enumerate(user_agents[:5]):
            bg = '#ffffff' if i % 2 == 0 else '#fafafa'
            status = '<span style="color: #2e7d32;">✓</span>' if agent.is_authentic else '<span style="color: #c62828;">✗</span>'
            html += f'''
            <tr style="background-color: {bg};">
                <td style="padding: 10px 12px; color: #424242;"><strong>{agent.firstname} {agent.lastname}</strong></td>
                <td style="padding: 10px 12px; color: #616161; font-family: monospace;">{agent.idnumber}</td>
                <td style="padding: 10px 12px; color: #616161;">{agent.phone_number or 'N/A'}</td>
                <td style="padding: 10px 12px; text-align: center;">{status}</td>
            </tr>
            '''
        html += '</table>'
        if len(user_agents) > 5:
            html += f'<p style="color: #757575; font-size: 12px; text-align: center; margin-top: 8px;">+{len(user_agents) - 5} more agents</p>'
        return html

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
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return obj

    def _record_report_history_sync(self, user, report_summary, report_type: str = 'historical'):
        """Record report history synchronously.

        Args:
            user: The User object.
            report_summary: Summary dict from fraud detection.
            report_type: 'historical' for the one-time full scan, 'periodic' for recurring.
        """
        try:
            serialized_report = self._serialize_for_json(report_summary)

            history = FraudReportHistory(
                user_id=user.id,
                report_type=report_type,
                analysis_period_days=None,  # not applicable — we scan all data
                total_transactions=report_summary.get('total_transactions_analyzed', 0),
                suspicious_patterns=report_summary.get('suspicious_patterns_found', 0),
                accounts_flagged=report_summary.get('accounts_flagged', 0),
                report_data=serialized_report
            )

            db.session.add(history)
            db.session.commit()

            logger.info(f"Recorded {report_type} fraud report history for user {user.email}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record report history: {str(e)}")
        
    def get_all_shortcodes_in_txn_tbl(self, user:User) -> List[str]:
        """Get all shortcodes that have been registered in the transactions table."""
        try:
            companies = company_service.get_companies_by_user_id(user.id)
            company_ids = [company.id for company in companies]
            with db_pool.get_cursor() as cursor:                
                return self._get_all_shortcodes_in_txn_tbl(cursor, company_ids)
        except Exception as e:
            logger.error(f"Error getting shortcodes: {str(e)}", exc_info=True)
            return []
    
    def _get_all_shortcodes_in_txn_tbl(self, cursor, company_ids=None):
        """Get all shortcodes that have been registered in the transactions table."""
        try:
            query = """
                SELECT DISTINCT business_shortcode
                FROM transactions
                WHERE business_shortcode IS NOT NULL
                AND business_shortcode != ''
            """
            
            if company_ids:
                # Ensure company_ids is a list/tuple
                if isinstance(company_ids, (list, tuple)):
                    # Don't wrap in another tuple - just use the tuple directly
                    query += " AND company_id IN %s"
                    cursor.execute(query, (tuple(company_ids),))
                else:
                    # Single company ID
                    query += " AND company_id = %s"
                    cursor.execute(query, (company_ids,))
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            # Debug logging
            logger.debug(f"Shortcode query returned {len(results)} rows")
            if results:
                logger.debug(f"First row: {results[0]}, type: {type(results[0])}")
            
            # Handle both tuple and dict cursor results
            shortcodes = []
            for row in results:
                try:
                    # Try dict access first
                    if isinstance(row, dict):
                        shortcode = row.get('business_shortcode')
                    else:
                        # Try tuple access
                        shortcode = row[0] if len(row) > 0 else None
                    
                    if shortcode and shortcode.strip():
                        shortcodes.append(shortcode.strip())
                        
                except Exception as e:
                    logger.warning(f"Error parsing row {row}: {e}")
                    continue
            
            logger.info(f"Found {len(shortcodes)} shortcodes")
            return shortcodes
            
        except Exception as e:
            logger.error(f"Failed to fetch shortcodes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to fetch shortcodes: {e}") from e
    
    def get_recent_transactions_for_shortcode(self, shortcode: str, 
                                            limit: int = 100) -> List[Dict]:
        """Get recent transactions for a specific shortcode."""
        try:
            with db_pool.get_cursor() as cursor:
                return self._get_recent_transactions_for_shortcode(cursor, shortcode, limit)
        except Exception as e:
            logger.error(f"Error getting transactions for {shortcode}: {str(e)}", exc_info=True)
            return []
    
    def _get_recent_transactions_for_shortcode(self, cursor, shortcode: str, 
                                             limit: int) -> List[Dict]:
        """Get recent transactions for a specific shortcode."""
        query = """
            SELECT 
                id, receipt_no, completion_time, initiation_time,
                details, transaction_status, paid_in, withdrawn,
                balance, balance_confirmed, reason_type, other_party_info,
                linked_transaction_id, account_number, currency,
                transaction_type, business_shortcode, company_id, agent_id,
                created_at, updated_at
            FROM transactions
            WHERE business_shortcode = %s
            AND transaction_status = 'Completed'
            ORDER BY completion_time DESC
            LIMIT %s
        """
        cursor.execute(query, (shortcode, limit))
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        
        transactions = []
        for row in results:
            txn = dict(zip(columns, row))
            # Convert datetime objects
            for date_field in ['completion_time', 'initiation_time', 'created_at', 'updated_at']:
                if txn.get(date_field) and isinstance(txn[date_field], datetime):
                    txn[date_field] = txn[date_field]
            transactions.append(txn)
        
        return transactions
    
    def get_historical_transactions_for_shortcode(self, shortcode: str, 
                                                days: int = 30) -> List[Dict]:
        """Get historical transactions for fraud analysis."""
        try:
            with db_pool.get_cursor() as cursor:
                return self._get_historical_transactions_for_shortcode(cursor, shortcode, days)
        except Exception as e:
            logger.error(f"Error getting historical transactions: {str(e)}", exc_info=True)
            return []
    
    def _get_historical_transactions_for_shortcode(self, cursor, shortcode: str, 
                                             days: int) -> List[Dict]:
        """Get historical transactions for fraud analysis."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                id, receipt_no, completion_time, initiation_time,
                details, transaction_status, paid_in, withdrawn,
                balance, balance_confirmed, reason_type, other_party_info,
                linked_transaction_id, account_number, currency,
                transaction_type, business_shortcode, company_id, agent_id,
                created_at, updated_at
            FROM transactions
            WHERE business_shortcode = %s
            AND transaction_status = 'Completed'
            AND completion_time >= %s
            ORDER BY completion_time DESC
        """
        cursor.execute(query, (shortcode, cutoff_date))
        
        # Use cursor.description to create a row factory that returns dictionaries
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        
        # Direct conversion - this assumes no corruption in DB
        transactions = [dict(zip(columns, row)) for row in results]
        
        # Post-processing: convert Decimal to float, handle 'NaN' strings
        for txn in transactions:
            # Convert Decimal to float for numeric fields
            for field in ['paid_in', 'withdrawn', 'balance']:
                if field in txn and isinstance(txn[field], Decimal):
                    txn[field] = float(txn[field])
            
            # Convert 'NaN' strings to None
            for field in ['linked_transaction_id', 'account_number']:
                if field in txn and txn[field] == 'NaN':
                    txn[field] = None
        
        logger.info(f"Retrieved {len(transactions)} transactions for {shortcode}")
        return transactions

    async def run_fraud_detection_for_user_async(self, user_id: int) -> Dict:
        """
        Run fraud detection for a user asynchronously.
        This is the main method called by Celery task.
        """
        logger.info(f"Starting async fraud detection for user_id: {user_id}")
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {'status': 'error', 'message': 'User not found'}
        
        # Load user's active fraud detection config
        config_obj = ConfigService.get_active_config(user.id)
        config_dict = config_obj.to_dict() if config_obj else {}

        # Initialize fraud detection service with user's config
        fraud_service = FraudDetectionService(user=user, config=config_dict)

        # Step 1: Historical analysis (first run only)
        historical_report = await self._run_historical_analysis(fraud_service, user)
        
        # Step 2: Recent transactions check
        recent_detections = await self._check_recent_transactions(user,fraud_service)
        
        # Step 3: Send summary to user
        await self._send_detection_summary(user, historical_report, recent_detections)
        
        logger.info(f"Completed fraud detection for user: {user.email}")
        
        return {
            'status': 'success',
            'user_id': user_id,
            'historical_patterns': len(historical_report.get('detections', [])),
            'recent_detections': len(recent_detections),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _run_historical_analysis(self, fraud_service: FraudDetectionService, user: User) -> Dict:
        """Run historical fraud analysis (first time for user)."""
        # Check if user has already received the historical report.
        # NULL report_type rows are legacy records treated as 'historical'.
        already_sent = FraudReportHistory.query.filter(
            FraudReportHistory.user_id == user.id,
            db.or_(
                FraudReportHistory.report_type == 'historical',
                FraudReportHistory.report_type == None  # noqa: E711
            )
        ).count()

        if already_sent > 0:
            logger.info(f"User {user.email} already received historical report — skipping")
            return {'summary': {}, 'detections': []}
        
        logger.info(f"Running historical analysis for {user.email}")
        
        # Get all shortcodes
        shortcodes = self.get_all_shortcodes_in_txn_tbl(user)
        all_transactions = []
        
        # Fetch historical transactions
        loop = asyncio.get_event_loop()
        
        for shortcode in shortcodes:
            transactions = await loop.run_in_executor(
                executor,
                lambda s=shortcode: self.get_historical_transactions_for_shortcode(s, days=30)
            )
            all_transactions.extend(transactions)
        
        if all_transactions:
            # Run detection
            result = await loop.run_in_executor(
                executor,
                fraud_service.run_detection,
                all_transactions
            )
            
            # Send historical report email
            await loop.run_in_executor(
                executor,
                fraud_service.send_historical_report,
                result['summary']
            )
            
            # Record in database
            await self._record_report_history(user, result['summary'])
            
            return result
        
        return {'summary': {}, 'detections': []}
    
    async def _check_recent_transactions(self, user:User ,fraud_service: FraudDetectionService) -> List[Dict]:
        """Check recent transactions for fraud patterns."""
        logger.info("Checking recent transactions for fraud patterns")
        
        shortcodes = self.get_all_shortcodes_in_txn_tbl(user)
        all_detections = []
        
        loop = asyncio.get_event_loop()
        
        # Process shortcodes in batches
        batch_size = 3
        for i in range(0, len(shortcodes), batch_size):
            batch = shortcodes[i:i + batch_size]
            
            batch_tasks = []
            for shortcode in batch:
                task = loop.run_in_executor(
                    executor,
                    lambda s=shortcode: self._process_single_shortcode(fraud_service, s)
                )
                batch_tasks.append(task)
            
            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing shortcode: {result}")
                elif result:
                    all_detections.extend(result)
        
        return all_detections
    
    def _process_single_shortcode(self, fraud_service: FraudDetectionService, shortcode: str) -> List[Dict]:
        """Process a single shortcode (runs in thread pool)."""
        # Get recent transactions
        transactions = self.get_recent_transactions_for_shortcode(
            shortcode,
            limit=fraud_service.config.get('recent_transactions_limit', 100)
        )
        
        if not transactions:
            return []
        
        # Run detection
        result = fraud_service.run_detection(transactions)
        
        # Send notifications for high-risk detections
        for detection in result.get('detections', []):
            if detection.get('risk_level') == 'HIGH':
                # Check alert limit before sending
                receipt_nos = detection.get('receipt_nos', [])
                if not self._should_limit_alerts(receipt_nos):
                    fraud_service.send_fraud_notification(detection, detection.get('fraud_type'))
        
        return result.get('detections', [])
    
    async def _send_detection_summary(self, user: User, historical_report: Dict, recent_detections: List[Dict]):
        """Send a summary of the fraud detection run to the user."""
        summary_template = """
        <html><body>
        <h2>🔍 Fraud Detection Summary</h2>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>User:</strong> {user_email}</p>
        
        <h3>📊 Results Summary</h3>
        <ul>
        <li><strong>Historical Analysis:</strong> {historical_patterns} suspicious patterns found</li>
        <li><strong>Recent Transactions Check:</strong> {recent_detections} fraud alerts detected</li>
        <li><strong>High-Risk Alerts:</strong> {high_risk_count}</li>
        </ul>
        
        <h3>🚨 Immediate Actions Required</h3>
        <p>Please review the detailed reports sent to your email.</p>
        
        <hr>
        <p style="color: #666; font-size: 12px;">
        This is an automated fraud detection summary.
        </p>
        </body></html>
        """
        
        # Count high-risk detections
        high_risk_count = sum(1 for d in recent_detections if d.get('risk_level') == 'HIGH')
        
        body = summary_template.format(
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            user_email=user.email,
            historical_patterns=len(historical_report.get('detections', [])),
            recent_detections=len(recent_detections),
            high_risk_count=high_risk_count
        )
        
        # Send email
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            lambda: _send_email(
                subject=f"Fraud Detection Summary - {datetime.now().strftime('%Y-%m-%d')}",
                html=body,
                recipient=user.email,
            )
        )

    def _check_recent_transactions_sync(self, user: User, fraud_service: FraudDetectionService) -> List[Dict]:
        """Periodic fraud check — only processes transactions that have NOT already been flagged.

        Starts from the completion_time of the most recently flagged transaction
        produced by the historical report, so there is no overlap with the historical scan.
        Any transaction ID already present in a FraudAlert record is excluded before
        running detection, guaranteeing a transaction is never flagged twice.
        """
        logger.info(f"Checking recent transactions for fraud patterns for user: {user.email}")

        try:
            # Collect all transaction IDs that have already been flagged for this user
            already_flagged_ids = self._get_already_flagged_transaction_ids(user.id)

            # Determine the earliest point in time the periodic scan should cover.
            # We start from right after the most-recent transaction flagged in the
            # historical report so we do not re-analyse already-processed transactions.
            after_date = self._get_latest_flagged_transaction_time(user.id)
            if after_date:
                logger.info(
                    f"Periodic scan for {user.email} starts after {after_date} "
                    f"({len(already_flagged_ids)} already-flagged transaction IDs excluded)"
                )
            else:
                logger.info(
                    f"No prior flagged transactions found for {user.email}; "
                    "periodic scan covers all available transactions"
                )

            shortcodes = self.get_all_shortcodes_in_txn_tbl(user)
            logger.info(f"Found {len(shortcodes)} shortcodes to check")

            if not shortcodes:
                logger.info("No shortcodes found for user")
                return []

            all_detections = []
            processed_count = 0

            batch_size = 3
            for i in range(0, len(shortcodes), batch_size):
                batch = shortcodes[i:i + batch_size]
                logger.info(
                    f"Processing batch {i // batch_size + 1}/"
                    f"{(len(shortcodes) + batch_size - 1) // batch_size}: {batch}"
                )

                for shortcode in batch:
                    try:
                        logger.info(f"Processing shortcode: {shortcode}")
                        detections = self._process_single_shortcode_sync(
                            fraud_service,
                            shortcode,
                            user,
                            after_date=after_date,
                            already_flagged_ids=already_flagged_ids,
                        )

                        if detections:
                            all_detections.extend(detections)
                            logger.info(
                                f"Found {len(detections)} suspicious patterns for shortcode {shortcode}"
                            )

                        processed_count += 1
                        if processed_count % 10 == 0:
                            logger.info(
                                f"Progress: Processed {processed_count}/{len(shortcodes)} shortcodes"
                            )

                    except Exception as e:
                        logger.error(f"Error processing shortcode {shortcode}: {str(e)}")
                        continue

            logger.info(
                f"Completed periodic check. Found {len(all_detections)} total suspicious patterns"
            )
            return all_detections

        except Exception as e:
            logger.error(f"Error in _check_recent_transactions_sync: {str(e)}", exc_info=True)
            return []

    def _process_single_shortcode_sync(
        self,
        fraud_service: FraudDetectionService,
        shortcode: str,
        user: User = None,
        after_date: Optional[datetime] = None,
        already_flagged_ids: Optional[set] = None,
    ) -> List[Dict]:
        """Process a single shortcode for periodic fraud detection.

        Args:
            fraud_service: Initialised FraudDetectionService for the user.
            shortcode: The business short-code to scan.
            user: The User whose companies own this shortcode.
            after_date: Only fetch transactions with completion_time > after_date.
                        This anchors the periodic scan to start immediately after
                        the most recent transaction flagged by the historical report.
            already_flagged_ids: Set of transaction IDs already recorded in FraudAlert
                        records. Any transaction in this set is removed before
                        detection so it cannot be flagged a second time.
        """
        if already_flagged_ids is None:
            already_flagged_ids = set()

        try:
            logger.info(f"Getting transactions for shortcode: {shortcode} (after_date={after_date})")

            # Fetch transactions starting from after_date (no hard limit on count)
            transactions = self._get_periodic_transactions_for_shortcode_sync(
                shortcode=shortcode,
                user_id=user.id if user else None,
                after_date=after_date,
            )

            if not transactions:
                logger.debug(f"No new transactions found for shortcode: {shortcode}")
                return []

            # Remove transactions already flagged in a previous report
            if already_flagged_ids:
                before = len(transactions)
                transactions = [
                    t for t in transactions
                    if t.get('id') not in already_flagged_ids
                ]
                skipped = before - len(transactions)
                if skipped:
                    logger.info(
                        f"Shortcode {shortcode}: excluded {skipped} already-flagged "
                        f"transactions; {len(transactions)} remain for analysis"
                    )

            if not transactions:
                logger.debug(f"All transactions for shortcode {shortcode} already flagged — skipping")
                return []

            logger.info(f"Running fraud detection on {len(transactions)} transactions for {shortcode}")

            result = fraud_service.run_detection(transactions)
            detections = result.get('detections', [])

            if not detections:
                logger.debug(f"No fraud patterns detected for shortcode: {shortcode}")
                return []

            # Record ALL detections (every fraud type, every risk level) in FraudAlert
            # so they are excluded from all future periodic scans.
            high_risk_count = 0
            for detection in detections:
                fraud_type = detection.get('fraud_type', 'unknown')
                # Always persist (idempotent — skips if receipt_hash already exists)
                self._record_fraud_alert_sync(detection, fraud_type, user)

                # Send immediate email notification only for HIGH-risk detections
                if detection.get('risk_level') == 'HIGH':
                    receipt_nos = detection.get('receipt_nos', [])
                    if not self._should_limit_alerts(receipt_nos):
                        try:
                            # Note: _send_fraud_notification_sync also calls
                            # _record_fraud_alert_sync internally, but the
                            # duplicate guard in that method makes it a no-op.
                            self._send_fraud_notification_sync(detection, user)
                            high_risk_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send notification for detection: {str(e)}")

            if high_risk_count > 0:
                logger.info(f"Sent {high_risk_count} high-risk notifications for shortcode {shortcode}")

            return detections

        except Exception as e:
            logger.error(f"Error processing shortcode {shortcode}: {str(e)}", exc_info=True)
            return []


    def get_recent_transactions_for_shortcode_sync(
        self,
        shortcode: str,
        user_id: Optional[int] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent completed transactions for a specific shortcode.
        Filters by last N days (default 30) and optional user/company association.
        Returns list of dicts ready for JSON serialization.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Base query (matches your successful test script)
            base_query = """
                SELECT 
                    id, receipt_no, completion_time, initiation_time,
                    details, transaction_status, paid_in, withdrawn,
                    balance, balance_confirmed, reason_type, other_party_info,
                    linked_transaction_id, account_number, currency,
                    transaction_type, business_shortcode, company_id, agent_id,
                    created_at, updated_at
                FROM transactions
                WHERE business_shortcode = %s
                AND transaction_status = 'Completed'
                AND completion_time >= %s
            """

            params: Tuple = (shortcode, cutoff_date)

            # Optional: filter by user's associated companies
            if user_id:
                company_ids = self._get_company_ids_for_user(user_id)
                if not company_ids:
                    logger.warning(f"No companies found for user {user_id}")
                    return []

                base_query += " AND company_id IN %s"
                params += (tuple(company_ids),)

            # Add ordering and limit
            query = base_query + """
                ORDER BY completion_time DESC
                LIMIT %s
            """
            params += (limit,)

            with db_pool.get_cursor() as cursor:
                logger.debug(f"Executing query:\n{query}\nParams: {params}")

                cursor.execute(query, params)
                rows = cursor.fetchall()

                transactions = []
                for row in rows:
                    # RealDictCursor returns dict-like rows, convert to regular dict
                    tx_dict = dict(row)

                    # Convert problematic types for safe JSON serialization
                    for key in ['paid_in', 'withdrawn', 'balance', 'balance_confirmed']:
                        if key in tx_dict and isinstance(tx_dict[key], Decimal):
                            tx_dict[key] = self._parse_decimal_to_float(tx_dict[key])

                    for key in ['completion_time', 'initiation_time', 'created_at', 'updated_at']:
                        if key in tx_dict and isinstance(tx_dict[key], datetime):
                            tx_dict[key] = self._parse_date_to_string(tx_dict[key])

                    # Optional: handle any NaN strings if they appear (seen in logs)
                    for key in ['linked_transaction_id', 'account_number']:
                        if tx_dict.get(key) == 'NaN':
                            tx_dict[key] = None

                    transactions.append(tx_dict)

                logger.info(f"Retrieved {len(transactions)} recent transactions for shortcode {shortcode}")
                return transactions

        except Exception as e:
            logger.error(
                f"Failed to fetch transactions for shortcode {shortcode} "
                f"(user={user_id}, days={days}, limit={limit}): {str(e)}",
                exc_info=True
            )
            return []

    # ------------------------------------------------------------------
    # Historical fetch — no date cutoff, no row limit
    # ------------------------------------------------------------------

    def _get_all_transactions_for_shortcode_sync(
        self,
        shortcode: str,
        user_id: Optional[int] = None,
    ) -> List[Dict]:
        """Fetch ALL completed transactions for a shortcode with no date or count limit.

        Used exclusively by the one-time historical fraud report so that the
        entire transaction history is analysed.
        """
        try:
            base_query = """
                SELECT
                    id, receipt_no, completion_time, initiation_time,
                    details, transaction_status, paid_in, withdrawn,
                    balance, balance_confirmed, reason_type, other_party_info,
                    linked_transaction_id, account_number, currency,
                    transaction_type, business_shortcode, company_id, agent_id,
                    created_at, updated_at
                FROM transactions
                WHERE business_shortcode = %s
                AND transaction_status = 'Completed'
            """
            params: Tuple = (shortcode,)

            if user_id:
                company_ids = self._get_company_ids_for_user(user_id)
                if not company_ids:
                    logger.warning(f"No companies found for user {user_id}")
                    return []
                base_query += " AND company_id IN %s"
                params += (tuple(company_ids),)

            query = base_query + " ORDER BY completion_time ASC"

            with db_pool.get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                transactions = []
                for row in rows:
                    tx_dict = dict(row)
                    for key in ['paid_in', 'withdrawn', 'balance', 'balance_confirmed']:
                        if key in tx_dict and isinstance(tx_dict[key], Decimal):
                            tx_dict[key] = self._parse_decimal_to_float(tx_dict[key])
                    for key in ['completion_time', 'initiation_time', 'created_at', 'updated_at']:
                        if key in tx_dict and isinstance(tx_dict[key], datetime):
                            tx_dict[key] = self._parse_date_to_string(tx_dict[key])
                    for key in ['linked_transaction_id', 'account_number']:
                        if tx_dict.get(key) == 'NaN':
                            tx_dict[key] = None
                    transactions.append(tx_dict)

                logger.info(
                    f"Retrieved {len(transactions)} historical transactions for shortcode {shortcode}"
                )
                return transactions

        except Exception as e:
            logger.error(
                f"Failed to fetch all transactions for shortcode {shortcode} "
                f"(user={user_id}): {str(e)}",
                exc_info=True,
            )
            return []

    # ------------------------------------------------------------------
    # Periodic fetch — transactions strictly after a given datetime
    # ------------------------------------------------------------------

    def _get_periodic_transactions_for_shortcode_sync(
        self,
        shortcode: str,
        user_id: Optional[int] = None,
        after_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """Fetch completed transactions for a shortcode that occurred after *after_date*.

        When *after_date* is None the query returns all completed transactions
        (fallback for when no historical report has been sent yet).
        No row-count limit is applied so every new transaction is considered.
        """
        try:
            base_query = """
                SELECT
                    id, receipt_no, completion_time, initiation_time,
                    details, transaction_status, paid_in, withdrawn,
                    balance, balance_confirmed, reason_type, other_party_info,
                    linked_transaction_id, account_number, currency,
                    transaction_type, business_shortcode, company_id, agent_id,
                    created_at, updated_at
                FROM transactions
                WHERE business_shortcode = %s
                AND transaction_status = 'Completed'
            """
            params: Tuple = (shortcode,)

            if after_date:
                base_query += " AND completion_time > %s"
                params += (after_date,)

            if user_id:
                company_ids = self._get_company_ids_for_user(user_id)
                if not company_ids:
                    logger.warning(f"No companies found for user {user_id}")
                    return []
                base_query += " AND company_id IN %s"
                params += (tuple(company_ids),)

            query = base_query + " ORDER BY completion_time ASC"

            with db_pool.get_cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                transactions = []
                for row in rows:
                    tx_dict = dict(row)
                    for key in ['paid_in', 'withdrawn', 'balance', 'balance_confirmed']:
                        if key in tx_dict and isinstance(tx_dict[key], Decimal):
                            tx_dict[key] = self._parse_decimal_to_float(tx_dict[key])
                    for key in ['completion_time', 'initiation_time', 'created_at', 'updated_at']:
                        if key in tx_dict and isinstance(tx_dict[key], datetime):
                            tx_dict[key] = self._parse_date_to_string(tx_dict[key])
                    for key in ['linked_transaction_id', 'account_number']:
                        if tx_dict.get(key) == 'NaN':
                            tx_dict[key] = None
                    transactions.append(tx_dict)

                logger.info(
                    f"Retrieved {len(transactions)} periodic transactions for shortcode {shortcode} "
                    f"(after {after_date})"
                )
                return transactions

        except Exception as e:
            logger.error(
                f"Failed to fetch periodic transactions for shortcode {shortcode} "
                f"(user={user_id}, after={after_date}): {str(e)}",
                exc_info=True,
            )
            return []

    # ------------------------------------------------------------------
    # Deduplication helpers
    # ------------------------------------------------------------------

    def _get_already_flagged_transaction_ids(self, user_id: int) -> set:
        """Return a set of all transaction IDs that have already been recorded in a
        FraudAlert for this user.  Any transaction present in this set should be
        excluded from future fraud-detection runs to prevent double-flagging.
        """
        try:
            alerts = FraudAlert.query.filter_by(user_id=user_id).all()
            flagged: set = set()
            for alert in alerts:
                if alert.transaction_ids:
                    for tid in alert.transaction_ids.split(','):
                        tid = tid.strip()
                        if tid:
                            try:
                                flagged.add(int(tid))
                            except ValueError:
                                pass
            logger.debug(
                f"Found {len(flagged)} already-flagged transaction IDs for user {user_id}"
            )
            return flagged
        except Exception as e:
            logger.error(
                f"Error fetching already-flagged transaction IDs for user {user_id}: {str(e)}"
            )
            return set()

    def _get_latest_flagged_transaction_time(self, user_id: int) -> Optional[datetime]:
        """Return the completion_time of the most recently flagged transaction for a user.

        The periodic scan starts immediately after this timestamp so it does not
        re-analyse any transaction that was covered by the historical report.
        Returns None if no transactions have been flagged yet.
        """
        try:
            flagged_ids = self._get_already_flagged_transaction_ids(user_id)
            if not flagged_ids:
                return None

            latest_txn = Transaction.query.filter(
                Transaction.id.in_(flagged_ids)
            ).order_by(Transaction.completion_time.desc()).first()

            if latest_txn and latest_txn.completion_time:
                logger.info(
                    f"Latest flagged transaction time for user {user_id}: "
                    f"{latest_txn.completion_time}"
                )
                return latest_txn.completion_time

            return None

        except Exception as e:
            logger.error(
                f"Error finding latest flagged transaction time for user {user_id}: {str(e)}"
            )
            return None

    def _send_fraud_notification_sync(self, detection: Dict, user: User = None):
        """Send fraud notification email synchronously."""
        if not user or not user.email:
            logger.warning("No user or email configured for fraud notifications")
            return
        
        from app.utils.email_utils import _send_email
        
        fraud_type = detection.get('fraud_type', 'unknown')
        
        # Create email content based on fraud type
        if fraud_type == 'split_transaction':
            subject = f"[Fraud Alert] Split Transaction Detected - {detection.get('account_phone', 'Unknown')}"
            body = f"""
            <html><body>
            <h2>🚨 Split Transaction Fraud Alert</h2>
            <p><strong>Account:</strong> {detection.get('account_phone', 'Unknown')}</p>
            <p><strong>Transactions Found:</strong> {detection.get('transaction_count', 0)}</p>
            <p><strong>Total Amount:</strong> KES {detection.get('total_amount', 0):,.2f}</p>
            <p><strong>Risk Level:</strong> {detection.get('risk_level', 'MEDIUM')}</p>
            <hr>
            <p>Please review these transactions immediately.</p>
            </body></html>
            """
        elif fraud_type == 'rollover_fraud':
            subject = f"[Fraud Alert] Roll-over Pattern Detected - {detection.get('account_phone', 'Unknown')}"
            body = f"""
            <html><body>
            <h2>🔄 Roll-over Fraud Alert</h2>
            <p><strong>Account:</strong> {detection.get('account_phone', 'Unknown')}</p>
            <p><strong>Pattern Type:</strong> {detection.get('pattern_type', 'Unknown')}</p>
            <p><strong>Transactions:</strong> {detection.get('transaction_count', 0)}</p>
            <p><strong>Risk Level:</strong> {detection.get('risk_level', 'MEDIUM')}</p>
            </body></html>
            """
        elif fraud_type == 'rapid_back_forth':
            subject = f"[Fraud Alert] Rapid Transaction Pattern - {detection.get('account_phone', 'Unknown')}"
            body = f"""
            <html><body>
            <h2>⚡ Rapid Transaction Alert</h2>
            <p><strong>Account:</strong> {detection.get('account_phone', 'Unknown')}</p>
            <p><strong>Transactions:</strong> {detection.get('transaction_count', 0)} in {detection.get('time_window', 0)}min</p>
            <p><strong>Net Flow:</strong> KES {detection.get('net_flow', 0):,.2f}</p>
            </body></html>
            """
        else:
            subject = f"[Fraud Alert] Suspicious Activity Detected"
            body = f"""
            <html><body>
            <h2>⚠️ Suspicious Activity Alert</h2>
            <p><strong>Account:</strong> {detection.get('account_phone', 'Unknown')}</p>
            <p><strong>Details:</strong> {detection}</p>
            </body></html>
            """
        
        # Send email
        try:
            _send_email(
                subject=subject,
                html=body,
                recipient=user.email,
            )
            logger.info(f"Sent {fraud_type} alert to {user.email}")

            # Record alert in database
            self._record_fraud_alert_sync(detection, fraud_type, user)
            
        except Exception as e:
            logger.error(f"Failed to send fraud notification: {str(e)}")

    def _record_fraud_alert_sync(self, detection: Dict, fraud_type: str, user: User) -> bool:
        """Record fraud alert in database synchronously.

        Idempotent: skips insert if an alert with the same receipt_hash already
        exists for this user, preventing double-recording when the same detection
        is seen across multiple calls (e.g. historical + periodic overlap).

        Returns True if a new record was inserted, False if it was skipped.
        """
        try:
            receipt_nos = detection.get('receipt_nos', [])
            receipt_hash = hash(tuple(sorted(receipt_nos)))

            # Guard: do not record the same alert twice
            existing = FraudAlert.query.filter_by(
                user_id=user.id,
                receipt_hash=receipt_hash,
            ).first()
            if existing:
                logger.debug(
                    f"FraudAlert for receipt_hash={receipt_hash} already exists — skipping"
                )
                return False

            alert = FraudAlert(
                user_id=user.id,
                fraud_type=fraud_type,
                account_phone=detection.get('account_phone'),
                account_name=detection.get('account_name'),
                transaction_count=detection.get('transaction_count', 0),
                total_amount=Decimal(str(detection.get('total_amount', 0))),
                fraud_score=detection.get('fraud_score', 0),
                risk_level=detection.get('risk_level', 'MEDIUM'),
                receipt_nos=','.join(receipt_nos),
                transaction_ids=','.join(str(tid) for tid in detection.get('transaction_ids', [])),
                receipt_hash=receipt_hash,
                detection_details=detection,
            )

            db.session.add(alert)
            db.session.commit()
            logger.info(f"Recorded fraud alert for {fraud_type}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record fraud alert: {str(e)}")
            return False

    def _get_company_ids_for_user(self, user_id: int) -> List[int]:
        """Get company IDs associated with a user."""
        try:            
            companies = company_service.get_companies_by_user_id(user_id=user_id)
            
            return [company.id for company in companies]
                
        except Exception as e:
            logger.error(f"Error getting company IDs for user {user_id}: {str(e)}")
            return []
        
    def _should_limit_alerts(self, receipt_nos: List[str]) -> bool:
        """Check if alerts should be limited for this receipt group."""
        if not receipt_nos:
            return False
        
        # Sort and create hash
        receipt_hash = hash(tuple(sorted(receipt_nos)))
        
        # Check existing alerts for this group in last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        
        alert_count = FraudAlert.query.filter(
            FraudAlert.receipt_hash == receipt_hash,
            FraudAlert.created_at >= yesterday
        ).count()
        
        return alert_count >= 3  # Max 3 alerts per group per day
    
    async def _record_report_history(self, user: User, report_summary: Dict):
        """Record report history in database."""
        try:
            # Serialize report_summary to handle datetime objects
            serialized_report = self._serialize_for_json(report_summary)

            history = FraudReportHistory(
                user_id=user.id,
                analysis_period_days=30,
                total_transactions=report_summary.get('total_transactions_analyzed', 0),
                suspicious_patterns=report_summary.get('suspicious_patterns_found', 0),
                accounts_flagged=report_summary.get('accounts_flagged', 0),
                report_data=serialized_report
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                lambda: db.session.add(history) or db.session.commit()
            )

            logger.info(f"Recorded fraud report history for user {user.email}")

        except Exception as e:
            logger.error(f"Failed to record report history: {str(e)}")
    
    # PERIODIC AND DAILY REPORTS (called by Celery beat)
    
    def send_daily_fraud_report(self):
        """Send daily fraud report (called by Celery beat)."""
        try:
            logger.info("Starting daily fraud report generation")
            
            # Get all admin users
            admins = User.query.filter_by(is_admin=True).all()
            
            for admin in admins:
                self._send_daily_report_to_admin(admin)
                
            logger.info("Daily fraud reports sent")
            
        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}", exc_info=True)
    
    def _send_daily_report_to_admin(self, admin: User):
        """Send daily report to a single admin."""
        # Get today's date
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get fraud alerts from yesterday
        alerts = FraudAlert.query.filter(
            FraudAlert.created_at >= yesterday,
            FraudAlert.created_at < today
        ).all()
        
        # Get report history from yesterday
        reports = FraudReportHistory.query.filter(
            FraudReportHistory.created_at >= yesterday,
            FraudReportHistory.created_at < today
        ).all()
        
        # Generate report
        report_template = """
        <html><body>
        <h2>📊 Daily Fraud Detection Report</h2>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Generated For:</strong> {admin_email}</p>
        
        <h3>📈 Daily Statistics</h3>
        <ul>
        <li><strong>Total Fraud Alerts:</strong> {total_alerts}</li>
        <li><strong>High-Risk Alerts:</strong> {high_risk_alerts}</li>
        <li><strong>Reports Generated:</strong> {reports_generated}</li>
        <li><strong>Unique Accounts Flagged:</strong> {unique_accounts}</li>
        </ul>
        
        <h3>🎯 Top Fraud Types</h3>
        <ul>
        {fraud_types}
        </ul>
        
        <hr>
        <p style="color: #666; font-size: 12px;">
        Generated automatically by Fraud Detection System.
        </p>
        </body></html>
        """
        
        # Count fraud types
        fraud_type_counts = {}
        for alert in alerts:
            fraud_type = alert.fraud_type
            fraud_type_counts[fraud_type] = fraud_type_counts.get(fraud_type, 0) + 1
        
        fraud_types_html = ""
        for fraud_type, count in sorted(fraud_type_counts.items(), key=lambda x: x[1], reverse=True):
            fraud_types_html += f"<li><strong>{fraud_type}:</strong> {count}</li>"
        
        # Count unique accounts
        unique_accounts = len(set(alert.account_phone for alert in alerts if alert.account_phone))
        
        body = report_template.format(
            date=today.strftime('%Y-%m-%d'),
            admin_email=admin.email,
            total_alerts=len(alerts),
            high_risk_alerts=sum(1 for a in alerts if a.risk_level == 'HIGH'),
            reports_generated=len(reports),
            unique_accounts=unique_accounts,
            fraud_types=fraud_types_html
        )
        
        # Send email
        _send_email(
            subject=f"Daily Fraud Report - {today.strftime('%Y-%m-%d')}",
            html=body,
            recipient=admin.email,
        )
    
    def run_fraud_detection_for_user(self, user) -> Dict:
        """Run fraud detection for a specific user."""
        logger.info(f"Starting fraud detection for user: {user.email}")
        
        # Load user's active fraud detection config
        config_obj = ConfigService.get_active_config(user.id)
        config_dict = config_obj.to_dict() if config_obj else {}

        # Initialize fraud detection service with user's config
        fraud_service = FraudDetectionService(user=user, config=config_dict)

        # Step 1: Get historical report (first run)
        historical_report = self._generate_historical_report(user, fraud_service)
        
        # Step 2: Check recent transactions per shortcode
        recent_detections = self._check_recent_transactions(user,fraud_service)
        
        # Combine results
        result = {
            'historical_report': historical_report,
            'recent_detections': recent_detections,
            'detection_time': datetime.now(),
            'user_id': user.id,
            'user_email': user.email
        }
        
        return result
    
    def _generate_historical_report(self, user, fraud_service: FraudDetectionService) -> Dict:
        """Generate historical fraud analysis report."""
        logger.info("Generating historical fraud analysis report")
        
        # Get all shortcodes
        shortcodes = self.get_all_shortcodes_in_txn_tbl(user=user)
        all_transactions = []
        
        # Get historical transactions for each shortcode
        for shortcode in shortcodes:
            transactions = self.get_historical_transactions_for_shortcode(
                shortcode, 
                days=fraud_service.config['analysis_period_days']
            )
            all_transactions.extend(transactions)
        
        # Run detection on historical data
        if all_transactions:
            historical_result = fraud_service.run_detection(all_transactions)

            # Send historical report with transactions and detections
            fraud_service.send_historical_report(
                historical_result['summary'],
                transactions=all_transactions,
                detections=historical_result.get('detections', [])
            )

            return historical_result
        else:
            logger.info("No historical transactions found for analysis")
            return {'summary': {}, 'detections': [], 'account_summary': {}}
    
    def _check_recent_transactions(self, user:User, fraud_service: FraudDetectionService) -> List[Dict]:
        """Check recent transactions for fraud patterns."""
        logger.info("Checking recent transactions for fraud patterns")
        
        shortcodes = self.get_all_shortcodes_in_txn_tbl(user=user)
        all_detections = []
        
        for shortcode in shortcodes:
            # Get recent transactions for this shortcode
            transactions = self.get_recent_transactions_for_shortcode(
                shortcode,
                limit=fraud_service.config['recent_transactions_limit']
            )
            
            if transactions:
                # Run detection
                result = fraud_service.run_detection(transactions)
                
                # Send notifications for high-risk detections
                for detection in result.get('detections', []):
                    if detection.get('risk_level') == 'HIGH':
                        fraud_service.send_fraud_notification(
                            detection, 
                            detection.get('fraud_type')
                        )
                
                all_detections.extend(result.get('detections', []))
        
        return all_detections
        
    def _get_basic_stats_raw(self, cursor, where_clause: str, params: list, transaction_type: str) -> Dict:
        """Get basic transaction statistics using raw SQL"""
        if transaction_type == 'float':
            query = f"""
                SELECT 
                    COUNT(id) as total_transactions,
                    COALESCE(SUM(paid_in), 0) as total_deposits,
                    COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                    COALESCE(AVG(paid_in), 0) as avg_deposit_amount,
                    COALESCE(AVG(withdrawn), 0) as avg_withdrawal_amount,
                    COALESCE(MAX(paid_in), 0) as max_deposit,
                    COALESCE(MAX(withdrawn), 0) as max_withdrawal,
                    COUNT(CASE WHEN paid_in > 0 THEN 1 END) as deposit_count,
                    COUNT(CASE WHEN withdrawn > 0 THEN 1 END) as withdrawal_count
                FROM transactions 
                WHERE {where_clause}
            """
            cursor.execute(query, params)
            stats = cursor.fetchone()
            
            total_deposits = Decimal(stats['total_deposits'] or '0.00')
            total_withdrawals = Decimal(stats['total_withdrawals'] or '0.00')
            net_flow = total_deposits - total_withdrawals
            
            return {
                "total_transactions": stats['total_transactions'] or 0,
                "total_deposits": str(total_deposits),
                "total_withdrawals": str(total_withdrawals),
                "net_flow": str(net_flow),
                "avg_deposit_amount": str(Decimal(stats['avg_deposit_amount'] or '0.00')),
                "avg_withdrawal_amount": str(Decimal(stats['avg_withdrawal_amount'] or '0.00')),
                "max_deposit": str(Decimal(stats['max_deposit'] or '0.00')),
                "max_withdrawal": str(Decimal(stats['max_withdrawal'] or '0.00')),
                "deposit_count": stats['deposit_count'] or 0,
                "withdrawal_count": stats['withdrawal_count'] or 0,
                "deposit_to_withdrawal_ratio": float(total_deposits / total_withdrawals) if total_withdrawals > 0 else 0
            }
        else:
            # Commission statistics
            query = f"""
                SELECT 
                    COUNT(id) as total_commissions,
                    COALESCE(SUM(commission_amount), 0) as total_commission_amount,
                    COALESCE(AVG(commission_amount), 0) as avg_commission,
                    COALESCE(MAX(commission_amount), 0) as max_commission,
                    COALESCE(MIN(commission_amount), 0) as min_commission,
                    COALESCE(SUM(CASE WHEN details ILIKE '%%Deposit%%' THEN commission_amount END), 0) as deposit_commissions,
                    COALESCE(SUM(CASE WHEN details ILIKE '%%Withdrawal%%' THEN commission_amount END), 0) as withdrawal_commissions
                FROM transactions 
                WHERE {where_clause}
            """
            cursor.execute(query, params)
            stats = cursor.fetchone()
            
            total_commission = Decimal(stats['total_commission_amount'] or '0.00')
            deposit_commissions = Decimal(stats['deposit_commissions'] or '0.00')
            withdrawal_commissions = Decimal(stats['withdrawal_commissions'] or '0.00')
            
            avg_commission_rate = self._get_avg_commission_rate_raw(cursor, where_clause, params)
            
            return {
                "total_commissions": stats['total_commissions'] or 0,
                "total_commission_amount": str(total_commission),
                "avg_commission": str(Decimal(stats['avg_commission'] or '0.00')),
                "max_commission": str(Decimal(stats['max_commission'] or '0.00')),
                "min_commission": str(Decimal(stats['min_commission'] or '0.00')),
                "deposit_commissions": str(deposit_commissions),
                "withdrawal_commissions": str(withdrawal_commissions),
                "deposit_commission_ratio": float(deposit_commissions / total_commission) if total_commission > 0 else 0,
                "avg_commission_rate": str(avg_commission_rate)
            }

    def _get_transaction_by_id(self, transaction_id: int) -> Transaction:
        """Get a transaction by ID"""
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction with ID {transaction_id} not found")
            return transaction
        except Exception as e:
            logger.error(f"Error fetching transaction by ID {transaction_id}: {str(e)}", exc_info=True)
            raise
        
    def _get_trend_stats_raw(self, cursor, where_clause: str, params: list, filters: Dict, transaction_type: str) -> Dict:
        """Get trend statistics grouped by time period using raw SQL"""
        group_by = filters.get('group_by', 'day')
        
        if group_by == 'day':
            date_expr = "DATE(completion_time)"
            date_format = '%Y-%m-%d'
            display_format = '%Y-%m-%d'
        elif group_by == 'week':
            date_expr = "DATE_TRUNC('week', completion_time)"
            date_format = 'YYYY-"W"IW'
            display_format = 'Week %U, %Y'
        elif group_by == 'month':
            date_expr = "DATE_TRUNC('month', completion_time)"
            date_format = 'YYYY-MM'
            display_format = '%B %Y'
        elif group_by == 'year':
            date_expr = "DATE_TRUNC('year', completion_time)"
            date_format = 'YYYY'
            display_format = '%Y'
        else:
            date_expr = "DATE(completion_time)"
            date_format = '%Y-%m-%d'
            display_format = '%Y-%m-%d'
        
        if transaction_type == 'float':
            query = f"""
                SELECT 
                    {date_expr} as period,
                    COUNT(id) as transaction_count,
                    COALESCE(SUM(paid_in), 0) as total_deposits,
                    COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                    COALESCE(AVG(paid_in), 0) as avg_deposit,
                    COALESCE(AVG(withdrawn), 0) as avg_withdrawal
                FROM transactions 
                WHERE {where_clause}
                GROUP BY {date_expr}
                ORDER BY {date_expr}
            """
        else:
            query = f"""
                SELECT 
                    {date_expr} as period,
                    COUNT(id) as commission_count,
                    COALESCE(SUM(commission_amount), 0) as total_commission,
                    COALESCE(AVG(commission_amount), 0) as avg_commission,
                    COUNT(CASE WHEN details ILIKE '%%Deposit%%' THEN 1 END) as deposit_commission_count,
                    COUNT(CASE WHEN details ILIKE '%%Withdrawal%%' THEN 1 END) as withdrawal_commission_count
                FROM transactions 
                WHERE {where_clause}
                GROUP BY {date_expr}
                ORDER BY {date_expr}
            """
        
        cursor.execute(query, params)
        trend_data = cursor.fetchall()
        
        trends = []
        for data in trend_data:
            period_date = data['period']
            if isinstance(period_date, str):
                period_date = datetime.strptime(str(period_date), '%Y-%m-%d')
            
            if transaction_type == 'float':
                trend = {
                    "period": period_date.strftime(display_format),
                    "date": period_date.strftime('%Y-%m-%d'),
                    "transaction_count": data['transaction_count'],
                    "total_deposits": str(Decimal(data['total_deposits'] or '0.00')),
                    "total_withdrawals": str(Decimal(data['total_withdrawals'] or '0.00')),
                    "net_flow": str(Decimal(data['total_deposits'] or '0.00') - Decimal(data['total_withdrawals'] or '0.00')),
                    "avg_deposit": str(Decimal(data['avg_deposit'] or '0.00')),
                    "avg_withdrawal": str(Decimal(data['avg_withdrawal'] or '0.00'))
                }
            else:
                trend = {
                    "period": period_date.strftime(display_format),
                    "date": period_date.strftime('%Y-%m-%d'),
                    "commission_count": data['commission_count'],
                    "total_commission": str(Decimal(data['total_commission'] or '0.00')),
                    "avg_commission": str(Decimal(data['avg_commission'] or '0.00')),
                    "deposit_commission_count": data['deposit_commission_count'],
                    "withdrawal_commission_count": data['withdrawal_commission_count'],
                    "deposit_commission_ratio": data['deposit_commission_count'] / data['commission_count'] if data['commission_count'] > 0 else 0
                }
            trends.append(trend)
        
        # Calculate growth rates
        growth_rates = self._calculate_growth_rates(trends, transaction_type)
        
        return {
            "group_by": group_by,
            "trends": trends,
            "growth_rates": growth_rates
        }

    def _get_last_scraped_per_till(self, cursor: Generator, transaction_type: str = None) -> Dict[str, int]:
        """
        Get number of days since last scrape for each till (Kenya time).

        Args:
            cursor: Database cursor
            transaction_type: Optional filter - 'float', 'commission', or None for all types

        Returns:
            Dict with business_shortcode as key and [days_since_last_scrape, latest_receipt_no] as value
            If transaction_type is None, returns nested dict: {shortcode: {'float': [...], 'commission': [...]}}
        """
        if transaction_type:
            # Get last scraped for specific transaction type
            query = """
                SELECT business_shortcode,
                       MAX(receipt_no) AS latest_receipt_no,
                       MAX(updated_at) AS latest_updated_at
                FROM transactions
                WHERE transaction_type = %s
                GROUP BY business_shortcode;
            """
            cursor.execute(query, (transaction_type,))
            results = cursor.fetchall()

            now = datetime.now(self.kenya_tz)

            return {
                row['business_shortcode']: [
                    (now - row['latest_updated_at'].replace(tzinfo=self.kenya_tz)).days,
                    row['latest_receipt_no']
                ]
                for row in results
            }
        else:
            # Get last scraped for both transaction types separately
            query = """
                SELECT business_shortcode,
                       transaction_type,
                       MAX(receipt_no) AS latest_receipt_no,
                       MAX(updated_at) AS latest_updated_at
                FROM transactions
                GROUP BY business_shortcode, transaction_type;
            """
            cursor.execute(query)
            results = cursor.fetchall()

            now = datetime.now(self.kenya_tz)

            # Build nested dictionary: {shortcode: {'float': [...], 'commission': [...]}}
            shortcode_data = {}
            for row in results:
                shortcode = row['business_shortcode']
                txn_type = row['transaction_type'] or 'float'

                if shortcode not in shortcode_data:
                    shortcode_data[shortcode] = {}

                days_diff = (now - row['latest_updated_at'].replace(tzinfo=self.kenya_tz)).days
                shortcode_data[shortcode][txn_type] = [days_diff, row['latest_receipt_no']]

            return shortcode_data
        
    def _get_all_short_codes_in_txn_tbl(self, cursor:Generator) -> List[int]:
        """Get all shortcodes that have been registered in the transactions table"""
        query = """
            select distinct(business_shortcode)
            from transactions;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        return results
    
    def _get_category_stats_raw(self, cursor, where_clause: str, params: list, transaction_type: str) -> Dict:
        """Get statistics by category using raw SQL"""
        if transaction_type == 'float':
            query = f"""
                SELECT 
                    reason_type as category,
                    COUNT(id) as count,
                    COALESCE(SUM(paid_in), 0) as total_deposits,
                    COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                    COALESCE(AVG(paid_in), 0) as avg_deposit,
                    COALESCE(AVG(withdrawn), 0) as avg_withdrawal,
                    COALESCE(MAX(paid_in), 0) as max_deposit,
                    COALESCE(MAX(withdrawn), 0) as max_withdrawal
                FROM transactions 
                WHERE {where_clause}
                GROUP BY reason_type
                ORDER BY COUNT(id) DESC
            """
        else:
            query = f"""
                SELECT 
                    details as category,
                    COUNT(id) as count,
                    COALESCE(SUM(commission_amount), 0) as total_commission,
                    COALESCE(AVG(commission_amount), 0) as avg_commission,
                    COALESCE(MAX(commission_amount), 0) as max_commission,
                    COALESCE(MIN(commission_amount), 0) as min_commission,
                    COALESCE(AVG(commission_rate), 0) as avg_rate
                FROM transactions 
                WHERE {where_clause}
                GROUP BY details
                ORDER BY COUNT(id) DESC
            """
        
        cursor.execute(query, params)
        categories_data = cursor.fetchall()
        
        categories = []
        total_count = 0
        total_amount = Decimal('0.00')
        
        for data in categories_data:
            if transaction_type == 'float':
                category = {
                    "category": data['category'],
                    "count": data['count'],
                    "total_deposits": str(Decimal(data['total_deposits'] or '0.00')),
                    "total_withdrawals": str(Decimal(data['total_withdrawals'] or '0.00')),
                    "avg_deposit": str(Decimal(data['avg_deposit'] or '0.00')),
                    "avg_withdrawal": str(Decimal(data['avg_withdrawal'] or '0.00')),
                    "max_deposit": str(Decimal(data['max_deposit'] or '0.00')),
                    "max_withdrawal": str(Decimal(data['max_withdrawal'] or '0.00')),
                    "net_flow": str(Decimal(data['total_deposits'] or '0.00') - Decimal(data['total_withdrawals'] or '0.00'))
                }
                total_amount += Decimal(data['total_deposits'] or '0.00') + Decimal(data['total_withdrawals'] or '0.00')
            else:
                category = {
                    "category": data['category'],
                    "count": data['count'],
                    "total_commission": str(Decimal(data['total_commission'] or '0.00')),
                    "avg_commission": str(Decimal(data['avg_commission'] or '0.00')),
                    "max_commission": str(Decimal(data['max_commission'] or '0.00')),
                    "min_commission": str(Decimal(data['min_commission'] or '0.00')),
                    "avg_rate": str(Decimal(data['avg_rate'] or '0.00'))
                }
                total_amount += Decimal(data['total_commission'] or '0.00')
            
            categories.append(category)
            total_count += data['count']
        
        # Calculate percentages
        for category in categories:
            category['percentage'] = (category['count'] / total_count * 100) if total_count > 0 else 0
            if transaction_type == 'float':
                cat_total = Decimal(category['total_deposits']) + Decimal(category['total_withdrawals'])
                category['amount_percentage'] = (cat_total / total_amount * 100) if total_amount > 0 else 0
            else:
                cat_total = Decimal(category['total_commission'])
                category['amount_percentage'] = (cat_total / total_amount * 100) if total_amount > 0 else 0
        
        return {
            "categories": categories,
            "total_categories": len(categories),
            "total_count": total_count,
            "total_amount": str(total_amount)
        }

    def _get_top_stats_raw(self, cursor, where_clause: str, params: list, transaction_type: str, filters: Dict) -> Dict:
        """Get top performing statistics using raw SQL"""
        top_stats = {}
        
        # Top transactions by amount
        if transaction_type == 'float':
            # Top deposits
            top_deposits_query = f"""
                SELECT receipt_no, paid_in, completion_time, details, other_party_info
                FROM transactions 
                WHERE {where_clause} AND paid_in > 0
                ORDER BY paid_in DESC
                LIMIT 10
            """
            cursor.execute(top_deposits_query, params)
            top_deposits = cursor.fetchall()
            
            # Top withdrawals
            top_withdrawals_query = f"""
                SELECT receipt_no, withdrawn, completion_time, details, other_party_info
                FROM transactions 
                WHERE {where_clause} AND withdrawn > 0
                ORDER BY withdrawn DESC
                LIMIT 10
            """
            cursor.execute(top_withdrawals_query, params)
            top_withdrawals = cursor.fetchall()
            
            top_stats["top_deposits"] = [
                {
                    "receipt_no": trans['receipt_no'],
                    "amount": str(Decimal(trans['paid_in'])),
                    "date": trans['completion_time'].strftime('%Y-%m-%d %H:%M'),
                    "details": trans['details'],
                    "other_party": trans['other_party_info']
                } for trans in top_deposits
            ]
            
            top_stats["top_withdrawals"] = [
                {
                    "receipt_no": trans['receipt_no'],
                    "amount": str(Decimal(trans['withdrawn'])),
                    "date": trans['completion_time'].strftime('%Y-%m-%d %H:%M'),
                    "details": trans['details'],
                    "other_party": trans['other_party_info']
                } for trans in top_withdrawals
            ]
        else:
            # Top commissions
            top_commissions_query = f"""
                SELECT receipt_no, commission_amount, completion_time, details, 
                    commission_rate, linked_transaction_id
                FROM transactions 
                WHERE {where_clause}
                ORDER BY commission_amount DESC
                LIMIT 10
            """
            cursor.execute(top_commissions_query, params)
            top_commissions = cursor.fetchall()
            
            top_stats["top_commissions"] = [
                {
                    "receipt_no": trans['receipt_no'],
                    "amount": str(Decimal(trans['commission_amount'])),
                    "date": trans['completion_time'].strftime('%Y-%m-%d %H:%M'),
                    "details": trans['details'],
                    "rate": str(Decimal(trans['commission_rate'] or '0.25')),
                    "original_receipt": trans['linked_transaction_id']
                } for trans in top_commissions
            ]
        
        # Top agents by transaction count
        if 'agent_id' not in filters:
            top_agents_query = f"""
                SELECT 
                    agent_id,
                    COUNT(id) as transaction_count,
                    COALESCE(SUM(paid_in), 0) as total_deposits,
                    COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                    COALESCE(SUM(commission_amount), 0) as total_commission
                FROM transactions 
                WHERE {where_clause} AND agent_id IS NOT NULL
                GROUP BY agent_id
                ORDER BY COUNT(id) DESC
                LIMIT 10
            """
            cursor.execute(top_agents_query, params)
            top_agents = cursor.fetchall()
            
            top_stats["top_agents"] = [
                {
                    "agent_id": data['agent_id'],
                    "transaction_count": data['transaction_count'],
                    "total_deposits": str(Decimal(data['total_deposits'] or '0.00')),
                    "total_withdrawals": str(Decimal(data['total_withdrawals'] or '0.00')),
                    "total_commission": str(Decimal(data['total_commission'] or '0.00'))
                } for data in top_agents
            ]
        
        # Top companies by transaction volume
        if 'company_id' not in filters:
            top_companies_query = f"""
                SELECT 
                    company_id,
                    COUNT(id) as transaction_count,
                    COALESCE(SUM(paid_in), 0) as total_deposits,
                    COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                    COALESCE(SUM(commission_amount), 0) as total_commission
                FROM transactions 
                WHERE {where_clause} AND company_id IS NOT NULL
                GROUP BY company_id
                ORDER BY COUNT(id) DESC
                LIMIT 10
            """
            cursor.execute(top_companies_query, params)
            top_companies = cursor.fetchall()
            
            top_stats["top_companies"] = []
            for data in top_companies:
                # Need to get company name - assuming we have a get_company function
                print(f"Fetching company info for ID: {data['company_id']}")
                company = company_service.get_company_by_id(data['company_id'])
                top_stats["top_companies"].append({
                    "company_id": data['company_id'],
                    "company_name": company.company_name if company else "Unknown",
                    "shortcode": company.shortcode if company else None,
                    "transaction_count": data['transaction_count'],
                    "total_deposits": str(Decimal(data['total_deposits'] or '0.00')),
                    "total_withdrawals": str(Decimal(data['total_withdrawals'] or '0.00')),
                    "total_commission": str(Decimal(data['total_commission'] or '0.00'))
                })
        
        return top_stats

    def _get_performance_metrics_raw(self, cursor, where_clause: str, params: list, 
                                    start_dt: datetime, end_dt: datetime, transaction_type: str) -> Dict:
        """Get performance metrics and KPIs using raw SQL"""
        days_in_period = (end_dt - start_dt).days + 1
        
        # Total statistics
        total_query = f"""
            SELECT 
                COUNT(id) as total_count,
                COALESCE(SUM(paid_in), 0) as total_deposits,
                COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                COALESCE(SUM(commission_amount), 0) as total_commission
            FROM transactions 
            WHERE {where_clause}
        """
        cursor.execute(total_query, params)
        total_stats = cursor.fetchone()
        
        total_count = total_stats['total_count'] or 0
        total_deposits = Decimal(total_stats['total_deposits'] or '0.00')
        total_withdrawals = Decimal(total_stats['total_withdrawals'] or '0.00')
        total_commission = Decimal(total_stats['total_commission'] or '0.00')
        
        # Success rate (completed transactions)
        success_query = f"""
            SELECT COUNT(id) as success_count
            FROM transactions 
            WHERE {where_clause} AND transaction_status = 'Completed'
        """
        cursor.execute(success_query, params)
        success_stats = cursor.fetchone()
        
        success_count = success_stats['success_count'] or 0
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        # Peak hours analysis
        peak_hours_query = f"""
            SELECT 
                EXTRACT(HOUR FROM completion_time) as hour,
                COUNT(id) as transaction_count,
                COALESCE(SUM(paid_in + withdrawn + commission_amount), 0) as total_amount
            FROM transactions 
            WHERE {where_clause}
            GROUP BY EXTRACT(HOUR FROM completion_time)
            ORDER BY COUNT(id) DESC
            LIMIT 5
        """
        cursor.execute(peak_hours_query, params)
        peak_hours = cursor.fetchall()
        
        peak_hours_list = [
            {
                "hour": f"{int(data['hour']):02d}:00",
                "transaction_count": data['transaction_count'],
                "total_amount": str(Decimal(data['total_amount'] or '0.00'))
            } for data in peak_hours
        ]
        
        # Busiest day
        busiest_day = self._get_busiest_day_raw(cursor, where_clause, params)
        
        metrics = {
            "daily_average_transactions": total_count / days_in_period if days_in_period > 0 else 0,
            "daily_average_amount": str((total_deposits + total_withdrawals + total_commission) / Decimal(str(days_in_period))) if days_in_period > 0 else "0.00",
            "success_rate": success_rate,
            "peak_hours": peak_hours_list,
            "busiest_day": busiest_day,
            "transaction_velocity": total_count / days_in_period if days_in_period > 0 else 0
        }
        
        if transaction_type == 'float':
            deposit_success_rate = self._get_deposit_success_rate_raw(cursor, where_clause, params)
            withdrawal_success_rate = self._get_withdrawal_success_rate_raw(cursor, where_clause, params)
            
            metrics.update({
                "deposit_success_rate": deposit_success_rate,
                "withdrawal_success_rate": withdrawal_success_rate,
                "average_transaction_value": str((total_deposits + total_withdrawals) / Decimal(str(total_count))) if total_count > 0 else "0.00"
            })
        else:
            commission_efficiency = self._get_commission_efficiency_raw(cursor, where_clause, params)
            avg_commission_rate = self._get_avg_commission_rate_raw(cursor, where_clause, params)
            
            metrics.update({
                "commission_efficiency": commission_efficiency,
                "average_commission_rate": str(avg_commission_rate)
            })
        
        return metrics

    def _get_comparison_stats_raw(self, filters: Dict, transaction_type: str) -> Dict:
        """Get comparison with previous period using raw SQL"""
        try:
            # Get current period dates
            end_date = filters.get('end_date')
            start_date = filters.get('start_date')
            
            if not start_date or not end_date:
                # Use default 30-day period
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=30)
                prev_end_dt = start_dt - timedelta(days=1)
                prev_start_dt = prev_end_dt - timedelta(days=30)
            else:
                end_dt = self._parse_date(end_date)
                start_dt = self._parse_date(start_date)
                period_days = (end_dt - start_dt).days + 1
                prev_end_dt = start_dt - timedelta(days=1)
                prev_start_dt = prev_end_dt - timedelta(days=period_days - 1)
            
            # Get current period stats using raw SQL
            current_stats = self._get_comparison_data_raw(filters, start_dt, end_dt, transaction_type)
            
            # Get previous period stats
            prev_stats = self._get_comparison_data_raw(filters, prev_start_dt, prev_end_dt, transaction_type)
            
            if current_stats and prev_stats:
                # Calculate growth/decline percentages
                comparison = {}
                
                if transaction_type == 'float':
                    fields_to_compare = [
                        'total_transactions', 'total_deposits', 'total_withdrawals',
                        'net_flow', 'deposit_count', 'withdrawal_count'
                    ]
                else:
                    fields_to_compare = [
                        'total_commissions', 'total_commission_amount',
                        'deposit_commissions', 'withdrawal_commissions'
                    ]
                
                for field in fields_to_compare:
                    if field in current_stats and field in prev_stats:
                        current_val = Decimal(current_stats[field]) if isinstance(current_stats[field], str) else current_stats[field]
                        prev_val = Decimal(prev_stats[field]) if isinstance(prev_stats[field], str) else prev_stats[field]
                        
                        if prev_val != 0:
                            change_percent = ((current_val - prev_val) / prev_val) * 100
                        else:
                            change_percent = 100 if current_val > 0 else 0
                        
                        comparison[field] = {
                            "current": current_stats[field],
                            "previous": prev_stats[field],
                            "change": float(change_percent),
                            "trend": "up" if change_percent > 0 else "down" if change_percent < 0 else "stable"
                        }
                
                return {
                    "current_period": {
                        "start_date": start_dt.strftime('%Y-%m-%d'),
                        "end_date": end_dt.strftime('%Y-%m-%d'),
                        "days": (end_dt - start_dt).days + 1
                    },
                    "previous_period": {
                        "start_date": prev_start_dt.strftime('%Y-%m-%d'),
                        "end_date": prev_end_dt.strftime('%Y-%m-%d'),
                        "days": (prev_end_dt - prev_start_dt).days + 1
                    },
                    "comparison": comparison
                }
            
            return {"error": "Could not calculate comparison"}
            
        except Exception as e:
            logger.error(f"Error calculating comparison stats: {str(e)}")
            return {"error": str(e)}

    def _get_comparison_data_raw(self, filters: Dict, start_dt: datetime, end_dt: datetime, transaction_type: str) -> Dict:
        """Helper to get comparison data for a specific period"""
        # Build conditions similar to main function
        conditions = ["transaction_type = %s"]
        params = [transaction_type]
        
        for key in ['agent_id', 'company_id', 'reason_type', 'transaction_status']:
            if key in filters:
                conditions.append(f"{key} = %s")
                params.append(filters[key])
        
        # Add date conditions
        conditions.append("completion_time >= %s")
        params.append(start_dt)
        conditions.append("completion_time <= %s")
        end_dt_adjusted = end_dt.replace(hour=23, minute=59, second=59)
        params.append(end_dt_adjusted)
        
        where_clause = " AND ".join(conditions)

        with db_pool.get_cursor() as cursor:
            if transaction_type == 'float':
                query = f"""
                    SELECT 
                        COUNT(id) as total_transactions,
                        COALESCE(SUM(paid_in), 0) as total_deposits,
                        COALESCE(SUM(withdrawn), 0) as total_withdrawals,
                        COALESCE(SUM(paid_in) - SUM(withdrawn), 0) as net_flow,
                        COUNT(CASE WHEN paid_in > 0 THEN 1 END) as deposit_count,
                        COUNT(CASE WHEN withdrawn > 0 THEN 1 END) as withdrawal_count
                    FROM transactions 
                    WHERE {where_clause}
                """
            else:
                query = f"""
                    SELECT 
                        COUNT(id) as total_commissions,
                        COALESCE(SUM(commission_amount), 0) as total_commission_amount,
                        COALESCE(SUM(CASE WHEN details ILIKE '%%Deposit%%' THEN commission_amount END), 0) as deposit_commissions,
                        COALESCE(SUM(CASE WHEN details ILIKE '%%Withdrawal%%' THEN commission_amount END), 0) as withdrawal_commissions
                    FROM transactions 
                    WHERE {where_clause}
                """
            
            cursor.execute(query, params)
            stats = cursor.fetchone()
            
            if stats:
                if transaction_type == 'float':
                    return {
                        "total_transactions": stats['total_transactions'],
                        "total_deposits": str(Decimal(stats['total_deposits'] or '0.00')),
                        "total_withdrawals": str(Decimal(stats['total_withdrawals'] or '0.00')),
                        "net_flow": str(Decimal(stats['net_flow'] or '0.00')),
                        "deposit_count": stats['deposit_count'],
                        "withdrawal_count": stats['withdrawal_count']
                    }
                else:
                    return {
                        "total_commissions": stats['total_commissions'],
                        "total_commission_amount": str(Decimal(stats['total_commission_amount'] or '0.00')),
                        "deposit_commissions": str(Decimal(stats['deposit_commissions'] or '0.00')),
                        "withdrawal_commissions": str(Decimal(stats['withdrawal_commissions'] or '0.00'))
                    }
            
            return {}

    def _get_avg_commission_rate_raw(self, cursor, where_clause: str, params: list) -> Decimal:
        """Get average commission rate using raw SQL"""
        query = f"""
            SELECT COALESCE(AVG(commission_rate), 0.25) as avg_rate
            FROM transactions 
            WHERE {where_clause} AND commission_rate > 0
        """
        cursor.execute(query, params)
        result = cursor.fetchone()
        return Decimal(result['avg_rate'] or '0.00')

    def _get_deposit_success_rate_raw(self, cursor, where_clause: str, params: list) -> float:
        """Get deposit success rate using raw SQL"""
        total_deposits_query = f"""
            SELECT COUNT(id) as count
            FROM transactions 
            WHERE {where_clause} AND paid_in > 0
        """
        cursor.execute(total_deposits_query, params)
        total_deposits = cursor.fetchone()['count'] or 0
        
        successful_deposits_query = f"""
            SELECT COUNT(id) as count
            FROM transactions 
            WHERE {where_clause} AND paid_in > 0 AND transaction_status = 'Completed'
        """
        cursor.execute(successful_deposits_query, params)
        successful_deposits = cursor.fetchone()['count'] or 0
        
        return (successful_deposits / total_deposits * 100) if total_deposits > 0 else 0

    def _get_withdrawal_success_rate_raw(self, cursor, where_clause: str, params: list) -> float:
        """Get withdrawal success rate using raw SQL"""
        total_withdrawals_query = f"""
            SELECT COUNT(id) as count
            FROM transactions 
            WHERE {where_clause} AND withdrawn > 0
        """
        cursor.execute(total_withdrawals_query, params)
        total_withdrawals = cursor.fetchone()['count'] or 0
        
        successful_withdrawals_query = f"""
            SELECT COUNT(id) as count
            FROM transactions 
            WHERE {where_clause} AND withdrawn > 0 AND transaction_status = 'Completed'
        """
        cursor.execute(successful_withdrawals_query, params)
        successful_withdrawals = cursor.fetchone()['count'] or 0
        
        return (successful_withdrawals / total_withdrawals * 100) if total_withdrawals > 0 else 0

    def _get_commission_efficiency_raw(self, cursor, where_clause: str, params: list) -> float:
        """Get commission efficiency metric using raw SQL"""
        total_commissions_query = f"""
            SELECT COUNT(id) as count
            FROM transactions 
            WHERE {where_clause}
        """
        cursor.execute(total_commissions_query, params)
        total_commissions = cursor.fetchone()['count'] or 0
        
        high_value_commissions_query = f"""
            SELECT COUNT(id) as count
            FROM transactions 
            WHERE {where_clause} AND commission_amount >= 100
        """
        cursor.execute(high_value_commissions_query, params)
        high_value_commissions = cursor.fetchone()['count'] or 0
        
        return (high_value_commissions / total_commissions * 100) if total_commissions > 0 else 0

    def _get_busiest_day_raw(self, cursor, where_clause: str, params: list) -> Dict:
        """Get the busiest day of the week using raw SQL"""
        query = f"""
            SELECT 
                EXTRACT(DOW FROM completion_time) as day_of_week,
                COUNT(id) as transaction_count
            FROM transactions 
            WHERE {where_clause}
            GROUP BY EXTRACT(DOW FROM completion_time)
            ORDER BY COUNT(id) DESC
            LIMIT 1
        """
        cursor.execute(query, params)
        busiest_day = cursor.fetchone()
        
        if busiest_day:
            days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            return {
                "day": days[int(busiest_day['day_of_week'])],
                "transaction_count": busiest_day['transaction_count']
            }
        
        return {"day": "Unknown", "transaction_count": 0}
    
    def _calculate_growth_rates(self, trends: List[Dict], transaction_type: str) -> Dict:
        """Calculate comprehensive growth rates from trend data"""
        if len(trends) < 2:
            return {
                "overall_growth": {
                    "rate": 0,
                    "trend": "stable",
                    "message": "Insufficient data for growth calculation"
                },
                "period_growth": {},
                "moving_averages": {},
                "volatility": 0
            }
        
        # 1. Overall growth (first vs last period)
        latest = trends[-1]
        first = trends[0]
        
        if transaction_type == 'float':
            latest_total = Decimal(latest.get('total_deposits', '0.00')) + Decimal(latest.get('total_withdrawals', '0.00'))
            first_total = Decimal(first.get('total_deposits', '0.00')) + Decimal(first.get('total_withdrawals', '0.00'))
            latest_net_flow = Decimal(latest.get('net_flow', '0.00'))
            first_net_flow = Decimal(first.get('net_flow', '0.00'))
        else:
            latest_total = Decimal(latest.get('total_commission', '0.00'))
            first_total = Decimal(first.get('total_commission', '0.00'))
            latest_net_flow = latest_total  # For commissions, net flow is just total commission
            first_net_flow = first_total
        
        # Calculate overall growth
        if first_total > 0:
            overall_growth_rate = ((latest_total - first_total) / first_total) * 100
        else:
            overall_growth_rate = 100 if latest_total > 0 else 0
        
        # 2. Recent growth (last vs previous period)
        previous = trends[-2]
        
        if transaction_type == 'float':
            previous_total = Decimal(previous.get('total_deposits', '0.00')) + Decimal(previous.get('total_withdrawals', '0.00'))
            previous_net_flow = Decimal(previous.get('net_flow', '0.00'))
        else:
            previous_total = Decimal(previous.get('total_commission', '0.00'))
            previous_net_flow = previous_total
        
        if previous_total > 0:
            recent_growth_rate = ((latest_total - previous_total) / previous_total) * 100
        else:
            recent_growth_rate = 100 if latest_total > 0 else 0
        
        # 3. Calculate moving averages for smoother trends
        moving_averages = self._calculate_moving_averages(trends, transaction_type)
        
        # 4. Calculate volatility (standard deviation of growth rates)
        volatility = self._calculate_volatility(trends, transaction_type)
        
        # 5. Calculate average growth per period
        periods = len(trends) - 1
        if periods > 0:
            avg_growth_per_period = overall_growth_rate / periods
        else:
            avg_growth_per_period = 0
        
        # 6. Determine growth momentum (accelerating, decelerating, stable)
        growth_momentum = self._determine_growth_momentum(trends, transaction_type)
        
        # 7. Calculate compound annual growth rate (CAGR) if we have enough data
        cagr = self._calculate_cagr(trends, transaction_type)
        
        # 8. Calculate period-over-period growth for all periods
        period_growth = []
        for i in range(1, len(trends)):
            current = trends[i]
            prev = trends[i-1]
            
            if transaction_type == 'float':
                current_total = Decimal(current.get('total_deposits', '0.00')) + Decimal(current.get('total_withdrawals', '0.00'))
                prev_total = Decimal(prev.get('total_deposits', '0.00')) + Decimal(prev.get('total_withdrawals', '0.00'))
                current_net = Decimal(current.get('net_flow', '0.00'))
                prev_net = Decimal(prev.get('net_flow', '0.00'))
            else:
                current_total = Decimal(current.get('total_commission', '0.00'))
                prev_total = Decimal(prev.get('total_commission', '0.00'))
                current_net = current_total
                prev_net = prev_total
            
            if prev_total > 0:
                growth_pct = ((current_total - prev_total) / prev_total) * 100
            else:
                growth_pct = 100 if current_total > 0 else 0
            
            if prev_net != 0:
                net_growth_pct = ((current_net - prev_net) / abs(prev_net)) * 100
            else:
                net_growth_pct = 100 if current_net > 0 else -100 if current_net < 0 else 0
            
            period_growth.append({
                "period": current.get('period'),
                "from_period": prev.get('period'),
                "growth_rate": float(growth_pct),
                "net_flow_growth": float(net_growth_pct),
                "total_amount": str(current_total),
                "net_flow": str(current_net),
                "trend": "up" if growth_pct > 0 else "down" if growth_pct < 0 else "stable"
            })
        
        # 9. Identify best and worst performing periods
        if period_growth:
            best_period = max(period_growth, key=lambda x: x['growth_rate'])
            worst_period = min(period_growth, key=lambda x: x['growth_rate'])
        else:
            best_period = worst_period = {}
        
        return {
            "overall_growth": {
                "rate": float(overall_growth_rate),
                "start_period": first.get('period'),
                "end_period": latest.get('period'),
                "start_amount": str(first_total),
                "end_amount": str(latest_total),
                "absolute_change": str(latest_total - first_total),
                "trend": "up" if overall_growth_rate > 5 else "down" if overall_growth_rate < -5 else "stable",
                "strength": "strong" if abs(overall_growth_rate) > 20 else "moderate" if abs(overall_growth_rate) > 5 else "weak"
            },
            "recent_growth": {
                "rate": float(recent_growth_rate),
                "current_period": latest.get('period'),
                "previous_period": previous.get('period'),
                "trend": "up" if recent_growth_rate > 0 else "down" if recent_growth_rate < 0 else "stable",
                "momentum": "accelerating" if recent_growth_rate > overall_growth_rate else "decelerating" if recent_growth_rate < overall_growth_rate else "consistent"
            },
            "period_growth": period_growth,
            "moving_averages": moving_averages,
            "performance_metrics": {
                "average_growth_per_period": float(avg_growth_per_period),
                "volatility": float(volatility),
                "growth_momentum": growth_momentum,
                "cagr": float(cagr) if cagr else None,
                "consistency": self._calculate_growth_consistency(period_growth)
            },
            "highlights": {
                "best_period": best_period,
                "worst_period": worst_period,
                "current_period_rank": self._get_period_rank(latest.get('period'), trends, transaction_type) if len(trends) > 3 else None
            }
        }

    def _calculate_moving_averages(self, trends: List[Dict], transaction_type: str) -> Dict:
        """Calculate 3-period and 5-period moving averages"""
        if len(trends) < 3:
            return {}
        
        moving_averages = {
            "three_period": [],
            "five_period": [] if len(trends) >= 5 else []
        }
        
        # Convert trends to amounts list
        amounts = []
        for trend in trends:
            if transaction_type == 'float':
                amount = Decimal(trend.get('total_deposits', '0.00')) + Decimal(trend.get('total_withdrawals', '0.00'))
            else:
                amount = Decimal(trend.get('total_commission', '0.00'))
            amounts.append(amount)
        
        # Calculate 3-period moving average
        for i in range(2, len(trends)):
            avg_3 = sum(amounts[i-2:i+1]) / Decimal('3')
            moving_averages["three_period"].append({
                "period": trends[i]['period'],
                "average": str(avg_3),
                "deviation": str((amounts[i] - avg_3) / avg_3 * 100) if avg_3 != 0 else "0"
            })
        
        # Calculate 5-period moving average
        if len(trends) >= 5:
            for i in range(4, len(trends)):
                avg_5 = sum(amounts[i-4:i+1]) / Decimal('5')
                moving_averages["five_period"].append({
                    "period": trends[i]['period'],
                    "average": str(avg_5),
                    "deviation": str((amounts[i] - avg_5) / avg_5 * 100) if avg_5 != 0 else "0"
                })
        
        return moving_averages

    def _calculate_volatility(self, trends: List[Dict], transaction_type: str) -> float:
        """Calculate volatility (standard deviation) of growth rates"""
        if len(trends) < 3:
            return 0.0
        
        growth_rates = []
        
        for i in range(1, len(trends)):
            current = trends[i]
            prev = trends[i-1]
            
            if transaction_type == 'float':
                current_total = Decimal(current.get('total_deposits', '0.00')) + Decimal(current.get('total_withdrawals', '0.00'))
                prev_total = Decimal(prev.get('total_deposits', '0.00')) + Decimal(prev.get('total_withdrawals', '0.00'))
            else:
                current_total = Decimal(current.get('total_commission', '0.00'))
                prev_total = Decimal(prev.get('total_commission', '0.00'))
            
            if prev_total > 0:
                growth_rate = ((current_total - prev_total) / prev_total) * 100
                growth_rates.append(float(growth_rate))
        
        if not growth_rates:
            return 0.0
        
        # Calculate standard deviation
        import statistics
        try:
            return statistics.stdev(growth_rates)
        except statistics.StatisticsError:
            return 0.0

    def _determine_growth_momentum(self, trends: List[Dict], transaction_type: str) -> str:
        """Determine if growth is accelerating, decelerating, or stable"""
        if len(trends) < 4:
            return "insufficient_data"
        
        # Get last 3 growth rates
        recent_growth_rates = []
        for i in range(len(trends)-3, len(trends)-1):
            current = trends[i+1]
            prev = trends[i]
            
            if transaction_type == 'float':
                current_total = Decimal(current.get('total_deposits', '0.00')) + Decimal(current.get('total_withdrawals', '0.00'))
                prev_total = Decimal(prev.get('total_deposits', '0.00')) + Decimal(prev.get('total_withdrawals', '0.00'))
            else:
                current_total = Decimal(current.get('total_commission', '0.00'))
                prev_total = Decimal(prev.get('total_commission', '0.00'))
            
            if prev_total > 0:
                growth_rate = ((current_total - prev_total) / prev_total) * 100
                recent_growth_rates.append(float(growth_rate))
        
        if len(recent_growth_rates) < 2:
            return "insufficient_data"
        
        # Check if growth rates are increasing
        if recent_growth_rates[-1] > recent_growth_rates[-2]:
            return "accelerating"
        elif recent_growth_rates[-1] < recent_growth_rates[-2]:
            return "decelerating"
        else:
            return "stable"
    
    def _calculate_cagr(self, trends: List[Dict], transaction_type: str) -> Optional[float]:
        """Calculate Compound Annual Growth Rate"""
        if len(trends) < 2:
            return None
        
        first = trends[0]
        latest = trends[-1]
        
        if transaction_type == 'float':
            first_total = Decimal(first.get('total_deposits', '0.00')) + Decimal(first.get('total_withdrawals', '0.00'))
            latest_total = Decimal(latest.get('total_deposits', '0.00')) + Decimal(latest.get('total_withdrawals', '0.00'))
        else:
            first_total = Decimal(first.get('total_commission', '0.00'))
            latest_total = Decimal(latest.get('total_commission', '0.00'))
        
        # Check for positive values (CAGR requires positive beginning value)
        if first_total <= 0:
            return None
        
        # Check if latest_total is positive (CAGR typically expects positive ending value)
        # If latest_total is negative or zero, CAGR calculation doesn't make sense
        if latest_total <= 0:
            return None
        
        n_periods = len(trends) - 1
        
        try:
            # Calculate CAGR: (Ending Value / Beginning Value)^(1/n) - 1
            ratio = float(latest_total) / float(first_total)
            
            # Ensure ratio is positive before calculating power
            if ratio <= 0:
                return None
                
            cagr = ratio ** (1 / n_periods) - 1
            return cagr * 100  # Convert to percentage
        except (ValueError, ZeroDivisionError):
            return None
        
    def _calculate_growth_consistency(self, period_growth: List[Dict]) -> Dict:
        """Calculate consistency metrics for growth"""
        if not period_growth:
            return {
                "score": 0,
                "rating": "insufficient_data",
                "positive_periods": 0,
                "negative_periods": 0,
                "stable_periods": 0
            }
        
        total_periods = len(period_growth)
        positive_periods = sum(1 for pg in period_growth if pg['growth_rate'] > 0)
        negative_periods = sum(1 for pg in period_growth if pg['growth_rate'] < 0)
        stable_periods = sum(1 for pg in period_growth if pg['growth_rate'] == 0)
        
        consistency_score = (positive_periods / total_periods * 100) if positive_periods > 0 else 0
        
        if consistency_score > 80:
            rating = "excellent"
        elif consistency_score > 60:
            rating = "good"
        elif consistency_score > 40:
            rating = "fair"
        else:
            rating = "poor"
        
        return {
            "score": float(consistency_score),
            "rating": rating,
            "positive_periods": positive_periods,
            "negative_periods": negative_periods,
            "stable_periods": stable_periods,
            "positive_ratio": positive_periods / total_periods if total_periods > 0 else 0
        }

    def _get_period_rank(self, period: str, trends: List[Dict], transaction_type: str) -> Dict:
        """Get rank of current period compared to all periods"""
        if len(trends) < 3:
            return {"rank": 1, "total": 1, "percentile": 100}
        
        # Create list of periods with their amounts
        period_amounts = []
        for trend in trends:
            if transaction_type == 'float':
                amount = Decimal(trend.get('total_deposits', '0.00')) + Decimal(trend.get('total_withdrawals', '0.00'))
            else:
                amount = Decimal(trend.get('total_commission', '0.00'))
            period_amounts.append({
                "period": trend['period'],
                "amount": amount
            })
        
        # Sort by amount descending
        period_amounts.sort(key=lambda x: x['amount'], reverse=True)
        
        # Find rank of current period
        for rank, item in enumerate(period_amounts, 1):
            if item['period'] == period:
                total_periods = len(period_amounts)
                percentile = ((total_periods - rank) / total_periods) * 100
                return {
                    "rank": rank,
                    "total": total_periods,
                    "percentile": float(percentile),
                    "performance": "top" if rank <= 3 else "above_average" if percentile > 50 else "below_average" if percentile > 20 else "bottom"
                }
        
        return {"rank": len(period_amounts) + 1, "total": len(period_amounts), "percentile": 0}

    def gather_scraping_statistics(self,start_date, end_date, company_shortcode):
        """
        Gather statistics from the database for the email report.
        """    
        # Agent statistics
        total_agents = AgentCompany.query.count()
                
        active_agents = AgentCompany.query.filter_by(
            parent_short_code=company_shortcode,
            is_active_on_portal=True
        ).count()
        
        # Float balance analysis        
        agents_below_20000,error= agent_company_service.count_agents_by_balance_threshold(
                            parent_short_code=company_shortcode,
                            threshold=20000,
                            above_threshold=False
                        )
        
        agents_below_5000,error= agent_company_service.count_agents_by_balance_threshold(
                            parent_short_code=company_shortcode,
                            threshold=5000,
                            above_threshold=False
                        )
        
        agents_below_1000,error= agent_company_service.count_agents_by_balance_threshold(
                            parent_short_code=company_shortcode,
                            threshold=5000,
                            above_threshold=False
                        )
                
        # Average float balance
        avg_float_result = db.session.query(
            db.func.avg(AgentCompany.float_balance)
        ).filter(
            AgentCompany.business_short_code == company_shortcode,
            AgentCompany.float_balance.isnot(None)
        ).first()
        
        average_float = avg_float_result[0] or 0
        
        # Transaction statistics for the period
        transactions = Transaction.query.filter(
            Transaction.company.has(shortcode=company_shortcode),
            Transaction.initiation_time.between(start_date, end_date)
        ).all()
        
        total_deposits = sum(1 for t in transactions if t.paid_in and t.paid_in > 0)
        total_withdrawals = sum(1 for t in transactions if t.withdrawn and t.withdrawn > 0)
        
        total_deposit_amount = sum(
            float(t.paid_in or 0) for t in transactions if t.paid_in
        )
        total_withdrawal_amount = sum(
            float(t.withdrawn or 0) for t in transactions if t.withdrawn
        )
        
        net_flow = total_deposit_amount + total_withdrawal_amount
        
        # Commission statistics
        commission_transactions = [t for t in transactions if t.transaction_type == 'commission']
        total_commission = sum(float(t.commission_amount or 0) for t in commission_transactions)
        commission_transaction_count = len(commission_transactions)
        
        avg_commission_rate = sum(
            float(t.commission_rate or 0) for t in commission_transactions
        ) / commission_transaction_count if commission_transaction_count > 0 else 0
        
        # Average transaction value
        all_amounts = [float(t.paid_in or 0) for t in transactions if t.paid_in] + \
                    [float(t.withdrawn or 0) for t in transactions if t.withdrawn]
        average_transaction_value = sum(all_amounts) / len(all_amounts) if all_amounts else 0
        
        return {
            'scraping_session': {
                'start_date': start_date,
                'end_date': end_date,
                'company_shortcode': company_shortcode,
                'total_transactions': len(transactions),
                'scraped_at': datetime.now(),
                'agent_company_count': total_agents,
                'successful_scrapes': total_agents,  # Adjust based on actual scraping
                'failed_scrapes': 0  # Adjust based on actual scraping
            },
            'agent_stats': {
                'total_agents': total_agents,
                'active_agents': active_agents,
                'agents_below_20000': agents_below_20000,
                'agents_below_5000': agents_below_5000,
                'agents_below_1000': agents_below_1000,
                'average_float': float(average_float)
            },
            'transaction_stats': {
                'total_deposits': total_deposits,
                'total_withdrawals': total_withdrawals,
                'total_deposit_amount': total_deposit_amount,
                'total_withdrawal_amount': total_withdrawal_amount,
                'net_flow': net_flow,
                'average_transaction_value': average_transaction_value
            },
            'commission_stats': {
                'total_commission': total_commission,
                'commission_transactions': commission_transaction_count,
                'average_commission_rate': avg_commission_rate
            }
        }

    def get_dashboard_analytics(self, filters: Dict = None) -> Dict:
        """
        Get comprehensive analytics data for the dashboard using ORM queries.
        Provides KPIs, trends, and recent activity based on transaction data.
        """
        try:
            filters = filters or {}
            days = filters.get('days', 30)

            # Calculate date ranges - truncate to day boundaries for consistent results
            now = datetime.now()
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            prev_end_date = (start_date - timedelta(seconds=1))  # end of the day before start
            prev_start_date = (start_date - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

            with db_pool.get_cursor() as cursor:
                # Build WHERE conditions
                conditions = ["1=1"]
                params = []

                if 'company_id' in filters and filters['company_id']:
                    conditions.append("company_id = %s")
                    params.append(filters['company_id'])

                if 'agent_id' in filters and filters['agent_id']:
                    conditions.append("agent_id = %s")
                    params.append(filters['agent_id'])

                where_clause = " AND ".join(conditions)

                # ============ KPI STATS ============

                # Current period stats - float transactions
                kpi_query = f"""
                    SELECT
                        COUNT(*) as total_transactions,
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(paid_in, 0)) ELSE 0 END), 0) as total_deposits,
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(withdrawn, 0)) ELSE 0 END), 0) as total_withdrawals,
                        COUNT(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL THEN 1 END) as float_transactions,
                        COUNT(DISTINCT agent_id) as active_agents,
                        COUNT(DISTINCT company_id) as active_companies
                    FROM transactions
                    WHERE {where_clause}
                    AND completion_time BETWEEN %s AND %s
                """
                cursor.execute(kpi_query, params + [start_date, end_date])
                current_stats = cursor.fetchone()

                cursor.execute(kpi_query, params + [prev_start_date, prev_end_date])
                prev_stats = cursor.fetchone()

                # Commission earned: sum ABS(withdrawn) for commission transactions
                # scoped to the current user's company shortcodes when provided.
                commission_shortcodes = filters.get('commission_shortcodes')
                if commission_shortcodes is not None and len(commission_shortcodes) > 0:
                    sc_placeholders = ','.join(['%s'] * len(commission_shortcodes))
                    commission_where = f"{where_clause} AND transaction_type = 'commission' AND business_shortcode IN ({sc_placeholders})"
                    commission_params = params + list(commission_shortcodes)
                else:
                    commission_where = f"{where_clause} AND transaction_type IN ('commission_held', 'commission')"
                    commission_params = params

                commission_query = f"""
                    SELECT
                        COUNT(*) as commission_transactions,
                        COALESCE(SUM(ABS(COALESCE(withdrawn, 0))), 0) as total_commissions
                    FROM transactions
                    WHERE {commission_where}
                    AND completion_time BETWEEN %s AND %s
                """
                cursor.execute(commission_query, commission_params + [start_date, end_date])
                current_commissions = cursor.fetchone()

                cursor.execute(commission_query, commission_params + [prev_start_date, prev_end_date])
                prev_commissions = cursor.fetchone()

                # Calculate growth percentages
                def calc_growth(current, previous):
                    if previous and previous > 0:
                        return round(((current - previous) / previous) * 100, 1)
                    return 0 if current == 0 else 100

                total_volume = float(current_stats['total_deposits'] or 0) + float(current_stats['total_withdrawals'] or 0)
                prev_volume = float(prev_stats['total_deposits'] or 0) + float(prev_stats['total_withdrawals'] or 0)

                kpi_data = {
                    'total_volume': {
                        'value': total_volume,
                        'change': calc_growth(total_volume, prev_volume),
                        'trend': 'up' if total_volume >= prev_volume else 'down'
                    },
                    'total_transactions': {
                        'value': int(current_stats['total_transactions'] or 0),
                        'change': calc_growth(current_stats['total_transactions'] or 0, prev_stats['total_transactions'] or 0),
                        'trend': 'up' if (current_stats['total_transactions'] or 0) >= (prev_stats['total_transactions'] or 0) else 'down'
                    },
                    'total_commissions': {
                        'value': float(current_commissions['total_commissions'] or 0),
                        'change': calc_growth(current_commissions['total_commissions'] or 0, prev_commissions['total_commissions'] or 0),
                        'trend': 'up' if (current_commissions['total_commissions'] or 0) >= (prev_commissions['total_commissions'] or 0) else 'down'
                    },
                    'active_agents': {
                        'value': int(current_stats['active_agents'] or 0),
                        'change': calc_growth(current_stats['active_agents'] or 0, prev_stats['active_agents'] or 0),
                        'trend': 'up' if (current_stats['active_agents'] or 0) >= (prev_stats['active_agents'] or 0) else 'down'
                    },
                    'average_transaction': {
                        'value': round(total_volume / max(current_stats['total_transactions'] or 1, 1), 2),
                        'change': 0,
                        'trend': 'up'
                    }
                }

                # ============ MONTHLY TRENDS ============
                # Using PostgreSQL date functions - properly separated by transaction_type
                trends_query = f"""
                    SELECT
                        TO_CHAR(completion_time, 'YYYY-MM') as month,
                        TO_CHAR(completion_time, 'Mon') as month_name,
                        COUNT(*) as transactions,
                        -- Float transactions: deposits and withdrawals
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(paid_in, 0)) ELSE 0 END), 0) as deposits,
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(withdrawn, 0)) ELSE 0 END), 0) as withdrawals,
                        -- Commission transactions only
                        COALESCE(SUM(CASE WHEN transaction_type = 'commission'
                            THEN COALESCE(commission_amount, 0) ELSE 0 END), 0) as commissions,
                        -- Count by type
                        COUNT(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL THEN 1 END) as float_count,
                        COUNT(CASE WHEN transaction_type = 'commission' THEN 1 END) as commission_count
                    FROM transactions
                    WHERE {where_clause}
                    AND completion_time >= NOW() - INTERVAL '12 months'
                    GROUP BY TO_CHAR(completion_time, 'YYYY-MM'), TO_CHAR(completion_time, 'Mon')
                    ORDER BY month ASC
                """
                cursor.execute(trends_query, params)
                trends_result = cursor.fetchall()

                monthly_trends = []
                for row in trends_result:
                    monthly_trends.append({
                        'name': row['month_name'],
                        'month': row['month'],
                        'transactions': int(row['transactions'] or 0),
                        'deposits': float(row['deposits'] or 0),
                        'withdrawals': float(row['withdrawals'] or 0),
                        'commissions': float(row['commissions'] or 0),
                        'volume': float(row['deposits'] or 0) + float(row['withdrawals'] or 0)
                    })

                # ============ TRANSACTION TYPE DISTRIBUTION ============
                # Shows distribution by reason_type for float transactions
                distribution_query = f"""
                    SELECT
                        reason_type,
                        COUNT(*) as count,
                        -- Float transactions volume
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(paid_in, 0)) + ABS(COALESCE(withdrawn, 0)) ELSE 0 END), 0) as float_volume,
                        -- Commission transactions total
                        COALESCE(SUM(CASE WHEN transaction_type = 'commission'
                            THEN COALESCE(commission_amount, 0) ELSE 0 END), 0) as commission_amount
                    FROM transactions
                    WHERE {where_clause}
                    AND completion_time BETWEEN %s AND %s
                    GROUP BY reason_type
                    ORDER BY count DESC
                    LIMIT 5
                """
                cursor.execute(distribution_query, params + [start_date, end_date])
                distribution_result = cursor.fetchall()

                # Color palette for pie chart
                colors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444']

                type_distribution = []
                total_count = sum(row['count'] or 0 for row in distribution_result)
                for idx, row in enumerate(distribution_result):
                    percentage = round((row['count'] / total_count * 100), 1) if total_count > 0 else 0
                    type_distribution.append({
                        'name': row['reason_type'] or 'Unknown',
                        'value': percentage,
                        'count': int(row['count'] or 0),
                        'float_volume': float(row['float_volume'] or 0),
                        'commission_amount': float(row['commission_amount'] or 0),
                        'color': colors[idx % len(colors)]
                    })

                # ============ RECENT TRANSACTIONS ============

                recent_query = f"""
                    SELECT
                        id,
                        receipt_no,
                        details,
                        COALESCE(paid_in, 0) as paid_in,
                        COALESCE(withdrawn, 0) as withdrawn,
                        completion_time,
                        reason_type,
                        transaction_type
                    FROM transactions
                    WHERE {where_clause}
                    ORDER BY completion_time DESC
                    LIMIT 10
                """
                cursor.execute(recent_query, params)
                recent_result = cursor.fetchall()

                recent_transactions = []
                for row in recent_result:
                    # Determine activity type based on transaction
                    if float(row['paid_in'] or 0) > 0:
                        action_type = 'deposit'
                        action = f"Deposit of KES {float(row['paid_in']):,.2f}"
                    elif float(row['withdrawn'] or 0) != 0:
                        action_type = 'withdrawal'
                        action = f"Withdrawal of KES {abs(float(row['withdrawn'])):,.2f}"
                    else:
                        action_type = 'other'
                        action = row['details'][:50] if row['details'] else 'Transaction processed'

                    # Calculate time ago
                    completion_time = row['completion_time']
                    if completion_time:
                        time_diff = datetime.now() - completion_time
                        if time_diff.days > 0:
                            time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                        elif time_diff.seconds >= 3600:
                            hours = time_diff.seconds // 3600
                            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                        elif time_diff.seconds >= 60:
                            minutes = time_diff.seconds // 60
                            time_ago = f"{minutes} min ago"
                        else:
                            time_ago = "Just now"
                    else:
                        time_ago = "Unknown"

                    recent_transactions.append({
                        'id': row['id'],
                        'receipt_no': row['receipt_no'],
                        'action': action,
                        'time': time_ago,
                        'type': action_type,
                        'reason_type': row['reason_type']
                    })

                # ============ DAILY TRENDS (for detailed chart) ============
                # Properly separated by transaction_type
                daily_query = f"""
                    SELECT
                        DATE(completion_time) as date,
                        COUNT(*) as transactions,
                        -- Float transactions: deposits and withdrawals
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(paid_in, 0)) ELSE 0 END), 0) as deposits,
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(withdrawn, 0)) ELSE 0 END), 0) as withdrawals,
                        -- Commission transactions only
                        COALESCE(SUM(CASE WHEN transaction_type = 'commission'
                            THEN COALESCE(commission_amount, 0) ELSE 0 END), 0) as commissions
                    FROM transactions
                    WHERE {where_clause}
                    AND completion_time BETWEEN %s AND %s
                    GROUP BY DATE(completion_time)
                    ORDER BY date ASC
                """
                cursor.execute(daily_query, params + [start_date, end_date])
                daily_result = cursor.fetchall()

                daily_trends = []
                for row in daily_result:
                    daily_trends.append({
                        'date': row['date'].strftime('%Y-%m-%d') if row['date'] else '',
                        'name': row['date'].strftime('%d %b') if row['date'] else '',
                        'transactions': int(row['transactions'] or 0),
                        'deposits': float(row['deposits'] or 0),
                        'withdrawals': float(row['withdrawals'] or 0),
                        'commissions': float(row['commissions'] or 0),
                        'volume': float(row['deposits'] or 0) + float(row['withdrawals'] or 0)
                    })

                # ============ BUSINESS HEALTH METRICS ============

                # Calculate average daily volume
                avg_daily_volume = total_volume / max(days, 1)

                # Transaction success rate
                success_query = f"""
                    SELECT
                        COUNT(CASE WHEN transaction_status = 'Completed' THEN 1 END) as completed,
                        COUNT(*) as total
                    FROM transactions
                    WHERE {where_clause}
                    AND completion_time BETWEEN %s AND %s
                """
                cursor.execute(success_query, params + [start_date, end_date])
                success_result = cursor.fetchone()
                success_rate = round((success_result['completed'] / max(success_result['total'], 1)) * 100, 1)

                # Growth momentum (comparing recent week to previous week)
                # Only considers float transactions for volume calculation
                week_ago = end_date - timedelta(days=7)
                two_weeks_ago = end_date - timedelta(days=14)

                momentum_query = f"""
                    SELECT
                        COALESCE(SUM(CASE WHEN transaction_type = 'float' OR transaction_type IS NULL
                            THEN ABS(COALESCE(paid_in, 0)) + ABS(COALESCE(withdrawn, 0)) ELSE 0 END), 0) as total_volume
                    FROM transactions
                    WHERE {where_clause}
                    AND completion_time BETWEEN %s AND %s
                """
                cursor.execute(momentum_query, params + [week_ago, end_date])
                recent_week = float(cursor.fetchone()['total_volume'] or 0)

                cursor.execute(momentum_query, params + [two_weeks_ago, week_ago])
                prev_week = float(cursor.fetchone()['total_volume'] or 0)

                weekly_growth = calc_growth(recent_week, prev_week)

                health_metrics = {
                    'avg_daily_volume': round(avg_daily_volume, 2),
                    'success_rate': success_rate,
                    'weekly_growth': weekly_growth,
                    'growth_momentum': 'accelerating' if weekly_growth > 5 else 'stable' if weekly_growth >= -5 else 'declining'
                }

                return {
                    'success': True,
                    'data': {
                        'kpis': kpi_data,
                        'monthly_trends': monthly_trends,
                        'daily_trends': daily_trends,
                        'type_distribution': type_distribution,
                        'recent_transactions': recent_transactions,
                        'health_metrics': health_metrics,
                        'period': {
                            'start_date': start_date.strftime('%Y-%m-%d'),
                            'end_date': end_date.strftime('%Y-%m-%d'),
                            'days': days
                        }
                    }
                }

        except Exception as e:
            logger.error(f"Error fetching dashboard analytics: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Failed to fetch dashboard analytics: {str(e)}"
            }

    def get_clawbacks(self, filters: Dict = None) -> Dict:
        """Return commission_clawback transactions, newest first."""
        try:
            from app.model.transaction import Transaction
            query = Transaction.query.filter_by(transaction_type='commission_clawback')

            if filters:
                if filters.get('start_date'):
                    query = query.filter(Transaction.completion_time >= filters['start_date'])
                if filters.get('end_date'):
                    query = query.filter(Transaction.completion_time <= filters['end_date'])

            rows = query.order_by(Transaction.completion_time.desc()).all()
            data = [
                {
                    'id': r.id,
                    'receipt_no': r.receipt_no,
                    'completion_time': r.completion_time.isoformat() if r.completion_time else None,
                    'details': r.details,
                    'withdrawn': float(r.withdrawn or 0),
                    'reason_type': r.reason_type,
                    'currency': r.currency,
                    'transaction_status': r.transaction_status,
                }
                for r in rows
            ]
            return {'success': True, 'data': data, 'total': len(data)}
        except Exception as e:
            logger.error(f"Error fetching clawbacks: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

