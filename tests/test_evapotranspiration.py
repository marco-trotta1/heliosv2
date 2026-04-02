from __future__ import annotations

import pytest

from helios.utils.evapotranspiration import estimate_reference_et_in


def test_hot_dry_sunny_conditions_are_in_expected_range() -> None:
    """Hot/dry/sunny/windy conditions should produce high ET₀ (0.28–0.55 in/day)."""
    et0 = estimate_reference_et_in(
        temperature_f=95.0,   # 35 °C
        humidity_pct=25.0,
        wind_mph=8.95,        # 4.0 m/s
        solar_radiation_mj_m2=28.0,
    )
    assert 0.28 <= et0 <= 0.55, f"Expected 0.28–0.55 in/day for hot/dry/sunny conditions, got {et0}"


def test_cool_humid_conditions_are_in_expected_range() -> None:
    """Cool/humid/low-wind conditions should produce low ET₀ (0.04–0.12 in/day)."""
    et0 = estimate_reference_et_in(
        temperature_f=59.0,   # 15 °C
        humidity_pct=80.0,
        wind_mph=2.24,        # 1.0 m/s
        solar_radiation_mj_m2=12.0,
    )
    assert 0.04 <= et0 <= 0.12, f"Expected 0.04–0.12 in/day for cool/humid conditions, got {et0}"


def test_et0_is_never_negative() -> None:
    """ET₀ must always be non-negative regardless of inputs."""
    temp_f_values = [14.0, 32.0, 41.0, 59.0, 104.0]  # -10, 0, 5, 15, 40 °C
    for temp_f in temp_f_values:
        for humidity in [0.0, 50.0, 100.0]:
            et0 = estimate_reference_et_in(
                temperature_f=temp_f,
                humidity_pct=humidity,
                wind_mph=4.47,        # 2.0 m/s
                solar_radiation_mj_m2=15.0,
            )
            assert et0 >= 0.0, f"ET₀ was negative ({et0}) for temp_f={temp_f}, humidity={humidity}"


def test_zero_solar_radiation_returns_near_zero_et0() -> None:
    """Zero solar radiation with low VPD should return near-zero ET₀."""
    et0 = estimate_reference_et_in(
        temperature_f=68.0,   # 20 °C
        humidity_pct=95.0,
        wind_mph=1.12,        # 0.5 m/s
        solar_radiation_mj_m2=0.0,
    )
    assert et0 < 0.04, f"Expected near-zero ET₀ with zero solar radiation, got {et0}"
