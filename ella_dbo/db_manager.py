# ella_dbo/db_manager.py
import os
import sqlite3
import uuid
import contextlib
import logging
import json
from typing import List, Optional, Dict, Any, Union
import importlib.util


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

# Add this function to your db_manager.py file
def run_migrations():
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    for filename in sorted(os.listdir(migrations_dir)):
        if filename.endswith('.py'):
            print(f"Running migration: {filename}")
            spec = importlib.util.spec_from_file_location(
                f"migrations.{filename[:-3]}",
                os.path.join(migrations_dir, filename)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.migrate()

# Modify your initialize_database function to run migrations
def initialize_database():
    """Initialize the database, creating it if it doesn't exist and setting up tables."""
    try:
        with get_db_connection() as conn:
            create_table(conn)
        logger.info("Database initialized and tables created successfully.")
        run_migrations()  # Run migrations after initializing the database
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def create_table(conn):
    """Create tables to store user info and calendar events."""
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
    
    create_events_table_sql = """
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        location TEXT,
        reminders TEXT,
        recurrence TEXT,
        FOREIGN KEY (user_id) REFERENCES users (memgpt_user_id)
    );"""
    
    try:
        conn.execute(create_users_table_sql)
        conn.execute(create_events_table_sql)
        logger.info("Tables created successfully or already exist.")
    except sqlite3.Error as e:
        logger.error(f"An error occurred while creating tables: {e}")
        raise

# Add new functions for calendar operations

def add_event(user_id: str, event_data: Dict[str, Any]) -> Optional[str]:
    try:
        event_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO events (
                    id, user_id, summary, description, start_time, end_time, 
                    location, reminders, recurrence, local_timezone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, user_id, 
                event_data['summary'], 
                event_data.get('description', ''),
                event_data['start']['dateTime'],
                event_data['end']['dateTime'],
                event_data.get('location', ''),
                json.dumps(event_data.get('reminders', {'useDefault': True})),
                json.dumps(event_data.get('recurrence', [])),
                event_data.get('local_timezone', 'UTC')
            ))
        return event_id
    except Exception as e:
        logger.error(f"Error adding event to database: {str(e)}", exc_info=True)
        return None

def get_events(user_id: str, time_min: str, time_max: str) -> List[Dict[str, Any]]:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_id, summary, description, start_time, end_time, 
                       location, reminders, recurrence, local_timezone
                FROM events 
                WHERE user_id = ? AND start_time >= ? AND end_time <= ?
                ORDER BY start_time ASC
            """, (user_id, time_min, time_max))
            
            events = []
            for row in cur.fetchall():
                event = {
                    'id': row[0],
                    'user_id': row[1],
                    'summary': row[2],
                    'description': row[3],
                    'start_time': row[4],
                    'end_time': row[5],
                    'location': row[6],
                    'reminders': row[7],
                    'recurrence': row[8],
                    'local_timezone': row[9]
                }
                events.append(event)
            
            return events
    except Exception as e:
        logger.error(f"Error fetching events from database: {str(e)}", exc_info=True)
        return []

# ... (existing imports and setup)

def update_event(event_id: str, event_data: Dict[str, Any]) -> bool:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Construct the SQL query dynamically based on the provided event_data
            set_clauses = ', '.join([f"{key} = ?" for key in event_data.keys()])
            query = f"UPDATE events SET {set_clauses} WHERE id = ?"
            
            # Prepare the values for the query
            values = list(event_data.values()) + [event_id]
            
            cur.execute(query, values)
            return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating event in database: {str(e)}", exc_info=True)
        return False

def delete_event(event_id: str) -> bool:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting event from database: {str(e)}", exc_info=True)
        return False

def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_id, summary, description, start_time, end_time, 
                       location, reminders, recurrence, local_timezone
                FROM events 
                WHERE id = ?
            """, (event_id,))
            
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'summary': row[2],
                    'description': row[3],
                    'start': {'dateTime': row[4], 'timeZone': row[9]},
                    'end': {'dateTime': row[5], 'timeZone': row[9]},
                    'location': row[6],
                    'reminders': json.loads(row[7]) if row[7] else None,
                    'recurrence': json.loads(row[8]) if row[8] else None,
                    'local_timezone': row[9]
                }
            return None
    except Exception as e:
        logger.error(f"Error fetching event from database: {str(e)}", exc_info=True)
        return None

# ... (other existing functions)
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
