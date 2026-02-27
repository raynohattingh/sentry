/// Manual turret control command published to `sentry/command`.
class ManualCommand {
  const ManualCommand({
    required this.sentryId,
    required this.panVelocity,
    required this.tiltVelocity,
    required this.timestampUtc,
  });

  final String sentryId;
  final double panVelocity;
  final double tiltVelocity;
  final DateTime timestampUtc;

  /// Zero-velocity stop command.
  factory ManualCommand.zero(String sentryId) {
    return ManualCommand(
      sentryId: sentryId,
      panVelocity: 0.0,
      tiltVelocity: 0.0,
      timestampUtc: DateTime.now().toUtc(),
    );
  }

  Map<String, dynamic> toJson() => {
        'sentry_id': sentryId,
        'pan_velocity': panVelocity,
        'tilt_velocity': tiltVelocity,
        'timestamp_utc': timestampUtc.toIso8601String(),
      };
}
