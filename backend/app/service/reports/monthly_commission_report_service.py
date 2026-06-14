"""
Monthly Commission Rollup Report Service

Shows the 'Aggregator Commission roll-up to Commission Held Account' rows
grouped by month, one row per till (business_shortcode), with MoM comparison.
"""

from datetime import datetime
from sqlalchemy import text
from app import db
from app.model.agentcompany import AgentCompany


class MonthlyCommissionReportService:

    ROLLUP_WHERE = """
        transaction_type = 'commission'
        AND receipt_no NOT LIKE 'COMM-%%'
        AND reason_type ILIKE '%%roll%%'
    """

    def _available_months(self, company_shortcodes=None):
        """Return list of {month, year, label, total} for months that have rollup data."""
        sc_filter = ""
        params = {}
        if company_shortcodes:
            sc_filter = "AND business_shortcode = ANY(:shortcodes)"
            params["shortcodes"] = list(company_shortcodes)

        rows = db.session.execute(text(f"""
            SELECT
                EXTRACT(YEAR  FROM completion_time)::int AS year,
                EXTRACT(MONTH FROM completion_time)::int AS month,
                COUNT(*)                                  AS till_count,
                SUM(ABS(withdrawn))                       AS total_amount
            FROM transactions
            WHERE {self.ROLLUP_WHERE}
            {sc_filter}
            GROUP BY 1, 2
            ORDER BY 1 DESC, 2 DESC
        """), params).fetchall()

        # Rollup transactions land on the 1st of month+1, so shift back by 1 month
        # to present the commission month (the month the commission was earned in).
        months = []
        for r in rows:
            comm_year, comm_month = self._prev_month(r.year, r.month)
            dt = datetime(comm_year, comm_month, 1)
            months.append({
                "year": comm_year,
                "month": comm_month,
                "label": dt.strftime("%B %Y"),
                "till_count": r.till_count,
                "total_amount": float(r.total_amount or 0),
            })
        return months

    def _next_month(self, year, month):
        if month == 12:
            return year + 1, 1
        return year, month + 1

    def _rollups_for_month(self, year, month, company_shortcodes=None):
        """Return per-till rollup rows for commission_month (year, month).

        Rollup transactions are posted on the 1st of month+1, so we query
        the next calendar month's transactions.
        """
        rollup_year, rollup_month = self._next_month(year, month)
        sc_filter = ""
        params = {"year": rollup_year, "month": rollup_month}
        if company_shortcodes:
            sc_filter = "AND t.business_shortcode = ANY(:shortcodes)"
            params["shortcodes"] = list(company_shortcodes)

        rows = db.session.execute(text(f"""
            SELECT
                t.receipt_no,
                t.business_shortcode,
                t.details,
                ABS(t.withdrawn)        AS amount,
                t.completion_time,
                ac.company_name,
                ac.location,
                ac.store_number
            FROM transactions t
            LEFT JOIN agentcompanies ac
                   ON ac.short_code = t.business_shortcode
            WHERE {self.ROLLUP_WHERE}
              AND EXTRACT(YEAR  FROM t.completion_time) = :year
              AND EXTRACT(MONTH FROM t.completion_time) = :month
            {sc_filter}
            ORDER BY ABS(t.withdrawn) DESC
        """), params).fetchall()

        return [
            {
                "receipt_no": r.receipt_no,
                "shortcode": r.business_shortcode,
                "company_name": r.company_name or r.details,
                "store_number": r.store_number,
                "location": r.location or "—",
                "amount": float(r.amount or 0),
                "completion_time": r.completion_time.isoformat() if r.completion_time else None,
            }
            for r in rows
        ]

    def _prev_month(self, year, month):
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def generate_report(self, year, month, company_id=None):
        company_shortcodes = None
        if company_id:
            acs = AgentCompany.query.filter_by(company_id=company_id).all()
            company_shortcodes = {ac.short_code for ac in acs if ac.short_code}

        tills = self._rollups_for_month(year, month, company_shortcodes)

        # Previous month for MoM
        prev_year, prev_month = self._prev_month(year, month)
        prev_tills = self._rollups_for_month(prev_year, prev_month, company_shortcodes)
        prev_map = {t["shortcode"]: t["amount"] for t in prev_tills}

        for t in tills:
            prev = prev_map.get(t["shortcode"], 0.0)
            t["prev_amount"] = prev
            t["mom_change"] = t["amount"] - prev
            t["mom_pct"] = ((t["amount"] - prev) / prev * 100) if prev else None

        total = sum(t["amount"] for t in tills)
        prev_total = sum(t["prev_amount"] for t in tills)

        label = datetime(year, month, 1).strftime("%B %Y")
        prev_label = datetime(prev_year, prev_month, 1).strftime("%B %Y")

        return {
            "month": month,
            "year": year,
            "label": label,
            "prev_label": prev_label,
            "summary": {
                "total_amount": total,
                "prev_total_amount": prev_total,
                "mom_change": total - prev_total,
                "mom_pct": ((total - prev_total) / prev_total * 100) if prev_total else None,
                "till_count": len(tills),
            },
            "tills": tills,
            "available_months": self._available_months(company_shortcodes),
        }
