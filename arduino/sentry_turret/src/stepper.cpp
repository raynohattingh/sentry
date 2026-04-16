/**
 * @file stepper.cpp
 * @brief Non-blocking stepper motor driver implementation.
 *
 * See stepper.h for full API documentation and design constraints.
 *
 * Step pulse strategy:
 *   A delayMicroseconds(2) is inserted between the STEP HIGH and LOW writes
 *   to guarantee the A4988/DRV8825 datasheet minimum of 1 µs STEP pulse width
 *   regardless of compiler optimisation level or clock speed.
 */

#ifndef NATIVE_ENV
#  include <Arduino.h>
#endif

#include "stepper.h"
#include "config.h"

#include <stdint.h>
#include <climits>  // INT32_MAX, INT32_MIN
#include <math.h>   // fabsf

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

void stepperInit(StepperAxis& axis, uint8_t stepPin, uint8_t dirPin) {
    axis.stepPin        = stepPin;
    axis.dirPin         = dirPin;
    axis.velocity       = 0.0f;
    axis.stepIntervalUs = 0;
    axis.nextStepTimeUs = micros();
    axis.stepCount      = 0;

    pinMode(axis.stepPin, OUTPUT);
    pinMode(axis.dirPin,  OUTPUT);
    digitalWrite(axis.stepPin, LOW);
    digitalWrite(axis.dirPin,  LOW);
}

void stepperSetVelocity(StepperAxis& axis, float velocity) {
    axis.velocity = velocity;

    if (velocity == 0.0f) {
        axis.stepIntervalUs = 0;
        // Do NOT touch nextStepTimeUs or stepCount (FR-013).
        return;
    }

    // Set direction pin.
    digitalWrite(axis.dirPin, velocity > 0.0f ? HIGH : LOW);

    // Compute interval from magnitude; apply minimum clamp (FR-014).
    uint32_t interval =
        static_cast<uint32_t>(VELOCITY_SCALE_FACTOR / fabsf(velocity));
    if (interval < MIN_STEP_INTERVAL_US) {
        interval = MIN_STEP_INTERVAL_US;
    }
    // Upper clamp: anything slower than MAX_STEP_INTERVAL_US is effectively
    // stopped — treat as zero velocity to avoid multi-second dead time.
    if (interval > MAX_STEP_INTERVAL_US) {
        axis.stepIntervalUs = 0;
        return;
    }
    axis.stepIntervalUs = interval;

    // Do NOT reset nextStepTimeUs or stepCount (FR-013).
}

void stepperTick(StepperAxis& axis) {
    // Stopped or uninitialised — nothing to do.
    if (axis.stepIntervalUs == 0) return;

    const uint32_t now = micros();
    // Unsigned subtraction handles micros() wrap-around at ~70 min correctly.
    if ((now - axis.nextStepTimeUs) < axis.stepIntervalUs) return;

    // Advance nextStepTimeUs by one interval to prevent timing drift.
    axis.nextStepTimeUs += axis.stepIntervalUs;
    // Catch-up guard: if we fell behind by more than 2 intervals, reset to now
    // to avoid a burst of rapid-fire steps.
    if ((now - axis.nextStepTimeUs) > axis.stepIntervalUs * 2) {
        axis.nextStepTimeUs = now + axis.stepIntervalUs;
    }

    // Emit STEP pulse with guaranteed minimum 1 µs HIGH duration.
    digitalWrite(axis.stepPin, HIGH);
    delayMicroseconds(2);
    digitalWrite(axis.stepPin, LOW);

    // Update signed step count with INT32 overflow guard (FR-022).
    if (axis.velocity > 0.0f) {
        if (axis.stepCount < INT32_MAX) {
            axis.stepCount++;
        }
    } else {
        if (axis.stepCount > INT32_MIN) {
            axis.stepCount--;
        }
    }
}
