# Sentry Constitution
<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 2.0.0  (MAJOR — product model redefined; new
  NON-NEGOTIABLE Mission & Safety tier added above engineering principles;
  precedence order changed)

Reason for MAJOR bump:
  v1.0.0 encoded an autonomous, visible-light, aiming-turret product
  ("threats", "target lock", "camera frame → turret serial command").
  The project has been redefined as a thermal EARLY-WARNING system that
  detects and alerts but never acts. Specs written under v1.0.0's
  assumptions are not automatically compliant — hence MAJOR.

Added (Mission & Safety Principles, I–VI):
  - I.   Early-Warning, Not Response (NON-NEGOTIABLE)
  - II.  Detection, Not Intent (NON-NEGOTIABLE)
  - III. False-Alarm Minimisation Is the Product (NON-NEGOTIABLE)
  - IV.  Offline-First, No Cloud Dependency (NON-NEGOTIABLE)
  - V.   Validate the Core Bet Before Building (empirical gating)
  - VI.  Privacy, Liability & Honest Claims (NON-NEGOTIABLE)

Renumbered (Engineering Principles, now VII–X; formerly I–IV):
  - VII.  Code Quality  (unchanged)
  - VIII. Testing Standards  (unchanged)
  - IX.   User Experience Consistency  (vocabulary reconciled: "threats" →
          "detections"; intent-neutral overlay/status wording required)
  - X.    Performance Requirements  (reframed: latency now measured to the
          operator ALERT, not a turret command; numeric targets tied to the
          superseded turret/visible-light model are flagged UNDER REVISION)

Precedence changed:
  Mission & Safety (I–VI) now outrank ALL engineering principles.
  Within Mission & Safety, I, II, IV and VI are absolute and may not be
  traded off. Engineering precedence unchanged among themselves.

UNDER REVISION (do not treat as authoritative until a follow-up amendment):
  - Performance numerics in Principle X (480×320, YOLOv8n FPS, 100 ms
    frame→command, "target lock") — depend on the Phase-0 sensor result and
    the 360° motion-model rewrite. Numbers to be set from measured data.
  - Technology Stack table — still lists Ultralytics YOLOv8 (visible-light)
    and AccelStepper (bounded turret). To be revised to a thermal-trained
    model + continuous-rotation drive once the reuse/rewrite plan lands.

Templates requiring follow-up (NOT edited in this amendment):
  - .specify/templates/plan-template.md — Constitution Check gate MUST be
    extended to assert Principles I–VI. ⚠ TODO.
  - .specify/templates/spec-template.md — add a "Safety & False-Alarm
    Impact" section placeholder. ⚠ TODO.
  - .specify/templates/tasks-template.md — no structural change required.

Deferred TODOs:
  - Set Principle X numerics post Phase-0.
  - Revise Technology Stack table post reuse/rewrite decision.
  - Update the two templates above.
-->

## Preamble — What This Product Is

Sentry is a **thermal early-warning system** for South African farms. It
detects the presence and bearing of warm targets, distinguishes humans from
animals as well as the sensor allows, and **alerts a human operator**. It does
not assess intent, it does not aim, and it never acts. Every principle below
serves one outcome: **a farmer who still has alerts switched on after 60 days
because the system warned them when it mattered and stayed quiet when it did
not.**

---

## Mission & Safety Principles

These principles define what the product is permitted to be. They outrank every
engineering principle in this document. When an engineering convenience
conflicts with a Mission & Safety principle, the Mission & Safety principle
wins.

### I. Early-Warning, Not Response (NON-NEGOTIABLE)

The system detects and alerts. It MUST NOT take autonomous physical action of
any kind.

- No feature may actuate a deterrent, light, siren, alarm-on-device, weapon, or
  any other physical response triggered by a detection.
- The unit's only outputs are information (bearing, range, classification,
  imagery) and notifications to a human.
