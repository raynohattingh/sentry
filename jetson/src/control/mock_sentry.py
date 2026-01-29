import time
import math
import serial
from pid import PIDController

# --- CONFIGURATION ---
# UPDATE THIS PORT!
SERIAL_PORT = '/dev/tty.usbserial-1140'  # Linux/Mac
# SERIAL_PORT = 'COM3'        # Windows

BAUD_RATE = 115200
CENTER_X = 320  # Simulated Image Center (640x480)

# Initialize PIDs
# Kp=5.0: For every 1 pixel of error, add 5 steps/sec of speed
pid_pan = PIDController(kp=5.0, ki=0.0, kd=0.1, max_out=1500)
pid_tilt = PIDController(kp=5.0, ki=0.0, kd=0.1, max_out=1500)

def main():
    try:
        print(f"[SYSTEM] Connecting to {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for Arduino to reboot
        
        # Enable Motors
        print("[SYSTEM] Enabling Motors...")
        ser.write(b"E 1\n")
        time.sleep(0.5)

        start_time = time.time()
        print("[TEST] Starting Sine Wave Simulation (Ctrl+C to stop)")

        while True:
            # 1. SIMULATE TARGET (Sine Wave)
            # Moves between pixel 120 and 520 (Amplitude 200)
            elapsed = time.time() - start_time
            mock_target_x = CENTER_X + (200 * math.sin(elapsed)) 
            
            # 2. CALCULATE ERROR
            error_x = mock_target_x - CENTER_X
            
            # 3. GET PID OUTPUT
            # Invert (-) if motor spins wrong way
            velocity = pid_pan.update(error_x)
            
            # 4. SEND TO ARDUINO
            # Sending 0 for tilt just to test Pan first
            cmd = f"V {velocity:.2f} 0\n"
            ser.write(cmd.encode())

            # 5. DEBUG OUTPUT
            # Visualizing the math
            bar_len = int(abs(error_x) / 10)
            bar = "#" * bar_len
            direction = "<<" if error_x < 0 else ">>"
            print(f"Tgt: {mock_target_x:.0f} | Err: {error_x:.0f} | Spd: {velocity:.0f} | {direction} {bar}")

            time.sleep(0.05) # 20Hz Loop

    except KeyboardInterrupt:
        print("\n[STOP] Emergency Stop triggered!")
        ser.write(b"V 0 0\n") # Stop moving
        ser.write(b"E 0\n")   # Disable motors
        ser.close()
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    main()