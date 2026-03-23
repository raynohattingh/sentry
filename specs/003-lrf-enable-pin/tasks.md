# Tasks: LRF Enable Pin Configuration

**Input**: Design documents from `/specs/003-lrf-enable-pin/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Automated tests are required by the project constitution and are included below in TDD order for the new enable-pin behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this belongs to (`US1`, `US2`, `US3`)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the firmware configuration and feature-doc surfaces that the feature will use.

- [X] T001 Add the initial LRF enable configuration surface in `arduino/sentry_turret/src/config.h`
- [X] T002 [P] Prepare feature-level validation steps in `specs/003-lrf-enable-pin/quickstart.md`
- [X] T003 [P] Prepare feature-level behavior contract notes in `specs/003-lrf-enable-pin/contracts/lrf-enable-behavior.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared LRF enable abstractions and host-native test seams that all user stories depend on.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [X] T004 Add shared LRF enable state and helper declarations in `arduino/sentry_turret/src/lrf.h`
- [X] T005 [P] Add native test scaffolding for GPIO-style enable behavior in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`
- [X] T006 Implement host-testable LRF enable helpers in `arduino/sentry_turret/src/lrf.cpp`
- [X] T007 [P] Add inline documentation for the new enable-pin constants and active-low semantics in `arduino/sentry_turret/src/config.h`

**Checkpoint**: Shared enable-pin configuration and test seams are ready; user-story work can now proceed.

---

## Phase 3: User Story 1 - Power the LRF correctly from controller configuration (Priority: P1) 🎯 MVP

**Goal**: Add the dedicated active-low LRF enable control and make demand-driven ranging power the module only during active measurement windows.

**Independent Test**: Flash the firmware, leave the sentry idle, verify the LRF remains disabled, then trigger `CMD_LASER` and confirm the enable line goes low only for the ranging operation while normal `DIST` reporting still works.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST and confirm they fail before implementation**

- [X] T008 [P] [US1] Add native tests for active-low enable polarity and idle-disabled default state in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`
- [X] T009 [P] [US1] Add native tests for enable assertion during demand-triggered ranging in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`
- [X] T010 [P] [US1] Add automated end-to-end firmware flow coverage for `CMD_LASER -> enable assert -> successful read attempt -> enable deassert` in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`

### Implementation for User Story 1

- [X] T011 [US1] Add the named LRF enable pin and active/inactive level constants in `arduino/sentry_turret/src/config.h`
- [X] T012 [US1] Implement enable/deassert helper behavior in `arduino/sentry_turret/src/lrf.h` and `arduino/sentry_turret/src/lrf.cpp`
- [X] T013 [US1] Wire startup idle-disabled state and `CMD_LASER`-scoped enable control into `arduino/sentry_turret/src/sentry_turret.ino`
- [X] T014 [US1] Ensure the ranging workflow deasserts the enable line after measurement completion or timeout in `arduino/sentry_turret/src/sentry_turret.ino`

**Checkpoint**: User Story 1 should now provide correct active-low power control for demand-driven ranging.

---

## Phase 4: User Story 2 - Keep the enable behavior explicit for future hardware changes (Priority: P2)

**Goal**: Make the new enable pin and its active-low semantics easy for future maintainers to find and preserve.

**Independent Test**: Review the firmware configuration and feature docs and confirm they identify the LRF enable pin, state that low powers the module on, and describe that the line is asserted only during active ranging.

### Tests for User Story 2 ⚠️

