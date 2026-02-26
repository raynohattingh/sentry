# Tasks: Farm Sentry Mobile App

**Input**: Design documents from `specs/001-sentry-mobile-app/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US8)
- All paths are relative to repository root

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Bootstrap the Flutter project and configure platform permissions.

- [ ] T001 Initialize Flutter project in `app/` — run `flutter create --org com.farmsentry --project-name sentry_mobile app`; commit generated project skeleton
- [ ] T002 [P] Add all dependencies to `app/pubspec.yaml`: `flutter_riverpod`, `mqtt_client`, `flutter_map`, `flutter_map_tile_caching`, `drift`, `sqlite3_flutter_libs`, `flutter_secure_storage`, `flutter_local_notifications`, `flutter_background_service`, `geolocator`, `http`, `go_router`; dev deps: `mocktail`, `build_runner`, `drift_dev`; run `flutter pub get`
- [ ] T003 [P] Create `app/analysis_options.yaml` extending `package:flutter_lints/flutter.yaml`; add `prefer_final_locals`, `avoid_print` rules
- [ ] T004 [P] Configure Android permissions and metadata in `app/android/app/src/main/AndroidManifest.xml`: `ACCESS_FINE_LOCATION`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_CONNECTED_DEVICE`, `RECEIVE_BOOT_COMPLETED`, `VIBRATE`, `USE_FULL_SCREEN_INTENT`, `POST_NOTIFICATIONS`; add `<service>` declaration for background service
- [ ] T005 [P] Configure iOS Info.plist in `app/ios/Runner/Info.plist`: `NSLocationWhenInUseUsageDescription`, `NSLocationAlwaysUsageDescription`, `UIBackgroundModes` (`fetch`, `remote-notification`); add `BGTaskSchedulerPermittedIdentifiers` key for background service

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 Create `app/lib/core/constants.dart` — define all named constants: `kDefaultMqttPort = 8883`, `kDefaultVideoPort = 5000`, `kHeartbeatTimeoutSec = 10`, `kMarkerFadeRemovalSec = 30`, `kJoystickPublishIntervalMs = 100`, `kThreatTierMedThreshold = 40.0`, `kThreatTierHighThreshold = 80.0`, `kMaxJoystickVelocity = 200.0`, `kDefaultRetentionDays = 7`; no magic numbers anywhere else
- [ ] T007 [P] Create `app/lib/core/theme.dart` — define `SentryTheme.dark()`: dark background `#0A0A0A`, card surface `#141414`, accent colours `kColorLow = #FFD700`, `kColorMed = #FF8C00`, `kColorHigh = #FF1E1E`, `kColorOffline = #555555`; tactical monospace secondary font; export `ThemeData`
- [ ] T008 [P] Create `app/lib/core/router.dart` — define `GoRouter` with named routes: `/setup`, `/` (map home), `/settings`, `/calibration`, `/override`; guard `/` redirect to `/setup` when `SentryConfig` is absent
- [ ] T009 [P] Create `app/lib/models/telemetry_record.dart` — `TelemetryRecord` immutable class; `ThreatTier` enum (`low`/`med`/`high`); `FsmState` enum (`scan`/`acquire`/`track`/`search`); `VelocityVector` value object; `fromJson()` factory with graceful handling of null `velocity_vector` and `fsm_state`; `toJson()`
- [ ] T010 [P] Create `app/lib/models/sentry_config.dart` — `SentryConfig` with all fields from data-model.md; `copyWith()`; separate MQTT and video credential fields; `isConfigured` getter returning false when broker IP or credentials are empty
- [ ] T011 [P] Create `app/lib/models/threat_marker.dart` — `ThreatMarker` with `MarkerState` enum (`active`/`fading`/`removed`); `copyWith()`; `color` getter mapping `ThreatTier` to theme colours; `isSelected` field; `distanceToUserM` nullable field
- [ ] T012 [P] Create `app/lib/models/alert_log_entry.dart` — `AlertLogEntry` data class matching SQLite schema in data-model.md; `fromTelemetryRecord()` factory that captures `distanceToUserM` at receipt time
- [ ] T013 [P] Create `app/lib/models/manual_command.dart` — `ManualCommand` with `toJson()` producing schema from `contracts/mqtt-command-outbound.md`; `zero()` factory returning stop command
- [ ] T014 [P] Create `app/lib/models/notification_preferences.dart` — `NotificationPreferences`; `NotificationMode` enum (`alarm`/`notification`/`silent`/`disabled`); `shouldNotify(ThreatTier, double score)` pure method; default: HIGH=alarm, MED=notification, LOW=silent
- [ ] T015 [P] Create `app/lib/models/connection_state.dart` — `SentryConnectionState` enum (`online`/`reconnecting`/`offline`) with `isLive` getter
- [ ] T016 Define abstract `MqttService` interface in `app/lib/services/mqtt_service.dart` — methods: `connect(SentryConfig)`, `disconnect()`, `publishCommand(ManualCommand)`, `Stream<TelemetryRecord> get telemetryStream`, `Stream<SentryConnectionState> get connectionStream`
- [ ] T017 [P] Define abstract `LocationService` interface in `app/lib/services/location_service.dart` — methods: `Stream<LatLng?> get locationStream`, `Future<bool> get hasPermission`, `Future<bool> requestPermission()`; static `distanceBetweenMetres(LatLng a, LatLng b)` pure function using Haversine formula
- [ ] T018 [P] Define abstract `NotificationService` interface in `app/lib/services/notification_service.dart` — methods: `Future<void> initialize()`, `Future<void> showThreatAlert(TelemetryRecord, NotificationPreferences)`, `Future<void> requestPermissions()`
- [ ] T019 [P] Define **abstract** `SecureStorageService` interface in `app/lib/services/secure_storage_service.dart` — declare: `saveMqttCredentials(String user, String pass)`, `loadMqttCredentials()→(String,String)?`, `saveVideoCredentials(String user, String pass)`, `loadVideoCredentials()→(String,String)?`; no implementation body; follows the same abstract-interface pattern as `MqttService` and `LocationService`
- [ ] T020 Create `app/lib/database/app_database.dart` — drift `AppDatabase` with `AlertLog` table matching schema in data-model.md; `timestamp_utc` column indexed; `@DriftDatabase` annotation; generate with `dart run build_runner build`
- [ ] T021 Create `app/lib/database/alert_log_dao.dart` — `AlertLogDao` with: `insertEntry()`, `watchAll()` stream, `getByTargetId()` for dot-tap lookup, `deleteOlderThan(DateTime cutoff)` purge method
- [ ] T022 [P] Create mock service implementations in `app/test/mocks/`: `MockMqttService`, `MockLocationService`, `MockNotificationService` using `mocktail`; expose `StreamController` fields so tests can inject telemetry events
- [ ] T023 [P] Create `app/lib/main.dart` — `ProviderScope` wrapping `SentryApp`; register `AppDatabase` singleton; call `flutter_background_service` `initialize()` with `onIosBackground` and `onStart` handlers; configure `GoRouter` consumer

