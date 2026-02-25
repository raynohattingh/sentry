# Tasks: Sentry Jetson Core

**Input**: Design documents from `specs/001-jetson-core/`  
**Branch**: `001-jetson-core`  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**TDD Policy**: Per Constitution §II — every test task MUST be written and confirmed failing
before the corresponding implementation task is started (Red → Green → Refactor).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Task can run in parallel with other [P] tasks in the same phase (no shared file writes)
- **[Story]**: Which user story this task delivers (US1–US5)
- All file paths are relative to the repo root

---

## Phase 1: Setup

**Purpose**: Create missing directories and update infrastructure dependencies.

- [X] T001 Create missing package directories, empty `__init__.py` files, and `.gitkeep` for runtime dirs: `jetson/src/telemetry/`, `jetson/src/state/` (add `.gitkeep`), `jetson/tests/`, `jetson/tests/unit/`, `jetson/tests/integration/`, `jetson/tests/system/`
- [X] T002 [P] Update `jetson/requirements.txt` — add `scipy>=1.11`, `paho-mqtt>=2.0`, `pytest>=8.0`, `pytest-mock>=3.14`
- [X] T003 [P] Update `jetson/docker/Dockerfile` — confirm `scipy` and `paho-mqtt` install correctly in the JetPack 6 base image; add `RUN pip3 install scipy paho-mqtt` after existing pip install
- [X] T004 [P] Update `jetson/docker/docker-compose.yaml` — add `state/` volume mount, `MQTT_BROKER`, `MQTT_PORT`, `MQTT_TOPIC`, `HUD_USERNAME`, `HUD_PASSWORD` environment variables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types, expanded configuration, and test infrastructure that ALL user story phases depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Create `jetson/src/types.py` — define all shared dataclasses and enums: `Frame`, `Detection`, `TrackedTarget`, `ThreatAssessment`, `TurretCommand`, `TurretPosition`, `LRFReading`, `TelemetryRecord`, `ThreatTier` enum (`LOW`/`MED`/`HIGH`), `FSMState` enum (`SCAN`/`TRACK`/`ACQUIRE`/`SEARCH`); full type hints and Google-style docstrings per data-model.md
- [X] T006 Expand `jetson/src/config.py` — add all ~50 parameters from `specs/001-jetson-core/contracts/config-schema.md`: scoring weights (`W_DISTANCE`, `W_MOTION`, `W_GROUPING`, `W_TIME_OF_DAY`), FSM dwell times (`MIN_DWELL_MS_SCAN/TRACK/ACQUIRE/SEARCH`), scan sweep params (`SCAN_PAN_MIN/MAX`, `SCAN_VELOCITY`, `SCAN_TILT_HOME`), limit thresholds (`PAN_LIMIT_WARN/HARD_STEPS`, `TILT_LIMIT_WARN/HARD_STEPS`), SEARCH params (`SEARCH_ARC_DEG`, `SEARCH_TIMEOUT_S`), telemetry params, MQTT params, web HUD params, resilience params (`MAX_BOOT_FAILURES`, `BOOT_STATE_PATH`)
- [X] T007 [P] Expand `jetson/src/utils/config.yaml` — document every parameter from `config.py` with its unit, valid range, and default value; format per `specs/001-jetson-core/contracts/config-schema.md`
- [X] T008 [P] Refactor `jetson/src/control/pid.py` — add full type hints (`kp: float`, `ki: float`, etc.), Google-style docstrings, and replace magic number `500` in windup clamp with a `max_integral` constructor parameter; algorithm and logic UNCHANGED
- [X] T009 Create `jetson/tests/conftest.py` — define shared pytest fixtures: `MockCamera` (Protocol with `read() → np.ndarray | None`, `stop()`), `MockSerial` (Protocol with `write()`, `read_line() → str | None`), `MockMQTTPublisher` (Protocol with `publish_async()`); provide factory functions that return pre-configured mock instances for all unit and integration tests
- [X] T010 [P] Remove deprecated dev scripts `jetson/src/control/tracker.py` (dev test harness) and `jetson/src/control/mock_sentry.py` (dev test harness) — these are replaced by `vision/tracker.py` and the test suite respectively

**Checkpoint**: Foundation complete — all user story phases may now begin (US1 must complete before US2+).

