import 'package:flutter/material.dart';

// Threat tier colours
const Color kColorLow = Color(0xFFFFD700); // yellow
const Color kColorMed = Color(0xFFFF8C00); // orange
const Color kColorHigh = Color(0xFFFF1E1E); // red
const Color kColorOffline = Color(0xFF555555); // grey

// Background / surface colours
const Color kColorBackground = Color(0xFF0A0A0A);
const Color kColorSurface = Color(0xFF141414);

/// Returns the dark [ThemeData] for the Farm Sentry app.
class SentryTheme {
  SentryTheme._();

  static ThemeData dark() {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: kColorBackground,
      colorScheme: const ColorScheme.dark(
        surface: kColorSurface,
        primary: kColorHigh,
        secondary: kColorMed,
      ),
      cardColor: kColorSurface,
      fontFamily: 'RobotoMono',
      textTheme: const TextTheme(
        bodyMedium: TextStyle(
          fontFamily: 'RobotoMono',
          color: Colors.white70,
        ),
        titleMedium: TextStyle(
          fontFamily: 'RobotoMono',
          color: Colors.white,
          fontWeight: FontWeight.bold,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: kColorBackground,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
    );
  }
}

const Color kColorAmber = Color(0xFFFFAA00); // amber — TRACK state
