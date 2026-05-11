# Farm Sentry

An autonomous farm-security sentry that detects, tracks, and classifies threats in real time using a pan/tilt turret, AI-accelerated inference on NVIDIA Jetson, and a tactical mobile app for remote monitoring and manual override. Designed for offline operation with no cloud dependency.

## System Overview

```
                  ┌─────────────────────────────────────┐
                  │         NVIDIA Jetson Orin/NX        │
                  │                                      │
  USB Serial      │  Camera -> YOLO -> Tracker -> Scorer │   MQTT (TLS)
 ┌──────────┐     │  -> SentryBrain FSM -> ArduinoLink   │<--------------> MQTT Broker
 │ Arduino  │<----│  -> TelemetryRecorder -> MQTT Pub    │
 │ (Turret) │     │  -> Flask MJPEG stream (port 5000)   │   HTTP(S) MJPEG
 └──────────┘     └─────────────────────────────────────-┘<--------------> Mobile App
  Stepper Motors                                                           (Flutter)
  Limit Switches
  Laser Rangefinder
```

Four components, three communication links:

| Link | Protocol | Purpose |
|------|----------|---------|
| Jetson <-> Arduino | USB Serial (115200 baud) | Velocity commands, position heartbeats, LRF readings, limit events |
| Jetson <-> MQTT Broker | MQTT over TLS (port 8883) | Telemetry, safety status, manual override commands |
| App <-> MQTT Broker | MQTT over TLS (port 8883) | Telemetry display, manual override joystick |
| App <-> Jetson | HTTP(S) (port 5000) | On-demand MJPEG video stream |

---

## Repository Structure

```
sentry/
├── jetson/                     # Python backend (NVIDIA Jetson)
│   ├── src/
│   │   ├── main.py             # Control loop entry point
│   │   ├── config.py           # All constants (env vars override at runtime)
│   │   ├── sentry_types.py     # Shared dataclasses and enums
│   │   ├── comms/              # MQTT publisher/subscriber + serial I/O
│   │   ├── control/            # FSM, PID, threat scoring, geo, turret manager
│   │   ├── hardware/           # Arduino serial bridge
│   │   ├── vision/             # Camera, YOLOv8 detector, centroid tracker
│   │   ├── telemetry/          # Telemetry recording + MQTT emission
│   │   └── web/                # Flask MJPEG stream with HTTP Basic Auth
│   ├── tests/                  # pytest unit, integration, and system tests
│   ├── docker/                 # Dockerfile + docker-compose.yaml
│   ├── requirements.txt        # Production dependencies
│   └── requirements-dev.txt    # Test dependencies
│
├── arduino/sentry_turret/      # Arduino Uno R3 firmware (PlatformIO)
│   ├── src/                    # .ino + .cpp/.h modules
│   ├── test/                   # Unity unit tests (native, no hardware)
│   └── platformio.ini
│
├── app/                        # Flutter mobile app (iOS + Android)
│   ├── lib/                    # Dart source
│   │   ├── features/           # Map, alerts, calibration, override, video, setup
│   │   ├── models/             # Data models
│   │   └── services/           # MQTT, location, notifications
│   └── test/                   # Dart unit + widget tests
│
└── specs/                      # Feature specifications
```

---

## Prerequisites

### Hardware

- NVIDIA Jetson Orin NX / Nano (JetPack 6)
- USB camera (V4L2-compatible, e.g. thermal or optical)
- Arduino Uno R3 + CNC Shield V3 + 2x A4988 or DRV8825 stepper drivers
- 2x NEMA stepper motors (pan and tilt axes)
- 4x normally-open limit switches (pan-left, pan-right, tilt-up, tilt-down)
- Laser rangefinder module (8-byte binary frame, 0x55 0xAA sync)
- A machine to run an MQTT broker (can be the Jetson itself, a Pi, or any server on the LAN)

### Software

| Component | Version |
|-----------|---------|
| Jetson OS | JetPack 6 (Ubuntu 22.04) |
| Docker | Docker Engine + NVIDIA Container Toolkit |
| PlatformIO | PlatformIO Core CLI or VS Code extension |
| Flutter | 3.22+ / Dart ^3.10 |
| MQTT Broker | Mosquitto 2.x (or any MQTT v3.1.1 broker with TLS) |

