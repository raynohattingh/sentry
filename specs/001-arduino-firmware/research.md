# Research: Arduino Firmware — Sentry HAL

**Branch**: `001-arduino-firmware` | **Date**: 2026-02-26

## 1. Step-Pulse Generation Strategy

**Decision**: Custom non-blocking `micros()` scheduling per axis (not AccelStepper).

**Rationale**: The firmware runs a strict cooperative single-`loop()` architecture where every subsystem — step-pulse generation, serial parsing, limit switch checking, LRF polling, and heartbeat — shares CPU time with no blocking calls. AccelStepper's ISR (Interrupt Service Routine)-based `runSpeedToPosition()` uses Timer1 output-compare interrupts, which conflict with `SoftwareSerial`'s use of external-change interrupts for bit-banged reception on AVR. AccelStepper's polling variant (`run()`/`runSpeed()`) avoids the ISR conflict but adds an unnecessary dependency and wraps a concept that is cleaner expressed directly.

The chosen approach maintains one `unsigned long nextStepTime` per axis (in `micros()` domain). Each `loop()` iteration checks `micros() >= nextStepTime` and fires a pulse if due, then recomputes `nextStepTime = micros() + stepIntervalUs`. Step interval is derived from the velocity command: `stepIntervalUs = VELOCITY_SCALE_FACTOR / |velocity|` (clamped to `MIN_STEP_INTERVAL_US`).

**Alternatives considered**:
- AccelStepper polling — Rejected: dependency overhead, no acceleration needed, ISR conflict risk.
- Timer1 ISR directly — Rejected: conflicts with `SoftwareSerial`; unnecessarily complex for two axes.
- FreeRTOS task per axis — Rejected: far beyond Uno R3 2 KB SRAM limit; massively over-engineered.

---

## 2. SoftwareSerial at 115200 Baud on AVR — Reliability Assessment

**Decision**: Use `SoftwareSerial` at 115200 baud with mandatory frame-integrity validation (FR-027) as the primary mitigation; fall back to 57600 baud via configuration-only change if testing reveals unacceptable error rates.

**Rationale**: At 16 MHz, each bit period at 115200 baud is ≈8.68 µs. AVR `SoftwareSerial` disables global interrupts during byte reception; for an 8-byte response frame this produces up to ≈695 µs of interrupt blackout per LRF read. This can cause missed `micros()` pulse deadlines and introduce step jitter during LRF ranging operations.

Mitigations built into the design:
1. LRF reads are only triggered on receipt of `L\n`; they are not continuous. The blackout window is bounded and infrequent.
2. Every received frame is validated (sync bytes + checksum + STA byte) before use; corrupt bytes are discarded, not forwarded.
3. `LRF_SOFTSERIAL_BAUD` is a named constant in `config.h`. Dropping to 57600 baud halves the interrupt blackout window and requires no logic changes.

If the AVR platform is retired in favour of ESP32 or Teensy 4.0, both platforms have multiple independent hardware UARTs — the `SoftwareSerial` constraint disappears entirely.

**Alternatives considered**:
- Hardware UART via USB-to-serial adapter for Jetson, freeing UART0 for LRF — Rejected: requires additional hardware; increases BOM (Bill of Materials) cost and wiring complexity.
- I²C (Inter-Integrated Circuit) or SPI (Serial Peripheral Interface) for LRF — Rejected: the specific LRF module uses a UART binary protocol; changing the interface requires a different module.
- 9600 baud for LRF — Rejected: much higher latency per frame; would likely breach SC-005 500 ms budget.

---

## 3. AVR WDT (Watchdog Timer) Configuration

**Decision**: `wdt_enable(WDTO_2S)` from `<avr/wdt.h>`, called as the last statement in `setup()`. `wdt_reset()` called as the first statement in every `loop()` iteration.

