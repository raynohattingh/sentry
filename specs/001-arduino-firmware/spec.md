# Feature Specification: Arduino Firmware — Sentry HAL

**Feature Branch**: `001-arduino-firmware`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "Arduino microcontroller firmware for the Sentry autonomous thermal turret. The Arduino lives in the `arduino/` directory and is the hardware abstraction layer between the Jetson Orin Nano Super (running the Jetson Core brain) and the physical pan/tilt stepper motors."

## Overview

The Sentry turret requires an embedded firmware layer that bridges the Jetson Core's high-level motion commands to the physical hardware — two stepper motors, physical limit switches, and a laser rangefinder (LRF). The Arduino microcontroller serves as this hardware abstraction layer (HAL), translating the Jetson's intent into precise hardware signals and reporting physical state back in real time.

The firmware must be reliable, safe, and maintainable: a crashed or misbehaving firmware is a safety risk given the physical hardware involved.

**Actors:**
- **Jetson Core** — the upstream controller; sends commands and consumes feedback over USB serial (USB/CDC (Universal Serial Bus/Communications Device Class) connection on the Uno R3)
- **Hardware Operator** — the person building, testing, and configuring the physical sentry unit

**Target Hardware:** Arduino Uno R3

---

## Clarifications

### Session 2026-02-26

- Q: Target Arduino board model? → A: Arduino Uno R3. Jetson communicates via USB serial (USB/CDC). LRF communicates via hardware TX/RX pins (UART0 — Universal Asynchronous Receiver-Transmitter 0). **Constraint:** On the Uno R3, USB serial and hardware TX/RX pins share UART0 — they cannot operate as two independent full-duplex serial channels simultaneously. The firmware must therefore route one of the two serial connections via SoftwareSerial on spare digital pins, or the LRF must use a non-serial interface (analog voltage output or digital trigger-and-pulse). Resolution of the LRF interface strategy is captured in Q2.
- Q: LRF interface strategy given UART0 conflict on the Uno R3? → A: **SoftwareSerial on spare digital pins (D2–D13 range)**. Jetson retains the USB/CDC connection on UART0 (`Serial`). The LRF is connected to a `SoftwareSerial` instance on two spare GPIO pins. The command/response protocol is preserved: `L\n` triggers a reading; the firmware responds with `DIST <value>\n` (or `DIST -1.0\n` on timeout).
- Q: Step-pulse generation strategy for motor control? → A: **Non-blocking `micros()` scheduling** — each axis maintains a `nextStepTime` timestamp; the main loop compares `micros()` against `nextStepTime` and fires a pulse only when due. `delay()` is forbidden anywhere in the firmware. All subsystems (serial parsing, limit checking, LRF polling, heartbeat) run cooperatively within a single tight loop with no blocking calls.
- Q: Step count integer width for POS message and internal accumulator? → A: **`int32_t`** (32-bit signed, ±2,147,483,647 steps). Provides explicit portable width across Arduino architectures, matches the `POS` message payload type, and gives ≈10.7 million full-revolution range before overflow — far beyond any physically reachable position for a pan/tilt turret. Overflow must be guarded against in the accumulator; if a count approaches `INT32_MAX` / `INT32_MIN` the firmware MUST clamp and emit a `LIMIT`-style warning rather than silently wrapping.
- Q: Watchdog/hang recovery strategy? → A: **AVR (Atmel AVR 8-bit microcontroller architecture) hardware WDT (Watchdog Timer), 2-second timeout, `wdt_reset()` called once per `loop()` iteration.** `wdt_enable(WDTO_2S)` from `<avr/wdt.h>` is called at the end of `setup()`; if `loop()` ever fails to return within 2 seconds the WDT forces an automatic hardware reset, recovering the firmware from any hung state without requiring manual power cycling.
- **Additional note — Hardware portability**: Future planned targets include ESP32 and Teensy 4.0. All hardware-specific pin assignments, timing constants, and platform-specific APIs (WDT via `<avr/wdt.h>`, `SoftwareSerial`, `micros()`/`millis()`) MUST be isolated in the configuration block (top of main `.ino` or a companion `config.h`). The current implementation targets Uno R3 (AVR architecture), but the firmware architecture MUST NOT assume AVR-only. Porting to a new platform MUST be a configuration-block change, not a logic rewrite.
- **Additional note — Acronym policy**: All acronyms and abbreviations are expanded on first use throughout this spec — e.g. HAL (Hardware Abstraction Layer), LRF (Laser Range Finder), USB/CDC (Universal Serial Bus/Communications Device Class), UART0 (Universal Asynchronous Receiver-Transmitter 0), GPIO (General-Purpose Input/Output), WDT (Watchdog Timer), AVR (Atmel AVR 8-bit microcontroller architecture).
- Q: LRF Trigger Mechanism — how does the firmware communicate with the LRF over SoftwareSerial? → A: **SoftwareSerial binary/framed command** (Option C). Firmware sends a binary trigger sequence over `SoftwareSerial` TX; the LRF responds with an **8-byte binary frame** on `SoftwareSerial` RX at **115200 baud, 8 data bits**. The firmware MUST validate the complete 8-byte frame before extracting the distance value; corrupt or incomplete frames MUST be discarded and the Jetson MUST receive `DIST -1.0\n` rather than a corrupted reading. Note: 115200 baud on AVR `SoftwareSerial` is at the upper reliability limit — see CONSTRAINT-001 in Constraints & Tradeoffs.
- Q: LRF Module Identity & 8-byte Frame Layout → A: Custom/unknown module. Sync bytes: `0x55 0xAA` (bytes 0–1). Send-frame checksum = SUM(Function Word + D1..D4) (bytes 2–6). Reply-frame checksum = SUM(all 7 bytes before checksum byte) (bytes 0–6). Single-ranging: send `55 AA 88 FF FF FF FF 84`; reply `55 AA 88 STA FF DIS_H DIS_L CHK` — STA=0x01 success, distance = `(DIS_H<<8 | DIS_L) / 10.0` metres. Error codes: `0x00` no echo, `0x16` below min range, `0x18` no echo (alt), `0x00–0x07` hardware error range. Boot self-test reply (power-on, no send): `55 AA 80 STA 00 00 ErrCode CHK`; firmware MUST read and discard this frame on startup. Full protocol reference in `### LRF Binary Protocol` under Functional Requirements.
- Q: LRF_READ_TIMEOUT_MS — maximum time the firmware waits for a complete 8-byte LRF reply frame before declaring a ranging failure? → A: **100 ms** (`LRF_READ_TIMEOUT_MS = 100`). Leaves 400 ms headroom against the 500 ms end-to-end DIST response budget (SC-005).
- Q: LIMIT notification anti-flood strategy — how should the firmware prevent repeated `LIMIT` messages while a switch is held? → A: **State-transition + 5 ms software debounce** (Option B). The pin must be continuously LOW for ≥ 5 ms (`LIMIT_DEBOUNCE_MS = 5`) before the firmware fires a single `LIMIT` message. No further `LIMIT` message is sent while the pin remains held; a new message is only emitted on the next confirmed LOW state-transition (i.e., after the pin returns HIGH and then goes LOW again for ≥ 5 ms).
- Q: Limit switch electrical wiring and Arduino pin mode? → A: **Normally-Open (NO) switches, active-LOW via `INPUT_PULLUP`** (Option A). One leg of each switch connects to a GPIO pin; the other leg connects directly to GND. `pinMode(pin, INPUT_PULLUP)` is used — no external resistor required. Pin reads HIGH when switch is open (not triggered); pin reads LOW when switch is pressed/closed (triggered). This is consistent with the "bridge its input pin to ground" test instruction already in User Story 2. Fail-open default: an open-circuit (disconnected switch) is the safe non-triggered state.
- Q: Hardware shield and Pan/Tilt axis mapping? → A: **Arduino Uno CNC Shield V3**. Pan axis uses the **X-axis driver slot** (`PAN_STEP_PIN = D2`, `PAN_DIR_PIN = D5`). Tilt axis uses the **Y-axis driver slot** (`TILT_STEP_PIN = D3`, `TILT_DIR_PIN = D6`). The Z-axis driver slot (D4/D7) is physically populated on the shield but unused — available as a hardware spare. The CNC Shield provides a shared active-LOW stepper enable line on **D8** (`STEPPER_ENABLE_PIN = 8`) that gates power to all drivers simultaneously; the firmware MUST pull this pin LOW in `setup()` to enable the drivers. The CNC Shield limit switch headers are on **D9** (X_Limit), **D10** (Y_Limit), and **D11** (Z_Limit). Note: the previous generic placeholder pin assignments in earlier spec drafts (`PAN_DIR=3`, `TILT_STEP=4`, `TILT_DIR=5`) are superseded by these CNC Shield V3 hardware pin assignments and MUST NOT be used.
- Q: Stepper enable pin management strategy? → A: **Always-enabled** (Option A). `STEPPER_ENABLE_PIN` (D8, active-LOW) is driven LOW once during `setup()` and held LOW for the duration of firmware operation. The tilt axis must maintain holding torque against gravity when stationary (`V 0.0 0.0\n`), making dynamic enable/disable unsafe. No idle-disable logic is implemented; motor heat management is a hardware concern (driver current-limit trim pot). `STEPPER_ENABLE_PIN` MUST remain a named constant in `config.h` so future platforms can override the behaviour if needed.
- Q: Limit switch pin allocation — CNC Shield V3 has 3 headers (D9/D10/D11) but spec requires 4 limit inputs. Which pin assignment? → A: **Option A — gravity-critical stops on shield headers**. D9=Pan-Left (`LIMIT_PAN_LEFT_PIN`), D10=Pan-Right (`LIMIT_PAN_RIGHT_PIN`), D11=Tilt-Down (`LIMIT_TILT_DOWN_PIN`, gravity-critical safety stop on shielded header), D12=Tilt-Up (`LIMIT_TILT_UP_PIN`, off-shield Arduino header pin accessed via pass-through or solder point beneath the shield). All four pins defined as named constants in the configuration block; all use `INPUT_PULLUP` active-LOW wiring identical to the shield header pins.
- Q: LRF (Laser Range Finder) SoftwareSerial pin allocation — which two free pins for RX/TX? → A: **Option A — analog pins A0/A1 as digital GPIO**. `LRF_RX_PIN = A0` (D14), `LRF_TX_PIN = A1` (D15). These pins carry no onboard load (unlike D13 which has the onboard LED), are not used by the CNC Shield V3, and are the cleanest available pair on the Uno R3. Both defined as named constants in the configuration block.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Velocity-Driven Motor Control (Priority: P1)

