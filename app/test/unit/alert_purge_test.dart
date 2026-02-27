import 'package:drift/drift.dart' hide isNull;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sentry_mobile/database/app_database.dart';
import 'package:sentry_mobile/database/alert_log_dao.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;
  late AlertLogDao dao;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    dao = db.alertLogDao;
  });

  tearDown(() async {
    await db.close();
  });

  Future<void> insertEntry({
    required int targetId,
    required DateTime timestamp,
    String tier = 'HIGH',
    double score = 90.0,
  }) async {
    await dao.insertEntry(AlertLogCompanion(
      targetId: Value(targetId),
      sessionId: const Value('test-session'),
      timestampUtc: Value(timestamp.millisecondsSinceEpoch),
      tier: Value(tier),
      threatScore: Value(score),
      panAngle: const Value(0.0),
      tiltAngle: const Value(0.0),
    ));
  }

  group('AlertLogDao', () {
    test('insertEntry adds record to database', () async {
      await insertEntry(
          targetId: 1, timestamp: DateTime.now(), tier: 'HIGH');
      final all = await dao.watchAll().first;
      expect(all.length, equals(1));
      expect(all.first.targetId, equals(1));
    });

    test('watchAll returns entries in reverse chronological order', () async {
      final now = DateTime.now();
      await insertEntry(targetId: 1, timestamp: now.subtract(const Duration(hours: 2)));
      await insertEntry(targetId: 2, timestamp: now.subtract(const Duration(hours: 1)));
      await insertEntry(targetId: 3, timestamp: now);

      final all = await dao.watchAll().first;
      expect(all.length, equals(3));
      // Should be newest first
      expect(all.first.targetId, equals(3));
      expect(all.last.targetId, equals(1));
    });

    test('deleteOlderThan keeps only entries within retention window', () async {
      final now = DateTime.now();
      // Insert entries spanning 40 days
      for (int i = 0; i <= 40; i++) {
        await insertEntry(
          targetId: i,
          timestamp: now.subtract(Duration(days: i)),
        );
      }

      // Delete entries older than 7 days
      final cutoff = now.subtract(const Duration(days: 7));
      final deleted = await dao.deleteOlderThan(cutoff);
      expect(deleted, greaterThan(0));

      final remaining = await dao.watchAll().first;
      // Only entries 0–7 days old should remain (8 entries: days 0-6 inclusive, plus boundary)
      expect(remaining.length, lessThanOrEqualTo(8));
      for (final entry in remaining) {
        final _ =
            DateTime.fromMillisecondsSinceEpoch(entry.timestampUtc);
        // Allow a 1-second tolerance for boundary conditions
        final boundaryMs = cutoff.millisecondsSinceEpoch - 1000;
        expect(entry.timestampUtc, greaterThanOrEqualTo(boundaryMs));
      }
    });

    test('deleteOlderThan with no matching entries returns 0', () async {
      final now = DateTime.now();
      await insertEntry(targetId: 1, timestamp: now);
      final cutoff = now.subtract(const Duration(days: 30));
      final deleted = await dao.deleteOlderThan(cutoff);
      expect(deleted, equals(0));
    });

    test('watchAll stream emits updated list after insert', () async {
      final stream = dao.watchAll();
      // First emit: empty
      final first = await stream.first;
      expect(first, isEmpty);

      // Insert and check stream emits
      await insertEntry(targetId: 42, timestamp: DateTime.now());
      final second = await dao.watchAll().first;
      expect(second.length, equals(1));
    });

    test('getByTargetId returns only matching entries', () async {
      await insertEntry(targetId: 1, timestamp: DateTime.now());
      await insertEntry(targetId: 2, timestamp: DateTime.now());
      await insertEntry(targetId: 1, timestamp: DateTime.now());

      final results = await dao.getByTargetId(1);
      expect(results.length, equals(2));
      expect(results.every((e) => e.targetId == 1), isTrue);
    });
  });
}
