from app.model.payment import Payment
from app import db
from sqlalchemy import and_

class PaymentService:
    def __init__(self):
        pass

    @staticmethod
    def getByCriteria(phone_number=None, checkout_id=None, payment_ref=None, start_date=None, end_date=None):
        query = db.session.query(Payment)

        filters = []

        if phone_number:
            filters.append(Payment.phone_number == phone_number)
        if checkout_id:
            filters.append(Payment.checkout_id == checkout_id)
        if payment_ref:
            filters.append(Payment.payment_ref == payment_ref)
        if start_date and end_date:
            filters.append(Payment.created_at.between(start_date, end_date))
        elif start_date:  
            filters.append(Payment.created_at >= start_date)
        elif end_date:  
            filters.append(Payment.created_at <= end_date)

        if filters:
            query = query.filter(and_(*filters))

        return query.all()
