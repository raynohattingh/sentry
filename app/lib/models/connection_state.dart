/// MQTT connection state enum.
enum SentryConnectionState {
  online,
  reconnecting,
  offline;

  /// True when telemetry is actively flowing.
  bool get isLive => this == SentryConnectionState.online;
}
