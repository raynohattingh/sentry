# Data Model: Farm Sentry Mobile App

**Phase 1 Output** | Branch: `001-sentry-mobile-app`

All Flutter-side entities, their Dart types, validation rules, and state transitions.

---

## Entity 1 — `SentryConfig`

Persisted via `flutter_secure_storage` (credentials) and `SharedPreferences` (non-sensitive config).

| Field | Dart Type | Constraints | Storage |
|---|---|---|---|
| `brokerId` | `String` | Non-empty; hostname or IPv4 | SharedPreferences |
| `brokerPort` | `int` | 1–65535; default `8883` | SharedPreferences |
| `mqttUsername` | `String` | Non-empty | Keychain/Keystore |
| `mqttPassword` | `String` | Non-empty | Keychain/Keystore |
| `sentryId` | `String` | Non-empty; used as MQTT client ID suffix | SharedPreferences |
| `sentryLat` | `double?` | WGS-84 decimal degrees; null until calibrated | SharedPreferences |
| `sentryLon` | `double?` | WGS-84 decimal degrees; null until calibrated | SharedPreferences |
| `trueNorthOffsetDeg` | `double` | −180.0 to +180.0; default `0.0` | SharedPreferences |
| `heartbeatTimeoutSec` | `int` | 5–120; default `10` | SharedPreferences |
| `alertRetentionDuration` | `Duration` | Options: 24 h / 7 d / 30 d; default 7 d | SharedPreferences |
| `videoStreamHost` | `String` | Hostname or IPv4; defaults to `brokerId` | SharedPreferences |
| `videoStreamPort` | `int` | 1–65535; default `5000` | SharedPreferences |
| `videoUsername` | `String` | Non-empty | Keychain/Keystore |
| `videoPassword` | `String` | Non-empty | Keychain/Keystore |

**Validation rules**:
- Setup flow must collect all mandatory fields before saving; form shown again if any are missing
- TLS is always active — port `1883` is rejected with a warning prompting `8883`
- `sentryLat`/`sentryLon` may be null; map centres on device location until calibrated

---

## Entity 2 — `TelemetryRecord`

Parsed from JSON received on MQTT topic `sentry/telemetry`. Immutable value object.

| Field | Dart Type | Source | Notes |
|---|---|---|---|
| `sessionId` | `String` | Backend | UUID4; constant per sentry process restart |
| `targetId` | `int` | Backend | Monotonically incrementing per session |
| `threatScore` | `double` | Backend | 0.0–100.0 |
| `tier` | `ThreatTier` (enum) | Backend | `low` \| `med` \| `high` |
| `lat` | `double?` | Backend | null when LRF unavailable |
| `lon` | `double?` | Backend | null when LRF unavailable |
| `lrfDistanceM` | `double?` | Backend | null when LRF unavailable |
| `panAngle` | `double` | Backend | Degrees |
| `tiltAngle` | `double` | Backend | Degrees |
| `timestampUtc` | `DateTime` | Backend | Parsed from ISO 8601 string |
| `velocityVector` | `VelocityVector?` | Backend (extension) | `{vx, vy}` in m/s; null during transition period |
| `fsmState` | `FsmState?` | Backend (extension) | `scan`\|`acquire`\|`track`\|`search`; null during transition |

**Parsing rules**:
- Unknown `tier` values → treated as `ThreatTier.low`; logged as warning
- Unknown `fsmState` values → treated as `null`; Sentry Mode badge shows "Unknown"
- `velocityVector` null → dot position updates without animation (snap to new position)
- Malformed JSON → record dropped silently; counter incremented for diagnostics

### `ThreatTier` enum (Dart)

```dart
enum ThreatTier { low, med, high }
// Thresholds: low < 40.0, med 40.0–79.9, high ≥ 80.0
```

### `FsmState` enum (Dart)

```dart
enum FsmState { scan, acquire, track, search }
```

### `VelocityVector` value object

```dart
class VelocityVector {
  final double vx; // m/s; positive = east
  final double vy; // m/s; positive = north
}
```

---

## Entity 3 — `ThreatMarker`

Runtime map entity derived from `TelemetryRecord`. Lives in Riverpod state; NOT persisted.

| Field | Dart Type | Notes |
|---|---|---|
| `targetId` | `int` | Unique key per marker |
| `lat` | `double` | Last known latitude |
| `lon` | `double` | Last known longitude |
| `tier` | `ThreatTier` | Drives colour |
| `threatScore` | `double` | Displayed on tap |
| `markerState` | `MarkerState` (enum) | `active` \| `fading` \| `removed` |
| `lastSeen` | `DateTime` | Set when state transitions to `fading` |
| `velocityVector` | `VelocityVector?` | Used for animation interpolation |
| `distanceToUserM` | `double?` | Recalculated on each location update; null if permission denied |
| `isSelected` | `bool` | True when tapped; drives highlight style |

### `MarkerState` lifecycle

```
active  ──(fsmState == SEARCH or telemetry loss)──►  fading
fading  ──(30 seconds elapsed)──────────────────────►  removed
```

