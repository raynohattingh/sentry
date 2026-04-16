"""Geodetic calculations for target GPS position estimation.

Uses pure-stdlib Haversine formula (math module only) — no external libraries
required on the offline Jetson.

Accuracy: ±2 m at distances < 2 km, which is well inside the ±10 m spec.

Reference: Decision 3 in specs/001-jetson-core/research.md.
"""

from __future__ import annotations

import logging
import math

import config

logger = logging.getLogger(__name__)

_geo_position_warned: bool = False

# Earth's mean radius in metres.
_EARTH_RADIUS_M: float = 6_371_000.0


def haversine(
    lat1: float,
    lon1: float,
    bearing_deg: float,
    distance_m: float,
) -> tuple[float, float]:
    """Compute the destination point given a start, bearing, and distance.

    Uses the Haversine forward formula on a spherical Earth model.

    Args:
        lat1: Starting latitude in decimal degrees (WGS-84).
        lon1: Starting longitude in decimal degrees (WGS-84).
        bearing_deg: True bearing from north in degrees [0, 360).
        distance_m: Distance to travel in metres.

    Returns:
        A (latitude, longitude) tuple in decimal degrees.

    Example:
        >>> lat, lon = haversine(-26.0, 28.0, 0.0, 100.0)
        >>> # lat ≈ -25.9991, lon ≈ 28.0
    """
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    bearing_r = math.radians(bearing_deg)

    angular_dist = distance_m / _EARTH_RADIUS_M

    sin_lat2 = (
        math.sin(lat1_r) * math.cos(angular_dist)
        + math.cos(lat1_r) * math.sin(angular_dist) * math.cos(bearing_r)
    )
    lat2_r = math.asin(max(-1.0, min(1.0, sin_lat2)))
    lon2_r = lon1_r + math.atan2(
        math.sin(bearing_r) * math.sin(angular_dist) * math.cos(lat1_r),
        math.cos(angular_dist) - math.sin(lat1_r) * math.sin(lat2_r),
    )

    lat2_deg = math.degrees(lat2_r)
    lon2_deg = math.degrees(lon2_r)
    # Normalise longitude to [-180, 180].
    lon2_deg = ((lon2_deg + 180.0) % 360.0) - 180.0
    return lat2_deg, lon2_deg


def bearing_from_pan(pan_steps: int) -> float:
    """Convert a pan step count to a true-north bearing in degrees.

    Args:
        pan_steps: Signed step count from the Arduino position feedback.

    Returns:
        True-north bearing in degrees [0, 360).
    """
    pan_degrees = pan_steps / config.STEPS_PER_DEGREE
    bearing = (pan_degrees + config.SENTRY_HEADING_DEG) % 360.0
    return bearing


def pan_tilt_to_azimuth(
    pan_steps: int,
    tilt_steps: int,
    heading_offset_deg: float,
) -> tuple[float, float]:
    """Convert step counts to azimuth and elevation angles.

    Args:
        pan_steps: Signed pan step count.
        tilt_steps: Signed tilt step count.
        heading_offset_deg: True-north offset at zero pan.

    Returns:
        A (azimuth_deg, elevation_deg) tuple.
    """
    azimuth = (pan_steps / config.STEPS_PER_DEGREE + heading_offset_deg) % 360.0
    elevation = tilt_steps / config.STEPS_PER_DEGREE
    return azimuth, elevation


def compute_target_gps(
    sentry_lat: float,
    sentry_lon: float,
    azimuth_deg: float,
    distance_m: float | None,
) -> tuple[float, float] | tuple[None, None]:
    """Compute target GPS coordinates from sentry position and LRF range.

    Args:
        sentry_lat: Sentry latitude in decimal degrees.
        sentry_lon: Sentry longitude in decimal degrees.
        azimuth_deg: True-north bearing to target in degrees.
        distance_m: LRF distance in metres, or None when unavailable.

    Returns:
        A (lat, lon) tuple in decimal degrees, or (None, None) when
        ``distance_m`` is None or zero.

    Example:
        >>> lat, lon = compute_target_gps(-26.0, 28.0, 0.0, 100.0)
    """
    global _geo_position_warned
    if not _geo_position_warned and sentry_lat == 0.0 and sentry_lon == 0.0:
        logger.warning(
            "[GEO] SENTRY_LAT and SENTRY_LON are both 0.0 — "
            "computed target GPS coordinates will be meaningless."
        )
        _geo_position_warned = True

    if distance_m is None or distance_m <= 0:
        return None, None  # type: ignore[return-value]

    # azimuth_deg is already a true-north bearing (caller applies heading offset).
    true_bearing = azimuth_deg % 360.0
    return haversine(sentry_lat, sentry_lon, true_bearing, distance_m)
