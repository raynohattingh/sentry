import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants.dart';
import '../../models/connection_state.dart';
import '../../services/mqtt_service.dart';
import 'telemetry_provider.dart';

/// Provider for [ConnectionStateNotifier].
final connectionStateProvider =
    StateNotifierProvider<ConnectionStateNotifier, SentryConnectionState>(
  (ref) => ConnectionStateNotifier(ref.read(mqttServiceProvider)),
);

/// Manages heartbeat and connection state transitions.
///
/// - Starts a timer on each telemetry event reset.
/// - Fires [SentryConnectionState.offline] if no telemetry arrives within
///   [heartbeatSec] seconds.
/// - Exposes [onConnected] / [onDisconnected] for the MQTT service callbacks.
class ConnectionStateNotifier extends StateNotifier<SentryConnectionState> {
  ConnectionStateNotifier(
    this._mqttService, {
    int heartbeatSec = kHeartbeatTimeoutSec,
  })  : _heartbeatSec = heartbeatSec,
        super(SentryConnectionState.offline) {
    _connectionSub = _mqttService.connectionStream.listen(_onConnectionEvent);
    _telemetrySub = _mqttService.telemetryStream.listen((_) => _resetTimer());
  }

  final MqttService _mqttService;
  final int _heartbeatSec;
  Timer? _heartbeatTimer;
  StreamSubscription<dynamic>? _connectionSub;
  StreamSubscription<dynamic>? _telemetrySub;

  /// Call when MQTT connects successfully.
  void onConnected() {
    state = SentryConnectionState.online;
    _resetTimer();
  }

  /// Call when MQTT disconnects.
  void onDisconnected() {
    _heartbeatTimer?.cancel();
    state = SentryConnectionState.reconnecting;
  }

  void _onConnectionEvent(SentryConnectionState event) {
    if (event == SentryConnectionState.online) {
      onConnected();
    } else if (event == SentryConnectionState.reconnecting) {
      onDisconnected();
    } else {
      state = event;
    }
  }

  void _resetTimer() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer(Duration(seconds: _heartbeatSec), () {
      state = SentryConnectionState.offline;
      // Notify ThreatMarkersNotifier to fade all markers (FR-004b)
      // This hook is called by ThreatMarkersNotifier listener in telemetry_provider.dart
    });
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    _connectionSub?.cancel();
    _telemetrySub?.cancel();
    super.dispose();
  }
}
