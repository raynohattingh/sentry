import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

import '../models/manual_command.dart';
import '../models/safety_status.dart';
import '../models/telemetry_record.dart';
import '../models/sentry_config.dart';
import '../models/connection_state.dart';

const String mqttTelemetryTopic = 'sentry/telemetry';
const String mqttStatusTopic = 'sentry/status';
const String mqttCommandTopic = 'sentry/command';

/// Abstract MQTT service interface.
abstract class MqttService {
  Future<void> connect(SentryConfig config);
  Future<void> disconnect();
  Future<void> publishCommand(ManualCommand command);
  Stream<TelemetryRecord> get telemetryStream;
  Stream<SafetyStatusRecord> get safetyStatusStream;
  Stream<SentryConnectionState> get connectionStream;
}

/// Concrete MQTT service implementation with TLS and exponential backoff.
class MqttServiceImpl implements MqttService {
  MqttServiceImpl();

  MqttServerClient? _client;
  SentryConfig? _config;

  final _telemetryController =
      StreamController<TelemetryRecord>.broadcast();
  final _safetyStatusController =
      StreamController<SafetyStatusRecord>.broadcast();
  final _connectionController =
      StreamController<SentryConnectionState>.broadcast();

  Timer? _reconnectTimer;
  int _backoffSec = 2;
  static const int _maxBackoffSec = 60;
  bool _disposed = false;

  @override
  Stream<TelemetryRecord> get telemetryStream => _telemetryController.stream;

  @override
  Stream<SafetyStatusRecord> get safetyStatusStream =>
      _safetyStatusController.stream;

  @override
  Stream<SentryConnectionState> get connectionStream =>
      _connectionController.stream;

  @override
  Future<void> connect(SentryConfig config) async {
    _config = config;
    _backoffSec = 2;
    await _doConnect(config);
  }

  Future<void> _doConnect(SentryConfig config) async {
    try {
      final clientId =
          'sentry_mobile_${DateTime.now().millisecondsSinceEpoch}';
      final client = MqttServerClient.withPort(
          config.brokerHost, clientId, config.brokerPort);

      client.secure = true;
      client.securityContext = SecurityContext.defaultContext;
      client.onBadCertificate = (_) => false; // strict — rejects bad certs

      client.logging(on: false);
      client.keepAlivePeriod = 20;
      client.autoReconnect = false;

      client.onDisconnected = _onDisconnected;
      client.onConnected = _onConnected;

      final connMessage = MqttConnectMessage()
          .withClientIdentifier(clientId)
          .authenticateAs(config.mqttUsername, config.mqttPassword)
          .startClean()
          .withWillQos(MqttQos.atLeastOnce);
      client.connectionMessage = connMessage;

      await client.connect(config.mqttUsername, config.mqttPassword);

      if (client.connectionStatus?.state == MqttConnectionState.connected) {
        _client = client;
        _backoffSec = 2;
        client.subscribe(mqttTelemetryTopic, MqttQos.atLeastOnce);
        client.subscribe(mqttStatusTopic, MqttQos.atLeastOnce);
        client.updates?.listen(_onMessage);
        _connectionController.add(SentryConnectionState.online);
      } else {
        _scheduleReconnect();
      }
    } catch (_) {
      _connectionController.add(SentryConnectionState.reconnecting);
      _scheduleReconnect();
    }
  }

  void _onConnected() {
    _connectionController.add(SentryConnectionState.online);
  }

  void _onDisconnected() {
    _connectionController.add(SentryConnectionState.reconnecting);
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: _backoffSec), () {
      if (_disposed || _config == null) return;
      _backoffSec = (_backoffSec * 2).clamp(2, _maxBackoffSec);
      _doConnect(_config!);
    });
  }

  void _onMessage(List<MqttReceivedMessage<MqttMessage>> messages) {
    for (final msg in messages) {
      final payload =
          (msg.payload as MqttPublishMessage).payload.message;
      final raw = utf8.decode(payload.toList());
      try {
        final json = jsonDecode(raw) as Map<String, dynamic>;
        // Skip messages from other sentry devices
        if (_config != null &&
            json['sentry_id'] != null &&
            json['sentry_id'] != _config!.sentryId) {
          continue;
        }
        if (msg.topic == mqttStatusTopic) {
          final status = SafetyStatusRecord.fromJson(json);
          _safetyStatusController.add(status);
        } else if (msg.topic == mqttTelemetryTopic) {
          final record = TelemetryRecord.fromJson(json);
          _telemetryController.add(record);
        }
      } catch (_) {
        // Malformed payload — ignore
      }
    }
  }

  @override
  Future<void> publishCommand(ManualCommand command) async {
    final client = _client;
    if (client == null ||
        client.connectionStatus?.state != MqttConnectionState.connected) {
      return;
    }
    final payload = jsonEncode(command.toJson());
    final builder = MqttClientPayloadBuilder()..addString(payload);
    client.publishMessage(
        mqttCommandTopic, MqttQos.atLeastOnce, builder.payload!);
  }

  @override
  Future<void> disconnect() async {
    _disposed = true;
    _reconnectTimer?.cancel();
    _client?.disconnect();
    _client = null;
    await _telemetryController.close();
    await _safetyStatusController.close();
    await _connectionController.close();
  }
}
