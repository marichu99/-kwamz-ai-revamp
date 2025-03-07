from io import BytesIO
import pandas as pd
from flask import send_file
from datetime import datetime
from app.model.transaction import Transaction
from app.model.agentcompany import AgentCompany
from app.service.date_service import DateService
from app.service.reports.commissions_report_service import CommissionReportService

class ExportService:
    """Service for exporting data in various formats"""
    
    def __init__(self):
        self.date_service = DateService()
        self.commission_service = CommissionReportService()
    
    def export_commission_report(self, format_type, start_date=None, end_date=None,
                               date_range='custom', transaction_type='commission',
                               reason_type=None, transaction_status=None):
        """
        Export commission report in specified format
        """
        # Generate report data
        report = self.commission_service.generate_report(
            start_date=start_date,
            end_date=end_date,
            date_range=date_range,
            transaction_type=transaction_type,
            reason_type=reason_type,
            transaction_status=transaction_status
        )
        
        # Get raw transaction data
        start_date_obj, end_date_obj = self.date_service.calculate_date_range(
            date_range, start_date, end_date
        )
        
        transactions = self._get_transactions_for_export(
            start_date_obj, end_date_obj, reason_type, transaction_status
        )
        
        # Export based on format
        if format_type == 'csv':
            return self._export_to_csv(transactions, report)
        elif format_type == 'excel':
            return self._export_to_excel(transactions, report)
        elif format_type == 'pdf':
            return self._export_to_pdf(transactions, report)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def export_transactions(self, transaction_type='float', start_date=None,
                          end_date=None, reason_type=None, transaction_status=None):
        """
        Export transactions in CSV format
        """
        # Calculate date range
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Get transactions
        transactions = self._get_transactions_for_export(
             start_date_obj, end_date_obj, reason_type, transaction_status, transaction_type
        )
        
        # Export to CSV
        return self._export_transactions_to_csv(transactions, transaction_type)
    
    def _get_transactions_for_export(self, start_date, end_date, reason_type=None,
                                   transaction_status=None, transaction_type='commission'):
        """Get transactions for export"""
        query = Transaction.query.filter(
            Transaction.transaction_type == transaction_type,
        )
        
        if start_date:
            query = query.filter(Transaction.initiation_time >= start_date)
        if end_date:
            query = query.filter(Transaction.initiation_time <= end_date)
        if reason_type:
            query = query.filter(Transaction.reason_type == reason_type)
        if transaction_status:
            query = query.filter(Transaction.transaction_status == transaction_status)
        
        return query.all()
    
    def _export_to_csv(self, transactions, report):
        """Export to CSV format"""
        # Prepare transaction data
        data = []
        for t in transactions:
            agent = AgentCompany.query.get(t.agent_id) if t.agent_id else None
            
            data.append({
                'Receipt No': t.receipt_no,
                'Completion Time': t.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
                'Agent Name': agent.company_name if agent else 'N/A',
                'Agent Code': agent.short_code if agent else 'N/A',
                'Transaction Type': t.reason_type,
                'Commission Amount': float(t.commission_amount or 0),
                'Commission Rate': float(t.commission_rate or 0),
                'Linked Transaction': t.linked_transaction_id,
                'Status': t.transaction_status,
                'Details': t.details
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Export to CSV
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'commissions_report_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    
    def _export_to_excel(self, transactions, report):
        """Export to Excel format"""
        # Prepare transaction data
        data = []
        for t in transactions:
            agent = AgentCompany.query.get(t.agent_id) if t.agent_id else None
            
            data.append({
                'Receipt No': t.receipt_no,
                'Completion Time': t.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
                'Agent Name': agent.company_name if agent else 'N/A',
                'Agent Code': agent.short_code if agent else 'N/A',
                'Transaction Type': t.reason_type,
                'Commission Amount': float(t.commission_amount or 0),
                'Commission Rate': float(t.commission_rate or 0),
                'Linked Transaction': t.linked_transaction_id,
                'Status': t.transaction_status,
                'Details': t.details
            })
        
        # Create DataFrames
        transactions_df = pd.DataFrame(data)
        
        # Summary DataFrame
        summary_data = {
            'Metric': ['Total Transactions', 'Total Commission', 'Average Commission', 'Period'],
            'Value': [
                report['summary']['total_transactions'],
                report['summary']['total_commission'],
                report['summary']['average_commission'],
                report['period']
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Export to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            transactions_df.to_excel(writer, sheet_name='Commission Transactions', index=False)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add categories sheet if available
            if report['categories']:
                categories_df = pd.DataFrame(report['categories'])
                categories_df.to_excel(writer, sheet_name='Categories', index=False)
        
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'commissions_report_{timestamp}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    def _export_to_pdf(self, transactions, report):
        """Export to PDF format (simplified version)"""
        # Note: For production, use a proper PDF library like reportlab
        # This is a simplified version that exports as CSV with PDF extension
        return self._export_to_csv(transactions, report)
    
    def _export_transactions_to_csv(self, transactions, transaction_type):
        """Export transactions to CSV"""
        data = []
        
        for t in transactions:
            if transaction_type == 'float':
                row = {
                    'Receipt No': t.receipt_no,
                    'Completion Time': t.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Initiation Time': t.initiation_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Details': t.details,
                    'Transaction Status': t.transaction_status,
                    'Paid In': float(t.paid_in or 0),
                    'Withdrawn': float(t.withdrawn or 0),
                    'Balance': float(t.balance or 0),
                    'Reason Type': t.reason_type,
                    'Other Party Info': t.other_party_info,
                    'Account Number': t.account_number,
                    'Currency': t.currency
                }
            else:  # commission
                row = {
                    'Receipt No': t.receipt_no,
                    'Completion Time': t.completion_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Initiation Time': t.initiation_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Details': t.details,
                    'Transaction Status': t.transaction_status,
                    'Commission Amount': float(t.commission_amount or 0),
                    'Commission Rate': float(t.commission_rate or 0),
                    'Parent Transaction ID': t.parent_transaction_id,
                    'Linked Transaction': t.linked_transaction_id,
                    'Reason Type': t.reason_type,
                    'Currency': t.currency
                }
            
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Export to CSV
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{transaction_type}_transactions_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )