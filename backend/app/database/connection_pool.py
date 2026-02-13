# database/connection_pool.py
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os
from typing import Optional, Generator
import logging
import threading

logger = logging.getLogger(__name__)

class DatabasePool:
    """Database connection pool manager - fork-safe for Celery prefork workers."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabasePool, cls).__new__(cls)
                cls._instance._initialized = False
                cls._instance._pid = None
        return cls._instance

    def __init__(self):
        """Initialize the connection pool only once per process."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._initialize_pool()
                    self._initialized = True

    def _check_pid(self):
        """Reinitialize the pool if we're in a forked child process.

        psycopg2 connections are not safe to share across fork().
        When Celery forks worker processes, the parent's pool becomes
        invalid in children. Detect this via PID change and recreate.
        """
        current_pid = os.getpid()
        if self._pid != current_pid:
            with self._lock:
                if self._pid != current_pid:
                    logger.info(
                        f"PID changed ({self._pid} -> {current_pid}), "
                        f"reinitializing connection pool for forked worker"
                    )
                    # Don't close the old pool — it belongs to the parent process
                    self._pool = None
                    self._initialize_pool()

    def _parse_database_url(self, url: str) -> dict:
        """Parse DATABASE_URL into connection parameters."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': str(parsed.port or 5432),
            'database': parsed.path.lstrip('/') or 'mpesaglobal',
            'user': parsed.username or 'postgres',
            'password': parsed.password or 'postgres',
        }

    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            # Support both DATABASE_URL and individual DB_* environment variables
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                logger.info("Using DATABASE_URL for connection")
                url_config = self._parse_database_url(database_url)
                config = {
                    'host': url_config['host'],
                    'port': url_config['port'],
                    'database': url_config['database'],
                    'user': url_config['user'],
                    'password': url_config['password'],
                    'sslmode': os.getenv('DB_SSLMODE', 'prefer'),
                }
            else:
                config = {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': os.getenv('DB_PORT', '5432'),
                    'database': os.getenv('DB_NAME', 'your_database'),
                    'user': os.getenv('DB_USER', 'your_user'),
                    'password': os.getenv('DB_PASSWORD', 'your_password'),
                    'sslmode': os.getenv('DB_SSLMODE', 'prefer'),
                }

            self._min_conn = int(os.getenv('DB_MIN_CONNECTIONS', '1'))
            self._max_conn = int(os.getenv('DB_MAX_CONNECTIONS', '10'))

            logger.info(f"Creating database connection pool (pid={os.getpid()}) with {self._min_conn}-{self._max_conn} connections")

            self._pool = ThreadedConnectionPool(
                minconn=self._min_conn,
                maxconn=self._max_conn,
                **config,
                cursor_factory=psycopg2.extras.RealDictCursor
            )

            self._pid = os.getpid()
            self._initialized = True
            logger.info("Database connection pool created successfully")

        except Exception as e:
            logger.error(f"Failed to create database connection pool: {str(e)}")
            raise

    def _ensure_pool(self):
        """Ensure the pool is initialized and belongs to this process."""
        self._check_pid()
        if not hasattr(self, '_pool') or self._pool is None:
            self._initialize_pool()

    @contextmanager
    def get_connection(self) -> Generator:
        """Get a connection from the pool with proper error handling"""
        self._ensure_pool()

        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Error in database connection: {str(e)}")
            if conn:
                try:
                    self._pool.putconn(conn, close=True)
                    conn = None
                except:
                    pass
            raise
        finally:
            if conn:
                try:
                    if conn.closed == 0:
                        self._pool.putconn(conn)
                    else:
                        logger.warning("Connection was closed, not returning to pool")
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {str(e)}")
                    try:
                        conn.close()
                    except:
                        pass

    @contextmanager
    def get_cursor(self, autocommit: bool = False) -> Generator:
        """Get a cursor from the pool with proper transaction management"""
        with self.get_connection() as conn:
            if conn is None:
                raise ConnectionError("Failed to get database connection")

            conn.autocommit = autocommit
            cursor = conn.cursor()

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

    def get_raw_connection(self):
        """Get a raw connection without context manager"""
        self._ensure_pool()
        return self._pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if conn and hasattr(self, '_pool') and self._pool:
            try:
                if conn.closed == 0:
                    self._pool.putconn(conn)
                else:
                    logger.warning("Connection was closed, not returning to pool")
            except Exception as e:
                logger.error(f"Error returning connection to pool: {str(e)}")

    def close_all(self):
        """Close all connections in the pool"""
        if hasattr(self, '_pool') and self._pool:
            try:
                self._pool.closeall()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {str(e)}")

    def get_pool_status(self):
        """Get pool status information"""
        if not hasattr(self, '_pool') or self._pool is None:
            return {"status": "not_initialized"}

        try:
            return {
                "status": "active",
                "pid": self._pid,
                "min_connections": self._min_conn,
                "max_connections": self._max_conn,
                "pool_class": self._pool.__class__.__name__
            }
        except:
            return {"status": "unknown"}

# Singleton instance
db_pool = DatabasePool()
