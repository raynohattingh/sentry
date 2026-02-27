"""Unit tests for enriched TelemetryRecord fields — T004 (FR-010a / FR-004a).

Tests velocity_vector pixel→m/s conversion and fsm_state propagation.
"""

import sys, os, datetime, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
import config
from unittest.mock import MagicMock, patch
from sentry_types import TrackedTarget, ThreatAssessment, ThreatTier, FSMState, LRFReading, TurretPosition
from telemetry.recorder import TelemetryRecorder, _convert_velocity


def _pos(pan=0, tilt=0):
    return TurretPosition(pan_steps=pan, tilt_steps=tilt,
                          received_utc=datetime.datetime.utcnow().isoformat() + "Z")


def _assessment(tid=1):
    return ThreatAssessment(target_id=tid, threat_score=55.0, tier=ThreatTier.MED,
                            lrf_required=True, recommended_state=FSMState.TRACK)


def _target(vx=2.0, vy=1.0, tid=1):
    return TrackedTarget(target_id=tid, centroid=(240, 160), bbox=(190, 130, 290, 190),
                         velocity_vector=(vx, vy), disappeared_frames=0, area=6000,
                         last_seen_utc=datetime.datetime.utcnow().isoformat() + "Z")


def _lrf(distance=50.0, valid=True):
    return LRFReading(distance_m=distance, valid=valid,
                      received_utc=datetime.datetime.utcnow().isoformat() + "Z")


@pytest.fixture
def recorder(tmp_path, monkeypatch):
    mock_mqtt = MagicMock()
    monkeypatch.setattr(config, "TELEMETRY_LOG_PATH", str(tmp_path / "t.jsonl"))
    monkeypatch.setattr(config, "LRF_ENABLED", True)
    import importlib, telemetry.recorder as _r; importlib.reload(_r)
    from telemetry.recorder import TelemetryRecorder
    return TelemetryRecorder(session_id="enrich-session", mqtt=mock_mqtt)


def test_velocity_vector_none_when_lrf_disabled(recorder, monkeypatch):
    monkeypatch.setattr(config, "LRF_ENABLED", False)
    rec = recorder.record(_target(), _assessment(), _lrf(), _pos(), fsm_state=FSMState.SCAN)
    assert rec.velocity_vector is None


def test_velocity_vector_none_when_lrf_invalid(recorder):
    rec = recorder.record(_target(), _assessment(), _lrf(valid=False, distance=None), _pos(),
                          fsm_state=FSMState.SCAN)
    assert rec.velocity_vector is None


def test_velocity_vector_has_vx_vy_keys(recorder):
    rec = recorder.record(_target(vx=3.0, vy=1.5), _assessment(), _lrf(distance=50.0), _pos(),
                          fsm_state=FSMState.TRACK)
    assert rec.velocity_vector is not None
    assert "vx" in rec.velocity_vector
    assert "vy" in rec.velocity_vector


def test_velocity_vector_conversion_formula(recorder):
    """Verify pixel→m/s matches pinhole camera model formula."""
    lrf_m = 50.0
    vx_px = 3.0
    vy_px = 1.5
    focal_px = (config.CAMERA_WIDTH / 2.0) / math.tan(math.radians(config.CAMERA_HFOV_DEG / 2.0))
    expected_vx = (vx_px * lrf_m) / (focal_px * config.CAMERA_FPS)
    expected_vy = (vy_px * lrf_m) / (focal_px * config.CAMERA_FPS)

    rec = recorder.record(_target(vx=vx_px, vy=vy_px), _assessment(), _lrf(distance=lrf_m), _pos(),
                          fsm_state=FSMState.TRACK)
    assert rec.velocity_vector["vx"] == pytest.approx(expected_vx, rel=1e-6)
    assert rec.velocity_vector["vy"] == pytest.approx(expected_vy, rel=1e-6)


def test_fsm_state_scan_propagates(recorder):
    rec = recorder.record(_target(), _assessment(), _lrf(), _pos(), fsm_state=FSMState.SCAN)
    assert rec.fsm_state == "SCAN"


def test_fsm_state_manual_override_propagates(recorder):
    rec = recorder.record(_target(), _assessment(), _lrf(), _pos(), fsm_state=FSMState.MANUAL_OVERRIDE)
    assert rec.fsm_state == "MANUAL_OVERRIDE"
