import 'dart:math' as math;

import 'package:latlong2/latlong.dart';

/// Geospatial utility functions.
class GeoUtils {
  GeoUtils._();

  /// Haversine distance between two [LatLng] coordinates in metres.
  static double distanceBetweenMetres(LatLng a, LatLng b) {
    const r = 6371000.0; // Earth radius in metres
    final lat1 = _deg2rad(a.latitude);
    final lat2 = _deg2rad(b.latitude);
    final dLat = _deg2rad(b.latitude - a.latitude);
    final dLon = _deg2rad(b.longitude - a.longitude);

    final h =
        math.sin(dLat / 2) * math.sin(dLat / 2) +
            math.cos(lat1) *
                math.cos(lat2) *
                math.sin(dLon / 2) *
                math.sin(dLon / 2);
    final c = 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h));
    return r * c;
  }

  /// Optionally computes distance when [userLocation] may be null.
  static double? distanceOrNull(LatLng? userLocation, LatLng target) {
    if (userLocation == null) return null;
    return distanceBetweenMetres(userLocation, target);
  }

  /// Rotates [raw] GPS coordinate around [sentryOrigin] by [offsetDegrees]
  /// (True North offset calibration — FR-021).
  ///
  /// Algorithm:
  ///   1. Convert raw position relative to sentry to polar (bearing, distance).
  ///   2. Subtract [offsetDegrees] from the bearing.
  ///   3. Convert corrected polar back to lat/lon.
  static LatLng applyNorthOffset(
      LatLng raw, LatLng sentryOrigin, double offsetDegrees) {
    if (offsetDegrees == 0.0) return raw;

    const r = 6371000.0;
    final lat1 = _deg2rad(sentryOrigin.latitude);
    final lon1 = _deg2rad(sentryOrigin.longitude);
    final lat2 = _deg2rad(raw.latitude);
    final lon2 = _deg2rad(raw.longitude);

    // Distance from sentry to target
    final dLat = lat2 - lat1;
    final dLon = lon2 - lon1;
    final a =
        math.sin(dLat / 2) * math.sin(dLat / 2) +
            math.cos(lat1) * math.cos(lat2) * math.sin(dLon / 2) * math.sin(dLon / 2);
    final d = r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));

    // Bearing from sentry to target (degrees, 0=North, CW)
    final y = math.sin(lon2 - lon1) * math.cos(lat2);
    final x =
        math.cos(lat1) * math.sin(lat2) -
            math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1);
    final bearingRad = math.atan2(y, x);
    final bearingDeg = (_rad2deg(bearingRad) + 360) % 360;

    // Apply offset (subtract to correct: if North is actually 10° East, rotate -10°)
    final correctedBearing = (bearingDeg - offsetDegrees + 360) % 360;

    // Convert corrected bearing + distance back to lat/lon
    final angDist = d / r;
    final corrRad = _deg2rad(correctedBearing);

    final newLatRad = math.asin(
      math.sin(lat1) * math.cos(angDist) +
          math.cos(lat1) * math.sin(angDist) * math.cos(corrRad),
    );
    final newLonRad = lon1 +
        math.atan2(
          math.sin(corrRad) * math.sin(angDist) * math.cos(lat1),
          math.cos(angDist) - math.sin(lat1) * math.sin(newLatRad),
        );

    return LatLng(_rad2deg(newLatRad), _rad2deg(newLonRad));
  }

  static double _deg2rad(double deg) => deg * math.pi / 180.0;
  static double _rad2deg(double rad) => rad * 180.0 / math.pi;
}
