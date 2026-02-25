"""Unit tests for SentryBrain FSM — T021.

Tests all state transitions, dwell timer blocking, SEARCH timeout.
"""

import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
import config
from sentry_types import FSMState, ThreatAssessment, ThreatTier, TurretPosition


def _pos(pan=0, tilt=0):
    import datetime
    return TurretPosition(pan_steps=pan, tilt_steps=tilt,
                          received_utc=datetime.datetime.utcnow().isoformat() + "Z")


def _assessment(tid=1, score=90.0, tier=ThreatTier.HIGH, state=FSMState.ACQUIRE):
    return ThreatAssessment(
        target_id=tid, threat_score=score, tier=tier,
        lrf_required=True, recommended_state=state
    )


@pytest.fixture(autouse=True)
def zero_dwell(monkeypatch):
    """Set all dwell timers to 0 for instant transitions in most tests."""
    monkeypatch.setattr(config, "MIN_DWELL_MS_SCAN", 0)
    monkeypatch.setattr(config, "MIN_DWELL_MS_TRACK", 0)
    monkeypatch.setattr(config, "MIN_DWELL_MS_ACQUIRE", 0)
    monkeypatch.setattr(config, "MIN_DWELL_MS_SEARCH", 0)


def _fresh_brain():
    import importlib, control.sentry_brain as _sb
    importlib.reload(_sb)
    return _sb.SentryBrain()


class TestFSMTransitions:
    def test_initial_state_is_scan(self):
        brain = _fresh_brain()
        assert brain.state == FSMState.SCAN

    def test_scan_to_track_on_med_threat(self):
        brain = _fresh_brain()
        a = _assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)
        brain.update([a], _pos())
        assert brain.state == FSMState.TRACK

    def test_scan_to_acquire_on_high_threat(self):
        brain = _fresh_brain()
        a = _assessment(score=90.0, tier=ThreatTier.HIGH, state=FSMState.ACQUIRE)
        brain.update([a], _pos())
        assert brain.state == FSMState.ACQUIRE

    def test_track_to_acquire_on_high_threat(self):
        brain = _fresh_brain()
        brain.update([_assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)], _pos())
        assert brain.state == FSMState.TRACK
        brain.update([_assessment(score=90.0, tier=ThreatTier.HIGH, state=FSMState.ACQUIRE)], _pos())
        assert brain.state == FSMState.ACQUIRE

    def test_acquire_to_track_on_med_after_dwell(self):
        brain = _fresh_brain()
        brain.update([_assessment(score=90.0, tier=ThreatTier.HIGH, state=FSMState.ACQUIRE)], _pos())
        brain.update([_assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)], _pos())
        assert brain.state == FSMState.TRACK

    def test_track_to_scan_on_low_after_dwell(self):
        brain = _fresh_brain()
        brain.update([_assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)], _pos())
        brain.update([_assessment(score=10.0, tier=ThreatTier.LOW, state=FSMState.SCAN)], _pos())
        assert brain.state == FSMState.SCAN

    def test_to_search_on_empty_targets_from_track(self):
        brain = _fresh_brain()
        brain.update([_assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)], _pos())
        brain.update([], _pos())
        assert brain.state == FSMState.SEARCH

    def test_search_to_scan_on_timeout(self, monkeypatch):
        monkeypatch.setattr(config, "SEARCH_TIMEOUT_S", 0.0)
        brain = _fresh_brain()
        brain._state = FSMState.SEARCH
        brain._state_entered_ns = time.monotonic_ns() - int(1e9)
        brain._search_entered_s = time.monotonic() - 10.0
        brain.update([], _pos())
        assert brain.state == FSMState.SCAN

    def test_search_to_track_on_target_reacquired(self):
        brain = _fresh_brain()
        brain._state = FSMState.SEARCH
        brain._state_entered_ns = time.monotonic_ns()
        brain._search_entered_s = time.monotonic()
        brain.update([_assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)], _pos())
        assert brain.state == FSMState.TRACK


class TestDwellTimer:
    def test_downward_transition_blocked_before_dwell(self, monkeypatch):
        """ACQUIRE -> TRACK should be blocked while dwell timer is active."""
        monkeypatch.setattr(config, "MIN_DWELL_MS_ACQUIRE", 99999)
        brain = _fresh_brain()
        brain._state = FSMState.ACQUIRE
        brain._state_entered_ns = time.monotonic_ns()  # just entered
        brain.update([_assessment(score=50.0, tier=ThreatTier.MED, state=FSMState.TRACK)], _pos())
        assert brain.state == FSMState.ACQUIRE

    def test_upward_transition_immediate(self, monkeypatch):
        """SCAN -> ACQUIRE should be immediate regardless of dwell."""
        monkeypatch.setattr(config, "MIN_DWELL_MS_SCAN", 99999)
        brain = _fresh_brain()
        brain._state_entered_ns = time.monotonic_ns()
        brain.update([_assessment(score=90.0, tier=ThreatTier.HIGH, state=FSMState.ACQUIRE)], _pos())
        assert brain.state == FSMState.ACQUIRE
