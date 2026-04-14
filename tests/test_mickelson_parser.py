from __future__ import annotations

from pathlib import Path

import pandas as pd

from helios.scripts.parse_mickelson_data import (
    _build_acreage_lookup,
    _build_weekly_et_lookup,
    _build_weekly_flow_lookup,
    _build_weekly_lookup_from_totals,
)


def test_rain_lookup_uses_location_and_week_dates() -> None:
    rain_totals = pd.DataFrame(
        [
            {"Location": "Imperial", pd.Timestamp("2024-07-01"): 0.25, pd.Timestamp("2024-07-08"): 0.10},
            {"Location": "Hamer", pd.Timestamp("2024-07-01"): 0.05, pd.Timestamp("2024-07-08"): 0.00},
        ]
    )

    lookup = _build_weekly_lookup_from_totals(rain_totals, id_column="Location")

    assert lookup[("imperial", pd.Timestamp("2024-07-01"))] == 0.25
    assert lookup[("hamer", pd.Timestamp("2024-07-08"))] == 0.0


def test_acreage_lookup_uses_farm_and_field() -> None:
    acre_feet = pd.DataFrame(
        [
            {"Column5": "Imperial ", "FIELD": "I-14", "Acres": 626.0},
            {"Column5": "Hamer", "FIELD": "H-2", "Acres": 145.5},
        ]
    )

    lookup = _build_acreage_lookup(acre_feet)

    assert lookup[("imperial", "i-14")] == 626.0
    assert lookup[("hamer", "h-2")] == 145.5


def test_weekly_flow_lookup_reads_week_sheets(tmp_path: Path) -> None:
    workbook_path = tmp_path / "weekly_flow.xlsx"
    with pd.ExcelWriter(workbook_path) as writer:
        pd.DataFrame(
            [
                {
                    "Location": "I-14",
                    " start date": "2024-07-01",
                    " flow gpm": 1350,
                }
            ]
        ).to_excel(writer, sheet_name="Week 9", index=False)
        pd.DataFrame([{"ignored": 1}]).to_excel(writer, sheet_name="Data", index=False)

    lookup = _build_weekly_flow_lookup(pd.ExcelFile(workbook_path))

    assert lookup[("i-14", pd.Timestamp("2024-07-01"))] == 1350.0


def test_weekly_et_lookup_prefers_crop_specific_column_with_etr_fallback() -> None:
    hamer = pd.DataFrame(
        [
            {"DATE": "2024-07-01", "ETr": 0.30, "SGRN": 0.24, "WGRN": 0.0, "POTA": 0.0},
            {"DATE": "2024-07-02", "ETr": 0.32, "SGRN": 0.26, "WGRN": 0.0, "POTA": 0.0},
            {"DATE": "2024-07-03", "ETr": 0.31, "SGRN": None, "WGRN": 0.0, "POTA": 0.0},
        ]
    )

    lookup = _build_weekly_et_lookup(
        hamer_df=hamer,
        week_dates=[pd.Timestamp("2024-07-01")],
        crop_raw="Spring Grain",
    )

    assert round(lookup[pd.Timestamp("2024-07-01")], 2) == 0.81
