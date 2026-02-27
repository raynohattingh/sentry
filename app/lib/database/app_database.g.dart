// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $AlertLogTable extends AlertLog
    with TableInfo<$AlertLogTable, AlertLogData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $AlertLogTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _targetIdMeta = const VerificationMeta(
    'targetId',
  );
  @override
  late final GeneratedColumn<int> targetId = GeneratedColumn<int>(
    'target_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sessionIdMeta = const VerificationMeta(
    'sessionId',
  );
  @override
  late final GeneratedColumn<String> sessionId = GeneratedColumn<String>(
    'session_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _timestampUtcMeta = const VerificationMeta(
    'timestampUtc',
  );
  @override
  late final GeneratedColumn<int> timestampUtc = GeneratedColumn<int>(
    'timestamp_utc',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _tierMeta = const VerificationMeta('tier');
  @override
  late final GeneratedColumn<String> tier = GeneratedColumn<String>(
    'tier',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _threatScoreMeta = const VerificationMeta(
    'threatScore',
  );
  @override
  late final GeneratedColumn<double> threatScore = GeneratedColumn<double>(
    'threat_score',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _latMeta = const VerificationMeta('lat');
  @override
  late final GeneratedColumn<double> lat = GeneratedColumn<double>(
    'lat',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _lonMeta = const VerificationMeta('lon');
  @override
  late final GeneratedColumn<double> lon = GeneratedColumn<double>(
    'lon',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _lrfDistanceMMeta = const VerificationMeta(
    'lrfDistanceM',
  );
  @override
  late final GeneratedColumn<double> lrfDistanceM = GeneratedColumn<double>(
    'lrf_distance_m',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _panAngleMeta = const VerificationMeta(
    'panAngle',
  );
  @override
  late final GeneratedColumn<double> panAngle = GeneratedColumn<double>(
    'pan_angle',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _tiltAngleMeta = const VerificationMeta(
    'tiltAngle',
  );
  @override
  late final GeneratedColumn<double> tiltAngle = GeneratedColumn<double>(
    'tilt_angle',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _distanceToUserMMeta = const VerificationMeta(
    'distanceToUserM',
  );
  @override
  late final GeneratedColumn<double> distanceToUserM = GeneratedColumn<double>(
    'distance_to_user_m',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    targetId,
    sessionId,
    timestampUtc,
    tier,
    threatScore,
    lat,
    lon,
    lrfDistanceM,
    panAngle,
    tiltAngle,
    distanceToUserM,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'alert_log';
  @override
  VerificationContext validateIntegrity(
    Insertable<AlertLogData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('target_id')) {
      context.handle(
        _targetIdMeta,
        targetId.isAcceptableOrUnknown(data['target_id']!, _targetIdMeta),
      );
    } else if (isInserting) {
      context.missing(_targetIdMeta);
    }
    if (data.containsKey('session_id')) {
      context.handle(
        _sessionIdMeta,
        sessionId.isAcceptableOrUnknown(data['session_id']!, _sessionIdMeta),
      );
    } else if (isInserting) {
      context.missing(_sessionIdMeta);
    }
    if (data.containsKey('timestamp_utc')) {
      context.handle(
        _timestampUtcMeta,
        timestampUtc.isAcceptableOrUnknown(
          data['timestamp_utc']!,
          _timestampUtcMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_timestampUtcMeta);
    }
    if (data.containsKey('tier')) {
      context.handle(
        _tierMeta,
        tier.isAcceptableOrUnknown(data['tier']!, _tierMeta),
      );
    } else if (isInserting) {
      context.missing(_tierMeta);
    }
    if (data.containsKey('threat_score')) {
      context.handle(
        _threatScoreMeta,
        threatScore.isAcceptableOrUnknown(
          data['threat_score']!,
          _threatScoreMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_threatScoreMeta);
    }
    if (data.containsKey('lat')) {
      context.handle(
        _latMeta,
        lat.isAcceptableOrUnknown(data['lat']!, _latMeta),
      );
    }
    if (data.containsKey('lon')) {
      context.handle(
        _lonMeta,
        lon.isAcceptableOrUnknown(data['lon']!, _lonMeta),
      );
    }
    if (data.containsKey('lrf_distance_m')) {
      context.handle(
        _lrfDistanceMMeta,
        lrfDistanceM.isAcceptableOrUnknown(
          data['lrf_distance_m']!,
          _lrfDistanceMMeta,
        ),
      );
    }
    if (data.containsKey('pan_angle')) {
      context.handle(
        _panAngleMeta,
        panAngle.isAcceptableOrUnknown(data['pan_angle']!, _panAngleMeta),
      );
    } else if (isInserting) {
      context.missing(_panAngleMeta);
    }
    if (data.containsKey('tilt_angle')) {
      context.handle(
        _tiltAngleMeta,
        tiltAngle.isAcceptableOrUnknown(data['tilt_angle']!, _tiltAngleMeta),
      );
    } else if (isInserting) {
      context.missing(_tiltAngleMeta);
    }
    if (data.containsKey('distance_to_user_m')) {
      context.handle(
        _distanceToUserMMeta,
        distanceToUserM.isAcceptableOrUnknown(
          data['distance_to_user_m']!,
          _distanceToUserMMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  AlertLogData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AlertLogData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      targetId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}target_id'],
      )!,
      sessionId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}session_id'],
      )!,
      timestampUtc: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}timestamp_utc'],
      )!,
      tier: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}tier'],
      )!,
      threatScore: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}threat_score'],
      )!,
      lat: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}lat'],
      ),
      lon: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}lon'],
      ),
      lrfDistanceM: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}lrf_distance_m'],
      ),
      panAngle: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}pan_angle'],
      )!,
      tiltAngle: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}tilt_angle'],
      )!,
      distanceToUserM: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}distance_to_user_m'],
      ),
    );
  }

  @override
  $AlertLogTable createAlias(String alias) {
    return $AlertLogTable(attachedDatabase, alias);
  }
}