The Jetson Core sends pan and tilt velocity commands; the firmware translates them into smooth, continuous stepper motor motion at the correct speed and direction on each axis independently.

**Why this priority**: Without motor control, the turret cannot aim. Every other capability depends on the turret moving. This is the most fundamental HAL responsibility.

**Independent Test**: Connect a logic analyser or oscilloscope to the step/direction pins of both stepper drivers. Send `V 100.0 -50.0\n` over serial. Verify pan step pulses at the expected frequency, pan direction pin HIGH (positive = right), tilt step pulses at half that frequency, and tilt direction pin LOW (positive = up, negative = down). Send `V 0.0 0.0\n` and verify pulses stop.

**Acceptance Scenarios**:

1. **Given** the firmware is running and connected via serial, **When** the Jetson sends `V 100.0 50.0\n`, **Then** both pan and tilt stepper drivers receive continuous step pulses at frequencies proportional to the velocity magnitudes, with direction pins reflecting the correct polarity.
2. **Given** both motors are running, **When** the Jetson sends `V 0.0 0.0\n`, **Then** both motors stop immediately (step pulses cease) within one command-processing cycle.
3. **Given** the firmware is running, **When** the Jetson sends `V -100.0 0.0\n`, **Then** pan motor runs in the reverse direction (left) and tilt is stationary.
4. **Given** a velocity command is active, **When** a new velocity command arrives before the next pulse cycle, **Then** the motor speed and direction update to the new values without a full stop/restart cycle.

