from flask import *
from flask_cors import CORS
from waitress import serve
from ntplib import NTPClient
import os, time as time, json, copy, shutil, logging, platform, sqlite3, requests, threading, sys, subprocess, zipfile, re
from glob import glob

# Define the NTP server
NTP_SERVER = "pool.ntp.org"

images_path = '/var/www/html/images/' # used when factory resetting

# Function to get the current time from NTP server
def get_ntp_time():
    c = NTPClient()
    response = c.request(NTP_SERVER)
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(response.tx_time))

# Function to update the system time and PiJuice time
def update_time():
    # Get the current time from NTP server
    ntp_time_str = get_ntp_time()  # e.g. "2025-04-05 16:28:37"
    log_and_print(f"NTP Time: {ntp_time_str}")

    if OSCHECK and net:
        # Update the system time
        os.system(f"sudo date -s '{ntp_time_str}'")

        # Convert to struct_time
        ntp_time = time.strptime(ntp_time_str, '%Y-%m-%d %H:%M:%S')

        # Create RTC time dictionary for PiJuice
        rtc_time = {
            'second': ntp_time.tm_sec,
            'minute': ntp_time.tm_min,
            'hour': ntp_time.tm_hour,
            'weekday': ntp_time.tm_wday + 1,  # Python: Monday = 0, PiJuice: Monday = 1
            'day': ntp_time.tm_mday,
            'month': ntp_time.tm_mon,
            'year': ntp_time.tm_year,
            'subsecond': 0,
            'daylightsaving': 'NONE',
            'storeoperation': False
        }

        # Set PiJuice RTC time
        result = pijuice.rtcAlarm.SetTime(rtc_time)
        if result['error'] != 'NO_ERROR':
            log_and_print(f"Failed to set PiJuice RTC time: {result['error']}")
        else:
            log_and_print("System time and PiJuice RTC time updated successfully.")

def get_sd_card_usage():
    sd_path = "/"  # Root directory (adjust if necessary)
    total, used, free = shutil.disk_usage(sd_path)
    
    return {
        "total_GB": round(total / (1024 ** 3), 2),      
        "used_GB": round(used / (1024 ** 3), 2),
        "free_GB": round(free / (1024 ** 3), 2),
        "used_percent": round((used / total) * 100, 2)
    }




if platform.system() == "Windows":
    OSCHECK = False
    print("This does not work on Windows you fucking idiot.")
    sys.exit(1)

