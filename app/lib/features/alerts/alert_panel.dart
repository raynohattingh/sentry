import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../database/app_database.dart';
import '../../features/map/selection_provider.dart';

import 'alerts_provider.dart';

/// Collapsible alert log panel.
class AlertPanel extends ConsumerStatefulWidget {
  const AlertPanel({
    super.key,
    required this.isOpen,
    required this.onToggle,
  });

  final bool isOpen;
  final VoidCallback onToggle;

  @override
  ConsumerState<AlertPanel> createState() => _AlertPanelState();
}

class _AlertPanelState extends ConsumerState<AlertPanel> {
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final entries = ref.watch(alertsProvider);
    final selected = ref.watch(selectedMarkerProvider);

    // Scroll to selected when selection changes
    ref.listen(selectedMarkerProvider, (_, newSelected) {
      if (newSelected != null && widget.isOpen) {
        _scrollToTarget(entries, newSelected);
      }
    });

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
      height: widget.isOpen ? 300 : 40,
      decoration: BoxDecoration(
        color: kColorSurface.withValues(alpha: 0.95),
        border: const Border(top: BorderSide(color: Colors.white12)),
      ),
      child: Column(
        children: [
          // Toggle header
          GestureDetector(
            onTap: widget.onToggle,
            child: Container(
              height: 40,
              color: Colors.transparent,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Icon(
                    widget.isOpen
                        ? Icons.keyboard_arrow_down
                        : Icons.keyboard_arrow_up,
                    color: Colors.white54,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '[ALERTS] ${entries.length} event${entries.length == 1 ? '' : 's'}',
                    style: const TextStyle(
                      color: Colors.white70,
                      fontFamily: 'RobotoMono',
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (widget.isOpen)
            Expanded(
              child: entries.isEmpty
                  ? const Center(
                      child: Text(
                        'No alerts recorded',
                        style: TextStyle(color: Colors.white38, fontSize: 12),
                      ),
                    )
                  : ListView.builder(
                      controller: _scrollController,
                      itemCount: entries.length,
                      itemBuilder: (context, index) {
                        final entry = entries[index];
                        final isHighlighted = selected == entry.targetId;
                        return AlertLogEntryTile(
                          entry: entry,
                          isHighlighted: isHighlighted,
                          onTap: () => ref
                              .read(selectedMarkerProvider.notifier)
                              .select(entry.targetId),
                        );
                      },
                    ),
            ),
        ],
      ),
    );
  }

  void _scrollToTarget(List<AlertLogData> entries, int targetId) {
    final index = entries.indexWhere((e) => e.targetId == targetId);
    if (index < 0) return;
    const itemHeight = 72.0;
    _scrollController.animateTo(
      index * itemHeight,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }
}

/// Single row in the alert log.
class AlertLogEntryTile extends StatelessWidget {
  const AlertLogEntryTile({
    super.key,
    required this.entry,
    required this.isHighlighted,
    required this.onTap,
  });

  final AlertLogData entry;
  final bool isHighlighted;
  final VoidCallback onTap;

  Color _tierColor() {
    switch (entry.tier.toUpperCase()) {
      case 'HIGH':
        return kColorHigh;
      case 'MED':
        return kColorMed;
      default:
        return kColorLow;
    }
  }

  String _distanceDisplay() {
    if (entry.distanceToUserM == null && entry.lat == null) {
      return 'Location Unknown'; // FR-025
    }
    if (entry.distanceToUserM != null) {
      final m = entry.distanceToUserM!;
      if (m >= 1000) return '${(m / 1000).toStringAsFixed(1)} km';
      return '${m.toStringAsFixed(0)} m';
    }
    return 'Location Unknown';
  }

  @override
  Widget build(BuildContext context) {
    final ts = DateTime.fromMillisecondsSinceEpoch(entry.timestampUtc);
    final tierColor = _tierColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        color: isHighlighted
            ? tierColor.withValues(alpha: 0.15)
            : Colors.transparent,
        child: Row(
          children: [
            // Tier badge
            Container(
              width: 4,
              height: 48,
              color: tierColor,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        entry.tier,
                        style: TextStyle(
                          color: tierColor,
                          fontFamily: 'RobotoMono',
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        entry.threatScore.toStringAsFixed(1),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        _distanceDisplay(),
                        style: const TextStyle(
                            color: Colors.white70, fontSize: 12),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Pan ${entry.panAngle.toStringAsFixed(1)}° | '
                    'Tilt ${entry.tiltAngle.toStringAsFixed(1)}°'
                    '${entry.lrfDistanceM != null ? ' | LRF ${entry.lrfDistanceM!.toStringAsFixed(0)} m' : ''}',
                    style: const TextStyle(
                        color: Colors.white38, fontSize: 10),
                  ),
                  Text(
                    '${ts.hour.toString().padLeft(2, '0')}:'
                    '${ts.minute.toString().padLeft(2, '0')}:'
                    '${ts.second.toString().padLeft(2, '0')} '
                    'sess:${entry.sessionId.substring(0, 8)}',
                    style: const TextStyle(
                        color: Colors.white24, fontSize: 9),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
