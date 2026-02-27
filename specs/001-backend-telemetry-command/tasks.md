# Tasks: Backend Telemetry Enrichment & Manual Override Subscriber

**Input**: Design documents from `/specs/001-backend-telemetry-command/`
**Branch**: `001-backend-telemetry-command`
**Spec**: `specs/001-backend-telemetry-command/spec.md`
**Plan**: `specs/001-backend-telemetry-command/plan.md`
**TDD Order**: Test (RED) → Implementation (GREEN) for all logic

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (touches different files, no incomplete dependencies)
- **[US1]**: User Story 1 — Enriched Telemetry (fsm_state + velocity_vector)
- **[US2]**: User Story 2 — Manual Override Subscriber (CommandSubscriber)
- File paths are relative to repository root

---

## Phase 1: Setup (Shared Prerequisites)

**Purpose**: Add config constants required by both user stories. No user story can start without this.

- [ ] T001 Add new config constants and update MQTT_PORT default in `jetson/src/config.py`: `SENTRY_ID = os.environ["SENTRY_ID"]` (required, no default — KeyError on startup if unset); `MQTT_USERNAME: str = os.environ.get("MQTT_USERNAME", "")`, `MQTT_PASSWORD: str = os.environ.get("MQTT_PASSWORD", "")`, `CAMERA_FPS: int = int(os.environ.get("CAMERA_FPS", "25"))`, `CAMERA_HFOV_DEG: float = float(os.environ.get("CAMERA_HFOV_DEG", "120.0"))`; change `MQTT_PORT` default from `"1883"` to `"8883"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the shared data model. Both user stories depend on these types before any tests or implementation can be written.

**⚠️ CRITICAL**: Complete T002 and T003 before starting Phase 3 or Phase 4.

- [ ] T002 [P] Add `MANUAL_OVERRIDE = "MANUAL_OVERRIDE"` to the `FSMState` enum in `jetson/src/types.py` (new value after `ACQUIRE`; insert before the closing blank line of the enum)
- [ ] T003 [P] Add two new fields to `TelemetryRecord` dataclass in `jetson/src/types.py`: `velocity_vector: dict | None` (docstring: `{"vx": float, "vy": float} in m/s, or null`) and `fsm_state: str` (docstring: `FSMState.value string; always present`); add both as positional fields after `timestamp_utc`

**Checkpoint**: Both types updated — Phase 3 and Phase 4 can now begin in parallel.

---

## Phase 3: User Story 1 — Enriched Telemetry (Priority: P1) 🎯 MVP

**Goal**: Every `sentry/telemetry` MQTT message includes `fsm_state` (always a string) and `velocity_vector` (m/s object or null). Mobile app can animate threat markers and display FSM state badge immediately.

**Independent Test**: Subscribe to `sentry/telemetry`. Confirm each message has `fsm_state` (one of SCAN/TRACK/ACQUIRE/SEARCH/MANUAL_OVERRIDE) and `velocity_vector` (`{"vx": ..., "vy": ...}` or `null`). Change FSM state by removing target — confirm next payload reflects new state.

- [ ] T004 Write failing tests (RED) for velocity conversion and new TelemetryRecord field population in `jetson/tests/unit/test_telemetry_enrichment.py`: `test_velocity_conversion_basic` (v_px=(1.0, 0.5), lrf=10.0m → assert approx m/s using pinhole formula with config defaults), `test_velocity_conversion_zero` (v_px=(0.0, 0.0) → `{"vx": 0.0, "vy": 0.0}`), `test_velocity_null_when_no_lrf` (lrf_distance=None → velocity_vector is None), `test_fsm_state_in_record` (record() with FSMState.TRACK → TelemetryRecord.fsm_state == "TRACK"), `test_fsm_state_manual_override` (FSMState.MANUAL_OVERRIDE → fsm_state == "MANUAL_OVERRIDE"), `test_velocity_vector_always_in_asdict` (dataclasses.asdict(record) always contains "velocity_vector" key even when null)
- [ ] T005 [P] Extend existing tests (RED) in `jetson/tests/unit/test_telemetry_recorder.py` with three new test functions: `test_emit_json_contains_fsm_state` (emitted JSON string contains `"fsm_state"`), `test_emit_json_contains_velocity_vector_key` (emitted JSON string always contains `"velocity_vector"` key), `test_emit_velocity_null_when_lrf_disabled` (monkeypatch `config.LRF_ENABLED=False` → velocity_vector is null in emitted JSON); update existing recorder fixture call sites to pass `fsm_state=FSMState.TRACK` as new required argument
- [ ] T006 Add private module-level helper `_convert_velocity(v_px_frame: tuple[float, float], lrf_m: float) -> tuple[float, float]` to `jetson/src/telemetry/recorder.py` using pinhole model: `focal_px = (config.CAMERA_WIDTH / 2.0) / math.tan(math.radians(config.CAMERA_HFOV_DEG / 2.0))`, then `vx = v_px_frame[0] * lrf_m / (focal_px * config.CAMERA_FPS)`, same for vy; import `math` at top of file
- [ ] T007 Update `TelemetryRecorder.record()` signature in `jetson/src/telemetry/recorder.py` to add `fsm_state: FSMState` as a required parameter; compute `velocity_vector` using `_convert_velocity()` when `lrf_distance` is not None (otherwise None); construct and return `TelemetryRecord` with both new fields populated; update the docstring Args section to document both new parameters
- [ ] T008 Run `pytest jetson/tests/unit/test_telemetry_enrichment.py jetson/tests/unit/test_telemetry_recorder.py -v` — confirm all US1 tests GREEN and zero failures before proceeding

---

## Phase 4: User Story 2 — Manual Override Subscriber (Priority: P1)

**Goal**: Operator can take physical control of the turret via the mobile app joystick. Commands received over `sentry/command` MQTT topic move the turret in near-real-time; 3-second safety timeout and zero-velocity exit restore autonomous operation.

**Independent Test**: Publish a `sentry/command` JSON message to the broker. Observe turret movement. Publish zero-velocity command — turret stops and FSM resumes. Publish command with wrong `sentry_id` — turret ignores it (warning log only).

### 4a — SentryBrain Override API

- [ ] T009 Write failing tests (RED) for SentryBrain override API by appending to `jetson/tests/unit/test_fsm_brain.py`: `test_enter_override_returns_manual_override_state` (call `enter_override()` → `brain.state == FSMState.MANUAL_OVERRIDE`), `test_exit_override_restores_underlying_fsm_state` (enter then exit → state equals original `_state`), `test_override_does_not_mutate_internal_state` (`brain._state` unchanged by enter/exit), `test_override_thread_safe` (10 concurrent threads alternating enter/exit — no assertion error after 0.1s)
- [ ] T010 [US2] Add thread-safe override support to `SentryBrain` in `jetson/src/control/sentry_brain.py`: import `threading` at top; add `self._override_lock = threading.Lock()` and `self._override: bool = False` in `__init__`; add `enter_override(self) -> None` (sets flag, logs `[BRAIN] MANUAL_OVERRIDE engaged.`) and `exit_override(self) -> None` (clears flag, logs `[BRAIN] MANUAL_OVERRIDE disengaged — resuming autonomous.`); modify `state` property to check `_override` under lock and return `FSMState.MANUAL_OVERRIDE` if set

### 4b — MQTTPublisher TLS Upgrade

- [ ] T011 [P] [US2] Update `MQTTPublisher._connect()` in `jetson/src/comms/mqtt.py` to add TLS and authentication: import `ssl` at top of file; after `client = mqtt.Client()` add `client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)` (only when both are non-empty); add `client.tls_set(ca_certs=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS_CLIENT)` and `client.tls_insecure_set(True)` before `client.connect()`; all other MQTTPublisher behaviour unchanged (FR-022a-9)

### 4c — CommandSubscriber

- [ ] T012 [US2] Write failing tests (RED) in `jetson/tests/unit/test_command_subscriber.py` (new file): `test_valid_command_calls_enter_override` (dispatch valid command payload → mock brain.enter_override called), `test_valid_command_sends_clamped_velocities` (pan_velocity=PAN_MAX*2 → mock turret receives PAN_MAX), `test_sentry_id_mismatch_discards_command` (wrong sentry_id → brain.enter_override NOT called, turret NOT called), `test_malformed_json_logs_warning_no_crash` (bad JSON → no exception raised), `test_zero_velocity_exits_override` (dispatch (0.0, 0.0) command → brain.exit_override called + turret.stop called), `test_rate_limit_blocks_excess_commands` (call `_handle_command()` 25 times within 50ms → turret called ≤ 20 times), `test_safety_timeout_stops_turret` (enter override, advance mock time by 3.1s → turret.stop + brain.exit_override called); use `unittest.mock.MagicMock` for brain and turret
- [ ] T013 [US2] Implement `CommandSubscriber` class in `jetson/src/comms/mqtt.py` (new class after MQTTPublisher): `__init__(self, brain: SentryBrain, turret: TurretManager, broker=None, port=None)` — stores refs, sets `COMMAND_TOPIC = "sentry/command"`, `_SAFETY_TIMEOUT_S = 3.0`, `_MIN_INTERVAL_S = 1.0 / 20`; `start(self) -> None` — TLS subscribe thread (daemon=True) + safety-timeout watchdog thread (daemon=True); `stop(self) -> None` — sets stop event; `_connect_and_subscribe()` — paho client with TLS (same pattern as MQTTPublisher T011), subscribe to `sentry/command`, `loop_forever()`; `_on_message()` — parse JSON, validate sentry_id (warn + return on mismatch), rate-limit check (return if within MIN_INTERVAL_S), call `_dispatch(cmd)`; `_dispatch(cmd: ManualCommand)` — if zero-velocity call exit + stop; else call enter_override + clamp velocities + send_velocity; `_watchdog()` — loop checking `time.monotonic() - _last_cmd_time > _SAFETY_TIMEOUT_S` while override active → stop + exit; log all events with `[COMMAND]` prefix
- [ ] T014 [US2] Write integration test in `jetson/tests/integration/test_command_subscriber_integration.py`: Scenario A — create CommandSubscriber with mock brain/turret, simulate two valid command dispatches then a zero-velocity command, assert exit_override called and turret stopped; Scenario B — simulate one valid command then advance time past 3.1s, assert watchdog called turret.stop and exit_override; both scenarios must complete without errors

### 4d — Verification

- [ ] T015 [P] [US2] Run `pytest jetson/tests/unit/test_fsm_brain.py jetson/tests/unit/test_command_subscriber.py jetson/tests/integration/test_command_subscriber_integration.py -v` — confirm all US2 tests GREEN

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T016 [P] Remove the BLOCKING TODO comment block from `jetson/src/types.py` (lines starting with `# TODO(mobile-app FR-010a BLOCKING)` added during mobile app implementation phase)
- [ ] T017 Run full test suite `pytest jetson/tests/ -v` to confirm no regressions; all pre-existing tests (test_telemetry_recorder, test_fsm_brain, test_pid, test_geo, test_detector, test_tracker, test_threat_scoring, test_serial_io, test_serial_framing, test_camera) must still pass

