# Contract: Jetson ↔ Arduino Serial Protocol

**Version**: 1.0.0 | **Branch**: `001-arduino-firmware` | **Date**: 2026-02-26

## Overview

The Jetson Core and the Arduino firmware communicate over a USB/CDC (Universal Serial Bus / Communications Device Class) serial link using the UART0 (Universal Asynchronous Receiver-Transmitter 0) port on the Arduino Uno R3. The protocol is line-delimited ASCII with fixed command prefixes. Each message is terminated by `\n` (LF, 0x0A).

**Physical link**: USB-A (Jetson) ↔ USB-B (Arduino Uno R3), presented as a virtual COM port on the Jetson.  
**Baud rate**: 115200 baud, 8 data bits, 1 stop bit, no parity.  
**Direction conventions**: "TX" = Jetson sends to Arduino; "RX" = Arduino sends to Jetson.

---

## Commands (TX — Jetson → Arduino)

### `V` — Velocity Move

```
V <pan_speed> <tilt_speed>\n
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `pan_speed` | `float` | `(-∞, +∞)`, clamped by firmware | Pan axis velocity in abstract speed units. Positive = right; negative = left. |
| `tilt_speed` | `float` | `(-∞, +∞)`, clamped by firmware | Tilt axis velocity in abstract speed units. Positive = up; negative = down. |

**Behaviour**:
- Sets both axes simultaneously.
- `V 0.0 0.0\n` stops both axes within one firmware loop cycle (≤ 5 ms).
- Supersedes any previous velocity command immediately.
- Step frequency is clamped to `MIN_STEP_INTERVAL_US`; values that would exceed this are silently clamped — no error response.

**Examples**:
```
V 100.0 -50.0\n   → pan right at 100 units, tilt down at 50 units
V 0.0 0.0\n       → stop both axes
V -200.0 0.0\n    → pan left at 200 units, tilt stationary
```

---

### `L` — Laser Range Trigger

```
L\n
```

No arguments. Triggers a single LRF (Laser Range Finder) measurement. The Arduino responds asynchronously with a `DIST` message.

**Behaviour**:
- Firmware sends the LRF binary trigger sequence over the LRF SoftwareSerial TX line.
- Firmware awaits up to `LRF_READ_TIMEOUT_MS` (100 ms) for the 8-byte binary response.
- Motor motion continues uninterrupted during LRF ranging.

---

## Responses (RX — Arduino → Jetson)

### `DIST` — Range Measurement Result

```
DIST <distance>\n
```

| Field | Type | Description |
|-------|------|-------------|
| `distance` | `float` | Distance to target in metres. `−1.0` indicates a ranging failure (timeout, frame validation error, or STA=0x00). |

**Sent in response to**: `L\n` command.  
**Timing**: Within 500 ms of receiving `L\n` (SC-005). `LRF_READ_TIMEOUT_MS` (100 ms) bounds the LRF frame wait; remaining budget covers trigger transmission and response serialisation.

**Examples**:
```
DIST 15.30\n      → target at 15.30 metres
DIST 1.5\n        → target at 1.5 metres
DIST -1.0\n       → ranging failure (timeout or invalid frame)
```

---

### `POS` — Position Heartbeat

```
POS <pan_steps> <tilt_steps>\n
```

| Field | Type | Description |
|-------|------|-------------|
| `pan_steps` | `int32_t` | Cumulative pan axis step count from power-on. Positive = right direction. |
| `tilt_steps` | `int32_t` | Cumulative tilt axis step count from power-on. Positive = up direction. |

**Sent**: Periodically, every `HEARTBEAT_INTERVAL_MS` (default 100 ms) regardless of motion state.  
**Timing jitter**: ≤ ±20% of the configured interval under normal operating conditions (SC-004).  
**Overflow behaviour**: If either counter reaches `INT32_MAX` or `INT32_MIN`, it is clamped at the boundary and the broadcast continues with the clamped value — no silent wrap-around.  
**Reset**: Step counts reset to zero at firmware power-on or hardware reset; there is no persistent position memory.

**Examples**:
```
POS 0 0\n          → stationary at power-on position
POS 1500 -200\n    → 1500 steps right, 200 steps down from origin
POS 2147483647 0\n → pan accumulator at INT32_MAX clamp boundary
```

---

### `LIMIT` — Limit Switch Notification

```
LIMIT <axis> <direction>\n
```

| Field | Type | Allowed values | Description |
|-------|------|---------------|-------------|
| `axis` | `string` | `PAN`, `TILT` | Which motor axis reached its physical end-stop |
| `direction` | `string` | `LEFT`, `RIGHT` (pan); `UP`, `DOWN` (tilt) | Which direction end-stop was reached |

**Sent**: Once per confirmed limit switch trigger. A switch is confirmed after `LIMIT_DEBOUNCE_MS` (5 ms) of continuous LOW state on the `INPUT_PULLUP` pin. No repeat messages while the switch remains held; one new message per re-trigger after the switch releases and is re-pressed.

**Motor behaviour on trigger**: Firmware immediately ceases step pulses in the triggering direction; motion in the opposite direction remains unblocked.

**Examples**:
```
LIMIT PAN RIGHT\n    → pan axis has reached its right physical end-stop
LIMIT TILT DOWN\n    → tilt axis has reached its down physical end-stop
```

---

### `LRF_BOOT_ERR` — LRF Boot Diagnostics (not currently emitted)

```
LRF_BOOT_ERR <err_code>\n
```

| Field | Type | Description |
|-------|------|-------------|
| `err_code` | `uint8_t` (hex or decimal) | Error code from the LRF boot self-test reply frame |

**Current behaviour**: The `setup()` boot-drain loop silently discards the LRF boot frame regardless of its STA value. `LRF_BOOT_ERR` is documented here as a future enhancement; it is **not currently emitted** by the firmware.

---

## Error Handling

| Condition | Firmware Behaviour |
|-----------|-------------------|
| Malformed `V` command (wrong arg count, non-numeric) | Discard the line silently; no response sent |
| Unknown command prefix | Discard the line silently; no response sent |
| `V` velocity exceeds maximum step rate | Silently clamp to `MIN_STEP_INTERVAL_US`; no error response |
| Serial buffer overflow (line > `SERIAL_LINE_BUF_LEN`) | Discard accumulated partial line; reset buffer |
| LRF timeout / corrupt frame | Respond `DIST -1.0\n` |
| step counter overflow | Clamp at `INT32_MAX`/`INT32_MIN`; continue broadcasting `POS` with clamped values |

---

## Timing Summary

| Event | Latency target | Source |
|-------|---------------|--------|
| Velocity command → motor motion onset | < 10 ms | SC-001 |
| Stop command (`V 0.0 0.0\n`) → motor halt | ≤ 5 ms | SC-002 |
| Limit switch trigger → motor halt | < 1 loop cycle | SC-003 |
| `POS` heartbeat interval | 100 ms ± 20% | SC-004 |
| `L\n` → `DIST` response | ≤ 500 ms | SC-005 |
