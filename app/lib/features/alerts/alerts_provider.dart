import 'dart:async';

import 'package:drift/drift.dart' as drift;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../database/alert_log_dao.dart';
import '../../database/app_database.dart';
import '../../main.dart';
import '../../models/alert_log_entry.dart';
import '../../features/map/telemetry_provider.dart';
import '../../features/setup/setup_provider.dart';
import '../../models/sentry_config.dart';
import '../../models/telemetry_record.dart';

/// Provider for the full alert log list.
final alertsProvider =
    StateNotifierProvider<AlertsNotifier, List<AlertLogData>>((ref) {
  final db = ref.watch(appDatabaseProvider);
  dynamic mqtt;
  try {
    mqtt = ref.watch(mqttServiceProvider);
  } catch (_) {}
  SentryConfig? config;
  try {
    config = ref.watch(sentryConfigProvider);
  } catch (_) {}
  return AlertsNotifier(db.alertLogDao, mqtt, config: config);
});

/// Manages the persisted alert log, backed by Drift watch stream.
///
/// Telemetry arrives at ~20 Hz; logging every record would explode the SQLite
/// file within minutes. Only log MED/HIGH tier records when the
/// `(target_id, tier)` pair changes (i.e. a new threat or a tier escalation).
/// On startup we also drop anything older than the configured retention.
class AlertsNotifier extends StateNotifier<List<AlertLogData>> {
  AlertsNotifier(this._dao, dynamic mqttService, {SentryConfig? config})
      : super([]) {
    _watchSub = _dao.watchAll().listen((entries) => state = entries);
    if (mqttService != null) {
      _telemetrySub =
          (mqttService.telemetryStream as Stream<TelemetryRecord>)
              .listen(_onTelemetry);
    }
    // Purge stale entries once at startup; do not block construction.
    final days = config?.retentionDays ?? 7;
    unawaited(purgeOldEntries(days));
  }

  final AlertLogDao _dao;
  StreamSubscription<List<AlertLogData>>? _watchSub;
  StreamSubscription<TelemetryRecord>? _telemetrySub;
  // Last logged tier per target — used to suppress duplicate inserts at the
  // 20 Hz telemetry rate. Only tier transitions and new targets land in the DB.
  final Map<int, ThreatTier> _lastLoggedTier = {};

  Future<void> _onTelemetry(TelemetryRecord record) async {
    // Skip LOW — operator log only tracks meaningful threats.
    if (record.tier == ThreatTier.low) return;
    final previous = _lastLoggedTier[record.targetId];
    if (previous == record.tier) return;
    _lastLoggedTier[record.targetId] = record.tier;
    try {
      final entry = AlertLogEntry.fromTelemetryRecord(record);
      await _dao.insertEntry(AlertLogCompanion(
        targetId: drift.Value(entry.targetId),
        sessionId: drift.Value(entry.sessionId),
        timestampUtc: drift.Value(entry.timestampUtcMs),
        tier: drift.Value(entry.tier),
        threatScore: drift.Value(entry.threatScore),
        lat: drift.Value(entry.lat),
        lon: drift.Value(entry.lon),
        lrfDistanceM: drift.Value(entry.lrfDistanceM),
        panAngle: drift.Value(entry.panAngle),
        tiltAngle: drift.Value(entry.tiltAngle),
        distanceToUserM: drift.Value(entry.distanceToUserM),
      ));
    } catch (_) {}
  }

  /// Deletes entries older than [retentionDays].
  Future<void> purgeOldEntries(int retentionDays) async {
    final cutoff = DateTime.now().subtract(Duration(days: retentionDays));
    await _dao.deleteOlderThan(cutoff);
  }

  @override
  void dispose() {
    _watchSub?.cancel();
    _telemetrySub?.cancel();
    super.dispose();
  }
}
