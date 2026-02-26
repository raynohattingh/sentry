# Tasks: Arduino Firmware — Sentry HAL

**Branch**: `001-arduino-firmware` | **Generated**: 2026-02-26  
**Input**: Design documents from `specs/001-arduino-firmware/`  
**Spec**: `spec.md` (28 FRs, 5 User Stories) | **Plan**: `plan.md` | **Data Model**: `data-model.md`

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[US#]**: Which user story this task delivers
- All paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the project skeleton, build toolchain, and PlatformIO native test environment. Nothing else can start until this is in place.

- [ ] T001 Create `arduino/sentry_turret/` directory and verify it is reachable from Arduino IDE and PlatformIO
- [ ] T002 Create `test/arduino/platformio.ini` with two environments: `[env:uno]` (upload target, board `uno`, framework `arduino`) and `[env:native]` (host test runner, platform `native`, build flags to exclude Arduino-specific headers). Both environments MUST include `build_src_dir = ../../arduino/sentry_turret` so PlatformIO can locate the source modules from the `test/arduino/` working directory.
- [ ] T003 [P] Create empty placeholder files for all six source modules so IDE can resolve includes: `arduino/sentry_turret/config.h`, `stepper.h`, `stepper.cpp`, `lrf.h`, `lrf.cpp`, `limits.h`, `limits.cpp`, `serial_proto.h`, `serial_proto.cpp`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user story phases depend on. No US work can begin until this phase is complete.

**⚠️ CRITICAL**: config.h defines every constant imported by every other file. serial_proto defines the command type enum used by sentry_turret.ino's dispatch loop.

- [ ] T004 Create `arduino/sentry_turret/config.h` — define ALL named constants with Doxygen comments (units, valid range, default). **CNC Shield V3 pin assignments (authoritative — do NOT use old placeholder values)**: `PAN_STEP_PIN` (2), `PAN_DIR_PIN` (5), `TILT_STEP_PIN` (3), `TILT_DIR_PIN` (6), `STEPPER_ENABLE_PIN` (8) (active-LOW, shared all drivers), `LIMIT_PAN_LEFT_PIN` (9), `LIMIT_PAN_RIGHT_PIN` (10), `LIMIT_TILT_DOWN_PIN` (11), `LIMIT_TILT_UP_PIN` (12). **LRF SoftwareSerial pins**: `LRF_RX_PIN` (A0), `LRF_TX_PIN` (A1). **WDT (Watchdog Timer) portability macros** (NFR-004/NFR-005): `#include <avr/wdt.h>` lives HERE in `config.h`; expose `WDT_ENABLE()` as `wdt_enable(WDTO_2S)` and `WDT_RESET()` as `wdt_reset()` — `sentry_turret.ino` calls only `WDT_ENABLE()`/`WDT_RESET()`, never `<avr/wdt.h>` directly. **All other constants**: `JETSON_BAUD` (115200), `LRF_SOFTSERIAL_BAUD` (115200), `HEARTBEAT_INTERVAL_MS` (100), `VELOCITY_SCALE_FACTOR` (1000.0f), `MIN_STEP_INTERVAL_US` (200), `LIMIT_DEBOUNCE_MS` (5), `LRF_FRAME_LEN` (8), `LRF_SYNC_H` (0x55), `LRF_SYNC_L` (0xAA), `LRF_TRIGGER[8]` (`{0x55,0xAA,0x88,0xFF,0xFF,0xFF,0xFF,0x84}`), `LRF_READ_TIMEOUT_MS` (100), `LRF_BOOT_TIMEOUT_MS` (500), `SERIAL_LINE_BUF_LEN` (64). No pin numbers, timing literals, or platform-specific API calls appear in any other file.
- [ ] T005 Create `arduino/sentry_turret/serial_proto.h` and `serial_proto.cpp` — define `CommandType` enum (`CMD_VELOCITY`, `CMD_LASER`, `CMD_UNKNOWN`); define `SerialCommand` struct (`type`, `panVelocity float`, `tiltVelocity float`); implement `feedByte(char c)` line-accumulator and `parseLine(const char* line) -> SerialCommand` tokeniser using `strtof()`; `CMD_UNKNOWN` on any malformed or unrecognised input; buffer overflow guard (discard line if > `SERIAL_LINE_BUF_LEN` without null-terminator issues). No Arduino API calls in the logic — accept raw chars so the native test runner can exercise it without hardware.

**Checkpoint**: config.h and serial_proto are complete — US phases may now proceed.

---

## Phase 3: User Story 1 — Velocity-Driven Motor Control (Priority: P1) 🎯 MVP

**Goal**: Jetson sends `V <pan> <tilt>\n`; both stepper motors run at the correct speed and direction via non-blocking `micros()` scheduling. `V 0.0 0.0\n` stops both axes within one loop cycle.

**Independent Test**: Open Serial Monitor at 115200 baud. Send `V 100.0 -50.0\n`. Observe pan STEP pulses at ~2× the frequency of tilt STEP pulses on a logic analyser. Pan DIR pin HIGH (right). Tilt DIR pin LOW (down). Send `V 0.0 0.0\n` — all pulses cease.

- [ ] T006 [P] Write `test/arduino/test_serial_proto.cpp` (TDD — write before verifying T005 implementation): tests must cover — valid `V 100.0 -50.0` parses to `CMD_VELOCITY` with correct floats; `V 0.0 0.0` stops both; `L` parses to `CMD_LASER`; `V 100.0` (missing tilt) → `CMD_UNKNOWN`; `GARBAGE` → `CMD_UNKNOWN`; line longer than `SERIAL_LINE_BUF_LEN` → buffer discarded cleanly with no crash. Run `pio test -e native` — confirm tests fail (red).
- [ ] T007a [P] Write `test/arduino/test_stepper.cpp` (TDD — write before T008 implementation): tests must cover — (1) `stepperSetVelocity` with positive velocity → `stepIntervalUs` equals `(uint32_t)(VELOCITY_SCALE_FACTOR / velocity)` and `dirPin` set HIGH; (2) negative velocity → `dirPin` set LOW, interval computed from `fabsf(velocity)`; (3) velocity = 0.0 → `stepIntervalUs` = 0 (no pulses); (4) velocity that would compute interval below `MIN_STEP_INTERVAL_US` → clamped to `MIN_STEP_INTERVAL_US`; (5) `stepCount` increments on each tick; (6) `stepCount` at `INT32_MAX - 1`, one more tick → clamped to `INT32_MAX`, does not wrap; (7) `stepCount` at `INT32_MIN + 1`, one more negative tick → clamped to `INT32_MIN`; (8) `stepperSetVelocity` called on a running axis → `stepIntervalUs` updates immediately, `stepCount` and `nextStepTime` are NOT reset to zero (FR-013). All tests use mock `micros()` input — no Arduino API. Run `pio test -e native` — confirm tests fail (red).
- [ ] T007 [P] Create `arduino/sentry_turret/stepper.h` — declare `StepperAxis` struct (`stepPin uint8_t`, `dirPin uint8_t`, `velocity float`, `stepIntervalUs unsigned long`, `nextStepTime unsigned long`, `stepCount int32_t`); declare `stepperInit(StepperAxis& axis, uint8_t stepPin, uint8_t dirPin)`, `stepperSetVelocity(StepperAxis& axis, float velocity)`, `stepperTick(StepperAxis& axis)`. Pure C++ — no Arduino API in the header. Note: `stepHigh bool` is NOT included (dead field — pulse state is transient, not stored).
- [ ] T008 Implement `arduino/sentry_turret/stepper.cpp` — `stepperInit`: sets pin modes via `pinMode()`; `stepperSetVelocity`: updates `velocity`, sets `dirPin` HIGH/LOW per sign (FR-011), computes `stepIntervalUs = (uint32_t)(VELOCITY_SCALE_FACTOR / fabsf(velocity))` clamped to `MIN_STEP_INTERVAL_US` (do NOT update `nextStepTime` or `stepCount` here — FR-013), sets `stepIntervalUs = 0` if velocity==0.0; `stepperTick`: if `stepIntervalUs > 0` and `micros() >= nextStepTime` → call `digitalWrite(stepPin, HIGH)` then immediately `digitalWrite(stepPin, LOW)` (two back-to-back calls, NO `delayMicroseconds()` — FR-026), increment/decrement `stepCount` per direction (with `INT32_MAX`/`INT32_MIN` clamp per FR-006), recompute `nextStepTime = micros() + stepIntervalUs`. No `delay()` or `delayMicroseconds()` anywhere.
- [ ] T009 Update `arduino/sentry_turret/sentry_turret.ino` — in `setup()`: call `Serial.begin(JETSON_BAUD)`; call `pinMode(STEPPER_ENABLE_PIN, OUTPUT)` then `digitalWrite(STEPPER_ENABLE_PIN, LOW)` to enable CNC Shield V3 drivers (FR-009a); call `stepperInit()` for both pan and tilt axes using config pin constants; in `loop()`: call `feedByte(Serial.read())` when `Serial.available()`; on complete command dispatch — `CMD_VELOCITY` → call `stepperSetVelocity()` for both axes; call `stepperTick()` for both axes every iteration. Implement `WDT_RESET()` stub comment placeholder (WDT wired in T023). Confirm `pio test -e native` for test_serial_proto passes (green).

---

## Phase 4: User Story 2 — Limit Switch Safety Stops (Priority: P2)

**Goal**: When a limit switch (NO, active-LOW, `INPUT_PULLUP`) triggers, the affected axis stops immediately and `LIMIT <axis> <direction>\n` is sent once. Motion in the safe (opposite) direction is unblocked.

**Independent Test**: With a motor running, bridge the corresponding limit pin to GND. Verify: step pulses on that axis cease within one loop cycle; firmware prints `LIMIT PAN RIGHT\n` (or correct axis/direction); holding the bridge does NOT repeat the message; releasing and re-bridging sends a second message.

- [ ] T010 [P] Write `test/arduino/test_limits.cpp` (TDD — write first): tests must cover — `IDLE → DEBOUNCING` on first LOW sample; `DEBOUNCING → IDLE` if pin goes HIGH within `LIMIT_DEBOUNCE_MS`; `DEBOUNCING → FIRED` after `LIMIT_DEBOUNCE_MS` ms of continuous LOW — event fires exactly once; `FIRED → IDLE` when pin returns HIGH; second LOW cycle after release fires a second event. Mock `millis()` as a uint32_t input parameter in the pure-logic function under test. Run `pio test -e native` — confirm tests fail (red).
- [ ] T011 [P] Create `arduino/sentry_turret/limits.h` — declare `LimitPin` struct (`pin uint8_t`, `axis const char*`, `direction const char*`, `debounceStart unsigned long`, `triggered bool`); declare `limitInit(LimitPin& lp, uint8_t pin, const char* axis, const char* direction)` and `limitTick(LimitPin& lp, unsigned long nowMs) -> bool` (returns true on confirmed trigger edge). Note: `wasTriggered bool` is NOT included — edge detection is achieved by the existing `triggered` flag transitioning from `false` to `true`.
- [ ] T012 Implement `arduino/sentry_turret/limits.cpp` — `limitInit`: `pinMode(pin, INPUT_PULLUP)`; `limitTick`: if `digitalRead(pin) == LOW` start or continue debounce timer; if sustained LOW for ≥ `LIMIT_DEBOUNCE_MS` ms and not already `triggered`, set `triggered = true`, return `true` (event edge); if pin HIGH reset `triggered`, `debounceStart`, return `false`. No blocking calls. Confirm `pio test -e native` for test_limits passes (green).
- [ ] T013 Update `arduino/sentry_turret/sentry_turret.ino` — in `setup()`: call `limitInit()` for all four `LimitPin` instances using config pin constants and correct axis/direction strings; in `loop()`: call `limitTick()` for all four limits each iteration; on a `true` return, send `LIMIT <axis> <direction>\n` over `Serial` AND gate `stepperSetVelocity()` to prevent motion into the active limit direction (velocity in the safe direction remains unblocked per FR-017).

---

## Phase 5: User Story 3 — Laser Rangefinder Integration (Priority: P3)

**Goal**: On `L\n`, firmware sends the 8-byte binary trigger over `SoftwareSerial` TX, accumulates the 8-byte binary reply non-blockingly, validates frame (sync bytes + checksum + STA), extracts distance, and responds `DIST <metres>\n`. Times out with `DIST -1.0\n` if no valid frame within `LRF_READ_TIMEOUT_MS`.

**Independent Test**: Wire LRF module to `LRF_RX_PIN`/`LRF_TX_PIN`. Send `L\n`. Verify `DIST <value>\n` returned within 500 ms. Disconnect LRF mid-reception — verify `DIST -1.0\n` returned and motor motion continues uninterrupted.

- [ ] T014 [P] Write `test/arduino/test_lrf_frame.cpp` (TDD — write first): tests must cover — valid reply frame `55 AA 88 01 FF 00 0F CHK` → distance = 1.5 m; STA=0x00 → `DIST -1.0`; bad sync byte[0] → discard; bad sync byte[1] → discard; checksum mismatch → discard; truncated frame (< 8 bytes at timeout) → discard; `DIS_H=0x05 DIS_L=0xDC` → 150.0 m; checksum edge case — all 0xFF payload. Run `pio test -e native` — confirm tests fail (red).
- [ ] T015 [P] Create `arduino/sentry_turret/lrf.h` — declare `LrfReader` struct (`pending bool`, `buf uint8_t[8]`, `bufLen uint8_t`, `readStart unsigned long`); declare `lrfInit(LrfReader& lr)`, `lrfTrigger(LrfReader& lr, Stream& serial, unsigned long nowMs)` (sends `LRF_TRIGGER[]` over `serial` — `Stream&` parameter makes this mockable for native tests; pass `lrfSerial` from `.ino`), `lrfFeedByte(LrfReader& lr, uint8_t byte, unsigned long nowMs) -> float` (returns distance ≥ 0 on complete valid frame, -1.0 on validation failure/timeout, -2.0 if still accumulating — caller must handle all three cases), `lrfCheckTimeout(LrfReader& lr, unsigned long nowMs) -> bool` (true if timed out). Pure C++ logic isolated from SoftwareSerial API.
- [ ] T016 Implement `arduino/sentry_turret/lrf.cpp` — `lrfFeedByte`: accumulate into `buf`; when `bufLen == LRF_FRAME_LEN` validate (sync bytes `buf[0]==LRF_SYNC_H`, `buf[1]==LRF_SYNC_L`; reply checksum `(sum of bytes 0–6) & 0xFF == buf[7]`; STA `buf[3]==0x01`); on pass extract `((uint16_t)buf[5]<<8 | buf[6]) / 10.0f`; on fail return -1.0 and flush. `lrfCheckTimeout`: if `pending` and `millis() - readStart > LRF_READ_TIMEOUT_MS` reset `pending`, reset `buf`, return true. No `while` loops or `delay()`. Confirm `pio test -e native` for test_lrf_frame passes (green).
- [ ] T017 Update `arduino/sentry_turret/sentry_turret.ino` — instantiate `SoftwareSerial lrfSerial(LRF_RX_PIN, LRF_TX_PIN)`; in `setup()`: `lrfSerial.begin(LRF_SOFTSERIAL_BAUD)`; add `// CONSTRAINT-001: SoftwareSerial at 115200 baud is at AVR interrupt-latency limit` comment; in `loop()`: dispatch `CMD_LASER` → `lrfTrigger(lrfReader, lrfSerial, millis())`; feed available `lrfSerial` bytes to `lrfFeedByte()`; handle all three return values: result ≥ 0.0 → print `DIST <value>\n`; result == -1.0 → print `DIST -1.0\n`; result == -2.0 → do nothing, frame still accumulating, continue loop; call `lrfCheckTimeout()` each iteration and print `DIST -1.0\n` if it returns true.
- [ ] T018 Implement LRF boot self-test discard in `arduino/sentry_turret/sentry_turret.ino setup()` (FR-028) — after `lrfSerial.begin()`, wait up to `LRF_BOOT_TIMEOUT_MS` for an 8-byte frame starting with `0x55 0xAA 0x80`; if `STA==0x00` print `LRF_BOOT_ERR <ErrCode>\n`; if no frame arrives within timeout, proceed normally; use non-blocking `millis()` polling — no `delay()`.

---

## Phase 6: User Story 4 — Position Heartbeat (Priority: P4)

**Goal**: `POS <pan_steps> <tilt_steps>\n` broadcast every `HEARTBEAT_INTERVAL_MS` (100 ms) at ≤ ±20% jitter. Step counts are `int32_t`, clamped at `INT32_MAX`/`INT32_MIN`, and accurately reflect steps driven since power-on.

**Independent Test**: Connect Serial Monitor at 115200 baud. Without sending any commands, observe `POS 0 0\n` messages at ~100 ms intervals. Drive both axes and verify counts increment/decrement proportionally. Run both motors for an extended session and verify no wrap-around occurs.

- [ ] T019 Add heartbeat to `arduino/sentry_turret/sentry_turret.ino` — declare `unsigned long lastHeartbeatMs = 0`; in `loop()`: if `millis() - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS` → print `"POS "`, print `panAxis.stepCount`, print `" "`, print `tiltAxis.stepCount`, print `"\n"`, update `lastHeartbeatMs`. Verify `POS` messages appear in Serial Monitor at correct interval with no other changes to logic.
- [ ] T020 Add `INT32_MAX`/`INT32_MIN` overflow clamp to `arduino/sentry_turret/stepper.cpp` `stepperTick()` — after `stepCount` increment/decrement, if `stepCount >= INT32_MAX` clamp to `INT32_MAX`; if `stepCount <= INT32_MIN` clamp to `INT32_MIN`. Add `#include <limits.h>` for `INT32_MAX`/`INT32_MIN`. This logic MUST be covered by the unit tests in T007a (test cases 6 and 7 specifically).

---

## Phase 7: User Story 5 — Operator Hardware Configuration (Priority: P5)

**Goal**: Every pin assignment and timing constant lives exclusively in `config.h`. No pin numbers, baud rate literals, or timing values appear inline in any logic file. Changing a constant and recompiling is sufficient — no other changes required.

**Independent Test**: Review all `.cpp` and `.ino` files with `grep` for raw pin numbers (2–11), baud rate literals (115200), and timing values (100, 200, 5, 1000). All results must be zero outside `config.h`. Modify `PAN_STEP_PIN` from 2 to 12 in `config.h`, recompile, and confirm no compilation errors and step pulses appear on pin 12.

- [ ] T021 Audit all logic files for inline literals — run `grep -rn "[^_]\b[2-9]\b\|115200\|HEARTBEAT\|DEBOUNCE" arduino/sentry_turret/stepper.cpp arduino/sentry_turret/stepper.h arduino/sentry_turret/lrf.cpp arduino/sentry_turret/lrf.h arduino/sentry_turret/limits.cpp arduino/sentry_turret/limits.h arduino/sentry_turret/serial_proto.cpp arduino/sentry_turret/serial_proto.h arduino/sentry_turret/sentry_turret.ino` and replace every raw literal with its named constant from `config.h` (FR-022, FR-023, FR-024). All pin numbers and timing values must resolve to `config.h` symbols. **Note**: grep MUST include `.h` header files — default to `grep -rn --include="*.h" --include="*.cpp" --include="*.ino"` for coverage.
- [ ] T022 [P] Add Doxygen-style `/** ... */` documentation comments to all public declarations in `config.h`, `stepper.h`, `lrf.h`, `limits.h`, and `serial_proto.h` — each constant must document: purpose, units (ms / µs / steps / baud), valid range, and default. Each public function must document: purpose, parameters, return value (Constitution I).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Reliability hardening, WDT activation, constraint documentation, final test run, HITL (Hardware-In-The-Loop) acceptance gate.

- [ ] T023 Enable WDT (Watchdog Timer) in `arduino/sentry_turret/sentry_turret.ino` — call `WDT_RESET()` (from `config.h` macro) as the **first statement** of `loop()`, unconditionally; call `WDT_ENABLE()` (from `config.h` macro) as the **last statement** of `setup()` (NFR-001, NFR-002). Do NOT add `#include <avr/wdt.h>` to the `.ino` — it lives in `config.h` (NFR-004/NFR-005). Add a comment above `WDT_RESET()`: `// WDT (Watchdog Timer) is hang-recovery only — NOT a serial-disconnect watchdog (see NFR-003)`. Add a comment near `WDT_ENABLE()`: `// NOTE: Optiboot v6+ required — earlier bootloaders may cause infinite reset loop after WDT fire`.
- [ ] T024 [P] Harden serial line buffer overflow guard in `arduino/sentry_turret/serial_proto.cpp` — if a line accumulates > `SERIAL_LINE_BUF_LEN - 1` bytes without a `\n`, discard the partial buffer and reset the accumulator; verify no buffer overrun or null-pointer dereference is possible (FR-004).
- [ ] T025 [P] Add `CONSTRAINT-001` reliability comment block at the `SoftwareSerial lrfSerial(...)` declaration site in `sentry_turret.ino`: document the 695 µs interrupt-blackout risk at 115200 baud, the frame-integrity mitigation (FR-027), and the `LRF_SOFTSERIAL_BAUD` fallback path to 57600 baud in `config.h` with no logic changes required.
- [ ] T026 Run full PlatformIO native test suite — `cd test/arduino && pio test -e native` — confirm all **four** test files pass with zero failures: `test_serial_proto`, `test_stepper`, `test_lrf_frame`, `test_limits`. Fix any regressions before proceeding to T027.
- [ ] T027 HITL acceptance test (hardware gate — requires physical Arduino Uno R3, stepper drivers, limit switches, LRF module) — verify SC-001 through SC-009 from `spec.md` in order: command→motion < 10 ms (SC-001); stop ≤ 5 ms (SC-002); limit halt < 1 loop cycle (SC-003); POS jitter ≤ ±20% (SC-004); DIST ≤ 500 ms (SC-005); all 4 limits independent (SC-006); config-only change works for ≥ 3 constants (SC-007); 30-min soak (SC-008); WDT hang-recovery in ≤ 2 s (SC-009). **This task is a pre-merge gate — the branch MUST NOT be merged to `main` until it passes.**

---

## Dependencies

```
T001 → T002 → T003
                └→ T004 → T005 → [T006, T007a, T007] → T008 → T009
                                                                  └→ [T010, T011] → T012 → T013
                                                                                             └→ [T014, T015] → T016 → T017 → T018
                                                                                                                              └→ T019 → T020
                                                                                                                                          └→ T021 → T022
                                                                                                                                                      └→ [T023, T024, T025] → T026 → T027
```

**Critical path**: T001 → T004 → T005 → T008 → T012 → T016 → T019 → T021 → T026 → T027

**Parallel opportunities per phase**:
- Phase 3 (US1): T006 (serial_proto tests) ‖ T007a (stepper tests) ‖ T007 (stepper header) — all need only T005/T004
- Phase 4 (US2): T010 (write failing tests) ‖ T011 (write header) — both need only T004
- Phase 5 (US3): T014 (write failing tests) ‖ T015 (write header) — both need only T004
- Phase 7 (US5): T021 (literal audit) ‖ T022 (Doxygen comments) — different files
- Phase 8 (Polish): T023 (WDT) ‖ T024 (buffer guard) ‖ T025 (constraint comment) — different concerns

---

## Implementation Strategy

**MVP scope** (User Story 1 only — minimum viable turret):
Complete T001–T009 → the turret can receive velocity commands and drive motors. This is a deployable, testable increment with zero hardware risk from unimplemented safety stops.

**Increment 2**: Add T010–T013 (US2 limit switches) — turret is now mechanically safe.

**Increment 3**: Add T014–T018 (US3 LRF) — full ranging capability; Jetson telemetry pipeline becomes functional.

**Increment 4**: Add T019–T020 (US4 heartbeat) — Jetson position synchronisation and disconnect detection active.

**Increment 5**: Add T021–T027 (US5 config + Polish + HITL) — production-ready, merge-eligible.

---

## Metrics

| Metric | Count |
|--------|-------|
| Total tasks | 28 |
| Setup tasks | 3 |
| Foundational tasks | 2 |
| US1 tasks (MVP) | 5 |
| US2 tasks | 4 |
| US3 tasks | 5 |
| US4 tasks | 2 |
| US5 tasks | 2 |
| Polish/HITL tasks | 5 |
| TDD test-first tasks | 4 (T006, T007a, T010, T014) |
| Parallelizable [P] tasks | 11 |
| Hardware-gate tasks | 1 (T027) |
