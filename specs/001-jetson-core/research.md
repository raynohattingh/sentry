# Research: Sentry Jetson Core

**Branch**: `001-jetson-core` | **Date**: 2026-02-25  
**Status**: ✅ All NEEDS CLARIFICATION resolved — ready for Phase 1 design

---

## Decision 1: Centroid Tracking Algorithm

**Decision**: `scipy.spatial.distance.cdist` with `OrderedDict` ID mapping and per-object
disappearance counter.

**Rationale**: The PyImageSearch centroid tracker is the canonical reference for this pattern.
It uses `cdist` to build an O(n²) distance matrix between existing tracked centroids and new
detection centroids, then assigns detections by minimum distance. The `disappeared` counter
increments each frame a tracked object has no match; when it exceeds `max_disappeared`, the
object is deregistered. On re-match after a brief disappearance, the counter resets to zero —
this is the occlusion recovery mechanism.

**Algorithm sketch**:
```python
D = dist.cdist(existing_centroids, input_centroids)  # shape: [n_tracked, n_detected]
rows = D.min(axis=1).argsort()
cols = D[rows].argmin(axis=1)
for row, col in zip(rows, cols):
    if D[row, col] > MAX_DISTANCE: continue
    objects[id_at_row] = input_centroids[col]
    disappeared[id_at_row] = 0  # re-identified
```

**Alternatives considered**:
- **SORT / ByteTrack**: More sophisticated Kalman-filter-based trackers. Rejected: adds
  significant complexity; overkill for a single-camera, low-crowd-density farm perimeter;
  no additional dependency justified.
- **Manual nested loop**: Functionally equivalent but 10–100× slower on numpy arrays and
  more error-prone to implement correctly.

---

## Decision 2: FSM Dwell Timer Implementation

**Decision**: Enum-based FSM where each state transition records `state_entered_ns =
time.monotonic_ns()`. Downward transitions check `elapsed_ms >= min_dwell_ms` before
permitting; upward transitions are unconditional.

**Rationale**: `time.monotonic_ns()` is immune to wall-clock adjustments (NTP, GPS sync)
that could corrupt dwell calculations. Storing dwell config in the FSM class (loaded from
`config.py`) keeps the policy co-located with the state. Using an `Enum` for states gives
exhaustive `match`/`if` checking and prevents invalid state strings.

**Pattern**:
```python
class FSMState(Enum):
    SCAN = "SCAN"
    TRACK = "TRACK"
    ACQUIRE = "ACQUIRE"
    SEARCH = "SEARCH"

# In SentryBrain:
self.state: FSMState = FSMState.SCAN
self.state_entered_ns: int = time.monotonic_ns()

def _transition(self, new_state: FSMState) -> bool:
    threat_order = {FSMState.SCAN: 0, FSMState.SEARCH: 1,
                    FSMState.TRACK: 2, FSMState.ACQUIRE: 3}
    is_upward = threat_order[new_state] > threat_order[self.state]
    if not is_upward:
        elapsed_ms = (time.monotonic_ns() - self.state_entered_ns) / 1_000_000
        if elapsed_ms < self.min_dwell_ms[self.state]:
            return False
    self.state = new_state
    self.state_entered_ns = time.monotonic_ns()
    return True
```

**Alternatives considered**:
- **time.time()**: Rejected — susceptible to wall-clock jumps from NTP or GPS PPS signal.
- **threading.Timer**: Rejected — adds thread management overhead; simple elapsed check
  achieves the same effect inline.

---

## Decision 3: GPS Computation Formula

**Decision**: Pure-stdlib **Haversine** formula — no external library.

**Rationale**: At distances ≤ 2 km, Haversine yields ±2 m accuracy. The spec acceptance
criterion (SC-004) requires ±10 m. Haversine satisfies this with a 5× safety margin using
only Python's `math` module — no pip install required on the offline Jetson.

**Formula** (target GPS from sentry + azimuth + distance):
```python
import math

def compute_target_gps(
    sentry_lat: float, sentry_lon: float,
    azimuth_deg: float, distance_m: float,
) -> tuple[float, float]:
    R = 6_371_000  # Earth radius, metres
    az = math.radians(azimuth_deg)
    d = distance_m / R
    lat1 = math.radians(sentry_lat)
    lon1 = math.radians(sentry_lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d) +
        math.cos(lat1) * math.sin(d) * math.cos(az)
    )
    lon2 = lon1 + math.atan2(
        math.sin(az) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)
```

**Alternatives considered**:
- **Vincenty (geopy)**: ±0.5 m accuracy but requires `geopy` library, iterative convergence,
  and internet access for install. Rejected: over-specified for ±10 m requirement.
