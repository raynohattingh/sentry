# Quickstart: Arduino Firmware — Sentry HAL

**Branch**: `001-arduino-firmware` | **Hardware**: Arduino Uno R3 + CNC Shield V3

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Arduino IDE | ≥ 2.x *or* PlatformIO CLI | Firmware build and upload |
| PlatformIO CLI | ≥ 6.x | Build, upload, and unit tests |
| Python | ≥ 3.x | PlatformIO dependency |
| USB-A to USB-B cable | — | Arduino Uno R3 programming / serial link |

No external Arduino libraries are required. All dependencies (`SoftwareSerial`, `avr/wdt.h`) ship with the Arduino AVR core.

---

## Repository Layout

All firmware source, configuration, and tests live together in one self-contained directory:

```
arduino/sentry_turret/
├── platformio.ini        ← PlatformIO project root (run pio commands from here)
├── sentry_turret.ino     ← Arduino sketch entry point / orchestrator
├── config.h              ← ALL pin assignments and tuning constants live here ONLY
├── serial_proto.h/.cpp   ← Jetson ↔ Arduino ASCII line parser
├── stepper.h/.cpp        ← Non-blocking micros()-based step scheduler
├── limit_switch.h/.cpp   ← INPUT_PULLUP debounce FSM (4 switches)
├── lrf.h/.cpp            ← LRF 8-byte binary frame accumulator
└── test/
    ├── test_serial_proto/test_main.cpp
    ├── test_stepper/test_main.cpp
    ├── test_lrf_frame/test_main.cpp
    └── test_limits/test_main.cpp
```

---

## Step 1 — Configure Hardware Pins

Open `arduino/sentry_turret/config.h`. The defaults match the **CNC Shield V3** carrier board on an Arduino Uno R3. Verify before uploading:

```cpp
// ── Stepper driver (CNC Shield V3) ──────────────────────────────────────────
static constexpr uint8_t PAN_STEP_PIN       = 2;   // X-axis STEP
static constexpr uint8_t PAN_DIR_PIN        = 5;   // X-axis DIR
static constexpr uint8_t TILT_STEP_PIN      = 3;   // Y-axis STEP
static constexpr uint8_t TILT_DIR_PIN       = 6;   // Y-axis DIR
static constexpr uint8_t STEPPER_ENABLE_PIN = 8;   // Shared active-LOW enable

// ── Limit switches (CNC Shield V3 headers + D12 off-shield) ─────────────────
static constexpr uint8_t LIMIT_PAN_LEFT_PIN  = 9;   // X_Limit header
static constexpr uint8_t LIMIT_PAN_RIGHT_PIN = 10;  // Y_Limit header
static constexpr uint8_t LIMIT_TILT_DOWN_PIN = 11;  // Z_Limit header (gravity-critical)
static constexpr uint8_t LIMIT_TILT_UP_PIN   = 12;  // Off-shield Arduino header

// ── LRF SoftwareSerial (A0/A1 used as digital GPIO) ─────────────────────────
static constexpr uint8_t LRF_RX_PIN = A0;  // D14 — LRF TX output → here
static constexpr uint8_t LRF_TX_PIN = A1;  // D15 — LRF RX input  ← here
```

> **Note — D12 (LIMIT_TILT_UP_PIN)**: This pin is not on a CNC Shield V3 header. Run a short wire from the Arduino D12 header pin (accessible beneath or beside the shield) to your tilt-up limit switch.

**Do not scatter hardware configuration across other source files** — `config.h` is the single source of truth.

---

## Step 2 — Build and Upload (Arduino IDE)

1. Open `arduino/sentry_turret/sentry_turret.ino` in Arduino IDE.
2. Select **Board**: `Arduino Uno` and the correct **Port** (e.g., `/dev/ttyUSB0` or `COMx`).
3. Click **Upload** (Ctrl+U / ⌘U).
4. Open **Serial Monitor** at **115200 baud**. You should see `POS 0 0` heartbeat messages every 100 ms.

---

## Step 3 — Build and Upload (PlatformIO CLI)

```bash
cd arduino/sentry_turret
pio run -e uno -t upload --upload-port /dev/ttyUSB0
```

Monitor serial output:
```bash
pio device monitor -e uno --baud 115200
```

---

## Step 4 — Run Unit Tests (No Hardware Required)

Tests run entirely on the host machine (GCC native build via PlatformIO). No Arduino board needed.

```bash
cd arduino/sentry_turret
pio test -e native
```

Expected output:
```
native:test_limits        [PASSED]
native:test_stepper       [PASSED]
native:test_lrf_frame     [PASSED]
native:test_serial_proto  [PASSED]
30 test cases: 30 succeeded
```

