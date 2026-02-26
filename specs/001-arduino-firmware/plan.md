# Implementation Plan: Arduino Firmware — Sentry HAL

**Branch**: `001-arduino-firmware` | **Date**: 2026-02-26 | **Spec**: [`specs/001-arduino-firmware/spec.md`](./spec.md)
**Input**: Feature specification from `specs/001-arduino-firmware/spec.md`

## Summary

Arduino Uno R3 firmware acting as the hardware abstraction layer (HAL) between the Jetson Core brain and the physical pan/tilt stepper motors. The firmware parses ASCII velocity commands from the Jetson over USB serial, drives two stepper motors using a non-blocking `micros()` cooperative scheduler, monitors four limit switches via `INPUT_PULLUP` active-LOW debounce, interfaces with a laser range finder (LRF) over `SoftwareSerial` using a custom 8-byte binary frame protocol, and broadcasts periodic position heartbeats. A 2-second AVR hardware watchdog timer (WDT) ensures the firmware recovers automatically from any hang.

All hardware-specific constants (pin assignments, baud rates, timing, protocol byte arrays) are isolated in `config.h` so that porting to a future platform (ESP32 or Teensy 4.0) requires only a configuration-block change.

## Technical Context

**Language/Version**: C++ (Arduino framework), avr-gcc (Arduino IDE ≥ 2.x or PlatformIO)
**Primary Dependencies**: `SoftwareSerial` (Arduino built-in), `<avr/wdt.h>` (AVR built-in — no external libraries required)
**Storage**: N/A — no persistent memory; step counts reset to zero on power-cycle
**Testing**: PlatformIO native tests for pure-logic unit tests; hardware HITL (Hardware-In-The-Loop) per SC-001–SC-009
**Target Platform**: Arduino Uno R3 — ATmega328P (AVR), 16 MHz, 32 KB flash, 2 KB SRAM
**Project Type**: Embedded firmware (bare-metal, single `loop()` cooperative scheduler)
**Performance Goals**: Loop completes within 2 s (WDT ceiling); velocity command → motion onset < 10 ms (SC-001); stop command ≤ 5 ms (SC-002); `DIST` response ≤ 500 ms end-to-end (SC-005)
**Constraints**: No heap allocation (`new`/`malloc` forbidden); no `delay()` or blocking waits anywhere; 32 KB flash / 2 KB SRAM budget; `int32_t` step counters clamped at `INT32_MAX`/`INT32_MIN`
**Scale/Scope**: Single-board firmware; 5 companion modules; 3 PlatformIO unit test files; 9 hardware success criteria (SC-001–SC-009)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Code Quality**: All modules have a single responsibility (`stepper`, `lrf`, `limits`, `serial_proto`, `config`). All named constants in `config.h` — zero magic numbers in logic. All public functions documented with Doxygen-style comments. Dead code and blocking stubs are prohibited.
- [x] **II. Testing Standards**: Unit tests planned for all pure-logic components (serial parser, LRF frame validator, debounce state machine) via PlatformIO native tests. Hardware-dependent output (step/direction pins, SoftwareSerial I/O) is isolated behind thin driver interfaces mockable in the native test environment. HITL acceptance tests defined per SC-001–SC-009. TDD Red–Green–Refactor confirmed for all unit-testable components.
- [x] **III. UX Consistency**: All operator-facing serial output uses consistent prefixes: `DIST`, `POS`, `LIMIT`, `LRF_BOOT_ERR` — readable, distinct, and unambiguous on the Jetson side. No visual overlays (N/A for firmware). Config parameters documented with units, valid ranges, and defaults in `config.h` comments.
- [x] **IV. Performance Requirements**: Firmware is a pure HAL — it does not affect the Jetson vision pipeline FPS. Serial round-trip budget: command → motion < 10 ms (SC-001), well within the 20 ms constitution target. `DIST` end-to-end ≤ 500 ms (SC-005). Non-blocking cooperative loop ensures no single subsystem starves another. No benchmark risk.

## Project Structure

### Documentation (this feature)

```text
specs/001-arduino-firmware/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   ├── serial-protocol.md           # Jetson ↔ Arduino ASCII serial contract
│   └── lrf-binary-protocol.md       # Arduino ↔ LRF binary frame contract
└── tasks.md                         # Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
arduino/
└── sentry_turret/
    ├── sentry_turret.ino            # Main sketch — setup(), loop(), global state
    ├── config.h                     # ALL named constants: pins, baud rates, timing,
    │                                #   protocol bytes, WDT timeout, LRF frame layout
    ├── stepper.h                    # StepperAxis struct + non-blocking pulse API
    ├── stepper.cpp                  # micros()-scheduled step/direction driver
    ├── lrf.h                        # LrfReader struct + frame parser API
    ├── lrf.cpp                      # SoftwareSerial binary frame accumulator + validator
    ├── limit_switch.h               # LimitPin struct + debounce API
    ├── limit_switch.cpp             # INPUT_PULLUP active-LOW debounce state machine
    ├── serial_proto.h               # Command parser API (V, L command types)
    └── serial_proto.cpp             # Line accumulator + tokeniser for Jetson commands

test/
└── (removed — tests moved to arduino/sentry_turret/test/)

arduino/sentry_turret/test/
├── test_serial_proto/
│   └── test_main.cpp        # Unit tests: V/L command parse, malformed input
├── test_stepper/
│   └── test_main.cpp        # Unit tests: velocity→interval, direction, clamp, FR-013
├── test_lrf_frame/
│   └── test_main.cpp        # Unit tests: sync bytes, checksum, STA, distance math
└── test_limits/
    └── test_main.cpp        # Unit tests: debounce state transitions, anti-flood
```

**Structure Decision**: Single embedded project (`arduino/sentry_turret/`) with companion `.h`/`.cpp` modules for each subsystem. Tests live in `arduino/sentry_turret/test/` using PlatformIO's conventional subdirectory layout (`test/<suite>/test_main.cpp`), compiled and executed on the host via the `native` test environment.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Custom `micros()` step scheduler instead of AccelStepper (listed in constitution) | Spec (FR-010, FR-026) mandates a strictly non-blocking cooperative loop with no library-owned ISR (Interrupt Service Routine) hooks. AccelStepper's run()/runSpeed() model abstracts step timing in ways that conflict with the per-axis `nextStepTimeUs` architecture required to co-schedule LRF polling and limit checking in the same loop body. | AccelStepper's ISR-based `runSpeedToPosition()` uses Timer1, which conflicts with `SoftwareSerial` interrupt usage on AVR; the polling variant adds overhead without gain over a direct `micros()` comparison. |
