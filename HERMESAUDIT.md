# HERMESAUDIT

# Helios Audit Report

Repository: `/Users/marcotrotta/Desktop/Irrigant Helios`

Audit mode: read-only inspection, except this exported Markdown file at the user's request.

Validation update: Codex re-audited this report with the same four lenses: ML Engineer, Software Engineer, AI Researcher, and Farmer / Operator Reviewer. The broad gate is unchanged, but several tactical claims below were corrected after direct repo and command verification.

## Executive Verdict

- **ML readiness:** Prototype only. The shipped artifact is XGBoost trained on synthetic plus Mickelson rows whose targets are heuristic water-balance outputs, not measured future VWC. CV RMSE 0.01497 measures fit to synthetic / heuristic target generation, not validated field forecasting.
- **Software readiness:** Internal or supervised use only. Python tests pass in a compatible Python 3.13 environment, schema validation is rigorous, and the evidence packet is honest. Fresh dependency setup is not blocked by `fastapi==0.135.1`; a temp venv install of `requirements-dev.txt` succeeded. The checked-in `.venv` is still stale because it uses Python 3.9 while `pyproject.toml` requires Python 3.11 or later.
- **Research/validation readiness:** Not production-ready. The maize cross-season LOYO gate is `CANDIDATE_FAIL`; the candidate loses to persistence at 24h and 72h measured horizons. No true held-out measured Idaho service-area validation exists. No calibrated uncertainty exists.
- **Farmer pilot readiness:** Conditional yes, supervised only. Helios can support a controlled validation pilot if `HELIOS_VALIDATION_MODE=1` is enabled, the operator is told the model is experimental, and every run is paired with observed probe outcomes.
- **Broad farmer release readiness:** No. Label realism, measured validation, uncertainty calibration, production infrastructure, auth, observability, and farmer-facing clarity are not ready.
- **Immediate ship recommendation:** **Ship only as supervised pilot**.

## What Is Good

### ML

- Honest labeling metadata exists. `helios/scripts/rebuild_training_bundle.py` records measured and interpolated maize label counts separately, and `helios/scripts/evaluate_maize_baseline.py` evaluates measured-only performance before promotion.
- Persistence comparison is treated as a real gate. The maize candidate is rejected because LOYO did not beat persistence, not because the report ignored the failure.
- The evaluation stack includes GroupKFold, LOYO, measured-only metrics, no-regression checks, and a transfer-proxy caveat.
- Texture-bounded prediction clipping exists in `helios/models/moisture_model.py`, with texture-specific physical envelopes for sand, loam, and clay.
- Artifact metadata records `model_hash`, `training_data_hash`, `training_rows`, target columns, feature columns, CV RMSE, validation RMSE, and training timestamp.
- Group-disjoint training behavior is tested in `tests/test_group_aware_training.py`.
- The model metadata reports fold-level RMSE, which allows stability checks across folds.

### Software

- Request validation is strong. The API checks timezone-aware timestamps, future timestamps, field-id consistency, weather bounds, sensor-reading counts, crop classes, soil classes, and feedback payload constraints.
- Startup has a model-feature schema guard. Runtime metadata feature columns are checked against the feature builder before serving.
- The service exposes `/livez` and `/health`, and degraded model state returns a 503 rather than silently serving predictions.
- Recommendation confidence is explicitly caveated as heuristic in code and documentation.
- Sensor outlier handling exists. The ingestion layer can reject a stuck-low probe with MAD filtering when there are at least three sensors.
- Feedback adjustment is statistically guarded with Wilson intervals and sample-size thresholds.
- OpenET lookup has a live, cached, and fallback path.
- Validation mode disables feedback adjustments for clean field-test scoring.
- The Python test suite passed in a compatible Python 3.13 environment: 127 passed, 1 warning.
- A fresh temporary Python 3.13 venv installed `requirements-dev.txt`, including `fastapi==0.135.1`, successfully.
- The docs repeatedly avoid overclaiming: README and architecture docs call Helios a prototype operator aid, not an autonomous controller.

