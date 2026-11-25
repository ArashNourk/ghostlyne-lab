# Ghostlyne max-leverage rule: 2022 holdout results

Run once on the pre-registered rules. Evaluation 2022-01-01 to 2022-12-31, walk-forward from 2021-03-01.

## Longs

7257 market-days, 22 markets, stress days 18.5%.

| Rule | Limit | Realized (90% CI) | Stress-day realized (90% CI) | Mean forecast | Mean leverage offered | Abstained |
|---|---|---|---|---|---|---|
| Locked (stress-calibrated + gate) | 2% | 0.68% (0.23%, 1.27%) | 0.00% (0.00%, 0.00%) | 1.04% | 5.01x | 18.8% |
| Locked (stress-calibrated + gate) | 5% | 1.79% (0.90%, 2.89%) | 0.00% (0.00%, 0.00%) | 2.92% | 6.77x | 17.4% |
| Locked (stress-calibrated + gate) | 10% | 3.67% (2.39%, 5.05%) | 3.36% (0.32%, 6.51%) | 5.25% | 9.05x | 0.1% |
| Live v2 (pooled calibration, no gate) | 2% | 0.94% (0.30%, 1.73%) | 1.85% (0.26%, 3.98%) | 1.05% | 4.42x | 26.8% |
| Live v2 (pooled calibration, no gate) | 5% | 2.14% (1.08%, 3.33%) | 4.08% (0.98%, 7.48%) | 2.94% | 7.57x | 0.8% |
| Live v2 (pooled calibration, no gate) | 10% | 4.45% (2.98%, 6.08%) | 7.66% (3.17%, 11.96%) | 5.93% | 9.46x | 0.0% |
| GARCH(1,1)-t | 2% | 1.47% (0.50%, 2.65%) | 3.77% (0.52%, 7.17%) | 1.14% | 5.91x | 9.1% |
| GARCH(1,1)-t | 5% | 2.59% (1.40%, 3.97%) | 5.34% (1.85%, 8.99%) | 2.81% | 7.59x | 2.1% |
| GARCH(1,1)-t | 10% | 4.49% (2.90%, 6.22%) | 8.59% (3.82%, 12.90%) | 5.69% | 9.33x | 0.8% |

Locked rule at 5%, by recommended leverage: none: 1263 days, realized -, 5x: 538 days, realized 1.67%, 7x: 3300 days, realized 1.27%, 10x: 1921 days, realized 2.65%, 15x: 118 days, realized 0.00%, 20x: 117 days, realized 4.27%
20x cap: the uncapped rule would have named 40x on 34 days; those 40x positions were liquidated 8.82%; the capped recommendation on the same days was liquidated 0.00%.
Matched risk, mean leverage offered (locked minus GARCH-t): at 3% realized: -0.27x (90% -0.57 to +0.72); at 4% realized: +0.31x (90% -0.40 to +0.72)
Brier skill of locked vs live v2 by leverage (40x..5x): -0.006 -0.003 -0.003 -0.003 -0.002 -0.009

## Shorts

6009 market-days, 22 markets, stress days 14.6%.

| Rule | Limit | Realized (90% CI) | Stress-day realized (90% CI) | Mean forecast | Mean leverage offered | Abstained |
|---|---|---|---|---|---|---|
| Locked (stress-calibrated + gate) | 2% | 1.38% (0.95%, 1.87%) | 3.30% (0.91%, 6.74%) | 1.12% | 6.79x | 15.7% |
| Locked (stress-calibrated + gate) | 5% | 2.85% (2.16%, 3.62%) | 2.28% (0.80%, 3.95%) | 2.33% | 8.77x | 9.0% |
| Locked (stress-calibrated + gate) | 10% | 5.67% (4.45%, 6.95%) | 6.26% (3.50%, 8.99%) | 5.35% | 11.47x | 0.8% |
| Live v2 (pooled calibration, no gate) | 2% | 1.38% (0.95%, 1.85%) | 1.40% (0.53%, 2.35%) | 1.19% | 7.30x | 7.0% |
| Live v2 (pooled calibration, no gate) | 5% | 3.10% (2.39%, 3.87%) | 5.35% (2.81%, 7.76%) | 2.35% | 9.23x | 1.2% |
| Live v2 (pooled calibration, no gate) | 10% | 6.49% (4.94%, 8.08%) | 12.62% (7.16%, 17.83%) | 5.75% | 11.63x | 0.4% |
| GARCH(1,1)-t | 2% | 1.74% (1.24%, 2.29%) | 3.53% (1.42%, 5.98%) | 1.12% | 7.01x | 6.1% |
| GARCH(1,1)-t | 5% | 3.72% (2.72%, 4.77%) | 7.39% (3.40%, 11.09%) | 3.03% | 9.50x | 0.8% |
| GARCH(1,1)-t | 10% | 6.95% (5.29%, 8.64%) | 12.53% (6.74%, 18.32%) | 6.32% | 11.74x | 0.7% |

Locked rule at 5%, by recommended leverage: none: 538 days, realized -, 5x: 246 days, realized 0.81%, 7x: 2252 days, realized 2.71%, 10x: 2056 days, realized 2.82%, 15x: 636 days, realized 3.46%, 20x: 281 days, realized 4.63%
20x cap: the uncapped rule would have named 40x on 49 days; those 40x positions were liquidated 24.49%; the capped recommendation on the same days was liquidated 4.08%.
Matched risk, mean leverage offered (locked minus GARCH-t): at 3% realized: +0.50x (90% -0.49 to +1.02); at 4% realized: +0.41x (90% -0.23 to +1.02)
Brier skill of locked vs live v2 by leverage (40x..5x): -0.004 -0.001 -0.002 +0.001 +0.010 -0.005

## Pre-registered criteria

| # | Longs | Shorts |
|---|---|---|
| H1 | pass | pass |
| H2 | pass | pass |
| H3 | pass | pass |
| H4 | pass | pass |
| H5 | FAIL | pass |
