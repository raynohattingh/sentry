"""Sentry Jetson Core — centralised configuration.

All numeric constants, thresholds, and configuration values live here.
No magic numbers are permitted in any other module.

Environment variables override these defaults at startup; see utils/config.yaml
for documentation of every parameter with units, valid ranges, and defaults.
"""

import os

# ---------------------------------------------------------------------------
# Hardware — Serial
# ---------------------------------------------------------------------------

SERIAL_PORT: str = os.environ.get("SERIAL_PORT", "/dev/ttyUSB0")
BAUD_RATE: int = 115200
SERIAL_RETRY_INTERVAL_S: float = 3.0
SERIAL_HEARTBEAT_TIMEOUT_S: float = 2.0
LRF_ENABLED: bool = True

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

CAMERA_INDEX: int = 0
CAMERA_WIDTH: int = 480
CAMERA_HEIGHT: int = 320
USE_GSTREAMER: bool = True
GST_PIPELINE: str = (
    "v4l2src device=/dev/video0 ! "
    "video/x-raw, format=YUY2, width=480, height=320, framerate=25/1 ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)
CAMERA_FAULT_THRESHOLD: int = 5  # Consecutive failed frames before fault declared
CAMERA_FPS: int = int(os.environ.get("CAMERA_FPS", "25"))
CAMERA_HFOV_DEG: float = float(os.environ.get("CAMERA_HFOV_DEG", "120.0"))

# ---------------------------------------------------------------------------
# AI / Inference
# ---------------------------------------------------------------------------

MODEL_PATH: str = os.environ.get("MODEL_PATH", "yolov8n.engine")
CONF_THRESHOLD: float = 0.5
TARGET_CLASS_ID: int = 0  # 0 = person (COCO)

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

MAX_DISAPPEARED: int = 30
MAX_CENTROID_DISTANCE: int = 300  # pixels

# ---------------------------------------------------------------------------
# Threat Scoring
# ---------------------------------------------------------------------------

HIGH_THREAT_THRESHOLD: float = 80.0
MED_THREAT_THRESHOLD: float = 40.0

W_DISTANCE: float = 0.4
W_MOTION: float = 0.3
W_GROUPING: float = 0.2
W_TIME_OF_DAY: float = 0.1

GROUP_RADIUS_PX: int = 80
GROUP_MAX_COUNT: int = 3

LRF_SAMPLE_INTERVAL_MS: int = 500
LRF_SWEEP_ARC_DEG: float = 5.0

NIGHT_START_HOUR: int = 20
NIGHT_END_HOUR: int = 6

# ---------------------------------------------------------------------------
# Motion Control (PID)
# ---------------------------------------------------------------------------

PAN_KP: float = 3.0
PAN_KI: float = 0.0
PAN_KD: float = 0.1
PAN_MAX: float = 1500.0

TILT_KP: float = 3.0
TILT_KI: float = 0.0
TILT_KD: float = 0.1
TILT_MAX: float = 1500.0

DEAD_ZONE: int = 20  # pixels
CENTER_X: int = CAMERA_WIDTH // 2   # 240
CENTER_Y: int = CAMERA_HEIGHT // 2  # 160

IDLE_TIMEOUT_S: float = 5.0

# Anti-windup clamp for PID integral term (steps/sec equivalent)
PID_MAX_INTEGRAL: float = 500.0

# ---------------------------------------------------------------------------
# Turret Limits
# ---------------------------------------------------------------------------

PAN_LIMIT_WARN_STEPS: int = 4500
PAN_LIMIT_HARD_STEPS: int = 5000
TILT_LIMIT_WARN_STEPS: int = 900
TILT_LIMIT_HARD_STEPS: int = 1000
STEPS_PER_DEGREE: float = 10.0

# ---------------------------------------------------------------------------
# FSM Dwell Timers
# ---------------------------------------------------------------------------

MIN_DWELL_MS_SCAN: int = 500
MIN_DWELL_MS_TRACK: int = 300
MIN_DWELL_MS_ACQUIRE: int = 500
MIN_DWELL_MS_SEARCH: int = 200

# ---------------------------------------------------------------------------
# Scan Sweep
# ---------------------------------------------------------------------------

SCAN_PAN_MIN: int = -4000  # steps (left boundary)
SCAN_PAN_MAX: int = 4000   # steps (right boundary)
SCAN_VELOCITY: float = 200.0  # steps/sec
SCAN_TILT_HOME: int = 0    # steps

# ---------------------------------------------------------------------------
# Search Arc
# ---------------------------------------------------------------------------

SEARCH_ARC_DEG: float = 45.0   # half-arc width in degrees
SEARCH_TIMEOUT_S: float = 10.0  # SEARCH -> SCAN timeout

# ---------------------------------------------------------------------------
# GPS / Geo
# ---------------------------------------------------------------------------

SENTRY_LAT: float = 0.0
SENTRY_LON: float = 0.0
SENTRY_HEADING_DEG: float = 0.0  # degrees from true north at pan=0

# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

TELEMETRY_LOG_PATH: str = os.environ.get("TELEMETRY_LOG_PATH", "/app/logs/telemetry.jsonl")
TELEMETRY_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
TELEMETRY_BACKUP_COUNT: int = 5

# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------

MQTT_BROKER: str = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT: int = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_TOPIC: str = os.environ.get("MQTT_TOPIC", "sentry/telemetry")
MQTT_COMMAND_TOPIC: str = os.environ.get("MQTT_COMMAND_TOPIC", "sentry/command")
MQTT_USERNAME: str = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD: str = os.environ.get("MQTT_PASSWORD", "")
SENTRY_ID: str = os.environ["SENTRY_ID"]
COMMAND_SAFETY_TIMEOUT_S: float = float(os.environ.get("COMMAND_SAFETY_TIMEOUT_S", "3.0"))
COMMAND_RATE_LIMIT_HZ: int = int(os.environ.get("COMMAND_RATE_LIMIT_HZ", "20"))

# ---------------------------------------------------------------------------
# Web HUD
# ---------------------------------------------------------------------------

HUD_USERNAME: str = os.environ.get("HUD_USERNAME", "sentry")
HUD_PASSWORD: str = os.environ.get("HUD_PASSWORD", "changeme")

# ---------------------------------------------------------------------------
# Resilience / Boot Counter
# ---------------------------------------------------------------------------

MAX_BOOT_FAILURES: int = 3
BOOT_STATE_PATH: str = os.environ.get("BOOT_STATE_PATH", "/app/state/boot_state.json")
