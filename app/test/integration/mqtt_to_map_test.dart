
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:sentry_mobile/features/map/telemetry_provider.dart';
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
  });

  tearDown(() {
    mockMqtt.dispose();
  });

  TelemetryRecord makeTelemetry({
    int targetId = 1,
    ThreatTier tier = ThreatTier.high,
  }) =>
      TelemetryRecord(
        sessionId: 'sess-int',
        targetId: targetId,
        threatScore: 90.0,
        tier: tier,
        lat: -26.2,
        lon: 28.05,
        panAngle: 0.0,
        tiltAngle: 0.0,
        timestampUtc: DateTime.now().toUtc(),
      );

  group('MQTT → ThreatMarkersNotifier pipeline', () {
    test('ThreatMarkersNotifier updates within 2s of injection (SC-002)', () async {
      final notifier = ThreatMarkersNotifier(mockMqtt, null);

      final stopwatch = Stopwatch()..start();
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 77));
      while (!notifier.state.containsKey(77) &&
          stopwatch.elapsed.inSeconds < 2) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
      stopwatch.stop();

      expect(notifier.state.containsKey(77), isTrue,
          reason: 'Marker should appear within 2s of telemetry injection');
      expect(stopwatch.elapsed.inMilliseconds, lessThan(2000));
      notifier.dispose();
    });

    test('offline connection state triggers fadeAll on active markers', () async {
      final notifier = ThreatMarkersNotifier(mockMqtt, null);
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 1));
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 2));
      await Future<void>.delayed(const Duration(milliseconds: 100));
      expect(notifier.state[1]?.markerState, equals(MarkerState.active));

      // Inject offline connection state
      mockMqtt.emitConnectionState(SentryConnectionState.offline);
      await Future<void>.delayed(const Duration(milliseconds: 100));
      expect(notifier.state[1]?.markerState, equals(MarkerState.fading));
      expect(notifier.state[2]?.markerState, equals(MarkerState.fading));
      notifier.dispose();
    });

    test('multiple targets tracked independently', () async {
      final notifier = ThreatMarkersNotifier(mockMqtt, null);
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 1, tier: ThreatTier.low));
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 2, tier: ThreatTier.high));
      await Future<void>.delayed(const Duration(milliseconds: 100));
      expect(notifier.state.length, equals(2));
      expect(notifier.state[1]!.tier, equals(ThreatTier.low));
      expect(notifier.state[2]!.tier, equals(ThreatTier.high));
      notifier.dispose();
    });
  });
}
