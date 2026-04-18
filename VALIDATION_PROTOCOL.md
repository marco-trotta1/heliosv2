# Irrigant Validation Protocol

## Purpose

This document defines the on-farm validation protocol for Irrigant's XGBoost-based soil moisture prediction model. It establishes what success looks like, what data will be collected, and how results will be evaluated before any production deployment.

## Accuracy Threshold

The agronomic accuracy target is ±0.03 VWC (volumetric water content) units between predicted and observed soil moisture at the 12-hour forecast horizon. This threshold was selected in consultation with University of Idaho extension agronomists as the minimum precision required to generate actionable irrigation recommendations for potato, corn, and wheat operations.

## Trial Design

- **Location**: Snake River Plain, Idaho (pilot farm TBD — coordinates withheld pending partner agreement)
- **Duration**: 30 days minimum, covering at least one full irrigation cycle per crop
- **Crops**: Potato (primary), corn, winter wheat (secondary)
- **Sensor setup**: Capacitance-based soil moisture sensors at 6", 12", and 24" depths
- **Measurement frequency**: Hourly readings logged to local datalogger; synced daily

## Data Collected Per Field

| Variable | Source | Frequency |
|---|---|---|
| Volumetric water content (VWC) | In-field sensor | Hourly |
| Air temperature, humidity, wind | NOAA weather API | Hourly |
| Evapotranspiration (ET₀) | OpenET REST API | Daily |
| Irrigation events (volume, timing) | Farmer log | Per event |
| Crop growth stage | Farmer report | Weekly |

## Evaluation Criteria

A trial is considered successful if:

1. Mean absolute error (MAE) of VWC predictions is ≤ 0.03 across all sensor depths and days
2. The system correctly classifies irrigate / do not irrigate decisions in ≥ 85% of cases where farmer action is recorded
3. No prediction falls outside the agronomically valid VWC range of 0.05–0.55

## Failure Conditions

The model will not be considered deployment-ready if:

- MAE exceeds 0.05 VWC at any sensor depth for more than 3 consecutive days
- Any systematic bias (consistent over- or under-prediction) exceeds 0.02 VWC

## Post-Trial Actions

- If validation passes: proceed to multi-farm pilot expansion and investor data room
- If validation fails: retrain on trial data, identify feature gaps, repeat protocol

## Version

Protocol version 1.0 — drafted prior to first field trial. Subject to revision after sensor calibration.