---

## Phase 3: User Story 1 — System Detects and Tracks a Human Threat (Priority: P1) 🎯 MVP

**Goal**: Camera captures frames → YOLO detects persons → centroid tracker assigns persistent IDs →
PID calculates pan/tilt velocity → Arduino serial receives `V <pan> <tilt>` commands. Turret
physically follows the target.

**Independent Test**: Point the thermal camera at a person; confirm turret pans/tilts to centre
them on screen. In CI: mock camera emits a moving bounding box; assert `V` command values converge
toward `V 0.00 0.00` as the simulated target approaches centre.

- [X] T011 Write `jetson/tests/unit/test_pid.py` — TDD (confirm failing first): test proportional output scales with error, integral accumulates over time, anti-windup clamps integral at `max_integral`, `reset()` zeroes all state, output is clamped to `±max_out`
- [X] T012 [P] Write `jetson/tests/unit/test_tracker.py` — TDD (confirm failing first): test new detection gets next sequential ID, same detection in next frame keeps same ID, disappearance counter increments each frame without match, counter resets to 0 on re-match, target deregistered after `max_disappeared` frames, velocity vector computed from centroid delta
- [X] T013 [P] Write `jetson/tests/integration/test_vision_pipeline.py` — TDD (confirm failing first): mock camera frame → `ObjectDetector` (mocked YOLO) → `CentroidTracker` → `PIDController` → assert `TurretCommand` pan/tilt velocities are non-zero for off-centre target and converge to zero for centred target
- [X] T013a Write `jetson/tests/unit/test_camera.py` — TDD (confirm failing first): mock `cv2.VideoCapture`; assert `ThreadedCamera.read()` returns `Frame` when capture is open; assert `is_open` is `False` after `stop()`; assert fallback to V4L2 when GStreamer open fails; assert `[CAMERA]` prefix on all log messages
- [X] T013b [P] Write `jetson/tests/unit/test_detector.py` — TDD (confirm failing first): mock `ultralytics.YOLO`; assert `ObjectDetector.__init__` calls warm-up with a black dummy frame; assert `detect()` returns `list[Detection]` with correct `bbox`, `confidence`, `class_id`; assert `RuntimeError` with `[AI]` prefix raised on model load failure
- [X] T013c [P] Write `jetson/tests/unit/test_serial_io.py` — TDD (confirm failing first): mock `pyserial.Serial`; assert `SerialPort.write()` encodes to bytes; assert `read_line()` returns `None` when buffer empty; assert `is_connected` is `False` when port not open; assert `close()` calls `serial.close()`
- [X] T014 Implement `jetson/src/vision/tracker.py` — `CentroidTracker` class: `update(detections: list[Detection]) → list[TrackedTarget]`; use `scipy.spatial.distance.cdist` for centroid-to-detection matching; `OrderedDict` for ID→centroid map; `disappeared` counter per target; velocity vector as centroid delta between last two matched frames; IDs reset to 0 at class instantiation (per session)
- [X] T015 Refactor `jetson/src/vision/camera.py` — add `CameraProtocol` ABC (`read() → Frame | None`, `stop()`); add type hints throughout; prefix all log messages with `[CAMERA]`; extract GStreamer pipeline string to `config.GST_PIPELINE`; add `is_open: bool` property; keep existing GStreamer→V4L2 fallback logic
- [X] T016 [P] Refactor `jetson/src/vision/detector.py` — change return type from single `dict` to `list[Detection]`; add TRT warm-up call on `__init__` with a black dummy frame; catch `RuntimeError`, `AssertionError`, `FileNotFoundError` and re-raise as `RuntimeError` with `[AI]` prefix; add full type hints and docstrings
- [X] T017 Implement `jetson/src/comms/serial_io.py` — define `SerialProtocol` (typing.Protocol: `write(data: bytes) → None`, `read_line() → str | None`, `is_connected: bool`, `close() → None`); implement `SerialPort` class wrapping `pyserial.Serial`; include `open(port, baud)` and `close()`; no reconnect logic here (that belongs in `arduino_link.py`)
- [X] T018 Refactor `jetson/src/hardware/arduino_link.py` — inject `SerialProtocol` via constructor (enables mocking); implement `send_velocity(pan: float, tilt: float) → None` formatting `V {pan:.2f} {tilt:.2f}\n`; implement `connect() → bool`; remove inline `serial.Serial` usage; prefix logs with `[SERIAL]`; keep `send_enable()` for now
- [X] T019 Refactor `jetson/src/main.py` — implement US1 loop: `camera.read()` → `detector.detect()` → `tracker.update()` → `pid.update(error)` → `arduino_link.send_velocity()`; wrap the core loop with `time.monotonic()` bracketing; log `[PERF] loop_ms=XX` every 100 iterations; emit `[PERF] WARNING: loop exceeded 100 ms (XX ms)` on any outlier; add dead-zone check using `config.DEAD_ZONE`; stub `session_id = None` placeholder (completed in US3); keep web stream thread start

