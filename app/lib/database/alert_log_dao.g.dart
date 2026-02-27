// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'alert_log_dao.dart';

// ignore_for_file: type=lint
mixin _$AlertLogDaoMixin on DatabaseAccessor<AppDatabase> {
  $AlertLogTable get alertLog => attachedDatabase.alertLog;
  AlertLogDaoManager get managers => AlertLogDaoManager(this);
}

class AlertLogDaoManager {
  final _$AlertLogDaoMixin _db;
  AlertLogDaoManager(this._db);
  $$AlertLogTableTableManager get alertLog =>
      $$AlertLogTableTableManager(_db.attachedDatabase, _db.alertLog);
}
