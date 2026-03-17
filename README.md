# Helios

Helios is an irrigation decision-support prototype for evaluating a soil-moisture forecast workflow, a rule-based irrigation planner, and a farmer feedback loop. It is not a production agronomic advisor.

The current MVP combines:

- a FastAPI backend with request validation and SQLite persistence
- a LightGBM-based multi-output moisture forecast model
- a rule-based irrigation optimizer
- a static browser frontend with two explicit modes:
  - `demo` mode: browser-side prototype estimate only
  - `live` mode: real API calls to a hosted Helios backend

## Product Honesty

Helios should be treated as a prototype and operator aid only.

- The model is trained on synthetic data.
- Reference ET is approximate.
- Recommendation confidence is heuristic, not calibrated uncertainty.
- Regional feedback adjustment is simple weighting logic, not causal agronomy.
- Optimization is rule-based, not a certified irrigation solver.

## Architecture

```text
Static frontend
  -> config.js decides demo or live API mode
  -> demo mode uses browser-side fallback logic only
  -> live mode calls FastAPI endpoints

FastAPI backend
  -> Pydantic validation
  -> startup runtime + readiness checks
  -> cached model loading
  -> rule-based irrigation recommendation service
  -> SQLite persistence
  -> feedback aggregation + conservative adjustment layer
```

## Repository Layout

```text
helios/
  api/
  data/
  database/
  lib/
  models/
  optimizer/
  schemas/
  scripts/
  services/
  utils/
tests/
config.js
config.live.example.js
index.html
viewer.js
styles.css
```

## Local Setup

Use Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Train the Prototype Model

Generate synthetic training data:

```bash
python3 -m helios.scripts.generate_sample_data --rows 2500
```

Train the model:

```bash
python3 -m helios.models.train_model
```

Artifacts written:

- `artifacts/moisture_model.pkl`
- `artifacts/model_metadata.json`

## Run the Backend API

```bash
uvicorn helios.api.main:app --reload
```

Primary endpoints:

- `GET /livez`
- `GET /health`
- `POST /predict`
- `POST /api/feedback`
- `GET /api/feedback/nearby`

### Health Semantics

- `GET /livez` only checks that the process is running.
- `GET /health` is a readiness check.
- `/health` returns `200` when the database is ready and model artifacts were loaded.
- `/health` returns `503` when the app is in degraded mode, for example if the model artifacts are missing.

## Frontend Modes

The frontend reads `window.HELIOS_CONFIG` from `config.js`.

Default `config.js` in this repo:

```js
window.HELIOS_CONFIG = {
  mode: "demo",
  apiBaseUrl: "",
  disclaimer:
    "Demo mode uses browser-side prototype logic only. It does not call a live backend or store feedback in the project database.",
};
```

### Demo Mode

Use demo mode when publishing the static frontend without a backend.

- Recommendations are generated in the browser using fallback prototype logic.
- Feedback is not stored in SQLite.
- Nearby farm feedback is not applied.
- This is the only mode GitHub Pages can support by itself.

### Live Mode

Use live mode when you have a deployed Helios API.

Copy the example:

```bash
cp config.live.example.js config.js
```

Then edit `config.js`:

```js
window.HELIOS_CONFIG = {
  mode: "live",
  apiBaseUrl: "https://your-helios-api.example.com",
  disclaimer:
    "Live API mode sends requests to a hosted Helios backend. Recommendations are still prototype decision support and should be reviewed by the operator.",
};
```

In live mode:

- `viewer.js` calls the backend instead of assuming same-origin blindly
- nearby feedback can adjust recommendations conservatively
- farmer feedback is stored in the backend database

## CORS and Backend Config

Helios uses environment variables for backend runtime configuration.

```bash
export HELIOS_DATABASE_PATH=data/helios.db
export HELIOS_MODEL_PATH=artifacts/moisture_model.pkl
export HELIOS_METADATA_PATH=artifacts/model_metadata.json
export HELIOS_CORS_ALLOW_ORIGINS=https://your-pages-site.example.com
export HELIOS_RATE_LIMIT_WINDOW_SECONDS=60
export HELIOS_RATE_LIMIT_MAX_REQUESTS=60
export HELIOS_STRICT_MODEL_STARTUP=0
export HELIOS_LOG_LEVEL=INFO
```

