import '../core/constants.dart';
import 'threat_marker.dart';

/// FSM state of the sentry turret.
enum FsmState {
  scan,
  acquire,
  track,
  search,
  manualOverride;

  static FsmState? fromJson(String? value) {
    if (value == null) return null;
    switch (value.toUpperCase()) {
      case 'SCAN':
        return FsmState.scan;
      case 'ACQUIRE':
        return FsmState.acquire;
      case 'TRACK':
        return FsmState.track;
      case 'SEARCH':
        return FsmState.search;
      case 'MANUAL_OVERRIDE':
        return FsmState.manualOverride;
      default:
        return null;
    }
  }

  String toJson() {
    if (this == FsmState.manualOverride) return 'MANUAL_OVERRIDE';
    return name.toUpperCase();
  }
}

/// 2D velocity vector from the telemetry payload.
class VelocityVector {
  const VelocityVector({required this.vx, required this.vy});

  final double vx;
  final double vy;

  factory VelocityVector.fromJson(Map<String, dynamic> json) {
    return VelocityVector(
      vx: (json['vx'] as num).toDouble(),
      vy: (json['vy'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {'vx': vx, 'vy': vy};

  @override
  bool operator ==(Object other) =>
      other is VelocityVector && other.vx == vx && other.vy == vy;

  @override
  int get hashCode => Object.hash(vx, vy);
}

/// Immutable telemetry record received from `sentry/telemetry`.
class TelemetryRecord {
  const TelemetryRecord({
    required this.sessionId,
    required this.targetId,
    required this.threatScore,
    required this.tier,
    this.lat,
    this.lon,
    this.lrfDistanceM,
    required this.panAngle,
    required this.tiltAngle,
    required this.timestampUtc,
    this.velocityVector,
    this.fsmState,
  });

  final String sessionId;
  final int targetId;
  final double threatScore;
  final ThreatTier tier;
  final double? lat;
  final double? lon;
  final double? lrfDistanceM;
  final double panAngle;
  final double tiltAngle;
  final DateTime timestampUtc;
  final VelocityVector? velocityVector;
  final FsmState? fsmState;

  factory TelemetryRecord.fromJson(Map<String, dynamic> json) {
    try {
      final rawTier = json['tier'] as String?;
      final tier = ThreatTierJsonParsing.fromJson(rawTier);

      final rawVv = json['velocity_vector'];
      final velocityVector = rawVv != null
          ? VelocityVector.fromJson(rawVv as Map<String, dynamic>)
          : null;

      final rawFsm = json['fsm_state'] as String?;
      final fsmState = FsmState.fromJson(rawFsm);

      return TelemetryRecord(
        sessionId: json['session_id'] as String,
        targetId: json['target_id'] as int,
        threatScore: (json['threat_score'] as num).toDouble(),
        tier: tier,
        lat: json['lat'] != null ? (json['lat'] as num).toDouble() : null,
        lon: json['lon'] != null ? (json['lon'] as num).toDouble() : null,
        lrfDistanceM: json['lrf_distance_m'] != null
            ? (json['lrf_distance_m'] as num).toDouble()
            : null,
        panAngle: (json['pan_angle'] as num).toDouble(),
        tiltAngle: (json['tilt_angle'] as num).toDouble(),
        timestampUtc: DateTime.parse(json['timestamp_utc'] as String),
        velocityVector: velocityVector,
        fsmState: fsmState,
      );
    } on FormatException {
      rethrow;
    } catch (e) {
      throw FormatException('Invalid TelemetryRecord JSON: $e');
    }
  }

  Map<String, dynamic> toJson() => {
        'session_id': sessionId,
        'target_id': targetId,
        'threat_score': threatScore,
        'tier': tier.toJson(),
        'lat': lat,
        'lon': lon,
        'lrf_distance_m': lrfDistanceM,
        'pan_angle': panAngle,
        'tilt_angle': tiltAngle,
        'timestamp_utc': timestampUtc.toIso8601String(),
        'velocity_vector': velocityVector?.toJson(),
        'fsm_state': fsmState?.toJson(),
      };
}

/// Parses a threat tier from the JSON string with graceful fallback.
extension ThreatTierJsonParsing on ThreatTier {
  static ThreatTier fromJson(String? value) {
    if (value == null) return ThreatTier.low;
    switch (value.toUpperCase()) {
      case 'HIGH':
        return ThreatTier.high;
      case 'MED':
        return ThreatTier.med;
      case 'LOW':
      default:
        return ThreatTier.low;
    }
  }

  String toJson() {
    switch (this) {
      case ThreatTier.high:
        return 'HIGH';
      case ThreatTier.med:
        return 'MED';
      case ThreatTier.low:
        return 'LOW';
    }
  }
}

/// Returns the [ThreatTier] for a given numeric [score].
ThreatTier tierFromScore(double score) {
  if (score >= kThreatTierHighThreshold) return ThreatTier.high;
  if (score >= kThreatTierMedThreshold) return ThreatTier.med;
  return ThreatTier.low;
}
