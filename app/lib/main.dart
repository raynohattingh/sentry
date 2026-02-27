import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router.dart';
import 'core/theme.dart';
import 'database/app_database.dart';
import 'features/setup/setup_provider.dart';
import 'models/notification_preferences.dart';
import 'services/mqtt_service.dart';
import 'services/secure_storage_service.dart';
import 'services/notification_service.dart';

/// Database singleton provider.
final appDatabaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _initBackgroundService();
  runApp(const ProviderScope(child: SentryApp()));
}

Future<void> _initBackgroundService() async {
  final service = FlutterBackgroundService();
  await service.configure(
    iosConfiguration: IosConfiguration(
      autoStart: true,
      onForeground: onStart,
      onBackground: onIosBackground,
    ),
    androidConfiguration: AndroidConfiguration(
      autoStart: true,
      onStart: onStart,
      isForegroundMode: true,
      notificationChannelId: 'sentry_threat_high',
      initialNotificationTitle: '[SENTRY] Background Service',
      initialNotificationContent: 'Monitoring for threats',
      foregroundServiceNotificationId: 888,
    ),
  );
}

@pragma('vm:entry-point')
Future<bool> onIosBackground(ServiceInstance service) async {
  WidgetsFlutterBinding.ensureInitialized();
  return true;
}

@pragma('vm:entry-point')
void onStart(ServiceInstance service) {
  // Background isolate — create its own ProviderContainer with service overrides.
  // Wire MQTT → notification pipeline (T046).
  final container = ProviderContainer(
    overrides: [
      // Overrides injected here at runtime from saved config
    ],
  );

  final notificationService = NotificationServiceImpl();
  notificationService.initialize();

  // Load config from SharedPreferences and connect MQTT in background
  _startBackgroundMqtt(container, notificationService);
}

Future<void> _startBackgroundMqtt(
  ProviderContainer container,
  NotificationService notificationService,
) async {
  try {
    final setupNotifier = SetupNotifier(SecureStorageServiceImpl());
    await setupNotifier.loadSavedConfig();
    final config = setupNotifier.currentConfig;
    if (!config.isConfigured) return;

    final mqtt = MqttServiceImpl();
    await mqtt.connect(config);

    final prefs = const NotificationPreferences();

    mqtt.telemetryStream.listen((record) async {
      await notificationService.showThreatAlert(record, prefs);
    });
  } catch (_) {
    // Background service — swallow errors gracefully
  }
}

class SentryApp extends ConsumerWidget {
  const SentryApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Farm Sentry',
      theme: SentryTheme.dark(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
