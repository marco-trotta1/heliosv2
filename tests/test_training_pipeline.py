from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from helios.scripts.rebuild_training_bundle import rebuild_training_bundle


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