else:
    print("Running on Linux or another OS")
    OSCHECK = True
    db_path = "/var/www/html/example.db"
    log_path = "/var/www/html/server.log"
    config_path = "/var/www/html/data.json"
    #SHT3x - Sensirion Temperature Humidity sensor modules and setup.
    import smbus, psutil # type: ignore
    from pijuice import PiJuice # type: ignore
    pijuice = PiJuice(1, 0x14)
    bus = smbus.SMBus(1)

    # SHT3x hex adres
    SHT3x_ADDR		= 0x44
    SHT3x_SS		= 0x2C
    SHT3x_HIGH		= 0x06
    SHT3x_READ		= 0x00

    #SDM120M - Eastron SDM120 Modbus Energy Meter modules and setup.
    from pymodbus.client import ModbusSerialClient  # type: ignore
    import struct

    # Configuration
    REGISTER_MAP = {
        0x0000: "Voltage (Volts)",
        0x0006: "Current (Amps)",
        0x000C: "Active Power (Watts)",
        0x0156: "Energy (kWh)",
        0x0046: "Hertz (Hz)",
    }
    
    PORT = '/dev/ttyUSB0'#/dev/        `ttyUSB0'  # Replace with your port (e.g., '/dev/ttyUSB0' on Linux)
    BAUDRATE = 9600
    PARITY = 'N'
    STOPBITS = 1
    BYTESIZE = 8
    TIMEOUT = 1
    client = ModbusSerialClient(
        port=PORT,
        baudrate=BAUDRATE,
        parity=PARITY,
        stopbits=STOPBITS,
        bytesize=BYTESIZE,
        timeout=TIMEOUT,
    )
    def read_register(client, address):
        try:
            response = client.read_input_registers(address=address, count=2)
            if not response.isError():
                # Combine registers in the correct order (high byte first)
                #inputArray = [response.registers[1], response.registers[0]]
                int32Val = response.registers[1] + (response.registers[0] << 16)
                decoded_value = struct.unpack('f', struct.pack('i', int32Val))[0]
                return decoded_value#, inputArray, int32Val
            else:
                raise Exception(f"Error reading register {address}: {response}")
        except Exception as e:
            log_and_print(f"Error reading register {address}: {e}")
            return None
    # Function to get PiJuice stats (using correct methods)
    def get_pijuice_stats():
        try:
            # Getting battery charge level
            battery_charge = pijuice.status.GetChargeLevel()
            # Getting battery voltage
            battery_voltage = pijuice.status.GetBatteryVoltage()
            # Getting battery temperature
            battery_temperature = pijuice.status.GetBatteryTemperature()
            # Getting current draw
            current_draw = pijuice.status.GetBatteryCurrent()

            stats = {
                "battery_charge_level": battery_charge['data'],
                "battery_voltage_mV": battery_voltage['data'],
                "battery_temperature_C": battery_temperature['data'],
                "current_draw_mA": current_draw['data'],
            }

            return stats

        except Exception as e:
            log_and_print(f"Error fetching PiJuice stats: {e}")
            return None

    # Function to get Raspberry Pi CPU temperature
    def get_cpu_temp():
        try:
            # Read the CPU temperature from the system file
            temp = float(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000
            return temp
        except Exception as e:
            log_and_print(f"Error fetching CPU temperature: {e}")
            return None

    # Function to get system memory usage with accurate values (Old function was shit)
    def get_memory_info():
        try:
            memory = psutil.virtual_memory()
            total_mb = memory.total / (1024 ** 2)
            available_mb = memory.available / (1024 ** 2)
            used_mb = total_mb - available_mb
            memory_stats = {
                "total_memory_MB": round(total_mb, 1),
                "used_memory_MB": round(used_mb, 1),
                "free_memory_MB": round(available_mb, 1),
                "memory_usage_percent": memory.percent
            }
            return memory_stats
        except Exception as e:
            log_and_print(f"Error fetching memory info: {e}")
            return None

    # Function to get system CPU usage
    def get_cpu_usage():
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            return {"cpu_usage_percent": cpu_usage}
        except Exception as e:
            log_and_print(f"Error fetching CPU usage: {e}")
            return None

    # Combine PiJuice and system stats into a single dictionary
    def get_system_and_pijuice_stats():
        pijuice_stats = get_pijuice_stats()
        cpu_temp = get_cpu_temp()
        memory_info = get_memory_info()
        cpu_usage = get_cpu_usage()
        sd_usage = get_sd_card_usage()

        system_stats = {
            "pijuice_stats": pijuice_stats,
            "cpu_temperature_C": cpu_temp,
            "cpu_usage_percent": cpu_usage["cpu_usage_percent"],
            "memory_info": memory_info,
            "sd_info": sd_usage
        }

        return system_stats

def log_and_print(message, level="info"):
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)

if not os.path.exists(config_path):
    config_data = {"logInterval": 300, "dbTable": "data", "SHT": True, "CamEnable": False} # Remeber to change this to the correct data
    with open(config_path, "w") as file:
        json.dump(config_data, file, indent=4)
        file.close()
    log_and_print(f"Created new config file at {config_path} with default values.")
else:
    with open(config_path, "r") as file:
        config_data = json.load(file)
        file.close()



logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
CORS(app)




log_and_print(f"Loaded config data: {config_data}")