### Research / validation

- The maize evaluation artifact clearly says `CANDIDATE_FAIL`.
- Measured-only metrics are separated from interpolated-included metrics.
- The report names the gate reason: `loyo: candidate did not beat persistence`.
- GroupKFold measured-only candidate metrics are strong relative to the baseline on the candidate evaluation, but the LOYO result prevents promotion.
- The evaluation includes a base no-regression guard so a candidate cannot improve one dataset while breaking the existing artifact path.
- The report caveats Idaho transfer risk instead of claiming validated transfer.

### Farmer / operator usability

- The product is framed as decision support, not automation.
- The frontend includes Idaho-relevant scenarios, including Kimberly Research Farm, heat wave, balanced day, and rain-incoming presets.
- NOAA auto-fill reduces farmer burden for weather inputs.
- Soil texture can auto-fill a plausible infiltration rate.
- The optimizer respects pump capacity, maximum event volume, budget, infiltration limits, and water windows.
- The UI has plain-language driver copy, for example high ET, near stress band, little rain, narrow water window, yield-sensitive growth stage, and drying trend.
- ET source and fallback status are exposed.
- Validation evidence includes model hash, training date, ET source, feedback status, driving zone, and confidence caveat.
- There is a copy-pastable evidence packet for farm logs and pilot review.

## What Is Bad

### ML

- The shipped model is not trained on true measured future soil-moisture labels. README line 20 says this directly.
- Synthetic targets are generated from a FAO-56 style water-balance formula, not observed future VWC.
- Mickelson targets are also generated by a water-balance step, not future measured probe values.
- USDA LIRF labels include many interpolated targets. The audit found 2,103 of 2,691 normalized USDA label rows are interpolated, roughly 78.2 percent.
- USDA LIRF was evaluated as a candidate, not included in the shipped artifact. `artifacts/model_metadata.json` reports 7,631 training rows, matching synthetic plus Mickelson, with no USDA CSV in `training_inputs`.
- Mickelson weather features are effectively constant in the parsed rows: temperature 72, humidity 38, wind 8, solar radiation 22. This weakens weather-learning claims.
- The LOYO measured-only candidate loses to persistence at 24h and 72h.
- No calibrated prediction intervals exist. The model returns point forecasts only.
- `feature_importances` is missing from the shipped `artifacts/model_metadata.json`, despite current training code writing it.
- The combined training CSV implied by the current rebuild path is not present, so the training hash cannot be reverified from the repo alone. The metadata stores a hash, not a file path.
- The earlier sklearn pickle version-skew claim was not reproduced during validation; `joblib.load("artifacts/moisture_model.pkl")` loaded without warning in the validation environment.
- The `transfer_proxy` is not a true geographic transfer test. It evaluates on Mickelson-shaped rows, not held-out Idaho field observations.

### Software

- `requirements.txt` pins `fastapi==0.135.1`, and validation confirmed this version is currently installable. The earlier "unsatisfiable dependency" claim is wrong / outdated.
- The checked-in `.venv` uses Python 3.9.6, while `pyproject.toml` requires Python 3.11 or later and code uses `float | None` style annotations. Importing the app under that `.venv` fails.
- The API cannot be treated as production-ready with single-key auth, in-memory rate limiting, SQLite persistence, and no tenant isolation.
- `/api/acknowledgements` is unauthenticated and can write arbitrary acknowledgement records subject only to rate limiting.
- Rate limiting is process-local. It resets on restart and is not shared across workers.
- OpenET cache is process-global and has no TTL.
- NOAA precipitation fallback uses a heuristic `probability of precipitation * 0.2 inches`, not real QPF.
- Solar fallback is hardcoded to an Idaho monthly climatology, not field-specific solar radiation.
- `config.js` contains a committed production API URL.
- SQLite tables are append-only with no retention, vacuum, backup, or archival policy.
- There is no production observability stack: no metrics exporter, latency histogram, fallback counter, alerting, or drift tracking. The API does have basic prediction logging, so this is a production-observability gap rather than zero logging.
- `railway.toml` only contains a start command. It does not define healthchecks, restart policy, secrets, or log shipping.
- README documents 5 routes, but the backend exposes additional routes such as `/version` and `/api/acknowledgements`.

