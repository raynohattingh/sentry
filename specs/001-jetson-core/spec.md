# Feature Specification: Sentry Jetson Core — Autonomous Thermal Turret Brain

**Feature Branch**: `001-jetson-core`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Autonomous thermal sentry turret brain for farm security (South Africa) — Jetson Orin Nano Super,
Python 3.10+, Docker, YOLOv8 TensorRT, PID pan/tilt, LRF GPS telemetry, Arduino serial, Flask MJPEG stream.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — System Detects and Tracks a Human Threat (Priority: P1)

The farm operator deploys the sentry on the perimeter. When a person enters the thermal camera's field of
view, the system automatically detects them, assigns a tracking ID, and begins physically following them
with the turret — without any operator intervention.

**Why this priority**: This is the minimum viable function of the turret. Without detection and tracking,
the system delivers no security value.

**Independent Test**: Can be fully tested by pointing the thermal camera at a person and confirming the
turret physically pans/tilts to keep the detection bounding box centred on screen.

**Acceptance Scenarios**:

1. **Given** the system is running and the thermal camera is connected,
   **When** a person enters the camera frame,
   **Then** a bounding box is drawn around them within 1 second, a unique tracking ID is assigned,
   and the turret begins moving to centre the target.

2. **Given** a person is being tracked,
   **When** they move laterally or vertically,
   **Then** the turret follows continuously and the bounding box remains centred within the dead-zone.

3. **Given** a person is being tracked,
   **When** they step briefly behind an obstruction and re-emerge within the same area,
   **Then** they are re-assigned the same tracking ID without the turret losing lock.

4. **Given** no person is visible for more than the configured idle timeout,
   **When** the timeout elapses,
   **Then** the turret stops all movement and the system transitions to SCAN state.

---

### User Story 2 — Threat Scoring Governs System Behaviour (Priority: P2)

The farm operator needs the sentry to respond proportionally to threat level: a distant stationary figure
warrants logging only, while a fast-approaching group triggers hard lock and continuous ranging.

**Why this priority**: Proportional response prevents false-alarm fatigue and ensures hardware resources
(LRF shots) are reserved for genuine threats.

**Independent Test**: Can be tested by simulating targets at different distances and motion vectors and
asserting that the system enters the correct state (SCAN / TRACK / ACQUIRE) and applies the correct
LRF sampling strategy for each threat tier.

**Acceptance Scenarios**:

1. **Given** a tracked target whose calculated threat score is below 40,
   **When** the score is evaluated,
   **Then** the system logs the target's position, does not fire the LRF, and continues scanning.

2. **Given** a tracked target whose threat score is between 40 and 79,
   **When** the score is evaluated,
   **Then** the system enters TRACK state, applies sampled LRF ranging (look → sweep → look), and
   updates the target's position estimate.

3. **Given** a tracked target whose threat score is 80 or above,
   **When** the score is evaluated,
   **Then** the system enters ACQUIRE state, fires the LRF continuously, hard-locks the turret on the
   target, and emits high-priority telemetry.

4. **Given** multiple targets in the frame simultaneously,
   **When** scores are calculated,
   **Then** the system locks onto the highest-scoring target first; lower-priority targets are queued.

---

### User Story 3 — GPS Telemetry Estimates Target Location (Priority: P3)

The farm operator monitors an incident remotely. When the LRF returns a distance, the system must
calculate the target's GPS coordinates so operators can dispatch a response to the correct location.

**Why this priority**: GPS output is the actionable intelligence that justifies the system's complexity.
Without it the operator knows there is a threat but not where to respond.

**Independent Test**: Can be tested by fixing the turret at a known pan/tilt angle, feeding a known LRF
distance, and asserting that the computed (lat, lon) matches the known ground-truth coordinate within
the acceptable error margin.

**Acceptance Scenarios**:

1. **Given** the sentry's own GPS position and the current turret pan/tilt angles are known,
   **When** the LRF returns a valid distance reading,
   **Then** the system computes the target's (lat, lon) and attaches it to the telemetry record.

2. **Given** the computed telemetry record,
   **When** the target is ≤ 500 m from the sentry,
   **Then** the calculated GPS position is accurate to within 10 m.

3. **Given** the LRF returns an invalid or out-of-range reading,
   **When** the telemetry calculation is attempted,
   **Then** the system marks the GPS field as unavailable and continues operating without crashing.

---

### User Story 4 — Operator Monitors the System via Web HUD (Priority: P4)

