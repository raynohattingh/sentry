import 'dart:async';

import 'package:mocktail/mocktail.dart';
import 'package:latlong2/latlong.dart';

import 'package:sentry_mobile/services/mqtt_service.dart';
import 'package:sentry_mobile/services/location_service.dart';
import 'package:sentry_mobile/services/notification_service.dart';
import 'package:sentry_mobile/models/telemetry_record.dart';
import 'package:sentry_mobile/models/connection_state.dart';

/// Mock MQTT service — exposes stream controllers for test injection.
class MockMqttService extends Mock implements MqttService {
  final StreamController<TelemetryRecord> _telemetryController =
      StreamController<TelemetryRecord>.broadcast();
  final StreamController<SentryConnectionState> _connectionController =
      StreamController<SentryConnectionState>.broadcast();

  @override
  Stream<TelemetryRecord> get telemetryStream => _telemetryController.stream;

  @override
  Stream<SentryConnectionState> get connectionStream =>
      _connectionController.stream;

  /// Injects a [TelemetryRecord] into the stream.
  void emitTelemetry(TelemetryRecord record) =>
      _telemetryController.add(record);

  /// Injects a [SentryConnectionState] into the stream.
  void emitConnectionState(SentryConnectionState state) =>
      _connectionController.add(state);

  void dispose() {
    _telemetryController.close();
    _connectionController.close();
  }
}

/// Mock location service.
class MockLocationService extends Mock implements LocationService {
  final StreamController<LatLng?> _locationController =
      StreamController<LatLng?>.broadcast();

  @override
  Stream<LatLng?> get locationStream => _locationController.stream;

  void emitLocation(LatLng? location) => _locationController.add(location);

  void dispose() => _locationController.close();
}

/// Mock notification service.
class MockNotificationService extends Mock implements NotificationService {}
