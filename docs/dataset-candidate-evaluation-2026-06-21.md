# Dataset Candidate Evaluation — 2026-06-21

This is a candidate-evaluation record, not a validation or shipping claim.

## USDA LIRF maize 2008–2011

Source: USDA-ARS Colorado Maize Water Productivity Dataset 2008–2011, DOI `10.15482/USDA.ADC/1254006`.

- Parsed from four maize workbooks and four matching weather workbooks.
- Produced 594 complete 24/48/72-hour origins across 2008–2011 and 1,782 normalized horizon rows.
- Direct measured-label counts: 24 at 24h, 150 at 48h, and 60 at 72h. Other rows are explicitly labeled as daily interpolations.

The candidate verdict is `CANDIDATE_FAIL`.

- GroupKFold passed all measured-label gates.
- LOYO failed the persistence gate. Candidate MAE remained above persistence at 24h (`0.005225` vs `0.004734`), 48h (`0.009134` vs `0.008639`), and 72h (`0.009447` vs `0.007441`).
- The base no-regression check passed (`0.015473` candidate RMSE versus `0.015416` baseline, within the configured `0.002` tolerance).
- The Mickelson transfer proxy did not improve (`0.005815` candidate RMSE versus `0.005772` baseline RMSE).

Result: retain the parser and evaluation evidence, but do not replace the shipped model.

## Combined USDA LIRF maize 2008–2013

The historical release was then combined with the existing 2012–2013 LIRF candidate and re-evaluated as one six-season source candidate.

- The combined candidate passed GroupKFold and LOYO measured-label gates, including persistence at every horizon.
- LOYO candidate MAE versus persistence MAE: 24h `0.004904` versus `0.005612`; 48h `0.008639` versus `0.010604`; 72h `0.009809` versus `0.010615`.
- The base no-regression check passed (`0.015459` candidate RMSE versus `0.015416` baseline RMSE, within the configured `0.002` tolerance).
- The Mickelson transfer proxy still regressed (`0.005910` candidate RMSE versus `0.005772` baseline RMSE).

Result: `CANDIDATE_FAIL` remains the shipping verdict because the Idaho transfer gate failed. The added years are nevertheless a measurable improvement for LIRF-domain forecast accuracy and evidence that temporal coverage, rather than parser quality, caused the original two-season persistence failure.

## USDA Bushland maize lysimeter bundle

Source: USDA-ARS Bushland soil-water and water-balance data, DOI `10.15482/USDA.ADC/1526332` and `10.15482/USDA.ADC/1526334`.

The data quality is strong: depth-resolved VWC and high-frequency lysimeter water-balance records exist for maize seasons in 2013, 2016, and 2018. However, the VWC sampling cadence is unsuitable for Helios's supervised 24/48/72-hour gate:

- The six reviewed maize workbooks have no directly measured 48-hour or 72-hour VWC pairs.
- The 2013 files have one 24-hour pair each; the 2016 and 2018 files have none.

Result: `NOT_EVALUABLE_AS_A_SUPERVISED_CANDIDATE` under the current evidence rules. Interpolating or integrating water-balance records would create derived labels, not independent measured 48/72-hour targets. That does not justify a farmer-facing accuracy claim.

## Remaining external data requirement

No additional publicly downloadable source met the measured 24/48/72-hour-label requirement. The following are the highest-value legitimate acquisition targets. They are not yet evaluated candidates: the raw exports must be provided through their owners before Helios can test them.

| Priority | Dataset / owner | Why it is high value | Required export | Current access |
| --- | --- | --- | --- | --- |
| 1 | Southern Idaho VRI telemetry archive — USU/University of Idaho collaborators, Grace, Pocatello, Rexburg, and Twin Falls | Actual southern Idaho irrigated fields, including wheat and potato rotation; multi-depth VWC, zone-specific variable-rate irrigation, yield, terrain, and sensor data. The Phase I report documents 2019--2021 sites and the Phase II work continues the Idaho trials. | Per-sensor timestamped VWC and calibration/depth metadata; every irrigation event/rate by zone; field/crop/soil identifiers; weather or ET; yield; 2019--2025 where available. | Not openly downloadable. The related Grace paper says interested parties must contact the corresponding author for data. |
| 2 | USU water-optimization sensor archive — Logan, Vernal, and Cedar City research farms | Controlled multi-year water-stress treatments with corn, hourly VWC at 6/18/30 inches, measured irrigation rates, crop system, and yield. It is the strongest non-Idaho source for adding many clean maize response sequences. | Hourly sensor records, irrigation flow-meter logs, weather/ET, plot/treatment/crop metadata, and yield for all complete site-years. | Not openly downloadable. The SARE report documents the measurements, but publishes results rather than an analysis-ready raw export. |
| 3 | University of Idaho SnakeFlux — southern Idaho producer fields | Ten irrigated commercial sites with half-hour ET, soil/crop/management observations. It provides the best potential breadth across crops and operating farms, which is essential to test transfer beyond research plots. | Timestamped depth-specific VWC, calibration, irrigation applications, field/crop/soil metadata, ET/weather/rainfall, and at least two seasons per field. | Cooperator/portal access required; no raw public export located. |

The first two targets are one connected research program but distinct data collections: on-farm Idaho VRI telemetry for transfer relevance, and replicated Utah plot telemetry for label volume and controlled irrigation responses. Request both rather than treating either publication figures or summary tables as training data.

The Idaho SnakeFlux source still needs the same kind of data-sharing export. Without raw exports from any of these owners, none can be tested or assigned an improvement verdict.

## Sources checked and rejected

- Idaho HydroShare VWC collections were rejected because the available series is watershed-scale and weekly/seasonal rather than dense irrigated field telemetry.
- USDA Bushland was rejected above for the same target-cadence reason.
- Satellite/model soil-moisture products were rejected as training labels: they are derived products and do not independently establish field-scale 24/48/72-hour VWC accuracy.
