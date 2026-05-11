import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../models/notification_preferences.dart';
import '../models/telemetry_record.dart';
import '../models/threat_marker.dart';
import '../core/theme.dart';

/// Abstract notification service interface.
abstract class NotificationService {
  Future<void> initialize();
  Future<void> showThreatAlert(
      TelemetryRecord record, NotificationPreferences preferences);
  Future<void> requestPermissions();
}

/// Concrete notification service backed by flutter_local_notifications.
class NotificationServiceImpl implements NotificationService {
  NotificationServiceImpl();

  final _plugin = FlutterLocalNotificationsPlugin();

  static const _channelId = 'sentry_threat_high';
  static const _channelName = 'Sentry Threat Alerts';
  static const _channelDesc =
      'Critical threat detection alerts from Farm Sentry';

  // Telemetry arrives at ~20 Hz; without de-duplication a single active HIGH
  // target produces ~20 push notifications per second. Track the last
  // notified (tier, time) per target_id so we only surface meaningful
  // transitions and at most one notification per target per window.
  static const Duration _kRepeatSuppress = Duration(seconds: 30);
  final Map<int, ThreatTier> _lastNotifiedTier = {};
  final Map<int, DateTime> _lastNotifiedAt = {};

  int _notifId = 0;

  @override
  Future<void> initialize() async {
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await _plugin.initialize(settings);
  }

  @override
  Future<void> requestPermissions() async {
    await _plugin
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
          critical: true,
        );
    await _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
  }

  @override
  Future<void> showThreatAlert(
      TelemetryRecord record, NotificationPreferences prefs) async {
    if (!prefs.shouldNotify(record.tier, record.threatScore)) return;

    // Rate limit: notify on tier transitions and at most once per
    // [_kRepeatSuppress] for the same target+tier.
    final now = DateTime.now();
    final lastTier = _lastNotifiedTier[record.targetId];
    final lastAt = _lastNotifiedAt[record.targetId];
    final tierUnchanged = lastTier == record.tier;
    final withinWindow =
        lastAt != null && now.difference(lastAt) < _kRepeatSuppress;
    if (tierUnchanged && withinWindow) return;
    _lastNotifiedTier[record.targetId] = record.tier;
    _lastNotifiedAt[record.targetId] = now;

    final isAlarm = prefs.highMode == NotificationMode.alarm &&
        record.tier == ThreatTier.high;

    final androidDetails = AndroidNotificationDetails(
      _channelId,
      _channelName,
      channelDescription: _channelDesc,
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      audioAttributesUsage:
          isAlarm ? AudioAttributesUsage.alarm : AudioAttributesUsage.notification,
      color: _tierColor(record.tier),
      ticker: '[SENTRY] Threat detected',
      fullScreenIntent: isAlarm,
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    final tierLabel = record.tier.toJson();
    final title = '[SENTRY] $tierLabel Threat — Target ${record.targetId}';
    final body =
        'Score: ${record.threatScore.toStringAsFixed(1)} | ${_posString(record)}';

    await _plugin.show(_notifId++, title, body, details);
  }

  String _posString(TelemetryRecord r) {
    if (r.lat != null && r.lon != null) {
      return '${r.lat!.toStringAsFixed(4)}, ${r.lon!.toStringAsFixed(4)}';
    }
    return 'Location Unknown';
  }

  Color _tierColor(ThreatTier tier) {
    switch (tier) {
      case ThreatTier.high:
        return kColorHigh;
      case ThreatTier.med:
        return kColorMed;
      case ThreatTier.low:
        return kColorLow;
    }
  }
}
