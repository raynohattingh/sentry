# Data Model: Backend Telemetry Enrichment & Manual Override

**Feature**: `001-backend-telemetry-command`

---

## 1. Modified Entities

### 1.1 `FSMState` (in `jetson/src/types.py`)

**Diff — add `MANUAL_OVERRIDE` value:**

```python
# Before
class FSMState(str, Enum):
    SCAN    = "SCAN"
    SEARCH  = "SEARCH"
    TRACK   = "TRACK"
    ACQUIRE = "ACQUIRE"

# After
class FSMState(str, Enum):
    SCAN            = "SCAN"
    SEARCH          = "SEARCH"
    TRACK           = "TRACK"
    ACQUIRE         = "ACQUIRE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"   # ← new
```

**Notes:**
- `MANUAL_OVERRIDE` is never stored in `SentryBrain._state` — it is only returned by the
  `state` property when `_override` is `True`. The underlying FSM continues running in
  whatever state it was in before the override began.
- The string value `"MANUAL_OVERRIDE"` is what appears in the `fsm_state` field of
  every `sentry/telemetry` message published during an active override.

---

### 1.2 `TelemetryRecord` (in `jetson/src/types.py`)

**Diff — add two fields:**

```python
# Before (existing fields)
@dataclass
class TelemetryRecord:
    session_id:     str
    target_id:      int
    threat_score:   float
    tier:           str
    lat:            float | None
    lon:            float | None
    lrf_distance_m: float | None
    pan_angle:      float
    tilt_angle:     float
    timestamp_utc:  str

# After
@dataclass
class TelemetryRecord:
    session_id:      str
    target_id:       int
    threat_score:    float
    tier:            str
    lat:             float | None
    lon:             float | None
    lrf_distance_m:  float | None
    pan_angle:       float
    tilt_angle:      float
    timestamp_utc:   str
    velocity_vector: dict | None   # ← new: {"vx": float, "vy": float} m/s or null
    fsm_state:       str           # ← new: FSMState.value string, always present
```

**Serialisation note:**  
`dataclasses.asdict()` (used in `TelemetryRecorder.emit()`) automatically serialises both
new fields. `velocity_vector` is a plain `dict` (not a dataclass) so it serialises to a
JSON object `{"vx": ..., "vy": ...}` or `null` directly.

---

### 1.3 `config.py` additions

| Constant | Type | Default | Source | Notes |
|----------|------|---------|--------|-------|
| `SENTRY_ID` | `str` | **none** | `os.environ["SENTRY_ID"]` | Raises `KeyError` on startup if unset |
| `MQTT_USERNAME` | `str` | `""` | `os.environ.get("MQTT_USERNAME", "")` | Empty string → no auth (dev mode) |
| `MQTT_PASSWORD` | `str` | `""` | `os.environ.get("MQTT_PASSWORD", "")` | Empty string → no auth (dev mode) |
| `CAMERA_FPS` | `int` | `25` | `os.environ.get("CAMERA_FPS", "25")` | Must match GST_PIPELINE framerate |
| `CAMERA_HFOV_DEG` | `float` | `120.0` | `os.environ.get("CAMERA_HFOV_DEG", "120.0")` | Calibrate per lens deployment |
| `MQTT_PORT` | `int` | **8883** | `os.environ.get("MQTT_PORT", "8883")` | Changed from 1883 default |

---

## 2. Modified Components

### 2.1 `TelemetryRecorder` (in `jetson/src/telemetry/recorder.py`)

**Method signature change (`record()`):**

```python
# Before
def record(
    self,
    target: TrackedTarget,
    assessment: ThreatAssessment,
    lrf_reading: LRFReading | None,
    position: TurretPosition,
) -> TelemetryRecord:

# After
def record(
    self,
    target: TrackedTarget,
    assessment: ThreatAssessment,
    lrf_reading: LRFReading | None,
    position: TurretPosition,
    fsm_state: FSMState,             # ← new required parameter
) -> TelemetryRecord:
```

**New logic in `record()` body:**

