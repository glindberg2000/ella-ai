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
    """Create a table to store user info, given a connection."""
    print('Creating table users...')
    create_table_sql = """CREATE TABLE IF NOT EXISTS users (
                            id integer PRIMARY KEY,
                            auth0_user_id text NOT NULL,
                            memgpt_user_id text,
                            memgpt_user_api_key text,
                            email text,
                            name text,
                            roles text
                          );"""
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)



def upsert_user(
    conn,
    auth0_user_id,
    email=None,
    name=None,
    roles=None,
    memgpt_user_id=None,
    memgpt_user_api_key=None,
):
    print('upsert_user() called')
    cur = conn.cursor()

    # Check if the user already exists
    cur.execute("SELECT COUNT(*) FROM users WHERE auth0_user_id = ?", (auth0_user_id,))
    user_exists = cur.fetchone()[0] > 0

    # Initialize SQL update parts and parameters list
    update_parts = []
    params = []

    if email is not None:
        update_parts.append("email = ?")
        params.append(email)
    if name is not None:
        update_parts.append("name = ?")
        params.append(name)
    if roles is not None:
        roles_str = ", ".join(roles) if isinstance(roles, list) else roles
        update_parts.append("roles = ?")
        params.append(roles_str)
    if memgpt_user_id is not None:
        update_parts.append("memgpt_user_id = ?")
        params.append(memgpt_user_id)
    if memgpt_user_api_key is not None:
        update_parts.append("memgpt_user_api_key = ?")
        params.append(memgpt_user_api_key)

    # Execute update or insert based on whether the user exists
    if user_exists:
        print('upsert_user(): Updating existing record')
        sql = f"UPDATE users SET {', '.join(update_parts)} WHERE auth0_user_id = ?"
        params.append(auth0_user_id)  # Append at the end for the WHERE clause
    else:
        print('upsert_user(): Inserting new record')
        fields = ["auth0_user_id"] + [field.split("=")[0].strip() for field in update_parts]  # Adjusted for field extraction
        placeholders = ["?"] * (len(params) + 1)  # +1 for the auth0_user_id itself
        sql = f"INSERT INTO users ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
        params = [auth0_user_id] + params  # Ensure auth0_user_id is first for the INSERT

    # Print the SQL command and parameters for debugging
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    cur.execute(sql, params)

    # Commit changes outside of the if-else block to cover both paths
    try:
        print('upsert_user(): Committing changes to the database')
        conn.commit()
    except Exception as e:
        print(f"Error committing changes to the database: {e}")

    # Read and print the updated or inserted record from the database
    cur.execute("SELECT * FROM users WHERE auth0_user_id = ?", (auth0_user_id,))
    updated_user = cur.fetchone()
    print(f"Updated user: {updated_user}")





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
