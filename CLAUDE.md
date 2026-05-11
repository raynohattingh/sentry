# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Farm Sentry is an autonomous farm-security system: a pan/tilt turret running YOLOv8n inference on an NVIDIA Jetson, controlled over MQTT from a Flutter mobile app, with an Arduino handling the physical stepper motors and laser rangefinder. It is designed for offline LAN operation with no cloud dependency.

Three runtimes, three communication links:

- **Jetson** (`jetson/`) -- Python, the integration hub
- **Arduino** (`arduino/sentry_turret/`) -- C++/PlatformIO, the motor/LRF controller
- **Mobile App** (`app/`) -- Flutter/Dart, the operator interface

## Commands

### Jetson (Python)

```bash
# Install deps
cd jetson && pip3 install -r requirements.txt
cd jetson && pip3 install -r requirements-dev.txt  # adds pytest, etc.

# Run (minimum env vars required)
cd jetson/src
SENTRY_ID=my-sentry-001 MQTT_BROKER=192.168.1.100 MQTT_USERNAME=sentry MQTT_PASSWORD=changeme python3 main.py

# Docker (recommended for Jetson hardware)
cd jetson && docker compose -f docker/docker-compose.yaml --env-file docker/.env up --build -d

# Tests
cd jetson && SENTRY_ID=test python3 -m pytest tests/unit/ -v
cd jetson && SENTRY_ID=test python3 -m pytest tests/integration/ -v
cd jetson && SENTRY_ID=test python3 -m pytest tests/unit/test_fsm_brain.py -v   # single module
```

`test_camera.py` and `test_serial_io.py` require `cv2`/`pyserial` and attached hardware -- they will fail in most dev environments.

### Arduino (PlatformIO)

```bash
cd arduino/sentry_turret
pio run --environment uno              # build for hardware
pio run --environment uno --target upload  # flash
pio test --environment native          # unit tests, no hardware needed
pio test --environment native --filter test_serial_proto  # single suite
```

### Flutter App

```bash
cd app
flutter pub get
flutter run
flutter analyze
flutter test
flutter test test/unit/telemetry_parsing_test.dart  # single file

# After changing Drift tables or DAOs, regenerate committed .g.dart files:
dart run build_runner build --delete-conflicting-outputs

# Release builds
flutter build apk --release
flutter build ios --release
```

## Architecture

### Jetson pipeline (`jetson/src/main.py`)

The main loop runs at 20+ Hz and chains:

```
ThreadedCamera -> ObjectDetector (YOLOv8n/TensorRT) -> CentroidTracker (Hungarian algorithm)
  -> ThreatScorer -> SentryBrain FSM -> ArduinoLink (serial)
  -> TelemetryRecorder -> MQTTPublisher
```

The Flask MJPEG HUD (`web/streamer.py`, port 5000) runs in a daemon thread alongside the control loop.

### SentryBrain FSM states

| State | Trigger | Behavior |
|-------|---------|----------|
| SCAN | No targets / LOW tier | Pan sweep |
| TRACK | MED tier target | PID tracking with sampled LRF |
| ACQUIRE | HIGH tier target | Hard lock with continuous LRF |
| SEARCH | Target lost from TRACK/ACQUIRE | Arc sweep around last-known position (10s timeout) |
| MANUAL_OVERRIDE | Joystick command | Direct operator control (3s safety timeout) |

Upward transitions (SCAN -> ACQUIRE) are immediate; downward transitions use dwell timers to prevent oscillation.

### Threat scoring weights

Distance 40% · Motion 30% · Grouping 20% · Time-of-day 10%  
Tiers: LOW (0-39) / MED (40-79) / HIGH (80-100)

### Flutter app

State is managed with **Riverpod providers** and **go_router**. `app/lib/core/router.dart` enforces setup flow: unconfigured users are redirected to `/setup`.

A background isolate (`app/lib/main.dart`) keeps MQTT connected and raises local notifications when the UI is backgrounded.

The app is **map-first**. `ThreatMarkersNotifier` turns telemetry into fading map markers using the saved true-north calibration. The MJPEG video stream is on-demand secondary context, not the primary data feed.

## Key Conventions

**`SENTRY_ID` is the cross-project identity key.** Jetson startup requires it; `CommandSubscriber` silently rejects commands whose `sentry_id` doesn't match; the app stores the same value in its saved config. Always set it in tests: `SENTRY_ID=test`.

**`jetson/src` is the runtime root, not an installed package.** Tests prepend `../../src` to `sys.path` and monkeypatch `config`, then reload modules that cache config-dependent constants at import time.

**`jetson/src/config.py` is the executable truth; `jetson/src/utils/config.yaml` is documentation only** -- it is not a second config loader.

**Two housing profiles control motion safety:**
- `TEST_BENCH` -- software-defined step limits, no physical switches required
- `MVP` -- motion is blocked until all four limit switches have been seen at least once

**Arduino firmware is host-testable.** Hardware paths are guarded with `NATIVE_ENV` so `pio test --environment native` compiles and runs without an Uno attached. Hardware pins and serial constants belong in `arduino/sentry_turret/src/config.h`.

**Drift generated files** (`app/lib/database/*.g.dart`) are committed. Do not hand-edit them; regenerate with `build_runner`.

**Cross-project timestamps** are UTC ISO 8601 strings in a field named `timestamp_utc`. MQTT and serial payload keys are `snake_case` across Python and Dart. FSM states and threat tiers stay uppercase (`SCAN`, `HIGH`, etc.).

**GPS and `velocity_vector` are conditionally null.** These fields are only populated when the Jetson has a valid LRF reading; otherwise `lat`, `lon`, `lrf_distance_m`, and `velocity_vector` are explicitly `null` in telemetry.

**Telemetry is dual-output by design.** `TelemetryRecorder` writes rotating JSONL logs to `jetson/src/state/` and publishes the same record to MQTT. Never write to only one of these paths.
