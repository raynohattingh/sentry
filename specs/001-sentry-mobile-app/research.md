# Research: Farm Sentry Mobile App

**Phase 0 Output** | Branch: `001-sentry-mobile-app`

All NEEDS CLARIFICATION items from `plan.md` Technical Context resolved below.

---

## Decision 1 — State Management

**Decision**: `flutter_riverpod` (Riverpod 2.x)

**Rationale**: Riverpod provides fine-grained, compile-time-safe reactivity. Each `TelemetryRecord` update can notify only the providers watching a specific `target_id`, preventing full-tree rebuilds under the 10+ Hz MQTT stream. `StreamProvider` integrates cleanly with the MQTT service stream. `StateNotifierProvider` manages the `ThreatMarker` lifecycle (active → fading → removed) without coupling UI to business logic. The `ProviderScope` enables clean test overrides for all hardware-backed services.

**Alternatives considered**:
- `bloc/cubit`: Mature and testable, but verbose event/state boilerplate for high-frequency telemetry streams; each MQTT message becomes an event dispatch, adding latency overhead
- `GetX`: Minimal boilerplate, but implicit global state coupling makes unit testing MQTT-to-UI flow difficult; less suitable for safety-critical apps requiring clear dependency graphs

---

## Decision 2 — MQTT Client

**Decision**: `mqtt_client` (pub.dev `mqtt_client: ^10.x`)

**Rationale**: The only mature, pure-Dart MQTT library with explicit TLS/SSL support via Dart's `SecurityContext`, username/password auth, QoS 0/1/2, and automatic reconnection callbacks. Used extensively in production Flutter IoT apps. Wraps neatly behind an abstract `MqttService` interface for mocking in tests.

**TLS configuration pattern**:
```dart
final client = MqttServerClient.withPort(brokerHost, clientId, 8883)
  ..secure = true
  ..securityContext = SecurityContext.defaultContext
  ..onBadCertificate = (cert) => false  // strict — no self-signed bypass
  ..connectionMessage = MqttConnectMessage()
      .authenticateAs(username, password)
      .withWillQos(MqttQos.atLeastOnce);
```

**Alternatives considered**:
- `flutter_mqtt`: A thin wrapper around `mqtt_client`; adds no value and introduces an unnecessary dependency
- Firebase MQTT proxy: Adds cloud dependency, violates local-only design, incompatible with private broker

---

## Decision 3 — Map Library

**Decision**: `flutter_map` (v7.x) + `flutter_map_tile_caching` (FMTC)

**Rationale**: `flutter_map` is the only Flutter map library with first-class offline tile caching (via FMTC), full control over tile sources (OpenStreetMap, custom dark tiles), and a `MarkerLayer` that can be rebuilt independently of the base map layer — satisfying FR-008. It is fully open-source with no API key requirement. FMTC allows pre-downloading farm-area tiles for offline use.

**Tile source for dark theme**: Stadia Maps "Alidade Smooth Dark" tiles (free tier, no API key for offline use); fallback to OSM standard tiles. Offline cache seeded during initial setup for the farm's bounding box.

**Marker animation**: Achieved via `AnimatedContainer` within `flutter_map`'s `MarkerLayer`, driven by Riverpod state changes — no full map rebuild triggered.

**Alternatives considered**:
- `google_maps_flutter`: Requires Google API key, no offline tile support, opinionated about tile sources; cannot meet FR-007
- `mapbox_maps_flutter`: Offline capable but requires Mapbox account/token, proprietary SDK, higher complexity

---

## Decision 4 — Background MQTT Execution

**Decision**: `flutter_background_service` (Android foreground service + iOS background mode)

**Rationale**: MQTT must survive phone lock for HIGH-tier alarm delivery (FR-013, FR-014). On Android, `flutter_background_service` creates a foreground service with a persistent notification, preventing the OS from killing the MQTT connection. On iOS, background execution uses Background App Refresh + a persistent `NSURLSession`-equivalent keep-alive; iOS limits mean a brief reconnection on wake is acceptable (the MQTT auto-reconnect covers this).

**iOS limitation acknowledged**: iOS aggressively terminates background processes after ~30 seconds without user interaction. Mitigation: set MQTT keepAlive to 60 s, enable Background App Refresh in entitlements, and supplement with APNs push via the broker's webhook-to-APNS bridge if critical alarm reliability is paramount in a future iteration.

**Alternatives considered**:
- Raw Dart isolates: Killed by OS on both platforms when app is backgrounded; insufficient for lock-screen alarm delivery
- `workmanager`: Periodic task scheduler, not suited for a persistent TCP connection

---

## Decision 5 — Local Notifications & Alarms

