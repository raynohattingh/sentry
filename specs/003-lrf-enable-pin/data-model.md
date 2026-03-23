# Data Model: LRF Enable Pin Configuration

## 1. Hardware Configuration Model

### 1.1 `LrfEnablePin`

Represents the Arduino output used to control LRF module power state.

| Field | Type | Notes |
|---|---|---|
| `pin` | integer constant | Arduino digital pin assignment stored in `config.h` |
| `active_level` | enum/value | `LOW` powers the module on |
| `inactive_level` | enum/value | `HIGH` powers the module off or deasserts enable |

**Validation rules**

- Must be represented as named configuration, not inline literals.
- Active level must remain explicitly documented as `LOW`.

## 2. Runtime Power State Model

### 2.1 `LrfPowerState`

Represents whether the LRF should currently be powered.

| State | Meaning |
|---|---|
| `IDLE_DISABLED` | LRF enable is deasserted; sensor is not kept powered while idle |
| `RANGING_ENABLED` | Active-low enable is asserted so the sensor can perform a requested range measurement |

**Transition rules**

```text
startup -> IDLE_DISABLED
CMD_LASER received -> RANGING_ENABLED
ranging attempt completes or times out -> IDLE_DISABLED
```

## 3. LRF Operation Window

### 3.1 `LrfMeasurementWindow`

Represents the bounded period during which the LRF is powered for an intended measurement.

| Field | Type | Notes |
|---|---|---|
| `requested` | boolean | A `CMD_LASER` request has been received |
| `enable_asserted` | boolean | Active-low pin state has been applied |
| `completed` | boolean | Measurement succeeded or failed and the operation window can close |

**Validation rules**

- The enable line should only remain asserted while an active ranging request is in progress.
- On completion or timeout, the window closes and the system returns to `IDLE_DISABLED`.

## 4. Affected Existing Components

### 4.1 `config.h`

Gains the named enable pin and explicit polarity constants.

### 4.2 `lrf.h` / `lrf.cpp`

Gain or absorb the explicit power-enable behavior so that LRF control stays encapsulated and testable.

### 4.3 `sentry_turret.ino`

Coordinates the timing of enable assertion around `CMD_LASER` while preserving the current `DIST` response flow.
