"""
Float Health Report Service

Per-till float balance health over a chosen period (weekly, monthly,
quarterly, semi-annual, yearly, or a custom date range), scoped to the
companies tied to the logged-in user. Shows opening/closing float balance,
the lowest balance seen in the period, deposits/withdrawals, and the user
agent(s) assigned to each till.
"""

import calendar
from datetime import datetime, date
from sqlalchemy import func, and_
from app import db
from app.model.agentcompany import AgentCompany
from app.model.agent_accounts import AgentAccount
from app.model.agent_account_balances import AgentAccountBalance
from app.model.transaction import Transaction
from flask import current_app


class FloatHealthReportService:

    # ──────────────────────────────────────────────
    # Period helpers
    # ──────────────────────────────────────────────

    def _parse_period(self, period_type, year=None, month=None, quarter=None,
                       half=None, week=None, start_date=None, end_date=None):
        today = date.today()
        year = year or today.year

        if period_type == 'custom':
            if not start_date or not end_date:
                raise ValueError('start_date and end_date are required for a custom range')
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            label = f"{start.strftime('%d %b %Y')} — {end.strftime('%d %b %Y')}"

        elif period_type == 'weekly':
            week = week or today.isocalendar()[1]
            start = date.fromisocalendar(year, week, 1)
            end = date.fromisocalendar(year, week, 7)
            label = f"Week {week}, {year} ({start.strftime('%d %b')} – {end.strftime('%d %b %Y')})"

        elif period_type == 'monthly':
            month = month or today.month
            if not (1 <= month <= 12):
                raise ValueError('month must be 1–12')
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            label = start.strftime('%B %Y')

        elif period_type == 'quarterly':
            quarter = quarter or ((today.month - 1) // 3 + 1)
            if not (1 <= quarter <= 4):
                raise ValueError('quarter must be 1–4')
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            start = date(year, start_month, 1)
            end = date(year, end_month, calendar.monthrange(year, end_month)[1])
            label = f"Q{quarter} {year}"

        elif period_type == 'semi_annual':
            half = half or (1 if today.month <= 6 else 2)
            if half not in (1, 2):
                raise ValueError('half must be 1 or 2')
            if half == 1:
                start, end = date(year, 1, 1), date(year, 6, 30)
                label = f"H1 {year}"
            else:
                start, end = date(year, 7, 1), date(year, 12, 31)
                label = f"H2 {year}"

        elif period_type == 'yearly':
            start = date(year, 1, 1)
            end = date(year, 12, 31)
            label = str(year)

        else:
            raise ValueError(f"Unknown period_type: {period_type}")

        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        return start_dt, end_dt, start, end, label

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _get_agent_companies(self, company_id=None, company_ids=None):
        q = AgentCompany.query
        if company_id:
            q = q.filter(AgentCompany.company_id == company_id)
        elif company_ids is not None:
            q = q.filter(AgentCompany.company_id.in_(company_ids))
        return q.all()

    def _float_metrics_map(self, agent_company_ids, start_dt, end_dt):
        """
        Per agent_company_id, using its FLOAT account's balance snapshots:
          - opening_balance: latest snapshot at/before the period start
          - closing_balance: latest snapshot at/before the period end
          - min/max_balance: extremes seen strictly within the period window
        """
        if not agent_company_ids:
            return {}

        accounts = (
            AgentAccount.query
            .filter(AgentAccount.agent_company_id.in_(agent_company_ids))
            .filter(AgentAccount.account_type.ilike('%float%'))
            .all()
        )
        if not accounts:
            return {}

        account_ids = [a.id for a in accounts]
        acc_to_company = {a.id: a.agent_company_id for a in accounts}

        def _latest_at_or_before(cutoff_dt):
            rows = (
                db.session.query(
                    AgentAccountBalance.agent_account_id,
                    AgentAccountBalance.current_balance,
                )
                .filter(
                    AgentAccountBalance.agent_account_id.in_(account_ids),
                    AgentAccountBalance.snapshot_at <= cutoff_dt,
                )
                .order_by(AgentAccountBalance.agent_account_id, AgentAccountBalance.snapshot_at.desc())
                .all()
            )
            latest = {}
            for acc_id, balance in rows:
                if acc_id not in latest:
                    latest[acc_id] = float(balance or 0)
            return latest

        opening_map = _latest_at_or_before(start_dt)
        closing_map = _latest_at_or_before(end_dt)

        minmax_rows = (
            db.session.query(
                AgentAccountBalance.agent_account_id,
                func.min(AgentAccountBalance.current_balance).label('min_bal'),
                func.max(AgentAccountBalance.current_balance).label('max_bal'),
                func.count(AgentAccountBalance.id).label('snapshot_count'),
            )
            .filter(
                AgentAccountBalance.agent_account_id.in_(account_ids),
                AgentAccountBalance.snapshot_at >= start_dt,
                AgentAccountBalance.snapshot_at <= end_dt,
            )
            .group_by(AgentAccountBalance.agent_account_id)
            .all()
        )
        minmax_map = {r.agent_account_id: (float(r.min_bal or 0), float(r.max_bal or 0), r.snapshot_count) for r in minmax_rows}

        result = {}
        for acc_id in account_ids:
            company_id = acc_to_company[acc_id]
            opening = opening_map.get(acc_id)
            closing = closing_map.get(acc_id, opening)
            has_data = opening is not None or closing is not None
            min_bal, max_bal, snap_count = minmax_map.get(acc_id, (None, None, 0))
            if snap_count == 0:
                bounds = [b for b in (opening, closing) if b is not None]
                min_bal = min(bounds) if bounds else 0
                max_bal = max(bounds) if bounds else 0

            result[company_id] = {
                'opening_balance': opening if opening is not None else 0.0,
                'closing_balance': closing if closing is not None else 0.0,
                'min_balance': min_bal,
                'max_balance': max_bal,
                'has_data': has_data,
            }
        return result

    def _deposit_withdrawal_map(self, start_dt, end_dt):
        """Sum paid_in and (absolute) withdrawn per business_shortcode in the period."""
        rows = (
            db.session.query(
                Transaction.business_shortcode,
                func.coalesce(func.sum(Transaction.paid_in), 0).label('deposits'),
                func.coalesce(func.sum(func.abs(Transaction.withdrawn)), 0).label('withdrawals'),
                func.count(Transaction.id).label('tx_count'),
            )
            .filter(
                Transaction.completion_time >= start_dt,
                Transaction.completion_time <= end_dt,
                Transaction.transaction_type == 'float',
            )
            .group_by(Transaction.business_shortcode)
            .all()
        )
        return {
            sc: {'deposits': float(deps), 'withdrawals': float(wdrs), 'tx_count': cnt}
            for sc, deps, wdrs, cnt in rows if sc
        }

    @staticmethod
    def _user_agents_for(ac, limit=5):
        try:
            agents = ac.user_agents.all() if hasattr(ac.user_agents, 'all') else list(ac.user_agents)
            return [
                {
                    'id': ua.id,
                    'name': f"{ua.firstname} {ua.lastname}",
                    'phone_number': ua.phone_number,
                    'operator_role': ua.operator_role,
                    'is_authentic': ua.is_authentic,
                }
                for ua in agents[:limit]
            ]
        except Exception:
            return []

    # ──────────────────────────────────────────────
    # Per-till metrics
    # ──────────────────────────────────────────────

    def _till_metrics(self, start_dt, end_dt, company_id, company_ids,
                       low_float_threshold, critical_float_threshold):
        agent_companies = self._get_agent_companies(company_id, company_ids)
        if not agent_companies:
            return []

        float_map = self._float_metrics_map([ac.id for ac in agent_companies], start_dt, end_dt)
        dw_map = self._deposit_withdrawal_map(start_dt, end_dt)

        tills = []
        for ac in agent_companies:
            sc = ac.short_code or ''
            fm = float_map.get(ac.id, {
                'opening_balance': 0.0, 'closing_balance': 0.0,
                'min_balance': 0.0, 'max_balance': 0.0, 'has_data': False,
            })
            dw = dw_map.get(sc, {'deposits': 0.0, 'withdrawals': 0.0, 'tx_count': 0})

            if not fm['has_data']:
                health_status = 'no_data'
            elif fm['min_balance'] < critical_float_threshold:
                health_status = 'critical'
            elif fm['min_balance'] < low_float_threshold:
                health_status = 'low'
            else:
                health_status = 'healthy'

            tills.append({
                'agent_company_id': ac.id,
                'company_name': ac.company_name,
                'store_number': ac.store_number,
                'short_code': sc,
                'location': ac.location or '—',
                'opening_balance': fm['opening_balance'],
                'closing_balance': fm['closing_balance'],
                'min_balance': fm['min_balance'],
                'max_balance': fm['max_balance'],
                'net_change': fm['closing_balance'] - fm['opening_balance'],
                'deposits': dw['deposits'],
                'withdrawals': dw['withdrawals'],
                'tx_count': dw['tx_count'],
                'health_status': health_status,
                'user_agents': self._user_agents_for(ac),
            })

        tills.sort(key=lambda t: t['closing_balance'])
        return tills

    # ──────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────

    def generate_report(self, period_type='monthly', year=None, month=None, quarter=None,
                         half=None, week=None, start_date=None, end_date=None,
                         company_id=None, company_ids=None,
                         low_float_threshold=20000.0, critical_float_threshold=5000.0):
        try:
            start_dt, end_dt, start_d, end_d, label = self._parse_period(
                period_type, year=year, month=month, quarter=quarter,
                half=half, week=week, start_date=start_date, end_date=end_date,
            )
        except ValueError:
            raise
        except Exception as e:
            current_app.logger.error(f"[FloatHealthReport] period parse error: {e}")
            raise ValueError('Invalid period parameters')

        tills = self._till_metrics(
            start_dt, end_dt, company_id, company_ids, low_float_threshold, critical_float_threshold
        )

        total_opening = sum(t['opening_balance'] for t in tills)
        total_closing = sum(t['closing_balance'] for t in tills)
        total_deposits = sum(t['deposits'] for t in tills)
        total_withdrawals = sum(t['withdrawals'] for t in tills)

        return {
            'period_type': period_type,
            'label': label,
            'start_date': start_d.isoformat(),
            'end_date': end_d.isoformat(),
            'thresholds': {'low': low_float_threshold, 'critical': critical_float_threshold},
            'summary': {
                'till_count': len(tills),
                'total_opening_float': total_opening,
                'total_closing_float': total_closing,
                'net_change': total_closing - total_opening,
                'total_deposits': total_deposits,
                'total_withdrawals': total_withdrawals,
                'avg_float_per_till': (total_closing / len(tills)) if tills else 0.0,
                'healthy_count': sum(1 for t in tills if t['health_status'] == 'healthy'),
                'low_count': sum(1 for t in tills if t['health_status'] == 'low'),
                'critical_count': sum(1 for t in tills if t['health_status'] == 'critical'),
                'no_data_count': sum(1 for t in tills if t['health_status'] == 'no_data'),
            },
            'tills': tills,
        }