---

## Phase 4: User Story 2 — Threat Scoring Governs System Behaviour (Priority: P2)

**Goal**: Each tracked target receives a threat score (0–100) based on distance, motion, time of
day, and grouping. The FSM transitions between SCAN / TRACK / ACQUIRE / SEARCH based on the
highest-scoring target. The FSM is the sole authority for serial commands.

**Independent Test**: Simulate targets at LOW/MED/HIGH score thresholds; assert the FSM enters the
correct state, applies the correct LRF sampling strategy, and dwell timers block premature downward
transitions.

- [X] T020 Write `jetson/tests/unit/test_threat_scoring.py` — TDD (confirm failing first): test score is clamped to [0, 100], LOW/MED/HIGH tier boundaries using configurable thresholds, highest-scoring target is selected from list, distance weight dominates when bounding box is large, `LRF_ENABLED=False` produces `lrf_required=False` regardless of score
- [X] T021 [P] Write `jetson/tests/unit/test_fsm_brain.py` — TDD (confirm failing first): test all 12 state transitions (every FROM→TO pair), dwell timer blocks downward transitions before `min_dwell_ms` elapses, upward transitions are immediate regardless of dwell, SEARCH times out to SCAN after `SEARCH_TIMEOUT_S`, SCAN sweep reverses direction at `SCAN_PAN_MIN`/`SCAN_PAN_MAX`, 360°-compatible mode when limits span full range
- [X] T022 Implement `jetson/src/control/threat_tracker.py` — `ThreatScorer.score(target: TrackedTarget, all_targets: list[TrackedTarget], lrf_enabled: bool) → ThreatAssessment`; scoring formula with configurable weights from `config`; bounding-box-area-to-distance-proxy calculation (for no-LRF mode); `ThreatTier` classification; `lrf_required` flag; `recommended_state` field mapping tier to FSMState
- [X] T023 Implement `jetson/src/control/sentry_brain.py` — `SentryBrain` FSM class: state stored as `FSMState` enum; `state_entered_ns = time.monotonic_ns()` on every transition; `_transition(new_state) → bool` with dwell gate (downward) / immediate (upward); `SCAN` sweep: oscillating pan between `SCAN_PAN_MIN`/`SCAN_PAN_MAX` with `SCAN_VELOCITY`, 360°-compatible when limits span full range, tilt at `SCAN_TILT_HOME`; `SEARCH` arc: sweep ±`SEARCH_ARC_DEG` around `last_known_pan` at `SCAN_VELOCITY`, timeout→SCAN; `update(targets, position) → TurretCommand` as primary API; `[BRAIN]` log prefix
- [X] T024 Update `jetson/src/hardware/arduino_link.py` — add `fire_lrf() → None` method sending `L\n`; add `last_lrf_reading: LRFReading | None` property populated from async DIST parse (stubbed here, completed in US5)
- [X] T025 Update `jetson/src/main.py` — replace direct PID→serial path with `SentryBrain.update()` as the sole control authority; pass `ThreatAssessment` list and `TurretPosition` to FSM; FSM returns `TurretCommand` which is sent to `arduino_link`; remove any direct `pid.update()` calls from main loop (PID now called inside `sentry_brain.py`)

---

## Phase 5: User Story 3 — GPS Telemetry Estimates Target Location (Priority: P3)

