# Contract: sentry/telemetry (Outbound — Enriched)

**Topic**: `sentry/telemetry`  
**Direction**: Jetson → MQTT Broker → Mobile App  
**Format**: UTF-8 JSON  
**QoS**: 0 (fire and forget)  
**Feature**: `001-backend-telemetry-command` (enriches existing schema)

---

## Schema

```json
{
  "session_id":      "string (UUID4)",
  "target_id":       "integer",
  "threat_score":    "float [0.0, 100.0]",
  "tier":            "string: LOW | MED | HIGH",
  "lat":             "float | null",
  "lon":             "float | null",
  "lrf_distance_m":  "float | null",
  "pan_angle":       "float (degrees)",
  "tilt_angle":      "float (degrees)",
  "timestamp_utc":   "string (ISO 8601, Z suffix)",
  "velocity_vector": "object | null",
  "fsm_state":       "string"
}
```

### `velocity_vector` sub-schema

```json
{
  "vx": "float (m/s, positive = rightward)",
  "vy": "float (m/s, positive = downward)"
}
```

- **Present and non-null** when LRF distance is available and a target is actively tracked.
- **`null`** when LRF is disabled, LRF reading is invalid, or no target is tracked.
- **Never omitted** from the payload (always either an object or `null`).

### `fsm_state` valid values

| Value | Meaning |
|-------|---------|
| `"SCAN"` | No target; sentry oscillating |
| `"SEARCH"` | Target recently lost; searching arc |
| `"TRACK"` | Target tracked; moderate confidence |
| `"ACQUIRE"` | Target tracked; high confidence (LRF firing) |
| `"MANUAL_OVERRIDE"` | Operator has taken manual control |

- **Always present** — never null or omitted.

---

## Example Payload (active tracking, LRF available)

```json
{
  "session_id":      "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "target_id":       3,
  "threat_score":    87.4,
  "tier":            "HIGH",
  "lat":             -26.20424,
  "lon":             28.04363,
  "lrf_distance_m":  42.5,
  "pan_angle":       12.5,
  "tilt_angle":      -3.2,
  "timestamp_utc":   "2025-07-15T03:14:12.456Z",
  "velocity_vector": {"vx": 1.23, "vy": -0.04},
  "fsm_state":       "ACQUIRE"
}
```

## Example Payload (no LRF)

```json
{
  "session_id":      "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "target_id":       1,
  "threat_score":    55.0,
  "tier":            "MED",
  "lat":             null,
  "lon":             null,
  "lrf_distance_m":  null,
  "pan_angle":       5.0,
  "tilt_angle":      0.0,
  "timestamp_utc":   "2025-07-15T03:14:13.100Z",
  "velocity_vector": null,
  "fsm_state":       "TRACK"
}
```

## Example Payload (manual override active)

```json
{
  "session_id":      "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "target_id":       0,
  "threat_score":    0.0,
  "tier":            "LOW",
  "lat":             null,
  "lon":             null,
  "lrf_distance_m":  null,
  "pan_angle":       3.0,
  "tilt_angle":      1.5,
  "timestamp_utc":   "2025-07-15T03:14:14.200Z",
  "velocity_vector": null,
  "fsm_state":       "MANUAL_OVERRIDE"
}
```

---

## Backward Compatibility

Mobile app consumers receiving this schema must:
1. Treat `velocity_vector: null` as "velocity unknown" (render marker as stationary).
2. Handle all five `fsm_state` values listed above, including the new `MANUAL_OVERRIDE`.
3. Existing fields (`session_id` through `timestamp_utc`) are **unchanged** — backward-compatible.
