# Quickstart: Test Bench Limit Switch Bypass

## 1. Configure Jetson for test bench mode

Set the housing profile and explicit software bounds before starting the Jetson runtime:

```bash
cd /Users/raynohattingh/dev/sentry/jetson/src && \
SENTRY_ID=my-sentry-001 \
MQTT_BROKER=192.168.1.100 \
MQTT_USERNAME=sentry \
MQTT_PASSWORD=changeme \
HOUSING_PROFILE=TEST_BENCH \
TEST_BENCH_PAN_MIN_STEPS=-4000 \
TEST_BENCH_PAN_MAX_STEPS=4000 \
TEST_BENCH_TILT_MIN_STEPS=-900 \
TEST_BENCH_TILT_MAX_STEPS=900 \
python3 main.py
```

Expected behavior:

- Jetson publishes `sentry/status` with `protection_mode=SOFT_LIMIT_BYPASS`
- motion is allowed only inside the configured software bounds
- missing hardware limit switches do not block test bench operation

## 2. Configure Jetson for MVP mode

```bash
cd /Users/raynohattingh/dev/sentry/jetson/src && \
SENTRY_ID=my-sentry-001 \
MQTT_BROKER=192.168.1.100 \
MQTT_USERNAME=sentry \
MQTT_PASSWORD=changeme \
HOUSING_PROFILE=MVP \
python3 main.py
```

Expected behavior:

- Jetson publishes `sentry/status` with `protection_mode=HARDWARE_VALIDATION_PENDING`
- motion remains blocked until all four switch directions are observed through existing `LIMIT` events

## 3. Validate MVP switches on hardware

With an MVP-style housing connected:

1. Start Jetson in `MVP` mode.
2. Manually actuate `PAN LEFT`, `PAN RIGHT`, `TILT DOWN`, and `TILT UP`.
3. Confirm Jetson receives all four `LIMIT` events.
4. Verify `sentry/status` transitions to `HARDWARE_LIMITS_ACTIVE` and `motion_allowed=true`.

## 4. App validation

Run app tests:

```bash
cd /Users/raynohattingh/dev/sentry/app && flutter test
```

Manual app checks:

1. Open the map screen and verify a persistent reduced-safety banner in test bench mode.
2. Open manual override and verify motion-blocked messaging when MVP validation is still pending.
3. Open settings and verify the current housing/protection state is visible.

## 5. Jetson validation

Run Jetson unit tests:

```bash
cd /Users/raynohattingh/dev/sentry/jetson && SENTRY_ID=test python3 -m pytest tests/unit/ -v
```

Focus areas:

- `LIMIT` frame parsing
- startup validation progress
- motion blocking and software-bound enforcement
- safety-status MQTT publication

## 6. Arduino validation

Run native firmware tests:

```bash
cd /Users/raynohattingh/dev/sentry/arduino/sentry_turret && pio test --environment native
```

If firmware logic remains unchanged, hardware-in-the-loop validation is still required to confirm:

- absent switches on the test bench do not produce false triggers
- installed switches on MVP hardware emit the expected `LIMIT` events