---

## Step 5 — Smoke Test Over Serial

With the board connected and Serial Monitor open at **115200 baud**, send the following commands:

**Move motors:**
```
V 100.0 50.0
```
Expected: `POS` messages with increasing step counts; both motors spin.

**Stop motors:**
```
V 0.0 0.0
```
Expected: Both motors stop; `POS` step counts stabilise.

**Fire laser range-finder:**
```
L
```
Expected: `DIST <metres>` if the LRF module is connected; `DIST -1.0` if not wired (timeout after 100 ms — normal during bench testing).

---

## Hardware Wiring Quick Reference (CNC Shield V3)

| Signal | Arduino Pin | CNC Shield Header | Connect to |
|--------|-------------|-------------------|------------|
| Pan STEP | D2 | X-axis STEP | A4988/DRV8825 STEP |
| Pan DIR | D5 | X-axis DIR | A4988/DRV8825 DIR |
| Tilt STEP | D3 | Y-axis STEP | A4988/DRV8825 STEP |
| Tilt DIR | D6 | Y-axis DIR | A4988/DRV8825 DIR |
| Stepper Enable | D8 | EN (shared) | All driver EN pins (active-LOW) |
| Pan Left Limit | D9 | X_Limit header | Switch leg A → pin, leg B → GND |
| Pan Right Limit | D10 | Y_Limit header | Switch leg A → pin, leg B → GND |
| Tilt Down Limit | D11 | Z_Limit header | Switch leg A → pin, leg B → GND |
| Tilt Up Limit | D12 | Off-shield | Switch leg A → pin, leg B → GND |
| LRF RX (Arduino) | A0 (D14) | Free analog pin | LRF TX output wire |
| LRF TX (Arduino) | A1 (D15) | Free analog pin | LRF RX input wire |
| Jetson Serial | USB-B port | — | Jetson USB-A port |

All limit switches: normally-open (NO), no external pull resistor required — `INPUT_PULLUP` is configured in firmware.

> **Enable pin**: `STEPPER_ENABLE_PIN` (D8) is driven LOW once in `setup()` and held permanently. This keeps all stepper drivers engaged at all times — required for the tilt axis to hold torque against gravity when stationary.

---

## Tuning Parameters

All tuning is done exclusively in `config.h`:

| Constant | Default | Effect |
|----------|---------|--------|
| `HEARTBEAT_INTERVAL_MS` | `100` | Milliseconds between `POS` broadcasts; increase to reduce serial bandwidth |
| `VELOCITY_SCALE_FACTOR` | `1000.0f` | `stepIntervalUs = SCALE / |velocity|`; decrease to run faster at the same velocity value |
| `MIN_STEP_INTERVAL_US` | `200` | Minimum µs between steps (maximum frequency clamp); increase for slower drivers |
| `LIMIT_DEBOUNCE_MS` | `5` | Debounce window; increase if switches show noise/chatter |
| `LRF_READ_TIMEOUT_MS` | `100` | Max wait for a complete LRF reply frame; increase if your module is slow |
| `LRF_SOFTSERIAL_BAUD` | `115200` | Reduce to `57600` if SoftwareSerial framing errors occur (no code changes needed) |
| `LRF_BOOT_TIMEOUT_MS` | `500` | Max wait for LRF power-on self-test frame during `setup()` |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| No `POS` output on Serial Monitor | Wrong baud rate | Set monitor to 115200 baud |
| Board resets every ~2 seconds | WDT firing; blocking call in `loop()` | Check for `delay()` or blocking serial reads; none are permitted |
| `DIST -1.0` always returned | LRF wiring wrong or baud mismatch | Verify `LRF_RX_PIN`/`LRF_TX_PIN` in `config.h`; try `LRF_SOFTSERIAL_BAUD = 57600` |
| Motors not moving | Enable pin not LOW | Verify D8 wired to all driver EN pins; check `STEPPER_ENABLE_PIN = 8` in `config.h` |
| Motors moving in wrong direction | DIR polarity inverted for your driver | Invert velocity sign on the Jetson side (`V -100.0 0.0` instead of `V 100.0 0.0`) |
| Limit switch not triggering | Pin wired to VCC instead of GND | Rewire switch leg to GND; `INPUT_PULLUP` is active-LOW |
| Tilt-up limit never triggers | D12 not connected | D12 is off-shield — route a wire to the Arduino D12 header pin beneath the CNC Shield |
| Constant spurious limit triggers on boot | Switch wired as NC (Normally-Closed) | Replace with NO (Normally-Open) switch, or rewire |
