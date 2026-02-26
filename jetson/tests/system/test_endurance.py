"""System endurance test — T049a (72-hour soak).

This test is marked ``@pytest.mark.slow`` and is excluded from default CI.
It runs the full pipeline loop with a looped test video and MockSerial,
sampling FPS every 60 s and asserting heap growth < 50 MB over the full run.

Run with: pytest jetson/tests/system/test_endurance.py -v -m slow

NOTE: This test requires a test video file at ENDURANCE_VIDEO_PATH (env var)
and is intended to be executed on the Jetson hardware or a comparable Linux
workstation. Skip this test in offline / CI environments.
"""

import os
import sys
import tracemalloc
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))


@pytest.mark.slow
@pytest.mark.skip(reason="Hardware endurance test — run manually on Jetson (72h soak)")
def test_72h_endurance():
    """72-hour soak test: FPS >= 18 Hz, heap growth < 50 MB.

    Runs the vision pipeline loop with a looped test video and MockSerial.
    Samples FPS every 60 s via a stats queue.
    Tracks heap via tracemalloc every 5 minutes.

    This is a stub — full implementation requires physical Jetson hardware.
    """
    # Stub body — the actual soak loop would be wired in here.
    pass
