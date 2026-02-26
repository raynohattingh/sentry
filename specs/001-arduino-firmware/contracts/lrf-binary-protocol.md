# Contract: Arduino ↔ LRF Binary Serial Protocol

**Version**: 1.0.0 | **Branch**: `001-arduino-firmware` | **Date**: 2026-02-26

## Overview

The Arduino firmware communicates with the LRF (Laser Range Finder) module over a `SoftwareSerial` instance on two spare GPIO (General-Purpose Input/Output) pins. The protocol uses a fixed-length 8-byte binary frame with a 2-byte sync header, a function word, 4 data bytes, and a 1-byte checksum.

**Physical link**: `SoftwareSerial` on configurable RX/TX pins (defaults: RX=D10, TX=D11).  
**Baud rate**: 115200 baud, 8 data bits, 1 stop bit, no parity (`LRF_SOFTSERIAL_BAUD`).  
**All constants below are defined in `config.h`; no raw bytes appear in logic code.**

---

## Frame Layout (All Frames — Send and Reply)

| Byte index | Field name | Size | Notes |
|-----------|------------|------|-------|
| 0 | Frame Header H | 1 byte | Always `0x55` (`LRF_SYNC_H`) |
| 1 | Frame Header L | 1 byte | Always `0xAA` (`LRF_SYNC_L`) |
| 2 | Function Word | 1 byte | Identifies the command/response type |
| 3 | D1 | 1 byte | Send: `0xFF`; Reply: STA byte (`0x01`=ok, `0x00`=fail) |
| 4 | D2 | 1 byte | Send: `0xFF`; Reply: `0xFF` or reserved |
| 5 | D3 | 1 byte | Send: `0xFF`; Reply: DIS_H (distance high byte) or ANG_H |
| 6 | D4 | 1 byte | Send: `0xFF`; Reply: DIS_L (distance low byte) or ANG_L |
| 7 | Checksum | 1 byte | Frame integrity (see formulas below) |

**Total frame length**: 8 bytes (`LRF_FRAME_LEN = 8`).

---

## Checksum Formulas

### Send-frame checksum
Covers bytes 2–6 (Function Word + D1..D4) only:
```
checksum = (byte[2] + byte[3] + byte[4] + byte[5] + byte[6]) & 0xFF
```

### Reply-frame checksum
Covers all 7 bytes preceding the checksum (bytes 0–6):
```
checksum = (byte[0] + byte[1] + byte[2] + byte[3] + byte[4] + byte[5] + byte[6]) & 0xFF
```

> **Note**: Send and reply checksum formulas differ. Send excludes the header bytes; reply includes them.

---

## Command Table

| Command | Function Word | Send frame (hex) | Reply frame (hex) | Firmware usage |
|---------|--------------|-----------------|------------------|----------------|
| Single ranging | `0x88` | `55 AA 88 FF FF FF FF 84` | `55 AA 88 STA FF DIS_H DIS_L CHK` | Primary: triggered on `L\n` |
| Continuous ranging | `0x89` | `55 AA 89 FF FF FF FF 85` | Same as single ranging reply | Not used in primary flow |
| Stop ranging | `0x8E` | `55 AA 8E FF FF FF FF 8A` | `55 AA 8E STA FF FF FF CHK` | Stops continuous mode |
| Angular measurement | `0x8A` | `55 AA 8A FF FF FF FF 86` | `55 AA 8A STA FF ANG_H ANG_L CHK` | Not used in primary flow |
| Boot self-test | N/A | *(no send — reply only)* | `55 AA 80 STA 00 00 ErrCode CHK` | Emitted by LRF at power-on |

**Checksum verification for the single-ranging send frame**:
```
0x88 + 0xFF + 0xFF + 0xFF + 0xFF = 0x384; & 0xFF = 0x84  ✓
```

---

## Single-Ranging Reply — Distance Extraction

Applies when `Function Word = 0x88` and validation passes.

