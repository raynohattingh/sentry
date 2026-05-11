import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../core/constants.dart';
import '../../models/connection_state.dart';
import '../../models/safety_status.dart';
import '../../models/sentry_config.dart';
import '../../models/telemetry_record.dart';
import '../../models/threat_marker.dart';
import '../../services/location_service.dart';
import '../../services/mqtt_service.dart';
import '../../utils/geo_utils.dart';
import '../setup/setup_provider.dart';

/// Provider for the MQTT service — override in tests and in DI root.
final mqttServiceProvider = Provider<MqttService>((ref) {
  final service = MqttServiceImpl();
  ref.listen<SentryConfig>(
    sentryConfigProvider,
    (_, next) {
      if (next.isConfigured) {
        unawaited(service.connect(next));
      }
    },
    fireImmediately: true,
  );
  ref.onDispose(() {
    unawaited(service.disconnect());
  });
  return service;
});

/// Provider for the location service. Defaults to the real geolocator-backed
/// implementation; tests override with a mock. Disposed with the container.
final locationServiceProvider = Provider<LocationService?>((ref) {
  final service = LocationServiceImpl();
  ref.onDispose(service.dispose);
  return service;
});

/// Provider for the current sentry config (north offset, GPS, retention).
/// Reads from the canonical [sentryConfigProvider] so calibration is applied.
final sentryConfigForMapProvider = Provider<SentryConfig>((ref) {
  return ref.watch(sentryConfigProvider);
});

/// Stream provider for the user's current location.
final userLocationStreamProvider = StreamProvider<LatLng?>((ref) {
  final service = ref.watch(locationServiceProvider);
  if (service == null) return const Stream.empty();
  return service.locationStream;
});

/// Stream provider for raw telemetry records.
final telemetryStreamProvider = StreamProvider<TelemetryRecord>((ref) {
  final mqtt = ref.watch(mqttServiceProvider);
  return mqtt.telemetryStream;
});

/// Stream provider for authoritative safety status records.
final safetyStatusStreamProvider = StreamProvider<SafetyStatusRecord>((ref) {
  final mqtt = ref.watch(mqttServiceProvider);
  return mqtt.safetyStatusStream;
});

