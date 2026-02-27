import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../features/setup/setup_provider.dart';
import 'mjpeg_viewer.dart';

/// Shows the live MJPEG video feed in a modal.
/// Stream is constructed only when explicitly tapped (never auto-starts).
Future<void> showVideoModal(BuildContext context, WidgetRef ref) {
  final config = ref.read(sentryConfigProvider);
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: kColorSurface,
    builder: (_) => SizedBox(
      height: MediaQuery.of(context).size.height * 0.6,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
            child: Row(
              children: [
                const Text('[VIDEO] Live Feed',
                    style: TextStyle(
                        color: Colors.white,
                        fontFamily: 'RobotoMono',
                        fontWeight: FontWeight.bold)),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white54),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),
          Expanded(
            child: MjpegViewer(
              host: config.videoHost.isNotEmpty
                  ? config.videoHost
                  : config.brokerHost,
              port: config.videoPort,
              username: config.videoUsername,
              password: config.videoPassword,
            ),
          ),
        ],
      ),
    ),
  );
}
