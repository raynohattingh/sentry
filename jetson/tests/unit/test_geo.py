"""Unit tests for geo module — T026.

Tests:
- Haversine against known coordinate pair
- compute_target_gps returns (None, None) when distance_m is None
- heading offset via SENTRY_HEADING_DEG
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
import math


def _get_geo():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sentry_geo",
        os.path.join(os.path.dirname(__file__), "../../src/control/geo.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_haversine_100m_north():
    """100 m north from -26.0, 28.0 should be ~-25.9991, 28.0."""
    geo = _get_geo()
    lat, lon = geo.haversine(-26.0, 28.0, 0.0, 100.0)  # bearing=0 = north
    assert lat == pytest.approx(-25.9991, abs=0.0002)
    assert lon == pytest.approx(28.0, abs=0.0001)


def test_haversine_100m_east():
    """100 m east from 0.0, 0.0."""
    geo = _get_geo()
    lat, lon = geo.haversine(0.0, 0.0, 90.0, 100.0)
    assert lat == pytest.approx(0.0, abs=0.001)
    assert lon > 0.0


def test_compute_target_gps_returns_none_when_distance_none():
    geo = _get_geo()
    result = geo.compute_target_gps(-26.0, 28.0, 0.0, None)
    assert result == (None, None)


def test_compute_target_gps_valid():
    geo = _get_geo()
    lat, lon = geo.compute_target_gps(-26.0, 28.0, 0.0, 100.0)
    assert lat is not None
    assert lon is not None


def test_heading_offset_applied():
    """With heading=90, pan=0 should point east."""
    geo = _get_geo()
    import config
    orig = config.SENTRY_HEADING_DEG
    config.SENTRY_HEADING_DEG = 90.0
    lat, lon = geo.compute_target_gps(0.0, 0.0, 0.0, 1000.0)
    config.SENTRY_HEADING_DEG = orig
    # Heading 90 means east, so lon should increase
    assert lon > 0.0