Notes:

- `HELIOS_CORS_ALLOW_ORIGINS` is comma-separated.
- Default CORS is permissive for prototype use. Tighten it for real deployments.
- `HELIOS_STRICT_MODEL_STARTUP=1` makes the API fail fast if model artifacts are missing.

## Deployment

### Frontend-Only on GitHub Pages

GitHub Pages can serve the static frontend only. It cannot run the FastAPI backend.

For Pages deployment:

1. Keep `config.js` in `demo` mode.
2. Push the repo to GitHub.
3. Enable GitHub Pages from the repository root.
4. Use the published site as a prototype demo only.

This deployment does not provide:

- live `/predict` calls
- persisted feedback
- nearby feedback aggregation
- SQLite-backed history

### Backend API Deployment

Deploy the FastAPI app anywhere you can run Python, for example:

- a small VM
- Render/Fly.io/Railway style Python hosting
- a container platform

Minimum backend deployment steps:

1. install `requirements.txt`
2. generate synthetic data and train the model, or ship existing artifacts
3. set the environment variables above
4. run `uvicorn helios.api.main:app --host 0.0.0.0 --port 8000`

### Full-Stack Deployment Options

Pragmatic options for this repo:

1. GitHub Pages frontend in `live` mode + separately hosted FastAPI backend
2. Static frontend on any CDN/static host + separately hosted FastAPI backend
3. Single VM with static files served by a web server and FastAPI behind the same domain

What this repo does not provide:

- managed cloud infra templates
- background workers
- multi-tenant auth
- production agronomic validation

## Example API Request

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "field_id": "field-001",
    "farm_id": "farm-001",
    "forecast_horizon_hours": 72,
    "weather": {
      "temperature_c": 31.0,
      "humidity_pct": 38.0,
      "wind_mps": 3.8,
      "precipitation_mm": 0.0,
      "solar_radiation_mj_m2": 24.0,
      "forecast_horizon_hours": 72
    },
    "irrigation_system": {
      "irrigation_type": "pivot",
      "pump_capacity_mm_per_hour": 6.0,
      "water_rights_schedule": ["tonight", "tomorrow_morning"],
      "energy_price_window": ["tonight"]
    },
    "soil_moisture_readings": [
      {
        "timestamp": "2026-03-16T06:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.22
      },
      {
        "timestamp": "2026-03-16T12:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.21
      },
      {
        "timestamp": "2026-03-16T18:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.20
      }
    ],
    "soil_properties": {
      "soil_texture": "loam",
      "infiltration_rate_mm_per_hour": 12.0,
      "slope_pct": 2.5,
      "drainage_class": "moderate"
    },
    "crop": {
      "crop_type": "corn",
      "growth_stage": "flowering"
    },
    "operational": {
      "max_irrigation_volume_mm": 18.0,
      "field_area_ha": 24.0,
      "budget_dollars": 2800.0
    },
    "location_lat": 43.615,
    "location_lon": -116.202,
    "recent_irrigation_events": [
      {
        "timestamp": "2026-03-15T18:00:00Z",
        "applied_mm": 8.0
      }
    ]
  }'
```

## Feedback Adjustment Logic

Helios now adjusts recommendations only when enough comparable nearby feedback exists.

Comparability rules:

- exact crop type match
- exact soil texture match
- exact irrigation type match
- growth stage and season month reduce weight when they differ

Adjustment safety rules:

- no adjustment unless there are at least `4` nearby samples
- no adjustment unless at least `2` are strongly comparable
- no adjustment unless weighted evidence exceeds `2.5`
- strong positive feedback increases the base recommendation modestly
- weak feedback reduces the base recommendation conservatively

This is a simple prototype feedback loop, not a validated agronomic learning system.

## Tests

```bash
python3 -m pytest -q
```

Current test coverage focuses on:

- schema validation
- API route success and failure cases
- readiness and startup behavior
- recommendation service behavior
- feedback aggregation and adjustment logic

## Notebook

```bash
jupyter notebook notebooks/helios_demo.ipynb
```

Use the notebook for internal exploration only, not as evidence of production reliability.