- The human operator is the sole decision-maker and actor on any detection.
- Any proposal to add an actuated response is out of scope and MUST be rejected
  at spec time, not deferred.

**Rationale**: This product warns people who may respond with force in a
high-stress context. An autonomous actuator turns a false positive into a
physical incident and turns the builder into the liable party. Removing the
possibility entirely is the only safe design.

### II. Detection, Not Intent (NON-NEGOTIABLE)

The system classifies *what* and *where*. It MUST NOT classify *whether a person
is a threat*.

- Classification outputs are limited to object type (e.g. human / animal /
  unknown) and geometry (bearing, range, position relative to the install
  point).
- There MUST be no "threat score" that ranks a *person's* danger or intent.
  (A detection-confidence or human-likelihood score used purely to gate alerts
  is permitted and is a different thing.)
- All operator-facing copy MUST be intent-neutral: "human detected at bearing
  X," never "intruder," "hostile," or "threat."

**Rationale**: The system cannot know intent and must never imply it can.
Labelling a detection a "threat" both misrepresents the capability and
prejudices the operator's response.

### III. False-Alarm Minimisation Is the Product (NON-NEGOTIABLE)

Retention-without-muting is the north-star metric. A muted system has zero
value regardless of detection quality.

- Every detection or classification feature MUST be evaluated for its
  false-positive impact before merge, against real confusers (animals, warm
  vehicles, sun-warmed surfaces, moving vegetation).
- A change that measurably increases the nuisance-alert rate MUST justify the
  trade explicitly in its spec, or it MUST NOT merge.
- Operator-adjustable sensitivity MUST be provided; the farmer, not the
  developer, sets their tolerance.
- Detection-capability claims used to gate alerts MUST be backed by field data
  (see Principle V), not assumed thresholds.

**Rationale**: Animal false alarms — not detection range — are the documented
make-or-break risk. The product lives or dies on the farmer's trust, and trust
is destroyed one nuisance alert at a time.

### IV. Offline-First, No Cloud Dependency (NON-NEGOTIABLE)

Core detection and alerting MUST function with no internet and no cloud
service.

- All detection, classification, ranging, and on-property alerting MUST run
  locally on the unit and the LAN.
- Alerting MUST degrade gracefully across channels (LAN/WiFi → cellular →
  SMS-over-2G backstop) without a cloud broker in the critical path.
- No feature may introduce a hard dependency on an external/cloud service for
  core detection or alerting. Optional cloud conveniences are permitted only as
  strictly non-essential add-ons.
- The 2G/3G network sunset MUST be treated as a deprecating backstop, never a
  foundation.

**Rationale**: The customers operate where connectivity is unreliable or
absent. A product that needs the cloud to warn you of an intruder will fail at
the exact moment it is needed.

### V. Validate the Core Bet Before Building (Empirical Gating)

Capability is proven by measurement, not assumed by specification.

- Any capability claim (detection range, classification accuracy, false-alarm
  rate) MUST be backed by field measurement before it is treated as true.
- Subsystems whose value depends on an unproven sensor or detection assumption
  MUST NOT be specced as committed work until that assumption is measured
  (the Phase-0 gate). Spec Kit MUST NOT be used to manufacture confidence that
  the bench has not yet earned.
- Field-test data (raw frames, labels, conditions) MUST be retained — it is
  both the evidence and the seed of the training dataset.

**Rationale**: Spec-driven development can produce a beautiful, internally
consistent plan for a product that cannot do its one job. This principle keeps
specification downstream of evidence, where it belongs.

### VI. Privacy, Liability & Honest Claims (NON-NEGOTIABLE)

The product is sold and described honestly, and it respects the people it
images.

- Thermal imagery of identifiable people is personal information under POPIA:
  it MUST be stored locally, minimised, and given a documented retention limit.
- The product MUST be positioned as an early-warning *aid* that supplements,
  never replaces, the operator's own judgement and existing security. Marketing,
  packaging, and in-app copy MUST reflect this.
