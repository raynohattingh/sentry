# Contract: MQTT Manual Override Command (Outbound)

**Topic**: `sentry/command`  
**Direction**: Mobile App → Backend (Jetson)  
**Protocol**: MQTT over TLS (port 8883)  
**QoS**: 1 (at least once)  
**Encoding**: UTF-8 JSON  
**Publish rate**: 10 Hz (100 ms interval) while joystick held; single zero-velocity message on release  
**Backend status**: ⚠️ **Requires backend implementation** — Jetson Core must subscribe to this topic and execute received velocities on `TurretManager` (FR-022a)

---

## Payload Schema

```json
{
  "sentry_id":     "<string — matches SentryConfig.sentryId>",
  "pan_velocity":  <float steps/sec>,
  "tilt_velocity": <float steps/sec>,
  "timestamp_utc": "<ISO 8601 UTC string>"
}
```

## Velocity Convention

| Field | Positive | Negative | Zero |
|---|---|---|---|
| `pan_velocity` | Pan right | Pan left | Stop pan |
| `tilt_velocity` | Tilt up | Tilt down | Stop tilt |

Units: stepper motor steps per second. Maximum values defined by backend `config.py` `MAX_PAN_VELOCITY` / `MAX_TILT_VELOCITY` constants.

## Example Messages

**Joystick held — pan right, tilt down**:
```json
{
  "sentry_id":     "farm-sentry-01",
  "pan_velocity":  120.0,
  "tilt_velocity": -60.0,
  "timestamp_utc": "2026-02-26T19:05:30.100Z"
}
```

**Joystick released (stop command)**:
```json
{
  "sentry_id":     "farm-sentry-01",
  "pan_velocity":  0.0,
  "tilt_velocity": 0.0,
  "timestamp_utc": "2026-02-26T19:05:30.800Z"
}
```

## Mobile-Side Behaviour

- A `Timer.periodic(Duration(milliseconds: 100), ...)` fires while the joystick is held
- On joystick release (`onPanEnd` / `onLongPressEnd`): timer cancelled, single zero-velocity command published
- On manual override screen `dispose()`: zero-velocity command published as safety stop
- If MQTT connection drops while joystick is held: timer cancelled, joystick widget disabled; reconnection attempted automatically
