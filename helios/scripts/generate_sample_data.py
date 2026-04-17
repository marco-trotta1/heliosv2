from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from helios.scripts.training_shared import (
    CROP_KC,
    CROP_TYPES,
    DRAINAGE_CLASSES,
    DRAINAGE_FACTOR,
    GROWTH_STAGES,
    IRRIGATION_EFFICIENCY,
    IRRIGATION_TYPES,
    ROOT_ZONE_DEPTH_IN,
    SOIL_TEXTURES,
    load_openet_monthly_et,
)
from helios.utils.evapotranspiration import estimate_reference_et_in


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic Helios training data.")
    parser.add_argument("--rows", type=int, default=2500)
    parser.add_argument("--output-path", default="data/sample_training_data.csv")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--openet-csv",
        default=None,
        help="Path to OpenET monthly ET CSV (columns: date, openet_et_mm). "
             "When provided, each generated row receives the real satellite ET "
             "for its sampled irrigation-season month.",
    )
    return parser.parse_args()


def _choose_category(rng: np.random.Generator, values: list[str]) -> str:
    return str(rng.choice(values))


def generate_sample_data(
    rows: int,
    output_path: str,
    seed: int,
    openet_csv: str | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records: list[dict[str, float | str | int]] = []
    openet_monthly_et: dict[int, float] = load_openet_monthly_et(openet_csv)

    texture_to_retention = {"sand": -0.04, "loam": 0.0, "clay": 0.05}

    for idx in range(rows):
        soil_texture = _choose_category(rng, SOIL_TEXTURES)
        drainage_class = _choose_category(rng, DRAINAGE_CLASSES)
        irrigation_type = _choose_category(rng, IRRIGATION_TYPES)
        growth_stage = _choose_category(rng, GROWTH_STAGES)
        crop_type = _choose_category(rng, CROP_TYPES)

        # Temperature in °F (27°C = 80.6°F, std dev 6°C × 1.8 = 10.8°F)
        temperature_f = float(rng.normal(80.6, 10.8))
        humidity_pct = float(np.clip(rng.normal(48.0, 18.0), 15.0, 95.0))
        # Wind in mph (3.2 m/s = 7.16 mph, std 1.4 m/s = 3.13 mph)
        wind_mph = float(np.clip(rng.normal(7.16, 3.13), 0.67, 20.13))
        # Precipitation in inches (scale from mm distribution)
        precipitation_in = float(np.clip(rng.gamma(1.2, 0.098) - 0.039, 0.0, 0.709))
        solar_radiation_mj_m2 = float(np.clip(rng.normal(22.0, 5.0), 8.0, 34.0))
        rolling_temp_mean = float(temperature_f + rng.normal(0, 1.8))
        rolling_humidity_mean = float(np.clip(humidity_pct + rng.normal(0, 4.0), 10.0, 100.0))
        rolling_precip_in = float(max(0.0, precipitation_in + rng.normal(0, 0.039)))
        rolling_solar_mean = float(np.clip(solar_radiation_mj_m2 + rng.normal(0, 1.5), 8.0, 35.0))
        # Pump capacity in in/hr (6.5 mm/hr = 0.256 in/hr, std 2.0 → 0.079)
        pump_capacity_in_per_hour = float(np.clip(rng.normal(0.256, 0.079), 0.059, 0.472))
        # Max irrigation volume in inches (18 mm = 0.709 in)
        max_irrigation_volume_in = float(np.clip(rng.normal(0.709, 0.197), 0.236, 1.181))
        # Field area in acres (28 ha = 69.2 ac, std 10 ha = 24.7 ac)
        field_area_acres = float(np.clip(rng.normal(69.2, 24.7), 9.9, 148.3))
        budget_dollars = float(np.clip(rng.normal(600.0, 180.0), 100.0, 1200.0))
        # Infiltration rate in in/hr (sand: 24→0.945, loam: 13→0.512, clay: 7→0.276)
        infiltration_rate_in_per_hour = float(
            np.clip(
                {"sand": 0.945, "loam": 0.512, "clay": 0.276}[soil_texture] + rng.normal(0, 0.071),
                0.118,
                1.181,
            )
        )
        slope_pct = float(np.clip(rng.normal(2.6, 1.4), 0.0, 9.0))
        current_soil_moisture = float(
            np.clip(0.24 + texture_to_retention[soil_texture] + rng.normal(0, 0.035), 0.08, 0.48)
        )
        soil_moisture_lag_1 = float(np.clip(current_soil_moisture + rng.normal(0, 0.015), 0.08, 0.5))
        soil_moisture_lag_2 = float(np.clip(soil_moisture_lag_1 + rng.normal(0, 0.015), 0.08, 0.5))
        soil_moisture_delta_1 = current_soil_moisture - soil_moisture_lag_1
        soil_moisture_delta_2 = soil_moisture_lag_1 - soil_moisture_lag_2
        # Cumulative irrigation in inches ([0,0,0,6,9,12,15] mm → inches)
        cumulative_irrigation_24h = float(np.clip(
            rng.choice([0, 0, 0, 0.236, 0.354, 0.472, 0.591]) + rng.normal(0, 0.031),
            0.0, 0.630,
        ))
        cumulative_irrigation_72h = float(np.clip(
            cumulative_irrigation_24h + rng.choice([0, 0.157, 0.315, 0.472]) + rng.normal(0, 0.047),
            0.0, 1.024,
        ))
        forecast_horizon_hours = int(rng.choice([24, 48, 72]))
        sensor_count = int(rng.integers(3, 8))
        water_rights_schedule_count = int(rng.integers(1, 4))
        energy_window_count = int(rng.integers(1, 3))

        # Irrigation season month (April–September). Used to attach real OpenET values.
        season_month = int(rng.choice([4, 5, 5, 6, 6, 7, 7, 7, 8, 8, 9]))

        reference_et_in = estimate_reference_et_in(
            temperature_f=rolling_temp_mean,
            humidity_pct=rolling_humidity_mean,
            wind_mph=wind_mph,
            solar_radiation_mj_m2=rolling_solar_mean,
        )

        # Real satellite ET for this month (in/day). Zero when no OpenET data provided.
        openet_monthly_et_in = openet_monthly_et.get(season_month, 0.0)

        # Soil water balance targets derived from FAO-56 ET₀ and crop coefficients.
        # This breaks the circular dependency: targets are physics-grounded, not
        # derived from the same heuristics the optimizer uses.
        kc = CROP_KC[growth_stage]
        root_depth = ROOT_ZONE_DEPTH_IN[soil_texture]
        eff = IRRIGATION_EFFICIENCY[irrigation_type]
        drainage = DRAINAGE_FACTOR[drainage_class]
        infiltration_efficiency = 0.90  # fraction of precipitation entering root zone

        def _step(moisture: float, precip: float, irrigation: float) -> float:
            et_depletion = (reference_et_in * kc * drainage) / root_depth
            precip_gain = precip * infiltration_efficiency / root_depth
            irrigation_gain = irrigation * eff / root_depth
            return float(np.clip(
                moisture - et_depletion + precip_gain + irrigation_gain + rng.normal(0, 0.012),
                0.05, 0.50,
            ))

        target_24h = _step(current_soil_moisture, precipitation_in, cumulative_irrigation_24h)
        target_48h = _step(target_24h, precipitation_in * 0.5, 0.0)
        target_72h = _step(target_48h, 0.0, cumulative_irrigation_72h - cumulative_irrigation_24h)

        records.append(
            {
                "field_id": f"field-{idx % 48:03d}",
                "forecast_horizon_hours": forecast_horizon_hours,
                "temperature_f": round(temperature_f, 3),
                "humidity_pct": round(humidity_pct, 3),
                "wind_mph": round(wind_mph, 3),
                "precipitation_in": round(precipitation_in, 4),
                "solar_radiation_mj_m2": round(solar_radiation_mj_m2, 3),
                "rolling_temp_mean": round(rolling_temp_mean, 3),
                "rolling_humidity_mean": round(rolling_humidity_mean, 3),
                "rolling_precip_in": round(rolling_precip_in, 4),
                "rolling_solar_mean": round(rolling_solar_mean, 3),
                "current_soil_moisture": round(current_soil_moisture, 4),
                "soil_moisture_lag_1": round(soil_moisture_lag_1, 4),
                "soil_moisture_lag_2": round(soil_moisture_lag_2, 4),
                "soil_moisture_delta_1": round(soil_moisture_delta_1, 4),
                "soil_moisture_delta_2": round(soil_moisture_delta_2, 4),
                "pump_capacity_in_per_hour": round(pump_capacity_in_per_hour, 4),
                "water_rights_schedule_count": water_rights_schedule_count,
                "energy_window_count": energy_window_count,
                "irrigation_type": irrigation_type,
                "soil_texture": soil_texture,
                "infiltration_rate_in_per_hour": round(infiltration_rate_in_per_hour, 4),
                "slope_pct": round(slope_pct, 3),
                "drainage_class": drainage_class,
                "crop_type": crop_type,
                "growth_stage": growth_stage,
                "max_irrigation_volume_in": round(max_irrigation_volume_in, 4),
                "field_area_acres": round(field_area_acres, 3),
                "budget_dollars": round(budget_dollars, 3),
                "cumulative_irrigation_24h": round(cumulative_irrigation_24h, 4),
                "cumulative_irrigation_72h": round(cumulative_irrigation_72h, 4),
                "sensor_count": sensor_count,
                "season_month": season_month,
                "openet_monthly_et_in": openet_monthly_et_in,
                "reference_et_in": round(reference_et_in, 4),
                "target_moisture_24h": round(target_24h, 4),
                "target_moisture_48h": round(target_48h, 4),
                "target_moisture_72h": round(target_72h, 4),
            }
        )

    frame = pd.DataFrame.from_records(records)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return frame


def main() -> None:
    args = parse_args()
    generate_sample_data(
        rows=args.rows,
        output_path=args.output_path,
        seed=args.seed,
        openet_csv=args.openet_csv,
    )


if __name__ == "__main__":
    main()
