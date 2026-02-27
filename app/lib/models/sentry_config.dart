/// Sentry connection configuration.
class SentryConfig {
  const SentryConfig({
    this.brokerHost = '',
    this.brokerPort = 8883,
    this.mqttUsername = '',
    this.mqttPassword = '',
    this.sentryId = '',
    this.videoHost = '',
    this.videoPort = 5000,
    this.videoUsername = '',
    this.videoPassword = '',
    this.sentryLat,
    this.sentryLon,
    this.northOffsetDegrees = 0.0,
    this.retentionDays = 7,
  });

  final String brokerHost;
  final int brokerPort;
  final String mqttUsername;
  final String mqttPassword;
  final String sentryId;
  final String videoHost;
  final int videoPort;
  final String videoUsername;
  final String videoPassword;
  final double? sentryLat;
  final double? sentryLon;
  final double northOffsetDegrees;
  final int retentionDays;

  /// Returns true only when all required connection fields are filled.
  bool get isConfigured =>
      brokerHost.isNotEmpty && mqttUsername.isNotEmpty && sentryId.isNotEmpty;

  SentryConfig copyWith({
    String? brokerHost,
    int? brokerPort,
    String? mqttUsername,
    String? mqttPassword,
    String? sentryId,
    String? videoHost,
    int? videoPort,
    String? videoUsername,
    String? videoPassword,
    double? sentryLat,
    double? sentryLon,
    double? northOffsetDegrees,
    int? retentionDays,
  }) {
    return SentryConfig(
      brokerHost: brokerHost ?? this.brokerHost,
      brokerPort: brokerPort ?? this.brokerPort,
      mqttUsername: mqttUsername ?? this.mqttUsername,
      mqttPassword: mqttPassword ?? this.mqttPassword,
      sentryId: sentryId ?? this.sentryId,
      videoHost: videoHost ?? this.videoHost,
      videoPort: videoPort ?? this.videoPort,
      videoUsername: videoUsername ?? this.videoUsername,
      videoPassword: videoPassword ?? this.videoPassword,
      sentryLat: sentryLat ?? this.sentryLat,
      sentryLon: sentryLon ?? this.sentryLon,
      northOffsetDegrees: northOffsetDegrees ?? this.northOffsetDegrees,
      retentionDays: retentionDays ?? this.retentionDays,
    );
  }

  Map<String, dynamic> toJson() => {
        'brokerHost': brokerHost,
        'brokerPort': brokerPort,
        'mqttUsername': mqttUsername,
        'sentryId': sentryId,
        'videoHost': videoHost,
        'videoPort': videoPort,
        'videoUsername': videoUsername,
        'sentryLat': sentryLat,
        'sentryLon': sentryLon,
        'northOffsetDegrees': northOffsetDegrees,
        'retentionDays': retentionDays,
        // NOTE: passwords are NOT serialised here — stored via SecureStorage
      };

  factory SentryConfig.fromJson(Map<String, dynamic> json) {
    return SentryConfig(
      brokerHost: json['brokerHost'] as String? ?? '',
      brokerPort: json['brokerPort'] as int? ?? 8883,
      mqttUsername: json['mqttUsername'] as String? ?? '',
      sentryId: json['sentryId'] as String? ?? '',
      videoHost: json['videoHost'] as String? ?? '',
      videoPort: json['videoPort'] as int? ?? 5000,
      videoUsername: json['videoUsername'] as String? ?? '',
      sentryLat: json['sentryLat'] as double?,
      sentryLon: json['sentryLon'] as double?,
      northOffsetDegrees: json['northOffsetDegrees'] as double? ?? 0.0,
      retentionDays: json['retentionDays'] as int? ?? 7,
    );
  }
}
