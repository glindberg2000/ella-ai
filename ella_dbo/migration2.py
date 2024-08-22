import sqlite3
import os

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(current_dir, "ella_dbo", "database.db")

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Check if local_timezone column exists
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'local_timezone' not in columns:
            print("Adding local_timezone column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN local_timezone TEXT")

        # Check and add other potentially missing columns
        if 'location' not in columns:
            print("Adding location column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN location TEXT")

        if 'reminders' not in columns:
            print("Adding reminders column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN reminders TEXT")

        if 'recurrence' not in columns:
            print("Adding recurrence column to events table...")
            cursor.execute("ALTER TABLE events ADD COLUMN recurrence TEXT")

        conn.commit()
        print("Migration completed successfully.")

        # Print the structure of the events table after migration
        cursor.execute("PRAGMA table_info(events)")
        print("Table structure after migration:")
        for column in cursor.fetchall():
            print(f"Column: {column[1]}, Type: {column[2]}")
            
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()