**Checkpoint**: Foundation complete — all models, interfaces, database, and mocks are ready. User story phases can now begin.

---

## Phase 3: User Story 5 — Initial Setup & Pairing (Priority: P1)

**Goal**: Guided first-launch flow that collects all MQTT and video stream credentials and persists them securely; auto-connects on subsequent launches.

**Independent Test**: Complete the setup form with valid broker details → app connects and navigates to map home screen. Re-launch the app → setup screen is not shown again; app reconnects automatically.

**⚑ TDD (Constitution II)**: Write test tasks and confirm they FAIL before implementing. T027 must be written and failing before T024–T026.

- [ ] T027 [P] [US5] Unit test `SetupNotifier` in `app/test/unit/setup_provider_test.dart` — assert: missing fields prevent save; valid config persists; port 1883 shows TLS warning; second-launch skips setup flow; `SecureStorageService` calls verified via mock *(write first — will fail until T024–T025 exist)*
- [ ] T024 [US5] Implement `SecureStorageServiceImpl` in `app/lib/services/secure_storage_service.dart` — concrete implementation of the `SecureStorageService` interface defined in T019; wraps `flutter_secure_storage`; uses namespaced keys (`mqtt_username`, `mqtt_password`, `video_username`, `video_password`); writes to iOS Keychain / Android Keystore; no plain-text fallback
- [ ] T025 [US5] Implement `SetupNotifier` (`StateNotifier<SentryConfig>`) in `app/lib/features/setup/setup_provider.dart` — load saved config on init, `save(SentryConfig)` persists non-secret fields to `SharedPreferences` and credentials to `SecureStorageServiceImpl`; `isConfigured` computed from `SentryConfig.isConfigured`; add `shared_preferences` to `pubspec.yaml` if not already present
- [ ] T026 [US5] Build `SetupScreen` in `app/lib/features/setup/setup_screen.dart` — two sections: **MQTT** (host, port defaulting to 8883, username, password, sentry ID) and **Video Stream** (host defaulting to MQTT host, port defaulting to 5000, username, password); all fields mandatory; show inline validation errors; "Connect" CTA calls `SetupNotifier.save()` then navigates to `/`

