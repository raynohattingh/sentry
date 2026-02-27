import 'dart:async';

import 'package:drift/drift.dart' as drift;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../database/alert_log_dao.dart';
import '../../database/app_database.dart';
import '../../main.dart';
import '../../models/alert_log_entry.dart';
import '../../features/map/telemetry_provider.dart';
import '../../models/telemetry_record.dart';

/// Provider for the full alert log list.
final alertsProvider =
    StateNotifierProvider<AlertsNotifier, List<AlertLogData>>((ref) {
  final db = ref.watch(appDatabaseProvider);
  dynamic mqtt;
  try {
    mqtt = ref.watch(mqttServiceProvider);
  } catch (_) {}
  return AlertsNotifier(db.alertLogDao, mqtt);
});

/// Manages the persisted alert log, backed by Drift watch stream.
class AlertsNotifier extends StateNotifier<List<AlertLogData>> {
  AlertsNotifier(this._dao, dynamic mqttService) : super([]) {
    _watchSub = _dao.watchAll().listen((entries) => state = entries);
    if (mqttService != null) {
      _telemetrySub =
          (mqttService.telemetryStream as Stream<TelemetryRecord>)
              .listen(_onTelemetry);
    }
  }

  final AlertLogDao _dao;
  StreamSubscription<List<AlertLogData>>? _watchSub;
  StreamSubscription<TelemetryRecord>? _telemetrySub;

  Future<void> _onTelemetry(TelemetryRecord record) async {
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
