from app import db
from datetime import datetime, date


class SwapScrapeLog(db.Model):
    __tablename__ = 'swap_scrape_logs'

    id = db.Column(db.Integer, primary_key=True)
    shortcode = db.Column(db.String(20), nullable=False)
    scraped_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('shortcode', 'scraped_date', name='uq_swap_scrape_shortcode_date'),
    )

    @classmethod
    def already_scraped_today(cls, shortcode: str) -> bool:
        return cls.query.filter_by(shortcode=shortcode, scraped_date=date.today()).first() is not None

    @classmethod
    def log(cls, shortcode: str, user_id=None):
        try:
            entry = cls(shortcode=shortcode, scraped_date=date.today(), user_id=user_id)
            db.session.add(entry)
            db.session.commit()
        except Exception:
            db.session.rollback()
