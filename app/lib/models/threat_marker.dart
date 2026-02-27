import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Tier classification of a threat target.
enum ThreatTier {
  low,
  med,
  high;
}

/// Lifecycle state of a threat marker on the map.
enum MarkerState {
  active,
  fading,
  removed,
}

/// A live threat marker shown on the tactical map.
class ThreatMarker {
  const ThreatMarker({
    required this.targetId,
    required this.tier,
    required this.lat,
    required this.lon,
    required this.threatScore,
    required this.panAngle,
    required this.tiltAngle,
    required this.lastUpdated,
    this.markerState = MarkerState.active,
    this.isSelected = false,
    this.distanceToUserM,
    this.lrfDistanceM,
    this.fadingStartedAt,
  });

  final int targetId;
  final ThreatTier tier;
  final double lat;
  final double lon;
  final double threatScore;
  final double panAngle;
  final double tiltAngle;
  final DateTime lastUpdated;
  final MarkerState markerState;
  final bool isSelected;
  final double? distanceToUserM;
  final double? lrfDistanceM;
  final DateTime? fadingStartedAt;

  /// Colour derived from the threat tier.
  Color get color {
    switch (tier) {
      case ThreatTier.high:
        return kColorHigh;
      case ThreatTier.med:
        return kColorMed;
      case ThreatTier.low:
        return kColorLow;
    }
  }

  /// Dot radius in logical pixels (FR-005).
  double get dotSize {
    switch (tier) {
      case ThreatTier.high:
        return 20.0;
      case ThreatTier.med:
        return 16.0;
      case ThreatTier.low:
        return 12.0;
    }
  }

  ThreatMarker copyWith({
    int? targetId,
    ThreatTier? tier,
    double? lat,
    double? lon,
    double? threatScore,
    double? panAngle,
    double? tiltAngle,
    DateTime? lastUpdated,
    MarkerState? markerState,
    bool? isSelected,
    double? distanceToUserM,
    double? lrfDistanceM,
    DateTime? fadingStartedAt,
  }) {
    return ThreatMarker(
      targetId: targetId ?? this.targetId,
      tier: tier ?? this.tier,
      lat: lat ?? this.lat,
      lon: lon ?? this.lon,
      threatScore: threatScore ?? this.threatScore,
      panAngle: panAngle ?? this.panAngle,
      tiltAngle: tiltAngle ?? this.tiltAngle,
      lastUpdated: lastUpdated ?? this.lastUpdated,
      markerState: markerState ?? this.markerState,
      isSelected: isSelected ?? this.isSelected,
      distanceToUserM: distanceToUserM ?? this.distanceToUserM,
      lrfDistanceM: lrfDistanceM ?? this.lrfDistanceM,
      fadingStartedAt: fadingStartedAt ?? this.fadingStartedAt,
    );
  }
}