The farm operator or technician opens a browser on a local network device to observe the live thermal
feed with detection overlays, current system state, and key metrics — without needing SSH or a monitor.

**Why this priority**: Visibility into the running system is essential for commissioning, diagnostics,
and live monitoring without physical access.

**Independent Test**: Can be tested by connecting a browser to the Jetson's IP on the configured port
and verifying the MJPEG stream shows live frames with bounding boxes, tracking IDs, and status text.

**Acceptance Scenarios**:

1. **Given** the system is running and a client browser navigates to the Jetson's IP and port,
   **When** the page loads,
   **Then** a live MJPEG stream is displayed at ≥ 15 FPS with bounding boxes and tracking IDs overlaid.

2. **Given** a target is being tracked,
   **When** the operator views the HUD,
   **Then** the current FSM state, threat score, target ID, and error offset are visible on-screen.

3. **Given** the web stream client disconnects or crashes,
   **When** the disconnection occurs,
   **Then** the main vision and control loop continues running unaffected.

---

### User Story 5 — System Recovers Automatically from Hardware Faults (Priority: P5)

The sentry runs unattended outdoors. If the thermal camera cable is knocked loose or the Arduino resets,
the system must recover automatically — the farm owner cannot be expected to SSH in and restart.

**Why this priority**: Unattended reliability is a hard requirement for a perimeter security system.

**Independent Test**: Can be tested by unplugging the USB camera or Arduino serial cable while the system
is running and confirming the system detects the fault, logs a warning, and successfully reconnects when
the cable is restored — without operator action.

**Acceptance Scenarios**:

1. **Given** the system is running normally,
   **When** the camera connection is lost,
   **Then** the system logs a `[CAMERA] Disconnected — retrying` warning, stops the turret, and
   continuously attempts to reconnect without crashing.

2. **Given** the camera reconnects after a fault,
   **When** the connection is re-established,
   **Then** the system resumes the vision pipeline automatically within 5 seconds.

3. **Given** the Arduino serial port is lost,
   **When** the fault is detected,
   **Then** the system stops sending velocity commands, logs the fault, and retries the serial
   connection at the configured reconnection interval.

4. **Given** the entire process crashes,
   **When** the Docker container restarts (auto-restart policy),
   **Then** the system resumes full operation within 30 seconds without manual intervention.

---

### Edge Cases

- **What happens when two people enter the frame simultaneously and one occludes the other?**:
  ID re-assignment is governed by the centroid-nearest match algorithm. ID swap on re-emergence is
  an acceptable outcome; the system MUST NOT crash. The `test_tracker.py` suite (T012) MUST include
  an occlusion scenario asserting that both targets retain valid IDs post-emergence even if swapped.
- **What happens if `SENTRY_LAT`/`SENTRY_LON` are not configured (default `0.0, 0.0`)?**: The
  system MUST emit `[GEO] WARNING: SENTRY_LAT/LON are (0.0, 0.0) — GPS origin not configured` at
  startup. All TelemetryRecord `lat`/`lon` fields will be set to `null` until a valid GPS origin is
  configured. The system MUST NOT crash; it MUST continue operating with `null` coordinates.
- **How does the system behave when the LRF is not fitted or powered off?**: Controlled by the
  `LRF_ENABLED` config flag. When `false`, the system operates in vision+tracking-only mode: no
  `L\n` commands are sent to the Arduino, GPS fields in TelemetryRecords are set to `null`, and
  threat scoring uses estimated distance from bounding-box size rather than LRF measurement.
  The system logs a `[LRF] Disabled — running in vision-only mode` notice at startup.
- **What happens when the turret reaches a mechanical hard stop (pan/tilt limit)?**: The Jetson
  tracks cumulative step counts from `POS` serial messages and defines a configurable software
  limit zone (warn threshold + hard threshold in steps). As the turret enters the warn threshold,
  the system MUST taper outbound velocity commands proportionally to zero — not clamp abruptly —
  and MUST display a `[TURRET] Approaching limit` warning on the HUD overlay and emit a log entry.
  Physical limit switches installed in the sentry housing trigger the Arduino's independent
  hardware stop as a final safety net; the Arduino's switch-triggered stop is not a substitute for
  Jetson-side graduated deceleration.
- **How does the system handle corrupt or incomplete serial frames from the Arduino?**: Malformed,
  truncated, or unparseable lines MUST be discarded immediately. The system MUST emit a
  `[SERIAL] Malformed frame discarded: <raw_content>` structured log entry and treat the frame
  as a missed reading; the control loop continues uninterrupted with no retry attempt.
