from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from helios.models.train_model import train_model
from helios.scripts.generate_sample_data import generate_sample_data
from helios.scripts.parse_usda_lirf_data import parse_usda_lirf
from helios.scripts.rebuild_training_bundle import rebuild_training_bundle
from tests.test_usda_lirf_ingestion import _write_usda_fixture


def _write_minimal_mickelson_workbook(path: Path) -> None:
    week_dates = [
        pd.Timestamp("2024-07-01"),
        pd.Timestamp("2024-07-08"),
        pd.Timestamp("2024-07-15"),
    ]

    data = pd.DataFrame(
        [
            {
                "Field ": "I-14",
                "Farm": "Imperial",
                "Group ": 1,
                "Manager": "Brent",
                "Location ": "Imperial",
                "Crop": "Spring Grain",
                "Variety": "Test",
                week_dates[0]: 1.4,
                week_dates[1]: 1.2,
                week_dates[2]: 0.9,
                " YTD ": 3.5,
            }
        ]
    )
    rain_totals = pd.DataFrame(
        [
            {
                "Location": "Imperial",
                "YTD Total": 0.6,
                week_dates[0]: 0.25,
                week_dates[1]: 0.10,
                week_dates[2]: 0.00,
            }
        ]
    )
    acre_feet = pd.DataFrame(
        [
            {
                "Column5": "Imperial ",
                "FIELD": "I-14",
                "YTD": 22.27,
                "Average inches": 20.73,
                "Feet": 1.7275,
                "Acres": 626.0,
            }
        ]
    )
    hamer = pd.DataFrame(
        [
            {"DATE ": pd.Timestamp("2024-07-01"), "ETr  ": "0.30", "WGRN ": 0.20, "SGRN ": 0.24, "POTA ": 0.18},
            {"DATE ": pd.Timestamp("2024-07-02"), "ETr  ": "0.32", "WGRN ": 0.22, "SGRN ": 0.26, "POTA ": 0.19},
            {"DATE ": pd.Timestamp("2024-07-03"), "ETr  ": "0.31", "WGRN ": 0.21, "SGRN ": 0.25, "POTA ": 0.18},
            {"DATE ": pd.Timestamp("2024-07-08"), "ETr  ": "0.33", "WGRN ": 0.23, "SGRN ": 0.27, "POTA ": 0.20},
            {"DATE ": pd.Timestamp("2024-07-09"), "ETr  ": "0.32", "WGRN ": 0.22, "SGRN ": 0.26, "POTA ": 0.19},
            {"DATE ": pd.Timestamp("2024-07-10"), "ETr  ": "0.31", "WGRN ": 0.21, "SGRN ": 0.25, "POTA ": 0.18},
            {"DATE ": pd.Timestamp("2024-07-15"), "ETr  ": "0.34", "WGRN ": 0.24, "SGRN ": 0.28, "POTA ": 0.21},
            {"DATE ": pd.Timestamp("2024-07-16"), "ETr  ": "0.35", "WGRN ": 0.25, "SGRN ": 0.29, "POTA ": 0.22},
            {"DATE ": pd.Timestamp("2024-07-17"), "ETr  ": "0.33", "WGRN ": 0.23, "SGRN ": 0.27, "POTA ": 0.20},
        ]
    )
    week_sheet = pd.DataFrame(
        [
            {
                "Location": "I-14",
                " ac-in week": 1.4,
                " ac-in to date": 1.4,
                " start date": "2024-07-01",
                " end date": "2024-07-07",
                " flow gpm": 1350,
            }
        ]
    )

    with pd.ExcelWriter(path) as writer:
        data.to_excel(writer, sheet_name="Data", index=False)
        rain_totals.to_excel(writer, sheet_name="Rain Totals", index=False)
        acre_feet.to_excel(writer, sheet_name="ACRE FEET", index=False)
        hamer.to_excel(writer, sheet_name="Hamer Agrimet", index=False)
        week_sheet.to_excel(writer, sheet_name="Week 9", index=False)


def test_rebuild_training_bundle_creates_combined_dataset_and_metadata(tmp_path: Path) -> None:
    workbook_path = tmp_path / "Water_usage_2024.xlsx"
    openet_csv = tmp_path / "openet.csv"
    sample_output = tmp_path / "sample.csv"
    mickelson_output = tmp_path / "mickelson.csv"
    combined_output = tmp_path / "combined.csv"
    model_path = tmp_path / "artifacts" / "moisture_model.pkl"
    metadata_path = tmp_path / "artifacts" / "model_metadata.json"

    _write_minimal_mickelson_workbook(workbook_path)
    pd.DataFrame(
        [
            {"date": "2024-07-01", "openet_et_mm": 85.0},
            {"date": "2024-08-01", "openet_et_mm": 70.0},
        ]
    ).to_csv(openet_csv, index=False)

    result = rebuild_training_bundle(
        mickelson_workbook=str(workbook_path),
        openet_csv=str(openet_csv),
        synthetic_rows=30,
        seed=42,
        sample_output=str(sample_output),
        mickelson_output=str(mickelson_output),
        usda_lirf_csv=None,
        combined_output=str(combined_output),
        model_path=str(model_path),
        metadata_path=str(metadata_path),
        n_estimators=10,
        learning_rate=0.1,
    )

    assert sample_output.exists()
    assert mickelson_output.exists()
    assert combined_output.exists()
    assert model_path.exists()
    assert metadata_path.exists()
    assert result["mickelson_rows"] >= 3
    assert result["combined_rows"] == result["synthetic_rows"] + result["mickelson_rows"]

    metadata = json.loads(metadata_path.read_text())
    combined = pd.read_csv(combined_output)
    assert metadata["training_rows"] == len(combined)
    assert metadata["training_data_hash"]
    assert metadata["model_hash"]
    assert combined["openet_monthly_et_in"].min() > 0

    # Feature importances are logged per target so we can see which features the model uses.
    importances = metadata["feature_importances"]
    assert set(importances) == {"target_moisture_24h", "target_moisture_48h", "target_moisture_72h"}
    for target_scores in importances.values():
        assert target_scores  # non-empty mapping of feature -> importance
        assert all(isinstance(value, (int, float)) for value in target_scores.values())


