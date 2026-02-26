"""Unit tests for ThreadedCamera — T013a."""

import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import numpy as np
import pytest
import logging
from unittest.mock import MagicMock, patch


def _make_mock_cap(ret=True, frame=None):
    if frame is None:
        frame = np.zeros((320, 480, 3), dtype=np.uint8)
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (ret, frame)
    cap.getBackendName.return_value = "V4L2"
    return cap


def test_read_returns_frame_when_open():
    with patch("cv2.VideoCapture", return_value=_make_mock_cap()):
        import importlib, vision.camera as _c; importlib.reload(_c)
        from vision.camera import ThreadedCamera
        cam = ThreadedCamera()
        cam.start()
        time.sleep(0.15)
        frame = cam.read()
        cam.stop()
    assert frame is not None
    assert hasattr(frame, 'data') and frame.data is not None


def test_is_open_false_after_stop():
    with patch("cv2.VideoCapture", return_value=_make_mock_cap()):
        import importlib, vision.camera as _c; importlib.reload(_c)
        from vision.camera import ThreadedCamera
        cam = ThreadedCamera()
        cam.start()
        assert cam.is_open
        cam.stop()
    assert not cam.is_open


def test_fallback_to_v4l2_when_gstreamer_fails():
    caps = [MagicMock(), _make_mock_cap()]
    caps[0].isOpened.return_value = False
    caps[0].getBackendName.return_value = "GSTREAMER"
    call_count = [0]

    def side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return caps[min(idx, len(caps) - 1)]

    with patch("cv2.VideoCapture", side_effect=side_effect):
        import importlib, vision.camera as _c; importlib.reload(_c)
        from vision.camera import ThreadedCamera
        cam = ThreadedCamera()
        cam.stop()
    assert call_count[0] >= 2  # attempted at least twice


def test_camera_log_prefix(caplog):
    with patch("cv2.VideoCapture", return_value=_make_mock_cap()):
        with caplog.at_level(logging.DEBUG):
            import importlib, vision.camera as _c; importlib.reload(_c)
            from vision.camera import ThreadedCamera
            cam = ThreadedCamera()
            cam.stop()
    camera_logs = [r for r in caplog.records if "[CAMERA]" in r.getMessage()]
    assert len(camera_logs) > 0
