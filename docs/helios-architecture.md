# How Helios Works

Helios is a decision-support prototype. It produces a short-range soil-moisture forecast and a constrained irrigation recommendation for an operator to review. It does not control irrigation equipment and does not treat its confidence score as calibrated uncertainty.

This document explains the software and model flow. It deliberately excludes raw data, farm-specific information, credentials, and personal identifiers.

## System overview

```text
Browser UI
    |
    | POST /predict
    v
FastAPI route
    |-- validates the request
    |-- uses supplied weather or fills missing weather from NOAA
    v
Recommendation service
    |-- resolves monthly ET from OpenET, cache, or fallback values
    |-- turns readings and constraints into one feature row
    |-- runs the moisture-forecast model
    |-- estimates stress and applies irrigation rules
    |-- optionally applies a small, guarded feedback adjustment
    v
Structured recommendation response
    |
    `-- best-effort persistence to SQLite
```

The backend is started by `helios.api.main`. At startup, it initializes SQLite, checks that the model metadata's feature-column list exactly matches the runtime feature builder, and loads the trained model. A missing model keeps the service in a degraded state; `/health` reports that condition and `/predict` returns `503`.

## A prediction request

`POST /predict` accepts:

- a field identifier and location;
- at least three timestamped volumetric-water-content readings for every sensor included in the request;
- crop, soil, irrigation-system, and operating constraints;
- recent irrigation events; and
- weather values for a 24-, 48-, or 72-hour horizon.

All sensor-reading timestamps must be timezone-aware, must not be materially in the future, and must belong to the request's field. If the caller provides all required weather values, the API uses them. Otherwise it fetches NOAA's hourly forecast, then preserves any weather values the caller did supply. NOAA does not provide the required solar-radiation value, so the fallback uses a monthly Idaho climatology estimate.

See [How to run Helios locally](how-to-run-helios.md) for setup and API use.

## Inference feature construction

`helios.data.ingestion.request_to_feature_frame` converts a request into one row of model inputs.

For each sensor, Helios uses its latest three readings to derive current moisture, two lags, and two changes. The driest current zone drives the forecast. With three or more sensors, a median-absolute-deviation check removes a clear outlier before selecting that zone, so a single stuck-low probe is less likely to cause unnecessary irrigation. The feature row also retains the minimum, maximum, mean, spread, and physical count across sensors.

The row includes weather, recent irrigation totals, crop and soil classes, irrigation and operating limits, season month, and monthly ET. `helios.data.feature_engineering` adds reference ET when it is not already present and one-hot encodes the categorical classes. At prediction time, the feature matrix is ordered to the model metadata. Missing trained columns are filled with zero and unseen input columns are ignored with a warning; the startup schema check prevents a shipped artifact with a different expected feature order from being served.

## Monthly ET enrichment

`helios.utils.openet.resolve_monthly_et_in` resolves a daily-average ET value for the month containing the latest reading:

1. With an `OPENET_API_KEY`, it requests the OpenET monthly point series.
2. Repeated requests for the same rounded location and month use an in-process cache.
3. If the key is absent, the request fails, or no matching month is returned, Helios uses a baked-in monthly fallback.

The response exposes `et_source` and `et_is_fallback`. Fallback ET lowers the recommendation confidence because it is not field-specific.

## Moisture forecast model

The training entry point is `helios.models.train_model`. It trains three XGBoost regressors, wrapped as a `MultiOutputRegressor`, for volumetric soil moisture at 24, 48, and 72 hours. The prediction endpoint returns all three horizons regardless of the request horizon.

The persisted model bundle contains the estimator and metadata. Metadata records the ordered feature list, target columns, model configuration, cross-validation results, validation RMSE, feature importances, hashes, training row count, and source/provenance summaries. It is used both to align inference features and to expose non-sensitive model evidence in responses.

Predictions are clipped to physically plausible texture-specific envelopes before they reach the recommendation layer. Unknown texture falls back to a wider default envelope. This is a guardrail against out-of-distribution feature combinations producing impossible moisture values; it is not a substitute for field validation.

## Training and candidate evaluation

The rebuild entry point is `helios.scripts.rebuild_training_bundle`. It:

1. generates the configured synthetic training rows;
2. parses any locally supplied training input;
3. optionally adds a separately prepared public-data candidate;
4. checks that every combined row has a source and field identifier;
5. trains with `field_id` as the grouping column; and
6. writes model metadata and provenance summaries.

Raw inputs and derived training tables are intentionally outside this document and should remain outside public documentation.

Training requires a non-empty, non-negative `openet_monthly_et_in` feature so the model sees the same ET context that runtime inference supplies. The normal rebuild path uses `GroupKFold`, so a field identifier cannot appear in both train and held-out groups in one fold. Training metadata contains fold-level metrics and feature importances, but those metrics are not proof of production accuracy.

Candidate data must pass the repository's candidate-evaluation gates before it replaces the shipped artifact. Those gates compare against a baseline, check measured-label performance and bias, require performance better than persistence, guard against regression on the base data, and record provenance. A candidate failure leaves the current artifact in place.

## Recommendation pipeline

After forecasting, `RecommendationService` derives a heuristic stress probability from the 48-hour forecast, the texture dry threshold, estimated reference ET, and crop growth stage. Forecast precipitation is already an input to the moisture model, so the stress and optimizer layers do not subtract it a second time.

`helios.optimizer.irrigation_optimizer.generate_irrigation_plan` uses the 48-hour prediction first. It recommends water when that prediction is below the texture dry threshold, or when the 72-hour prediction is below the threshold and stress probability is at least `0.80`.

For a water decision, the optimizer:

1. sets a target moisture below the texture wet threshold;
2. converts the moisture deficit through texture root-zone depth, drainage behavior, and irrigation efficiency;
3. caps the gross application by the configured per-event maximum, pump capacity during permitted hours, budget, and a short infiltration-rate limit; and
4. selects an overlapping water-rights and low-energy window when one exists, otherwise the first permitted window.

If the capped amount is below the minimum actionable amount, Helios returns `wait` and `0.0` inches. The response confidence is heuristic: it combines model CV RMSE, distance from the dry threshold, physical sensor count, timing limitations, and whether ET was a fallback. It must not be interpreted as a calibrated probability that the advice is correct.

## Feedback adjustment and validation mode

In standard mode, Helios can query comparable nearby feedback after calculating the rule-based recommendation. The feedback query filters by crop, recommendation type, soil texture, and irrigation type; aggregation also considers distance, growth stage, and month.

Helios makes no adjustment unless there are enough total, comparable, and weighted samples. It then uses a Wilson interval around the feedback success rate and only makes a small positive or negative adjustment when the interval clears the neutral midpoint. Inconclusive feedback leaves the base recommendation unchanged.

Set `HELIOS_VALIDATION_MODE=1` for a clean field-test run. In this mode the feedback query and adjustment are disabled, and the response says so in its validation-evidence packet.

## Response and persistence

`/predict` returns the water-or-wait decision, amount, timing window, three moisture forecasts, stress explanation, selected driving zone, zone summary, ET provenance, confidence caveat, feedback-adjustment details, and a validation-evidence packet. The API stores a prediction record and sensor snapshots in SQLite after constructing the response. Persistence is best effort: a database write failure is logged but does not suppress a valid recommendation response.

## Important limits

- Helios is an operator aid, not an autonomous controller or certified scheduling engine.
- Forecast and recommendation confidence are heuristic, not calibrated uncertainty.
- Runtime fallback weather and ET values are approximations and are identified in the response.
- A passing test suite or candidate gate does not establish field-validated performance.
- SQLite persistence, in-memory rate limiting, and single-key authentication are prototype infrastructure choices.

## Source map

| Concern | Primary implementation |
| --- | --- |
| API lifecycle and routes | `helios/api/main.py`, `helios/api/runtime.py`, `helios/api/routes.py` |
| Request and response contracts | `helios/schemas/inputs.py`, `helios/schemas/outputs.py` |
| Request-to-feature conversion | `helios/data/ingestion.py`, `helios/data/feature_engineering.py` |
| ET and weather enrichment | `helios/utils/openet.py`, `helios/utils/weather_api.py`, `helios/utils/evapotranspiration.py` |
| Model loading and training | `helios/models/moisture_model.py`, `helios/models/train_model.py` |
| Recommendation orchestration | `helios/services/recommendation_service.py` |
| Rule-based irrigation plan | `helios/optimizer/irrigation_optimizer.py` |
| Feedback aggregation and storage | `helios/lib/feedback.py`, `helios/lib/aggregation.py`, `helios/database/db.py` |
| Rebuild and candidate evaluation | `helios/scripts/rebuild_training_bundle.py`, `helios/scripts/evaluate_maize_baseline.py` |

## Related documentation

- [How to run Helios locally](how-to-run-helios.md)
- [Public dataset ingestion](public-dataset-ingestion.md)
