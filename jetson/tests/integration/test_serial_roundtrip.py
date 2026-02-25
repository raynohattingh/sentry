"""Integration tests for Arduino serial roundtrip — T037."""

import sys, os, time, datetime, threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from sentry_types import LRFReading, TurretPosition


class _MockSerial:
    def __init__(self):
        self.written = []
        self.incoming = []
        self._connected = True

    @property
    def is_connected(self):
        return self._connected

    def write(self, data: bytes):
        self.written.append(data)

    def read_line(self):
        if self.incoming:
            return self.incoming.pop(0)
        return None

    def close(self):
        self._connected = False


@pytest.fixture
def link():
    mock_serial = _MockSerial()
    import importlib, hardware.arduino_link as _al; importlib.reload(_al)
    from hardware.arduino_link import ArduinoLink
    # Use the real constructor with injected mock serial
    l = ArduinoLink(serial_port=mock_serial)
    return l, mock_serial


def test_send_velocity_writes_correct_bytes(link):
    l, mock = link
    l.send_velocity(100.0, -50.0)
    assert b"V 100.00 -50.00\n" in mock.written


def test_fire_lrf_writes_l_command(link):
    l, mock = link
    l.fire_lrf()
    assert b"L\n" in mock.written


def test_send_zero_velocity(link):
    l, mock = link
    l.send_velocity(0.0, 0.0)
    assert b"V 0.00 0.00\n" in mock.written
