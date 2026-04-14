# Helios

[![CI](https://github.com/marco-trotta1/heliosv2/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/marco-trotta1/heliosv2/actions/workflows/ci.yml)

Helios is an irrigation decision-support prototype for Idaho row crop operations. It helps growers review water stress risk, likely near-term soil moisture, and an operator-constrained irrigation recommendation. It is not an autonomous controller.

The current repo combines:

- a static frontend that can run in demo mode or call a live backend
- a FastAPI backend with health checks, validation, and SQLite persistence
- a moisture-forecast model trained on mixed synthetic + Mickelson-derived field history
- ET-aware recommendation logic with hybrid OpenET runtime enrichment and fallback
- a lightweight nearby-feedback loop that can modestly adjust recommendations

## Current Status

Helios is still a prototype operator aid.

- The model is not trained on true measured future soil-moisture labels.
- Mickelson Farms data improves realism, but many agronomic features still require conservative defaults.
- Recommendation confidence is heuristic, not a calibrated uncertainty estimate.
- The irrigation optimizer is rule-based, not a certified scheduling engine.
- SQLite, in-memory rate limiting, and single-key auth are prototype choices, not production infrastructure.

That said, this repo is no longer purely synthetic. The shipped artifact is trained from a combined dataset that blends:

- synthetic water-balance rows generated from FAO-56 ET and irrigation constraints
- Mickelson irrigation history parsed from the local workbook and enriched with rain, acreage, flow, and crop-aware Agrimet ET

## How Helios Works

At prediction time Helios:

1. Accepts soil moisture readings, crop, soil, irrigation, operational, and location inputs.
2. Uses caller-supplied weather or backfills missing weather from NOAA.
3. Enriches the inference row with monthly ET:
   - live OpenET monthly point ET when `OPENET_API_KEY` is available
   - in-process cache reuse for repeated requests in the same area/month
   - fallback to the baked-in monthly ET lookup when OpenET is unavailable
4. Forecasts soil moisture at 24 h / 48 h / 72 h.
5. Generates a conservative irrigation recommendation subject to pump, budget, infiltration, and water-window limits.
6. Optionally nudges the recommendation using comparable nearby feedback already stored in SQLite.

The external API remains:

- `GET /livez`
- `GET /health`
- `POST /predict`
- `POST /api/feedback`
- `GET /api/feedback/nearby`

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
uvicorn helios.api.main:app --reload
```

Open `index.html` directly for the static frontend, or point `config.js` at a deployed backend for live API mode.

## Repository Layout

```text
helios/
  api/           FastAPI app, routes, runtime wiring
  data/          feature/inference helpers and OpenET enrichment tools
  database/      SQLite helpers
  lib/           Feedback and aggregation logic
  models/        Training and model loading
  optimizer/     Rule-based irrigation planning
  schemas/       Request and response models
  scripts/       Data-prep, parsing, and rebuild scripts
  services/      Recommendation orchestration
  utils/         Shared ET, weather, and OpenET utilities
src/
  constants.js
  domain.js
  state.js
  api.js
  ui.js
  validation.js
tests/
index.html
viewer.js
styles.css
```

## Environment Variables

See [.env.example](.env.example) for the full template.

Key runtime settings:

- `HELIOS_DATABASE_PATH`
- `HELIOS_MODEL_PATH`
- `HELIOS_METADATA_PATH`
- `HELIOS_CORS_ALLOW_ORIGINS`
- `HELIOS_RATE_LIMIT_WINDOW_SECONDS`
- `HELIOS_RATE_LIMIT_MAX_REQUESTS`
- `HELIOS_STRICT_MODEL_STARTUP`
- `HELIOS_LOG_LEVEL`
- `HELIOS_API_KEY`
- `OPENET_API_KEY`

Notes:

- `HELIOS_API_KEY` protects `POST /predict` and `POST /api/feedback` when set.
- `OPENET_API_KEY` enables live monthly OpenET enrichment during `/predict`.
- When `OPENET_API_KEY` is missing or OpenET fails, runtime inference falls back to the baked-in monthly ET lookup so predictions still succeed.

## Data Policy

This repo intentionally separates public code/artifacts from private farm data.

- `artifacts/` contains the public model artifact and metadata used by the app.
- Raw Mickelson workbook files are local/private inputs.
- Derived `data/*.csv` files are kept out of the public repo.
- Public commits should contain code, tests, docs, and refreshed artifacts/metadata, not raw or derived farm datasets.

If you are rebuilding locally, expect to supply your own local copies of:

- `data/Water_usage_2024.xlsx`
- an OpenET monthly CSV such as `data/openet_sample.csv`

## Rebuilding Training Data And Artifacts

The reproducible local rebuild flow is:

1. Parse Mickelson irrigation history from the workbook.
2. Attach OpenET monthly ET where available.
3. Regenerate synthetic rows with the same monthly ET context.
4. Build the combined training dataset.
5. Retrain the model artifact and metadata.

Run the bundled rebuild script:

```bash
python3 -m helios.scripts.rebuild_training_bundle \
  --mickelson-workbook data/Water_usage_2024.xlsx \
  --openet-csv data/openet_sample.csv \
  --synthetic-rows 5000
```

Outputs written locally:

- `data/sample_training_data.csv`
- `data/mickelson_training_data.csv`
- `data/combined_training_data.csv`
- `artifacts/moisture_model.pkl`
- `artifacts/model_metadata.json`

### Mickelson parsing details

The Mickelson parser uses the local workbook to extract:

- weekly irrigation history from `Data`
- weekly rain totals from `Rain Totals`
- acreage from `ACRE FEET`
- weekly flow where available from `Week *` sheets
- crop-aware Agrimet ET from `Hamer Agrimet`

Where the workbook has no direct source, Helios still uses conservative defaults for soil class, drainage, slope, and probe-derived moisture features.

### OpenET usage

OpenET is used in two different places:

- training/data prep:
  - synthetic rows can ingest local monthly OpenET CSV data
  - Mickelson rows can attach monthly OpenET values by month when a CSV is provided
- runtime prediction:
  - live monthly OpenET point ET is fetched for the month of the latest soil-moisture reading
  - the result is cached by rounded lat/lon and month
  - fallback values are used when no key is present or the API is unavailable

## Model Notes

The forecast model is an XGBoost multi-output regressor that predicts volumetric soil moisture at 24 h, 48 h, and 72 h.

The current feature space includes:

- recent soil moisture levels and deltas
- weather and ET features
- irrigation-system and operational constraints
- crop and growth stage
- month/season context
- monthly ET context from OpenET-style features

The target-generation logic is still physics-informed and heuristic rather than true sensor-ground-truth supervision. Mickelson history improves realism, but Helios should still be treated as a prototype agronomic aid.

## Running Tests

```bash
python3 -m pytest -q
```

The test suite covers:

- schemas and API routes
- OpenET integration and runtime fallback behavior
- ET calculations
- recommendation service behavior
- feedback logic
- model range regression guards
- Mickelson parsing helpers
- rebuild-pipeline smoke coverage

## Frontend Modes

The frontend reads `window.HELIOS_CONFIG` from `config.js`.

### Demo mode

Use this for GitHub Pages or static previews. Recommendations are browser-side only and no backend persistence occurs.

### Live mode

Point the frontend at a deployed FastAPI backend. In this mode:

- `/predict` calls the real backend
- feedback is stored in SQLite
- nearby feedback can adjust recommendations
- runtime OpenET enrichment is available when `OPENET_API_KEY` is configured

## Limitations

- No true field-validated soil-moisture ground-truth training labels yet
- No field-polygon OpenET or higher-frequency remote-sensing integration yet
- No production auth, tenant isolation, or external rate-limit store
- No production deployment template or managed observability stack
- The browser demo path is still an approximation of the backend path

## License

This project is source-available under BSL 1.1. You can view, fork, and modify it for personal, educational, evaluation, and non-production use. Commercial or production use requires separate permission.

See [LICENSE](LICENSE) for the full Business Source License 1.1 terms.