**STA byte** (byte[3]):
- `0x01` — measurement successful; proceed to distance extraction
- `0x00` — measurement failure; return `DIST -1.0\n` (do not extract distance)

**Distance formula** (only when `STA = 0x01`):
```c
uint16_t rawDist = ((uint16_t)buf[5] << 8) | buf[6];  // DIS_H, DIS_L
float distanceM  = rawDist / 10.0f;                   // module encodes real_m × 10
```

**Example**:
```
buf = [0x55, 0xAA, 0x88, 0x01, 0xFF, 0x00, 0x0F, CHK]
DIS_H = 0x00, DIS_L = 0x0F → rawDist = 15 → distanceM = 1.5 m
```

---

## Frame Validation (FR-027 — Mandatory)

Before extracting any data, the firmware MUST validate all three criteria in order:

1. **Sync bytes**: `buf[0] == 0x55` AND `buf[1] == 0xAA` — any mismatch → discard
2. **Checksum**: `(buf[0]+buf[1]+buf[2]+buf[3]+buf[4]+buf[5]+buf[6]) & 0xFF == buf[7]` — mismatch → discard
3. **STA byte**: `buf[3] == 0x01` → success; `buf[3] == 0x00` → failure → discard

On any validation failure: flush the `SoftwareSerial` RX buffer, return `DIST -1.0\n`.

---

## Boot Self-Test Frame (Power-On Only)

**Frame**: `55 AA 80 STA 00 00 ErrCode CHK` (reply-only — firmware never sends this command).

The LRF MAY emit this frame on power-on before it is ready to accept ranging commands.

**Firmware handling in `setup()` (FR-028)**:
- Wait up to `LRF_BOOT_TIMEOUT_MS` (500 ms) for an 8-byte frame starting with `0x55 0xAA 0x80`.
- `STA = 0x01` → discard silently; proceed to main loop.
- `STA = 0x00` → optionally log `LRF_BOOT_ERR <ErrCode>\n` over USB serial; proceed to main loop regardless.
- No boot frame within timeout → proceed normally (some LRF revisions omit the success notification).

---

## Error / Status Codes

| Code | Meaning |
|------|---------|
| `0x00` | No echo signal received |
| `0x16` | Out of range — target below minimum measurable range |
| `0x18` | No echo signal received (alternate code) |
| `0x00`–`0x07` | Hardware error range |

All of the above produce `DIST -1.0\n` on the Jetson serial link.

---

## Non-Blocking Read Protocol

The firmware MUST NOT use blocking reads or `delay()` for LRF frame reception (FR-026, NFR-007). The required non-blocking pattern per `loop()` iteration:

```c
if (lrfPending) {
    while (lrfSerial.available() && lrfBufLen < LRF_FRAME_LEN) {
        lrfBuf[lrfBufLen++] = lrfSerial.read();
    }
    if (lrfBufLen == LRF_FRAME_LEN) {
        // validate and extract
    } else if (millis() - lrfReadStart > LRF_READ_TIMEOUT_MS) {
        // timeout: flush, emit DIST -1.0\n, reset state
        while (lrfSerial.available()) lrfSerial.read();  // flush
    }
}
```

---

## AVR SoftwareSerial Reliability Note (CONSTRAINT-001)

At 115200 baud on AVR (16 MHz), `SoftwareSerial` disables global interrupts for ≈8.68 µs per bit — approximately 695 µs of interrupt blackout for a full 8-byte frame. This can cause missed `micros()` step-pulse deadlines and introduce short motor jitter during LRF reads.

**Mitigations**:
1. LRF reads are demand-driven (only on `L\n`), not continuous — blackout windows are infrequent.
2. Frame-integrity validation catches corrupt frames introduced by bit errors.
3. If hardware testing reveals an unacceptable error rate, set `LRF_SOFTSERIAL_BAUD = 57600` in `config.h` — no logic changes required.
