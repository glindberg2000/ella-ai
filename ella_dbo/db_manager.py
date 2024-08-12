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

### Deprecated
# import os
# import sqlite3
# import uuid
# import argparse

# # Get the directory of the current file (__file__ is the path to the current script)
# current_dir = os.path.dirname(__file__)

# # Define the database file path as relative to the current directory
# DB_FILE = os.path.join(current_dir, "database.db")

# def create_connection():
#     """Create and return a database connection to the SQLite database specified by db_file."""
#     print('Creating connection to database...')
#     conn = None
#     try:
#         conn = sqlite3.connect(DB_FILE)
#     except sqlite3.Error as e:
#         print(e)
#     return conn

# def create_table(conn):
#     """Create tables to store user info, including calendar ID, notification preferences, active event count, and local timezone."""
#     print('Creating table users...')
#     create_users_table_sql = """
#     CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY,
#         auth0_user_id TEXT NOT NULL,
#         memgpt_user_id TEXT,
#         memgpt_user_api_key TEXT,
#         email TEXT,
#         phone TEXT,
#         name TEXT,
#         roles TEXT,
#         default_agent_key TEXT,
#         vapi_assistant_id TEXT,
#         calendar_id TEXT,
#         default_reminder_time INTEGER DEFAULT 15,
#         reminder_method TEXT DEFAULT 'email,sms',
#         active_events_count INTEGER DEFAULT 0,
#         local_timezone TEXT DEFAULT 'America/Los_Angeles'  -- New column for user's local timezone
#     );"""
#     try:
#         c = conn.cursor()
#         c.execute(create_users_table_sql)
#         print("Table created successfully or already exists.")
#     except sqlite3.Error as e:
#         print(f"An error occurred: {e}")

# def upsert_user(conn, lookup_field, lookup_value, **kwargs):
#     print('upsert_user() called')
#     cur = conn.cursor()
#     try:
#         # Convert UUIDs to strings for storage and make sure lookup_value is also converted
#         converted_kwargs = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in kwargs.items()}
#         lookup_value = str(lookup_value) if isinstance(lookup_value, uuid.UUID) else lookup_value
        
#         # Check if the record exists using the dynamic lookup field and value
#         cur.execute(f"SELECT COUNT(*) FROM users WHERE {lookup_field} = ?", (lookup_value,))
#         exists = cur.fetchone()[0] > 0
#         fields = list(converted_kwargs.keys())
#         values = list(converted_kwargs.values())

#         if exists:
#             updates = ', '.join(f"{k} = ?" for k in fields)
#             sql = f"UPDATE users SET {updates} WHERE {lookup_field} = ?"
#             params = values + [lookup_value]
#             cur.execute(sql, params)
#         else:
#             fields_str = ', '.join(fields)
#             placeholders = ', '.join('?' * len(kwargs))
#             sql = f"INSERT INTO users ({lookup_field}, {fields_str}) VALUES (?, {placeholders})"
#             params = [lookup_value] + values
#             cur.execute(sql, params)

#         conn.commit()
#         print('User upserted successfully.')
#     except Exception as e:
#         print(f"Database error during upsert: {e}")
#     finally:
#         cur.close()

# def get_user_data_by_field(conn, field_name, field_value):
#     """
#     Retrieve user data by a specified field and value, ensuring all relevant user fields are included.
    
#     Parameters:
#     - conn: The database connection object.
#     - field_name: The field name to filter by.
#     - field_value: The value to match for the specified field.
    
#     Returns:
#     - A dictionary containing the user details if found, None otherwise.
#     """
#     conn.row_factory = sqlite3.Row  # Set row factory to Row for dictionary-like access
#     cur = conn.cursor()
#     sql = f"SELECT * FROM users WHERE {field_name} = ?"
#     cur.execute(sql, (field_value,))
#     result = cur.fetchone()
#     if result:
#         return dict(result)
#     return None

# # close the database connection if needed
# def close_connection(conn):
#     """Close a database connection."""
#     print('closing connection')
#     if conn:
#         conn.close()

#### Deprecated Functions ###

# def create_table(conn):
#     """Create tables to store user info, including calendar ID, notification preferences, and active event count, given a connection."""
#     print('Creating table users...')
#     create_users_table_sql = """
#     CREATE TABLE IF NOT EXISTS users (
#         id INTEGER PRIMARY KEY,
#         auth0_user_id TEXT NOT NULL,
#         memgpt_user_id TEXT,
#         memgpt_user_api_key TEXT,
#         email TEXT,
#         phone TEXT,
#         name TEXT,
#         roles TEXT,
#         default_agent_key TEXT,
#         vapi_assistant_id TEXT,
#         calendar_id TEXT,  -- Column to store the Google Calendar ID
#         default_reminder_time INTEGER DEFAULT 15,  -- Default reminder time in minutes before the event
#         reminder_method TEXT DEFAULT 'email,sms',  -- Default method for sending reminders
#         active_events_count INTEGER DEFAULT 0  -- Column to store the count of active events
#     );"""
#     try:
#         c = conn.cursor()
#         c.execute(create_users_table_sql)
#         print("Table created successfully or already exists.")
#     except sqlite3.Error as e:
#         print(f"An error occurred: {e}")

