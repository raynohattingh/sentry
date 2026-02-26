# Feature Specification: Farm Sentry Mobile App

**Feature Branch**: `001-sentry-mobile-app`
**Created**: 2026-02-26
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Tactical Map Home Screen (Priority: P1)

As a farm owner, I want to open the app and immediately see a live tactical map showing where my sentry is pointing and where any threats are located, so I can get situational awareness at a glance without navigating menus.

**Why this priority**: This is the core value proposition of the app. Without the map HUD, no other feature has context. It is the entry point to every other workflow.

**Independent Test**: Can be fully tested by launching the app with a live sentry broadcasting telemetry — the map must show the sentry position and update threat markers in real time. All other screens can be deferred.

**Acceptance Scenarios**:

1. **Given** the app is connected to the sentry, **When** the home screen opens, **Then** a map is displayed centred on the sentry's configured GPS position with a distinctive sentry marker
2. **Given** a threat is detected by the sentry, **When** telemetry with valid coordinates arrives, **Then** a threat marker appears at the correct map position within 2 seconds
3. **Given** a HIGH-tier threat is active, **When** it is displayed on the map, **Then** its marker is visually distinct from MED and LOW markers (different colour and/or icon)
4. **Given** multiple threats are tracked simultaneously, **When** they are rendered, **Then** each appears as a separate marker on the map
5. **Given** no threats are currently detected, **When** the sentry is in SCAN state, **Then** no threat markers are shown and the sentry marker indicates a scanning state
6. **Given** a tracked target disappears (sentry enters SEARCH state), **When** telemetry reflects this, **Then** the dot immediately begins fading and shows "Last Seen: <timestamp>"; the dot is fully removed after 30 seconds
7. **Given** a threat dot is visible on the map, **When** the user taps it, **Then** the dot is visually highlighted and the alert log panel scrolls to and highlights its matching entry; if the panel was collapsed it opens automatically

---

### User Story 2 — Background & Lockscreen Threat Alerts (Priority: P1)

As a farm owner, I want to be immediately alerted when the sentry detects a significant threat, even if my phone is locked or I am asleep, so I never miss a critical intrusion.

**Why this priority**: The entire purpose of a security system depends on reliable alerting. Without this, the app provides no protection advantage over not having a phone.

**Independent Test**: Can be fully tested by locking the phone and simulating a HIGH-tier MQTT telemetry message — the device must produce an audible alarm and a lockscreen notification.

**Acceptance Scenarios**:

1. **Given** the phone is locked, **When** a HIGH-tier detection arrives, **Then** the device produces an audible alarm that overrides silent mode and displays a lockscreen notification
2. **Given** a MED-tier detection arrives, **When** the app is in the background, **Then** a standard push notification is delivered with tier and location summary
3. **Given** a LOW-tier detection arrives in default settings, **When** received, **Then** no push notification is triggered; only the in-app alert log is updated
4. **Given** the user has configured a custom minimum score threshold, **When** a detection below that threshold arrives, **Then** no notification is triggered regardless of tier
5. **Given** the user has muted notifications for a specific tier, **When** a detection of that tier arrives, **Then** no notification is triggered for that tier

---

### User Story 3 — On-Demand Live Video Verification (Priority: P2)

As a farm owner, I want to pull up the sentry's thermal camera feed when I see a threat marker, so I can visually confirm whether it is a genuine threat before deciding how to respond.

**Why this priority**: Video is a critical verification tool but explicitly secondary to the map-centric MQTT telemetry flow. It must not consume bandwidth automatically.

**Independent Test**: Can be fully tested by tapping "View Feed" and verifying the MJPEG stream opens in a modal overlay while the map remains accessible upon dismissal.

**Acceptance Scenarios**:

1. **Given** the sentry is online, **When** the user explicitly taps the "View Feed" action, **Then** an MJPEG stream viewer opens as a modal overlay or Picture-in-Picture
2. **Given** the stream viewer is open, **When** the user dismisses it, **Then** the full tactical map is restored without any reload or state loss
3. **Given** the stream is unreachable (e.g., phone is off the local farm network / on mobile data only), **When** the user opens the viewer, **Then** a clear error message is shown explaining the stream is only available on the local network
4. **Given** the user has NOT explicitly opened the stream, **When** the app is running, **Then** no video data is fetched or buffered at any time

