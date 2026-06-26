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
   ```

   A ready response has `"ready": true` and `"model_loaded": true`. If it is degraded, inspect the `issues` array. A missing model artifact prevents `/predict` from serving recommendations.

4. Send `POST /predict` from your application or an API client. Include every required request field listed in `helios/schemas/inputs.py`.

   The request must include at least three readings for each sensor. Each reading timestamp must be timezone-aware, and every reading must use the request's `field_id`. You may supply all five weather values. If any are absent, Helios fills missing values from NOAA.

5. Inspect the response before acting on it.

   Check `decision`, `recommended_amount_in`, `timing_window`, and `predicted_moisture`. Also check `et_source`, `confidence_caveat`, `recommendation_adjustment`, and `validation_evidence`; these describe whether fallback ET or feedback affected the recommendation.

## Run a clean field-test configuration

Set validation mode when you need to isolate the model-and-rule recommendation from stored feedback:

```bash
HELIOS_VALIDATION_MODE=1 uvicorn helios.api.main:app --reload
```

In this mode, `recommendation_adjustment.adjustment_factor` remains `1.0` and the validation-evidence packet explicitly reports that feedback was disabled.

## Verify the installation

Run the repository test suite:

```bash
python3 -m pytest -q
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

When `HELIOS_API_KEY` is configured, include `Authorization: Bearer <key>`. A `429` means the in-memory request limit was reached; wait for its configured window or adjust the local rate-limit settings for development.

## Related documentation

- [How Helios works](helios-architecture.md)
- [Environment template](../.env.example)
