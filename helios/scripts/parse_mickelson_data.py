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
AGRIMET_COLUMN_BY_CROP = {
    "Potatoes": "POTA",
    "Spring Grain": "SGRN",
    "Winter Grain": "WGRN",
}

DEFAULT_SOIL_TEXTURE = "loam"
DEFAULT_DRAINAGE_CLASS = "moderate"
DEFAULT_IRRIGATION_TYPE = "pivot"
DEFAULT_INFILTRATION_RATE_IN_PER_HOUR = 0.512
DEFAULT_SLOPE_PCT = 2.0
DEFAULT_BUDGET_DOLLARS = 600.0
DEFAULT_MAX_IRRIGATION_VOLUME_IN = 1.0
DEFAULT_SENSOR_COUNT = 4
DEFAULT_PUMP_CAPACITY_IN_PER_HOUR = 0.256
DEFAULT_FIELD_AREA_ACRES = 100.0
DEFAULT_BASE_MOISTURE = {
    "potato": 0.30,
    "corn": 0.26,
    "soybean": 0.24,
}

MOISTURE_MIN = 0.10
MOISTURE_MAX = 0.45
ROOT_ZONE_DEPTH_IN = {
    "loam": 17.717,
}
IRRIGATION_EFFICIENCY = {
    "pivot": 0.82,
}
DRAINAGE_FACTOR = {
    "moderate": 1.0,
}
CROP_KC = {
    "emergence": 0.3,
    "vegetative": 0.7,
    "flowering": 1.15,
    "grain_fill": 1.0,
    "maturity": 0.5,
}

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
INCHES_PER_MM = 0.039370
GALLONS_PER_ACRE_INCH = 27154.0


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


def _strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: (col.strip() if isinstance(col, str) else col) for col in df.columns}
    return df.rename(columns=renamed)


