# Public Dataset Ingestion

Helios now has a reproducible path for preparing public irrigation and soil-water datasets without committing raw data.

## USDA LIRF 2012-2013

Status: evaluated training candidate. The current artifact-backed verdict is `CANDIDATE_FAIL`, so the shipped model artifacts were not replaced.

Source:

- Ag Data Commons: https://agdatacommons.nal.usda.gov/articles/dataset/USDA-ARS_Colorado_Maize_Water_Productivity_Dataset_2012-2013/24662391
- Figshare API: https://api.figshare.com/v2/articles/24662391
- DOI: `10.15482/USDA.ADC/1439968`
- License: U.S. Public Domain

Why it is useful:

- Controlled maize irrigation treatments.
- Daily measured soil water content by depth (`SWC_15` through `SWC_200`).
- Irrigation, precipitation, ET, crop stage, LAI, canopy cover, and root depth.
- Hourly weather that can be aggregated into past-context features.

The parser converts depth-specific SWC percentages into root-zone weighted VWC. It keeps measured SWC dates as prediction origins, then creates daily D+1, D+2, and D+3 labels for the current Helios targets. When the target day does not have a direct SWC measurement, the label is daily time-interpolated inside the same treatment series and marked with `target_source=root_zone_weighted_swc_daily_interpolated` in the normalized output:

- `target_moisture_24h`
- `target_moisture_48h`
- `target_moisture_72h`

The raw downloads and generated CSVs live under `data/public/`, which is ignored by git.

The current processed outputs are:

- Wide training CSV: 897 complete 24 h / 48 h / 72 h examples.
- Normalized examples: 2691 horizon rows.
- Measured labels: 588.
- Interpolated labels: 2103.

The wide CSV now includes `source_id`, `prediction_time`, and per-horizon `target_source_*` columns so evaluation can separate measured labels from daily interpolations without joining to the normalized file.

## Morris Nebraska CRNS

Status: evaluation pending.

Source:

- Paper: https://www.mdpi.com/1424-8220/24/13/4094
- Repository: https://github.com/tanessamorris/Effect-of-biomass-water-dynamics-in-cosmic-ray-neutron-sensor-observations
- License: CC0-1.0

This dataset includes TDR SWC, precipitation, irrigation, field logs, biomass water equivalent, neutron counts, and CSP1/CSP2/CSP3 site data. It should start as a validation/generalization source because CRNS is area-integrated and the study objective is biomass correction, not irrigation decision labels. Training use should require source-aware splits by site/year and an explicit decision about weighting area-integrated CRNS or TDR rows against point-probe Helios targets.

## Commands

Download USDA files:

```bash
python3 -m helios.scripts.download_public_datasets --source usda_lirf_2012_2013
```

Normalize USDA rows and create a Helios training CSV:

```bash
python3 -m helios.scripts.parse_usda_lirf_data \
  --input "data/public/usda_lirf_2012_2013/raw/2012-2013_Maize_Compiled database 06012018.xlsx" \
  --output data/public/usda_lirf_2012_2013/processed/usda_lirf_training_data.csv \
  --normalized-output data/public/usda_lirf_2012_2013/processed/usda_lirf_normalized_examples.csv
```

Build candidate and baseline artifacts for evaluation:

```bash
python3 -m helios.scripts.rebuild_training_bundle \
  --mickelson-workbook data/Water_usage_2024.xlsx \
  --openet-csv data/openet_sample.csv \
  --usda-lirf-csv data/public/usda_lirf_2012_2013/processed/usda_lirf_training_data.csv \
  --synthetic-rows 5000 \
  --sample-output data/candidates/maize/sample_training_data.csv \
  --mickelson-output data/candidates/maize/mickelson_training_data.csv \
  --combined-output data/combined_candidate.csv \
  --model-path artifacts/candidates/maize/moisture_model.pkl \
  --metadata-path artifacts/candidates/maize/model_metadata.json

python3 -m helios.scripts.rebuild_training_bundle \
  --mickelson-workbook data/Water_usage_2024.xlsx \
  --openet-csv data/openet_sample.csv \
  --synthetic-rows 5000 \
  --sample-output data/candidates/baseline/sample_training_data.csv \
  --mickelson-output data/candidates/baseline/mickelson_training_data.csv \
  --combined-output data/combined_baseline.csv \
  --model-path artifacts/candidates/baseline/moisture_model.pkl \
  --metadata-path artifacts/candidates/baseline/model_metadata.json
```

Run the candidate gate:

```bash
python3 -m helios.scripts.evaluate_maize_baseline \
  --base-csv data/combined_baseline.csv \
  --maize-csv data/public/usda_lirf_2012_2013/processed/usda_lirf_training_data.csv \
  --out-json artifacts/maize_baseline_eval.json \
  --out-md artifacts/maize_baseline_eval.md
```

Run tests:

```bash
python3 -m pytest -q
```

## Limitations

- USDA LIRF is daily treatment-level research-station data, not real-time grower probe telemetry.
- The parser treats each daily row as an end-of-day prediction origin; same-day daily weather, ET, irrigation, and precipitation are past context, while D+1/D+2/D+3 SWC values are labels.
- The training output uses VWC as the target. Soil-water deficit is preserved only as source context in the normalized data path, not as the primary model target.
- Some USDA labels are daily interpolations between measured SWC dates because the source measures soil water periodically. The normalized output records whether each horizon label is direct or interpolated.
- Soil texture is mapped to Helios's current `loam` category until a stronger soil-texture mapping is added from companion soil data.
- Morris/Nebraska is not yet wired into training; it needs a separate normalizer and a source-aware validation split.

## Current Training Status

USDA rows are usable as prepared candidate rows after download and normalization. They must remain candidate-only unless `artifacts/maize_baseline_eval.json` reports `CANDIDATE_PASS`.

The current evaluation showed strong GroupKFold corn-holdout improvement and base no-regression pass, but failed the cross-season LOYO persistence gate at 72 h. Because the verdict is `CANDIDATE_FAIL`, `artifacts/moisture_model.pkl` and `artifacts/model_metadata.json` remain unchanged.

The 2008-2011 LIRF dataset is available as a follow-up acquisition target; see `docs/maize-2008-2011-acquisition-audit.md`.
