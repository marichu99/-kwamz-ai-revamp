from datetime import datetime, timedelta, date
from decimal import Decimal
from app import db
from app.model.user import User
from app.model.agentcompany import AgentCompany
from app.model.subscription import Subscription
from app.model.config import SmtpConfig

_DEFAULT_RATE_PER_TILL = Decimal('200.00')
_DEFAULT_TRIAL_DAYS = 30


def _get_trial_days():
    try:
        cfg = SmtpConfig.get_global()
        return cfg.trial_days if cfg.trial_days is not None else _DEFAULT_TRIAL_DAYS
    except Exception:
        db.session.rollback()
        return _DEFAULT_TRIAL_DAYS


def _get_rate_per_till():
    try:
        cfg = SmtpConfig.get_global()
        return Decimal(str(cfg.rate_per_till)) if cfg.rate_per_till is not None else _DEFAULT_RATE_PER_TILL
    except Exception:
        db.session.rollback()
        return _DEFAULT_RATE_PER_TILL


class BillingService:

    @staticmethod
    def get_active_tills_count(user_id):
        return AgentCompany.query.filter_by(user_id=user_id, status='active').count()

    @staticmethod
    def get_active_tills(user_id):
        return AgentCompany.query.filter_by(user_id=user_id, status='active').all()

    @staticmethod
    def calculate_monthly_bill(user_id):
        count = BillingService.get_active_tills_count(user_id)
        return count, count * _get_rate_per_till()

    @staticmethod
    def get_current_billing_period():
        today = date.today()
        period_start = today.replace(day=1)
        # Last day of current month
        if today.month == 12:
            period_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        return period_start, period_end

    @staticmethod
    def is_in_trial(user):
        if not user.created_at:
            return False
        trial_end = user.created_at + timedelta(days=_get_trial_days())
        return datetime.utcnow() <= trial_end

    @staticmethod
    def get_trial_end_date(user):
        if not user.created_at:
            return None
        return (user.created_at + timedelta(days=_get_trial_days())).date()

    @staticmethod
    def get_trial_days_remaining(user):
        if not user.created_at:
            return 0
        trial_end = user.created_at + timedelta(days=_get_trial_days())
        remaining = (trial_end - datetime.utcnow()).days
        return max(0, remaining)

    @staticmethod
    def get_current_subscription(user_id):
        period_start, period_end = BillingService.get_current_billing_period()
        return Subscription.query.filter_by(
            user_id=user_id,
            billing_period_start=period_start,
            billing_period_end=period_end,
        ).first()

    @staticmethod
    def get_billing_status(user_id):
        user = User.query.get(user_id)
        if not user:
            return None

        # Check trial
        if BillingService.is_in_trial(user):
            tills_count, amount = BillingService.calculate_monthly_bill(user_id)
            return {
                'status': 'TRIAL',
                'trial_end_date': BillingService.get_trial_end_date(user).isoformat(),
                'trial_days_remaining': BillingService.get_trial_days_remaining(user),
                'active_tills_count': tills_count,
                'amount_due': float(amount),
                'rate_per_till': float(_get_rate_per_till()),
                'subscription': None,
            }

        # Post-trial: check for paid subscription this month
        subscription = BillingService.get_current_subscription(user_id)
        tills_count, amount = BillingService.calculate_monthly_bill(user_id)

        if subscription and subscription.is_paid:
            return {
                'status': 'PAID',
                'trial_end_date': BillingService.get_trial_end_date(user).isoformat() if user.created_at else None,
                'trial_days_remaining': 0,
                'active_tills_count': tills_count,
                'amount_due': float(amount),
                'rate_per_till': float(_get_rate_per_till()),
                'subscription': subscription.to_dict(),
            }

        return {
            'status': 'NOT_PAID',
            'trial_end_date': BillingService.get_trial_end_date(user).isoformat() if user.created_at else None,
            'trial_days_remaining': 0,
            'active_tills_count': tills_count,
            'amount_due': float(amount),
            'rate_per_till': float(_get_rate_per_till()),
            'subscription': subscription.to_dict() if subscription else None,
        }

    @staticmethod
    def create_subscription_for_current_period(user_id):
        period_start, period_end = BillingService.get_current_billing_period()

        existing = BillingService.get_current_subscription(user_id)
        if existing:
            # Update tills count and amount in case it changed
            tills_count, amount = BillingService.calculate_monthly_bill(user_id)
            existing.active_tills_count = tills_count
            existing.amount_due = amount
            db.session.commit()
            return existing

        tills_count, amount = BillingService.calculate_monthly_bill(user_id)

        subscription = Subscription(
            user_id=user_id,
            billing_period_start=period_start,
            billing_period_end=period_end,
            active_tills_count=tills_count,
            amount_due=amount,
            status='PENDING',
        )
        db.session.add(subscription)
        db.session.commit()
        return subscription

    @staticmethod
    def mark_subscription_paid(subscription_id, pesapal_payment_id=None):
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        subscription.mark_as_paid(pesapal_payment_id)
        db.session.commit()
        return subscription

    @staticmethod
    def get_billing_summary(user_id):
        user = User.query.get(user_id)
        if not user:
            return None

        tills = BillingService.get_active_tills(user_id)
        tills_count = len(tills)
        amount = tills_count * _get_rate_per_till()

        # Payment history (last 6 months)
        recent_subscriptions = Subscription.query.filter_by(
            user_id=user_id,
        ).order_by(Subscription.billing_period_start.desc()).limit(6).all()

        return {
            'user_id': user_id,
            'active_tills': [{
                'id': t.id,
                'company_name': t.company_name,
                'agent_number': t.agent_number,
                'store_number': t.store_number,
                'till_number': t.till_number,
            } for t in tills],
            'active_tills_count': tills_count,
            'rate_per_till': float(_get_rate_per_till()),
            'total_amount_due': float(amount),
            'currency': 'KES',
            'is_trial': BillingService.is_in_trial(user),
            'trial_end_date': BillingService.get_trial_end_date(user).isoformat() if user.created_at else None,
            'trial_days_remaining': BillingService.get_trial_days_remaining(user),
            'payment_history': [s.to_dict() for s in recent_subscriptions],
        }
