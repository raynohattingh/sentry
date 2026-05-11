import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/map/map_screen.dart';
import '../features/setup/setup_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/calibration/calibration_screen.dart';
import '../features/override/override_screen.dart';
import '../features/setup/setup_provider.dart';
import '../models/sentry_config.dart';

/// Named route paths.
const String kRouteSetup = '/setup';
const String kRouteHome = '/';
const String kRouteSettings = '/settings';
const String kRouteCalibration = '/calibration';
const String kRouteOverride = '/override';

/// Adapter that turns a Riverpod [sentryConfigProvider] subscription into a
/// [Listenable] so [GoRouter.refreshListenable] re-evaluates redirects on
/// config changes (e.g. when SetupNotifier loads saved config async at start).
class _ConfigRefreshListenable extends ChangeNotifier {
  _ConfigRefreshListenable(Ref ref) {
    _sub = ref.listen<SentryConfig>(
      sentryConfigProvider,
      (_, __) => notifyListeners(),
    );
  }
  late final ProviderSubscription<SentryConfig> _sub;

  @override
  void dispose() {
    _sub.close();
    super.dispose();
  }
}

/// [GoRouter] provider.
final routerProvider = Provider<GoRouter>((ref) {
  final listenable = _ConfigRefreshListenable(ref);
  ref.onDispose(listenable.dispose);
  return GoRouter(
    initialLocation: kRouteHome,
    refreshListenable: listenable,
    redirect: (context, state) {
      final config = ref.read(sentryConfigProvider);
      final isConfigured = config.isConfigured;
      final goingToSetup = state.matchedLocation == kRouteSetup;

      if (!isConfigured && !goingToSetup) {
        return kRouteSetup;
      }
      if (isConfigured && goingToSetup) {
        return kRouteHome;
      }
      return null;
    },
    routes: [
      GoRoute(
        path: kRouteSetup,
        name: 'setup',
        builder: (context, state) => const SetupScreen(),
      ),
      GoRoute(
        path: kRouteHome,
        name: 'home',
        builder: (context, state) => const MapScreen(),
      ),
      GoRoute(
        path: kRouteSettings,
        name: 'settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: kRouteCalibration,
        name: 'calibration',
        builder: (context, state) => const CalibrationScreen(),
      ),
      GoRoute(
        path: kRouteOverride,
        name: 'override',
        builder: (context, state) => const OverrideScreen(),
      ),
    ],
  );
});
