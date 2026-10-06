from flask import *
from flask_cors import CORS
from waitress import serve
from ntplib import NTPClient
import os, time as time, json, copy, shutil, logging, platform, sqlite3, requests, threading, sys, subprocess, zipfile, re, struct, psutil, smbus # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from glob import glob
from thingsboard_uploader import start_thingsboard_uploader
from bounded_logging import SizeCappedFileHandler
from network_utils import get_session, resolve_interface, get_route_interface, interface_exists
from pijuice import PiJuice # type: ignore
from pymodbus.client import ModbusSerialClient  # type: ignore

# Clipper only needs the APN for the PPP peer in almost all cases.
# The user/password/auth fields are intentionally ignored here.
DEFAULT_CARRIER_APNS = {
    "giffgaff": {"apn": "giffgaff.com"},
    "EE": {"apn": "everywhere"},
    "Vodafone": {"apn": "internet"},
    "O2": {"apn": "mobile.o2.co.uk"},
    "Three": {"apn": "three.co.uk"},
}
IDENTITY_FIELDS = [
    "thingsboard_url",
    "thingsboard_token",
    "cellular_enabled",
    "active_carrier",
    "custom_apn",
    "logger_ID",
]

# Define the NTP server
NTP_SERVER = "pool.ntp.org"
DB_TABLE_PATTERN = r"[A-Za-z0-9_-]+"
DB_TABLE_MAX_LENGTH = 50

db_path = "/var/www/html/example.db"
log_path = "/var/www/html/server.log"
config_path = "/var/www/html/data.json"
identity_path = "/var/www/html/device_identity.json"
carrier_apns_path = "/var/www/html/carrier_apns.json"

if platform.system() == "Windows":
    print("This does not work on Windows.")
    sys.exit(1)

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
    logging.info(f"NTP Time: {ntp_time_str}")

    if net:
        # Update the system time
        subprocess.run(['sudo', 'date', '-s', ntp_time_str], check=True)

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
            logging.info(f"Failed to set PiJuice RTC time: {result['error']}")
        else:
            logging.info("System time and PiJuice RTC time updated successfully.")

def get_sd_card_usage():
    sd_path = "/"  # Root directory (adjust if necessary)
    total, used, free = shutil.disk_usage(sd_path)
    
    return {
        "total_GB": round(total / (1024 ** 3), 2),      
        "used_GB": round(used / (1024 ** 3), 2),
        "free_GB": round(free / (1024 ** 3), 2),
        "used_percent": round((used / total) * 100, 2)
    }


pijuice = PiJuice(1, 0x14)
bus = smbus.SMBus(1)

# SHT3x hex adres
SHT3x_ADDR		= 0x44
SHT3x_SS		= 0x2C
SHT3x_HIGH		= 0x06
SHT3x_READ		= 0x00

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
        logging.info(f"Error reading register {address}: {e}")
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
        logging.info(f"Error fetching PiJuice stats: {e}")
        return None

