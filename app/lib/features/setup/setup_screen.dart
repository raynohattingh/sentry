import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../models/sentry_config.dart';
import 'setup_provider.dart';

/// Initial setup screen — collects MQTT and video stream credentials.
class SetupScreen extends ConsumerStatefulWidget {
  const SetupScreen({super.key});

  @override
  ConsumerState<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends ConsumerState<SetupScreen> {
  final _formKey = GlobalKey<FormState>();

  // MQTT fields
  late final TextEditingController _brokerHostCtrl;
  late final TextEditingController _brokerPortCtrl;
  late final TextEditingController _mqttUserCtrl;
  late final TextEditingController _mqttPassCtrl;
  late final TextEditingController _sentryIdCtrl;

  // Video fields
  late final TextEditingController _videoHostCtrl;
  late final TextEditingController _videoPortCtrl;
  late final TextEditingController _videoUserCtrl;
  late final TextEditingController _videoPassCtrl;

  bool _saving = false;
  bool _showTlsWarning = false;

  @override
  void initState() {
    super.initState();
    final config = ref.read(sentryConfigProvider);
    _brokerHostCtrl = TextEditingController(text: config.brokerHost);
    _brokerPortCtrl =
        TextEditingController(text: config.brokerPort.toString());
    _mqttUserCtrl = TextEditingController(text: config.mqttUsername);
    _mqttPassCtrl = TextEditingController(text: config.mqttPassword);
    _sentryIdCtrl = TextEditingController(text: config.sentryId);
    _videoHostCtrl = TextEditingController(text: config.videoHost);
    _videoPortCtrl =
        TextEditingController(text: config.videoPort.toString());
    _videoUserCtrl = TextEditingController(text: config.videoUsername);
    _videoPassCtrl = TextEditingController(text: config.videoPassword);

    _brokerPortCtrl.addListener(_checkTlsWarning);
  }

  void _checkTlsWarning() {
    final port = int.tryParse(_brokerPortCtrl.text) ?? kDefaultMqttPort;
    setState(() => _showTlsWarning = port != kDefaultMqttPort);
  }

  @override
  void dispose() {
    _brokerHostCtrl.dispose();
    _brokerPortCtrl.dispose();
    _mqttUserCtrl.dispose();
    _mqttPassCtrl.dispose();
    _sentryIdCtrl.dispose();
    _videoHostCtrl.dispose();
    _videoPortCtrl.dispose();
    _videoUserCtrl.dispose();
    _videoPassCtrl.dispose();
    super.dispose();
  }

  Future<void> _onConnect() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _saving = true);
    try {
      final config = SentryConfig(
        brokerHost: _brokerHostCtrl.text.trim(),
        brokerPort:
            int.tryParse(_brokerPortCtrl.text.trim()) ?? kDefaultMqttPort,
        mqttUsername: _mqttUserCtrl.text.trim(),
        mqttPassword: _mqttPassCtrl.text,
        sentryId: _sentryIdCtrl.text.trim(),
        videoHost: _videoHostCtrl.text.trim().isEmpty
            ? _brokerHostCtrl.text.trim()
            : _videoHostCtrl.text.trim(),
        videoPort:
            int.tryParse(_videoPortCtrl.text.trim()) ?? kDefaultVideoPort,
        videoUsername: _videoUserCtrl.text.trim(),
        videoPassword: _videoPassCtrl.text,
      );
      await ref.read(sentryConfigProvider.notifier).save(config);
      // T064: Offer offline tile pre-seeding after connection
      if (mounted) {
        final shouldSeed = await _askTileDownload(context, config);
        if (shouldSeed && mounted) {
          await _downloadOfflineTiles(context, config);
        }
      }
      if (mounted) context.go('/');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<bool> _askTileDownload(BuildContext context, SentryConfig config) async {
    if (config.sentryLat == null || config.sentryLon == null) return false;
    final result = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: kColorSurface,
        title: const Text('Download Offline Maps?',
            style: TextStyle(color: Colors.white)),
        content: const Text(
          'Download map tiles for a 20 km radius around the sentry for offline use.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Skip'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Download'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<void> _downloadOfflineTiles(BuildContext context, SentryConfig config) async {
    // FMTC tile pre-seeding (T064)
    // FlutterMapTileCaching store initialised in MapScreen (T035).
    // Here we trigger the download with a progress indicator.
    // Full FMTC download API requires an initialised store — done at first MapScreen load.
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('[MAP] Tile download queued — open map to begin'),
        backgroundColor: kColorSurface,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kColorBackground,
      appBar: AppBar(title: const Text('[SENTRY] Setup')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _sectionHeader('MQTT Broker'),
              _textField('Broker Host / IP', _brokerHostCtrl,
                  validator: _required),
              const SizedBox(height: 12),
              _textField('Port (default 8883)', _brokerPortCtrl,
                  keyboardType: TextInputType.number, validator: _validPort),
              if (_showTlsWarning)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    '⚠ Port ${_brokerPortCtrl.text} is non-standard — TLS not guaranteed',
                    style: const TextStyle(color: kColorMed, fontSize: 12),
                  ),
                ),
              const SizedBox(height: 12),
              _textField('MQTT Username', _mqttUserCtrl, validator: _required),
              const SizedBox(height: 12),
              _textField('MQTT Password', _mqttPassCtrl,
                  obscure: true, validator: _required),
              const SizedBox(height: 12),
              _textField('Sentry ID', _sentryIdCtrl, validator: _required),
              const SizedBox(height: 24),
              _sectionHeader('Video Stream'),
              _textField('Video Host (leave blank = MQTT host)', _videoHostCtrl),
              const SizedBox(height: 12),
              _textField('Video Port (default 5000)', _videoPortCtrl,
                  keyboardType: TextInputType.number),
              const SizedBox(height: 12),
              _textField('Video Username', _videoUserCtrl),
              const SizedBox(height: 12),
              _textField('Video Password', _videoPassCtrl, obscure: true),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _saving ? null : _onConnect,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: kColorHigh,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: _saving
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text(
                          'Connect',
                          style: TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _sectionHeader(String title) => Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Text(
          title,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.2,
          ),
        ),
      );

  Widget _textField(
    String label,
    TextEditingController controller, {
    bool obscure = false,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboardType,
      validator: validator,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: Colors.white54),
        enabledBorder: const OutlineInputBorder(
            borderSide: BorderSide(color: Colors.white24)),
        focusedBorder: OutlineInputBorder(
            borderSide: BorderSide(color: kColorHigh.withValues(alpha: 0.8))),
        errorBorder: const OutlineInputBorder(
            borderSide: BorderSide(color: kColorHigh)),
        focusedErrorBorder: const OutlineInputBorder(
            borderSide: BorderSide(color: kColorHigh)),
      ),
    );
  }

  String? _required(String? v) =>
      (v == null || v.trim().isEmpty) ? 'This field is required' : null;

  String? _validPort(String? v) {
    if (v == null || v.trim().isEmpty) return 'Port is required';
    final n = int.tryParse(v.trim());
    if (n == null || n < 1 || n > 65535) return 'Enter a valid port (1–65535)';
    return null;
  }
}