---

## Phase 4: User Story 8 — Network Loss Handling (Priority: P1)

**Goal**: MQTT connection is maintained as a persistent TLS service; clear online/reconnecting/offline state is surfaced on the HUD; reconnection is fully automatic.

**Independent Test**: Disconnect the MQTT broker while the app is running → "System Offline / Reconnecting" banner appears within 10 s. Reconnect broker → banner disappears and telemetry resumes without user action.

**⚑ TDD (Constitution II)**: T031 must be written and failing before T028–T030.

- [ ] T031 [P] [US8] Unit test `ConnectionStateNotifier` in `app/test/unit/connection_state_test.dart` — assert: heartbeat timer fires `offline` after `kHeartbeatTimeoutSec` (timing assertion: state must change within `kHeartbeatTimeoutSec + 1 s`); incoming telemetry resets timer; `onConnected` callback sets `online`; `onDisconnected` sets `reconnecting`; mock MQTT reconnect completes within 30 s (SC-006) *(write first — will fail until T029 exists)*
- [ ] T028 [US8] Implement `MqttServiceImpl` in `app/lib/services/mqtt_service.dart` — `mqtt_client` with `MqttServerClient.withPort`, TLS via `SecurityContext.defaultContext`, `onBadCertificate: (_) => false` (strict), `authenticateAs(username, password)`, QoS 1 subscription on `sentry/telemetry`; emit parsed `TelemetryRecord` on `telemetryStream`; emit `SentryConnectionState` changes on `connectionStream`; exponential-backoff auto-reconnect on disconnect
- [ ] T029 [US8] Implement `ConnectionStateNotifier` (`StateNotifier<SentryConnectionState>`) in `app/lib/features/map/connection_provider.dart` *(split from map_provider.dart — Constitution I SRP)*: starts a `Timer(kHeartbeatTimeoutSec)` that fires `offline` if no telemetry received; resets timer on every `TelemetryRecord`; listens to `MqttService.connectionStream` for `reconnecting`/`online` transitions; when state → `offline`, calls `ThreatMarkersNotifier.fadeAll()` (H3 fix — FR-004b telemetry-loss path)
- [ ] T030 [US8] Build `ConnectionStatusBar` widget in `app/lib/features/map/widgets/connection_status_bar.dart` — shows `[MQTT] Reconnecting…` in amber and `[SENTRY] System Offline` in `kColorOffline` when not `online`; disappears when `online`; always rendered above the map in a `Stack`

---

## Phase 5: User Story 1 — Tactical Map Home Screen (Priority: P1) 🎯 MVP

**Goal**: Full-screen tactical map HUD showing sentry position, animated threat dots coloured by tier, user location, distance readouts, Sentry Mode badge, and a collapsible alert panel — all updating live from MQTT telemetry.

**Independent Test**: Launch app with live MQTT telemetry → map shows sentry marker; HIGH-tier message arrives → red dot appears at correct coordinates within 2 s; sentry enters SEARCH → dot fades immediately, "Last Seen" label appears, dot fully gone after 30 s; tap dot → alert panel opens and scrolls to matching entry.

**⚑ TDD (Constitution II)**: Write T041–T044 and confirm they FAIL before T032–T040.

