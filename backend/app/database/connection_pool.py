# database/connection_pool.py
import psycopg2.extras
from contextlib import contextmanager
from typing import Generator
import logging

logger = logging.getLogger(__name__)


class DatabasePool:
    """Raw psycopg2 cursors backed by the app's single SQLAlchemy connection
    pool — not a second, independently-sized pool.

    This used to maintain its own ThreadedConnectionPool alongside
    SQLAlchemy's engine pool. Two pools sized without awareness of each
    other meant this process's worst-case connection demand (SQLAlchemy's
    pool_size+max_overflow, plus this pool's own max) could add up to more
    than the DB role's entire connection budget on its own. Borrowing from
    db.engine keeps there being exactly one pool, sized by
    DB_POOL_SIZE/DB_MAX_OVERFLOW.
    """

    @contextmanager
    def get_connection(self) -> Generator:
        """Borrow a raw DBAPI connection from the SQLAlchemy pool."""
        from app import db

        conn = None
        try:
            conn = db.engine.raw_connection()
            yield conn
        except Exception as e:
            logger.error(f"Error in database connection: {str(e)}")
            raise
        finally:
            if conn:
                try:
                    conn.close()  # returns the connection to the SQLAlchemy pool
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {str(e)}")

    @contextmanager
    def get_cursor(self, autocommit: bool = False) -> Generator:
        """Get a dict-row cursor with proper transaction management"""
        with self.get_connection() as conn:
            conn.autocommit = autocommit
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            try:
                yield cursor
                if not autocommit:
                    conn.commit()
            except Exception as e:
                if not autocommit:
                    try:
                        conn.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
                raise
            finally:
                try:
                    cursor.close()
                except Exception as close_error:
                    logger.error(f"Error closing cursor: {str(close_error)}")


# Singleton instance
db_pool = DatabasePool()