- The system MUST NOT claim or imply a guarantee of safety. False positives and
  false negatives are inherent and MUST be disclosed at point of sale.
- Material legal exposure (terms of use, liability framing) MUST be reviewed by
  a South African attorney before any unit is sold.

**Rationale**: Overclaiming on a safety product is both an ethical failure and
a legal one. Honest framing protects the user and the builder.

---

## Engineering Principles

These govern *how* the software is built. They are subordinate to the Mission &
Safety Principles above.

### VII. Code Quality (NON-NEGOTIABLE)

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

### VIII. Testing Standards (NON-NEGOTIABLE)

Every feature MUST be accompanied by automated tests before the implementation
is considered complete.

- Unit tests MUST cover all non-trivial pure-logic components (geo utilities,
  detection thresholds, serial protocol framing, classification gating).
- Hardware-dependent code (camera, serial I/O, MQTT) MUST expose a mockable
  interface so unit tests can run without physical hardware.
- Integration tests MUST verify end-to-end flows across subsystem boundaries:
  Jetson ↔ Arduino serial protocol, vision pipeline → alert, detection →
  notification delivery.
- A test MUST be written and confirmed to **fail** before the corresponding
  implementation is written (Red–Green–Refactor).
- CI MUST gate merges on all tests passing; flaky tests MUST be fixed or
  removed within one sprint.

**Rationale**: Physical hardware errors are expensive to reproduce and debug.
Automated tests with hardware mocks allow rapid iteration and catch regressions
before deployment to the embedded system.

### IX. User Experience Consistency

The operator-facing surface of the system — app controls, visual overlays,
alerts, and status feedback — MUST be consistent, predictable, and
intent-neutral.

- Visual overlays and markers MUST use a consistent colour convention; colour
  MUST denote *detection state and confidence*, not asserted threat level, and
  labels MUST follow Principle II (intent-neutral wording).
- All status messages emitted to the operator (console, app, MQTT topics) MUST
  follow a consistent format: `[SUBSYSTEM] <message>` (e.g.,
  `[VISION] Human detected`, `[COMMS] Cellular fallback active`).
- Any user-facing configuration parameter MUST be documented with its units,
  valid range, and default value in `config.yaml` or equivalent.
- Behavioural changes that alter the operator experience (new alert fields,
  changed status strings, modified modes) MUST be noted in the feature spec
  before implementation.
- Error states MUST surface to the operator with an actionable message rather
  than silently failing or logging only to a file.

**Rationale**: The system is safety-relevant and operator-supervised.
Inconsistent or intent-loaded feedback increases cognitive load and can cause
the operator to misread system state during time-sensitive scenarios.

### X. Performance Requirements

The system MUST meet real-time processing and latency targets appropriate to an
early-warning role; performance is a functional requirement, not an afterthought.

> ⚠ **UNDER REVISION** — the specific numerics in this principle were set for
> the superseded autonomous-turret, visible-light model. They remain here as a
> placeholder and MUST be re-derived from Phase-0 measurements and the 360°
> motion-model design before being treated as authoritative. See the Sync
> Impact Report.

- The detection pipeline MUST sustain a real-time frame rate adequate to catch
  a walking target during a sweep (target FPS and sensor resolution TBD from
  Phase-0; the prior 480×320 / YOLOv8n / ≥20 FPS figures are not assumed).
- End-to-end latency from detection to **operator alert dispatch** MUST be
  bounded and specified per the alerting design (prior 100 ms frame→turret
  figure is superseded — early-warning has no aiming deadline).
- Serial communication with the Arduino MUST operate reliably at its configured
  baud with bounded round-trip acknowledgement time.
- On-demand video delivery MUST NOT block the main detection/alert loop.
- Any new feature that risks degrading agreed targets MUST include a benchmark
  or profiling report demonstrating compliance before merge.
- Resource consumption on the Jetson (CPU %, GPU %, RAM, thermal) MUST be
  monitored and documented for every major release; enclosure thermal
  throttling is a known field risk and MUST be tracked.

