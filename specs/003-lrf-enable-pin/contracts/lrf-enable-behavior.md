# Contract: LRF Enable Pin Behavior

## Purpose

Define the expected firmware-side behavior for the new LRF enable control so hardware configuration, control flow, and testing all align.

## Configuration Contract

- The Arduino firmware must define a dedicated LRF enable pin in `config.h`.
- The enable control is **active-low**:
  - `LOW` = LRF powered on / enabled
  - `HIGH` = LRF powered off / deasserted

## Runtime Behavior Contract

- On startup, the firmware must place the LRF in its idle disabled state.
- The firmware must not leave the LRF powered while idle.
- When a `CMD_LASER` request is processed, the firmware must:
  1. assert the active-low enable state,
  2. perform the normal trigger / read workflow,
  3. return the enable control to its inactive state after the measurement window completes.

## Failure Behavior Contract

- If the enable control is missing, misconfigured, or not asserted for the measurement window, the firmware must not emit a success-shaped distance result.
- The firmware must preserve the existing non-success path for an unavailable or failed reading rather than inventing a new Jetson ↔ Arduino command contract.
- After any failed or incomplete ranging attempt, the firmware must return the enable control to its idle-disabled state.
- Repeated ranging failures must not leave the LRF continuously powered between attempts.

## Non-Goals

- No new Jetson ↔ Arduino serial commands
- No change to the `DIST` response format
- No permanent always-on LRF power mode as the default behavior for this feature

## Validation Expectations

- Host-native tests should verify polarity and idle-vs-ranging transitions.
- Host-native tests should verify the end-to-end `CMD_LASER -> enable assert -> read attempt -> enable deassert` flow without changing the serial contract.
- Host-native tests should verify boot-state recovery, repeated request handling, and failure behavior that suppresses success-shaped distance output.
- Hardware-in-the-loop validation should verify that the module only powers on during active ranging operations.
- Hardware-in-the-loop validation should verify that a disconnected or miswired module does not appear as a successful ranging result.
