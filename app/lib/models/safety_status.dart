enum HousingProfile {
  testBench('TEST_BENCH'),
  mvp('MVP');

  const HousingProfile(this.value);

  final String value;

  static HousingProfile fromJson(String? value) {
    switch (value?.toUpperCase()) {
      case 'TEST_BENCH':
        return HousingProfile.testBench;
      case 'MVP':
      default:
        return HousingProfile.mvp;
    }
  }
}

enum ProtectionMode {
  softLimitBypass('SOFT_LIMIT_BYPASS'),
  hardwareValidationPending('HARDWARE_VALIDATION_PENDING'),
  hardwareLimitsActive('HARDWARE_LIMITS_ACTIVE');

  const ProtectionMode(this.value);

  final String value;

  static ProtectionMode fromJson(String? value) {
    switch (value?.toUpperCase()) {
      case 'SOFT_LIMIT_BYPASS':
        return ProtectionMode.softLimitBypass;
      case 'HARDWARE_VALIDATION_PENDING':
        return ProtectionMode.hardwareValidationPending;
      case 'HARDWARE_LIMITS_ACTIVE':
      default:
        return ProtectionMode.hardwareLimitsActive;
    }
  }
}

class SafetyStatusRecord {
  const SafetyStatusRecord({
    required this.sentryId,
    required this.housingProfile,
    required this.protectionMode,
    required this.motionAllowed,
    required this.validatedSwitches,
    required this.timestampUtc,
    this.motionBlockReason,
  });

  final String sentryId;
  final HousingProfile housingProfile;
  final ProtectionMode protectionMode;
  final bool motionAllowed;
  final String? motionBlockReason;
  final List<String> validatedSwitches;
  final DateTime timestampUtc;

  factory SafetyStatusRecord.fromJson(Map<String, dynamic> json) {
    try {
      return SafetyStatusRecord(
        sentryId: json['sentry_id'] as String,
        housingProfile:
            HousingProfile.fromJson(json['housing_profile'] as String?),
        protectionMode:
            ProtectionMode.fromJson(json['protection_mode'] as String?),
        motionAllowed: json['motion_allowed'] as bool? ?? false,
        motionBlockReason: json['motion_block_reason'] as String?,
        validatedSwitches: (json['validated_switches'] as List<dynamic>? ?? [])
            .map((value) => value as String)
            .toList(growable: false),
        timestampUtc: DateTime.parse(json['timestamp_utc'] as String),
      );
    } on FormatException {
      rethrow;
    } catch (e) {
      throw FormatException('Invalid SafetyStatusRecord JSON: $e');
    }
  }

  Map<String, dynamic> toJson() => {
        'sentry_id': sentryId,
        'housing_profile': housingProfile.value,
        'protection_mode': protectionMode.value,
        'motion_allowed': motionAllowed,
        'motion_block_reason': motionBlockReason,
        'validated_switches': validatedSwitches,
        'timestamp_utc': timestampUtc.toIso8601String(),
      };
}
