# CP1 pre-registration: calling ERCOT's monthly coincident peak from public data

Committed before any 2024–2026 result was computed. Code: `cp1.py` (this commit). Input: `hourly_panel.csv.gz` on branch `registry-r5fetch` (EIA-930 hourly ERCOT demand and ERCOT's day-ahead demand forecast as reported to EIA, local hour ending).

## Why this test
The PUCT has proposed replacing 4CP (four summer 15-minute peaks) with 12CP (one peak per month). A coincident-peak alert product is only worth building if public data can call the monthly peak day a day ahead, within a curtailment budget customers will accept, and better than the obvious free rule. This test decides that. No paid data. Product work stays suspended until the result is in.

## Target
- **Primary:** the day of each month's highest hourly ERCOT demand (EIA-930, operational data). That is what a 12CP customer must avoid.
- **Secondary (reported, not gated):** the official settlement 4CP day for summer months where ERCOT's filed date is known (2023-06 to 2026-08, 14 months, listed in `cp1.py`). The official CP uses settlement load, which can differ from operational load (storage charging and DC ties are treated differently). Disclosed before registration: operational and official days agree in all four 2023 months. 2024 was not checked before registration.

## Information time
- **Primary, day-ahead alert (issued on D−1):** actual demand known up to D−2. ERCOT day-ahead demand forecasts are known for D−1 and D.
- **Secondary, same-morning alert (issued on D):** actual demand known up to D−1, plus the forecast for D.

## Model M1 (fixed)
Logistic regression (L2, C=1, standardised features), refit each month on all earlier months (expanding window). Features for day D:
- x1 = log(forecast peak D / month-to-date reference). The reference is the month-to-date maximum of known actuals, together with the D−1 forecast in day-ahead mode. Before any in-month information exists, it falls back to the climatological reference.
- x2 = log(forecast peak D / climatological reference). The reference is last year's same-month actual maximum × the growth in trailing 365-day mean load.
- x3 = share of the month remaining after D; x4 = weekend or NERC holiday.
- The products x1·x3 and x2·x3, a winter (Dec–Feb) indicator, and x2·winter.

## Baselines
- **B0 (climatology):** peak-day frequency by weekday vs weekend/holiday, from earlier months. Used for the Brier score.
- **B1 (the free rule):** alert when the forecast exceeds the month-to-date reference by a threshold. Score = x1. This is what a simple utility alert does.

## Alert policy and budget
Each method gets a fixed threshold, set on exploration months (2018-07 to 2023-12, walk-forward predictions) to produce a mean of k alert days per month. Then it is applied unchanged to confirmation months (2024-01 to 2026-10).
- **Primary k = 6.** This was chosen after exploration and before confirmation for two reasons:
  1. Industry alert counts run 6–10 calls a month (Enverus reported 10/7/7/6 for summer 2025).
  2. In exploration, even an oracle that knows D's actual peak catches only 71% of monthly peaks at k=3 (94% at k=6), because future days are unknown.
- k = 2, 3 and 4 are also reported.

## Disclosed exploration results (2018-07 to 2023-12, 66 months, day-ahead)
| k | M1 capture | B1 capture | oracle M1 | noise M1 |
|---|---|---|---|---|
| 3 | 0.64 | 0.58 | 0.71 | 0.11 |
| 6 | 0.82 | 0.82 | 0.94 | 0.29 |

M1 Brier skill vs B0: 0.115 (95% CI 0.057–0.172).

## Metrics
- **Capture:** the share of months whose peak day received an alert.
- **Hour capture:** the peak day was alerted and the actual peak hour fell within the forecast peak hour ±1.
- **Realised alerts per month.**
- **Brier skill vs B0,** with a month-block bootstrap (2,000 draws, seed 20261127).
- Breakdowns: winter months, summer months, and "tight" months (top two days within 1%).

## Gates (confirmation, day-ahead, k = 6)
- **G1 lab validity:** the oracle (forecast replaced by actual) captures ≥ 0.85, and the noise control (forecast shuffled within month) captures ≤ 0.40. If G1 fails, the results are void.
- **G2 skill:** the lower 95% bound of M1's Brier skill vs B0 is > 0.
- **G3 commercial capture:** M1 captures ≥ 0.85 of months with ≤ 7 realised alerts per month.
- **G4 differentiation:** M1 capture − B1 capture ≥ 0.10, with M1 alerts per month ≤ B1's + 0.5.

## Decision rule
- **G1 fails:** fix the lab; no conclusion.
- **G2 or G3 fails:** public-data CP forecasting is not commercially sufficient. The forecast product is not viable without paid weather or multi-day forecasts, which require founder approval.
- **G2 and G3 pass, G4 fails:** calling peaks is a commodity (the free rule does as well). The only defensible product is the neutral, timestamped ledger plus the 12CP bill-impact calculator, and building it is a founder decision.
- **All pass:** build the prototype, landing page and waitlist for Texas brokers.

## Known limits
- Data granularity is hourly. Official CPs are 15-minute (4CP) or 30-minute (proposed 12CP) intervals.
- EIA-930 demand values may have been revised after first publication.
- The forecast is ERCOT's own, as reported to EIA.
- February 2021 demand was suppressed by load shedding.
