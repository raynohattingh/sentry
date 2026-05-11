"""Unit tests for TurretManager safety gating."""

import datetime
import importlib

import config


class _HardwareStub:
    def __init__(self, pan_steps=0, tilt_steps=0, validated=False):
        from sentry_types import TurretPosition

        self.current_position = TurretPosition(
            pan_steps=pan_steps,
            tilt_steps=tilt_steps,
            received_utc=datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        )
        self.validated_switches = ()
        self._validated = validated
        self.sent_commands: list[tuple[float, float]] = []

    def send_velocity(self, pan_velocity: float, tilt_velocity: float) -> None:
        self.sent_commands.append((pan_velocity, tilt_velocity))

    def all_required_switches_validated(self) -> bool:
        return self._validated


def _fresh_manager(monkeypatch, hardware, **overrides):
    for key, value in overrides.items():
        monkeypatch.setattr(config, key, value, raising=False)

    import control.turret_manager as _tm

    importlib.reload(_tm)
    return _tm.TurretManager(hardware=hardware)


def test_test_bench_allows_motion_inside_valid_bounds(monkeypatch):
    hardware = _HardwareStub(pan_steps=0, tilt_steps=0)
    manager = _fresh_manager(
        monkeypatch,
        hardware,
        HOUSING_PROFILE="TEST_BENCH",
        TEST_BENCH_PAN_MIN_STEPS=-100,
        TEST_BENCH_PAN_MAX_STEPS=100,
        TEST_BENCH_TILT_MIN_STEPS=-50,
        TEST_BENCH_TILT_MAX_STEPS=50,
    )

    manager.set_velocity(25.0, -15.0)

    assert manager.motion_allowed is True
    assert hardware.sent_commands[-1] == (25.0, -15.0)


def test_test_bench_blocks_outward_motion_at_configured_bound(monkeypatch):
    hardware = _HardwareStub(pan_steps=100, tilt_steps=-50)
    manager = _fresh_manager(
        monkeypatch,
        hardware,
        HOUSING_PROFILE="TEST_BENCH",
        TEST_BENCH_PAN_MIN_STEPS=-100,
        TEST_BENCH_PAN_MAX_STEPS=100,
        TEST_BENCH_TILT_MIN_STEPS=-50,
        TEST_BENCH_TILT_MAX_STEPS=50,
    )

    manager.set_velocity(30.0, -20.0)

    assert hardware.sent_commands[-1] == (0.0, 0.0)


def test_test_bench_allows_recovery_back_into_range(monkeypatch):
    hardware = _HardwareStub(pan_steps=100, tilt_steps=-50)
    manager = _fresh_manager(
        monkeypatch,
        hardware,
        HOUSING_PROFILE="TEST_BENCH",
        TEST_BENCH_PAN_MIN_STEPS=-100,
        TEST_BENCH_PAN_MAX_STEPS=100,
        TEST_BENCH_TILT_MIN_STEPS=-50,
        TEST_BENCH_TILT_MAX_STEPS=50,
    )

    manager.set_velocity(-30.0, 20.0)

    assert hardware.sent_commands[-1] == (-30.0, 20.0)


def test_invalid_test_bench_bounds_block_all_motion(monkeypatch):
    hardware = _HardwareStub(pan_steps=0, tilt_steps=0)
    manager = _fresh_manager(
        monkeypatch,
        hardware,
        HOUSING_PROFILE="TEST_BENCH",
        TEST_BENCH_PAN_MIN_STEPS=100,
        TEST_BENCH_PAN_MAX_STEPS=100,
        TEST_BENCH_TILT_MIN_STEPS=-50,
        TEST_BENCH_TILT_MAX_STEPS=50,
    )

    manager.set_velocity(25.0, 10.0)

    assert manager.motion_allowed is False
    assert manager.motion_block_reason == "INVALID_TEST_BENCH_BOUNDS"
    assert hardware.sent_commands[-1] == (0.0, 0.0)


def test_mvp_blocks_motion_until_switches_validated(monkeypatch):
    hardware = _HardwareStub(pan_steps=0, tilt_steps=0, validated=False)
    manager = _fresh_manager(
        monkeypatch,
        hardware,
        HOUSING_PROFILE="MVP",
        TEST_BENCH_PAN_MIN_STEPS=None,
        TEST_BENCH_PAN_MAX_STEPS=None,
        TEST_BENCH_TILT_MIN_STEPS=None,
        TEST_BENCH_TILT_MAX_STEPS=None,
    )

    manager.set_velocity(40.0, -20.0)

    assert manager.motion_allowed is False
    assert manager.motion_block_reason == "LIMIT_SWITCH_VALIDATION_REQUIRED"
    assert hardware.sent_commands[-1] == (0.0, 0.0)


def test_mvp_allows_motion_after_switches_validated(monkeypatch):
    hardware = _HardwareStub(pan_steps=0, tilt_steps=0, validated=True)
    manager = _fresh_manager(
        monkeypatch,
        hardware,
        HOUSING_PROFILE="MVP",
        TEST_BENCH_PAN_MIN_STEPS=None,
        TEST_BENCH_PAN_MAX_STEPS=None,
        TEST_BENCH_TILT_MIN_STEPS=None,
        TEST_BENCH_TILT_MAX_STEPS=None,
    )

    manager.set_velocity(40.0, -20.0)

    assert manager.motion_allowed is True
    assert hardware.sent_commands[-1] == (40.0, -20.0)
