/**
 * @file sentry_turret.ino
 * @brief Sentry Turret Arduino firmware — main orchestrator.
 *
 * Responsibilities:
 *   1. Initialise all hardware modules (Serial, steppers, limit switches, LRF).
 *   2. Feed incoming Jetson bytes through the serial protocol parser each loop().
 *   3. Dispatch parsed commands to the appropriate module.
 *   4. Tick all state-machine modules (stepper, limit switches) every loop().
 *   5. Gate stepper velocity to zero when any limit switch is triggered.
 *   6. Broadcast a POS heartbeat every HEARTBEAT_INTERVAL_MS milliseconds.
 *   7. Enable the Watchdog Timer (WDT) at the end of setup(); reset it at the
 *      start of every loop() to prevent spurious resets (NFR-001/NFR-002).
 *
 * Platform: Arduino Uno R3 + CNC Shield V3 + A4988/DRV8825 stepper drivers.
 *
 * CONSTRAINT-001: SoftwareSerial at 115200 baud causes ~695 µs interrupt
 * blackout per 8-byte LRF frame. Demand-driven ranging (trigger on CMD_LASER
 * only) and binary frame validation mitigate this. If framing errors are
 * observed during HITL testing, reduce LRF_SOFTSERIAL_BAUD to 57600 in
 * config.h — no logic changes required (NFR-004/NFR-006).
 */

#include <SoftwareSerial.h>

#include "config.h"
#include "serial_proto.h"
#include "stepper.h"
#include "limit_switch.h"
#include "lrf.h"

// ─────────────────────────────────────────────────────────────────────────────
// Global state
// ─────────────────────────────────────────────────────────────────────────────

// --- Serial protocol ---
static SerialProtoState protoState;

// --- Stepper axes ---
static StepperAxis panAxis;
static StepperAxis tiltAxis;

// --- Limit switches ---
static LimitPin limitPanLeft;
static LimitPin limitPanRight;
static LimitPin limitTiltDown;
static LimitPin limitTiltUp;

// --- LRF ---
// CONSTRAINT-001: See file-level comment above regarding SoftwareSerial reliability.
static SoftwareSerial lrfSerial(LRF_RX_PIN, LRF_TX_PIN);
static LrfReader      lrfReader;

// --- Heartbeat ---
static unsigned long lastHeartbeatMs = 0;

// ─────────────────────────────────────────────────────────────────────────────
// Helper: gate stepper velocity when any limit switch is triggered (FR-007)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Check limit switches and zero the affected axis velocity if triggered.
 *
 * The direction convention:
 *   Pan  — positive velocity = right; negative = left
 *   Tilt — positive velocity = up;   negative = down
 */
