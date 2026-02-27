/// Core constants for the Farm Sentry mobile application.
/// All named constants are defined here — no magic numbers elsewhere.
library;

// MQTT
const int kDefaultMqttPort = 8883;

// Video stream
const int kDefaultVideoPort = 5000;

// Heartbeat / connection timeout
const int kHeartbeatTimeoutSec = 10;

// Marker lifecycle
const int kMarkerFadeRemovalSec = 30;

// Joystick / manual override
const int kJoystickPublishIntervalMs = 100;
const double kMaxJoystickVelocity = 200.0;

// Threat tier thresholds
const double kThreatTierMedThreshold = 40.0;
const double kThreatTierHighThreshold = 80.0;

// Alert log
const int kDefaultRetentionDays = 7;
