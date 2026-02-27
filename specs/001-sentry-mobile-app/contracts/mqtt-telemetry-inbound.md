# Contract: MQTT Telemetry (Inbound)

**Topic**: `sentry/telemetry`  
**Direction**: Backend (Jetson) → Mobile App  
**Protocol**: MQTT over TLS (port 8883)  
**QoS**: 1 (at least once)  
**Encoding**: UTF-8 JSON

---

## Payload Schema

```json
{
  "session_id":      "<UUID4 string>",
  "target_id":       <integer>,
  "threat_score":    <float 0.0–100.0>,
  "tier":            "LOW" | "MED" | "HIGH",
  "lat":             <float decimal degrees> | null,
  "lon":             <float decimal degrees> | null,
  "lrf_distance_m":  <float metres> | null,
  "pan_angle":       <float degrees>,
  "tilt_angle":      <float degrees>,
  "timestamp_utc":   "<ISO 8601 UTC string>",
  "velocity_vector": { "vx": <float m/s>, "vy": <float m/s> } | null,
  "fsm_state":       "SCAN" | "ACQUIRE" | "TRACK" | "SEARCH" | null
}
```

## Example Message

```json
{
  "session_id":      "a1b2c3d4-0000-4000-8000-000000000001",
  "target_id":       3,
  "threat_score":    82.4,
  "tier":            "HIGH",
  "lat":             -26.204103,
  "lon":             28.047305,
  "lrf_distance_m":  47.2,
  "pan_angle":       12.5,
  "tilt_angle":      -3.1,
  "timestamp_utc":   "2026-02-26T19:00:00.000Z",
  "velocity_vector": { "vx": 0.8, "vy": -0.3 },
  "fsm_state":       "TRACK"
}
```

## Field Notes

| Field | Required | Backend Status | Mobile Behaviour if Absent |
|---|---|---|---|
| `session_id` | Yes | Existing | Parse error → drop message |
| `target_id` | Yes | Existing | Parse error → drop message |
| `threat_score` | Yes | Existing | Parse error → drop message |
| `tier` | Yes | Existing | Unknown value → default `LOW` |
| `lat` / `lon` | No | Existing | null → "Location Unknown" in log; no map pin |
| `lrf_distance_m` | No | Existing | null → "—" in log |
| `pan_angle` / `tilt_angle` | Yes | Existing | Parse error → drop message |
| `timestamp_utc` | Yes | Existing | Parse error → drop message |
| `velocity_vector` | No | **Backend extension required** | null → snap position, no animation |
| `fsm_state` | No | **Backend extension required** | null → Sentry Mode badge shows "—"; fade on telemetry loss only |

## Threat Tier Thresholds (from backend `config.py`)

| Tier | Condition | Mobile Dot Colour |
|---|---|---|
| `LOW` | `threat_score < 40.0` | Yellow `#FFD700` |
| `MED` | `40.0 ≤ threat_score < 80.0` | Orange `#FF8C00` |
| `HIGH` | `threat_score ≥ 80.0` | Red `#FF1E1E` + glow |
