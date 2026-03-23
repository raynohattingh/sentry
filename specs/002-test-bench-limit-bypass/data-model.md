# Data Model: Test Bench Limit Switch Bypass

## 1. Jetson Configuration Model

### 1.1 `HousingProfile`

Represents the intended physical enclosure mode for a sentry unit.

| Field | Type | Allowed Values | Notes |
|---|---|---|---|
| `housing_profile` | enum/string | `TEST_BENCH`, `MVP` | Source-of-truth profile loaded from Jetson config |

**Validation rules**

- `TEST_BENCH` enables software-bound operation only when all four configured bounds are valid.
- `MVP` disables the bypass and requires physical switch validation before motion.

### 1.2 `SoftMotionBounds`

Represents the preconfigured software travel envelope used only in test bench mode.

| Field | Type | Notes |
|---|---|---|
| `pan_min_steps` | int | Inclusive lower pan bound |
| `pan_max_steps` | int | Inclusive upper pan bound |
| `tilt_min_steps` | int | Inclusive lower tilt bound |
| `tilt_max_steps` | int | Inclusive upper tilt bound |

**Validation rules**

- `pan_min_steps < pan_max_steps`
- `tilt_min_steps < tilt_max_steps`
- Bounds are mandatory when `housing_profile == TEST_BENCH`
- Invalid or missing bounds force `motion_allowed = false`

### 1.3 New Jetson config additions

| Name | Type | Default | Validation |
|---|---|---|---|
| `HOUSING_PROFILE` | `str` | `"MVP"` | Must be `TEST_BENCH` or `MVP` |
| `TEST_BENCH_PAN_MIN_STEPS` | `int` | none | Required for `TEST_BENCH` |
| `TEST_BENCH_PAN_MAX_STEPS` | `int` | none | Required for `TEST_BENCH` |
| `TEST_BENCH_TILT_MIN_STEPS` | `int` | none | Required for `TEST_BENCH` |
| `TEST_BENCH_TILT_MAX_STEPS` | `int` | none | Required for `TEST_BENCH` |
| `MQTT_STATUS_TOPIC` | `str` | `"sentry/status"` | MQTT topic for safety status |

## 2. Serial Event Model

### 2.1 `LimitEvent`

Represents one inbound Arduino `LIMIT` notification consumed by Jetson.

| Field | Type | Allowed Values | Notes |
|---|---|---|---|
| `axis` | enum/string | `PAN`, `TILT` | From serial payload |
| `direction` | enum/string | `LEFT`, `RIGHT`, `UP`, `DOWN` | From serial payload |
| `received_utc` | string | ISO 8601 UTC | Assigned by Jetson at parse time |

**Relationships**

- Produced by `parse_frame()` / `ArduinoLink`
- Consumed by startup switch-validation logic

## 3. Validation State Model

### 3.1 `LimitValidationState`

Represents whether the sentry may move under the current housing profile.

| State | Meaning |
|---|---|
| `BYPASSED` | Test bench mode with valid software bounds; hardware switch validation not required |
| `BLOCKED_INVALID_BOUNDS` | Test bench mode selected but bounds are missing/invalid |
| `PENDING_SWITCH_VALIDATION` | MVP mode active; waiting to observe all four switch triggers |
| `READY_HARDWARE_VALIDATED` | MVP mode active and all required switches validated this boot |

### 3.2 Validation transitions

```text
Startup
  -> TEST_BENCH + valid bounds         -> BYPASSED
  -> TEST_BENCH + invalid/missing      -> BLOCKED_INVALID_BOUNDS
  -> MVP                               -> PENDING_SWITCH_VALIDATION

PENDING_SWITCH_VALIDATION
  -> observe PAN LEFT, PAN RIGHT, TILT DOWN, TILT UP
  -> READY_HARDWARE_VALIDATED

Any profile change to TEST_BENCH/MVP
  -> recompute from startup rules
```

## 4. Runtime Safety Status Model

### 4.1 `SafetyStatus`

Authoritative runtime status published by Jetson and consumed by the app.

| Field | Type | Notes |
|---|---|---|
| `sentry_id` | string | Identifies the unit emitting status |
| `housing_profile` | string | `TEST_BENCH` or `MVP` |
| `protection_mode` | string | `SOFT_LIMIT_BYPASS`, `HARDWARE_VALIDATION_PENDING`, or `HARDWARE_LIMITS_ACTIVE` |
| `motion_allowed` | bool | Whether turret movement is currently permitted |
| `motion_block_reason` | string/null | e.g. `INVALID_TEST_BENCH_BOUNDS`, `LIMIT_SWITCH_VALIDATION_REQUIRED` |
| `validated_switches` | array[string] | Distinct validated directions seen this boot |
| `timestamp_utc` | string | ISO 8601 UTC |

**Validation rules**

- `motion_allowed == true` only in `BYPASSED` or `READY_HARDWARE_VALIDATED`
- `motion_block_reason == null` when `motion_allowed == true`
- `validated_switches` is empty in test bench mode

## 5. App Model

### 5.1 `SafetyStatusRecord` (Flutter)

Mirrors the MQTT safety status payload in Dart for provider/UI use.

| Field | Type |
|---|---|
| `sentryId` | `String` |
| `housingProfile` | enum |
| `protectionMode` | enum |
| `motionAllowed` | `bool` |
| `motionBlockReason` | nullable enum/string |
| `validatedSwitches` | `List<String>` |
| `timestampUtc` | `DateTime` |

**Relationships**

- Parsed in `mqtt_service.dart`
- Exposed through a Riverpod provider
- Rendered by map, override, and settings surfaces

## 6. Affected Existing Models

### 6.1 `TelemetryRecord`

No structural change is strictly required if safety status moves to a dedicated MQTT topic. If implementation chooses to duplicate selected fields in telemetry for convenience, the status topic remains authoritative.

### 6.2 `ArduinoLink`

`ArduinoLink` gains runtime state for:

- last observed `LimitEvent`
- set of unique validated switch directions for the current boot
- helper/query methods used by motion gating and status publication
