
import os
import logging
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2 import pool

logger = logging.getLogger("velo-lab-analysis")

class Database:
    _pool: pool.ThreadedConnectionPool = None

    @classmethod
    def initialize(cls):
        """Initialize the database connection pool"""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")

        try:
            # Initialize a threaded connection pool
            # minconn=1, maxconn=20 (adjust based on your tier limits)
            cls._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=database_url
            )
            logger.info("Database connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    @classmethod
    def close(cls):
        """Close all connections in the pool"""
        if cls._pool:
            cls._pool.closeall()
            logger.info("Database connection pool closed.")

    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator[any, None, None]:
        """
        Context manager to yield a connection from the pool.
        Automatically returns the connection to the pool when done.
        """
        if not cls._pool:
            # Lazy initialization if not explicitly called (safety net)
            # ideally calling initialize() on startup is better
            cls.initialize()
            
        conn = None
        try:
            conn = cls._pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
        finally:
            if conn:
                cls._pool.putconn(conn)

    @classmethod
    @contextmanager
    def get_cursor(cls) -> Generator[any, None, None]:
        """
        Context manager to yield a cursor.
        Handles connection retrieval and return automatically.
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
