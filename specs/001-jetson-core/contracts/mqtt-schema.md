# Contract: MQTT Telemetry Schema

**Branch**: `001-jetson-core` | **Date**: 2026-02-25  
**Owner**: `jetson/src/comms/mqtt.py` + `jetson/src/telemetry/recorder.py`

---

## Transport

| Parameter | Value |
|-----------|-------|
| Protocol | MQTT 3.1.1 |
| QoS | 1 (at least once) |
| Retain | false |
| Encoding | UTF-8 JSON |
| Topic | configurable via `config.MQTT_TOPIC` (default: `sentry/telemetry`) |

---

## Message: Telemetry Record

Published once per tracked target, per control loop iteration, when the target has an active
`ThreatAssessment`.

**Topic**: `sentry/telemetry` (or configured value)

**Payload**:
```json
{
  "session_id":      "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "target_id":       3,
  "threat_score":    85.2,
  "tier":            "HIGH",
  "lat":             -26.123456,
  "lon":             28.567890,
  "lrf_distance_m":  142.5,
  "pan_angle":       12.5,
  "tilt_angle":      -3.2,
  "timestamp_utc":   "2026-02-25T08:18:07.507Z"
}
```

**Field reference**:

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `session_id` | string (UUID4) | No | Unique ID for this container run |
| `target_id` | integer | No | Monotonic tracking ID (resets on restart) |
| `threat_score` | number [0–100] | No | Composite threat score |
| `tier` | string enum | No | `"LOW"`, `"MED"`, or `"HIGH"` |
| `lat` | number (decimal degrees) | **Yes** | `null` when `LRF_ENABLED=false` or invalid reading |
| `lon` | number (decimal degrees) | **Yes** | `null` when `LRF_ENABLED=false` or invalid reading |
| `lrf_distance_m` | number (metres) | **Yes** | `null` when `LRF_ENABLED=false` or invalid reading |
| `pan_angle` | number (degrees) | No | Current turret pan angle; positive = right |
| `tilt_angle` | number (degrees) | No | Current turret tilt angle; positive = up |
| `timestamp_utc` | string (ISO 8601) | No | UTC timestamp of record creation |

---

## Message: System Event (optional, future extension)

Reserved topic: `sentry/events`

Not implemented in this feature. Defined here for forward compatibility.

---

## Failure Handling

- If the MQTT broker is unreachable at startup, the publisher thread queues messages and
  retries with exponential backoff (1s → 2s → 4s → ... → 30s max).
- If the queue fills (`maxsize=500` messages), new messages are **discarded** and a
  `[MQTT] Queue full — message discarded` log is emitted.
- MQTT publish failures are **non-fatal** — the local JSON-lines log always writes
  regardless of MQTT status.
- Consumers must tolerate `null` values for GPS fields.