- [ ] T041 [P] [US1] Unit test `TelemetryRecord.fromJson()` in `app/test/unit/telemetry_parsing_test.dart` — assert: valid full message parses correctly; null `lat`/`lon` permitted; unknown `tier` defaults to `low`; null `velocity_vector` parses to null; null `fsm_state` parses to null; malformed JSON throws `FormatException` *(write first)*
- [ ] T042 [P] [US1] Unit test `ThreatMarker` lifecycle FSM in `app/test/unit/threat_marker_fsm_test.dart` — assert: SEARCH state triggers `fading`; 30 s elapsed transitions to `removed`; new telemetry on `fading` marker reverts to `active`; distance recalculated on location update; **`offline` connection state triggers `fadeAll()` on all active markers** (FR-004b telemetry-loss path) *(write first)*
- [ ] T043 [P] [US1] Unit test Haversine distance in `app/test/unit/geo_utils_test.dart` — assert known coordinates produce expected distances within 1 m tolerance; same-point returns 0; null location returns null; **`applyNorthOffset()` test: sentry at origin, offset 90°, target at 0° bearing → appears at 270° corrected** (H1 True North fix) *(write first)*
- [ ] T044 [P] [US1] Integration test MQTT→provider→map pipeline in `app/test/integration/mqtt_to_map_test.dart` — inject mock `TelemetryRecord` via `MockMqttService` stream controller; assert `ThreatMarkersNotifier` state updates **within 2 s of message injection** (SC-002 timing assertion); assert distance field populated when mock location active; assert mock `offline` event triggers `fadeAll()` on active markers *(write first)*
- [ ] T032 [US1] Implement `LocationServiceImpl` in `app/lib/services/location_service.dart` — `geolocator` position stream; `requestPermission()` delegates to platform; `hasPermission` getter; `distanceBetweenMetres()` static using `Geolocator.distanceBetween()`
- [ ] T033 [US1] Implement `TelemetryStreamProvider` (`StreamProvider<TelemetryRecord>`) and `ThreatMarkersNotifier` (`StateNotifier<Map<int, ThreatMarker>>`) in `app/lib/features/map/telemetry_provider.dart` *(split from map_provider.dart — Constitution I SRP)*: on each `TelemetryRecord` upsert marker (position, tier, `velocityVector`, `fsmState`); trigger fade when `fsmState == FsmState.search`; expose `fadeAll()` method called by `ConnectionStateNotifier` when `offline` state fires (FR-004b telemetry-loss path); schedule removal after `kMarkerFadeRemovalSec`; recalculate `distanceToUserM` using `LocationService`; apply `GeoUtils.applyNorthOffset()` to raw `lat`/`lon` before plotting (FR-021 — see T069)
- [ ] T034 [US1] Implement `SentryModeProvider` (`StateProvider<FsmState?>`) in `app/lib/features/map/telemetry_provider.dart` — updated from every `TelemetryRecord.fsmState`; null when no telemetry received
- [ ] T035 [US1] Build `MapScreen` scaffold in `app/lib/features/map/map_screen.dart` — `FlutterMap` with `TileLayer` (Stadia Alidade Smooth Dark tiles), `FMTC` store initialised on first run; `Stack` layout: map → `ThreatMarkerLayer` → `UserLocationLayer` → `SentryModeBadge` → `ConnectionStatusBar` → location-denied banner → collapsible `AlertPanel`
- [ ] T036 [US1] Build `ThreatMarkerLayer` in `app/lib/features/map/widgets/threat_marker_layer.dart` — `MarkerLayer` consuming `ThreatMarkersNotifier`; dot colour per FR-005 (`kColorLow`/`kColorMed`/`kColorHigh`); dot **size scales by tier** (LOW=12px, MED=16px, HIGH=20px) satisfying the FR-005 MAY clause; HIGH-tier dots pulse via `AnimatedContainer` glow; fading markers use `AnimatedOpacity`; `velocityVector` drives `AnimatedPositioned` interpolation; tapping calls `SelectedMarkerNotifier.select(targetId)`
- [ ] T037 [US1] Build `UserLocationLayer` in `app/lib/features/map/widgets/user_location_layer.dart` — blue dot from `UserLocationProvider`; hidden when location permission denied
- [ ] T038 [US1] Build `SentryModeBadge` widget in `app/lib/features/map/widgets/sentry_mode_badge.dart` — reads `SentryModeProvider`; displays `SCAN` / `ACQUIRE` / `TRACK` / `SEARCH` with colour coding (SCAN=grey, TRACK=amber, ACQUIRE=orange, SEARCH=red-pulse); shows `—` when null
- [ ] T039 [US1] Implement location-denied banner in `app/lib/features/map/map_screen.dart` — persistent `MaterialBanner` (non-blocking) shown when `!LocationService.hasPermission`; message: `"[LOCATION] Position unavailable — distances hidden"`; action button opens app settings via `geolocator`'s `openAppSettings()`
- [ ] T040 [US1] Implement `SelectedMarkerNotifier` (`StateNotifier<int?>`) in `app/lib/features/map/selection_provider.dart` *(split from map_provider.dart — Constitution I SRP)*: `select(int targetId)` and `clear()`; `MapScreen` listens: on select, notify `AlertPanel` to scroll and highlight, auto-open panel if collapsed

---

## Phase 6: User Story 2 — Background & Lockscreen Threat Alerts (Priority: P1)

**Goal**: MED/HIGH-tier detections trigger local push notifications even when the phone is locked; HIGH-tier alarms override silent/DND mode.

**Independent Test**: Lock the phone; inject HIGH-tier MQTT message via test broker → device produces full-volume alarm sound and shows lockscreen notification within 3 s. Inject LOW-tier message → no notification. Set MED tier to `silent` in settings → MED message produces no notification.

