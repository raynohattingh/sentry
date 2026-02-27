import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

import '../../core/theme.dart';
import '../../features/alerts/alert_panel.dart';
import '../../features/video/video_modal.dart';
import '../../features/setup/setup_provider.dart';
import '../../models/connection_state.dart';
import '../../models/sentry_config.dart';
import 'connection_provider.dart';
import 'widgets/connection_status_bar.dart';
import 'widgets/sentry_mode_badge.dart';
import 'widgets/threat_marker_layer.dart';
import 'widgets/user_location_layer.dart';

/// Live tactical map home screen.
class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  final _mapController = MapController();
  bool _alertPanelOpen = false;
  bool _locationPermission = false;

  @override
  void initState() {
    super.initState();
    _checkLocationPermission();
  }

  Future<void> _checkLocationPermission() async {
    final perm = await Geolocator.checkPermission();
    if (mounted) {
      setState(() {
        _locationPermission = perm == LocationPermission.always ||
            perm == LocationPermission.whileInUse;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(sentryConfigProvider);
    final connectionState = ref.watch(connectionStateProvider);

    return Scaffold(
      backgroundColor: kColorBackground,
      appBar: AppBar(
        title: const Text('[SENTRY] Tactical Map',
            style: TextStyle(fontSize: 14, letterSpacing: 1)),
        actions: [
          // Video feed button (T056)
          IconButton(
            icon: const Icon(Icons.videocam),
            tooltip: 'View Feed',
            onPressed: connectionState == SentryConnectionState.online
                ? () => showVideoModal(context, ref)
                : null,
          ),
          // Override button — only when online (T063)
          if (connectionState == SentryConnectionState.online)
            IconButton(
              icon: const Icon(Icons.gamepad),
              tooltip: 'Manual Override',
              onPressed: () => context.go('/override'),
            ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => context.go('/settings'),
          ),
        ],
      ),
      body: Stack(
        children: [
          _buildMap(config),
          Positioned(top: 0, left: 0, right: 0,
              child: const ConnectionStatusBar()),
          Positioned(top: 48, right: 12, child: const SentryModeBadge()),
          if (!_locationPermission)
            Positioned(
              bottom: _alertPanelOpen ? 320 : 0,
              left: 0,
              right: 0,
              child: _buildLocationDeniedBanner(),
            ),
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: AlertPanel(
              isOpen: _alertPanelOpen,
              onToggle: () => setState(() => _alertPanelOpen = !_alertPanelOpen),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMap(SentryConfig config) {
    final sentryLatLng = config.sentryLat != null && config.sentryLon != null
        ? LatLng(config.sentryLat!, config.sentryLon!)
        : const LatLng(-26.2041, 28.0473); // Default: Joburg

    return FlutterMap(
      mapController: _mapController,
      options: MapOptions(
        initialCenter: sentryLatLng,
        initialZoom: 15.0,
        backgroundColor: kColorBackground,
      ),
      children: [
        TileLayer(
          urlTemplate:
              'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',
          userAgentPackageName: 'com.farmsentry.sentry_mobile',
        ),
        const ThreatMarkerLayer(),
        if (_locationPermission) const UserLocationLayer(),
        // Sentry position marker
        if (config.sentryLat != null && config.sentryLon != null)
          MarkerLayer(
            markers: [
              Marker(
                point: sentryLatLng,
                width: 20,
                height: 20,
                child: const Icon(
                  Icons.my_location,
                  color: Colors.lightBlueAccent,
                  size: 20,
                ),
              ),
            ],
          ),
      ],
    );
  }

  Widget _buildLocationDeniedBanner() {
    return MaterialBanner(
      backgroundColor: kColorBackground,
      content: const Text(
        '[LOCATION] Position unavailable — distances hidden',
        style: TextStyle(color: Colors.white70, fontSize: 12),
      ),
      actions: [
        TextButton(
          onPressed: () async {
            await Geolocator.openAppSettings();
          },
          child: const Text('Open Settings',
              style: TextStyle(color: kColorMed)),
        ),
      ],
    );
  }
}