/// Notifier managing the map of live threat markers.
class ThreatMarkersNotifier
    extends StateNotifier<Map<int, ThreatMarker>> {
  ThreatMarkersNotifier(
    this._mqttService,
    LatLng? initialUserLocation, {
    SentryConfig config = const SentryConfig(),
    Ref? ref,
  })  : _userLocation = initialUserLocation,
        _config = config,
        _ref = ref,
        super({}) {
    _telemetrySub =
        _mqttService.telemetryStream.listen(_onTelemetry);
    _connectionSub =
        _mqttService.connectionStream.listen(_onConnectionState);
  }

  final MqttService _mqttService;
  LatLng? _userLocation;
  final SentryConfig _config;
  final Ref? _ref;

  StreamSubscription<TelemetryRecord>? _telemetrySub;
  StreamSubscription<SentryConnectionState>? _connectionSub;
  final Map<int, Timer> _fadeTimers = {};

  void updateUserLocation(LatLng? location) {
    _userLocation = location;
    // Recalculate distances for all active markers
    final updated = Map<int, ThreatMarker>.from(state);
    for (final entry in updated.entries) {
      if (entry.value.markerState != MarkerState.removed) {
        final dist = GeoUtils.distanceOrNull(
            _userLocation, LatLng(entry.value.lat, entry.value.lon));
        updated[entry.key] = entry.value.copyWith(distanceToUserM: dist);
      }
    }
    state = updated;
  }

  void _onTelemetry(TelemetryRecord record) {
    // Always reflect the latest FSM state on the badge, even when the record
    // has no GPS (e.g. before any LRF lock or during MANUAL_OVERRIDE).
    if (_ref != null && record.fsmState != null) {
      _ref.read(sentryModeProvider.notifier).state = record.fsmState;
    }

    if (record.lat == null || record.lon == null) return;

    // Apply north offset calibration (FR-021)
    LatLng position = LatLng(record.lat!, record.lon!);
    if (_config.sentryLat != null &&
        _config.sentryLon != null &&
        _config.northOffsetDegrees != 0.0) {
      position = GeoUtils.applyNorthOffset(
        position,
        LatLng(_config.sentryLat!, _config.sentryLon!),
        _config.northOffsetDegrees,
      );
    }

    final isFading = record.fsmState == FsmState.search;
    final dist = GeoUtils.distanceOrNull(_userLocation, position);

    final existing = state[record.targetId];
    final markerState =
        isFading ? MarkerState.fading : MarkerState.active;

    final marker = ThreatMarker(
      targetId: record.targetId,
      tier: record.tier,
      lat: position.latitude,
      lon: position.longitude,
      threatScore: record.threatScore,
      panAngle: record.panAngle,
      tiltAngle: record.tiltAngle,
      lastUpdated: record.timestampUtc,
      markerState: markerState,
      isSelected: existing?.isSelected ?? false,
      distanceToUserM: dist,
      lrfDistanceM: record.lrfDistanceM,
      fadingStartedAt:
          isFading ? (existing?.fadingStartedAt ?? DateTime.now()) : null,
    );

    // Cancel any existing fade timer if going back to active
    if (!isFading) {
      _fadeTimers[record.targetId]?.cancel();
      _fadeTimers.remove(record.targetId);
    } else {
      _scheduleFadeRemoval(record.targetId);
    }

    state = {...state, record.targetId: marker};
  }

  void _onConnectionState(SentryConnectionState connState) {
    if (connState == SentryConnectionState.offline) {
      fadeAll();
    }
  }

  void _scheduleFadeRemoval(int targetId) {
    _fadeTimers[targetId]?.cancel();
    _fadeTimers[targetId] =
        Timer(const Duration(seconds: kMarkerFadeRemovalSec), () {
      final updated = Map<int, ThreatMarker>.from(state);
      updated.remove(targetId);
      state = updated;
      _fadeTimers.remove(targetId);
    });
  }

  /// Fades all active markers (called on telemetry loss / offline state).
  void fadeAll() {
    final updated = <int, ThreatMarker>{};
    for (final entry in state.entries) {
      if (entry.value.markerState == MarkerState.active) {
        updated[entry.key] = entry.value.copyWith(
          markerState: MarkerState.fading,
          fadingStartedAt: DateTime.now(),
        );
        _scheduleFadeRemoval(entry.key);
      } else {
        updated[entry.key] = entry.value;
      }
    }
    state = updated;
  }

  @override
  void dispose() {
    _telemetrySub?.cancel();
    _connectionSub?.cancel();
    for (final timer in _fadeTimers.values) {
      timer.cancel();
    }
    super.dispose();
  }
}

/// Riverpod provider for [ThreatMarkersNotifier].
final threatMarkersProvider =
    StateNotifierProvider<ThreatMarkersNotifier, Map<int, ThreatMarker>>(
  (ref) {
    final mqtt = ref.watch(mqttServiceProvider);
    final config = ref.watch(sentryConfigForMapProvider);
    // Eagerly subscribe to user location and feed it into the notifier so
    // marker distances and the blue-dot stay live. Without this the
    // distance/blue-dot remained null even when location was available.
    final notifier =
        ThreatMarkersNotifier(mqtt, null, config: config, ref: ref);
    ref.listen<AsyncValue<LatLng?>>(userLocationStreamProvider, (_, next) {
      next.whenData(notifier.updateUserLocation);
    }, fireImmediately: true);
    return notifier;
  },
);

/// Provider tracking the current sentry FSM state. Written to by
/// [ThreatMarkersNotifier] on every telemetry record.
final sentryModeProvider = StateProvider<FsmState?>((ref) => null);
