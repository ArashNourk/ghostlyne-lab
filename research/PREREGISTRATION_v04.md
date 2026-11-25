# Ghostlyne v0.4: pre-registered test on 2023

Written and committed **before** the test is run; the commit time is the proof. Run once by `research/holdout04.py`;
output committed unedited to `research/HOLDOUT_v04_RESULTS.md`.

## Why

An external review found two real problems with v0.3:

1. **Resolution.** Isotonic calibration maps forecasts onto a few steps, so many markets show the identical number
   (in development, 86% of 10x long forecasts matched another market's to 0.01%).
2. **Over-conservatism.** At a 5% limit, recommended positions were liquidated only 1.8% (longs) and 2.9% (shorts) of
   the time in 2022, and the fixed halving on stress days is a blunt patch.

## Changes under test (developed on 2024-01-01 to 2026-11-23 only)

1. **Smooth calibration:** the same walk-forward regime isotonic maps (normal and stress), then linear interpolation in
   logit space between the centres of the isotonic blocks (`research/v04.py`, `SmoothIso`). Development: Brier equal or
   slightly better (+0.1%), identical-value share 86% → 12%.
2. **Tuned max-leverage rule:** on normal days, instead of the fixed limit, an internal threshold is set each month as the
   largest value whose recommended positions over the past 12 months of normal days were liquidated at or below **90% of
   the chosen limit** (fallback: the limit itself). On stress days the v0.3 rule is kept: the limit is halved. A tuned
   stress-day threshold was tried and rejected in development: it overshot badly in 2024 (7.9% longs, 7.1% shorts at a 5%
   limit), because stress samples are too thin to tune. Cap 20x and abstention unchanged. Development (2024-2026) at 5%:
   realized 4.1% longs and 4.2% shorts (stress days 1.6% and 2.5%); mean leverage 10.8x and 10.6x against 9.6x and 9.7x for v0.3.
3. **Colour levels** compare 10x odds with the market's 365-day normal instead of 90 days (presentation only; not tested here).

Development also showed that the same tuned rule applied to GARCH-t gives nearly the same result (about 0.2 to 0.6x less
leverage). The gain comes mainly from the rule, not from a better model. Year by year the rule is close to the limit:
longs at 5% realized 4.7% in 2024 alone.

## Test design

- Evaluation 2023-01-01 to 2023-12-31. Walk-forward from 2021-03-01: every forecast, calibration map and threshold uses only
  earlier data; nothing from 2024 or later is used.
- 2023 has never been used to evaluate calibration or the max-leverage rule. It was included, pooled with 2024 to 2026, in an
  early feature experiment with a different target (positioning data; `results/report.md`), which is disclosed here.
- Comparisons: v0.3 (step calibration, fixed limit halved on stress days) and GARCH(1,1)-t with the same tuned rule.
- Week-block bootstrap 90% intervals.

## Pre-registered criteria (5% limit, each side)

| # | Criterion | Pass if |
|---|---|---|
| H1 | Realized liquidation rate of recommended positions | at or below 5% |
| H2 | Uses the risk budget | at or above 3% |
| H3 | Stress-day realized rate | at or below 5% |
| H4 | Leverage offered | mean leverage above v0.3's |
| H5 | Smooth calibration | Brier at 20x, 15x and 10x no more than 0.2% worse than step calibration, and under 30% of 10x forecasts identical to another market's |
| H6 | Against GARCH-t with the same rule | Ghostlyne offers more mean leverage *and* its realized rate is no more than 0.5 points higher |

Also reported without pass/fail: 2% and 10% limits, abstention, by-leverage results.
v0.4 goes live only if H1 to H5 pass on both sides. H6 decides only whether we may claim an advantage over GARCH-t.
