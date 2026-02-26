"""Unit tests for SerialPort — T013c.

Tests:
- write() encodes to bytes
- read_line() returns None when buffer empty
- is_connected is False when port not open
- close() calls serial.close()
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def test_write_encodes_string():
    mock_serial_instance = MagicMock()
    mock_serial_instance.isOpen.return_value = True
    with patch("serial.Serial", return_value=mock_serial_instance):
        from comms.serial_io import SerialPort
        port = SerialPort()
        port._serial = mock_serial_instance
        port._connected = True
        port.write(b"V 1.00 2.00\n")
    mock_serial_instance.write.assert_called_once_with(b"V 1.00 2.00\n")


def test_read_line_returns_none_when_empty():
    mock_serial_instance = MagicMock()
    mock_serial_instance.readline.return_value = b""
    with patch("serial.Serial", return_value=mock_serial_instance):
        from comms.serial_io import SerialPort
        port = SerialPort()
        port._serial = mock_serial_instance
        port._connected = True
        result = port.read_line()
    assert result is None


def test_is_connected_false_when_not_open():
    from comms.serial_io import SerialPort
    port = SerialPort()
    assert not port.is_connected


def test_close_calls_serial_close():
    mock_serial_instance = MagicMock()
    mock_serial_instance.isOpen.return_value = True
    with patch("serial.Serial", return_value=mock_serial_instance):
        from comms.serial_io import SerialPort
        port = SerialPort()
        port._serial = mock_serial_instance
        port._connected = True
        port.close()
    mock_serial_instance.close.assert_called_once()
    assert not port.is_connected
