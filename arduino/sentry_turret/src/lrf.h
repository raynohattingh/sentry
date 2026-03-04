/**
 * @file lrf.h
 * @brief Laser Range Finder (LRF) driver — demand-triggered binary frame protocol.
 *
 * Protocol overview (8-byte binary frame, big-endian):
 *   Byte[0] = 0x55  (sync H)
 *   Byte[1] = 0xAA  (sync L)
 *   Byte[2] = STA   (0x00 = valid measurement, non-zero = error)
 *   Byte[3..6]      = distance in mm as uint32_t big-endian
 *   Byte[7]         = checksum: sum of Byte[2..6] & 0xFF
 *
 * Design constraints:
 *   - lrfTrigger() accepts a Stream& parameter to allow native unit testing
 *     without instantiating SoftwareSerial on the host (M5 remediation).
 *   - lrfFeedByte() returns one of three values: ≥0.0 success, -1.0 failure,
 *     -2.0 still accumulating.  Caller MUST handle all three.
 *   - CONSTRAINT-001 (in sentry_turret.ino): SoftwareSerial at 115200 baud
 *     causes ~695 µs interrupt blackout per 8-byte frame. Using demand-driven
 *     (not continuous) ranging and frame validation mitigates this risk.
 *     If framing errors are observed during HITL testing, reduce LRF_SOFTSERIAL_BAUD
 *     to 57600 — no logic changes required (NFR-004/NFR-006).
 */

#pragma once

#include <stdint.h>

// ─────────────────────────────────────────────────────────────────────────────
// Platform-portable Stream abstraction
// ─────────────────────────────────────────────────────────────────────────────

#ifndef NATIVE_ENV
#  include <Arduino.h>   // Provides Stream
#else
// Minimal Stream interface for native unit tests.
#  include <stddef.h>
class Stream {
public:
    virtual ~Stream() = default;
    virtual int  available() = 0;
    virtual int  read()      = 0;
    virtual void write(const uint8_t* buf, size_t len) = 0;
};
#endif

// ─────────────────────────────────────────────────────────────────────────────
// Data model
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Mutable accumulator state for one LRF reader instance.
 *
 * Declare one instance globally in the .ino.
 */
struct LrfReader {
    uint8_t  buf[8];   ///< Byte accumulation buffer (LRF_FRAME_LEN)
    uint8_t  idx;      ///< Current write index into buf
    bool     active;   ///< True while accumulating a frame in progress
};

// ─────────────────────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Initialise an LrfReader struct. Call once in setup().
 * @param[out] reader  Reader to initialise.
 */
void lrfInit(LrfReader& reader);

/**
 * @brief Send the single-ranging trigger frame over the LRF serial link.
 *
 * Takes a Stream& to allow native unit testing without SoftwareSerial.
 *
 * @param[in] serial  The serial stream connected to the LRF TX line.
 */
void lrfTrigger(Stream& serial);

/**
 * @brief Feed one byte from the LRF SoftwareSerial into the frame accumulator.
 *
 * Return values — caller MUST handle all three:
 *   ≥0.0  Valid distance in metres (frame fully received and checksum OK).
 *   -1.0  Frame error: checksum failure, STA byte non-zero, or accumulator reset.
 *         Caller should emit "DIST -1.0\n" to Jetson.
 *   -2.0  Still accumulating — no action required this call.
 *
 * @param[in,out] reader  Accumulator state.
 * @param[in]     byte    Incoming byte from the LRF serial stream.
 * @return Distance in metres (≥0.0), -1.0 (error), or -2.0 (accumulating).
 */
float lrfFeedByte(LrfReader& reader, uint8_t byte);
