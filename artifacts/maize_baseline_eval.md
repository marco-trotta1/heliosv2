# Maize Baseline Evaluation

Verdict: CANDIDATE_FAIL

This evaluation is a candidate gate, not a validation claim.

## Measured-Only Metrics

| Protocol | Horizon | Count | Baseline MAE | Candidate MAE | Delta MAE | Persistence MAE | Candidate Bias | Candidate RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| group_kfold | 24h | 36 | 0.01259 | 0.003938 | 0.008652 | 0.006197 | -0.00058 | 0.004705 |
| group_kfold | 48h | 429 | 0.028116 | 0.005826 | 0.02229 | 0.011291 | -0.002352 | 0.007367 |
| group_kfold | 72h | 123 | 0.028258 | 0.006388 | 0.02187 | 0.012163 | 0.00152 | 0.007767 |
| loyo | 24h | 36 | 0.01259 | 0.009224 | 0.003366 | 0.006197 | 0.004966 | 0.011027 |
| loyo | 48h | 429 | 0.028116 | 0.008598 | 0.019518 | 0.011291 | -0.003675 | 0.0107 |
| loyo | 72h | 123 | 0.028258 | 0.012466 | 0.015792 | 0.012163 | 0.001275 | 0.014762 |

## Gates

- GroupKFold gates: `{"measured_48h_count_nonzero": true, "measured_72h_count_nonzero": true, "measured_threshold_pass": true, "persistence_pass": true}`
- LOYO gates: `{"measured_48h_count_nonzero": true, "measured_72h_count_nonzero": true, "measured_threshold_pass": true, "persistence_pass": false}`
- Base no-regression: baseline RMSE `0.015416`, candidate RMSE `0.015444`, pass `True`
- Transfer proxy: `{"baseline_rmse_mean": 0.005772, "candidate_better": true, "candidate_rmse_mean": 0.005772, "claim": "Mickelson holdout improved; Idaho transfer still requires field validation", "status": "scored"}`

## Gate Reasons
- loyo: candidate did not beat persistence

## Caveat
Mickelson holdout improved; Idaho transfer still requires field validation

