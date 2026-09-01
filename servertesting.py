from flask import *
from flask_cors import CORS
from waitress import serve
from ntplib import NTPClient
import os, time as time, json, copy, shutil, logging, platform, sqlite3, requests, threading, sys, subprocess, zipfile, re, struct, psutil, smbus # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from glob import glob
from thingsboard_uploader import start_thingsboard_uploader

# Define the NTP server
NTP_SERVER = "pool.ntp.org"
DB_TABLE_PATTERN = r"[A-Za-z0-9_-]+"
DB_TABLE_MAX_LENGTH = 50

def sanitize_db_table(value):
    if not isinstance(value, str):
        return "data"
    sanitized = "".join(re.findall(DB_TABLE_PATTERN, value))[:DB_TABLE_MAX_LENGTH]
    return sanitized or "data"

def get_images_path():
    return f'/var/www/html/images/{config_data["dbTable"]}/'

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
    print("This does not work on Windows.")
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
    
    PORT = '/dev/ttyUSB0'
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
                "current_draw_mA": (current_draw['data']/10),
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
    config_data = {
        "logInterval": 300,
        "dbTable": "data",
        "SHT": True,
        "CamEnable": "none",
        "thingsboard_enabled": False,
        "thingsboard_url": "",
        "thingsboard_token": "",
        "batch_size": 100,
        "check_interval": 5
    }
    with open(config_path, "w") as file:
        json.dump(config_data, file, indent=4)
        file.close()
    log_and_print(f"Created new config file at {config_path} with default values.")
else:
    with open(config_path, "r") as file:
        config_data = json.load(file)
        file.close()
    original_db_table = config_data.get("dbTable")
    config_data["dbTable"] = sanitize_db_table(original_db_table)
    if config_data["dbTable"] != original_db_table:
        log_and_print("Invalid dbTable in config; removed invalid characters or truncated its length.", "warning")
        with open(config_path, "w") as file:
            json.dump(config_data, file, indent=4)
    # Add ThingsBoard fields if they don't exist (for backwards compatibility)
    if "thingsboard_enabled" not in config_data:
        config_data["thingsboard_enabled"] = False
    if "thingsboard_url" not in config_data:
        config_data["thingsboard_url"] = ""
    if "thingsboard_token" not in config_data:
        config_data["thingsboard_token"] = ""
    if "batch_size" not in config_data:
        config_data["batch_size"] = 100
    if "check_interval" not in config_data:
        config_data["check_interval"] = 5



logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
CORS(app)



images_path = get_images_path()
log_and_print(f"Loaded config data: {config_data}")



