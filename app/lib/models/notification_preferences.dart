import 'threat_marker.dart';
import '../core/constants.dart';

/// How the app should respond to a given alert.
enum NotificationMode {
  alarm,
  notification,
  silent,
  disabled,
}

/// Per-tier notification preferences.
class NotificationPreferences {
  const NotificationPreferences({
    this.highMode = NotificationMode.alarm,
    this.medMode = NotificationMode.notification,
    this.lowMode = NotificationMode.silent,
    this.medScoreThreshold = kThreatTierMedThreshold,
    this.highScoreThreshold = kThreatTierHighThreshold,
  });

  final NotificationMode highMode;
  final NotificationMode medMode;
  final NotificationMode lowMode;
  final double medScoreThreshold;
  final double highScoreThreshold;

  /// Returns true when the given [tier] and [score] combination should
  /// trigger a notification.
  bool shouldNotify(ThreatTier tier, double score) {
    final mode = _modeFor(tier);
    if (mode == NotificationMode.disabled || mode == NotificationMode.silent) {
      return false;
    }
    // Score threshold check
    switch (tier) {
      case ThreatTier.high:
        if (score < highScoreThreshold) return false;
      case ThreatTier.med:
        if (score < medScoreThreshold) return false;
      case ThreatTier.low:
        break; // No extra threshold for LOW
    }
    return true;
  }

  NotificationMode _modeFor(ThreatTier tier) {
    switch (tier) {
      case ThreatTier.high:
        return highMode;
      case ThreatTier.med:
        return medMode;
      case ThreatTier.low:
        return lowMode;
    }
  }

  NotificationPreferences copyWith({
    NotificationMode? highMode,
    NotificationMode? medMode,
    NotificationMode? lowMode,
    double? medScoreThreshold,
    double? highScoreThreshold,
  }) {
    return NotificationPreferences(
      highMode: highMode ?? this.highMode,
      medMode: medMode ?? this.medMode,
      lowMode: lowMode ?? this.lowMode,
      medScoreThreshold: medScoreThreshold ?? this.medScoreThreshold,
      highScoreThreshold: highScoreThreshold ?? this.highScoreThreshold,
    );
  }

  Map<String, dynamic> toJson() => {
        'highMode': highMode.name,
        'medMode': medMode.name,
        'lowMode': lowMode.name,
        'medScoreThreshold': medScoreThreshold,
        'highScoreThreshold': highScoreThreshold,
      };

  factory NotificationPreferences.fromJson(Map<String, dynamic> json) {
    NotificationMode parseMode(String? value, NotificationMode def) {
      if (value == null) return def;
      return NotificationMode.values.firstWhere(
        (e) => e.name == value,
        orElse: () => def,
      );
    }

    return NotificationPreferences(
      highMode: parseMode(json['highMode'] as String?, NotificationMode.alarm),
      medMode: parseMode(
          json['medMode'] as String?, NotificationMode.notification),
      lowMode: parseMode(json['lowMode'] as String?, NotificationMode.silent),
      medScoreThreshold:
          (json['medScoreThreshold'] as num?)?.toDouble() ?? kThreatTierMedThreshold,
      highScoreThreshold:
          (json['highScoreThreshold'] as num?)?.toDouble() ?? kThreatTierHighThreshold,
    );
  }
}
