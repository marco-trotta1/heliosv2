from __future__ import annotations


def estimate_reference_et_mm(
    temperature_c: float,
    humidity_pct: float,
    wind_mps: float,
    solar_radiation_mj_m2: float,
) -> float:
    """Approximate reference evapotranspiration in mm/day.

    This is a compact FAO-56 inspired proxy for local prototyping only. It should
    not be used as a certified agronomic ET calculator.
    """

    humidity_factor = max(0.1, 1.0 - (humidity_pct / 100.0) * 0.65)
    temperature_factor = max(0.0, (temperature_c + 5.0) / 25.0)
    wind_factor = 1.0 + min(wind_mps, 12.0) * 0.08
    solar_factor = solar_radiation_mj_m2 * 0.11
    et_mm = solar_factor * humidity_factor * wind_factor * temperature_factor
    return round(max(0.0, et_mm), 3)
