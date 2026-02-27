import 'dart:async';

import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Abstract location service interface.
abstract class LocationService {
  Stream<LatLng?> get locationStream;
  Future<bool> get hasPermission;
  Future<bool> requestPermission();

  /// Haversine distance between two coordinates in metres.
  static double distanceBetweenMetres(LatLng a, LatLng b) {
    return Geolocator.distanceBetween(
        a.latitude, a.longitude, b.latitude, b.longitude);
  }
}

/// Concrete location service using geolocator.
class LocationServiceImpl implements LocationService {
  LocationServiceImpl() {
    _init();
  }

  final StreamController<LatLng?> _controller =
      StreamController<LatLng?>.broadcast();

  StreamSubscription<Position>? _positionSub;

  void _init() {
    _positionSub = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 5,
      ),
    ).listen(
      (pos) => _controller.add(LatLng(pos.latitude, pos.longitude)),
      onError: (_) => _controller.add(null),
    );
  }

  @override
  Stream<LatLng?> get locationStream => _controller.stream;

  @override
  Future<bool> get hasPermission async {
    final permission = await Geolocator.checkPermission();
    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  @override
  Future<bool> requestPermission() async {
    final permission = await Geolocator.requestPermission();
    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  void dispose() {
    _positionSub?.cancel();
    _controller.close();
  }
}
