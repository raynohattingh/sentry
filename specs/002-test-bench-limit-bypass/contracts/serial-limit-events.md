# Serial Contract: Existing `LIMIT` Events Consumed by Jetson

## Purpose

Use the Arduino's existing limit-switch notifications as the evidence stream for MVP startup validation, without changing the serial wire protocol.

## Existing Wire Format

```text
LIMIT <axis> <direction>\n
```

Examples:

```text
LIMIT PAN LEFT
LIMIT PAN RIGHT
LIMIT TILT DOWN
LIMIT TILT UP
```

## Producer

Arduino firmware (`arduino/sentry_turret/src/sentry_turret.ino`)

## Consumer

Jetson serial parser and `ArduinoLink`

## Consumption Rules

- Jetson must accept and parse the existing `LIMIT` frames in addition to `POS` and `DIST`.
- Each distinct switch direction counts once toward MVP startup validation for the current boot.
- Test bench mode ignores `LIMIT` validation requirements but may still log observed events.
- No new Jetson-to-Arduino commands are added for this feature.

## Validation Semantics

In MVP profile:

- motion remains blocked until all four distinct events are observed:
  - `PAN LEFT`
  - `PAN RIGHT`
  - `TILT DOWN`
  - `TILT UP`
- once all four are observed after startup, Jetson may transition to motion-allowed state

In test bench profile:

- motion permission is controlled by configured software bounds instead of limit-event validation

## Non-Goals

- No firmware-side awareness of housing profile
- No new serial handshake, commissioning command, or homing protocol
