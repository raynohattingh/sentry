import 'package:drift/drift.dart';

import 'app_database.dart';

part 'alert_log_dao.g.dart';

@DriftAccessor(tables: [AlertLog])
class AlertLogDao extends DatabaseAccessor<AppDatabase>
    with _$AlertLogDaoMixin {
  AlertLogDao(super.db);

  /// Inserts a new alert log entry.
  Future<int> insertEntry(AlertLogCompanion entry) =>
      into(alertLog).insert(entry);

  /// Watches all entries, ordered newest-first.
  Stream<List<AlertLogData>> watchAll() =>
      (select(alertLog)..orderBy([(t) => OrderingTerm.desc(t.timestampUtc)]))
          .watch();

  /// Returns all entries for a specific [targetId].
  Future<List<AlertLogData>> getByTargetId(int targetId) =>
      (select(alertLog)..where((t) => t.targetId.equals(targetId))).get();

  /// Deletes entries older than [cutoff].
  Future<int> deleteOlderThan(DateTime cutoff) =>
      (delete(alertLog)
            ..where(
                (t) => t.timestampUtc.isSmallerThanValue(
                    cutoff.millisecondsSinceEpoch)))
          .go();
}