**Colour mapping**:
- `ThreatTier.low` → `Color(0xFFFFD700)` (yellow)
- `ThreatTier.med` → `Color(0xFFFF8C00)` (orange)
- `ThreatTier.high` → `Color(0xFFFF1E1E)` (red) + pulsing glow

---

## Entity 4 — `AlertLogEntry`

Persisted in SQLite via `drift`. One row per `TelemetryRecord` received.

| Field | Dart Type | Column | Notes |
|---|---|---|---|
| `id` | `int` | `INTEGER PRIMARY KEY` | Auto-increment |
| `targetId` | `int` | `target_id INTEGER` | From telemetry |
| `sessionId` | `String` | `session_id TEXT` | From telemetry |
| `timestampUtc` | `DateTime` | `timestamp_utc INTEGER` (Unix ms) | Indexed for range queries |
| `tier` | `String` | `tier TEXT` | `"LOW"` \| `"MED"` \| `"HIGH"` |
| `threatScore` | `double` | `threat_score REAL` | |
| `lat` | `double?` | `lat REAL` | Nullable |
| `lon` | `double?` | `lon REAL` | Nullable |
| `lrfDistanceM` | `double?` | `lrf_distance_m REAL` | Nullable |
| `panAngle` | `double` | `pan_angle REAL` | Secondary display |
| `tiltAngle` | `double` | `tilt_angle REAL` | Secondary display |
| `distanceToUserM` | `double?` | `distance_to_user_m REAL` | Calculated at receipt time; null if no location |

**Indices**: `timestamp_utc` (DESC) for panel display; `(session_id, target_id)` for dot-tap scroll lookup.

**Purge rule**: `DELETE FROM alert_log WHERE timestamp_utc < (NOW - retentionDuration)`. Executed on app foreground.

---

## Entity 5 — `NotificationPreferences`

Persisted via `SharedPreferences`.

| Field | Dart Type | Default | Notes |
|---|---|---|---|
| `lowTierMode` | `NotificationMode` | `silent` | `alarm`\|`notification`\|`silent`\|`disabled` |
| `medTierMode` | `NotificationMode` | `notification` | |
| `highTierMode` | `NotificationMode` | `alarm` | |
| `minScoreThreshold` | `double` | `0.0` | 0–100; alerts below this score suppressed |

### `NotificationMode` enum

```dart
enum NotificationMode { alarm, notification, silent, disabled }
```

---

## Entity 6 — `ManualCommand`

Published to MQTT topic `sentry/command`. Ephemeral; not persisted.

| Field | Dart Type | MQTT JSON key | Constraints |
|---|---|---|---|
| `sentryId` | `String` | `sentry_id` | From `SentryConfig.sentryId` |
| `panVelocity` | `double` | `pan_velocity` | Steps/sec; clamped to configured max; positive = right |
| `tiltVelocity` | `double` | `tilt_velocity` | Steps/sec; clamped to configured max; positive = up |
| `timestampUtc` | `String` | `timestamp_utc` | ISO 8601 UTC; generated at publish time |

**Publish rate**: 10 Hz (100 ms interval via `Timer.periodic`) while joystick is held.  
**On release**: Single zero-velocity command `{pan_velocity: 0.0, tilt_velocity: 0.0}` published immediately.  
**On screen exit**: Zero-velocity command sent before `dispose()`.

---

## Entity 7 — `ConnectionState`

Derived runtime state. Managed by `MqttService`; exposed via Riverpod `StateProvider`.

```dart
enum SentryConnectionState { online, reconnecting, offline }
```

**Transition rules**:
- `online` → `reconnecting`: MQTT `onDisconnected` callback fires
- `reconnecting` → `online`: MQTT `onConnected` callback fires
- `online` → `offline`: No telemetry received for `heartbeatTimeoutSec` seconds (timer-based)
- `offline` → `reconnecting`: Auto-reconnect attempt initiated

---

## Riverpod Provider Dependency Graph

```
SentryConfigProvider (StateNotifierProvider)
  └─► MqttServiceProvider (Provider — singleton service)
        └─► TelemetryStreamProvider (StreamProvider<TelemetryRecord>)              [telemetry_provider.dart]
              ├─► ThreatMarkersProvider (StateNotifierProvider<Map<int, ThreatMarker>>)  [telemetry_provider.dart]
              │     └─► SelectedMarkerProvider (StateProvider<int?>)               [selection_provider.dart]
              ├─► AlertLogProvider (StreamProvider — drift watch query)
              ├─► SentryModeProvider (StateProvider<FsmState?>)                    [telemetry_provider.dart]
              └─► ConnectionStateProvider (StateNotifierProvider<SentryConnectionState>)  [connection_provider.dart]
                    └─► (calls ThreatMarkersNotifier.fadeAll() on offline transition)

LocationServiceProvider (Provider — singleton service)
  └─► UserLocationProvider (StreamProvider<LatLng?>)
        └─► DistanceCalculationProvider (reads ThreatMarkersProvider + UserLocationProvider)
```
