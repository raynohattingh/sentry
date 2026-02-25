# Data Model: Sentry Jetson Core

**Branch**: `001-jetson-core` | **Date**: 2026-02-25

All entities are Python dataclasses or typed dicts. No database — data flows between modules
in-memory; only `TelemetryRecord` is serialised to disk and MQTT.

---

## Entity: `Frame`

Produced by `vision/camera.py` on each captured frame.

```python
@dataclass
class Frame:
    data: np.ndarray          # BGR image array, shape (320, 480, 3)
    timestamp_utc: str        # ISO 8601 UTC timestamp at capture
    width: int = 480
    height: int = 320
```

**Validation rules**:
- `data.shape == (height, width, 3)` — enforced at construction in tests
- `timestamp_utc` is populated by the capture thread immediately after `cap.read()`

---

## Entity: `Detection`

Produced by `vision/detector.py` for each YOLO bounding box with class "Person".

```python
@dataclass
class Detection:
    bbox: tuple[int, int, int, int]   # (x1, y1, x2, y2) in pixels
    confidence: float                  # 0.0 – 1.0
    centroid: tuple[int, int]          # (cx, cy) derived from bbox
    area: int                          # (x2-x1) * (y2-y1), used for distance estimate
```

**Validation rules**:
- `confidence >= config.CONF_THRESHOLD` (filtered by YOLO before emission)
- `centroid` is always `((x1+x2)//2, (y1+y2)//2)` — computed from bbox, not stored separately

---

## Entity: `TrackedTarget`

Produced by `vision/tracker.py`. Enriches a `Detection` with a persistent ID and motion state.

```python
@dataclass
class TrackedTarget:
    target_id: int                         # Monotonic int, resets to 0 on container restart
    centroid: tuple[int, int]              # Latest centroid (cx, cy)
    bbox: tuple[int, int, int, int]        # Latest bounding box
    velocity_vector: tuple[float, float]   # (vx, vy) pixels/frame; (0.0, 0.0) on first frame
    disappeared_frames: int                # Frames since last matching detection
    area: int                              # Latest bbox area (proxy for distance)
    last_seen_utc: str                     # ISO 8601 UTC of last matched frame
```

**State rules**:
- `target_id` is assigned sequentially from a class-level counter that resets on restart.
- `disappeared_frames` increments every frame without a match; resets to 0 on re-match.
- A target is deregistered when `disappeared_frames > config.MAX_DISAPPEARED`.
- `velocity_vector` is the centroid delta between the last two matched frames.

---

## Entity: `ThreatAssessment`

Produced by `control/threat_tracker.py` from a `TrackedTarget`.

```python
@dataclass
class ThreatAssessment:
    target_id: int
    threat_score: float          # 0.0 – 100.0
    tier: ThreatTier             # LOW | MED | HIGH (enum)
    lrf_required: bool           # True if tier is MED or HIGH and LRF_ENABLED
    recommended_state: FSMState  # SCAN | TRACK | ACQUIRE | SEARCH
```

**Scoring formula** (configurable weights):

```
score = (
    W_DISTANCE   * distance_score(area)       +  # larger bbox = closer = higher
    W_MOTION     * motion_score(velocity)     +  # higher speed = higher
    W_GROUPING   * grouping_score(n_targets)  +  # more targets = higher
    W_TIME_OF_DAY * time_score(hour)          +  # night hours = higher
)
clamped to [0, 100]
```

**Tier boundaries** (configurable):
- `HIGH`: `score >= HIGH_THREAT_THRESHOLD` (default 80) → ACQUIRE state, continuous LRF
- `MED`: `score >= MED_THREAT_THRESHOLD` (default 40) → TRACK state, sampled LRF
- `LOW`: `score < MED_THREAT_THRESHOLD` → SCAN state, no LRF

---

## Entity: `FSMState` (Enum)

Used in `control/sentry_brain.py`.

```python
class FSMState(Enum):
    SCAN    = "SCAN"     # No active target; oscillating pan sweep
    TRACK   = "TRACK"    # Active target, MED threat; sampled LRF
    ACQUIRE = "ACQUIRE"  # Active target, HIGH threat; continuous LRF, hard lock
    SEARCH  = "SEARCH"   # Target lost; arc sweep around last-known position
```

**Transition rules**:
- `SCAN → TRACK`: threat score enters MED tier (immediate)
- `SCAN → ACQUIRE`: threat score enters HIGH tier (immediate)
- `TRACK → ACQUIRE`: threat score enters HIGH tier (immediate)
- `TRACK → SCAN`: score drops below MED AND `min_dwell_ms[TRACK]` elapsed
- `ACQUIRE → TRACK`: score drops to MED AND `min_dwell_ms[ACQUIRE]` elapsed
- `ACQUIRE → SCAN`: score drops below MED AND `min_dwell_ms[ACQUIRE]` elapsed
- `* → SEARCH`: target disappears beyond `MAX_DISAPPEARED` frames (immediate from TRACK/ACQUIRE)
- `SEARCH → TRACK`: target re-acquired during sweep (immediate)
- `SEARCH → SCAN`: `search_timeout` elapses without re-acquisition

