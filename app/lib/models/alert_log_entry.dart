import 'telemetry_record.dart';
import 'threat_marker.dart';

/// Persisted alert log entry (mirrors the SQLite schema).
class AlertLogEntry {
  const AlertLogEntry({
    this.id,
    required this.targetId,
    required this.sessionId,
    required this.timestampUtcMs,
    required this.tier,
    required this.threatScore,
    this.lat,
    this.lon,
    this.lrfDistanceM,
    required this.panAngle,
    required this.tiltAngle,
    this.distanceToUserM,
  });

  final int? id; // auto-assigned by SQLite
  final int targetId;
  final String sessionId;
  final int timestampUtcMs; // Unix epoch milliseconds
  final String tier; // "LOW" | "MED" | "HIGH"
  final double threatScore;
  final double? lat;
  final double? lon;
  final double? lrfDistanceM;
  final double panAngle;
  final double tiltAngle;
  final double? distanceToUserM;

  /// Create from a live [TelemetryRecord], capturing distance at receipt time.
  factory AlertLogEntry.fromTelemetryRecord(
    TelemetryRecord record, {
    double? distanceToUserM,
  }) {
    return AlertLogEntry(
      targetId: record.targetId,
      sessionId: record.sessionId,
      timestampUtcMs: record.timestampUtc.millisecondsSinceEpoch,
      tier: record.tier.toJson(),
      threatScore: record.threatScore,
      lat: record.lat,
      lon: record.lon,
      lrfDistanceM: record.lrfDistanceM,
      panAngle: record.panAngle,
      tiltAngle: record.tiltAngle,
      distanceToUserM: distanceToUserM,
    );
  }

  /// Convenience getter for the tier as enum.
  ThreatTier get tierEnum {
    switch (tier.toUpperCase()) {
      case 'HIGH':
        return ThreatTier.high;
      case 'MED':
        return ThreatTier.med;
      default:
        return ThreatTier.low;
    }
  }

  /// Display string for distance — shows "Location Unknown" per FR-025 when
  /// coordinates are unavailable.
  String get distanceDisplay {
    if (distanceToUserM == null) return 'Location Unknown';
    final km = distanceToUserM! / 1000.0;
    return km >= 1.0
        ? '${km.toStringAsFixed(1)} km'
        : '${distanceToUserM!.toStringAsFixed(0)} m';
  }
}
