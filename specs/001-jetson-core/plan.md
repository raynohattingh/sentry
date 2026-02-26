# Implementation Plan: Sentry Jetson Core

**Branch**: `001-jetson-core` | **Date**: 2026-02-25 | **Spec**: [specs/001-jetson-core/spec.md](./spec.md)  
**Input**: Autonomous thermal sentry turret brain — Jetson Orin Nano Super, Python 3.10+, Docker,
YOLOv8 TensorRT, PID pan/tilt, LRF GPS telemetry, Arduino serial, Flask MJPEG stream.

## Summary

Build the complete Python brain for an autonomous thermal sentry turret. The existing codebase is a
partial prototype (~30% complete); this plan refactors and extends it to the full 34-FR spec. The
delivery is a modular monolith in `jetson/src/` organised into vision, control, hardware, comms,
web, and telemetry packages, deployed as a Docker container with auto-restart on the Jetson.

**Core loop**: Threaded GStreamer/V4L2 camera → YOLOv8n TensorRT inference → centroid tracking →
threat scoring → FSM (SCAN/TRACK/ACQUIRE/SEARCH) → PID velocity → Arduino serial → GPS telemetry
→ Flask MJPEG HUD.

**Key decisions from research** (see `research.md`):

- Centroid tracker uses `scipy.spatial.distance.cdist` — the reference algorithm from PyImageSearch,
  minimal dependencies, microsecond runtime.
- GPS computation uses pure-stdlib Haversine — ±2 m at <2 km; well inside the ±10 m spec.
  No external library needed on the offline Jetson.
- MQTT uses a daemon thread + `queue.Queue` — publish is fire-and-forget; broker unavailability
  never blocks the main loop.
- FSM dwell timers use `time.monotonic_ns()` stored at state-entry time; downward transitions
  check elapsed time, upward transitions are immediate.
- Velocity tapering is a linear scale factor: `(limit_hard − pos) / taper_width`, clamped [0, 1].

## Technical Context

**Language/Version**: Python 3.10+ (JetPack 6 container base)  
**Primary Dependencies**: OpenCV 4.x, Ultralytics YOLOv8, Flask, pyserial, paho-mqtt, scipy  
**Storage**: JSON-lines rotating log file (configurable path/size); small JSON state file for boot
failure counter; MQTT broker (external, optional)  
**Testing**: pytest; mockable Protocol interfaces for all hardware (camera, serial, MQTT);
integration tests use mock serial port and mock camera  
**Target Platform**: NVIDIA Jetson Orin Nano Super, JetPack 6 / Ubuntu 22.04, Docker
(`ultralytics/ultralytics:latest-jetson-jetpack6` base image)  
**Project Type**: Embedded AI service — hard real-time control loop with hardware I/O  
**Performance Goals**: ≥ 20 Hz main loop; < 100 ms frame-to-serial-command latency;
≥ 15 FPS web stream; serial RTT < 20 ms  
**Constraints**: Docker auto-restart; no GPU degraded mode at startup; all params in `config.py`;
no internet access on Jetson (pure stdlib preferred); hardware-in-the-loop test before merge  
**Scale/Scope**: Single deployment unit; 480×320 video; single MQTT topic; 1 concurrent HUD viewer

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Code Quality**: All new modules have a single responsibility; no magic numbers;
  public interfaces are documented.
  - Every module maps to exactly one spec subsystem (vision / control / hardware / comms / web /
    telemetry); no module crosses subsystem boundaries.
  - All numeric constants and thresholds centralised in `config.py` and `utils/config.yaml`;
    zero magic numbers permitted in logic modules.
  - All public classes and functions carry Google-style docstrings (enforced in task descriptions).

- [x] **II. Testing Standards**: Unit tests planned for all pure-logic components; hardware-dependent
  code has a mockable interface; integration tests cover subsystem-boundary flows; TDD confirmed.
  - **Unit** (7 suites): `test_pid.py`, `test_geo.py`, `test_tracker.py`, `test_threat_scoring.py`,
    `test_fsm_brain.py`, `test_serial_framing.py`, `test_telemetry_recorder.py`
  - **Mockable interfaces**: `CameraProtocol`, `SerialProtocol`, `MQTTProtocol` (typing.Protocol)
  - **Integration** (3 suites): vision→command pipeline, serial roundtrip, web stream delivery
  - TDD workflow: test file written and confirmed failing before corresponding module implementation.

- [x] **III. UX Consistency**: Operator-facing output follows `[SUBSYSTEM] <message>` convention
  and the constitution colour scheme.
  - All log messages use `[SUBSYSTEM] <message>` format (e.g., `[VISION]`, `[TURRET]`, `[SERIAL]`).
  - HUD overlay colours: red = threat/active tracking, green = status/metadata, yellow = warnings.
  - Every config parameter in `config.yaml` documented with units, valid range, and default value.