static void applyLimitGates() {
    // Pan-left: stop pan if moving left (negative pan velocity)
    if (limitPanLeft.triggered && panAxis.velocity < 0.0f) {
        stepperSetVelocity(panAxis, 0.0f);
    }
    // Pan-right: stop pan if moving right (positive pan velocity)
    if (limitPanRight.triggered && panAxis.velocity > 0.0f) {
        stepperSetVelocity(panAxis, 0.0f);
    }
    // Tilt-down: stop tilt if moving down (negative tilt velocity)
    if (limitTiltDown.triggered && tiltAxis.velocity < 0.0f) {
        stepperSetVelocity(tiltAxis, 0.0f);
    }
    // Tilt-up: stop tilt if moving up (positive tilt velocity)
    if (limitTiltUp.triggered && tiltAxis.velocity > 0.0f) {
        stepperSetVelocity(tiltAxis, 0.0f);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// setup()
// ─────────────────────────────────────────────────────────────────────────────

void setup() {
    // --- Jetson USB/CDC link ---
    Serial.begin(JETSON_BAUD);
    serialProtoInit(protoState);

    // --- Stepper enable (active-LOW, held permanently) (FR-009a) ---
    // All A4988/DRV8825 drivers share D8. Tilt axis requires continuous hold
    // torque against gravity; therefore the enable line is NEVER de-asserted.
    pinMode(STEPPER_ENABLE_PIN, OUTPUT);
    digitalWrite(STEPPER_ENABLE_PIN, LOW);

    // --- Stepper axes ---
    stepperInit(panAxis,  PAN_STEP_PIN,  PAN_DIR_PIN);
    stepperInit(tiltAxis, TILT_STEP_PIN, TILT_DIR_PIN);

    // --- Limit switches ---
    limitInit(limitPanLeft,  LIMIT_PAN_LEFT_PIN);
    limitInit(limitPanRight, LIMIT_PAN_RIGHT_PIN);
    limitInit(limitTiltDown, LIMIT_TILT_DOWN_PIN);
    limitInit(limitTiltUp,   LIMIT_TILT_UP_PIN);

    // --- LRF SoftwareSerial ---
    lrfSerial.begin(LRF_SOFTSERIAL_BAUD);
    lrfInit(lrfReader);

    // Discard LRF boot self-test frame (FR-028).
    // Some module revisions emit a status frame at power-on; wait briefly and
    // drain any bytes. Non-fatal on timeout.
    {
        const unsigned long bootStart = millis();
        while ((millis() - bootStart) < LRF_BOOT_TIMEOUT_MS) {
            if (lrfSerial.available()) {
                (void)lrfSerial.read();  // Drain boot frame, result ignored.
            }
        }
        lrfInit(lrfReader);  // Reset accumulator to clean state after drain.
    }

    // --- WDT: enable LAST in setup() (NFR-001) ---
    // <avr/wdt.h> is never included here; WDT_ENABLE() is the portable macro
    // defined in config.h (NFR-004/NFR-005).
    WDT_ENABLE();
}

// ─────────────────────────────────────────────────────────────────────────────
// loop()
// ─────────────────────────────────────────────────────────────────────────────

void loop() {
    // --- WDT reset: FIRST statement (NFR-002/NFR-003) ---
    WDT_RESET();

    // ── Serial command processing ────────────────────────────────────────────
    while (Serial.available()) {
        const int8_t cmd = serialProtoFeed(protoState,
                                           static_cast<uint8_t>(Serial.read()));
        switch (cmd) {
            case CMD_VELOCITY:
                // Apply velocity only if the corresponding limit allows it.
                stepperSetVelocity(panAxis,  protoState.panSpeed);
                stepperSetVelocity(tiltAxis, protoState.tiltSpeed);
                // Immediately re-apply limit gates in case we just commanded
                // into a triggered limit.
                applyLimitGates();
                break;

            case CMD_LASER:
                // Send trigger frame; reply bytes arrive asynchronously in
                // subsequent loop() iterations via the lrfSerial byte feed below.
                lrfTrigger(lrfSerial);
                break;

            case CMD_NONE:
            case CMD_UNKNOWN:
            default:
                break;
        }
    }

    // ── LRF reply byte ingestion ─────────────────────────────────────────────
    while (lrfSerial.available()) {
        const float lrfResult = lrfFeedByte(lrfReader,
                                            static_cast<uint8_t>(lrfSerial.read()));
        if (lrfResult >= 0.0f) {
            // Valid distance — report to Jetson.
            Serial.print(F("DIST "));
            Serial.println(lrfResult, 3);
        } else if (lrfResult == -1.0f) {
            // Frame error (checksum failure or non-zero STA) — report failure.
            Serial.println(F("DIST -1.0"));
        }
        // lrfResult == -2.0f → still accumulating; do nothing.
    }

    // ── Limit switch debounce ────────────────────────────────────────────────
    limitTick(limitPanLeft);
    limitTick(limitPanRight);
    limitTick(limitTiltDown);
    limitTick(limitTiltUp);

    // Apply limit gates after ticking (state may have just changed).
    applyLimitGates();

    // ── Stepper step emission ────────────────────────────────────────────────
    stepperTick(panAxis);
    stepperTick(tiltAxis);

    // ── Heartbeat: POS broadcast (FR-006) ────────────────────────────────────
    const unsigned long now = millis();
    if ((now - lastHeartbeatMs) >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatMs = now;
        Serial.print(F("POS "));
        Serial.print(panAxis.stepCount);
        Serial.print(' ');
        Serial.println(tiltAxis.stepCount);
    }
}