**Goal**: When LRF returns a distance, compute target GPS coordinates from sentry position +
turret angle + LRF range. Emit `TelemetryRecord` (with `session_id`) to a rotating JSON-lines
log file and to MQTT. GPS fields are `null` when `LRF_ENABLED=False`.

**Independent Test**: Fix sentry at a known position, feed known pan/tilt + LRF distance, assert
computed (lat, lon) matches known ground truth within ±2 m.

- [X] T026 Write `jetson/tests/unit/test_geo.py` — TDD (confirm failing first): test Haversine against known coordinate pair (e.g., Johannesburg → 100 m north), assert result within ±0.0001° (~10 m), test `compute_target_gps` returns `(None, None)` when `distance_m` is `None`, test heading offset via `SENTRY_HEADING_DEG`
- [X] T027 [P] Write `jetson/tests/unit/test_telemetry_recorder.py` — TDD (confirm failing first): test every emitted record contains the constructor's `session_id`, test `lat`/`lon`/`lrf_distance_m` are `null` when LRF disabled, test JSON output is valid parseable JSON-lines, test `publish_async` is called on the mock MQTT client, test file is rotated when size exceeds `TELEMETRY_MAX_BYTES`
- [X] T028 Implement `jetson/src/control/geo.py` — `compute_target_gps(sentry_lat, sentry_lon, azimuth_deg, distance_m) → tuple[float, float]` using pure-stdlib Haversine formula from `research.md §Decision 3`; `pan_tilt_to_azimuth(pan_steps, tilt_steps, heading_offset_deg) → tuple[float, float]` converting step counts via `config.STEPS_PER_DEGREE` + `SENTRY_HEADING_DEG`; full type hints and docstrings; returns `(None, None)` when `distance_m` is `None`
- [X] T029 Implement `jetson/src/comms/mqtt.py` — `MQTTPublisher` class: `MQTTProtocol` ABC (`publish_async(payload: str) → None`); daemon background thread with `queue.Queue(maxsize=500)`; `paho.mqtt.client` with `on_connect`/`on_disconnect` callbacks; exponential backoff reconnect (1s→2s→…→30s max) in thread loop; `publish_async()` does `queue.put_nowait()` + logs `[MQTT] Queue full` on overflow; MQTT failures never propagate to caller; `[MQTT]` log prefix throughout
- [X] T030 Implement `jetson/src/telemetry/recorder.py` — `TelemetryRecorder(session_id: str, mqtt: MQTTProtocol, config)` class; `session_id` injected at construction (UUID4, generated in `main.py`); `record(target, assessment, lrf_reading, position) → TelemetryRecord` builds the dataclass, sets nullable GPS fields via `geo.compute_target_gps`; `emit(record)` serialises with `dataclasses.asdict()` → `json.dumps()` → writes to `RotatingFileHandler` and calls `mqtt.publish_async()`; `[TELEMETRY]` log prefix
- [X] T031 Update `jetson/src/main.py` — generate `session_id = str(uuid.uuid4())` at process startup; pass `session_id` to `TelemetryRecorder` constructor; instantiate `MQTTPublisher` and `TelemetryRecorder`; call `recorder.record(...)` once per FSM update for every active target
- [X] T032 [P] Implement `jetson/src/control/geo.py` (canonical location per plan.md — do NOT move to `utils/`); implement Haversine formula: `bearing_from_pan(pan_steps: int) → float`, `haversine(lat1, lon1, bearing_deg, distance_m) → tuple[float, float]`; validate against known coordinate pairs in docstring; add `[GEO] WARNING` log at module import if `SENTRY_LAT == 0.0 and SENTRY_LON == 0.0`; delete `jetson/src/utils/geo.py` stub and update any imports

---

## Phase 6: User Story 4 — Operator Monitors the System via Web HUD (Priority: P4)

**Goal**: Flask MJPEG stream at configured port, protected by HTTP Basic Auth. Overlays show
bounding boxes (red), tracking IDs, threat score, FSM state, and limit warnings (yellow). Web
thread never degrades the main control loop.

**Independent Test**: `curl -u sentry:changeme http://localhost:5000/video_feed` returns
`multipart/x-mixed-replace` stream. `curl http://localhost:5000/video_feed` returns HTTP 401.

