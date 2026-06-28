from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from helios.data.feature_engineering import TARGET_COLUMNS, build_training_features
from helios.scripts.download_public_datasets import find_dataset, load_registry
from helios.scripts.parse_usda_lirf_data import parse_usda_lirf
from helios.scripts.parse_usda_lirf_2008_2011 import parse_usda_lirf_2008_2011


def _write_usda_fixture(path: Path) -> None:
    dates = pd.date_range("2012-06-01", periods=5, freq="D")
    water_rows = []
    for index, date in enumerate(dates):
        water_rows.append(
            {
                "Year": 2012,
                "DOY": int(date.dayofyear),
                "Date": date,
                "Trt_code": 1,
                "Growth_stage": "V6" if index < 3 else "R1",
                "Nitrogen_Appl (kg/ha)": 42.0,
                "LAI": 1.2 + index,
                "Plant_height (cm)": 35.0 + index,
                "root_depth (cm)": 105.0,
                "canopy_cover": 10.0 + index,
                "SWC_15": 25.0 - index,
                "SWC_30": 24.0 - index,
                "SWC_60": 23.0 - index,
                "SWC_90": 22.0 - index,
                "SWC_120": 21.0 - index,
                "SWC_150": 20.0 - index,
                "SWC_200": 19.0 - index,
                "SWD_105": 10.0 + index,
                "SWD_RZ": 11.0 + index,
                "precip_gross (mm)": 2.54 if index == 0 else 0.0,
                "precip_eff (mm)": 2.0 if index == 0 else 0.0,
                "irr_gross (mm)": 5.08 if index == 1 else 0.0,
                "irr_eff (mm)": 4.0 if index == 1 else 0.0,
                "ETr (mm)": 2.54 * (index + 1),
                "Kcb_cc": 0.8,
                "Ks": 1.0,
                "deep_perc (mm)": 0.0,
                "Soil_Evap (mm)": 1.0,
                "ETc_WB (mm)": 5.0,
                "ETc_BREB (mm)": 5.1,
                "SWD_Pred_105": 12.0,
                "SWD_Pred_RZ": 13.0,
            }
        )

    weather_rows = []
    for date in dates:
        weather_rows.append(
            {
                "Year": 2012,
                "DOY": int(date.dayofyear),
                "TIMESTAMP": date + pd.Timedelta(hours=12),
                "AirTemp_C": 25.0,
                "RH_fraction": 0.45,
                "Vap_Press_kPa": 1.2,
                "HrlySolRad_kJ_m^2_min^1": 10.0,
                "WindSpeed_m_s^1": 3.0,
                "WindDir_Deg": 180.0,
                "WindDir_STDD_Deg": 5.0,
                "Rain-Tot": 0.0,
                "SoilTemp_5cm_C": 20.0,
                "SoilTemp_15cm_C": 18.0,
                "HWG_maxspeed_m_s^1": 4.0,
                "HWG_time": 1200,
                "HWG_Dir": 180.0,
                "BaPress_kPa": 86.0,
                "ETr": 0.0,
                "ETo": 0.0,
                "ETr-Daily": 2.54 * (date.day - dates[0].day + 1),
                "ETo-Daily": 5.0,
                "Rain-Daily": 0.0,
            }
        )

    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([{"ignored": "title"}]).to_excel(writer, sheet_name="Water Balance ET", index=False, header=False)
        pd.DataFrame(water_rows).to_excel(writer, sheet_name="Water Balance ET", index=False, startrow=1)
        pd.DataFrame(weather_rows).to_excel(writer, sheet_name="Weather data", index=False)