**⚑ TDD (Constitution II)**: T048 must be written and failing before T045–T047.

- [ ] T048 [P] [US2] Unit test `NotificationPreferences.shouldNotify()` in `app/test/unit/notification_routing_test.dart` — assert: HIGH alarm mode triggers; MED notification mode triggers; LOW silent mode suppresses; score below threshold suppresses regardless of tier; `disabled` mode always suppresses; **manual benchmark target for SC-004**: phone locked, inject HIGH-tier message → lockscreen alarm fires within 3 s *(write first)*
- [ ] T045 [US2] Implement `NotificationServiceImpl` in `app/lib/services/notification_service.dart` — `flutter_local_notifications` init with Android channel `id: "sentry_threat_high"`, `importance: Importance.max`, `playSound: true`, `audioAttributesUsage: AudioAttributesUsage.alarm`; iOS config with `Critical Alert` request; `showThreatAlert()` builds notification payload from `TelemetryRecord` with tier badge and score; `requestPermissions()` calls platform permission API
- [ ] T046 [US2] Wire background MQTT → notification pipeline in `app/lib/main.dart` — `flutter_background_service` `onStart` handler subscribes to `MqttService.telemetryStream`; on each record: calls `NotificationService.showThreatAlert()` if `NotificationPreferences.shouldNotify(tier, score)` returns true; background isolate has its own `ProviderContainer`
- [ ] T047 [US2] Implement `NotificationPreferencesNotifier` (`StateNotifier<NotificationPreferences>`) in `app/lib/features/settings/settings_provider.dart` *(not `settings_screen.dart` — Constitution I SRP)*: loads from `SharedPreferences`; `update()` persists; exposed via `notificationPreferencesProvider`

---

## Phase 7: User Story 4 — Chronological Alert Feed (Priority: P2)

**Goal**: Collapsible side panel showing a persisted reverse-chronological alert log with prominent tier/score/distance and secondary metadata; survives app restarts; auto-purges stale entries.

**Independent Test**: Simulate 5 MQTT messages of mixed tiers → all 5 appear in panel in reverse-chronological order. Kill and relaunch app → entries still present. Set retention to 1 day; inject an entry with a timestamp 2 days old → it is absent on next foreground. Tap a HIGH dot → panel opens and scrolls to its entry.

**⚑ TDD (Constitution II)**: T053 must be written and failing before T049–T052.

- [ ] T053 [P] [US4] Unit test `AlertLogDao` purge in `app/test/unit/alert_purge_test.dart` — insert entries with timestamps spanning 40 days; call `deleteOlderThan(now - 7 days)`; assert only entries within 7 days remain; assert `watchAll()` stream emits updated list *(write first)*
- [ ] T049 [US4] Implement `AlertsNotifier` (`StateNotifier` backed by drift watch stream) in `app/lib/features/alerts/alerts_provider.dart` — subscribes to `AlertLogDao.watchAll()`; on each `TelemetryRecord` inserts via `AlertLogDao.insertEntry()`; triggers `purgeOldEntries()` when app comes to foreground (using `AppLifecycleListener`)
- [ ] T050 [US4] Build collapsible `AlertPanel` in `app/lib/features/alerts/alert_panel.dart` — `AnimatedContainer` slide-in from right (or bottom on narrow screens); collapse toggle button on map edge; `ListView.builder` rendering `AlertLogEntryTile` items
- [ ] T051 [US4] Build `AlertLogEntryTile` in `app/lib/features/alerts/alert_panel.dart` — prominent row: tier colour badge, threat score (large), distance to user (display `"Location Unknown"` literal string when `lat`/`lon` are null — FR-025), timestamp; secondary row (smaller, muted): `pan_angle`, `tilt_angle`, `lrf_distance_m`, `session_id`; highlighted background when `targetId` matches `SelectedMarkerNotifier`; `onTap` calls `SelectedMarkerNotifier.select()`
- [ ] T052 [US4] Implement `ScrollToSelected` logic in `app/lib/features/alerts/alert_panel.dart` — `AlertsNotifier` listens to `SelectedMarkerNotifier`; when selection changes, `ScrollController.animateTo()` to matching entry index; if panel collapsed, calls panel open callback

---

## Phase 8: User Story 3 — On-Demand Live Video Verification (Priority: P2)

**Goal**: Tap a single action to open the sentry's MJPEG thermal camera feed as a modal overlay; stream never auto-starts; graceful error when off local network.

**Independent Test**: Tap "View Feed" → MJPEG frames render in modal. Dismiss → map state unchanged. Open feed while on mobile data / with broker host unreachable → error message shown explaining local-network requirement. Verify no HTTP request made until explicit tap.

