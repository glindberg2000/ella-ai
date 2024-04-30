import pg8000

try:
    connection = pg8000.connect(user="memgpt", password="memgpt", host="127.0.0.1", port="5432", database="memgpt")

    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    row = cursor.fetchone()
    print("Connected to database!")
    print("PostgreSQL version:", row[0])

except (Exception, pg8000.Error) as error:
    print("Error while connecting to PostgreSQL", error)
finally:
    # closing database connection.
    if connection:
        cursor.close()
        connection.close()
        print("PostgreSQL connection closed")
