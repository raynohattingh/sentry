# Contract: Serial Protocol — Jetson ↔ Arduino

**Branch**: `001-jetson-core` | **Date**: 2026-02-25  
**Owner**: `jetson/src/hardware/arduino_link.py` (Jetson side)

---

## Transport

| Parameter | Value |
|-----------|-------|
| Interface | USB Serial (CDC) |
| Baud rate | 115 200 |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |
| Line ending | `\n` (LF only) |
| Encoding | ASCII |
| Timeout (read) | 100 ms |

---

## Jetson → Arduino (TX)

### Velocity Command

Sent every control loop tick when a target is active or when SCAN sweep velocity is applied.
Also sent as a stop command (`V 0.00 0.00`) on loss of target or camera fault.

```
V <pan_speed> <tilt_speed>\n
```

| Field | Type | Units | Sign convention |
|-------|------|-------|----------------|
| `pan_speed` | float, 2 decimal places | steps/sec | positive = right, negative = left |
| `tilt_speed` | float, 2 decimal places | steps/sec | positive = up, negative = down |

**Examples**:
```
V 100.00 -50.00\n    ← Pan right 100 steps/sec, tilt down 50 steps/sec
V 0.00 0.00\n        ← Stop all movement
V -1500.00 0.00\n    ← Maximum left pan (PAN_MAX = 1500)
```

**Range**: `|pan_speed| ≤ PAN_MAX`, `|tilt_speed| ≤ TILT_MAX` (enforced Jetson-side before send)

---

### LRF Trigger Command

Sent by the FSM when in TRACK or ACQUIRE state and `LRF_ENABLED = true`.

```
L\n
```

No parameters. The Arduino fires the laser rangefinder and responds asynchronously with a
`DIST` message. The Jetson does not wait synchronously; responses are parsed in the serial
read thread.

---

## Arduino → Jetson (RX)

### Distance Message

Sent asynchronously after receiving `L\n` and completing a laser ranging cycle.

```
DIST <distance>\n
```

| Field | Type | Units |
|-------|------|-------|
| `distance` | float | metres |

**Examples**:
```
DIST 150.50\n    ← Target at 150.50 metres
DIST 0.00\n      ← Invalid / no return (treated as null reading)
```

**Parsing rule**: If `distance <= 0.0` or parse fails, `LRFReading.valid = False`.

---

### Position Message

Sent periodically by the Arduino (configurable rate, default 10 Hz) to report cumulative
stepper motor step counts since last reset.

```
POS <pan_steps> <tilt_steps>\n
```

| Field | Type | Units | Sign convention |
|-------|------|-------|----------------|
| `pan_steps` | int | steps | positive = right, negative = left |
| `tilt_steps` | int | steps | positive = up, negative = down |

**Examples**:
```
POS 1000 500\n      ← Pan at +1000 steps, tilt at +500 steps
POS -250 0\n        ← Pan at -250 steps, tilt at home
```

**Usage**: The Jetson accumulates `TurretPosition` from this stream to drive the velocity
taper logic (FR-031). Step-to-angle conversion: `angle_deg = steps * config.STEPS_PER_DEGREE`.

---

## Error Handling

### Malformed Frames (FR-033)

Any line that does not match the patterns below MUST be discarded:
- Valid TX: (never received back)
- Valid RX: `^DIST \d+(\.\d+)?$` or `^POS -?\d+ -?\d+$`

**On discard**:
1. Emit structured log: `[SERIAL] Malformed frame discarded: <raw_content>`
2. `LRFReading.valid = False` if a DIST frame was expected
3. Continue; do NOT raise exception or stall the read loop

**Examples of malformed frames**:
```
DIST\n               ← Missing value
POS 100\n            ← Missing tilt
DIST abc\n           ← Non-numeric
\n                   ← Empty line
ERROR: timeout\n     ← Arduino debug output
```

---

## Heartbeat / Watchdog

- The Jetson tracks time since last valid `POS` message.
- If no `POS` received within `config.SERIAL_HEARTBEAT_TIMEOUT_S` (default: 2.0 s), the
  connection is considered stale.
- The `ArduinoLink` reconnect loop is triggered: close port → retry open → re-enable.
- Log: `[SERIAL] Heartbeat timeout — reconnecting`

---

## Reconnection Protocol

On any `serial.SerialException` or heartbeat timeout:

1. Send `V 0.00 0.00\n` (best-effort; may fail if port is gone)
2. Close the serial port
3. Log: `[SERIAL] Disconnected — retrying in <interval>s`
4. Wait `config.SERIAL_RETRY_INTERVAL_S` (default: 3.0 s)
5. Attempt `serial.Serial(port, baud, timeout=0.1)`
6. On success: log `[SERIAL] Reconnected to <port>`, reset `TurretPosition` to (0, 0)
7. On failure: repeat from step 4 indefinitely

---

## Thread Safety

- **Write thread**: Only `arduino_link.send_velocity()` and `arduino_link.fire_lrf()` write
  to the serial port. These are protected by a `threading.Lock`.
- **Read thread**: A dedicated background thread reads and parses lines, updating
  `TurretPosition` and `LRFReading` in thread-safe shared state (protected by locks).
- The main control loop NEVER reads directly from the serial port.
