import sqlite3
import time
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
def insert_data(cursor, ID, data):
    """
    Inserts data into the correct columns.
    - ID is inserted into the ID column.
    - Current time (seconds since epoch) is inserted into the TIMESTAMP column.
    - Remaining data is inserted according to the passed dictionary.
    """
    # Get the current timestamp (seconds since the epoch)
    timestamp = int(time.time() * 1000)
    
    # Prepare the column-value mapping
    columns = ['ID', 'TIMESTAMP'] + list(data.keys())
    values = [ID, timestamp] + list(data.values())
    
    # Generate SQL statement dynamically
    column_names = ", ".join(columns)
    placeholders = ", ".join(["?"] * len(values))
    sql = f"INSERT INTO data ({column_names}) VALUES ({placeholders})"
    
    # Execute SQL
    cursor.execute(sql, values)

data_1 = {
    'T01': 99.1,
    'H01': 88.8,
}

# Insert data for ID = 1
insert_data(cursor, 1, data_1)
del data_1

# Example data dictionary for ID = 99
data_99 = {
    'LI1': False,
}

# Insert data for ID = 99
insert_data(cursor, 99, data_99)
del data_99

data_0 = {
    'EN1': 1.1,
    'EN2': 2.2,
    'EN3': 3.3,
    'EN4': 4.4,
    'EN5': 5.5,
    'T00': 0.5,
    'H00': 0.5,
}

# Insert data for ID = 0
insert_data(cursor, 0, data_0)
del data_0

# Commit and close the connection
conn.commit()
conn.close()