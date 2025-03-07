from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.model.transaction import Transaction
from app.model.agentcompany import AgentCompany
from app.service.date_service import DateService

class CommissionReportService:
    """Service for generating commission reports"""
    
    def __init__(self):
        self.date_service = DateService()
    
    def generate_report(self, start_date=None, end_date=None, date_range='custom',
                       transaction_type='commission', reason_type=None, transaction_status=None):
        """
        Generate comprehensive commission report
        """        
        # Calculate date range
        start_date_obj, end_date_obj = self.date_service.calculate_date_range(
            date_range, start_date, end_date
        )
        
        # Get commission transactions
        commission_transactions = self._get_commission_transactions(
            start_date_obj, end_date_obj, reason_type, transaction_status
        )
        
        if not commission_transactions:
            return self._get_empty_report(start_date_obj, end_date_obj)
        
        # Generate report sections
        summary = self._generate_summary(commission_transactions, start_date_obj, end_date_obj)
        categories = self._generate_category_analysis(commission_transactions)
        top_agents = self._generate_top_agents(commission_transactions)
        trends = self._generate_trends(commission_transactions, start_date_obj, end_date_obj)
        
        # Compile report
        report = {
            'period': f"{start_date_obj.strftime('%d %b %Y')} - {end_date_obj.strftime('%d %b %Y')}",
            'summary': summary,
            'categories': categories,
            'top_agents': top_agents,
            'trends': trends
        }
        
        return report
    
    def _get_commission_transactions(self, start_date, end_date, reason_type=None, transaction_status=None):
        """Get commission transactions with filters"""
        query = Transaction.query.filter(
            Transaction.transaction_type == 'commission',
            Transaction.initiation_time >= start_date,
            Transaction.initiation_time <= end_date
        )
        
        if reason_type:
            query = query.filter(Transaction.reason_type == reason_type)
        
        if transaction_status:
            query = query.filter(Transaction.transaction_status == transaction_status)
        
        return query.all()
    
    def _generate_summary(self, transactions, start_date, end_date):
        """Generate summary statistics"""
        total_transactions = len(transactions)
        total_commission = sum(float(t.commission_amount or 0) for t in transactions)
        average_commission = total_commission / total_transactions if total_transactions > 0 else 0
        
        # Find top agent
        top_agent = self._find_top_agent(transactions)
        
        # Calculate growth
        previous_period_data = self._get_previous_period_data(
            transactions[0].company_id, start_date, end_date
        )
        current_total = total_commission
        previous_total = previous_period_data.get('total_commission', 0)
        
        growth_percentage = 0
        if previous_total > 0:
            growth_percentage = ((current_total - previous_total) / previous_total * 100)
        
        return {
            'total_transactions': total_transactions,
            'total_commission': round(total_commission, 2),
            'average_commission': round(average_commission, 2),
            'top_agent_commission': round(top_agent['total_commission'], 2) if top_agent else 0,
            'top_agent_name': top_agent['name'] if top_agent else 'N/A',
            'growth_percentage': round(growth_percentage, 2)
        }
    
    def _find_top_agent(self, transactions):
        """Find agent with highest total commission"""
        agent_data = {}
        
        for t in transactions:
            agent_id = t.agent_id
            if not agent_id:
                continue
            
            if agent_id not in agent_data:
                agent = AgentCompany.query.get(agent_id)
                agent_data[agent_id] = {
                    'name': agent.company_name if agent else f'Agent {agent_id}',
                    'total_commission': 0
                }
            
            agent_data[agent_id]['total_commission'] += float(t.commission_amount or 0)
        
        if not agent_data:
            return None
        
        top_agent_id = max(agent_data.items(), key=lambda x: x[1]['total_commission'])[0]
        return {
            'id': top_agent_id,
            'name': agent_data[top_agent_id]['name'],
            'total_commission': agent_data[top_agent_id]['total_commission']
        }
    
    def _generate_category_analysis(self, transactions):
        """Analyze commissions by category"""
        categories = {}
        
        for t in transactions:
            category = t.reason_type or 'Unknown'
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'total_commission': 0,
                    'transactions': []
                }
            
            categories[category]['count'] += 1
            categories[category]['total_commission'] += float(t.commission_amount or 0)
            categories[category]['transactions'].append(t)
        
        # Calculate total for percentages
        total_commission = sum(data['total_commission'] for data in categories.values())
        
        # Format categories
        result = []
        for category_name, data in categories.items():
            avg_commission = data['total_commission'] / data['count'] if data['count'] > 0 else 0
            percentage = (data['total_commission'] / total_commission * 100) if total_commission > 0 else 0
            
            result.append({
                'name': category_name,
                'count': data['count'],
                'total_commission': round(data['total_commission'], 2),
                'average_commission': round(avg_commission, 2),
                'percentage': round(percentage, 2)
            })
        
        return sorted(result, key=lambda x: x['total_commission'], reverse=True)
    
    def _generate_top_agents(self, transactions, limit=10):
        """Generate top agents ranking"""
        agents_data = {}
        
        for t in transactions:
            agent_id = t.agent_id
            if not agent_id:
                continue
            
            if agent_id not in agents_data:
                agent = AgentCompany.query.get(agent_id)
                agents_data[agent_id] = {
                    'id': agent_id,
                    'name': agent.company_name if agent else f'Agent {agent_id}',
                    'code': agent.short_code if agent else str(agent_id),
                    'count': 0,
                    'total_commission': 0
                }
            
            agents_data[agent_id]['count'] += 1
            agents_data[agent_id]['total_commission'] += float(t.commission_amount or 0)
        
        # Format and sort agents
        agents = []
        for agent_data in sorted(agents_data.values(), 
                                key=lambda x: x['total_commission'], 
                                reverse=True)[:limit]:
            avg_commission = agent_data['total_commission'] / agent_data['count'] if agent_data['count'] > 0 else 0
            
            agents.append({
                'id': agent_data['id'],
                'name': agent_data['name'],
                'code': agent_data['code'],
                'transaction_count': agent_data['count'],
                'total_commission': round(agent_data['total_commission'], 2),
                'average_commission': round(avg_commission, 2)
            })
        
        return agents
    
    def _generate_trends(self, transactions, start_date, end_date):
        """Generate commission trends over time"""
        trends = []
        
        # Group by month
        current = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end_date:
            next_month = (current.replace(day=28) + timedelta(days=4)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            
            # Get transactions for this month
            month_transactions = [
                t for t in transactions 
                if current <= t.initiation_time < next_month
            ]
            
            month_total = sum(float(t.commission_amount or 0) for t in month_transactions)
            days_in_month = (next_month - current).days
            
            trends.append({
                'period': current.strftime('%b %Y'),
                'transaction_count': len(month_transactions),
                'total_commission': round(month_total, 2),
                'growth': 0,  # Will be calculated below
                'average_daily': round(month_total / days_in_month, 2) if month_total > 0 else 0
            })
            
            current = next_month
        
        # Calculate growth percentages
        for i in range(1, len(trends)):
            prev_total = trends[i-1]['total_commission']
            current_total = trends[i]['total_commission']
            
            if prev_total > 0:
                growth = ((current_total - prev_total) / prev_total * 100)
            else:
                growth = 100 if current_total > 0 else 0
            
            trends[i]['growth'] = round(growth, 2)
        
        return trends
    
    def _get_previous_period_data(self, company_id, start_date, end_date):
        """Get data for previous period for comparison"""
        period_days = (end_date - start_date).days
        
        previous_start = start_date - timedelta(days=period_days)
        previous_end = start_date - timedelta(days=1)
        
        previous_transactions = Transaction.query.filter(
            Transaction.transaction_type == 'commission',
            Transaction.company_id == company_id,
            Transaction.initiation_time >= previous_start,
            Transaction.initiation_time <= previous_end
        ).all()
        
        total_commission = sum(float(t.commission_amount or 0) for t in previous_transactions)
        
        return {
            'total_transactions': len(previous_transactions),
            'total_commission': total_commission
        }
    
    def _get_empty_report(self, start_date, end_date):
        """Return empty report structure"""
        return {
            'period': f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}",
            'summary': {
                'total_transactions': 0,
                'total_commission': 0,
                'average_commission': 0,
                'top_agent_commission': 0,
                'top_agent_name': 'N/A',
                'growth_percentage': 0
            },
            'categories': [],
            'top_agents': [],
            'trends': []
        }