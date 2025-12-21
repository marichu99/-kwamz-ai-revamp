# database/connection_pool.py
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os
from typing import Optional, Generator
import logging
import threading

logger = logging.getLogger(__name__)

class DatabasePool:
    """Database connection pool manager with proper error handling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabasePool, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the connection pool only once"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._initialize_pool()
                    self._initialized = True
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
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
            
            logger.info(f"Creating database connection pool with {self._min_conn}-{self._max_conn} connections")
            
            self._pool = ThreadedConnectionPool(
                minconn=self._min_conn,
                maxconn=self._max_conn,
                **config,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            
            logger.info("Database connection pool created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {str(e)}")
            raise
    
    def _ensure_pool(self):
        """Ensure the pool is initialized"""
        if not hasattr(self, '_pool') or self._pool is None:
            self._initialize_pool()
    
    @contextmanager
    def get_connection(self) -> Generator:
        """Get a connection from the pool with proper error handling"""
        self._ensure_pool()
        
        conn = None
        key = None
        try:
            # Get connection from pool
            conn = self._pool.getconn()
            if conn:
                # Get the key (ThreadedConnectionPool assigns keys internally)
                # We don't need to manage the key explicitly
                pass
            yield conn
        except Exception as e:
            logger.error(f"Error in database connection: {str(e)}")
            # If connection is bad, close it instead of returning to pool
            if conn:
                try:
                    self._pool.putconn(conn, close=True)
                except:
                    pass
            raise
        finally:
            # Always return connection to pool if we got one
            if conn:
                try:
                    # Check if connection is still open
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
                # Only commit if not in autocommit mode
                if not autocommit:
                    conn.commit()
            except Exception as e:
                # Rollback on error if not in autocommit mode
                if not autocommit:
                    try:
                        conn.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
                raise
            finally:
                # Always close cursor
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
            # ThreadedConnectionPool doesn't expose these directly,
            # but we can try to get some info
            return {
                "status": "active",
                "min_connections": self._min_conn,
                "max_connections": self._max_conn,
                "pool_class": self._pool.__class__.__name__
            }
        except:
            return {"status": "unknown"}

# Singleton instance
db_pool = DatabasePool()