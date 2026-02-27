import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../telemetry_provider.dart';

final _userLocationStreamProvider = StreamProvider<LatLng?>((ref) {
  final service = ref.watch(locationServiceProvider);
  return service?.locationStream ?? const Stream.empty();
});

/// Blue dot showing the user's current GPS position.
class UserLocationLayer extends ConsumerWidget {
  const UserLocationLayer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locationAsync = ref.watch(_userLocationStreamProvider);
    return locationAsync.when(
      data: (latLng) {
        if (latLng == null) return const MarkerLayer(markers: []);
        return MarkerLayer(
          markers: [
            Marker(
              point: latLng,
              width: 16,
              height: 16,
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.blue,
                  border: Border.all(color: Colors.white, width: 2),
                ),
              ),
            ),
          ],
        );
      },
      loading: () => const MarkerLayer(markers: []),
      error: (context, err) => const MarkerLayer(markers: []),
    );
  }
}
