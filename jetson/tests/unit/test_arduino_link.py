"""Unit tests for ArduinoLink limit-event tracking."""

import datetime
import importlib

from sentry_types import LimitAxis, LimitDirection, LimitEvent


def _fresh_link(mock_serial):
    import hardware.arduino_link as _al

    importlib.reload(_al)
    return _al.ArduinoLink(serial_port=mock_serial)


def _limit(axis: LimitAxis, direction: LimitDirection) -> LimitEvent:
    return LimitEvent(
        axis=axis,
        direction=direction,
        received_utc=datetime.datetime.utcnow().isoformat() + "Z",
    )


def test_limit_event_updates_last_event_and_switch_set(mock_serial):
    link = _fresh_link(mock_serial)
    event = _limit(LimitAxis.PAN, LimitDirection.LEFT)

    link._handle_parsed_frame(event)

    assert link.last_limit_event == event
    assert link.is_switch_validated("PAN_LEFT")
    assert set(link.validated_switches) == {"PAN_LEFT"}


def test_duplicate_limit_events_do_not_duplicate_switch_tracking(mock_serial):
    link = _fresh_link(mock_serial)
    event = _limit(LimitAxis.PAN, LimitDirection.LEFT)

    link._handle_parsed_frame(event)
    link._handle_parsed_frame(event)

    assert set(link.validated_switches) == {"PAN_LEFT"}


def test_all_required_switches_validated_after_all_four_events(mock_serial):
    link = _fresh_link(mock_serial)

    for axis, direction in (
        (LimitAxis.PAN, LimitDirection.LEFT),
        (LimitAxis.PAN, LimitDirection.RIGHT),
        (LimitAxis.TILT, LimitDirection.DOWN),
        (LimitAxis.TILT, LimitDirection.UP),
    ):
        link._handle_parsed_frame(_limit(axis, direction))

    assert link.all_required_switches_validated() is True


def test_reset_limit_validation_clears_progress(mock_serial):
    link = _fresh_link(mock_serial)
    link._handle_parsed_frame(_limit(LimitAxis.TILT, LimitDirection.UP))

    link.reset_limit_validation()

    assert link.last_limit_event is None
    assert link.validated_switches == ()
    assert link.all_required_switches_validated() is False