---

### User Story 2 — Limit Switch Safety Stops (Priority: P2)

Physical limit switches protect the turret from mechanical over-travel. When a limit switch is triggered, the affected motor axis must stop instantly regardless of any pending velocity command, and the Jetson must be notified so it can update its motion planning.

**Why this priority**: Mechanical over-travel can damage the turret. Safety stops must be implemented in firmware (not software alone) for guaranteed hardware-level protection.

**Independent Test**: With a motor running in one direction, manually trigger the corresponding limit switch (or bridge its input pin to ground). Verify step pulses for that axis cease immediately and the firmware transmits `LIMIT <axis> <direction>\n` over serial. Verify the other axis continues to operate normally.

**Acceptance Scenarios**:

1. **Given** the pan axis is moving in the positive (right) direction, **When** the pan-right limit switch triggers, **Then** pan step pulses cease immediately and the firmware sends `LIMIT PAN RIGHT\n` to the Jetson; the tilt axis is unaffected.
2. **Given** the tilt axis is moving in the negative (down) direction, **When** the tilt-down limit switch triggers, **Then** tilt step pulses cease immediately and the firmware sends `LIMIT TILT DOWN\n`; the pan axis is unaffected.
3. **Given** a limit switch has been triggered and motion has stopped on that axis, **When** the Jetson sends a velocity command that would move that axis away from the limit (opposite direction), **Then** motion resumes normally — the limit only blocks motion into the limit, not motion away from it.
4. **Given** the firmware is running, **When** a limit switch is continuously held (stuck or wired closed), **Then** the affected axis remains stopped and the firmware sends exactly **one** `LIMIT` message on the confirmed trigger (pin LOW for ≥ `LIMIT_DEBOUNCE_MS` = 5 ms) and sends **no further** `LIMIT` messages while the pin remains held LOW — the serial bus is not flooded.

---

### User Story 3 — Laser Rangefinder Integration (Priority: P3)

The Jetson Core can request a range measurement at any time. The firmware triggers the laser rangefinder, reads the resulting distance, and replies with the value so the Jetson can use it for targeting calculations.

**Why this priority**: Range data is needed for accurate targeting but is not required for basic turret movement. It is independently testable and deliverable after core motion is verified.

**Independent Test**: Send `L\n` over serial with the laser rangefinder module wired to the configured `SoftwareSerial` RX/TX pins. Verify the firmware transmits the binary trigger sequence over `SoftwareSerial` TX and then receives the 8-byte binary response frame. Verify the firmware transmits `DIST <float>\n` to the Jetson within the configured timeout and that a plausible float value is returned (e.g., `DIST 1.505`). Deliberately corrupt the frame (disconnect mid-reception or inject wrong bytes) and verify `DIST -1.0\n` is returned instead.

**Acceptance Scenarios**:

1. **Given** the firmware is running and the laser rangefinder module is connected via `SoftwareSerial`, **When** the Jetson sends `L\n`, **Then** the firmware transmits the binary trigger sequence over `SoftwareSerial` TX, receives and validates the 8-byte binary response frame (FR-027), and responds with `DIST <value>\n` where `<value>` is a floating-point number in metres.
2. **Given** `L\n` is received, **When** the rangefinder module does not return a valid reading within the configured timeout, **Then** the firmware responds with `DIST -1.0\n` (or a configured sentinel value) to indicate a ranging failure — it does not hang or block other operations.
3. **Given** the turret is mid-movement, **When** `L\n` is received, **Then** the range request is serviced without interrupting stepper motion.

---

### User Story 4 — Position Heartbeat (Priority: P4)

The firmware broadcasts the current step counts for both axes at a regular interval so the Jetson can track accumulated position, detect serial disconnection, and synchronise its internal model with the physical hardware state.

**Why this priority**: Position telemetry and disconnection detection are important for operational reliability but do not block core motion control from working.

**Independent Test**: Connect to the firmware over serial and observe output. Without sending any commands, verify `POS <pan> <tilt>\n` messages appear at the configured interval. Drive the motors and verify the reported counts change proportionally to the steps commanded.

**Acceptance Scenarios**:

1. **Given** the firmware is running, **When** no commands are being processed, **Then** `POS <pan_steps> <tilt_steps>\n` is broadcast at the configured heartbeat interval (default: 100 ms).
2. **Given** motors are running from a velocity command, **When** a heartbeat is due, **Then** the `POS` message is transmitted and the counts reflect the actual steps taken on each axis since power-on.
3. **Given** a limit switch has triggered and reset one axis's motion, **When** the heartbeat fires, **Then** the reported position accurately reflects steps taken up to and including the stop.
4. **Given** the step counts have been running for an extended session, **When** the Jetson reads the heartbeat, **Then** the `int32_t` accumulators do not silently wrap — if either count approaches `INT32_MAX` or `INT32_MIN` the firmware clamps the value and signals an overflow condition rather than wrapping around to an incorrect position.

---

### User Story 5 — Operator Hardware Configuration (Priority: P5)

A hardware operator must be able to wire the turret and configure the firmware without editing logic code. All pin assignments, timing constants, and tuning values are defined in a single configuration section at the top of the main sketch file.

**Why this priority**: Maintainability and hardware iteration speed. Different prototypes may use different pin layouts or stepper driver boards.

**Independent Test**: Review the sketch source. Verify all hardware-specific constants (pin numbers, baud rate, heartbeat interval, steps-per-unit, velocity scale factor) are defined with named constants at the top of the file and that no pin numbers or timing literals appear anywhere else in the sketch.

**Acceptance Scenarios**:

1. **Given** the firmware source, **When** a hardware operator reviews the first section of the main sketch file, **Then** every hardware pin assignment is visible as a named constant with a descriptive comment.
2. **Given** the operator changes the pan step pin constant to a different number and recompiles, **When** the firmware runs, **Then** the step pulses appear on the newly configured pin — no other code changes are needed.
3. **Given** the timing constants (heartbeat interval, velocity-to-frequency scale), **When** the operator changes them and recompiles, **Then** the new values are in effect with no other code changes required.