def _write_historical_lirf_fixture(root: Path) -> None:
    dates = pd.date_range("2008-06-01", periods=6, freq="D")
    water_header = [
        "DOY", "Precip", "Irrig", "unused", "0 - 15", "15 - 45", "45 - 75", "75 - 105",
        "105 - 135", "135 - 165", "165 - 200", "unused", "Growth Stage", "Root Depth",
        "Canopy Cover", "LAI", "Height", "N Applied", "unused", "ETr", "Kcb", "Ks", "ETcb",
        "Evap", "Deep Perc", "ETc", "BREB ETc", "unused", "Predicted 0 - 1050", "Measured 0 - 1050",
        "Predicted Active Root Zone", "Measured Active Root Zone",
    ]
    water_rows = [
        [
            int(date.dayofyear), 2.54 if index == 0 else 0.0, 5.08 if index == 1 else 0.0, None,
            25.0 - index, 24.0 - index, 23.0 - index, 22.0 - index, 21.0 - index, 20.0 - index,
            19.0 - index, None, "V6" if index < 3 else "R1", 105.0, 10.0 + index, 1.0 + index,
            35.0 + index, 148.0, None, 3.0 + index, 0.8, 1.0, 2.4, 0.5, 0.0, 2.9, 3.0, None,
            60.0, 59.0, 6.0, 5.0,
        ]
        for index, date in enumerate(dates)
    ]
    weather_header = [
        "Date/Time", "DOY", "AirTemp_Avg", "RH_Avg", "Vap_Press_Avg", "HrlySolRad_Avg", "WindSpeed",
        "WindDir", "WindDir_STDD", "Rain_Tot", "SoilTemp_5cm", "SoilTemp_15cm", "HWG_speed", "HWG_time",
        "HWG_dir", "BaPress_Avg", "AVPT_Avg", "SVPT_Avg", "ETr", "ETo", "FLAG", "Daily ETr", "Daily ETo",
    ]
    weather_rows = [
        [date + pd.Timedelta(hours=12), int(date.dayofyear), 25.0, 0.45, 1.2, 10.0, 3.0, 180.0, 5.0, 0.0,
         20.0, 18.0, 4.0, 1200, 180.0, 86.0, 1.0, 2.0, 3.0, 2.0, "GLY04", 3.0, 2.0]
        for date in dates
    ]
    with pd.ExcelWriter(root / "LIRF Maize 2008 r1.xlsx") as writer:
        for treatment in range(1, 7):
            rows = [[f"LIRF 2008 Water Balance Data"], ["Water Inputs"], water_header, ["units"]] + water_rows
            pd.DataFrame(rows).to_excel(writer, sheet_name=f"Tmnt{treatment}", index=False, header=False)
    with pd.ExcelWriter(root / "LIRF Weather 2008.xlsx") as writer:
        rows = [["LIRF 2008 Hourly Weather Data"], weather_header, ["units"]] + weather_rows
        pd.DataFrame(rows).to_excel(writer, sheet_name="Hourly", index=False, header=False)


def test_parse_historical_lirf_builds_three_horizons(tmp_path: Path) -> None:
    _write_historical_lirf_fixture(tmp_path)

    report = parse_usda_lirf_2008_2011(
        input_dir=str(tmp_path),
        output_path=str(tmp_path / "training.csv"),
        normalized_output_path=str(tmp_path / "normalized.csv"),
        report_output_path=str(tmp_path / "report.json"),
    )

    training = pd.read_csv(tmp_path / "training.csv")
    normalized = pd.read_csv(tmp_path / "normalized.csv")

    assert report["usable_for_training"] is True
    assert report["source_id"] == "usda_lirf_2008_2011"
    assert set(training["source_id"]) == {"usda_lirf_2008_2011"}
    assert set(normalized["horizon_hours"]) == {24, 48, 72}


def test_parse_historical_lirf_rejects_missing_year_weather(tmp_path: Path) -> None:
    _write_historical_lirf_fixture(tmp_path)
    shutil.copy(tmp_path / "LIRF Maize 2008 r1.xlsx", tmp_path / "LIRF Maize 2009 r1.xlsx")

    with pytest.raises(ValueError, match="weather for years"):
        parse_usda_lirf_2008_2011(
            input_dir=str(tmp_path),
            output_path=str(tmp_path / "training.csv"),
            normalized_output_path=str(tmp_path / "normalized.csv"),
            report_output_path=str(tmp_path / "report.json"),
        )


def test_public_dataset_registry_has_usda_provenance() -> None:
    registry = load_registry()
    usda = find_dataset(registry, "usda_lirf_2012_2013")

    assert usda["doi"] == "10.15482/USDA.ADC/1439968"
    assert usda["license"] == "U.S. Public Domain"
    assert usda["role"] == "training_candidate"
    assert {file_info["name"] for file_info in usda["raw_files"]} >= {
        "2012-2013_Maize_Compiled database 06012018.xlsx",
        "Data Description 06012018.xlsx",
        "Data_Dictionary_Water_Prod_2012.csv",
        "Plot map 2012 2013.pdf",
    }