### Research / validation

- The current accuracy evidence does not prove useful future prediction in real Idaho fields.
- Measured-label counts are small, especially for the 24h horizon. The headline 36 / 429 / 123 measured counts are per-row sums across folds, not per-fold averages.
- The only measured dataset is public USDA LIRF, not the target service area or pilot fields.
- No true field-held-out measured Idaho validation exists. The repo has a Mickelson holdout / transfer proxy, but it is not measured service-area field validation.
- No season-held-out validation exists for the shipped synthetic plus Mickelson training bundle.
- Persistence is the only naive baseline in the maize artifact. There is no FAO-56 baseline, climatology baseline, or autoregressive drift baseline.
- `current_soil_moisture` is both a feature and the basis of target construction, creating structural dependence that makes low error easier.
- USDA soil texture appears simplified to `loam`, which hides soil-texture-specific error.
- No ablation exists for synthetic rows, OpenET features, weather features, or measured-only rows.
- No uncertainty calibration exists, so decision risk cannot be quantified.

### Farmer / operator usability

- `confidence_score` is a heuristic but is displayed as a numeric score that a farmer could read as probability.
- Raw 24h, 48h, and 72h moisture values are mostly in technical / copy-export text rather than the main hero UI, but they still imply more precision than the evidence supports.
- The optimizer can recommend water based on the 72h forecast if stress probability is high, even when the 48h forecast is above the dry threshold.
- Demo-mode and live-mode have explicit labels and docs, but recommendations share enough UI structure that a casual reviewer could still over-read demo output as model-backed output.
- The frontend sends three readings from one synthetic sensor ID. Multi-zone probe behavior is not exercised from the normal UI path.
- High variability between sensors is computed but not prominent in the headline recommendation.
- Feedback adjustment can nudge recommendation amount up or down, but the headline does not make this obvious.
- The form is heavy. A pilot operator can face roughly 26 explicit inputs before running an analysis.
- Technical phrases such as Reference ET, validation build, model hash, and confidence caveat are useful for researchers but not yet simple enough for farmers.

## What Needs Work

### 1. Must fix before supervised farmer pilot

1. Fix local Python environment setup.
   - Remove or recreate the stale checked-in `.venv` with Python 3.11 or later.
   - Keep `fastapi==0.135.1` unless a separate compatibility reason appears; validation confirmed it is installable.
   - Verification: fresh clone plus `pip install -r requirements-dev.txt` succeeds; `python -m pytest` runs.

2. Add authentication to `/api/acknowledgements`.
   - Current route only uses rate limiting.
   - Verification: endpoint returns 401 without API key when `HELIOS_API_KEY` is set.

3. Add model artifact CI checks.
   - Required fields: `feature_importances`, `model_hash`, `training_data_hash`, `training_rows`, `training_provenance`, `cv_splitter`, `group_column`.
   - Verification: CI fails on stale or incomplete artifact metadata.

4. Surface evaluation verdict in model evidence.
   - Response should include model hash and a pointer to the latest evaluation artifact.
   - Verification: response evidence packet names `CANDIDATE_FAIL` for the current maize candidate.

5. Replace numeric confidence in the main UI with a plain-language level.
   - Keep the raw heuristic score in technical details only.
   - Verification: result card shows High / Medium / Low confidence with a caveat, not a 0.72 style probability.

6. Keep raw 24h / 48h / 72h forecast values out of default farmer-facing surfaces.
   - Verification: the main farmer-facing card uses plain-language trajectory / risk language; raw moisture values remain only in technical details or copy export.

7. Gate urgent decisions on sensor variability.
   - If `high_variability_flag` is true, the recommendation should require human review rather than headline urgency.
   - Verification: tests cover high-spread sensor scenarios.

