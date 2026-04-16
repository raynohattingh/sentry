/**
 * @file serial_proto.cpp
 * @brief Jetson ↔ Arduino ASCII serial protocol implementation.
 *
 * See serial_proto.h for protocol specification and API documentation.
 */

#include "serial_proto.h"
#include "config.h"

#include <string.h>
#include <stdlib.h>   // strtof
#include <math.h>     // isnan, isinf

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Reset accumulator to empty without touching parsed-value fields. */
static void flushBuf(SerialProtoState& s) {
    s.head     = 0;
    s.overflow = false;
    s.buf[0]   = '\0';
}

/** @brief Parse a complete null-terminated line and return the command code. */
static int8_t parseLine(SerialProtoState& s) {
    const char* line = s.buf;

    // --- Velocity: "V <pan> <tilt>" ---
    if (line[0] == 'V' && line[1] == ' ') {
        char* endPtr1 = nullptr;
        char* endPtr2 = nullptr;
        const char* p = line + 2;

        float pan = strtof(p, &endPtr1);
        if (endPtr1 == p) return CMD_UNKNOWN;  // no valid float

        float tilt = strtof(endPtr1, &endPtr2);
        if (endPtr2 == endPtr1) return CMD_UNKNOWN;

        // Reject non-finite values — NaN/Inf from malformed input could
        // propagate into stepper math and cause unsafe behaviour (SC-NaN).
        if (isnan(pan) || isinf(pan) || isnan(tilt) || isinf(tilt)) {
            s.panSpeed  = 0.0f;
            s.tiltSpeed = 0.0f;
            return CMD_VELOCITY;
        }

        s.panSpeed  = pan;
        s.tiltSpeed = tilt;
        return CMD_VELOCITY;
    }

    // --- Laser: "L" ---
    if (line[0] == 'L' && (line[1] == '\0' || line[1] == '\r')) {
        return CMD_LASER;
    }

    return CMD_UNKNOWN;
}

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

void serialProtoInit(SerialProtoState& s) {
    s.panSpeed  = 0.0f;
    s.tiltSpeed = 0.0f;
    flushBuf(s);
}

int8_t serialProtoFeed(SerialProtoState& s, uint8_t byte) {
    const char c = static_cast<char>(byte);

    // Discard carriage-returns silently (Windows line endings).
    if (c == '\r') return CMD_NONE;

    if (c == '\n') {
        if (s.overflow) {
            // Line was too long — already flushed; clear overflow flag.
            s.overflow = false;
            return CMD_NONE;
        }
        s.buf[s.head] = '\0';
        int8_t cmd = parseLine(s);
        flushBuf(s);
        return cmd;
    }

    // While in overflow state, discard all bytes until the next newline.
    if (s.overflow) return CMD_NONE;

    // Buffer-overflow protection (FR-004): discard and flag.
    if (s.head >= SERIAL_LINE_BUF_LEN - 1) {
        flushBuf(s);
        s.overflow = true;
        return CMD_NONE;
    }

    s.buf[s.head++] = c;
    return CMD_NONE;
}