---

## Setup Guide

### Step 1 -- Set Up the MQTT Broker

Both the Jetson and the mobile app connect to this broker. Set it up first.

**Install Mosquitto** (on any machine on your LAN):

```bash
sudo apt install mosquitto mosquitto-clients
```

**Configure TLS** (`/etc/mosquitto/conf.d/sentry.conf`):

```
listener 8883
cafile   /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile  /etc/mosquitto/certs/server.key
require_certificate false

allow_anonymous false
password_file /etc/mosquitto/passwd
```

**Create credentials and start:**

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd sentry
# Enter password when prompted

sudo systemctl restart mosquitto
```

**Verify** from another terminal:

```bash
mosquitto_sub -h <broker-ip> -p 8883 --cafile ca.crt -u sentry -P <password> -t "sentry/#"
```

> For development without TLS, you can use port 1883 with `allow_anonymous true`, but this is insecure and should never be used in the field.

---

### Step 2 -- Flash the Arduino

Connect the Arduino Uno to your computer via USB.

```bash
cd arduino/sentry_turret

# PlatformIO CLI
pio run --environment uno --target upload

# Or open sentry_turret.ino in Arduino IDE
# Board: Arduino Uno | Port: /dev/ttyUSB0 | Baud: 115200
```

**Verify:** Open the serial monitor at 115200 baud. You should see `POS 0 0` every 100ms.

**Run firmware unit tests** (no hardware needed):

```bash
pio test --environment native
```

**Pin reference** (all configurable in `config.h`):

| Signal | Pin | Notes |
|--------|-----|-------|
| Pan STEP / DIR | D2 / D5 | X-axis on CNC Shield |
| Tilt STEP / DIR | D3 / D6 | Y-axis on CNC Shield |
| Stepper ENABLE | D8 | Active-LOW, held LOW |
| Limit Pan L/R | D9 / D10 | Normally-open, INPUT_PULLUP |
| Limit Tilt D/U | D11 / D12 | Normally-open, INPUT_PULLUP |
| LRF RX / TX | A0 / A1 | SoftwareSerial |
| LRF ENABLE | A2 | Active-LOW enable |

---

### Step 3 -- Deploy the Jetson Core

Connect the Arduino to the Jetson via USB. Connect the camera to the Jetson.

**Choose a housing profile:**

| Profile | Use case | Behavior |
|---------|----------|----------|
| `TEST_BENCH` | Bench testing without limit switches | Motion allowed within software-defined bounds |
| `MVP` | Production housing with physical limit switches | Motion blocked until all 4 limit switches are validated |

#### Option A -- Docker (recommended)

Create a `.env` file in `jetson/docker/`:

```bash
# Required
SENTRY_ID=my-sentry-001
MQTT_BROKER=192.168.1.100
MQTT_USERNAME=sentry
MQTT_PASSWORD=your-password
HUD_USERNAME=operator
HUD_PASSWORD=your-hud-password

# Housing profile
HOUSING_PROFILE=TEST_BENCH
TEST_BENCH_PAN_MIN_STEPS=-4000
TEST_BENCH_PAN_MAX_STEPS=4000
TEST_BENCH_TILT_MIN_STEPS=-900
TEST_BENCH_TILT_MAX_STEPS=900

# Optional
SENTRY_LAT=-26.012345
SENTRY_LON=28.012345
SENTRY_HEADING_DEG=0.0
TIMEZONE_OFFSET_H=2
```

```bash
cd jetson
docker compose -f docker/docker-compose.yaml --env-file docker/.env up --build -d
docker logs -f sentry_brain
```

#### Option B -- Run directly

```bash
cd jetson/src
pip3 install -r ../requirements.txt