8. Run the pilot in `HELIOS_VALIDATION_MODE=1`.
   - Verification: response packet says feedback adjustment is disabled.

9. Document the pilot as experimental decision support.
   - Verification: farmer-facing copy says the model is trained on synthetic / heuristic labels and is not field-validated.

10. Add minimal production logging.
    - Log request id, decision, et source, model hash, validation mode, and latency.
    - Do not log raw sensitive farm data.

### 2. Must fix before broader farmer release

1. Collect measured future VWC labels from service-area fields.
   - Required: at least one season, 24h / 48h / 72h horizons, fixed sampling protocol.
   - Verification: held-out field and held-out season evaluation reports beat persistence and FAO-56 baselines.

2. Add calibrated uncertainty.
   - Use quantile regression, conformal intervals, or another calibrated interval method.
   - Verification: empirical coverage on measured held-out data matches interval claims.

3. Replace random KFold on time-correlated rows with time-aware validation.
   - Verification: production artifact metadata records temporal split protocol.

4. Add measured field-held-out and geography-held-out evaluation.
   - Verification: model beats persistence on held-out measured Idaho fields.

5. Add true production auth and tenant isolation.
   - Verification: feedback and prediction history are tenant-scoped and cannot leak across farms.

6. Replace in-memory rate limit and OpenET cache.
   - Verification: shared Redis or database-backed implementation supports multi-worker deployments.

7. Add production observability.
   - Required metrics: request count, latency, error rate, OpenET live/cache/fallback count, NOAA fallback count, model verdict, decision distribution.

8. Add database retention and backup policy.
   - Verification: SQLite or Postgres storage has retention configuration and backup restore test.

9. Replace NOAA precipitation heuristic with real QPF or explicit uncertainty warning.
   - Verification: weather input provenance states whether precipitation is measured, forecast QPF, or heuristic.

10. Simplify farmer UI.
    - Collapse to Field, Soil and Water, Conditions.
    - Hide advanced fields by default.
    - Replace technical labels with farmer language.

### 3. Nice-to-have / later

- Add model-staleness warning when artifact age exceeds a threshold.
- Add crop and soil texture ablation reports.
- Add per-feature importance summary into the evidence packet for researchers only.
- Add explicit field log export for pilot reports.
- Add frontend localStorage quota error handling.
- Add CORS preflight tests.
- Add route docs for `/version` and `/api/acknowledgements`.
- Add OpenET TTL cache tests.
- Add feedback-table indexes for scale.
- Add a farmer-facing explanation of ET and soil-moisture thresholds.

## What Can Be Shipped Immediately

### Can ship now

- **Supervised validation pilot workflow**
  - Use `HELIOS_VALIDATION_MODE=1`.
  - Use the existing evidence packet.
  - Pair every recommendation with observed probe outcomes.
  - Do not present the model as validated.

- **Internal demo**
  - Static frontend can demonstrate workflow and UX.
  - Must retain demo banner and prototype caveat.

- **Docs**
  - README and architecture docs are mostly honest about limitations.
  - `HermesAuditRepair.md` already lays out the right repair plan.

- **Dataset ingestion tooling**
  - Rebuild and parser scripts are usable as internal tools.

- **Evaluation scripts**
  - `evaluate_maize_baseline.py` is useful because it correctly rejected a weak candidate.

- **OpenET enrichment component**
  - Useful as a standalone enrichment layer with live/cache/fallback provenance.

- **Validation preflight and scoring flow**
  - `validation_preflight.py` and `score_validation_results.py` are suitable for controlled pilot data collection.

### Cannot ship now

- Broad farmer-facing recommendations.
- Claims of validated accuracy.
- Claims of calibrated confidence.
- Autonomous or semi-autonomous irrigation control.
- Production API exposed to broad internet traffic.
- The raw model artifact as proof of field-ready prediction.
- Demo-mode recommendations as farm-use recommendations.

## Evidence Table

