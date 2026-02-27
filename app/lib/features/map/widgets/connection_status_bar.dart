import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme.dart';
import '../../../models/connection_state.dart';
import '../connection_provider.dart';

/// HUD bar showing MQTT connection state.
/// Visible only when not [SentryConnectionState.online].
class ConnectionStatusBar extends ConsumerWidget {
  const ConnectionStatusBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final connectionState = ref.watch(connectionStateProvider);

    if (connectionState == SentryConnectionState.online) {
      return const SizedBox.shrink();
    }

    final Color barColor;
    final String message;

    switch (connectionState) {
      case SentryConnectionState.reconnecting:
        barColor = kColorMed;
        message = '[MQTT] Reconnecting…';
      case SentryConnectionState.offline:
        barColor = kColorOffline;
        message = '[SENTRY] System Offline';
      case SentryConnectionState.online:
        return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: barColor.withValues(alpha: 0.9),
      child: Row(
        children: [
          Icon(
            connectionState == SentryConnectionState.reconnecting
                ? Icons.sync
                : Icons.wifi_off,
            color: Colors.white,
            size: 16,
          ),
          const SizedBox(width: 8),
          Text(
            message,
            style: const TextStyle(
              color: Colors.white,
              fontFamily: 'RobotoMono',
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