# Function to get Raspberry Pi CPU temperature
def get_cpu_temp():
    try:
        # Read the CPU temperature from the system file
        temp = float(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000
        return temp
    except Exception as e:
        logging.info(f"Error fetching CPU temperature: {e}")
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
        logging.info(f"Error fetching memory info: {e}")
        return None

# Function to get system CPU usage
def get_cpu_usage():
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        return {"cpu_usage_percent": cpu_usage}
    except Exception as e:
        logging.info(f"Error fetching CPU usage: {e}")
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



server_log_handler = SizeCappedFileHandler(log_path, encoding="utf-8")
server_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(server_log_handler)


def load_identity():
    if os.path.exists(identity_path):
        with open(identity_path, "r") as file:
            return json.load(file)
    return {}


def save_identity():
    identity = {key: config_data[key] for key in IDENTITY_FIELDS if key in config_data}
    temporary_path = identity_path + ".tmp"
    with open(temporary_path, "w") as file:
        json.dump(identity, file, indent=4)
    os.replace(temporary_path, identity_path)


def write_clipper_apn(apn):
    """Update /etc/ppp/peers/clipper so the PPP peer uses the selected APN."""
    if not apn:
        logging.warning("No APN provided for Clipper peer; leaving PPP config unchanged.")
        return False

    peer_path = "/etc/ppp/peers/clipper"
    try:
        with open(peer_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except FileNotFoundError:
        logging.warning(f"PPP peer file not found at {peer_path}; cannot update APN.")
        return False
    except Exception as e:
        logging.error(f"Failed to read PPP peer file at {peer_path}: {e}")
        return False

    updated = []
    changed = False
    target_prefix = 'connect "/usr/sbin/chat -v -f /etc/chatscripts/gprs -T '
    apn_line = f'{target_prefix}{apn}"\n'

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('connect "/usr/sbin/chat -v -f /etc/chatscripts/gprs -T '):
            updated.append(apn_line)
            changed = True
        else:
            updated.append(line)

    if not changed:
        updated.append(apn_line)

    try:
        with open(peer_path, "w", encoding="utf-8") as file:
            file.writelines(updated)
        logging.info(f"Updated PPP peer APN in {peer_path} to '{apn}'")
        return True
    except Exception as e:
        logging.error(f"Failed to write APN to {peer_path}: {e}")
        return False


if not os.path.exists(carrier_apns_path):
    with open(carrier_apns_path, "w") as file:
        json.dump(DEFAULT_CARRIER_APNS, file, indent=4)
    logging.info(f"Created default carrier APN table at {carrier_apns_path}")

with open(carrier_apns_path, "r") as file:
    carrier_apns = json.load(file)

legacy_identity = {}
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
        "check_interval": 300,
        "uplink_mode": "auto",
        "cellular_enabled": False,
        "active_carrier": "",
        "custom_apn": {"apn": ""},
        "logger_ID": ""
    }
    with open(config_path, "w") as file:
        json.dump(config_data, file, indent=4)
        file.close()
    logging.info(f"Created new config file at {config_path} with default values.")
else:
    with open(config_path, "r") as file:
        config_data = json.load(file)
        file.close()
    legacy_identity = {key: config_data[key] for key in IDENTITY_FIELDS if key in config_data}
    original_db_table = config_data.get("dbTable")
    config_data["dbTable"] = sanitize_db_table(original_db_table)
    if config_data["dbTable"] != original_db_table:
        logging.warning("Invalid dbTable in config; removed invalid characters or truncated its length.")
        with open(config_path, "w") as file:
            json.dump(config_data, file, indent=4)
    # Add ThingsBoard and uplink fields if they don't exist (for backwards compatibility)
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
    if "uplink_mode" not in config_data:
        config_data["uplink_mode"] = "auto"
    if "cellular_enabled" not in config_data:
        config_data["cellular_enabled"] = False
    if "active_carrier" not in config_data:
        config_data["active_carrier"] = ""
    if "custom_apn" not in config_data:
        config_data["custom_apn"] = {"apn": ""}
    if "logger_ID" not in config_data:
        config_data["logger_ID"] = ""

config_data.setdefault("thingsboard_url", "")
config_data.setdefault("thingsboard_token", "")
config_data.setdefault("logger_ID", "")

identity = load_identity()
legacy_identity = {
    key: config_data[key]
    for key in IDENTITY_FIELDS
    if key in config_data and config_data[key] not in (None, "", {})
}

moved_any = False
for key in IDENTITY_FIELDS:
    if key in config_data:
        config_data.pop(key, None)
        moved_any = True

for key, value in legacy_identity.items():
    if identity.get(key) != value:
        identity[key] = value
        moved_any = True

config_data.update(identity)
if moved_any:
    logging.info("Moved identity settings out of data.json")

if not os.path.exists(identity_path) or any(key not in identity for key in IDENTITY_FIELDS):
    save_identity()

temporary_path = config_path + ".tmp"
with open(temporary_path, "w") as file:
    json.dump(config_data, file, indent=4)
os.replace(temporary_path, config_path)


app = Flask(__name__)
CORS(app)



images_path = get_images_path()
logging.info(f"Loaded config data: {config_data}")



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
            logging.info(f"Inserted data: {values}")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    except Exception as e:
        logging.error(f"Exception in insert_data: {e}")
    finally:
        conn.close()

def cycle_ppp_link():
    """Restart the Clipper PPP link when the configured uplink is ppp0.

    This is intentionally tolerant: the SIM may be absent, the modem may not be
    attached, or the peer may not be available yet. In those cases we log a
    warning and continue rather than crashing the app.
    """
    if config_data.get("uplink_mode") != "ppp0":
        return True

    steps = [
        (["sudo", "poff", "clipper"], "Powering down Clipper PPP link"),
        (["sudo", "pon", "clipper"], "Starting Clipper PPP link"),
    ]

    for command, message in steps:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                logging.info(f"{message} succeeded.")
            else:
                stderr = (result.stderr or result.stdout or "").strip()
                logging.warning(f"{message} failed (rc={result.returncode}): {stderr or 'no output'}")
        except FileNotFoundError:
            logging.warning("PPP control utility not available; cannot toggle Clipper link.")
            return False
        except subprocess.TimeoutExpired:
            logging.warning(f"{message} timed out; continuing without crashing.")
            return False
        except Exception as e:
            logging.warning(f"Unexpected error while {message.lower()}: {e}")
            return False

    return True


def restartSoftware():
    if config_data.get("uplink_mode") == "ppp0":
        cycle_ppp_link()
    subprocess.Popen(["sudo", "systemctl", "restart", "hostapd.service"]) # In addition to new midnight restart of it (systemctl list-timers)
    subprocess.Popen(["sudo", "systemctl", "restart", "startup.service"])

@app.route('/', methods=['POST', 'GET'])
def handle_request():
    if request.method == 'POST':
        command = request.form.get('command')
        code = request.form.get('code')
        logging.info(f"Received command: {command}, code: {code}")
        if command == "CLEARLOG":
            with open(log_path, "w") as file:
                file.write("")
                file.close()
            with open("/var/www/html/camera.log", "w") as file:
                file.write("")
                file.close()
            logging.info("Log cleared")
            return "Log cleared", 200
        elif command == "UPDATETIME":
            try:
                update_time()
                return "Time updated", 200
            except Exception as e:
                logging.error(f"Error updating time: {e}")
                return f"Error updating time: {e}", "error", 500
        elif command == "SHUTDOWN":
            logging.warning("Shutting down system")
            pijuice.power.SetPowerOff(120)
            subprocess.run(['sudo', 'shutdown', '-h', '0'])
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
                    logging.info(f"Created missing directory: {images_path}")
                except Exception as e:
                    logging.info(f"Failed to create directory {images_path}: {e}")
            else:
                # If folder exists, clean it out
                for root, dirs, files in os.walk(images_path, topdown=False):
                    for f in files:
                        try:
                            os.unlink(os.path.join(root, f))
                        except Exception as e:
                            logging.info(f"Error deleting file {f}: {e}")
                    for d in dirs:
                        try:
                            shutil.rmtree(os.path.join(root, d))
                        except Exception as e:
                            logging.info(f"Error deleting directory {d}: {e}")
            logging.info("Performed factory reset")
            logging.warning("All data and common settings deleted")
            pijuice.power.SetPowerOff(120)
            subprocess.run(['sudo', 'shutdown', '-h', '0'])
            return "Factory reset performed", 200
        elif command == "RESTARTSOFTWARE":
            logging.warning("Restarting software")
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
    logging.info(f"Using USB device at {usb_path} for export")
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
                logging.info(f"copied {file_path} to {dest_path}")
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
        logging.info(f"Received export command: {command}, code: {code}")
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
                logging.info(f"ALLZIP: found {len(image_files)} image files for zipping")
                files_to_zip.extend(image_files)

                output_zip = f"/var/www/html/dl/export_{export_datetime}_{config_data['dbTable']}.zip"
                os.makedirs(os.path.dirname(output_zip), exist_ok=True)

                with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in files_to_zip:
                        if not os.path.exists(file):
                            logging.warning(f"ALLZIP: skipping missing file: {file}")
                            continue
                        try:
                            arcname = os.path.relpath(file, start="/var/www/html")
                            logging.info(f"ALLZIP: adding {file} as {arcname}")
                            zipf.write(file, arcname)
                        except Exception:
                            logging.exception(f"ALLZIP: failed to add {file} to zip")
                logging.info(f"Created zip file: {output_zip}")
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
                logging.info(f"TIMELAPSE: running ffmpeg with command: {' '.join(ffmpeg_cmd)}")
                try:
                    res = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, timeout=300)
                    if res.stdout:
                        logging.info(f"ffmpeg stdout: {res.stdout.strip()}")
                    if res.stderr:
                        logging.info(f"ffmpeg stderr: {res.stderr.strip()}")
                    logging.info("Timelapse created successfully")
                    return f"U:/dl/timelapse_{export_datetime}_{config_data['dbTable']}.mp4"
                except subprocess.CalledProcessError as e:
                    logging.error(f"Failed to create timelapse (non-zero exit): {e.returncode}")
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
                logging.info(f"USB: preparing to copy {len(image_files)} image files and {len(files_to_copie)} base files")
                files_to_copie.extend(image_files)
                # Log first few files for debug
                for idx, fpath in enumerate(files_to_copie[:20]):
                    logging.info(f"USB candidate [{idx}]: {fpath}")
                result = copy_files_to_usb(files_to_copie)
                if result == "SUCCESS":
                    logging.info("Files copied to USB successfully")
                    return "I:Files copied to USB successfully, please remove USB drive", 200
                else:
                    logging.error(f"Failed to copy files to USB: {result}")
                    return f"Error copying files to USB: {result}", 500

            elif command == "export-csv":
                Table = config_data["dbTable"]
                try:
                    with sqlite3.connect(db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT * FROM {Table}")
                        rows = cursor.fetchall()
                        if not rows:
                            logging.warning("export-csv: no rows found")
                            return "No data to export", 404

                        output_dir = "/var/www/html/dl"
                        os.makedirs(output_dir, exist_ok=True)
                        csv_file_path = os.path.join(output_dir, f"export_{export_datetime}_{config_data['dbTable']}.csv")

                        import csv

                        # Get column names
                        cursor.execute(f"PRAGMA table_info({Table})")
                        columns = [info[1] for info in cursor.fetchall()]
                        logging.info(f"export-csv: columns = {columns}")
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

                        logging.info(f"Exported data to CSV: {csv_file_path} (rows: {len(rows)})")
                        return f"U:/dl/export_{export_datetime}_{config_data['dbTable']}.csv", 200

                except sqlite3.Error as e:
                    logging.error(f"Database error during export: {e}")
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
        "check_interval": int,
        "uplink_mode": str,
        "cellular_enabled": bool,
        "active_carrier": str,
        "logger_ID": str
    }

    valid_cam_modes = {"none", "door", "doorcam"}

    if request.method == 'GET':
        return jsonify(config_data), 200

    elif request.method == 'POST':
        datar = request.get_json()

        # Validate JSON data
        if not isinstance(datar, dict):
            logging.error(f"Invalid JSON format: {datar}")
            return "Invalid JSON format", 400

        datar.pop("cellular_apns", None)
        datar.pop("carrier_apns", None)

        for field, expected_type in required_fields.items():
            if field not in datar:
                logging.error(f"Missing required field: {field}")
                return f"Missing required field: {field}", 422
            if not isinstance(datar[field], expected_type):
                logging.error(f"Incorrect type for '{field}'. Expected {expected_type.__name__}, got {type(datar[field]).__name__}")
                return f"Incorrect type for '{field}'. Expected {expected_type.__name__}, got {type(datar[field]).__name__}", 422

        if datar["uplink_mode"] not in ("ppp0", "eth0", "auto"):
            logging.error(f"Invalid uplink_mode value: {datar['uplink_mode']}")
            return "Invalid uplink_mode. Must be 'ppp0', 'eth0', or 'auto'.", 422

        if datar["cellular_enabled"]:
            if not datar.get("active_carrier"):
                logging.error("Cellular enabled but no active_carrier set")
                return "active_carrier required when cellular is enabled", 422
            if datar["active_carrier"] != "custom" and datar["active_carrier"] not in carrier_apns:
                logging.error(f"Unknown active_carrier: {datar['active_carrier']}")
                return "active_carrier must be a known carrier name or 'custom'", 422
            if datar["active_carrier"] == "custom":
                custom = datar.get("custom_apn")
                if not isinstance(custom, dict):
                    logging.error("active_carrier is 'custom' but custom_apn missing/invalid")
                    return "custom_apn (object) required when active_carrier is 'custom'", 422
                # Clipper only needs the APN string. Ignore username/password/auth settings.
                if "apn" not in custom or not str(custom.get("apn", "")).strip():
                    logging.error("custom_apn missing required APN value")
                    return "custom_apn.apn is required when active_carrier is 'custom'", 422

        original_db_table = datar["dbTable"]
        datar["dbTable"] = sanitize_db_table(original_db_table)
        if datar["dbTable"] != original_db_table:
            logging.warning("Removed invalid characters from dbTable or truncated its length.")

        # Check for negative logInterval
        if datar["logInterval"] < 0:
            logging.error(f"logInterval is negative: {datar['logInterval']}")
            return "logInterval must be non-negative.", 422

        # Validate CamEnable value
        if datar["CamEnable"] not in valid_cam_modes:
            logging.error(f"Invalid CamEnable value: {datar['CamEnable']}")
            return "Invalid CamEnable value. Must be 'none', 'door', or 'doorcam'.", 422

        # Validate ThingsBoard settings
        if datar["thingsboard_enabled"]:
            if not datar["thingsboard_url"]:
                logging.error("ThingsBoard enabled but URL not provided")
                return "ThingsBoard URL required when enabled", 422
            if not datar["thingsboard_token"]:
                logging.error("ThingsBoard enabled but token not provided")
                return "ThingsBoard token required when enabled", 422
        
        # Validate batch_size and check_interval
        if datar["batch_size"] < 1:
            logging.error(f"batch_size must be positive: {datar['batch_size']}")
            return "batch_size must be at least 1", 422
        
        if datar["check_interval"] < 1:
            logging.error(f"check_interval must be positive: {datar['check_interval']}")
            return "check_interval must be at least 1", 422

        logging.info(f"Received valid config data: {datar}")

        apn_value = ""
        if datar.get("active_carrier") == "custom":
            apn_value = str((datar.get("custom_apn") or {}).get("apn", "")).strip()
        elif datar.get("active_carrier") in carrier_apns:
            apn_value = str(carrier_apns[datar["active_carrier"]].get("apn", "")).strip()

        # Only the APN is used by the Clipper PPP peer config.
        datar["custom_apn"] = {"apn": apn_value}

        temporary_path = config_path + ".tmp"
        with open(temporary_path, "w") as file:
            json.dump(datar, file, indent=4)
        os.replace(temporary_path, config_path)
        config_data = copy.deepcopy(datar)
        save_identity()

        write_clipper_apn(apn_value)
        return "Saved config data", 200


