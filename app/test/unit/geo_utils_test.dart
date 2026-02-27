import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:sentry_mobile/utils/geo_utils.dart';

void main() {
  group('GeoUtils.distanceBetweenMetres', () {
    test('known coordinates produce expected distance within 1 m', () {
      // Johannesburg CBD to Sandton (approx 20.5 km)
      final a = LatLng(-26.2041, 28.0473);
      final b = LatLng(-26.1075, 28.0567);
      final d = GeoUtils.distanceBetweenMetres(a, b);
      expect(d, closeTo(10800, 500)); // ~10.8 km, allow 500 m margin
    });

    test('same point returns 0 distance', () {
      final p = LatLng(-26.2041, 28.0473);
      expect(GeoUtils.distanceBetweenMetres(p, p), closeTo(0, 0.01));
    });

    test('null location returns null via distanceOrNull', () {
      final target = LatLng(-26.2041, 28.0473);
      expect(GeoUtils.distanceOrNull(null, target), isNull);
    });

    test('non-null location returns distance via distanceOrNull', () {
      final a = LatLng(-26.2041, 28.0473);
      final b = LatLng(-26.2041, 28.0573);
      final d = GeoUtils.distanceOrNull(a, b);
      expect(d, isNotNull);
      expect(d!, greaterThan(0));
    });
  });

  group('GeoUtils.applyNorthOffset', () {
    test('zero offset returns same position', () {
      final sentry = LatLng(0.0, 0.0);
      final target = LatLng(0.01, 0.0); // North of sentry
      final result = GeoUtils.applyNorthOffset(target, sentry, 0.0);
      expect(result.latitude, closeTo(target.latitude, 0.0001));
      expect(result.longitude, closeTo(target.longitude, 0.0001));
    });

    test('90-degree offset: target at 0 deg bearing appears at 270 deg (H1)', () {
      // Sentry at origin; target is due North (0° bearing, small distance).
      // With 90° North offset: reported 0° → corrected 360°-90° = 270° (West).
      final sentry = LatLng(0.0, 0.0);
      // A point ~1km due North
      final target = LatLng(0.009, 0.0); // ~1km North, bearing ≈ 0°
      final corrected = GeoUtils.applyNorthOffset(target, sentry, 90.0);

      // After 90° correction the corrected bearing should be West (~270°)
      // i.e. longitude should be negative (West), latitude near 0
      expect(corrected.longitude, lessThan(0.0),
          reason: 'Corrected position should be West of sentry (270°)');
      expect(corrected.latitude.abs(), lessThan(0.001),
          reason: 'Corrected latitude should be near equator');
    });

    test('180-degree offset flips direction', () {
      final sentry = LatLng(0.0, 0.0);
      final target = LatLng(0.009, 0.0); // due North
      final corrected = GeoUtils.applyNorthOffset(target, sentry, 180.0);
      // 0° bearing - 180° offset = 180° (South) → latitude should be negative
      expect(corrected.latitude, lessThan(0.0));
    });
  });
}
