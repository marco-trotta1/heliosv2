# Technical Review

## What Was Broken

- The repo documentation implied GitHub Pages could run the full product, even though the real app depends on backend endpoints like `/predict`.
- The static frontend assumed same-origin API paths, which breaks when the frontend is hosted separately from the backend.
- The backend loaded model artifacts during request handling instead of treating model readiness as startup/runtime state.
- `GET /health` behaved like an aliveness check instead of a readiness check.
- Raw internal exceptions were exposed to API clients.
- The feedback adjustment logic was too permissive and could overreact to weak anecdotal input.
- There was no meaningful automated test baseline.

## What Changed

- Added explicit frontend runtime config with `demo` and `live` modes via [config.js](/Users/marcotrotta/Desktop/Irrigant%20Helios/config.js).
- Made GitHub Pages-safe behavior the default by keeping static hosting in browser-only demo mode.
- Added `config.live.example.js` to show how to point the frontend at a hosted backend.
- Added backend CORS configuration and basic in-memory rate limiting.
- Refactored FastAPI startup to build a runtime once, initialize the database, and preload the model service.
- Added readiness-aware `/health` and simple `/livez`.
- Stopped leaking raw exception text to clients; API errors now return structured error bodies.
- Added conservative comparability filters to the feedback logic: crop, soil texture, irrigation type, plus growth-stage and seasonal weighting.
- Added a feedback-table migration path for older local SQLite databases.
- Added pytest coverage for schemas, routes, runtime behavior, service behavior, and feedback logic.
- Rewrote the README so deployment instructions match the actual product.

## What Remains Risky

- The predictive model is still trained on synthetic data.
- ET and confidence remain heuristic.
- Regional feedback adjustment is still a simple weighted heuristic, not a validated agronomic learning system.
- Rate limiting is in-memory only, so it is not sufficient for a serious public deployment.
- SQLite is fine for prototype persistence but not ideal for concurrent production traffic.
- There is still no authentication, tenancy separation, or operator audit trail.

## How To Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m helios.scripts.generate_sample_data --rows 2500
python3 -m helios.models.train_model
uvicorn helios.api.main:app --reload
```

Optional frontend testing:

- open `index.html` directly for demo mode
- or serve the repo statically and switch `config.js` to `live` mode for backend calls

Run tests:

```bash
python3 -m pytest -q
```

## How To Deploy Frontend-Only

GitHub Pages can only host the static frontend.

1. Keep [config.js](/Users/marcotrotta/Desktop/Irrigant%20Helios/config.js) in `demo` mode.
2. Enable GitHub Pages from the repository root.
3. Publish the site as a prototype demo only.

In this mode:

- recommendations are browser-side fallback estimates
- feedback is not stored in SQLite
- nearby feedback is not applied

## How To Deploy With Backend

1. Deploy the FastAPI app on any Python-capable host.
2. Install `requirements.txt`.
3. Train or ship the model artifacts.
4. Set backend env vars such as:

```bash
export HELIOS_CORS_ALLOW_ORIGINS=https://your-frontend.example.com
export HELIOS_DATABASE_PATH=data/helios.db
export HELIOS_MODEL_PATH=artifacts/moisture_model.pkl
export HELIOS_METADATA_PATH=artifacts/model_metadata.json
```

5. Run:

```bash
uvicorn helios.api.main:app --host 0.0.0.0 --port 8000
```

6. Switch the frontend to `live` mode using [config.live.example.js](/Users/marcotrotta/Desktop/Irrigant%20Helios/config.live.example.js) as the template.