@app.route('/getapn', methods=['GET'])
def get_apn():
    return jsonify(carrier_apns), 200


@app.route('/test-connection', methods=['POST'])
def test_connection():
    """
    Server-side ThingsBoard connectivity test. Runs from the Pi itself so the
    result reflects the configured uplink path, not the browser's.
    """
    body = request.get_json(silent=True) or {}

    url = body.get("thingsboard_url") or config_data.get("thingsboard_url", "")
    token = body.get("thingsboard_token") or config_data.get("thingsboard_token", "")

    if not url or not token:
        logging.warning("Test connection requested without URL/token")
        return jsonify({"success": False, "message": "URL and token are required"}), 400

    iface = resolve_interface(config_data.get("uplink_mode", "auto"))
    session = get_session(iface, logger=None)

    test_url = f"{url.rstrip('/')}/api/v1/{token}/telemetry"
    test_payload = [{"ts": int(time.time() * 1000), "values": {"test": "connection_test"}}]

    try:
        response = session.post(
            test_url,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if response.ok:
            logging.info(f"Test connection succeeded via interface={iface or 'auto'}")
            return jsonify({
                "success": True,
                "message": "Successfully connected to ThingsBoard",
                "interface": iface or "auto",
            }), 200

        logging.error(f"Test connection failed: HTTP {response.status_code}: {response.text}")
        return jsonify({
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text}",
            "interface": iface or "auto",
        }), 200
    except requests.RequestException as e:
        logging.error(f"Test connection failed ({type(e).__name__}): {e}")
        return jsonify({
            "success": False,
            "message": f"{type(e).__name__}: {e}",
            "interface": iface or "auto",
        }), 200