SENTRY_ID=my-sentry-001 \
MQTT_BROKER=192.168.1.100 \
MQTT_USERNAME=sentry \
MQTT_PASSWORD=your-password \
HUD_PASSWORD=your-hud-password \
HOUSING_PROFILE=TEST_BENCH \
TEST_BENCH_PAN_MIN_STEPS=-4000 \
TEST_BENCH_PAN_MAX_STEPS=4000 \
TEST_BENCH_TILT_MIN_STEPS=-900 \
TEST_BENCH_TILT_MAX_STEPS=900 \
python3 main.py
```

**Verify:** Look for `[SYSTEM] Sentry Core Online.` and `[MQTT] Connected to broker` in the logs. The web HUD is at `http://<jetson-ip>:5000`.

> For TLS certificate verification (recommended), set `MQTT_TLS_VERIFY=true` and `MQTT_CA_CERT=/path/to/ca.crt`. Without these, TLS is encrypted but does not verify the broker's identity.

---

### Step 4 -- Build and Run the Mobile App

```bash
cd app
flutter pub get
flutter run          # connected device or emulator
```

The app opens to the **Setup** screen on first launch. Enter:

| Field | Value |
|-------|-------|
| Broker Host | IP of your MQTT broker |
| Broker Port | `8883` |
| MQTT Username | Broker username |
| MQTT Password | Broker password |
| Sentry ID | Must match `SENTRY_ID` on the Jetson |
| Video Host | IP of the Jetson |
| Video Port | `5000` |
| Video Username | HUD username (default: `sentry`) |
| Video Password | HUD password |

After saving, the app connects to the broker and displays the tactical map.

**Build for release:**

```bash
flutter build apk --release    # Android
flutter build ios --release    # iOS (requires Xcode)
```

---

### Step 5 -- First-Run Calibration

Open the **Calibration** screen in the app:

1. **Pin Sentry Location** -- Tap "Use My Location" if you are standing at the sentry, or enter GPS coordinates manually.
2. **True North Offset** -- With the turret at pan=0, measure the angle between the camera's forward direction and true north using a compass. Enter this value in degrees.

After saving, update `SENTRY_LAT`, `SENTRY_LON`, and `SENTRY_HEADING_DEG` in the Jetson environment and restart the container.

---

### Step 6 -- Verify End-to-End

1. Confirm `POS` heartbeats in the Jetson logs (Arduino is connected)
2. Open the web HUD at `http://<jetson-ip>:5000` -- you should see the camera feed
3. Walk in front of the camera -- the turret should begin tracking
4. Check the mobile app map -- threat markers should appear at the correct GPS location
5. Open the **Override** screen -- the joystick should move the turret
6. Release the joystick -- the turret should stop within 3 seconds (safety timeout)

For **MVP housing**, manually actuate each limit switch once. The Jetson logs will show `LIMIT PAN LEFT`, `LIMIT PAN RIGHT`, `LIMIT TILT DOWN`, `LIMIT TILT UP`. Once all four are seen, `sentry/status` transitions to `HARDWARE_LIMITS_ACTIVE` and motion is allowed.

---

## Configuration Reference

### Jetson Environment Variables

