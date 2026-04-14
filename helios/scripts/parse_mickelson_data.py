from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path

import pandas as pd


CROP_MAPPING = {
    "Potatoes": "potato",
    "Spring Grain": "corn",
    "Winter Grain": "corn",
    "Canola": "soybean",
}

PLACEHOLDER_CURRENT_MOISTURE = 0.55
PLACEHOLDER_FIELD_CAPACITY = 0.35
PLACEHOLDER_WILTING_POINT = 0.15
PLACEHOLDER_ROLLING_TEMP = 72.0
PLACEHOLDER_ROLLING_HUMIDITY = 38.0
PLACEHOLDER_ROLLING_SOLAR = 22.0
PLACEHOLDER_WIND_MPH = 8.0
PLACEHOLDER_DAYS_SINCE_RAIN = 7.0
PLACEHOLDER_RAIN_LAST_7_DAYS_IN = 0.1

MOISTURE_MIN = 0.10
MOISTURE_MAX = 0.45

SCHEMA_COLUMNS = [
    "field_id",
    "forecast_horizon_hours",
    "temperature_f",
    "humidity_pct",
    "wind_mph",
    "precipitation_in",
    "solar_radiation_mj_m2",
    "rolling_temp_mean",
    "rolling_humidity_mean",
    "rolling_precip_in",
    "rolling_solar_mean",
    "current_soil_moisture",
    "soil_moisture_lag_1",
    "soil_moisture_lag_2",
    "soil_moisture_delta_1",
    "soil_moisture_delta_2",
    "pump_capacity_in_per_hour",
    "water_rights_schedule_count",
    "energy_window_count",
    "irrigation_type",
    "soil_texture",
    "infiltration_rate_in_per_hour",
    "slope_pct",
    "drainage_class",
    "crop_type",
    "growth_stage",
    "max_irrigation_volume_in",
    "field_area_acres",
    "budget_dollars",
    "cumulative_irrigation_24h",
    "cumulative_irrigation_72h",
    "sensor_count",
    "season_month",
    "openet_monthly_et_in",
    "reference_et_in",
    "target_moisture_24h",
    "target_moisture_48h",
    "target_moisture_72h",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse Mickelson Farms water usage Excel into Helios training CSV.")
    parser.add_argument("--input", required=True, help="Path to the Mickelson Water_usage_2024.xlsx file")
    parser.add_argument("--output", default="data/mickelson_training_data.csv")
    return parser.parse_args()


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: (col.strip() if isinstance(col, str) else col) for col in df.columns}
    return df.rename(columns=renamed)


def _infer_growth_stage(week_index: int) -> str:
    if week_index <= 3:
        return "emergence"
    if week_index <= 8:
        return "vegetative"
    if week_index <= 13:
        return "flowering"
    if week_index <= 17:
        return "grain_fill"
    return "maturity"


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _build_weekly_et_lookup(hamer_df: pd.DataFrame, week_dates: list[pd.Timestamp]) -> dict[pd.Timestamp, float]:
    hamer = _strip_columns(hamer_df).copy()
    if "DATE" not in hamer.columns or "ETr" not in hamer.columns:
        raise ValueError("Hamer Agrimet sheet missing required DATE or ETr columns")
    hamer["DATE"] = pd.to_datetime(hamer["DATE"], errors="coerce")
    hamer = hamer.dropna(subset=["DATE"])
    hamer["ETr"] = pd.to_numeric(hamer["ETr"], errors="coerce").fillna(0.0)

    lookup: dict[pd.Timestamp, float] = {}
    for week_start in week_dates:
        window_end = week_start + pd.Timedelta(days=7)
        mask = (hamer["DATE"] >= week_start) & (hamer["DATE"] < window_end)
        lookup[week_start] = float(hamer.loc[mask, "ETr"].sum())
    return lookup


