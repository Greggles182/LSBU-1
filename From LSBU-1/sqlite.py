import sqlite3
from time import sleep
# Connect to an SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('example.db')

# Create a cursor object using the cursor() method
cursor = conn.cursor()

# Create table
cursor.execute('''
CREATE TABLE IF NOT EXISTS data (
    TIMESTAMP INTEGER,
    ID INTEGER,
    EN1 REAL,
    EN2 REAL,
    EN3 REAL,
    EN4 REAL,
    EN5 REAL,
    LI1 BOOLEAN,
    T00 REAL,
    H00 REAL,
    T01 REAL,
    H01 REAL,
    T02 REAL,
    H02 REAL,
    T03 REAL,
    H03 REAL,
    T04 REAL,
    H04 REAL,
    T05 REAL,
    H05 REAL
)
''')


# # Insert a row of data

# cursor.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
# sleep(5)
# cursor.execute("INSERT INTO stocks VALUES ('2006-01-06','SELL','RHAT',100,35.34)")

# Save (commit) the changes
conn.commit()

# Close the connection
conn.close()