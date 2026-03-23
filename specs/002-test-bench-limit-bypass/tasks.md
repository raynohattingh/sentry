# Tasks: Test Bench Limit Switch Bypass

**Input**: Design documents from `/specs/002-test-bench-limit-bypass/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Automated tests are required by the project constitution and are included below in TDD order where the feature introduces non-trivial logic.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`US1`, `US2`, `US3`)
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Introduce shared configuration and status-model scaffolding used across the feature.

- [X] T001 Add housing profile, test-bench bound, and status-topic configuration constants in `jetson/src/config.py`
- [X] T002 [P] Document `HOUSING_PROFILE`, test-bench bound, and `MQTT_STATUS_TOPIC` settings in `jetson/src/utils/config.yaml`
- [X] T003 [P] Create the app-side safety status model and topic constants in `app/lib/models/safety_status.dart` and `app/lib/services/mqtt_service.dart`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core runtime types and serial/event plumbing that block all user stories.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [X] T004 Add shared Jetson enums/dataclasses for housing profile, limit events, validation state, and safety status in `jetson/src/types.py`
- [X] T005 [P] Extend serial frame parsing tests for `LIMIT <axis> <direction>` messages in `jetson/tests/unit/test_serial_framing.py`
- [X] T006 Implement `LIMIT` frame parsing and typed return values in `jetson/src/comms/serial_io.py`
- [X] T007 [P] Add `ArduinoLink` limit-event tracking and validation-state tests in `jetson/tests/unit/test_arduino_link.py`
- [X] T008 Implement limit-event retention and validated-switch tracking in `jetson/src/hardware/arduino_link.py`

**Checkpoint**: Shared config, models, and serial plumbing are ready; user stories can now proceed.

---

## Phase 3: User Story 1 - Run the test bench without installed switches (Priority: P1) 🎯 MVP

**Goal**: Allow a test-bench sentry to boot and move without installed hardware limit switches, as long as valid software bounds are configured.

**Independent Test**: Configure Jetson with `HOUSING_PROFILE=TEST_BENCH` and valid pan/tilt bounds, start the runtime without installed switches, and verify bounded motion commands succeed without a limit-switch startup block.

### Tests for User Story 1 ⚠️

- [X] T009 [P] [US1] Add test-bench soft-bound and invalid-bound blocking coverage in `jetson/tests/unit/test_turret_manager.py`

### Implementation for User Story 1

- [X] T010 [US1] Implement test-bench software-bound enforcement and invalid-bound motion blocking in `jetson/src/control/turret_manager.py`
- [X] T011 [US1] Wire test-bench housing-profile startup handling into the main runtime flow in `jetson/src/main.py`
- [ ] T012 [US1] Add test-bench execution and validation notes for bounded motion in `specs/002-test-bench-limit-bypass/quickstart.md`
- [ ] T032 [US1] Document the persisted per-unit housing profile storage mechanism in `specs/002-test-bench-limit-bypass/quickstart.md` and `jetson/src/utils/config.yaml`

**Checkpoint**: User Story 1 is functional when a test-bench unit has valid software bounds configured.

---

## Phase 4: User Story 2 - Keep the temporary bypass explicit and safe (Priority: P2)

**Goal**: Expose an authoritative reduced-safety state to operators and keep motion visibly constrained to configured software bounds.

**Independent Test**: Run a test-bench unit with the bypass active, verify `sentry/status` publishes `SOFT_LIMIT_BYPASS`, and confirm the app shows the reduced-safety warning and blocked/allowed motion state in the map, override, and settings surfaces.

### Tests for User Story 2 ⚠️

- [X] T013 [P] [US2] Add Jetson safety-status payload tests for test-bench bypass mode in `jetson/tests/unit/test_safety_status.py`
- [X] T014 [P] [US2] Add Flutter parsing tests for safety-status records in `app/test/unit/safety_status_test.dart`
- [ ] T015 [P] [US2] Add Flutter UI coverage for the reduced-safety banner and override warning in `app/test/integration/safety_status_ui_test.dart`
- [ ] T030 [P] [US2] Add Jetson integration test for `LIMIT` frame ingestion to validation-state update in `jetson/tests/integration/test_limit_validation_flow.py`
- [ ] T031 [P] [US2] Add integration coverage for Jetson safety-status publish and app-side consumption in `jetson/tests/integration/test_safety_status_mqtt.py` and `app/test/integration/safety_status_mqtt_flow_test.dart`

### Implementation for User Story 2

- [X] T016 [US2] Implement asynchronous safety-status publication for test-bench mode in `jetson/src/comms/mqtt.py` and `jetson/src/main.py`
- [X] T017 [US2] Subscribe to `sentry/status` and expose safety-status state in `app/lib/services/mqtt_service.dart` and `app/lib/features/map/telemetry_provider.dart`
- [X] T018 [US2] Render the persistent reduced-safety banner on the home screen in `app/lib/features/map/map_screen.dart`
- [X] T019 [US2] Render blocked-motion and reduced-safety messaging in `app/lib/features/override/override_screen.dart`
- [X] T020 [US2] Surface the current housing/protection summary in `app/lib/features/settings/settings_screen.dart`
- [ ] T021 [US2] Document the app-visible reduced-safety behavior in `specs/002-test-bench-limit-bypass/contracts/mqtt-safety-status.md` and `specs/002-test-bench-limit-bypass/quickstart.md`

**Checkpoint**: User Story 2 is functional when operators can always see that a unit is running with the temporary bypass enabled.

---

## Phase 5: User Story 3 - Preserve MVP requirements for real switches (Priority: P3)

**Goal**: Block MVP motion until all four physical switches are validated and ensure the bypass remains scoped to test-bench units only.

**Independent Test**: Start one unit in `MVP` mode and verify motion stays blocked until `PAN LEFT`, `PAN RIGHT`, `TILT DOWN`, and `TILT UP` `LIMIT` events are observed; start a second unit in `TEST_BENCH` mode and verify the bypass remains available only there.

### Tests for User Story 3 ⚠️

- [X] T022 [P] [US3] Add MVP switch-validation progression and blocked-motion tests in `jetson/tests/unit/test_arduino_link.py` and `jetson/tests/unit/test_turret_manager.py`
- [ ] T023 [P] [US3] Add app-side MVP blocked-state rendering tests in `app/test/unit/safety_status_test.dart` and `app/test/integration/safety_status_ui_test.dart`
- [ ] T033 [P] [US3] Add profile-change tests for `TEST_BENCH -> MVP` bypass invalidation and validation reset in `jetson/tests/unit/test_turret_manager.py`

### Implementation for User Story 3

- [X] T024 [US3] Implement MVP startup validation state transitions from observed `LIMIT` events in `jetson/src/hardware/arduino_link.py` and `jetson/src/control/turret_manager.py`
- [X] T025 [US3] Publish validated-switch progress and MVP block reasons from `jetson/src/main.py` and `jetson/src/comms/mqtt.py`
- [X] T026 [US3] Render MVP validation progress and hardware-required messaging in `app/lib/features/map/map_screen.dart`, `app/lib/features/override/override_screen.dart`, and `app/lib/features/settings/settings_screen.dart`
- [ ] T027 [US3] Update MVP commissioning and switch-validation instructions in `specs/002-test-bench-limit-bypass/contracts/serial-limit-events.md` and `specs/002-test-bench-limit-bypass/quickstart.md`
- [ ] T034 [US3] Implement profile-change recomputation, bypass invalidation, and renewed motion blocking in `jetson/src/control/turret_manager.py` and `jetson/src/main.py`

**Checkpoint**: User Story 3 is functional when MVP units cannot move until real switch validation completes, while test-bench units still use the temporary bypass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cross-story documentation, and regression safety.

- [X] T028 [P] Update cross-project documentation for the new safety workflow in `README.md` and `jetson/src/utils/config.yaml`
- [ ] T029 Run feature validation from `specs/002-test-bench-limit-bypass/quickstart.md`, `jetson/tests/unit/`, `app/test/`, and `arduino/sentry_turret/test/`
- [ ] T036 [P] Measure the control-loop impact of safety gating and status publication, then record results in `specs/002-test-bench-limit-bypass/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories
- **Phase 3 (US1)**: Depends on Phase 2; delivers the MVP
- **Phase 4 (US2)**: Depends on Phase 2 and builds on the status scaffolding introduced earlier
- **Phase 5 (US3)**: Depends on Phase 2; recommended after US2 because it extends the same status surfaces
- **Phase 6 (Polish)**: Depends on completion of the desired user stories

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other user stories
- **US2 (P2)**: Starts after Foundational; can be validated independently once status publication exists
- **US3 (P3)**: Starts after Foundational; recommended after US2 because it extends the operator-facing safety-status presentation and profile-transition handling

