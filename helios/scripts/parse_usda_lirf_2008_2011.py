from __future__ import annotations

import argparse
import json
import re
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
from helios.scripts.parse_usda_lirf_data import (
    MM_PER_INCH,
    MPS_TO_MPH,
    TRAINING_COLUMNS,
    _growth_stage,
)


SOURCE_ID = "usda_lirf_2008_2011"
DEPTH_LAYERS_CM = [(4, 0.0, 15.0), (5, 15.0, 45.0), (6, 45.0, 75.0), (7, 75.0, 105.0), (8, 105.0, 135.0), (9, 135.0, 165.0), (10, 165.0, 200.0)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse historical USDA LIRF maize workbooks into Helios training rows.")
    parser.add_argument("--input-dir", default="data/candidates/usda_lirf_2008_2011/raw")
    parser.add_argument("--output", default="data/candidates/usda_lirf_2008_2011/processed/training.csv")
    parser.add_argument("--normalized-output", default="data/candidates/usda_lirf_2008_2011/processed/normalized.csv")
    parser.add_argument("--report-output", default="data/candidates/usda_lirf_2008_2011/processed/report.json")
    return parser.parse_args()


def _year_from_path(path: Path) -> int:
    match = re.search(r"(20\d{2})", path.name)
    if match is None:
        raise ValueError(f"Could not determine year from {path.name}")
    return int(match.group(1))


def _root_zone_vwc(row: pd.Series) -> float | None:
    root_depth = pd.to_numeric(row.get("root_depth_cm"), errors="coerce")
    if pd.isna(root_depth) or float(root_depth) <= 0:
        return None
    weighted_sum = 0.0
    total_depth = 0.0
    for column, top_cm, bottom_cm in DEPTH_LAYERS_CM:
        value = pd.to_numeric(row.get(f"swc_{column}"), errors="coerce")
        overlap = max(0.0, min(float(root_depth), bottom_cm) - top_cm)
        if pd.isna(value) or overlap <= 0:
            continue
        weighted_sum += float(value) * overlap
        total_depth += overlap
    return round((weighted_sum / total_depth) / 100.0, 6) if total_depth else None


def _read_treatment_workbooks(input_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for workbook in sorted(input_dir.glob("LIRF Maize 20*.xlsx")):
        year = _year_from_path(workbook)
        excel = pd.ExcelFile(workbook)
        for sheet_name in excel.sheet_names:
            match = re.fullmatch(r"Tmnt(\d+)", sheet_name)
            if match is None:
                continue
            treatment = int(match.group(1))
            raw = pd.read_excel(excel, sheet_name=sheet_name, header=None)
            for _, values in raw.iloc[4:].iterrows():
                doy = pd.to_numeric(values.iloc[0], errors="coerce")
                if pd.isna(doy):
                    continue
                date = pd.Timestamp(year=year, month=1, day=1) + pd.to_timedelta(int(doy) - 1, unit="D")
                row: dict[str, Any] = {
                    "year": year,
                    "treatment": treatment,
                    "date": date,
                    "precipitation_mm": pd.to_numeric(values.iloc[1], errors="coerce"),
                    "irrigation_mm": pd.to_numeric(values.iloc[2], errors="coerce"),
                    "growth_stage": _growth_stage(values.iloc[12]),
                    "root_depth_cm": pd.to_numeric(values.iloc[13], errors="coerce"),
                    "canopy_cover": pd.to_numeric(values.iloc[14], errors="coerce"),
                    "lai": pd.to_numeric(values.iloc[15], errors="coerce"),
                    "plant_height_cm": pd.to_numeric(values.iloc[16], errors="coerce"),
                    "etr_mm": pd.to_numeric(values.iloc[19], errors="coerce"),
                }
                for index, _, _ in DEPTH_LAYERS_CM:
                    row[f"swc_{index}"] = pd.to_numeric(values.iloc[index], errors="coerce")
                row["observed_vwc"] = _root_zone_vwc(pd.Series(row))
                if pd.notna(row["observed_vwc"]):
                    rows.append(row)
    if not rows:
        raise ValueError(f"No LIRF treatment rows found in {input_dir}")
    return pd.DataFrame(rows).sort_values(["year", "treatment", "date"]).reset_index(drop=True)


def _read_weather_workbooks(input_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for workbook in sorted(input_dir.glob("LIRF Weather 20*.xlsx")):
        year = _year_from_path(workbook)
        raw = pd.read_excel(workbook, sheet_name="Hourly", header=None)
        for _, values in raw.iloc[3:].iterrows():
            timestamp = pd.to_datetime(values.iloc[0], errors="coerce")
            if pd.isna(timestamp):
                continue
            rows.append(
                {
                    "year": year,
                    "date": pd.Timestamp(timestamp).normalize(),
                    "temperature_f": float(pd.to_numeric(values.iloc[2], errors="coerce") * 9.0 / 5.0 + 32.0),
                    "humidity_pct": float(pd.to_numeric(values.iloc[3], errors="coerce") * 100.0),
                    "wind_mph": float(pd.to_numeric(values.iloc[6], errors="coerce") * MPS_TO_MPH),
                    "solar_radiation_mj_m2": float(pd.to_numeric(values.iloc[5], errors="coerce") * 60.0 / 1000.0),
                    "rain_mm": pd.to_numeric(values.iloc[9], errors="coerce"),
                    "etr_mm": pd.to_numeric(values.iloc[21], errors="coerce"),
                }
            )
    if not rows:
        raise ValueError(f"No LIRF weather rows found in {input_dir}")
    weather = pd.DataFrame(rows)
    return weather.groupby(["year", "date"], as_index=False).agg(
        temperature_f=("temperature_f", "mean"),
        humidity_pct=("humidity_pct", "mean"),
        wind_mph=("wind_mph", "mean"),
        solar_radiation_mj_m2=("solar_radiation_mj_m2", "sum"),
        rain_mm=("rain_mm", "sum"),
        etr_mm=("etr_mm", "first"),
    )


def _build_features(water: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    frame = water.merge(weather, on=["year", "date"], how="left", suffixes=("", "_weather"))
    for column, fallback in {"temperature_f": 72.0, "humidity_pct": 45.0, "wind_mph": 7.0, "solar_radiation_mj_m2": 22.0}.items():
        frame[column] = frame[column].fillna(fallback)
    frame["reference_et_in"] = (frame["etr_mm"].fillna(frame["etr_mm_weather"]) / MM_PER_INCH).fillna(0.2)
    frame["precipitation_in"] = (frame["precipitation_mm"].fillna(frame["rain_mm"]) / MM_PER_INCH).fillna(0.0)
    frame["cumulative_irrigation_24h"] = (frame["irrigation_mm"] / MM_PER_INCH).fillna(0.0).clip(lower=0.0)
    grouped = frame.groupby(["year", "treatment"], group_keys=False)
    for source, destination, aggregation in [
        ("temperature_f", "rolling_temp_mean", "mean"),
        ("humidity_pct", "rolling_humidity_mean", "mean"),
        ("solar_radiation_mj_m2", "rolling_solar_mean", "mean"),
        ("precipitation_in", "rolling_precip_in", "sum"),
        ("cumulative_irrigation_24h", "cumulative_irrigation_72h", "sum"),
    ]:
        frame[destination] = grouped[source].transform(lambda values: values.rolling(3, min_periods=1).agg(aggregation))
    frame["soil_moisture_lag_1"] = grouped["observed_vwc"].shift(1).fillna(frame["observed_vwc"])
    frame["soil_moisture_lag_2"] = grouped["observed_vwc"].shift(2).fillna(frame["soil_moisture_lag_1"])
    frame["soil_moisture_delta_1"] = frame["observed_vwc"] - frame["soil_moisture_lag_1"]
    frame["soil_moisture_delta_2"] = frame["soil_moisture_lag_1"] - frame["soil_moisture_lag_2"]
    frame["openet_monthly_et_in"] = frame.groupby(["year", "treatment", frame["date"].dt.month])["reference_et_in"].transform(lambda values: values.expanding(min_periods=1).mean())
    return frame


def _target_lookup(frame: pd.DataFrame) -> dict[tuple[int, int, pd.Timestamp], tuple[float, str]]:
    lookup: dict[tuple[int, int, pd.Timestamp], tuple[float, str]] = {}
    for (year, treatment), group in frame.groupby(["year", "treatment"]):
        observed = group.set_index("date")["observed_vwc"].sort_index()
        daily_index = pd.date_range(observed.index.min(), observed.index.max(), freq="D")
        interpolated = observed.reindex(daily_index).interpolate(method="time", limit_area="inside")
        observed_dates = set(observed.index)
        for date, value in interpolated.dropna().items():
            source = "root_zone_weighted_swc" if date in observed_dates else "root_zone_weighted_swc_daily_interpolated"
            lookup[(int(year), int(treatment), pd.Timestamp(date))] = (float(value), source)
    return lookup


def _build_rows(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = _target_lookup(frame)
    training_rows: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        horizon_targets = {horizon: lookup.get((int(row["year"]), int(row["treatment"]), pd.Timestamp(row["date"]) + pd.Timedelta(hours=horizon))) for horizon in (24, 48, 72)}
        if any(value is None for value in horizon_targets.values()):
            continue
        field_id = f"{SOURCE_ID}_{int(row['year'])}_trt_{int(row['treatment'])}"
        row_data: dict[str, Any] = {
            "source_id": SOURCE_ID, "field_id": field_id, "prediction_time": pd.Timestamp(row["date"]).isoformat(),
            "forecast_horizon_hours": 72, "temperature_f": row["temperature_f"], "humidity_pct": row["humidity_pct"], "wind_mph": row["wind_mph"],
            "precipitation_in": row["precipitation_in"], "solar_radiation_mj_m2": row["solar_radiation_mj_m2"], "rolling_temp_mean": row["rolling_temp_mean"],
            "rolling_humidity_mean": row["rolling_humidity_mean"], "rolling_precip_in": row["rolling_precip_in"], "rolling_solar_mean": row["rolling_solar_mean"],
            "current_soil_moisture": row["observed_vwc"], "soil_moisture_lag_1": row["soil_moisture_lag_1"], "soil_moisture_lag_2": row["soil_moisture_lag_2"],
            "soil_moisture_delta_1": row["soil_moisture_delta_1"], "soil_moisture_delta_2": row["soil_moisture_delta_2"], "moisture_min": min(row[f"swc_{index}"] for index, _, _ in DEPTH_LAYERS_CM if pd.notna(row[f"swc_{index}"])) / 100.0,
            "moisture_max": max(row[f"swc_{index}"] for index, _, _ in DEPTH_LAYERS_CM if pd.notna(row[f"swc_{index}"])) / 100.0,
            "moisture_mean": row["observed_vwc"], "moisture_spread": 0.0, "physical_sensor_count": 7, "pump_capacity_in_per_hour": DEFAULT_PUMP_CAPACITY_IN_PER_HOUR,
            "water_rights_schedule_count": 1, "energy_window_count": 1, "irrigation_type": DEFAULT_IRRIGATION_TYPE, "soil_texture": "loam", "infiltration_rate_in_per_hour": DEFAULT_INFILTRATION_RATE_IN_PER_HOUR,
            "slope_pct": DEFAULT_SLOPE_PCT, "drainage_class": DEFAULT_DRAINAGE_CLASS, "crop_type": "corn", "growth_stage": row["growth_stage"], "max_irrigation_volume_in": DEFAULT_MAX_IRRIGATION_VOLUME_IN,
            "field_area_acres": 0.09, "budget_dollars": DEFAULT_BUDGET_DOLLARS, "cumulative_irrigation_24h": row["cumulative_irrigation_24h"], "cumulative_irrigation_72h": row["cumulative_irrigation_72h"],
            "sensor_count": 7, "season_month": pd.Timestamp(row["date"]).month, "openet_monthly_et_in": row["openet_monthly_et_in"], "reference_et_in": row["reference_et_in"],
        }
        for horizon, target_info in horizon_targets.items():
            assert target_info is not None
            row_data[f"target_source_{horizon}h"] = target_info[1]
            row_data[f"target_moisture_{horizon}h"] = target_info[0]
            normalized_rows.append({"source_id": SOURCE_ID, "field_id": field_id, "prediction_time": row_data["prediction_time"], "horizon_hours": horizon, "observed_vwc": target_info[0], "target_source": target_info[1]})
        training_rows.append(row_data)
    return pd.DataFrame(training_rows, columns=TRAINING_COLUMNS), pd.DataFrame(normalized_rows)


def parse_usda_lirf_2008_2011(*, input_dir: str, output_path: str, normalized_output_path: str, report_output_path: str) -> dict[str, Any]:
    water = _read_treatment_workbooks(Path(input_dir))
    weather = _read_weather_workbooks(Path(input_dir))
    missing_weather_years = sorted(set(water["year"]) - set(weather["year"]))
    if missing_weather_years:
        raise ValueError(f"Historical LIRF weather for years {missing_weather_years} is required")
    features = _build_features(water, weather)
    training, normalized = _build_rows(features)
    if training.empty:
        raise ValueError("Historical LIRF parser produced no complete 24/48/72-hour examples")
    report = {"source_id": SOURCE_ID, "training_rows": len(training), "normalized_rows": len(normalized), "measured_label_counts": {f"{horizon}h": int((training[f"target_source_{horizon}h"] == "root_zone_weighted_swc").sum()) for horizon in (24, 48, 72)}, "years": sorted(training["prediction_time"].str[:4].astype(int).unique().tolist()), "usable_for_training": True}
    for path, data in [(Path(output_path), training), (Path(normalized_output_path), normalized)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False)
    report_path = Path(report_output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    args = parse_args()
    print(json.dumps(parse_usda_lirf_2008_2011(input_dir=args.input_dir, output_path=args.output, normalized_output_path=args.normalized_output, report_output_path=args.report_output), indent=2))


if __name__ == "__main__":
    main()
