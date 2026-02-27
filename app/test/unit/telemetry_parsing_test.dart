import 'package:flutter_test/flutter_test.dart';

import 'package:sentry_mobile/models/telemetry_record.dart';
import 'package:sentry_mobile/models/threat_marker.dart';

void main() {
  group('TelemetryRecord.fromJson', () {
    test('valid full message parses correctly', () {
      final json = {
        'session_id': 'abc-123',
        'target_id': 42,
        'threat_score': 75.5,
        'tier': 'MED',
        'lat': -26.2041,
        'lon': 28.0473,
        'lrf_distance_m': 150.0,
        'pan_angle': 45.0,
        'tilt_angle': -10.0,
        'timestamp_utc': '2025-01-01T12:00:00.000Z',
        'velocity_vector': {'vx': 1.5, 'vy': -0.5},
        'fsm_state': 'TRACK',
      };
      final record = TelemetryRecord.fromJson(json);
      expect(record.sessionId, equals('abc-123'));
      expect(record.targetId, equals(42));
      expect(record.threatScore, closeTo(75.5, 0.01));
      expect(record.tier, equals(ThreatTier.med));
      expect(record.lat, closeTo(-26.2041, 0.0001));
      expect(record.lon, closeTo(28.0473, 0.0001));
      expect(record.lrfDistanceM, closeTo(150.0, 0.01));
      expect(record.panAngle, closeTo(45.0, 0.01));
      expect(record.tiltAngle, closeTo(-10.0, 0.01));
      expect(record.velocityVector?.vx, closeTo(1.5, 0.01));
      expect(record.fsmState, equals(FsmState.track));
    });

    test('null lat/lon is permitted', () {
      final json = {
        'session_id': 'sess-1',
        'target_id': 1,
        'threat_score': 20.0,
        'tier': 'LOW',
        'lat': null,
        'lon': null,
        'pan_angle': 0.0,
        'tilt_angle': 0.0,
        'timestamp_utc': '2025-01-01T00:00:00.000Z',
      };
      final record = TelemetryRecord.fromJson(json);
      expect(record.lat, isNull);
      expect(record.lon, isNull);
    });

    test('unknown tier defaults to low', () {
      final json = {
        'session_id': 'sess-1',
        'target_id': 1,
        'threat_score': 10.0,
        'tier': 'UNKNOWN_TIER',
        'pan_angle': 0.0,
        'tilt_angle': 0.0,
        'timestamp_utc': '2025-01-01T00:00:00.000Z',
      };
      final record = TelemetryRecord.fromJson(json);
      expect(record.tier, equals(ThreatTier.low));
    });

    test('null velocity_vector parses to null', () {
      final json = {
        'session_id': 'sess-1',
        'target_id': 1,
        'threat_score': 50.0,
        'tier': 'MED',
        'pan_angle': 0.0,
        'tilt_angle': 0.0,
        'timestamp_utc': '2025-01-01T00:00:00.000Z',
        'velocity_vector': null,
      };
      final record = TelemetryRecord.fromJson(json);
      expect(record.velocityVector, isNull);
    });

    test('null fsm_state parses to null', () {
      final json = {
        'session_id': 'sess-1',
        'target_id': 1,
        'threat_score': 50.0,
        'tier': 'MED',
        'pan_angle': 0.0,
        'tilt_angle': 0.0,
        'timestamp_utc': '2025-01-01T00:00:00.000Z',
        'fsm_state': null,
      };
      final record = TelemetryRecord.fromJson(json);
      expect(record.fsmState, isNull);
    });

    test('malformed JSON throws FormatException', () {
      // Missing required field target_id
      expect(
        () => TelemetryRecord.fromJson({
          'session_id': 'sess-1',
          'threat_score': 50.0,
          'tier': 'MED',
          'pan_angle': 0.0,
          'tilt_angle': 0.0,
          'timestamp_utc': 'not-a-date',
        }),
        throwsA(isA<FormatException>()),
      );
    });
  });
}
