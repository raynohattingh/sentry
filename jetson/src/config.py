# src/config.py

# HARDWARE
SERIAL_PORT = '/dev/ttyUSB0'  # Check your actual port
BAUD_RATE = 115200

# CAMERA
CAMERA_INDEX = 0
USE_GSTREAMER = True
GST_PIPELINE = (
    "v4l2src device=/dev/video0 ! "
    "video/x-raw, format=YUY2, width=480, height=320, framerate=25/1 ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)

# AI
MODEL_PATH = "yolov8n.pt"
CONF_THRESHOLD = 0.5
TARGET_CLASS_ID = 0  # 0 = Person

# TURRET CONTROL
DEAD_ZONE = 20       # Pixels
CENTER_X = 240
CENTER_Y = 160

# PID CONSTANTS (Tune these!)
PAN_KP = 3.0
PAN_KI = 0.0
PAN_KD = 0.1
PAN_MAX = 2000

TILT_KP = 3.0
TILT_KI = 0.0
TILT_KD = 0.1
TILT_MAX = 1500