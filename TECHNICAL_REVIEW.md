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
- **Fixed rate limiter bug**: the rate limiter was being created fresh on every request due to a `@property` that re-instantiated `InMemoryRateLimiter`. It is now created once in `build_runtime()` and stored as a dataclass field.
- Added readiness-aware `/health` and simple `/livez`.
- Stopped leaking raw exception text to clients; API errors now return structured error bodies.
- Added conservative comparability filters to the feedback logic: crop, soil texture, irrigation type, plus growth-stage and seasonal weighting.
- **Decoupled persistence from prediction**: `RecommendationService.predict()` no longer calls `save_prediction_run()`. Persistence happens in the route handler after a successful API response, with errors caught and logged so a database failure does not block the recommendation.
- **Feature alignment warnings**: `prepare_feature_matrix` now logs structured warnings when inference features contain columns unseen during training, or when training columns are absent from the inference matrix, rather than silently filling zeros.
- Added a feedback-table migration path for older local SQLite databases.
- Added pytest coverage for schemas, routes, runtime behavior, service behavior, and feedback logic.
- **Swapped gradient boosting library**: replaced LightGBM with XGBoost (`XGBRegressor`, `reg:squarederror`). `early_stopping_rounds` is passed as a `fit()` argument. `requirements.txt` updated accordingly (`xgboost>=2.0,<3.0`).
- **Implemented FAO-56 Penman-Monteith ET₀**: replaced the approximate heuristic in `helios/utils/evapotranspiration.py` with the full FAO-56 Penman-Monteith equation (psychrometric constant, Tetens saturation vapor pressure, VPD, delta curve, Rn ≈ 0.77 × Rs). The identical formula is used in `src/domain.js` so demo-mode and live-API results share the same physics.
- **Soil water balance training targets**: `generate_sample_data.py` now derives 24 h / 48 h / 72 h moisture targets from a soil water balance simulation (ET depletion adjusted by crop Kc, drainage class, and irrigation efficiency) instead of hand-tuned heuristics.
- **Model provenance hashing**: `train_model.py` computes SHA-256 hashes of the trained `.pkl` artifact and the training data CSV and writes them into `model_metadata.json`. The hashes are logged at startup and surfaced in `/health`.
- **API key authentication**: `POST /predict` and `POST /api/feedback` accept an `Authorization: Bearer <key>` header. When `HELIOS_API_KEY` is unset, the check is skipped so demo mode works without credentials.
- **Request ID middleware**: every request receives a `uuid4` request ID, stored in `request.state.request_id` and returned in the `X-Request-Id` response header.
- **Structured logging**: route handlers log prediction outcomes with `latency_ms`, `decision`, `confidence_score`, `request_id`, and `field_id` using `logger.info(..., extra={...})`.
- **Split frontend into ES modules**: the 2 000+ line `viewer.js` monolith is replaced by six modules under `src/` (`constants.js`, `domain.js`, `state.js`, `api.js`, `ui.js`, `validation.js`). `viewer.js` is now a 5-line entry point.
- **Client-side input validation**: `src/validation.js` exports `validateForm` which runs synchronously on form submit and returns a human-readable error string before any API call is made.
- Rewrote the README so deployment instructions match the actual product.

## What Remains Risky

- The predictive model is still trained on synthetic data.
- Recommendation confidence is heuristic, not calibrated against field outcomes.
- Regional feedback adjustment is still a simple weighted heuristic, not a validated agronomic learning system.
- Rate limiting is in-memory only — resets on restart and is not sufficient for a serious public deployment behind multiple processes.
- SQLite is fine for prototype persistence but not ideal for concurrent production traffic.
- API key authentication is a single shared secret. There is no per-tenant key management or operator audit trail.

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
export HELIOS_API_KEY=your-secret-key   # omit to disable auth
```

5. Run:

```bash
uvicorn helios.api.main:app --host 0.0.0.0 --port 8000
```

6. Switch the frontend to `live` mode using [config.live.example.js](/Users/marcotrotta/Desktop/Irrigant%20Helios/config.live.example.js) as the template.
