# How to run Helios locally

Run the FastAPI backend, check that its model is ready, and send a prediction request without committing or sharing private inputs.

## Prerequisites

- Python 3.11 or later
- a local model artifact and matching metadata at the paths configured in `.env.example`
- optionally, an `OPENET_API_KEY` for live monthly ET enrichment

Do not place raw farm data, credentials, or personal information in request examples, commits, or documentation.

## Steps

1. Create an isolated environment and install the development dependencies.

   ```bash
   rm -rf .venv  # optional cleanup if this checkout has an old Python 3.9 environment
   python3 -m venv .venv
   source .venv/bin/activate
   python3 -m pip install --upgrade pip
   python3 -m pip install -r requirements-dev.txt
   ```

2. Copy the environment template and set only the local settings you need. At a minimum, ensure `HELIOS_MODEL_PATH` and `HELIOS_METADATA_PATH` point to a matching artifact pair. Helios reads process environment variables, so export the file before starting the API.

   ```bash
   cp .env.example .env
   set -a
   source .env
   set +a
   ```

   `OPENET_API_KEY` is optional. Without it, Helios returns an ET fallback and lowers the heuristic confidence score.

3. Start the API and check its readiness.

   ```bash
   uvicorn helios.api.main:app --reload
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/version
   ```

   A ready `/health` response has `"ready": true` and `"model_loaded": true`. `/version` reports the model artifact hash, training date, API version, and validation-mode state. If health is degraded, inspect the `issues` array. A missing model artifact prevents `/predict` from serving recommendations.

4. Send `POST /predict` from your application or an API client. Include every required request field listed in `helios/schemas/inputs.py`.

   The request must include at least three readings for each sensor. Each reading timestamp must be timezone-aware, and every reading must use the request's `field_id`. You may supply all five weather values. If any are absent, Helios fills missing values from NOAA.

5. Inspect the response before acting on it.

   Check `decision`, `recommended_amount_in`, and `timing_window`. Also check `et_source`, `confidence_caveat`, `recommendation_adjustment`, and `validation_evidence`; these describe whether fallback ET or feedback affected the recommendation, whether the latest candidate verdict blocks promotion, and whether operator review is required.

6. If an operator reviewed a recommendation, your application can record that review with `POST /api/acknowledgements`. When `HELIOS_API_KEY` is set, this endpoint uses the same `Authorization: Bearer <key>` rule as `/predict` and `/api/feedback`.

## Run a clean field-test configuration

Set validation mode when you need to isolate the model-and-rule recommendation from stored feedback:

```bash
HELIOS_VALIDATION_MODE=1 uvicorn helios.api.main:app --reload
```

In this mode, `recommendation_adjustment.adjustment_factor` remains `1.0` and the validation-evidence packet explicitly reports that feedback was disabled.

For a supervised pilot, keep validation mode enabled, log observed VWC outcomes after each recommendation, and treat Helios as experimental decision support only. High sensor variability should pause urgent farmer-facing action until an operator reviews the field context.

## Verify the installation

Run the repository test suite:

```bash
python3 -m pytest -q
```

Validate the committed model artifact metadata contract:

```bash
python3 -m helios.scripts.check_model_artifact_contract
```

The tests cover request validation, feature/schema compatibility, model-output bounds, ET fallback behavior, recommendation caps, feedback safeguards, and API routes.

## Troubleshooting

### `/health` reports a degraded service

The model artifact or metadata may be missing, unreadable, or incompatible with the runtime feature schema. Ensure both files exist and came from the same training run. Set `HELIOS_STRICT_MODEL_STARTUP=1` to make this startup failure explicit instead of running in degraded mode.

### `/predict` returns `422`

The request failed schema validation. Common causes are fewer than three readings for a sensor, naive or future timestamps, a field mismatch between the request and readings, invalid categorical values, or a weather horizon that differs from the request horizon.

### The response uses fallback ET

`et_source: "openet-fallback"` means a live OpenET value was unavailable. Confirm that `OPENET_API_KEY` is set and valid, then retry. The API intentionally continues with the fallback so a transient enrichment failure does not prevent an operator from receiving a recommendation.

### `/predict` returns `401` or `429`

When `HELIOS_API_KEY` is configured, include `Authorization: Bearer <key>` for `/predict`, `/api/acknowledgements`, and `/api/feedback`. A `429` means the in-memory request limit was reached; wait for its configured window or adjust the local rate-limit settings for development.

## Broad-release blockers

These local steps do not make Helios broadly farmer-ready. Broader release still requires measured Idaho validation, calibrated uncertainty, tenant isolation, external rate limiting, production observability, and retention/backup policy.

## Related documentation

- [How Helios works](helios-architecture.md)
- [Environment template](../.env.example)
