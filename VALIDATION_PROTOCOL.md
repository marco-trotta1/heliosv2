# Irrigant Validation Protocol

## Purpose

This document defines the on-farm validation protocol for the current Helios field-test build.
It is intended for the University of Idaho Kimberly Research and Extension Center field test scheduled for Tuesday, April 21, 2026.

This version of the protocol is aligned to the software that exists in this repository today.

## What Helios Actually Predicts

The current Helios backend predicts field-level volumetric water content forecasts at:

- 24 hours
- 48 hours
- 72 hours

It does not currently produce:

- 12-hour forecasts
- independent depth-specific forecasts for 6", 12", and 24"

When multiple probes are submitted, Helios builds one field-level feature row and uses the driest zone as the primary driving sensor for recommendation logic. The API response also reports the latest zone moisture summary so field variability can still be reviewed during the test.

## Trial Scope

- **Location**: University of Idaho Kimberly Research and Extension Center, Idaho
- **Date**: Tuesday, April 21, 2026
- **System under test**: current Helios backend and shipped model artifact
- **Evaluation type**: prospective field validation of a research-stage decision-support prototype

## Required Pre-Test Freeze

Before the first measurement is recorded, the team must freeze the exact software and model build being tested.

Record all of the following:

- git commit SHA
- app version
- model artifact hash
- metadata hash
- training date
- training row count
- whether validation mode was enabled

Recommended command:

```bash
HELIOS_VALIDATION_MODE=1 python3 -m helios.scripts.validation_preflight \
  --output artifacts/kimberly-validation-manifest.json
```

The generated manifest file becomes part of the official field-test record.

## Runtime Mode For The Test

For the Kimberly accuracy test, Helios should run with:

- `HELIOS_VALIDATION_MODE=1`

This disables nearby-feedback-based recommendation adjustments so the field test measures the model and base irrigation optimizer, not prior SQLite feedback records.

## Data Collection

For each field test run, collect:

- timestamp of observation
- field ID
- sensor ID
- probe depth
- observed VWC
- weather inputs actually used by Helios
- irrigation events in the prior 72 hours
- crop type
- growth stage
- Helios predicted 24h / 48h / 72h moisture
- Helios decision and recommended irrigation amount
- notes on anomalies, sensor issues, or operator overrides

## Evaluation Unit

The primary evaluation unit for the current system is the field-level forecast generated from the submitted probe set.

Because the model is not yet depth-specific, the team must choose and document one of these comparison rules before the test starts:

1. Compare Helios against the driest sensor at each observation time.
2. Compare Helios against the mean VWC across the submitted sensors.
3. Compare Helios against one predesignated reference probe and depth for the whole trial.

The rule chosen must stay fixed for the entire Kimberly test.

## Primary Evaluation Criteria

The Kimberly field test is considered successful only if all of the following are true:

1. Mean absolute error at the chosen comparison target is `<= 0.03 VWC` at the primary forecast horizon being evaluated.
2. No systematic bias exceeds `0.02 VWC` over the test window.
3. No prediction falls outside the agronomically valid VWC range of `0.05` to `0.55`.
4. Irrigate / wait classification is directionally reasonable when compared with researcher judgment and recorded irrigation decisions.

## Recommended Horizon Scoring

Because the current system predicts 24h / 48h / 72h horizons, the recommended scoring order is:

1. Primary: 24h forecast accuracy
2. Secondary: 48h forecast accuracy
3. Exploratory: 72h forecast accuracy

This keeps the test centered on the shortest forecast horizon the deployed model actually produces.

## Failure Conditions

The model should not be presented as field-validated if any of the following occur:

- protocol and software behavior are mismatched during the test
- the build or model changes after the pre-test freeze
- MAE exceeds `0.05 VWC` for the primary comparison target
- a sustained over- or under-prediction bias exceeds `0.02 VWC`
- the team cannot clearly state which sensor/depth reference Helios was scored against

## Reporting Requirements

The final Kimberly test report should include:

- the frozen validation manifest
- the exact scoring rule used
- the number of observations collected
- MAE by horizon
- bias by horizon
- any out-of-range predictions
- observed sensor anomalies or missing-data issues
- whether validation mode was enabled throughout the test

## Version

Protocol version 2.0, aligned to the current Helios 24h / 48h / 72h field-level forecast system on April 19, 2026.