def test_rebuild_training_bundle_records_source_provenance_with_usda(tmp_path: Path) -> None:
    workbook_path = tmp_path / "Water_usage_2024.xlsx"
    openet_csv = tmp_path / "openet.csv"
    usda_workbook = tmp_path / "usda_fixture.xlsx"
    usda_training_output = tmp_path / "usda_training.csv"
    usda_normalized_output = tmp_path / "usda_normalized.csv"
    sample_output = tmp_path / "sample.csv"
    mickelson_output = tmp_path / "mickelson.csv"
    combined_output = tmp_path / "combined.csv"
    model_path = tmp_path / "artifacts" / "moisture_model.pkl"
    metadata_path = tmp_path / "artifacts" / "model_metadata.json"

    _write_minimal_mickelson_workbook(workbook_path)
    _write_usda_fixture(usda_workbook)
    parse_usda_lirf(
        input_path=str(usda_workbook),
        output_path=str(usda_training_output),
        normalized_output_path=str(usda_normalized_output),
        report_output_path=None,
    )
    pd.DataFrame(
        [
            {"date": "2024-07-01", "openet_et_mm": 85.0},
            {"date": "2024-08-01", "openet_et_mm": 70.0},
        ]
    ).to_csv(openet_csv, index=False)

    rebuild_training_bundle(
        mickelson_workbook=str(workbook_path),
        openet_csv=str(openet_csv),
        synthetic_rows=30,
        seed=42,
        sample_output=str(sample_output),
        mickelson_output=str(mickelson_output),
        usda_lirf_csv=str(usda_training_output),
        combined_output=str(combined_output),
        model_path=str(model_path),
        metadata_path=str(metadata_path),
        n_estimators=10,
        learning_rate=0.1,
    )

    combined = pd.read_csv(combined_output)
    metadata = json.loads(metadata_path.read_text())

    assert combined["field_id"].notna().all()
    assert combined["source_id"].notna().all()
    assert set(combined["source_id"]) == {"synthetic", "mickelson", "usda_lirf_2012_2013"}

    provenance = metadata["training_provenance"]
    assert provenance["source_counts"]["synthetic"] == 30
    assert provenance["source_counts"]["mickelson"] >= 3
    assert provenance["source_counts"]["usda_lirf_2012_2013"] == 2
    assert provenance["maize_years"] == [2012]
    assert provenance["maize_treatments"] == [1]
    assert provenance["maize_label_counts"] == {"measured": 6, "interpolated": 0}
    assert provenance["maize_dataset"]["doi"] == "10.15482/USDA.ADC/1439968"
    assert provenance["maize_dataset"]["license"] == "U.S. Public Domain"
    assert provenance["contains_private_local_derivatives"] is True


def test_generate_sample_data_uses_openet_climatology_without_csv(tmp_path: Path) -> None:
    output_path = tmp_path / "sample.csv"

    frame = generate_sample_data(
        rows=30,
        output_path=str(output_path),
        seed=42,
        openet_csv=None,
    )

    assert output_path.exists()
    assert frame["openet_monthly_et_in"].min() > 0


def test_train_model_rejects_missing_openet_feature(tmp_path: Path) -> None:
    data_path = tmp_path / "training.csv"
    pd.DataFrame(
        [
            {
                "target_moisture_24h": 0.2,
                "target_moisture_48h": 0.19,
                "target_moisture_72h": 0.18,
            }
        ]
    ).to_csv(data_path, index=False)

    with pytest.raises(ValueError, match="openet_monthly_et_in"):
        train_model(
            data_path=str(data_path),
            model_path=str(tmp_path / "model.pkl"),
            metadata_path=str(tmp_path / "metadata.json"),
            n_estimators=1,
            learning_rate=0.1,
        )


def test_train_model_rejects_all_zero_openet_feature(tmp_path: Path) -> None:
    data_path = tmp_path / "training.csv"
    frame = generate_sample_data(
        rows=30,
        output_path=str(data_path),
        seed=42,
        openet_csv=None,
    )
    frame["openet_monthly_et_in"] = 0.0
    frame.to_csv(data_path, index=False)

    with pytest.raises(ValueError, match="all zero"):
        train_model(
            data_path=str(data_path),
            model_path=str(tmp_path / "model.pkl"),
            metadata_path=str(tmp_path / "metadata.json"),
            n_estimators=1,
            learning_rate=0.1,
        )