@app.route("/status", methods=["GET"])
def status():
    return jsonify(get_system_and_pijuice_stats()), 200


@app.route("/data", methods=["POST"])
def data():
    logging.info("Data received")
    try:
        data = request.get_data().decode("utf-8")
        if data.startswith("data="):
            data = data[5:]
        data_list = data.split(",")
        data_list = [int(data_list[0])] + [float(i.strip()) for i in data_list[1:]]
        logging.info(f"Processed data: {data_list}")
        if data_list[0] > 90:
            return "ID out of range", 416
        datas = {
            f"T{data_list[0]:02d}": data_list[1],
            f"H{data_list[0]:02d}": data_list[2],
        }
        insert_data(data_list[0], datas)
        return "Received and Saved", 200
    except (ValueError, IndexError) as e:
        logging.error(f"Error processing data: {e}")
        return "Invalid data format", 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "Server error", 500

#Add ID option for this at some point (Just fucking don't. It will definetly break shit)
@app.route("/Lidata", methods=["POST"])
def Lidata():
    logging.info("Light data received")
    try:
        data = request.get_data().decode("utf-8")
        if data.startswith("data="):
            data = data[5:]
        LiTime = int(data)
        logging.info(f"Processed time data: {LiTime}")
        datas = {
            f"LI1": LiTime,
        }
        insert_data(99, datas)
        return "Received and Saved", 200
    except (ValueError, IndexError) as e:
        logging.error(f"Error processing data: {e}")
        return "Invalid data format", 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "Server error", 500
    
