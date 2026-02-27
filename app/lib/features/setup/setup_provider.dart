import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../models/sentry_config.dart';
import '../../services/secure_storage_service.dart';

const _kConfigKey = 'sentry_config';

/// Provider exposing the current [SentryConfig].
final sentryConfigProvider =
    StateNotifierProvider<SetupNotifier, SentryConfig>(
  (ref) => SetupNotifier(SecureStorageServiceImpl()),
);

/// Manages sentry configuration state and persistence.
class SetupNotifier extends StateNotifier<SentryConfig> {
  SetupNotifier(this._storage) : super(const SentryConfig()) {
    _loadInitial();
  }

  /// Named constructor for testing — accepts an injected [SecureStorageService].
  SetupNotifier.withStorage(SecureStorageService storage)
      : _storage = storage,
        super(const SentryConfig());

  final SecureStorageService _storage;

  Future<void> _loadInitial() async {
    await loadSavedConfig();
  }

  /// Loads saved configuration from SharedPreferences + SecureStorage.
  /// Returns the current configuration.
  // ignore: invalid_use_of_protected_member
  SentryConfig get currentConfig => state;

  Future<void> loadSavedConfig() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kConfigKey);
    SentryConfig loaded = const SentryConfig();
    if (raw != null) {
      try {
        loaded = SentryConfig.fromJson(
            Map<String, dynamic>.from(jsonDecode(raw) as Map));
      } catch (_) {}
    }
    // Restore credentials from secure storage
    final mqttCreds = await _storage.loadMqttCredentials();
    final videoCreds = await _storage.loadVideoCredentials();
    state = loaded.copyWith(
      mqttUsername: mqttCreds?.$1 ?? loaded.mqttUsername,
      mqttPassword: mqttCreds?.$2 ?? loaded.mqttPassword,
      videoUsername: videoCreds?.$1 ?? loaded.videoUsername,
      videoPassword: videoCreds?.$2 ?? loaded.videoPassword,
    );
  }

  /// Persists [config] and updates state.
  Future<void> save(SentryConfig config) async {
    // Persist non-secret fields to SharedPreferences
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kConfigKey, jsonEncode(config.toJson()));

    // Persist credentials to secure storage
    if (config.mqttUsername.isNotEmpty) {
      await _storage.saveMqttCredentials(
          config.mqttUsername, config.mqttPassword);
    }
    if (config.videoUsername.isNotEmpty) {
      await _storage.saveVideoCredentials(
          config.videoUsername, config.videoPassword);
    }

    state = config;
  }
}
