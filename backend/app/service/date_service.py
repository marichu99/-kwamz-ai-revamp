from datetime import datetime, timedelta

class DateService:
    """Service for handling date-related calculations"""

    def calculate_date_range(self, date_range, start_date=None, end_date=None):
        """
        Calculate date range based on selection.
        Returns start_date at 00:00:00 and end_date at 23:59:59 for full day coverage.
        """
        if date_range == 'custom':
            if not start_date or not end_date:
                raise ValueError('Start and end dates required for custom range')

            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        else:
            start_date_obj = self._get_predefined_range_start(date_range)
            end_date_obj = datetime.now().replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

        return start_date_obj, end_date_obj

    def _get_predefined_range_start(self, date_range):
        """Get start date for predefined ranges"""
        today = datetime.now()

        ranges = {
            'today': today.replace(hour=0, minute=0, second=0, microsecond=0),
            'yesterday': (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
            'this_week': (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0),
            'last_week': self._get_last_week_start(today),
            'this_month': today.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            'last_month': self._get_last_month_start(today),
            'last_3_months': (today.replace(day=1) - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0),
            'last_6_months': (today.replace(day=1) - timedelta(days=180)).replace(hour=0, minute=0, second=0, microsecond=0),
            'this_year': today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0),
            'last_year': today.replace(year=today.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        }

        return ranges.get(date_range, today.replace(day=1, hour=0, minute=0, second=0, microsecond=0))

    def _get_last_week_start(self, today):
        """Get start of last week"""
        last_week = today - timedelta(weeks=1)
        return (last_week - timedelta(days=last_week.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def _get_last_month_start(self, today):
        """Get start of last month"""
        first_day_current = today.replace(day=1)
        return (first_day_current - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
