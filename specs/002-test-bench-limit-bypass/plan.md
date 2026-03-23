# Implementation Plan: Test Bench Limit Switch Bypass

**Branch**: `002-test-bench-limit-bypass` | **Date**: 2026-03-23 | **Spec**: `specs/002-test-bench-limit-bypass/spec.md`  
**Input**: Feature specification from `/specs/002-test-bench-limit-bypass/spec.md`

## Summary

Add an explicit, temporary test-bench operating mode that lets the sentry run without installed hardware limit switches, while keeping MVP operation gated behind real limit-switch validation.

The design keeps the Arduino serial wire format stable, makes the Jetson the enforcement point for the saved per-unit housing profile and motion gating, and gives the Flutter app an authoritative MQTT status feed for reduced-safety warnings and blocked-motion reasons. The saved profile is persisted on the sentry unit as Jetson-local runtime configuration. Test bench mode uses preconfigured software min/max pan and tilt bounds. MVP mode requires startup validation of all four physical limit switches before motion is allowed.

## Technical Context

**Language/Version**: Python 3.10+ (Jetson), Dart/Flutter 3.x (app), C++17 / Arduino Uno R3 (firmware tests via PlatformIO native)  
**Primary Dependencies**: paho-mqtt, pytest, Flutter Riverpod, go_router, shared_preferences, mqtt_client, PlatformIO/Unity  
**Storage**: Jetson runtime config via `config.py` + environment variables, rotating JSONL telemetry log, MQTT topics for runtime status, app in-memory/status providers; no new database  
**Testing**: `pytest` for Jetson, `flutter test` for app, `pio test --environment native` for Arduino host tests, plus hardware-in-the-loop validation for switch commissioning  
**Target Platform**: NVIDIA Jetson Linux runtime, Arduino Uno R3 + CNC Shield V3, Flutter iOS/Android app  
**Project Type**: Multi-runtime embedded control system enhancement (Jetson service + mobile app + serial contract consumption)  
**Performance Goals**: Preserve existing Jetson control-loop responsiveness and >=20 FPS vision throughput; add only non-blocking status publication and O(1) motion-bound checks on command dispatch  
**Constraints**: No new serial wire commands, operator-visible reduced-safety state, all new config documented in `jetson/src/utils/config.yaml`, MVP motion blocked until limit validation completes, existing TLS MQTT posture preserved  
**Scale/Scope**: Jetson config/types/comms/control changes, app MQTT/status/model/UI updates, contract docs, quickstart docs, targeted tests; minimal or no Arduino logic changes expected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Code Quality**: Feature is decomposed into configuration, typed safety state, serial event parsing, motion gating, and UI status rendering. New constants live in `config.py` / `config.yaml`; no raw literals are required in logic paths.
- [x] **II. Testing Standards**: All new Jetson logic remains mockable through existing `SerialProtocol` / MQTT seams; app status handling is testable through current provider and widget patterns; hardware validation is explicitly called out for switch commissioning.
- [x] **III. UX Consistency**: Reduced-safety and blocked-motion messages will follow existing `[SUBSYSTEM]` conventions and be surfaced in app screens where operators choose to move or monitor the turret.
- [x] **IV. Performance Requirements**: Motion enforcement occurs at dispatch time using already-available position state; MQTT status publication is asynchronous; no blocking work is added to the camera/vision critical path.

**Post-Design Re-check**: PASS. Phase 1 artifacts keep the solution within existing stack/runtime boundaries and do not introduce constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-test-bench-limit-bypass/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mqtt-safety-status.md
│   └── serial-limit-events.md
└── tasks.md
```

### Source Code (repository root)

```text
jetson/src/
├── config.py                     ← add housing-profile + test-bench bound config
├── types.py                      ← add housing/safety/limit-event models
├── comms/
│   ├── mqtt.py                   ← add status publisher support
│   └── serial_io.py              ← parse LIMIT frames
├── hardware/
│   └── arduino_link.py           ← retain latest LIMIT events / validation progress
├── control/
│   └── turret_manager.py         ← enforce software bounds and motion gating
└── utils/
    └── config.yaml               ← document new config parameters

jetson/tests/unit/
├── test_serial_framing.py        ← extend for LIMIT parsing
├── test_turret_manager.py        ← new motion-bound / blocked-motion coverage
├── test_arduino_link.py          ← new validation-progress coverage
└── test_safety_status.py         ← new safety mode / MQTT payload coverage

