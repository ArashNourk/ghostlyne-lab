# Ghostlyne max-leverage rule: pre-registered holdout test

Written and committed **before** the holdout is run. The git commit time of this file is the proof. The holdout is run
exactly once, by `research/holdout.py`, and its output is committed unedited to `research/HOLDOUT_RESULTS.md`.

## Why a holdout

Every design choice so far (the 20x cap, the stress definition, stress calibration, the stress gate, keeping the
current feature set) was made after looking at 2024-01-01 to 2026-11-23 results. Those results cannot validate those
choices. 2022 has never been evaluated for this model. It contains the LUNA collapse (May), the 3AC/Celsius
contagion (June) and the FTX collapse (November), so it is also a stress test.

## Development findings that led to the rules (2024-01-01 to 2026-11-23)

- Extra regime features, jump counts, GJR-GARCH-t, EVT (GPD-tailed FHS) and an ensemble did **not** produce a
  measurable out-of-sample benefit over the current model. They are not adopted.
- All methods, including GARCH-t and EVT, under-forecast on stress days: recommended positions at the 5% limit were
  liquidated about 6% (longs) and 5.4% (shorts) of the time while forecasting about 3%.
- Stress-regime calibration cut this to 4.7% / 3.9%; adding a stress gate cut it to 2.6% / 2.9%.
- At matched realized liquidation rates, Ghostlyne offered about 0.2 to 0.4x more leverage than GARCH-t.

## Locked rules

1. **Model:** unchanged logistic texture model (features v1, v7, v30, ret1, ret7, dd30, ru30, b_v7, b_ret1), refit monthly.
2. **Stress day** (known at 23:15 UTC), per side: more than 30% of markets moved at least 5% against that side today
   (down for longs, up for shorts), or today's log Parkinson variance exceeds its 30-day level by more than 1.
3. **Calibration:** separate walk-forward isotonic maps for stress and normal rows (stress map: 24-month lookback,
   at least 300 rows and 15 events, otherwise the pooled map scaled up by the past stress realized/forecast ratio).
   Then leverage monotonicity.
4. **Rule:** the highest leverage up to **20x** whose odds are at or below the risk limit. On stress days the limit
   is **halved**. If none qualifies, **abstain** ("none").

## Holdout design

- Evaluation: 2022-01-01 to 2022-12-31, every market with data (about 25). Walk-forward from 2021-03-01: every
  forecast, calibration map and stress map uses only earlier data. Nothing from 2023 or later is used.
- Comparisons: the same procedure with the current pooled calibration and no gate (the live v2 rule), and GARCH(1,1)-t.
- Confidence intervals: week-block bootstrap (all markets in a week resampled together), 90%.

## Pre-registered criteria (at the 5% risk limit)

| # | Criterion | Pass if |
|---|---|---|
| H1 | Realized liquidation rate of recommended positions | point estimate at or below 5% |
| H2 | Realized rate on stress days | point estimate at or below 5% |
| H3 | Locked rule vs live v2 rule on stress days | locked rule's realized rate is lower |
| H4 | 20x cap | on days the uncapped rule would name 40x, realized 40x liquidation rate is above 5% (cap justified) or there are too few such days (under 30) to judge |
| H5 | Matched risk vs GARCH-t | Ghostlyne (locked) offers more mean leverage than GARCH-t at realized 3% and 4% |

Also reported, with no pass/fail: results at 2% and 10% limits, abstention rate, by-leverage breakdown, Brier skill.
A failed criterion is reported as failed and is not tuned away on this data.