- [ ] T054 [US3] Build `MjpegViewer` widget in `app/lib/features/video/mjpeg_viewer.dart` — Dart `http.Client().send()` with `Authorization: Basic <base64>` header; parse `multipart/x-mixed-replace` chunked stream; render decoded JPEG frames via `Image.memory`; show spinner after 5 s stall; on `SocketException` / `401` show inline error per contracts/video-stream-http.md; `dispose()` closes HTTP client
- [ ] T055 [US3] Build `VideoModal` in `app/lib/features/video/video_modal.dart` — `showModalBottomSheet` or `Dialog` containing `MjpegViewer`; opened only via explicit "View Feed" `IconButton` in `MapScreen` app bar; stream constructed with `videoStreamHost`, `videoStreamPort`, and video credentials from `SentryConfig`; `dispose()` guaranteed on close
- [ ] T056 [P] [US3] Add "View Feed" action button to `MapScreen` app bar in `app/lib/features/map/map_screen.dart` — tapping calls `showVideoModal(context, config)`; button disabled (greyed) when sentry `ConnectionState` is `offline`

---

## Phase 9: User Story 6 — Sentry Calibration (Priority: P2)

**Goal**: Settings flow allows pinning the sentry's GPS location and True North offset; changes immediately update the sentry marker on the map.

**Independent Test**: Enter GPS coordinates and a 10° North offset → sentry marker moves to pinned position; simulate telemetry at known bearing → threat dot appears at geometrically correct position. Change retention duration → alert log purge respects the new value.

- [ ] T057 [US6] Build `CalibrationScreen` in `app/lib/features/calibration/calibration_screen.dart` — lat/lon text fields with decimal validation; "Pin My Location" button pre-fills from `LocationService.locationStream`; True North offset slider (−180 to +180°) with degree readout; save calls `SetupNotifier.save(config.copyWith(...))`; sentry marker on map updates reactively via `SentryConfigProvider`
- [ ] T058 [US6] Build `SettingsScreen` in `app/lib/features/settings/settings_screen.dart` — sections: **Notifications** (per-tier `NotificationMode` dropdowns, score threshold slider); **Alert Log** (retention duration picker: 24 h / 7 d / 30 d); **Sentry** (link to Calibration screen); **Connection** (link back to Setup flow for re-pairing); all saves are immediate via respective providers
- [ ] T059 [P] [US6] Wire `SentryConfigProvider` to sentry map marker in `app/lib/features/map/map_screen.dart` — `ref.watch(sentryConfigProvider)` drives a dedicated `MarkerLayer` for the sentry position; marker updates when `sentryLat`/`sentryLon` change without map rebuild

---

## Phase 10: User Story 7 — Manual Turret Override (Priority: P3)

**Goal**: Virtual joystick publishes pan/tilt velocity commands to `sentry/command` at 10 Hz; releases immediately send a zero-velocity stop; controls are disabled when sentry is offline.

**Independent Test**: Open override screen with sentry online; drag joystick → MQTT inspector shows `sentry/command` messages at ~10 Hz with non-zero velocities. Release → single zero-velocity command published. Disconnect sentry → joystick becomes disabled. Exit screen → zero-velocity stop command published.

**⚑ TDD (Constitution II)**: T062 must be written and failing before T060–T061.

- [ ] T062 [P] [US7] Unit test joystick velocity in `app/test/unit/joystick_test.dart` — assert: delta normalisation produces correct velocity; values clamped to `kMaxJoystickVelocity`; `ManualCommand.zero()` has both velocities == 0.0; `ManualCommand.toJson()` matches schema in contracts/mqtt-command-outbound.md *(write first)*
- [ ] T060 [US7] Build `JoystickWidget` in `app/lib/features/override/joystick_widget.dart` — `GestureDetector` tracking `onPanUpdate`; normalise delta to `(panVelocity, tiltVelocity)` in steps/sec, clamped to `kMaxJoystickVelocity`; expose `ValueNotifier<ManualCommand>`; visual: outer ring + inner movable nub with `AnimatedPositioned`; snaps to centre on release
- [ ] T061 [US7] Build `OverrideScreen` in `app/lib/features/override/override_screen.dart` — `JoystickWidget` centred on screen; `Timer.periodic(Duration(milliseconds: kJoystickPublishIntervalMs))` started on first drag, cancelled on release; on each tick: `MqttService.publishCommand(currentCommand)`; on release: publish `ManualCommand.zero()`; in `dispose()`: publish `ManualCommand.zero()` then cancel timer; reads `connectionStateProvider` — if not `online`, disables joystick with `[TURRET] Offline — manual control unavailable` label
- [ ] T063 [P] [US7] Add "Override" navigation button to `MapScreen` app bar in `app/lib/features/map/map_screen.dart` — navigates to `/override`; only visible when sentry is `online`

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Offline map seeding, test tooling, visual polish, and backend dependency documentation.

