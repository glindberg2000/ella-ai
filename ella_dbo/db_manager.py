# ella_dbo/db_manager.py

import os
import sqlite3
import uuid

# Get the directory of the current file (__file__ is the path to the current script)
current_dir = os.path.dirname(__file__)

# Define the database file path as relative to the current directory
DB_FILE = os.path.join(current_dir, "database.db")


def create_connection():
    """Create and return a database connection to the SQLite database specified by db_file."""
    print('Creating connection to database...')
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        print(e)
    return conn

def get_user_data_by_memgpt_id(conn, memgpt_user_id):
    """
    Retrieve the MemGPT user API key, default agent key, and VAPI assistant ID for a given MemGPT user ID.

    Parameters:
    - conn: The database connection object.
    - memgpt_user_id: The MemGPT user ID.

    Returns:
    - A tuple containing the MemGPT user API key, default agent key, and VAPI assistant ID if found, 
      (None, None, None) otherwise.
    """
    print('get_user_data_by_memgpt_id() called')
    sql = """
    SELECT memgpt_user_api_key, default_agent_key, vapi_assistant_id 
    FROM users 
    WHERE memgpt_user_id = ?
    """
    cur = conn.cursor()
    cur.execute(sql, (memgpt_user_id,))
    result = cur.fetchone()
    print('get_user_data_by_memgpt_id result: ', result)
    # Return a tuple including the vapi_assistant_id
    return (result[0], result[1], result[2]) if result else (None, None, None)

def create_table(conn):
    """Create tables to store user info, given a connection."""
    print('Creating table users...')
    create_users_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        auth0_user_id TEXT NOT NULL,
        memgpt_user_id TEXT,
        memgpt_user_api_key TEXT,
        email TEXT,
        name TEXT,
        roles TEXT,
        default_agent_key TEXT,  -- Store only the default agent key
        vapi_assistant_id TEXT   -- Store field for storing VAPI assistant ID
    );"""
    try:
        c = conn.cursor()
        c.execute(create_users_table_sql)
        print("Table created successfully or already exists.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

def upsert_user(conn, auth0_user_id, **kwargs):
    print('upsert_user() called')
    cur = conn.cursor()
    try:
        # Convert UUIDs to strings for storage
        converted_kwargs = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in kwargs.items()}
        
        cur.execute("SELECT COUNT(*) FROM users WHERE auth0_user_id = ?", (auth0_user_id,))
        exists = cur.fetchone()[0] > 0
        fields = list(converted_kwargs.keys())
        values = list(converted_kwargs.values())

        if exists:
            updates = ', '.join(f"{k} = ?" for k in fields)
            sql = f"UPDATE users SET {updates} WHERE auth0_user_id = ?"
            params = values + [auth0_user_id]
            cur.execute(sql, params)
        else:
            fields_str = ', '.join(fields)
            placeholders = ', '.join('?' * len(converted_kwargs))
            sql = f"INSERT INTO users (auth0_user_id, {fields_str}) VALUES (?, {placeholders})"
            params = [auth0_user_id] + values
            cur.execute(sql, params)

        conn.commit()
        print('User upserted successfully.')
    except Exception as e:
        print(f"Database error during upsert: {e}")
    finally:
        cur.close()



def get_memgpt_user_id(conn, auth0_user_id):
    """
    Retrieve the MemGPT user ID for a given Auth0 user ID.

    Parameters:
    - conn: The database connection object.
    - auth0_user_id: The Auth0 user ID.

    Returns:
    - The MemGPT user ID if found, None otherwise.
    """
    print('get_memgpt_user_id() called')
    sql = """SELECT memgpt_user_id FROM users WHERE auth0_user_id = ?"""
    cur = conn.cursor()
    cur.execute(sql, (auth0_user_id,))
    result = cur.fetchone()
    return result[0] if result else None


def get_memgpt_user_id_and_api_key(conn, auth0_user_id):
    """
    Retrieve the MemGPT user ID and API key for a given Auth0 user ID.

    Parameters:
    - conn: The database connection object.
    - auth0_user_id: The Auth0 user ID.

    Returns:
    - A tuple containing the MemGPT user ID and API key if found, (None, None) otherwise.
    """
    print('get_memgpt_user_id_and_api_key() called')
    sql = """SELECT memgpt_user_id, memgpt_user_api_key FROM users WHERE auth0_user_id = ?"""
    cur = conn.cursor()
    cur.execute(sql, (auth0_user_id,))
    result = cur.fetchone()
    print('get_memgpt_user_id_and_api_key() result: ', result)
    return (result[0], result[1]) if result else (None, None)

def get_user_data(conn, auth0_user_id):
    """
    Retrieve the MemGPT user ID, API key, default agent key, and VAPI assistant ID for a given Auth0 user ID.

    Parameters:
    - conn: The database connection object.
    - auth0_user_id: The Auth0 user ID.

    Returns:
    - A tuple containing the MemGPT user ID, API key, default agent key, and VAPI assistant ID if found, 
      (None, None, None, None) otherwise.
    """
    print('get_user_data() called')
    # Include vapi_assistant_id in the SELECT clause
    sql = """
    SELECT memgpt_user_id, memgpt_user_api_key, default_agent_key, vapi_assistant_id 
    FROM users 
    WHERE auth0_user_id = ?
    """
    cur = conn.cursor()
    cur.execute(sql, (auth0_user_id,))
    result = cur.fetchone()
    print('get_user_data result: ', result)
    # Return a tuple including the vapi_assistant_id
    return (result[0], result[1], result[2], result[3]) if result else (None, None, None, None)



def print_all_records(conn):
    """Print all records from the users table."""
    print('printing all records from users table: ')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    for row in rows:
        print(row)

def print_tables(conn):
    """Print a list of all tables in the database."""
    print('printing all tables in database: ')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    for table in tables:
        print(table[0])


# close the database connection if needed
def close_connection(conn):
    """Close a database connection."""
    print('closing connection')
    if conn:
        conn.close()


def main():
    print('main() called')
    # Create a database connection
    conn = create_connection()
    print_tables (conn)
    print_all_records(conn)

if __name__ == "__main__":
    main()
