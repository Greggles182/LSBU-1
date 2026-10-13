from flask import *
from flask_cors import CORS
from waitress import serve
from ntplib import NTPClient
import os, time as time, json, copy, shutil, logging, platform, sqlite3, requests, threading, sys, subprocess, zipfile, re, struct, psutil, smbus # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from glob import glob
from thingsboard_uploader import start_thingsboard_uploader
from bounded_logging import SizeCappedFileHandler
from network_utils import get_session
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
MODEM_ATTACHED = True
MODEM_SERIAL_PORT = "/dev/serial0"
MODEM_BAUDRATE = 115200
NETWORK_PROBE_URL = "https://www.google.com/generate_204"
NETWORK_PROBE_TIMEOUT = 4
NETWORK_CHECK_INTERVAL = 30
PPP_RETRY_INTERVAL = 300
STATUS_REFRESH_INTERVAL = 60
DAILY_DIAGNOSTICS_INTERVAL = 24 * 60 * 60
PPP_LOCK = threading.RLock()

# Define the NTP server
NTP_SERVER = "pool.ntp.org"
DB_TABLE_PATTERN = r"[A-Za-z0-9_-]+"
DB_TABLE_MAX_LENGTH = 50

db_path = "/var/www/html/example.db"
log_path = "/var/www/html/server.log"
config_path = "/var/www/html/data.json"
identity_path = "/var/www/html/device_identity.json"
carrier_apns_path = "/var/www/html/carrier_apns.json"

server_log_handler = SizeCappedFileHandler(log_path, encoding="utf-8")
server_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(server_log_handler)

if platform.system() == "Windows":
    print("This does not work on Windows.")
    sys.exit(1)