- **pyproj**: Rejected — requires PROJ data files; not reliably available in the Docker base.

---

## Decision 4: MQTT Non-Blocking Client Pattern

**Decision**: Daemon background thread with `queue.Queue` for publish. `publish_async()` is
fire-and-forget; broker unavailability is handled transparently via exponential backoff reconnect
in the background thread.

**Pattern**:
```python
class MQTTPublisher:
    def __init__(self, host, port, topic):
        self._queue: queue.Queue[str] = queue.Queue(maxsize=500)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def publish_async(self, payload: str) -> None:
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            logger.warning("[MQTT] Queue full — message discarded")

    def _run(self) -> None:
        backoff = 1
        while True:
            try:
                self._client.connect(self._host, self._port, keepalive=10)
                backoff = 1
                while True:
                    payload = self._queue.get(timeout=0.1)
                    self._client.publish(self._topic, payload, qos=1)
            except Exception as e:
                logger.warning(f"[MQTT] Error: {e} — retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
```

**Alternatives considered**:
- **`client.loop_start()` (paho background loop)**: Viable but harder to control reconnect
  backoff; non-fatal error handling is less explicit. Rejected in favour of manual thread.
- **Synchronous publish in main loop**: Rejected — any broker timeout blocks the control loop,
  violating the <100 ms latency requirement.

---

## Decision 5: YOLOv8 / TensorRT Model Loading

**Decision**: `YOLO(model_path)` — Ultralytics handles `.pt` and `.engine` transparently.
Startup failures are caught as `RuntimeError` (CUDA) or `AssertionError` (TRT version mismatch)
and trigger the fatal-halt path (FR-029).

**Pattern**:
```python
try:
    model = YOLO(config.MODEL_PATH)
    # Warm-up inference to detect TRT issues early
    dummy = np.zeros((config.CAMERA_HEIGHT, config.CAMERA_WIDTH, 3), dtype=np.uint8)
    model.predict(dummy, verbose=False)
except (RuntimeError, AssertionError, FileNotFoundError) as exc:
    logger.critical(f"[SYSTEM] FATAL — TensorRT inference failed to initialise: {exc}")
    sys.exit(1)
```

**Rationale**: The warm-up call surfaces TRT engine errors (e.g., engine built on a different
JetPack version) before the main loop starts — preventing silent degraded-mode operation.

**Alternatives considered**:
- **Catching all `Exception`**: Rejected — too broad; masks programming errors. Explicit
  exception types document expected failure modes.
- **Lazy loading (first inference)**: Rejected — violates FR-029 which requires fail-fast at
  startup, not mid-loop.

---

## Decision 6: Velocity Tapering Near Turret Limits

**Decision**: Linear scale factor computed per-axis per-direction. When inside the taper
zone, velocity is multiplied by `scale = max(0, (limit_hard − |pos|) / taper_width)`.

**Formula**:
```python
def taper_velocity(pos: int, warn: int, hard: int, velocity: float) -> float:
    """
    Scale velocity toward zero as |pos| approaches hard limit.
    Works symmetrically for both ± directions.
    """
    abs_pos = abs(pos)
    if abs_pos < warn:
        return velocity  # outside taper zone
    if abs_pos >= hard:
        return 0.0       # at or past hard limit
    taper_width = hard - warn
    scale = (hard - abs_pos) / taper_width
    return velocity * scale
```

**Rationale**: Absolute-value symmetry means the same formula handles both pan left/right
and tilt up/down limits. `scale` is always in [0, 1] due to the guard clauses.

**Alternatives considered**:
- **Hard clamp without taper**: Rejected — spec FR-031 explicitly requires graduated
  deceleration, not hard stop, to prevent mechanical shock.
- **Cosine taper**: Smoother deceleration curve but adds complexity. Rejected — linear
  taper is adequate for stepper motor velocity control and easier to tune.

---

## Summary of All Resolved Unknowns

| Unknown | Resolution |
|---------|-----------|
| Centroid tracking algorithm | `scipy.spatial.distance.cdist` — PyImageSearch reference impl |
| FSM dwell timer | `time.monotonic_ns()` stored at state entry; downward gate checks elapsed |
| GPS formula | Pure-stdlib Haversine — ±2 m at <2 km; satisfies ±10 m spec |
| MQTT non-blocking | Daemon thread + `queue.Queue`; `publish_async()` never blocks |
| TRT loading / error handling | `YOLO(path)` + warm-up; catch `RuntimeError`/`AssertionError`; `sys.exit(1)` |
| Velocity tapering | Linear scale factor: `(hard - \|pos\|) / taper_width`, clamped [0, 1] |
