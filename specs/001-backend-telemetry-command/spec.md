# Feature Specification: Backend Telemetry Extensions & Manual Override Subscriber

**Feature Branch**: `001-backend-telemetry-command`
**Created**: 2026-02-27
**Status**: Draft
**Counterpart**: `specs/001-sentry-mobile-app/spec.md` (FR-010a, FR-022a)

---

## Clarifications

### Session 2026-02-27

- Q: Should `velocity_vector` be published as pixels/frame (raw camera) or metres/second? → A: The backend MUST convert pixels/frame to m/s before publishing. The receiving device is responsible for rendering the velocity vector on its display. This ensures device-independence regardless of camera resolution or frame rate.
- Q: Should TLS + credentials be enforced for the CommandSubscriber and/or the existing MQTTPublisher? → A: TLS + username/password MUST be added to BOTH `CommandSubscriber` AND `MQTTPublisher`. Both components must connect to the broker on the TLS port (8883) with authenticated credentials — consistent with the mobile app's security requirements.
- Q: When in MANUAL_OVERRIDE, does the vision/detection pipeline continue running or fully pause? → A: The detection pipeline (camera capture, detection, threat scoring, LRF) continues running during MANUAL_OVERRIDE. Only motor control is handed to the operator. On zero-velocity command or safety timeout, the FSM resumes tracking any currently-detected target immediately — no SCAN restart required.
- Q: Should `SENTRY_ID` be a required env var or have a default value? → A: Required env var — the process MUST raise an error on startup if `SENTRY_ID` is unset. No default is permitted. This prevents silent misconfiguration when multiple sentries share the same broker.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mobile App Receives Enriched Telemetry (Priority: P1)

The mobile operator opens the Farm Sentry app and sees each tracked threat represented
as an animated marker moving smoothly across the map. A "Sentry Mode" badge in the HUD
reflects the current FSM state (SCAN / TRACK / ACQUIRE / SEARCH) in real time. When the
sentry loses a target and enters SEARCH mode, the mobile app immediately fades the threat
dot — because the `fsm_state` field in the telemetry payload signals this transition.

**Why this priority**: Without `fsm_state` and `velocity_vector` in the telemetry
payload, the mobile app cannot animate marker movement or trigger the correct fade
behaviour. Every mobile user is affected on every telemetry tick.

**Independent Test**: Run the sentry against a test scene. Subscribe to
`sentry/telemetry` with any MQTT client. Confirm each message contains `fsm_state`
(one of SCAN/TRACK/ACQUIRE/SEARCH) and `velocity_vector` (`{vx, vy}` in m/s or `null`).
Transition the FSM to SEARCH by removing the target — confirm the next payload carries
`fsm_state: "SEARCH"`.

**Acceptance Scenarios**:

1. **Given** the sentry is actively tracking a target, **When** a telemetry record is
   published, **Then** the payload MUST include `fsm_state: "TRACK"` or `"ACQUIRE"` and
   a non-null `velocity_vector: {"vx": <float m/s>, "vy": <float m/s>}` representing
   the target's real-world velocity converted from the camera's pixels-per-frame
   measurement using LRF distance and frame rate.

2. **Given** the sentry has no active target (SCAN state), **When** a telemetry record
   is published, **Then** the payload MUST include `fsm_state: "SCAN"` and
   `velocity_vector: null`.

3. **Given** the sentry transitions to SEARCH (target lost), **When** the next telemetry
   record is published, **Then** `fsm_state` MUST equal `"SEARCH"`.

4. **Given** an existing MQTT client that does not read the new fields, **When** it
   receives the enriched payload, **Then** it MUST continue to function correctly — new
   fields are additive and do not break existing consumers.

---

### User Story 2 — Operator Takes Manual Turret Override (Priority: P1)

A farm operator on the mobile app suspects a threat has evaded detection. They open the
Manual Override screen and use the virtual joystick to sweep the turret to a specific
direction. The turret responds to each joystick movement in near-real-time. When they
release the joystick — or close the override screen — the turret stops immediately and
autonomous tracking resumes.

**Why this priority**: The manual override is a safety-critical feature. Without the
backend subscriber, the mobile app's joystick has zero physical effect. This is explicitly
flagged as a BLOCKING dependency for mobile US7.

**Independent Test**: With the sentry process running, publish a `sentry/command`
message to the MQTT broker. Observe the physical turret moving. Publish a zero-velocity
command — confirm turret stops and FSM resumes. Publish a command with a wrong
`sentry_id` — confirm turret does not move.

**Acceptance Scenarios**:

