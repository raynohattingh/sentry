import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../features/map/connection_provider.dart';
import '../../features/setup/setup_provider.dart';
import '../../models/connection_state.dart';
import '../../models/safety_status.dart';
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
  DateTime _lastTouchTime = DateTime.now();

  // Cached references for safe use in dispose() (C6)
  MqttService? _cachedMqtt;
  String _cachedSentryId = '';

  @override
  void initState() {
    super.initState();
    try {
      _mqtt = ref.read(mqttServiceProvider);
      _cachedMqtt = _mqtt;
    } catch (_) {
      // mqttServiceProvider not overridden — OK in test/dev
    }
    try {
      _cachedSentryId = ref.read(sentryConfigProvider).sentryId;
    } catch (_) {
      // sentryConfigProvider not overridden — OK in test/dev
    }
  }

  void _onCommandChanged(ManualCommand command) {
    _currentCommand = command;
    _lastTouchTime = DateTime.now();
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
    // Dead-man's switch: auto-stop if no touch input for >2 seconds
    if (DateTime.now().difference(_lastTouchTime) > const Duration(seconds: 2)) {
      final stop = ManualCommand.zero(_cachedSentryId);
      _mqtt?.publishCommand(stop);
      _publishTimer?.cancel();
      _publishTimer = null;
      _currentCommand = null;
      return;
    }
    final cmd = _currentCommand;
    if (cmd == null) return;
    _mqtt?.publishCommand(cmd);
  }

  @override
  void dispose() {
    _publishTimer?.cancel();
    // Publish zero-velocity stop on exit using cached references (C6)
    _cachedMqtt?.publishCommand(ManualCommand.zero(_cachedSentryId));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connectionState = ref.watch(connectionStateProvider);
    final isOnline = connectionState == SentryConnectionState.online;
    final safetyStatus = ref.watch(safetyStatusStreamProvider).valueOrNull;
    final motionAllowed = safetyStatus?.motionAllowed ?? true;
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
            if (safetyStatus != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 24),
                child: _buildSafetyNotice(safetyStatus),
              ),
            JoystickWidget(
              sentryId: config.sentryId,
              disabled: !isOnline || !motionAllowed,
              onCommandChanged: (cmd) {
                _onCommandChanged(cmd);
                if (cmd.panVelocity == 0.0 && cmd.tiltVelocity == 0.0) {
                  _onJoystickReleased();
                }
              },
            ),
            const SizedBox(height: 24),
            Text(
              isOnline && motionAllowed ? 'DRAG TO CONTROL' : 'CONTROL BLOCKED',
              style: TextStyle(
                color: isOnline && motionAllowed ? Colors.white38 : kColorOffline,
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

  Widget _buildSafetyNotice(SafetyStatusRecord status) {
    final bool isTestBench = status.housingProfile == HousingProfile.testBench;
    final bool blocked = !status.motionAllowed;
    final Color color = blocked ? kColorHigh : kColorAmber;
    final String message = blocked
        ? '[SAFETY] Motion blocked — validate all four limit switches (${status.validatedSwitches.length}/4)'
        : isTestBench
            ? '[SAFETY] Reduced safety active — movement limited by configured software bounds'
            : '[SAFETY] Hardware limit protection active';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.25),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color),
      ),
      child: Text(
        message,
        style: TextStyle(
          color: blocked ? kColorHigh : kColorAmber,
          fontFamily: 'RobotoMono',
          fontSize: 12,
        ),
        textAlign: TextAlign.center,
      ),
    );
  }
}
