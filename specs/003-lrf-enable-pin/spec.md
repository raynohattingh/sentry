# Feature Specification: LRF Enable Pin Configuration

**Feature Branch**: `[003-lrf-enable-pin]`  
**Created**: 2026-03-23  
**Status**: Draft  
**Input**: User description: "We need to add a LFR_ENABLE pin to the arduino config. The documentation specifies that it needs a Low level to power on. See documentation @/Users/raynohattingh/dev/sentry/docs/LRF1000A.pdf"

## Clarifications

### Session 2026-03-23

- Q: When should the active-low LRF enable line be asserted? → A: Only during ranging operations; deassert it afterward for power efficiency.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Power the LRF correctly from controller configuration (Priority: P1)

As a hardware integrator, I need the controller configuration to include a dedicated LRF enable control, so that the rangefinder can be powered on reliably according to its documented active-low behavior.

**Why this priority**: If the enable behavior is wrong or undocumented in the controller configuration, the rangefinder may never power on correctly and the rest of the sentry stack cannot obtain distance readings.

**Independent Test**: Configure a sentry unit with the new LRF enable control, start the system, and verify the rangefinder remains unpowered until a ranging workflow begins, then powers on only while the controller drives the active-low enable state needed for measurement.

**Acceptance Scenarios**:

1. **Given** a sentry unit with an attached LRF module, **When** the system is idle and not performing ranging work, **Then** it keeps the enable control deasserted so the module is not left powered unnecessarily.
2. **Given** the LRF enable control is configured, **When** the sentry starts a normal ranging workflow, **Then** it drives the enable control to the documented active-low state required to power on the module for that operation without requiring manual rewiring or ad hoc code edits.

---

### User Story 2 - Keep the enable behavior explicit for future hardware changes (Priority: P2)

As a firmware maintainer, I need the enable pin and its active-low behavior to be clearly represented in the hardware configuration, so that future board revisions or sensor replacements do not accidentally invert or remove the control.

**Why this priority**: This behavior comes from the sensor documentation and is easy to get wrong later if it is only implied instead of represented clearly in the system configuration.

**Independent Test**: Review the hardware configuration and operational documentation for the sentry controller and confirm both identify the LRF enable control and state that low level powers the sensor on.

**Acceptance Scenarios**:

1. **Given** a maintainer reviewing the sentry hardware configuration, **When** they inspect the LRF-related settings, **Then** they can identify which control is responsible for enabling the LRF and what signal level turns it on.
2. **Given** the team updates wiring or controller pins later, **When** they adjust the LRF control mapping, **Then** the active-low power requirement remains explicit and preserved.

---

### User Story 3 - Fail safely when the enable control is unavailable or misconfigured (Priority: P3)

As an operator or tester, I need the sentry to fail in a predictable way when the LRF enable control is missing or incorrect, so that LRF problems are diagnosed quickly instead of producing unreliable ranging behavior.

**Why this priority**: Misconfigured power control can create intermittent or invisible LRF failures, which are harder to debug than a clear unavailable state.

**Independent Test**: Start a unit with the LRF enable control unavailable or assigned incorrectly and verify the system does not behave as though the LRF is healthy when the sensor is not actually powered correctly, including by withholding success-shaped distance output and returning to the idle-disabled state after the failed measurement attempt.

**Acceptance Scenarios**:

1. **Given** the LRF enable control is unavailable or misconfigured, **When** the system attempts to use the rangefinder, **Then** it surfaces the LRF as unavailable, MUST NOT emit a success-shaped distance reading, and MUST return the enable control to its idle-disabled state after the failed attempt.
2. **Given** the LRF enable control is configured correctly, **When** the system powers on the module, **Then** normal distance-reading behavior remains available without regressing existing LRF workflows.

---

### Edge Cases

- What happens if the LRF enable control is assigned but starts in the wrong default state during boot? The system must drive the enable control back to the idle-disabled state during startup and must avoid treating the sensor as ready until the documented active-low power-on state has been applied for an active ranging request.
- What happens if the LRF hardware is present but the enable control is omitted from configuration? The system must fail predictably, must not emit success-shaped distance output, and must behave as though ranging is unavailable.
- What happens if future hardware uses a different control polarity? The system must keep the documented active-low behavior explicit so any change is intentional and reviewable.
- What happens if the LRF enable control is asserted while the sensor is physically disconnected? The system must still surface the rangefinder as unavailable, must not report a success-shaped distance reading, and must return the enable control to idle-disabled afterward.
- What happens if repeated ranging requests occur close together? The system must apply the enable behavior consistently without reverting to leaving the sensor powered continuously between unrelated idle periods, and each measurement window must still close back to idle-disabled before or when the next request completes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a dedicated configuration entry for controlling LRF power enable behavior.
- **FR-002**: The system MUST treat the LRF enable control as active-low, meaning a low signal level powers the LRF module on.
- **FR-003**: The system MUST keep the LRF enable control deasserted while the rangefinder is not being used for an active ranging operation.
- **FR-004**: The system MUST apply the documented active-low enable behavior only for the duration needed to perform an intended ranging operation.
- **FR-005**: The system MUST preserve existing ranging workflows when the LRF enable control is configured correctly.
- **FR-006**: The system MUST make the LRF enable behavior explicit in the hardware configuration rather than relying on undocumented assumptions.
- **FR-007**: The system MUST document, in operator- or maintainer-facing guidance, that the LRF enable control powers the module on at a low level and is only asserted during active ranging use.
- **FR-008**: The system MUST fail predictably when the LRF enable control is missing, unavailable, or inconsistent with the documented behavior by withholding success-shaped distance output, preserving existing non-success behavior, and returning the enable control to the idle-disabled state after the failed measurement attempt.
- **FR-009**: Maintainers MUST be able to identify the LRF enable control and its power-on polarity from the sentry configuration and supporting documentation.

### Key Entities *(include if feature involves data)*

- **LRF Enable Control**: The controller-managed hardware control used to turn the rangefinder power state on or off.
- **LRF Power State**: The observed operating state of the rangefinder, especially whether it is powered for normal ranging use.
- **Hardware Configuration**: The sentry’s maintained set of hardware control definitions, including pin assignments and documented signal behavior.

### Assumptions

- The request refers to the Arduino hardware configuration surface even though the original message said "android config."
- The LRF datasheet requirement provided by the user is authoritative for this feature: a low signal level powers the module on.
- Existing ranging behavior is already present and this feature only adds the missing enable-control definition and its documented behavior.
- The feature scope includes documentation updates alongside configuration changes so future hardware work uses the correct polarity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer can identify the LRF enable control and its active-low power-on behavior from the sentry documentation in under 2 minutes.
- **SC-002**: In validation, 100% of sentry boots with a correctly configured LRF enable control keep the rangefinder unpowered while idle and power it on successfully for intended ranging operations without requiring manual source edits.
- **SC-003**: In validation, 100% of sentry boots with a missing or incorrect LRF enable control surface the rangefinder as unavailable instead of silently behaving as though ranging is healthy.
- **SC-004**: Existing distance-reading workflows remain usable after the new LRF enable control is added, with no regression to the normal operator ranging path.
