from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from helios.scripts.mickelson_support import (
    CROP_MAPPING,
    DEFAULT_BASE_MOISTURE,
    DEFAULT_BUDGET_DOLLARS,
    DEFAULT_DRAINAGE_CLASS,
    DEFAULT_INFILTRATION_RATE_IN_PER_HOUR,
    DEFAULT_IRRIGATION_TYPE,
    DEFAULT_MAX_IRRIGATION_VOLUME_IN,
    DEFAULT_SENSOR_COUNT,
    DEFAULT_SLOPE_PCT,
    SCHEMA_COLUMNS,
    build_acreage_lookup,
    build_week_dates,
    build_weekly_et_lookup,
    build_weekly_flow_lookup,
    build_weekly_lookup_from_totals,
    daily_moisture_step,
    infer_growth_stage,
    load_openet_monthly_et,
    pump_capacity_from_flow_gpm,
    simulate_weekly_start_state,
    strip_columns,
)

_build_acreage_lookup = build_acreage_lookup
_build_weekly_et_lookup = build_weekly_et_lookup
_build_weekly_flow_lookup = build_weekly_flow_lookup
_build_weekly_lookup_from_totals = build_weekly_lookup_from_totals
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse Mickelson Farms water usage Excel into Helios training CSV.")
    parser.add_argument("--input", required=True, help="Path to the Mickelson Water_usage_2024.xlsx file")
    parser.add_argument("--output", default="data/mickelson_training_data.csv")
    parser.add_argument(
        "--openet-csv",
        default=None,
        help="Optional monthly OpenET CSV with columns date and openet_et_mm. "
        "When omitted, openet_monthly_et_in falls back to the weekly Agrimet-derived daily ET.",
    )
    return parser.parse_args()


def _build_training_record(
    *,
    field_id: str,
    crop_type: str,
    growth_stage: str,
    week_date: pd.Timestamp,
    start_moisture: float,
    moisture_lag_1: float,
    moisture_lag_2: float,
    daily_rain_in: float,
    rain_week_in: float,
    daily_irrigation_in: float,
    daily_reference_et_in: float,
    openet_monthly_et_in: float,
    flow_gpm: float | None,
    field_area_acres: float,
) -> dict[str, object]:
    target_24h = daily_moisture_step(
        start_moisture,
        daily_precip_in=daily_rain_in,
        daily_irrigation_in=daily_irrigation_in,
        daily_reference_et_in=daily_reference_et_in,
        growth_stage=growth_stage,
    )
    target_48h = daily_moisture_step(
        target_24h,
        daily_precip_in=daily_rain_in,
        daily_irrigation_in=daily_irrigation_in,
        daily_reference_et_in=daily_reference_et_in,
        growth_stage=growth_stage,
    )
    target_72h = daily_moisture_step(
        target_48h,
        daily_precip_in=daily_rain_in,
        daily_irrigation_in=daily_irrigation_in,
        daily_reference_et_in=daily_reference_et_in,
        growth_stage=growth_stage,
    )

    return {
        "field_id": field_id,
        "forecast_horizon_hours": 72,
        "temperature_f": 72.0,
        "humidity_pct": 38.0,
        "wind_mph": 8.0,
        "precipitation_in": round(daily_rain_in, 4),
        "solar_radiation_mj_m2": 22.0,
        "rolling_temp_mean": 72.0,
        "rolling_humidity_mean": 38.0,
        "rolling_precip_in": round(rain_week_in, 4),
        "rolling_solar_mean": 22.0,
        "current_soil_moisture": round(start_moisture, 4),
        "soil_moisture_lag_1": round(moisture_lag_1, 4),
        "soil_moisture_lag_2": round(moisture_lag_2, 4),
        "soil_moisture_delta_1": round(start_moisture - moisture_lag_1, 4),
        "soil_moisture_delta_2": round(moisture_lag_1 - moisture_lag_2, 4),
        "pump_capacity_in_per_hour": round(pump_capacity_from_flow_gpm(flow_gpm, field_area_acres), 4),
        "water_rights_schedule_count": 1,
        "energy_window_count": 1,
        "irrigation_type": DEFAULT_IRRIGATION_TYPE,
        "soil_texture": "loam",
        "infiltration_rate_in_per_hour": DEFAULT_INFILTRATION_RATE_IN_PER_HOUR,
        "slope_pct": DEFAULT_SLOPE_PCT,
        "drainage_class": DEFAULT_DRAINAGE_CLASS,
        "crop_type": crop_type,
        "growth_stage": growth_stage,
        "max_irrigation_volume_in": DEFAULT_MAX_IRRIGATION_VOLUME_IN,
        "field_area_acres": round(field_area_acres, 3),
        "budget_dollars": DEFAULT_BUDGET_DOLLARS,
        "cumulative_irrigation_24h": round(daily_irrigation_in, 4),
        "cumulative_irrigation_72h": round(daily_irrigation_in * 3.0, 4),
        "sensor_count": DEFAULT_SENSOR_COUNT,
        "season_month": int(week_date.month),
        "openet_monthly_et_in": round(openet_monthly_et_in, 4),
        "reference_et_in": round(daily_reference_et_in, 4),
        "target_moisture_24h": round(target_24h, 4),
        "target_moisture_48h": round(target_48h, 4),
        "target_moisture_72h": round(target_72h, 4),
    }


