
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:sentry_mobile/features/map/connection_provider.dart';
import 'package:sentry_mobile/models/connection_state.dart';
import 'package:sentry_mobile/models/sentry_config.dart';
import 'package:sentry_mobile/models/telemetry_record.dart';
import 'package:sentry_mobile/models/threat_marker.dart';
import '../mocks/mock_mqtt_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    registerFallbackValue(const SentryConfig());
  });

  late MockMqttService mockMqtt;

  setUp(() {
    mockMqtt = MockMqttService();
    when(() => mockMqtt.connect(any())).thenAnswer((_) async {});
    when(() => mockMqtt.disconnect()).thenAnswer((_) async {});
  });

  tearDown(() {
    mockMqtt.dispose();
  });

  TelemetryRecord makeTelemetry() => TelemetryRecord(
        sessionId: 'sess-1',
        targetId: 1,
        threatScore: 90.0,
        tier: ThreatTier.high,
        panAngle: 0.0,
        tiltAngle: 0.0,
        timestampUtc: DateTime.now().toUtc(),
      );

  group('ConnectionStateNotifier', () {
    test('onConnected callback sets state to online', () {
      final notifier = ConnectionStateNotifier(mockMqtt);
      notifier.onConnected();
      expect(notifier.state, equals(SentryConnectionState.online));
      notifier.dispose();
    });

    test('onDisconnected sets state to reconnecting', () {
      final notifier = ConnectionStateNotifier(mockMqtt);
      notifier.onConnected();
      notifier.onDisconnected();
      expect(notifier.state, equals(SentryConnectionState.reconnecting));
      notifier.dispose();
    });

    test('incoming telemetry resets heartbeat timer', () async {
      final notifier = ConnectionStateNotifier(mockMqtt, heartbeatSec: 3);
      notifier.onConnected();
      // Emit telemetry to reset the timer
      mockMqtt.emitTelemetry(makeTelemetry());
      await Future<void>.delayed(const Duration(seconds: 1));
      expect(notifier.state, equals(SentryConnectionState.online));
      notifier.dispose();
    });

    test('heartbeat fires offline after timeout with no telemetry', () async {
      final notifier = ConnectionStateNotifier(mockMqtt, heartbeatSec: 1);
      notifier.onConnected();
      // No telemetry emitted — timer should fire
      await Future<void>.delayed(const Duration(seconds: 2));
      expect(notifier.state, equals(SentryConnectionState.offline));
      notifier.dispose();
    }, timeout: const Timeout(Duration(seconds: 5)));

    test('connection stream reconnecting state propagates', () async {
      final notifier = ConnectionStateNotifier(mockMqtt, heartbeatSec: 10);
      mockMqtt.emitConnectionState(SentryConnectionState.reconnecting);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier.state, equals(SentryConnectionState.reconnecting));
      notifier.dispose();
    });

    test('connection stream online state sets online', () async {
      final notifier = ConnectionStateNotifier(mockMqtt, heartbeatSec: 10);
      mockMqtt.emitConnectionState(SentryConnectionState.online);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier.state, equals(SentryConnectionState.online));
      notifier.dispose();
    });
  });
}