All values in `config.py` can be overridden with environment variables. See `jetson/src/utils/config.yaml` for the full reference with units and valid ranges.

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_ID` | *required* | Unique sentry identifier (must match the app) |
| `MQTT_BROKER` | `localhost` | MQTT broker hostname or IP |
| `MQTT_PORT` | `8883` | Broker port |
| `MQTT_USERNAME` | `""` | Broker username |
| `MQTT_PASSWORD` | `""` | Broker password |
| `MQTT_TLS_VERIFY` | `true` | Verify broker TLS certificate |
| `MQTT_CA_CERT` | `None` | Path to CA certificate for TLS verification |
| `HOUSING_PROFILE` | `MVP` | `TEST_BENCH` or `MVP` |
| `TEST_BENCH_PAN_MIN_STEPS` | `None` | Software pan lower bound (TEST_BENCH only) |
| `TEST_BENCH_PAN_MAX_STEPS` | `None` | Software pan upper bound (TEST_BENCH only) |
| `TEST_BENCH_TILT_MIN_STEPS` | `None` | Software tilt lower bound (TEST_BENCH only) |
| `TEST_BENCH_TILT_MAX_STEPS` | `None` | Software tilt upper bound (TEST_BENCH only) |
| `SERIAL_PORT` | `/dev/ttyUSB0` | Arduino USB serial device |
| `MODEL_PATH` | `yolov8n.engine` | TensorRT model path |
| `CAMERA_FPS` | `25` | Camera frame rate |
| `CAMERA_HFOV_DEG` | `120.0` | Camera horizontal FOV (calibrate per lens) |
| `SENTRY_LAT` | `0.0` | Sentry latitude (WGS-84) |
| `SENTRY_LON` | `0.0` | Sentry longitude (WGS-84) |
| `SENTRY_HEADING_DEG` | `0.0` | True north offset at pan=0 |
| `TIMEZONE_OFFSET_H` | `0` | Hours offset from UTC for night/day threat scoring |
| `HUD_USERNAME` | `sentry` | Web HUD Basic Auth username |
| `HUD_PASSWORD` | `changeme` | Web HUD Basic Auth password (**change before deployment**) |
| `HUD_BIND_ADDRESS` | `0.0.0.0` | Web HUD bind address |
| `COMMAND_SAFETY_TIMEOUT_S` | `3.0` | Auto-stop if no joystick command within this window |

---

## Protocol Reference

### MQTT Topics

**`sentry/telemetry`** (Jetson -> App) -- published per tracked target per loop tick:

```json
{
  "sentry_id": "my-sentry-001",
  "session_id": "uuid4",
  "target_id": 1,
  "threat_score": 87.3,
  "tier": "HIGH",
  "lat": -26.012,
  "lon": 28.012,
  "lrf_distance_m": 47.2,
  "pan_angle": 12.5,
  "tilt_angle": -3.0,
  "timestamp_utc": "2026-02-27T10:00:00.000Z",
  "velocity_vector": {"vx": 0.42, "vy": 0.11},
  "fsm_state": "ACQUIRE"
}
```

The `sentry_id` field enables multi-sentry deployments: the app filters incoming telemetry by `sentry_id` so a single broker can serve multiple turrets simultaneously.

**`sentry/command`** (App -> Jetson) -- joystick commands at up to 10 Hz:

```json
{
  "sentry_id": "my-sentry-001",
  "pan_velocity": 150.0,
  "tilt_velocity": -80.0,
  "timestamp_utc": "2026-02-27T10:00:00.000Z"
}
```

**`sentry/status`** (Jetson -> App) -- published on state change:

```json
{
  "sentry_id": "my-sentry-001",
  "housing_profile": "MVP",
  "protection_mode": "HARDWARE_LIMITS_ACTIVE",
  "motion_allowed": true,
  "motion_block_reason": null,
  "validated_switches": ["PAN_LEFT", "PAN_RIGHT", "TILT_DOWN", "TILT_UP"],
  "timestamp_utc": "2026-03-23T17:00:00Z"
}
```

### Serial Protocol (Jetson <-> Arduino, 115200 baud)

| Direction | Format | Description |
|-----------|--------|-------------|
| Jetson -> Arduino | `V <pan> <tilt>\n` | Set velocity (steps/sec). `V 0.0 0.0\n` to stop. |
| Jetson -> Arduino | `L\n` | Trigger LRF ranging shot |
| Arduino -> Jetson | `POS <pan> <tilt>\n` | Position heartbeat every 100ms |
| Arduino -> Jetson | `DIST <metres>\n` | LRF distance (-1.0 = error) |
| Arduino -> Jetson | `LIMIT PAN LEFT\n` | Limit switch triggered (also: `PAN RIGHT`, `TILT DOWN`, `TILT UP`) |

---

## How It Works

### Control Loop

The main loop runs at 20+ Hz on the Jetson:

1. **Capture** frame from camera
2. **Detect** targets with YOLOv8n (TensorRT)
3. **Track** targets with centroid matching (Hungarian algorithm) to maintain persistent IDs
4. **Score** threats using a weighted formula: distance (40%), motion (30%), grouping (20%), time-of-day (10%)
5. **Classify** into tiers: LOW (0-39), MED (40-79), HIGH (80-100)
6. **FSM decides** state and computes velocity via PID controllers
7. **Send** velocity to Arduino over serial
8. **Record** telemetry to MQTT and JSON-lines log
9. **Stream** annotated video to the web HUD

### FSM States

| State | Trigger | Behavior |
|-------|---------|----------|
| SCAN | No targets / LOW tier | Pan sweep between limits |
| TRACK | MED tier target | PID tracking with sampled LRF |
| ACQUIRE | HIGH tier target | Hard lock with continuous LRF |
| SEARCH | Target lost from TRACK/ACQUIRE | Arc sweep around last-known position (10s timeout) |
| MANUAL_OVERRIDE | Joystick command received | Operator has direct control (3s safety timeout) |

Upward transitions (SCAN -> ACQUIRE) are immediate. Downward transitions require dwell timers to prevent oscillation.

### Threat Scoring

| Factor | Weight | Range |
|--------|--------|-------|
| Distance (bbox area proxy) | 40% | Larger bbox = closer = higher |
| Motion (pixel velocity) | 30% | Faster movement = higher |
| Grouping (nearby targets) | 20% | More targets nearby = higher |
| Time of day | 10% | Night hours (20:00-06:00) = bonus |

### Alert Log and Notifications

The alert log in the **Alerts** screen stores only tier-transition events (e.g. LOW → MED, MED → HIGH). Repeated telemetry records for the same target at the same tier are not persisted, keeping the SQLite file small at 20 Hz. Entries older than the configured retention period (default 7 days, configurable in Settings) are purged at startup.

Push notifications follow the same transition logic and additionally suppress re-notification for the same target+tier for 30 seconds. HIGH-tier alerts use the alarm audio channel on Android and critical notifications on iOS so they break through Do Not Disturb.

---

## Running Tests

```bash
# Arduino firmware (native, no hardware)
cd arduino/sentry_turret && pio test --environment native

