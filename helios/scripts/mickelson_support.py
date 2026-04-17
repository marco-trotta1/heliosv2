from __future__ import annotations

import datetime as _dt

import pandas as pd

from helios.scripts.training_shared import CROP_KC, INCHES_PER_MM, IRRIGATION_EFFICIENCY, load_openet_monthly_et


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
DRAINAGE_FACTOR = {
    "moderate": 1.0,
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
GALLONS_PER_ACRE_INCH = 27154.0


def strip_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: (col.strip() if isinstance(col, str) else col) for col in df.columns}
    return df.rename(columns=renamed)


def normalize_key(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip().lower()


def infer_growth_stage(week_index: int) -> str:
    if week_index <= 3:
        return "emergence"
    if week_index <= 8:
        return "vegetative"
    if week_index <= 13:
        return "flowering"
    if week_index <= 17:
        return "grain_fill"
    return "maturity"


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def build_week_dates(data_df: pd.DataFrame) -> tuple[list[pd.Timestamp], dict[pd.Timestamp, object]]:
    week_columns_raw = [col for col in data_df.columns if isinstance(col, (pd.Timestamp, _dt.datetime))]
    if not week_columns_raw:
        raise ValueError("Data sheet has no weekly date columns")
    week_dates = sorted(pd.Timestamp(col) for col in week_columns_raw)
    week_column_lookup = {pd.Timestamp(col): col for col in week_columns_raw}
    return week_dates, week_column_lookup


def build_weekly_lookup_from_totals(df: pd.DataFrame, id_column: str) -> dict[tuple[str, pd.Timestamp], float]:
    totals = strip_columns(df).copy()
    week_dates = [pd.Timestamp(col) for col in totals.columns if isinstance(col, (pd.Timestamp, _dt.datetime))]
    lookup: dict[tuple[str, pd.Timestamp], float] = {}

    for _, row in totals.iterrows():
        entity_key = normalize_key(row.get(id_column))
        if not entity_key:
            continue
        for week_date in week_dates:
            value = pd.to_numeric(row.get(week_date), errors="coerce")
            if pd.isna(value):
                continue
            lookup[(entity_key, pd.Timestamp(week_date))] = float(value)

    return lookup


def build_acreage_lookup(acre_feet_df: pd.DataFrame) -> dict[tuple[str, str], float]:
    acreage = strip_columns(acre_feet_df).copy()
    lookup: dict[tuple[str, str], float] = {}

    for _, row in acreage.iterrows():
        farm_key = normalize_key(row.get("Column5"))
        field_key = normalize_key(row.get("FIELD"))
        acres = pd.to_numeric(row.get("Acres"), errors="coerce")
        if not farm_key or not field_key or pd.isna(acres) or float(acres) <= 0:
            continue
        lookup[(farm_key, field_key)] = float(acres)

    return lookup


def build_weekly_flow_lookup(excel: pd.ExcelFile) -> dict[tuple[str, pd.Timestamp], float]:
    lookup: dict[tuple[str, pd.Timestamp], float] = {}

    for sheet_name in excel.sheet_names:
        if not sheet_name.startswith("Week "):
            continue
        weekly = strip_columns(pd.read_excel(excel, sheet_name=sheet_name))
        if weekly.empty or "Location" not in weekly.columns or "flow gpm" not in weekly.columns:
            continue
        for _, row in weekly.iterrows():
            location_key = normalize_key(row.get("Location"))
            week_start = pd.to_datetime(row.get("start date"), errors="coerce")
            flow_gpm = pd.to_numeric(row.get("flow gpm"), errors="coerce")
            if not location_key or pd.isna(week_start) or pd.isna(flow_gpm) or float(flow_gpm) <= 0:
                continue
            lookup[(location_key, pd.Timestamp(week_start).normalize())] = float(flow_gpm)

    return lookup


def build_weekly_et_lookup(
    hamer_df: pd.DataFrame,
    week_dates: list[pd.Timestamp],
    crop_raw: str,
) -> dict[pd.Timestamp, float]:
    hamer = strip_columns(hamer_df).copy()
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


def pump_capacity_from_flow_gpm(flow_gpm: float | None, field_area_acres: float) -> float:
    if flow_gpm is None or field_area_acres <= 0:
        return DEFAULT_PUMP_CAPACITY_IN_PER_HOUR
    gallons_per_hour = flow_gpm * 60.0
    return max(0.01, gallons_per_hour / (GALLONS_PER_ACRE_INCH * field_area_acres))


def daily_moisture_step(
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
    return clamp(moisture - et_depletion + precip_gain + irrigation_gain, MOISTURE_MIN, MOISTURE_MAX)


def simulate_weekly_start_state(
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
        state = daily_moisture_step(
            state,
            daily_precip_in=daily_precip_in,
            daily_irrigation_in=daily_irrigation_in,
            daily_reference_et_in=daily_reference_et_in,
            growth_stage=growth_stage,
        )
    return state