- **GPU / TensorRT fault at startup**: The system MUST halt immediately with a `[SYSTEM] FATAL —
  TensorRT inference failed to initialise` log entry. It MUST NOT enter the main loop in a
  degraded state. The Docker `always`/`unless-stopped` restart policy handles automatic recovery.
  If the process crashes on startup more than a configurable `max_boot_failures` consecutive times
  (default: 3), the system MUST trigger a full Jetson OS reboot via a system command to recover
  from hardware-level GPU faults (e.g., driver hang).
- **How does the system behave when the threat score oscillates rapidly across a tier boundary?**:
  The FSM enforces a per-state minimum dwell duration (`min_dwell_ms`, individually configurable
  per state). Downward transitions are blocked until the dwell elapses; upward transitions are
  immediate. This prevents LRF spam and erratic turret behaviour caused by frame-to-frame score
  noise near a boundary.
- What happens when the sentry's own GPS position is unavailable (fix not acquired)?

## Clarifications

### Session 2026-02-25

- Q: What should the system do in SEARCH state — and what triggers entry/exit? → A: Turret sweeps a configurable arc around the last-known target position for a configurable duration; if re-acquired → TRACK, if timeout elapses → SCAN.
- Q: Where should telemetry records (target ID, threat score, GPS estimate, timestamp) be published/stored? → A: Local file + MQTT publish (dual output: persist locally as a JSON-lines rotating log on the Jetson filesystem and broadcast to a broker topic in real time).
- Q: Should the web HUD require authentication before serving the MJPEG stream? → A: HTTP Basic Auth with a single configurable username/password stored in the config file.
- Q: What should the system do if TensorRT/GPU inference fails to initialise at startup? → A: Halt with a fatal error and descriptive log message; Docker auto-restart handles recovery. If consecutive crash-restart cycles exceed a configurable threshold, the system triggers a Jetson OS reboot via system command.
- Q: Who is responsible for enforcing pan/tilt position limits? → A: Dual enforcement. The Jetson tracks POS step counts and applies graduated velocity tapering as the turret approaches configurable software limits (not a hard clamp), and emits a visible HUD warning plus a log entry when the limit zone is entered. Physical limit switches installed on the sentry housing serve as the Arduino's independent hardware safety net.

### Session 2026-02-25 (continued)

- Q: Is the LRF a required hardware component, or an optional module the system operates without? → A: Optional, controlled by a config flag (`LRF_ENABLED`). When disabled or unresponsive, the system continues in vision+tracking-only mode; telemetry records omit GPS coordinates but are still written/published.
- Q: How should the system prevent rapid FSM state thrashing when a threat score oscillates near a tier boundary? → A: Minimum dwell time per state. Once in a state, the FSM MUST NOT make a downward transition until a configurable per-state dwell duration has elapsed. Each FSM state (SCAN, TRACK, ACQUIRE, SEARCH) has its own independently configurable `min_dwell_ms`. Upward transitions (to higher threat tier) are immediate regardless of dwell.
- Q: What movement pattern should the turret execute during SCAN state? → A: Oscillating sweep (left→right→left) at configurable angular velocity between configurable `scan_pan_min` and `scan_pan_max` step limits, with tilt held at a configurable `scan_tilt_home`. The design MUST be forward-compatible with full 360° continuous rotation: when `scan_pan_min` and `scan_pan_max` span the full step range, the turret sweeps continuously without reversing direction.
- Q: How should the system handle corrupt or incomplete serial frames from the Arduino? → A: Discard and emit a structured `[SERIAL] Malformed frame discarded: <raw>` log entry; treat the frame as a missed reading and continue with no retry.
- Q: Do tracking IDs reset on each container restart, or persist across restarts? → A: Reset to zero on each restart. A unique `session_id` (UUID) is generated at startup and included in every TelemetryRecord, enabling cross-restart correlation in log analysis.

## Requirements *(mandatory)*

### Functional Requirements

**Vision Pipeline**

- **FR-001**: The system MUST ingest video from a USB thermal camera (CVBS→USB, 480×320 YUYV) via
  GStreamer with automatic fallback to V4L2 if GStreamer is unavailable.
- **FR-002**: Frame capture MUST run in a dedicated background thread; the buffer MUST discard stale
  frames so the consumer always receives the most recent frame.
- **FR-003**: The system MUST run YOLOv8 inference (TensorRT-optimised) on each frame to detect
  objects of class "Person" with a configurable confidence threshold.

**Target Tracking**

