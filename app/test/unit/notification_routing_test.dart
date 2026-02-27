import 'package:flutter_test/flutter_test.dart';

import 'package:sentry_mobile/models/notification_preferences.dart';
import 'package:sentry_mobile/models/threat_marker.dart';
import 'package:sentry_mobile/core/constants.dart';

void main() {
  group('NotificationPreferences.shouldNotify', () {
    const prefs = NotificationPreferences();

    test('HIGH alarm mode triggers', () {
      expect(prefs.shouldNotify(ThreatTier.high, kThreatTierHighThreshold),
          isTrue);
    });

    test('MED notification mode triggers', () {
      expect(prefs.shouldNotify(ThreatTier.med, kThreatTierMedThreshold),
          isTrue);
    });

    test('LOW silent mode suppresses', () {
      expect(prefs.shouldNotify(ThreatTier.low, 10.0), isFalse);
    });

    test('score below threshold suppresses regardless of tier', () {
      // MED tier but score below med threshold (38 < 40)
      expect(prefs.shouldNotify(ThreatTier.med, 38.0), isFalse);
    });

    test('HIGH score below high threshold suppresses', () {
      // HIGH tier but score is 79 < 80 threshold
      expect(prefs.shouldNotify(ThreatTier.high, 79.0), isFalse);
    });

    test('disabled mode always suppresses', () {
      final disabledPrefs = NotificationPreferences(
        highMode: NotificationMode.disabled,
        medMode: NotificationMode.disabled,
        lowMode: NotificationMode.disabled,
      );
      expect(disabledPrefs.shouldNotify(ThreatTier.high, 99.0), isFalse);
      expect(disabledPrefs.shouldNotify(ThreatTier.med, 60.0), isFalse);
      expect(disabledPrefs.shouldNotify(ThreatTier.low, 10.0), isFalse);
    });

    test('silent mode suppresses even above threshold', () {
      final silentPrefs = NotificationPreferences(
        highMode: NotificationMode.silent,
        medMode: NotificationMode.silent,
      );
      expect(silentPrefs.shouldNotify(ThreatTier.high, 95.0), isFalse);
      expect(silentPrefs.shouldNotify(ThreatTier.med, 55.0), isFalse);
    });

    test('notification mode triggers for MED', () {
      const notifPrefs = NotificationPreferences(
        medMode: NotificationMode.notification,
      );
      expect(notifPrefs.shouldNotify(ThreatTier.med, 50.0), isTrue);
    });

    // Manual benchmark target for SC-004:
    // phone locked, inject HIGH-tier message → lockscreen alarm fires within 3s
    // (This is verified manually — documented here for traceability)
    test('SC-004 manual benchmark: HIGH alarm should fire within 3s on lockscreen', () {
      // Verifiable via NotificationServiceImpl + flutter_local_notifications
      // with channel importance: Importance.max and audioAttributesUsage: alarm.
      // Test documents the intent; actual timing measured on device.
      expect(prefs.shouldNotify(ThreatTier.high, 90.0), isTrue,
          reason: 'HIGH tier at 90 score must trigger notification (SC-004 path)');
    });
  });
}
