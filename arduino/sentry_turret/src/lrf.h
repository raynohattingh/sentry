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

/** @brief Function pointer for setting a pin mode in a host-testable way.
 *  @param[in] pin   Arduino pin number to configure.
 *  @param[in] mode  Pin mode value (for example OUTPUT). */
using LrfPinModeFn = void (*)(uint8_t pin, uint8_t mode);

/** @brief Function pointer for driving a digital pin in a host-testable way.
 *  @param[in] pin    Arduino pin number to drive.
 *  @param[in] level  Logical output level to apply. */
using LrfDigitalWriteFn = void (*)(uint8_t pin, uint8_t level);

/**
 * @brief Mutable power-control state for the LRF enable signal.
 *
 * This keeps power gating logic encapsulated in the LRF module while still
 * allowing native tests to inject mock pin-control functions.
 */
struct LrfPowerControl {
    uint8_t           pin;                 ///< Pin used to drive the LRF enable signal.
    uint8_t           activeLevel;         ///< Level that powers the LRF on.
    uint8_t           inactiveLevel;       ///< Level that powers the LRF off.
    bool              enabled;             ///< True when the active power level is asserted.
    bool              measurementActive;   ///< True while a ranging window is in progress.
    unsigned long     measurementStartMs;  ///< Timestamp when the current window began.
    LrfPinModeFn      pinModeFn;           ///< Injected pinMode implementation.
    LrfDigitalWriteFn digitalWriteFn;      ///< Injected digitalWrite implementation.
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
 * @brief Configure the LRF enable control and force it to the idle-disabled state.
 *
 * @param[out] control          Power-control state to initialise.
 * @param[in]  pin              Pin used for the enable signal.
 * @param[in]  activeLevel      Logical level that powers the LRF on.
 * @param[in]  inactiveLevel    Logical level that powers the LRF off.
 * @param[in]  pinModeFn        Hardware or mock function used to configure the pin.
 * @param[in]  digitalWriteFn   Hardware or mock function used to drive the pin.
 */
void lrfPowerInit(LrfPowerControl& control,
                  uint8_t pin,
                  uint8_t activeLevel,
                  uint8_t inactiveLevel,
                  LrfPinModeFn pinModeFn,
                  LrfDigitalWriteFn digitalWriteFn);

/**
 * @brief Send the single-ranging trigger frame over the LRF serial link.
 *
 * Takes a Stream& to allow native unit testing without SoftwareSerial.
 *
 * @param[in] serial  The serial stream connected to the LRF TX line.
 */
void lrfTrigger(Stream& serial);

/**
 * @brief Start a new measurement window by enabling power, resetting the reader,
 *        and sending the trigger frame.
 *
 * Repeated calls restart the measurement window and preserve the demand-driven
 * `CMD_LASER` workflow.
 *
 * @param[in]     serial   Serial stream connected to the LRF.
 * @param[in,out] reader   Frame accumulator to reset for the new measurement.
 * @param[in,out] control  Power-control state to update.
 * @param[in]     nowMs    Current `millis()` timestamp.
 */
void lrfBeginMeasurement(Stream& serial,
                         LrfReader& reader,
                         LrfPowerControl& control,
                         unsigned long nowMs);

/**
 * @brief End the current measurement window and return the LRF to idle-disabled.
 *
 * @param[in,out] reader   Frame accumulator to reset.
 * @param[in,out] control  Power-control state to update.
 */
void lrfEndMeasurement(LrfReader& reader, LrfPowerControl& control);

/**
 * @brief Check whether the current measurement window has exceeded the timeout.
 *
 * @param[in] control  Power-control state to inspect.
 * @param[in] nowMs    Current `millis()` timestamp.
 * @return True if an active measurement window has timed out.
 */
bool lrfMeasurementTimedOut(const LrfPowerControl& control, unsigned long nowMs);

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
