# Ghostlyne v0.4: 2023 test results

Run once on the pre-registered rules. Evaluation 2023-01-01 to 2023-12-31, walk-forward from 2021-03-01.

## Longs

8650 market-days, 25 markets, stress days 12.2%.

| Rule | Limit | Realized (90% CI) | Stress-day realized (90% CI) | Mean leverage | Abstained |
|---|---|---|---|---|---|
| v0.4 (smooth, tuned) | 2% | 2.03% (1.18%, 3.02%) | 7.52% (0.00%, 16.49%) | 8.99x | 10.6% |
| v0.3 (step, halved on stress) | 2% | 1.40% (0.74%, 2.23%) | 9.35% (0.00%, 20.01%) | 7.97x | 11.8% |
| GARCH-t, same tuned rule | 2% | 2.02% (1.22%, 2.96%) | 1.90% (0.00%, 4.48%) | 9.96x | 2.0% |
| v0.4 (smooth, tuned) | 5% | 5.57% (4.05%, 7.29%) | 6.25% (0.58%, 13.95%) | 13.22x | 6.6% |
| v0.3 (step, halved on stress) | 5% | 2.88% (1.81%, 4.15%) | 5.82% (0.56%, 12.84%) | 10.58x | 6.4% |
| GARCH-t, same tuned rule | 5% | 5.60% (4.31%, 7.08%) | 2.73% (0.55%, 5.83%) | 14.07x | 0.3% |
| v0.4 (smooth, tuned) | 10% | 8.79% (7.03%, 10.69%) | 3.88% (0.35%, 8.62%) | 16.21x | 0.5% |
| v0.3 (step, halved on stress) | 10% | 5.26% (3.78%, 6.96%) | 3.63% (0.34%, 8.21%) | 13.89x | 0.4% |
| GARCH-t, same tuned rule | 10% | 9.54% (7.83%, 11.31%) | 4.90% (1.63%, 8.94%) | 16.72x | 0.2% |

v0.4 at 5%, by recommended leverage: none: 573 days, 5x: 212 days, realized 2.36%, 7x: 274 days, realized 2.55%, 10x: 2467 days, realized 3.32%, 15x: 3148 days, realized 6.29%, 20x: 1976 days, realized 8.00%
Brier skill, smooth vs step calibration (40x..5x): +0.0024 +0.0015 +0.0008 +0.0012 +0.0035 -0.0001
10x forecasts identical to another market's the same day: step 82.8%, smooth 16.6%

## Shorts

8650 market-days, 25 markets, stress days 12.7%.

| Rule | Limit | Realized (90% CI) | Stress-day realized (90% CI) | Mean leverage | Abstained |
|---|---|---|---|---|---|
| v0.4 (smooth, tuned) | 2% | 1.86% (1.34%, 2.45%) | 1.13% (0.30%, 2.04%) | 9.23x | 9.7% |
| v0.3 (step, halved on stress) | 2% | 1.64% (1.18%, 2.15%) | 2.50% (0.86%, 4.43%) | 8.77x | 10.0% |
| GARCH-t, same tuned rule | 2% | 2.39% (1.77%, 3.09%) | 1.84% (0.89%, 2.81%) | 9.66x | 3.3% |
| v0.4 (smooth, tuned) | 5% | 4.56% (3.55%, 5.67%) | 2.20% (0.71%, 4.16%) | 12.68x | 3.6% |
| v0.3 (step, halved on stress) | 5% | 3.56% (2.72%, 4.52%) | 2.26% (0.78%, 3.91%) | 11.91x | 4.1% |
| GARCH-t, same tuned rule | 5% | 5.55% (4.41%, 6.78%) | 4.51% (3.09%, 5.88%) | 13.03x | 0.9% |
| v0.4 (smooth, tuned) | 10% | 8.94% (7.44%, 10.50%) | 4.92% (2.72%, 7.48%) | 15.66x | 1.2% |
| v0.3 (step, halved on stress) | 10% | 6.61% (5.37%, 7.92%) | 5.10% (2.92%, 7.66%) | 14.29x | 1.2% |
| GARCH-t, same tuned rule | 10% | 10.13% (8.37%, 11.95%) | 8.24% (5.87%, 10.68%) | 16.07x | 0.5% |

v0.4 at 5%, by recommended leverage: none: 310 days, 5x: 261 days, realized 3.07%, 7x: 1047 days, realized 1.72%, 10x: 2818 days, realized 3.76%, 15x: 2291 days, realized 5.33%, 20x: 1923 days, realized 6.55%
Brier skill, smooth vs step calibration (40x..5x): +0.0003 +0.0005 -0.0019 -0.0010 +0.0009 +0.0050
10x forecasts identical to another market's the same day: step 81.5%, smooth 14.1%

## Pre-registered criteria

| # | Longs | Shorts |
|---|---|---|
| H1 | FAIL | pass |
| H2 | pass | pass |
| H3 | FAIL | pass |
| H4 | pass | pass |
| H5 | pass | pass |
| H6 | FAIL | FAIL |

Decision rule (H1 to H5 on both sides): **v0.4 does not go live**.
