# 🛡️ Farm Sentry — Autonomous Thermal Surveillance System

An autonomous farm-security sentry that detects, tracks, and classifies threats in real time using a pan/tilt thermal camera turret, AI-accelerated inference on NVIDIA Jetson, and a tactical mobile app for remote monitoring and manual override.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Components](#components)
  - [Jetson Core (Python Backend)](#1-jetson-core-python-backend)
  - [Arduino Firmware](#2-arduino-firmware)
  - [Mobile App (Flutter)](#3-mobile-app-flutter)
- [MQTT Protocol Reference](#mqtt-protocol-reference)
- [Serial Protocol Reference](#serial-protocol-reference)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [Step 1 — Flash the Arduino](#step-1--flash-the-arduino)
  - [Step 2 — Deploy the Jetson Core](#step-2--deploy-the-jetson-core)
  - [Step 3 — Set Up the MQTT Broker](#step-3--set-up-the-mqtt-broker)
  - [Step 4 — Build and Run the Mobile App](#step-4--build-and-run-the-mobile-app)
  - [Step 5 — First-Run Calibration](#step-5--first-run-calibration)
- [Configuration Reference](#configuration-reference)
  - [Jetson Environment Variables](#jetson-environment-variables)
  - [Arduino Hardware Pins](#arduino-hardware-pins)
  - [Mobile App Settings](#mobile-app-settings)
- [Running Tests](#running-tests)
- [Threat Scoring](#threat-scoring)
- [FSM State Machine](#fsm-state-machine)
- [Troubleshooting](#troubleshooting)

---

## System Overview

Farm Sentry is an **early-warning tactical surveillance system**, not a standard CCTV setup. The design philosophy prioritises:

- **Ultra-low-latency threat detection** — YOLOv8 on TensorRT runs at ≥20 Hz on the Jetson
- **Lightweight telemetry** — Only MQTT JSON coordinates and threat scores are sent over the network; full video is on-demand only
- **Offline resilience** — The Jetson operates autonomously with no cloud dependency; the mobile app works on edge/3G connections
- **Manual override** — The operator can take direct joystick control of the turret via the mobile app at any time

```
                  ┌─────────────────────────────────────┐
                  │         NVIDIA Jetson Orin/NX       │
                  │                                     │
  USB-CDC         │  Camera → YOLO → Tracker → Scorer   │   MQTT (TLS)
 ┌──────────┐     │  → SentryBrain FSM → ArduinoLink    │◄──────────────► MQTT Broker
 │ Arduino  │◄────┤  → TelemetryRecorder → MQTT Pub     │
 │  (Turret)│     │  → Flask MJPEG stream (port 5000)   │   HTTP MJPEG
 └──────────┘     └─────────────────────────────────────┘◄──────────────► Mobile App
  Pan / Tilt                                                                (Flutter)
  Stepper Motors
  Limit Switches (required for MVP, optional for test bench)
  Laser Rangefinder
```

---

## Architecture

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| Vision | YOLOv8n (TensorRT) + CentroidTracker | Detect and track person-class targets at 25 fps |
| Control | SentryBrain FSM + dual PID | Map threat tier to turret velocity; pan/tilt closed-loop tracking |
| Hardware I/O | ArduinoLink (serial) | Send velocity commands; receive position heartbeats, LRF readings, and `LIMIT` events |
| Telemetry | TelemetryRecorder + MQTTPublisher | Serialise TelemetryRecord to JSON-lines log and MQTT |
| Safety | TurretManager + MQTTPublisher | Enforce housing-profile safety rules and publish authoritative runtime safety status |
| Comms | CommandSubscriber (MQTT) | Receive joystick ManualCommand from mobile app; drive TurretManager |
| Web HUD | Flask + OpenCV MJPEG | Serve annotated video stream at `http://<jetson>:5000/video` |
| Mobile | Flutter + Riverpod + flutter_map | Tactical map, alerts, on-demand video, manual joystick override |

---

## Repository Structure

```
sentry/
├── jetson/                  # Python backend (runs on NVIDIA Jetson)
│   ├── src/
│   │   ├── main.py          # Main control loop entry point
│   │   ├── config.py        # All constants — env vars override at runtime
│   │   ├── sentry_types.py  # Shared dataclasses and enums
│   │   ├── comms/
│   │   │   ├── mqtt.py      # MQTTPublisher + CommandSubscriber
│   │   │   └── serial_io.py # Low-level serial helpers
│   │   ├── control/
│   │   │   ├── sentry_brain.py   # FSM state machine (SCAN/TRACK/ACQUIRE/SEARCH/MANUAL_OVERRIDE)
│   │   │   ├── threat_tracker.py # ThreatScorer — computes threat score and tier
│   │   │   ├── pid.py            # Generic PID controller
│   │   │   ├── geo.py            # Haversine GPS calculation
│   │   │   └── turret_manager.py # Velocity dispatch to ArduinoLink
│   │   ├── hardware/
│   │   │   └── arduino_link.py   # Serial command bridge (V/L commands, POS/DIST replies)
│   │   ├── telemetry/
│   │   │   └── recorder.py       # Builds and emits TelemetryRecord
│   │   ├── vision/
│   │   │   ├── camera.py     # ThreadedCamera (GStreamer / V4L2)
│   │   │   ├── detector.py   # ObjectDetector (YOLOv8n TensorRT)
│   │   │   └── tracker.py    # CentroidTracker
│   │   ├── web/
│   │   │   └── streamer.py   # Flask MJPEG stream + HTTP Basic Auth
│   │   └── utils/
│   │       └── config.yaml   # Human-readable parameter documentation
│   ├── tests/
│   │   └── unit/             # pytest unit test suite
│   ├── docker/
│   │   ├── Dockerfile        # JetPack 6 base image
│   │   └── docker-compose.yaml
│   └── requirements.txt
│
├── arduino/
│   └── sentry_turret/       # Arduino Uno R3 firmware (PlatformIO)
│       ├── sentry_turret.ino # Main sketch — setup() + loop()
│       ├── config.h          # All pin assignments and timing constants
│       ├── serial_proto.h/cpp # Jetson ↔ Arduino ASCII protocol parser
│       ├── stepper.h/cpp     # Velocity-mode step pulse generation
│       ├── limit_switch.h/cpp # Debounced limit switch with gate enforcement
│       ├── lrf.h/cpp         # Laser rangefinder SoftwareSerial driver
│       ├── platformio.ini    # Build targets: [env:uno] and [env:native]
│       └── test/             # Unity unit tests (runs natively, no hardware)
│
├── app/                     # Flutter mobile app (iOS + Android)
│   ├── lib/
│   │   ├── main.dart
│   │   ├── core/
│   │   │   ├── constants.dart  # App-wide constants (ports, timeouts, thresholds)
│   │   │   ├── theme.dart      # Dark tactical colour palette
│   │   │   └── router.dart     # go_router screen definitions
│   │   ├── features/
│   │   │   ├── map/            # Tactical map HUD (home screen)
│   │   │   ├── alerts/         # Sliding alert panel + log
│   │   │   ├── calibration/    # Sentry GPS and True North offset setup
│   │   │   ├── override/       # Joystick manual control screen
│   │   │   ├── settings/       # Notification thresholds and retention config
│   │   │   ├── setup/          # Initial pairing (broker, sentry ID, credentials)
│   │   │   └── video/          # On-demand MJPEG viewer modal
│   │   ├── models/             # Dart data models (TelemetryRecord, ManualCommand, …)
│   │   ├── services/           # MQTT, Location, Notification, SecureStorage
│   │   ├── database/           # Drift (SQLite) alert log persistence
│   │   └── utils/
│   │       └── geo_utils.dart  # Haversine distance + True North correction
│   ├── test/
│   │   ├── unit/               # Dart unit tests
│   │   └── integration/        # Widget integration tests
│   └── pubspec.yaml
│
└── specs/                   # Feature specifications and design artefacts
```

---

## Components

### 1. Jetson Core (Python Backend)

The brain of the sentry. Runs as a Docker container on an NVIDIA Jetson Orin/NX.

**Control Loop** (`main.py`) — executes at ≥20 Hz:

```
A. Capture frame (ThreadedCamera)
B. Detect targets (YOLOv8n TensorRT → ObjectDetector)
C. Track targets  (CentroidTracker — centroid matching + velocity)
D. Score threats  (ThreatScorer — weighted score → tier: LOW/MED/HIGH)
E. Get turret position from Arduino
F. Compute PID velocities (pan/tilt PIDs targeting frame centre)
G. FSM update (SentryBrain → SCAN/TRACK/ACQUIRE/SEARCH/MANUAL_OVERRIDE)
H. Send velocity command to Arduino via serial
I. Record and emit TelemetryRecord to MQTT + JSON-lines log
J. Update Flask MJPEG overlay frame
```

**FSM States** — see [FSM State Machine](#fsm-state-machine) section.

**Key subsystems:**

| Module | Class | Role |
|--------|-------|------|
| `vision/camera.py` | `ThreadedCamera` | GStreamer pipeline → BGR frames in a daemon thread |
| `vision/detector.py` | `ObjectDetector` | YOLOv8n TensorRT inference; returns `Detection` list |
| `vision/tracker.py` | `CentroidTracker` | Persistent IDs; emits `TrackedTarget` with pixel velocity |
| `control/threat_tracker.py` | `ThreatScorer` | Weighted score (distance 40%, motion 30%, grouping 20%, time-of-day 10%) |
| `control/sentry_brain.py` | `SentryBrain` | FSM + dwell timers + override API |
| `control/turret_manager.py` | `TurretManager` | Applies test-bench software bounds or MVP hardware-validation gating |
| `hardware/arduino_link.py` | `ArduinoLink` | Serial bridge; sends `V <pan> <tilt>\n`, `L\n`, and tracks validated `LIMIT` events |
| `comms/mqtt.py` | `MQTTPublisher` | Async TLS MQTT publish queue (daemon thread) |
| `comms/mqtt.py` | `CommandSubscriber` | Subscribes to `sentry/command`; validates, rate-limits, dispatches |
| `telemetry/recorder.py` | `TelemetryRecorder` | Builds `TelemetryRecord`; converts pixel velocity → m/s; emits to MQTT + log |
| `web/streamer.py` | Flask app | MJPEG stream at `:5000/video` with HTTP Basic Auth |

---

### 2. Arduino Firmware

Runs on an **Arduino Uno R3 + CNC Shield V3** with A4988/DRV8825 stepper drivers.

**Responsibilities:**

- Receive velocity commands (`V <pan> <tilt>\n`) from Jetson and drive stepper axes
- Fire the laser rangefinder on demand (`L\n`), assert its active-LOW enable only for the active measurement window, and report distance (`DIST <m>\n`)
- Broadcast turret position every 100 ms (`POS <pan_steps> <tilt_steps>\n`)
- Enforce hardware limit switches — zero velocity immediately when triggered
- Hardware Watchdog Timer (2-second timeout) to recover from any firmware hang

**Hardware Connections (CNC Shield V3 on Uno R3):**

| Signal | Pin | Notes |
|--------|-----|-------|
| Pan STEP | D2 | X-axis stepper driver |
| Pan DIR | D5 | HIGH = right, LOW = left |
| Tilt STEP | D3 | Y-axis stepper driver |
| Tilt DIR | D6 | HIGH = up, LOW = down |
| Stepper ENABLE | D8 | Active-LOW; held LOW permanently (continuous hold torque) |
| Limit Pan Left | D9 | X_Limit header — normally-open, INPUT_PULLUP |
| Limit Pan Right | D10 | Y_Limit header |
| Limit Tilt Down | D11 | Z_Limit header |
| Limit Tilt Up | D12 | Off-shield header |
| LRF RX | A0 (D14) | SoftwareSerial RX — laser rangefinder |
| LRF TX | A1 (D15) | SoftwareSerial TX — laser rangefinder |
| LRF ENABLE | A2 (D16) | Active-LOW enable — LOW powers the LRF only during active ranging |

**Firmware modules:**

| File | Responsibility |
|------|---------------|
| `config.h` | All pin numbers, baud rates, timing constants — **only file to edit for new hardware** |
| `serial_proto.h/cpp` | Line accumulator + ASCII command parser |
| `stepper.h/cpp` | Velocity-to-step-interval conversion; step pulse generation in `loop()` |
| `limit_switch.h/cpp` | 5 ms debounce; gates stepper velocity to zero when triggered |
| `lrf.h/cpp` | 8-byte binary LRF frame parser; SoftwareSerial trigger/read |

---

### 3. Mobile App (Flutter)

A **dark, tactical-first** mobile app for iOS and Android. Data is map-centric; video is secondary.

**Screens:**

| Route | Screen | Purpose |
|-------|--------|---------|
| `/` (home) | **Map HUD** | Full-screen tactical map; live threat markers; alert panel; FSM status badge; connection status bar; safety banner when bypass or MVP block is active |
| `/setup` | **Setup** | Pair with sentry: MQTT broker host, port, credentials, Sentry ID, video stream URL |
| `/calibration` | **Calibration** | Pin sentry GPS position; set True North offset for accurate coordinate mapping |
| `/override` | **Manual Override** | Virtual joystick → publishes `ManualCommand` to `sentry/command` at 10 Hz; shows reduced-safety or blocked-motion messaging |
| `/settings` | **Settings** | Notification thresholds; alert log retention period; current housing / protection summary |

**Map features:**

- Live threat markers (red dots) — sized by threat score, animated by velocity vector (`vx`, `vy` in m/s)
- Markers fade when target is lost (`disappeared_frames` > 0); removed after 30 seconds
- User's live GPS position displayed alongside sentry position
- Haversine distance from the user to each active target shown inline
- Alert panel slides in from the side — hideable for full-screen map view
- Offline tile caching via `flutter_map_tile_caching`

**Key packages:**

| Package | Role |
|---------|------|
| `flutter_riverpod` | State management |
| `mqtt_client` | MQTT over TLS |
| `flutter_map` | OpenStreetMap tile rendering |
| `flutter_map_tile_caching` | Offline tile cache for dead zones |
| `geolocator` | Live GPS position |
| `flutter_local_notifications` | Background push alerts |
| `flutter_background_service` | Background MQTT connection |
| `drift` | SQLite alert log persistence |
| `flutter_secure_storage` | Encrypted credential storage |

---

## MQTT Protocol Reference

All topics use **TLS on port 8883** (default). Credentials set via env vars / app settings.

### `sentry/telemetry` — Outbound (Jetson → App)

Published by `TelemetryRecorder` for every tracked target on every control loop tick.

```json
{
  "session_id":     "uuid4-string",
  "target_id":      1,
  "threat_score":   87.3,
  "tier":           "HIGH",
  "lat":            -26.012345,
  "lon":            28.012345,
  "lrf_distance_m": 47.2,
  "pan_angle":      12.5,
  "tilt_angle":     -3.0,
  "timestamp_utc":  "2026-02-27T10:00:00.000Z",
  "velocity_vector": { "vx": 0.42, "vy": 0.11 },
  "fsm_state":      "ACQUIRE"
}
```

> `lat`/`lon`/`lrf_distance_m`/`velocity_vector` are `null` when LRF is disabled or reading is invalid.

### `sentry/command` — Inbound (App → Jetson)

Published by the mobile app Override screen at up to 10 Hz. Rate-limited to 20 Hz max on the Jetson `CommandSubscriber`.

```json
{
  "sentry_id":     "my-sentry-001",
  "pan_velocity":  150.0,
  "tilt_velocity": -80.0,
  "timestamp_utc": "2026-02-27T10:00:00.000Z"
}
```

> Velocities are in **steps/sec** (Jetson steps per second — same unit as the PID output). Max magnitude is `±200.0` (configurable via `kMaxJoystickVelocity` in the app). The `CommandSubscriber` validates `sentry_id`, rate-limits, and automatically stops the turret after 3 seconds of silence (`COMMAND_SAFETY_TIMEOUT_S`).

### `sentry/status` — Outbound (Jetson → App)

Published at startup and whenever the motion-safety state changes.

```json
{
  "sentry_id": "my-sentry-001",
  "housing_profile": "TEST_BENCH",
  "protection_mode": "SOFT_LIMIT_BYPASS",
  "motion_allowed": true,
  "motion_block_reason": null,
  "validated_switches": [],
  "timestamp_utc": "2026-03-23T17:00:00Z"
}
```

Common values:

- `housing_profile`: `TEST_BENCH` or `MVP`
- `protection_mode`: `SOFT_LIMIT_BYPASS`, `HARDWARE_VALIDATION_PENDING`, or `HARDWARE_LIMITS_ACTIVE`
- `motion_block_reason`: `INVALID_TEST_BENCH_BOUNDS` or `LIMIT_SWITCH_VALIDATION_REQUIRED`
- `validated_switches`: distinct switch hits seen this boot, e.g. `PAN_LEFT`, `PAN_RIGHT`

The mobile app treats `sentry/status` as the authority for the map safety banner, override-screen blocking state, and settings summary.

---

## Serial Protocol Reference

Communication between the **Jetson** and **Arduino** over USB-CDC at 115200 baud.

### Jetson → Arduino (commands)

| Command | Format | Description |
|---------|--------|-------------|
| Velocity | `V <pan_speed> <tilt_speed>\n` | Set pan and tilt step velocities (steps/sec). Send `V 0.0 0.0\n` to stop. |
| Laser | `L\n` | Trigger a single LRF ranging shot. Reply arrives asynchronously. |

### Arduino → Jetson (replies)

| Message | Format | Description |
|---------|--------|-------------|
| Position heartbeat | `POS <pan_steps> <tilt_steps>\n` | Broadcast every 100 ms. Cumulative signed step counts. |
| LRF distance | `DIST <metres>\n` | LRF reply. ≥ 0.0 = valid; -1.0 = framing error or timeout. |
| Limit hit | `LIMIT PAN LEFT\n` | Edge-triggered (once per press) when limit switch fires. Also: `PAN RIGHT`, `TILT DOWN`, `TILT UP`. |

---

## Prerequisites

### Hardware

- NVIDIA Jetson Orin NX / Nano / AGX (JetPack 6, Ubuntu 22.04)
- USB thermal/optical camera (V4L2-compatible, e.g. `/dev/video0`)
- Arduino Uno R3 + CNC Shield V3 + 2× A4988 or DRV8825 stepper drivers
- 2× NEMA stepper motors (pan and tilt axes)
- 4× normally-open limit switches (pan-left, pan-right, tilt-up, tilt-down) for MVP housing
- Laser rangefinder module with binary serial protocol (8-byte frame, 0x55 0xAA sync)
- MQTT broker accessible by both the Jetson and the mobile device (e.g. Mosquitto on your local network)

### Software

| Component | Requirement |
|-----------|------------|
| Jetson OS | JetPack 6 (Ubuntu 22.04) |
| Python | 3.11+ (included in JetPack 6 base image) |
| Docker | Docker Engine + NVIDIA Container Toolkit (`nvidia-docker2`) |
| Arduino IDE / PlatformIO | PlatformIO Core CLI or VS Code PlatformIO extension |
| Flutter | Flutter 3.22+ / Dart SDK ^3.10 |
| MQTT Broker | Mosquitto 2.x (or any MQTT v3.1.1-compatible broker with TLS) |

---

## Getting Started

### Step 1 — Flash the Arduino

```bash
cd arduino/sentry_turret

# Option A: PlatformIO CLI
pio run --environment uno --target upload

# Option B: Arduino IDE
# Open arduino/sentry_turret/sentry_turret.ino
# Select Board: Arduino Uno, Port: /dev/ttyUSB0 (or COMx on Windows)
# Click Upload
```

**Verify:** Open the Serial Monitor at 115200 baud. You should see `POS 0 0` messages every 100 ms.

**Run firmware unit tests without hardware:**

```bash
pio test --environment native
```

---

### Step 2 — Deploy the Jetson Core

Before launching, choose the housing profile for the unit you are commissioning:

| Profile | When to use it | Required config | Runtime behavior |
|---------|----------------|-----------------|------------------|
| `TEST_BENCH` | Initial bench housing with no physical limit switches installed yet | `HOUSING_PROFILE=TEST_BENCH` plus all four `TEST_BENCH_*_STEPS` bounds | Motion is allowed only inside the configured software envelope. `sentry/status` reports `SOFT_LIMIT_BYPASS`. |
| `MVP` | Production-style housing with real physical limit switches | `HOUSING_PROFILE=MVP` | Motion stays blocked until Jetson sees all four `LIMIT` events: `PAN LEFT`, `PAN RIGHT`, `TILT DOWN`, `TILT UP`. |

#### Option A — Docker (recommended)

```bash
cd jetson

# Set required environment variables
export SENTRY_ID=my-sentry-001
export MQTT_BROKER=192.168.1.100   # IP of your MQTT broker
export MQTT_PORT=8883
export MQTT_USERNAME=sentry
export MQTT_PASSWORD=changeme
export HOUSING_PROFILE=TEST_BENCH
export TEST_BENCH_PAN_MIN_STEPS=-4000
export TEST_BENCH_PAN_MAX_STEPS=4000
export TEST_BENCH_TILT_MIN_STEPS=-900
export TEST_BENCH_TILT_MAX_STEPS=900

# Build and start
docker compose -f docker/docker-compose.yaml up --build -d

# Follow logs
docker logs -f sentry_brain
```

> **Note:** Edit `docker/docker-compose.yaml` to set your environment variables. Docker Compose now provides fallbacks for `SENTRY_ID`, `MQTT_STATUS_TOPIC`, and `HOUSING_PROFILE`, and it passes through the optional `TEST_BENCH_*_STEPS` bounds. You should still override `SENTRY_ID` so it matches your real unit/app configuration. The `privileged: true` flag is required for USB camera and serial access.

#### Option B — Direct Python

```bash
cd jetson/src

pip3 install -r ../requirements.txt

SENTRY_ID=my-sentry-001 \
MQTT_BROKER=192.168.1.100 \
MQTT_USERNAME=sentry \
MQTT_PASSWORD=changeme \
HOUSING_PROFILE=TEST_BENCH \
TEST_BENCH_PAN_MIN_STEPS=-4000 \
TEST_BENCH_PAN_MAX_STEPS=4000 \
TEST_BENCH_TILT_MIN_STEPS=-900 \
TEST_BENCH_TILT_MAX_STEPS=900 \
python3 main.py
```

**Verify:** The Jetson logs should show `[SYSTEM] Sentry Core Online.` and you should see `[MQTT] Connected to broker` messages. The web HUD will be available at `http://<jetson-ip>:5000/video` (login: `sentry` / `changeme`).

#### Using the new housing profiles

For the current test bench with no switches installed:

1. Set `HOUSING_PROFILE=TEST_BENCH`.
2. Set all four software bounds: `TEST_BENCH_PAN_MIN_STEPS`, `TEST_BENCH_PAN_MAX_STEPS`, `TEST_BENCH_TILT_MIN_STEPS`, and `TEST_BENCH_TILT_MAX_STEPS`.
3. Start the Jetson runtime.
4. Confirm `sentry/status` reports `SOFT_LIMIT_BYPASS` and `motion_allowed=true`.

For the later MVP housing with physical switches:

1. Set `HOUSING_PROFILE=MVP`.
2. Start the Jetson runtime.
3. Manually actuate each switch once so Jetson observes `PAN LEFT`, `PAN RIGHT`, `TILT DOWN`, and `TILT UP`.
4. Confirm `sentry/status` transitions from `HARDWARE_VALIDATION_PENDING` to `HARDWARE_LIMITS_ACTIVE`.

> In `TEST_BENCH`, missing or inverted software bounds block motion and publish `motion_block_reason=INVALID_TEST_BENCH_BOUNDS`. In `MVP`, motion remains blocked until all four switches are validated.

---

### Step 3 — Set Up the MQTT Broker

If you don't have an MQTT broker, install Mosquitto on any machine on your local network:

```bash
# Ubuntu / Debian
sudo apt install mosquitto mosquitto-clients

# Example minimal TLS config (/etc/mosquitto/conf.d/sentry.conf)
listener 8883
cafile   /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile  /etc/mosquitto/certs/server.key
require_certificate false

allow_anonymous false
password_file /etc/mosquitto/passwd
```

```bash
# Create a user
sudo mosquitto_passwd -c /etc/mosquitto/passwd sentry
# Enter password when prompted

sudo systemctl restart mosquitto
```

**Test it:**

```bash
# Subscribe in one terminal
mosquitto_sub -h localhost -p 8883 --cafile ca.crt -u sentry -P changeme -t "sentry/telemetry"

# In another terminal, watch safety status
mosquitto_sub -h localhost -p 8883 --cafile ca.crt -u sentry -P changeme -t "sentry/status"

# The Jetson will start publishing once it detects targets
```

---

### Step 4 — Build and Run the Mobile App

```bash
cd app

# Install dependencies
flutter pub get

# Run on a connected device or emulator
flutter run

# Build release APK (Android)
flutter build apk --release

# Build release IPA (iOS — requires Xcode on macOS)
flutter build ios --release
```

**First launch:** The app will open the **Setup screen** automatically if no configuration is saved.

---

### Step 5 — First-Run Calibration

#### App Setup (pairing)

On the **Setup** screen, enter:

| Field | Value |
|-------|-------|
| Broker Host | IP address of your MQTT broker (e.g. `192.168.1.100`) |
| Broker Port | `8883` (TLS) |
| MQTT Username | Your broker username |
| MQTT Password | Your broker password |
| Sentry ID | Must match the `SENTRY_ID` env var on the Jetson |
| Video Host | IP address of the Jetson |
| Video Port | `5000` |

#### Sentry Calibration

On the **Calibration** screen:

1. **Pin Sentry Location** — Tap "Use My Location" if you're standing at the sentry, or enter the GPS coordinates manually.
2. **True North Offset** — With the sentry powered and the turret at pan=0, use a compass to measure the angle between the camera's forward direction and true north. Enter this value in degrees. This ensures target GPS coordinates on the map align correctly with reality.

> After saving calibration, update `SENTRY_LAT`, `SENTRY_LON`, and `SENTRY_HEADING_DEG` in the Jetson config or Docker environment variables and restart the container.

---

## Configuration Reference

### Jetson Environment Variables

All values in `config.py` can be overridden with environment variables. The following are the most important for field deployment:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SENTRY_ID` | — | **Yes** | Unique sentry identifier. Must match the mobile app setting. |
| `MQTT_BROKER` | `localhost` | **Yes** | MQTT broker hostname or IP |
| `MQTT_PORT` | `8883` | No | MQTT broker port (8883 = TLS, 1883 = plain) |
| `MQTT_USERNAME` | `""` | **Yes** | MQTT broker username |
| `MQTT_PASSWORD` | `""` | **Yes** | MQTT broker password |
| `MQTT_TOPIC` | `sentry/telemetry` | No | Outbound telemetry topic |
| `MQTT_STATUS_TOPIC` | `sentry/status` | No | Outbound safety-status topic used by the app warnings and motion-gating UI |
| `MQTT_COMMAND_TOPIC` | `sentry/command` | No | Inbound manual command topic |
| `HOUSING_PROFILE` | `MVP` | No | `TEST_BENCH` enables software-bound bypass; `MVP` requires physical limit-switch validation |
| `TEST_BENCH_PAN_MIN_STEPS` | `None` | For `TEST_BENCH` | Inclusive minimum pan step bound for the temporary bypass |
| `TEST_BENCH_PAN_MAX_STEPS` | `None` | For `TEST_BENCH` | Inclusive maximum pan step bound for the temporary bypass |
| `TEST_BENCH_TILT_MIN_STEPS` | `None` | For `TEST_BENCH` | Inclusive minimum tilt step bound for the temporary bypass |
| `TEST_BENCH_TILT_MAX_STEPS` | `None` | For `TEST_BENCH` | Inclusive maximum tilt step bound for the temporary bypass |
| `SERIAL_PORT` | `/dev/ttyUSB0` | No | Arduino USB serial device path |
| `MODEL_PATH` | `yolov8n.engine` | No | Path to TensorRT .engine model file |
| `TELEMETRY_LOG_PATH` | `/app/logs/telemetry.jsonl` | No | Rotating JSON-lines telemetry log |
| `CAMERA_FPS` | `25` | No | Camera frame rate (used for velocity conversion) |
| `CAMERA_HFOV_DEG` | `120.0` | No | Camera horizontal field-of-view in degrees — **calibrate per lens** |
| `COMMAND_SAFETY_TIMEOUT_S` | `3.0` | No | Turret auto-stop if no joystick command arrives within this window |
| `COMMAND_RATE_LIMIT_HZ` | `20` | No | Max rate to forward joystick commands to TurretManager |
| `HUD_USERNAME` | `sentry` | No | HTTP Basic Auth username for the web HUD |
| `HUD_PASSWORD` | `changeme` | No | HTTP Basic Auth password for the web HUD — **change before deployment** |

> See `jetson/src/utils/config.yaml` for the full reference including all PID gains, threat thresholds, turret limits, and scan sweep parameters.

#### Safety-profile usage notes

- Use `TEST_BENCH` only for the temporary bench housing that does not yet include physical limit switches.
- In `TEST_BENCH`, all four software bounds must be set and must satisfy `min < max` on both axes.
- In `MVP`, the Arduino wire protocol does not change; Jetson simply consumes the existing `LIMIT` events as commissioning evidence.
- The mobile app does not infer safety locally. It reads `sentry/status` and surfaces the result on the map, override, and settings screens.

### Arduino Hardware Pins

All pin assignments live in `arduino/sentry_turret/config.h`. To adapt to a different carrier board, edit only that file.

| Constant | Default Pin | Signal |
|----------|------------|--------|
| `PAN_STEP_PIN` | D2 | Pan stepper STEP |
| `PAN_DIR_PIN` | D5 | Pan stepper DIR |
| `TILT_STEP_PIN` | D3 | Tilt stepper STEP |
| `TILT_DIR_PIN` | D6 | Tilt stepper DIR |
| `STEPPER_ENABLE_PIN` | D8 | All driver ENABLE (active-LOW) |
| `LIMIT_PAN_LEFT_PIN` | D9 | Pan-left limit switch |
| `LIMIT_PAN_RIGHT_PIN` | D10 | Pan-right limit switch |
| `LIMIT_TILT_DOWN_PIN` | D11 | Tilt-down limit switch |
| `LIMIT_TILT_UP_PIN` | D12 | Tilt-up limit switch |
| `LRF_RX_PIN` | A0 | LRF SoftwareSerial RX |
| `LRF_TX_PIN` | A1 | LRF SoftwareSerial TX |
| `LRF_ENABLE_PIN` | A2 | LRF active-LOW enable control |
| `LRF_ENABLE_ACTIVE_LEVEL` | `0` | LOW powers the LRF on |
| `LRF_ENABLE_INACTIVE_LEVEL` | `1` | HIGH keeps the LRF idle-disabled |

### Mobile App Settings

Stored encrypted via `flutter_secure_storage`. Configured through the app UI — no config file needed.

| Setting | Default | Description |
|---------|---------|-------------|
| MQTT Broker Port | `8883` | Changing from 8883 triggers a TLS warning in the UI |
| Heartbeat Timeout | `10 s` | After 10 s without a telemetry message, shows "Sentry Offline" |
| Marker Fade Removal | `30 s` | Lost-target markers are removed from the map after 30 seconds |
| Joystick Publish Interval | `100 ms` | How often the joystick sends a `ManualCommand` (10 Hz) |
| Max Joystick Velocity | `±200 steps/sec` | Full joystick deflection maps to this speed |
| HIGH Threat Threshold | `80.0` | Score at or above this triggers a HIGH alert and wake notification |
| MED Threat Threshold | `40.0` | Score at or above this triggers a MED alert |
| Alert Retention | `7 days` | How long alert log entries are kept in the local SQLite database |

---

## Running Tests

### Jetson Python Unit Tests

```bash
cd jetson

# Install test dependencies
pip3 install pytest numpy scipy --break-system-packages

# Run all unit tests
SENTRY_ID=test python3 -m pytest tests/unit/ -v

# Run a specific module
SENTRY_ID=test python3 -m pytest tests/unit/test_fsm_brain.py -v
SENTRY_ID=test python3 -m pytest tests/unit/test_command_subscriber.py -v
SENTRY_ID=test python3 -m pytest tests/unit/test_telemetry_enrichment.py -v
SENTRY_ID=test python3 -m pytest tests/unit/test_turret_manager.py -v
SENTRY_ID=test python3 -m pytest tests/unit/test_safety_status.py -v
```

> Note: `test_camera.py` and `test_serial_io.py` require `cv2` / `pyserial` hardware libraries and will fail without them — this is expected in a CI / development environment.

### Arduino Firmware Unit Tests

```bash
cd arduino/sentry_turret

# Run native tests (no hardware required)
pio test --environment native
```

### Flutter App Tests

```bash
cd app

# Unit and widget tests
flutter test

# Specific test file
flutter test test/unit/geo_utils_test.dart
flutter test test/unit/joystick_test.dart
```

---

## Threat Scoring

The `ThreatScorer` computes a normalised score in [0.0, 100.0] from four weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Distance proxy | 40% | Bounding-box area as a proxy for proximity (larger = closer = higher score) |
| Motion | 30% | Pixel velocity magnitude of the tracked centroid |
| Grouping | 20% | Number of targets within `GROUP_RADIUS_PX` (80 px) of this target |
| Time of day | 10% | Night hours (20:00–06:00) receive a score bonus |

**Tier classification:**

| Tier | Score range | FSM recommendation | LRF |
|------|------------|-------------------|-----|
| `LOW` | 0 – 39.9 | `SCAN` | Off |
| `MED` | 40.0 – 79.9 | `TRACK` | Sampled (every 500 ms) |
| `HIGH` | 80.0 – 100.0 | `ACQUIRE` | Continuous |

---

## FSM State Machine

`SentryBrain` is the sole authority on turret behaviour. State transitions are governed by threat tier and dwell timers.

```
                    no targets                 no targets
        ┌───────────────────────────────────────────────────────────┐
        │                                                           │
        ▼           MED threat                                      │
  ┌──────────┐ ─────────────────► ┌──────────┐  target lost         │
  │  SCAN    │                    │  TRACK   │ ─────────────►  ┌──────────┐
  │ (sweep)  │ ◄───────────────── │  (PID)   │                 │  SEARCH  │
  └──────────┘    LOW threat      └──────────┘ ◄─────────────  │ (arc sw) │
        ▲         (dwell gate)         │         not found     └──────────┘
        │                             │ HIGH threat                  │
        │                             ▼                    timeout (10s)
        │                       ┌──────────┐                         │
        └───────────────────────│  ACQUIRE │ ◄───────────────────────┘
             threat gone        │ (hard lk)│
             (dwell gate)       └──────────┘
                                     │
                            MANUAL_OVERRIDE
                            (enter_override())
                                     │
                                     ▼
                             ┌──────────────┐
                             │   MANUAL     │  joystick active
                             │  OVERRIDE    │  (CommandSubscriber)
                             └──────────────┘
                                     │ safety timeout (3s)
                                     │ or exit_override()
                                     ▼
                               (back to SCAN)
```

**Rules:**
- Upward transitions (e.g. SCAN → ACQUIRE) are **always immediate**
- Downward transitions (e.g. ACQUIRE → TRACK) require the dwell timer to elapse first
- `SEARCH` fires immediately when a target disappears from `TRACK` or `ACQUIRE`
- `MANUAL_OVERRIDE` is never stored in `_state` — only returned by the `state` property; internal FSM is paused

---

## Troubleshooting

### Sentry Core won't start — `KeyError: 'SENTRY_ID'`

The `SENTRY_ID` environment variable is required with no default. Set it before starting:

```bash
export SENTRY_ID=my-sentry-001
```

### `[MQTT] Connection error` in Jetson logs

1. Verify the broker is reachable: `ping <MQTT_BROKER>`
2. Verify TLS port is open: `nc -zv <MQTT_BROKER> 8883`
3. Check credentials match in both the Jetson env vars and the broker password file
4. For testing on a plain TCP broker (no TLS), set `MQTT_PORT=1883` and update `_connect()` in `mqtt.py` to skip `tls_set()`

### `[GEO] WARNING: SENTRY_LAT and SENTRY_LON are both 0.0`

GPS target coordinates will be wrong. Run the Calibration screen in the app and set the sentry's position, then update `SENTRY_LAT` and `SENTRY_LON` in the Jetson environment.

### Arduino not responding — `[SERIAL] Heartbeat timeout`

1. Check the USB cable and port: `ls /dev/ttyUSB*`
2. Verify baud rate is 115200 in both `config.h` (`JETSON_BAUD`) and the Jetson's `BAUD_RATE`
3. Open the Arduino Serial Monitor; you should see `POS 0 0` every 100 ms
4. Check the Watchdog Timer hasn't locked the Arduino — power cycle and re-flash if needed

### LRF always returns -1.0

1. Check SoftwareSerial wiring: LRF TX → Arduino A0, LRF RX → Arduino A1
2. Check the active-LOW enable wiring: Arduino A2 must drive the LRF enable input LOW only during ranging
3. Verify LRF baud rate matches `LRF_SOFTSERIAL_BAUD` (default 115200)
4. If framing errors persist, reduce to 57600 in `config.h` — no logic changes needed (see `CONSTRAINT-001` in `sentry_turret.ino`)

### Map shows threats at wrong location

Run the Calibration screen and re-measure the True North offset. The offset corrects for the angle between the camera's forward axis (pan=0) and magnetic/true north.

### App shows "Sentry Offline"

The app declares the sentry offline if no `sentry/telemetry` message arrives within 10 seconds (`kHeartbeatTimeoutSec`). Check:
1. Jetson is running and seeing targets (or connected to broker — telemetry only publishes when targets are active)
2. The `SENTRY_ID` in the app matches the Jetson's `SENTRY_ID` env var
3. MQTT broker is reachable from the phone's network

### Joystick commands have no effect on the turret

The `CommandSubscriber` must be started in `main.py`. Verify the Jetson logs show `[CMD] CommandSubscriber started; topic=sentry/command`. Also confirm the `sentry_id` field in the command matches the Jetson's `SENTRY_ID` exactly.

---

## License

Private — all rights reserved.
