from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from helios.utils.evapotranspiration import estimate_reference_et_mm


SOIL_TEXTURES = ["sand", "loam", "clay"]
DRAINAGE_CLASSES = ["poor", "moderate", "well"]
IRRIGATION_TYPES = ["pivot", "drip", "flood"]
GROWTH_STAGES = ["emergence", "vegetative", "flowering", "grain_fill", "maturity"]
CROP_TYPES = ["corn", "soybean", "alfalfa", "potato"]

# Crop coefficients (Kc) per FAO-56 growth stage guidelines
CROP_KC = {
    "emergence": 0.3,
    "vegetative": 0.7,
    "flowering": 1.15,
    "grain_fill": 1.0,
    "maturity": 0.5,
}

# Root zone depth by soil texture (mm)
ROOT_ZONE_DEPTH_MM = {
    "sand": 300.0,
    "loam": 450.0,
    "clay": 500.0,
}

# Irrigation system efficiency (fraction of applied water entering root zone)
IRRIGATION_EFFICIENCY = {
    "pivot": 0.82,
    "drip": 0.93,
    "flood": 0.68,
}

# Drainage factor: fraction of excess water that drains per day
DRAINAGE_FACTOR = {
    "poor": 0.75,
    "moderate": 1.0,
    "well": 1.15,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic Helios training data.")
    parser.add_argument("--rows", type=int, default=2500)
    parser.add_argument("--output-path", default="data/sample_training_data.csv")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _choose_category(rng: np.random.Generator, values: list[str]) -> str:
    return str(rng.choice(values))


def generate_sample_data(rows: int, output_path: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records: list[dict[str, float | str | int]] = []

    texture_to_retention = {"sand": -0.04, "loam": 0.0, "clay": 0.05}

    for idx in range(rows):
        soil_texture = _choose_category(rng, SOIL_TEXTURES)
        drainage_class = _choose_category(rng, DRAINAGE_CLASSES)
        irrigation_type = _choose_category(rng, IRRIGATION_TYPES)
        growth_stage = _choose_category(rng, GROWTH_STAGES)
        crop_type = _choose_category(rng, CROP_TYPES)

        temperature_c = float(rng.normal(27.0, 6.0))
        humidity_pct = float(np.clip(rng.normal(48.0, 18.0), 15.0, 95.0))
        wind_mps = float(np.clip(rng.normal(3.2, 1.4), 0.3, 9.0))
        precipitation_mm = float(np.clip(rng.gamma(1.2, 2.5) - 1.0, 0.0, 18.0))
        solar_radiation_mj_m2 = float(np.clip(rng.normal(22.0, 5.0), 8.0, 34.0))
        rolling_temp_mean = float(temperature_c + rng.normal(0, 1.0))
        rolling_humidity_mean = float(np.clip(humidity_pct + rng.normal(0, 4.0), 10.0, 100.0))
        rolling_precip_mm = float(max(0.0, precipitation_mm + rng.normal(0, 1.0)))
        rolling_solar_mean = float(np.clip(solar_radiation_mj_m2 + rng.normal(0, 1.5), 8.0, 35.0))
        pump_capacity_mm_per_hour = float(np.clip(rng.normal(6.5, 2.0), 1.5, 12.0))
        max_irrigation_volume_mm = float(np.clip(rng.normal(18.0, 5.0), 6.0, 30.0))
        field_area_ha = float(np.clip(rng.normal(28.0, 10.0), 4.0, 60.0))
        budget_dollars = float(np.clip(rng.normal(600.0, 180.0), 100.0, 1200.0))
        infiltration_rate_mm_per_hour = float(
            np.clip(
                {"sand": 24.0, "loam": 13.0, "clay": 7.0}[soil_texture] + rng.normal(0, 1.8),
                3.0,
                30.0,
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
        cumulative_irrigation_24h = float(np.clip(rng.choice([0, 0, 0, 6, 9, 12, 15]) + rng.normal(0, 0.8), 0.0, 16.0))
        cumulative_irrigation_72h = float(
            np.clip(cumulative_irrigation_24h + rng.choice([0, 4, 8, 12]) + rng.normal(0, 1.2), 0.0, 26.0)
        )
        forecast_horizon_hours = int(rng.choice([24, 48, 72]))
        sensor_count = int(rng.integers(3, 8))
        water_rights_schedule_count = int(rng.integers(1, 4))
        energy_window_count = int(rng.integers(1, 3))

        reference_et_mm = estimate_reference_et_mm(
            temperature_c=rolling_temp_mean,
            humidity_pct=rolling_humidity_mean,
            wind_mps=wind_mps,
            solar_radiation_mj_m2=rolling_solar_mean,
        )

        # Soil water balance targets derived from FAO-56 ET₀ and crop coefficients.
        # This breaks the circular dependency: targets are physics-grounded, not
        # derived from the same heuristics the optimizer uses.
        kc = CROP_KC[growth_stage]
        root_depth = ROOT_ZONE_DEPTH_MM[soil_texture]
        eff = IRRIGATION_EFFICIENCY[irrigation_type]
        drainage = DRAINAGE_FACTOR[drainage_class]
        infiltration_efficiency = 0.90  # fraction of precipitation entering root zone

        def _step(moisture: float, precip: float, irrigation: float) -> float:
            et_depletion = (reference_et_mm * kc * drainage) / root_depth
            precip_gain = precip * infiltration_efficiency / root_depth
            irrigation_gain = irrigation * eff / root_depth
            return float(np.clip(
                moisture - et_depletion + precip_gain + irrigation_gain + rng.normal(0, 0.012),
                0.05, 0.50,
            ))

        target_24h = _step(current_soil_moisture, precipitation_mm, cumulative_irrigation_24h)
        target_48h = _step(target_24h, precipitation_mm * 0.5, 0.0)
        target_72h = _step(target_48h, 0.0, cumulative_irrigation_72h - cumulative_irrigation_24h)

        records.append(
            {
                "field_id": f"field-{idx % 48:03d}",
                "forecast_horizon_hours": forecast_horizon_hours,
                "temperature_c": round(temperature_c, 3),
                "humidity_pct": round(humidity_pct, 3),
                "wind_mps": round(wind_mps, 3),
                "precipitation_mm": round(precipitation_mm, 3),
                "solar_radiation_mj_m2": round(solar_radiation_mj_m2, 3),
                "rolling_temp_mean": round(rolling_temp_mean, 3),
                "rolling_humidity_mean": round(rolling_humidity_mean, 3),
                "rolling_precip_mm": round(rolling_precip_mm, 3),
                "rolling_solar_mean": round(rolling_solar_mean, 3),
                "current_soil_moisture": round(current_soil_moisture, 4),
                "soil_moisture_lag_1": round(soil_moisture_lag_1, 4),
                "soil_moisture_lag_2": round(soil_moisture_lag_2, 4),
                "soil_moisture_delta_1": round(soil_moisture_delta_1, 4),
                "soil_moisture_delta_2": round(soil_moisture_delta_2, 4),
                "pump_capacity_mm_per_hour": round(pump_capacity_mm_per_hour, 3),
                "water_rights_schedule_count": water_rights_schedule_count,
                "energy_window_count": energy_window_count,
                "irrigation_type": irrigation_type,
                "soil_texture": soil_texture,
                "infiltration_rate_mm_per_hour": round(infiltration_rate_mm_per_hour, 3),
                "slope_pct": round(slope_pct, 3),
                "drainage_class": drainage_class,
                "crop_type": crop_type,
                "growth_stage": growth_stage,
                "max_irrigation_volume_mm": round(max_irrigation_volume_mm, 3),
                "field_area_ha": round(field_area_ha, 3),
                "budget_dollars": round(budget_dollars, 3),
                "cumulative_irrigation_24h": round(cumulative_irrigation_24h, 3),
                "cumulative_irrigation_72h": round(cumulative_irrigation_72h, 3),
                "sensor_count": sensor_count,
                "reference_et_mm": round(reference_et_mm, 3),
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
    generate_sample_data(rows=args.rows, output_path=args.output_path, seed=args.seed)


if __name__ == "__main__":
    main()