- **FR-004**: The system MUST assign a unique numeric ID to each detected person and maintain that ID
  across consecutive frames using centroid-based tracking. IDs reset to zero on each container
  restart. A `session_id` (UUID4 generated at startup) MUST be attached to every TelemetryRecord
  to enable cross-restart correlation of events. Tracking IDs reset to zero on each container
  restart; they are scoped to the current session only.
- **FR-034**: At startup, the system MUST generate a unique `session_id` (UUID4) and attach it to
  every TelemetryRecord emitted during that run. The `session_id` enables cross-restart
  correlation when analysing JSON-lines log files or MQTT streams.
- **FR-005**: The tracker MUST handle temporary occlusion: if a target disappears for fewer than the
  configured `max_disappeared` frames, its ID MUST be preserved on re-detection.

**Threat Scoring**

- **FR-006**: The system MUST calculate a threat score (0–100) for each tracked target using at least
  these inputs: estimated distance, motion vector magnitude, current time of day, and proximity to
  other detected targets. Grouping is computed as:
  `min(1.0, count_of_targets_within_GROUP_RADIUS_PX / GROUP_MAX_COUNT)` where `GROUP_RADIUS_PX`
  is the pixel-distance threshold for considering two targets grouped, and `GROUP_MAX_COUNT` is the
  count at which the grouping component saturates to 1.0. Both values are configurable.
- **FR-007**: Threat tier thresholds MUST be configurable in the central config file without code changes.
- **FR-008**: Targets scoring ≥ 80 MUST receive continuous LRF ranging and hard turret lock (ACQUIRE state).
- **FR-009**: Targets scoring 40–79 MUST receive sampled LRF ranging (look → sweep → look) and
  sustained tracking (TRACK state). The look→sweep→look pattern is: (1) fire LRF (`L\n`), wait
  `LRF_SAMPLE_INTERVAL_MS`; (2) apply a pan offset of `LRF_SWEEP_ARC_DEG` degrees; (3) fire LRF
  again; (4) return to the tracked-target centroid. Both `LRF_SAMPLE_INTERVAL_MS` and
  `LRF_SWEEP_ARC_DEG` are configurable constants.
- **FR-010**: Targets scoring < 40 MUST have their last known position logged; the LRF MUST NOT be
  fired; the turret continues scanning (SCAN state).

**Motion Control**

- **FR-011**: The system MUST calculate pan and tilt velocity commands using a configurable PID
  controller to minimise the pixel-error between the target centroid and the frame centre.
- **FR-012**: The PID controller MUST include integral windup protection to prevent runaway
  accumulated error.
- **FR-013**: Within a configurable dead-zone radius (pixels) around the frame centre, the system
  MUST send zero-velocity commands to prevent mechanical jitter.
- **FR-014**: All motor movement MUST be issued exclusively via velocity commands to the Arduino over
  serial; the Jetson MUST NOT attempt direct motor control.
- **FR-015**: While in SCAN state, if no target has been acquired for longer than the configured
  `idle_timeout_s`, the system MUST send a zero-velocity command and remain in SCAN state with
  motors stopped. This timeout applies only within SCAN — it does not override the SEARCH state
  (FR-022). When a tracked target disappears, the FSM transitions immediately to SEARCH (not SCAN);
  SCAN is only re-entered when SEARCH times out or from idle within SCAN itself.

**Telemetry & GPS**

- **FR-016**: When `LRF_ENABLED` is `true` and an LRF reading is received, the system MUST compute
  the target's (lat, lon) from the sentry's known GPS position, current pan/tilt angles, and the
  measured distance using Vincenty or Haversine geodesic math. When `LRF_ENABLED` is `false`, this
  computation MUST be skipped entirely.
- **FR-017**: Computed telemetry (target ID, threat score, GPS estimate, timestamp) MUST be output
  via two channels simultaneously:
  1. **Local file**: Appended as a JSON-lines entry to a rotating log file on the Jetson
     filesystem; the file path and rotation policy (max size / max files) MUST be configurable.
  2. **MQTT publish**: Published to a configurable MQTT broker topic in the same JSON format
     so remote consumers can receive alerts in real time.
  If the MQTT broker is unavailable, the system MUST continue operating and writing to the local
  file without interruption; MQTT failures MUST be logged but MUST NOT propagate as fatal errors.
- **FR-018**: When `LRF_ENABLED` is `false`, or when a reading is invalid or absent, the system MUST
  set `lat`, `lon`, and `lrf_distance_m` to `null` in the TelemetryRecord and continue operating
  without error. The record MUST still be written to the local log and published via MQTT.

