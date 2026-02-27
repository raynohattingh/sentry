# Research: Backend Telemetry Enrichment & Manual Override

**Feature**: `001-backend-telemetry-command`  
**Branch**: `001-backend-telemetry-command`

---

## §1 — TLS with paho-mqtt (FR-022a-1, FR-022a-1b)

### Decision

Enable TLS on both `MQTTPublisher` and `CommandSubscriber` using paho-mqtt's native TLS API.

### Minimal API sequence

```python
import ssl
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
client.tls_set(
    ca_certs=None,
    cert_reqs=ssl.CERT_NONE,          # self-signed broker — skip CA verification
    tls_version=ssl.PROTOCOL_TLS_CLIENT,
)
client.tls_insecure_set(True)         # skip hostname verification
client.connect(self.broker, 8883, keepalive=60)
client.loop_start()                   # works unchanged after tls_set()
```

### Rationale

- Farm deployments use self-signed broker certificates (e.g., Mosquitto with local CA).
  `CERT_NONE` + `tls_insecure_set(True)` allows TLS encryption without requiring a
  trusted CA — suitable for a private local-network broker.
- `loop_start()` is unaffected by TLS setup; it handles the encrypted socket loop identically.
- `username_pw_set()` must be called **before** `connect()` — order matters.
- The `ssl` module is part of the Python stdlib — no new dependency.

### Config constants required (new)

```python
MQTT_USERNAME: str = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD: str = os.environ.get("MQTT_PASSWORD", "")
```

Port change: `MQTT_PORT` default updated from `1883` → `8883`.

---

## §2 — Velocity Pixels/Frame → m/s Conversion (FR-010a-2)

### Decision

Use the **pinhole camera model** to convert `TrackedTarget.velocity_vector` (pixels/frame)
to real-world velocity (m/s).

### Formula

```
focal_length_px = (CAMERA_WIDTH / 2.0) / tan(radians(CAMERA_HFOV_DEG / 2.0))
velocity_m_s    = (velocity_px_frame * lrf_distance_m) / (focal_length_px * CAMERA_FPS)
```

Applied per axis (vx, vy independently):

```python
import math

def pixels_per_frame_to_ms(v_px_frame: float, lrf_m: float) -> float:
    focal = (config.CAMERA_WIDTH / 2.0) / math.tan(math.radians(config.CAMERA_HFOV_DEG / 2.0))
    return (v_px_frame * lrf_m) / (focal * config.CAMERA_FPS)
```

### New config constants

```python
CAMERA_FPS: int = 25                  # matches GST_PIPELINE framerate=25/1
CAMERA_HFOV_DEG: float = 120.0       # wide-angle default; calibrate per deployment
```

> **Note**: `CAMERA_HFOV_DEG = 120.0` is a conservative wide-angle default for a 480×320
> security camera. Accurate values require physical camera calibration (e.g., via checkerboard).
> Making it a config constant (env-overridable) allows per-deployment tuning without code changes.

### Assumptions & failure modes

| Condition | Behaviour |
|-----------|-----------|
| `lrf_distance_m` is `None` (LRF disabled or reading invalid) | Publish `velocity_vector: null` (FR-010a-3) |
| `CAMERA_HFOV_DEG = 0` | Guard: return `null` (division by zero protection) |
| Target velocity = `(0.0, 0.0)` | Publish `{"vx": 0.0, "vy": 0.0}` normally |

---

## §3 — Thread-Safe FSM Override (FR-022a-3, FR-022a-8)

### Decision

Add a private `threading.Lock` + `bool` flag to `SentryBrain`. Expose `enter_override()`
and `exit_override()` as the sole mutation points. The `state` property checks the flag.

### Implementation pattern

```python
# In SentryBrain.__init__:
import threading
self._override_lock = threading.Lock()
self._override: bool = False

def enter_override(self) -> None:
    with self._override_lock:
        self._override = True
    logger.info("[BRAIN] MANUAL_OVERRIDE engaged.")

def exit_override(self) -> None:
    with self._override_lock:
        self._override = False
    logger.info("[BRAIN] MANUAL_OVERRIDE disengaged — resuming autonomous.")

@property
def state(self) -> FSMState:
    with self._override_lock:
        if self._override:
            return FSMState.MANUAL_OVERRIDE
    return self._state       # underlying FSM continues running
```

### Why `threading.Lock` over `threading.Event`

- `Event` is designed for blocking-wait patterns (`event.wait()`). The FSM loop doesn't block
  on the override flag — it reads it every iteration and continues.
- A `bool` protected by `Lock` is semantically clearer: "is override currently active?"
- Lock acquire/release overhead is negligible at 30 Hz FSM loop frequency.

### Rate limiting in CommandSubscriber (FR-022a-6)

Timestamp-based: track `_last_command_time` per subscriber instance.

```python
_MIN_INTERVAL_S: float = 1.0 / 20  # 50 ms → 20 Hz max

def _is_rate_limited(self) -> bool:
    now = time.monotonic()
    if now - self._last_command_time < self._MIN_INTERVAL_S:
        return True
    self._last_command_time = now
    return False
```

Advantages: no state machine, no queue, O(1) per command, thread-local (no shared state).

### Safety timeout (FR-022a-5)

Track `_last_command_received_s` (updated on each accepted command). In a background loop
within `CommandSubscriber`, check if `time.monotonic() - _last_command_received_s > 3.0`
while `_override` is active → call `exit_override()` + `turret.stop()`.

---

## §4 — SENTRY_ID Required Env Var (FR-022a-2)

### Decision

Add `SENTRY_ID` to `config.py` with **no default** — fail at import time if unset.

```python
SENTRY_ID: str = os.environ["SENTRY_ID"]   # KeyError if not set → intentional
```

> Using `os.environ["KEY"]` (not `os.environ.get("KEY")`) ensures the process raises
> `KeyError` at startup rather than silently accepting an empty/wrong ID at runtime.

This is validated in `CommandSubscriber` on every inbound message (FR-022a-2).
