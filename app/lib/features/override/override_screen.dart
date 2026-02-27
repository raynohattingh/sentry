import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../features/map/connection_provider.dart';
import '../../features/setup/setup_provider.dart';
import '../../models/connection_state.dart';
import '../../models/manual_command.dart';
import '../../services/mqtt_service.dart';
import '../map/telemetry_provider.dart';
import 'joystick_widget.dart';

/// Manual turret override screen.
class OverrideScreen extends ConsumerStatefulWidget {
  const OverrideScreen({super.key});

  @override
  ConsumerState<OverrideScreen> createState() => _OverrideScreenState();
}

class _OverrideScreenState extends ConsumerState<OverrideScreen> {
  ManualCommand? _currentCommand;
  Timer? _publishTimer;
  MqttService? _mqtt;

  @override
  void initState() {
    super.initState();
    try {
      _mqtt = ref.read(mqttServiceProvider);
    } catch (_) {
      // mqttServiceProvider not overridden — OK in test/dev
    }
  }

  void _onCommandChanged(ManualCommand command) {
    _currentCommand = command;
    _publishTimer ??= Timer.periodic(
      Duration(milliseconds: kJoystickPublishIntervalMs),
      (_) => _publish(),
    );
  }

  void _onJoystickReleased() {
    _publishTimer?.cancel();
    _publishTimer = null;
    final config = ref.read(sentryConfigProvider);
    final stop = ManualCommand.zero(config.sentryId);
    _mqtt?.publishCommand(stop);
    _currentCommand = null;
  }

  void _publish() {
    final cmd = _currentCommand;
    if (cmd == null) return;
    _mqtt?.publishCommand(cmd);
  }

  @override
  void dispose() {
    _publishTimer?.cancel();
    // Publish zero-velocity stop on exit
    final config = ref.read(sentryConfigProvider);
    _mqtt?.publishCommand(ManualCommand.zero(config.sentryId));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connectionState = ref.watch(connectionStateProvider);
    final isOnline = connectionState == SentryConnectionState.online;
    final config = ref.watch(sentryConfigProvider);

    return Scaffold(
      backgroundColor: kColorBackground,
      appBar: AppBar(title: const Text('[SENTRY] Manual Override')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (!isOnline)
              Padding(
                padding: const EdgeInsets.only(bottom: 24),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: kColorOffline.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    '[TURRET] Offline — manual control unavailable',
                    style: TextStyle(
                      color: kColorOffline,
                      fontFamily: 'RobotoMono',
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            JoystickWidget(
              sentryId: config.sentryId,
              disabled: !isOnline,
              onCommandChanged: (cmd) {
                _onCommandChanged(cmd);
                if (cmd.panVelocity == 0.0 && cmd.tiltVelocity == 0.0) {
                  _onJoystickReleased();
                }
              },
            ),
            const SizedBox(height: 24),
            Text(
              isOnline ? 'DRAG TO CONTROL' : 'OFFLINE',
              style: TextStyle(
                color: isOnline ? Colors.white38 : kColorOffline,
                fontFamily: 'RobotoMono',
                fontSize: 11,
                letterSpacing: 2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
