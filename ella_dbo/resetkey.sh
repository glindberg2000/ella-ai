#!/bin/bash

# Path to the SQLite database
DB_PATH="./database.db"

# SQL command to update the row
SQL_COMMAND="
UPDATE users
SET default_agent_key = NULL
WHERE email = 'realcryptoplato@gmail.com';
"

# Execute the SQL command using sqlite3
sqlite3 "$DB_PATH" <<EOF
$SQL_COMMAND
EOF

echo "Update completed successfully."

# SQL command to select the updated row with headers
SELECT_COMMAND="
.headers on
SELECT * FROM users
WHERE email = 'realcryptoplato@gmail.com';
"

# Execute the SQL command to print the updated row with headers
sqlite3 "$DB_PATH" <<EOF
$SELECT_COMMAND
EOF
