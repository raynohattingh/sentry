import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:sentry_mobile/features/map/telemetry_provider.dart';
import 'package:sentry_mobile/models/telemetry_record.dart';
import 'package:sentry_mobile/models/threat_marker.dart';
import '../mocks/mock_mqtt_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockMqttService mockMqtt;
  late ThreatMarkersNotifier notifier;

  setUp(() {
    mockMqtt = MockMqttService();
    notifier = ThreatMarkersNotifier(mockMqtt, null);
  });

  tearDown(() {
    mockMqtt.dispose();
    notifier.dispose();
  });

  TelemetryRecord makeTelemetry({
    int targetId = 1,
    ThreatTier tier = ThreatTier.high,
    double? lat = -26.2,
    double? lon = 28.05,
    FsmState? fsmState,
  }) =>
      TelemetryRecord(
        sessionId: 'sess-test',
        targetId: targetId,
        threatScore: 90.0,
        tier: tier,
        lat: lat,
        lon: lon,
        panAngle: 0.0,
        tiltAngle: 0.0,
        timestampUtc: DateTime.now().toUtc(),
        fsmState: fsmState,
      );

  group('ThreatMarkersNotifier', () {
    test('upserts marker on telemetry record', () async {
      mockMqtt.emitTelemetry(makeTelemetry());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier.state.containsKey(1), isTrue);
      expect(notifier.state[1]!.markerState, equals(MarkerState.active));
    });

    test('state updates within 2 seconds of message injection (SC-002)', () async {
      final stopwatch = Stopwatch()..start();
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 99));
      while (!notifier.state.containsKey(99) &&
          stopwatch.elapsed.inSeconds < 2) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
      stopwatch.stop();
      expect(notifier.state.containsKey(99), isTrue);
      expect(stopwatch.elapsed.inSeconds, lessThan(2));
    });

    test('SEARCH fsmState triggers fading', () async {
      mockMqtt.emitTelemetry(makeTelemetry(fsmState: FsmState.search));
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier.state[1]?.markerState, equals(MarkerState.fading));
    });

    test('new telemetry on fading marker reverts to active', () async {
      // First emit with SEARCH (fading)
      mockMqtt.emitTelemetry(makeTelemetry(fsmState: FsmState.search));
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier.state[1]?.markerState, equals(MarkerState.fading));

      // Then emit normal telemetry (active)
      mockMqtt.emitTelemetry(makeTelemetry(fsmState: FsmState.track));
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier.state[1]?.markerState, equals(MarkerState.active));
    });

    test('fadeAll sets all active markers to fading (FR-004b)', () async {
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 1));
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 2));
      await Future<void>.delayed(const Duration(milliseconds: 50));
      notifier.fadeAll();
      expect(notifier.state[1]?.markerState, equals(MarkerState.fading));
      expect(notifier.state[2]?.markerState, equals(MarkerState.fading));
    });

    test('distance populated when user location available', () async {
      final userLocation = LatLng(-26.21, 28.05);
      final notifier2 =
          ThreatMarkersNotifier(mockMqtt, userLocation);
      mockMqtt.emitTelemetry(makeTelemetry(targetId: 3));
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(notifier2.state[3]?.distanceToUserM, isNotNull);
      notifier2.dispose();
    });
  });
}
