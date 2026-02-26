/**
 * @file limits.h
 * @brief Normally-open limit switch driver with software debounce.
 *
 * Switches are active-LOW (INPUT_PULLUP).  A trigger is only confirmed after
 * the pin has been continuously LOW for LIMIT_DEBOUNCE_MS milliseconds.
 *
 * The state machine is intentionally simple:
 *   IDLE         → pin samples HIGH: no action
 *   IDLE         → pin samples LOW:  record candidateTime, transition to DEBOUNCING
 *   DEBOUNCING   → pin samples HIGH: cancel, transition back to IDLE
 *   DEBOUNCING   → elapsed ≥ LIMIT_DEBOUNCE_MS: set triggered=true, transition to TRIGGERED
 *   TRIGGERED    → pin samples HIGH: clear triggered, transition to IDLE
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

// ─────────────────────────────────────────────────────────────────────────────
// Data model
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Internal debounce FSM states. */
enum class LimitState : uint8_t {
    IDLE       = 0,
    DEBOUNCING = 1,
    TRIGGERED  = 2,
};

/**
 * @brief Per-switch mutable state.
 *
 * Uses standard C++ types for native-test compatibility.
 */
struct LimitPin {
    uint8_t    pin;            ///< Arduino digital pin number
    LimitState state;          ///< FSM state
    unsigned long candidateMs; ///< millis() timestamp when LOW was first sampled
    bool       triggered;      ///< True when debounce window has elapsed
};

// ─────────────────────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Initialise a LimitPin struct and configure the pin as INPUT_PULLUP.
 * @param[out] lim  Limit struct to initialise.
 * @param[in]  pin  Arduino digital pin number.
 */
void limitInit(LimitPin& lim, uint8_t pin);

/**
 * @brief Service one switch; update debounce FSM.
 *
 * Call every loop() iteration.  After this returns, read lim.triggered to
 * determine if the limit has been confirmed.
 *
 * @param[in,out] lim  Limit struct to service.
 */
void limitTick(LimitPin& lim);
