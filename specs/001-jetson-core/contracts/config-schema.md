# Contract: Configuration Schema

**Branch**: `001-jetson-core` | **Date**: 2026-02-25  
**Owner**: `jetson/src/config.py` + `jetson/src/utils/config.yaml`

All parameters in `config.py` are Python constants; `config.yaml` documents the same
parameters with units, valid ranges, and defaults for operator reference.
Environment variables override `config.py` defaults at startup.

---

## Hardware

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `SERIAL_PORT` | str | `/dev/ttyUSB0` | — | Valid device path | Arduino serial port |
| `BAUD_RATE` | int | `115200` | baud | Fixed | Serial baud rate |
| `SERIAL_RETRY_INTERVAL_S` | float | `3.0` | seconds | 0.5 – 30 | Delay between reconnect attempts |
| `SERIAL_HEARTBEAT_TIMEOUT_S` | float | `2.0` | seconds | 0.5 – 10 | Max silence before reconnect |
| `LRF_ENABLED` | bool | `true` | — | true/false | Enable laser rangefinder |

---

## Camera

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `CAMERA_INDEX` | int | `0` | — | 0 – 9 | V4L2 device index |
| `CAMERA_WIDTH` | int | `480` | pixels | 320 – 1920 | Frame width |
| `CAMERA_HEIGHT` | int | `320` | pixels | 240 – 1080 | Frame height |
| `USE_GSTREAMER` | bool | `true` | — | true/false | Try GStreamer before V4L2 |
| `GST_PIPELINE` | str | *(see config.py)* | — | Valid pipeline string | GStreamer capture pipeline |
| `CAMERA_FAULT_THRESHOLD` | int | `5` | frames | 1 – 50 | Consecutive failed frame captures before camera fault declared |

---

## AI / Inference

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `MODEL_PATH` | str | `yolov8n.engine` | — | Valid file path | YOLOv8 model (`.pt` or `.engine`) |
| `CONF_THRESHOLD` | float | `0.5` | — | 0.1 – 0.95 | Minimum detection confidence |
| `TARGET_CLASS_ID` | int | `0` | — | 0 – 79 (COCO) | YOLO class ID to track (0 = person) |

---

## Tracking

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `MAX_DISAPPEARED` | int | `30` | frames | 5 – 200 | Frames before target deregistered |
| `MAX_CENTROID_DISTANCE` | int | `300` | pixels | 50 – 500 | Max centroid jump for ID match |

---

## Threat Scoring

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `HIGH_THREAT_THRESHOLD` | float | `80.0` | score | 50 – 100 | Score ≥ this → ACQUIRE state |
| `MED_THREAT_THRESHOLD` | float | `40.0` | score | 10 – 80 | Score ≥ this → TRACK state |
| `W_DISTANCE` | float | `0.4` | — | 0.0 – 1.0 | Distance component weight |
| `W_MOTION` | float | `0.3` | — | 0.0 – 1.0 | Motion component weight |
| `W_GROUPING` | float | `0.2` | — | 0.0 – 1.0 | Grouping component weight |
| `W_TIME_OF_DAY` | float | `0.1` | — | 0.0 – 1.0 | Time-of-day component weight |
| `GROUP_RADIUS_PX` | int | `80` | pixels | 10 – 500 | Pixel-distance threshold for considering two targets grouped |
| `GROUP_MAX_COUNT` | int | `3` | count | 1 – 20 | Target count at which grouping component saturates to 1.0 |
| `LRF_SAMPLE_INTERVAL_MS` | int | `500` | ms | 100 – 5000 | Interval between LRF firings in look→sweep→look medium-threat sampling |
| `LRF_SWEEP_ARC_DEG` | float | `5.0` | degrees | 1.0 – 30.0 | Pan offset applied between first and second LRF firing in sampled-track mode |
| `NIGHT_START_HOUR` | int | `20` | hour (0–23) | 0 – 23 | Hour when night multiplier activates |
| `NIGHT_END_HOUR` | int | `6` | hour (0–23) | 0 – 23 | Hour when night multiplier deactivates |

---

