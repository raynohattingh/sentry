# Feature Specification: Test Bench Limit Switch Bypass

**Feature Branch**: `[002-test-bench-limit-bypass]`  
**Created**: 2026-03-23  
**Status**: Draft  
**Input**: User description: "For the initial testing model, the housing was not designed with hardware limit switches in place. Add a way to disable the need for limit switches for the test bench housing for now, while keeping MVP housing requirements aligned to include real limit switches later."

## Clarifications

### Session 2026-03-23

- Q: How should the safe motion range be defined in test bench mode? → A: Use preconfigured software min/max pan and tilt bounds that must be set before motion is allowed.
- Q: How should test bench mode be designated? → A: Persist test bench versus MVP as a saved housing profile per sentry unit.
- Q: Where is the saved per-unit housing profile stored? → A: It is saved on the sentry unit itself, persisted on the Jetson as unit-local runtime configuration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the test bench without installed switches (Priority: P1)

As a builder validating the first physical test bench, I need to operate the turret even though the housing does not yet include hardware limit switches, so that I can continue mechanical and motion testing without waiting for a new housing revision.

**Why this priority**: The current prototype is blocked by a hardware dependency the test bench cannot satisfy. Removing that blocker is the fastest path to continued validation.

**Independent Test**: Configure a unit with a saved test bench housing profile and no installed switches, start it, and verify the operator can complete basic pan and tilt movement checks without a limit-switch installation fault preventing operation.

**Acceptance Scenarios**:

1. **Given** a sentry has a saved test bench housing profile, **When** the system starts without detecting hardware limit switches, **Then** it allows operation without treating the missing switches as a startup blocker.
2. **Given** a sentry is running with a saved test bench housing profile, **When** an operator sends motion commands, **Then** the turret responds normally within the allowed motion range for that housing.

---

### User Story 2 - Keep the temporary bypass explicit and safe (Priority: P2)

As an operator using the temporary housing, I need the system to make it obvious that hardware end-stop protection is bypassed, so that I understand I am working in a reduced-safety testing configuration.

**Why this priority**: Running without switches introduces real risk. The bypass must never feel like normal production behavior or fail silently.

**Independent Test**: Put a unit with a saved test bench housing profile into operation and verify the operator sees a persistent reduced-safety indication before and during movement, and that motion remains constrained to the configured software pan and tilt bounds for the bench.

**Acceptance Scenarios**:

1. **Given** the limit-switch bypass is enabled, **When** the operator views system status or begins motion testing, **Then** the system clearly indicates that hardware limit protection is disabled for this unit.
2. **Given** the system is operating under a saved test bench housing profile, **When** an operator commands movement toward a known physical boundary, **Then** the system prevents travel beyond the preconfigured software pan and tilt bounds defined for that housing.

---

### User Story 3 - Preserve MVP requirements for real switches (Priority: P3)

As the product owner preparing the MVP housing, I need the temporary bypass to stay scoped to the test bench only, so that the production-ready housing still requires real hardware limit switches.

**Why this priority**: The bypass is a prototype accommodation, not a change to the long-term product safety baseline.

**Independent Test**: Configure one sentry with a saved test bench housing profile and another with a saved MVP housing profile, then verify the bypass is available only to the test bench configuration and that the MVP configuration still requires hardware limit switches.

**Acceptance Scenarios**:

1. **Given** a sentry is configured for MVP or production-intent housing, **When** hardware limit switches are absent or unavailable, **Then** the system refuses to enter normal operating mode.
2. **Given** the team transitions from the test bench housing to the MVP housing, **When** the housing profile is updated, **Then** hardware limit switches become a required prerequisite again without depending on undocumented manual workarounds.

---

### Edge Cases

- What happens if a unit previously configured with a saved test bench housing profile is reclassified as MVP while the bypass is still enabled? The system must invalidate the bypass and require the MVP housing to satisfy the hardware switch prerequisite before normal operation resumes.
- What happens if the safe motion range for the test bench has not been defined? The system must not allow unrestricted movement; it must block motion until preconfigured software pan and tilt bounds are declared.
- What happens if an operator attempts to hide or ignore the reduced-safety state? The reduced-safety indication must remain persistent while the bypass is active.
- What happens if the test bench configuration is copied to another unit unintentionally? The copied unit must still require its own saved test bench housing profile before the bypass takes effect.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a test bench housing mode in which missing hardware limit switches do not block motion testing.
- **FR-002**: The system MUST require a saved per-unit housing profile on the sentry unit, designating test bench mode, before the limit-switch bypass can take effect.
- **FR-003**: The system MUST present a persistent reduced-safety indication whenever hardware limit switch protection is bypassed.
- **FR-004**: The system MUST constrain turret motion in test bench housing mode to preconfigured software minimum and maximum pan and tilt bounds appropriate to that housing.
- **FR-005**: The system MUST prevent motion when the test bench software pan and tilt bounds have not been defined or are invalid.
- **FR-006**: Operators MUST be able to perform basic motion validation on the test bench without installing hardware limit switches first.
- **FR-007**: The system MUST record, per sentry unit, whether the saved housing profile requires hardware limit switches or allows the temporary test bench bypass.
- **FR-008**: The system MUST make the active protection mode visible anywhere operators decide whether it is safe to start or continue motion testing.
- **FR-009**: The system MUST scope the bypass to the test bench housing only and MUST NOT treat it as an acceptable default for MVP or production-intent housings.
- **FR-010**: The system MUST require MVP or production-intent housings to provide hardware limit switches before entering normal operating mode.
- **FR-011**: The system MUST support a straightforward transition from test bench mode back to hardware-switch-required mode when the housing is upgraded.
- **FR-012**: The system MUST preserve traceable documentation of the temporary nature of the bypass and the expectation that MVP housing includes real hardware limit switches.

### Key Entities *(include if feature involves data)*

- **Housing Profile**: A saved per-sentry-unit designation, stored on the sentry unit, describing the physical enclosure type, including whether it is a temporary test bench housing or an MVP/production-intent housing.
- **Protection Mode**: States whether the unit is operating with hardware limit switches required or with the temporary test bench bypass enabled.
- **Safe Motion Range**: The preconfigured software minimum and maximum pan and tilt bounds that define how far the test bench unit may move while physical switches are absent.
- **Bypass Acknowledgement**: The explicit operator- or configuration-level confirmation that the unit is running in a reduced-safety test bench state.

### Assumptions

- The current test bench is for controlled development use, not unattended field deployment.
- The team wants the bypass to be temporary and clearly reversible once the MVP housing is ready.
- Test bench operation still needs preconfigured software travel bounds even without physical end-stop switches.
- MVP and later housings retain the existing expectation that real hardware limit switches are part of the mechanical design.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A builder can configure a new test bench unit for first motion testing in under 5 minutes without being blocked by missing hardware limit switches.
- **SC-002**: 100% of test bench sessions that use the bypass display a visible reduced-safety status before and during motion operation.
- **SC-003**: 100% of MVP or production-intent housing configurations reject normal operation when hardware limit switches are not available.
- **SC-004**: Operators can complete the primary pan and tilt verification workflow on the test bench without needing undocumented manual overrides or code changes.
- **SC-005**: During validation, commanded motion never exceeds the configured software pan and tilt bounds for the test bench housing.