---

### User Story 4 — Chronological Alert Feed (Priority: P2)

As a farm owner, I want to see a scrollable list of recent alerts on the home screen, so I can review what happened while I was away or catch alerts I may have missed.

**Why this priority**: The alert log provides temporal context alongside the spatial map view, completing the situational awareness picture.

**Independent Test**: Can be fully tested with a series of simulated MQTT messages — the feed must show entries in reverse-chronological order with accurate tier, timestamp, and location details.

**Acceptance Scenarios**:

1. **Given** multiple alerts have arrived, **When** viewing the alert feed, **Then** entries are displayed in reverse-chronological order with timestamp, tier, target ID, and location summary
2. **Given** an alert has null coordinates (LRF unavailable), **When** shown in the feed, **Then** it displays "Location Unknown" rather than being omitted
3. **Given** the app has been closed and restarted, **When** the user opens it, **Then** all alerts within the configured retention period are visible in the feed

---

### User Story 5 — Initial Setup & Pairing (Priority: P1)

As a farm owner setting up the app for the first time, I want a guided setup flow that asks for the sentry's connection details, so I can get the system running without needing technical documentation.

**Why this priority**: Without successful pairing, no other feature works. This is the prerequisite for all telemetry-dependent stories.

**Independent Test**: Can be fully tested by completing the setup flow with valid broker details and verifying the app connects and shows the sentry on the map.

**Acceptance Scenarios**:

1. **Given** this is the first app launch, **When** setup begins, **Then** the user is prompted to enter MQTT broker IP address, port (default: 8883 for TLS), username, password, and Sentry ID; all fields are mandatory
2. **Given** valid connection details are entered, **When** the user confirms, **Then** the app connects and transitions to the home map screen
3. **Given** invalid or unreachable connection details are entered, **When** the connection fails, **Then** a clear error message is shown and the user can correct and retry
4. **Given** the app has been configured before, **When** it launches, **Then** it reconnects automatically using saved settings without showing the setup flow again

---

### User Story 6 — Sentry Calibration (Priority: P2)

As a farm owner, I want to set my sentry's exact GPS location and true north heading offset, so that threat positions are plotted accurately on my tactical map.

**Why this priority**: Without correct calibration, threat coordinates on the map will be inaccurate, undermining the primary value of the spatial display.

**Independent Test**: Can be fully tested by setting GPS coordinates and a heading offset, then verifying that a simulated telemetry message places its marker at the geometrically correct position.

**Acceptance Scenarios**:

1. **Given** I navigate to the calibration screen, **When** I enter or pin GPS coordinates for the sentry, **Then** the sentry marker updates to that position on the map
2. **Given** I set a True North heading offset in degrees, **When** I save, **Then** subsequent threat markers are rendered at positions that account for the corrected bearing
3. **Given** I set a custom notification score threshold, **When** I save, **Then** only detections above that score trigger notifications

---

### User Story 7 — Manual Turret Override (Priority: P3)

As a farm owner, I want to manually aim the sentry's turret at a specific area using a virtual joystick, so I can investigate a point of interest that the autonomous system is not currently tracking.

**Why this priority**: Manual override is a power-user feature for direct control; the sentry operates autonomously by default. It enhances the system but is not required for core security monitoring.

**Independent Test**: Can be fully tested by opening the manual override screen, verifying joystick input sends velocity commands, and confirming a stop command is sent on joystick release.

**Acceptance Scenarios**:

1. **Given** the manual override screen is open and the sentry is online, **When** the user drags the virtual joystick, **Then** pan and tilt velocity commands are continuously sent in the corresponding direction
2. **Given** the joystick is released, **When** the touch is lifted, **Then** a zero-velocity stop command is immediately sent to the sentry
3. **Given** the sentry is in Offline state, **When** the user attempts to open manual override, **Then** the joystick is disabled with an explanatory message
4. **Given** manual override is active, **When** the user exits the screen, **Then** a stop command is sent before the screen closes

---

