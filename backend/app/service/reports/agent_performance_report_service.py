"""
Agent Performance Report Service
Sections:
  1. Top commission earners over the period
  2. Agents with float or commission below user-defined thresholds
  3. Fraud-flagged agents – three categories (split_transaction,
     high_frequency_daily, rapid_back_forth), up to 5 transactions each
"""

from datetime import datetime, date, timedelta
from sqlalchemy import func, desc, and_
from app import db
from app.model.agentcompany import AgentCompany
from app.model.useragent import UserAgent
from app.model.transaction import Transaction
from app.model.agent_accounts import AgentAccount
from app.model.agent_account_balances import AgentAccountBalance
from flask import current_app


FRAUD_CATEGORIES = ['split_transaction', 'high_frequency_daily', 'rapid_back_forth']

FRAUD_CATEGORY_LABELS = {
    'split_transaction':    'Split Transaction',
    'high_frequency_daily': 'High Frequency Daily',
    'rapid_back_forth':     'Rapid Back & Forth',
}


class AgentPerformanceReportService:

    # ──────────────────────────────────────────────
    # Date helpers
    # ──────────────────────────────────────────────

    def _parse_dates(self, start_date, end_date, date_range):
        today = date.today()
        if date_range and date_range != 'custom':
            if date_range == 'today':
                start = end = today
            elif date_range == 'yesterday':
                start = end = today - timedelta(days=1)
            elif date_range == 'this_week':
                start = today - timedelta(days=today.weekday())
                end = today
            elif date_range == 'last_week':
                start = today - timedelta(days=today.weekday() + 7)
                end = start + timedelta(days=6)
            elif date_range == 'this_month':
                start = today.replace(day=1)
                end = today
            elif date_range == 'last_month':
                first_of_this = today.replace(day=1)
                end = first_of_this - timedelta(days=1)
                start = end.replace(day=1)
            elif date_range == 'last_3_months':
                start = today - timedelta(days=90)
                end = today
            elif date_range == 'last_6_months':
                start = today - timedelta(days=180)
                end = today
            elif date_range == 'this_year':
                start = today.replace(month=1, day=1)
                end = today
            else:
                start = end = today
        else:
            if not start_date or not end_date:
                raise ValueError('start_date and end_date are required for custom range')
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()

        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        return start_dt, end_dt, start, end

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def _get_agent_companies(self, company_id=None):
        q = AgentCompany.query
        if company_id:
            q = q.filter(AgentCompany.company_id == company_id)
        return q.all()

    def _float_balance_map(self):
        """
        Return {agent_company_id: float_balance} using the latest AgentAccountBalance
        snapshot for each FLOAT account — same logic as SwapService.
        """
        try:
            # Latest snapshot per account
            latest_subq = (
                db.session.query(
                    AgentAccountBalance.agent_account_id,
                    func.max(AgentAccountBalance.snapshot_at).label('latest'),
                )
                .group_by(AgentAccountBalance.agent_account_id)
                .subquery()
            )
            rows = (
                db.session.query(
                    AgentAccount.agent_company_id,
                    AgentAccountBalance.current_balance,
                )
                .join(
                    latest_subq,
                    and_(
                        AgentAccountBalance.agent_account_id == latest_subq.c.agent_account_id,
                        AgentAccountBalance.snapshot_at == latest_subq.c.latest,
                    ),
                )
                .join(AgentAccount, AgentAccount.id == AgentAccountBalance.agent_account_id)
                .filter(AgentAccount.account_type.ilike('%float%'))
                .all()
            )
            return {ac_id: float(bal or 0) for ac_id, bal in rows}
        except Exception as e:
            current_app.logger.error(f"[AgentPerfReport] float_balance_map error: {e}")
            return {}

    def _commission_map(self, start_dt, end_dt):
        """
        Sum commission earned per business_shortcode within the date range.
        Excludes COMM-% synthetic snapshot records (child shortcode rollups).
        """
        rows = (
            db.session.query(
                Transaction.business_shortcode,
                func.coalesce(func.sum(func.abs(Transaction.withdrawn)), 0).label('total'),
            )
            .filter(
                Transaction.transaction_type == 'commission',
                Transaction.receipt_no.notlike('COMM-%'),
                Transaction.completion_time >= start_dt,
                Transaction.completion_time <= end_dt,
            )
            .group_by(Transaction.business_shortcode)
            .all()
        )
        return {sc: float(total) for sc, total in rows if sc}

    def _deposit_withdrawal_map(self, start_dt, end_dt):
        """Sum paid_in and withdrawn per business_shortcode in the period."""
        rows = (
            db.session.query(
                Transaction.business_shortcode,
                func.coalesce(func.sum(Transaction.paid_in), 0).label('deposits'),
                func.coalesce(func.sum(Transaction.withdrawn), 0).label('withdrawals'),
                func.count(Transaction.id).label('tx_count'),
            )
            .filter(
                Transaction.completion_time >= start_dt,
                Transaction.completion_time <= end_dt,
            )
            .group_by(Transaction.business_shortcode)
            .all()
        )
        return {
            sc: {
                'deposits': float(deps),
                'withdrawals': float(wdrs),
                'tx_count': cnt,
            }
            for sc, deps, wdrs, cnt in rows if sc
        }

    @staticmethod
    def _user_agents_for(ac, limit=3):
        try:
            agents = ac.user_agents.all() if hasattr(ac.user_agents, 'all') else list(ac.user_agents)
            return [
                {
                    'id': ua.id,
                    'name': f"{ua.firstname} {ua.lastname}",
                    'phone_number': ua.phone_number,
                    'is_authentic': ua.is_authentic,
                }
                for ua in agents[:limit]
            ]
        except Exception:
            return []

    # ──────────────────────────────────────────────
    # Section 1 – Top commission earners
    # ──────────────────────────────────────────────

    def _top_commission_earners(self, start_dt, end_dt, company_id, limit=10):
        try:
            agent_companies = self._get_agent_companies(company_id)
            comm_map = self._commission_map(start_dt, end_dt)
            dw_map = self._deposit_withdrawal_map(start_dt, end_dt)
            float_map = self._float_balance_map()

            earners = []
            for ac in agent_companies:
                sc = ac.short_code or ''
                commission = comm_map.get(sc, 0.0)
                dw = dw_map.get(sc, {'deposits': 0.0, 'withdrawals': 0.0, 'tx_count': 0})
                earners.append({
                    'agent_company_id': ac.id,
                    'company_name': ac.company_name,
                    'store_number': ac.store_number,
                    'short_code': sc,
                    'location': ac.location,
                    'total_commission': commission,
                    'commission_rate': float(ac.commission_rate or 0),
                    'tx_count': dw['tx_count'],
                    'total_deposits': dw['deposits'],
                    'total_withdrawals': dw['withdrawals'],
                    'current_float_balance': float_map.get(ac.id, 0.0),
                    'user_agents': self._user_agents_for(ac),
                })

            earners.sort(key=lambda x: x['total_commission'], reverse=True)
            return earners[:limit]
        except Exception as e:
            current_app.logger.error(f"[AgentPerfReport] top earners error: {e}")
            return []

    # ──────────────────────────────────────────────
    # Section 2 – Below-threshold agents
    # ──────────────────────────────────────────────

    def _below_threshold_agents(self, start_dt, end_dt, company_id,
                                 commission_threshold, float_threshold):
        try:
            agent_companies = self._get_agent_companies(company_id)
            comm_map = self._commission_map(start_dt, end_dt)
            float_map = self._float_balance_map()

            result = []
            for ac in agent_companies:
                sc = ac.short_code or ''
                float_bal = float_map.get(ac.id, 0.0)
                commission = comm_map.get(sc, 0.0)

                below_float = float_bal < float_threshold
                below_commission = commission < commission_threshold

                if not (below_float or below_commission):
                    continue

                reasons = []
                if below_float:
                    reasons.append(
                        f"Float KES {float_bal:,.2f} is below threshold KES {float_threshold:,.2f}"
                    )
                if below_commission:
                    reasons.append(
                        f"Commission KES {commission:,.2f} is below threshold KES {commission_threshold:,.2f}"
                    )

                result.append({
                    'agent_company_id': ac.id,
                    'company_name': ac.company_name,
                    'store_number': ac.store_number,
                    'short_code': sc,
                    'location': ac.location or '—',
                    'float_balance': float_bal,
                    'period_commission': commission,
                    'commission_rate': float(ac.commission_rate or 0),
                    'status': ac.status or 'unknown',
                    'below_float': below_float,
                    'below_commission': below_commission,
                    'reasons': reasons,
                    'user_agents': self._user_agents_for(ac),
                })

            # Sort: worst float first
            result.sort(key=lambda x: x['float_balance'])
            return result
        except Exception as e:
            current_app.logger.error(f"[AgentPerfReport] below threshold error: {e}")
            return []

    # ──────────────────────────────────────────────
    # Section 3 – Fraud-flagged (3 categories, ≤5 txns each)
    # ──────────────────────────────────────────────

    def _fraud_flagged_agents(self, start_dt, end_dt, company_id,
                               max_per_category=5, max_findings_per_cat=20):
        """
        Reuse FraudReportService and filter to our three categories.
        """
        try:
            from app.service.reports.fraud_report_service import FraudReportService
            svc = FraudReportService()
            fraud_report = svc.generate_report(
                start_date=start_dt.strftime('%Y-%m-%d'),
                end_date=end_dt.strftime('%Y-%m-%d'),
                date_range='custom',
                company_id=company_id,
            )
            all_findings = fraud_report.get('findings', [])

            categorized = {cat: [] for cat in FRAUD_CATEGORIES}
            for finding in all_findings:
                cat = finding.get('fraud_type')
                if cat not in categorized:
                    continue
                if len(categorized[cat]) >= max_findings_per_cat:
                    continue
                f = dict(finding)
                f['transaction_details'] = finding.get('transaction_details', [])[:max_per_category]
                categorized[cat].append(f)

            summary = {cat: len(categorized[cat]) for cat in FRAUD_CATEGORIES}

            return {
                'categories': categorized,
                'summary': summary,
                'total_flagged': sum(summary.values()),
            }
        except Exception as e:
            current_app.logger.error(f"[AgentPerfReport] fraud flagged error: {e}")
            return {
                'categories': {cat: [] for cat in FRAUD_CATEGORIES},
                'summary': {cat: 0 for cat in FRAUD_CATEGORIES},
                'total_flagged': 0,
            }

    # ──────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────

    def generate_report(self, start_date, end_date, date_range,
                        company_id=None,
                        commission_threshold=5000.0,
                        float_threshold=50000.0):
        start_dt, end_dt, start_d, end_d = self._parse_dates(start_date, end_date, date_range)

        top_earners = self._top_commission_earners(start_dt, end_dt, company_id)
        below_threshold = self._below_threshold_agents(
            start_dt, end_dt, company_id, commission_threshold, float_threshold
        )
        fraud_flagged = self._fraud_flagged_agents(start_dt, end_dt, company_id)

        return {
            'period': f"{start_d.strftime('%d %b %Y')} — {end_d.strftime('%d %b %Y')}",
            'thresholds': {
                'commission': commission_threshold,
                'float': float_threshold,
            },
            'summary': {
                'top_earners_count': len(top_earners),
                'below_threshold_count': len(below_threshold),
                'fraud_flagged_count': fraud_flagged['total_flagged'],
                'split_transaction_count': fraud_flagged['summary'].get('split_transaction', 0),
                'high_frequency_daily_count': fraud_flagged['summary'].get('high_frequency_daily', 0),
                'rapid_back_forth_count': fraud_flagged['summary'].get('rapid_back_forth', 0),
            },
            'top_earners': top_earners,
            'below_threshold': below_threshold,
            'fraud_flagged': fraud_flagged,
        }
