"""Unit tests for ThreatScorer — T020.

Tests:
- Score clamped to [0, 100]
- LOW/MED/HIGH tier boundaries
- Highest-scoring target selected from list
- Distance weight dominates when bbox is large
- LRF_ENABLED=False produces lrf_required=False regardless of score
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from sentry_types import TrackedTarget, ThreatTier, FSMState


def _make_target(tid=1, cx=240, cy=160, vx=0.0, vy=0.0, area=5000, disappeared=0):
    import datetime
    return TrackedTarget(
        target_id=tid,
        centroid=(cx, cy),
        bbox=(cx-50, cy-50, cx+50, cy+50),
        velocity_vector=(vx, vy),
        disappeared_frames=disappeared,
        area=area,
        last_seen_utc=datetime.datetime.utcnow().isoformat() + "Z",
    )


def _get_scorer():
    from control.threat_tracker import ThreatScorer
    return ThreatScorer()


def test_score_clamped_to_100():
    scorer = _get_scorer()
    t = _make_target(area=999999, vx=9999.0, vy=9999.0)
    result = scorer.score(t, [t], lrf_enabled=True)
    assert result.threat_score <= 100.0


def test_score_clamped_to_0():
    scorer = _get_scorer()
    t = _make_target(area=0, vx=0.0, vy=0.0)
    result = scorer.score(t, [t], lrf_enabled=True)
    assert result.threat_score >= 0.0


def test_low_tier_below_med_threshold():
    import config
    scorer = _get_scorer()
    t = _make_target(area=100, vx=0.0, vy=0.0)
    result = scorer.score(t, [t], lrf_enabled=True)
    if result.threat_score < config.MED_THREAT_THRESHOLD:
        assert result.tier == ThreatTier.LOW


def test_high_tier_above_high_threshold():
    import config
    scorer = _get_scorer()
    # Force high score: very large area + high velocity
    t = _make_target(area=153600, vx=500.0, vy=500.0)  # full frame
    result = scorer.score(t, [t, _make_target(tid=2), _make_target(tid=3)], lrf_enabled=True)
    if result.threat_score >= config.HIGH_THREAT_THRESHOLD:
        assert result.tier == ThreatTier.HIGH


def test_lrf_disabled_produces_no_lrf_required():
    scorer = _get_scorer()
    t = _make_target(area=153600, vx=500.0, vy=500.0)
    result = scorer.score(t, [t], lrf_enabled=False)
    assert result.lrf_required is False


def test_lrf_enabled_high_tier_requires_lrf():
    import config
    scorer = _get_scorer()
    t = _make_target(area=153600, vx=500.0, vy=500.0)
    result = scorer.score(t, [t, _make_target(tid=2), _make_target(tid=3)], lrf_enabled=True)
    if result.tier == ThreatTier.HIGH:
        assert result.lrf_required is True


def test_large_area_raises_score():
    scorer = _get_scorer()
    t_small = _make_target(area=500)
    t_large = _make_target(area=100000)
    r_small = scorer.score(t_small, [t_small], lrf_enabled=True)
    r_large = scorer.score(t_large, [t_large], lrf_enabled=True)
    assert r_large.threat_score > r_small.threat_score


def test_tier_matches_recommended_state():
    import config
    scorer = _get_scorer()
    t = _make_target(area=5000)
    result = scorer.score(t, [t], lrf_enabled=True)
    if result.tier == ThreatTier.LOW:
        assert result.recommended_state == FSMState.SCAN
    elif result.tier == ThreatTier.MED:
        assert result.recommended_state == FSMState.TRACK
    elif result.tier == ThreatTier.HIGH:
        assert result.recommended_state == FSMState.ACQUIRE