### User Story 8 — Network Loss Handling (Priority: P1)

As a farm owner in a rural area, I want the app to clearly show me when it has lost contact with the sentry, so I always know whether I am looking at live or stale data.

**Why this priority**: On EDGE/3G, network drops are expected. A security system that silently shows stale data is dangerous — clear offline indication is a fundamental safety requirement.

**Independent Test**: Can be fully tested by disconnecting the MQTT broker while the app is running — a prominent offline banner must appear within the configured timeout and disappear when the broker reconnects.

**Acceptance Scenarios**:

1. **Given** the MQTT connection is active, **When** telemetry stops arriving for longer than the configured heartbeat timeout (default: 10 seconds), **Then** a prominent "System Offline / Reconnecting" indicator is displayed on the map HUD
2. **Given** the app is in Offline state, **When** the MQTT connection is restored, **Then** the offline indicator disappears and live telemetry resumes without user action
3. **Given** internet drops but local Wi-Fi/Intranet remains active, **When** the MQTT broker is still reachable, **Then** the app continues to operate normally
4. **Given** the app is backgrounded during an outage, **When** connectivity is restored, **Then** the app reconnects silently without requiring user interaction

---

### Edge Cases

- What happens when telemetry contains null `lat`/`lon` (LRF unavailable)? → Alert appears in the log with "Location Unknown" and is not plotted as a map pin
- What if the MQTT message queue overflows under severe network degradation? → Oldest unprocessed messages are discarded gracefully; no crash occurs
- What if the offline tile cache is empty and internet is unavailable? → The map renders a dark grid with coordinate overlays; threat markers and sentry position still render correctly
- What if two threats have the same or nearly identical coordinates? → Markers cluster with a count badge rather than overlapping
- What if the heartbeat timeout fires but alerts are still arriving (partial connectivity)? → The app remains online as long as any telemetry is being received
- What if the user opens the video feed over a mobile data connection (off-network)? → The stream attempts to connect; if unreachable a clear message explains the feed is only accessible on the local farm network; no background data is consumed silently
- What if MQTT authentication fails (wrong username/password)? → The app displays a clear "Authentication Failed" error in the setup flow and on the connection status HUD; the user is directed back to settings to correct credentials
- What if the broker's TLS certificate cannot be verified? → The connection is refused and the user is shown a "Secure Connection Failed" error; no fallback to unencrypted connection is permitted
- What if the joystick is held while the MQTT connection drops? → Command publishing stops immediately; a reconnection attempt begins; the joystick is visually disabled until the connection is restored
- What if location permission is denied or revoked? → All core features (map, MQTT, alerting, manual override) continue; user position dot and distance readouts are hidden (shown as "—"); a persistent non-blocking banner explains the limitation with a shortcut to system settings

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST display a full-screen tactical map as the primary home screen
- **FR-002**: The map MUST show the configured sentry position as a persistent, labelled marker
- **FR-003**: The map MUST continuously track and display the user's current GPS location when location permission is granted
- **FR-003a**: The app MUST calculate and display the straight-line distance between the user's current GPS position and each active target dot, shown both on the map HUD and in the alert log
- **FR-003b**: If the user denies location permission, the app MUST continue to function fully (map, MQTT, alerting, manual override); the user position dot and all distance readouts MUST be hidden and replaced with "—"; a persistent but non-blocking banner MUST explain the limitation and provide a shortcut to system settings to grant permission
- **FR-004**: The map MUST render active threat targets as animated dots, positioned at their telemetry-reported coordinates, coloured by severity tier: LOW = yellow, MED = orange, HIGH = red
- **FR-004a**: Active target dots MUST animate using the `velocity_vector` (vx, vy in m/s) published in each TelemetryRecord; this field is a backend dependency (TelemetryRecord extension required)
- **FR-004b**: When a target is lost (sentry enters SEARCH state), the dot MUST immediately begin a fade animation and display a "Last Seen: <timestamp>" label; the dot MUST be fully removed from the map after 30 seconds
- **FR-005**: Threat dot colour MUST map to severity tier: LOW = yellow, MED = orange, HIGH = red; size or glow intensity MAY additionally convey severity
- **FR-006**: The map MUST update threat dot positions within 2 seconds of new telemetry being received
- **FR-007**: The map MUST support offline tile caching so the tactical overlay remains usable when internet is unavailable but the local sentry network is active
- **FR-008**: Map marker updates MUST NOT trigger full-screen redraws; only affected markers may be re-rendered
- **FR-009**: The home screen MUST include a collapsible side panel (alert log) showing a scrollable, reverse-chronological list of recent detections; collapsing the panel reveals a full-screen map view
- **FR-009a**: Each alert log entry MUST prominently display: tier colour badge, threat score, straight-line distance to the user, and timestamp; secondary metadata (pan_angle, tilt_angle, lrf_distance_m, session_id) MUST be displayed in a visually smaller, secondary style
- **FR-009b**: The alert log MUST be persisted on-device and survive app restarts; the user MUST be able to configure the retention duration (e.g., 24 hours, 7 days, 30 days) in settings
- **FR-009c**: Alert log entries older than the configured retention period MUST be automatically purged
- **FR-009d**: Tapping an active threat dot on the map MUST select that dot (visual highlight) and scroll the alert log to its matching entry; if the panel is collapsed it MUST auto-open
- **FR-010**: The app MUST subscribe to MQTT topic `sentry/telemetry` and parse each TelemetryRecord JSON message (fields: `session_id`, `target_id`, `threat_score`, `tier`, `lat`, `lon`, `lrf_distance_m`, `pan_angle`, `tilt_angle`, `timestamp_utc`, `velocity_vector`, **`fsm_state`**)
- **FR-010a**: The map HUD MUST display an explicit "Sentry Mode" badge showing the current FSM state derived from the most-recently-received `fsm_state` value (`SCAN` / `ACQUIRE` / `TRACK` / `SEARCH`); the badge MUST update within 2 seconds of any state change
- **FR-011**: The app MUST display a persistent "System Offline / Reconnecting" indicator when no telemetry has been received within the configured heartbeat timeout (default: 10 seconds)
- **FR-012**: The app MUST automatically attempt to reconnect to the MQTT broker after any connection loss without requiring user action
- **FR-013**: The app MUST trigger a local push notification for every MED-tier or HIGH-tier detection, including when the app is backgrounded or the phone is locked
- **FR-014**: HIGH-tier detections MUST trigger an audible alarm that overrides device silent/do-not-disturb mode
- **FR-015**: The user MUST be able to configure per-tier notification behaviour (alarm / notification / silent / disabled) and a minimum score threshold (0–100)
- **FR-016**: The app MUST provide an on-demand MJPEG video stream viewer (modal overlay or Picture-in-Picture), accessible via an explicit user action only
- **FR-017**: The video stream viewer MUST NOT initiate streaming automatically under any circumstances
- **FR-018**: The app MUST include a first-launch setup flow collecting: MQTT broker IP, port, **username, password**, and Sentry ID; all fields are mandatory
- **FR-018a**: All MQTT connections (both `sentry/telemetry` subscription and `sentry/command` publishing) MUST use TLS encryption; unencrypted connections MUST be refused
- **FR-018b**: MQTT credentials MUST be stored in the platform's secure credential store (e.g., iOS Keychain / Android Keystore), never in plain-text app storage
- **FR-018c**: The setup flow MUST include a separate **Video Stream** section collecting the HTTP Basic Auth username and password for the MJPEG stream; these are distinct fields from the MQTT credentials
- **FR-018d**: Video stream credentials MUST also be stored in the platform secure credential store, never in plain-text storage
- **FR-019**: The app MUST persist all configuration and automatically reconnect on subsequent launches without re-displaying the setup flow
- **FR-020**: The user MUST be able to configure the sentry's physical GPS coordinates via a calibration settings screen
- **FR-021**: The user MUST be able to configure the sentry's True North heading offset (in degrees) for accurate coordinate projection
- **FR-022**: The app MUST provide a manual override screen with a virtual joystick that continuously publishes to MQTT topic `sentry/command` at 10 Hz (one message per 100 ms) with payload `{"sentry_id": "<id>", "pan_velocity": <float>, "tilt_velocity": <float>, "timestamp_utc": "<ISO8601>"}` while the joystick is held, and a zero-velocity payload immediately on release
- **FR-022a**: The backend (Jetson Core) MUST implement a corresponding MQTT subscription on topic `sentry/command` to receive and execute these velocity commands — this is a required backend implementation paired with this mobile feature
- **FR-023**: Manual override controls MUST be disabled and clearly labelled when the sentry is in Offline state
- **FR-024**: The app UI MUST use a dark, high-contrast visual theme throughout
- **FR-025**: Telemetry records with null `lat`/`lon` values MUST appear in the alert log with a "Location Unknown" indicator and MUST NOT be plotted as map markers