- [x] **IV. Performance Requirements**: Feature impact on all four targets assessed; benchmark
  instrumentation included.
  - **Main loop**: GStreamer `appsink drop=1` prevents frame buffering; TensorRT is GPU-accelerated.
  - **Web stream**: Runs in a daemon thread with its own JPEG frame buffer; cannot block main loop.
  - **Serial**: Non-blocking `write()`; DIST/POS responses parsed in a dedicated read thread.
  - **MQTT**: Daemon thread + `queue.Queue`; zero main loop blocking on publish.
  - **Benchmark**: Loop timing logged every 100 iterations (`[SYSTEM] Loop FPS: <n>`); FPS drop
    below 18 triggers a `[SYSTEM] WARNING — loop rate degraded` log entry.

**Constitution Check post-design**: ✅ All four gates pass. No violations. See `research.md` for
`scipy` and `telemetry/` package justifications (Complexity Tracking below).

## Project Structure

### Documentation (this feature)

```text
specs/001-jetson-core/
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   ├── serial-protocol.md    ← Phase 1 output
│   ├── mqtt-schema.md        ← Phase 1 output
│   └── config-schema.md      ← Phase 1 output
└── tasks.md             ← Phase 2 output (speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
jetson/
├── docker/
│   ├── Dockerfile          ← Update: add scipy, paho-mqtt install
│   └── docker-compose.yaml ← Update: add MQTT_BROKER, MQTT_TOPIC, HUD_USERNAME, HUD_PASSWORD env vars
├── requirements.txt        ← Add: scipy, paho-mqtt
└── src/
    ├── main.py             ← REFACTOR: session_id, boot counter, FSM wiring, loop FPS logging
    ├── config.py           ← EXPAND: ~25 new parameters (all FRs covered)
    ├── utils/
    │   └── config.yaml     ← EXPAND: all params with units, ranges, defaults
    ├── vision/
    │   ├── camera.py       ← REFACTOR: reconnection loop, type hints, [VISION] log prefix
    │   ├── detector.py     ← REFACTOR: multi-target list output, TRT error handling, type hints
    │   └── tracker.py      ← NEW: centroid tracker (deprecates control/tracker.py dev script)
    ├── control/
    │   ├── sentry_brain.py    ← NEW: FSM with dwell timers, limit taper, SEARCH arc
    │   ├── threat_tracker.py  ← NEW: threat scoring formula + adaptive LRF sampling
    │   ├── pid.py          ← REFACTOR: type hints, docstrings (algorithm unchanged)
    │   └── geo.py          ← MOVE + COMPLETE: Haversine impl from utils/geo.py
    ├── hardware/
    │   └── arduino_link.py ← MAJOR REFACTOR: reconnect loop, POS/DIST parsing,
    │                          LRF trigger, malformed frame handling, heartbeat watchdog
    ├── comms/
    │   ├── serial_io.py    ← IMPLEMENT: low-level serial port open/read/write/close
    │   └── mqtt.py         ← IMPLEMENT: non-blocking MQTT (daemon thread + Queue)
    ├── web/
    │   └── streamer.py     ← REFACTOR: HTTP Basic Auth, type hints
    └── telemetry/
        └── recorder.py     ← NEW: TelemetryRecord dataclass, JSON-lines rotating writer,
                               session_id attachment

tests/
├── conftest.py                         ← Shared fixtures: mock camera, mock serial, mock MQTT
├── unit/
│   ├── test_pid.py                     ← PID output, anti-windup, reset
│   ├── test_geo.py                     ← Haversine: known coordinates, null handling
│   ├── test_tracker.py                 ← Centroid assign, disappearance, re-id
│   ├── test_threat_scoring.py          ← Score formula, tier boundaries, multi-target priority
│   ├── test_fsm_brain.py               ← All state transitions, dwell blocking, dwell pass-through
│   ├── test_serial_framing.py          ← Valid/malformed frame parsing, discard + log
│   └── test_telemetry_recorder.py      ← session_id attach, null fields, file rotation
└── integration/
    ├── test_vision_pipeline.py         ← Mock camera → detector → tracker → turret command
    ├── test_serial_roundtrip.py        ← Jetson→Arduino mock: V command, L command, DIST parse
    └── test_web_stream.py              ← Basic Auth 401, stream delivery, main loop unaffected
```

**Structure Decision**: Modular monolith as mandated by spec. The `control/tracker.py` dev test
script is superseded by `vision/tracker.py` (the correct spec location for centroid tracking).
The empty `comms/` stubs are fully implemented. A new `telemetry/` package provides a single-
responsibility home for `TelemetryRecord` and the JSON-lines writer (would otherwise bloat
`main.py`). The `utils/geo.py` stub is moved to `control/geo.py` per spec layout.

## Complexity Tracking

No constitution violations. All dependencies are in the approved Technology Stack table. Two
additions require justification:

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|-------------------------------------|
| `scipy` (new dependency) | `scipy.spatial.distance.cdist` provides vectorised O(n²) centroid-to-detection matching — the reference implementation for this tracking algorithm | Manual nested-loop O(n²) is error-prone and performs 10–100× slower on numpy arrays; `scipy` is pre-installed on JetPack 6 base image, zero installation overhead |
| `telemetry/` package (new directory) | Single-responsibility module for `TelemetryRecord` dataclass, session_id management, JSON-lines writer, and log rotation | Inlining in `main.py` violates Constitution Principle I (single responsibility); telemetry logic covers non-trivial concerns: dataclass serialisation, nullable GPS fields, rotating file handler, session_id attachment |