- [ ] T064 Implement offline tile pre-seeding in `app/lib/features/setup/setup_screen.dart` — after successful MQTT connection, prompt user to download tiles for a configurable bounding box (default: 20 km radius around sentry position) using `FMTC`'s `FMTCStore.manage.download()`; show progress indicator; skippable
- [ ] T065 [P] Create MQTT test simulation script `test/mqtt_sim.py` — Python script using `paho-mqtt` over TLS; CLI args: `--broker`, `--port`, `--username`, `--password`, `--tier`, `--lat`, `--lon`, `--fsm-state`, `--vx`, `--vy`; publishes a `TelemetryRecord` JSON matching the schema in `contracts/mqtt-telemetry-inbound.md`; add `--throttle-kbps` flag (uses Linux `tc` or token-bucket sleep loop) to simulate SC-003 EDGE/3G conditions (~50 kbps); used for manual integration testing per quickstart.md
- [ ] T066 [P] Audit all screens for theme consistency in `app/lib/` — verify no hardcoded colour literals outside `theme.dart`; verify all status strings follow `[SUBSYSTEM] <message>` convention; verify no magic numbers outside `constants.dart`
- [ ] T067 [P] Add backend dependency notes to `jetson/src/types.py` — add `# TODO(mobile-app FR-022a BLOCKING): subscribe to sentry/command topic in mqtt.py and execute received ManualCommand velocities via TurretManager` and `# TODO(mobile-app FR-010a BLOCKING): add velocity_vector and fsm_state fields to TelemetryRecord — required by FR-004a and FR-010a`; **FR-022a (backend MQTT subscriber for manual override) is a BLOCKING dependency for US7 Phase 10 — the app publishes but the sentry must subscribe and execute**; these TODO comments must be resolved before US7 is considered production-ready
- [ ] T069 [US6] Implement `GeoUtils.applyNorthOffset()` in `app/lib/utils/geo_utils.dart` — static method `LatLng applyNorthOffset(LatLng raw, double offsetDegrees)`; rotates a raw GPS coordinate around the sentry origin by the configured True North offset; called in `ThreatMarkersNotifier` (T033) when plotting each telemetry coordinate; include unit test in `app/test/unit/geo_utils_test.dart` asserting sentry at origin + 90° offset + target at 0° bearing → appears at 270° corrected (resolves FR-021 calibration gap — H1)
- [ ] T070 [Polish] Implement marker clustering in `flutter_map_marker_cluster` for 5+ simultaneous active markers — clusters display a count badge; tapping expands cluster; prevents marker overlap at low zoom levels; **note**: `flutter_map_marker_cluster` must be checked for compatibility with current `flutter_map` version before adding to pubspec
- [ ] T068 Run `flutter test` suite (all unit + integration tests) to confirm full green; run `flutter analyze` with zero warnings; document any iOS Critical Alert entitlement request status in `specs/001-sentry-mobile-app/quickstart.md`; manual checklist: (SC-004) setup → MQTT connected ≤ 5 min on clean install; (SC-007) 1-hour background session on Android/iOS with background service active — verify battery drain ≤ 5% per hour on a mid-range device; (SC-008) "View Feed" tap to first MJPEG frame ≤ 10 s on local Wi-Fi; (SC-003) run `mqtt_sim.py --throttle-kbps 50` and confirm map updates and notifications still fire

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US5 Setup & Pairing (Phase 3)**: Depends on Phase 2 — first user-facing story; credentials required for all MQTT phases
- **US8 Network Handling (Phase 4)**: Depends on Phase 2 — MQTT service impl blocks US1, US2, US7
- **US1 Map HUD (Phase 5)**: Depends on Phase 4 (MQTT service running) — core MVP
- **US2 Alerts (Phase 6)**: Depends on Phase 4 (MQTT stream) — independent of US1
- **US4 Alert Feed (Phase 7)**: Depends on Phase 2 (database) + Phase 4 (MQTT stream) — independent of US1
- **US3 Video (Phase 8)**: Depends on Phase 3 (video credentials from setup) — independent of map
- **US6 Calibration (Phase 9)**: Depends on Phase 3 (config persistence) — independent of alerting
- **US7 Override (Phase 10)**: Depends on Phase 4 (MQTT publish via `MqttService`) — independent of map rendering
- **Polish (Final Phase)**: Depends on all desired user stories complete