**Rationale**: The 2-second timeout is safe because the non-blocking cooperative loop is expected to complete each iteration in well under 1 ms under normal load. The 2-second ceiling is a generous safety margin that catches genuine hangs (a blocked `while` loop, a stalled serial read, an unexpected spin-wait) while being short enough to recover the system quickly. Calling `wdt_enable()` last in `setup()` ensures hardware initialisation faults during `Serial.begin()` or `SoftwareSerial` init are also caught.

**Known AVR bootloader interaction**: Some Arduino bootloaders (Optiboot v4 and earlier) do not properly disable the WDT after a WDT reset, causing an infinite reset loop. Optiboot v6+ (shipped with Arduino Uno R3 boards manufactured 2016 and later) handles this correctly. If an infinite-reset symptom is observed during testing, the solution is to flash an updated Optiboot bootloader.

**Alternatives considered**:
- Software watchdog using `millis()` — Rejected: a hung CPU cannot service a software check; only a hardware WDT provides true hang recovery.
- 8-second WDT timeout — Rejected: too long for a safety-critical turret system; 2 seconds is a reasonable recovery window.
- No watchdog — Rejected: violates SC-009 and NFR-001.

---

## 4. PlatformIO Native Test Strategy for AVR Firmware

**Decision**: Use PlatformIO's `native` test environment to compile and run pure-logic modules (serial parser, LRF frame validator, limit debounce state machine) as host-executable test binaries. Hardware-pin-touching code is excluded from the native build via compile-time guards.

**Rationale**: PlatformIO supports a `[env:native]` configuration that compiles the project with the host GCC (GNU Compiler Collection) toolchain rather than avr-gcc. By structuring the modules so that only `config.h` references AVR/Arduino-specific types (`uint8_t`, `unsigned long`) — all of which exist as standard C++ types on the host — the logic modules can be compiled and tested without a physical board. The Arduino `Serial`, `SoftwareSerial`, `micros()`, and `millis()` API calls are restricted to `sentry_turret.ino` and thin driver shims that are replaced by mocks in the native test environment.

**Test file structure**:
- `test_serial_proto.cpp` — tests `parseCommand()` for valid `V`/`L` lines, malformed input, missing arguments, and buffer overflow.
- `test_lrf_frame.cpp` — tests `validateFrame()` for correct sync bytes, checksum computation, STA byte handling, distance extraction formula, and all error code paths.
- `test_limits.cpp` — tests the debounce state machine: clean HIGH→LOW transition fires exactly one event; held-LOW produces no repeats; LOW→HIGH→LOW fires a second event after `LIMIT_DEBOUNCE_MS`.

**Alternatives considered**:
- Arduino unit test frameworks (AUnit, ArduinoUnit) — Rejected: require physical hardware or a simulator; slower iteration loop.
- Host-only test with raw Makefiles — Rejected: more friction than PlatformIO's `pio test -e native`; harder to integrate with CI.

---

## 5. Memory Budget Assessment (ATmega328P)

**Flash**: 32 KB available.  
Estimated usage: ~8–12 KB for the full firmware (serial parser, stepper driver, LRF framer, limit handler, WDT setup, heartbeat — all without dynamic allocation or large lookup tables). Leaves > 50% headroom.

**SRAM**: 2 KB available (2048 bytes).  
Estimated usage:
- Global structs: 2× `StepperAxis` (~16 bytes each) + 4× `LimitPin` (~8 bytes each) + `LrfReader` (~16 bytes) + serial line buffer (64 bytes) + LRF frame buffer (8 bytes) = ~168 bytes of global state.
- Stack: Arduino framework overhead + `setup()` + `loop()` + function call depth ≈ 200–300 bytes.
- Total estimate: < 500 bytes. No memory pressure; > 75% SRAM headroom.

**Recommendation**: No memory-reduction measures needed at this stage. Monitor via `avr-size` output at build time; flag if flash exceeds 80% (25.6 KB) or SRAM exceeds 60% (1.2 KB).