# def upsert_user(conn, lookup_field, lookup_value, **kwargs):
#     print('upsert_user() called')
#     cur = conn.cursor()
#     try:
#         # Convert UUIDs to strings for storage and make sure lookup_value is also converted
#         converted_kwargs = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in kwargs.items()}
#         lookup_value = str(lookup_value) if isinstance(lookup_value, uuid.UUID) else lookup_value
        
#         # Check if the record exists using the dynamic lookup field and value
#         cur.execute(f"SELECT COUNT(*) FROM users WHERE {lookup_field} = ?", (lookup_value,))
#         exists = cur.fetchone()[0] > 0
#         fields = list(converted_kwargs.keys())
#         values = list(converted_kwargs.values())

#         if exists:
#             updates = ', '.join(f"{k} = ?" for k in fields)
#             sql = f"UPDATE users SET {updates} WHERE {lookup_field} = ?"
#             params = values + [lookup_value]
#             cur.execute(sql, params)
#         else:
#             fields_str = ', '.join(fields)
#             placeholders = ', '.join('?' * len(kwargs))
#             sql = f"INSERT INTO users ({lookup_field}, {fields_str}) VALUES (?, {placeholders})"
#             params = [lookup_value] + values
#             cur.execute(sql, params)

#         conn.commit()
#         print('User upserted successfully.')
#     except Exception as e:
#         print(f"Database error during upsert: {e}")
#     finally:
#         cur.close()

# def get_user_data_by_field(conn, field_name, field_value):
#     """
#     Retrieve user data by a specified field and value, ensuring all relevant user fields are included.
    
#     Parameters:
#     - conn: The database connection object.
#     - field_name: The field name to filter by.
#     - field_value: The value to match for the specified field.
    
#     Returns:
#     - A dictionary containing the user details if found, None otherwise.
#     """
#     conn.row_factory = sqlite3.Row  # Set row factory to Row for dictionary-like access
#     cur = conn.cursor()
#     sql = f"SELECT * FROM users WHERE {field_name} = ?"
#     cur.execute(sql, (field_value,))
#     result = cur.fetchone()
#     if result:
#         return dict(result)
#     return None


# def get_all_user_data_by_memgpt_id(conn, memgpt_user_id):
#     """
#     Retrieve all user data by MemGPT user ID.

#     Parameters:
#     - conn: The database connection object.
#     - memgpt_user_id: The MemGPT user ID.

#     Returns:
#     - A dictionary containing all user details if found, None otherwise.
#     """
#     print('get_all_user_data_by_memgpt_id() called')
#     user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
#     print('get_all_user_data_by_memgpt_id result:', user_data)
#     return user_data

# def get_user_data_by_memgpt_id(conn, memgpt_user_id):
#     """
#     Retrieve the MemGPT user API key, default agent key, and VAPI assistant ID for a given MemGPT user ID.

#     Parameters:
#     - conn: The database connection object.
#     - memgpt_user_id: The MemGPT user ID.

#     Returns:
#     - A tuple containing the MemGPT user API key, default agent key, and VAPI assistant ID if found, 
#       (None, None, None) otherwise.
#     """
#     print('get_user_data_by_memgpt_id() called')
#     sql = """
#     SELECT memgpt_user_api_key, default_agent_key, vapi_assistant_id 
#     FROM users 
#     WHERE memgpt_user_id = ?
#     """
#     cur = conn.cursor()
#     cur.execute(sql, (memgpt_user_id,))
#     result = cur.fetchone()
#     print('get_user_data_by_memgpt_id result: ', result)
#     # Return a tuple including the vapi_assistant_id
#     return (result[0], result[1], result[2]) if result else (None, None, None)



# def get_memgpt_user_id(conn, auth0_user_id):
#     """
#     Retrieve the MemGPT user ID for a given Auth0 user ID.

#     Parameters:
#     - conn: The database connection object.
#     - auth0_user_id: The Auth0 user ID.

#     Returns:
#     - The MemGPT user ID if found, None otherwise.
#     """
#     print('get_memgpt_user_id() called')
#     sql = """SELECT memgpt_user_id FROM users WHERE auth0_user_id = ?"""
#     cur = conn.cursor()
#     cur.execute(sql, (auth0_user_id,))
#     result = cur.fetchone()
#     return result[0] if result else None

# def get_memgpt_user_id_and_api_key(conn, auth0_user_id):
#     """
#     Retrieve the MemGPT user ID and API key for a given Auth0 user ID.

#     Parameters:
#     - conn: The database connection object.
#     - auth0_user_id: The Auth0 user ID.