class AlertLogData extends DataClass implements Insertable<AlertLogData> {
  final int id;
  final int targetId;
  final String sessionId;
  final int timestampUtc;
  final String tier;
  final double threatScore;
  final double? lat;
  final double? lon;
  final double? lrfDistanceM;
  final double panAngle;
  final double tiltAngle;
  final double? distanceToUserM;
  const AlertLogData({
    required this.id,
    required this.targetId,
    required this.sessionId,
    required this.timestampUtc,
    required this.tier,
    required this.threatScore,
    this.lat,
    this.lon,
    this.lrfDistanceM,
    required this.panAngle,
    required this.tiltAngle,
    this.distanceToUserM,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['target_id'] = Variable<int>(targetId);
    map['session_id'] = Variable<String>(sessionId);
    map['timestamp_utc'] = Variable<int>(timestampUtc);
    map['tier'] = Variable<String>(tier);
    map['threat_score'] = Variable<double>(threatScore);
    if (!nullToAbsent || lat != null) {
      map['lat'] = Variable<double>(lat);
    }
    if (!nullToAbsent || lon != null) {
      map['lon'] = Variable<double>(lon);
    }
    if (!nullToAbsent || lrfDistanceM != null) {
      map['lrf_distance_m'] = Variable<double>(lrfDistanceM);
    }
    map['pan_angle'] = Variable<double>(panAngle);
    map['tilt_angle'] = Variable<double>(tiltAngle);
    if (!nullToAbsent || distanceToUserM != null) {
      map['distance_to_user_m'] = Variable<double>(distanceToUserM);
    }
    return map;
  }

  AlertLogCompanion toCompanion(bool nullToAbsent) {
    return AlertLogCompanion(
      id: Value(id),
      targetId: Value(targetId),
      sessionId: Value(sessionId),
      timestampUtc: Value(timestampUtc),
      tier: Value(tier),
      threatScore: Value(threatScore),
      lat: lat == null && nullToAbsent ? const Value.absent() : Value(lat),
      lon: lon == null && nullToAbsent ? const Value.absent() : Value(lon),
      lrfDistanceM: lrfDistanceM == null && nullToAbsent
          ? const Value.absent()
          : Value(lrfDistanceM),
      panAngle: Value(panAngle),
      tiltAngle: Value(tiltAngle),
      distanceToUserM: distanceToUserM == null && nullToAbsent
          ? const Value.absent()
          : Value(distanceToUserM),
    );
  }

  factory AlertLogData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AlertLogData(
      id: serializer.fromJson<int>(json['id']),
      targetId: serializer.fromJson<int>(json['targetId']),
      sessionId: serializer.fromJson<String>(json['sessionId']),
      timestampUtc: serializer.fromJson<int>(json['timestampUtc']),
      tier: serializer.fromJson<String>(json['tier']),
      threatScore: serializer.fromJson<double>(json['threatScore']),
      lat: serializer.fromJson<double?>(json['lat']),
      lon: serializer.fromJson<double?>(json['lon']),
      lrfDistanceM: serializer.fromJson<double?>(json['lrfDistanceM']),
      panAngle: serializer.fromJson<double>(json['panAngle']),
      tiltAngle: serializer.fromJson<double>(json['tiltAngle']),
      distanceToUserM: serializer.fromJson<double?>(json['distanceToUserM']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'targetId': serializer.toJson<int>(targetId),
      'sessionId': serializer.toJson<String>(sessionId),
      'timestampUtc': serializer.toJson<int>(timestampUtc),
      'tier': serializer.toJson<String>(tier),
      'threatScore': serializer.toJson<double>(threatScore),
      'lat': serializer.toJson<double?>(lat),
      'lon': serializer.toJson<double?>(lon),
      'lrfDistanceM': serializer.toJson<double?>(lrfDistanceM),
      'panAngle': serializer.toJson<double>(panAngle),
      'tiltAngle': serializer.toJson<double>(tiltAngle),
      'distanceToUserM': serializer.toJson<double?>(distanceToUserM),
    };
  }

  AlertLogData copyWith({
    int? id,
    int? targetId,
    String? sessionId,
    int? timestampUtc,
    String? tier,
    double? threatScore,
    Value<double?> lat = const Value.absent(),
    Value<double?> lon = const Value.absent(),
    Value<double?> lrfDistanceM = const Value.absent(),
    double? panAngle,
    double? tiltAngle,
    Value<double?> distanceToUserM = const Value.absent(),
  }) => AlertLogData(
    id: id ?? this.id,
    targetId: targetId ?? this.targetId,
    sessionId: sessionId ?? this.sessionId,
    timestampUtc: timestampUtc ?? this.timestampUtc,
    tier: tier ?? this.tier,
    threatScore: threatScore ?? this.threatScore,
    lat: lat.present ? lat.value : this.lat,
    lon: lon.present ? lon.value : this.lon,
    lrfDistanceM: lrfDistanceM.present ? lrfDistanceM.value : this.lrfDistanceM,
    panAngle: panAngle ?? this.panAngle,
    tiltAngle: tiltAngle ?? this.tiltAngle,
    distanceToUserM: distanceToUserM.present
        ? distanceToUserM.value
        : this.distanceToUserM,
  );
  AlertLogData copyWithCompanion(AlertLogCompanion data) {
    return AlertLogData(
      id: data.id.present ? data.id.value : this.id,
      targetId: data.targetId.present ? data.targetId.value : this.targetId,
      sessionId: data.sessionId.present ? data.sessionId.value : this.sessionId,
      timestampUtc: data.timestampUtc.present
          ? data.timestampUtc.value
          : this.timestampUtc,
      tier: data.tier.present ? data.tier.value : this.tier,
      threatScore: data.threatScore.present
          ? data.threatScore.value
          : this.threatScore,
      lat: data.lat.present ? data.lat.value : this.lat,
      lon: data.lon.present ? data.lon.value : this.lon,
      lrfDistanceM: data.lrfDistanceM.present
          ? data.lrfDistanceM.value
          : this.lrfDistanceM,
      panAngle: data.panAngle.present ? data.panAngle.value : this.panAngle,
      tiltAngle: data.tiltAngle.present ? data.tiltAngle.value : this.tiltAngle,
      distanceToUserM: data.distanceToUserM.present
          ? data.distanceToUserM.value
          : this.distanceToUserM,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AlertLogData(')
          ..write('id: $id, ')
          ..write('targetId: $targetId, ')
          ..write('sessionId: $sessionId, ')
          ..write('timestampUtc: $timestampUtc, ')
          ..write('tier: $tier, ')
          ..write('threatScore: $threatScore, ')
          ..write('lat: $lat, ')
          ..write('lon: $lon, ')
          ..write('lrfDistanceM: $lrfDistanceM, ')
          ..write('panAngle: $panAngle, ')
          ..write('tiltAngle: $tiltAngle, ')
          ..write('distanceToUserM: $distanceToUserM')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    targetId,
    sessionId,
    timestampUtc,
    tier,
    threatScore,
    lat,
    lon,
    lrfDistanceM,
    panAngle,
    tiltAngle,
    distanceToUserM,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AlertLogData &&
          other.id == this.id &&
          other.targetId == this.targetId &&
          other.sessionId == this.sessionId &&
          other.timestampUtc == this.timestampUtc &&
          other.tier == this.tier &&
          other.threatScore == this.threatScore &&
          other.lat == this.lat &&
          other.lon == this.lon &&
          other.lrfDistanceM == this.lrfDistanceM &&
          other.panAngle == this.panAngle &&
          other.tiltAngle == this.tiltAngle &&
          other.distanceToUserM == this.distanceToUserM);
}

class AlertLogCompanion extends UpdateCompanion<AlertLogData> {
  final Value<int> id;
  final Value<int> targetId;
  final Value<String> sessionId;
  final Value<int> timestampUtc;
  final Value<String> tier;
  final Value<double> threatScore;
  final Value<double?> lat;
  final Value<double?> lon;
  final Value<double?> lrfDistanceM;
  final Value<double> panAngle;
  final Value<double> tiltAngle;
  final Value<double?> distanceToUserM;
  const AlertLogCompanion({
    this.id = const Value.absent(),
    this.targetId = const Value.absent(),
    this.sessionId = const Value.absent(),
    this.timestampUtc = const Value.absent(),
    this.tier = const Value.absent(),
    this.threatScore = const Value.absent(),
    this.lat = const Value.absent(),
    this.lon = const Value.absent(),
    this.lrfDistanceM = const Value.absent(),
    this.panAngle = const Value.absent(),
    this.tiltAngle = const Value.absent(),
    this.distanceToUserM = const Value.absent(),
  });
  AlertLogCompanion.insert({
    this.id = const Value.absent(),
    required int targetId,
    required String sessionId,
    required int timestampUtc,
    required String tier,
    required double threatScore,
    this.lat = const Value.absent(),
    this.lon = const Value.absent(),
    this.lrfDistanceM = const Value.absent(),
    required double panAngle,
    required double tiltAngle,
    this.distanceToUserM = const Value.absent(),
  }) : targetId = Value(targetId),
       sessionId = Value(sessionId),
       timestampUtc = Value(timestampUtc),
       tier = Value(tier),
       threatScore = Value(threatScore),
       panAngle = Value(panAngle),
       tiltAngle = Value(tiltAngle);
  static Insertable<AlertLogData> custom({
    Expression<int>? id,
    Expression<int>? targetId,
    Expression<String>? sessionId,
    Expression<int>? timestampUtc,
    Expression<String>? tier,
    Expression<double>? threatScore,
    Expression<double>? lat,
    Expression<double>? lon,
    Expression<double>? lrfDistanceM,
    Expression<double>? panAngle,
    Expression<double>? tiltAngle,
    Expression<double>? distanceToUserM,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (targetId != null) 'target_id': targetId,
      if (sessionId != null) 'session_id': sessionId,
      if (timestampUtc != null) 'timestamp_utc': timestampUtc,
      if (tier != null) 'tier': tier,
      if (threatScore != null) 'threat_score': threatScore,
      if (lat != null) 'lat': lat,
      if (lon != null) 'lon': lon,
      if (lrfDistanceM != null) 'lrf_distance_m': lrfDistanceM,
      if (panAngle != null) 'pan_angle': panAngle,
      if (tiltAngle != null) 'tilt_angle': tiltAngle,
      if (distanceToUserM != null) 'distance_to_user_m': distanceToUserM,
    });
  }

  AlertLogCompanion copyWith({
    Value<int>? id,
    Value<int>? targetId,
    Value<String>? sessionId,
    Value<int>? timestampUtc,
    Value<String>? tier,
    Value<double>? threatScore,
    Value<double?>? lat,
    Value<double?>? lon,
    Value<double?>? lrfDistanceM,
    Value<double>? panAngle,
    Value<double>? tiltAngle,
    Value<double?>? distanceToUserM,
  }) {
    return AlertLogCompanion(
      id: id ?? this.id,
      targetId: targetId ?? this.targetId,
      sessionId: sessionId ?? this.sessionId,
      timestampUtc: timestampUtc ?? this.timestampUtc,
      tier: tier ?? this.tier,
      threatScore: threatScore ?? this.threatScore,
      lat: lat ?? this.lat,
      lon: lon ?? this.lon,
      lrfDistanceM: lrfDistanceM ?? this.lrfDistanceM,
      panAngle: panAngle ?? this.panAngle,
      tiltAngle: tiltAngle ?? this.tiltAngle,
      distanceToUserM: distanceToUserM ?? this.distanceToUserM,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (targetId.present) {
      map['target_id'] = Variable<int>(targetId.value);
    }
    if (sessionId.present) {
      map['session_id'] = Variable<String>(sessionId.value);
    }
    if (timestampUtc.present) {
      map['timestamp_utc'] = Variable<int>(timestampUtc.value);
    }
    if (tier.present) {
      map['tier'] = Variable<String>(tier.value);
    }
    if (threatScore.present) {
      map['threat_score'] = Variable<double>(threatScore.value);
    }
    if (lat.present) {
      map['lat'] = Variable<double>(lat.value);
    }
    if (lon.present) {
      map['lon'] = Variable<double>(lon.value);
    }
    if (lrfDistanceM.present) {
      map['lrf_distance_m'] = Variable<double>(lrfDistanceM.value);
    }
    if (panAngle.present) {
      map['pan_angle'] = Variable<double>(panAngle.value);
    }
    if (tiltAngle.present) {
      map['tilt_angle'] = Variable<double>(tiltAngle.value);
    }
    if (distanceToUserM.present) {
      map['distance_to_user_m'] = Variable<double>(distanceToUserM.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AlertLogCompanion(')
          ..write('id: $id, ')
          ..write('targetId: $targetId, ')
          ..write('sessionId: $sessionId, ')
          ..write('timestampUtc: $timestampUtc, ')
          ..write('tier: $tier, ')
          ..write('threatScore: $threatScore, ')
          ..write('lat: $lat, ')
          ..write('lon: $lon, ')
          ..write('lrfDistanceM: $lrfDistanceM, ')
          ..write('panAngle: $panAngle, ')
          ..write('tiltAngle: $tiltAngle, ')
          ..write('distanceToUserM: $distanceToUserM')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $AlertLogTable alertLog = $AlertLogTable(this);
  late final AlertLogDao alertLogDao = AlertLogDao(this as AppDatabase);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [alertLog];
}

typedef $$AlertLogTableCreateCompanionBuilder =
    AlertLogCompanion Function({
      Value<int> id,
      required int targetId,
      required String sessionId,
      required int timestampUtc,
      required String tier,
      required double threatScore,
      Value<double?> lat,
      Value<double?> lon,
      Value<double?> lrfDistanceM,
      required double panAngle,
      required double tiltAngle,
      Value<double?> distanceToUserM,
    });
typedef $$AlertLogTableUpdateCompanionBuilder =
    AlertLogCompanion Function({
      Value<int> id,
      Value<int> targetId,
      Value<String> sessionId,
      Value<int> timestampUtc,
      Value<String> tier,
      Value<double> threatScore,
      Value<double?> lat,
      Value<double?> lon,
      Value<double?> lrfDistanceM,
      Value<double> panAngle,
      Value<double> tiltAngle,
      Value<double?> distanceToUserM,
    });

class $$AlertLogTableFilterComposer
    extends Composer<_$AppDatabase, $AlertLogTable> {
  $$AlertLogTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get targetId => $composableBuilder(
    column: $table.targetId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sessionId => $composableBuilder(
    column: $table.sessionId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get timestampUtc => $composableBuilder(
    column: $table.timestampUtc,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get tier => $composableBuilder(
    column: $table.tier,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get threatScore => $composableBuilder(
    column: $table.threatScore,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get lat => $composableBuilder(
    column: $table.lat,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get lon => $composableBuilder(
    column: $table.lon,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get lrfDistanceM => $composableBuilder(
    column: $table.lrfDistanceM,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get panAngle => $composableBuilder(
    column: $table.panAngle,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get tiltAngle => $composableBuilder(
    column: $table.tiltAngle,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get distanceToUserM => $composableBuilder(
    column: $table.distanceToUserM,
    builder: (column) => ColumnFilters(column),
  );
}

class $$AlertLogTableOrderingComposer
    extends Composer<_$AppDatabase, $AlertLogTable> {
  $$AlertLogTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get targetId => $composableBuilder(
    column: $table.targetId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sessionId => $composableBuilder(
    column: $table.sessionId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get timestampUtc => $composableBuilder(
    column: $table.timestampUtc,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get tier => $composableBuilder(
    column: $table.tier,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get threatScore => $composableBuilder(
    column: $table.threatScore,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get lat => $composableBuilder(
    column: $table.lat,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get lon => $composableBuilder(
    column: $table.lon,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get lrfDistanceM => $composableBuilder(
    column: $table.lrfDistanceM,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get panAngle => $composableBuilder(
    column: $table.panAngle,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get tiltAngle => $composableBuilder(
    column: $table.tiltAngle,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get distanceToUserM => $composableBuilder(
    column: $table.distanceToUserM,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$AlertLogTableAnnotationComposer
    extends Composer<_$AppDatabase, $AlertLogTable> {
  $$AlertLogTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get targetId =>
      $composableBuilder(column: $table.targetId, builder: (column) => column);

  GeneratedColumn<String> get sessionId =>
      $composableBuilder(column: $table.sessionId, builder: (column) => column);

  GeneratedColumn<int> get timestampUtc => $composableBuilder(
    column: $table.timestampUtc,
    builder: (column) => column,
  );

  GeneratedColumn<String> get tier =>
      $composableBuilder(column: $table.tier, builder: (column) => column);

  GeneratedColumn<double> get threatScore => $composableBuilder(
    column: $table.threatScore,
    builder: (column) => column,
  );

  GeneratedColumn<double> get lat =>
      $composableBuilder(column: $table.lat, builder: (column) => column);

  GeneratedColumn<double> get lon =>
      $composableBuilder(column: $table.lon, builder: (column) => column);

  GeneratedColumn<double> get lrfDistanceM => $composableBuilder(
    column: $table.lrfDistanceM,
    builder: (column) => column,
  );

  GeneratedColumn<double> get panAngle =>
      $composableBuilder(column: $table.panAngle, builder: (column) => column);

  GeneratedColumn<double> get tiltAngle =>
      $composableBuilder(column: $table.tiltAngle, builder: (column) => column);

  GeneratedColumn<double> get distanceToUserM => $composableBuilder(
    column: $table.distanceToUserM,
    builder: (column) => column,
  );
}

class $$AlertLogTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $AlertLogTable,
          AlertLogData,
          $$AlertLogTableFilterComposer,
          $$AlertLogTableOrderingComposer,
          $$AlertLogTableAnnotationComposer,
          $$AlertLogTableCreateCompanionBuilder,
          $$AlertLogTableUpdateCompanionBuilder,
          (
            AlertLogData,
            BaseReferences<_$AppDatabase, $AlertLogTable, AlertLogData>,
          ),
          AlertLogData,
          PrefetchHooks Function()
        > {
  $$AlertLogTableTableManager(_$AppDatabase db, $AlertLogTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$AlertLogTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$AlertLogTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$AlertLogTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> targetId = const Value.absent(),
                Value<String> sessionId = const Value.absent(),
                Value<int> timestampUtc = const Value.absent(),
                Value<String> tier = const Value.absent(),
                Value<double> threatScore = const Value.absent(),
                Value<double?> lat = const Value.absent(),
                Value<double?> lon = const Value.absent(),
                Value<double?> lrfDistanceM = const Value.absent(),
                Value<double> panAngle = const Value.absent(),
                Value<double> tiltAngle = const Value.absent(),
                Value<double?> distanceToUserM = const Value.absent(),
              }) => AlertLogCompanion(
                id: id,
                targetId: targetId,
                sessionId: sessionId,
                timestampUtc: timestampUtc,
                tier: tier,
                threatScore: threatScore,
                lat: lat,
                lon: lon,
                lrfDistanceM: lrfDistanceM,
                panAngle: panAngle,
                tiltAngle: tiltAngle,
                distanceToUserM: distanceToUserM,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int targetId,
                required String sessionId,
                required int timestampUtc,
                required String tier,
                required double threatScore,
                Value<double?> lat = const Value.absent(),
                Value<double?> lon = const Value.absent(),
                Value<double?> lrfDistanceM = const Value.absent(),
                required double panAngle,
                required double tiltAngle,
                Value<double?> distanceToUserM = const Value.absent(),
              }) => AlertLogCompanion.insert(
                id: id,
                targetId: targetId,
                sessionId: sessionId,
                timestampUtc: timestampUtc,
                tier: tier,
                threatScore: threatScore,
                lat: lat,
                lon: lon,
                lrfDistanceM: lrfDistanceM,
                panAngle: panAngle,
                tiltAngle: tiltAngle,
                distanceToUserM: distanceToUserM,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$AlertLogTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $AlertLogTable,
      AlertLogData,
      $$AlertLogTableFilterComposer,
      $$AlertLogTableOrderingComposer,
      $$AlertLogTableAnnotationComposer,
      $$AlertLogTableCreateCompanionBuilder,
      $$AlertLogTableUpdateCompanionBuilder,
      (
        AlertLogData,
        BaseReferences<_$AppDatabase, $AlertLogTable, AlertLogData>,
      ),
      AlertLogData,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$AlertLogTableTableManager get alertLog =>
      $$AlertLogTableTableManager(_db, _db.alertLog);
}
