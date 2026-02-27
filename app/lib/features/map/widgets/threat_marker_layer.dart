import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_marker_cluster/flutter_map_marker_cluster.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/theme.dart';
import '../../../models/threat_marker.dart';
import '../selection_provider.dart';
import '../telemetry_provider.dart';

/// Map layer rendering all threat markers.
/// Uses [MarkerClusterLayerWidget] when 5+ active markers are present (T070).
class ThreatMarkerLayer extends ConsumerWidget {
  const ThreatMarkerLayer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final markers = ref.watch(threatMarkersProvider);
    final selected = ref.watch(selectedMarkerProvider);

    final activeMarkers = markers.entries
        .where((e) => e.value.markerState != MarkerState.removed)
        .toList();

    final mapMarkers = activeMarkers.map((entry) {
      final marker = entry.value;
      final isFading = marker.markerState == MarkerState.fading;
      final size = marker.dotSize;
      final isSelected = selected == marker.targetId;

      return Marker(
        point: LatLng(marker.lat, marker.lon),
        width: size + (isSelected ? 8 : 0),
        height: size + (isSelected ? 8 : 0),
        child: GestureDetector(
          onTap: () => ref
              .read(selectedMarkerProvider.notifier)
              .select(marker.targetId),
          child: AnimatedOpacity(
            opacity: isFading ? 0.4 : 1.0,
            duration: const Duration(seconds: 2),
            child: _MarkerDot(
              marker: marker,
              size: size,
              isSelected: isSelected,
            ),
          ),
        ),
      );
    }).toList();

    // Use clustering when 5+ active markers (T070)
    if (activeMarkers.length >= 5) {
      return MarkerClusterLayerWidget(
        options: MarkerClusterLayerOptions(
          maxClusterRadius: 45,
          size: const Size(40, 40),          markers: mapMarkers,
          builder: (context, clusterMarkers) {
            return Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: kColorHigh.withValues(alpha: 0.85),
                border: Border.all(color: Colors.white, width: 2),
              ),
              child: Center(
                child: Text(
                  '${clusterMarkers.length}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ),
            );
          },
        ),
      );
    }

    return MarkerLayer(markers: mapMarkers);
  }
}

class _MarkerDot extends StatefulWidget {
  const _MarkerDot({
    required this.marker,
    required this.size,
    required this.isSelected,
  });

  final ThreatMarker marker;
  final double size;
  final bool isSelected;

  @override
  State<_MarkerDot> createState() => _MarkerDotState();
}

class _MarkerDotState extends State<_MarkerDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.3).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    if (widget.marker.tier == ThreatTier.high) {
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.marker.color;
    final size = widget.size;

    if (widget.marker.tier == ThreatTier.high) {
      return AnimatedBuilder(
        animation: _pulseAnimation,
        builder: (context, anim) => Container(
          width: size * _pulseAnimation.value,
          height: size * _pulseAnimation.value,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: 0.6),
                blurRadius: 8 * _pulseAnimation.value,
                spreadRadius: 2,
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        border: widget.isSelected
            ? Border.all(color: Colors.white, width: 2)
            : null,
      ),
    );
  }
}