### Within Each User Story

- Tests MUST be written and confirmed failing before implementation
- Jetson data/config work precedes runtime behavior changes
- MQTT publication precedes app subscription and UI rendering
- Documentation updates land with the behavior they describe

### Story Completion Order

`US1 -> US2 -> US3`

---

## Parallel Opportunities

- **Phase 1**: `T002` and `T003` can run in parallel after `T001`
- **Phase 2**: `T005` and `T007` can run in parallel after `T004`
- **US2**: `T013`, `T014`, `T015`, `T030`, and `T031` can run in parallel before implementation starts
- **US3**: `T022`, `T023`, and `T033` can run in parallel before implementation starts

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Add Jetson safety-status payload tests for test-bench bypass mode in jetson/tests/unit/test_safety_status.py"
Task: "Add Flutter parsing tests for safety-status records in app/test/unit/safety_status_test.dart"
Task: "Add Flutter UI coverage for the reduced-safety banner and override warning in app/test/integration/safety_status_ui_test.dart"
Task: "Add Jetson integration test for LIMIT frame ingestion to validation-state update in jetson/tests/integration/test_limit_validation_flow.py"
Task: "Add integration coverage for Jetson safety-status publish and app-side consumption in jetson/tests/integration/test_safety_status_mqtt.py and app/test/integration/safety_status_mqtt_flow_test.dart"
```

## Parallel Example: User Story 3

```bash
# Launch US3 validation tests together:
Task: "Add MVP switch-validation progression and blocked-motion tests in jetson/tests/unit/test_arduino_link.py and jetson/tests/unit/test_turret_manager.py"
Task: "Add app-side MVP blocked-state rendering tests in app/test/unit/safety_status_test.dart and app/test/integration/safety_status_ui_test.dart"
Task: "Add profile-change tests for TEST_BENCH -> MVP bypass invalidation and validation reset in jetson/tests/unit/test_turret_manager.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (US1)
3. Validate test-bench startup and bounded motion independently
4. Stop and demo the prototype-safe test-bench flow

### Incremental Delivery

1. Deliver **US1** to unblock prototype motion testing
2. Deliver **US2** to make the reduced-safety state obvious to operators
3. Deliver **US3** to restore strict MVP hardware gating
4. Finish with polish and full validation

### Parallel Team Strategy

1. One engineer handles Jetson config/types/serial foundations
2. One engineer prepares app safety-status model/tests after the status contract stabilizes
3. Rejoin for US2/US3 integration and full-system validation

---

## Notes

- All tasks follow the required checklist format with IDs, optional `[P]` markers, story labels where required, and concrete file paths
- The Arduino wire protocol remains unchanged; all commissioning logic is implemented by consuming existing `LIMIT` events
- The suggested MVP scope is **User Story 1 only**