def run_ppp_command(command, message):
    try:
        result = subprocess.run(
            ["sudo", *command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        logging.error("%s failed: PPP control utility is not installed.", message)
        return False
    except subprocess.TimeoutExpired:
        logging.error("%s timed out.", message)
        return False
    except Exception:
        logging.exception("%s failed unexpectedly.", message)
        return False

    if result.returncode == 0:
        logging.info("%s succeeded.", message)
        return True

    detail = (result.stderr or result.stdout or "").strip()
    logging.error(
        "%s failed (rc=%s): %s",
        message,
        result.returncode,
        detail or "no output",
    )
    return False


def start_ppp_link():
    """Ask pppd to bring up the configured Clipper peer without blocking startup."""
    with PPP_LOCK:
        return run_ppp_command(["pon", "clipper"], "Starting Clipper PPP link")


def cycle_ppp_link():
    """Restart the Clipper PPP peer for explicit software restarts or recovery."""
    with PPP_LOCK:
        run_ppp_command(["poff", "clipper"], "Stopping Clipper PPP link")
        time.sleep(1)
        return run_ppp_command(["pon", "clipper"], "Restarting Clipper PPP link")


startup_ppp_succeeded = None
if __name__ == "__main__":
    startup_ppp_succeeded = start_ppp_link()


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


def load_json_object(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            value = json.load(file)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        logging.exception("Failed to read JSON configuration at %s", path)
        raise

    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def save_config_data(data=None):
    temporary_path = config_path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(config_data if data is None else data, file, indent=4)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary_path, config_path)


default_config = {
    "logInterval": 300,
    "dbTable": "data",
    "SHT": True,
    "CamEnable": "none",
    "thingsboard_enabled": False,
    "thingsboard_url": "",
    "thingsboard_token": "",
    "batch_size": 100,
    "check_interval": 5,
    "cellular_enabled": False,
    "active_carrier": "",
    "custom_apn": {"apn": ""},
    "logger_ID": "",
}
config_data = load_json_object(config_path)
if not config_data:
    config_data = copy.deepcopy(default_config)
    logging.info("Created new configuration at %s", config_path)

legacy_identity = load_json_object(identity_path)
legacy_carrier_apns = load_json_object(carrier_apns_path)
for key in IDENTITY_FIELDS:
    current_value = config_data.get(key)
    empty_custom_apn = (
        key == "custom_apn"
        and isinstance(current_value, dict)
        and not str(current_value.get("apn", "")).strip()
    )
    if (
        key in legacy_identity
        and (current_value in (None, "", {}) or empty_custom_apn)
    ):
        config_data[key] = legacy_identity[key]

carrier_apns = copy.deepcopy(DEFAULT_CARRIER_APNS)
stored_carrier_apns = config_data.get("carrier_apns")
if not isinstance(stored_carrier_apns, dict) or not stored_carrier_apns:
    stored_carrier_apns = legacy_carrier_apns
if isinstance(stored_carrier_apns, dict):
    carrier_apns.update(stored_carrier_apns)
config_data["carrier_apns"] = carrier_apns

for key, value in default_config.items():
    config_data.setdefault(key, copy.deepcopy(value))
config_data.pop("uplink_mode", None)

original_db_table = config_data.get("dbTable")
config_data["dbTable"] = sanitize_db_table(original_db_table)
if config_data["dbTable"] != original_db_table:
    logging.warning("Invalid dbTable in config; removed invalid characters or truncated its length.")

save_config_data()
for legacy_path in (identity_path, carrier_apns_path):
    try:
        os.remove(legacy_path)
        logging.info("Removed migrated configuration file %s", legacy_path)
    except FileNotFoundError:
        pass
    except OSError:
        logging.exception("Failed to remove migrated configuration file %s", legacy_path)

config_lock = threading.RLock()
network_status_lock = threading.Lock()
last_network_check = 0.0
last_network_available = None
network_status = {
    "ppp0": {"reachable": False, "checked_at": None, "error": "Not checked"},
    "eth0": {"reachable": False, "checked_at": None, "error": "Not checked"},
}
modem_status_lock = threading.Lock()
modem_query_lock = threading.Lock()
modem_status = {
    "attached": MODEM_ATTACHED,
    "sim_state": "unknown",
    "signal_rssi": None,
    "signal_dbm": None,
    "signal_ber": None,
    "signal_percent": None,
    "signal_bars": 0,
    "manufacturer": None,
    "model": "A7683E",
    "firmware": None,
    "sim_response": None,
    "signal_response": None,
    "registration_status": None,
    "operator_status": None,
    "packet_attachment_status": None,
    "checked_at": None,
    "error": "Not checked",
}
thingsboard_uploader = None


app = Flask(__name__)
CORS(app)



images_path = get_images_path()

SENSITIVE = re.compile(r"token|pass|secret|pwd|apikey|api_key", re.I)

def mask(value, keep=5):
    s = str(value)
    if not s:
        return s
    if len(s) <= keep * 2:          # too short to show any of it safely
        return "*" * len(s)
    return s[:keep] + "…" + "*" * 3

def redact(obj, keep=5):
    if isinstance(obj, dict):
        return {k: (mask(v, keep) if SENSITIVE.search(str(k)) and not isinstance(v, (dict, list))
                    else redact(v, keep))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(i, keep) for i in obj]
    return obj

logging.info(f"Loaded config data: {redact(config_data)}")



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

def restartSoftware():
    cycle_ppp_link()
    subprocess.Popen(["sudo", "systemctl", "restart", "hostapd.service"]) # In addition to new midnight restart of it (systemctl list-timers)
    subprocess.Popen(["sudo", "systemctl", "restart", "startup.service"])

@app.route('/', methods=['POST', 'GET'])
def handle_request():
    global config_data
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
            images_to_clear = get_images_path()
            with config_lock:
                reset_config = copy.deepcopy(config_data)
                reset_config["logInterval"] = 300
                reset_config["dbTable"] = "data"
                reset_config["CamEnable"] = "none"
                try:
                    save_config_data(reset_config)
                except OSError:
                    logging.exception("Factory reset could not persist default logger settings.")
                    return "Factory reset could not save configuration", 500
                config_data = reset_config

            with open(log_path, "w") as file:
                file.write("")
                file.close()
            with open("/var/www/html/camera.log", "w") as file:
                file.write("")
                file.close()

            images_path = images_to_clear
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
            logging.info("Factory reset preserved data and credentials; restored logger defaults.")
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
        datar.pop("uplink_mode", None)

        for field, expected_type in required_fields.items():
            if field not in datar:
                logging.error(f"Missing required field: {field}")
                return f"Missing required field: {field}", 422
            if not isinstance(datar[field], expected_type):
                logging.error(f"Incorrect type for '{field}'. Expected {expected_type.__name__}, got {type(datar[field]).__name__}")
                return f"Incorrect type for '{field}'. Expected {expected_type.__name__}, got {type(datar[field]).__name__}", 422

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

        apn_value = ""
        if datar.get("active_carrier") == "custom":
            apn_value = str((datar.get("custom_apn") or {}).get("apn", "")).strip()
        elif datar.get("active_carrier") in carrier_apns:
            apn_value = str(carrier_apns[datar["active_carrier"]].get("apn", "")).strip()

        # Only the APN is used by the Clipper PPP peer config.
        datar["custom_apn"] = {"apn": apn_value}
        datar["carrier_apns"] = copy.deepcopy(carrier_apns)
        logging.info("Received valid config data: %s", redact(datar))

        try:
            with config_lock:
                save_config_data(datar)
                config_data = copy.deepcopy(datar)
        except OSError:
            logging.exception("Could not persist configuration.")
            return "Could not save configuration", 500

        write_clipper_apn(apn_value)
        return "Saved config data", 200


@app.route('/getapn', methods=['GET'])
def get_apn():
    return jsonify(carrier_apns), 200


@app.route('/network-status', methods=['GET'])
def get_network_status_route():
    if request.args.get("refresh") == "1":
        refresh_status_snapshot()
    return jsonify(get_status_snapshot()), 200


@app.route('/test-connection', methods=['POST'])
def test_connection():
    """
    Server-side ThingsBoard connectivity test. Runs from the Pi itself so the
    result reflects the route selected by the kernel, not the browser's.
    """
    body = request.get_json(silent=True) or {}

    url = body.get("thingsboard_url") or config_data.get("thingsboard_url", "")
    token = body.get("thingsboard_token") or config_data.get("thingsboard_token", "")

    if not url or not token:
        logging.warning("Test connection requested without URL/token")
        return jsonify({"success": False, "message": "URL and token are required"}), 400

    session = requests.Session()

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
            logging.info("Test connection succeeded via the kernel-selected route.")
            return jsonify({
                "success": True,
                "message": "Successfully connected to ThingsBoard",
            }), 200

        logging.error(f"Test connection failed: HTTP {response.status_code}: {response.text}")
        return jsonify({
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text}",
        }), 200
    except requests.RequestException as e:
        logging.error(f"Test connection failed ({type(e).__name__}): {e}")
        return jsonify({
            "success": False,
            "message": f"{type(e).__name__}: {e}",
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

def probe_interface_connection(interface, timeout=NETWORK_PROBE_TIMEOUT):
    """Test outbound internet reachability bound to one interface."""
    try:
        with get_session(interface).get(
            NETWORK_PROBE_URL,
            timeout=timeout,
            allow_redirects=False,
        ) as response:
            return {
                "reachable": response.status_code in (200, 204),
                "checked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "error": None if response.status_code in (200, 204) else
                    f"Probe endpoint returned HTTP {response.status_code}",
            }
    except Exception as exc:
        return {
            "reachable": False,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "error": f"{type(exc).__name__}: {exc}",
        }


def refresh_network_status():
    """Update per-interface internet status using independent bound requests."""
    for interface in ("ppp0", "eth0"):
        if interface == "ppp0":
            with PPP_LOCK:
                status = probe_interface_connection(interface)
        else:
            status = probe_interface_connection(interface)
        with network_status_lock:
            previous_status = network_status[interface]
            previous = previous_status["reachable"]
            previous_error = previous_status["error"]
            network_status[interface] = status
        if status["reachable"]:
            if not previous:
                logging.info("%s internet probe succeeded.", interface)
        elif previous or previous_error != status["error"]:
            logging.warning("%s internet probe failed: %s", interface, status["error"])
    return get_network_status()


def get_network_status():
    with network_status_lock:
        return copy.deepcopy(network_status)


def check_network(force=False):
    """Check connectivity through the kernel's normal route, with bounded retries."""
    global last_network_check, last_network_available, net
    now = time.monotonic()
    with network_status_lock:
        if not force and now - last_network_check < NETWORK_CHECK_INTERVAL:
            return last_network_available

        last_network_check = now
        try:
            response = requests.get(NETWORK_PROBE_URL, timeout=NETWORK_PROBE_TIMEOUT)
            available = response.status_code in (200, 204)
            response.close()
            error = None if available else f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            available = False
            error = f"{type(exc).__name__}: {exc}"

        if last_network_available is None or available != last_network_available:
            if available:
                logging.info("Kernel-routed internet connection is available.")
            else:
                logging.error("No usable kernel-routed internet connection: %s", error)
        last_network_available = available
        net = available
        return available


net = False


def network_monitor_loop():
    failures = 0
    next_ppp_retry = 0.0
    while True:
        refresh_network_status()
        check_network()
        ppp_connected = get_network_status()["ppp0"]["reachable"]
        failures = 0 if ppp_connected else failures + 1
        if failures >= 3 and time.monotonic() >= next_ppp_retry:
            logging.error(
                "ppp0 has failed three consecutive internet checks; attempting PPP recovery."
            )
            cycle_ppp_link()
            next_ppp_retry = time.monotonic() + PPP_RETRY_INTERVAL
            failures = 0
        time.sleep(STATUS_REFRESH_INTERVAL)


def send_modem_command(connection, command, timeout=3):
    connection.reset_input_buffer()
    connection.write(f"{command}\r".encode("ascii"))
    connection.flush()
    deadline = time.monotonic() + timeout
    response = bytearray()
    while time.monotonic() < deadline:
        response.extend(connection.read(connection.in_waiting or 1))
        text = response.decode("ascii", errors="replace")
        if re.search(r"(^|\r?\n)(OK|ERROR|\+CME ERROR:.*)(\r?\n|$)", text):
            return text
    raise TimeoutError(f"No final modem response to {command}")


def modem_response_lines(response, command):
    """Remove command echoes and terminal result codes from a modem response."""
    lines = []
    for line in response.replace("\r", "\n").splitlines():
        value = line.strip()
        if not value or value == command or value in ("OK", "ERROR"):
            continue
        if value.startswith("+CME ERROR:") or value.startswith("+CMS ERROR:"):
            continue
        lines.append(value)
    return lines


def parse_at_value(response, command, prefix=None):
    lines = modem_response_lines(response, command)
    if prefix:
        match = re.search(rf"{re.escape(prefix)}\s*(.*)", "\n".join(lines))
        return match.group(1).strip() if match else None
    return " ".join(lines) or None


def parse_registration_status(response):
    match = re.search(r"\+CEREG:\s*(?:\d+\s*,\s*)?(\d+)", response)
    if not match:
        return None
    states = {
        0: "Not registered",
        1: "Registered (home network)",
        2: "Searching for network",
        3: "Registration denied",
        4: "Registration status unknown",
        5: "Registered (roaming)",
    }
    state = int(match.group(1))
    return states.get(state, f"Unknown registration state ({state})")


def parse_operator_status(response):
    match = re.search(
        r'\+COPS:\s*(\d+)\s*,\s*(\d+)\s*,\s*"([^"]*)"(?:\s*,\s*(\d+))?',
        response,
    )
    if not match:
        return None

    operator_code = match.group(3).strip()
    access_technology = match.group(4)
    technologies = {
        "0": "GSM",
        "2": "UMTS",
        "3": "EDGE",
        "7": "LTE",
        "9": "NB-IoT",
        "10": "LTE-M",
        "11": "NR",
    }
    technology = technologies.get(access_technology)
    return f"{operator_code} ({technology})" if technology else operator_code or None


def parse_packet_attachment_status(response):
    match = re.search(r"\+CGATT:\s*([01])", response)
    if not match:
        return None
    return "Attached" if match.group(1) == "1" else "Not attached"


def query_modem_status():
    """Read SIM readiness and signal quality without sharing the PPP serial line."""
    if not MODEM_ATTACHED:
        return {
            "attached": False,
            "sim_state": "not attached",
            "signal_rssi": None,
            "signal_dbm": None,
            "signal_ber": None,
            "signal_percent": None,
            "signal_bars": 0,
            "manufacturer": None,
            "model": "A7683E",
            "firmware": None,
            "sim_response": None,
            "signal_response": None,
            "registration_status": None,
            "operator_status": None,
            "packet_attachment_status": None,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "error": "Modem probing disabled by MODEM_ATTACHED",
        }

    result = {
        "attached": True,
        "sim_state": "unknown",
        "signal_rssi": None,
        "signal_dbm": None,
        "signal_ber": None,
        "signal_percent": None,
        "signal_bars": 0,
        "manufacturer": None,
        "model": "A7683E",
        "firmware": None,
        "sim_response": None,
        "signal_response": None,
        "registration_status": None,
        "operator_status": None,
        "packet_attachment_status": None,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "error": None,
    }

    with modem_query_lock, PPP_LOCK:
        resume_ppp = False
        try:
            try:
                stopped = subprocess.run(
                    ["sudo", "poff", "clipper"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(f"Could not safely stop PPP before AT query: {exc}") from exc

            if stopped.returncode == 0:
                logging.info("Paused PPP for modem status query.")
                resume_ppp = True
            else:
                detail = (stopped.stderr or stopped.stdout or "").strip()
                pppd_process = subprocess.run(
                    ["pgrep", "-x", "pppd"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if pppd_process.returncode == 0:
                    raise RuntimeError(
                        "poff did not stop pppd; refusing to access the PPP serial device"
                    )
                if pppd_process.returncode != 1:
                    raise RuntimeError(
                        f"Could not confirm pppd stopped: {pppd_process.stderr.strip()}"
                    )
                logging.info(
                    "PPP was already down before modem query: %s",
                    detail or "no output",
                )
                resume_ppp = True
            time.sleep(1)

            import serial

            with serial.Serial(
                MODEM_SERIAL_PORT,
                baudrate=MODEM_BAUDRATE,
                timeout=0.25,
                write_timeout=2,
            ) as connection:
                send_modem_command(connection, "AT")
                sim_response = send_modem_command(connection, "AT+CPIN?")
                result["sim_response"] = sim_response.strip()[:256]
                sim_match = re.search(r"\+CPIN:\s*([^\r\n]+)", sim_response)
                if sim_match:
                    result["sim_state"] = sim_match.group(1).strip()
                else:
                    raise ValueError("Modem response did not contain a SIM state")

                signal_response = send_modem_command(connection, "AT+CSQ")
                result["signal_response"] = signal_response.strip()[:256]
                signal_match = re.search(r"\+CSQ:\s*(\d+)\s*,\s*(\d+)", signal_response)
                if not signal_match:
                    raise ValueError("Modem response did not contain signal quality")

                rssi = int(signal_match.group(1))
                result["signal_ber"] = int(signal_match.group(2))
                if rssi != 99 and 0 <= rssi <= 31:
                    result["signal_rssi"] = rssi
                    result["signal_dbm"] = -113 + (2 * rssi)
                    result["signal_percent"] = round(rssi * 100 / 31)
                    result["signal_bars"] = min(5, (rssi * 5 + 30) // 31)

                optional_commands = {
                    "manufacturer": "AT+CGMI",
                    "model": "AT+CGMM",
                    "firmware": "AT+CGMR",
                    "registration_status": "AT+CEREG?",
                    "operator_status": "AT+COPS?",
                    "packet_attachment_status": "AT+CGATT?",
                }
                for key, command in optional_commands.items():
                    try:
                        response = send_modem_command(connection, command)
                    except (TimeoutError, OSError) as exc:
                        result[key] = f"Unavailable: {type(exc).__name__}: {exc}"
                        continue
                    if key in ("manufacturer", "model", "firmware"):
                        result[key] = parse_at_value(
                            response,
                            command,
                            prefix="+CGMR:" if key == "firmware" else None,
                        )
                    elif key == "registration_status":
                        result[key] = parse_registration_status(response)
                    elif key == "operator_status":
                        result[key] = parse_operator_status(response)
                    else:
                        result[key] = parse_packet_attachment_status(response)

        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
            logging.exception("A7683E modem status query failed.")
        finally:
            if resume_ppp:
                try:
                    if not run_ppp_command(
                        ["pon", "clipper"],
                        "Resuming Clipper PPP after modem query",
                    ):
                        resume_error = "Failed to resume PPP after modem status query"
                        result["error"] = (
                            f"{result['error']}; {resume_error}"
                            if result["error"]
                            else resume_error
                        )
                except Exception:
                    logging.exception("Failed to resume PPP after modem status query.")
                    result["error"] = "Unexpected failure resuming PPP after modem status query"

    with modem_status_lock:
        modem_status.update(result)
        return copy.deepcopy(modem_status)


def refresh_status_snapshot():
    """Collect current network and modem diagnostics for display or telemetry."""
    refresh_modem_status()
    refresh_network_status()
    return get_status_snapshot()


def refresh_modem_status():
    result = query_modem_status()
    with modem_status_lock:
        modem_status.update(result)
        return copy.deepcopy(modem_status)


def get_status_snapshot():
    with modem_status_lock:
        current_modem_status = copy.deepcopy(modem_status)
    return {
        "interfaces": get_network_status(),
        "modem": current_modem_status,
        "network_available": check_network(),
        "last_successful_upload": (
            thingsboard_uploader.get_last_successful_upload()
            if thingsboard_uploader else None
        ),
    }


def collect_daily_diagnostics():
    snapshot = refresh_status_snapshot()
    modem = snapshot["modem"]
    interfaces = snapshot["interfaces"]
    values = {
        "ppp0_reachable": interfaces["ppp0"]["reachable"],
        "eth0_reachable": interfaces["eth0"]["reachable"],
        "network_available": snapshot["network_available"],
        "modem_attached": modem["attached"],
        "modem_status": "ok" if not modem["error"] else "error",
        "sim_state": modem["sim_state"],
        "signal_bars": modem["signal_bars"],
        "modem_checked_at": modem["checked_at"] or "",
        "modem_model": "A7683E",
    }
    for key in (
        "manufacturer",
        "model",
        "firmware",
        "sim_response",
        "signal_response",
        "signal_rssi",
        "signal_dbm",
        "signal_ber",
        "signal_percent",
        "registration_status",
        "operator_status",
        "packet_attachment_status",
    ):
        value = modem.get(key)
        if value is not None:
            values[key] = value
    for interface in ("ppp0", "eth0"):
        status = interfaces[interface]
        values[f"{interface}_checked_at"] = status.get("checked_at") or ""
        if status.get("error"):
            values[f"{interface}_error"] = str(status["error"])[:240]
    if modem["error"]:
        values["modem_error"] = str(modem["error"])[:240]
    return values


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
    if startup_ppp_succeeded:
        logging.info("PPP startup command completed; checking actual ppp0 reachability.")
    else:
        logging.error("PPP did not start; local data logging will continue while recovery retries.")
    configure_ip()
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=collect_results, daemon=True).start()
    threading.Thread(target=fan, daemon=True).start()
    threading.Thread(target=network_monitor_loop, daemon=True).start()
    threading.Thread(target=refresh_modem_status, daemon=True).start()
    if config_data["CamEnable"] in ("door", "doorcam"):
        def start_camera_thread():
            subprocess.run(["sudo", "python3", "/home/pi/Camera-handle.py"])
        logging.info("Camera/door sensor enabled, starting camera thread")
        try:
            threading.Thread(target=start_camera_thread, daemon=True).start()
        except ImportError as e:
            logging.error(f"Failed to start camera module: {e}")
    
    # Start the uploader regardless of startup connectivity; it waits for the
    # kernel-selected route while local sensor collection continues.
    if config_data.get("thingsboard_enabled", False):
        thingsboard_config = {
            "thingsboard_url": config_data.get("thingsboard_url", ""),
            "thingsboard_token": config_data.get("thingsboard_token", ""),
            "database_path": db_path,
            "state_path": "/var/www/html/thingsboard_upload_state.json",
            "batch_size": config_data.get("batch_size", 100),
            "check_interval": config_data.get("check_interval", 5),
            "http_timeout": 20,
            "connectivity_check": check_network,
            "diagnostics_provider": collect_daily_diagnostics,
            "diagnostics_interval": DAILY_DIAGNOSTICS_INTERVAL,
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