---

## Dependencies

```
T001 (config)
  └── T002, T003 (types — Phase 2, parallel)
        ├── T004, T005 (US1 tests RED — parallel)
        │     └── T006 (velocity helper)
        │           └── T007 (recorder update GREEN)
        │                 └── T008 (US1 test run GREEN ✅)
        └── T009 (US2 brain tests RED)
              └── T010 (SentryBrain override GREEN)
                    ├── T011 (MQTTPublisher TLS — parallel)
                    ├── T012 (CommandSubscriber tests RED — depends on T010)
                    │     └── T013 (CommandSubscriber GREEN)
                    │           └── T014 (integration test)
                    │                 └── T015 (US2 test run GREEN ✅)
                    └── (T011 can run in parallel with T012)
T008 + T015 → T016 → T017 (full suite)
```

## Parallel Execution Opportunities

| After | Can run in parallel |
|-------|---------------------|
| T001 complete | T002 + T003 |
| T002 + T003 complete | T004 + T005 (US1 RED) AND T009 (US2 RED) |
| T009 complete | T010 starts; T011 can start independently |
| T010 complete | T011 (TLS upgrade) + T012 (subscriber tests) in parallel |
| T008 + T015 complete | T016 + T017 |

## Implementation Strategy

**MVP** (minimum to unblock mobile app): Complete Phase 1 → Phase 2 → Phase 3 (US1 only).
This delivers enriched telemetry (`fsm_state` + `velocity_vector`) to the mobile app without
the override subscriber — mobile app can animate markers and show FSM state immediately.

**Full delivery**: Continue Phase 4 (US2) for manual override. Both phases are P1 in spec
but US1 is safer to deploy first (additive-only change, no new threading).

## Summary

| Phase | Tasks | User Story | Parallel Opportunities |
|-------|-------|------------|------------------------|
| Phase 1: Setup | T001 | — | — |
| Phase 2: Foundational | T002, T003 | — | T002 ‖ T003 |
| Phase 3: US1 Enriched Telemetry | T004–T008 | US1 | T004 ‖ T005 |
| Phase 4: US2 Manual Override | T009–T015 | US2 | T009→T010; T011 ‖ T012 |
| Phase 5: Polish | T016, T017 | — | T016 ‖ T017 |
| **Total** | **17 tasks** | | **7 parallel pairs** |