@app.route("/intdata", methods=["POST"])
def intdata():
    try:
        data = request.get_json()
        if data is None:
            logging.warning("No JSON data received")
            return "No JSON data received", 400
        if config_data["SHT"]:
            required_fields = ["EN1", "EN2", "EN3", "EN4", "EN5", "T00", "H00"]
            if not all(field in data for field in required_fields):
                logging.warning("Missing required data")
                return "Missing required data", 422
            datas = {field: float(data[field]) for field in required_fields}
        if not config_data["SHT"]:
            required_fields = ["EN1", "EN2", "EN3", "EN4", "EN5"]
            if not all(field in data for field in required_fields):
                logging.warning("Missing required data")
                return "Missing required data", 422
            datas = {field: float(data[field]) for field in required_fields}

        # logging.info(f"Received JSON data: {datas}")
        insert_data(0, datas)
        return "Success", 200
    except ValueError as e:
        logging.error(f"Invalid data type: {e}")
        return "Invalid data type", 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
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
        logging.error(f"Error listing tables: {e}")
        return jsonify({"error": str(e)}), 500


def run_flask():
    logging.info("Starting Flask server")
    serve(app, host="0.0.0.0", port=8000)
    logging.info("Flask server started")


# def vacuum_journal(): ##No longer needed as logs to RAM now
#     while True:
#         try:
#             subprocess.run(
#                 ["sudo", "journalctl", "--rotate", "--vacuum-size=100M"],
#                 check=True,
#                 capture_output=True,
#                 text=True,
#                 timeout=60,
#             )
#             logging.info("System journal vacuumed to 100 MB")
#         except Exception as e:
#             logging.warning(f"Failed to vacuum system journal: {e}")
#         time.sleep(24 * 60 * 60)


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
                logging.error(f"Failed to read SHT3x")
                time.sleep(config_data["logInterval"])
                continue

            try:
                # Divide data into counts
                t_data = data[0] << 8 | data[1]
                h_data = data[3] << 8 | data[4]

                # Convert counts to Temperature/Humidity
                Humidity = round(100.0 * float(h_data) / 65535.0, 2)
                Temperature = round(-45.0 + 175.0 * float(t_data) / 65535.0, 2)

                # logging.info(f"Temp: {Temperature}C  H: {Humidity}%")
            except Exception:
                logging.error(f"Failed to process sensor data")
                continue

        try:
            if client.connect():
                values = []
                for address, name in REGISTER_MAP.items():
                    value = read_register(client, address)
                    if value is not None:
                        # logging.info(f"{name}: {value:.2f}")
                        values.append(value)
                    else:
                        logging.warning(f"Failed to read {name}")
                client.close()
            else:
                logging.error("Failed to connect to SDM120M")
        except Exception:
            logging.error(f"Error reading SDM120M registers")
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
                logging.info("Server Response:")
            else:
                logging.warning("Insufficient SDM120M values or sensor data to send to server")
        except Exception:
            logging.error(f"Failed to send data to server")

        log_interval = config_data.get("logInterval", 300)  # Default to 300 if missing
        if isinstance(log_interval, int) and log_interval > 0:
            time.sleep(log_interval)
        else:
            logging.warning(f"Invalid logInterval value: {log_interval}. Using default value of 300.")
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
    logging.info(f"Current IP address: {ip_address}")

    return ip_address