def parse_mickelson(input_path: str, output_path: str) -> pd.DataFrame:
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Input Excel file not found: {input_path}")

    excel = pd.ExcelFile(source)
    if "Data" not in excel.sheet_names:
        raise ValueError("Excel file missing 'Data' sheet")
    if "Hamer Agrimet" not in excel.sheet_names:
        raise ValueError("Excel file missing 'Hamer Agrimet' sheet")

    data = _strip_columns(pd.read_excel(excel, sheet_name="Data"))
    hamer = pd.read_excel(excel, sheet_name="Hamer Agrimet")

    week_columns_raw = [col for col in data.columns if isinstance(col, (pd.Timestamp, _dt.datetime))]
    if not week_columns_raw:
        raise ValueError("Data sheet has no weekly date columns")
    week_columns = sorted(pd.Timestamp(col) for col in week_columns_raw)
    week_column_lookup = {pd.Timestamp(col): col for col in week_columns_raw}

    weekly_et = _build_weekly_et_lookup(hamer, week_columns)

    skipped_no_crop = 0
    skipped_unmapped_crop = 0
    skipped_insufficient_weeks = 0
    skipped_zero_irrigation = 0
    skipped_missing_et = 0
    total_input_rows = len(data)
    records: list[dict[str, object]] = []

    for _, row in data.iterrows():
        crop_raw = row.get("Crop")
        if pd.isna(crop_raw) or crop_raw == 0 or crop_raw == "":
            skipped_no_crop += 1
            continue
        crop_key = str(crop_raw).strip()
        if crop_key not in CROP_MAPPING:
            skipped_unmapped_crop += 1
            continue
        crop_type = CROP_MAPPING[crop_key]

        weekly_values: list[tuple[int, pd.Timestamp, float]] = []
        for week_index, week_date in enumerate(week_columns, start=1):
            raw_value = row.get(week_column_lookup[week_date])
            if pd.isna(raw_value):
                continue
            try:
                numeric = float(raw_value)
            except (TypeError, ValueError):
                continue
            weekly_values.append((week_index, week_date, numeric))

        nonzero_count = sum(1 for _, _, v in weekly_values if v > 0)
        if nonzero_count < 3:
            skipped_insufficient_weeks += 1
            continue

        farm = str(row.get("Farm", "Unknown")).strip()
        field_label = str(row.get("Field", "Unknown")).strip()
        field_id = f"{farm}_{field_label}"

        for week_index, week_date, irrigation_in in weekly_values:
            if irrigation_in <= 0:
                skipped_zero_irrigation += 1
                continue
            reference_et_in = weekly_et.get(week_date, 0.0)
            if reference_et_in <= 0 or pd.isna(reference_et_in):
                skipped_missing_et += 1
                continue

            growth_stage = _infer_growth_stage(week_index)
            daily_et = reference_et_in / 7.0

            target_24h = _clamp(
                PLACEHOLDER_CURRENT_MOISTURE - (daily_et * 0.042) + (irrigation_in * 0.85 * 0.042),
                MOISTURE_MIN,
                MOISTURE_MAX,
            )
            target_48h = _clamp(target_24h - (daily_et * 0.042), MOISTURE_MIN, MOISTURE_MAX)
            target_72h = _clamp(target_48h - (daily_et * 0.042), MOISTURE_MIN, MOISTURE_MAX)

            record = {
                "field_id": field_id,
                "forecast_horizon_hours": 72,
                "temperature_f": PLACEHOLDER_ROLLING_TEMP,
                "humidity_pct": PLACEHOLDER_ROLLING_HUMIDITY,
                "wind_mph": PLACEHOLDER_WIND_MPH,
                "precipitation_in": round(PLACEHOLDER_RAIN_LAST_7_DAYS_IN / 7.0, 4),
                "solar_radiation_mj_m2": PLACEHOLDER_ROLLING_SOLAR,
                "rolling_temp_mean": PLACEHOLDER_ROLLING_TEMP,
                "rolling_humidity_mean": PLACEHOLDER_ROLLING_HUMIDITY,
                "rolling_precip_in": PLACEHOLDER_RAIN_LAST_7_DAYS_IN,
                "rolling_solar_mean": PLACEHOLDER_ROLLING_SOLAR,
                "current_soil_moisture": PLACEHOLDER_CURRENT_MOISTURE,
                "soil_moisture_lag_1": PLACEHOLDER_CURRENT_MOISTURE,
                "soil_moisture_lag_2": PLACEHOLDER_CURRENT_MOISTURE,
                "soil_moisture_delta_1": 0.0,
                "soil_moisture_delta_2": 0.0,
                "pump_capacity_in_per_hour": 0.256,
                "water_rights_schedule_count": 1,
                "energy_window_count": 1,
                "irrigation_type": "pivot",
                "soil_texture": "loam",
                "infiltration_rate_in_per_hour": 0.512,
                "slope_pct": 2.0,
                "drainage_class": "moderate",
                "crop_type": crop_type,
                "growth_stage": growth_stage,
                "max_irrigation_volume_in": 1.0,
                "field_area_acres": 100.0,
                "budget_dollars": 600.0,
                "cumulative_irrigation_24h": round(irrigation_in / 7.0, 4),
                "cumulative_irrigation_72h": round(irrigation_in * 3.0 / 7.0, 4),
                "sensor_count": 4,
                "season_month": int(week_date.month),
                "openet_monthly_et_in": round(daily_et, 4),
                "reference_et_in": round(reference_et_in, 4),
                "target_moisture_24h": round(target_24h, 4),
                "target_moisture_48h": round(target_48h, 4),
                "target_moisture_72h": round(target_72h, 4),
            }
            records.append(record)

    frame = pd.DataFrame.from_records(records, columns=SCHEMA_COLUMNS)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)

    print(f"Total input rows in Data sheet: {total_input_rows}")
    print("Skipped:")
    print(f"  no/zero crop:              {skipped_no_crop}")
    print(f"  unmapped crop:             {skipped_unmapped_crop}")
    print(f"  fewer than 3 nonzero weeks: {skipped_insufficient_weeks}")
    print(f"  zero/negative irrigation:   {skipped_zero_irrigation}")
    print(f"  missing/zero reference ET:  {skipped_missing_et}")
    print(f"Rows written: {len(frame)} → {destination}")
    return frame


def main() -> None:
    args = parse_args()
    parse_mickelson(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
