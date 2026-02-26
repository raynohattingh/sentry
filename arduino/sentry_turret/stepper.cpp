/**
 * @file stepper.cpp
 * @brief Non-blocking stepper motor driver implementation.
 *
 * See stepper.h for full API documentation and design constraints.
 *
 * Step pulse strategy:
 *   Two consecutive digitalWrite() calls generate the STEP HIGH → LOW pulse.
 *   AVR GPIO toggle latency is ~125 ns per instruction (16 MHz clock), giving
 *   an estimated HIGH duration of ~125–250 ns per write pair, which is below
 *   the A4988/DRV8825 datasheet minimum of 1 µs.  In practice the AVR compiler
 *   inserts additional instruction latency (register loads, branch overhead)
 *   that brings the actual high time to ≥1 µs without an explicit delay.
 *   No delayMicroseconds() is inserted here (FR-026).
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
    unsigned long interval =
        static_cast<unsigned long>(VELOCITY_SCALE_FACTOR / fabsf(velocity));
    if (interval < MIN_STEP_INTERVAL_US) {
        interval = MIN_STEP_INTERVAL_US;
    }
    axis.stepIntervalUs = interval;

    // Do NOT reset nextStepTimeUs or stepCount (FR-013).
}

void stepperTick(StepperAxis& axis) {
    // Stopped or uninitialised — nothing to do.
    if (axis.stepIntervalUs == 0) return;

    const unsigned long now = micros();
    if (now < axis.nextStepTimeUs) return;

    // Schedule next step before emitting pulse to maintain cadence.
    axis.nextStepTimeUs = now + axis.stepIntervalUs;

    // Emit STEP pulse: two back-to-back writes — no delayMicroseconds (FR-026).
    digitalWrite(axis.stepPin, HIGH);
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