# Function to add IP address if necessary
def configure_ip():
    ip_address = check_ip()
    
    # Check if the IP address contains '192.168.5.1'
    if '192.168.5.1' not in ip_address:
        # Add the IP address and restart hostapd service
        subprocess.run(['sudo', 'ip', 'addr', 'add', '192.168.5.1/24', 'dev', 'wlan0'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'hostapd.service'])
        logging.info("IP address added and hostapd service restarted.")
    else:
        logging.info("IP address 192.168.5.1 is already configured.")

def check_network():
    """
    Check internet connectivity via the currently configured uplink_mode.
    Returns True/False. Logs the interface actually used.
    """
    configured_mode = config_data.get("uplink_mode", "auto")
    primary_iface = resolve_interface(configured_mode)
    attempted = []

    if primary_iface is not None:
        candidates = [primary_iface, None]
    else:
        candidates = [None]

    for iface in candidates:
        if iface is None and primary_iface is not None:
            logging.warning(f"Network check failed on configured interface '{primary_iface}', retrying with auto routing.")

        attempted.append(iface)
        session = get_session(iface, logger=None)
        try:
            response = session.get('https://www.google.com/', timeout=10)
            response.raise_for_status()
            logging.info(f"Network is working (uplink_mode={configured_mode}, "
                f"bound interface={iface or 'auto/unbound'}).")
            return True
        except Exception as e:
            logging.warning(f"Network check failed (uplink_mode={configured_mode}, "
                f"bound interface={iface or 'auto/unbound'}): {e}")

    logging.warning(f"Network is down (uplink_mode={configured_mode}, attempted interfaces={attempted}).")
    return False

