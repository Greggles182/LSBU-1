import os, logging, time, requests, json, subprocess
from gpiozero import Button # type: ignore

# Load camera mode and dbTable from config
CONFIG_PATH = "/var/www/html/data.json"
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
        CAMERA_MODE = config.get("CamEnable", "none")
        DB_TABLE = config.get("dbTable", "data")
except Exception:
    CAMERA_MODE = "none"
    DB_TABLE = "data"

IMAGES_PATH = f"/var/www/html/images/{DB_TABLE}/"
if not os.path.exists(IMAGES_PATH):
    os.makedirs(IMAGES_PATH)

# Initialize button on GPIO4 with debounce (100ms)
button = Button(4, bounce_time=0.1)
enable = Button(15, bounce_time=0.1)

DoorOpen = False
DOT1 = 0
DOT = 0

log_path = "/var/www/html/camera.log"
logging.basicConfig(filename=log_path, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def log_and_print(message, level="info"):
    print(message)
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)

# Add helper to run shell commands and log stdout/stderr/return code
def run_cmd(cmd, timeout=60):
    log_and_print(f"Running command: {cmd}")
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if res.stdout and res.stdout.strip():
            logging.debug(f"cmd stdout: {res.stdout.strip()}")
        if res.stderr and res.stderr.strip():
            logging.debug(f"cmd stderr: {res.stderr.strip()}")
        if res.returncode != 0:
            log_and_print(f"Command failed (code {res.returncode}): {cmd}", "error")
            if res.stderr:
                log_and_print(f"Command stderr: {res.stderr.strip()}", "error")
        else:
            log_and_print(f"Command succeeded: {cmd}")
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        log_and_print(f"Exception running command '{cmd}': {e}", "error")
        return -1, "", str(e)

def print1():
    if enable.is_pressed:
        global DoorOpen, DOT, DOT1
        DoorOpen = False
        DOT = round(time.time()) - DOT1
        log_and_print(f"DOOR SHUT AFTER {DOT} SECONDS")
        if DOT < 10000000:
            url = "http://localhost:8000/Lidata"
            payload = {"data": DOT}
            response = requests.post(url, data=payload)
            log_and_print(response.status_code, response.text)  
    else:
        log_and_print("Enable button not pressed, ignoring door shut event", "warning")

def print2():
    if enable.is_pressed:
        global DoorOpen, DOT1, DOT
        DOT1 = round(time.time())
        DOT = 0
        log_and_print("DOOR OPEN")
        time.sleep(1)  # short delay before taking first picture
        DoorOpen = True

        # Take initial photo when door opens (only if camera mode is doorcam)
        if CAMERA_MODE == "doorcam":
            filename = f"{IMAGES_PATH}{time.strftime('%Y-%m-%d_%H-%M-%S')}_image_1_from_door_open.jpg"
            log_and_print(f"Taking photo: {filename}")
            rc, out, err = run_cmd(f"sudo fswebcam -r 1280x720 --no-banner {filename}")
            if rc == 0:
                if os.path.exists(filename):
                    log_and_print(f"Photo saved: {filename}")
                else:
                    log_and_print(f"Command succeeded but file not found: {filename}", "error")
                    if out:
                        logging.debug(f"fswebcam stdout: {out.strip()}")
                    if err:
                        logging.debug(f"fswebcam stderr: {err.strip()}")
            else:
                log_and_print(f"Failed to save photo: {filename} (rc={rc})", "error")
                if out:
                    logging.debug(f"fswebcam stdout: {out.strip()}")
                if err:
                    logging.debug(f"fswebcam stderr: {err.strip()}")
    else:
        log_and_print("Enable button not pressed, ignoring door open event", "warning")

# Assign event handlers for button press/release
button.when_pressed = print1   # Door shut
button.when_released = print2  # Door open

i = 1
b = 1

try:
    while True:
        if DoorOpen and enable.is_pressed:
            while i <= 10:
                if not DoorOpen:
                    break
                time.sleep(1)
                i += 1
                print(i)
                if i == 10 and b <= 10:
                    # Take repeated photo every 10 seconds (only if camera mode is doorcam)
                    if CAMERA_MODE == "doorcam":
                        filename = f"{IMAGES_PATH}{time.strftime('%Y-%m-%d_%H-%M-%S')}_image_{b}_from_door_open.jpg"
                        log_and_print(f"Taking photo: {filename}")
                        rc, out, err = run_cmd(f"sudo fswebcam -r 1280x720 --no-banner {filename}")
                        if rc == 0:
                            if os.path.exists(filename):
                                log_and_print(f"Photo saved: {filename}")
                            else:
                                log_and_print(f"Command succeeded but file not found: {filename}", "error")
                                if out:
                                    logging.debug(f"fswebcam stdout: {out.strip()}")
                                if err:
                                    logging.debug(f"fswebcam stderr: {err.strip()}")
                        else:
                            log_and_print(f"Failed to save photo: {filename} (rc={rc})", "error")
                            if out:
                                logging.debug(f"fswebcam stdout: {out.strip()}")
                            if err:
                                logging.debug(f"fswebcam stderr: {err.strip()}")
                    i = 1
                    b += 1
        else:
            i = 1
            b = 2
except Exception as e:
    log_and_print(f"Error in camera loop: {e}", "error")