### Key Entities

- **SentryConfig**: MQTT broker IP, port, **username** (required), **password** (required, stored in secure credential store), Sentry ID, physical GPS coordinates (lat/lon), True North heading offset (degrees), heartbeat timeout (seconds), alert log retention duration; TLS required for all connections
- **TelemetryRecord**: session_id (UUID4), target_id (integer), threat_score (0.0–100.0), tier ("LOW" | "MED" | "HIGH"), lat (decimal degrees | null), lon (decimal degrees | null), lrf_distance_m (float | null), pan_angle (degrees), tilt_angle (degrees), timestamp_utc (ISO 8601), **velocity_vector** (vx: float, vy: float in m/s — backend extension required for animation), **fsm_state** ("SCAN" | "ACQUIRE" | "TRACK" | "SEARCH" — backend extension required for Sentry Mode badge)
- **ThreatMarker**: Map entity derived from a TelemetryRecord; carries visual state (active → fading → removed), colour (yellow=LOW / orange=MED / red=HIGH), last-seen timestamp, and calculated distance from the user's current GPS position. State transitions: active while telemetry arrives; fading (with "Last Seen" label) immediately when `fsm_state` == SEARCH or telemetry loss; removed 30 seconds after fade begins
- **AlertLogEntry**: timestamp, tier (with colour badge: yellow/orange/red), target_id, distance to user, threat_score (prominent); pan_angle, tilt_angle, lrf_distance_m, session_id (secondary/small); persisted on-device with user-configurable retention duration
- **NotificationPreferences**: per-tier mode (alarm / notification / silent / disabled), minimum score threshold (0–100)
- **ManualCommand**: Published to MQTT topic `sentry/command`; JSON schema: `{"sentry_id": string, "pan_velocity": float (steps/sec; positive = right, negative = left), "tilt_velocity": float (steps/sec; positive = up, negative = down), "timestamp_utc": ISO8601}`
- **ConnectionState**: Online | Reconnecting | Offline — derived from MQTT connection status and heartbeat timer

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: HIGH-tier threat notifications are delivered to a locked phone within 3 seconds of the sentry emitting the corresponding telemetry event
- **SC-002**: Threat marker positions on the tactical map update within 2 seconds of the corresponding MQTT message being published
- **SC-003**: The app operates as the primary monitoring interface on an EDGE/3G connection (~50 kbps) without loss of MQTT telemetry data; only the optional video stream degrades
- **SC-004**: A first-time user completes initial setup and calibration in under 5 minutes
- **SC-005**: The map remains visually smooth with no perceptible lag when up to 10 threat targets are tracked and updated simultaneously
- **SC-006**: The app automatically restores live monitoring within 30 seconds of network connectivity being re-established, without user intervention
- **SC-007**: Background battery consumption during active monitoring (MQTT only, no video) is within platform-standard expectations for a background network service
- **SC-008**: Users can activate the video verification overlay within 10 seconds of observing a threat marker, without prior training or documentation

