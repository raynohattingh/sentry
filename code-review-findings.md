# Sentry Codebase Review Findings

**Date:** 2026-04-15
**Scope:** Full codebase — Jetson backend (Python), Arduino firmware (C++), Flutter app (Dart), infrastructure (Docker), tests

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 8 |
| HIGH | 17 |
| MEDIUM | 27 |
| LOW | 30 |
| **Total** | **82** |

The most dangerous cluster of issues is in the **Arduino firmware**: a NaN velocity injected via serial bypasses all limit switch protection, allowing the turret to physically drive past hardware stops. This is compounded by disabled TLS on MQTT, meaning an attacker on the network can inject the malicious command remotely.

---

## CRITICAL

### C-01 — NaN Velocity Bypasses All Limit Switch Gates
- **Category:** Security / Safety
- **Files:** `arduino/sentry_turret/src/serial_proto.cpp:30-43`, `arduino/sentry_turret/src/sentry_turret.ino:91-106`
- **Description:** `strtof()` parses `"nan"` and `"inf"` as valid floats from the serial protocol. In `applyLimitGates()`, the comparisons `velocity < 0.0f` and `velocity > 0.0f` both return `false` for NaN, so limit switches are **completely bypassed**. A turret receiving `V nan nan\n` will continue driving through hardware stops.
- **Fix:** Add `isnan()`/`isinf()` checks in `parseLine()` before storing velocity. Reject the command and zero both axes.

### C-02 — TLS Certificate Verification Disabled on All MQTT Connections
- **Category:** Security
- **Files:** `jetson/src/comms/mqtt.py:130-132` (publisher), `jetson/src/comms/mqtt.py:237-239` (subscriber)
- **Description:** `cert_reqs=ssl.CERT_NONE` + `tls_insecure_set(True)` on both publisher and subscriber. An attacker on the network can MITM the connection to exfiltrate target GPS coordinates or **inject turret movement commands** via the command topic. Combined with C-01, this is a remote code-to-physical-harm path.
- **Fix:** Use `ssl.CERT_REQUIRED` with a pinned CA certificate. Gate insecure mode behind an explicit env var that logs a loud warning.

### C-03 — Double Heading Offset Corrupts All Target GPS Coordinates
- **Category:** Logic error
- **Files:** `jetson/src/control/geo.py:102` (`pan_tilt_to_azimuth` adds `heading_offset_deg`), `jetson/src/control/geo.py:132` (`compute_target_gps` adds `SENTRY_HEADING_DEG` again)
- **Description:** When `recorder.py` calls `pan_tilt_to_azimuth(heading_offset_deg=config.SENTRY_HEADING_DEG)` and then passes the result to `compute_target_gps()`, the heading offset is applied **twice**. For a heading of 90 degrees, every target GPS coordinate is rotated an extra 90 degrees from truth.
- **Fix:** Remove the `+ config.SENTRY_HEADING_DEG` on line 132 of `compute_target_gps`, since the caller already applies it.

### C-04 — Default HUD Password Is "changeme"
- **Category:** Security (CWE-798)
- **Files:** `jetson/src/config.py:183`, `jetson/docker/docker-compose.yaml:41`, `jetson/src/web/streamer.py:55`
- **Description:** `HUD_PASSWORD` defaults to `"changeme"`. The docker-compose file also hardcodes it. Any unit deployed without overriding this env var has its web HUD accessible with a well-known password. The password is also documented in `utils/config.yaml`.
- **Fix:** Refuse to start (or log a critical-level warning every 10s) if the default password is in use. Remove hardcoded credentials from docker-compose; use `.env` files or Docker secrets.

### C-05 — MJPEG Viewer Sends Credentials Over Plaintext HTTP
- **Category:** Security
- **Files:** `app/lib/features/video/mjpeg_viewer.dart:55`
- **Description:** The video stream URI is hardcoded to `http://` (not HTTPS). Basic Auth credentials (username + password) are sent in the clear. Any network observer can intercept them.
- **Fix:** Use HTTPS, or at minimum make the scheme configurable and warn the user when using HTTP.