## Motion Control (PID)

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `PAN_KP` | float | `3.0` | — | 0.1 – 20 | Pan proportional gain |
| `PAN_KI` | float | `0.0` | — | 0.0 – 5 | Pan integral gain |
| `PAN_KD` | float | `0.1` | — | 0.0 – 2 | Pan derivative gain |
| `PAN_MAX` | float | `1500.0` | steps/sec | 100 – 3000 | Pan max velocity |
| `TILT_KP` | float | `3.0` | — | 0.1 – 20 | Tilt proportional gain |
| `TILT_KI` | float | `0.0` | — | 0.0 – 5 | Tilt integral gain |
| `TILT_KD` | float | `0.1` | — | 0.0 – 2 | Tilt derivative gain |
| `TILT_MAX` | float | `1500.0` | steps/sec | 100 – 3000 | Tilt max velocity |
| `DEAD_ZONE` | int | `20` | pixels | 5 – 100 | Zero-velocity dead zone radius |
| `CENTER_X` | int | `240` | pixels | — | Frame centre X (= CAMERA_WIDTH / 2) |
| `CENTER_Y` | int | `160` | pixels | — | Frame centre Y (= CAMERA_HEIGHT / 2) |
| `IDLE_TIMEOUT_S` | float | `5.0` | seconds | 1.0 – 60 | No-target timeout before SCAN |

---

## Turret Limits

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `PAN_LIMIT_WARN_STEPS` | int | `4500` | steps | 100 – 50000 | Pan taper zone start (absolute) |
| `PAN_LIMIT_HARD_STEPS` | int | `5000` | steps | 100 – 50000 | Pan hard stop (absolute) |
| `TILT_LIMIT_WARN_STEPS` | int | `900` | steps | 100 – 10000 | Tilt taper zone start (absolute) |
| `TILT_LIMIT_HARD_STEPS` | int | `1000` | steps | 100 – 10000 | Tilt hard stop (absolute) |
| `STEPS_PER_DEGREE` | float | `10.0` | steps/degree | 1 – 100 | Mechanical conversion factor |

---

## FSM

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `MIN_DWELL_MS_SCAN` | int | `500` | ms | 0 – 5000 | Min time in SCAN before downward transition |
| `MIN_DWELL_MS_TRACK` | int | `300` | ms | 0 – 5000 | Min time in TRACK before downward transition |
| `MIN_DWELL_MS_ACQUIRE` | int | `500` | ms | 0 – 5000 | Min time in ACQUIRE before downward transition |
| `MIN_DWELL_MS_SEARCH` | int | `200` | ms | 0 – 5000 | Min time in SEARCH before downward transition |
| `SEARCH_ARC_DEG` | float | `45.0` | degrees | 10 – 180 | Half-arc width for SEARCH sweep |
| `SEARCH_TIMEOUT_S` | float | `10.0` | seconds | 2 – 60 | SEARCH → SCAN if no re-acquisition |
| `SCAN_PAN_MIN` | int | `-4000` | steps | -50000 – 0 | Left boundary of SCAN sweep |
| `SCAN_PAN_MAX` | int | `4000` | steps | 0 – 50000 | Right boundary of SCAN sweep |
| `SCAN_VELOCITY` | float | `200.0` | steps/sec | 10 – 1500 | SCAN sweep speed |
| `SCAN_TILT_HOME` | int | `0` | steps | -1000 – 1000 | Tilt position during SCAN |

---

## Geospatial

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `SENTRY_LAT` | float | `0.0` | decimal degrees | -90 – 90 | Sentry GPS latitude |
| `SENTRY_LON` | float | `0.0` | decimal degrees | -180 – 180 | Sentry GPS longitude |
| `SENTRY_HEADING_DEG` | float | `0.0` | degrees (true north) | 0 – 360 | Turret zero-pan = true north offset |

---

## Telemetry & Logging

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `TELEMETRY_LOG_PATH` | str | `/app/logs/telemetry.jsonl` | — | Valid path | JSON-lines output file |
| `TELEMETRY_MAX_BYTES` | int | `10485760` | bytes | 1MB – 1GB | Max log file size before rotation |
| `TELEMETRY_BACKUP_COUNT` | int | `5` | — | 1 – 50 | Number of rotated log files to keep |
| `MQTT_BROKER` | str | `localhost` | — | Hostname or IP | MQTT broker host |
| `MQTT_PORT` | int | `1883` | — | 1 – 65535 | MQTT broker port |
| `MQTT_TOPIC` | str | `sentry/telemetry` | — | Valid topic string | MQTT publish topic |

---

## Web HUD

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `WEB_HOST` | str | `0.0.0.0` | — | Valid bind address | Flask bind address |
| `WEB_PORT` | int | `5000` | — | 1024 – 65535 | Flask bind port |
| `HUD_USERNAME` | str | `sentry` | — | Non-empty string | HTTP Basic Auth username |
| `HUD_PASSWORD` | str | `changeme` | — | Non-empty string | HTTP Basic Auth password |

---

## Resilience

| Parameter | Type | Default | Units | Valid Range | Description |
|-----------|------|---------|-------|-------------|-------------|
| `MAX_BOOT_FAILURES` | int | `3` | — | 1 – 10 | Consecutive failures before Jetson OS reboot |
| `BOOT_STATE_PATH` | str | `/app/state/boot_state.json` | — | Valid path | Persistent boot failure counter file |
