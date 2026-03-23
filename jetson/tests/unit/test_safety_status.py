"""Unit tests for TurretManager safety-status payloads."""

import datetime
import importlib

import config


class _HardwareStub:
    def __init__(self, validated=False, validated_switches=()):
        from sentry_types import TurretPosition

        self.current_position = TurretPosition(
            pan_steps=0,
            tilt_steps=0,
            received_utc=datetime.datetime.now(datetime.UTC)
            .isoformat()
            .replace("+00:00", "Z"),
        )
        self._validated = validated
        self.validated_switches = validated_switches

    def send_velocity(self, pan_velocity: float, tilt_velocity: float) -> None:
        return None

    def all_required_switches_validated(self) -> bool:
        return self._validated


def _fresh_manager(monkeypatch, hardware, **overrides):
    for key, value in overrides.items():
        monkeypatch.setattr(config, key, value, raising=False)

    import control.turret_manager as _tm

    importlib.reload(_tm)
    return _tm.TurretManager(hardware=hardware)


def test_test_bench_status_reports_soft_limit_bypass(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_ID", "unit-1", raising=False)
    manager = _fresh_manager(
        monkeypatch,
        _HardwareStub(),
        HOUSING_PROFILE="TEST_BENCH",
        TEST_BENCH_PAN_MIN_STEPS=-100,
        TEST_BENCH_PAN_MAX_STEPS=100,
        TEST_BENCH_TILT_MIN_STEPS=-50,
        TEST_BENCH_TILT_MAX_STEPS=50,
    )

    status = manager.get_safety_status()

    assert status.to_dict()["housing_profile"] == "TEST_BENCH"
    assert status.to_dict()["protection_mode"] == "SOFT_LIMIT_BYPASS"
    assert status.to_dict()["motion_allowed"] is True
    assert status.to_dict()["validated_switches"] == []


def test_mvp_pending_status_reports_validation_progress(monkeypatch):
    monkeypatch.setattr(config, "SENTRY_ID", "unit-2", raising=False)
    manager = _fresh_manager(
        monkeypatch,
        _HardwareStub(validated=False, validated_switches=("PAN_LEFT", "PAN_RIGHT")),
        HOUSING_PROFILE="MVP",
        TEST_BENCH_PAN_MIN_STEPS=None,
        TEST_BENCH_PAN_MAX_STEPS=None,
        TEST_BENCH_TILT_MIN_STEPS=None,
        TEST_BENCH_TILT_MAX_STEPS=None,
    )

    status = manager.get_safety_status()

    assert status.to_dict()["housing_profile"] == "MVP"
    assert status.to_dict()["protection_mode"] == "HARDWARE_VALIDATION_PENDING"
    assert status.to_dict()["motion_allowed"] is False
    assert status.to_dict()["motion_block_reason"] == "LIMIT_SWITCH_VALIDATION_REQUIRED"
    assert status.to_dict()["validated_switches"] == ["PAN_LEFT", "PAN_RIGHT"]
