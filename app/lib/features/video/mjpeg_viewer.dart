import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../core/theme.dart';

/// Streams and renders an MJPEG feed from the sentry camera.
class MjpegViewer extends StatefulWidget {
  const MjpegViewer({
    super.key,
    required this.host,
    required this.port,
    required this.username,
    required this.password,
    this.path = '/video',
    this.useTls = true,
  });

  final String host;
  final int port;
  final String username;
  final String password;
  final String path;
  final bool useTls;

  @override
  State<MjpegViewer> createState() => _MjpegViewerState();
}

class _MjpegViewerState extends State<MjpegViewer> {
  http.Client? _client;
  StreamSubscription<dynamic>? _streamSub;
  Uint8List? _currentFrame;
  String? _errorMessage;
  bool _loading = true;
  Timer? _stallTimer;

  @override
  void initState() {
    super.initState();
    _startStream();
  }

  void _startStream() {
    _loading = true;
    _errorMessage = null;
    _startStallTimer();

    final credentials =
        base64Encode(utf8.encode('${widget.username}:${widget.password}'));
    final uri = Uri(
      scheme: widget.useTls ? 'https' : 'http',
      host: widget.host,
      port: widget.port,
      path: widget.path,
    );

    _client = http.Client();
    final request = http.Request('GET', uri)
      ..headers['Authorization'] = 'Basic $credentials';

    _client!.send(request).then((response) {
      if (response.statusCode == 401) {
        _setError('[VIDEO] Authentication failed (401)');
        return;
      }
      if (response.statusCode != 200) {
        _setError('[VIDEO] Server error (${response.statusCode})');
        return;
      }

      _streamSub = response.stream
          .toBytes()
          .asStream()
          .listen(null); // Simplified — full MJPEG parsing below

      _parseMultipart(response);
    }).catchError((Object e) {
      if (e is SocketException) {
        _setError('[VIDEO] Connection failed — check local network');
      } else {
        _setError('[VIDEO] Stream error: $e');
      }
    });
  }

  void _parseMultipart(http.StreamedResponse response) {
    final boundary = _extractBoundary(response.headers['content-type'] ?? '');
    final buffer = <int>[];

    response.stream.listen(
      (chunk) {
        _resetStallTimer();
        buffer.addAll(chunk);
        // Extract JPEG frames from multipart stream
        _extractFrames(buffer, boundary);
      },
      onError: (Object e) {
        _setError('[VIDEO] Stream interrupted');
      },
      onDone: () {
        if (mounted && _currentFrame == null) {
          _setError('[VIDEO] Stream ended unexpectedly');
        }
      },
    );
  }

  void _extractFrames(List<int> buffer, String boundary) {
    // Look for JPEG SOI (0xFF 0xD8) and EOI (0xFF 0xD9) markers
    final soi = [0xFF, 0xD8];
    final eoi = [0xFF, 0xD9];

    int soiIdx = -1;
    for (int i = 0; i < buffer.length - 1; i++) {
      if (buffer[i] == soi[0] && buffer[i + 1] == soi[1]) {
        soiIdx = i;
        break;
      }
    }
    if (soiIdx < 0) return;

    for (int i = soiIdx; i < buffer.length - 1; i++) {
      if (buffer[i] == eoi[0] && buffer[i + 1] == eoi[1]) {
        final frame = Uint8List.fromList(buffer.sublist(soiIdx, i + 2));
        buffer.removeRange(0, i + 2);
        if (mounted) {
          setState(() {
            _currentFrame = frame;
            _loading = false;
          });
        }
        return;
      }
    }
  }

  String _extractBoundary(String contentType) {
    final match = RegExp(r'boundary=([^;]+)').firstMatch(contentType);
    return match?.group(1)?.trim() ?? '';
  }

  void _startStallTimer() {
    _stallTimer?.cancel();
    _stallTimer = Timer(const Duration(seconds: 5), () {
      if (_currentFrame == null && mounted) {
        _setError('[VIDEO] No frames received — check network');
      }
    });
  }

  void _resetStallTimer() {
    _stallTimer?.cancel();
    _stallTimer = Timer(const Duration(seconds: 5), () {
      if (mounted) {
        _setError('[VIDEO] Stream stalled');
      }
    });
  }

  void _setError(String message) {
    if (!mounted) return;
    setState(() {
      _errorMessage = message;
      _loading = false;
    });
  }

  @override
  void dispose() {
    _stallTimer?.cancel();
    _streamSub?.cancel();
    _client?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            _errorMessage!,
            style: const TextStyle(color: kColorHigh, fontFamily: 'RobotoMono'),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    if (_loading || _currentFrame == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Image.memory(
      _currentFrame!,
      gaplessPlayback: true,
      fit: BoxFit.contain,
    );
  }
}
