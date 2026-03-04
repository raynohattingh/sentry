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
    lim.pin         = pin;
    lim.state       = LimitState::IDLE;
    lim.candidateMs = 0;
    lim.triggered   = false;
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
                // Switch released — clear flag and return to idle.
                lim.triggered = false;
                lim.state     = LimitState::IDLE;
            }
            break;
    }
}
