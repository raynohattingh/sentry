/**
 * @file lrf.cpp
 * @brief Laser Range Finder (LRF) driver implementation.
 *
 * See lrf.h for protocol specification and API documentation.
 */

#ifndef NATIVE_ENV
#  include <Arduino.h>
#endif

#include "lrf.h"
#include "config.h"

#include <string.h>

// ─────────────────────────────────────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Verify sync bytes, STA byte, and checksum of a complete 8-byte frame. */
static bool frameValid(const uint8_t buf[8]) {
    // Sync bytes
    if (buf[0] != LRF_SYNC_H || buf[1] != LRF_SYNC_L) return false;
    // STA byte — 0x00 means valid ranging
    if (buf[2] != 0x00) return false;
    // Checksum: sum of bytes [2..6] & 0xFF must equal byte[7]
    uint8_t ck = 0;
    for (uint8_t i = 2; i <= 6; ++i) ck += buf[i];
    return ck == buf[7];
}

/** @brief Extract distance in metres from a validated 8-byte frame.
 *  Bytes [3..6] encode the distance in millimetres as a big-endian uint32_t. */
static float extractDistanceM(const uint8_t buf[8]) {
    uint32_t mm = (static_cast<uint32_t>(buf[3]) << 24) |
                  (static_cast<uint32_t>(buf[4]) << 16) |
                  (static_cast<uint32_t>(buf[5]) <<  8) |
                  (static_cast<uint32_t>(buf[6]));
    return static_cast<float>(mm) / 1000.0f;
}

/** @brief Drive the enable signal to the requested power state. */
static void applyPowerState(LrfPowerControl& control, bool enabled) {
    if (control.digitalWriteFn != nullptr) {
        control.digitalWriteFn(control.pin,
                               enabled ? control.activeLevel : control.inactiveLevel);
    }
    control.enabled = enabled;
}

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

void lrfInit(LrfReader& reader) {
    memset(reader.buf, 0, sizeof(reader.buf));
    reader.idx    = 0;
    reader.active = false;
}

void lrfPowerInit(LrfPowerControl& control,
                  uint8_t pin,
                  uint8_t activeLevel,
                  uint8_t inactiveLevel,
                  LrfPinModeFn pinModeFn,
                  LrfDigitalWriteFn digitalWriteFn) {
    control.pin = pin;
    control.activeLevel = activeLevel;
    control.inactiveLevel = inactiveLevel;
    control.measurementStartMs = 0;
    control.measurementActive = false;
    control.pinModeFn = pinModeFn;
    control.digitalWriteFn = digitalWriteFn;

    if (control.pinModeFn != nullptr) {
        control.pinModeFn(control.pin, OUTPUT);
    }

    applyPowerState(control, false);
}

void lrfTrigger(Stream& serial) {
    serial.write(LRF_TRIGGER, LRF_FRAME_LEN);
}

void lrfBeginMeasurement(Stream& serial,
                         LrfReader& reader,
                         LrfPowerControl& control,
                         unsigned long nowMs) {
    lrfInit(reader);
    control.measurementActive = true;
    control.measurementStartMs = nowMs;
    applyPowerState(control, true);
    delay(1);  // 1 ms settling time after power-on before issuing trigger.
    lrfTrigger(serial);
}

void lrfEndMeasurement(LrfReader& reader, LrfPowerControl& control) {
    lrfInit(reader);
    control.measurementActive = false;
    control.measurementStartMs = 0;
    applyPowerState(control, false);
}

bool lrfMeasurementTimedOut(const LrfPowerControl& control, unsigned long nowMs) {
    return control.measurementActive &&
           ((nowMs - control.measurementStartMs) >= LRF_READ_TIMEOUT_MS);
}

float lrfFeedByte(LrfReader& reader, uint8_t byte) {
    // Wait for sync header before accepting bytes.
    if (!reader.active) {
        if (reader.idx == 0 && byte == LRF_SYNC_H) {
            reader.buf[reader.idx++] = byte;
        } else if (reader.idx == 1 && byte == LRF_SYNC_L) {
            reader.buf[reader.idx++] = byte;
            reader.active = true;
        } else {
            // Unexpected byte before sync — reset accumulator.
            reader.idx = 0;
        }
        return -2.0f;
    }

    // Accumulate remaining bytes.
    reader.buf[reader.idx++] = byte;

    if (reader.idx < LRF_FRAME_LEN) {
        return -2.0f;  // Still accumulating.
    }

    // Frame complete — validate and extract distance.
    const bool valid = frameValid(reader.buf);

    // Reset for next frame.
    reader.idx    = 0;
    reader.active = false;

    if (!valid) return -1.0f;
    return extractDistanceM(reader.buf);
}
