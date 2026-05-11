import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme.dart';
import '../../../models/telemetry_record.dart';
import '../telemetry_provider.dart';

/// HUD badge showing the sentry's current FSM state.
class SentryModeBadge extends ConsumerWidget {
  const SentryModeBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(sentryModeProvider);
    final (label, color) = _labelAndColor(mode);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color, width: 1),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontFamily: 'RobotoMono',
          fontSize: 11,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  (String, Color) _labelAndColor(FsmState? mode) {
    switch (mode) {
      case FsmState.scan:
        return ('SCAN', kColorOffline);
      case FsmState.acquire:
        return ('ACQUIRE', kColorMed);
      case FsmState.track:
        return ('TRACK', const Color(0xFFFFAA00) /* kColorAmber */); // amber
      case FsmState.search:
        return ('SEARCH', kColorHigh);
      case FsmState.manualOverride:
        return ('MANUAL', kColorHigh);
      case null:
        return ('—', kColorOffline);
    }
  }
}