def test_parse_usda_lirf_builds_horizons_without_future_features(tmp_path: Path) -> None:
    workbook = tmp_path / "usda_fixture.xlsx"
    training_output = tmp_path / "usda_training.csv"
    normalized_output = tmp_path / "usda_normalized.csv"
    report_output = tmp_path / "report.json"
    _write_usda_fixture(workbook)

    report = parse_usda_lirf(
        input_path=str(workbook),
        output_path=str(training_output),
        normalized_output_path=str(normalized_output),
        report_output_path=str(report_output),
    )

    training = pd.read_csv(training_output)
    normalized = pd.read_csv(normalized_output)
    report_from_disk = json.loads(report_output.read_text())

    assert report["usable_for_training"] is True
    assert report["measured_label_count"] > 0
    assert report["vwc_range"] == {"min": 0.1929, "max": 0.2329}
    assert report_from_disk["training_rows"] == len(training)
    assert set(normalized["horizon_hours"]) == {24, 48, 72}
    assert set(TARGET_COLUMNS).issubset(training.columns)
    assert {
        "source_id",
        "prediction_time",
        "target_source_24h",
        "target_source_48h",
        "target_source_72h",
    }.issubset(training.columns)
    assert len(training) == 2
    assert set(training["source_id"]) == {"usda_lirf_2012_2013"}
    assert set(training["target_source_24h"]) == {"root_zone_weighted_swc"}
    assert set(training["target_source_48h"]) == {"root_zone_weighted_swc"}
    assert set(training["target_source_72h"]) == {"root_zone_weighted_swc"}
    assert (
        int((training["target_source_48h"] == "root_zone_weighted_swc").sum())
        == int(
            (
                (normalized["horizon_hours"] == 48)
                & (normalized["target_source"] == "root_zone_weighted_swc")
            ).sum()
        )
    )

    first_row = training.iloc[0]
    assert first_row["source_id"] == "usda_lirf_2012_2013"
    assert first_row["current_soil_moisture"] == 0.2329
    assert first_row["target_moisture_24h"] == 0.2229
    assert first_row["target_moisture_48h"] == 0.2129
    assert first_row["target_moisture_72h"] == 0.2029
    assert first_row["target_source_24h"] == "root_zone_weighted_swc"
    assert first_row["target_source_48h"] == "root_zone_weighted_swc"
    assert first_row["target_source_72h"] == "root_zone_weighted_swc"
    assert first_row["precipitation_in"] == 0.1
    assert first_row["cumulative_irrigation_24h"] == 0.0
    assert first_row["reference_et_in"] == 0.1
    assert first_row["openet_monthly_et_in"] == 0.1

    second_row = training.iloc[1]
    assert second_row["reference_et_in"] == 0.2
    assert second_row["openet_monthly_et_in"] == 0.15

    normalized["feature_cutoff_at"] = pd.to_datetime(normalized["feature_cutoff_at"])
    normalized["label_time"] = pd.to_datetime(normalized["label_time"])
    assert (normalized["feature_cutoff_at"] < normalized["label_time"]).all()
    assert pd.to_datetime(training["prediction_time"], errors="coerce").notna().all()


def test_parse_usda_lirf_report_tracks_group_counts(tmp_path: Path) -> None:
    workbook = tmp_path / "usda_fixture.xlsx"
    training_output = tmp_path / "usda_training.csv"
    normalized_output = tmp_path / "usda_normalized.csv"
    _write_usda_fixture(workbook)

    report = parse_usda_lirf(
        input_path=str(workbook),
        output_path=str(training_output),
        normalized_output_path=str(normalized_output),
        report_output_path=None,
    )

    assert report["usable_for_training"] is True
    assert report["measured_label_count"] == 6
    assert report["year_treatment_training_counts"] == {"2012_trt_1": 2}
    assert report["year_treatment_measured_counts"] == {"2012_trt_1": 6}


