"""Unit tests for ObjectDetector — T013b."""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

# Provide a mock ultralytics module if not installed
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


def _empty_results():
    result = MagicMock()
    result.boxes = []
    return [result]


@pytest.fixture(autouse=True)
def reload_detector():
    import importlib
    import vision.detector as _d
    importlib.reload(_d)
    yield


def test_detect_returns_list_of_detections():
    mock_model = MagicMock()
    mock_model.predict.return_value = _make_yolo_results([(100, 50, 200, 150, 0.9, 0)])
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)
    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    det = ObjectDetector()
    frame = np.zeros((320, 480, 3), dtype=np.uint8)
    results = det.detect(frame)
    assert isinstance(results, list)
    assert len(results) == 1
    from sentry_types import Detection
    assert isinstance(results[0], Detection)


def test_detect_correct_bbox():
    mock_model = MagicMock()
    mock_model.predict.return_value = _make_yolo_results([(100, 50, 200, 150, 0.9, 0)])
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)
    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    det = ObjectDetector()
    results = det.detect(np.zeros((320, 480, 3), dtype=np.uint8))
    assert results[0].bbox == (100, 50, 200, 150)
    assert results[0].confidence == pytest.approx(0.9, abs=0.01)
    assert results[0].class_id == 0


def test_detect_correct_centroid():
    mock_model = MagicMock()
    mock_model.predict.return_value = _make_yolo_results([(100, 50, 200, 150, 0.9, 0)])
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)
    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    det = ObjectDetector()
    results = det.detect(np.zeros((320, 480, 3), dtype=np.uint8))
    assert results[0].centroid == (150, 100)


def test_detect_empty_returns_empty_list():
    mock_model = MagicMock()
    mock_model.predict.return_value = _empty_results()
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)
    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    det = ObjectDetector()
    results = det.detect(np.zeros((320, 480, 3), dtype=np.uint8))
    assert results == []


def test_runtime_error_on_load_failure():
    sys.modules['ultralytics'].YOLO = MagicMock(side_effect=RuntimeError("engine not found"))
    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    with pytest.raises(RuntimeError, match=r"\[AI\]"):
        ObjectDetector()


def test_warmup_called_on_init():
    mock_model = MagicMock()
    mock_model.predict.return_value = _empty_results()
    sys.modules['ultralytics'].YOLO = MagicMock(return_value=mock_model)
    import importlib, vision.detector as _d; importlib.reload(_d)
    from vision.detector import ObjectDetector
    ObjectDetector()
    assert mock_model.predict.called
