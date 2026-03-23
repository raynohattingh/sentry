import 'package:flutter_test/flutter_test.dart';
import 'package:sentry_mobile/models/safety_status.dart';

void main() {
  group('SafetyStatusRecord', () {
    test('parses test bench bypass payload', () {
      final record = SafetyStatusRecord.fromJson({
        'sentry_id': 'unit-1',
        'housing_profile': 'TEST_BENCH',
        'protection_mode': 'SOFT_LIMIT_BYPASS',
        'motion_allowed': true,
        'motion_block_reason': null,
        'validated_switches': <String>[],
        'timestamp_utc': '2026-03-23T17:00:00Z',
      });

      expect(record.sentryId, 'unit-1');
      expect(record.housingProfile, HousingProfile.testBench);
      expect(record.protectionMode, ProtectionMode.softLimitBypass);
      expect(record.motionAllowed, isTrue);
      expect(record.validatedSwitches, isEmpty);
    });

    test('parses mvp validation-pending payload', () {
      final record = SafetyStatusRecord.fromJson({
        'sentry_id': 'unit-2',
        'housing_profile': 'MVP',
        'protection_mode': 'HARDWARE_VALIDATION_PENDING',
        'motion_allowed': false,
        'motion_block_reason': 'LIMIT_SWITCH_VALIDATION_REQUIRED',
        'validated_switches': <String>['PAN_LEFT', 'PAN_RIGHT'],
        'timestamp_utc': '2026-03-23T17:02:15Z',
      });

      expect(record.housingProfile, HousingProfile.mvp);
      expect(
          record.protectionMode, ProtectionMode.hardwareValidationPending);
      expect(record.motionAllowed, isFalse);
      expect(record.motionBlockReason, 'LIMIT_SWITCH_VALIDATION_REQUIRED');
      expect(record.validatedSwitches, ['PAN_LEFT', 'PAN_RIGHT']);
    });
  });
}
