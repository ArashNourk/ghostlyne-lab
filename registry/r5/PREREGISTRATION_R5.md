# Ghostlyne Discovery Lab · Pre-registration R5 (final bounded iteration)

Authorized 26 Nov 2026: seven-day maximum, no paid data, product and marketing suspended, no R6 if R5 fails. If R5 passes scientifically, customer willingness to pay is tested next. If it fails to show differentiated economic usefulness, Ghostlyne is suspended.

## The question

Does information beyond the established local drivers measurably improve a defined energy-market decision or risk assessment, on data not used to build it?

## Decisions (made at 09:00 Central on D−1, before the 10:00 day-ahead deadline, for delivery day D; peak hours HE7–22)

1. **SPIKE: risk assessment.** Probability that the maximum hourly ERCOT North real-time price on D exceeds its trailing-year 95th percentile. The threshold uses data to D−2 only. Value: reduction in Brier score. This is a risk-assessment value, not a trading return.
2. **PROCURE: procurement timing.** For 1 MW of North peak load: buy day-ahead, or stay in real time. Real time is chosen only if the predicted day-ahead minus real-time spread exceeds a $1/MWh friction, which is charged whenever real time is chosen. Value: reduction in average cost per MWh. CVaR95 of daily cost is also reported.
3. **SELL: sale timing.** For 1 MW of West-hub peak generation: sell day-ahead or in real time, with the same friction. Value: increase in revenue per MWh.

**Market access.** A load-serving entity or flexible load can choose day-ahead purchase or real-time exposure, and a generator can choose its sale market. Both are standard ERCOT choices.

## Information-time rule

At the decision, the following are used:
- realised prices and grid data to D−2;
- day-ahead prices to D−1;
- the published day-ahead demand forecast for D (EIA-930, the balancing authorities' own forecasts);
- market closes to D−2;
- hashprice to D−2;
- El Niño from the latest published week;
- storage from the latest release.

Realised wind, load or weather for D−1 or D is never used. Historical weather forecasts are not available free, so the baseline lacks them. Professional desks have them, which makes our baseline weaker than theirs. Any pass is therefore provisional until re-tested against a forecast-informed baseline.

## Conventional baseline (what any ERCOT participant has free)

- prior day-ahead prices;
- prior real-time prices, spreads and spikes;
- ERCOT demand, wind, solar, gas generation and nuclear output (D−2);
- the ERCOT day-ahead demand forecast for D, and its change;
- forecast net load;
- Henry Hub;
- Dallas and Houston temperature stress (D−2);
- day of week;
- annual harmonics.

## Groups tested for incremental value (each added to the baseline separately)

| Group | Contents | Classification |
|---|---|---|
| G1 neighbouring grids | SPP and MISO wind and demand (D−2); SPP and MISO day-ahead demand forecasts for D | conventional energy complex (D2) |
| G2 east and global gas | PJM demand, Philadelphia and Boston temperature stress, TTF, WTI, Cheniere and NYMEX front-month 7-day returns, storage surprise | conventional energy complex (D2) |
| G3 industry and finance | copper, CAD, MXN, utilities, Vistra, dry-bulk 7-day returns | unconventional |
| G4 climate and agriculture | El Niño, corn | unconventional |
| G5 crypto and AI | **hashprice computed from on-chain data** (miner revenue ÷ network hash rate): its 7-day change, the implied miner breakeven power price at 25 J/TH, and breakeven minus the North day-ahead price; Bitcoin, MARA, Riot, Nvidia, the chip index, Digital Realty, Equinix 7-day returns | unconventional |
| G35 | all unconventional groups together | unconventional |
| G0 | three synthetic noise features | must not pass |
| GP | planted informative features (noisy copies of the outcome) | must pass; checks the pipeline |

## Models and evaluation

- **Models:** logistic regression (C = 0.5) for SPIKE; ridge regression (α = 10) for the spreads. Standardised features. Expanding window from Jul 2018, refitted monthly; training uses days up to D−2 only. No tuning on results.
- **Exploration** (out of sample): 2020–2023. A group is a candidate if its gain is positive with one-sided block-bootstrap p < 0.10 (14-day blocks, 2,000 draws).
- **Confirmation** (out of sample): Jan 2024 – latest. Validated if the gain is positive with 95% block-bootstrap interval above zero and Benjamini–Hochberg q ≤ 0.05 among candidates.
- **Secondary, reported but not gates:**
  - gains on high-stress days (forecast net load in its trailing top 20%);
  - gains with a $3/MWh friction.

## On "genuinely untouched" data

R4 used 2019–2026 daily data for association tests. R5's decisions, hourly peak statistics and decision values are new, and no R5 model or result has been seen. But the calendar period overlaps R4's. The confirmation window is therefore untouched for these statistics, not for the underlying calendar. Any group that passes is also registered for prospective confirmation on data from 1 Dec 2026, before any commercial claim.

## Acceptance gates (locked)

| Gate | Requirement in R5 |
|---|---|
| Independence | The gain comes from a group added to the conventional baseline |
| Reproducibility | Validated in confirmation (above), then prospectively from Dec 2026 |
| Economic value | Positive confirmed gain in Brier score, cost or revenue, with CVaR not worse |
| Differentiation | A pass by G3, G4, G5 or G35 counts as unconventional differentiation. A pass by G1 or G2 is reported as cross-market intelligence, built from data on public dashboards |
| Operational viability | Every input in a passing group is current and usable in production. Hashprice must be recomputable from public chain data |
| Willingness to pay | Tested only after a scientific pass |

**Lab validity:** the baseline SPIKE model must beat climatology (Brier skill > 0) in exploration, GP must pass, and G0 must not.

## Data (`r5_coverage.json`)

- ERCOT hourly hub prices, Dec 2010 – Nov 2026 (real time averaged from 15-minute intervals).
- EIA-930 hourly, Jul 2015 / Jul 2018 – Nov 2026, with the wind and solar sub-columns summed.
- Hashprice, Jan 2009 – Nov 2026, from public chain statistics.
- Market series for research only.

The hashprice sources named in review were checked:
- CloudMineCrypto's site shows a live value and an app download, but no dataset or licence was found.
- Firsthand Bitcoin could not be located.

Hashprice was therefore computed from public chain statistics. In production it can be recomputed from the public blockchain itself.

Any change after this commit is a new run.