def insert_data(ID, data):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {config_data["dbTable"]} (
            TIMESTAMP INTEGER,
            ID INTEGER,
            EN1 REAL,
            EN2 REAL,
            EN3 REAL,
            EN4 REAL,
            EN5 REAL,
            LI1 REAL,
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
        timestamp = int(time.time() * 1000)
        columns = ['ID', 'TIMESTAMP'] + list(data.keys())
        values = [ID, timestamp] + list(data.values())
        column_names = ", ".join(columns)
        placeholders = ", ".join(["?"] * len(values))
        sql = f"INSERT INTO {config_data['dbTable']} ({column_names}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        log_and_print(f"Inserted data: {values}")
    except sqlite3.Error as e:
        log_and_print(f"Database error: {e}", "error")
    except Exception as e:
        log_and_print(f"Exception in insert_data: {e}", "error")
    finally:
        conn.close()

def restartSoftware():
    subprocess.Popen(["sudo", "systemctl", "restart", "startup.service"])

@app.route('/', methods=['POST', 'GET'])
def handle_request():
    if request.method == 'POST':
        command = request.form.get('command')
        code = request.form.get('code')
        log_and_print(f"Received command: {command}, code: {code}")
        if command == "CLEARLOG":
            with open(log_path, "w") as file:
                file.write("")
                file.close()
            with open("/var/www/html/camera.log", "w") as file:
                file.write("")
                file.close()
            log_and_print("Log cleared", "info")
            return "Log cleared", 200
        elif command == "UPDATETIME":
            try:
                update_time()
                return "Time updated", 200
            except Exception as e:
                log_and_print(f"Error updating time: {e}", "error")
                return f"Error updating time: {e}", "error", 500
        elif command == "SHUTDOWN":
            log_and_print("Shutting down system", "warning")
            if OSCHECK:
                pijuice.power.SetPowerOff(120)
                os.system("sudo shutdown -h 0")
            else:
                return "Something is very fucked", 599
            return "Shutting down system", 200
        elif command == "FACTORYRESET":
            os.remove(config_path)
            os.remove(db_path)
            with open(log_path, "w") as file:
                file.write("")
                file.close()
            with open("/var/www/html/camera.log", "w") as file:
                file.write("")
                file.close()

            

            # Create folder if missing
            if not os.path.exists(images_path):
                try:
                    os.makedirs(images_path)
                    log_and_print(f"Created missing directory: {images_path}")
                except Exception as e:
                    log_and_print(f"Failed to create directory {images_path}: {e}")
            else:
                # If folder exists, clean it out
                for root, dirs, files in os.walk(images_path, topdown=False):
                    for f in files:
                        try:
                            os.unlink(os.path.join(root, f))
                        except Exception as e:
                            log_and_print(f"Error deleting file {f}: {e}")
                    for d in dirs:
                        try:
                            shutil.rmtree(os.path.join(root, d))
                        except Exception as e:
                            log_and_print(f"Error deleting directory {d}: {e}")
            log_and_print("Performed factory reset", "warning")
            log_and_print("WILL NOT DELETE AP NAME, OR REMOTE DEBUG TOKEN.", "error")
            log_and_print("LOG IN USING SSH TO CHANGE THESE VALUES.", "error")
            restartSoftware()
            return "Factory reset performed", 200
        elif command == "RESTARTSOFTWARE":
            log_and_print("Restarting software", "warning")
            restartSoftware()
            return "Restarting software", 200
        return "Invalid command", 400
    else:
        return "Server is running. This page does not do anything of value.", 200


def get_device_for_mount(mount_point):
    result = subprocess.run(['lsblk', '-o', 'NAME,MOUNTPOINT', '-P'], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if f'MOUNTPOINT="{mount_point}"' in line:
            for part in line.split():
                if part.startswith('NAME='):
                    return '/dev/' + part.split('=')[1].strip('"')
    return None

def copy_files_to_usb(files_to_copy):
    import os
    usb_base = '/media/'
    usb_mounts = [os.path.join(usb_base, d) for d in os.listdir(usb_base) if os.path.ismount(os.path.join(usb_base, d))]
    if not usb_mounts:
        return "No USB device detected"

    usb_path = usb_mounts[0]  # Use the first detected USB device

    for file_path in files_to_copy:
        if os.path.exists(file_path):
            try:
                shutil.copy(file_path, usb_path)
                log_and_print(f"copied {file_path} to {usb_path}", "info")
            except Exception as e:
                return f"Failed to copy {file_path}: {e}"
        else:
            return f"File not found: {file_path}"

    # Eject the USB device
    try:
        device_path = get_device_for_mount(usb_path)
        if not device_path:
            return "Copied files, but could not determine device for eject"
        subprocess.run(['udisksctl', 'unmount', '-b', device_path], check=True)
        subprocess.run(['udisksctl', 'power-off', '-b', device_path], check=True)
    except Exception as e:
        return f"Copied files, but failed to eject USB: {e}"

    return "SUCCESS"

######################################################################################

@app.route('/export', methods=['POST', 'GET'])
def handle_export_request():
    if request.method == 'POST':
        command = request.form.get('command')
        code = request.form.get('code')
        log_and_print(f"Received export command: {command}, code: {code}")
        if command == "ALLZIP":
            # List of specific files to include
            files_to_zip = [
                "/var/www/html/example.db",
                "/var/www/html/data.json",
                "/var/www/html/server.log",
                "/var/www/html/camera.log"
            ]

            # Add all files from the images directory
            image_files = glob("/var/www/html/images/*")
            files_to_zip.extend(image_files)

            # Output zip file path
            output_zip = "/var/www/html/dl/all.zip"

            # Create the zip file
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files_to_zip:
                    # Add with a relative path so it's neat inside the zip
                    arcname = os.path.relpath(file, start="/var/www/html")
                    zipf.write(file, arcname)

            log_and_print(f"Created zip file: {output_zip}")
            return "U:/dl/all.zip"
        elif command == "TIMELAPSE":
            # Ensure output directory exists
            output_dir = "/var/www/html/dl"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            # Build ffmpeg command
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",  # <-- this line forces overwrite
                "-framerate", "7.5",
                "-pattern_type", "glob",
                "-i", "/var/www/html/images/*.jpg",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "/var/www/html/dl/timelapse.mp4"
            ]

            try:
                subprocess.run(ffmpeg_cmd, check=True)
                log_and_print("Timelapse created successfully", "info")
                return "U:/dl/timelapse.mp4"
            except Exception as e:
                log_and_print(f"Failed to create timelapse: {e}", "error")
                return f"Error creating timelapse: {e}", 500
        elif command == "USB":
            files_to_copie = [
                "/var/www/html/example.db",
                "/var/www/html/data.json",
                "/var/www/html/server.log",
                "/var/www/html/camera.log"
            ]

            # Add all files from the images directory
            image_files = glob("/var/www/html/images/*")
            files_to_copie.extend(image_files)
            result = copy_files_to_usb(files_to_copie)
            if result == "SUCCESS":
                log_and_print("Files copied to USB successfully", "info")
                return "I:Files copied to USB successfully, please remove USB drive", 200
            else:
                log_and_print(f"Failed to copy files to USB: {result}", "error")
                return f"Error copying files to USB: {result}", 500
    
        elif command == "export-csv":
            Table = config_data["dbTable"]
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {Table}")
                rows = cursor.fetchall()
                if not rows:
                    return "No data to export", 404

                output_dir = "/var/www/html/dl"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                csv_file_path = os.path.join(output_dir, "export.csv")
                import csv
                with open(csv_file_path, "w", newline="") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerows(rows)
                conn.close()
                log_and_print(f"Exported data to CSV: {csv_file_path}", "info")
                return f"U:/dl/export.csv", 200
            except sqlite3.Error as e:
                log_and_print(f"Database error during export: {e}", "error")
                return f"Database error: {e}", 500
            except Exception as e:
                log_and_print(f"Unexpected error during export: {e}", "error")
                return f"Unexpected error: {e}", 500
    
        else:
            return "Invalid command", 400
    else:
        return "Server is running. This page does not do anything of value.", 200





@app.route('/configs', methods=['GET','POST'])
def configs():
    global config_data
    required_fields = {
        "logInterval": int,
        "dbTable": str,
        "SHT": bool,
        "CamEnable": bool
    }

    if request.method == 'GET':
        return jsonify(config_data), 200

    elif request.method == 'POST':
        datar = request.get_json()

        # Validate JSON data
        if not isinstance(datar, dict):
            log_and_print(f"Invalid JSON format: {datar}", "error")
            return "Invalid JSON format", 400

        for field, expected_type in required_fields.items():
            if field not in datar:
                log_and_print(f"Missing required field: {field}", "error")
                return f"Missing required field: {field}", 422
            if not isinstance(datar[field], expected_type):
                log_and_print(f"Incorrect type for '{field}'. Expected {expected_type.__name__}, got {type(datar[field]).__name__}", "error")
                return f"Incorrect type for '{field}'. Expected {expected_type.__name__}, got {type(datar[field]).__name__}", 422

        # Check for special characters in dbTable (allow only alphanumeric and underscores)
        if not re.match(r'^[A-Za-z0-9_]+$', datar["dbTable"]):
            log_and_print(f"dbTable contains invalid characters: {datar['dbTable']}", "error")
            return "dbTable contains invalid characters. Only letters, numbers, and underscores are allowed.", 422

        # Check for negative logInterval
        if datar["logInterval"] < 0:
            log_and_print(f"logInterval is negative: {datar['logInterval']}", "error")
            return "logInterval must be non-negative.", 422

        log_and_print(f"Received valid config data: {datar}")
        with open(config_path, "w") as file:
            json.dump(datar, file, indent=4)
            file.close()
        config_data = copy.deepcopy(datar)
        return "Saved config data", 200


@app.route("/status", methods=["GET"])
def status():
    if not OSCHECK:
        return "Something is very fucked.", 500
    else:
        stat = get_system_and_pijuice_stats()
    return jsonify(stat), 200


@app.route("/data", methods=["POST"])
def data():
    log_and_print("Data received")
    try:
        data = request.get_data().decode("utf-8")
        if data.startswith("data="):
            data = data[5:]
        data_list = data.split(",")
        data_list = [int(data_list[0])] + [float(i.strip()) for i in data_list[1:]]
        log_and_print(f"Processed data: {data_list}")
        if data_list[0] > 90:
            return "ID out of range", 416
        datas = {
            f"T{data_list[0]:02d}": data_list[1],
            f"H{data_list[0]:02d}": data_list[2],
        }
        insert_data(data_list[0], datas)
        return "Received and Saved", 200
    except (ValueError, IndexError) as e:
        log_and_print(f"Error processing data: {e}", "error")
        return "Invalid data format", 400
    except Exception as e:
        log_and_print(f"Unexpected error: {e}", "error")
        return "Server error", 500

#Add ID option for this at some point (Just fucking don't. It will definetly break shit)
@app.route("/Lidata", methods=["POST"])
def Lidata():
    log_and_print("Light data received")
    try:
        data = request.get_data().decode("utf-8")
        if data.startswith("data="):
            data = data[5:]
        LiTime = int(data)
        log_and_print(f"Processed time data: {LiTime}")
        datas = {
            f"LI1": LiTime,
        }
        insert_data(99, datas)
        return "Received and Saved", 200
    except (ValueError, IndexError) as e:
        log_and_print(f"Error processing data: {e}", "error")
        return "Invalid data format", 400
    except Exception as e:
        log_and_print(f"Unexpected error: {e}", "error")
        return "Server error", 500
    
@app.route("/intdata", methods=["POST"])
def intdata():
    try:
        data = request.get_json()
        if data is None:
            log_and_print("No JSON data received", "warning")
            return "No JSON data received", 400
        required_fields = ["EN1", "EN2", "EN3", "EN4", "EN5", "T00", "H00"]
        if not all(field in data for field in required_fields):
            log_and_print("Missing required data", "warning")
            return "Missing required data", 422
        datas = {field: float(data[field]) for field in required_fields}
        if not config_data["SHT"]:
            del datas["T00"]
            del datas["H00"]

        #log_and_print(f"Received JSON data: {datas}")
        insert_data(0, datas)
        return "Success", 200
    except ValueError as e:
        log_and_print(f"Invalid data type: {e}", "error")
        return "Invalid data type", 400
    except Exception as e:
        log_and_print(f"Unexpected error: {e}", "error")
        return "Server error", 500

@app.route('/tables', methods=['GET'])
def list_tables():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({"tables": tables}), 200
    except Exception as e:
        log_and_print(f"Error listing tables: {e}", "error")
        return jsonify({"error": str(e)}), 500


def run_flask():
    log_and_print("Starting Flask server")
    serve(app, host="0.0.0.0", port=8000)
    log_and_print("Flask server started")


def collect_results():
    while True:
        values = None  # Ensure values is always defined
        Temperature = None
        Humidity = None
        try:
            # MS to SL
            bus.write_i2c_block_data(SHT3x_ADDR, SHT3x_SS, [0x06])
            time.sleep(0.2)

            # Read out data
            data = bus.read_i2c_block_data(SHT3x_ADDR, SHT3x_READ, 6)
        except Exception:
            log_and_print(f"Failed to read SHT3x", "error")
            time.sleep(config_data["logInterval"])
            continue

        try:
            # Divide data into counts
            t_data = data[0] << 8 | data[1]
            h_data = data[3] << 8 | data[4]

            # Convert counts to Temperature/Humidity
            Humidity = round(100.0 * float(h_data) / 65535.0, 2)
            Temperature = round(-45.0 + 175.0 * float(t_data) / 65535.0, 2)

            log_and_print(f"Temp: {Temperature}C  H: {Humidity}%")
        except Exception:
            log_and_print(f"Failed to process sensor data", "error")
            continue

        try:
            if client.connect():
                values = []
                for address, name in REGISTER_MAP.items():
                    value = read_register(client, address)
                    if value is not None:
                        log_and_print(f"{name}: {value:.2f}")
                        values.append(value)
                    else:
                        log_and_print(f"Failed to read {name}", "warning")
                client.close()
            else:
                log_and_print("Failed to connect to SDM120M", "error")
        except Exception:
            log_and_print(f"Error reading SDM120M registers", "error")
            continue

        try:
            if (
                values is not None
                and len(values) >= 5
                and Temperature is not None
                and Humidity is not None
            ):
                url = "http://localhost:8000/intdata"  # Change to your actual Flask server address
                data = {
                    "EN1": values[0],
                    "EN2": values[1],
                    "EN3": values[2],
                    "EN4": values[3],
                    "EN5": values[4],
                    "T00": Temperature,
                    "H00": Humidity,
                }
                response = requests.post(url, json=data)
                log_and_print("Server Response:", response.text)
            else:
                log_and_print("Insufficient SDM120M values or sensor data to send to server", "warning")
        except Exception:
            log_and_print(f"Failed to send data to server", "error")

        log_interval = config_data.get("logInterval", 300)  # Default to 300 if missing
        if isinstance(log_interval, int) and log_interval > 0:
            time.sleep(log_interval)
        else:
            log_and_print(f"Invalid logInterval value: {log_interval}. Using default value of 300.", "warning")
            time.sleep(300)

        # Here are some common SDM120M registers:

        #     0x0000: Voltage (Volts)
        #     0x0006: Current (Amps)
        #     0x000C: Active Power (Watts)
        #     0x0012: Apparent Power (VA)
        #     0x0018: Reactive Power (VAR)
        #     0x0046: Total Energy (kWh)

        # Refer to the SDM120M manual for the full register map.

# Function to check the IP address
def check_ip():
    # Run the command to get the IP address
    result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ip_address = result.stdout.decode().strip()  # Get the output as a string
    log_and_print(f"Current IP address: {ip_address}")

    return ip_address

# Function to add IP address if necessary
def configure_ip():
    ip_address = check_ip()
    
    # Check if the IP address contains '192.168.5.1'
    if '192.168.5.1' not in ip_address:
        # Add the IP address and restart hostapd service
        subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.5.1/24', 'dev', 'wlan0'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'hostapd.service'])
        log_and_print("IP address added and hostapd service restarted.")
    else:
        log_and_print("IP address 192.168.5.1 is already configured.")

#Test network
try:
    response = requests.get('https://www.google.com/')
    log_and_print('Network is working.')
    net = True
except:
    log_and_print('Network is down.')
    net = False


def fan():
    import RPi.GPIO as IO          # type: ignore # Calling GPIO to allow use of the GPIO pins

    IO.setwarnings(False)          # Do not show any GPIO warnings
    IO.setmode (IO.BCM)            # BCM pin numbers - PIN8 as ‘GPIO14’
    IO.setup(14,IO.OUT)            # Initialize GPIO14 as our fan output pin
    fan = IO.PWM(14,100)           # Set GPIO14 as a PWM output, with 100Hz frequency (this should match your fans specified PWM frequency)
    fan.start(0)                   # Generate a PWM signal with a 0% duty cycle (fan off)

    def get_temp():                              # Function to read in the CPU temperature and return it as a float in degrees celcius
        output = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True)
        temp_str = output.stdout.decode()
        try:
            return float(temp_str.split('=')[1].split('\'')[0])
        except (IndexError, ValueError):
            raise RuntimeError('Could not get temperature')

    while True:                                     # Execute loop forever
        temp = get_temp()                        # Get the current CPU temperature
        log_and_print(temp)
        if temp > 60:                            # Check temperature threshhold, in degrees celcius
            fan.ChangeDutyCycle(100)             # Set fan duty based on temperature, 100 is max speed and 0 is min speed or off.
        if temp < 55:                            # If temperature is below threshold
            fan.ChangeDutyCycle(0)               # Set fan duty to 0% if temperature is below threshold
        time.sleep(5)                            # Sleep for 5 seconds

if __name__ == "__main__":
    if OSCHECK:
        configure_ip()
        time.sleep(10)
    threading.Thread(target=run_flask).start()
    if OSCHECK:
        threading.Thread(target=collect_results).start()
        threading.Thread(target=fan).start()
        if config_data["CamEnable"]:
            def start_camera_thread():
                subprocess.run(["sudo", "python3", "/home/pi/Camera-handle.py"])
            log_and_print("Camera enabled, starting camera thread")
            try:
                threading.Thread(target=start_camera_thread).start()
            except ImportError as e:
                log_and_print(f"Failed to start camera module: {e}", "error")
    while True:
        time.sleep(5)