- [X] T033 Write `jetson/tests/integration/test_web_stream.py` — TDD (confirm failing first): test unauthenticated `GET /video_feed` returns HTTP 401 with `WWW-Authenticate` header, test authenticated request returns HTTP 200 with `multipart/x-mixed-replace` content-type, test `GET /` returns HTML page, test wrong password returns 401
- [X] T034 Refactor `jetson/src/web/streamer.py` — add HTTP Basic Auth: wrap `/video_feed` and `/` routes with `functools.wraps`-based auth decorator checking `config.HUD_USERNAME` / `config.HUD_PASSWORD`; return `401` with `WWW-Authenticate: Basic realm="Sentry HUD"` on failure; add `StreamProtocol` ABC for mock injection; add full type hints; add `[WEB]` log prefix; keep MJPEG generate logic unchanged
- [X] T035 Update `jetson/src/main.py` — add HUD overlay rendering: red bounding boxes for all tracked targets, green text for FSM state + target ID + threat score + loop FPS, yellow `[TURRET] Approaching limit` warning text when `SentryBrain` reports limit proximity; pass annotated frame to `update_stream_frame()`

---

## Phase 7: User Story 5 — System Recovers Automatically from Hardware Faults (Priority: P5)

**Goal**: Camera disconnect → stop motors + retry indefinitely. Serial disconnect → retry
indefinitely + heartbeat watchdog. GPU startup failure → fatal halt + Docker restart + OS reboot
escalation. Turret near limit → graduated velocity taper + HUD warning. Malformed serial frames
→ discard + log.

**Independent Test**: Unplug USB camera while running; confirm `[CAMERA] Disconnected` log and
zero-velocity command; reconnect cable; confirm system resumes within 5 s. Replay malformed
serial lines into mock port; confirm each is discarded with `[SERIAL] Malformed frame discarded`
log and the control loop continues.

- [X] T036 Write `jetson/tests/unit/test_serial_framing.py` — TDD (confirm failing first): test `DIST 150.50` parses to `LRFReading(distance_m=150.50, valid=True)`, test `POS 1000 -250` parses to `TurretPosition(pan_steps=1000, tilt_steps=-250)`, test `DIST abc` emits `[SERIAL] Malformed frame discarded: DIST abc` log and returns `LRFReading(valid=False)`, test empty line is discarded, test heartbeat timeout flag set when no POS received within `SERIAL_HEARTBEAT_TIMEOUT_S`
- [X] T037 [P] Write `jetson/tests/integration/test_serial_roundtrip.py` — TDD (confirm failing first): using `MockSerial`, test `send_velocity(100.0, -50.0)` writes `b"V 100.00 -50.00\n"`, test `fire_lrf()` writes `b"L\n"`, test `DIST` response updates `last_lrf_reading`, test `MockSerial` injecting `POS 0 0` lines keeps heartbeat alive, test disconnect detection triggers reconnect attempt
- [X] T038 Complete `jetson/src/comms/serial_io.py` — add background read thread: calls `readline()` in loop, validates each line against `re.match(r'^(DIST \d+(\.\d+)?|POS -?\d+ -?\d+)$', line)`; on match: parse and update shared `TurretPosition` / `LRFReading` state (thread-safe `threading.Lock`); on no match: log `[SERIAL] Malformed frame discarded: <raw>`; track `last_pos_received_ns` for heartbeat; expose `is_heartbeat_alive() → bool`
- [X] T039 Complete `jetson/src/hardware/arduino_link.py` — add full reconnect loop: on `SerialException` or `is_heartbeat_alive() == False`, send best-effort `V 0.00 0.00\n`, close port, log `[SERIAL] Disconnected — retrying in <n>s`, wait `config.SERIAL_RETRY_INTERVAL_S`, retry `SerialPort.open()`; on success log `[SERIAL] Reconnected`; reset `TurretPosition` to `(0, 0)` on reconnect; expose `current_position: TurretPosition` property; all write operations protected by `threading.Lock`
- [X] T040 [P] Update `jetson/src/vision/camera.py` — on `cap.read()` returning `ret=False` for `CAMERA_FAULT_THRESHOLD` consecutive frames: call `arduino_link.send_velocity(0, 0)`, log `[CAMERA] Disconnected — retrying`, release and reopen capture; retry indefinitely at `SERIAL_RETRY_INTERVAL_S` cadence; on reconnect log `[CAMERA] Reconnected — resuming pipeline`
- [X] T041 Add FR-031 velocity tapering to `jetson/src/control/sentry_brain.py` — add `taper_velocity(pos: int, warn: int, hard: int, velocity: float) → float` (linear scale: `max(0, (hard - abs(pos)) / (hard - warn))` when inside zone); apply per-axis before every `TurretCommand` is emitted; set `approaching_limit: bool` flag on `SentryBrain` when either axis is in taper zone; log `[TURRET] Approaching limit` once per taper-zone entry event
- [X] T042 Update `jetson/src/main.py` — implement boot failure counter (FR-030): on startup, read `config.BOOT_STATE_PATH` JSON; if `consecutive_failures >= config.MAX_BOOT_FAILURES`, call `os.system("sudo reboot")`; wrap `ObjectDetector.__init__()` in try/except `(RuntimeError, AssertionError, FileNotFoundError)`; on exception: increment counter, write file, log `[SYSTEM] FATAL — TensorRT inference failed to initialise`, `sys.exit(1)`; on successful main loop entry: reset counter to 0 and write file

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Resolve known spec conflicts, clean up, and validate end-to-end.

