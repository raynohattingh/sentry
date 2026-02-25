# Pre-Implementation Checklist: Sentry Jetson Core

**Purpose**: Validate that all 34 FRs are complete, clear, consistent, and measurable before
implementation begins. Authored by the implementer as a self-review gate.  
**Created**: 2026-02-25  
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)  
**Depth**: Standard (breadth-first, all subsystems)  
**Audience**: Author (pre-implementation self-review)

> Each item tests the **quality of the requirement itself** — not whether the implementation works.
> Use `[x]` to mark items as satisfied. Add inline findings on unresolved items.

---

## Requirement Completeness

*Are all necessary requirements present and documented?*

- [ ] CHK001 — Is the distance-estimation formula defined for when `LRF_ENABLED=false`? FR-006 requires
  threat scoring to use "estimated distance" but FR-018's vision-only mode omits the bounding-box-to-
  metres conversion formula or the calibration parameters needed to derive it. `[Gap, Spec §FR-006 / §FR-018]`

- [ ] CHK002 — Is multi-target queue management specified in an FR? User Story 2 AC-4 states the system
  "locks onto the highest-scoring target first; lower-priority targets are queued", but no FR formalises
  queue depth, eviction policy, or what "queued" means for the control loop. `[Gap, Spec §US2-AC4]`

- [ ] CHK003 — Does FR-028's parameter list explicitly include the scoring weight parameters
  (`W_DISTANCE`, `W_MOTION`, `W_GROUPING`, `W_TIME_OF_DAY`)? Currently FR-028 lists "thresholds" but
  scoring weights are distinct from tier boundaries; their omission would allow them to be hard-coded.
  `[Completeness, Spec §FR-028]`

- [ ] CHK004 — Are SEARCH-state sweep velocity requirements specified? FR-022 defines arc width
  (`SEARCH_ARC_DEG`) and timeout (`SEARCH_TIMEOUT_S`) but does not state the velocity used during the
  arc sweep — is it `scan_velocity`, a fixed value, or separately configurable? `[Gap, Spec §FR-022]`

- [ ] CHK005 — Is the `[TURRET] Approaching limit` HUD warning persistence defined? FR-031 mandates the
  warning is displayed but does not specify whether it appears every frame while in the taper zone or
  only once per entry event. `[Gap, Spec §FR-031]`

- [ ] CHK006 — Are the mockable hardware interfaces (`CameraProtocol`, `SerialProtocol`,
  `MQTTProtocol`) specified in the spec? Constitution Principle II requires mockable interfaces; they
  appear only in plan.md. If absent from the spec, the abstraction boundary is insufficiently
  authoritative. `[Gap, plan.md §Testing Standards]`

- [ ] CHK007 — Does the spec define the expected process exit code for a fatal GPU startup failure
  (FR-029)? Without a specified exit code, Docker's restart policy and monitoring systems cannot
  distinguish a fatal crash from a normal shutdown or intentional stop. `[Gap, Spec §FR-029]`

- [ ] CHK008 — Are log severity levels (INFO, WARNING, ERROR, CRITICAL) defined for each `[SUBSYSTEM]`
  log entry pattern? The constitution deferred log-level taxonomy to planning; FR-017, FR-029, FR-030,
  and FR-033 all reference log entries without severity designations. `[Gap, Deferred from clarification]`

---

## Requirement Clarity

*Are requirements specific, unambiguous, and actionable?*

- [ ] CHK009 — Is "estimated distance" in FR-006 precisely defined for the no-LRF path? The edge case
  section mentions "estimated distance from bounding-box size" but provides no formula, calibration
  constant, or reference for how bounding box area maps to metres. `[Ambiguity, Spec §FR-006]`

- [ ] CHK010 — Is the dead-zone shape in FR-013 unambiguous — circular (radius applied to Euclidean
  distance) or rectangular (independent ±x, ±y thresholds)? The spec uses "radius" suggesting a circle,
  but the PID applies `error_x` and `error_y` independently, which implies a square. `[Ambiguity, Spec §FR-013]`

- [ ] CHK011 — Is the turret zero-pan azimuth reference defined in an FR? FR-016 relies on "current
  pan/tilt angles" to compute GPS bearing but the mapping of pan step 0 to a compass direction is only
  present in the config schema (`SENTRY_HEADING_DEG`) — no FR mandates its use or documents the
  reference frame. `[Clarity, Gap, Spec §FR-016]`

- [ ] CHK012 — Is the geodesic formula in FR-016 authoritative, or is "Vincenty or Haversine"
  intentionally flexible? The research selected Haversine, but the spec still reads "or", leaving the
  formula choice open to the implementer. `[Clarity, Spec §FR-016]`

- [ ] CHK013 — Is "continuous LRF ranging" in FR-008 quantified? "Continuous" could mean one shot per
  control loop tick (~20 Hz), one per frame, or one per configurable interval. The spec does not
  distinguish these, which affects Arduino-side duty cycle and LRF hardware limits. `[Clarity, Spec §FR-008]`