```python
# Velocity conversion (only when LRF distance is available)
velocity_vector: dict | None = None
if lrf_distance and target.velocity_vector != (0.0, 0.0):
    vx_m, vy_m = _convert_velocity(target.velocity_vector, lrf_distance)
    velocity_vector = {"vx": round(vx_m, 4), "vy": round(vy_m, 4)}
elif lrf_distance:
    velocity_vector = {"vx": 0.0, "vy": 0.0}
# else: lrf unavailable → velocity_vector remains None

return TelemetryRecord(
    ...,                             # existing fields unchanged
    velocity_vector=velocity_vector,
    fsm_state=fsm_state.value,
)
```

**Helper function (private, module-level):**

```python
import math

def _convert_velocity(
    v_px_frame: tuple[float, float],
    lrf_m: float,
) -> tuple[float, float]:
    """Convert (vx, vy) pixels/frame to m/s using the pinhole camera model."""
    focal_px = (config.CAMERA_WIDTH / 2.0) / math.tan(
        math.radians(config.CAMERA_HFOV_DEG / 2.0)
    )
    fps = config.CAMERA_FPS
    vx = (v_px_frame[0] * lrf_m) / (focal_px * fps)
    vy = (v_px_frame[1] * lrf_m) / (focal_px * fps)
    return vx, vy
```

---

### 2.2 `SentryBrain` (in `jetson/src/control/sentry_brain.py`)

**New imports:**

```python
import threading
```

**`__init__` additions:**

```python
self._override_lock: threading.Lock = threading.Lock()
self._override: bool = False
```

**Modified `state` property:**

```python
@property
def state(self) -> FSMState:
    with self._override_lock:
        if self._override:
            return FSMState.MANUAL_OVERRIDE
    return self._state
```

**New public methods:**

```python
def enter_override(self) -> None:
    """Engage MANUAL_OVERRIDE — suspends motor control; detection continues."""
    with self._override_lock:
        self._override = True
    logger.info("[BRAIN] MANUAL_OVERRIDE engaged.")

def exit_override(self) -> None:
    """Disengage MANUAL_OVERRIDE — FSM resumes immediately; no SCAN restart."""
    with self._override_lock:
        self._override = False
    logger.info("[BRAIN] MANUAL_OVERRIDE disengaged — resuming autonomous.")
```

---

## 3. New Component: `CommandSubscriber`

### Location

`jetson/src/comms/mqtt.py` — new class alongside `MQTTPublisher`.

### Class design

```python
class CommandSubscriber:
    """MQTT subscriber for sentry/command manual override messages.

    Runs on a dedicated daemon thread. Validates sentry_id, rate-limits at
    20 Hz, implements 3-second safety timeout, and forwards velocities to
    TurretManager via SentryBrain's override API.

    Prefix: ``[COMMAND]``
    """

    COMMAND_TOPIC: str = "sentry/command"
    _SAFETY_TIMEOUT_S: float = 3.0
    _MIN_INTERVAL_S: float = 1.0 / 20        # 50 ms = 20 Hz

    def __init__(
        self,
        brain: SentryBrain,
        turret: TurretManager,
        broker: str | None = None,
        port: int | None = None,
    ) -> None: ...

    def start(self) -> None:
        """Start the subscriber background thread."""

    def stop(self) -> None:
        """Gracefully stop the subscriber thread."""
```

### Sequence diagram (happy path)

```
Mobile App          MQTT Broker         CommandSubscriber Thread     SentryBrain
    │                   │                        │                        │
    │──sentry/command──►│                        │                        │
    │                   │──on_message()─────────►│                        │
    │                   │                        │──validate sentry_id    │
    │                   │                        │──rate-limit check      │
    │                   │                        │──enter_override()─────►│
    │                   │                        │──turret.send_velocity()│
    │                   │                        │                        │
    │  (3s no command)  │                        │                        │
    │                   │                   _timeout_loop                 │
    │                   │                        │──turret.stop()         │
    │                   │                        │──exit_override()──────►│
```

### State machine (CommandSubscriber)

```
IDLE
 │  valid command received
 ▼
OVERRIDE_ACTIVE ──── 3s timeout / zero-vel cmd ──► IDLE
                      (stop + exit_override)
```
