"""Unit tests for TelemetryRecorder — T027."""

import sys, os, json, datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
import config
from sentry_types import TrackedTarget, ThreatAssessment, ThreatTier, FSMState, LRFReading, TurretPosition
from unittest.mock import MagicMock


def _pos(pan=0, tilt=0):
    return TurretPosition(pan_steps=pan, tilt_steps=tilt,
                          received_utc=datetime.datetime.utcnow().isoformat() + "Z")


def _assessment(tid=1):
    return ThreatAssessment(target_id=tid, threat_score=55.0, tier=ThreatTier.MED,
                            lrf_required=True, recommended_state=FSMState.TRACK)


def _target(tid=1):
    return TrackedTarget(target_id=tid, centroid=(240, 160), bbox=(190, 130, 290, 190),
                         velocity_vector=(1.0, 0.5), disappeared_frames=0, area=6000,
                         last_seen_utc=datetime.datetime.utcnow().isoformat() + "Z")


def _lrf(distance=100.0, valid=True):
    return LRFReading(distance_m=distance, valid=valid,
                      received_utc=datetime.datetime.utcnow().isoformat() + "Z")


@pytest.fixture
def mock_mqtt():
    m = MagicMock()
    m.published = []
    m.publish_async.side_effect = lambda p: m.published.append(p)
    return m


@pytest.fixture
def recorder(mock_mqtt, tmp_path, monkeypatch):
    log_file = str(tmp_path / "t.jsonl")
    monkeypatch.setattr(config, "TELEMETRY_LOG_PATH", log_file)
    monkeypatch.setattr(config, "LRF_ENABLED", True)
    import importlib, telemetry.recorder as _r; importlib.reload(_r)
    from telemetry.recorder import TelemetryRecorder
    return TelemetryRecorder(session_id="test-session", mqtt=mock_mqtt), mock_mqtt


@pytest.fixture
def recorder_no_lrf(mock_mqtt, tmp_path, monkeypatch):
    log_file = str(tmp_path / "t.jsonl")
    monkeypatch.setattr(config, "TELEMETRY_LOG_PATH", log_file)
    monkeypatch.setattr(config, "LRF_ENABLED", False)
    import importlib, telemetry.recorder as _r; importlib.reload(_r)
    from telemetry.recorder import TelemetryRecorder
    return TelemetryRecorder(session_id="test-session-nolrf", mqtt=mock_mqtt), mock_mqtt


def test_record_contains_session_id(recorder):
    rec, _ = recorder
    record = rec.record(_target(), _assessment(), _lrf(), _pos())
    assert record.session_id == "test-session"


def test_lrf_disabled_nulls_gps(recorder_no_lrf):
    rec, _ = recorder_no_lrf
    record = rec.record(_target(), _assessment(), _lrf(), _pos())
    assert record.lat is None
    assert record.lon is None
    assert record.lrf_distance_m is None


def test_emit_produces_valid_json(recorder, tmp_path):
    rec, _ = recorder
    record = rec.record(_target(), _assessment(), _lrf(), _pos())
    rec.emit(record)
    # Find the log file
    jsonl_files = list(tmp_path.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    with open(jsonl_files[0]) as f:
        line = f.readline()
    data = json.loads(line)
    assert data["session_id"] == "test-session"


def test_publish_async_called(recorder):
    rec, mqtt = recorder
    record = rec.record(_target(), _assessment(), _lrf(), _pos())
    rec.emit(record)
    assert mqtt.publish_async.called


def test_invalid_lrf_produces_null_distance(recorder):
    rec, _ = recorder
    record = rec.record(_target(), _assessment(), _lrf(valid=False, distance=None), _pos())
    assert record.lrf_distance_m is None