- [X] T043 Run full test suite `pytest jetson/tests/ -v` — confirm all unit and integration tests pass (TDD Green phase); fix any failing tests before proceeding; record final coverage metric
- [X] T044 [P] Audit codebase for any `isinstance(session_id, ...)` checks or ISO-format date assertions that may have been introduced; ensure all `session_id` usages match `uuid.uuid4()` generation pattern (spec FR-004/FR-034 now unified on UUID4)
- [X] T045 [P] Add explicit comment block in `sentry_brain.py` documenting FSM transition priority (SEARCH fires immediately on `max_disappeared`; idle-timeout motor-stop applies only within SCAN; this is already specified in spec FR-015/FR-022 — code comment ensures future maintainers don't reintroduce the conflict)
- [X] T046 [P] Ensure `jetson/src/state/.gitkeep` exists (created in T001); add `jetson/src/state/*.json` to `.gitignore` (runtime-generated file); document `boot_state.json` schema in `specs/001-jetson-core/quickstart.md §Troubleshooting`
- [X] T047 [P] Update `specs/001-jetson-core/quickstart.md` — add prerequisites: `nvidia-container-toolkit` install, TRT engine export command (`yolo export model=yolov8n.pt format=engine`), JetPack version pinning note, `sudo reboot` permission note for boot counter
- [X] T049 End-to-end smoke test [NOTE: Requires physical hardware — skipped per spec instructions] — run container with looped thermal test video (OpenCV `VideoCapture` on a recorded `.mp4`) + mock serial port (`socat pty,raw,echo=0 pty,raw,echo=0`); assert: main loop ≥20 Hz logged, web HUD stream accessible at port 5000, telemetry JSON-lines file written, no Python exceptions in 5-minute run; capture `tegrastats --interval 1000` output for first 60 s; log CPU/GPU/RAM baseline to `jetson/docs/resource-baseline.md`
- [X] T049a Write `jetson/tests/system/test_endurance.py` — 72-hour soak: run full pipeline loop with looped test video + `MockSerial`; sample FPS every 60 s via `stats_queue`; assert FPS never drops below 18 Hz; track heap via `tracemalloc` every 5 min; assert heap growth < 50 MB over full run. Mark as `@pytest.mark.slow` — excluded from default CI; run on scheduled nightly workflow.
- [X] T050 **[HITL [NOTE: Requires physical hardware — pre-merge gate only] — Pre-Merge Gate]** Execute hardware-in-the-loop validation on physical Jetson + Arduino bench: (1) verify live USB thermal camera stream produces `Frame` objects at ≥20 Hz; (2) verify `V 100.0 0.0\n` over real serial port moves turret pan axis; (3) verify `L\n` triggers LRF and `DIST` response is parsed to `LRFReading`; (4) verify `TelemetryRecord` is written to JSON-lines file with valid `session_id` (UUID4); (5) verify `docker restart sentry` brings system back to SCAN state within 10 s. Document pass/fail in `jetson/docs/hitl-results.md`. **This task MUST be marked complete before any merge to `main`.**

---

## Dependencies

```
Phase 1 (Setup)
    └─► Phase 2 (Foundational)
            └─► Phase 3 (US1 — MVP) ← Must complete before US2, US3, US4, US5
                    └─► Phase 4 (US2 — Threat Scoring)
                    │       └─► Phase 5 (US3 — Telemetry)
                    └─► Phase 5 (US3 — Telemetry)  [needs US1 types]
                    └─► Phase 6 (US4 — Web HUD)    [needs US1 camera/main]
                    └─► Phase 7 (US5 — Fault Recovery) [needs US1 serial/camera]
Phase 8 (Polish) ← depends on all phases complete
```

**Key inter-phase dependencies**:
- T023 (`sentry_brain.py`) depends on T022 (`threat_tracker.py`)
- T024/T025 (`arduino_link.fire_lrf`, `main.py` FSM wiring) depend on T023
- T030 (`recorder.py`) depends on T028 (`geo.py`) and T029 (`mqtt.py`)
- T031 (`main.py` telemetry wiring) depends on T030
- T039 (`arduino_link` complete) depends on T038 (`serial_io` read thread)
- T042 (`main.py` boot counter) depends on T039 (full arduino_link)

---

## Parallel Execution Examples

### US1 Phase (after T013):
```
T014 (tracker.py)  ────────────────────────┐
T015 (camera.py)   ──────┐                 ├─► T019 (main.py)
T016 (detector.py) ──┐   │                 │
T017 (serial_io.py)  └───┴── T018 (link) ──┘
```

### US2 Phase (after T021):
```
T022 (threat_tracker.py) ──┐
                            ├─► T023 (sentry_brain.py) ─► T025 (main.py)
[T021 tests already done]  ┘
T024 (arduino_link LRF) can run alongside T022
```

### US3 Phase (after T027):
```
T028 (geo.py)   ──┐
T029 (mqtt.py)  ──┴─► T030 (recorder.py) ─► T031 (main.py)
```

### US5 Phase:
```
T036 (test_serial_framing.py) ──────────────────────────┐
T037 (test_serial_roundtrip.py) ──┐                     │
                                   ├─► T038 (serial_io) ─► T039 (arduino_link)
T040 (camera fault) ──── independent [P]                │
T041 (taper in brain) ── independent [P]                └─► T042 (main.py boot)
```

---

## Implementation Strategy

**MVP** = Phase 1 + Phase 2 + Phase 3 (US1) — delivers a working detect-and-track turret.

**Delivery order** (each increment is independently testable):
1. **US1** (T001–T019): Turret follows a detected person — the minimum viable security function
2. **US2** (T020–T025): Proportional threat response — prevents LRF spam and jitter
3. **US3** (T026–T032): GPS telemetry — actionable intelligence for incident response
4. **US4** (T033–T035): Web HUD — remote visibility for commissioning and monitoring
5. **US5** (T036–T042): Fault recovery — unattended field deployment reliability
6. **Polish** (T043–T050): Spec alignment, smoke test, documentation, HITL validation

---

## Task Summary

| Phase | Tasks | User Story | Parallel Tasks | Key Deliverable |
|-------|-------|------------|----------------|-----------------|
| 1 — Setup | T001–T004 | — | T002, T003, T004 | Directory structure, deps |
| 2 — Foundation | T005–T010 | — | T007, T008, T010 | Types, config, test fixtures |
| 3 — US1 | T011–T019 | US1 | T012, T013, T016 | Working detect-and-track MVP |
| 4 — US2 | T020–T025 | US2 | T021, T024 | FSM + threat scoring |
| 5 — US3 | T026–T032 | US3 | T027, T032 | GPS telemetry + MQTT |
| 6 — US4 | T033–T035 | US4 | — | Authenticated web HUD |
| 7 — US5 | T036–T042 | US5 | T037, T040, T041 | Full fault recovery |
| 8 — Polish | T043–T050 | — | T044–T047, T049a, T050 | Validated, deployable system |

**Total tasks**: 53
**Parallel-eligible**: 22 tasks marked `[P]`
**TDD test tasks**: 13 (T011–T013, T013a–T013c, T020–T021, T026–T027, T033, T036–T037)
