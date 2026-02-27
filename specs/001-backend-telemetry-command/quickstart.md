# Quickstart: Backend Telemetry Enrichment & Manual Override

**Feature**: `001-backend-telemetry-command`  
**Branch**: `001-backend-telemetry-command`

---

## Prerequisites

- Python 3.10+ installed on the Jetson
- [Mosquitto](https://mosquitto.org/) MQTT broker running (local or remote)
- paho-mqtt installed: `pip install paho-mqtt`
- pytest installed: `pip install pytest`

---

## 1. Environment Variables

Set these before starting the Jetson sentry process:

```bash
# Required — process will not start without this
export SENTRY_ID="farm-alpha-01"

# MQTT broker (TLS, port 8883 is the new default)
export MQTT_BROKER="192.168.1.100"
export MQTT_PORT="8883"           # optional if using default 8883
export MQTT_USERNAME="sentry"
export MQTT_PASSWORD="your_password"

# Camera parameters (optional — defaults are sensible for most deployments)
export CAMERA_FPS="25"
export CAMERA_HFOV_DEG="120.0"   # calibrate to your actual lens
```

### Minimal dev/test broker (Mosquitto without TLS)

For local development without TLS, you can set `MQTT_PORT=1883` and leave
`MQTT_USERNAME`/`MQTT_PASSWORD` empty. The sentry process will skip TLS when
`MQTT_PORT` is not 8883.

> **Note**: Production deployments must use port 8883 with valid credentials.

---

## 2. Running the Test Suite

```bash
cd jetson
pytest tests/unit/ -v
```

Expected output includes:

```
tests/unit/test_telemetry_enrichment.py::test_velocity_conversion_basic     PASSED
tests/unit/test_telemetry_enrichment.py::test_velocity_null_when_no_lrf     PASSED
tests/unit/test_telemetry_enrichment.py::test_fsm_state_in_record           PASSED
tests/unit/test_fsm_brain.py::test_enter_override_returns_manual_state      PASSED
tests/unit/test_fsm_brain.py::test_exit_override_resumes_fsm_state          PASSED
tests/unit/test_fsm_brain.py::test_override_thread_safe                     PASSED
tests/unit/test_command_subscriber.py::test_sentry_id_mismatch_discarded    PASSED
tests/unit/test_command_subscriber.py::test_rate_limiting_at_20hz           PASSED
tests/unit/test_command_subscriber.py::test_safety_timeout_stops_turret     PASSED
tests/unit/test_command_subscriber.py::test_zero_vel_exits_override         PASSED
tests/unit/test_telemetry_recorder.py::...                                  PASSED (all existing)
```

---

## 3. Manual Override Test (MQTT CLI)

With the sentry process running, simulate the mobile app joystick:

### Step 1 — Subscribe to telemetry (verify enriched payload)

```bash
mosquitto_sub -h 192.168.1.100 -p 8883 \
  -u sentry -P your_password \
  --cafile /dev/null --insecure \
  -t "sentry/telemetry" | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(f\"fsm={d['fsm_state']} vel={d['velocity_vector']} score={d['threat_score']}\")
"
```

### Step 2 — Send a pan-right command

```bash
mosquitto_pub -h 192.168.1.100 -p 8883 \
  -u sentry -P your_password \
  --cafile /dev/null --insecure \
  -t "sentry/command" \
  -m '{"sentry_id":"farm-alpha-01","pan_velocity":500.0,"tilt_velocity":0.0,"timestamp_utc":"2025-07-15T00:00:00Z"}'
```

Expected: telemetry `fsm_state` changes to `"MANUAL_OVERRIDE"`. Turret pans right.

### Step 3 — Release (zero-velocity stop)

```bash
mosquitto_pub -h 192.168.1.100 -p 8883 \
  -u sentry -P your_password \
  --cafile /dev/null --insecure \
  -t "sentry/command" \
  -m '{"sentry_id":"farm-alpha-01","pan_velocity":0.0,"tilt_velocity":0.0,"timestamp_utc":"2025-07-15T00:00:01Z"}'
```

Expected: telemetry `fsm_state` reverts to `"SCAN"` or `"TRACK"` (whichever the FSM was in).

### Step 4 — Test safety timeout

Send a non-zero command, then wait 4 seconds without sending another. The turret
should stop and FSM should resume within 3.5 seconds.

---

## 4. Verifying Enriched Telemetry Fields

With a stationary target at ~10m distance and LRF enabled:

```bash
mosquitto_sub ... -t "sentry/telemetry" | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    v = d.get('velocity_vector')
    if v:
        print(f\"vx={v['vx']:.3f} m/s  vy={v['vy']:.3f} m/s\")
    else:
        print('velocity_vector: null (no LRF)')
"
```

---

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `KeyError: 'SENTRY_ID'` at startup | `SENTRY_ID` env var not set | `export SENTRY_ID="farm-alpha-01"` |
| Commands not received | TLS mismatch or wrong topic | Check `mosquitto_sub` output; verify broker TLS config |
| `sentry_id mismatch` in logs | Wrong `sentry_id` in command payload | Must match `SENTRY_ID` env var exactly |
| Velocity always `null` | LRF disabled or reading invalid | Check `LRF_ENABLED` and LRF hardware connection |
| Turret not stopping after timeout | Thread not started | Ensure `CommandSubscriber.start()` is called from `main.py` |
