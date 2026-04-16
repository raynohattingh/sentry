/**
 * @file config.h
 * @brief Central configuration block for the Sentry Turret firmware.
 *
 * ALL hardware pin assignments, timing constants, protocol byte sequences,
 * and platform-specific API macros are defined here. No pin numbers, timing
 * literals, or platform-specific API calls appear in any logic file.
 *
 * Porting to a new platform (ESP32, Teensy 4.0) requires only changes in
 * this file — the logic layer is platform-neutral (NFR-004/NFR-005).
 *
 * CNC Shield V3 is the current carrier board. Pin assignments reflect the
 * physical header positions of that shield on an Arduino Uno R3.
 */

#pragma once

#include <stdint.h>

// ─────────────────────────────────────────────────────────────────────────────
// Common digital signal levels (Arduino-compatible numeric values)
// ─────────────────────────────────────────────────────────────────────────────

static constexpr uint8_t SIGNAL_LEVEL_LOW  = 0;
static constexpr uint8_t SIGNAL_LEVEL_HIGH = 1;

// ─────────────────────────────────────────────────────────────────────────────
// Serial Communication
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Baud rate for the Jetson USB/CDC link (UART0 / Serial).
 *  Units: bits/second. Valid range: standard UART baud rates. Default: 115200. */
static constexpr uint32_t JETSON_BAUD = 115200;

/** @brief Size of the line-accumulator buffer for incoming Jetson commands.
 *  Units: bytes. Valid range: 16–255. Default: 64.
 *  A line longer than (SERIAL_LINE_BUF_LEN - 1) bytes is discarded (FR-004). */
static constexpr uint8_t SERIAL_LINE_BUF_LEN = 64;

// ─────────────────────────────────────────────────────────────────────────────
// Motor / Stepper Driver (CNC Shield V3 — A4988 / DRV8825 compatible)
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Pan axis STEP pulse pin — CNC Shield V3 X-axis driver slot.
 *  Units: Arduino digital pin number. Default: 2 (D2). */
static constexpr uint8_t PAN_STEP_PIN = 2;

/** @brief Pan axis DIR (direction) pin — CNC Shield V3 X-axis driver slot.
 *  Units: Arduino digital pin number. Default: 5 (D5).
 *  HIGH = positive (right); LOW = negative (left). */
static constexpr uint8_t PAN_DIR_PIN = 5;

/** @brief Tilt axis STEP pulse pin — CNC Shield V3 Y-axis driver slot.
 *  Units: Arduino digital pin number. Default: 3 (D3). */
static constexpr uint8_t TILT_STEP_PIN = 3;

/** @brief Tilt axis DIR (direction) pin — CNC Shield V3 Y-axis driver slot.
 *  Units: Arduino digital pin number. Default: 6 (D6).
 *  HIGH = positive (up); LOW = negative (down). */
static constexpr uint8_t TILT_DIR_PIN = 6;

/** @brief Shared stepper driver enable pin — CNC Shield V3 D8 (active-LOW).
 *  Units: Arduino digital pin number. Default: 8 (D8).
 *  Driven LOW once in setup() and held LOW permanently (always-enabled).
 *  Pulling HIGH disables all drivers simultaneously. */
static constexpr uint8_t STEPPER_ENABLE_PIN = 8;

/** @brief Velocity-to-step-interval scale factor.
 *  stepIntervalUs = VELOCITY_SCALE_FACTOR / |velocity|
 *  Units: microseconds × speed-units. Valid range: > 0. Default: 1000.0. */
static constexpr float VELOCITY_SCALE_FACTOR = 1000.0f;

/** @brief Minimum step interval — maximum step frequency clamp (FR-014).
 *  stepIntervalUs is never set below this value.
 *  Units: microseconds. Valid range: 100–10000. Default: 200 (= 5000 steps/sec). */
static constexpr uint16_t MIN_STEP_INTERVAL_US = 200;

/** @brief Maximum step interval — anything slower is treated as stopped.
 *  Prevents near-zero velocities from producing extremely long (multi-second)
 *  inter-step delays that could appear as a locked-up axis.
 *  Units: microseconds. Default: 1000000 (1 second). */
static constexpr uint32_t MAX_STEP_INTERVAL_US = 1000000;

// ─────────────────────────────────────────────────────────────────────────────
// Limit Switches (Normally-Open, active-LOW via INPUT_PULLUP)
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Pan-left limit switch — CNC Shield V3 X_Limit header (D9).
 *  Units: Arduino digital pin number. Default: 9. */
static constexpr uint8_t LIMIT_PAN_LEFT_PIN = 9;

/** @brief Pan-right limit switch — CNC Shield V3 Y_Limit header (D10).
 *  Units: Arduino digital pin number. Default: 10. */
static constexpr uint8_t LIMIT_PAN_RIGHT_PIN = 10;

/** @brief Tilt-down limit switch — CNC Shield V3 Z_Limit header (D11).
 *  Gravity-critical safety stop; uses shielded header.
 *  Units: Arduino digital pin number. Default: 11. */
static constexpr uint8_t LIMIT_TILT_DOWN_PIN = 11;

/** @brief Tilt-up limit switch — Arduino header pin D12 (off-shield).
 *  Accessed via pass-through/solder point beneath the CNC Shield.
 *  Units: Arduino digital pin number. Default: 12. */
static constexpr uint8_t LIMIT_TILT_UP_PIN = 12;

/** @brief Debounce window: pin must be continuously LOW for this duration
 *  before a limit trigger is confirmed (FR-008).
 *  Units: milliseconds. Valid range: 1–50. Default: 5. */
