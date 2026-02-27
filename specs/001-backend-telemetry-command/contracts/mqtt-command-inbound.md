# Contract: sentry/command (Inbound — Manual Override)

**Topic**: `sentry/command`  
**Direction**: Mobile App → MQTT Broker → Jetson `CommandSubscriber`  
**Format**: UTF-8 JSON  
**QoS**: 0 (fire and forget)  
**Feature**: `001-backend-telemetry-command`

---

## Schema

```json
{
  "sentry_id":      "string (must match SENTRY_ID env var on Jetson)",
  "pan_velocity":   "float (steps/sec; clamped to ±PAN_MAX by receiver)",
  "tilt_velocity":  "float (steps/sec; clamped to ±TILT_MAX by receiver)",
  "timestamp_utc":  "string (ISO 8601, Z suffix)"
}
```

### Field descriptions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `sentry_id` | string | ✅ | Must exactly match `config.SENTRY_ID` on the Jetson. Commands with wrong `sentry_id` are silently discarded with a WARNING log. |
| `pan_velocity` | float | ✅ | Horizontal motor velocity in steps/sec. Positive = pan right. Clamped to `[-PAN_MAX, +PAN_MAX]` by `CommandSubscriber`. |
| `tilt_velocity` | float | ✅ | Vertical motor velocity in steps/sec. Positive = tilt up. Clamped to `[-TILT_MAX, +TILT_MAX]` by `CommandSubscriber`. |
| `timestamp_utc` | string | ✅ | Publisher timestamp; used for logging only. Not used for timeout computation. |

---

## Zero-Velocity Command (Override Exit)

A command where **both** `pan_velocity` and `tilt_velocity` are `0.0` is treated as an
**explicit override exit** — the system immediately returns to autonomous FSM operation,
regardless of the 3-second safety timeout.

```json
{
  "sentry_id":     "farm-alpha-01",
  "pan_velocity":  0.0,
  "tilt_velocity": 0.0,
  "timestamp_utc": "2025-07-15T03:14:20.000Z"
}
```

---

## Rate Limiting

The `CommandSubscriber` accepts a maximum of **20 commands per second** (one per 50 ms
window). Commands arriving within 50 ms of the previous accepted command are silently
discarded. The mobile app joystick should emit at ≤ 20 Hz to avoid unnecessary drops.

---

## Safety Timeout

If no command is received for **3 consecutive seconds** while the sentry is in
`MANUAL_OVERRIDE` mode (e.g., mobile app network drop), the Jetson will:
1. Issue a zero-velocity stop to the turret motors.
2. Return the FSM to autonomous tracking immediately (no SCAN restart).

---

## Receiver Behaviour Summary

| Condition | Action |
|-----------|--------|
| `sentry_id` mismatch | Discard + `[COMMAND] WARNING: sentry_id mismatch` log |
| Malformed JSON | Discard + `[COMMAND] WARNING: malformed payload` log |
| Rate-limited (within 50 ms) | Discard silently |
| Valid command (first in session) | `brain.enter_override()` → clamp + send velocities |
| Valid command (continuing session) | Clamp + send velocities; reset 3s timeout |
| Zero-velocity command | `turret.stop()` → `brain.exit_override()` |
| 3s without command | `turret.stop()` → `brain.exit_override()` |

---

## Example Payloads

### Pan right at half speed

```json
{
  "sentry_id":     "farm-alpha-01",
  "pan_velocity":  750.0,
  "tilt_velocity": 0.0,
  "timestamp_utc": "2025-07-15T03:14:15.000Z"
}
```

### Diagonal movement

```json
{
  "sentry_id":     "farm-alpha-01",
  "pan_velocity":  300.0,
  "tilt_velocity": -200.0,
  "timestamp_utc": "2025-07-15T03:14:16.050Z"
}
```

### Explicit override exit

```json
{
  "sentry_id":     "farm-alpha-01",
  "pan_velocity":  0.0,
  "tilt_velocity": 0.0,
  "timestamp_utc": "2025-07-15T03:14:19.000Z"
}
```

---

## Mobile App Reference

This contract is the server-side view of the payload published by the Flutter app in:
`app/lib/features/override/` — `ManualOverrideScreen` joystick callbacks.

The `ManualCommand` dataclass in `jetson/src/types.py` mirrors this schema exactly.
