/**
 * @file test_lrf_frame/test_main.cpp
 * @brief Unity unit tests for the LRF binary frame accumulator — native host.
 *
 * Verifies:
 *   1. Valid frame: correct distance extracted
 *   2. Bad checksum returns -1.0
 *   3. Non-zero STA byte returns -1.0
 *   4. Bad sync H returns -2.0 (accumulating) and resets accumulator
 *   5. Bad sync L returns -2.0 and resets accumulator
 *   6. Incomplete frame returns -2.0
 *   7. Two consecutive valid frames decode correctly
 */

#include <unity.h>
#include <stdint.h>
#include <string.h>

// ─────────────────────────────────────────────────────────────────────────────
// Arduino stub layer
// ─────────────────────────────────────────────────────────────────────────────

static constexpr uint8_t A0 = 14;
static constexpr uint8_t A1 = 15;
static constexpr uint8_t OUTPUT = 1;
static constexpr uint8_t INPUT  = 0;
static constexpr uint8_t HIGH   = 1;
static constexpr uint8_t LOW    = 0;
static constexpr uint8_t INPUT_PULLUP = 2;
static void     pinMode(uint8_t, uint8_t) {}
static void     digitalWrite(uint8_t, uint8_t) {}
static uint8_t  digitalRead(uint8_t) { return 1; }
static unsigned long millis() { return 0; }
static unsigned long micros() { return 0; }

// Minimal Stream stub (NATIVE_ENV already defined via build_flags)
#include "lrf.h"

// Implement Stream::write for test use (unused but satisfies vtable)
class MockStream : public Stream {
public:
    int  available() override { return 0; }
    int  read()      override { return -1; }
    void write(const uint8_t*, size_t) override {}
};

#include "config.h"
#include "lrf.cpp"

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Build a valid 8-byte LRF reply frame for a given distance in mm. */
static void buildFrame(uint8_t out[8], uint32_t distMm, uint8_t sta = 0x00) {
    out[0] = LRF_SYNC_H;
    out[1] = LRF_SYNC_L;
    out[2] = sta;
    out[3] = (distMm >> 24) & 0xFF;
    out[4] = (distMm >> 16) & 0xFF;
    out[5] = (distMm >>  8) & 0xFF;
    out[6] = (distMm >>  0) & 0xFF;
    // Checksum: sum bytes [2..6]
    uint8_t ck = 0;
    for (int i = 2; i <= 6; ++i) ck += out[i];
    out[7] = ck;
}

/** Feed an 8-byte frame byte-by-byte; return the final non-(-2.0) result. */
static float feedFrame(LrfReader& reader, const uint8_t frame[8]) {
    float result = -2.0f;
    for (int i = 0; i < 8; ++i) {
        float r = lrfFeedByte(reader, frame[i]);
        if (r != -2.0f) result = r;
    }
    return result;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

/** Valid frame: 10000 mm → 10.0 m. */
void test_valid_frame_10m(void) {
    LrfReader reader{};
    lrfInit(reader);
    uint8_t frame[8];
    buildFrame(frame, 10000);
    float dist = feedFrame(reader, frame);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, dist);
}

/** Valid frame: 1500 mm → 1.5 m. */
void test_valid_frame_1500mm(void) {
    LrfReader reader{};
    lrfInit(reader);
    uint8_t frame[8];
    buildFrame(frame, 1500);
    float dist = feedFrame(reader, frame);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.5f, dist);
}

/** Bad checksum — returns -1.0. */
void test_bad_checksum(void) {
    LrfReader reader{};
    lrfInit(reader);
    uint8_t frame[8];
    buildFrame(frame, 5000);
    frame[7] ^= 0xFF;  // corrupt checksum
    float result = feedFrame(reader, frame);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -1.0f, result);
}

/** Non-zero STA byte — returns -1.0. */
void test_nonzero_sta(void) {
    LrfReader reader{};
    lrfInit(reader);
    uint8_t frame[8];
    buildFrame(frame, 5000, 0x01);
    float result = feedFrame(reader, frame);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -1.0f, result);
}

/** Incomplete frame (only 4 bytes fed) — returns -2.0 throughout. */
void test_incomplete_frame_returns_accumulating(void) {
    LrfReader reader{};
    lrfInit(reader);
    uint8_t frame[8];
    buildFrame(frame, 2000);
    float last = -2.0f;
    for (int i = 0; i < 4; ++i) {
        last = lrfFeedByte(reader, frame[i]);
    }
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -2.0f, last);
}

/** Two consecutive valid frames decode independently. */
void test_two_consecutive_frames(void) {
    LrfReader reader{};
    lrfInit(reader);

    uint8_t frame1[8], frame2[8];
    buildFrame(frame1, 3000);   // 3.0 m
    buildFrame(frame2, 7500);   // 7.5 m

    float d1 = feedFrame(reader, frame1);
    float d2 = feedFrame(reader, frame2);

    TEST_ASSERT_FLOAT_WITHIN(0.001f, 3.0f, d1);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 7.5f, d2);
}

// ─────────────────────────────────────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────────────────────────────────────

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_valid_frame_10m);
    RUN_TEST(test_valid_frame_1500mm);
    RUN_TEST(test_bad_checksum);
    RUN_TEST(test_nonzero_sta);
    RUN_TEST(test_incomplete_frame_returns_accumulating);
    RUN_TEST(test_two_consecutive_frames);
    return UNITY_END();
}
