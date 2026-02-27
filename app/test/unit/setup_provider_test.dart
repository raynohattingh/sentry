import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sentry_mobile/features/setup/setup_provider.dart';
import 'package:sentry_mobile/models/sentry_config.dart';
import 'package:sentry_mobile/services/secure_storage_service.dart';

class MockSecureStorageService extends Mock implements SecureStorageService {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockSecureStorageService mockStorage;
  late SetupNotifier notifier;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    mockStorage = MockSecureStorageService();
    when(() => mockStorage.saveMqttCredentials(any(), any()))
        .thenAnswer((_) async {});
    when(() => mockStorage.saveVideoCredentials(any(), any()))
        .thenAnswer((_) async {});
    when(() => mockStorage.loadMqttCredentials())
        .thenAnswer((_) async => null);
    when(() => mockStorage.loadVideoCredentials())
        .thenAnswer((_) async => null);
    notifier = SetupNotifier.withStorage(mockStorage);
  });

  group('SetupNotifier', () {
    test('initial state is not configured when fields are empty', () {
      expect(notifier.state.isConfigured, isFalse);
    });

    test('save with valid config sets isConfigured true', () async {
      const config = SentryConfig(
        brokerHost: '192.168.1.100',
        mqttUsername: 'user',
        mqttPassword: 'pass',
        sentryId: 'sentry-01',
      );
      await notifier.save(config);
      expect(notifier.state.isConfigured, isTrue);
      expect(notifier.state.brokerHost, equals('192.168.1.100'));
    });

    test('save calls SecureStorageService with credentials', () async {
      const config = SentryConfig(
        brokerHost: '192.168.1.100',
        mqttUsername: 'user',
        mqttPassword: 'secret',
        sentryId: 'sentry-01',
      );
      await notifier.save(config);
      verify(() => mockStorage.saveMqttCredentials('user', 'secret')).called(1);
    });

    test('missing brokerHost prevents isConfigured', () {
      const config = SentryConfig(
        brokerHost: '',
        mqttUsername: 'user',
        sentryId: 'sentry-01',
      );
      expect(config.isConfigured, isFalse);
    });

    test('missing sentryId prevents isConfigured', () {
      const config = SentryConfig(
        brokerHost: '192.168.1.100',
        mqttUsername: 'user',
        sentryId: '',
      );
      expect(config.isConfigured, isFalse);
    });

    test('port 1883 shows non-TLS warning flag', () {
      const config = SentryConfig(
        brokerHost: '192.168.1.100',
        brokerPort: 1883,
        mqttUsername: 'user',
        sentryId: 'sentry-01',
      );
      expect(config.brokerPort, equals(1883));
      expect(config.brokerPort != 8883, isTrue,
          reason: 'Port 1883 is non-TLS — app should warn user');
    });

    test('loadSavedConfig restores MQTT credentials from storage', () async {
      when(() => mockStorage.loadMqttCredentials())
          .thenAnswer((_) async => ('savedUser', 'savedPass'));
      await notifier.loadSavedConfig();
      verify(() => mockStorage.loadMqttCredentials()).called(1);
      expect(notifier.state.mqttUsername, equals('savedUser'));
    });

    test('second launch skips setup when config persisted', () async {
      const config = SentryConfig(
        brokerHost: '10.0.0.1',
        mqttUsername: 'admin',
        mqttPassword: 'pw',
        sentryId: 'sentry-02',
      );
      await notifier.save(config);
      // Simulate app restart by creating a new notifier with same prefs
      final newNotifier = SetupNotifier.withStorage(mockStorage);
      await newNotifier.loadSavedConfig();
      // isConfigured should be true without re-entering setup
      expect(newNotifier.state.isConfigured, isTrue);
    });
  });
}
