"""Unit tests for PIDController — T011.

Tests:
- Proportional output scales with error
- Integral accumulates over time
- Anti-windup clamps at max_integral
- reset() zeroes all state
- Output clamped to ±max_out
"""

import time
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from control.pid import PIDController


def test_positive_error_positive_output():
    pid = PIDController(kp=1.0, ki=0.0, kd=0.0, max_out=9999.0)
    time.sleep(0.05)
    assert pid.update(100.0) > 0


def test_negative_error_negative_output():
    pid = PIDController(kp=1.0, ki=0.0, kd=0.0, max_out=9999.0)
    time.sleep(0.05)
    assert pid.update(-100.0) < 0


def test_zero_error_zero_output():
    pid = PIDController(kp=5.0, ki=0.0, kd=0.0, max_out=9999.0)
    time.sleep(0.05)
    assert pid.update(0.0) == pytest.approx(0.0, abs=1e-6)


def test_integral_accumulates():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, max_out=9999.0)
    time.sleep(0.05)
    out1 = abs(pid.update(10.0))
    time.sleep(0.05)
    out2 = abs(pid.update(10.0))
    assert out2 > out1


def test_antiwindup_clamp_positive():
    max_int = 100.0
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, max_out=9999.0, max_integral=max_int)
    for _ in range(200):
        time.sleep(0.005)
        pid.update(1000.0)
    assert pid._integral <= max_int + 1e-6


def test_antiwindup_clamp_negative():
    max_int = 100.0
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, max_out=9999.0, max_integral=max_int)
    for _ in range(200):
        time.sleep(0.005)
        pid.update(-1000.0)
    assert pid._integral >= -max_int - 1e-6


def test_reset_clears_integral():
    pid = PIDController(kp=0.0, ki=1.0, kd=0.0, max_out=9999.0)
    for _ in range(10):
        time.sleep(0.01)
        pid.update(50.0)
    pid.reset()
    assert pid._integral == pytest.approx(0.0, abs=1e-9)


def test_reset_clears_prev_error():
    pid = PIDController(kp=0.0, ki=0.0, kd=1.0, max_out=9999.0)
    time.sleep(0.05)
    pid.update(100.0)
    pid.reset()
    assert pid._prev_error == pytest.approx(0.0, abs=1e-9)


def test_output_clamped_positive():
    pid = PIDController(kp=1000.0, ki=0.0, kd=0.0, max_out=500.0)
    time.sleep(0.05)
    assert pid.update(999.0) == pytest.approx(500.0, abs=1e-6)


def test_output_clamped_negative():
    pid = PIDController(kp=1000.0, ki=0.0, kd=0.0, max_out=500.0)
    time.sleep(0.05)
    assert pid.update(-999.0) == pytest.approx(-500.0, abs=1e-6)