### C-06 — Background Monitoring Service Silently Swallows All Errors
- **Category:** Edge case
- **Files:** `app/lib/main.dart:88`
- **Description:** `catch (_) {}` wraps the entire background MQTT pipeline. If connection, config, or notification fails, the operator sees zero feedback. The app appears to be monitoring but is actually dead. For a threat-monitoring application, silent failure is especially dangerous.
- **Fix:** Log the error, surface a persistent notification or badge indicating background monitoring is down.

### C-07 — `os.system("sudo reboot")` Shell Injection Vector
- **Category:** Security
- **Files:** `jetson/src/main.py:70`
- **Description:** `os.system()` invokes a shell. While no injection vector exists today, this pattern is one config change away from being exploitable. `subprocess.run(["sudo", "reboot"])` is the safe equivalent.
- **Fix:** Replace with `subprocess.run(["sudo", "reboot"], check=False)`.

### C-08 — `micros()` Wrap-Around Stalls Steppers After ~70 Minutes
- **Category:** Logic error
- **Files:** `arduino/sentry_turret/src/stepper.cpp:74`
- **Description:** `if (now < axis.nextStepTimeUs) return;` fails when `micros()` overflows its 32-bit unsigned range (~70 min). After overflow, `now` wraps to near-zero and is always less than `nextStepTimeUs`, so no steps are emitted for up to 70 minutes. The turret freezes.
- **Fix:** Use unsigned subtraction: `if ((now - axis.lastStepTimeUs) < axis.stepIntervalUs) return;`.

---

## HIGH

### H-01 — Deadlock in `ArduinoLink._reconnect()`
- **Category:** Logic error
- **Files:** `jetson/src/hardware/arduino_link.py:185-203` (called from `send_velocity` at line 148 which holds `self._lock`; `_reconnect` attempts `with self._lock:` at line 197)
- **Description:** `threading.Lock` is not reentrant. `send_velocity()` holds `self._lock`, then calls `_reconnect()`, which tries to acquire the same lock. This deadlocks the control thread permanently.
- **Fix:** Use `threading.RLock`, or restructure so `_reconnect` does not re-acquire the lock.

### H-02 — No Velocity Bounds on MQTT Commands to Serial Output
- **Category:** Security / Safety
- **Files:** `jetson/src/comms/mqtt.py:275-276`, `jetson/src/hardware/arduino_link.py:143`
- **Description:** `pan_velocity`/`tilt_velocity` from MQTT pass `isinstance(x, (int, float))` checks but accept `float('inf')`, `float('nan')`, and extreme magnitudes (e.g., `1e308`). These propagate through `ArduinoLink.send_velocity()` to the serial port as `V inf inf\n` or `V nan nan\n`, triggering C-01.
- **Fix:** Reject non-finite values (`math.isfinite()`) and clamp to `[-MAX_VELOCITY, MAX_VELOCITY]` at the MQTT command handler.

### H-03 — Unprotected Subsystem Init Bypasses Boot-Failure Counter
- **Category:** Edge case
- **Files:** `jetson/src/main.py:117-148`
- **Description:** Vision init failures correctly increment the boot failure counter. But `SentryBrain`, `ThreatScorer`, `ArduinoLink`, `TurretManager`, and PID init are completely unprotected. If any raise, the process crashes without incrementing the counter, defeating the FR-030 resilience mechanism.
- **Fix:** Wrap the remaining init blocks in the same try/except pattern used for vision.

### H-04 — `send_enable()` Missing Lock — Concurrent Serial Writes
- **Category:** Logic error
- **Files:** `jetson/src/hardware/arduino_link.py:167-173`
- **Description:** `send_enable()` writes to the serial port without acquiring `self._lock`. If `send_velocity()` (which holds the lock) runs concurrently, bytes interleave on the wire (e.g., `V 10E 1\n0.00 50.00\n`).
- **Fix:** Acquire `self._lock` in `send_enable()`.

