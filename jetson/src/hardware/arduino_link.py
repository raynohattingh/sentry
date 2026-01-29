# src/hardware/arduino_link.py
import serial
import time
import config

class ArduinoLink:
    def __init__(self):
        self.ser = None
        self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=0.1)
            time.sleep(2) # Wait for Bootloader
            self.send_enable(True)
            print(f"[HARDWARE] Connected to {config.SERIAL_PORT}")
        except serial.SerialException as e:
            print(f"[ERROR] Serial connection failed: {e}")
            self.ser = None

    def send_velocity(self, pan_speed, tilt_speed):
        if not self.ser: return
        
        cmd = f"V {pan_speed:.2f} {tilt_speed:.2f}\n"
        try:
            self.ser.write(cmd.encode())
        except serial.SerialException:
            print("[ERROR] Lost connection to Turret. Reconnecting...")
            self.ser.close()
            self.connect()

    def send_enable(self, state):
        if not self.ser: return
        val = 1 if state else 0
        self.ser.write(f"E {val}\n".encode())