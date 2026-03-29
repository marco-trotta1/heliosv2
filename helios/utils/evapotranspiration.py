from __future__ import annotations

import math


def estimate_reference_et_mm(
    temperature_c: float,
    humidity_pct: float,
    wind_mps: float,
    solar_radiation_mj_m2: float,
    elevation_m: float = 800.0,
) -> float:
    """Simplified FAO-56 Penman-Monteith reference ET₀ (mm/day).

    Assumes grass reference crop, daily timestep, and approximates
    net radiation from solar radiation. Soil heat flux is assumed
    negligible for daily calculations per FAO-56 guidelines.

    Parameters use standard meteorological units matching NOAA/AgriMet
    station output.
    """
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

    et0 = numerator / denominator if denominator > 0 else 0.0
    return round(max(0.0, et0), 3)
