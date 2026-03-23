# Quickstart: LRF Enable Pin Configuration

## 1. Update firmware configuration

Add the LRF enable control to `arduino/sentry_turret/src/config.h` with the documented active-low power behavior.

Expected outcome:

- The pin assignment is defined as a named constant.
- The docs/comments make it explicit that `LOW` powers the LRF on.

## 2. Build and run native tests

```bash
cd /Users/raynohattingh/dev/sentry/arduino/sentry_turret
pio test --environment native
```

Focus areas:

- idle LRF state does not leave the module enabled
- active-low enable behavior is preserved
- a ranging request enables the module only for the active operation window
- a failed or unavailable ranging attempt does not emit a success-shaped distance result

## 3. Flash firmware and validate on hardware

```bash
cd /Users/raynohattingh/dev/sentry/arduino/sentry_turret
pio run --environment uno --target upload
```

Hardware validation steps:

1. Power the sentry with the updated firmware.
2. Confirm the LRF is not left continuously powered during idle operation.
3. Trigger a ranging operation from the Jetson path.
4. Confirm the firmware pulls the enable control low only during the measurement attempt.
5. Confirm normal `DIST` reporting still works.
6. Disconnect or miswire the LRF enable path and confirm the firmware does not appear to produce a successful reading.

## 4. Regression checks

- Verify the existing Jetson `CMD_LASER` → Arduino `DIST` flow still works unchanged.
- Verify native tests remain green with `NATIVE_ENV`.
- Verify no unrelated limit-switch or stepper behavior regresses during firmware startup.

## 5. Performance validation

- Measure `CMD_LASER` to completed read behavior before and after the enable-gating change and confirm no meaningful regression to the operator-visible ranging path.
- Verify the firmware still returns the LRF to the idle-disabled state after success and after failure.
- Verify the control loop / `POS` heartbeat cadence is not degraded while the new enable logic is active.

### Current implementation evidence

- Host-native validation passes with `36/36` tests green after the LRF enable-gating changes, including new tests for idle-disabled startup, active-low enable assertion, repeated request handling, timeout handling, and return to idle-disabled state.
- The LRF failure path remains non-blocking in firmware: timeout handling uses the existing `millis()`-based window instead of adding a blocking wait loop around `CMD_LASER`.
- Hardware latency and heartbeat-cadence measurements still need to be captured on a physical unit before merge.