---

## Assumptions

- The sentry publishes telemetry on MQTT topic `sentry/telemetry` using the TelemetryRecord JSON schema from the backend codebase; all field names and types are assumed stable
- Threat tier thresholds are: LOW < 40.0, MED 40.0–79.9, HIGH ≥ 80.0 (as defined in backend `config.py`)
- The MJPEG stream is served over HTTP at port 5000 on the same host as the MQTT broker, protected by HTTP Basic Auth; video stream credentials are separate from MQTT credentials and are configured independently in the setup flow; the stream is expected to be accessible only over the local farm network (LAN/intranet)
- No inbound MQTT command subscription currently exists in the backend for manual override; the backend MUST be extended to subscribe to topic `sentry/command` and apply received `pan_velocity`/`tilt_velocity` values — this is a paired backend requirement for User Story 7 / FR-022
- The backend's `TelemetryRecord` must be extended to include `velocity_vector` (vx, vy in m/s) derived from `TrackedTarget.velocity_vector`; this is a backend dependency required for FR-004a (dot movement animation)
- The backend's `TelemetryRecord` must be extended to include `fsm_state` (string enum: SCAN / ACQUIRE / TRACK / SEARCH) reflecting the current FSM state at time of publish; this is a backend dependency required for FR-010a (Sentry Mode badge)
- The app targets a single-sentry deployment; multi-sentry support is out of scope for this version
- Telemetry records with null lat/lon are valid and expected when LRF is disabled or a target has not yet been ranged
- The heartbeat mechanism is implicit: absence of any telemetry messages for the configured timeout signals offline state (no dedicated heartbeat topic exists in the backend)
- All MQTT connections require TLS encryption and username/password authentication; the broker must be configured with a valid TLS certificate and credentials (this is a backend/infrastructure requirement); the default TLS port is 8883

