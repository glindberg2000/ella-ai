import sqlite3
import argparse

def list_users(database, table):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    
    # Fetch column headers
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Fetch rows
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    conn.close()

    if rows:
        print(f"\n{table} Table Contents:")
        print(" | ".join(columns))  # Print the column headers
        print("-" * len(" | ".join(columns)))  # Print a separator

        for index, row in enumerate(rows):
            print(f"{index + 1}: {row}")
    else:
        print(f"No data found in {table}.")

    return rows, columns

def delete_row(database, table, row_id):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
    conn.commit()
    conn.close()
    print(f"\nRow with id {row_id} deleted from {table}.")
    list_users(database, table)  # Print the entire table after deletion

def delete_field(database, table, row_id, field):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {table} SET {field}=NULL WHERE id=?", (row_id,))
    conn.commit()
    
    # Fetch and print the updated row
    cursor.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,))
    updated_row = cursor.fetchone()
    conn.close()
    print(f"\nField '{field}' from row with id {row_id} in {table} set to NULL.")
    print(f"Updated row: {updated_row}")

def main():
    parser = argparse.ArgumentParser(description='List and manage the users table in a SQLite database.')
    parser.add_argument('--database', type=str, default='database.db', help='The path to the SQLite database file (default: database.db).')
    parser.add_argument('--table', type=str, default='users', help='The table name from which to delete (default: users).')

    args = parser.parse_args()

    rows, columns = list_users(args.database, args.table)
    if not rows:
        return

    selection = input("\nEnter the number of the row to manage, or 'q' to quit: ")
    
    if selection.lower() == 'q':
        print("Exiting.")
        return

    try:
        selected_index = int(selection) - 1
        if 0 <= selected_index < len(rows):
            row = rows[selected_index]
            row_id = row[0]  # Assuming the first column is the ID
            action = input(f"\nSelected row: {row}\nChoose an action - 'd' to delete the row, 'f' to clear a field, 'q' to quit: ")

            if action.lower() == 'd':
                delete_row(args.database, args.table, row_id)
            elif action.lower() == 'f':
                print("\nColumns:")
                for idx, column in enumerate(columns):
                    print(f"{idx + 1}: {column}")
                
                field_selection = input("Enter the number or name of the field to clear (set to NULL): ")
                
                if field_selection.isdigit():
                    field_index = int(field_selection) - 1
                    if 0 <= field_index < len(columns):
                        field = columns[field_index]
                    else:
                        print("Invalid field selection.")
                        return
                else:
                    field = field_selection

                if field in columns:
                    delete_field(args.database, args.table, row_id, field)
                else:
                    print(f"Field '{field}' does not exist.")
            else:
                print("Exiting.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input. Please enter a valid number.")

if __name__ == '__main__':
    main()