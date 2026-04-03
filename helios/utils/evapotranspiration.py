"""
Reference evapotranspiration estimation.

Method: simplified Penman-Monteith (FAO-56).
Parameters calibrated for arid high-desert conditions typical of the Snake River Plain, Idaho.
Not a certified agronomic model. For decision support use only.
"""

from __future__ import annotations

import math


def estimate_reference_et_in(
    temperature_f: float,
    humidity_pct: float,
    wind_mph: float,
    solar_radiation_mj_m2: float,
    elevation_m: float = 800.0,
) -> float:
    """Simplified FAO-56 Penman-Monteith reference ET₀ (in/day).

    Assumes grass reference crop, daily timestep, and approximates
    net radiation from solar radiation. Soil heat flux is assumed
    negligible for daily calculations per FAO-56 guidelines.

    Inputs use imperial units; internal calculation uses metric per
    FAO-56 standard, with output converted to inches/day.
    """
    # Convert imperial inputs to metric for FAO-56 formula
    temperature_c = (temperature_f - 32.0) * 5.0 / 9.0
    wind_mps = wind_mph / 2.23694

    # Psychrometric constant (kPa/°C)
    atmospheric_pressure = 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26
    gamma = 0.000665 * atmospheric_pressure

    # Saturation vapor pressure (kPa) — Tetens formula
    e_sat = 0.6108 * math.exp((17.27 * temperature_c) / (temperature_c + 237.3))

    # Actual vapor pressure from relative humidity
    e_act = e_sat * (humidity_pct / 100.0)

    # Vapor pressure deficit
    vpd = max(0.0, e_sat - e_act)

    # Slope of saturation vapor pressure curve (kPa/°C)
    delta = (4098.0 * e_sat) / ((temperature_c + 237.3) ** 2)

    # Net radiation approximation (MJ/m²/day)
    # Using albedo = 0.23 for grass reference, and approximate
    # net longwave from Rn ≈ 0.77 * Rs (simplified for prototype)
    rn = 0.77 * solar_radiation_mj_m2

    # Soil heat flux ≈ 0 for daily timestep (FAO-56 recommendation)
    g = 0.0

    # FAO-56 Penman-Monteith equation
    numerator = (0.408 * delta * (rn - g)) + (gamma * (900.0 / (temperature_c + 273.0)) * wind_mps * vpd)
    denominator = delta + gamma * (1.0 + 0.34 * wind_mps)

    et0_mm = numerator / denominator if denominator > 0 else 0.0
    et0_in = max(0.0, et0_mm) * 0.039370
    return round(et0_in, 4)
