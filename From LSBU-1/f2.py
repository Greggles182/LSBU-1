import re
import subprocess
import serial
import serial.tools.list_ports
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# -----------------------------
# Utility: get available COM ports
# -----------------------------
def get_com_ports():
    return [port.device for port in serial.tools.list_ports.comports() if "USB" in port.description or "COM" in port.device]

# -----------------------------
# Flashing Functionality
# -----------------------------
def flash_devices(output_widget, command):
    ports = get_com_ports()
    if not ports:
        output_widget.insert(tk.END, "❌ No ESP8266 devices found. Check connections and try again.\n")
        return
    for port in ports:
        output_widget.insert(tk.END, f"\n⚡ Flashing ESP8266 on {port}...\n{'='*50}\n")
        cmd = re.sub(r'COM\d{1,2}', port, command)
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            for line in process.stdout:
                output_widget.insert(tk.END, line)
                output_widget.see(tk.END)
            process.wait()
            if process.returncode != 0:
                output_widget.insert(tk.END, f"\n❗ Error flashing {port}:\n")
                for line in process.stderr:
                    output_widget.insert(tk.END, line)
        except Exception as e:
            output_widget.insert(tk.END, f"\n❌ Exception occurred while flashing {port}: {e}\n")
        output_widget.insert(tk.END, f"\n✅ Done with {port}!\n{'='*50}\n")
    output_widget.insert(tk.END, "🎉 All devices flashed!\n")

def start_flash_thread(output_widget, command):
    threading.Thread(target=flash_devices, args=(output_widget, command), daemon=True).start()

# -----------------------------
# Serial Monitor Functionality
# -----------------------------
class SerialMonitor:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.serial_conn = None
        self.stop_thread = False
        self.thread = None

    def connect(self, port, baudrate):
        try:
            self.serial_conn = serial.Serial(port, baudrate, timeout=1)
            self.stop_thread = False
            self.thread = threading.Thread(target=self.read_serial, daemon=True)
            self.thread.start()
            self.text_widget.insert(tk.END, f"Connected to {port} at {baudrate} baud.\n")
        except Exception as e:
            self.text_widget.insert(tk.END, f"Failed to connect: {e}\n")

    def disconnect(self):
        self.stop_thread = True
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.text_widget.insert(tk.END, "Disconnected.\n")

    def read_serial(self):
        while not self.stop_thread and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='replace')
                if line:
                    self.text_widget.insert(tk.END, line)
                    self.text_widget.see(tk.END)
            except Exception as e:
                self.text_widget.insert(tk.END, f"Error reading: {e}\n")
                break
            time.sleep(0.1)

    def send_command(self, command):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(command.encode('utf-8') + b'\n')
            self.text_widget.insert(tk.END, f"Sent: {command}\n")
        else:
            self.text_widget.insert(tk.END, "Serial connection not established.\n")

# -----------------------------
# Tkinter GUI Setup
# -----------------------------
root = tk.Tk()
root.title("ESP8266 Flasher and Serial Monitor")
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# ----- Tab 1: Flash Devices -----
flash_frame = ttk.Frame(notebook)
notebook.add(flash_frame, text="Flash Devices")

flash_command_label = ttk.Label(flash_frame, text="Flashing Command:")
flash_command_label.pack(pady=5)
flash_command_entry = ttk.Entry(flash_frame, width=100)
flash_command_entry.pack(pady=5)

flash_output = scrolledtext.ScrolledText(flash_frame, wrap=tk.WORD, width=80, height=20)
flash_output.pack(padx=10, pady=10, fill='both', expand=True)
flash_button = ttk.Button(flash_frame, text="Flash Devices", command=lambda: start_flash_thread(flash_output, flash_command_entry.get()))
flash_button.pack(pady=5)

# ----- Tab 2: Serial Monitor -----
serial_frame = ttk.Frame(notebook)
notebook.add(serial_frame, text="Serial Monitor")

com_label = ttk.Label(serial_frame, text="Select COM Port:")
com_label.pack(pady=5)
com_var = tk.StringVar()
com_options = get_com_ports()
com_dropdown = ttk.Combobox(serial_frame, textvariable=com_var, values=com_options, state='readonly')
com_dropdown.pack(pady=5)
if com_options:
    com_var.set(com_options[0])

baud_label = ttk.Label(serial_frame, text="Baud Rate:")
baud_label.pack(pady=5)
baud_var = tk.StringVar(value="115200")
baud_dropdown = ttk.Combobox(serial_frame, textvariable=baud_var, values=["115200", "74880", "9600"], state='readonly')
baud_dropdown.pack(pady=5)

serial_output = scrolledtext.ScrolledText(serial_frame, wrap=tk.WORD, width=80, height=15)
serial_output.pack(padx=10, pady=10)

serial_monitor = SerialMonitor(serial_output)

command_label = ttk.Label(serial_frame, text="Command:")
command_label.pack(pady=5)
command_entry = ttk.Entry(serial_frame, width=80)
command_entry.pack(pady=5)

connect_button = ttk.Button(serial_frame, text="Connect", command=lambda: serial_monitor.connect(com_var.get(), int(baud_var.get())))
connect_button.pack(side=tk.LEFT, padx=5, pady=5)

disconnect_button = ttk.Button(serial_frame, text="Disconnect", command=serial_monitor.disconnect)
disconnect_button.pack(side=tk.LEFT, padx=5, pady=5)

send_button = ttk.Button(serial_frame, text="Send", command=lambda: serial_monitor.send_command(command_entry.get()))
send_button.pack(side=tk.LEFT, padx=5, pady=5)

# def refresh_ports():
#     com_options = get_com_ports()
#     com_dropdown['values'] = com_options
#     if com_options:
#         com_var.set(com_options[0])

# send_button = ttk.Button(serial_frame, text="Refresh ports", command= refresh_ports)
# send_button.pack(side=tk.LEFT, padx=5, pady=5)

# Start the Tkinter main loop
root.mainloop()