### User Story Dependencies

```
Phase 1 (Setup)
  └─► Phase 2 (Foundation)
        ├─► Phase 3 (US5: Pairing) ──────────────────────────────────────────┐
        ├─► Phase 4 (US8: Network) ──────────────────────────────────────────┤
        │     ├─► Phase 5 (US1: Map HUD)                                      │
        │     ├─► Phase 6 (US2: Alerts)              (parallel with US1)      │
        │     ├─► Phase 7 (US4: Alert Feed)           (parallel with US1/US2) │
        │     └─► Phase 10 (US7: Override)            (parallel with US1–US4) │
        └─► Phase 8 (US3: Video) ◄──────────────────────────────────────────┘
              Phase 9 (US6: Calibration) ◄──────────────────────────────────┘
```

### Within Each Phase

- Tests (marked [P]) MUST be written before the corresponding implementation tasks
- Models before services; services before screens
- Story complete and independently tested before moving to next priority

---

## Parallel Execution Examples

### Phase 2 — Foundational (all [P] tasks run simultaneously)

```
T006 constants.dart
T007 theme.dart
T008 router.dart
T009 telemetry_record.dart  ─┐
T010 sentry_config.dart      │  All model files simultaneously
T011 threat_marker.dart      │
T012 alert_log_entry.dart    │
T013 manual_command.dart     │
T014 notification_prefs.dart │
T015 connection_state.dart  ─┘
T017 location_service.dart  ─┐  All abstract interfaces simultaneously
T018 notification_service.dart│
T019 secure_storage.dart    ─┘
T022 test/mocks/             ← simultaneously with service interfaces
```

### Phase 5 — US1 Map HUD ([P] tasks)

```
T041 telemetry_parsing_test.dart  ─┐
T042 threat_marker_fsm_test.dart   │  Write all US1 tests simultaneously
T043 geo_utils_test.dart           │
T044 mqtt_to_map_test.dart        ─┘
```

### Phases 5–10 — After Phase 4 completes (independent stories in parallel)

```
Developer A: Phase 5 (US1 Map HUD)       → highest value, longest effort
Developer B: Phase 6 (US2 Alerts)        → independent notification path
Developer C: Phase 7 (US4 Alert Feed)    → independent DB path
Developer D: Phase 8 (US3 Video)         → independent HTTP path
```

---

## Implementation Strategy

### MVP Scope (User Stories 1 + 5 + 8 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US5 — pair with sentry
4. Complete Phase 4: US8 — MQTT connection + offline indicator
5. Complete Phase 5: US1 — tactical map HUD
6. **STOP and VALIDATE**: Live sentry → map shows threat dots in real time
7. Demo / deploy minimal viable app

### Incremental Delivery

- **v0.1 (MVP)**: Phases 1–5 → Live map HUD
- **v0.2**: Phase 6 (US2 Alerts) → Lockscreen alarms on HIGH threats
- **v0.3**: Phase 7 (US4 Feed) → Persisted alert log panel
- **v0.4**: Phases 8–9 (US3 Video + US6 Calibration) → Full verification + calibration
- **v1.0**: Phase 10 (US7 Override) + Polish → Manual turret control + hardening

---

## Summary

| Phase | User Story | Tasks | Priority | Test-First (TDD) |
|---|---|---|---|---|
| Phase 1 | Setup | T001–T005 | — | T002–T005 |
| Phase 2 | Foundational | T006–T023 | — | T007–T022 |
| Phase 3 | US5 Pairing | T024–T027 | P1 | **T027 → then T024–T026** |
| Phase 4 | US8 Network | T028–T031 | P1 | **T031 → then T028–T030** |
| Phase 5 | US1 Map HUD | T032–T044 | P1 🎯 MVP | **T041–T044 → then T032–T040** |
| Phase 6 | US2 Alerts | T045–T048 | P1 | **T048 → then T045–T047** |
| Phase 7 | US4 Feed | T049–T053 | P2 | **T053 → then T049–T052** |
| Phase 8 | US3 Video | T054–T056 | P2 | T056 |
| Phase 9 | US6 Calibration | T057–T059 + T069 | P2 | T059 |
| Phase 10 | US7 Override | T060–T063 | P3 | **T062 → then T060–T061, T063** |
| Final | Polish | T064–T068 + T070 | — | T065–T068 |
| **Total** | | **71 tasks** | | **TDD order enforced in all phases** |
