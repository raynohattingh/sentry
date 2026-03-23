import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../models/notification_preferences.dart';
import '../../models/safety_status.dart';
import '../../models/threat_marker.dart';
import '../map/telemetry_provider.dart';
import 'settings_provider.dart';

/// Settings screen — notifications, alert log retention, calibration link.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final List<int> _retentionOptions = [1, 7, 30];

  @override
  Widget build(BuildContext context) {
    final prefs = ref.watch(notificationPreferencesProvider);
    final safetyStatus = ref.watch(safetyStatusStreamProvider).valueOrNull;

    return Scaffold(
      backgroundColor: kColorBackground,
      appBar: AppBar(title: const Text('[SENTRY] Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionHeader('Notifications'),
          _tierRow('HIGH Alerts', ThreatTier.high, prefs),
          _tierRow('MED Alerts', ThreatTier.med, prefs),
          _tierRow('LOW Alerts', ThreatTier.low, prefs),
          const SizedBox(height: 24),
          _sectionHeader('Alert Log'),
          _retentionPicker(prefs),
          const SizedBox(height: 24),
          _sectionHeader('Sentry'),
          if (safetyStatus != null) _safetySummaryTile(safetyStatus),
          ListTile(
            title: const Text('Calibration',
                style: TextStyle(color: Colors.white)),
            subtitle: const Text('Set GPS position & True North offset',
                style: TextStyle(color: Colors.white54, fontSize: 12)),
            trailing: const Icon(Icons.arrow_forward_ios,
                color: Colors.white54, size: 14),
            onTap: () => context.go('/calibration'),
          ),
          const SizedBox(height: 24),
          _sectionHeader('Connection'),
          ListTile(
            title: const Text('Re-configure Broker',
                style: TextStyle(color: Colors.white)),
            subtitle: const Text('Change MQTT / video credentials',
                style: TextStyle(color: Colors.white54, fontSize: 12)),
            trailing: const Icon(Icons.arrow_forward_ios,
                color: Colors.white54, size: 14),
            onTap: () => context.go('/setup'),
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(
          title.toUpperCase(),
          style: const TextStyle(
              color: Colors.white54, fontSize: 11, letterSpacing: 1.5),
        ),
      );

  Widget _tierRow(String label, ThreatTier tier, NotificationPreferences prefs) {
    final mode = _modeFor(tier, prefs);
    return Row(
      children: [
        Text(label, style: const TextStyle(color: Colors.white, fontSize: 14)),
        const Spacer(),
        DropdownButton<NotificationMode>(
          value: mode,
          dropdownColor: kColorSurface,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          items: NotificationMode.values.map((m) {
            return DropdownMenuItem(
              value: m,
              child: Text(m.name.toUpperCase()),
            );
          }).toList(),
          onChanged: (newMode) {
            if (newMode == null) return;
            final updated = _setMode(tier, newMode, prefs);
            ref.read(notificationPreferencesProvider.notifier).update(updated);
          },
        ),
      ],
    );
  }

  Widget _retentionPicker(NotificationPreferences prefs) {
    // Use the alert log retention from setup provider
    return Row(
      children: [
        const Text('Retention period',
            style: TextStyle(color: Colors.white, fontSize: 14)),
        const Spacer(),
        DropdownButton<int>(
          value: 7,
          dropdownColor: kColorSurface,
          style: const TextStyle(color: Colors.white, fontSize: 13),
          items: _retentionOptions.map((days) {
            final label = days == 1 ? '24 hours' : '$days days';
            return DropdownMenuItem(value: days, child: Text(label));
          }).toList(),
          onChanged: (_) {
            // Save retention days to config
          },
        ),
      ],
    );
  }

  NotificationMode _modeFor(ThreatTier tier, NotificationPreferences prefs) {
    switch (tier) {
      case ThreatTier.high:
        return prefs.highMode;
      case ThreatTier.med:
        return prefs.medMode;
      case ThreatTier.low:
        return prefs.lowMode;
    }
  }

  NotificationPreferences _setMode(
      ThreatTier tier, NotificationMode mode, NotificationPreferences prefs) {
    switch (tier) {
      case ThreatTier.high:
        return prefs.copyWith(highMode: mode);
      case ThreatTier.med:
        return prefs.copyWith(medMode: mode);
      case ThreatTier.low:
        return prefs.copyWith(lowMode: mode);
    }
  }

  Widget _safetySummaryTile(SafetyStatusRecord status) {
    final String motionText = status.motionAllowed
        ? 'ALLOWED'
        : 'BLOCKED (${status.motionBlockReason ?? 'UNKNOWN'})';

    return ListTile(
      title: Text(
        'Safety Profile: ${status.housingProfile.value}',
        style: const TextStyle(color: Colors.white),
      ),
      subtitle: Text(
        'Protection: ${status.protectionMode.value}\n'
        'Motion: $motionText\n'
        'Validated switches: ${status.validatedSwitches.length}/4',
        style: const TextStyle(color: Colors.white54, fontSize: 12),
      ),
    );
  }
}
