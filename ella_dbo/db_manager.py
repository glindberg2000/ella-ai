# ella_dbo/db_manager.py
import os
import sqlite3
import uuid
import contextlib
import logging

current_dir = os.path.dirname(__file__)
DB_FILE = os.path.join(current_dir, "database.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(DB_FILE)
            self.conn.row_factory = sqlite3.Row
            return self.conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()

def get_db_connection():
    return DatabaseConnectionManager()

def initialize_database():
    """Initialize the database, creating it if it doesn't exist and setting up tables."""
    try:
        with get_db_connection() as conn:
            create_table(conn)
        logger.info("Database initialized and tables created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def create_table(conn):
    """Create tables to store user info."""
    create_users_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        auth0_user_id TEXT NOT NULL,
        memgpt_user_id TEXT,
        memgpt_user_api_key TEXT,
        email TEXT,
        phone TEXT,
        name TEXT,
        roles TEXT,
        default_agent_key TEXT,
        vapi_assistant_id TEXT,
        calendar_id TEXT,
        default_reminder_time INTEGER DEFAULT 15,
        reminder_method TEXT DEFAULT 'email,sms',
        active_events_count INTEGER DEFAULT 0,
        local_timezone TEXT DEFAULT 'America/Los_Angeles'
    );"""
    try:
        conn.execute(create_users_table_sql)
        logger.info("Table created successfully or already exists.")
    except sqlite3.Error as e:
        logger.error(f"An error occurred while creating table: {e}")
        raise

def upsert_user(conn, lookup_field, lookup_value, **kwargs):
    try:
        converted_kwargs = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in kwargs.items()}
        lookup_value = str(lookup_value) if isinstance(lookup_value, uuid.UUID) else lookup_value
        
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM users WHERE {lookup_field} = ?", (lookup_value,))
        exists = cur.fetchone()[0] > 0
        fields = list(converted_kwargs.keys())
        values = list(converted_kwargs.values())

        if exists:
            updates = ', '.join(f"{k} = ?" for k in fields)
            sql = f"UPDATE users SET {updates} WHERE {lookup_field} = ?"
            params = values + [lookup_value]
            cur.execute(sql, params)
        else:
            fields_str = ', '.join(fields)
            placeholders = ', '.join('?' * len(kwargs))
            sql = f"INSERT INTO users ({lookup_field}, {fields_str}) VALUES (?, {placeholders})"
            params = [lookup_value] + values
            cur.execute(sql, params)

        logger.info('User upserted successfully.')
    except Exception as e:
        logger.error(f"Database error during upsert: {e}")
        raise

def get_user_data_by_field(field_name, field_value):
    """Retrieve user data by a specified field and value."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        sql = f"SELECT * FROM users WHERE {field_name} = ?"
        cur.execute(sql, (field_value,))
        result = cur.fetchone()
        return dict(result) if result else None

def get_active_users():
    """Retrieve all active users (users with memgpt_user_id)."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE memgpt_user_id IS NOT NULL")
        return [dict(row) for row in cur.fetchall()]