def insert_data(ID, data):
    try:
        with sqlite3.connect(db_path) as conn:
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

            images_path = get_images_path()
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
            log_and_print("Performed factory reset", "info")
            log_and_print("WILL NOT DELETE Wifi name or other factory values", "warning")
            log_and_print("LOG IN USING SSH TO CHANGE THESE VALUES.", "warning")
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
    usb_base = '/media/'
    usb_mounts = [os.path.join(usb_base, d) for d in os.listdir(usb_base) if os.path.ismount(os.path.join(usb_base, d))]
    if not usb_mounts:
        return "No USB device detected"

    usb_path = usb_mounts[0]  # Use the first detected USB device
    log_and_print(f"Using USB device at {usb_path} for export", "info")
    export_datetime = time.strftime("_%Y-%m-%d_%H-%M-%S")
    export_folder = os.path.join(usb_path, f"export_{export_datetime}")
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)

    for file_path in files_to_copy:
        if os.path.exists(file_path):
            try:
                # Preserve folder structure relative to /var/www/html
                rel_path = os.path.relpath(file_path, "/var/www/html")
                dest_path = os.path.join(export_folder, rel_path)
                dest_dir = os.path.dirname(dest_path)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                shutil.copy(file_path, dest_path)
                log_and_print(f"copied {file_path} to {dest_path}", "info")
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
        log_and_print(f"Received export command: {command}, code: {code}", "info")
        images_path = get_images_path()
        export_datetime = time.strftime("_%Y-%m-%d_%H-%M-%S")

        try:
            if command == "ALLZIP":
                files_to_zip = [
                    "/var/www/html/example.db",
                    "/var/www/html/data.json",
                    "/var/www/html/server.log",
                    "/var/www/html/camera.log"
                ]
                image_files = glob(f"{images_path}*")
                log_and_print(f"ALLZIP: found {len(image_files)} image files for zipping", "info")
                files_to_zip.extend(image_files)

                output_zip = f"/var/www/html/dl/export_{export_datetime}_{config_data['dbTable']}.zip"
                os.makedirs(os.path.dirname(output_zip), exist_ok=True)

                with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in files_to_zip:
                        if not os.path.exists(file):
                            log_and_print(f"ALLZIP: skipping missing file: {file}", "warning")
                            continue
                        try:
                            arcname = os.path.relpath(file, start="/var/www/html")
                            log_and_print(f"ALLZIP: adding {file} as {arcname}", "debug")
                            zipf.write(file, arcname)
                        except Exception:
                            logging.exception(f"ALLZIP: failed to add {file} to zip")
                log_and_print(f"Created zip file: {output_zip}", "info")
                return f"U:/dl/export_{export_datetime}_{config_data['dbTable']}.zip"

            elif command == "TIMELAPSE":
                output_dir = "/var/www/html/dl"
                os.makedirs(output_dir, exist_ok=True)
                input_pattern = f"{images_path}*.jpg"
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-framerate", "7.5",
                    "-pattern_type", "glob",
                    "-i", input_pattern,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    f"/var/www/html/dl/timelapse_{export_datetime}_{config_data['dbTable']}.mp4"
                ]
                log_and_print(f"TIMELAPSE: running ffmpeg with command: {' '.join(ffmpeg_cmd)}", "info")
                try:
                    res = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, timeout=300)
                    if res.stdout:
                        logging.info(f"ffmpeg stdout: {res.stdout.strip()}")
                    if res.stderr:
                        logging.info(f"ffmpeg stderr: {res.stderr.strip()}")
                    log_and_print("Timelapse created successfully", "info")
                    return f"U:/dl/timelapse_{export_datetime}_{config_data['dbTable']}.mp4"
                except subprocess.CalledProcessError as e:
                    log_and_print(f"Failed to create timelapse (non-zero exit): {e.returncode}", "error")
                    logging.info(f"ffmpeg stdout: {e.stdout}")
                    logging.info(f"ffmpeg stderr: {e.stderr}")
                    return f"Error creating timelapse: ffmpeg failed (rc={e.returncode})", 500
                except Exception:
                    logging.exception("TIMELAPSE: unexpected error creating timelapse")
                    return "Error creating timelapse: unexpected error", 500

            elif command == "USB":
                files_to_copie = [
                    "/var/www/html/example.db",
                    "/var/www/html/data.json",
                    "/var/www/html/server.log",
                    "/var/www/html/camera.log"
                ]
                image_files = glob(f"{images_path}**/*", recursive=True)
                image_files = [f for f in image_files if os.path.isfile(f)]
                log_and_print(f"USB: preparing to copy {len(image_files)} image files and {len(files_to_copie)} base files", "info")
                files_to_copie.extend(image_files)
                # Log first few files for debug
                for idx, fpath in enumerate(files_to_copie[:20]):
                    log_and_print(f"USB candidate [{idx}]: {fpath}", "info")
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
                    with sqlite3.connect(db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT * FROM {Table}")
                        rows = cursor.fetchall()
                        if not rows:
                            log_and_print("export-csv: no rows found", "warning")
                            return "No data to export", 404

                        output_dir = "/var/www/html/dl"
                        os.makedirs(output_dir, exist_ok=True)
                        csv_file_path = os.path.join(output_dir, f"export_{export_datetime}_{config_data['dbTable']}.csv")

                        import csv

                        # Get column names
                        cursor.execute(f"PRAGMA table_info({Table})")
                        columns = [info[1] for info in cursor.fetchall()]
                        log_and_print(f"export-csv: columns = {columns}", "debug")
                        ts_index = None
                        if "TIMESTAMP" in columns:
                            ts_index = columns.index("TIMESTAMP")

                        with open(csv_file_path, "w", newline="") as csv_file:
                            writer = csv.writer(csv_file)
                            # Write header
                            writer.writerow(columns)

                            for row_idx, row in enumerate(rows):
                                row = list(row)
                                if ts_index is not None and row[ts_index] is not None:
                                    try:
                                        # Convert milliseconds to Excel datetime with full precision (float)
                                        excel_date = ((float(row[ts_index]) / 1000.0) / 86400.0) + 25569.0
                                        # Keep high precision, avoid scientific notation by formatting as decimal string
                                        row[ts_index] = format(excel_date, 'f')
                                    except Exception:
                                        logging.exception(f"export-csv: failed converting TIMESTAMP on row {row_idx}")
                                        row[ts_index] = ""
                                writer.writerow(row)

                        log_and_print(f"Exported data to CSV: {csv_file_path} (rows: {len(rows)})", "info")
                        return f"U:/dl/export_{export_datetime}_{config_data['dbTable']}.csv", 200

                except sqlite3.Error as e:
                    log_and_print(f"Database error during export: {e}", "error")
                    logging.exception("export-csv: sqlite error")
                    return f"Database error: {e}", 500
                except Exception:
                    logging.exception("export-csv: unexpected error")
                    return "Unexpected error during export", 500

            else:
                return "Invalid command", 400

        except Exception:
            logging.exception("Unhandled exception in export handler")
            return "Server error", 500

    else:
        return "Server is running. This page does not do anything of value.", 200





@app.route('/configs', methods=['GET','POST'])
def configs():
    global config_data
    required_fields = {
        "logInterval": int,
        "dbTable": str,
        "SHT": bool,
        "CamEnable": str,
        "thingsboard_enabled": bool,
        "thingsboard_url": str,
        "thingsboard_token": str,
        "batch_size": int,
        "check_interval": int
    }

    valid_cam_modes = {"none", "door", "doorcam"}

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

        original_db_table = datar["dbTable"]
        datar["dbTable"] = sanitize_db_table(original_db_table)
        if datar["dbTable"] != original_db_table:
            log_and_print("Removed invalid characters from dbTable or truncated its length.", "warning")

        # Check for negative logInterval
        if datar["logInterval"] < 0:
            log_and_print(f"logInterval is negative: {datar['logInterval']}", "error")
            return "logInterval must be non-negative.", 422

        # Validate CamEnable value
        if datar["CamEnable"] not in valid_cam_modes:
            log_and_print(f"Invalid CamEnable value: {datar['CamEnable']}", "error")
            return "Invalid CamEnable value. Must be 'none', 'door', or 'doorcam'.", 422

        # Validate ThingsBoard settings
        if datar["thingsboard_enabled"]:
            if not datar["thingsboard_url"]:
                log_and_print("ThingsBoard enabled but URL not provided", "error")
                return "ThingsBoard URL required when enabled", 422
            if not datar["thingsboard_token"]:
                log_and_print("ThingsBoard enabled but token not provided", "error")
                return "ThingsBoard token required when enabled", 422
        
        # Validate batch_size and check_interval
        if datar["batch_size"] < 1:
            log_and_print(f"batch_size must be positive: {datar['batch_size']}", "error")
            return "batch_size must be at least 1", 422
        
        if datar["check_interval"] < 1:
            log_and_print(f"check_interval must be positive: {datar['check_interval']}", "error")
            return "check_interval must be at least 1", 422

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
        if config_data["SHT"]:
            required_fields = ["EN1", "EN2", "EN3", "EN4", "EN5", "T00", "H00"]
            if not all(field in data for field in required_fields):
                log_and_print("Missing required data", "warning")
                return "Missing required data", 422
            datas = {field: float(data[field]) for field in required_fields}
        if not config_data["SHT"]:
            required_fields = ["EN1", "EN2", "EN3", "EN4", "EN5"]
            if not all(field in data for field in required_fields):
                log_and_print("Missing required data", "warning")
                return "Missing required data", 422
            datas = {field: float(data[field]) for field in required_fields}

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
        if config_data["SHT"]:
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

                #log_and_print(f"Temp: {Temperature}C  H: {Humidity}%")
            except Exception:
                log_and_print(f"Failed to process sensor data", "error")
                continue

        try:
            if client.connect():
                values = []
                for address, name in REGISTER_MAP.items():
                    value = read_register(client, address)
                    if value is not None:
                        #log_and_print(f"{name}: {value:.2f}")
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
            ):
                url = "http://localhost:8000/intdata"
                if config_data["SHT"]:
                    data = {
                        "EN1": values[0],
                        "EN2": values[1],
                        "EN3": values[2],
                        "EN4": values[3],
                        "EN5": values[4],
                        "T00": Temperature,
                        "H00": Humidity,
                    }
                elif not config_data["SHT"]:
                    data = {
                        "EN1": values[0],
                        "EN2": values[1],
                        "EN3": values[2],
                        "EN4": values[3],
                        "EN5": values[4],
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
        #log_and_print(temp)
        if temp > 60:                            # Check temperature threshhold, in degrees celcius
            fan.ChangeDutyCycle(100)             # Set fan duty based on temperature, 100 is max speed and 0 is min speed or off.
        if temp < 55:                            # If temperature is below threshold
            fan.ChangeDutyCycle(0)               # Set fan duty to 0% if temperature is below threshold
        time.sleep(5)                            # Sleep for 5 seconds

@app.route('/remove-table-and-images', methods=['POST'])
def remove_table_and_images():
    data = request.get_json()
    log_and_print("Received request to remove table and images", "info")
    
    table = data.get('table')
    if not table or not sanitize_db_table(table) == table:
        log_and_print(f"Invalid table name provided: {table}", "error")
        return "Invalid table name", 400

    log_and_print(f"Removing table and images for: {table}", "info")
    
    # Check if the table is the active one and update config if necessary
    if table == config_data["dbTable"]:
        log_and_print(f"Table '{table}' is the active table. Updating config to use default table.", "warning")
        config_data_mod = copy.deepcopy(config_data)
        config_data_mod["dbTable"] = "data"
        try:
            response = requests.post("http://127.0.0.1:8000/configs", json=config_data_mod)
            if response.status_code == 200:
                log_and_print("Successfully updated config to use default table.", "info")
            else:
                log_and_print(f"Failed to update config. Response: {response.status_code}, {response.text}", "error")
        except Exception as e:
            log_and_print(f"Error updating config: {e}", "error")

    # Remove images
    images_path = f'/var/www/html/images/{table}/'
    if os.path.exists(images_path):
        log_and_print(f"Removing images at path: {images_path}", "info")
        for root, dirs, files in os.walk(images_path, topdown=False):
            for f in files:
                try:
                    os.unlink(os.path.join(root, f))
                    log_and_print(f"Deleted file: {os.path.join(root, f)}", "info")
                except Exception as e:
                    log_and_print(f"Error deleting file {os.path.join(root, f)}: {e}", "error")
            for d in dirs:
                try:
                    shutil.rmtree(os.path.join(root, d))
                    log_and_print(f"Deleted directory: {os.path.join(root, d)}", "info")
                except Exception as e:
                    log_and_print(f"Error deleting directory {os.path.join(root, d)}: {e}", "error")
        try:
            os.rmdir(images_path)
            log_and_print(f"Deleted images folder: {images_path}", "info")
        except Exception as e:
            log_and_print(f"Error deleting images folder {images_path}: {e}", "error")
    else:
        log_and_print(f"Images path does not exist: {images_path}", "warning")

    # Remove table from database
    try:
        log_and_print(f"Attempting to remove table '{table}' from database.", "info")
        db_path = "/var/www/html/example.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.commit()
        conn.close()
        log_and_print(f"Successfully removed table '{table}' from database.", "info")
        return "Table and images removed", 200
    except Exception as e:
        log_and_print(f"Error removing table '{table}' from database: {e}", "error")
        return f"Error removing table/images: {e}", 500
    

if __name__ == "__main__":
    if OSCHECK:
        configure_ip()
        time.sleep(10)
    threading.Thread(target=run_flask).start()
    if OSCHECK:
        threading.Thread(target=collect_results).start()
        threading.Thread(target=fan).start()
        if config_data["CamEnable"] in ("door", "doorcam"):
            def start_camera_thread():
                subprocess.run(["sudo", "python3", "/home/pi/Camera-handle.py"])
            log_and_print("Camera/door sensor enabled, starting camera thread")
            try:
                threading.Thread(target=start_camera_thread).start()
            except ImportError as e:
                log_and_print(f"Failed to start camera module: {e}", "error")
        
        # Start ThingsBoard uploader if enabled
        if config_data.get("thingsboard_enabled", True):
            thingsboard_config = {
                "thingsboard_url": config_data.get("thingsboard_url", ""),
                "thingsboard_token": config_data.get("thingsboard_token", ""),
                "database_path": db_path,
                "state_path": "/var/www/html/thingsboard_upload_state.json",
                "batch_size": config_data.get("batch_size", 100),
                "check_interval": config_data.get("check_interval", 5),
                "http_timeout": 20
            }
            thingsboard_uploader = start_thingsboard_uploader(
                thingsboard_config
            )
            if thingsboard_uploader:
                log_and_print("ThingsBoard uploader started successfully")
            else:
                log_and_print("ThingsBoard uploader failed to start (misconfigured)", "error")
    while True:
        time.sleep(5)

