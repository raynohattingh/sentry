# Implementation Plan: LRF Enable Pin Configuration

**Branch**: `[003-lrf-enable-pin]` | **Date**: 2026-03-23 | **Spec**: [/Users/raynohattingh/dev/sentry/specs/003-lrf-enable-pin/spec.md]  
**Input**: Feature specification from `/Users/raynohattingh/dev/sentry/specs/003-lrf-enable-pin/spec.md`

## Summary

Add an explicit Arduino-side LRF enable control to the sentry firmware so the LRF1000A can be powered correctly using its documented active-low enable behavior. The firmware will keep the sensor disabled while idle, assert the enable pin only around demand-driven ranging operations, preserve the existing `CMD_LASER`/`DIST` workflow, and document the new pin assignment and polarity clearly in both firmware configuration and operator-facing documentation.

## Technical Context

**Language/Version**: Arduino C++ on Arduino Uno R3; host-native test build via PlatformIO native  
**Primary Dependencies**: Arduino core / `Arduino.h`, `SoftwareSerial`, PlatformIO native test harness  
**Storage**: N/A  
**Testing**: PlatformIO native tests (`pio test --environment native`) plus existing Arduino host-side suites, automated end-to-end firmware flow coverage for `CMD_LASER -> DIST`, and hardware-in-the-loop validation  
**Target Platform**: Arduino Uno R3 + CNC Shield V3 + LRF1000A module  
**Project Type**: Embedded firmware  
**Performance Goals**: Preserve existing demand-driven ranging behavior and avoid degrading loop responsiveness or `POS` heartbeat cadence; keep LRF power asserted only for the active ranging window; capture no-regression evidence for ranging latency and loop cadence before merge  
**Constraints**: No magic pin literals outside `config.h`; preserve host-testability under `NATIVE_ENV`; no regression to existing serial protocol or LRF frame parsing behavior; active-low enable is authoritative from datasheet and must remain explicit  
**Scale/Scope**: Single Arduino firmware feature touching hardware configuration, LRF control flow, documentation, and host-native tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality**: PASS — change is scoped to `config.h`, `lrf.*`, and `sentry_turret.ino`, with new pin behavior represented through named constants/helpers rather than inline literals.
- **Testing Standards**: PASS — plan includes host-native unit coverage, automated end-to-end firmware flow coverage, and hardware-in-the-loop validation because the feature touches sensor power control.
- **UX Consistency**: PASS — user-facing docs/config reference will describe the new active-low enable behavior and idle-vs-ranging power semantics explicitly.
- **Performance Requirements**: PASS — feature preserves demand-driven ranging and should reduce idle power use; validation will include explicit no-regression evidence for loop behavior and demand-triggered ranging flow.

## Project Structure

### Documentation (this feature)

```text
specs/003-lrf-enable-pin/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
arduino/sentry_turret/
├── src/
│   ├── config.h
│   ├── lrf.h
│   ├── lrf.cpp
│   └── sentry_turret.ino
├── test/
│   ├── test_lrf_frame/
│   └── test_serial_proto/
└── platformio.ini

docs/
└── LRF1000A.pdf
```

**Structure Decision**: This is a single embedded-firmware feature centered on the Arduino project. The main implementation lives in `arduino/sentry_turret/src/`, with host-native tests under `arduino/sentry_turret/test/` and supporting feature docs under `specs/003-lrf-enable-pin/`.

## Phase 0: Research

### Research Goals

1. Determine the safest firmware pattern for active-low enable control around demand-triggered LRF measurements.
2. Confirm how to keep the enable logic host-testable under `NATIVE_ENV` without depending on physical Arduino APIs in native tests.
3. Decide where to document the new enable-pin assignment and power-on polarity so future hardware changes remain explicit.

### Research Output

See: `/Users/raynohattingh/dev/sentry/specs/003-lrf-enable-pin/research.md`

## Phase 1: Design & Contracts

### Data Model

See: `/Users/raynohattingh/dev/sentry/specs/003-lrf-enable-pin/data-model.md`

### Contracts

See:

- `/Users/raynohattingh/dev/sentry/specs/003-lrf-enable-pin/contracts/lrf-enable-behavior.md`

### Quickstart

See: `/Users/raynohattingh/dev/sentry/specs/003-lrf-enable-pin/quickstart.md`

## Implementation Order

1. Add the new LRF enable pin and active/deasserted level definitions to `arduino/sentry_turret/src/config.h`.
2. Extend the LRF module interface to make enable/deassert behavior explicit and host-testable.
3. Update `sentry_turret.ino` so the LRF remains disabled while idle, powers on only for demand-triggered ranging, and returns to idle-safe power state afterward.
4. Add or extend PlatformIO native tests to cover enable polarity, idle state, ranging-window behavior, failure handling, and an end-to-end `CMD_LASER -> DIST` flow with enable gating in place.
5. Update firmware documentation and operator quickstart guidance, then run native tests, collect no-regression timing evidence, and complete hardware-in-the-loop validation.

## Post-Design Constitution Check

- **Code Quality**: PASS — the design keeps hardware control centralized in `config.h` and encapsulates enable behavior behind dedicated LRF helpers instead of scattering pin writes.
- **Testing Standards**: PASS — design includes host-native tests for logic/polarity, automated integration-style flow coverage, and HITL validation for real hardware power behavior.
- **UX Consistency**: PASS — docs will explicitly state that low powers the LRF on and that power is only asserted during active ranging.
- **Performance Requirements**: PASS — design preserves demand-driven ranging and avoids continuous sensor power draw; implementation must record no-regression timing evidence before merge.
