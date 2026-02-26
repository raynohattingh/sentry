# Quickstart: Arduino Firmware — Sentry HAL

**Branch**: `001-arduino-firmware` | **Date**: 2026-02-26

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Arduino IDE | ≥ 2.x *or* PlatformIO CLI | Firmware build and upload |
| PlatformIO CLI | ≥ 6.x | Unit tests (native runner) |
| Python | ≥ 3.x | PlatformIO dependency |
| USB-A to USB-B cable | — | Arduino Uno R3 programming / serial link |

No external Arduino libraries are required. All dependencies (`SoftwareSerial`, `avr/wdt.h`) ship with the Arduino AVR core.

---

## Repository Layout

```
arduino/
└── sentry_turret/
    ├── sentry_turret.ino   ← open this in Arduino IDE, OR use pio run
    ├── config.h            ← edit pin assignments and tuning here ONLY
    ├── stepper.h/cpp
    ├── lrf.h/cpp
    ├── limits.h/cpp
    └── serial_proto.h/cpp

test/
└── arduino/
    ├── platformio.ini
    ├── test_serial_proto.cpp
    ├── test_lrf_frame.cpp
    └── test_limits.cpp
```

---

## Step 1 — Configure Hardware Pins

Open `arduino/sentry_turret/config.h`. Verify or update the pin constants to match your physical wiring before uploading:

```cpp
// Stepper driver step/direction pins
constexpr uint8_t PAN_STEP_PIN  = 2;
constexpr uint8_t PAN_DIR_PIN   = 3;
constexpr uint8_t TILT_STEP_PIN = 4;
constexpr uint8_t TILT_DIR_PIN  = 5;

// Limit switch INPUT_PULLUP pins (wire one leg to pin, other leg to GND)
constexpr uint8_t LIMIT_PAN_LEFT_PIN  = 6;
constexpr uint8_t LIMIT_PAN_RIGHT_PIN = 7;
constexpr uint8_t LIMIT_TILT_UP_PIN   = 8;
constexpr uint8_t LIMIT_TILT_DOWN_PIN = 9;

// LRF SoftwareSerial pins (LRF TX → LRF_RX_PIN, LRF RX ← LRF_TX_PIN)
constexpr uint8_t LRF_RX_PIN = 10;
constexpr uint8_t LRF_TX_PIN = 11;
```

**Do not change any other source files to reconfigure the hardware.**

---

## Step 2 — Build and Upload (Arduino IDE)

1. Open `arduino/sentry_turret/sentry_turret.ino` in Arduino IDE.
2. Select **Board**: `Arduino Uno` and the correct **Port** (e.g., `/dev/ttyUSB0` or `COMx`).
3. Click **Upload** (Ctrl+U / ⌘U).
4. Open **Serial Monitor** at 115200 baud. You should see `POS 0 0` messages every 100 ms.

---

## Step 3 — Build and Upload (PlatformIO CLI)

```bash
cd arduino/sentry_turret
pio run --target upload --upload-port /dev/ttyUSB0
```

Monitor output:
```bash
pio device monitor --baud 115200
```

---

## Step 4 — Run Unit Tests (No Hardware Required)

```bash
cd test/arduino
pio test -e native
```

Expected output:
```
test/arduino/test_serial_proto.cpp   [PASSED]
test/arduino/test_lrf_frame.cpp      [PASSED]
test/arduino/test_limits.cpp         [PASSED]
```

Tests run on the host machine using GCC (GNU Compiler Collection); no Arduino board is needed.

---

## Step 5 — Smoke Test Over Serial

With the board connected and the Serial Monitor open at 115200 baud, send:

```
V 100.0 50.0
```

You should observe: `POS` messages with increasing step counts; both motors running.

```
V 0.0 0.0
```

Both motors stop; `POS` counts stabilise.

```
L
```

Firmware transmits the LRF binary trigger. If LRF is connected: `DIST <value>`. If not connected: `DIST -1.0` (timeout after 100 ms).

---

## Hardware Wiring Quick Reference

| Signal | Arduino Pin (default) | Connect to |
|--------|----------------------|-----------|
| Pan STEP | D2 | Stepper driver STEP |
| Pan DIR | D3 | Stepper driver DIR |
| Tilt STEP | D4 | Stepper driver STEP |
| Tilt DIR | D5 | Stepper driver DIR |
| Pan Left Limit | D6 | Switch leg A; switch leg B → GND |
| Pan Right Limit | D7 | Switch leg A; switch leg B → GND |
| Tilt Up Limit | D8 | Switch leg A; switch leg B → GND |
| Tilt Down Limit | D9 | Switch leg A; switch leg B → GND |
| LRF RX (Arduino) | D10 | LRF TX output |
| LRF TX (Arduino) | D11 | LRF RX input |
| Jetson Serial | USB-B port | Jetson USB-A port |

All limit switches: normally-open (NO), no external resistor required — `INPUT_PULLUP` is used.

---

## Tuning Parameters

All tuning is done in `config.h`:

| Constant | Default | Effect |
|----------|---------|--------|
| `HEARTBEAT_INTERVAL_MS` | `100` | Increase to reduce POS message frequency |
| `VELOCITY_SCALE_FACTOR` | `1000.0f` | Decrease to make motors faster at the same velocity value |
| `MIN_STEP_INTERVAL_US` | `200` | Increase to set a lower maximum step frequency (protect slow drivers) |
| `LIMIT_DEBOUNCE_MS` | `5` | Increase if limit switches show noise/chatter |
| `LRF_READ_TIMEOUT_MS` | `100` | Increase if LRF response arrives slowly on your module variant |
| `LRF_SOFTSERIAL_BAUD` | `115200` | Reduce to `57600` if SoftwareSerial LRF errors are high |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| No `POS` output on Serial Monitor | Wrong baud rate in monitor | Set monitor to 115200 baud |
| Board resets every 2 seconds | WDT triggering due to a blocking call in `loop()` | Check for any `delay()` or blocking serial read; remove it |
| `DIST -1.0` always returned | LRF wiring wrong or baud mismatch | Verify `LRF_RX_PIN`/`LRF_TX_PIN` in `config.h`; try `LRF_SOFTSERIAL_BAUD = 57600` |
| Motors moving in wrong direction | DIR pin polarity inverted for your driver board | Swap `PAN_DIR_PIN` polarity logic in `stepper.cpp` or invert velocity sign in Jetson |
| Limit switch not triggering | Pin wired to VCC instead of GND | Rewire switch leg to GND; `INPUT_PULLUP` expects active-LOW |
| Constant `LIMIT` messages on boot | Switch stuck LOW / wired NC (Normally-Closed) instead of NO | Verify switch is normally-open; check wiring |
