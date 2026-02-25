# Sentry Constitution
<!--
SYNC IMPACT REPORT
==================
Version change: (unversioned template) → 1.0.0
Added sections:
  - Core Principles (I–IV): Code Quality, Testing Standards,
    UX Consistency, Performance Requirements
  - Technology Stack
  - Development Workflow
  - Governance
Templates updated:
  - .specify/templates/plan-template.md ✅ Constitution Check gates added
  - .specify/templates/spec-template.md ✅ No structural changes required;
    existing placeholders align with new principles
  - .specify/templates/tasks-template.md ✅ No structural changes required
Deferred TODOs:
  - None — all fields resolved from repo context
-->

## Core Principles

### I. Code Quality (NON-NEGOTIABLE)

All code across every layer of the system (Jetson Python, Arduino C++, app)
MUST be clean, intentional, and maintainable.

- Modules MUST have a single, clearly stated responsibility.
- Functions and methods MUST be kept short and focused; complex logic MUST be
  broken into named helper functions with descriptive identifiers.
- Magic numbers and raw literals MUST be extracted to named constants or
  configuration (e.g., `config.py`, `config.yaml`, `#define`).
- All new public interfaces MUST include inline documentation (docstring /
  Doxygen comment) describing purpose, parameters, and return values.
- Dead code, commented-out blocks, and placeholder stubs MUST NOT be merged
  to the main branch.

**Rationale**: The Sentry system spans three codebases with distinct runtimes
(Python, C++, web/mobile). Inconsistent quality compounds quickly across
language boundaries and makes hardware-software debugging disproportionately
expensive.

### II. Testing Standards (NON-NEGOTIABLE)

Every feature MUST be accompanied by automated tests before the implementation
is considered complete.

- Unit tests MUST cover all non-trivial pure-logic components (PID controller,
  geo utilities, detection thresholds, serial protocol framing).
- Hardware-dependent code (camera, serial I/O, MQTT) MUST expose a mockable
  interface so unit tests can run without physical hardware.
- Integration tests MUST verify end-to-end flows across subsystem boundaries:
  Jetson ↔ Arduino serial protocol, vision pipeline → turret command,
  web stream → client frame delivery.
- A test MUST be written and confirmed to **fail** before the corresponding
  implementation is written (Red–Green–Refactor).
- CI MUST gate merges on all tests passing; flaky tests MUST be fixed or
  removed within one sprint.

**Rationale**: Physical hardware errors are expensive to reproduce and debug.
Automated tests with hardware mocks allow rapid iteration and catch regressions
before deployment to the embedded system.

### III. User Experience Consistency

The operator-facing surface of the system — web stream, app controls, visual
overlays, and status feedback — MUST be consistent and predictable.

- Visual overlays on the camera feed MUST use a consistent color convention:
  red for threats/active tracking, green for status/metadata, yellow for
  warnings.
- All status messages emitted to the operator (console, web UI, MQTT topics)
  MUST follow a consistent format: `[SUBSYSTEM] <message>` (e.g.,
  `[VISION] Target acquired`, `[TURRET] Dead-zone reached`).
- Any user-facing configuration parameter MUST be documented with its units,
  valid range, and default value in `config.yaml` or equivalent.
- Behavioral changes that alter the operator experience (new overlay fields,
  changed status strings, modified control modes) MUST be noted in the
  feature spec before implementation.
- Error states MUST surface to the operator with an actionable message rather
  than silently failing or logging only to a file.

**Rationale**: The Sentry system is safety-critical and operator-supervised.
Inconsistent feedback increases cognitive load and can cause the operator to
misread system state during time-sensitive scenarios.

### IV. Performance Requirements

The system MUST meet its real-time processing and latency targets at all times;
performance is a functional requirement, not an optimisation afterthought.

- The Jetson vision pipeline MUST process frames at ≥ 20 FPS under expected
  operating conditions (480×320, YOLOv8n, NVIDIA-accelerated inference).
- End-to-end latency from camera frame capture to turret serial command MUST
  NOT exceed 100 ms under normal operating load.
- Serial communication with the Arduino MUST operate at 115 200 baud with a
  round-trip command acknowledgement time of < 20 ms.
- Web stream frame delivery MUST sustain ≥ 15 FPS to connected clients
  without blocking the main vision/control loop.
- Any new feature that risks degrading these targets MUST include a benchmark
  or profiling report demonstrating compliance before merge.
- Resource consumption on the Jetson (CPU %, GPU %, RAM) MUST be monitored
  and documented for every major release.

**Rationale**: The tracking loop is a hard real-time control system. Missed
deadlines translate directly to lost target lock and mechanical instability.
Establishing numeric targets makes performance regressions objectively
detectable.

## Technology Stack

The canonical technology choices for each layer are fixed below. Deviations
MUST be justified in the feature plan's Complexity Tracking table.

| Layer | Language | Key Libraries / Tools |
|---|---|---|
| Jetson (AI/Control) | Python 3.10+ | OpenCV, Ultralytics YOLOv8, Flask, pyserial, paho-mqtt |
| Arduino (Firmware) | C++ (Arduino) | AccelStepper, PlatformIO |
| Infrastructure | Docker | docker-compose (Jetson deployment) |
| Testing | Python | pytest (Jetson); PlatformIO native tests (Arduino) |

Hardware interfaces MUST communicate over well-defined contracts:
- Jetson ↔ Arduino: serial (115 200 baud), ASCII or binary framing defined in
  `jetson/src/comms/serial_io.py`.
- Jetson ↔ external systems: MQTT topics defined in
  `jetson/src/comms/mqtt.py`.

## Development Workflow

- **Branch strategy**: All work MUST be done on a feature branch named
  `###-short-description`; merges to `main` require passing CI and at least
  one peer review.
- **Constitution Check**: Every feature plan MUST include a Constitution Check
  gate verifying compliance with all four Core Principles before implementation
  begins.
- **Complexity justification**: Any deviation from the Technology Stack table
  or any violation of a Core Principle MUST be documented in the feature plan's
  Complexity Tracking table with rationale and rejected alternatives.
- **Hardware-in-the-loop testing**: Features touching serial I/O, camera, or
  motor control MUST be validated on physical hardware before the feature branch
  is merged.
- **Configuration changes**: Any change to tunable parameters (PID constants,
  thresholds, baud rate) MUST be made in the canonical config file, not
  hard-coded in logic.

## Governance

This constitution supersedes all other development practices and conventions
within the Sentry project. Conflicts are resolved in favour of the constitution.

- **Amendments**: Any change to this constitution MUST follow semantic
  versioning (MAJOR for principle removal/redefinition, MINOR for additions,
  PATCH for clarifications) and be recorded via the Sync Impact Report
  comment at the top of this file.
- **Compliance review**: Constitution Check gates in every feature plan serve
  as the primary compliance mechanism. Pull request reviewers MUST verify
  these gates are honestly completed.
- **Versioning policy**: `LAST_AMENDED_DATE` MUST be updated on every
  amendment. `RATIFICATION_DATE` is immutable once set.
- **Precedence of principles**: In cases of conflict between principles,
  priority order is: Testing Standards > Performance Requirements >
  Code Quality > UX Consistency.

**Version**: 1.0.0 | **Ratified**: 2026-02-25 | **Last Amended**: 2026-02-25
