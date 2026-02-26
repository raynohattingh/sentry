/**
 * @file test_stepper/test_main.cpp
 * @brief Unity unit tests for the stepper motor driver — native host environment.
 *
 * Because this runs without Arduino hardware, all AVR platform calls are
 * replaced by the stub layer below. The tests verify:
 *   1. Velocity-to-interval math
 *   2. Direction pin state
 *   3. MIN_STEP_INTERVAL_US clamp
 *   4. Zero-velocity stops stepping
 *   5. stepCount increment / decrement
 *   6. FR-013: velocity update does NOT reset nextStepTimeUs or stepCount
 *   7. FR-022: INT32_MAX overflow clamp (positive)
 *   8. FR-022: INT32_MIN overflow clamp (negative)
 */

#include <unity.h>
#include <stdint.h>
#include <climits>

// ─────────────────────────────────────────────────────────────────────────────
// Arduino stub layer
// ─────────────────────────────────────────────────────────────────────────────

// Simulated GPIO state (indexed by pin number, up to 20 pins for Uno R3)
static uint8_t  g_pinValue[20]  = {};
static uint8_t  g_pinMode[20]   = {};
static unsigned long g_micros   = 0;

static constexpr uint8_t OUTPUT     = 1;
static constexpr uint8_t INPUT      = 0;
static constexpr uint8_t HIGH       = 1;
static constexpr uint8_t LOW        = 0;
static constexpr uint8_t INPUT_PULLUP = 2;

static void     pinMode(uint8_t pin, uint8_t mode) { g_pinMode[pin] = mode; }
static void     digitalWrite(uint8_t pin, uint8_t val) { g_pinValue[pin] = val; }
static uint8_t  digitalRead(uint8_t pin) { return g_pinValue[pin]; }
static unsigned long micros() { return g_micros; }
static unsigned long millis() { return g_micros / 1000UL; }

// Native env: A0 = 14 (matching Uno R3 numbering)
static constexpr uint8_t A0 = 14;
static constexpr uint8_t A1 = 15;

// ─────────────────────────────────────────────────────────────────────────────
// Pull in config.h and stepper implementation under test
// ─────────────────────────────────────────────────────────────────────────────

#include "config.h"
#include "stepper.h"
#include "stepper.cpp"  // Direct inclusion for native single-TU test build

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

/** Velocity-to-interval math: interval = VELOCITY_SCALE_FACTOR / |velocity|.
 *  Use velocity = 1.0f → interval = 1000 µs, well above MIN_STEP_INTERVAL_US (200). */
void test_velocity_interval_math(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 1.0f);
    unsigned long expected = static_cast<unsigned long>(VELOCITY_SCALE_FACTOR / 1.0f);
    TEST_ASSERT_EQUAL_UINT32(expected, axis.stepIntervalUs);
}

/** Positive velocity sets DIR pin HIGH. */
void test_positive_velocity_dir_high(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 100.0f);
    TEST_ASSERT_EQUAL_UINT8(HIGH, g_pinValue[5]);
}

/** Negative velocity sets DIR pin LOW. */
void test_negative_velocity_dir_low(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, -100.0f);
    TEST_ASSERT_EQUAL_UINT8(LOW, g_pinValue[5]);
}

/** Very high velocity must not push interval below MIN_STEP_INTERVAL_US. */
void test_min_interval_clamp(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 1000000.0f);  // unrealistically fast
    TEST_ASSERT_GREATER_OR_EQUAL_UINT32(MIN_STEP_INTERVAL_US, axis.stepIntervalUs);
}

/** Zero velocity stops stepping — stepCount must not change across tick calls. */
void test_zero_velocity_no_steps(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 0.0f);
    g_micros = 0;
    int32_t before = axis.stepCount;
    // Advance time well past any interval
    for (int i = 0; i < 100; ++i) {
        g_micros += 10000UL;
        stepperTick(axis);
    }
    TEST_ASSERT_EQUAL_INT32(before, axis.stepCount);
}

/** stepCount increments on each step when velocity is positive. */
void test_step_count_increments(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 500.0f);
    g_micros = 0;
    axis.nextStepTimeUs = 0;

    int32_t before = axis.stepCount;
    g_micros = axis.stepIntervalUs + 1;
    stepperTick(axis);
    TEST_ASSERT_EQUAL_INT32(before + 1, axis.stepCount);
}

/** stepCount decrements on each step when velocity is negative. */
void test_step_count_decrements(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, -500.0f);
    g_micros = 0;
    axis.nextStepTimeUs = 0;

    int32_t before = axis.stepCount;
    g_micros = axis.stepIntervalUs + 1;
    stepperTick(axis);
    TEST_ASSERT_EQUAL_INT32(before - 1, axis.stepCount);
}

/**
 * FR-013: stepperSetVelocity must NOT reset nextStepTimeUs or stepCount.
 * After a velocity update, those fields must retain their pre-update values.
 */
void test_velocity_update_preserves_state(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 100.0f);

    // Advance time and emit one step to establish non-zero state.
    g_micros = 0;
    axis.nextStepTimeUs = 0;
    g_micros = axis.stepIntervalUs + 1;
    stepperTick(axis);

    unsigned long savedNextStep = axis.nextStepTimeUs;
    int32_t       savedCount    = axis.stepCount;

    // Change velocity — state must be preserved.
    stepperSetVelocity(axis, 200.0f);
    TEST_ASSERT_EQUAL_UINT32(savedNextStep, axis.nextStepTimeUs);
    TEST_ASSERT_EQUAL_INT32(savedCount,     axis.stepCount);
}

/** FR-022: stepCount clamps to INT32_MAX instead of overflowing (positive). */
void test_step_count_overflow_clamp_positive(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, 100.0f);
    axis.stepCount      = INT32_MAX;
    axis.nextStepTimeUs = 0;
    g_micros            = axis.stepIntervalUs + 1;
    stepperTick(axis);
    TEST_ASSERT_EQUAL_INT32(INT32_MAX, axis.stepCount);
}

/** FR-022: stepCount clamps to INT32_MIN instead of overflowing (negative). */
void test_step_count_overflow_clamp_negative(void) {
    StepperAxis axis{};
    stepperInit(axis, 2, 5);
    stepperSetVelocity(axis, -100.0f);
    axis.stepCount      = INT32_MIN;
    axis.nextStepTimeUs = 0;
    g_micros            = axis.stepIntervalUs + 1;
    stepperTick(axis);
    TEST_ASSERT_EQUAL_INT32(INT32_MIN, axis.stepCount);
}

// ─────────────────────────────────────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────────────────────────────────────

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_velocity_interval_math);
    RUN_TEST(test_positive_velocity_dir_high);
    RUN_TEST(test_negative_velocity_dir_low);
    RUN_TEST(test_min_interval_clamp);
    RUN_TEST(test_zero_velocity_no_steps);
    RUN_TEST(test_step_count_increments);
    RUN_TEST(test_step_count_decrements);
    RUN_TEST(test_velocity_update_preserves_state);
    RUN_TEST(test_step_count_overflow_clamp_positive);
    RUN_TEST(test_step_count_overflow_clamp_negative);
    return UNITY_END();
}