---

### Edge Cases

- What happens if a step counter (`int32_t`) reaches `INT32_MAX` or `INT32_MIN`? → The firmware clamps the value at the boundary and does not allow it to wrap. A warning or sentinel `POS` value is emitted so the Jetson can detect the condition; normal operation continues on the other axis.
- What happens when the serial buffer contains a malformed or partial command (e.g. `V 100.0\n` missing tilt value)? → Firmware discards the incomplete command and awaits the next valid line.
- What happens if both a pan limit and a tilt limit trigger simultaneously? → Both axes stop; two `LIMIT` messages are sent.
- What happens when the velocity value is extremely large (beyond the stepper driver's maximum step rate)? → Firmware clamps the step frequency to the configured maximum pulse rate rather than skipping steps or crashing.
- What happens if the serial connection to the Jetson is lost mid-operation? → The firmware continues operating at the last commanded velocity; it does not automatically stop motors, since the Jetson is responsible for sending `V 0.0 0.0\n` before disconnecting. (No auto-stop on disconnect; the Jetson watchdog handles this at the application layer.)
- What happens when a limit is already active at startup? → The affected axis is treated as at-limit from boot; motion in the limit direction is blocked until cleared by opposite-direction commands.
- What happens if the LRF `SoftwareSerial` RX receives a corrupt or partial 8-byte binary frame (sync/header mismatch, checksum failure, or fewer than 8 bytes within the read timeout)? → Firmware validates the frame per FR-027, discards the failed frame, flushes the RX buffer, and returns `DIST -1.0\n` to the Jetson. Each read attempt starts fresh; the main control loop is not blocked.
- What happens when the LRF reply STA byte is `0x00` (measurement failure)? → Firmware treats STA=0x00 as a ranging failure regardless of checksum validity; returns `DIST -1.0\n`. Error codes `0x00` (no echo), `0x16` (below minimum range), and `0x18` (no echo, alternate) may appear as the STA/ErrCode byte; all produce `DIST -1.0\n`. Error codes `0x00–0x07` indicate a hardware error range; same handling applies.
- What happens when the LRF emits a boot self-test frame (`55 AA 80 ...`) at power-on? → The firmware attempts to read and discard this frame in `setup()` within `LRF_BOOT_TIMEOUT_MS`. STA=0x01 (success) is silently discarded; STA=0x00 (failure) MAY be logged as `LRF_BOOT_ERR <ErrCode>\n`. If no boot frame arrives within the timeout, startup continues normally (per FR-028).
- What happens if a `55 AA 80 ...` boot notification frame arrives unexpectedly during normal operation (e.g. LRF resets mid-session)? → The frame will fail the Function Word check for the expected ranging response (`0x88`) and be discarded by the frame-validation logic (FR-027); the pending `L\n` request yields `DIST -1.0\n`.

---

## Requirements *(mandatory)*

### Functional Requirements

**Serial Communication**

- **FR-001**: The firmware MUST communicate with the Jetson at 115200 baud over the USB serial interface.
- **FR-002**: The firmware MUST parse velocity commands in the format `V <pan_speed> <tilt_speed>\n` where both values are signed floating-point numbers.
- **FR-003**: The firmware MUST parse the laser trigger command `L\n` as a distinct command with no arguments.
- **FR-004**: The firmware MUST ignore and discard any received line that does not match a known command format, without stalling the main loop.
- **FR-005**: The firmware MUST transmit `DIST <value>\n` in response to an `L\n` command, where `<value>` is a floating-point distance in metres.
- **FR-006**: The firmware MUST transmit `POS <pan_steps> <tilt_steps>\n` as a periodic heartbeat at a configurable interval, where both values are `int32_t` (32-bit signed integer) accumulated step counts from power-on. If either accumulator approaches `INT32_MAX` or `INT32_MIN`, the firmware MUST clamp the value and must not silently wrap.
- **FR-007**: The firmware MUST transmit `LIMIT <axis> <direction>\n` when a limit switch triggers, where `<axis>` is `PAN` or `TILT` and `<direction>` is `LEFT`, `RIGHT`, `UP`, or `DOWN`.
- **FR-008**: `LIMIT` notifications MUST use a **state-transition + software debounce** strategy to prevent serial bus flooding from a persistently active switch. The firmware MUST require the limit switch pin to be continuously LOW for ≥ `LIMIT_DEBOUNCE_MS` (5 ms) before emitting a `LIMIT` message. Only **one** `LIMIT` message is sent per confirmed LOW state-transition; no further message is sent while the pin remains held LOW. A new `LIMIT` message is only permitted after the pin returns HIGH and subsequently sustains a new LOW for ≥ `LIMIT_DEBOUNCE_MS`.

**Motor Control**

- **FR-009**: The firmware MUST drive each stepper motor via step and direction output signals compatible with industry-standard stepper driver modules (A4988/DRV8825 signal interface). The firmware MUST also manage the shared stepper driver enable signal (`STEPPER_ENABLE_PIN`, default: D8 on CNC Shield V3): this pin MUST be driven LOW during `setup()` to enable all drivers. The enable pin is active-LOW on the CNC Shield V3; pulling it HIGH disables all drivers simultaneously.
- **FR-009a**: `STEPPER_ENABLE_PIN` (CNC Shield V3: D8, active-LOW) MUST be defined as a named constant in the configuration block. The firmware MUST call `pinMode(STEPPER_ENABLE_PIN, OUTPUT)` and `digitalWrite(STEPPER_ENABLE_PIN, LOW)` during `setup()` before any velocity commands are processed. The enable pin is driven LOW once and held LOW permanently — no dynamic enable/disable logic is implemented (tilt axis must maintain holding torque at rest; see Assumptions).
- **FR-010**: The firmware MUST translate the received float velocity values into step pulse intervals using non-blocking `micros()` scheduling: each axis maintains a `nextStepTime` variable; the main loop fires a step pulse when `micros() >= nextStepTime` and immediately recomputes the next interval. No `delay()` or blocking wait is permitted at any point in the firmware.
- **FR-011**: Pan positive velocity MUST produce rightward motion; pan negative velocity MUST produce leftward motion. Tilt positive velocity MUST produce upward motion; tilt negative velocity MUST produce downward motion.
- **FR-012**: Receiving a velocity of `0.0` on an axis MUST immediately cease step pulses on that axis.
- **FR-013**: New velocity commands MUST update the step rate without requiring a full stop/restart of the pulse train.
- **FR-014**: The step pulse frequency MUST be clamped to a configurable maximum so it never exceeds the safe operating rate of the configured stepper driver.

**Limit Switch Safety**

- **FR-015**: The firmware MUST monitor digital limit switch inputs for all four extremes (pan-left, pan-right, tilt-up, tilt-down). All limit switch pins MUST be configured as `INPUT_PULLUP`. Switches are wired Normally-Open (NO) with one leg to the GPIO pin and the other to GND — no external resistor required. Pin reads HIGH = open/untriggered; pin reads LOW = switch closed/triggered (active-LOW). **CNC Shield V3 pin assignments**: `LIMIT_PAN_LEFT_PIN = D9` (X_Limit header), `LIMIT_PAN_RIGHT_PIN = D10` (Y_Limit header), `LIMIT_TILT_DOWN_PIN = D11` (Z_Limit header, gravity-critical stop), `LIMIT_TILT_UP_PIN = D12` (Arduino header pin, accessed via pass-through/solder point beneath shield — not a shield header). All four constants MUST be defined in the configuration block.
- **FR-016**: When a limit switch triggers, the firmware MUST immediately cease step pulses on the affected axis and direction.
- **FR-017**: When a limit is active, motion on that axis in the opposite (safe) direction MUST remain unblocked.
- **FR-018**: Limit switches MUST be handled within the same main-loop cycle as motor stepping — there MUST NOT be a delay path that allows significant over-travel before the stop takes effect.

**Laser Rangefinder**

- **FR-019**: On receipt of `L\n` from the Jetson, the firmware MUST transmit the LRF **binary trigger sequence** over the LRF `SoftwareSerial` TX line to initiate a single-ranging measurement. The trigger is a binary byte sequence (NOT an ASCII command and NOT a GPIO pulse); the exact byte array MUST be defined as a named constant (e.g. `constexpr uint8_t LRF_TRIGGER[]`) in the configuration block. The single-ranging trigger frame is `55 AA 88 FF FF FF FF 84` (8 bytes): sync `0x55 0xAA`, Function Word `0x88`, payload `0xFF 0xFF 0xFF 0xFF`, checksum `0x84` = (`0x88 + 0xFF + 0xFF + 0xFF + 0xFF`) & `0xFF`. See `### LRF Binary Protocol` for the full protocol reference.
- **FR-020**: The firmware MUST communicate with the LRF via a `SoftwareSerial` instance on two spare digital GPIO (General-Purpose Input/Output) pins (NOT UART0, which is reserved for the Jetson USB/CDC link). **CNC Shield V3 pin assignments**: `LRF_RX_PIN = A0` (Arduino analog pin 0, used as digital GPIO) and `LRF_TX_PIN = A1` (Arduino analog pin 1, used as digital GPIO). These pins are completely free on the CNC Shield V3 and carry no onboard load — they are the safest pairing for `SoftwareSerial` RX/TX at 115200 baud. Both constants MUST be defined in the configuration block. The `SoftwareSerial` instance MUST be initialised at **115200 baud, 8 data bits** (baud rate defined as `LRF_SOFTSERIAL_BAUD = 115200` in the configuration block). The firmware sends the **binary trigger sequence** (FR-019) over `SoftwareSerial` TX; the LRF responds with an **8-byte binary response frame** on `SoftwareSerial` RX. The firmware MUST validate the 8-byte frame integrity (see FR-027) before extracting the distance value; a frame that fails the integrity check MUST be treated as a ranging failure. Additionally, the firmware MUST check the **STA byte** (byte[3] of the reply frame): `STA=0x01` indicates a successful measurement; `STA=0x00` indicates measurement failure and MUST be treated as a ranging failure equivalent to a checksum error, producing `DIST -1.0\n`. Distance is extracted only when both integrity validation and STA=0x01 are satisfied: `distance_m = ((uint16_t)DIS_H << 8 | DIS_L) / 10.0`, where `DIS_H` is byte[5] and `DIS_L` is byte[6] of the reply frame. The firmware transmits `DIST <value>\n` to the Jetson over `Serial` (UART0/USB). **AVR SoftwareSerial reliability constraint**: 115200 baud is at the upper limit of `SoftwareSerial` reliability on AVR Uno R3 due to interrupt latency; byte errors are possible under CPU load. Frame-integrity validation (FR-027) is the primary mitigation. If the frame error rate proves unacceptable during hardware testing, `LRF_SOFTSERIAL_BAUD` MUST be reduced to the next supported rate (e.g. 57600 baud) — a configuration-block change only (see CONSTRAINT-001).
- **FR-021**: If no valid reading is obtained within the configured timeout, OR if the received 8-byte frame fails integrity validation (checksum mismatch, wrong header/sync bytes, truncated frame — see FR-027), the firmware MUST respond with a sentinel error value (`DIST -1.0\n`) and must not block the main control loop.

- **FR-027**: The firmware MUST validate the complete 8-byte LRF binary response frame before extracting the distance value. Validation criteria:
  - **Sync bytes**: byte[0] MUST equal `0x55` AND byte[1] MUST equal `0xAA`. Any frame not starting with these two bytes MUST be discarded.
  - **Checksum**: The reply-frame checksum (byte[7]) equals the 8-bit truncated sum of bytes 0–6: `checksum = (byte[0] + byte[1] + byte[2] + byte[3] + byte[4] + byte[5] + byte[6]) & 0xFF`. A mismatch MUST cause the frame to be discarded.
  - **STA byte** (byte[3]): `0x01` = measurement successful (proceed to distance extraction); `0x00` = measurement failure (discard and return `DIST -1.0\n`). See FR-020 for full STA handling.
  - These constants MUST be defined in the configuration block: `LRF_SYNC_H = 0x55`, `LRF_SYNC_L = 0xAA`, `LRF_FRAME_LEN = 8`.
  Any frame that is incomplete (fewer than 8 bytes received within the configured timeout window) or fails any of the above validation steps MUST be discarded in its entirety; the `SoftwareSerial` RX buffer MUST be flushed after a failed read attempt. No partially-parsed or unvalidated distance value may be forwarded to the Jetson.

- **FR-028**: On firmware startup, the LRF module MAY emit a single boot self-test notification frame (`55 AA 80 STA 00 00 ErrCode CHK`, reply-only — no send required). The firmware MUST attempt to read and discard this frame during `setup()` by waiting up to `LRF_BOOT_TIMEOUT_MS` (configurable, default: 500 ms) for an 8-byte frame starting with `0x55 0xAA 0x80`. If received: `STA=0x01` (success) — discard silently; `STA=0x00` (failure) — the firmware MAY log the `ErrCode` via `Serial` as a diagnostic message (e.g. `LRF_BOOT_ERR <ErrCode>\n`) but MUST NOT block startup. If no boot frame is received within `LRF_BOOT_TIMEOUT_MS`, the firmware proceeds normally (some module revisions do not emit a boot frame on success).

### LRF Binary Protocol

The firmware communicates with the LRF module using a fixed 8-byte binary framed protocol over `SoftwareSerial` at 115200 baud. This section is the authoritative protocol reference; all magic bytes referenced here MUST be represented as named constants in the configuration block.

**Frame layout (both send and reply):**

| Byte | Index | Field | Notes |
|------|-------|-------|-------|
| Frame Header H | 0 | Sync byte 1 | Always `0x55` |
| Frame Header L | 1 | Sync byte 2 | Always `0xAA` |
| Function Word | 2 | Command/response code | e.g. `0x88` = single ranging |
| D1 | 3 | Data byte 1 / STA | Reply: status byte (`0x01`=ok, `0x00`=fail) |
| D2 | 4 | Data byte 2 | Command: `0xFF`; Reply: `0xFF` or high data |
| D3 | 5 | Data byte 3 / DIS_H | Reply: distance high byte |
| D4 | 6 | Data byte 4 / DIS_L | Reply: distance low byte |
| Checksum | 7 | Frame integrity | See checksum formulas below |

**Send-frame checksum:** `(byte[2] + byte[3] + byte[4] + byte[5] + byte[6]) & 0xFF` — sum of Function Word + D1..D4.

**Reply-frame checksum:** `(byte[0] + byte[1] + byte[2] + byte[3] + byte[4] + byte[5] + byte[6]) & 0xFF` — sum of all 7 bytes preceding the checksum byte.

**Command table:**

| Command | Send (hex) | Reply (hex) | Firmware use |
|---------|-----------|------------|--------------|
| Single ranging | `55 AA 88 FF FF FF FF 84` | `55 AA 88 STA FF DIS_H DIS_L CHK` | Primary command for `L\n` |
| Continuous ranging | `55 AA 89 FF FF FF FF 85` | Same as single ranging reply | Not used in primary firmware flow |
| Stop ranging | `55 AA 8E FF FF FF FF 8A` | `55 AA 8E STA FF FF FF CHK` | Stops continuous mode |
| Angular measurement | `55 AA 8A FF FF FF FF 86` | `55 AA 8A STA FF ANG_H ANG_L CHK` | Not used in primary firmware flow |
| Boot self-test | *(reply only — no send)* | `55 AA 80 STA 00 00 ErrCode CHK` | Emitted by LRF on power-on; see FR-028 |

**Distance extraction (single/continuous ranging reply):**
- STA byte (byte[3]): `0x01` = measurement successful; `0x00` = measurement failure → return `DIST -1.0\n`.
- Raw distance: `(DIS_H << 8) | DIS_L` — unsigned 16-bit big-endian composite.
- Distance in metres: `raw_value / 10.0` (the module encodes distance as real_distance × 10 in the raw integer).
- Example: `DIS_H=0x00, DIS_L=0x0F` → raw = 15 → distance = 1.5 m.

**Error / status codes (ErrCode or STA=0x00 failure context):**

| Code | Meaning |
|------|---------|
| `0x00` | No echo signal received |
| `0x16` | Out of range — target below minimum range |
| `0x18` | No echo signal received (alternate code) |
| `0x00–0x07` | Hardware error range |



- **FR-022**: All hardware pin assignments MUST be defined as named constants in a dedicated configuration section at the top of the main sketch file.
- **FR-023**: All timing constants (heartbeat interval, velocity scale factor, maximum step frequency, serial line buffer length (`SERIAL_LINE_BUF_LEN` = `64`), LRF `SoftwareSerial` baud rate (`LRF_SOFTSERIAL_BAUD`, default: `115200`), LRF frame length (`LRF_FRAME_LEN` = `8`), LRF sync bytes (`LRF_SYNC_H = 0x55`, `LRF_SYNC_L = 0xAA`), LRF binary trigger byte sequence (`LRF_TRIGGER[]` = `{0x55, 0xAA, 0x88, 0xFF, 0xFF, 0xFF, 0xFF, 0x84}`), LRF read timeout (`LRF_READ_TIMEOUT_MS` = `100`), LRF boot timeout (`LRF_BOOT_TIMEOUT_MS`, default: `500`), limit switch debounce window (`LIMIT_DEBOUNCE_MS` = `5`)) MUST be defined as named constants in the same configuration section.
- **FR-024**: No pin numbers or timing literals MUST appear inline in the logic sections of the sketch.
- **FR-025**: The firmware source MUST be structured as a primary `.ino` sketch file; motor control and serial parsing logic MAY be extracted into companion `.h`/`.cpp` files for readability.
- **FR-026**: The firmware MUST NOT use `delay()` or any other blocking wait (e.g. `while (!Serial.available())` busy-loops, blocking `SoftwareSerial` reads) anywhere in the sketch. All timing and waiting MUST be implemented with non-blocking `millis()` / `micros()` comparisons.

### Key Entities

- **Velocity Command**: A paired (pan, tilt) float instruction from the Jetson specifying the desired angular rate of each axis; consumed by the motor control subsystem.
- **Step Count**: A **`int32_t`** (32-bit signed integer) maintained per axis tracking cumulative steps from power-on; the primary position representation for this system. Range: ±2,147,483,647 steps (≈±10.7 million full motor revolutions at 200 steps/rev). Must be clamped — not wrapped — if the physical limit is somehow approached.
- **Limit Switch State**: A boolean flag per axis-direction reflecting whether the physical end-stop is currently triggered; gates motion output.
- **Range Reading**: A floating-point distance in metres extracted from the LRF's 8-byte binary response frame and transmitted to the Jetson as a `DIST` message. Only readings from frames that pass integrity validation (FR-027) are forwarded; failed or timed-out frames yield `DIST -1.0\n`.
- **Configuration Block**: The top-of-sketch set of named constants that fully describes the hardware wiring and timing parameters for a given physical unit.

---

## Non-Functional Requirements *(mandatory)*

### Reliability & Watchdog

- **NFR-001**: The firmware MUST enable the AVR hardware WDT (Watchdog Timer) with a 2-second timeout by calling `wdt_enable(WDTO_2S)` from `<avr/wdt.h>` as the **last step of `setup()`**, ensuring a hang during any hardware initialisation phase is also caught.
- **NFR-002**: The main `loop()` MUST call `wdt_reset()` **exactly once per iteration** as its first statement, unconditionally resetting the WDT timer. If `loop()` ever fails to return within 2 seconds — due to a blocking I/O call, infinite sub-loop, or any unexpected hang — the WDT forces an automatic hardware reset, recovering the system without requiring manual power cycling.
- **NFR-003**: The WDT is strictly a hang-recovery mechanism, NOT a serial-disconnect watchdog. The firmware does NOT automatically stop motors on serial timeout (the Jetson is responsible for sending `V 0.0 0.0\n` before disconnect; see Assumptions).

### Hardware Portability

- **NFR-004**: The current target platform is **Arduino Uno R3 (AVR architecture)**. Future planned targets include **ESP32** and **Teensy 4.0**. The firmware architecture MUST NOT assume AVR-only: all hardware-specific elements — pin assignments, baud rates, timing constants, and platform-specific APIs (`<avr/wdt.h>` WDT, `SoftwareSerial`, `micros()`/`millis()`) — MUST be isolated in the configuration block (top of main `.ino` or a companion `config.h`).
- **NFR-005**: Porting to a new platform MUST require only changes to the configuration block. Logic sections MUST contain no inline platform-specific assumptions, literals, or API calls that are not abstracted through the configuration block.

### SoftwareSerial & LRF Reliability (AVR-Specific)

- **NFR-006**: On the AVR Uno R3 platform, `SoftwareSerial` at 115200 baud operates at the upper limit of reliable reception due to AVR interrupt latency under concurrent workload (step-pulse scheduling, USB serial handling). This is a **documented hardware platform risk** (see also CONSTRAINT-001). The firmware MUST mitigate this via mandatory frame-integrity validation on every received 8-byte LRF binary frame (FR-027) — corrupt frames are discarded and treated as ranging failures. If hardware testing reveals an unacceptable frame error rate, `LRF_SOFTSERIAL_BAUD` MUST be reduced to the next supported rate (e.g. 57600 baud) — a configuration-block change only (per NFR-004/NFR-005).
- **NFR-007**: The LRF `SoftwareSerial` read MUST NOT use blocking `while`-loops or `delay()`. All LRF frame reception MUST be implemented with non-blocking polling: check `SoftwareSerial.available()` each `loop()` iteration, accumulate bytes into a frame buffer, and only process a frame once all `LRF_FRAME_LEN` (8) bytes are present or `LRF_READ_TIMEOUT_MS` (100 ms) elapses — whichever comes first. On timeout, the incomplete frame is discarded and `DIST -1.0\n` is returned. This 100 ms ceiling leaves 400 ms of headroom against the 500 ms end-to-end DIST budget (SC-005) and ensures `SoftwareSerial` RX activity does not violate the non-blocking constraint (FR-026, NFR-002).

---

## Constraints & Tradeoffs

- **CONSTRAINT-001 — SoftwareSerial at 115200 baud on AVR Uno R3**: 115200 baud is at the upper reliability limit of the AVR `SoftwareSerial` library on a 16 MHz AVR core. At this baud rate each bit period is ≈8.7 µs; `SoftwareSerial` disables global interrupts during byte reception, producing up to ≈87 µs of interrupt latency per received byte — for an 8-byte response frame this can create up to ≈700 µs of interrupt blackout per LRF read. This conflicts with the non-blocking motor step scheduler (FR-010, FR-026) and introduces framing-error risk under interrupt load. **Mandatory mitigations**: (1) FR-027 frame-integrity validation must reject corrupt frames before use; (2) `LRF_SOFTSERIAL_BAUD` is a named configuration constant — if testing reveals an unacceptable error rate it MUST be reduced to the next supported rate (e.g. 57600 baud) with no logic changes required. This risk MUST be noted in a code comment at the `SoftwareSerial` initialisation site.
- **TRADEOFF-001 — SoftwareSerial vs. dedicated hardware UART for LRF**: Routing the LRF through `SoftwareSerial` preserves UART0/USB for the Jetson at the cost of reduced reliability at high baud rates (see CONSTRAINT-001). The alternative — a USB-to-Serial adapter for the Jetson or a hardware-modified LRF wiring to a dedicated UART — is deferred to hardware revision if `SoftwareSerial` proves insufficient during extended testing.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A velocity command sent from the Jetson results in visible stepper motor motion within 10 ms of the command being received — there is no perceptible lag between command and motion onset.
- **SC-002**: A `V 0.0 0.0\n` command stops both motors within one main-loop cycle (target: under 5 ms) — the turret cannot "coast" after a stop command.
- **SC-003**: A triggered limit switch halts the affected axis within one main-loop cycle — over-travel past a triggered limit is negligible (< 1 full step pulse interval).
- **SC-004**: `POS` heartbeat messages are broadcast at the configured interval with a jitter of no more than ±20% of the configured period under normal operating conditions.
- **SC-005**: A `DIST` response is returned within 500 ms of an `L\n` command under normal rangefinder operating conditions — ranging does not block the control loop for longer than this. (`LRF_READ_TIMEOUT_MS` = 100 ms consumes at most 100 ms of this budget, leaving ≥400 ms headroom for trigger transmission, module processing, and serial response serialisation.)
- **SC-006**: All four limit switch inputs can be independently triggered and produce the correct `LIMIT` message; no cross-axis interference occurs.
- **SC-007**: Changing any pin assignment or timing constant in the configuration section and recompiling produces a correctly functioning firmware with no other code changes required — verified for at least 3 different constants.
- **SC-008**: The firmware runs continuously for at least 30 minutes of active motor operation without crashing, hanging, or producing corrupt serial output.
- **SC-009**: If the firmware is made to hang (e.g., a test that introduces a blocking delay > 2 seconds), the AVR hardware WDT (2-second timeout) triggers an automatic reset — the board restarts within 2 seconds and resumes normal operation, confirming hang recovery without manual intervention.

---

## Assumptions

- The stepper driver modules present a standard step/direction/enable signal interface (A4988 or DRV8825 compatible); microstepping configuration is set on the driver hardware, not in firmware. **Hardware platform**: Arduino Uno CNC Shield V3 houses the driver modules. Pan axis occupies the X-axis slot (`PAN_STEP_PIN = D2`, `PAN_DIR_PIN = D5`); Tilt axis occupies the Y-axis slot (`TILT_STEP_PIN = D3`, `TILT_DIR_PIN = D6`). The shared enable pin is D8 (active-LOW, `STEPPER_ENABLE_PIN = 8`), driven LOW once in `setup()`. The Z-axis slot (D4/D7) is a hardware spare. CNC Shield limit switch headers: X_Limit=D9, Y_Limit=D10, Z_Limit=D11.
- The velocity float values from the Jetson are in abstract "speed units" (not radians/sec or degrees/sec); a configurable scale factor in the firmware maps them to step pulse frequencies.
- Limit switches are normally-open (NO) and pull to ground when triggered; internal pull-up resistors on the Arduino are used.
- The target microcontroller is an **Arduino Uno R3**. UART0 is the sole hardware serial port and is reserved for the USB/CDC Jetson link (`Serial`). There is no independent secondary hardware UART. The LRF communicates via a **`SoftwareSerial` instance on analog pins A0 (D14) and A1 (D15)** used as digital GPIO (`LRF_RX_PIN = A0`, `LRF_TX_PIN = A1`, defined in the configuration block). These pins are load-free and fully unoccupied on the CNC Shield V3.
- The laser rangefinder module communicates over `SoftwareSerial` at **115200 baud, 8 data bits** (`LRF_SOFTSERIAL_BAUD`, defined in the configuration block). The trigger is a **binary byte sequence** sent by the firmware over `SoftwareSerial` TX (single-ranging command: `55 AA 88 FF FF FF FF 84`; exact bytes defined as `LRF_TRIGGER[]` in the configuration block). The LRF responds with an **8-byte binary response frame** on `SoftwareSerial` RX (sync `0x55 0xAA`, Function Word `0x88`, STA byte, DIS_H, DIS_L, checksum). The firmware validates sync bytes, reply-frame checksum (sum of bytes 0–6 & 0xFF), and STA byte before extracting distance as `(DIS_H<<8 | DIS_L) / 10.0` metres (FR-027, FR-020). STA=0x00 or any validation failure produces `DIST -1.0\n`. A boot self-test frame (`55 AA 80 ...`) is expected at power-on and is discarded during `setup()` per FR-028. 115200 baud on `SoftwareSerial` is at the upper limit of AVR reliability — frame-integrity validation and configuration-block baud override are the primary mitigations (see CONSTRAINT-001, NFR-006).
- **The main control loop is strictly non-blocking and cooperative.** All subsystems — step-pulse generation, serial command parsing, limit switch checking, LRF polling, and heartbeat transmission — share a single `loop()` with no `delay()` calls. Each axis uses a `nextStepTime` (`unsigned long`, `micros()` domain) to schedule pulses independently; all other time-based events use `millis()` comparisons.
- Step counters are typed `int32_t` (explicitly 32-bit signed). At 200 steps/rev the range of ±2,147,483,647 steps far exceeds any mechanical travel possible on a pan/tilt turret. Overflow is nonetheless guarded: the accumulator clamps at `INT32_MAX` / `INT32_MIN` and the firmware emits a warning rather than silently wrapping.
- The Jetson is responsible for motor safety on serial disconnect (it sends `V 0.0 0.0\n` before shutting down); the firmware does not implement an autonomous watchdog stop on serial timeout. (The AVR hardware WDT handles firmware hang-recovery independently — see NFR-001/NFR-002 — but that is distinct from serial-disconnect behaviour.)
- Step counts are reset to zero at firmware power-on/reset; there is no persistent position memory across power cycles.
- The heartbeat interval default of 100 ms is appropriate for the Jetson's disconnection-detection logic.
- Both stepper motors are assumed to be identical in wiring; the configuration block provides separate constants for each axis to allow independent tuning.
- **Hardware portability**: The firmware architecture anticipates future migration to ESP32 or Teensy 4.0. All platform-specific APIs (`<avr/wdt.h>` WDT, `SoftwareSerial`, AVR-specific interrupt registers) MUST remain isolated in the configuration block. The logic layer is platform-neutral by design; porting is a configuration-block change only, not a logic rewrite (see NFR-004/NFR-005).
