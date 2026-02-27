import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../features/setup/setup_provider.dart';

import '../map/telemetry_provider.dart';

/// Calibration screen — pins sentry position and True North offset.
class CalibrationScreen extends ConsumerStatefulWidget {
  const CalibrationScreen({super.key});

  @override
  ConsumerState<CalibrationScreen> createState() => _CalibrationScreenState();
}

class _CalibrationScreenState extends ConsumerState<CalibrationScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _latCtrl;
  late final TextEditingController _lonCtrl;
  double _northOffset = 0.0;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final config = ref.read(sentryConfigProvider);
    _latCtrl =
        TextEditingController(text: config.sentryLat?.toString() ?? '');
    _lonCtrl =
        TextEditingController(text: config.sentryLon?.toString() ?? '');
    _northOffset = config.northOffsetDegrees;
  }

  @override
  void dispose() {
    _latCtrl.dispose();
    _lonCtrl.dispose();
    super.dispose();
  }

  Future<void> _pinMyLocation() async {
    final service = ref.read(locationServiceProvider);
    if (service == null) return;
    final latLng = await service.locationStream.first;
    if (latLng != null && mounted) {
      setState(() {
        _latCtrl.text = latLng.latitude.toStringAsFixed(6);
        _lonCtrl.text = latLng.longitude.toStringAsFixed(6);
      });
    }
  }

  Future<void> _save() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _saving = true);
    try {
      final current = ref.read(sentryConfigProvider);
      await ref.read(sentryConfigProvider.notifier).save(
            current.copyWith(
              sentryLat: double.tryParse(_latCtrl.text.trim()),
              sentryLon: double.tryParse(_lonCtrl.text.trim()),
              northOffsetDegrees: _northOffset,
            ),
          );
      if (mounted) Navigator.pop(context);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kColorBackground,
      appBar: AppBar(title: const Text('[SENTRY] Calibration')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Sentry GPS Position',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              TextFormField(
                controller: _latCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  labelText: 'Latitude',
                  labelStyle: TextStyle(color: Colors.white54),
                  enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: Colors.white24)),
                ),
                keyboardType: const TextInputType.numberWithOptions(
                    decimal: true, signed: true),
                validator: (v) => v == null || v.isEmpty
                    ? null
                    : double.tryParse(v) == null
                        ? 'Invalid latitude'
                        : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _lonCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  labelText: 'Longitude',
                  labelStyle: TextStyle(color: Colors.white54),
                  enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: Colors.white24)),
                ),
                keyboardType: const TextInputType.numberWithOptions(
                    decimal: true, signed: true),
                validator: (v) => v == null || v.isEmpty
                    ? null
                    : double.tryParse(v) == null
                        ? 'Invalid longitude'
                        : null,
              ),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                icon: const Icon(Icons.my_location),
                label: const Text('Pin My Location'),
                onPressed: _pinMyLocation,
                style: ElevatedButton.styleFrom(
                    backgroundColor: kColorSurface),
              ),
              const SizedBox(height: 32),
              const Text('True North Offset',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(
                '${_northOffset.toStringAsFixed(1)}°',
                style: const TextStyle(
                    color: kColorMed,
                    fontSize: 24,
                    fontFamily: 'RobotoMono'),
              ),
              Slider(
                value: _northOffset,
                min: -180.0,
                max: 180.0,
                divisions: 360,
                activeColor: kColorMed,
                onChanged: (v) => setState(() => _northOffset = v),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: kColorHigh,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: _saving
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('Save Calibration'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
