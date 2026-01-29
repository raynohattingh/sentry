import time
import serial
from pid import PIDController

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/tty.usbserial-1140'  # CHECK THIS (might be ttyACM0)
BAUD_RATE = 115200

# PID TUNING (This is the "Secret Sauce" you will tweak)
# Start conservative. 
# Kp=5.0 means: 100 pixel error -> 500 steps/sec speed.
PAN_PID = PIDController(kp=5.0, ki=0.0, kd=0.1, max_out=1500)
TILT_PID = PIDController(kp=5.0, ki=0.0, kd=0.1, max_out=1500)

CENTER_X = 320 # Half of 640 (Example Resolution)
CENTER_Y = 240 # Half of 480
DEAD_ZONE = 20 # Pixels

def send_velocity_command(ser, pan_speed, tilt_speed):
    """Formats the command V <pan> <tilt>"""
    cmd = f"V {pan_speed:.2f} {tilt_speed:.2f}\n"
    ser.write(cmd.encode())
    print(f"[CMD] {cmd.strip()}")

def main():
    # 1. Setup Serial
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for Arduino reset
        ser.write(b"E 1\n") # Enable Motors
        print("Connected to Sentry Hardware.")
    except Exception as e:
        print(f"Error connecting to Serial: {e}")
        return

    # 2. Mocking the YOLO Loop (Replace this with real YOLO later)
    print("Starting Tracking Loop...")
    try:
        target_x = 600 
        target_y = 240 # Centered vertically
        
        while True:
            # --- REPLACE THIS BLOCK WITH REAL YOLO DATA ---
            # Simulation: Target moves from Left (x=100) to Center (x=320)
            # We pretend the camera sees a target at X=100
            
            target_visible = True
            # -----------------------------------------------

            if target_visible:
                # Calculate Error (Standard Computer Vision Coord System)
                # X: Positive is Right. Y: Positive is Down.
                # If Target is at 100, and Center is 320. Error = 100 - 320 = -220.
                # Negative Error means "Turn Left".
                error_x = target_x - CENTER_X
                error_y = target_y - CENTER_Y

                # Apply Dead Zone
                if abs(error_x) < DEAD_ZONE: error_x = 0
                if abs(error_y) < DEAD_ZONE: error_y = 0

                # Get Velocity from PID
                # Note: We might need to invert (-) depending on motor wiring!
                vel_pan = PAN_PID.update(error_x)
                vel_tilt = TILT_PID.update(error_y)

                send_velocity_command(ser, vel_pan, vel_tilt)

                if target_x < CENTER_X:
                    target_x += 5  # Move target towards center for simulation

                if target_x > CENTER_X:
                    target_x -= 5  # Move target towards center for simulation

                print(f"[TRACKING] Target X: {target_x}, Error X: {error_x}, Pan Speed: {vel_pan:.2f}")

            else:
                # Lost target -> Stop
                send_velocity_command(ser, 0, 0)
                PAN_PID.reset()
                TILT_PID.reset()

            # Control Loop Frequency (e.g., 20Hz = 0.05s)
            # This should match your Camera FPS roughly
            

            time.sleep(0.05) 

    except KeyboardInterrupt:
        print("Stopping...")
        ser.write(b"V 0 0\n")
        ser.write(b"E 0\n")
        ser.close()

if __name__ == "__main__":
    main()