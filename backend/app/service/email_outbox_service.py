from app.model.email_outbox import EmailOutbox
from app import db
from sqlalchemy import and_

class EmailOutboxService:

    # CREATE
    def create(
        sender: str,
        receiver: str,
        reason: str,
        business_short_code: str,
        sent_times: int = 0,
        time_generated=None
    ) -> EmailOutbox:
        email = EmailOutbox(
            sender=sender,
            receiver=receiver,
            reason=reason,
            business_short_code=business_short_code,
            sent_times=sent_times,
            time_generated=time_generated
        )
        db.session.add(email)
        db.session.commit()
        return email

    # READ: by ID
    def get_by_id(email_id: int) -> EmailOutbox | None:
        return EmailOutbox.query.get(email_id)

    # READ: all
    def get_all():
        return EmailOutbox.query.order_by(
            EmailOutbox.time_generated.desc()
        ).all()

    # READ: by receiver
    def get_by_receiver(receiver: str):
        return EmailOutbox.query.filter(
            EmailOutbox.receiver == receiver
        ).all()

    # READ: by business short code and reason
    def get_by_business_and_reason(business_short_code: str, reason: str):
        return EmailOutbox.query.filter(
            and_(
                EmailOutbox.business_short_code == business_short_code,
                EmailOutbox.reason == reason
            )
        ).all()

    # UPDATE
    def update(email_id: int, **kwargs) -> EmailOutbox | None:
        email = EmailOutbox.query.get(email_id)
        if not email:
            return None

        for key, value in kwargs.items():
            if hasattr(email, key):
                setattr(email, key, value)

        db.session.commit()
        return email

    # INCREMENT sent_times (common use-case)
    def increment_sent_times(email_id: int) -> EmailOutbox | None:
        email = EmailOutbox.query.get(email_id)
        if not email:
            return None

        email.sent_times = (email.sent_times or 0) + 1
        db.session.commit()
        return email

    # DELETE
    def delete(email_id: int) -> bool:
        email = EmailOutbox.query.get(email_id)
        if not email:
            return False

        db.session.delete(email)
        db.session.commit()
        return True
