# Historical LIRF Candidate Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate the public 2008–2011 USDA LIRF maize release as a leakage-safe Helios candidate without replacing the shipped model unless it passes every gate.

**Architecture:** Keep the 2012–2013 LIRF parser unchanged because the historical release uses one workbook per season and six treatment tabs with multi-row headers. Add one focused parser that emits the same wide and normalized schemas, then use the existing maize evaluator for GroupKFold, LOYO, base no-regression, and transfer-proxy gates.

**Tech Stack:** Python 3, pandas, pytest, existing XGBoost evaluation harness.

## Global Constraints

- Raw public workbooks remain under ignored `data/candidates/`; never commit raw or derived data.
- Use only information available at each prediction origin; 24/48/72-hour labels are held out.
- Preserve the shipped artifacts unless the existing evaluator emits `CANDIDATE_PASS`.
- Treat measured labels separately from interpolated labels in all evidence.

---

### Task 1: Parse historical LIRF treatment workbooks

**Files:**
- Create: `helios/scripts/parse_usda_lirf_2008_2011.py`
- Modify: `tests/test_usda_lirf_ingestion.py`

**Interfaces:**
- Consumes: a directory containing `LIRF Maize 2008 r1.xlsx` through `LIRF Maize 2011 r1.xlsx` and matching weather workbooks.
- Produces: `parse_usda_lirf_2008_2011(input_dir, output_path, normalized_output_path, report_output_path) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing test**

```python
def test_parse_historical_lirf_builds_three_horizons(tmp_path: Path) -> None:
    _write_historical_lirf_fixture(tmp_path)
    report = parse_usda_lirf_2008_2011(
        input_dir=str(tmp_path),
        output_path=str(tmp_path / "training.csv"),
        normalized_output_path=str(tmp_path / "normalized.csv"),
        report_output_path=str(tmp_path / "report.json"),
    )
    assert report["usable_for_training"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_usda_lirf_ingestion.py::test_parse_historical_lirf_builds_three_horizons -q`

Expected: import failure because `parse_usda_lirf_2008_2011` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def parse_usda_lirf_2008_2011(*, input_dir: str, output_path: str,
                              normalized_output_path: str, report_output_path: str) -> dict[str, Any]:
    water = _read_treatment_workbooks(Path(input_dir))
    weather = _read_weather_workbooks(Path(input_dir))
    features = _build_features(water, weather)
    training, normalized = _build_rows(features)
    return _write_outputs(training, normalized, output_path, normalized_output_path, report_output_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_usda_lirf_ingestion.py::test_parse_historical_lirf_builds_three_horizons -q`

Expected: PASS.

### Task 2: Run the candidate gate and record its verdict

**Files:**
- Create: `artifacts/historical_lirf_maize_eval.json` locally only
- Create: `artifacts/historical_lirf_maize_eval.md` locally only

**Interfaces:**
- Consumes: the parsed historical candidate and `data/combined_baseline.csv`.
- Produces: existing `evaluate_maize_baseline(...)` verdict with all gate metrics.

- [ ] **Step 1: Parse the downloaded source data**

Run: `python3 -m helios.scripts.parse_usda_lirf_2008_2011 --input-dir data/candidates/usda_lirf_2008_2011/raw --output data/candidates/usda_lirf_2008_2011/processed/training.csv --normalized-output data/candidates/usda_lirf_2008_2011/processed/normalized.csv --report-output data/candidates/usda_lirf_2008_2011/processed/report.json`

- [ ] **Step 2: Evaluate without changing shipped artifacts**

Run: `python3 -m helios.scripts.evaluate_maize_baseline --base-csv data/combined_baseline.csv --maize-csv data/candidates/usda_lirf_2008_2011/processed/training.csv --out-json artifacts/historical_lirf_maize_eval.json --out-md artifacts/historical_lirf_maize_eval.md`

- [ ] **Step 3: Verify the conclusion**

Check: `verdict` and every LOYO measured-only persistence result in the JSON. A result is not a ship candidate unless every gate passes.

