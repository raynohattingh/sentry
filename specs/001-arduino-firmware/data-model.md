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
| `nextStepTime` | `unsigned long` | `micros()` value at which the next step pulse is due |
| `stepCount` | `int32_t` | Accumulated steps from power-on; positive = forward axis direction |
| `stepHigh` | `bool` | Toggle flag tracking current STEP pin state (for pulse generation) |

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

| Field | Type | Description |
|-------|------|-------------|
| `pin` | `uint8_t` | Arduino digital pin (configured as `INPUT_PULLUP`) |
| `axis` | `const char*` | `"PAN"` or `"TILT"` — used in `LIMIT` message |
| `direction` | `const char*` | `"LEFT"`, `"RIGHT"`, `"UP"`, or `"DOWN"` — used in `LIMIT` message |
| `debounceStart` | `unsigned long` | `millis()` timestamp when pin first read LOW; `0` = not debouncing |
| `triggered` | `bool` | `true` once debounce has confirmed a full press; stays `true` while pin held LOW |
| `wasTriggered` | `bool` | Previous-cycle `triggered` state; used to detect state-transition edge |

**Validation rules**:
- Pin mode: `INPUT_PULLUP` — pin reads HIGH (1) when switch open; LOW (0) when switch closed/pressed
- A `LIMIT` message is emitted only on the `false → true` transition of `triggered` (rising edge of debounced state)
- `triggered` reverts to `false` when pin reads HIGH again (switch released) — ready for next event
- Debounce window: `LIMIT_DEBOUNCE_MS` = 5 ms; pin must be continuously LOW for this duration before `triggered` is set

**Debounce state machine**:
```
IDLE (pin HIGH, triggered = false)
  ──pin goes LOW──► DEBOUNCING (debounceStart = millis())
DEBOUNCING
  ──pin HIGH again (< LIMIT_DEBOUNCE_MS)──► IDLE (false alarm)
  ──millis() - debounceStart >= LIMIT_DEBOUNCE_MS──► FIRED (triggered = true; emit LIMIT msg)
FIRED (pin LOW, triggered = true)
  ──pin HIGH──► IDLE (triggered = false; ready for next event)
```

---

## 3. `LrfReader` — LRF binary frame accumulator

One global instance: `lrfReader`.

| Field | Type | Description |
|-------|------|-------------|
| `pending` | `bool` | `true` when an `L\n` command has been received and ranging is in progress |
| `buf` | `uint8_t[8]` | Raw byte accumulator for the 8-byte binary response frame |
| `bufLen` | `uint8_t` | Number of bytes accumulated so far (0–8) |
| `readStart` | `unsigned long` | `millis()` timestamp when the trigger was sent; used for `LRF_READ_TIMEOUT_MS` check |

**Frame validation (FR-027)**:
1. `buf[0] == LRF_SYNC_H (0x55)` AND `buf[1] == LRF_SYNC_L (0xAA)` — sync bytes
2. Checksum: `(buf[0]+buf[1]+buf[2]+buf[3]+buf[4]+buf[5]+buf[6]) & 0xFF == buf[7]`
3. STA byte: `buf[3] == 0x01` (success); `buf[3] == 0x00` → failure

**Distance extraction** (only when all 3 validation steps pass):
```
rawDist = ((uint16_t)buf[5] << 8) | buf[6]   // DIS_H, DIS_L
distanceM = rawDist / 10.0f
```

**State transitions**:
```
IDLE (pending = false)
  ──L\n received──► WAITING (send LRF_TRIGGER[]; pending = true; readStart = millis())
WAITING
  ──SoftwareSerial byte arrives──► accumulate into buf; bufLen++
  ──bufLen == LRF_FRAME_LEN (8)──► VALIDATING
  ──millis() - readStart > LRF_READ_TIMEOUT_MS──► IDLE (emit DIST -1.0\n; flush RX buf)
VALIDATING
  ──frame valid, STA=1──► IDLE (emit DIST <value>\n)
  ──frame invalid / STA=0──► IDLE (emit DIST -1.0\n; flush RX buf)
```

---

## 4. `SerialCommand` — Parsed Jetson command (value type)

Not stored globally; created on the stack each time a complete line is received and immediately consumed.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `enum CommandType` | `CMD_VELOCITY`, `CMD_LASER`, `CMD_UNKNOWN` |
| `panVelocity` | `float` | Pan speed from `V <pan> <tilt>` command (valid only when `type == CMD_VELOCITY`) |
| `tiltVelocity` | `float` | Tilt speed from `V <pan> <tilt>` command (valid only when `type == CMD_VELOCITY`) |

**Validation rules**:
- A `V` command with fewer than 2 float arguments → `CMD_UNKNOWN` (discarded)
- Any line not matching `V` or `L` (case-sensitive) → `CMD_UNKNOWN` (discarded; no error response)
- `atof()` used for float parsing; out-of-range floats are clamped by the stepper driver layer

---

## 5. Configuration Block (`config.h`) — Named Constants

All constants are `constexpr` or `#define`. No values appear inline in logic files.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `JETSON_BAUD` | `uint32_t` | `115200` | USB serial baud rate for Jetson link |
| `LRF_SOFTSERIAL_BAUD` | `uint32_t` | `115200` | SoftwareSerial baud rate for LRF link |
| `LRF_RX_PIN` | `uint8_t` | `10` | SoftwareSerial RX pin (LRF TX → this pin) |
| `LRF_TX_PIN` | `uint8_t` | `11` | SoftwareSerial TX pin (this pin → LRF RX) |
| `PAN_STEP_PIN` | `uint8_t` | `2` | Pan axis stepper driver STEP pin |
| `PAN_DIR_PIN` | `uint8_t` | `3` | Pan axis stepper driver DIR pin |
| `TILT_STEP_PIN` | `uint8_t` | `4` | Tilt axis stepper driver STEP pin |
| `TILT_DIR_PIN` | `uint8_t` | `5` | Tilt axis stepper driver DIR pin |
| `LIMIT_PAN_LEFT_PIN` | `uint8_t` | `6` | Pan-left limit switch input pin |
| `LIMIT_PAN_RIGHT_PIN` | `uint8_t` | `7` | Pan-right limit switch input pin |
| `LIMIT_TILT_UP_PIN` | `uint8_t` | `8` | Tilt-up limit switch input pin |
| `LIMIT_TILT_DOWN_PIN` | `uint8_t` | `9` | Tilt-down limit switch input pin |
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