**Decision**: `flutter_local_notifications` + `android_alarm_manager_plus` for Android; `flutter_local_notifications` with critical alert entitlement for iOS

**Rationale**: `flutter_local_notifications` provides the unified cross-platform API. On Android, HIGH-tier alarms use `Notification.Builder` with `IMPORTANCE_MAX` + `setFullScreenIntent` + `AudioAttributes.USAGE_ALARM` to override silent mode. On iOS, the `Critical Alert` entitlement (requires Apple approval) allows alarm sounds to override Do Not Disturb; without the entitlement, sounds play at normal volume with DND respected.

**Note**: iOS Critical Alert entitlement is a prerequisite for FR-014 on iOS. Must be requested from Apple during App Store submission.

---

## Decision 6 — Secure Credential Storage

**Decision**: `flutter_secure_storage` (v9.x)

**Rationale**: Wraps iOS Keychain Services and Android Keystore with a single Dart API. AES-256 encryption on Android (via EncryptedSharedPreferences), Keychain on iOS. No platform-channel boilerplate. Used for both MQTT credentials and video stream credentials (stored as separate key namespaces).

**Alternatives considered**:
- Manual platform channels: Equivalent functionality, significantly more code, no testing advantage
- `encrypted_shared_preferences` (Android-only): Not cross-platform

---

## Decision 7 — Alert Log Persistence

**Decision**: `drift` (v2.x) with SQLite via `sqlite3_flutter_libs`

**Rationale**: Type-safe SQL with compile-time query validation, reactive `Stream<List<AlertLogEntry>>` for live panel updates, built-in migration system for schema evolution, and native support for `DELETE WHERE timestamp < ?` purge queries. Drift's `TableInfo` generates the DAO layer, avoiding raw SQL string maintenance.

**Schema approach**: Single `alert_log` table with indexed `timestamp_utc` column. Purge triggered on app foreground via a `drift` delete statement comparing `timestamp_utc` to `DateTime.now().subtract(retentionDuration)`.

**Alternatives considered**:
- `sqflite`: No type safety, manual SQL strings; higher risk of SQL errors in a security-critical log
- `isar`: Excellent performance but NoSQL document model less natural for time-series log queries; migration API less mature

---

## Decision 8 — MJPEG Stream Viewer

**Decision**: Custom `MjpegViewer` widget using Dart `http` package with chunked multipart/x-mixed-replace parsing

**Rationale**: No well-maintained Flutter MJPEG package exists on pub.dev that supports HTTP Basic Auth headers. A thin custom widget (~80 lines) reads the chunked HTTP response, decodes JPEG boundaries, and renders via `Image.memory` — full control over auth headers and error states. Stream opened only on explicit user tap (FR-017).

---

## Decision 9 — Virtual Joystick

**Decision**: Custom `JoystickWidget` using Flutter `GestureDetector` + `Stack` + `AnimatedPositioned`

**Rationale**: The `flutter_joystick` package does not offer the fine-grained velocity normalisation needed (pan/tilt velocity as floats in steps/sec, clamped to configured max). A custom widget (~120 lines) provides precise control over velocity mapping and the zero-velocity-on-release guarantee (FR-022). Timer-based 10 Hz publish loop managed by the parent `OverrideScreen` provider.

---

## Decision 10 — Geo Distance Calculation

**Decision**: Haversine formula implemented in `lib/core/geo_utils.dart`; no external package

**Rationale**: Straight-line (great-circle) distance between two lat/lon points is a ~10-line Haversine formula. Adding `geolocator` solely for distance calculation is overkill; `geolocator` is still used for obtaining the device's current position (GPS). The pure-Dart `geolocator` distance utility (`Geolocator.distanceBetween`) is acceptable as an alternative if already imported.

---

## Backend Dependencies (confirmed from spec)

Three backend extensions are required before mobile features can be fully tested against a live sentry:

| # | Change | Required By | Spec Reference |
|---|--------|-------------|----------------|
| 1 | Add `velocity_vector: {vx: float, vy: float}` to `TelemetryRecord` JSON output | Animated dot movement | FR-004a |
| 2 | Add `fsm_state: "SCAN"\|"ACQUIRE"\|"TRACK"\|"SEARCH"` to `TelemetryRecord` JSON output | Sentry Mode badge; dot fade trigger | FR-010a, FR-004b |
| 3 | Add MQTT subscriber on topic `sentry/command`; execute received `pan_velocity`/`tilt_velocity` on `TurretManager` | Manual joystick override | FR-022, FR-022a |

**Mitigation**: All three can be developed in parallel with the mobile app. The mobile app will parse these fields as nullable during development; mock telemetry with all fields populated will be used for integration testing.