1. **Given** the sentry is running in any FSM state, **When** a valid `sentry/command`
   message arrives with non-zero velocities and the correct `sentry_id`, **Then** the
   turret MUST move at approximately the requested velocities within 200 ms of receipt.

2. **Given** the sentry is tracking a HIGH-threat target (ACQUIRE state), **When** a
   `sentry/command` arrives, **Then** only motor control MUST be suspended and handed
   to the operator — the detection pipeline (camera, detection, threat scoring, LRF)
   continues running silently. On override end, the FSM resumes tracking any
   currently-detected target immediately without restarting from SCAN.

3. **Given** the operator releases the joystick, **When** a zero-velocity
   `sentry/command` is received, **Then** the turret MUST stop and the FSM MUST
   resume autonomous operation.

4. **Given** a `sentry/command` arrives with a `sentry_id` that does not match the
   configured sentry, **When** the subscriber processes it, **Then** the command MUST
   be silently discarded and a warning logged.

5. **Given** the override is active and no `sentry/command` has been received for more
   than 3 seconds (network drop or app closed), **When** the safety timeout fires,
   **Then** the turret MUST issue a zero-velocity stop and autonomous FSM operation
   MUST resume.

6. **Given** the sentry is in override mode, **When** a burst of more than 20 commands
   arrives within 1 second, **Then** the subscriber MUST rate-limit to at most 20
   commands per second, discarding excess commands without error.

---

### Edge Cases

- What happens if MQTT delivers a duplicate `sentry/command` (QoS 1 re-delivery)?
  Velocity commands are absolute (not deltas), so re-execution is safe — idempotent.
- What if `velocity_vector` cannot be computed (first detection frame, or LRF
  unavailable)? Publish `velocity_vector: null` — the receiving device handles this
  gracefully (snap position, no animation).
- What if the sentry process restarts mid-override session? Override state is not
  persisted; on restart the FSM initialises in SCAN state (safe default).
- What if `pan_velocity` or `tilt_velocity` exceeds the hardware maximum? Values MUST be
  clamped to the hardware-safe range, not rejected, to ensure partial commands still work.
- What if the `sentry/command` payload is malformed JSON? Log a warning and discard —
  never crash the subscriber thread.

---

## Requirements *(mandatory)*

### Functional Requirements

#### FR-010a: Velocity Vector in Telemetry

- **FR-010a-1**: The `TelemetryRecord` data model MUST include a `velocity_vector` field
  containing the tracked target's real-world velocity as `{"vx": float, "vy": float}`
  in metres per second (m/s) when a target is actively tracked, or `null` when no
  target is present. The receiving device is responsible for rendering this on its
  display; units are device-independent by design.
- **FR-010a-2**: The telemetry publisher MUST derive `velocity_vector` from
  `TrackedTarget.velocity_vector` (pixels/frame) by converting to m/s using the
  current LRF distance measurement and the camera frame rate. If LRF distance is
  unavailable, publish `velocity_vector: null`.
- **FR-010a-3**: `velocity_vector` MUST be serialised to the MQTT payload as a JSON
  object or JSON `null` — never omitted — to maintain a consistent payload schema.

#### FR-010b: FSM State in Telemetry

- **FR-010b-1**: The `TelemetryRecord` data model MUST include an `fsm_state` field
  containing the current FSM state as one of the string literals:
  `"SCAN"`, `"TRACK"`, `"ACQUIRE"`, `"SEARCH"`, `"MANUAL_OVERRIDE"`.
- **FR-010b-2**: The telemetry publisher MUST populate `fsm_state` at the time each
  `TelemetryRecord` is created.
- **FR-010b-3**: `fsm_state` MUST be serialised to the MQTT payload as a JSON string and
  MUST NOT be omitted.

#### FR-022a: Manual Override MQTT Subscriber

- **FR-022a-1**: A new `CommandSubscriber` component MUST subscribe to the
  `sentry/command` MQTT topic using TLS (port 8883) and username/password credentials
  from config. This matches the security posture required by the mobile app.
- **FR-022a-1b**: The existing `MQTTPublisher` MUST be updated to connect via TLS
  (port 8883) with the same username/password credentials. The broker host, TLS port,
  username, and password MUST be sourced from config constants (`MQTT_PORT`,
  `MQTT_USERNAME`, `MQTT_PASSWORD`) — no hardcoded values permitted.
- **FR-022a-2**: On receipt of a `sentry/command` message, the subscriber MUST validate
  the `sentry_id` field against `config.SENTRY_ID`. `SENTRY_ID` is a **required**
  environment variable — the process MUST raise a startup error if it is unset (no
  default value). Mismatched IDs MUST be discarded with a warning log and no motor
  action taken.