def test_parse_usda_lirf_requires_water_balance_columns(tmp_path: Path) -> None:
    workbook = tmp_path / "missing_water_columns.xlsx"
    dates = pd.date_range("2012-06-01", periods=5, freq="D")

    water_rows = []
    for date in dates:
        water_rows.append(
            {
                "Year": 2012,
                "DOY": int(date.dayofyear),
                "Date": date,
                "Growth_stage": "V6",
                "root_depth (cm)": 105.0,
                "SWC_15": 25.0,
                "SWC_30": 24.0,
                "SWC_60": 23.0,
                "SWC_90": 22.0,
                "SWC_120": 21.0,
                "SWC_150": 20.0,
                "SWC_200": 19.0,
                "SWD_RZ": 11.0,
                "precip_gross (mm)": 0.0,
                "irr_gross (mm)": 0.0,
                "ETr (mm)": 2.54,
            }
        )

    weather_rows = []
    for date in dates:
        weather_rows.append(
            {
                "TIMESTAMP": date + pd.Timedelta(hours=12),
                "AirTemp_C": 25.0,
                "RH_fraction": 0.45,
                "WindSpeed_m_s^1": 3.0,
                "HrlySolRad_kJ_m^2_min^1": 10.0,
                "Rain-Tot": 0.0,
                "ETr-Daily": 2.54,
            }
        )

    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame([{"ignored": "title"}]).to_excel(writer, sheet_name="Water Balance ET", index=False, header=False)
        pd.DataFrame(water_rows).to_excel(writer, sheet_name="Water Balance ET", index=False, startrow=1)
        pd.DataFrame(weather_rows).to_excel(writer, sheet_name="Weather data", index=False)

    try:
        parse_usda_lirf(
            input_path=str(workbook),
            output_path=str(tmp_path / "training.csv"),
            normalized_output_path=str(tmp_path / "normalized.csv"),
            report_output_path=None,
        )
    except ValueError as exc:
        assert str(exc) == "USDA water balance sheet missing required columns: Trt_code"
    else:
        raise AssertionError("expected missing water balance column error")


def test_parse_usda_lirf_requires_weather_columns(tmp_path: Path) -> None:
    workbook = tmp_path / "missing_weather_columns.xlsx"
    dates = pd.date_range("2012-06-01", periods=5, freq="D")
    _write_usda_fixture(workbook)
    water_balance = pd.read_excel(workbook, sheet_name="Water Balance ET", header=1)

    weather = pd.DataFrame(
        {
            "TIMESTAMP": dates + pd.Timedelta(hours=12),
            "AirTemp_C": [25.0] * len(dates),
            "RH_fraction": [0.45] * len(dates),
            "WindSpeed_m_s^1": [3.0] * len(dates),
            "Rain-Tot": [0.0] * len(dates),
            "ETr-Daily": [2.54] * len(dates),
        }
    )
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame([{"ignored": "title"}]).to_excel(writer, sheet_name="Water Balance ET", index=False, header=False)
        water_balance.to_excel(writer, sheet_name="Water Balance ET", index=False, startrow=1)
        weather.to_excel(writer, sheet_name="Weather data", index=False)

    try:
        parse_usda_lirf(
            input_path=str(workbook),
            output_path=str(tmp_path / "training.csv"),
            normalized_output_path=str(tmp_path / "normalized.csv"),
            report_output_path=None,
        )
    except ValueError as exc:
        assert str(exc) == "USDA weather sheet missing required columns: HrlySolRad_kJ_m^2_min^1"
    else:
        raise AssertionError("expected missing weather column error")


def test_usda_training_output_matches_feature_schema(tmp_path: Path) -> None:
    workbook = tmp_path / "usda_fixture.xlsx"
    training_output = tmp_path / "usda_training.csv"
    normalized_output = tmp_path / "usda_normalized.csv"
    _write_usda_fixture(workbook)

    parse_usda_lirf(
        input_path=str(workbook),
        output_path=str(training_output),
        normalized_output_path=str(normalized_output),
        report_output_path=None,
    )
    training = pd.read_csv(training_output)

    features, targets = build_training_features(training)

    assert not features.empty
    assert list(targets.columns) == TARGET_COLUMNS
    assert training["openet_monthly_et_in"].min() > 0
    assert training["growth_stage"].isin(["vegetative", "flowering"]).all()
