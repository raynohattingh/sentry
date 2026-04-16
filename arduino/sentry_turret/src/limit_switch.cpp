/**
 * @file limits.cpp
 * @brief Normally-open limit switch driver with software debounce.
 *
 * See limits.h for state machine description and API documentation.
 */

#ifndef NATIVE_ENV
#  include <Arduino.h>
#endif

#include "limit_switch.h"
#include "config.h"

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

void limitInit(LimitPin& lim, uint8_t pin) {
    lim.pin          = pin;
    lim.state        = LimitState::IDLE;
    lim.candidateMs  = 0;
    lim.triggered    = false;
    lim.releaseCount = 0;
    pinMode(lim.pin, INPUT_PULLUP);
}

void limitTick(LimitPin& lim) {
    const uint8_t sample = digitalRead(lim.pin);  // LOW = switch closed

    switch (lim.state) {
        case LimitState::IDLE:
            if (sample == LOW) {
                lim.candidateMs = millis();
                lim.state       = LimitState::DEBOUNCING;
            }
            break;

        case LimitState::DEBOUNCING:
            if (sample == HIGH) {
                // Bounce — cancel debounce window.
                lim.state = LimitState::IDLE;
            } else if ((millis() - lim.candidateMs) >= LIMIT_DEBOUNCE_MS) {
                lim.triggered = true;
                lim.state     = LimitState::TRIGGERED;
            }
            break;

        case LimitState::TRIGGERED:
            if (sample == HIGH) {
                // Require multiple consecutive HIGH samples before releasing
                // to reject spurious single-sample glitches from vibration.
                lim.releaseCount++;
                if (lim.releaseCount >= LIMIT_RELEASE_DEBOUNCE_COUNT) {
                    lim.triggered    = false;
                    lim.releaseCount = 0;
                    lim.state        = LimitState::IDLE;
                }
            } else {
                // Still pressed — reset the release counter.
                lim.releaseCount = 0;
            }
            break;
    }
}
