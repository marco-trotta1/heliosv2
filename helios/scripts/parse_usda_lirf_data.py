from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from helios.scripts.mickelson_support import (
    DEFAULT_BUDGET_DOLLARS,
    DEFAULT_DRAINAGE_CLASS,
    DEFAULT_INFILTRATION_RATE_IN_PER_HOUR,
    DEFAULT_IRRIGATION_TYPE,
    DEFAULT_MAX_IRRIGATION_VOLUME_IN,
    DEFAULT_PUMP_CAPACITY_IN_PER_HOUR,
    DEFAULT_SLOPE_PCT,
)


SOURCE_ID = "usda_lirf_2012_2013"
MM_PER_INCH = 25.4
CM_PER_INCH = 2.54
MPS_TO_MPH = 2.2369362921

DEPTH_LAYERS_CM = [
    ("SWC_15", 0.0, 15.0),
    ("SWC_30", 15.0, 45.0),
    ("SWC_60", 45.0, 75.0),
    ("SWC_90", 75.0, 105.0),
    ("SWC_120", 105.0, 135.0),
    ("SWC_150", 135.0, 175.0),
    ("SWC_200", 175.0, 225.0),
]

TRAINING_COLUMNS = [
    "source_id",
    "field_id",
    "prediction_time",
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
    "moisture_min",
    "moisture_max",
    "moisture_mean",
    "moisture_spread",
    "physical_sensor_count",
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
    "target_source_24h",
    "target_source_48h",
    "target_source_72h",
    "target_moisture_24h",
    "target_moisture_48h",
    "target_moisture_72h",
]

WATER_BALANCE_REQUIRED_COLUMNS = [
    "Year",
    "Date",
    "Trt_code",
    "Growth_stage",
    "root_depth (cm)",
    "precip_gross (mm)",
    "irr_gross (mm)",
    "ETr (mm)",
    *[column for column, _, _ in DEPTH_LAYERS_CM],
]

WEATHER_REQUIRED_COLUMNS = [
    "TIMESTAMP",
    "AirTemp_C",
    "RH_fraction",
    "WindSpeed_m_s^1",
    "HrlySolRad_kJ_m^2_min^1",
    "Rain-Tot",
    "ETr-Daily",
]


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse USDA LIRF maize workbook into Helios training rows.")
    parser.add_argument(
        "--input",
        default="data/public/usda_lirf_2012_2013/raw/2012-2013_Maize_Compiled database 06012018.xlsx",
    )
    parser.add_argument(
        "--output",
        default="data/public/usda_lirf_2012_2013/processed/usda_lirf_training_data.csv",
        help="Helios-compatible wide training CSV.",
    )
    parser.add_argument(
        "--normalized-output",
        default="data/public/usda_lirf_2012_2013/processed/usda_lirf_normalized_examples.csv",
        help="Long normalized CSV with one row per origin and horizon.",
    )
    parser.add_argument(
        "--report-output",
        default="data/public/usda_lirf_2012_2013/processed/usda_lirf_parse_report.json",
    )
    return parser.parse_args()


def _sheet(excel: pd.ExcelFile, sheet_name: str, *, header: int = 1) -> pd.DataFrame:
    if sheet_name not in excel.sheet_names:
        raise ValueError(f"USDA workbook missing required sheet: {sheet_name}")
    return pd.read_excel(excel, sheet_name=sheet_name, header=header)


def _growth_stage(value: object) -> str:
    if pd.isna(value):
        return "vegetative"
    text = str(value).strip().upper()
    if text in {"PLANT", "EMERGENCE"} or text.startswith("V1") or text in {"V2", "V3"}:
        return "emergence"
    if text.startswith("V") or text == "VT":
        return "vegetative"
    if text in {"R1", "R2"}:
        return "flowering"
    if text.startswith("R3") or text.startswith("R4") or text.startswith("R5"):
        return "grain_fill"
    if text.startswith("R6") or text == "HARVEST":
        return "maturity"
    return "vegetative"


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    coerced = frame.copy()
    for column in columns:
        if column in coerced.columns:
            coerced[column] = pd.to_numeric(coerced[column], errors="coerce")
    return coerced


