import re
import subprocess
import serial.tools.list_ports

# 🔹 MODIFY THIS COMMAND TEMPLATE 🔹
base_command = r'"C:\Users\Gregory\AppData\Local\Arduino15\packages\esp8266\tools\python3\3.7.2-post1/python3" -I "C:\Users\Gregory\AppData\Local\Arduino15\packages\esp8266\hardware\esp8266\3.1.2/tools/upload.py" --chip esp8266 --port "COM26" --baud "115200" ""  --before default_reset --after hard_reset write_flash 0x0 "C:\Users\Gregory\AppData\Local\arduino\sketches\16EAA60C0362615D329EB933F797D478/Sensor-SHT-F.ino.bin"'

# 🔍 Find all connected ESP8266 devices
ports = [port.device for port in serial.tools.list_ports.comports() if "USB" in port.description or "COM" in port.device]

# ⚠️ Check if any ESP8266 devices were found
if not ports:
    print("❌ No ESP8266 devices found. Check connections and try again.")
    exit(1)

# 🚀 Flash each ESP8266
for port in ports:
    print(f"\n⚡ Flashing ESP8266 on {port}...\n{'='*50}")

    # 🔄 Automatically replace COM?/COM?? with actual port
    cmd = re.sub(r'COM\d{1,2}', port, base_command)

    try:
        # Run the command and stream output live
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)

        # Print output as it happens
        for line in process.stdout:
            print(line, end="")  # Avoids extra newlines

        # Wait for process to finish
        process.wait()

        # Print any errors
        if process.returncode != 0:
            print(f"\n❗ Error flashing {port}:")
            for line in process.stderr:
                print(line, end="")

    except Exception as e:
        print(f"\n❌ Exception occurred while flashing {port}: {e}")

    print(f"\n✅ Done with {port}!\n{'='*50}")

print("🎉 All devices flashed!")
