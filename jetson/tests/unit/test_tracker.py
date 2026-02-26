"""Unit tests for CentroidTracker — T012.

Tests:
- New detection gets next sequential ID
- Same detection in next frame keeps same ID
- Disappeared counter increments each frame without match
- Counter resets to 0 on re-match
- Target deregistered after max_disappeared frames
- Velocity vector computed from centroid delta
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from sentry_types import Detection  # loaded by conftest
from vision.tracker import CentroidTracker


def _d(cx: int, cy: int, w: int = 50, h: int = 80) -> Detection:
    x1, y1 = cx - w // 2, cy - h // 2
    x2, y2 = cx + w // 2, cy + h // 2
    return Detection(bbox=(x1, y1, x2, y2), confidence=0.9, class_id=0, centroid=(cx, cy), area=w * h)


def test_new_detection_gets_id():
    t = CentroidTracker(max_disappeared=5)
    targets = t.update([_d(100, 100)])
    assert len(targets) == 1
    assert isinstance(targets[0].target_id, int)


def test_two_detections_get_different_ids():
    t = CentroidTracker(max_disappeared=5)
    targets = t.update([_d(100, 100), _d(300, 100)])
    ids = {tgt.target_id for tgt in targets}
    assert len(ids) == 2


def test_same_detection_keeps_id():
    t = CentroidTracker(max_disappeared=5)
    d = _d(100, 100)
    id1 = t.update([d])[0].target_id
    id2 = t.update([d])[0].target_id
    assert id1 == id2


def test_nearby_detection_keeps_id():
    t = CentroidTracker(max_disappeared=5)
    id1 = t.update([_d(100, 100)])[0].target_id
    id2 = t.update([_d(105, 103)])[0].target_id
    assert id1 == id2


def test_disappeared_counter_increments():
    t = CentroidTracker(max_disappeared=10)
    t.update([_d(100, 100)])
    targets = t.update([])
    assert len(targets) == 1
    assert targets[0].disappeared_frames == 1


def test_disappeared_counter_increments_multiple():
    t = CentroidTracker(max_disappeared=10)
    t.update([_d(100, 100)])
    t.update([])
    targets = t.update([])
    assert targets[0].disappeared_frames == 2


def test_disappeared_resets_on_rematch():
    t = CentroidTracker(max_disappeared=10)
    t.update([_d(100, 100)])
    t.update([])  # 1 disappeared
    targets = t.update([_d(100, 100)])  # reappear
    assert targets[0].disappeared_frames == 0


def test_target_deregistered_after_max():
    t = CentroidTracker(max_disappeared=3)
    t.update([_d(100, 100)])
    for _ in range(4):
        t.update([])
    assert t.update([]) == []


def test_velocity_zero_first_frame():
    t = CentroidTracker(max_disappeared=5)
    targets = t.update([_d(100, 100)])
    assert targets[0].velocity_vector == (0.0, 0.0)


def test_velocity_reflects_delta():
    t = CentroidTracker(max_disappeared=5)
    t.update([_d(100, 100)])
    targets = t.update([_d(110, 105)])
    vx, vy = targets[0].velocity_vector
    assert vx == pytest.approx(10.0)
    assert vy == pytest.approx(5.0)
