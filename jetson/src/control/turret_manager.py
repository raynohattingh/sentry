from __future__ import annotations

import datetime

import config
from hardware.arduino_link import ArduinoLink
from sentry_types import (
    HousingProfile,
    LimitValidationState,
    ProtectionMode,
    SafetyStatus,
    SoftMotionBounds,
)


class TurretManager:
    def __init__(self, hardware: ArduinoLink | None = None):
        self.hardware = hardware or ArduinoLink()
        self.refresh_profile_from_config()

    def refresh_profile_from_config(self) -> None:
        self._housing_profile = HousingProfile.from_raw(config.HOUSING_PROFILE)
        self._soft_bounds = SoftMotionBounds(
            pan_min_steps=config.TEST_BENCH_PAN_MIN_STEPS,
            pan_max_steps=config.TEST_BENCH_PAN_MAX_STEPS,
            tilt_min_steps=config.TEST_BENCH_TILT_MIN_STEPS,
            tilt_max_steps=config.TEST_BENCH_TILT_MAX_STEPS,
        )

    @property
    def housing_profile(self) -> HousingProfile:
        return self._housing_profile

    @property
    def soft_bounds(self) -> SoftMotionBounds:
        return self._soft_bounds

    @property
    def validation_state(self) -> LimitValidationState:
        if self._housing_profile == HousingProfile.TEST_BENCH:
            if self._soft_bounds.is_valid:
                return LimitValidationState.BYPASSED
            return LimitValidationState.BLOCKED_INVALID_BOUNDS
        if self.hardware.all_required_switches_validated():
            return LimitValidationState.READY_HARDWARE_VALIDATED
        return LimitValidationState.PENDING_SWITCH_VALIDATION

    @property
    def protection_mode(self) -> ProtectionMode:
        if self.validation_state == LimitValidationState.BYPASSED:
            return ProtectionMode.SOFT_LIMIT_BYPASS
        if self.validation_state == LimitValidationState.PENDING_SWITCH_VALIDATION:
            return ProtectionMode.HARDWARE_VALIDATION_PENDING
        return ProtectionMode.HARDWARE_LIMITS_ACTIVE

    @property
    def motion_allowed(self) -> bool:
        return self.validation_state in (
            LimitValidationState.BYPASSED,
            LimitValidationState.READY_HARDWARE_VALIDATED,
        )

    @property
    def motion_block_reason(self) -> str | None:
        if self.validation_state == LimitValidationState.BLOCKED_INVALID_BOUNDS:
            return "INVALID_TEST_BENCH_BOUNDS"
        if self.validation_state == LimitValidationState.PENDING_SWITCH_VALIDATION:
            return "LIMIT_SWITCH_VALIDATION_REQUIRED"
        return None

    def get_safety_status(self) -> SafetyStatus:
        validated_switches = []
        if self._housing_profile == HousingProfile.MVP:
            validated_switches = list(self.hardware.validated_switches)
        return SafetyStatus(
            sentry_id=config.SENTRY_ID,
            housing_profile=self._housing_profile,
            protection_mode=self.protection_mode,
            motion_allowed=self.motion_allowed,
            motion_block_reason=self.motion_block_reason,
            validated_switches=validated_switches,
            timestamp_utc=datetime.datetime.now(datetime.UTC)
            .isoformat()
            .replace("+00:00", "Z"),
        )

    def apply_motion_bounds(
        self,
        pan_velocity: float,
        tilt_velocity: float,
    ) -> tuple[float, float]:
        if not self.motion_allowed:
            return 0.0, 0.0

        if self._housing_profile != HousingProfile.TEST_BENCH:
            # Software backstop: hard-clamp velocities for non-test-bench profiles.
            position = self.hardware.current_position
            pan_velocity = self._bound_axis(
                position.pan_steps,
                pan_velocity,
                -config.PAN_LIMIT_HARD_STEPS,
                config.PAN_LIMIT_HARD_STEPS,
            )
            tilt_velocity = self._bound_axis(
                position.tilt_steps,
                tilt_velocity,
                -config.TILT_LIMIT_HARD_STEPS,
                config.TILT_LIMIT_HARD_STEPS,
            )
            return pan_velocity, tilt_velocity

        position = self.hardware.current_position
        bounds = self._soft_bounds
        if bounds.pan_min_steps is None:
            raise ValueError("pan_min_steps must not be None for TEST_BENCH profile")
        if bounds.pan_max_steps is None:
            raise ValueError("pan_max_steps must not be None for TEST_BENCH profile")
        if bounds.tilt_min_steps is None:
            raise ValueError("tilt_min_steps must not be None for TEST_BENCH profile")
        if bounds.tilt_max_steps is None:
            raise ValueError("tilt_max_steps must not be None for TEST_BENCH profile")

        return (
            self._bound_axis(
                position.pan_steps,
                pan_velocity,
                bounds.pan_min_steps,
                bounds.pan_max_steps,
            ),
            self._bound_axis(
                position.tilt_steps,
                tilt_velocity,
                bounds.tilt_min_steps,
                bounds.tilt_max_steps,
            ),
        )

    def _bound_axis(
        self,
        current_steps: int,
        requested_velocity: float,
        lower_bound: int,
        upper_bound: int,
    ) -> float:
        if current_steps <= lower_bound and requested_velocity < 0.0:
            return 0.0
        if current_steps >= upper_bound and requested_velocity > 0.0:
            return 0.0
        return requested_velocity

    def set_velocity(self, pan_velocity: float, tilt_velocity: float) -> None:
        bounded_pan, bounded_tilt = self.apply_motion_bounds(pan_velocity, tilt_velocity)
        self.hardware.send_velocity(bounded_pan, bounded_tilt)

    def stop(self):
        self.set_velocity(0.0, 0.0)
