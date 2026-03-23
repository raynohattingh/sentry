# MQTT Contract: `sentry/status`

## Purpose

Provide an authoritative, persistent runtime safety view for operator-facing clients so reduced-safety test bench mode and blocked MVP motion are visible even when no threats are currently being tracked.

## Topic

`sentry/status`

## Publisher

Jetson runtime

## Subscribers

Flutter mobile app and any future operator status surfaces

## Payload

```json
{
  "sentry_id": "my-sentry-001",
  "housing_profile": "TEST_BENCH",
  "protection_mode": "SOFT_LIMIT_BYPASS",
  "motion_allowed": true,
  "motion_block_reason": null,
  "validated_switches": [],
  "timestamp_utc": "2026-03-23T17:00:00Z"
}
```

## Field Rules

| Field | Type | Rules |
|---|---|---|
| `sentry_id` | string | Must match the configured `SENTRY_ID` |
| `housing_profile` | string | `TEST_BENCH` or `MVP` |
| `protection_mode` | string | `SOFT_LIMIT_BYPASS`, `HARDWARE_VALIDATION_PENDING`, or `HARDWARE_LIMITS_ACTIVE` |
| `motion_allowed` | boolean | `true` only when motion is currently permitted |
| `motion_block_reason` | string/null | Null when motion is allowed; otherwise machine-readable reason |
| `validated_switches` | array[string] | Distinct validated switch directions seen this boot |
| `timestamp_utc` | string | UTC ISO 8601 timestamp |

## Behavior

- Jetson publishes this status at startup and whenever the safety state changes.
- The app treats this topic as the authority for reduced-safety banners and blocked-motion messaging.
- `motion_block_reason` values remain snake_case or uppercase-enum style consistently across producer and consumer implementation.

## Example MVP blocked payload

```json
{
  "sentry_id": "my-sentry-001",
  "housing_profile": "MVP",
  "protection_mode": "HARDWARE_VALIDATION_PENDING",
  "motion_allowed": false,
  "motion_block_reason": "LIMIT_SWITCH_VALIDATION_REQUIRED",
  "validated_switches": ["PAN_LEFT", "PAN_RIGHT"],
  "timestamp_utc": "2026-03-23T17:02:15Z"
}
```