| Claim | Evidence | File / artifact / command | Confidence | Risk if wrong |
|---|---|---|---|---|
| The shipped model is not trained on true measured future soil-moisture labels | README says the model is not trained on true measured future soil-moisture labels | `README.md:20` | High | Farmer or buyer over-trusts model predictions |
| Shipped artifact has 7,631 training rows | `training_rows: 7631` | `artifacts/model_metadata.json` | High | Provenance of shipped model is misunderstood |
| Shipped artifact uses synthetic plus Mickelson, not USDA | `training_inputs` lists Mickelson workbook and OpenET CSV, not USDA; 5,000 synthetic plus 2,631 Mickelson equals 7,631 | `artifacts/model_metadata.json`; data row counts | High | Candidate evaluation gets confused with shipped model evidence |
| CV RMSE is 0.01497 | `cv_rmse_mean: 0.01497301752859212` | `artifacts/model_metadata.json` | High | Accuracy is overstated if treated as measured-field accuracy |
| CV RMSE is not measured-field validation | Shipped labels are synthetic / heuristic; README says no true measured future labels | `README.md`; `helios/scripts/generate_sample_data.py`; `helios/scripts/parse_mickelson_data.py` | High | Prototype fit is mistaken for field accuracy |
| Per-target CV RMSE increases with horizon | 24h 0.010826, 48h 0.015384, 72h 0.018709 | `artifacts/model_metadata.json` | High | Horizon risk is hidden |
| Maize candidate verdict is failure | `Verdict: CANDIDATE_FAIL` | `artifacts/maize_baseline_eval.md:3` | High | Failed candidate might be promoted accidentally |
| LOYO failed because candidate did not beat persistence | Gate reason says `loyo: candidate did not beat persistence` | `artifacts/maize_baseline_eval.md:25-27` | High | Cross-season weakness is underplayed |
| GroupKFold measured metrics look strong | Candidate MAE 24h 0.003938, 48h 0.005826, 72h 0.006388 | `artifacts/maize_baseline_eval.md:11-13` | High | Strong in-fold evidence could be mistaken for production validation |
| LOYO measured metrics are weaker | Candidate MAE 24h 0.009224, 48h 0.008598, 72h 0.012466 | `artifacts/maize_baseline_eval.md:14-16` | High | Model may fail under season shift |
| LOYO 24h and 72h lose to persistence | Persistence MAE 24h 0.006197, 72h 0.012163, both below candidate MAE | `artifacts/maize_baseline_eval.md:14-16` | High | Simplest baseline beats model at key horizons |
| Confidence is heuristic, not calibrated | Constant caveat says heuristic confidence is not calibrated uncertainty | `helios/services/recommendation_service.py` | High | Farmer reads score as probability |
| Predictions are point forecasts only | `MoistureForecastModel.predict` returns floats, not intervals | `helios/models/moisture_model.py` | High | No risk-aware decision support |
| Synthetic targets are generated by water-balance formula | `_step` updates moisture from ET, precip, irrigation, noise, and clip | `helios/scripts/generate_sample_data.py` | High | Model learns formula instead of field dynamics |
| Mickelson targets are simulated by daily water-balance step | `daily_moisture_step` computes target moisture | `helios/scripts/mickelson_support.py` | High | Private data realism is overstated |
| Mickelson weather features are constant | Parsed rows use fixed weather values | `helios/scripts/parse_mickelson_data.py` | High | Model cannot learn local weather effects from those rows |
| Feature importances missing from shipped metadata | Metadata lacks `feature_importances` despite trainer writing it | `artifacts/model_metadata.json`; `helios/models/train_model.py` | High | Cannot inspect model behavior |
| `fastapi==0.135.1` can currently be installed | Fresh temp venv installed `requirements-dev.txt` successfully | `/tmp/helios-audit-venv/bin/python -m pip install -r requirements-dev.txt` | High | Stale setup warning causes the wrong repair |
| Checked-in `.venv` uses Python 3.9.6 | `.venv/bin/python --version` reported 3.9.6 | command output | High | App import fails because code expects Python 3.11+ |
| Python tests pass in compatible env | 127 passed, 1 warning on Python 3.13 | `python3 -m pytest -q`; `/tmp/helios-audit-venv/bin/python -m pytest -q` | High | Code health is understated if the old count is retained |
| Rate limit is in-memory | `_hits` is a process-local defaultdict | `helios/api/rate_limit.py` | High | Multi-worker prod rate limit is ineffective |
| OpenET cache has no TTL | Module-global dictionary with manual clear only | `helios/utils/openet.py` | High | Stale ET values persist until restart |
| `/api/acknowledgements` lacks auth | Route uses rate limit dependency but not API-key dependency | `helios/api/routes.py` | High | Anyone can write records |
| NOAA precip is heuristic | Precip is computed from probability times 0.2 inches | `helios/utils/weather_api.py` | High | Forecast water input can be misleading |
| Demo-mode path is a heuristic | Static demo path is documented separately from live API mode | `README.md`; `src/api/scenario.js`; `src/domain/recommendations.js` | High | Demo recommendation can be confused with production model |
| UI sends one synthetic sensor ID with three readings | Run builder repeats one sensor id for lag and current readings | `src/api/run-builders.js` | High | Multi-zone sensor logic not exercised by normal UI |
| High variability is not prominent | Flag is computed but rendered in details rather than headline | `helios/services/recommendation_service.py`; `src/ui/results.js` | Medium | Operator may miss probe disagreement |
| Production URL is committed | `config.js` includes live Railway URL | `config.js` | High | Demo and live modes are easy to confuse |
| README route list is incomplete | README lists 5 routes; backend exposes more | `README.md`; `helios/api/routes.py` | High | Operators miss supported endpoints |