static constexpr uint8_t LIMIT_DEBOUNCE_MS = 5;

/** @brief Number of consecutive HIGH samples required before a triggered
 *  limit switch transitions back to IDLE.  Prevents a single spurious
 *  HIGH sample (e.g. from vibration) from prematurely releasing the gate.
 *  Units: samples (loop iterations). Valid range: 1–10. Default: 3. */
static constexpr uint8_t LIMIT_RELEASE_DEBOUNCE_COUNT = 3;

// ─────────────────────────────────────────────────────────────────────────────
// Laser Range Finder (LRF) — SoftwareSerial on A0/A1 (D14/D15)
// ─────────────────────────────────────────────────────────────────────────────

/** @brief LRF SoftwareSerial RX pin — Arduino analog A0 used as digital GPIO.
 *  Load-free; not used by CNC Shield V3.
 *  Units: Arduino digital pin number. Default: 14 (= A0 on Uno R3). */
static constexpr uint8_t LRF_RX_PIN = 14;

/** @brief LRF SoftwareSerial TX pin — Arduino analog A1 used as digital GPIO.
 *  Load-free; not used by CNC Shield V3.
 *  Units: Arduino digital pin number. Default: 15 (= A1 on Uno R3). */
static constexpr uint8_t LRF_TX_PIN = 15;

/** @brief LRF enable pin — Arduino analog A2 used as digital GPIO.
 *  Active-LOW: driving this pin LOW powers the LRF on for a ranging window.
 *  Units: Arduino digital pin number. Default: 16 (= A2 on Uno R3). */
static constexpr uint8_t LRF_ENABLE_PIN = 16;

/** @brief Logical level that powers the LRF on.
 *  LOW is the documented active level for the attached LRF module. */
static constexpr uint8_t LRF_ENABLE_ACTIVE_LEVEL = SIGNAL_LEVEL_LOW;

/** @brief Logical level that deasserts LRF power while idle.
 *  HIGH keeps the LRF disabled when no measurement is active. */
static constexpr uint8_t LRF_ENABLE_INACTIVE_LEVEL = SIGNAL_LEVEL_HIGH;

/** @brief Baud rate for the LRF SoftwareSerial link.
 *  CONSTRAINT-001: 115200 baud is at the upper reliability limit of
 *  AVR SoftwareSerial. If framing errors are observed during hardware testing,
 *  reduce to 57600 — no logic changes required (NFR-004/NFR-006).
 *  Units: bits/second. Default: 115200. */
static constexpr uint32_t LRF_SOFTSERIAL_BAUD = 115200;

/** @brief Expected length of one complete LRF binary response frame.
 *  Units: bytes. Default: 8 (fixed by LRF protocol). */
static constexpr uint8_t LRF_FRAME_LEN = 8;

/** @brief LRF frame sync byte 1 (first byte of every send/reply frame).
 *  Default: 0x55. */
static constexpr uint8_t LRF_SYNC_H = 0x55;

/** @brief LRF frame sync byte 2 (second byte of every send/reply frame).
 *  Default: 0xAA. */
static constexpr uint8_t LRF_SYNC_L = 0xAA;

/** @brief Single-ranging trigger frame sent over SoftwareSerial TX (FR-019).
 *  Bytes: 55 AA 88 FF FF FF FF 84
 *  Checksum: (0x88+0xFF+0xFF+0xFF+0xFF) & 0xFF = 0x84. */
static constexpr uint8_t LRF_TRIGGER[LRF_FRAME_LEN] = {
    0x55, 0xAA, 0x88, 0xFF, 0xFF, 0xFF, 0xFF, 0x84
};

/** @brief Maximum time to wait for a complete 8-byte LRF reply frame (FR-021).
 *  On timeout the firmware emits DIST -1.0\n and resumes normal operation.
 *  Units: milliseconds. Valid range: 50–500. Default: 100. */
static constexpr uint16_t LRF_READ_TIMEOUT_MS = 100;

/** @brief Maximum time to wait for the LRF boot self-test frame in setup() (FR-028).
 *  Some module revisions do not emit a boot frame on success; timeout is non-fatal.
 *  Units: milliseconds. Valid range: 200–2000. Default: 500. */
static constexpr uint16_t LRF_BOOT_TIMEOUT_MS = 500;

// ─────────────────────────────────────────────────────────────────────────────
// Heartbeat
// ─────────────────────────────────────────────────────────────────────────────

/** @brief Interval between POS heartbeat broadcasts (FR-006).
 *  Units: milliseconds. Valid range: 50–1000. Default: 100. */
static constexpr uint16_t HEARTBEAT_INTERVAL_MS = 100;

// ─────────────────────────────────────────────────────────────────────────────
// Watchdog Timer (WDT) — Platform portability macros (NFR-004/NFR-005)
//
// <avr/wdt.h> is included here — the ONLY place platform-specific WDT API
// appears. Logic files call WDT_ENABLE() and WDT_RESET() exclusively.
// To port to ESP32 or Teensy 4.0, replace the macro bodies below.
// ─────────────────────────────────────────────────────────────────────────────

#ifndef NATIVE_ENV
#  include <avr/wdt.h>
/** @brief Enable the hardware WDT with a 2-second timeout.
 *  Call as the LAST statement of setup() (NFR-001). */
#  define WDT_ENABLE()  wdt_enable(WDTO_2S)
/** @brief Reset (pet) the hardware WDT. Call as the FIRST statement of loop() (NFR-002). */
#  define WDT_RESET()   wdt_reset()
#else
// Native test environment — WDT is a no-op.
#  define WDT_ENABLE()  ((void)0)
#  define WDT_RESET()   ((void)0)
#endif