- **FR-022a-3**: On receipt of a valid command, the subscriber MUST put the system into
  `MANUAL_OVERRIDE` mode, suspending only motor control for the duration of the override
  session. The detection pipeline (camera capture, target detection, threat scoring, LRF
  ranging) MUST continue running throughout the override. On override end, the FSM MUST
  resume tracking any currently-detected target immediately — no restart from SCAN.
- **FR-022a-4**: In `MANUAL_OVERRIDE` mode, `pan_velocity` and `tilt_velocity` from
  the command MUST be forwarded directly to the motor driver, clamped to the
  hardware-safe velocity range.
- **FR-022a-5**: The subscriber MUST implement a **3-second safety timeout**: if no
  `sentry/command` is received for 3 consecutive seconds while in `MANUAL_OVERRIDE`
  mode, a zero-velocity stop MUST be issued and the system MUST return to autonomous
  operation.
- **FR-022a-6**: The subscriber MUST rate-limit inbound commands to a maximum of 20
  per second; excess commands within a 50 ms window MUST be discarded silently.
- **FR-022a-7**: A zero-velocity command (`pan_velocity: 0.0`, `tilt_velocity: 0.0`)
  MUST immediately end the override session and return the system to autonomous
  operation, regardless of the safety timeout.
- **FR-022a-8**: The `CommandSubscriber` MUST run on a dedicated thread, independent
  of the FSM control loop.
- **FR-022a-9**: The existing `MQTTPublisher` MUST be updated for TLS and credentials
  (FR-022a-1b); all other `MQTTPublisher` behaviour remains unchanged. `CommandSubscriber`
  is implemented as a new, independent component.

### Key Entities

- **TelemetryRecord** (extended): Existing data model. Gains two new fields:
  `velocity_vector` (object with `vx`/`vy` in m/s, or null) and `fsm_state` (string).
  Both are included in every MQTT telemetry payload.
- **CommandSubscriber**: New component. Subscribes to `sentry/command`, validates
  `sentry_id`, manages override state and safety timeout, forwards clamped velocities
  to the motor driver.
- **ManualCommand**: Existing data model (`sentry_id`, `pan_velocity`, `tilt_velocity`,
  `timestamp_utc`). Used as the inbound command schema — no changes required.
- **FSMState** (extended): Gains a new `MANUAL_OVERRIDE` state value, visible in
  outbound telemetry and testable independently.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every `sentry/telemetry` MQTT message published after deployment includes
  both `fsm_state` and `velocity_vector` fields; validated across 1,000 consecutive
  messages with 100% compliance.
- **SC-002**: The turret responds to a `sentry/command` message within 200 ms of broker
  delivery under normal local-network operating conditions.
- **SC-003**: The safety timeout reliably stops the turret within 3.5 seconds (3 s
  timeout + 500 ms margin) of the last received command when the network drops.
- **SC-004**: The subscriber correctly discards 100% of commands with a non-matching
  `sentry_id` in a test batch of 50 commands (25 correct, 25 wrong IDs).
- **SC-005**: Autonomous tracking resumes within 500 ms of a zero-velocity command or
  safety-timeout stop.
- **SC-006**: The existing test suite passes without modification against the updated
  telemetry payload — backward compatibility confirmed.

---

## Assumptions

- `TrackedTarget.velocity_vector` (already a `tuple[float, float]` in `types.py`) is
  the raw pixels/frame source. The telemetry publisher converts this to m/s using
  `lrf_distance_m` and the camera frame rate (from config). If `lrf_distance_m` is
  `None`, `velocity_vector` is published as `null`.
- `config.SENTRY_ID` is a **required** environment variable added to `config.py` as
  part of this feature. The process MUST fail at startup with a clear error message
  if `SENTRY_ID` is unset — no default value permitted.
- `TurretManager.hardware.send_velocity(v_pan, v_tilt)` is the correct low-level call
  for both autonomous and manual velocities.
- Hardware-safe velocity bounds are `config.PAN_MAX` and `config.TILT_MAX`.
- `CommandSubscriber` and `MQTTPublisher` both connect to the broker via TLS (port 8883)
  using `MQTT_USERNAME` and `MQTT_PASSWORD` from config. New config constants
  `MQTT_USERNAME` and `MQTT_PASSWORD` must be added to `config.py`; `MQTT_PORT` default
  changes from 1883 to 8883.
- MQTT QoS 1 is used for `sentry/command` subscriptions (at-least-once delivery);
  idempotent velocity commands make this safe.
