/**
 * @file serial_proto.h
 * @brief Jetson ↔ Arduino ASCII serial protocol — parser and command dispatcher.
 *
 * Inbound protocol (Jetson → Arduino):
 *   V <pan_speed> <tilt_speed>\\n   — velocity move command
 *   L\\n                            — fire laser range-finder
 *
 * Outbound protocol (Arduino → Jetson):
 *   DIST <metres>\\n                — LRF distance result  (≥0.0 = valid, -1.0 = timeout)
 *   POS <pan_steps> <tilt_steps>\\n — heartbeat position broadcast
 */

#pragma once

#include <stdint.h>
#include "config.h"

// ─────────────────────────────────────────────────────────────────────────────
// Command codes returned by serialProtoParse
// ─────────────────────────────────────────────────────────────────────────────

/** @brief No complete line available yet. */
static constexpr int8_t CMD_NONE   =  0;
/** @brief Velocity command parsed. Fields: cmdPanSpeed, cmdTiltSpeed. */
static constexpr int8_t CMD_VELOCITY = 1;
/** @brief Laser trigger command parsed. No extra fields. */
static constexpr int8_t CMD_LASER  = 2;
/** @brief Line received but unrecognised. Caller should ignore. */
static constexpr int8_t CMD_UNKNOWN = -1;

// ─────────────────────────────────────────────────────────────────────────────
// State held by the parser (opaque to callers)
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Mutable parser state. Declare one instance globally in the .ino. */
struct SerialProtoState {
    char     buf[SERIAL_LINE_BUF_LEN]; ///< Line accumulation buffer
    uint8_t  head;      ///< Write index into buf
    bool     overflow;  ///< True when a line exceeded buf capacity (discarded)
    float    panSpeed;  ///< Parsed pan velocity (valid when CMD_VELOCITY returned)
    float    tiltSpeed; ///< Parsed tilt velocity (valid when CMD_VELOCITY returned)
};

// ─────────────────────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Initialise the parser state. Call once in setup().
 * @param[out] s  Parser state to initialise.
 */
void serialProtoInit(SerialProtoState& s);

/**
 * @brief Feed one byte from the inbound stream into the line accumulator.
 *
 * When a newline ('\\n') terminates a complete line the function parses it and
 * returns the appropriate CMD_* code.  All other bytes return CMD_NONE.
 *
 * Buffer-overflow protection (FR-004): if a line reaches SERIAL_LINE_BUF_LEN-1
 * bytes without a newline, the accumulator is flushed and the line discarded;
 * subsequent bytes of the same line are also discarded until the next '\\n'.
 *
 * @param[in,out] s     Parser state.
 * @param[in]     byte  The incoming byte.
 * @return CMD_VELOCITY, CMD_LASER, CMD_UNKNOWN, or CMD_NONE.
 */
int8_t serialProtoFeed(SerialProtoState& s, uint8_t byte);