def _collect_records(
    data: pd.DataFrame,
    hamer: pd.DataFrame,
    week_dates: list[pd.Timestamp],
    week_column_lookup: dict[pd.Timestamp, object],
    rainfall_lookup: dict[tuple[str, pd.Timestamp], float],
    acreage_lookup: dict[tuple[str, str], float],
    flow_lookup: dict[tuple[str, pd.Timestamp], float],
    openet_monthly_lookup: dict[int, float],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    stats = {
        "no_crop": 0,
        "unmapped_crop": 0,
        "insufficient_weeks": 0,
        "zero_irrigation": 0,
        "missing_et": 0,
    }
    records: list[dict[str, object]] = []

    for _, row in data.iterrows():
        crop_raw = row.get("Crop")
        if pd.isna(crop_raw) or crop_raw == 0 or crop_raw == "":
            stats["no_crop"] += 1
            continue

        crop_key = str(crop_raw).strip()
        if crop_key not in CROP_MAPPING:
            stats["unmapped_crop"] += 1
            continue

        crop_type = CROP_MAPPING[crop_key]
        weekly_et = build_weekly_et_lookup(hamer, week_dates, crop_key)
        weekly_values: list[tuple[int, pd.Timestamp, float]] = []
        for week_index, week_date in enumerate(week_dates, start=1):
            raw_value = row.get(week_column_lookup[week_date])
            if pd.isna(raw_value):
                continue
            try:
                irrigation_in = float(raw_value)
            except (TypeError, ValueError):
                continue
            weekly_values.append((week_index, week_date, irrigation_in))

        if sum(1 for _, _, value in weekly_values if value > 0) < 3:
            stats["insufficient_weeks"] += 1
            continue

        farm = str(row.get("Farm", "Unknown")).strip()
        field_label = str(row.get("Field", "Unknown")).strip()
        field_id = f"{farm}_{field_label}"
        farm_key = farm.strip().lower()
        field_key = field_label.strip().lower()
        location_key = str(row.get("Location", "")).strip().lower() or field_key
        field_area_acres = acreage_lookup.get((farm_key, field_key), 100.0)

        history: list[float] = []
        current_state = DEFAULT_BASE_MOISTURE.get(crop_type, 0.27)

        for week_index, week_date, irrigation_in in weekly_values:
            growth_stage = infer_growth_stage(week_index)
            reference_et_week = weekly_et.get(week_date, 0.0)
            if reference_et_week <= 0 or pd.isna(reference_et_week):
                stats["missing_et"] += 1
                continue

            rain_week_in = rainfall_lookup.get((location_key, week_date), 0.0)
            daily_reference_et_in = reference_et_week / 7.0
            daily_rain_in = rain_week_in / 7.0
            daily_irrigation_in = max(0.0, irrigation_in) / 7.0
            openet_monthly_et_in = openet_monthly_lookup.get(int(week_date.month), round(daily_reference_et_in, 4))
            flow_gpm = flow_lookup.get((field_key, week_date)) or flow_lookup.get((location_key, week_date))
            moisture_lag_1 = history[-1] if history else current_state
            moisture_lag_2 = history[-2] if len(history) >= 2 else moisture_lag_1
            start_moisture = current_state

            if irrigation_in <= 0:
                stats["zero_irrigation"] += 1
            else:
                records.append(
                    _build_training_record(
                        field_id=field_id,
                        crop_type=crop_type,
                        growth_stage=growth_stage,
                        week_date=week_date,
                        start_moisture=start_moisture,
                        moisture_lag_1=moisture_lag_1,
                        moisture_lag_2=moisture_lag_2,
                        daily_rain_in=daily_rain_in,
                        rain_week_in=rain_week_in,
                        daily_irrigation_in=daily_irrigation_in,
                        daily_reference_et_in=daily_reference_et_in,
                        openet_monthly_et_in=openet_monthly_et_in,
                        flow_gpm=flow_gpm,
                        field_area_acres=field_area_acres,
                    )
                )

            current_state = simulate_weekly_start_state(
                start_moisture,
                week_precip_in=rain_week_in,
                week_irrigation_in=irrigation_in,
                daily_reference_et_in=daily_reference_et_in,
                growth_stage=growth_stage,
            )
            history.append(start_moisture)

    return records, stats


def parse_mickelson(input_path: str, output_path: str, openet_csv: str | None = None) -> pd.DataFrame:
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Input Excel file not found: {input_path}")

    excel = pd.ExcelFile(source)
    required_sheets = {"Data", "Hamer Agrimet", "Rain Totals", "ACRE FEET"}
    missing_sheets = required_sheets - set(excel.sheet_names)
    if missing_sheets:
        raise ValueError(f"Excel file missing required sheets: {sorted(missing_sheets)}")

    data = strip_columns(pd.read_excel(excel, sheet_name="Data"))
    hamer = pd.read_excel(excel, sheet_name="Hamer Agrimet")
    rain_totals = pd.read_excel(excel, sheet_name="Rain Totals")
    acre_feet = pd.read_excel(excel, sheet_name="ACRE FEET")

    week_dates, week_column_lookup = build_week_dates(data)
    rainfall_lookup = build_weekly_lookup_from_totals(rain_totals, id_column="Location")
    acreage_lookup = build_acreage_lookup(acre_feet)
    flow_lookup = build_weekly_flow_lookup(excel)
    openet_monthly_lookup = load_openet_monthly_et(openet_csv)
    records, stats = _collect_records(
        data=data,
        hamer=hamer,
        week_dates=week_dates,
        week_column_lookup=week_column_lookup,
        rainfall_lookup=rainfall_lookup,
        acreage_lookup=acreage_lookup,
        flow_lookup=flow_lookup,
        openet_monthly_lookup=openet_monthly_lookup,
    )

    frame = pd.DataFrame.from_records(records, columns=SCHEMA_COLUMNS)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)

    logger.info("Total input rows in Data sheet: %s", len(data))
    logger.info("Skipped:")
    logger.info("  no/zero crop:               %s", stats["no_crop"])
    logger.info("  unmapped crop:              %s", stats["unmapped_crop"])
    logger.info("  fewer than 3 nonzero weeks: %s", stats["insufficient_weeks"])
    logger.info("  zero/negative irrigation:   %s", stats["zero_irrigation"])
    logger.info("  missing/zero reference ET:  %s", stats["missing_et"])
    logger.info("Rows written: %s -> %s", len(frame), destination)
    return frame


def main() -> None:
    args = parse_args()
    parse_mickelson(input_path=args.input, output_path=args.output, openet_csv=args.openet_csv)


if __name__ == "__main__":
    main()
