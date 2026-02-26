# Data Model: Arduino Firmware — Sentry HAL

**Branch**: `001-arduino-firmware` | **Date**: 2026-02-26

> The firmware has no persistent storage. All entities below are in-memory runtime structures maintained in RAM for the duration of a power cycle. Step counts reset to zero at firmware reset.

---

## 1. `StepperAxis` — Per-axis motor state

Maintained as two global instances: `panAxis` and `tiltAxis`.

| Field | Type | Description |
|-------|------|-------------|
| `stepPin` | `uint8_t` | Arduino digital pin connected to the stepper driver STEP input |
| `dirPin` | `uint8_t` | Arduino digital pin connected to the stepper driver DIR input |
| `velocity` | `float` | Current commanded velocity in abstract speed units (from last `V` command) |
| `stepIntervalUs` | `unsigned long` | Microseconds between step pulses at current velocity; `0` = stopped |
| `nextStepTimeUs` | `unsigned long` | `micros()` value at which the next step pulse is due |
| `stepCount` | `int32_t` | Accumulated steps from power-on; positive = forward axis direction |

**Validation rules**:
- `velocity = 0.0` → `stepIntervalUs = 0` (motor stopped; no pulses generated)
- `stepIntervalUs` is clamped to `MIN_STEP_INTERVAL_US` (config): `stepIntervalUs = max(computed, MIN_STEP_INTERVAL_US)`
- `stepCount` is clamped at `INT32_MAX` / `INT32_MIN`; overflow detection is checked after each increment/decrement
- Direction pin: HIGH = positive velocity direction; LOW = negative velocity direction (per FR-011)

**State transitions**:
```
STOPPED (velocity == 0.0)
  ──V cmd (|v| > 0)──► RUNNING (stepIntervalUs set; nextStepTime = micros() + stepIntervalUs)
RUNNING
  ──V cmd (v == 0.0)──► STOPPED
  ──V cmd (v changed)──► RUNNING (stepIntervalUs updated; dir pin updated)
  ──LIMIT triggered (same direction)──► LIMIT_HOLD (step pulses gated)
LIMIT_HOLD
  ──V cmd (opposite direction)──► RUNNING
```

---

## 2. `LimitPin` — Per-limit-switch debounce state

Maintained as four global instances: `limitPanLeft`, `limitPanRight`, `limitTiltUp`, `limitTiltDown`.

**`LimitState` enum** (defined in `limit_switch.h`):

| Value | Meaning |
|-------|---------|
| `IDLE` | Pin is HIGH; no trigger in progress |
| `DEBOUNCING` | Pin went LOW; debounce timer running |
| `TRIGGERED` | Debounce confirmed; limit is active |

| Field | Type | Description |
|-------|------|-------------|
| `pin` | `uint8_t` | Arduino digital pin (configured as `INPUT_PULLUP`) |
| `state` | `LimitState` | FSM state: `IDLE`, `DEBOUNCING`, or `TRIGGERED` |
| `candidateMs` | `unsigned long` | `millis()` timestamp when pin first read LOW; used for debounce window comparison |
| `triggered` | `bool` | `true` once debounce window has elapsed; stays `true` while pin held LOW |

**Validation rules**:
- Pin mode: `INPUT_PULLUP` — pin reads HIGH (1) when switch open; LOW (0) when switch closed/pressed
- A `LIMIT` message is emitted only on the `false → true` transition of `triggered` (rising edge of debounced state), tracked by `prevTriggered_*` booleans in `sentry_turret.ino`
- `triggered` reverts to `false` when pin reads HIGH again (switch released) — ready for next event
- Debounce window: `LIMIT_DEBOUNCE_MS` = 5 ms; pin must be continuously LOW for this duration before `triggered` is set