## Sub-Agent Findings

### ML Engineer

The ML system is well-structured but not validated enough. Strengths include measured/interpolated label tracking, persistence gates, LOYO and GroupKFold evaluation, physical clipping, and provenance hashes. Weaknesses are label realism, lack of uncertainty, failed LOYO persistence gate, missing feature importances, synthetic target dependence, and unproven Idaho transfer. The model is acceptable for internal demo only, not broad farmer use. A supervised pilot is possible only if it is framed as validation, not a validated decision product.

### Software Engineer

The software architecture is stronger than the stale local environment. Backend validation, route structure, runtime checks, error responses, feedback safeguards, validation mode, and Python tests are solid. The biggest blockers are stale checked-in `.venv`, in-memory rate limit, unauthenticated acknowledgement route, no tenant auth, no production observability, no retention policy, and a committed live API URL. The FastAPI service can be used internally or in a controlled supervised pilot, but it is not production infrastructure.

### AI Researcher

The scientific evidence is credible only as prototype evidence. The maize candidate evaluation is honest because it rejects the candidate. But the evidence does not prove useful real-world prediction. Most labels are simulated or interpolated; measured counts are small; persistence remains competitive; no true held-out measured Idaho service-area validation exists; no uncertainty calibration exists. Safe claims are narrow: Helios can produce prototype short-horizon moisture estimates and the current USDA maize candidate failed promotion. Unsafe claims include validated accuracy, calibrated confidence, farmer readiness, or broad transfer to Idaho.

### Farmer / Operator Reviewer

A farmer would like the conservative caps, plain-language drivers, NOAA auto-fill, Idaho presets, evidence packet, ET source labels, and validation mode. A farmer would be skeptical of numeric confidence, raw moisture values in technical exports, heavy input burden, similar demo/live recommendation cards, silent feedback adjustment, and the 72h forecast trigger. The product can support a supervised pilot with a researcher present, but the farmer-facing surface needs simplification and stronger caveats before it should influence real irrigation decisions.

## Top 10 Next Actions

1. **Fix local Python environment setup**
   - Owner: Software Engineer
   - Why it matters: the checked-in `.venv` is stale and fails imports under Python 3.9.
   - Verification: `pip install -r requirements-dev.txt` succeeds on Python 3.11+ and tests run.
   - Ship impact: removes a false setup blocker and prevents developers from using the wrong interpreter.

