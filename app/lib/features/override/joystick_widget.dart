import 'package:flutter/material.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../models/manual_command.dart';

const double _kJoystickRadius = 80.0;
const double _kNubRadius = 24.0;

/// Virtual joystick for pan/tilt control.
class JoystickWidget extends StatefulWidget {
  const JoystickWidget({
    super.key,
    required this.sentryId,
    required this.onCommandChanged,
    this.disabled = false,
  });

  final String sentryId;
  final ValueChanged<ManualCommand> onCommandChanged;
  final bool disabled;

  @override
  State<JoystickWidget> createState() => _JoystickWidgetState();
}

class _JoystickWidgetState extends State<JoystickWidget> {
  Offset _nubOffset = Offset.zero;

  void _onPanUpdate(DragUpdateDetails details) {
    if (widget.disabled) return;
    final newOffset = _nubOffset + details.delta;
    // Clamp to joystick radius
    final dist = newOffset.distance;
    final clamped =
        dist > _kJoystickRadius ? newOffset / dist * _kJoystickRadius : newOffset;
    setState(() => _nubOffset = clamped);
    _emitCommand(clamped);
  }

  void _onPanEnd(DragEndDetails _) {
    setState(() => _nubOffset = Offset.zero);
    _emitCommand(Offset.zero);
  }

  void _emitCommand(Offset offset) {
    final panVelocity = (offset.dx / _kJoystickRadius * kMaxJoystickVelocity)
        .clamp(-kMaxJoystickVelocity, kMaxJoystickVelocity);
    // Flutter `dy` is positive going DOWN on screen, but the Jetson/Arduino
    // convention is tilt_velocity positive = UP (sentry_types.py
    // TurretCommand, arduino config.h TILT_DIR_PIN). Negate so dragging
    // the nub up aims the turret up.
    final tiltVelocity =
        (-offset.dy / _kJoystickRadius * kMaxJoystickVelocity)
            .clamp(-kMaxJoystickVelocity, kMaxJoystickVelocity);

    widget.onCommandChanged(ManualCommand(
      sentryId: widget.sentryId,
      panVelocity: panVelocity,
      tiltVelocity: tiltVelocity,
      timestampUtc: DateTime.now().toUtc(),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: widget.disabled ? 0.4 : 1.0,
      child: GestureDetector(
        onPanUpdate: _onPanUpdate,
        onPanEnd: _onPanEnd,
        child: SizedBox(
          width: _kJoystickRadius * 2 + 20,
          height: _kJoystickRadius * 2 + 20,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Outer ring
              Container(
                width: _kJoystickRadius * 2,
                height: _kJoystickRadius * 2,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white24, width: 2),
                  color: kColorSurface.withValues(alpha: 0.7),
                ),
              ),
              // Inner nub
              AnimatedPositioned(
                duration: const Duration(milliseconds: 50),
                left: _kJoystickRadius - _kNubRadius + _nubOffset.dx,
                top: _kJoystickRadius - _kNubRadius + _nubOffset.dy,
                child: Container(
                  width: _kNubRadius * 2,
                  height: _kNubRadius * 2,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: kColorHigh.withValues(alpha: 0.8),
                    boxShadow: [
                      BoxShadow(
                        color: kColorHigh.withValues(alpha: 0.4),
                        blurRadius: 8,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
