/**
 * @file test_limits/test_main.cpp
 * @brief Unity unit tests for the limit switch debounce driver — native host.
 *
 * Verifies:
 *   1. Instantaneous HIGH does not set triggered
 *   2. Instantaneous LOW for less than LIMIT_DEBOUNCE_MS does not set triggered
 *   3. LOW held for exactly LIMIT_DEBOUNCE_MS sets triggered
 *   4. Bounce (LOW then HIGH before timeout) does NOT set triggered
 *   5. Triggered clears when pin returns HIGH
 *   6. Consecutive triggers work correctly (state resets)
 */

#include <unity.h>
#include <stdint.h>

// ─────────────────────────────────────────────────────────────────────────────
// Arduino stub layer
// ─────────────────────────────────────────────────────────────────────────────

static uint8_t      g_pinValue[20]  = {};
static unsigned long g_millis       = 0;
static unsigned long g_micros       = 0;

static constexpr uint8_t OUTPUT      = 1;
static constexpr uint8_t INPUT       = 0;
static constexpr uint8_t HIGH        = 1;
static constexpr uint8_t LOW         = 0;
static constexpr uint8_t INPUT_PULLUP = 2;
static constexpr uint8_t A0          = 14;
static constexpr uint8_t A1          = 15;

static void     pinMode(uint8_t, uint8_t) {}
static void     digitalWrite(uint8_t pin, uint8_t val) { g_pinValue[pin] = val; }
static uint8_t  digitalRead(uint8_t pin) { return g_pinValue[pin]; }
static unsigned long millis() { return g_millis; }
static unsigned long micros() { return g_micros; }

// ─────────────────────────────────────────────────────────────────────────────
// Pull in implementation under test
// ─────────────────────────────────────────────────────────────────────────────

#include "config.h"
#include "limit_switch.h"
#include "limit_switch.cpp"

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Simulate pin reading HIGH and advance time by dt ms. */
static void setHigh(uint8_t pin) { g_pinValue[pin] = HIGH; }
static void setLow(uint8_t pin)  { g_pinValue[pin] = LOW; }
static void advanceMs(unsigned long dt) { g_millis += dt; }

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

/** Pin stays HIGH — never triggered. */
void test_no_trigger_when_high(void) {
    LimitPin lim{};
    limitInit(lim, 9);
    setHigh(9);
    for (int i = 0; i < 100; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_FALSE(lim.triggered);
}

/** LOW for less than debounce window — not triggered. */
void test_no_trigger_short_low(void) {
    LimitPin lim{};
    g_millis = 0;
    limitInit(lim, 9);
    setLow(9);
    // Hold LOW for LIMIT_DEBOUNCE_MS - 1 ms
    for (unsigned int i = 0; i < LIMIT_DEBOUNCE_MS - 1u; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_FALSE(lim.triggered);
}

/** LOW held for ≥ LIMIT_DEBOUNCE_MS sets triggered. */
void test_trigger_after_debounce(void) {
    LimitPin lim{};
    g_millis = 0;
    limitInit(lim, 9);
    setLow(9);
    // Advance past the debounce window
    for (unsigned int i = 0; i <= LIMIT_DEBOUNCE_MS; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_TRUE(lim.triggered);
}

/** Bounce: LOW → HIGH before debounce window — not triggered. */
void test_bounce_cancelled(void) {
    LimitPin lim{};
    g_millis = 0;
    limitInit(lim, 9);
    setLow(9);
    advanceMs(LIMIT_DEBOUNCE_MS / 2u);
    limitTick(lim);  // start debounce

    // Pin bounces back HIGH before window closes
    setHigh(9);
    limitTick(lim);

    // Continue past what would have been the timeout
    for (unsigned int i = 0; i <= LIMIT_DEBOUNCE_MS; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_FALSE(lim.triggered);
}

/** Triggered flag clears after LIMIT_RELEASE_DEBOUNCE_COUNT consecutive HIGH samples. */
void test_triggered_clears_on_release(void) {
    LimitPin lim{};
    g_millis = 0;
    limitInit(lim, 9);
    setLow(9);
    for (unsigned int i = 0; i <= LIMIT_DEBOUNCE_MS; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_TRUE(lim.triggered);

    setHigh(9);
    for (uint8_t i = 0; i < LIMIT_RELEASE_DEBOUNCE_COUNT; ++i) {
        limitTick(lim);
    }
    TEST_ASSERT_FALSE(lim.triggered);
}

/** Single HIGH sample is not enough to clear triggered (rejects glitches). */
void test_single_high_does_not_release(void) {
    LimitPin lim{};
    g_millis = 0;
    limitInit(lim, 9);
    setLow(9);
    for (unsigned int i = 0; i <= LIMIT_DEBOUNCE_MS; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_TRUE(lim.triggered);

    setHigh(9);
    limitTick(lim);
    // One HIGH sample is below LIMIT_RELEASE_DEBOUNCE_COUNT — must stay triggered.
    TEST_ASSERT_TRUE(lim.triggered);
}

/** Consecutive triggers: state machine resets correctly after release. */
void test_consecutive_triggers(void) {
    LimitPin lim{};
    g_millis = 0;
    limitInit(lim, 9);

    // First trigger
    setLow(9);
    for (unsigned int i = 0; i <= LIMIT_DEBOUNCE_MS; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_TRUE(lim.triggered);

    // Release: requires LIMIT_RELEASE_DEBOUNCE_COUNT consecutive HIGH samples.
    setHigh(9);
    for (uint8_t i = 0; i < LIMIT_RELEASE_DEBOUNCE_COUNT; ++i) {
        limitTick(lim);
    }
    TEST_ASSERT_FALSE(lim.triggered);

    // Second trigger
    setLow(9);
    for (unsigned int i = 0; i <= LIMIT_DEBOUNCE_MS; ++i) {
        advanceMs(1);
        limitTick(lim);
    }
    TEST_ASSERT_TRUE(lim.triggered);
}

// ─────────────────────────────────────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────────────────────────────────────

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_no_trigger_when_high);
    RUN_TEST(test_no_trigger_short_low);
    RUN_TEST(test_trigger_after_debounce);
    RUN_TEST(test_bounce_cancelled);
    RUN_TEST(test_triggered_clears_on_release);
    RUN_TEST(test_single_high_does_not_release);
    RUN_TEST(test_consecutive_triggers);
    return UNITY_END();
}
