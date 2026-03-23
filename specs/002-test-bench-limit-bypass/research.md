# Phase 0 Research: Test Bench Limit Switch Bypass

## Decision 1: Jetson-local persisted runtime config is the source of truth for the housing profile

**Decision**: Store the saved per-unit housing profile on the sentry unit, persisted on the Jetson via `config.py` / environment-backed settings, and treat the Flutter app as a consumer of published safety state rather than the authority.

**Rationale**:

- The Jetson is the sentry runtime that decides whether motion is allowed at startup and during autonomous operation.
- Existing app persistence in `app/lib/models/sentry_config.dart` and `app/lib/features/setup/setup_provider.dart` is operator-device configuration, not sentry-unit behavior control.
- A startup safety gate cannot depend on whether the app is connected.
- This preserves the spec requirement that the profile is saved per unit, while keeping the enforcement authority on the sentry itself.

**Alternatives considered**:

- **App-only persistence**: Rejected because the sentry must enforce safety even when no mobile client is attached.
- **Arduino compile-time profile**: Rejected because the profile is operational configuration, not firmware structure, and changing it should not require reflashing.

## Decision 2: Add explicit test-bench bound config instead of reusing existing hard-limit constants

**Decision**: Introduce explicit Jetson config fields for `HOUSING_PROFILE`, `TEST_BENCH_PAN_MIN_STEPS`, `TEST_BENCH_PAN_MAX_STEPS`, `TEST_BENCH_TILT_MIN_STEPS`, and `TEST_BENCH_TILT_MAX_STEPS`.

**Rationale**:

- The clarified requirement is preconfigured software min/max pan and tilt bounds.
- Existing `PAN_LIMIT_WARN_STEPS`, `PAN_LIMIT_HARD_STEPS`, and `TILT_LIMIT_*` values are asymmetric warning/hard-stop constants, not a fully declared min/max envelope.
- Existing scan constants (`SCAN_PAN_MIN`, `SCAN_PAN_MAX`, `SCAN_TILT_HOME`) are motion-behavior values, not an explicit safety contract for all operator-driven movement.

**Alternatives considered**:

- **Reuse existing limit constants only**: Rejected because they do not encode the full four-bound test-bench envelope.
- **Derive bounds from scan/search settings**: Rejected because scan behavior and safety boundaries are separate concerns.

## Decision 3: Keep the Arduino wire protocol unchanged and extend Jetson consumption of `LIMIT` events

**Decision**: Do not add new serial commands. Extend Jetson `parse_frame()` and `ArduinoLink` state tracking to consume the existing Arduino `LIMIT <axis> <direction>` notifications.

**Rationale**:

- The firmware already emits `LIMIT` events on confirmed switch triggers.
- The existing protocol can support MVP validation without additional wire-level complexity.
- Preserving the serial contract keeps firmware risk low and avoids unnecessary Arduino implementation churn.

**Alternatives considered**:

- **New serial command for mode/profile sync**: Rejected because Jetson can enforce software bounds before sending velocity and does not need Arduino awareness of housing profile.
- **Ignore `LIMIT` events and enforce Jetson-only soft bounds everywhere**: Rejected because MVP mode explicitly requires real hardware switches.

## Decision 4: MVP mode uses startup switch-validation instead of passive assumptions

**Decision**: In MVP profile, motion stays blocked until Jetson observes one `LIMIT` event from each of the four physical switches after startup.

**Rationale**:

- Normally-open switches on `INPUT_PULLUP` lines are indistinguishable from disconnected wires while idle.
- Observing all four real switch activations is the most practical proof of presence/availability available within current hardware constraints.
- This preserves the test-bench bypass as temporary while making MVP mode actively require hardware validation.

**Alternatives considered**:

- **Assume switches exist in MVP mode based on profile alone**: Rejected because it would not actually enforce the MVP requirement.
- **Automatic homing/probing routine**: Rejected for this feature because no homing workflow exists today and it would expand scope significantly.

## Decision 5: Publish an authoritative MQTT safety-status topic for the app

**Decision**: Add a dedicated MQTT status topic carrying housing profile, protection mode, motion readiness, and blocked-motion reason so the app can show persistent safety state.

**Rationale**:

- Current telemetry is target-driven and only appears when detections exist, so it cannot guarantee a persistent warning.
- The app already consumes MQTT streams, making a second status stream a natural extension.
- Operator-facing warnings should reflect the unit’s current runtime state, not local guesses.

**Alternatives considered**:

- **Piggyback safety state onto threat telemetry only**: Rejected because no-target conditions would hide safety status.
- **Mirror the profile in app local config only**: Rejected because mirrored local state can drift from the sentry’s actual runtime configuration.

## Decision 6: Testing must center on TDD plus hardware validation of the commissioning path

**Decision**: Cover the feature with Jetson unit tests for parsing/gating/status publication, app tests for status rendering and motion blocking, and hardware-in-the-loop validation for the MVP switch-validation flow.

**Rationale**:

- The constitution requires automated coverage for non-trivial logic and explicit validation for hardware-touching flows.
- The risky behavior in this feature is not just config parsing but the interaction between serial events, motion gating, and operator feedback.

**Alternatives considered**:

- **Jetson-only unit tests**: Rejected because the operator-visible reduced-safety requirement also affects the app.
- **Hardware-only verification**: Rejected because repeatable regression coverage is needed before touching the physical rig.
