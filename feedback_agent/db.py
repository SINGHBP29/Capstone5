import sqlite3
import logging
from .config import DB_CONNECTION_STRING, MOCK_MODE

logger = logging.getLogger("feedback_agent.db")

class OCSDatabase:
    """
    Manages database connection and schemas.
    Falls back to SQLite if MOCK_MODE is enabled or PostgreSQL is unavailable.
    """
    def __init__(self):
        self.is_sqlite = True
        self.conn = None
        self.initialize_db()

    def initialize_db(self):
        # Even in live mode, if Postgres connection fails, we fall back to SQLite
        if not MOCK_MODE:
            try:
                # Dynamically import psycopg2/other driver if needed
                import psycopg2
                self.conn = psycopg2.connect(DB_CONNECTION_STRING)
                self.is_sqlite = False
                logger.info("Connected to PostgreSQL database.")
            except Exception as e:
                logger.warning(f"Failed to connect to PostgreSQL ({e}). Falling back to SQLite.")

        if self.conn is None:
            # Local SQLite database in the workspace directory
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ocs_feedback.db")
            self.conn = sqlite3.connect(db_path)
            self.is_sqlite = True
            logger.info(f"Connected to local SQLite database at {db_path}.")

        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # SQLite types differ slightly from PG, but standard SQL is compatible
        serial_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if self.is_sqlite else "SERIAL PRIMARY KEY"
        text_type = "TEXT"
        bool_type = "BOOLEAN"
        real_type = "REAL"
        
        # Audit record table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS audit_records (
                id {serial_type},
                incident_id {text_type},
                query {text_type},
                gap_type {text_type},
                fix_order_executed {text_type},
                patches_applied INTEGER,
                evidence_artifacts INTEGER,
                owner_path {text_type},
                rollback_available {bool_type},
                decision {text_type},
                confidence {real_type},
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Thresholds / configuration watchlist table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS watchlist (
                id {serial_type},
                query {text_type} UNIQUE,
                status {text_type}, -- ACTIVE, RESOLVED, REGRESSED
                monitoring_window {text_type},
                regression_threshold {text_type},
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Runbook metrics table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS runbook_history (
                id {serial_type},
                gap_type {text_type},
                remediation_steps {text_type},
                success {bool_type},
                duration_minutes INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Canary release state tracking table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS canary_releases (
                id {serial_type},
                incident_id {text_type},
                query {text_type},
                current_tier INTEGER DEFAULT 0,
                status {text_type} DEFAULT 'PENDING',
                tiers_completed {text_type} DEFAULT '[]',
                hold_count INTEGER DEFAULT 0,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                final_decision {text_type}
            )
        """)

        self.conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> list:
        if not self.is_sqlite:
            # PostgreSQL uses %s placeholders, while SQLite uses ? placeholders.
            query = query.replace('?', '%s')
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            self.conn.commit()
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            return []
        except Exception as e:
            logger.error(f"Database error executing query '{query}': {e}")
            raise e

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")