---

## Entity: `TurretCommand`

Produced by `control/sentry_brain.py` or `control/pid.py`; consumed by `hardware/arduino_link.py`.

```python
@dataclass
class TurretCommand:
    pan_velocity: float   # steps/sec; positive = right, negative = left
    tilt_velocity: float  # steps/sec; positive = up, negative = down
    fire_lrf: bool        # True triggers an `L\n` command on the same loop tick
    timestamp_utc: str    # For telemetry / debug logging
```

**Constraints**:
- `abs(pan_velocity) <= config.PAN_MAX`
- `abs(tilt_velocity) <= config.TILT_MAX`
- Velocity tapering applied before this entity is created (in `sentry_brain.py`)

---

## Entity: `TurretPosition`

Maintained by `hardware/arduino_link.py` from incoming `POS <pan_steps> <tilt_steps>` messages.

```python
@dataclass
class TurretPosition:
    pan_steps: int    # Cumulative step count, signed; positive = right
    tilt_steps: int   # Cumulative step count, signed; positive = up
    received_utc: str # ISO 8601 UTC of last POS message
```

---

## Entity: `LRFReading`

Produced by `hardware/arduino_link.py` when a `DIST <float>` message is received.

```python
@dataclass
class LRFReading:
    distance_m: float | None   # Measured distance in metres; None if invalid or LRF_ENABLED=False
    valid: bool                 # False if message was malformed or LRF disabled
    received_utc: str           # ISO 8601 UTC of message receipt
```

---

## Entity: `TelemetryRecord`

Produced by `telemetry/recorder.py`. Serialised to JSON-lines log and MQTT.

```python
@dataclass
class TelemetryRecord:
    session_id: str             # UUID4 generated at startup; immutable for lifetime of process
    target_id: int              # From TrackedTarget
    threat_score: float         # From ThreatAssessment
    tier: str                   # "LOW" | "MED" | "HIGH"
    lat: float | None           # None when LRF_ENABLED=False or reading invalid
    lon: float | None           # None when LRF_ENABLED=False or reading invalid
    lrf_distance_m: float | None  # None when LRF_ENABLED=False or reading invalid
    pan_angle: float            # Current turret pan angle in degrees (derived from pan_steps)
    tilt_angle: float           # Current turret tilt angle in degrees (derived from tilt_steps)
    timestamp_utc: str          # ISO 8601 UTC at record creation
```

**Serialisation**: `dataclasses.asdict()` → `json.dumps()` → newline appended to log file.

**JSON example**:
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "target_id": 3,
  "threat_score": 85.2,
  "tier": "HIGH",
  "lat": -26.1234,
  "lon": 28.5678,
  "lrf_distance_m": 142.5,
  "pan_angle": 12.5,
  "tilt_angle": -3.2,
  "timestamp_utc": "2026-02-25T08:18:07.507Z"
}
```

**Null example** (LRF disabled):
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "target_id": 1,
  "threat_score": 55.0,
  "tier": "MED",
  "lat": null,
  "lon": null,
  "lrf_distance_m": null,
  "pan_angle": 0.0,
  "tilt_angle": 0.0,
  "timestamp_utc": "2026-02-25T08:19:00.000Z"
}
```

---

## Entity Relationships

```
Frame ──produces──► Detection[] ──feeds──► CentroidTracker
                                               │
                                          TrackedTarget[]
                                               │
                                         ThreatAssessment
                                               │
                                          SentryBrain (FSM)
                                          ┌────┴────┐
                                     TurretCommand   LRFRequest
                                          │               │
                                    ArduinoLink      ArduinoLink
                                          │               │
                                    TurretPosition   LRFReading
                                               │
                                         TelemetryRecord ──► JSON-lines log
                                                          ──► MQTT broker
```

---

## State Persistence (Boot Failure Counter)

A small JSON file persists the boot failure counter across Docker restarts (FR-030).

**Location**: Configurable via `config.BOOT_STATE_PATH` (default: `/app/state/boot_state.json`)

**Schema**:
```json
{
  "consecutive_failures": 2,
  "last_failure_utc": "2026-02-25T08:00:00.000Z"
}
```

**Lifecycle**:
1. At startup: read counter. If `>= max_boot_failures` → `os.system("reboot")`.
2. On fatal GPU error: increment counter and write file, then `sys.exit(1)`.
3. On successful main loop entry: reset counter to 0 and write file.