def _normalize_key(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip().lower()


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


def _load_openet_monthly_et(openet_csv: str | None) -> dict[int, float]:
    if openet_csv is None:
        return {}
    df = pd.read_csv(openet_csv, parse_dates=["date"])
    lookup: dict[int, float] = {}
    for _, row in df.iterrows():
        month = int(row["date"].month)
        days_in_month = row["date"].days_in_month
        monthly_mm = float(row["openet_et_mm"])
        lookup[month] = round((monthly_mm / days_in_month) * INCHES_PER_MM, 4)
    return lookup


def _build_week_dates(data_df: pd.DataFrame) -> tuple[list[pd.Timestamp], dict[pd.Timestamp, object]]:
    week_columns_raw = [col for col in data_df.columns if isinstance(col, (pd.Timestamp, _dt.datetime))]
    if not week_columns_raw:
        raise ValueError("Data sheet has no weekly date columns")
    week_dates = sorted(pd.Timestamp(col) for col in week_columns_raw)
    week_column_lookup = {pd.Timestamp(col): col for col in week_columns_raw}
    return week_dates, week_column_lookup


def _build_weekly_lookup_from_totals(df: pd.DataFrame, id_column: str) -> dict[tuple[str, pd.Timestamp], float]:
    totals = _strip_columns(df).copy()
    week_dates = [pd.Timestamp(col) for col in totals.columns if isinstance(col, (pd.Timestamp, _dt.datetime))]
    lookup: dict[tuple[str, pd.Timestamp], float] = {}

    for _, row in totals.iterrows():
        entity_key = _normalize_key(row.get(id_column))
        if not entity_key:
            continue
        for week_date in week_dates:
            value = pd.to_numeric(row.get(week_date), errors="coerce")
            if pd.isna(value):
                continue
            lookup[(entity_key, pd.Timestamp(week_date))] = float(value)

    return lookup


def _build_acreage_lookup(acre_feet_df: pd.DataFrame) -> dict[tuple[str, str], float]:
    acreage = _strip_columns(acre_feet_df).copy()
    lookup: dict[tuple[str, str], float] = {}

    for _, row in acreage.iterrows():
        farm_key = _normalize_key(row.get("Column5"))
        field_key = _normalize_key(row.get("FIELD"))
        acres = pd.to_numeric(row.get("Acres"), errors="coerce")
        if not farm_key or not field_key or pd.isna(acres) or float(acres) <= 0:
            continue
        lookup[(farm_key, field_key)] = float(acres)

    return lookup


def _build_weekly_flow_lookup(excel: pd.ExcelFile) -> dict[tuple[str, pd.Timestamp], float]:
    lookup: dict[tuple[str, pd.Timestamp], float] = {}

    for sheet_name in excel.sheet_names:
        if not sheet_name.startswith("Week "):
            continue
        weekly = _strip_columns(pd.read_excel(excel, sheet_name=sheet_name))
        if weekly.empty or "Location" not in weekly.columns or "flow gpm" not in weekly.columns:
            continue
        for _, row in weekly.iterrows():
            location_key = _normalize_key(row.get("Location"))
            week_start = pd.to_datetime(row.get("start date"), errors="coerce")
            flow_gpm = pd.to_numeric(row.get("flow gpm"), errors="coerce")
            if not location_key or pd.isna(week_start) or pd.isna(flow_gpm) or float(flow_gpm) <= 0:
                continue
            lookup[(location_key, pd.Timestamp(week_start).normalize())] = float(flow_gpm)

    return lookup


def _build_weekly_et_lookup(
    hamer_df: pd.DataFrame,
    week_dates: list[pd.Timestamp],
    crop_raw: str,
) -> dict[pd.Timestamp, float]:
    hamer = _strip_columns(hamer_df).copy()
    if "DATE" not in hamer.columns or "ETr" not in hamer.columns:
        raise ValueError("Hamer Agrimet sheet missing required DATE or ETr columns")
    hamer["DATE"] = pd.to_datetime(hamer["DATE"], errors="coerce")
    hamer = hamer.dropna(subset=["DATE"])

    candidate_column = AGRIMET_COLUMN_BY_CROP.get(crop_raw)
    et_column = candidate_column if candidate_column in hamer.columns else "ETr"
    hamer[et_column] = pd.to_numeric(hamer[et_column], errors="coerce")
    if et_column != "ETr" and hamer[et_column].fillna(0.0).sum() <= 0:
        et_column = "ETr"
    hamer["ETr"] = pd.to_numeric(hamer["ETr"], errors="coerce").fillna(0.0)
    if et_column != "ETr":
        hamer[et_column] = hamer[et_column].fillna(hamer["ETr"])

    lookup: dict[pd.Timestamp, float] = {}
    for week_start in week_dates:
        window_end = week_start + pd.Timedelta(days=7)
        mask = (hamer["DATE"] >= week_start) & (hamer["DATE"] < window_end)
        lookup[week_start] = float(hamer.loc[mask, et_column].sum())
    return lookup


def _pump_capacity_from_flow_gpm(flow_gpm: float | None, field_area_acres: float) -> float:
    if flow_gpm is None or field_area_acres <= 0:
        return DEFAULT_PUMP_CAPACITY_IN_PER_HOUR
    gallons_per_hour = flow_gpm * 60.0
    return max(0.01, gallons_per_hour / (GALLONS_PER_ACRE_INCH * field_area_acres))


def _daily_moisture_step(
    moisture: float,
    *,
    daily_precip_in: float,
    daily_irrigation_in: float,
    daily_reference_et_in: float,
    growth_stage: str,
) -> float:
    kc = CROP_KC[growth_stage]
    root_depth = ROOT_ZONE_DEPTH_IN[DEFAULT_SOIL_TEXTURE]
    irrigation_efficiency = IRRIGATION_EFFICIENCY[DEFAULT_IRRIGATION_TYPE]
    drainage_factor = DRAINAGE_FACTOR[DEFAULT_DRAINAGE_CLASS]
    infiltration_efficiency = 0.90
    et_depletion = (daily_reference_et_in * kc * drainage_factor) / root_depth
    precip_gain = daily_precip_in * infiltration_efficiency / root_depth
    irrigation_gain = daily_irrigation_in * irrigation_efficiency / root_depth
    return _clamp(moisture - et_depletion + precip_gain + irrigation_gain, MOISTURE_MIN, MOISTURE_MAX)


def _simulate_weekly_start_state(
    moisture: float,
    *,
    week_precip_in: float,
    week_irrigation_in: float,
    daily_reference_et_in: float,
    growth_stage: str,
) -> float:
    state = moisture
    daily_precip_in = week_precip_in / 7.0
    daily_irrigation_in = max(0.0, week_irrigation_in) / 7.0
    for _ in range(7):
        state = _daily_moisture_step(
            state,
            daily_precip_in=daily_precip_in,
            daily_irrigation_in=daily_irrigation_in,
            daily_reference_et_in=daily_reference_et_in,
            growth_stage=growth_stage,
        )
    return state


def parse_mickelson(input_path: str, output_path: str, openet_csv: str | None = None) -> pd.DataFrame:
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Input Excel file not found: {input_path}")

    excel = pd.ExcelFile(source)
    required_sheets = {"Data", "Hamer Agrimet", "Rain Totals", "ACRE FEET"}
    missing_sheets = required_sheets - set(excel.sheet_names)
    if missing_sheets:
        raise ValueError(f"Excel file missing required sheets: {sorted(missing_sheets)}")

    data = _strip_columns(pd.read_excel(excel, sheet_name="Data"))
    hamer = pd.read_excel(excel, sheet_name="Hamer Agrimet")
    rain_totals = pd.read_excel(excel, sheet_name="Rain Totals")
    acre_feet = pd.read_excel(excel, sheet_name="ACRE FEET")

    week_dates, week_column_lookup = _build_week_dates(data)
    rainfall_lookup = _build_weekly_lookup_from_totals(rain_totals, id_column="Location")
    acreage_lookup = _build_acreage_lookup(acre_feet)
    flow_lookup = _build_weekly_flow_lookup(excel)
    openet_monthly_lookup = _load_openet_monthly_et(openet_csv)

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
        weekly_et = _build_weekly_et_lookup(hamer, week_dates, crop_key)
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

        nonzero_count = sum(1 for _, _, value in weekly_values if value > 0)
        if nonzero_count < 3:
            skipped_insufficient_weeks += 1
            continue

        farm = str(row.get("Farm", "Unknown")).strip()
        field_label = str(row.get("Field", "Unknown")).strip()
        field_id = f"{farm}_{field_label}"
        farm_key = _normalize_key(farm)
        field_key = _normalize_key(field_label)
        location_key = _normalize_key(row.get("Location")) or field_key
        field_area_acres = acreage_lookup.get((farm_key, field_key), DEFAULT_FIELD_AREA_ACRES)

        history: list[float] = []
        current_state = DEFAULT_BASE_MOISTURE.get(crop_type, 0.27)

        for week_index, week_date, irrigation_in in weekly_values:
            growth_stage = _infer_growth_stage(week_index)
            reference_et_week = weekly_et.get(week_date, 0.0)
            if reference_et_week <= 0 or pd.isna(reference_et_week):
                skipped_missing_et += 1
                continue

            rain_week_in = rainfall_lookup.get((location_key, week_date), 0.0)
            daily_reference_et_in = reference_et_week / 7.0
            daily_rain_in = rain_week_in / 7.0
            daily_irrigation_in = max(0.0, irrigation_in) / 7.0
            openet_monthly_et_in = openet_monthly_lookup.get(
                int(week_date.month),
                round(daily_reference_et_in, 4),
            )
            flow_gpm = flow_lookup.get((field_key, week_date))
            if flow_gpm is None:
                flow_gpm = flow_lookup.get((location_key, week_date))

            moisture_lag_1 = history[-1] if history else current_state
            moisture_lag_2 = history[-2] if len(history) >= 2 else moisture_lag_1
            start_moisture = current_state

            if irrigation_in <= 0:
                skipped_zero_irrigation += 1
            else:
                target_24h = _daily_moisture_step(
                    start_moisture,
                    daily_precip_in=daily_rain_in,
                    daily_irrigation_in=daily_irrigation_in,
                    daily_reference_et_in=daily_reference_et_in,
                    growth_stage=growth_stage,
                )
                target_48h = _daily_moisture_step(
                    target_24h,
                    daily_precip_in=daily_rain_in,
                    daily_irrigation_in=daily_irrigation_in,
                    daily_reference_et_in=daily_reference_et_in,
                    growth_stage=growth_stage,
                )
                target_72h = _daily_moisture_step(
                    target_48h,
                    daily_precip_in=daily_rain_in,
                    daily_irrigation_in=daily_irrigation_in,
                    daily_reference_et_in=daily_reference_et_in,
                    growth_stage=growth_stage,
                )

                records.append(
                    {
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
                        "pump_capacity_in_per_hour": round(
                            _pump_capacity_from_flow_gpm(flow_gpm, field_area_acres),
                            4,
                        ),
                        "water_rights_schedule_count": 1,
                        "energy_window_count": 1,
                        "irrigation_type": DEFAULT_IRRIGATION_TYPE,
                        "soil_texture": DEFAULT_SOIL_TEXTURE,
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
                )

            current_state = _simulate_weekly_start_state(
                start_moisture,
                week_precip_in=rain_week_in,
                week_irrigation_in=irrigation_in,
                daily_reference_et_in=daily_reference_et_in,
                growth_stage=growth_stage,
            )
            history.append(start_moisture)

    frame = pd.DataFrame.from_records(records, columns=SCHEMA_COLUMNS)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)

    print(f"Total input rows in Data sheet: {total_input_rows}")
    print("Skipped:")
    print(f"  no/zero crop:               {skipped_no_crop}")
    print(f"  unmapped crop:              {skipped_unmapped_crop}")
    print(f"  fewer than 3 nonzero weeks: {skipped_insufficient_weeks}")
    print(f"  zero/negative irrigation:   {skipped_zero_irrigation}")
    print(f"  missing/zero reference ET:  {skipped_missing_et}")
    print(f"Rows written: {len(frame)} → {destination}")
    return frame


def main() -> None:
    args = parse_args()
    parse_mickelson(
        input_path=args.input,
        output_path=args.output,
        openet_csv=args.openet_csv,
    )


if __name__ == "__main__":
    main()
