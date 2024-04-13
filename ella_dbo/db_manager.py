# ella_dbo/db_manager.py

import os
import sqlite3

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


def create_table(conn):
    """Create tables to store user info, given a connection."""
    print('Creating table users...')
    create_users_table_sql = """CREATE TABLE IF NOT EXISTS users (
                                    id INTEGER PRIMARY KEY,
                                    auth0_user_id TEXT NOT NULL,
                                    memgpt_user_id TEXT,
                                    memgpt_user_api_key TEXT,
                                    email TEXT,
                                    name TEXT,
                                    roles TEXT,
                                    default_agent_key TEXT  -- Store only the default agent key
                                );"""
    try:
        c = conn.cursor()
        c.execute(create_users_table_sql)
    except sqlite3.Error as e:
        print(e)



def upsert_user(conn, auth0_user_id, **kwargs):
    print('upsert_user() called')
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users WHERE auth0_user_id = ?", (auth0_user_id,))
        exists = cur.fetchone()[0] > 0
        fields = list(kwargs.keys())  # Convert keys to a list
        values = list(kwargs.values())  # Convert values to a list

        if exists:
            updates = ', '.join(f"{k} = ?" for k in fields)
            sql = f"UPDATE users SET {updates} WHERE auth0_user_id = ?"
            params = values + [auth0_user_id]  # Combine the values and auth0_user_id into a single list
            cur.execute(sql, params)  # Pass the SQL statement and the combined parameters as a tuple
        else:
            fields_str = ', '.join(fields)
            placeholders = ', '.join(['?'] * len(kwargs))
            sql = f"INSERT INTO users (auth0_user_id, {fields_str}) VALUES (?, {placeholders})"
            params = [auth0_user_id] + values  # Combine auth0_user_id and values into a single list
            cur.execute(sql, params)  # Pass the SQL statement and the combined parameters as a tuple

        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        cur.close()


# Usage:
#upsert_user(conn, auth0_user_id, email=user_email, name=user_name, roles=roles_str, memgpt_user_id=memgpt_user_id, memgpt_user_api_key=memgpt_user_api_key, default_agent_key=default_agent_key)


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

def get_memgpt_user_data(conn, auth0_user_id):
    """
    Retrieve the MemGPT user ID, API key, and default agent key for a given Auth0 user ID.

    Parameters:
    - conn: The database connection object.
    - auth0_user_id: The Auth0 user ID.

    Returns:
    - A tuple containing the MemGPT user ID, API key, and default agent key if found, (None, None, None) otherwise.
    """
    print('get_memgpt_user_data() called')
    sql = """SELECT memgpt_user_id, memgpt_user_api_key, default_agent_key FROM users WHERE auth0_user_id = ?"""
    cur = conn.cursor()
    cur.execute(sql, (auth0_user_id,))
    result = cur.fetchone()
    print('gget_memgpt_user_data result: ', result)
    return (result[0], result[1], result[2]) if result else (None, None, None)


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
