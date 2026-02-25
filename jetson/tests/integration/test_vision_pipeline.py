"""Integration tests for the vision pipeline — T013."""

import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import numpy as np
import pytest
from unittest.mock import MagicMock

# Provide mock ultralytics if not installed
if 'ultralytics' not in sys.modules:
    import types
    _ult = types.ModuleType('ultralytics')
    _ult.YOLO = MagicMock()
    sys.modules['ultralytics'] = _ult


def _make_yolo_results(boxes):
    result = MagicMock()
    mock_boxes = []
    for x1, y1, x2, y2, conf, cls in boxes:
        b = MagicMock()
        b.xyxy = [np.array([x1, y1, x2, y2], dtype=float)]
        b.conf = [conf]
        b.cls = [cls]
        mock_boxes.append(b)
    result.boxes = mock_boxes
    return [result]


def test_offcenter_target_produces_nonzero_velocity():
    mock_model = MagicMock()
    mock_model.predict.return_value = _make_yolo_results([(310, 100, 390, 200, 0.9, 0)])
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)

    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    from vision.tracker import CentroidTracker
    from control.pid import PIDController
    import config

    detector = ObjectDetector()
    tracker = CentroidTracker()
    pan_pid = PIDController(config.PAN_KP, config.PAN_KI, config.PAN_KD, config.PAN_MAX)

    frame = np.zeros((320, 480, 3), dtype=np.uint8)
    detections = detector.detect(frame)
    targets = tracker.update(detections)
    assert len(targets) > 0

    err_x = targets[0].centroid[0] - config.CENTER_X
    time.sleep(0.05)
    v_pan = pan_pid.update(err_x)
    assert v_pan != 0.0


def test_centred_target_produces_zero_velocity():
    mock_model = MagicMock()
    # Target at exact centre (240, 160) — bbox (215,140)-(265,180)
    mock_model.predict.return_value = _make_yolo_results([(215, 140, 265, 180, 0.9, 0)])
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)

    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    from vision.tracker import CentroidTracker
    from control.pid import PIDController
    import config

    detector = ObjectDetector()
    tracker = CentroidTracker()
    pan_pid = PIDController(config.PAN_KP, config.PAN_KI, config.PAN_KD, config.PAN_MAX)

    frame = np.zeros((320, 480, 3), dtype=np.uint8)
    detections = detector.detect(frame)
    targets = tracker.update(detections)
    err_x = targets[0].centroid[0] - config.CENTER_X
    if abs(err_x) < config.DEAD_ZONE:
        err_x = 0
    time.sleep(0.05)
    v_pan = pan_pid.update(err_x)
    assert v_pan == pytest.approx(0.0, abs=1.0)