jetson/tests/integration/
├── test_limit_validation_flow.py ← Jetson serial LIMIT -> validation integration
└── test_safety_status_mqtt.py    ← Jetson safety-status publish/consume integration

app/lib/
├── services/mqtt_service.dart    ← subscribe to safety-status topic
├── models/
│   ├── telemetry_record.dart     ← optional safety metadata extension if reused
│   └── safety_status.dart        ← new status model
└── features/
    ├── map/                      ← persistent safety banner / status provider
    ├── override/                 ← blocked-motion warning + gating UI
    └── settings/                 ← housing/protection summary surface

app/test/
├── unit/                         ← safety-status parsing/provider tests
└── integration/                  ← app banner / override gating tests

arduino/sentry_turret/
└── test/                         ← existing native tests; no protocol-format changes expected
```

**Structure Decision**: Keep the existing multi-runtime repository layout. Most implementation work lands in Jetson because it is the runtime authority for motion gating and startup safety. The app consumes authoritative safety status via MQTT. Arduino remains wire-compatible and primarily participates through existing `LIMIT` events and hardware-in-the-loop validation.

## Phase 0 — Research (completed)

See `research.md` for full decision records. Key decisions:

| Decision | Chosen Approach | Why |
|----------|-----------------|-----|
| Housing profile authority | Jetson-local persisted runtime config is the source of truth | Startup gating and autonomous behavior must not depend on app state, while still satisfying the saved per-unit profile requirement |
| Test bench bounds | Add explicit min/max pan/tilt config for test bench mode | Existing limit constants do not fully represent the clarified safe-range model |
| MVP limit enforcement | Require startup observation of all four existing `LIMIT` events before motion | Uses present hardware protocol without inventing new Arduino commands |
| Operator warning surface | Publish authoritative MQTT safety status and render it in app | Telemetry is target-driven and cannot guarantee a persistent warning by itself |
| Serial protocol churn | No new wire commands; extend Jetson parser to consume existing `LIMIT` lines | Minimizes firmware risk and preserves established contracts |

## Phase 1 — Design Artifacts (completed)

Artifacts generated this phase:

- `research.md` — architectural decisions and alternatives
- `data-model.md` — housing profile, safety status, limit-event, and validation-state design
- `contracts/mqtt-safety-status.md` — authoritative app-facing safety status contract
- `contracts/serial-limit-events.md` — Jetson-side consumption of existing Arduino limit events
- `quickstart.md` — setup, validation, and test commands for test bench and MVP flows

## Implementation Order (for /speckit.tasks)

Tasks should be generated in TDD order:

1. Add Jetson config constants and `config.yaml` entries for housing profile and test-bench bounds.
2. Add Jetson typed models/enums for housing profile, safety status, limit events, and validation state.
3. Extend Jetson serial parsing tests for `LIMIT <axis> <direction>` frames (RED).
4. Implement `LIMIT` frame parsing and `ArduinoLink` event tracking (GREEN).
5. Add Jetson motion-gating tests for test bench bounds and MVP blocked-motion behavior (RED).
6. Implement `TurretManager` safety enforcement and startup validation state machine (GREEN).
7. Add automated Jetson integration coverage for serial `LIMIT` ingestion -> validation state (RED).
8. Add Jetson MQTT/status payload + publish/consume integration tests (RED).
9. Implement asynchronous safety-status publication on a dedicated MQTT topic (GREEN).
10. Add app model/service/provider tests for safety-status parsing and delivery (RED).
11. Implement app subscription, status provider, map banner, override gating, and settings summary (GREEN).
12. Add profile-transition coverage for `TEST_BENCH -> MVP` invalidation (RED/GREEN).
13. Run control-loop impact measurement for safety gating/status publication and record results.
14. Run hardware-in-the-loop validation on a test bench unit and an MVP-style switch-equipped unit.

## Complexity Tracking

> No Constitution violations or stack deviations require justification.

| Concern | Mitigated By |
|---------|-------------|
| App banner could drift from unit reality | Jetson publishes authoritative safety status; app does not infer runtime safety locally |
| MVP switch presence is not electrically detectable at idle | Startup validation uses observed `LIMIT` events from all four switches before motion is enabled |
| Added safety features could affect control-loop latency | Enforcement is bounded state/position checks only; MQTT status publish stays asynchronous |