- [ ] CHK014 — Is "sampled LRF ranging (look → sweep → look)" in FR-009 precisely defined? The
  MED-threat sampling strategy names the pattern but does not specify the duration or step count for
  each phase, or whether timing is configurable. `[Clarity, Spec §FR-009]`

- [ ] CHK015 — Is "MUST NOT degrade" in FR-025 measurable? The spec prohibits throughput degradation
  from the web stream but sets no numeric bound (e.g., "web thread must not reduce main loop rate by
  more than 2 Hz"). Without a threshold, this FR cannot be objectively verified. `[Clarity, Spec §FR-025]`

- [ ] CHK016 — Is "proportionally to zero" in FR-031 defined as a specific curve (linear, cosine,
  quadratic)? The research chose linear, but the spec uses only "proportionally" which is ambiguous
  and will lead to inconsistent implementations if the spec is referenced independently. `[Clarity, Spec §FR-031]`

---

## Requirement Consistency

*Do requirements align without conflicts or contradictions?*

- [ ] CHK017 — Is the `session_id` data type consistent across FRs? FR-004 describes it as "ISO-format
  UTC timestamp" while FR-034 specifies "UUID4". These are structurally different; only one can be
  authoritative, and the inconsistency will create a runtime type mismatch. `[Conflict, Spec §FR-004 vs §FR-034]`

- [ ] CHK018 — Do FR-015 and FR-022 define compatible target-loss flows? FR-015 transitions to SCAN on
  idle timeout; FR-022 defines a SEARCH state entered when a target is "lost beyond `max_disappeared`
  frames". Both are triggered by target absence — the spec must define which fires first and whether
  they are mutually exclusive. `[Conflict, Spec §FR-015 vs §FR-022]`

- [ ] CHK019 — Is the ACQUIRE→SEARCH transition subject to the FR-032 dwell timer? FR-032 gates
  "downward transitions" but ACQUIRE→SEARCH (target lost) is a safety-critical immediate transition
  that should arguably bypass dwell. The spec does not explicitly carve out this case. `[Ambiguity, Spec §FR-022 vs §FR-032]`

- [ ] CHK020 — Is "no magic numbers in logic modules" in FR-028 in the correct specification artifact?
  This is a code quality governance principle (Constitution Principle I) embedded as a functional
  requirement. Mixing governance rules into FRs may cause confusion about what is testable vs. what
  is a development practice. `[Consistency, Spec §FR-028 vs constitution §I]`

- [ ] CHK021 — Are all `[SUBSYSTEM] <message>` log format patterns consistent between FRs? FR-033
  defines `[SERIAL] Malformed frame discarded: <raw>`, FR-031 defines `[TURRET] Approaching limit`,
  and FR-029 defines `[SYSTEM] FATAL — TensorRT…`. Do all follow the same convention for structured
  log fields and casing? `[Consistency, Spec §FR-029 / §FR-031 / §FR-033]`

- [ ] CHK022 — Does FR-023 ("FSM is the sole authority for serial commands") explicitly exempt or
  address the hardware limit switch scenario? If the Arduino's physical limit switch triggers an
  independent motor stop, is that a violation of FR-023, or is it intentionally outside the FSM's
  authority? `[Consistency, Spec §FR-023 vs §FR-031]`

---

## Acceptance Criteria Quality

*Can success criteria be objectively measured and verified?*

- [ ] CHK023 — Is SC-001 (≥20 Hz main loop) measurable with a defined methodology? The criterion does
  not specify whether "20 Hz" is a rolling average, a minimum, a p50, or a p95, nor how many frames
  the measurement window spans. `[Measurability, Spec §SC-001]`

- [ ] CHK024 — Is SC-003 ("re-identified in ≥95% of trials") testable without a specified test
  protocol? The criterion does not define occlusion duration, re-emergence area, distance from the
  last known centroid, or number of trials — all of which materially affect the pass/fail outcome.
  `[Measurability, Spec §SC-003]`

- [ ] CHK025 — Is SC-004 (GPS accuracy ±10m) verifiable with a defined error budget? The ±10m figure
  depends on LRF accuracy, pan/tilt encoder accuracy, and GPS datum — none of which are specified.
  Without an error budget, this criterion cannot be traced to the underlying hardware specifications.
  `[Measurability, Spec §SC-004]`

- [ ] CHK026 — Is SC-007 ("72-hour continuous run in simulated environment") defined with a specific
  test harness? The criterion does not specify how the camera (looped test video), Arduino serial
  (mock port), LRF, and MQTT broker are simulated — leaving the pass/fail condition ambiguous.
  `[Measurability, Spec §SC-007]`

---

## Scenario Coverage

*Are all flows, boundary conditions, and edge cases addressed?*

- [ ] CHK027 — Are requirements defined for simultaneous multi-target appearance where one immediately
  occludes the other? FR-005 addresses disappearance of an existing target, but initial ID assignment
  when two targets appear together and one is immediately occluded is not covered. `[Edge Case, Spec §FR-005]`

- [ ] CHK028 — Are requirements defined for when `SENTRY_LAT` and `SENTRY_LON` are at their default
  values of `(0.0, 0.0)`? The assumptions state GPS is provided externally but no FR mandates a
  startup validation check or warning when coordinates are at the zero/unconfigured default.
  `[Edge Case, Gap, Spec §Assumptions]`

- [ ] CHK029 — Are requirements defined for a missing or corrupted `boot_state.json` file at startup?
  FR-030 requires reading the failure counter, but the spec does not specify whether a missing file
  should be treated as 0 failures (lenient) or trigger a conservative default. `[Edge Case, Spec §FR-030]`

- [ ] CHK030 — Are requirements defined for a zero-width SCAN sweep range (`SCAN_PAN_MIN ==
  SCAN_PAN_MAX`)? This configuration value would create a degenerate sweep, likely producing a
  divide-by-zero or infinite loop in the oscillation logic. `[Edge Case, Spec §FR-022]`

- [ ] CHK031 — Are requirements defined for misconfigured limit thresholds where
  `LIMIT_WARN_STEPS > LIMIT_HARD_STEPS`? Inverted thresholds would invert the taper formula
  and produce positive scaling beyond the limit. `[Edge Case, Spec §FR-031]`

- [ ] CHK032 — Are requirements defined for what happens when the primary target (highest-threat) is
  lost while a secondary target remains visible? Should the FSM immediately lock on the next-highest
  target or transition to SEARCH first? `[Edge Case, Gap, Spec §FR-022]`

---

## Non-Functional Requirements

*Are performance, security, and operational requirements fully specified?*

- [ ] CHK033 — Are CPU and GPU memory consumption upper bounds specified for the Jetson? The
  constitution mandates monitoring but no FR places measurable caps on memory use. On a Jetson Orin
  Nano Super with shared memory, uncapped memory growth can degrade inference FPS. `[NFR, Gap]`

- [ ] CHK034 — Are security requirements defined for the local telemetry log file? The JSON-lines log
  contains GPS coordinates of individuals. If accessible by unauthorised users on the Jetson, it
  represents a privacy risk. File permission or encryption requirements are absent. `[NFR, Security, Gap]`

- [ ] CHK035 — Are network exposure requirements defined for the web HUD? FR-024 mandates HTTP Basic
  Auth but does not restrict the bind interface (config default: `0.0.0.0`). Binding to all interfaces
  could expose the HUD to the WAN if the farm network has internet routing. `[NFR, Security, Spec §FR-024]`

- [ ] CHK036 — Are MQTT payload size requirements specified? TelemetryRecord JSON payloads with GPS
  fields and full timestamps are well within typical MQTT limits, but if the broker enforces a low
  `max_packet_size`, silent discard could occur without the publisher knowing. `[NFR, Spec §FR-017]`

---

## Dependencies & Assumptions

*Are external dependencies and assumptions documented and validated?*

- [ ] CHK037 — Is the assumption that "network bandwidth is sufficient for 480×320 MJPEG at 15 FPS"
  validated with a bitrate estimate? At JPEG quality 80%, this stream is approximately 2–5 Mbps. The
  spec does not quantify bandwidth or specify minimum LAN speed. `[Assumption, Spec §Assumptions]`

- [ ] CHK038 — Is the Arduino firmware version dependency documented? The serial protocol contract
  defines `DIST` and `POS` message formats, but the spec does not reference which Arduino firmware
  version these formats correspond to. A firmware change could silently break the Jetson-side parser.
  `[Dependency, Gap, contracts/serial-protocol.md]`

- [ ] CHK039 — Is the TensorRT `.engine` file portability constraint documented in the spec? A `.engine`
  file is compiled for a specific JetPack version, GPU architecture, and batch size. Deploying an
  engine compiled on one Jetson to another (or after a JetPack upgrade) will cause a startup failure.
  This constraint belongs in the Assumptions section. `[Dependency, Assumption, Gap, Spec §Assumptions]`

- [ ] CHK040 — Is the `nvidia-container-toolkit` host dependency documented? The Docker compose file
  uses `runtime: nvidia` which silently fails if the toolkit is not installed on the host. This
  deployment prerequisite is absent from the spec's Assumptions and the quickstart. `[Dependency, Gap]`

---

## Notes

- Items marked `[Gap]` indicate missing requirements — add an FR or assumption before implementation.
- Items marked `[Conflict]` require a spec amendment to resolve the contradiction before coding.
- Items marked `[Ambiguity]` should be clarified with a precise definition added to the relevant FR.
- Priority order for resolution: Conflicts (CHK017–CHK022) → Gaps in core FRs (CHK001–CHK008) →
  Clarity issues (CHK009–CHK016) → Edge cases and NFRs.