### H-05 — `detector.detect()` Has No Exception Handling
- **Category:** Edge case
- **Files:** `jetson/src/vision/detector.py:74-79`
- **Description:** `self.model.predict()` is unprotected. A corrupted frame, wrong dtype, or TensorRT fault raises an unhandled exception that crashes the entire main loop.
- **Fix:** Wrap in try/except, return empty list, log the error.

### H-06 — Greedy Centroid Matching Causes Target ID Flickering
- **Category:** Logic error
- **Files:** `jetson/src/vision/tracker.py:143-145`
- **Description:** The tracker uses a greedy (sort-by-min-distance) assignment instead of an optimal one. When a column is already claimed, the current row gets no match and is marked as disappeared — even if another unmatched column is within `max_distance`. Under dense clustering, target IDs flicker between active and disappeared.
- **Fix:** Use the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`).

### H-07 — `lrf_reading.distance_m` Falsiness Rejects Valid `0.0` Readings
- **Category:** Logic error
- **Files:** `jetson/src/telemetry/recorder.py:134`
- **Description:** `lrf_reading.distance_m` is falsy when the distance is `0.0` (valid point-blank measurement). GPS computation and velocity conversion are skipped.
- **Fix:** Change to `lrf_reading.distance_m is not None`.

### H-08 — Buffer Size Mismatch in Serial Protocol
- **Category:** Logic error
- **Files:** `arduino/sentry_turret/src/serial_proto.h:37` (hardcoded `char buf[64]`), `arduino/sentry_turret/src/config.h:37` (`SERIAL_LINE_BUF_LEN`)
- **Description:** The buffer is `char buf[64]` but the overflow check uses `SERIAL_LINE_BUF_LEN`. If `SERIAL_LINE_BUF_LEN` is increased above 64, the check passes but the buffer overflows.
- **Fix:** Change to `char buf[SERIAL_LINE_BUF_LEN]`.

### H-09 — Unclamped Step Interval on Very Small Velocities
- **Category:** Logic error
- **Files:** `arduino/sentry_turret/src/stepper.cpp:59-60`
- **Description:** `VELOCITY_SCALE_FACTOR / fabsf(velocity)` for tiny velocities produces enormous intervals (up to `ULONG_MAX`). The float-to-`unsigned long` cast is undefined behavior past 2^32. No upper clamp on `stepIntervalUs`.
- **Fix:** Add a maximum interval clamp (e.g., if interval > threshold, treat as stopped: set `stepIntervalUs = 0`).

### H-10 — `SentryBrain` Returns Zero Velocity in TRACK/ACQUIRE States
- **Category:** Logic error
- **Files:** `jetson/src/control/sentry_brain.py:280-290`
- **Description:** In TRACK and ACQUIRE — the most critical operational states — `_compute_velocities` returns `(0.0, 0.0, fire_lrf)`. The PID controllers owned by `SentryBrain` are never called. The comment says "main.py will compute error," meaning the FSM is not the sole authority for velocity. This creates a dual-authority conflict with `TurretManager.track()`.
- **Fix:** Decide on a single owner for PID velocity computation. Either `SentryBrain.update()` computes velocities using its PIDs, or remove the dead PID controllers from SentryBrain.

### H-11 — Dual PID Controller Ownership
- **Category:** Logic error
- **Files:** `jetson/src/control/sentry_brain.py:85-92`, `jetson/src/control/turret_manager.py:20-25`
- **Description:** Two independent PID controller pairs exist. If both are active, they issue conflicting velocity commands. The `TurretManager` pair uses default `max_integral` (500.0) while `SentryBrain` uses `config.PID_MAX_INTEGRAL` — a maintenance hazard.
- **Fix:** Consolidate to a single PID pair in one component.

### H-12 — `assert` Used for Safety Validation in Production
- **Category:** Logic error
- **Files:** `jetson/src/control/turret_manager.py:107-110`
- **Description:** `assert` validates soft bounds are not None. Running with `python -O` strips asserts, and `None` values silently pass through to `_bound_axis`, causing a `TypeError`.
- **Fix:** Replace with explicit `if ... raise ValueError(...)`.

### H-13 — Camera `stop()` Doesn't Join Background Thread
- **Category:** Edge case
- **Files:** `jetson/src/vision/camera.py:171-176`
- **Description:** `stop()` sets `_running = False` and immediately releases the capture device. The background thread may still be in `self._cap.read()`, causing a segfault or OpenCV exception.
- **Fix:** Join the thread after setting `_running = False`, before releasing the capture.

### H-14 — No Dead-Man's Switch on Override Joystick
- **Category:** Safety / Edge case
- **Files:** `app/lib/features/override/override_screen.dart:111-119`
- **Description:** The manual override joystick publishes velocity at 100ms intervals indefinitely. If the phone is set down with the joystick deflected, the turret continues moving. No automatic timeout stops publishing after a period of no user interaction.
- **Fix:** Add a timeout (e.g., 2s of no touch events) that auto-centers the joystick and sends a stop command.

### H-15 — Docker Image Runs as Root with `privileged: true`
- **Category:** Security
- **Files:** `jetson/docker/docker-compose.yaml:20`, `jetson/docker/Dockerfile` (no `USER` directive)
- **Description:** `privileged: true` grants full kernel access. Combined with a Flask RCE, an attacker gets full host root. Use `--device` passthrough (already present) and drop `privileged`.
- **Fix:** Remove `privileged: true`. Add a non-root `USER` in the Dockerfile. Use `--cap-add` for specific capabilities.

### H-16 — Unpinned Docker Base Image Tag
- **Category:** Security
- **Files:** `jetson/docker/Dockerfile:3`
- **Description:** `FROM ultralytics/ultralytics:latest-jetson-jetpack6` uses `:latest`. A malicious or broken upstream push silently changes the build.
- **Fix:** Pin to a specific digest: `@sha256:...`.

### H-17 — `sessionId.substring(0, 8)` Crash on Short IDs
- **Category:** Logic error
- **Files:** `app/lib/features/alerts/alert_panel.dart:228`
- **Description:** Throws `RangeError` if `sessionId` is shorter than 8 characters.
- **Fix:** Use `sessionId.substring(0, min(8, sessionId.length))`.

---

## MEDIUM

### M-01 — MQTT Client Leak on Reconnection
- **Files:** `jetson/src/comms/mqtt.py:134-135`
- **Description:** A new `mqtt.Client()` is created on every reconnect, but the old client's `loop_start()` thread is never stopped. Leaks threads and sockets.

### M-02 — MQTT Drain Busy-Loop When Broker Is Down
- **Files:** `jetson/src/comms/mqtt.py:145-152`
- **Description:** Failed publishes are re-enqueued with `put_nowait`, then immediately dequeued on the next iteration. CPU-burning hot loop with only 0.5s sleep.

### M-03 — Incomplete Resource Cleanup on Shutdown
- **Files:** `jetson/src/main.py:300-305`
- **Description:** Only `link.stop()` and `camera.stop()` are called. `mqtt_pub`, `status_pub`, `recorder` are never shut down. Open file handles, MQTT threads, and pending publishes are abandoned.

### M-04 — Target Selection by Area Instead of Threat Score
- **Files:** `jetson/src/main.py:213`
- **Description:** PID tracking targets the largest bounding box (`max(area)`), but threat assessment targets the highest score. The turret may physically track a large, low-threat target while ignoring a small, high-threat one.

### M-05 — PID Uses `time.time()` Instead of `time.monotonic()`
- **Files:** `jetson/src/control/pid.py:54, 66-67`
- **Description:** NTP clock adjustments can cause `dt` to go negative (caught, returns 0) or spike massively (uncaught, causes integral windup and erratic velocity).

### M-06 — PID Derivative Term Has No Filter
- **Files:** `jetson/src/control/pid.py:83`
- **Description:** When `dt` is very small but positive, `delta_error / dt` produces an enormous derivative spike. No low-pass filter or D-term clamp exists.

### M-07 — SEARCH State Timer Uninitialized on Direct Entry
- **Files:** `jetson/src/control/sentry_brain.py:196-204`
- **Description:** `_search_entered_s` defaults to `0.0`. If FSM starts in SEARCH state, `time.monotonic() - 0.0` is huge, causing immediate transition to SCAN instead of searching.

### M-08 — LOW-Tier Target Triggers Exit from SEARCH to SCAN
- **Files:** `jetson/src/control/sentry_brain.py:226-227`, `jetson/src/control/threat_tracker.py:152`
- **Description:** A visible LOW-tier target recommends SCAN. If the FSM is in SEARCH, it exits to SCAN — ignoring the target entirely rather than monitoring it.

### M-09 — Velocity Taper Applies in Both Directions
- **Files:** `jetson/src/control/sentry_brain.py:334-366`
- **Description:** `taper_velocity` reduces speed even when the turret is moving *away* from a limit. The turret moves slowly when retreating from the edge, getting "stuck" in the taper zone.

### M-10 — `TurretManager.track()` Uses Untyped `dict` Parameter
- **Files:** `jetson/src/control/turret_manager.py:144-164`
- **Description:** `target_data["cx"]` — a `KeyError` at runtime if the dict is malformed. Inconsistent with the rest of the codebase which uses typed dataclasses.

### M-11 — Threat Score Weights Not Validated to Sum to 1.0
- **Files:** `jetson/src/config.py:70-73`
- **Description:** `W_DISTANCE + W_MOTION + W_GROUPING + W_TIME_OF_DAY = 1.0` currently, but there is no runtime assertion. Changing one weight without adjusting others silently mis-scales scores.

### M-12 — Time-of-Day Score Uses UTC Instead of Local Time
- **Files:** `jetson/src/control/threat_tracker.py:129`
- **Description:** `utcnow().hour` determines night/day. For a sentry in UTC+2, the night window is shifted by 2 hours, making the score incorrect for local conditions.

### M-13 — Serial Port Regex Accepts Invalid Axis/Direction Pairings
- **Files:** `jetson/src/comms/serial_io.py:59-60`
- **Description:** The regex accepts `LIMIT PAN UP` and `LIMIT TILT LEFT` — physically impossible combinations. These produce invalid `switch_key` values that pollute `_validated_switches` without matching `required_switch_keys()`.

### M-14 — `SerialPort.write()` Silently Drops Data When Disconnected
- **Files:** `jetson/src/comms/serial_io.py:161-168`
- **Description:** If `self._serial` is None, the write is silently discarded. The caller (e.g., `send_enable()` during connect) has no way to know the command was lost.

### M-15 — Unhandled Main Loop Exceptions Kill the Process
- **Files:** `jetson/src/main.py:186-298`
- **Description:** Only `KeyboardInterrupt` is caught. A TensorRT fault, serial error, or numpy shape mismatch crashes the process with no boot-failure increment, no telemetry flush, and incomplete hardware cleanup.

### M-16 — `ArduinoLink.is_heartbeat_alive()` Returns True When No POS Ever Received
- **Files:** `jetson/src/hardware/arduino_link.py:216-219`
- **Description:** Returns `True` when `_last_pos_received_ns == 0` (startup). If the Arduino is dead, this returns True forever, masking the failure. Needs a startup grace period.

### M-17 — `_convert_velocity` Can Produce Infinity, Breaking JSON Serialization
- **Files:** `jetson/src/telemetry/recorder.py:49-52, 169`
- **Description:** Large `lrf_m * v_px_frame` values can overflow to `inf`. `json.dumps()` raises `ValueError` on `Infinity`/`NaN`, crashing `emit()`. The try/except only covers MQTT publish, not JSON serialization.

### M-18 — MVP Profile Has No Software Motion Backstop
- **Files:** `jetson/src/control/turret_manager.py:94-125`
- **Description:** For `HousingProfile.MVP`, `apply_motion_bounds` returns velocities unchanged, relying entirely on hardware limit switches. A stuck or disconnected limit switch means zero protection.

### M-19 — Web Streamer Has No Connection Limit
- **Files:** `jetson/src/web/streamer.py:93-119`
- **Description:** `generate()` is an infinite generator with no client disconnect detection. Each connected client spawns a long-lived thread. No limit on concurrent connections — trivial DoS.

### M-20 — Flask Development Server Used in Production
- **Files:** `jetson/src/web/streamer.py:173`
- **Description:** `app.run()` is Flask's built-in development server. No request timeouts, no connection limits, no security hardening.

### M-21 — Web HUD Binds to `0.0.0.0` by Default
- **Files:** `jetson/src/web/streamer.py:163`
- **Description:** Exposes the HUD to all network interfaces, including untrusted networks. Combined with C-04 (default password) and M-20 (dev server), this is a significant attack surface.

### M-22 — MQTT Port Mismatch Between Docker Compose and Config
- **Files:** `jetson/docker/docker-compose.yaml:37` (`1883` plaintext), `jetson/src/config.py:168` (default `8883` TLS)
- **Description:** Docker compose sets `MQTT_PORT=1883` (plaintext) but the code always enables TLS. TLS client to plaintext port = cryptic SSL handshake failure.

### M-23 — paho-mqtt v2 API Incompatibility
- **Files:** `jetson/src/comms/mqtt.py:125, 232`, `test/mqtt_sim.py:129`
- **Description:** `mqtt.Client()` uses the v1 API, but `requirements.txt` specifies `paho-mqtt>=2.0`. In v2, the constructor requires `CallbackAPIVersion` as the first argument. This will raise `TypeError` at runtime.

### M-24 — MQTT Command Handler Does Not Validate `sentry_id`
- **Files:** `app/lib/services/mqtt_service.dart:127-145`
- **Description:** Incoming telemetry/status messages are rendered regardless of their `sentry_id`. An attacker on the broker can inject telemetry for any device, and the operator's map will render it.

### M-25 — Override Screen Stop Command Is Unreliable
- **Files:** `app/lib/features/override/override_screen.dart:64-69`
- **Description:** `ref.read()` in `dispose()` is unsafe after deactivation. If MQTT lost connection during screen lifetime, the stop command is silently dropped. Turret continues moving after operator leaves the screen.

### M-26 — `copyWith()` Cannot Set Nullable Fields Back to Null
- **Files:** `app/lib/models/sentry_config.dart:37-66`
- **Description:** `sentryLat: sentryLat ?? this.sentryLat` means passing `null` keeps the old value. Operator cannot clear sentry GPS calibration through the UI.

### M-27 — Limit Switch Release Has No Debounce
- **Files:** `arduino/sentry_turret/src/limit_switch.cpp:48-54`
- **Description:** TRIGGERED -> IDLE transition happens on a single HIGH sample. Mechanical bounce on release can briefly clear the flag, allowing one step into the limit before re-triggering.

---

## LOW

### L-01 — `SafetyStatus` Mutable List in Frozen Dataclass
- **Files:** `jetson/src/sentry_types.py:292-293`
- **Description:** `validated_switches: list[str]` is mutable despite `frozen=True`. Callers can `.append()` to a "frozen" safety object.

### L-02 — `Frame` Width/Height Can Disagree with `data.shape`
- **Files:** `jetson/src/sentry_types.py:98-112`
- **Description:** Default width=480, height=320 are never validated against `data.shape`. If the camera returns a different resolution, metadata disagrees with pixels.

### L-03 — `TelemetryRecord` Uses Weak Typing
- **Files:** `jetson/src/sentry_types.py:334, 339, 341`
- **Description:** `tier: str` instead of `ThreatTier`, `fsm_state: str` instead of `FSMState`, `velocity_vector: dict | None` instead of a typed dict.

### L-04 — `FSMState.MANUAL_OVERRIDE` Not Documented in Docstring
- **Files:** `jetson/src/sentry_types.py:34-48`

### L-05 — `HousingProfile.from_raw()` Silently Defaults on Invalid Input
- **Files:** `jetson/src/sentry_types.py:58-64`
- **Description:** Invalid strings silently become `MVP` with no warning.

### L-06 — `SENTRY_ID` Bare `KeyError` on Missing Env Var
- **Files:** `jetson/src/config.py:174`
- **Description:** Every other env var uses `.get()` with a default. This one crashes at import with an unhelpful traceback.

### L-07 — Env Var Parsing Has No Error Handling
- **Files:** `jetson/src/config.py:45-46, 168, 175-176`
- **Description:** `int(os.environ.get(...))` raises `ValueError` on non-numeric strings (e.g., `CAMERA_FPS=auto`).

### L-08 — `STEPS_PER_DEGREE` Division by Zero
- **Files:** `jetson/src/control/geo.py:82, 102-103`
- **Description:** If misconfigured to 0.0, causes `ZeroDivisionError` in the control loop.

### L-09 — Module-Level Lat/Lon Warning Fires at Import Time
- **Files:** `jetson/src/control/geo.py:21-26`
- **Description:** Checks `(0.0, 0.0)` on import. Stale if config is later overridden. Also, `(0.0, 0.0)` is a valid coordinate.

### L-10 — `math.asin` Domain Error at Extreme Distances
- **Files:** `jetson/src/control/geo.py:60-68`
- **Description:** Floating-point rounding can push the argument past [-1, 1]. Add `max(-1, min(1, ...))` clamp.

### L-11 — Haversine Does Not Normalize Output Longitude
- **Files:** `jetson/src/control/geo.py:70`
- **Description:** Near the antimeridian, output longitude can exceed [-180, 180].

### L-12 — `datetime.datetime.utcnow()` Deprecated (Project-Wide)
- **Files:** `main.py:81`, `camera.py:133`, `tracker.py:92,158,209`, `recorder.py:122`, `sentry_brain.py:148,176`, `threat_tracker.py:129`, `serial_io.py:47`, `arduino_link.py:55,199`
- **Description:** Deprecated since Python 3.12. Use `datetime.datetime.now(datetime.timezone.utc)`.

### L-13 — `list.pop(0)` Used as Ring Buffer
- **Files:** `jetson/src/main.py:285-287`
- **Description:** O(n) per pop. Use `collections.deque(maxlen=100)`.

### L-14 — `Union[...]` vs `X | Y` Syntax Inconsistency
- **Files:** `jetson/src/hardware/arduino_link.py:21, 113`

### L-15 — `MANUAL_OVERRIDE` Missing from `_STATE_ORDER`
- **Files:** `jetson/src/control/sentry_brain.py:44-49`
- **Description:** Indexing with `MANUAL_OVERRIDE` would raise `KeyError`.

### L-16 — Scan Sweep Oscillation at Exact Boundary
- **Files:** `jetson/src/control/sentry_brain.py:294-308`
- **Description:** If position exactly equals boundary and velocity is zero, direction flips every tick.

### L-17 — PID First Output After Reset Is Always Zero
- **Files:** `jetson/src/control/pid.py:95-103`
- **Description:** `reset()` sets `_last_time = time.time()`. Immediate `update()` gets `dt ~ 0`, returns 0.0.

### L-18 — Camera Uses `SERIAL_RETRY_INTERVAL_S` for Reconnection
- **Files:** `jetson/src/vision/camera.py:127`
- **Description:** Misnamed constant. Should have a dedicated `CAMERA_RETRY_INTERVAL_S`.

### L-19 — Camera V4L2 Fallback Ignores `cap.set()` Return Values
- **Files:** `jetson/src/vision/camera.py:90`

### L-20 — Tracker `_next_id` Is Unbounded
- **Files:** `jetson/src/vision/tracker.py:59`
- **Description:** Not a crash risk in Python, but could overflow if serialized to a fixed-width field.

### L-21 — Velocity Computed as t-2 to t Instead of t-1 to t
- **Files:** `jetson/src/vision/tracker.py:160-162`
- **Description:** `_prev_centroids` update order causes velocity to span two frames instead of one.

### L-22 — Web Streamer Uses Global State Instead of Class
- **Files:** `jetson/src/web/streamer.py:38-46`

### L-23 — Unnecessary `global` in `generate()`
- **Files:** `jetson/src/web/streamer.py:99`

### L-24 — No Security Headers on HUD HTML
- **Files:** `jetson/src/web/streamer.py:127-147`
- **Description:** Missing `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`.

### L-25 — Timing Side-Channel in Password Comparison
- **Files:** `jetson/src/web/streamer.py:55`
- **Description:** `==` comparison is vulnerable to timing attacks. Use `hmac.compare_digest()`.

### L-26 — Stepper Pulse Width Not Guaranteed
- **Files:** `arduino/sentry_turret/src/stepper.cpp:80-81`
- **Description:** Two `digitalWrite` calls with no delay. LTO/O2 could optimize to <1us, below A4988 minimum pulse width.

### L-27 — `LRF_READ_TIMEOUT_MS` Type Is `uint8_t` but Documented Range Is 50-500
- **Files:** `arduino/sentry_turret/src/config.h:161`

### L-28 — LRF Power-On Settling Time Not Accounted For
- **Files:** `arduino/sentry_turret/src/lrf.cpp:87-96`
- **Description:** Trigger frame sent immediately after power-on. Module may not be ready.

### L-29 — Stepper Timing Drift (Absolute vs Relative Scheduling)
- **Files:** `arduino/sentry_turret/src/stepper.cpp:77`
- **Description:** `nextStepTimeUs = now + interval` instead of `nextStepTimeUs += interval` causes cumulative drift.

### L-30 — Limit Switches Are Normally-Open (Hardware Design)
- **Files:** `arduino/sentry_turret/src/config.h:79`
- **Description:** A broken wire is electrically indistinguishable from "not pressed". NC switches would be fail-safe.

---

## Test Coverage Gaps

| Module | Gap | Severity |
|--------|-----|----------|
| `main.py` | **Zero tests.** Boot-failure counter, main loop, shutdown untested. | HIGH |
| `MQTTPublisher` | **Zero tests.** Connection, reconnection, queue overflow untested. | HIGH |
| `control/geo.py` | `bearing_from_pan()`, `pan_tilt_to_azimuth()` untested. Double-offset bug (C-03) exists because composition is untested. | HIGH |
| `SentryBrain` velocities | `_scan_sweep()`, `_search_arc()`, `taper_velocity()`, `_compute_velocities()` all untested. | MEDIUM |
| `web/streamer.py` | `generate()`, `update_stream_frame()`, `start_web_server()` untested. Only auth + status codes covered. | MEDIUM |
| `ArduinoLink` | `connect()`, `_reconnect()`, `is_heartbeat_alive()`, `send_enable()`, `_read_loop` untested. | MEDIUM |
| `CommandSubscriber` watchdog | Test re-implements logic inline instead of exercising real code. | MEDIUM |
| Threat scoring tests | Assertions guarded by `if` — pass vacuously when condition is false. | MEDIUM |
| PID tests | Use `time.sleep()` for dt — flaky under CI load. Should mock clock. | LOW |
| `TurretManager.track()` | Zero tests. | LOW |

---

## Test Quality Issues

| Issue | File | Description |
|-------|------|-------------|
| Config mutation without cleanup | `test_geo.py:59-65`, `test_web_stream.py:22-24` | Direct mutation of `config.*` globals. Use `monkeypatch.setattr()`. |
| Flaky sleep-based timing | `test_camera.py:27-28`, `test_pid.py:21+` | `time.sleep()` for synchronization. Use polling or mock clocks. |
| Test dependencies in prod image | `requirements.txt:5-6` | `pytest` and `pytest-mock` baked into production Docker image. |
