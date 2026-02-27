import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provider for the currently selected threat marker target ID.
final selectedMarkerProvider =
    StateNotifierProvider<SelectedMarkerNotifier, int?>((ref) {
  return SelectedMarkerNotifier();
});

/// Manages which threat marker (if any) is currently selected.
class SelectedMarkerNotifier extends StateNotifier<int?> {
  SelectedMarkerNotifier() : super(null);

  /// Selects a marker by [targetId].
  void select(int targetId) => state = targetId;

  /// Clears the selection.
  void clear() => state = null;
}
