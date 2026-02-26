/**
 * @file test_serial_proto/test_main.cpp
 * @brief Unity unit tests for serial_proto — Jetson ASCII command parser.
 *
 * Tests target the native PlatformIO environment (NATIVE_ENV defined).
 * No Arduino hardware is required.
 */

#include <unity.h>
#include "serial_proto.h"
#include "serial_proto.cpp"  // Direct inclusion for native single-TU test build

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/** Feed a C-string byte-by-byte through the parser; return the last non-CMD_NONE result. */
static int8_t feedString(SerialProtoState& s, const char* str) {
    int8_t result = CMD_NONE;
    for (const char* p = str; *p != '\0'; ++p) {
        int8_t r = serialProtoFeed(s, static_cast<uint8_t>(*p));
        if (r != CMD_NONE) result = r;
    }
    return result;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

/** Velocity command: positive pan, negative tilt. */
void test_velocity_parse_basic(void) {
    SerialProtoState s{};
    serialProtoInit(s);
    int8_t cmd = feedString(s, "V 100.0 -50.0\n");
    TEST_ASSERT_EQUAL_INT8(CMD_VELOCITY, cmd);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 100.0f, s.panSpeed);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -50.0f, s.tiltSpeed);
}

/** Velocity command: both negative values. */
void test_velocity_parse_negative_both(void) {
    SerialProtoState s{};
    serialProtoInit(s);
    int8_t cmd = feedString(s, "V -30.5 -75.25\n");
    TEST_ASSERT_EQUAL_INT8(CMD_VELOCITY, cmd);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -30.5f,  s.panSpeed);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -75.25f, s.tiltSpeed);
}

/** Velocity command: zero values (stop command). */
void test_velocity_parse_zero(void) {
    SerialProtoState s{};
    serialProtoInit(s);
    int8_t cmd = feedString(s, "V 0.0 0.0\n");
    TEST_ASSERT_EQUAL_INT8(CMD_VELOCITY, cmd);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, s.panSpeed);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, s.tiltSpeed);
}

/** Laser command: bare "L\n". */
void test_laser_parse(void) {
    SerialProtoState s{};
    serialProtoInit(s);
    int8_t cmd = feedString(s, "L\n");
    TEST_ASSERT_EQUAL_INT8(CMD_LASER, cmd);
}

/** Unknown command: unrecognised prefix. */
void test_unknown_command(void) {
    SerialProtoState s{};
    serialProtoInit(s);
    int8_t cmd = feedString(s, "Z 1 2\n");
    TEST_ASSERT_EQUAL_INT8(CMD_UNKNOWN, cmd);
}

/** Buffer overflow: a line longer than SERIAL_LINE_BUF_LEN must be discarded
 *  and a subsequent valid command must be parsed correctly. */
void test_buffer_overflow_discards_line(void) {
    SerialProtoState s{};
    serialProtoInit(s);

    // Build an oversized line (SERIAL_LINE_BUF_LEN is 64; send 80 chars + newline)
    const char* longLine = "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV\n";
    feedString(s, longLine);

    // After overflow the parser should cleanly accept the next valid command.
    int8_t cmd = feedString(s, "L\n");
    TEST_ASSERT_EQUAL_INT8(CMD_LASER, cmd);
}

/** Windows CRLF line endings must be handled transparently. */
void test_crlf_line_ending(void) {
    SerialProtoState s{};
    serialProtoInit(s);
    int8_t cmd = feedString(s, "V 10.0 20.0\r\n");
    TEST_ASSERT_EQUAL_INT8(CMD_VELOCITY, cmd);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 10.0f, s.panSpeed);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 20.0f, s.tiltSpeed);
}

/** Consecutive commands: parser state resets correctly after each newline. */
void test_consecutive_commands(void) {
    SerialProtoState s{};
    serialProtoInit(s);

    int8_t cmd1 = feedString(s, "V 1.0 2.0\n");
    TEST_ASSERT_EQUAL_INT8(CMD_VELOCITY, cmd1);

    int8_t cmd2 = feedString(s, "L\n");
    TEST_ASSERT_EQUAL_INT8(CMD_LASER, cmd2);
}

// ─────────────────────────────────────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────────────────────────────────────

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_velocity_parse_basic);
    RUN_TEST(test_velocity_parse_negative_both);
    RUN_TEST(test_velocity_parse_zero);
    RUN_TEST(test_laser_parse);
    RUN_TEST(test_unknown_command);
    RUN_TEST(test_buffer_overflow_discards_line);
    RUN_TEST(test_crlf_line_ending);
    RUN_TEST(test_consecutive_commands);
    return UNITY_END();
}