**Debounce state machine**:
```
IDLE (pin HIGH, triggered = false)
  ──pin goes LOW──► DEBOUNCING (candidateMs = millis())
DEBOUNCING
  ──pin HIGH again (< LIMIT_DEBOUNCE_MS)──► IDLE (false alarm)
  ──millis() - candidateMs >= LIMIT_DEBOUNCE_MS──► TRIGGERED (triggered = true)
TRIGGERED (pin LOW, triggered = true)
  ──pin HIGH──► IDLE (triggered = false; ready for next event)
```

---

## 3. `LrfReader` — LRF binary frame accumulator

One global instance: `lrfReader`.

| Field | Type | Description |
|-------|------|-------------|
| `buf` | `uint8_t[8]` | Raw byte accumulation buffer for the 8-byte binary response frame |
| `idx` | `uint8_t` | Current write index into `buf` (0–8) |
| `active` | `bool` | `true` while a frame is being accumulated (sync bytes received) |

**Frame validation (FR-027)** — performed inside `lrfFeedByte()` when `idx == LRF_FRAME_LEN`:
1. `buf[0] == LRF_SYNC_H (0x55)` AND `buf[1] == LRF_SYNC_L (0xAA)` — sync bytes (checked during accumulation)
2. `buf[2] == 0x00` — STA byte (`0x00` = measurement success; any non-zero value = error)
3. Checksum: `(buf[2]+buf[3]+buf[4]+buf[5]+buf[6]) & 0xFF == buf[7]`

**Distance extraction** (only when all validation steps pass):
```c
uint32_t mm = ((uint32_t)buf[3] << 24) | ((uint32_t)buf[4] << 16)
            | ((uint32_t)buf[5] <<  8) | (uint32_t)buf[6];  // big-endian mm
float distanceM = (float)mm / 1000.0f;
```

**`lrfFeedByte()` return values** — caller must handle all three:
- `≥ 0.0` — valid distance in metres; emit `DIST <value>\n`
- `−1.0` — frame error (checksum failure or non-zero STA); emit `DIST -1.0\n`
- `−2.0` — still accumulating; no action required

**Accumulation flow**:
```
inactive (idx = 0, active = false)
  ──byte == 0x55 received──► active = true; buf[0] = 0x55; idx = 1
active (idx 1–7)
  ──next byte arrives──► buf[idx++] = byte
  ──idx == 8 (frame complete)──► validate; return ≥0.0 / -1.0; reset (idx=0, active=false)
  ──any byte mismatches expected sync──► (accumulator continues; validator catches errors)
```

---

## 4. `SerialProtoState` — Jetson command parser state

One global instance: `protoState` (declared in `sentry_turret.ino`).

| Field | Type | Description |
|-------|------|-------------|
| `buf` | `char[64]` | Line accumulation buffer (`SERIAL_LINE_BUF_LEN` bytes) |
| `head` | `uint8_t` | Write index into `buf` |
| `overflow` | `bool` | `true` when the current line has exceeded `buf` capacity; line is discarded |
| `panSpeed` | `float` | Parsed pan velocity (valid when `serialProtoFeed()` returns `CMD_VELOCITY`) |
| `tiltSpeed` | `float` | Parsed tilt velocity (valid when `serialProtoFeed()` returns `CMD_VELOCITY`) |

**Command codes** — returned by `serialProtoFeed()` as `int8_t` constants (defined in `serial_proto.h`):

| Constant | Value | Meaning |
|----------|-------|---------|
| `CMD_NONE` | `0` | No complete line available yet |
| `CMD_VELOCITY` | `1` | `V` command parsed; `panSpeed` and `tiltSpeed` are valid |
| `CMD_LASER` | `2` | `L` command parsed; no extra fields |
| `CMD_UNKNOWN` | `−1` | Line received but unrecognised; discard |

