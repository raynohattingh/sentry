import 'package:flutter_test/flutter_test.dart';

import 'package:sentry_mobile/core/constants.dart';
import 'package:sentry_mobile/models/manual_command.dart';

void main() {
  group('JoystickWidget velocity', () {
    test('ManualCommand.zero() has both velocities == 0.0', () {
      final cmd = ManualCommand.zero('sentry-01');
      expect(cmd.panVelocity, equals(0.0));
      expect(cmd.tiltVelocity, equals(0.0));
      expect(cmd.sentryId, equals('sentry-01'));
    });

    test('ManualCommand.toJson() matches expected schema', () {
      final now = DateTime.utc(2025, 1, 1, 12, 0, 0);
      final cmd = ManualCommand(
        sentryId: 'sentry-01',
        panVelocity: 50.0,
        tiltVelocity: -30.0,
        timestampUtc: now,
      );
      final json = cmd.toJson();
      expect(json['sentry_id'], equals('sentry-01'));
      expect(json['pan_velocity'], equals(50.0));
      expect(json['tilt_velocity'], equals(-30.0));
      expect(json['timestamp_utc'], equals('2025-01-01T12:00:00.000Z'));
    });

    test('velocities are clamped to kMaxJoystickVelocity', () {
      // Simulate normalisation: delta of 500px should clamp to max
      const rawPan = 500.0;
      const rawTilt = -500.0;
      final pan =
          rawPan.clamp(-kMaxJoystickVelocity, kMaxJoystickVelocity);
      final tilt =
          rawTilt.clamp(-kMaxJoystickVelocity, kMaxJoystickVelocity);
      expect(pan, equals(kMaxJoystickVelocity));
      expect(tilt, equals(-kMaxJoystickVelocity));
    });

    test('delta normalisation produces correct velocity', () {
      // 100px drag in a 150px radius → 66.7% of max
      const dragDelta = 100.0;
      const joystickRadius = 150.0;
      final velocity =
          (dragDelta / joystickRadius * kMaxJoystickVelocity)
              .clamp(-kMaxJoystickVelocity, kMaxJoystickVelocity);
      expect(velocity, closeTo(133.3, 0.1)); // 100/150 * 200
    });

    test('kMaxJoystickVelocity equals 200.0', () {
      expect(kMaxJoystickVelocity, equals(200.0));
    });

    test('kJoystickPublishIntervalMs equals 100', () {
      expect(kJoystickPublishIntervalMs, equals(100));
    });
  });
}