net = check_network()

pin = 22 # CHANGED FROM 14!!!!! (14 was HW UART)
def fan():
    import RPi.GPIO as IO          # type: ignore # Calling GPIO to allow use of the GPIO pins

    IO.setwarnings(False)          # Do not show any GPIO warnings
    IO.setmode (IO.BCM)            # BCM pin numbers - PIN8 as ‘GPIO14’
    IO.setup(pin,IO.OUT)            # Initialize GPIO14 as our fan output pin
    fan = IO.PWM(pin,100)           # Set GPIO14 as a PWM output, with 100Hz frequency (this should match your fans specified PWM frequency)
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
        # logging.info(temp)
        if temp > 60:                            # Check temperature threshhold, in degrees celcius
            fan.ChangeDutyCycle(100)             # Set fan duty based on temperature, 100 is max speed and 0 is min speed or off.
        if temp < 55:                            # If temperature is below threshold
            fan.ChangeDutyCycle(0)               # Set fan duty to 0% if temperature is below threshold
        time.sleep(5)                            # Sleep for 5 seconds

@app.route('/remove-table-and-images', methods=['POST'])
def remove_table_and_images():
    data = request.get_json()
    logging.info("Received request to remove table and images")
    
    table = data.get('table')
    if not table or not sanitize_db_table(table) == table:
        logging.error(f"Invalid table name provided: {table}")
        return "Invalid table name", 400

    logging.info(f"Removing table and images for: {table}")
    
    # Check if the table is the active one and update config if necessary
    if table == config_data["dbTable"]:
        logging.warning(f"Table '{table}' is the active table. Updating config to use default table.")
        config_data_mod = copy.deepcopy(config_data)
        config_data_mod["dbTable"] = "data"
        try:
            response = requests.post("http://127.0.0.1:8000/configs", json=config_data_mod)
            if response.status_code == 200:
                logging.info("Successfully updated config to use default table.")
            else:
                logging.error(f"Failed to update config. Response: {response.status_code}, {response.text}")
        except Exception as e:
            logging.error(f"Error updating config: {e}")

    # Remove images
    images_path = f'/var/www/html/images/{table}/'
    if os.path.exists(images_path):
        logging.info(f"Removing images at path: {images_path}")
        for root, dirs, files in os.walk(images_path, topdown=False):
            for f in files:
                try:
                    os.unlink(os.path.join(root, f))
                    logging.info(f"Deleted file: {os.path.join(root, f)}")
                except Exception as e:
                    logging.error(f"Error deleting file {os.path.join(root, f)}: {e}")
            for d in dirs:
                try:
                    shutil.rmtree(os.path.join(root, d))
                    logging.info(f"Deleted directory: {os.path.join(root, d)}")
                except Exception as e:
                    logging.error(f"Error deleting directory {os.path.join(root, d)}: {e}")
        try:
            os.rmdir(images_path)
            logging.info(f"Deleted images folder: {images_path}")
        except Exception as e:
            logging.error(f"Error deleting images folder {images_path}: {e}")
    else:
        logging.warning(f"Images path does not exist: {images_path}")

    # Remove table from database
    try:
        logging.info(f"Attempting to remove table '{table}' from database.")
        db_path = "/var/www/html/example.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.commit()
        conn.close()
        logging.info(f"Successfully removed table '{table}' from database.")
        return "Table and images removed", 200
    except Exception as e:
        logging.error(f"Error removing table '{table}' from database: {e}")
        return f"Error removing table/images: {e}", 500
    

