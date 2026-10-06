import os, logging, time, requests, json, subprocess, shutil
from gpiozero import Button # type: ignore
from bounded_logging import SizeCappedFileHandler

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
enable = Button(27, bounce_time=0.1) ###CHANGED FROM 15!!!!!!!!!

DoorOpen = False
DOT1 = 0
DOT = 0

log_path = "/var/www/html/camera.log"
camera_log_handler = SizeCappedFileHandler(log_path, encoding="utf-8")
camera_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
camera_logger = logging.getLogger()
camera_logger.setLevel(logging.DEBUG)
camera_logger.addHandler(camera_log_handler)



# Add helper to run shell commands and log stdout/stderr/return code
def run_cmd(cmd, timeout=60):
    logging.info(f"Running command: {cmd}")
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if res.stdout and res.stdout.strip():
            logging.debug(f"cmd stdout: {res.stdout.strip()}")
        if res.stderr and res.stderr.strip():
            logging.debug(f"cmd stderr: {res.stderr.strip()}")
        if res.returncode != 0:
            logging.error(f"Command failed (code {res.returncode}): {cmd}")
            if res.stderr:
                logging.error(f"Command stderr: {res.stderr.strip()}")
        else:
            logging.info(f"Command succeeded: {cmd}")
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        logging.error(f"Exception running command '{cmd}': {e}")
        return -1, "", str(e)

def print1():
    if enable.is_pressed:
        global DoorOpen, DOT, DOT1
        DoorOpen = False
        DOT = round(time.time()) - DOT1
        logging.info(f"DOOR SHUT AFTER {DOT} SECONDS")
        if DOT < 10000000:
            url = "http://localhost:8000/Lidata"
            payload = {"data": DOT}
            response = requests.post(url, data=payload)
            logging.info(f"{response.status_code}: {response.text}") 
    else:
        logging.warning("Enable button not pressed, ignoring door shut event")

def print2():
    if enable.is_pressed:
        global DoorOpen, DOT1, DOT
        DOT1 = round(time.time())
        DOT = 0
        logging.info("DOOR OPEN")
        time.sleep(1)  # short delay before taking first picture
        DoorOpen = True

        # Take initial photo when door opens (only if camera mode is doorcam)
        if CAMERA_MODE == "doorcam":
            if get_sd_card_usage()["free_GB"] > 0.5:
                filename = f"{IMAGES_PATH}{time.strftime('%Y-%m-%d_%H-%M-%S')}_image_1_from_door_open.jpg"
                logging.info(f"Taking photo: {filename}")
                rc, out, err = run_cmd(f"sudo fswebcam -r 1280x720 --no-banner {filename}")
                if rc == 0:
                    if os.path.exists(filename):
                        logging.info(f"Photo saved: {filename}")
                    else:
                        logging.error(f"Command succeeded but file not found: {filename}")
                        if out:
                            logging.debug(f"fswebcam stdout: {out.strip()}")
                        if err:
                            logging.debug(f"fswebcam stderr: {err.strip()}")
                else:
                    logging.error(f"Failed to save photo: {filename} (rc={rc})")
                    if out:
                        logging.debug(f"fswebcam stdout: {out.strip()}")
                    if err:
                        logging.debug(f"fswebcam stderr: {err.strip()}")
            else:
                logging.error("Insufficient SD card space to take photo")
    else:
        logging.warning("Enable button not pressed, ignoring door open event")

# Assign event handlers for button press/release
button.when_pressed = print1   # Door shut
button.when_released = print2  # Door open

def get_sd_card_usage():
    sd_path = "/"  # Root directory (adjust if necessary)
    total, used, free = shutil.disk_usage(sd_path)
    
    return {
        "total_GB": round(total / (1024 ** 3), 2),      
        "used_GB": round(used / (1024 ** 3), 2),
        "free_GB": round(free / (1024 ** 3), 2),
        "used_percent": round((used / total) * 100, 2)
    }

#Only run loop if camera mode is doorcam as mode is constant
if CAMERA_MODE == "doorcam":
    i = 1
    b = 1
    while True:
        try:
            if DoorOpen and enable.is_pressed:
                while i <= 10:
                    if not DoorOpen:
                        break
                    time.sleep(1)
                    i += 1
                    print(i)
                    if i == 10 and b <= 10:
                        # Take repeated photo every 10 seconds (only if camera mode is doorcam)
                        if get_sd_card_usage()["free_GB"] > 0.5:
                            filename = f"{IMAGES_PATH}{time.strftime('%Y-%m-%d_%H-%M-%S')}_image_{b}_from_door_open.jpg"
                            logging.info(f"Taking photo: {filename}")
                            rc, out, err = run_cmd(f"sudo fswebcam -r 1280x720 --no-banner {filename}")
                            if rc == 0:
                                if os.path.exists(filename):
                                    logging.info(f"Photo saved: {filename}")
                                else:
                                    logging.error(f"Command succeeded but file not found: {filename}")
                                    if out:
                                        logging.debug(f"fswebcam stdout: {out.strip()}")
                                    if err:
                                        logging.debug(f"fswebcam stderr: {err.strip()}")
                            else:
                                logging.error(f"Failed to save photo: {filename} (rc={rc})")
                                if out:
                                    logging.debug(f"fswebcam stdout: {out.strip()}")
                                if err:
                                    logging.debug(f"fswebcam stderr: {err.strip()}")
                        else:
                            logging.error("Insufficient SD card space to take photo")
                    i = 1
                    b += 1
            else:
                i = 1
                b = 1 #Why was this 2 before?
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in camera loop: {e}")