#     Returns:
#     - A tuple containing the MemGPT user ID and API key if found, (None, None) otherwise.
#     """
#     print('get_memgpt_user_id_and_api_key() called')
#     sql = """SELECT memgpt_user_id, memgpt_user_api_key FROM users WHERE auth0_user_id = ?"""
#     cur = conn.cursor()
#     cur.execute(sql, (auth0_user_id,))
#     result = cur.fetchone()
#     print('get_memgpt_user_id_and_api_key() result: ', result)
#     return (result[0], result[1]) if result else (None, None)

# def get_user_data(conn, auth0_user_id):
#     """
#     Retrieve the MemGPT user ID, API key, email, phone, default agent key, and VAPI assistant ID for a given Auth0 user ID.

#     Parameters:
#     - conn: The database connection object.
#     - auth0_user_id: The Auth0 user ID.

#     Returns:
#     - A tuple containing the MemGPT user ID, API key, email, phone, default agent key, and VAPI assistant ID if found,
#       (None, None, None, None, None, None) otherwise.
#     """
#     print('get_user_data() called')
#     sql = """
#     SELECT memgpt_user_id, memgpt_user_api_key, email, phone, default_agent_key, vapi_assistant_id 
#     FROM users 
#     WHERE auth0_user_id = ?
#     """
#     cur = conn.cursor()
#     cur.execute(sql, (auth0_user_id,))
#     result = cur.fetchone()
#     print('get_user_data result: ', result)
#     return (result[0], result[1], result[2], result[3], result[4], result[5]) if result else (None, None, None, None, None, None)

# def get_user_data_by_phone(conn, phone_number):
#     """
#     Retrieve user data by a phone number, ignoring differences in formatting or country codes.

#     Parameters:
#     - conn: The database connection object.
#     - phone_number: The phone number, possibly including formatting and country code.

#     Returns:
#     - A tuple containing the user details if found, None otherwise.
#     """
#     print('get_user_data_by_phone() called')
#     # Remove all non-numeric characters from the phone number for comparison
#     normalized_phone_number = ''.join(filter(str.isdigit, phone_number))[-10:]  # Get last 10 digits, typical for US numbers
#     sql = """
#     SELECT memgpt_user_id, memgpt_user_api_key, email, phone, default_agent_key, vapi_assistant_id 
#     FROM users 
#     WHERE phone LIKE ?
#     """
#     cur = conn.cursor()
#     # Use SQL LIKE clause with wildcard to match the last 10 digits
#     cur.execute(sql, ('%' + normalized_phone_number,))
#     result = cur.fetchone()
#     print('get_user_data_by_phone result: ', result)
#     return (result[0], result[1], result[2], result[3], result[4], result[5]) if result else (None, None, None, None, None, None)

# def get_user_data_by_email(conn, email):
#     """
#     Retrieve user data by an email address.

#     Parameters:
#     - conn: The database connection object.
#     - email: The email address to search for.

#     Returns:
#     - A tuple containing the user details if found, None otherwise.
#     """
#     print('get_user_data_by_email() called')
#     sql = """
#     SELECT memgpt_user_id, memgpt_user_api_key, email, phone, default_agent_key, vapi_assistant_id 
#     FROM users 
#     WHERE email LIKE ?
#     """
#     cur = conn.cursor()
#     # Use SQL LIKE clause to match the email exactly
#     cur.execute(sql, (email,))
#     result = cur.fetchone()
#     print('get_user_data_by_email result: ', result)
#     return (result[0], result[1], result[2], result[3], result[4], result[5]) if result else (None, None, None, None, None, None)

# def print_all_records(conn):
#     """Print all records from the users table."""
#     print('printing all records from users table: ')
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM users")
#     rows = cur.fetchall()
#     for row in rows:
#         print(row)

# def print_tables(conn):
#     """Print a list of all tables in the database."""
#     print('printing all tables in database: ')
#     cur = conn.cursor()
#     cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
#     tables = cur.fetchall()
#     for table in tables:
#         print(table[0])



# def set_value_to_none_by_email(conn, email, column_index):
#     columns = ["memgpt_user_id", "memgpt_user_api_key", "email", "phone", "default_agent_key", "vapi_assistant_id"]
#     if column_index < 0 or column_index >= len(columns):
#         print(f"Invalid column index: {column_index}. No action taken.")
#         return
#     column_name = columns[column_index]
#     sql = f"UPDATE users SET {column_name} = NULL WHERE email = ?"
#     try:
#         cur = conn.cursor()
#         cur.execute(sql, (email,))
#         conn.commit()
#         print(f"Successfully set {column_name} to None for user with email {email}.")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         conn.rollback()

# def main():
#     parser = argparse.ArgumentParser(description="Set a specific user field to None in the database by email.")
#     parser.add_argument("email", type=str, help="The email address of the user to modify.")
#     parser.add_argument("column_index", type=int, help="The index of the column to set to None (0-based).")
    
#     args = parser.parse_args()
    
#     conn = create_connection()
#     if conn is not None:
#         set_value_to_none_by_email(conn, args.email, args.column_index)
#         conn.close()
#     else:
#         print("Failed to establish a database connection.")

# if __name__ == "__main__":
#     main()