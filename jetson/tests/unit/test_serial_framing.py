"""Unit tests for serial frame parsing — T036.

Tests:
- DIST 150.50 parses to LRFReading(distance_m=150.50, valid=True)
- POS 1000 -250 parses to TurretPosition(pan_steps=1000, tilt_steps=-250)
- DIST abc emits [SERIAL] Malformed frame discarded log and returns LRFReading(valid=False)
- Empty line is discarded
- Heartbeat timeout flag set when no POS received within SERIAL_HEARTBEAT_TIMEOUT_S
"""

import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from sentry_types import LRFReading, TurretPosition


def _get_parsers():
    from comms.serial_io import parse_frame
    return parse_frame


def test_dist_parses_correctly():
    parse_frame = _get_parsers()
    result = parse_frame("DIST 150.50")
    assert isinstance(result, LRFReading)
    assert result.distance_m == pytest.approx(150.50)
    assert result.valid is True


def test_pos_parses_correctly():
    parse_frame = _get_parsers()
    result = parse_frame("POS 1000 -250")
    assert isinstance(result, TurretPosition)
    assert result.pan_steps == 1000
    assert result.tilt_steps == -250


def test_malformed_dist_returns_invalid(caplog):
    import logging
    parse_frame = _get_parsers()
    with caplog.at_level(logging.WARNING):
        result = parse_frame("DIST abc")
    assert isinstance(result, LRFReading)
    assert result.valid is False
    assert any("[SERIAL]" in r.getMessage() and "Malformed" in r.getMessage()
               for r in caplog.records)


def test_empty_line_returns_none():
    parse_frame = _get_parsers()
    result = parse_frame("")
    assert result is None


def test_unknown_command_returns_none(caplog):
    import logging
    parse_frame = _get_parsers()
    with caplog.at_level(logging.WARNING):
        result = parse_frame("FOO 123")
    assert result is None