if __name__ == "__main__":
    if config_data.get("uplink_mode") == "ppp0":
        cycle_ppp_link()
    configure_ip()
    time.sleep(10)
    # threading.Thread(target=vacuum_journal, daemon=True).start()
    threading.Thread(target=run_flask).start()
    threading.Thread(target=collect_results).start()
    threading.Thread(target=fan).start()
    if config_data["CamEnable"] in ("door", "doorcam"):
        def start_camera_thread():
            subprocess.run(["sudo", "python3", "/home/pi/Camera-handle.py"])
        logging.info("Camera/door sensor enabled, starting camera thread")
        try:
            threading.Thread(target=start_camera_thread).start()
        except ImportError as e:
            logging.error(f"Failed to start camera module: {e}")
    
    # Start ThingsBoard uploader if enabled
    if (config_data.get("thingsboard_enabled", True) and net):
        thingsboard_config = {
            "thingsboard_url": config_data.get("thingsboard_url", ""),
            "thingsboard_token": config_data.get("thingsboard_token", ""),
            "database_path": db_path,
            "state_path": "/var/www/html/thingsboard_upload_state.json",
            "batch_size": config_data.get("batch_size", 100),
            "check_interval": config_data.get("check_interval", 5),
            "http_timeout": 20,
            "uplink_mode": config_data.get("uplink_mode", "auto"),
        }
        thingsboard_uploader = start_thingsboard_uploader(
            thingsboard_config
        )
        if thingsboard_uploader:
            logging.info("ThingsBoard uploader started successfully")
        else:
            logging.error("ThingsBoard uploader failed to start (misconfigured)")
    while True:
        time.sleep(5)

