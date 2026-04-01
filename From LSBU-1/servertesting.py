from flask import *
from flask_cors import CORS # type: ignore
from waitress import serve # type: ignore
import threading
import sqlite3
import time

def insert_data(ID, data):
    conn = sqlite3.connect('/var/www/example.db')
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
    conn.commit()
    conn.close()

app = Flask(__name__)
app2 = Flask(__name__)
CORS(app2)

@app2.route('/', methods=['POST'])
def handle_request():
    # Retrieve fields from POST form data
    command = request.form.get('command')
    code = request.form.get('code')

    # Print the received fields to the console
    print("Received command:", command)
    print("Received code:", code)

    # Respond to the client
    return "Fields printed to console.", 200

@app.route("/data", methods=["POST"])
def data():
    print("Data received")
    data = request.get_data().decode("utf-8")  # Decode the raw byte data to string
    
    # Remove 'data=' from the beginning of the string if it's there
    if data.startswith("data="):
        data = data[5:]  # Remove the first 5 characters ("data=")
    
    # Split the data by commas
    data_list = data.split(",")
    if data_list[0] == "99":
        value = int(data_list[1])
        print("99 (Light), " + str(value))
        datas = {
            f"LI1": data_list[1]
        }
        insert_data(99, datas)
        del datas
        return "Received", 200
    
    # Convert the first element to an integer and the rest to floats
    data_list = [int(data_list[0])] + [float(i.strip()) for i in data_list[1:]]
    data_lists = [int(time.time() * 1000)] + data_list
    print(data_lists)  # Output the converted list

    if data_list[0] > 5 or data_list[0] < 0:
        return "ID out of range", 416
    
    datas = {
        f"T{data_list[0]:02d}": data_list[1],
        f"H{data_list[0]:02d}": data_list[2],
    }
    insert_data(data_list[0], datas)
    del datas

    return "Received and Saved", 200



@app.route("/")
def home():
    return "Hello World", 200

def run_flask():
    #app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
    serve(app, host="0.0.0.0", port=8000)

def run_flask2():
    #app2.run(host="0.0.0.0", port=3440, debug=False, threaded=True)
    
    serve(app2, host="0.0.0.0", port=3440)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_flask2).start()