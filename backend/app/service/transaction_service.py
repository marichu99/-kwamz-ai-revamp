import pandas as pd
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app import db
from app.model.transaction import Transaction, TransactionStats
from app.database.connection_pool import db_pool
from app.model.company import Company
from sqlalchemy import and_, case, extract, or_, func
import logging
from typing import List, Dict, Any, Optional, Tuple,Union
from werkzeug.utils import secure_filename
import json
import traceback
from datetime import datetime
from decimal import Decimal, InvalidOperation
import numpy as np
from flask import current_app

from app.service.company_service import CompanyService
from app.model.agentcompany import AgentCompany

logger = logging.getLogger(__name__)

company_service = CompanyService(db)

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
    
    def _parse_date(self, date_string):
        """Parse date string to datetime object, handling multiple formats"""
        if not date_string:
            return datetime.now()
        
        # Convert to string if it's not already
        if not isinstance(date_string, str):
            date_string = str(date_string)
        
        # Remove any whitespace
        date_string = date_string.strip()
        
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
        
        # If all else fails, log and use current time
        print(f"Warning: Could not parse date '{date_string}'. Using current time.")
        return datetime.now()
        
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
                
                # Parse dates
                completion_time = self._parse_date(trans_data.get('completion_time'))
                initiation_time = self._parse_date(trans_data.get('initiation_time', trans_data.get('completion_time')))
                
                # Parse balance confirmed
                balance_confirmed = trans_data.get('balance_confirmed', False)
                if isinstance(balance_confirmed, str):
                    balance_confirmed = balance_confirmed.upper() in ['TRUE', 'YES', '1', 'Y']
                    
                company_id = company_service.get_company_by_shortcode(company_shortcode).id
                
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
                    'other_party_info': trans_data.get('other_party_info'),
                    'linked_transaction_id': trans_data.get('linked_transaction_id'),
                    'account_number': trans_data.get('account_number'),
                    'currency': trans_data.get('currency', 'KES'),
                    'transaction_type': transaction_type,
                    'company_id': company_id,
                    'agent_id': agent_id,
                    'business_shortcode': business_shortcode,
                    'updated_at': datetime.now()
                }
                
                # Add commission-specific fields for commission transactions
                if transaction_type == 'commission':
                    # Extract commission amount from paid_in or withdrawn
                    commission_amount = self._parse_decimal(trans_data.get('commission_amount'))
                    if not commission_amount:
                        commission_amount = self._parse_decimal(trans_data.get('paid_in', trans_data.get('withdrawn')))
                    
                    # Calculate commission rate if not provided
                    commission_rate = self._parse_decimal(trans_data.get('commission_rate', '0'))
                    
                    transaction_data.update({
                        'commission_rate': commission_rate,
                        'commission_amount': commission_amount,
                        'parent_transaction_id': trans_data.get('parent_transaction_id')
                    })
                
                if existing:
                    # Update existing transaction
                    for key, value in transaction_data.items():
                        if key not in ['receipt_no', 'transaction_type']:  # Don't update these
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
                
                # Prepare transaction data from row
                transaction_data = {
                    'receipt_no': receipt_no,
                    'completion_time': self._parse_date(row.get('completion_time')),
                    'initiation_time': self._parse_date(row.get('initiation_time', row.get('completion_time'))),
                    'details': str(row.get('details', '')),
                    'transaction_status': str(row.get('transaction_status', 'Completed')),
                    'paid_in': self._parse_decimal(row.get('paid_in')),
                    'withdrawn': self._parse_decimal(row.get('withdrawn')),
                    'balance': self._parse_decimal(row.get('balance', '0')),
                    'balance_confirmed': str(row.get('balance_confirmed', 'FALSE')).upper() in ['TRUE', 'YES', '1', 'Y'],
                    'reason_type': str(row.get('reason_type', '')),
                    'other_party_info': str(row.get('other_party_info', '')),
                    'linked_transaction_id': str(row.get('linked_transaction_id', '')),
                    'account_number': str(row.get('account_number', '')),
                    'currency': str(row.get('currency', 'KES')),
                    'transaction_type': transaction_type,
                    'company_id': company_id,
                    'agent_id': agent_id
                }
                
                if transaction_type == 'commission':
                    transaction_data.update({
                        'commission_rate': self._parse_decimal(row.get('commission_rate', '0')),
                        'commission_amount': self._parse_decimal(row.get('commission_amount', 
                                                                       row.get('paid_in', row.get('withdrawn')))),
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
                        Transaction.reason_type.ilike(search_term)
                    )
                )

            # Get total count before pagination
            total = query.count()

            # Order by most recent first
            query = query.order_by(Transaction.completion_time.desc())

            # Pagination
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            transactions = pagination.items

            # Serialize transactions
            transactions_data = [trans.to_dict() for trans in transactions]

            # Calculate summary totals (optional but very useful)
            totals_query = Transaction.query
            if 'start_date' in filters or 'end_date' in filters or 'company_id' in filters or 'agent_id' in filters:
                # Re-apply same filters for accurate totals
                if filters.get('company_id'):
                    totals_query = totals_query.filter(Transaction.company_id == filters['company_id'])
                if filters.get('agent_id'):
                    totals_query = totals_query.filter(Transaction.agent_id == filters['agent_id'])
                if filters.get('transaction_type'):
                    totals_query = totals_query.filter(Transaction.transaction_type == filters['transaction_type'])
                # Date filters already handled above — reuse logic if needed

                if filters.get('start_date'):
                    # Reuse parsed start_dt if available, or re-parse safely
                    try:
                        start_dt = datetime.strptime(filters['start_date'].split(' ')[0], '%Y-%m-%d')
                        totals_query = totals_query.filter(Transaction.completion_time >= start_dt)
                    except:
                        pass
                if filters.get('end_date'):
                    try:
                        end_dt = datetime.strptime(filters['end_date'].split(' ')[0], '%Y-%m-%d')
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                        totals_query = totals_query.filter(Transaction.completion_time <= end_dt)
                    except:
                        pass

            total_paid_in = totals_query.with_entities(func.sum(Transaction.paid_in)).scalar() or Decimal('0.00')
            total_withdrawn = totals_query.with_entities(func.sum(Transaction.withdrawn)).scalar() or Decimal('0.00')

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
                    "net_flow": str(total_paid_in + total_withdrawn)  # withdrawn is negative
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
    
    def get_last_scraped_per_shortcode(self) -> Dict[str,int]:
        """Get the last scraped transaction ID per business shortcode"""
        try:
            print(f"We are trying to get the last scraped dictionary ")
            with db_pool.get_cursor() as cursor:
                return self._get_last_scraped_per_till(cursor)
            
        except Exception as e:
            logger.error(f"Error getting last scraped per shortcode: {str(e)}", exc_info=True)
            return {}
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

    def _get_last_scraped_per_till(self, cursor) -> Dict[str, int]:
        """Get number of days since last scrape for each till (Kenya time)"""
        query = """
            select business_short_code,
                MAX(last_scraped_at) as last_scraped_time
            from agentcompanies
            GROUP BY business_short_code
            ORDER BY last_scraped_time ASC;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        now = datetime.now(self.kenya_tz)

        return {
            row['business_short_code']: (
                now - row['last_scraped_time'].replace(tzinfo=self.kenya_tz)
            ).days
            for row in results
        }
    
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
                    "rate": str(Decimal(trans['commission_rate'] or '0.00')),
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
            SELECT COALESCE(AVG(commission_rate), 0) as avg_rate
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
        
        if first_total <= 0:
            return None
        
        # Assume each period is roughly equal time (daily, weekly, monthly)
        # For CAGR, we need to know the actual time period in years
        # This is a simplified version assuming each trend is a time period
        n_periods = len(trends) - 1
        
        # Calculate CAGR: (Ending Value / Beginning Value)^(1/n) - 1
        cagr = (float(latest_total) / float(first_total)) ** (1 / n_periods) - 1
        return cagr * 100  # Convert to percentage

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
        total_agents = AgentCompany.query.filter_by(
            business_short_code=company_shortcode
        ).count()
        
        active_agents = AgentCompany.query.filter_by(
            business_short_code=company_shortcode,
            is_active_on_portal=True
        ).count()
        
        # Float balance analysis
        agents_below_20000 = AgentCompany.query.filter(
            AgentCompany.business_short_code == company_shortcode,
            AgentCompany.float_balance < 20000,
            AgentCompany.float_balance.isnot(None)
        ).count()
        
        agents_below_5000 = AgentCompany.query.filter(
            AgentCompany.business_short_code == company_shortcode,
            AgentCompany.float_balance < 5000,
            AgentCompany.float_balance.isnot(None)
        ).count()
        
        agents_below_1000 = AgentCompany.query.filter(
            AgentCompany.business_short_code == company_shortcode,
            AgentCompany.float_balance < 1000,
            AgentCompany.float_balance.isnot(None)
        ).count()
        
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
        
        net_flow = total_deposit_amount - total_withdrawal_amount
        
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

