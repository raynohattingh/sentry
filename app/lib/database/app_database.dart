import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'alert_log_dao.dart';

part 'app_database.g.dart';

/// Drift table definition for the alert log.
class AlertLog extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get targetId => integer()();
  TextColumn get sessionId => text()();
  IntColumn get timestampUtc => integer()(); // Unix ms — indexed
  TextColumn get tier => text()(); // "LOW" | "MED" | "HIGH"
  RealColumn get threatScore => real()();
  RealColumn get lat => real().nullable()();
  RealColumn get lon => real().nullable()();
  RealColumn get lrfDistanceM => real().nullable()();
  RealColumn get panAngle => real()();
  RealColumn get tiltAngle => real()();
  RealColumn get distanceToUserM => real().nullable()();
}

@DriftDatabase(tables: [AlertLog], daos: [AlertLogDao])
class AppDatabase extends _$AppDatabase {
  AppDatabase([QueryExecutor? executor]) : super(executor ?? _openConnection());

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) async {
          await m.createAll();
          // Create timestamp index manually
          await customStatement(
            'CREATE INDEX IF NOT EXISTS alert_log_timestamp_idx ON alert_log (timestamp_utc)',
          );
        },
      );
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'sentry_mobile.db'));
    return NativeDatabase(file);
  });
}