**Hardware Communication**

- **FR-019**: The system MUST communicate with the Arduino over serial at 115 200 baud using the
  defined protocol: `V <pan> <tilt>\n` for velocity, `L\n` to trigger the LRF.
- **FR-033**: All incoming serial lines MUST be validated before processing. Lines that do not
  match an expected message pattern (`DIST <float>` or `POS <int> <int>`) MUST be discarded
  without raising an exception. A structured `[SERIAL] Malformed frame discarded: <raw>`
  log entry MUST be emitted for each discarded line. The control loop MUST NOT stall or crash
  on malformed input.
- **FR-020**: The serial link MUST implement a heartbeat or watchdog so a silent Arduino is detected
  within a configurable timeout.
- **FR-021**: On serial disconnection or fault, the system MUST attempt reconnection indefinitely at a
  configurable retry interval without crashing.

**Finite State Machine**

- **FR-022**: The system MUST implement a Finite State Machine with states: SCAN, TRACK, ACQUIRE,
  SEARCH; transitions MUST be driven by threat score and target visibility. State definitions:
  - **SCAN**: No active target; turret executes a continuous oscillating pan sweep between
    configurable `scan_pan_min` and `scan_pan_max` step limits at a configurable
    `scan_velocity`, while tilt is held at a configurable `scan_tilt_home` position.
    The implementation MUST be forward-compatible with full 360° continuous rotation:
    when the configured limits span the full mechanical step range, the turret rotates
    continuously in one direction without reversing.
  - **TRACK**: Active target with threat score 40–79; turret follows target with sampled LRF ranging.
  - **ACQUIRE**: Active target with threat score ≥ 80; turret hard-locks with continuous LRF ranging.
  - **SEARCH**: Entered when a tracked target is lost (disappears beyond `max_disappeared` frames);
    turret sweeps a configurable arc centred on the last-known target position for a configurable
    `search_timeout` duration; if the target is re-acquired → TRACK; if timeout elapses → SCAN.
- **FR-023**: The FSM MUST be the sole authority for deciding which serial commands are sent and when
  the LRF is triggered.
- **FR-032**: The FSM MUST enforce a per-state minimum dwell duration to prevent thrashing when a
  threat score oscillates near a tier boundary. Each state (SCAN, TRACK, ACQUIRE, SEARCH) MUST
  have an independently configurable `min_dwell_ms` value. Downward transitions (to a lower
  threat tier or back to SCAN) are only permitted after the current state's `min_dwell_ms` has
  elapsed. Upward transitions (to a higher threat tier) are immediate regardless of dwell time.

**Web Interface**

- **FR-024**: The system MUST serve a live MJPEG stream with detection overlays (bounding boxes,
  tracking IDs, threat score, FSM state) on a configurable HTTP port, protected by HTTP Basic
  Auth. The username and password MUST be configurable in the central config file. Unauthenticated
  requests MUST receive a 401 response.
- **FR-025**: The web stream MUST run in a background thread and MUST NOT degrade the main
  vision/control loop's throughput.

**Resilience**

- **FR-026**: On camera disconnection, the system MUST stop issuing movement commands, log the fault,
  and retry camera initialisation indefinitely. A camera fault is declared after
  `CAMERA_FAULT_THRESHOLD` consecutive frames fail to produce a valid capture. The system MUST log
  `[CAMERA] Fault declared after {N} failed frames` and initiate reconnect.
- **FR-027**: The system MUST be deployable as a Docker container with an `always` or `unless-stopped`
  restart policy so that a process crash triggers automatic recovery.
- **FR-029**: If TensorRT/GPU inference fails to initialise at startup, the system MUST log a fatal
  error (`[SYSTEM] FATAL — TensorRT inference failed to initialise`) and exit immediately; it MUST
  NOT enter the main loop.
- **FR-030**: The system MUST track consecutive startup failures using a persistent counter (e.g., a
  small state file on the Jetson filesystem). If the failure count exceeds a configurable
  `max_boot_failures` threshold (default: 3), the system MUST trigger a Jetson OS reboot via a
  system command before Docker attempts the next restart. The counter MUST reset to zero upon a
  successful startup.