# Jetson Python
cd jetson
pip install -r requirements-dev.txt
SENTRY_ID=test python3 -m pytest tests/unit/ -v

# Flutter app
cd app && flutter test
```

---

## Troubleshooting

**`SENTRY_ID` not set** -- The Jetson requires this env var and will exit with a clear error if it is missing.

**`[MQTT] Connection error`** -- Check broker reachability (`ping <broker>`), verify port 8883 is open (`nc -zv <broker> 8883`), and confirm credentials match.

**`[GEO] SENTRY_LAT and SENTRY_LON are both 0.0`** -- Run the Calibration screen in the app, then update `SENTRY_LAT` and `SENTRY_LON` in the Jetson environment.

**Arduino not responding** -- Check USB connection (`ls /dev/ttyUSB*`), verify baud 115200 in both `config.h` and Jetson `SERIAL_PORT`. Open the serial monitor to confirm `POS 0 0` heartbeats.

**LRF always returns -1.0** -- Check wiring (LRF TX -> Arduino A0, RX -> A1, Enable -> A2). If framing errors persist, reduce `LRF_SOFTSERIAL_BAUD` to 57600 in `config.h`.

**Map shows threats at wrong location** -- Re-measure the True North offset on the Calibration screen. The offset corrects for the angle between the camera's forward axis and true north.

**App shows "Sentry Offline"** -- No telemetry received in 10 seconds. Check: Jetson is running, `SENTRY_ID` matches between app and Jetson, broker is reachable from the phone's network.

**Joystick has no effect** -- Verify `[CMD] CommandSubscriber started` in Jetson logs and that the app's Sentry ID matches the Jetson's `SENTRY_ID` exactly.

**Setup screen resets calibration/GPS fields** -- Re-entering broker credentials via Settings -> Re-configure now preserves `sentryLat`, `sentryLon`, `northOffsetDegrees`, and `retentionDays` from the previous save. Only the fields shown on screen are overwritten.

**HUD password warning in logs** -- Change `HUD_PASSWORD` from the default `changeme` before deployment.

---

## License

Private -- all rights reserved.
