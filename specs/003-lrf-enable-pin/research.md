# Research: LRF Enable Pin Configuration

## Decision 1: Use a dedicated active-low enable pin in firmware configuration

**Decision**: Add a named LRF enable pin to `arduino/sentry_turret/src/config.h` together with explicit active and inactive levels.

**Rationale**: The datasheet requirement is polarity-sensitive, and the project constitution requires hardware behavior to be represented through named configuration rather than magic literals. Encoding both the pin and the active-low semantics in `config.h` keeps the behavior visible and reviewable.

**Alternatives considered**:

- Infer polarity only from comments in `sentry_turret.ino` — rejected because it is easy to miss and violates the configuration-centralization rule.
- Hard-code the pin and LOW/HIGH values directly in LRF control logic — rejected because it spreads hardware-specific literals into logic files.

## Decision 2: Keep the LRF disabled while idle and only assert enable around `CMD_LASER`

**Decision**: The firmware should hold the LRF in its inactive state while idle, assert the active-low enable when a laser command is requested, perform the demand-driven ranging flow, then deassert the enable again afterward.

**Rationale**: The clarified requirement explicitly prioritizes power efficiency. This preserves the existing demand-driven design in `sentry_turret.ino` and avoids leaving the sensor powered between unrelated ranging requests.

**Alternatives considered**:

- Keep the LRF enabled for the entire runtime once initialized — rejected because the user explicitly chose demand-based power control for efficiency.
- Gate power at a higher-level subsystem outside the Arduino firmware — rejected because the feature request is specifically for the Arduino hardware configuration surface.

## Decision 3: Encapsulate enable behavior in the LRF module so host-native tests stay viable

**Decision**: Extend the LRF module (`lrf.h/.cpp`) with small helper functions or an interface that controls enable/deassert behavior without forcing direct hardware pin writes to be duplicated in `sentry_turret.ino`.

**Rationale**: The constitution requires hardware-dependent code to expose a mockable or host-testable interface. Encapsulating the behavior allows native tests to verify active-low semantics and call ordering without needing real GPIO.

**Alternatives considered**:

- Put all pin toggling directly in `sentry_turret.ino` — rejected because it makes the behavior harder to test and duplicates LRF-specific knowledge outside the LRF module.
- Skip native coverage and validate only on hardware — rejected because the constitution requires automated tests before implementation is complete.

## Decision 4: Preserve the existing serial contract and `DIST` workflow

**Decision**: Do not change the Jetson ↔ Arduino serial protocol. `CMD_LASER` remains the trigger, and `DIST <value>` remains the response surface.

**Rationale**: The feature is about sensor power control, not protocol redesign. Preserving the contract avoids unnecessary cross-runtime changes and keeps the scope tightly bounded.

**Alternatives considered**:

- Add new serial commands for explicit LRF power management — rejected because they are unnecessary for the stated requirement and would expand scope into Jetson changes.

## Decision 5: Document both wiring and operational semantics

**Decision**: Update firmware-facing configuration docs and feature quickstart guidance to describe both the new pin assignment and the rule that low powers the sensor on only during active ranging operations.

**Rationale**: This feature is easy to regress later during hardware revisions. Documentation must cover not just the pin, but also the intended lifecycle of the enable signal.

**Alternatives considered**:

- Document only the pin assignment — rejected because polarity and timing semantics are the risky part of the feature.