def _root_zone_vwc(row: pd.Series) -> float | None:
    root_depth = pd.to_numeric(row.get("root_depth (cm)"), errors="coerce")
    if pd.isna(root_depth) or float(root_depth) <= 0:
        root_depth = 105.0

    weighted_sum = 0.0
    total_depth = 0.0
    for column, top_cm, bottom_cm in DEPTH_LAYERS_CM:
        value = pd.to_numeric(row.get(column), errors="coerce")
        if pd.isna(value):
            continue
        overlap = max(0.0, min(float(root_depth), bottom_cm) - top_cm)
        if overlap <= 0:
            continue
        weighted_sum += float(value) * overlap
        total_depth += overlap

    if total_depth <= 0:
        return None
    return round((weighted_sum / total_depth) / 100.0, 6)


def _daily_weather(weather: pd.DataFrame) -> pd.DataFrame:
    working = weather.copy()
    _require_columns(working, WEATHER_REQUIRED_COLUMNS, "USDA weather sheet")
    working["Date"] = pd.to_datetime(working["TIMESTAMP"], errors="coerce").dt.normalize()
    working = _coerce_numeric(
        working,
        [
            "AirTemp_C",
            "RH_fraction",
            "WindSpeed_m_s^1",
            "HrlySolRad_kJ_m^2_min^1",
            "Rain-Tot",
            "ETr-Daily",
        ],
    )
    grouped = working.groupby("Date", as_index=False).agg(
        temperature_c=("AirTemp_C", "mean"),
        humidity_fraction=("RH_fraction", "mean"),
        wind_m_s=("WindSpeed_m_s^1", "mean"),
        solar_kj_m2_min=("HrlySolRad_kJ_m^2_min^1", "sum"),
        rain_mm=("Rain-Tot", "sum"),
        etr_daily_mm=("ETr-Daily", "first"),
    )
    grouped["temperature_f"] = grouped["temperature_c"] * 9.0 / 5.0 + 32.0
    grouped["humidity_pct"] = grouped["humidity_fraction"] * 100.0
    grouped["wind_mph"] = grouped["wind_m_s"] * MPS_TO_MPH
    grouped["solar_radiation_mj_m2"] = grouped["solar_kj_m2_min"] * 60.0 / 1000.0
    return grouped[
        ["Date", "temperature_f", "humidity_pct", "wind_mph", "solar_radiation_mj_m2", "rain_mm", "etr_daily_mm"]
    ]


def _prepare_water_balance(excel: pd.ExcelFile) -> pd.DataFrame:
    water = _sheet(excel, "Water Balance ET", header=1)
    _require_columns(water, WATER_BALANCE_REQUIRED_COLUMNS, "USDA water balance sheet")
    water["Date"] = pd.to_datetime(water["Date"], errors="coerce").dt.normalize()
    water = water.dropna(subset=["Year", "Date", "Trt_code"]).copy()
    numeric_columns = [
        "Year",
        "DOY",
        "Trt_code",
        "LAI",
        "Plant_height (cm)",
        "root_depth (cm)",
        "canopy_cover",
        "SWD_RZ",
        "precip_gross (mm)",
        "irr_gross (mm)",
        "ETr (mm)",
        *[column for column, _, _ in DEPTH_LAYERS_CM],
    ]
    water = _coerce_numeric(water, numeric_columns)
    water["observed_vwc"] = water.apply(_root_zone_vwc, axis=1)
    water = water.dropna(subset=["observed_vwc"]).copy()
    water["growth_stage_normalized"] = water["Growth_stage"].map(_growth_stage)
    water["group_id"] = water["Year"].astype(int).astype(str) + "_trt_" + water["Trt_code"].astype(int).astype(str)
    water = water.sort_values(["Year", "Trt_code", "Date"]).reset_index(drop=True)
    return water