- [X] T015 [P] [US2] Add native regression coverage that fails if default enable polarity is inverted in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`

### Implementation for User Story 2

- [X] T016 [US2] Refine `config.h` comments so the LRF enable pin assignment and active-low behavior are explicit for maintainers in `arduino/sentry_turret/src/config.h`
- [X] T017 [US2] Update LRF module interface documentation for idle-disabled and active-ranging semantics in `arduino/sentry_turret/src/lrf.h`
- [X] T018 [US2] Update feature-level maintainer guidance for wiring and runtime behavior in `specs/003-lrf-enable-pin/quickstart.md` and `specs/003-lrf-enable-pin/contracts/lrf-enable-behavior.md`

**Checkpoint**: User Stories 1 and 2 should both work independently, and the configuration intent should be obvious to future maintainers.

---

## Phase 5: User Story 3 - Fail safely when the enable control is unavailable or misconfigured (Priority: P3)

**Goal**: Ensure bad or missing enable control behavior results in predictable LRF-unavailable outcomes rather than silent false readiness.

**Independent Test**: Build or simulate firmware with missing/incorrect enable behavior and verify ranging does not appear healthy when the module is not properly powered.

### Tests for User Story 3 ⚠️

- [X] T019 [P] [US3] Add native tests for safe fallback when enable control is absent or not asserted for a measurement window in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`
- [X] T020 [P] [US3] Add native regression coverage for repeated ranging requests across enable/deassert cycles in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`
- [X] T021 [P] [US3] Add native coverage for boot-time recovery to idle-disabled state in `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`

### Implementation for User Story 3

- [X] T022 [US3] Add predictable LRF-unavailable handling around failed enable/ranging windows in `arduino/sentry_turret/src/sentry_turret.ino`
- [X] T023 [US3] Ensure repeated `CMD_LASER` operations re-enter and exit the active-low enable window safely in `arduino/sentry_turret/src/lrf.cpp` and `arduino/sentry_turret/src/sentry_turret.ino`
- [X] T024 [US3] Document failure expectations and validation outcomes in `specs/003-lrf-enable-pin/quickstart.md` and `specs/003-lrf-enable-pin/contracts/lrf-enable-behavior.md`

**Checkpoint**: All user stories should now be independently functional, including safe handling of missing or incorrect enable behavior.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cross-story regression safety.

- [X] T025 [P] Update repository-level firmware documentation for the new LRF enable control in `README.md`
- [X] T026 Run full Arduino native validation for this feature with `arduino/sentry_turret/test/test_lrf_frame/test_main.cpp`, `arduino/sentry_turret/test/test_serial_proto/test_main.cpp`, and `arduino/sentry_turret/platformio.ini`
- [ ] T027 [P] Perform hardware-in-the-loop validation of idle-disabled and active-ranging power behavior using `specs/003-lrf-enable-pin/quickstart.md`
- [X] T028 Record no-regression evidence for ranging latency and control-loop cadence in `specs/003-lrf-enable-pin/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately
- **Phase 2 (Foundational)**: Depends on Setup completion; blocks all user stories
- **Phase 3 (US1)**: Depends on Foundational; delivers the MVP
- **Phase 4 (US2)**: Depends on Foundational and builds on US1 behavior/docs
- **Phase 5 (US3)**: Depends on Foundational and extends the same LRF power-control flow
- **Phase 6 (Polish)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other user stories
- **US2 (P2)**: Starts after Foundational; recommended after US1 because it documents the implemented power-control behavior
- **US3 (P3)**: Starts after Foundational; recommended after US1 because it extends the same measurement-window logic with failure handling

### Within Each User Story

- Tests MUST be written and confirmed failing before implementation
- `config.h` changes precede logic changes that consume them
- LRF helper abstractions precede `.ino` orchestration
- Core behavior lands before documentation and HITL validation

### Parallel Opportunities

- **Phase 1**: `T002` and `T003` can run in parallel after `T001`
- **Phase 2**: `T005` and `T007` can run in parallel after `T004`
- **US1**: `T008`, `T009`, and `T010` can run in parallel before implementation starts
- **US3**: `T019`, `T020`, and `T021` can run in parallel before implementation starts
- **Polish**: `T025` and `T027` can run in parallel once implementation is complete

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Add native tests for active-low enable polarity and idle-disabled default state in arduino/sentry_turret/test/test_lrf_frame/test_main.cpp"
Task: "Add native tests for enable assertion during demand-triggered ranging in arduino/sentry_turret/test/test_lrf_frame/test_main.cpp"
Task: "Add automated end-to-end firmware flow coverage for CMD_LASER -> enable assert -> read attempt -> enable deassert in arduino/sentry_turret/test/test_lrf_frame/test_main.cpp"
```

## Parallel Example: User Story 3

```bash
# Launch US3 validation tests together:
Task: "Add native tests for safe fallback when enable control is absent or not asserted for a measurement window in arduino/sentry_turret/test/test_lrf_frame/test_main.cpp"
Task: "Add native regression coverage for repeated ranging requests across enable/deassert cycles in arduino/sentry_turret/test/test_lrf_frame/test_main.cpp"
Task: "Add native coverage for boot-time recovery to idle-disabled state in arduino/sentry_turret/test/test_lrf_frame/test_main.cpp"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate active-low power control independently on native tests and hardware

### Incremental Delivery

1. Deliver **US1** to get correct active-low demand-based LRF power behavior
2. Deliver **US2** to make the configuration and polarity explicit for future maintainers
3. Deliver **US3** to harden failure behavior and repeated-ranging handling
4. Finish with polish and full validation

### Parallel Team Strategy

1. One engineer handles `config.h` + `lrf.*` enable abstractions and native tests
2. One engineer prepares documentation updates in the feature docs/README
3. Rejoin for `.ino` orchestration and hardware validation

---

## Notes

- All tasks follow the required checklist format with IDs, optional `[P]` markers, story labels where required, and exact file paths
- The existing Jetson ↔ Arduino serial contract remains unchanged
- The suggested MVP scope is **User Story 1 only**
