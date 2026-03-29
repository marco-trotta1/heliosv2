from __future__ import annotations

import pytest

from helios.utils.evapotranspiration import estimate_reference_et_mm


def test_hot_dry_sunny_conditions_are_in_expected_range() -> None:
    """Hot/dry/sunny/windy conditions should produce high ET₀ (7–14 mm/day)."""
    et0 = estimate_reference_et_mm(
        temperature_c=35.0,
        humidity_pct=25.0,
        wind_mps=4.0,
        solar_radiation_mj_m2=28.0,
    )
    assert 7.0 <= et0 <= 14.0, f"Expected 7–14 mm/day for hot/dry/sunny conditions, got {et0}"


def test_cool_humid_conditions_are_in_expected_range() -> None:
    """Cool/humid/low-wind conditions should produce low ET₀ (1–3 mm/day)."""
    et0 = estimate_reference_et_mm(
        temperature_c=15.0,
        humidity_pct=80.0,
        wind_mps=1.0,
        solar_radiation_mj_m2=12.0,
    )
    assert 1.0 <= et0 <= 3.0, f"Expected 1–3 mm/day for cool/humid conditions, got {et0}"


def test_et0_is_never_negative() -> None:
    """ET₀ must always be non-negative regardless of inputs."""
    for temp in [-10.0, 0.0, 5.0, 15.0, 40.0]:
        for humidity in [0.0, 50.0, 100.0]:
            et0 = estimate_reference_et_mm(
                temperature_c=temp,
                humidity_pct=humidity,
                wind_mps=2.0,
                solar_radiation_mj_m2=15.0,
            )
            assert et0 >= 0.0, f"ET₀ was negative ({et0}) for temp={temp}, humidity={humidity}"


def test_zero_solar_radiation_returns_near_zero_et0() -> None:
    """Zero solar radiation with low VPD should return near-zero ET₀."""
    et0 = estimate_reference_et_mm(
        temperature_c=20.0,
        humidity_pct=95.0,
        wind_mps=0.5,
        solar_radiation_mj_m2=0.0,
    )
    assert et0 < 1.0, f"Expected near-zero ET₀ with zero solar radiation, got {et0}"