def _build_base_features(water: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    merged = water.merge(weather, on="Date", how="left")
    merged = merged.sort_values(["Year", "Trt_code", "Date"]).reset_index(drop=True)
    merged["temperature_f"] = merged["temperature_f"].fillna(72.0)
    merged["humidity_pct"] = merged["humidity_pct"].fillna(45.0)
    merged["wind_mph"] = merged["wind_mph"].fillna(7.0)
    merged["solar_radiation_mj_m2"] = merged["solar_radiation_mj_m2"].fillna(22.0)
    merged["reference_et_in"] = (merged["ETr (mm)"].fillna(merged["etr_daily_mm"]) / MM_PER_INCH).fillna(0.2)
    merged["precipitation_in"] = (merged["precip_gross (mm)"].fillna(merged["rain_mm"]) / MM_PER_INCH).fillna(0.0)
    merged["cumulative_irrigation_24h"] = (merged["irr_gross (mm)"] / MM_PER_INCH).fillna(0.0).clip(lower=0.0)

    grouped = merged.groupby(["Year", "Trt_code"], group_keys=False)
    merged["rolling_temp_mean"] = grouped["temperature_f"].transform(lambda values: values.rolling(3, min_periods=1).mean())
    merged["rolling_humidity_mean"] = grouped["humidity_pct"].transform(lambda values: values.rolling(3, min_periods=1).mean())
    merged["rolling_solar_mean"] = grouped["solar_radiation_mj_m2"].transform(
        lambda values: values.rolling(3, min_periods=1).mean()
    )
    merged["rolling_precip_in"] = grouped["precipitation_in"].transform(lambda values: values.rolling(3, min_periods=1).sum())
    merged["cumulative_irrigation_72h"] = grouped["cumulative_irrigation_24h"].transform(
        lambda values: values.rolling(3, min_periods=1).sum()
    )
    merged["soil_moisture_lag_1"] = grouped["observed_vwc"].shift(1)
    merged["soil_moisture_lag_2"] = grouped["observed_vwc"].shift(2)
    merged["soil_moisture_lag_1"] = merged["soil_moisture_lag_1"].fillna(merged["observed_vwc"])
    merged["soil_moisture_lag_2"] = merged["soil_moisture_lag_2"].fillna(merged["soil_moisture_lag_1"])
    merged["soil_moisture_delta_1"] = merged["observed_vwc"] - merged["soil_moisture_lag_1"]
    merged["soil_moisture_delta_2"] = merged["soil_moisture_lag_1"] - merged["soil_moisture_lag_2"]
    month_key = merged["Date"].dt.month
    merged["openet_monthly_et_in"] = merged.groupby(["Year", "Trt_code", month_key])["reference_et_in"].transform(
        lambda values: values.expanding(min_periods=1).mean()
    )
    return merged


def _target_lookup(frame: pd.DataFrame) -> dict[tuple[int, int, pd.Timestamp], tuple[float, str]]:
    lookup: dict[tuple[int, int, pd.Timestamp], tuple[float, str]] = {}
    for (year, trt_code), group in frame.groupby(["Year", "Trt_code"]):
        observed = (
            group[["Date", "observed_vwc"]]
            .dropna()
            .drop_duplicates(subset=["Date"])
            .set_index("Date")
            .sort_index()["observed_vwc"]
        )
        if observed.empty:
            continue

        daily_index = pd.date_range(observed.index.min(), observed.index.max(), freq="D")
        interpolated = observed.reindex(daily_index).interpolate(method="time", limit_area="inside")
        observed_dates = set(observed.index)
        for date, value in interpolated.dropna().items():
            source = "root_zone_weighted_swc" if date in observed_dates else "root_zone_weighted_swc_daily_interpolated"
            lookup[(int(year), int(trt_code), pd.Timestamp(date))] = (float(value), source)
    return lookup


def _build_rows(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = _target_lookup(features)
    normalized_rows: list[dict[str, Any]] = []
    training_rows: list[dict[str, Any]] = []

    for _, row in features.iterrows():
        year = int(row["Year"])
        trt_code = int(row["Trt_code"])
        prediction_time = pd.Timestamp(row["Date"])
        horizon_targets: dict[int, tuple[float, str]] = {}
        origin_normalized_rows: list[dict[str, Any]] = []
        for horizon in (24, 48, 72):
            label_time = prediction_time + pd.Timedelta(hours=horizon)
            target_info = lookup.get((year, trt_code, label_time))
            if target_info is None:
                continue
            target, target_source = target_info
            horizon_targets[horizon] = target_info
            origin_normalized_rows.append(
                {
                    "source_id": SOURCE_ID,
                    "field_id": f"{SOURCE_ID}_{year}_trt_{trt_code}",
                    "treatment_code": trt_code,
                    "prediction_time": prediction_time.isoformat(),
                    "feature_cutoff_at": (prediction_time + pd.Timedelta(hours=23, minutes=59, seconds=59)).isoformat(),
                    "horizon_hours": horizon,
                    "label_time": label_time.isoformat(),
                    "observed_vwc": target,
                    "target_source": target_source,
                    "temporal_resolution": "daily",
                    "label_tolerance_hours": 0,
                    "current_soil_moisture": float(row["observed_vwc"]),
                    "cumulative_irrigation_24h": float(row["cumulative_irrigation_24h"]),
                    "cumulative_irrigation_72h": float(row["cumulative_irrigation_72h"]),
                    "precipitation_in": float(row["precipitation_in"]),
                    "reference_et_in": float(row["reference_et_in"]),
                    "growth_stage": row["growth_stage_normalized"],
                    "root_depth_in": float(row["root_depth (cm)"]) / CM_PER_INCH
                    if pd.notna(row["root_depth (cm)"])
                    else None,
                }
            )

        if set(horizon_targets) != {24, 48, 72}:
            continue
        normalized_rows.extend(origin_normalized_rows)

        swc_values = [
            float(row[column])
            for column, _, _ in DEPTH_LAYERS_CM
            if column in row and pd.notna(row[column])
        ]
        moisture_values = [value / 100.0 for value in swc_values] or [float(row["observed_vwc"])]
        training_rows.append(
            {
                "source_id": SOURCE_ID,
                "field_id": f"{SOURCE_ID}_{year}_trt_{trt_code}",
                "prediction_time": prediction_time.isoformat(),
                "forecast_horizon_hours": 72,
                "temperature_f": round(float(row["temperature_f"]), 3),
                "humidity_pct": round(float(row["humidity_pct"]), 3),
                "wind_mph": round(float(row["wind_mph"]), 3),
                "precipitation_in": round(float(row["precipitation_in"]), 4),
                "solar_radiation_mj_m2": round(float(row["solar_radiation_mj_m2"]), 3),
                "rolling_temp_mean": round(float(row["rolling_temp_mean"]), 3),
                "rolling_humidity_mean": round(float(row["rolling_humidity_mean"]), 3),
                "rolling_precip_in": round(float(row["rolling_precip_in"]), 4),
                "rolling_solar_mean": round(float(row["rolling_solar_mean"]), 3),
                "current_soil_moisture": round(float(row["observed_vwc"]), 4),
                "soil_moisture_lag_1": round(float(row["soil_moisture_lag_1"]), 4),
                "soil_moisture_lag_2": round(float(row["soil_moisture_lag_2"]), 4),
                "soil_moisture_delta_1": round(float(row["soil_moisture_delta_1"]), 4),
                "soil_moisture_delta_2": round(float(row["soil_moisture_delta_2"]), 4),
                "moisture_min": round(min(moisture_values), 4),
                "moisture_max": round(max(moisture_values), 4),
                "moisture_mean": round(sum(moisture_values) / len(moisture_values), 4),
                "moisture_spread": round(max(moisture_values) - min(moisture_values), 4),
                "physical_sensor_count": len(moisture_values),
                "pump_capacity_in_per_hour": DEFAULT_PUMP_CAPACITY_IN_PER_HOUR,
                "water_rights_schedule_count": 1,
                "energy_window_count": 1,
                "irrigation_type": DEFAULT_IRRIGATION_TYPE,
                "soil_texture": "loam",
                "infiltration_rate_in_per_hour": DEFAULT_INFILTRATION_RATE_IN_PER_HOUR,
                "slope_pct": DEFAULT_SLOPE_PCT,
                "drainage_class": DEFAULT_DRAINAGE_CLASS,
                "crop_type": "corn",
                "growth_stage": row["growth_stage_normalized"],
                "max_irrigation_volume_in": DEFAULT_MAX_IRRIGATION_VOLUME_IN,
                "field_area_acres": 1.0,
                "budget_dollars": DEFAULT_BUDGET_DOLLARS,
                "cumulative_irrigation_24h": round(float(row["cumulative_irrigation_24h"]), 4),
                "cumulative_irrigation_72h": round(float(row["cumulative_irrigation_72h"]), 4),
                "sensor_count": len(moisture_values),
                "season_month": int(prediction_time.month),
                "openet_monthly_et_in": round(float(row["openet_monthly_et_in"]), 4),
                "reference_et_in": round(float(row["reference_et_in"]), 4),
                "target_source_24h": horizon_targets[24][1],
                "target_source_48h": horizon_targets[48][1],
                "target_source_72h": horizon_targets[72][1],
                "target_moisture_24h": round(horizon_targets[24][0], 4),
                "target_moisture_48h": round(horizon_targets[48][0], 4),
                "target_moisture_72h": round(horizon_targets[72][0], 4),
            }
        )

    return pd.DataFrame.from_records(training_rows, columns=TRAINING_COLUMNS), pd.DataFrame.from_records(normalized_rows)


def parse_usda_lirf(
    *,
    input_path: str,
    output_path: str,
    normalized_output_path: str,
    report_output_path: str | None = None,
) -> dict[str, Any]:
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"USDA workbook not found: {input_path}")

    excel = pd.ExcelFile(source)
    water = _prepare_water_balance(excel)
    weather = _daily_weather(_sheet(excel, "Weather data", header=0))
    features = _build_base_features(water, weather)
    training, normalized = _build_rows(features)
    measured = normalized[normalized["target_source"] == "root_zone_weighted_swc"] if not normalized.empty else normalized
    vwc_min = float(water["observed_vwc"].min()) if not water.empty else None
    vwc_max = float(water["observed_vwc"].max()) if not water.empty else None
    vwc_in_range = vwc_min is not None and vwc_max is not None and 0.05 <= vwc_min <= vwc_max <= 0.45
    measured_label_count = int(len(measured))
    training_counts = (
        training.assign(
            _group=training["field_id"].str.replace(f"{SOURCE_ID}_", "", regex=False)
            if "field_id" in training
            else pd.Series(dtype=str)
        )
        .groupby("_group")
        .size()
        .to_dict()
        if not training.empty
        else {}
    )
    measured_counts = (
        measured.assign(
            _group=measured["field_id"].str.replace(f"{SOURCE_ID}_", "", regex=False)
            if "field_id" in measured
            else pd.Series(dtype=str)
        )
        .groupby("_group")
        .size()
        .to_dict()
        if not measured.empty
        else {}
    )
    has_year_treatment_counts = bool(training_counts) and all(count > 0 for count in training_counts.values())
    has_measured_year_treatment_counts = bool(measured_counts) and all(count > 0 for count in measured_counts.values())

    output = Path(output_path)
    normalized_output = Path(normalized_output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized_output.parent.mkdir(parents=True, exist_ok=True)
    training.to_csv(output, index=False)
    normalized.to_csv(normalized_output, index=False)

    report = {
        "source_id": SOURCE_ID,
        "input_path": input_path,
        "training_output": str(output),
        "normalized_output": str(normalized_output),
        "water_balance_rows_with_vwc": int(len(water)),
        "normalized_rows": int(len(normalized)),
        "training_rows": int(len(training)),
        "horizons": [24, 48, 72],
        "target_columns": ["target_moisture_24h", "target_moisture_48h", "target_moisture_72h"],
        "target_source": "root_zone_weighted_swc_or_daily_interpolated",
        "temporal_resolution": "daily",
        "measured_label_count": measured_label_count,
        "vwc_range": {
            "min": round(vwc_min, 4) if vwc_min is not None else None,
            "max": round(vwc_max, 4) if vwc_max is not None else None,
        },
        "year_treatment_training_counts": {str(key): int(value) for key, value in training_counts.items()},
        "year_treatment_measured_counts": {str(key): int(value) for key, value in measured_counts.items()},
        "usable_for_training": bool(
            len(training) > 0
            and measured_label_count > 0
            and vwc_in_range
            and has_year_treatment_counts
            and has_measured_year_treatment_counts
        ),
    }
    if report_output_path is not None:
        report_output = Path(report_output_path)
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    args = parse_args()
    report = parse_usda_lirf(
        input_path=args.input,
        output_path=args.output,
        normalized_output_path=args.normalized_output,
        report_output_path=args.report_output,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