---

## Clarifications

### Session 2026-02-26

- Q: How should active threat targets be rendered on the map? → A: As animated coloured dots; LOW=yellow, MED=orange, HIGH=red; position animates smoothly between successive telemetry updates
- Q: How should dot movement animation be produced? → A: Extend the backend TelemetryRecord to also publish velocity_vector (vx, vy in m/s); the mobile app animates dots using these values (backend dependency)
- Q: What happens to the dot when a target is lost (sentry enters SEARCH state)? → A: The dot fades gradually and displays a "Last Seen: <timestamp>" label rather than disappearing instantly
- Q: Should the alert log be always-visible or hidable? → A: The alert log is a collapsible side panel; collapsing it gives a full-screen map view
- Q: Should the app calculate and display the user's distance to each target? → A: Yes — the app calculates the user's current GPS position and displays the straight-line distance from the user to each active target on the map HUD and in the alert log
- Q: Should MQTT broker authentication be required, optional, or absent? → A: Mandatory credentials (username/password required in setup flow); TLS encryption is also required for all MQTT broker connections
- Q: What MQTT topic and payload schema should the manual override joystick publish? → A: Topic `sentry/command`; payload `{"sentry_id": "…", "pan_velocity": 0.0, "tilt_velocity": 0.0, "timestamp_utc": "…"}`; backend MUST also implement subscription to this topic (backend implementation required)
- Q: When does a lost-target dot begin fading, and when is it removed? → A: Fade begins immediately when the sentry enters SEARCH state; the dot is fully removed after 30 seconds
- Q: How long should the alert log persist across app restarts? → A: Persisted on-device with configurable retention duration (user sets how long to keep entries)
- Q: How should information density be managed in the UI? → A: Primary target info (tier, distance to target, last-seen time, threat score) is displayed prominently; secondary metadata (session_id, pan_angle, tilt_angle, lrf_distance_m) is displayed in a smaller, secondary style

### Session 2026-02-26 (continued)

- Q: What happens when the user taps an active threat dot on the map? → A: Tap selects the dot and highlights the matching entry in the side panel; the panel auto-opens if it was collapsed
- Q: At what rate should the joystick publish MQTT commands while held? → A: 10 Hz — one command every 100 ms
- Q: Are video stream credentials shared with MQTT credentials or separately configured? → A: Separate credentials, independently configured in the setup flow; video stream is accessible over the local network only
- Q: What should the app do if the user denies location permission? → A: Graceful degradation — map, alerting, and all other features continue; user position dot and distance calculations are hidden; a non-blocking banner explains what's missing with a shortcut to system settings
- Q: Should the sentry's current FSM state (SCAN/ACQUIRE/TRACK/SEARCH) be visible on the map HUD? → A: Yes, backend-provided — add `fsm_state` field to `TelemetryRecord`; displayed as an explicit "Sentry Mode" status badge on the HUD (paired backend change required)
