# Helios

Helios is an early-stage irrigation decision-support system for reviewing soil-moisture forecasts, generating a conservative irrigation recommendation, and capturing operator feedback. It is a prototype workflow, not a production agronomic controller.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
uvicorn helios.api.main:app --reload
```

Open `index.html` directly for the static demo frontend, or point `config.js` at a deployed backend for live API mode.

## Project Status

Helios should be treated as a prototype decision-support tool and operator aid only.

- The model is trained on synthetic data.
- Reference ET is approximate.
- Recommendation confidence is heuristic, not calibrated.
- The optimizer is rule-based, not a certified irrigation solver.
- Feedback adjustment is conservative weighting logic, not causal agronomy.

## Why It Matters

Irrigation decisions combine weather pressure, soil conditions, equipment limits, and operational timing. Helios packages that workflow into a reviewable prototype with:

- a static frontend that can run in demo mode or call a live API
- a FastAPI backend with validation, health checks, and SQLite persistence
- a trained moisture-forecast model plus rule-based recommendation logic
- a lightweight farmer feedback loop for nearby recommendation adjustment

## Architecture Overview

```text
Static frontend
  -> config.js selects demo or live mode
  -> demo mode runs browser-side fallback logic only
  -> live mode calls the FastAPI backend

FastAPI backend
  -> request validation via Pydantic
  -> startup/runtime health checks
  -> cached model artifact loading
  -> recommendation service + rule-based optimizer
  -> SQLite-backed feedback persistence
```

## Repository Layout

```text
helios/
  api/           FastAPI app, routes, runtime wiring
  database/      SQLite helpers
  lib/           Feedback and aggregation logic
  models/        Training and model loading
  optimizer/     Rule-based irrigation planning
  schemas/       Request and response models
  services/      Recommendation orchestration
  utils/         Shared domain utilities
tests/           Backend and schema tests
index.html       Static frontend entrypoint
viewer.js        Frontend application logic
styles.css       Frontend styles
```

## Local Setup

Use Python 3.11 for the cleanest match with CI.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt
```

### Runtime dependencies

- `requirements.txt`: backend and application runtime packages
- `requirements-dev.txt`: runtime packages plus test and notebook tooling

If you only need the backend runtime without tests or notebook tooling:

```bash
python3 -m pip install -r requirements.txt
```

## Running the Backend

```bash
uvicorn helios.api.main:app --reload
```

Primary endpoints:

- `GET /livez`
- `GET /health`
- `POST /predict`
- `POST /api/feedback`
- `GET /api/feedback/nearby`

### Health semantics

- `/livez` checks whether the process is running.
- `/health` is the readiness endpoint.
- `/health` returns `200` when the database is ready and model artifacts loaded.
- `/health` returns `503` when the app is degraded, such as when database initialization fails or model artifacts are missing.

## API Examples

Minimal liveness check:

```bash
curl http://127.0.0.1:8000/livez
```

Readiness check:

```bash
curl http://127.0.0.1:8000/health
```

Prediction request:

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
        "timestamp": "2026-03-16T18:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.22
      },
      {
        "timestamp": "2026-03-17T00:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.21
      },
      {
        "timestamp": "2026-03-17T06:00:00Z",
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
        "timestamp": "2026-03-16T06:00:00Z",
        "applied_mm": 8.0
      }
    ]
  }'
```

Feedback submission:

```bash
curl -X POST http://127.0.0.1:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "farm_id": "farm-001",
    "timestamp": "2026-03-18T18:00:00Z",
    "crop_type": "corn",
    "soil_texture": "loam",
    "irrigation_type": "pivot",
    "growth_stage": "flowering",
    "recommendation_type": "irrigation",
    "recommendation_value": "12.5",
    "outcome": "SUCCESS",
    "yield_delta": 4.0,
    "notes": "Recommendation performed as expected.",
    "location_lat": 43.615,
    "location_lon": -116.202
  }'
```

## Frontend Deployment Modes

The frontend reads `window.HELIOS_CONFIG` from `config.js`.

### Demo / static mode

This repo ships with `config.js` in demo mode:

```js
window.HELIOS_CONFIG = {
  mode: "demo",
  apiBaseUrl: "",
  disclaimer:
    "Demo mode uses browser-side prototype logic only. It does not call a live backend or store feedback in the project database.",
};
```

Use this mode for GitHub Pages or local static previews. Recommendations are computed in the browser and feedback is not persisted.

### Live / backend mode

Copy the provided example and point it at a deployed API:

```bash
cp config.live.example.js config.js
```

```js
window.HELIOS_CONFIG = {
  mode: "live",
  apiBaseUrl: "https://your-helios-api.example.com",
  disclaimer:
    "Live API mode sends requests to a hosted Helios backend. Recommendations are still prototype decision support and should be reviewed by the operator.",
};
```

In live mode the frontend calls the backend, feedback is stored in SQLite, and nearby feedback can modestly adjust recommendations.

## Environment Variables

Backend configuration is driven by environment variables. See [.env.example](.env.example) for a safe template.

Key variables:

- `HELIOS_DATABASE_PATH`
- `HELIOS_MODEL_PATH`
- `HELIOS_METADATA_PATH`
- `HELIOS_CORS_ALLOW_ORIGINS`
- `HELIOS_RATE_LIMIT_WINDOW_SECONDS`
- `HELIOS_RATE_LIMIT_MAX_REQUESTS`
- `HELIOS_STRICT_MODEL_STARTUP`
- `HELIOS_LOG_LEVEL`

Notes:

- `HELIOS_CORS_ALLOW_ORIGINS` is comma-separated.
- `HELIOS_STRICT_MODEL_STARTUP=1` makes the API fail fast when model artifacts are missing.

## Training the Prototype Model

Generate synthetic sample data:

```bash
python3 -m helios.scripts.generate_sample_data --rows 2500
```

Train the model:

```bash
python3 -m helios.models.train_model
```

Artifacts are written to:

- `artifacts/moisture_model.pkl`
- `artifacts/model_metadata.json`

## Tests

The test suite lives under `tests/`.

Run the local test suite with:

```bash
python3 -m pytest
```

GitHub Actions uses the same command on pushes and pull requests.

## Deployment Notes

### Static frontend only

GitHub Pages can host the frontend in demo mode, but it cannot run the FastAPI backend. That means:

- no live `/predict` requests
- no persisted feedback
- no nearby feedback aggregation
- no backend health or readiness behavior

### Full stack

Pragmatic deployment patterns for this repo:

1. GitHub Pages or another static host for the frontend in `live` mode
2. A separately hosted FastAPI backend on a VM, container platform, or Python app host
3. A single VM serving static files and the API under one domain

## Current Limitations

- No production agronomic validation
- No authentication or tenancy
- No managed infrastructure templates
- No background job system
- SQLite is used for prototype persistence only
- Browser demo mode intentionally diverges from the live backend path

## Roadmap

Near-term improvements that fit the current prototype:

1. Better artifact/version management for trained models
2. Containerized local dev and deployment examples
3. Basic observability around request volume, degraded startup, and feedback ingestion

## License

This project is source-available under BSL 1.1. You can view, fork, and modify it for personal, educational, evaluation, and non-production use. Commercial or production use requires separate permission.

See [LICENSE](LICENSE) for the full Business Source License 1.1 terms.