**Validation rules**:
- A `V` command with fewer than 2 float arguments → `CMD_UNKNOWN` (discarded)
- Any line not matching `V` or `L` (case-sensitive) → `CMD_UNKNOWN` (discarded; no error response)
- `strtof()` used for float parsing; out-of-range floats are clamped by the stepper driver layer
- Buffer overflow (line ≥ `SERIAL_LINE_BUF_LEN − 1` bytes without `\n`): accumulator flushed, line discarded

---

## 5. Configuration Block (`config.h`) — Named Constants

All constants are `constexpr` or `#define`. No values appear inline in logic files.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `JETSON_BAUD` | `uint32_t` | `115200` | USB serial baud rate for Jetson link |
| `LRF_SOFTSERIAL_BAUD` | `uint32_t` | `115200` | SoftwareSerial baud rate for LRF link |
| `LRF_RX_PIN` | `uint8_t` | `A0 (14)` | SoftwareSerial RX pin — Arduino analog A0 used as digital GPIO |
| `LRF_TX_PIN` | `uint8_t` | `A1 (15)` | SoftwareSerial TX pin — Arduino analog A1 used as digital GPIO |
| `PAN_STEP_PIN` | `uint8_t` | `2` | Pan axis stepper driver STEP pin — CNC Shield V3 X-axis slot |
| `PAN_DIR_PIN` | `uint8_t` | `5` | Pan axis stepper driver DIR pin — CNC Shield V3 X-axis slot |
| `TILT_STEP_PIN` | `uint8_t` | `3` | Tilt axis stepper driver STEP pin — CNC Shield V3 Y-axis slot |
| `TILT_DIR_PIN` | `uint8_t` | `6` | Tilt axis stepper driver DIR pin — CNC Shield V3 Y-axis slot |
| `STEPPER_ENABLE_PIN` | `uint8_t` | `8` | Shared driver enable pin (active-LOW, D8); held LOW permanently for tilt torque |
| `LIMIT_PAN_LEFT_PIN` | `uint8_t` | `9` | Pan-left limit switch — CNC Shield V3 X_Limit header |
| `LIMIT_PAN_RIGHT_PIN` | `uint8_t` | `10` | Pan-right limit switch — CNC Shield V3 Y_Limit header |
| `LIMIT_TILT_DOWN_PIN` | `uint8_t` | `11` | Tilt-down limit switch — CNC Shield V3 Z_Limit header (gravity-critical) |
| `LIMIT_TILT_UP_PIN` | `uint8_t` | `12` | Tilt-up limit switch — Arduino D12 (off-shield, requires direct wire) |
| `HEARTBEAT_INTERVAL_MS` | `uint16_t` | `100` | POS broadcast interval in milliseconds |
| `VELOCITY_SCALE_FACTOR` | `float` | `1000.0f` | Maps velocity units → `stepIntervalUs`; `interval = SCALE / |vel|` |
| `MIN_STEP_INTERVAL_US` | `uint16_t` | `200` | Minimum step interval (max frequency clamp) in microseconds |
| `LIMIT_DEBOUNCE_MS` | `uint8_t` | `5` | Minimum LOW duration to confirm limit switch trigger |
| `LRF_FRAME_LEN` | `uint8_t` | `8` | Expected LRF binary response frame length in bytes |
| `LRF_SYNC_H` | `uint8_t` | `0x55` | LRF frame sync byte 1 |
| `LRF_SYNC_L` | `uint8_t` | `0xAA` | LRF frame sync byte 2 |
| `LRF_TRIGGER` | `uint8_t[8]` | `{0x55,0xAA,0x88,0xFF,0xFF,0xFF,0xFF,0x84}` | Single-ranging trigger frame bytes |
| `LRF_READ_TIMEOUT_MS` | `uint8_t` | `100` | Max wait for complete LRF reply frame |
| `LRF_BOOT_TIMEOUT_MS` | `uint16_t` | `500` | Max wait for LRF boot self-test frame in setup() |
| `SERIAL_LINE_BUF_LEN` | `uint8_t` | `64` | Jetson command line buffer size in bytes |
