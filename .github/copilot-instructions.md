# Copilot instructions for `sentry`

## Build, test, and lint commands

### Jetson core (`jetson/`)

- Install dependencies: `cd jetson && pip3 install -r requirements.txt`
- Run directly: `cd jetson/src && SENTRY_ID=my-sentry-001 MQTT_BROKER=192.168.1.100 MQTT_USERNAME=sentry MQTT_PASSWORD=changeme python3 main.py`
- Run in Docker: `cd jetson && docker compose -f docker/docker-compose.yaml up --build -d`
- Run unit tests: `cd jetson && SENTRY_ID=test python3 -m pytest tests/unit/ -v`
- Run integration tests: `cd jetson && SENTRY_ID=test python3 -m pytest tests/integration/ -v`
- Run system tests: `cd jetson && SENTRY_ID=test python3 -m pytest tests/system/ -v`
- Run one test module: `cd jetson && SENTRY_ID=test python3 -m pytest tests/unit/test_fsm_brain.py -v`

`test_camera.py` and `test_serial_io.py` expect `cv2` / `pyserial` support and may fail on machines without those libraries or attached hardware.

### Arduino firmware (`arduino/sentry_turret/`)

- Build for hardware: `cd arduino/sentry_turret && pio run --environment uno`
- Upload to hardware: `cd arduino/sentry_turret && pio run --environment uno --target upload`
- Run host-native firmware tests: `cd arduino/sentry_turret && pio test --environment native`
- Run one native test suite: `cd arduino/sentry_turret && pio test --environment native --filter test_serial_proto`

PlatformIO defaults to the `native` environment here; host tests rely on the `NATIVE_ENV` compile guards in the firmware sources.

### Flutter app (`app/`)

- Install dependencies: `cd app && flutter pub get`
- Run the app: `cd app && flutter run`
- Build Android release: `cd app && flutter build apk --release`
- Lint/analyze: `cd app && flutter analyze`
- Run tests: `cd app && flutter test`
- Run one test file: `cd app && flutter test test/unit/telemetry_parsing_test.dart`

If you change Drift tables or DAOs, regenerate committed `*.g.dart` files with `cd app && dart run build_runner build --delete-conflicting-outputs`.

## High-level architecture

This repo is one system split across three runtimes:

- The Flutter app publishes manual override commands to MQTT on `sentry/command` and subscribes to Jetson telemetry on `sentry/telemetry`.
- The Jetson backend is the integration hub. `jetson/src/main.py` wires the runtime pipeline as `ThreadedCamera -> ObjectDetector -> CentroidTracker -> ThreatScorer -> SentryBrain -> ArduinoLink -> TelemetryRecorder/MQTTPublisher`, while also starting the Flask MJPEG HUD in a daemon thread.
- The Arduino firmware is a serial motor/LRF controller. It consumes `V <pan> <tilt>` and `L` commands from the Jetson and emits `POS`, `DIST`, and `LIMIT` messages back over USB serial.

Important runtime boundaries:

- MQTT is the app/Jetson contract. The payloads are plain JSON with snake_case keys; FSM and threat-tier values stay uppercase (`SCAN`, `TRACK`, `ACQUIRE`, `SEARCH`, `LOW`, `MED`, `HIGH`).
- The Jetson telemetry path is dual-output by design: `TelemetryRecorder` writes rotating JSONL logs and publishes the same record to MQTT.
- GPS coordinates and `velocity_vector` are only populated when the Jetson has a valid LRF reading; otherwise `lat`, `lon`, `lrf_distance_m`, and `velocity_vector` are intentionally `null`.
- The app is map-first, not video-first. `ThreatMarkersNotifier` turns telemetry into fading map markers, applies the saved north-offset calibration, and removes lost targets after the configured timeout.
- The Jetson also exposes an authenticated MJPEG stream at `http://<jetson>:5000/video`; the app treats that as on-demand secondary context, not the main data feed.

## Key conventions

- `SENTRY_ID` is the cross-project identity key. Jetson startup requires it, `CommandSubscriber` rejects commands for other sentries, and the app setup flow stores the same value in its saved config.
- In Jetson code, `jetson/src` is treated as the runtime root instead of an installed Python package. Tests mirror that by inserting `../../src` into `sys.path`, monkeypatching `config`, and reloading modules when config-dependent constants need to be reevaluated.
- `jetson/src/config.py` is the executable source of truth for runtime settings; `jetson/src/utils/config.yaml` is documentation for those settings, not a second config loader.
- Flutter state is organized around Riverpod providers plus `go_router`. Setup routing is enforced centrally in `app/lib/core/router.dart`: unconfigured users are redirected to `/setup`, configured users are redirected away from it.
- The Flutter background service is part of the expected architecture. `app/lib/main.dart` starts a background isolate that reconnects MQTT and raises local notifications even when the UI is not foregrounded.
- Drift generated files (`app/lib/database/app_database.g.dart`, `app/lib/database/alert_log_dao.g.dart`) are committed and should be regenerated, not hand-edited.
- Arduino firmware is written to stay host-testable. Hardware-specific paths are guarded with `NATIVE_ENV` so `pio test --environment native` can compile and run without an Uno attached.
- Hardware pin mappings and watchdog/serial constants are centralized in `arduino/sentry_turret/src/config.h`; board adaptations should go there rather than being spread across the firmware.
- Cross-project timestamps are consistently UTC ISO 8601 strings (`timestamp_utc`), and MQTT/serial payload fields stay snake_case across Python and Dart models.
