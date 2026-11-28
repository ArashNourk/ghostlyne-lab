# WATCH2 lab check (simulated markets, not evidence about Bitcoin)

Run on 2026-11-28, before any real data. Purpose: show that the harness can find a real advantage when one exists, and does not invent one when none exists.

## Formula
The three-outcome first-passage formula agrees with a Monte Carlo simulation, using a continuity correction for discrete monitoring, within **0.23 pp** across five cases. The pre-registered limit is 0.5 pp. Code: `fp3.py`.

## Markets
- **const**: volatility never changes and returns are normal. No model can legitimately beat CV here.
- **sv**: volatility clusters (log-AR(1) plus occasional shocks) with a daily rhythm, and returns are fat-tailed (Student t, 5 degrees of freedom).

Each market is 6 years of 5-minute paths, seen by the models only as hourly candles. Development is the first 3.5 years; confirmation is the rest, with about 131,000 scenarios and 1.8 million checkpoints.

## Results on confirmation data, with Amendment 1 applied (`watch2.py <market> --cal`)
| Gate | const (control) | sv |
|---|---|---|
| H1 Brier, G vs CV | −0.01% [−0.09, +0.07] | **+10.6% [8.4, 12.8]** |
| H1c calibration | pass | pass |
| H2 level rule, G vs best benchmark | 0.99× [0.98, 1.00] (CV level rule) | **1.09× [1.04, 1.16]** (CV level rule), false-warning rate 20.1% |
| H3 same price, different risk | never triggered (0 checkpoints) | **+22.7% [17.9, 27.3]**, 198,883 checkpoints across 31 months |

Without the calibration layer, H1 in sv was +18.9%, but H1c failed. With the layer applied fairly to both models, the honest edge is 10.6%. The pre-registered rise rule failed in both markets (0.76× and 0.77× of the best benchmark), which led to Amendment 1.

## What this shows and what it doesn't
It shows that the code works, that the gates can pass when an advantage exists, and that they stay shut when none does. It says nothing about Bitcoin. Whether Bitcoin's volatility clusters enough, at a resolution we can buy, to clear these gates is the question the licensed-data run answers.

Rerun: `python3 watch2.py const --cal` and `python3 watch2.py sv --cal`, about 30 seconds each, deterministic seeds.