- **FR-031**: The system MUST track the turret's cumulative step position for both pan and tilt axes
  using `POS` messages received from the Arduino. Two configurable thresholds MUST be defined per
  axis: `limit_warn_steps` (enter graduated deceleration zone) and `limit_hard_steps` (zero
  velocity). As the position approaches `limit_warn_steps`, outbound velocity commands MUST be
  tapered proportionally to zero; the HUD overlay MUST display a `[TURRET] Approaching limit`
  warning and a structured log entry MUST be emitted. The Arduino's physical limit switches serve
  as an independent hardware safety net and are not a substitute for Jetson-side tapering.

**Configuration**

- **FR-028**: ALL tunable parameters (PID gains, thresholds, serial port, camera resolution, model
  path, confidence, dead-zone, timeouts, threat tier boundaries, SEARCH arc width,
  `search_timeout`, telemetry log path, log rotation policy, MQTT broker URL, MQTT topic,
  web HUD port, Basic Auth username/password, `max_boot_failures`, `limit_warn_steps`,
  `limit_hard_steps`, `LRF_ENABLED`, `min_dwell_ms` per FSM state,
  `scan_pan_min`, `scan_pan_max`, `scan_velocity`, `scan_tilt_home`) MUST be centralised in `config.py` and/or `config.yaml`;
  no magic numbers in logic modules.

### Key Entities

- **Frame**: A single captured thermal image; carries a timestamp and raw pixel buffer.
- **Detection**: A single model output for one person in a frame; carries bounding box, confidence,
  and centroid coordinates.
- **TrackedTarget**: A detection enriched with a persistent tracking ID (resets to zero on each
  container restart), velocity vector, and disappearance counter. The associated `session_id`
  from the enclosing TelemetryRecord enables cross-restart correlation.
- **ThreatAssessment**: The scored evaluation of a TrackedTarget; carries threat score (0–100), tier
  classification, and recommended FSM action.
- **TurretCommand**: A velocity instruction (pan speed, tilt speed) sent to the Arduino.
- **LRFReading**: A distance measurement (metres) received from the Arduino in response to an `L`
  command. `null` when `LRF_ENABLED` is `false` or the reading is invalid.
- **TelemetryRecord**: A time-stamped record associating a TrackedTarget with its ThreatAssessment,
  LRFReading, and computed GPS estimate. Published to both the local JSON-lines rotating log file
  and the configured MQTT broker topic. Fields: `session_id`, `target_id`, `threat_score`, `tier`,
  `lat`, `lon`, `lrf_distance_m`, `pan_angle`, `tilt_angle`, `timestamp_utc`.
- **FSMState**: The current operating mode of the system (SCAN / TRACK / ACQUIRE / SEARCH).

## Assumptions

- The sentry's own GPS position is provided externally (fixed config or a connected GPS module) and
  is not dynamically acquired by this codebase.
- The Arduino firmware is developed and maintained separately; this spec covers only the Jetson-side
  serial protocol client.
- The thermal camera outputs raw YUYV video; colour/RGB conversion is handled in the pipeline.
- Network bandwidth on the farm LAN is sufficient to sustain a 480×320 MJPEG stream at 15 FPS to
  one concurrent viewer.
- Docker and NVIDIA container runtime (JetPack 6) are pre-installed on the Jetson; this spec does
  not cover OS or JetPack setup.
- The YOLOv8n TensorRT engine file is pre-converted and available at the path specified in config.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The main detection-to-command loop completes at ≥ 20 iterations per second under normal
  operating conditions with a single target in frame.
- **SC-002**: End-to-end latency from camera frame capture to serial velocity command dispatch does
  not exceed 100 ms under normal operating load.
- **SC-003**: A person who steps out of frame and returns within the configured `max_disappeared`
  threshold is re-identified with the same tracking ID in ≥ 95 % of test trials.
- **SC-004**: GPS position estimates for targets within 500 m of the sentry are accurate to ± 10 m
  when the LRF and turret angle readings are accurate.
- **SC-005**: After a camera or serial cable is reconnected, the system resumes full operation
  automatically within 5 seconds — no operator action required.
- **SC-006**: The web HUD stream delivers ≥ 15 FPS to a connected browser client without causing the
  main loop to drop below the 20 Hz target.
- **SC-007**: The system runs continuously for ≥ 72 hours in a simulated environment (looped test
  video + mock serial port) without crashing, memory leak, or degraded throughput. FPS MUST NOT
  drop below 18 Hz at any point during the run (10% floor below the 20 Hz target). Python heap
  growth MUST NOT exceed 50 MB over the full 72-hour run (measured via `tracemalloc`).
- **SC-008**: All tunable parameters can be changed by editing a single config file and restarting the
  container — no code changes required.

