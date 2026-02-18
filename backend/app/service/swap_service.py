from app import db
from app.model.agent_swap import AgentSwap
from app.model.agentcompany import AgentCompany
from app.model.agent_accounts import AgentAccount
from app.model.agent_account_balances import AgentAccountBalance
from app.model.useragent import UserAgent, user_agent_companies
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func


class SwapService:

    def _get_balance_for_account_type(self, agent_company_id, account_type):
        accounts = AgentAccount.query.filter_by(
            agent_company_id=agent_company_id
        ).all()

        # Match using case-insensitive contains, same as frontend
        account = None
        for acc in accounts:
            if acc.account_type and account_type.lower() in acc.account_type.lower():
                account = acc
                break

        if not account:
            return Decimal('0.00')

        latest = (
            AgentAccountBalance.query
            .filter_by(agent_account_id=account.id)
            .order_by(AgentAccountBalance.snapshot_at.desc())
            .first()
        )
        if latest and latest.current_balance is not None:
            return latest.current_balance
        return Decimal('0.00')

    def _serialize_agents(self, user_agents):
        return [
            {
                'id': ua.id,
                'name': f"{ua.firstname} {ua.lastname}",
                'idnumber': ua.idnumber,
                'phone_number': ua.phone_number
            }
            for ua in user_agents
        ]

    def initiate_swap(self, agent_company_id, new_agent_ids, notes, user_id):
        try:
            agent_company = AgentCompany.query.get(agent_company_id)
            if not agent_company:
                return None, "Agent company not found"

            # Snapshot current balances
            float_balance = self._get_balance_for_account_type(agent_company_id, 'FLOAT')
            commission_balance = self._get_balance_for_account_type(agent_company_id, 'COMMISSION')

            # Snapshot current agents
            current_agents = list(agent_company.user_agents)
            previous_agents_data = self._serialize_agents(current_agents)

            # Validate new agents exist
            new_agents = UserAgent.query.filter(UserAgent.id.in_(new_agent_ids)).all()
            if len(new_agents) != len(new_agent_ids):
                return None, "One or more new agent IDs are invalid"
            new_agents_data = self._serialize_agents(new_agents)

            # Create swap record
            swap = AgentSwap(
                agent_company_id=agent_company_id,
                initiated_by=user_id,
                swap_date=datetime.utcnow(),
                float_balance_at_swap=float_balance,
                commission_balance_at_swap=commission_balance,
                previous_agents=previous_agents_data,
                new_agents=new_agents_data,
                notes=notes,
                status='completed'
            )
            db.session.add(swap)

            # Update the many-to-many: remove old agents, add new ones
            # Clear existing associations
            db.session.execute(
                user_agent_companies.delete().where(
                    user_agent_companies.c.agent_company_id == agent_company_id
                )
            )
            # Add new associations
            for agent in new_agents:
                db.session.execute(
                    user_agent_companies.insert().values(
                        user_agent_id=agent.id,
                        agent_company_id=agent_company_id,
                        created_at=datetime.utcnow()
                    )
                )

            db.session.commit()
            return swap.to_dict(), None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    def revert_swap(self, swap_id, user_id):
        try:
            original_swap = AgentSwap.query.get(swap_id)
            if not original_swap:
                return None, "Swap not found"

            agent_company_id = original_swap.agent_company_id
            agent_company = AgentCompany.query.get(agent_company_id)
            if not agent_company:
                return None, "Agent company not found"

            # Restore previous agents on the company
            previous_agent_ids = [a['id'] for a in (original_swap.previous_agents or [])]
            previous_agents = UserAgent.query.filter(UserAgent.id.in_(previous_agent_ids)).all() if previous_agent_ids else []

            db.session.execute(
                user_agent_companies.delete().where(
                    user_agent_companies.c.agent_company_id == agent_company_id
                )
            )
            for agent in previous_agents:
                db.session.execute(
                    user_agent_companies.insert().values(
                        user_agent_id=agent.id,
                        agent_company_id=agent_company_id,
                        created_at=datetime.utcnow()
                    )
                )

            # Delete the swap record
            db.session.delete(original_swap)

            db.session.commit()
            return {'message': 'Swap reverted and deleted'}, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    def get_swaps_by_company(self, agent_company_id):
        try:
            swaps = (
                AgentSwap.query
                .filter_by(agent_company_id=agent_company_id)
                .order_by(AgentSwap.swap_date.desc())
                .all()
            )
            return [s.to_dict() for s in swaps], None
        except Exception as e:
            return None, str(e)

    def get_all_swaps(self, user_id, filters=None):
        try:
            filters = filters or {}

            # Get agent companies belonging to this user
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]

            if not company_ids:
                return [], None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))

            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                query = query.filter(AgentSwap.swap_date >= datetime.fromisoformat(filters['start_date']))
            if filters.get('end_date'):
                query = query.filter(AgentSwap.swap_date <= datetime.fromisoformat(filters['end_date']))

            swaps = query.order_by(AgentSwap.swap_date.desc()).all()
            return [s.to_dict() for s in swaps], None

        except Exception as e:
            return None, str(e)

    def get_swaps_grouped_by_company(self, user_id, filters=None):
        try:
            filters = filters or {}
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]

            if not company_ids:
                return [], None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))

            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                query = query.filter(AgentSwap.swap_date >= datetime.fromisoformat(filters['start_date']))
            if filters.get('end_date'):
                query = query.filter(AgentSwap.swap_date <= datetime.fromisoformat(filters['end_date']))

            swaps = query.order_by(AgentSwap.agent_company_id, AgentSwap.swap_date.desc()).all()

            # Group by company
            grouped = {}
            for swap in swaps:
                cid = swap.agent_company_id
                if cid not in grouped:
                    grouped[cid] = {
                        'agent_company_id': cid,
                        'agent_company_name': swap.agent_company.company_name if swap.agent_company else None,
                        'till_number': swap.agent_company.till_number if swap.agent_company else None,
                        'total_swaps': 0,
                        'swaps': []
                    }
                grouped[cid]['total_swaps'] += 1
                grouped[cid]['swaps'].append(swap.to_dict())

            return list(grouped.values()), None

        except Exception as e:
            return None, str(e)

    def generate_swap_report(self, user_id, filters=None):
        try:
            filters = filters or {}
            user_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            company_ids = [c.id for c in user_companies]

            if not company_ids:
                return {'summary': {}, 'companies': []}, None

            query = AgentSwap.query.filter(AgentSwap.agent_company_id.in_(company_ids))

            if filters.get('agent_company_id'):
                query = query.filter_by(agent_company_id=int(filters['agent_company_id']))
            if filters.get('start_date'):
                start = datetime.fromisoformat(filters['start_date'])
                query = query.filter(AgentSwap.swap_date >= start)
            if filters.get('end_date'):
                end = datetime.fromisoformat(filters['end_date'])
                query = query.filter(AgentSwap.swap_date <= end)

            swaps = query.order_by(AgentSwap.swap_date.desc()).all()

            if not swaps:
                return {
                    'period': {
                        'start_date': filters.get('start_date'),
                        'end_date': filters.get('end_date')
                    },
                    'summary': {
                        'total_swaps': 0,
                        'companies_involved': 0,
                        'avg_float_at_swap': '0.00',
                        'avg_commission_at_swap': '0.00',
                        'total_float_at_swaps': '0.00',
                        'total_commission_at_swaps': '0.00',
                    },
                    'companies': []
                }, None

            total_float = sum(s.float_balance_at_swap or Decimal('0') for s in swaps)
            total_commission = sum(s.commission_balance_at_swap or Decimal('0') for s in swaps)
            total_swaps = len(swaps)
            unique_companies = len(set(s.agent_company_id for s in swaps))

            # Per-company breakdown
            company_stats = {}
            for swap in swaps:
                cid = swap.agent_company_id
                if cid not in company_stats:
                    company_stats[cid] = {
                        'agent_company_id': cid,
                        'company_name': swap.agent_company.company_name if swap.agent_company else None,
                        'till_number': swap.agent_company.till_number if swap.agent_company else None,
                        'swap_count': 0,
                        'total_float': Decimal('0'),
                        'total_commission': Decimal('0'),
                        'first_swap': swap.swap_date,
                        'last_swap': swap.swap_date,
                    }
                cs = company_stats[cid]
                cs['swap_count'] += 1
                cs['total_float'] += swap.float_balance_at_swap or Decimal('0')
                cs['total_commission'] += swap.commission_balance_at_swap or Decimal('0')
                if swap.swap_date < cs['first_swap']:
                    cs['first_swap'] = swap.swap_date
                if swap.swap_date > cs['last_swap']:
                    cs['last_swap'] = swap.swap_date

            companies_list = []
            for cs in company_stats.values():
                companies_list.append({
                    'agent_company_id': cs['agent_company_id'],
                    'company_name': cs['company_name'],
                    'till_number': cs['till_number'],
                    'swap_count': cs['swap_count'],
                    'avg_float_at_swap': str(round(cs['total_float'] / cs['swap_count'], 2)),
                    'avg_commission_at_swap': str(round(cs['total_commission'] / cs['swap_count'], 2)),
                    'total_float_at_swaps': str(cs['total_float']),
                    'total_commission_at_swaps': str(cs['total_commission']),
                    'first_swap': cs['first_swap'].isoformat() if cs['first_swap'] else None,
                    'last_swap': cs['last_swap'].isoformat() if cs['last_swap'] else None,
                })

            report = {
                'period': {
                    'start_date': filters.get('start_date'),
                    'end_date': filters.get('end_date')
                },
                'summary': {
                    'total_swaps': total_swaps,
                    'companies_involved': unique_companies,
                    'avg_float_at_swap': str(round(total_float / total_swaps, 2)),
                    'avg_commission_at_swap': str(round(total_commission / total_swaps, 2)),
                    'total_float_at_swaps': str(total_float),
                    'total_commission_at_swaps': str(total_commission),
                },
                'companies': companies_list
            }

            return report, None

        except Exception as e:
            return None, str(e)

    def export_swap_report(self, user_id, filters=None, format='csv'):
        import io
        import csv

        report, error = self.generate_swap_report(user_id, filters)
        if error:
            return None, error

        swaps_data, _ = self.get_all_swaps(user_id, filters)
        if not swaps_data:
            swaps_data = []

        if format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'Swap ID', 'Company Name', 'Swap Date',
                'Float Balance at Swap', 'Commission Balance at Swap',
                'Previous Agents', 'New Agents',
                'Initiated By', 'Notes', 'Status'
            ])
            for swap in swaps_data:
                prev_names = ', '.join(a.get('name', '') for a in (swap.get('previous_agents') or []))
                new_names = ', '.join(a.get('name', '') for a in (swap.get('new_agents') or []))
                writer.writerow([
                    swap['id'],
                    swap.get('agent_company_name', ''),
                    swap.get('swap_date', ''),
                    swap.get('float_balance_at_swap', '0.00'),
                    swap.get('commission_balance_at_swap', '0.00'),
                    prev_names,
                    new_names,
                    swap.get('initiator_name', ''),
                    swap.get('notes', ''),
                    swap.get('status', ''),
                ])
            return output.getvalue(), None

        return None, f"Unsupported format: {format}"
