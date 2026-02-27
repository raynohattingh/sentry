import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Abstract secure storage service interface.
abstract class SecureStorageService {
  Future<void> saveMqttCredentials(String user, String pass);
  Future<(String, String)?> loadMqttCredentials();
  Future<void> saveVideoCredentials(String user, String pass);
  Future<(String, String)?> loadVideoCredentials();
}

/// Concrete implementation backed by flutter_secure_storage.
class SecureStorageServiceImpl implements SecureStorageService {
  SecureStorageServiceImpl()
      : _storage = const FlutterSecureStorage(
          aOptions: AndroidOptions(encryptedSharedPreferences: true),
        );

  final FlutterSecureStorage _storage;

  static const _kMqttUser = 'mqtt_username';
  static const _kMqttPass = 'mqtt_password';
  static const _kVideoUser = 'video_username';
  static const _kVideoPass = 'video_password';

  @override
  Future<void> saveMqttCredentials(String user, String pass) async {
    await _storage.write(key: _kMqttUser, value: user);
    await _storage.write(key: _kMqttPass, value: pass);
  }

  @override
  Future<(String, String)?> loadMqttCredentials() async {
    final user = await _storage.read(key: _kMqttUser);
    final pass = await _storage.read(key: _kMqttPass);
    if (user == null || pass == null) return null;
    return (user, pass);
  }

  @override
  Future<void> saveVideoCredentials(String user, String pass) async {
    await _storage.write(key: _kVideoUser, value: user);
    await _storage.write(key: _kVideoPass, value: pass);
  }

  @override
  Future<(String, String)?> loadVideoCredentials() async {
    final user = await _storage.read(key: _kVideoUser);
    final pass = await _storage.read(key: _kVideoPass);
    if (user == null || pass == null) return null;
    return (user, pass);
  }
}