**Rationale**: Early warning has a soft real-time budget (seconds), not the hard
control-loop budget of an aiming turret. Targets must reflect the actual job —
detect and alert in time — and must be set from measured data, not inherited
from the old model.

## Technology Stack

> ⚠ **UNDER REVISION** — this table reflects the superseded turret/visible-light
> design and will be updated once the reuse-vs-rewrite plan and motion model are
> settled. It is retained for continuity, not as a fixed mandate.

| Layer | Language | Key Libraries / Tools |
|---|---|---|
| Jetson (AI/Control) | Python 3.10+ | OpenCV, thermal-trained detector (model TBD), Flask, pyserial, paho-mqtt |
| Arduino (Firmware) | C++ (Arduino) | Stepper drive (continuous-rotation; library TBD), PlatformIO |
| Infrastructure | Docker | docker-compose (Jetson deployment) |
| Testing | Python | pytest (Jetson); PlatformIO native tests (Arduino) |

Hardware interfaces MUST communicate over well-defined contracts:
- Jetson ↔ Arduino: serial framing defined in
  `jetson/src/comms/serial_io.py`.
- Jetson ↔ external systems: MQTT topics defined in
  `jetson/src/comms/mqtt.py`.

## Development Workflow

- **Branch strategy**: All work MUST be done on a feature branch named
  `###-short-description`; merges to `main` require passing CI and at least
  one peer review.
- **Constitution Check**: Every feature plan MUST include a Constitution Check
  gate verifying compliance with the Mission & Safety Principles (I–VI) **and**
  the Engineering Principles (VII–X) before implementation begins. A plan that
  cannot pass I, II, IV, or VI MUST NOT proceed.
- **Safety & false-alarm impact**: Any feature touching detection,
  classification, or alerting MUST state its false-alarm impact (Principle III)
  and confirm intent-neutrality (Principle II) in its spec.
- **Empirical gating**: A feature whose value rests on an unproven sensor or
  detection assumption MUST cite the field measurement that justifies it, or be
  explicitly marked as exploratory and gated behind Phase-0 (Principle V).
- **Complexity justification**: Any deviation from the Technology Stack table or
  any violation of an Engineering Principle MUST be documented in the feature
  plan's Complexity Tracking table with rationale and rejected alternatives.
  Mission & Safety Principles I, II, IV, VI admit no such deviation.
- **Hardware-in-the-loop testing**: Features touching serial I/O, camera, or
  motor control MUST be validated on physical hardware before merge.
- **Configuration changes**: Any change to tunable parameters MUST be made in
  the canonical config file, not hard-coded in logic.

## Governance

This constitution supersedes all other development practices and conventions
within the Sentry project. Conflicts are resolved in favour of the constitution.

- **Amendments**: Any change to this constitution MUST follow semantic
  versioning (MAJOR for principle removal/redefinition or precedence change,
  MINOR for additions, PATCH for clarifications) and be recorded via the Sync
  Impact Report comment at the top of this file.
- **Compliance review**: Constitution Check gates in every feature plan serve
  as the primary compliance mechanism. Pull request reviewers MUST verify these
  gates are honestly completed, including the Mission & Safety tier.
- **Versioning policy**: `Last Amended` MUST be updated on every amendment.
  `Ratified` is immutable once set.
- **Precedence of principles**: Mission & Safety Principles (I–VI) outrank all
  Engineering Principles (VII–X). Principles I (No Response), II (No Intent),
  IV (Offline-First), and VI (Privacy/Liability) are absolute and admit no
  trade-off. Among the remaining principles, priority order is:
  III (False-Alarm) > V (Empirical Gating) > VIII (Testing) >
  X (Performance) > VII (Code Quality) > IX (UX Consistency).

**Version**: 2.0.0 | **Ratified**: 2026-02-25 | **Last Amended**: 2026-06-08
