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
PORT = '/dev/ttyUSB0'#/dev/ttyUSB0  # Replace with your port (e.g., '/dev/ttyUSB0' on Linux)
BAUDRATE = 9600
PARITY = 'N'
STOPBITS = 1
BYTESIZE = 8
TIMEOUT = 1

# Initialize Modbus Serial Client
client = ModbusSerialClient(
    port=PORT,
    baudrate=BAUDRATE,
    parity=PARITY,
    stopbits=STOPBITS,
    bytesize=BYTESIZE,
    timeout=TIMEOUT,
)

# Function to read and decode Modbus registers
def read_register(client, address):
    try:
        response = client.read_input_registers(address=address, count=2)
        if not response.isError():
            # Combine registers in the correct order (high byte first)
            inputArray = [response.registers[1], response.registers[0]]
            int32Val = response.registers[1] + (response.registers[0] << 16)
            decoded_value = struct.unpack('f', struct.pack('i', int32Val))[0]
            return decoded_value, inputArray, int32Val
        else:
            raise Exception(f"Error reading register {address}: {response}")
            return None, None, None
    except Exception as e:
        print(f"Error reading register {address}: {e}")
        return None, None, None

# Main script
if client.connect():
    print("Connected to SDM120M")
    print("-------------------------")

    for address, name in REGISTER_MAP.items():
        #print(f"Reading {name}...")
        value, inputArray, int32Val = read_register(client, address)
        if value is not None:
            print(f"{name}: {value:.2f}")
            # print(f"  Raw Registers: {inputArray}")
            # print(f"  Combined Int32: {int32Val}")
        else:
            print(f"Failed to read {name}")
            print()
    client.close()
else:
    print("Failed to connect to SDM120M")

"""
6. Common MODBUS Register Addresses

Here are some common SDM120M registers:

    0x0000: Voltage (Volts)
    0x0006: Current (Amps)
    0x000C: Active Power (Watts)
    0x0012: Apparent Power (VA)
    0x0018: Reactive Power (VAR)
    0x0046: Total Energy (kWh)

Refer to the SDM120M manual for the full register map.
"""