2. **Add model artifact contract check in CI**
   - Owner: ML Engineer
   - Why it matters: current shipped metadata is missing important fields.
   - Verification: CI fails if `feature_importances`, provenance, hashes, row counts, or split metadata are missing.
   - Ship impact: prevents stale artifacts from looking shippable.

3. **Run measured-only USDA evaluation**
   - Owner: ML Engineer
   - Why it matters: current evidence is diluted by simulated and interpolated labels.
   - Verification: measured-only CV and measured-only LOYO metrics per horizon are reported.
   - Ship impact: clarifies whether candidate data helps.

4. **Add `promotion_allowed` gate**
   - Owner: ML Engineer
   - Why it matters: promotion should be machine-checkable.
   - Verification: current candidate produces `promotion_allowed: false`.
   - Ship impact: prevents failed candidates from replacing shipped artifacts.

5. **Authenticate `/api/acknowledgements`**
   - Owner: Software Engineer
   - Why it matters: unauthenticated writes can contaminate pilot data.
   - Verification: 401 without key, 200 with key, 422 on invalid payload.
   - Ship impact: closes a pilot data-integrity hole.

6. **Replace main UI numeric confidence with plain-language levels**
   - Owner: Frontend / Farmer Reviewer
   - Why it matters: a farmer will read 0.72 as probability.
   - Verification: default result card shows High / Medium / Low plus caveat, not a numeric confidence.
   - Ship impact: reduces overtrust.

7. **Keep raw 24h / 48h / 72h moisture values out of default farmer-facing surfaces**
   - Owner: Frontend
   - Why it matters: raw values imply more precision than the evidence supports.
   - Verification: the main farmer-facing card uses plain-language trajectory / risk language; raw moisture values remain only in technical details or copy export.
   - Ship impact: makes pilot UI more honest.

8. **Add high-variability gating to urgent recommendations**
   - Owner: ML Engineer / Software Engineer
   - Why it matters: disagreeing probes should trigger caution, not urgency.
   - Verification: high spread prevents urgent headline unless human override or multiple sensors agree.
   - Ship impact: improves farmer trust and safety.

9. **Add response-level evaluation verdict pointer**
   - Owner: ML Engineer / Software Engineer
   - Why it matters: model hash without eval status is incomplete.
   - Verification: response packet includes model hash, training date, eval verdict, and artifact path.
   - Ship impact: makes every pilot run auditable.

10. **Collect a measured-label Idaho pilot dataset**
    - Owner: Research / Field Ops
    - Why it matters: this is the only path to real farmer readiness.
    - Verification: held-out field and held-out season metrics beat persistence and FAO-56 baselines with calibrated intervals.
    - Ship impact: turns Helios from prototype into defensible recommendation engine.

## Final Gate

- **Can Helios be shipped broadly to farmers today?**
  - No.
  - The model is not validated on measured future soil moisture in the service area.
  - The maize candidate failed cross-season persistence at 24h and 72h.
  - Confidence is heuristic, not calibrated.
  - Infrastructure is prototype-grade.

- **Can Helios be used in a supervised validation pilot today?**
  - Yes, with strict framing.
  - Use `HELIOS_VALIDATION_MODE=1`.
  - Keep a researcher or operator supervisor in the loop.
  - Record observed probe outcomes for every recommendation.
  - Present every output as experimental decision support, not validated advice.

- **What is the smallest honest thing we can ship now?**
  - A supervised-validation pilot workflow: docs, validation preflight, scoring scripts, demo presets, evidence packet, and a live backend configured in validation mode.
  - Do not ship the model as a validated predictor.

- **What single next step most improves Helios' chance of becoming farmer-ready?**
  - Collect and evaluate measured future VWC labels from Magic Valley / Hamer / Teton service-area fields, with 24h / 48h / 72h horizons, held-out fields, held-out seasons, persistence and FAO-56 baselines, and calibrated uncertainty intervals.
