import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../models/notification_preferences.dart';

const _kNotifPrefsKey = 'notification_preferences';

/// Provider exposing notification preferences.
final notificationPreferencesProvider =
    StateNotifierProvider<NotificationPreferencesNotifier, NotificationPreferences>(
  (ref) => NotificationPreferencesNotifier(),
);

/// Manages [NotificationPreferences] with SharedPreferences persistence.
class NotificationPreferencesNotifier
    extends StateNotifier<NotificationPreferences> {
  NotificationPreferencesNotifier() : super(const NotificationPreferences()) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kNotifPrefsKey);
    if (raw != null) {
      try {
        state = NotificationPreferences.fromJson(
            Map<String, dynamic>.from(jsonDecode(raw) as Map));
      } catch (_) {}
    }
  }

  /// Updates the preferences and persists them.
  Future<void> update(NotificationPreferences updated) async {
    state = updated;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kNotifPrefsKey, jsonEncode(updated.toJson()));
  }
}
