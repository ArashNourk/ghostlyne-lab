# Ghostlyne Discovery Lab · Pre-registration R4 (North American power and natural gas)

Governing decisions: R4 authorization, 26 Nov 2026. Ghostlyne is an energy-market intelligence company. AI infrastructure, crypto mining, metals, agriculture, logistics, currencies and weather are external discovery domains, not target markets. R1–R3 records are preserved unchanged.

## 1. Data feasibility (`r4_feasibility.json`, `panel_coverage.json`)

| Source | Coverage | Usage rights |
|---|---|---|
| ERCOT hub prices, day-ahead and real-time (NP4-180-ER, NP6-785-ER) | Dec 2010 – Nov 2026, hourly or 15-minute → daily averages | ERCOT terms permit public raw data in compilations, charts and analyses |
| EIA-930 grid monitor: demand, day-ahead demand forecast, generation by fuel (ERCOT, PJM, MISO, SPP, ISO-NE, CAISO) | Demand Jul 2015 –; fuel mix Jul 2018 –. Wind and solar end Jun 2024 because of a file-format change (fix deferred) | Public domain |
| EIA Henry Hub spot (daily), Lower-48 storage (weekly) | 1997 – / 2010 – | Public domain |
| NOAA GHCN-Daily (Dallas, Houston, Philadelphia, Boston); NOAA CPC weekly Niño 3.4 | 2009 – | Public domain |
| Market series (NYMEX front month, crude, TTF, equities, FX, crypto) via Yahoo | Varies | Research use only. Raw values are never committed or published, only derived statistics |
| PJM Data Miner | — | Requires an API key the company must register; not used in R4 |
| ISO-NE (Mass Hub) | Public files reachable | Terms not yet confirmed; deferred |
| Regional gas hubs, power forwards, historical weather forecasts | — | Licensed or unavailable; not purchased |

## 2. Focal markets (seven distinct measurements, never merged)

1. ERCOT North day-ahead (daily average).
2. ERCOT North real-time.
3. North day-ahead minus real-time spread.
4. West minus North day-ahead basis.
5. North implied heat rate (day-ahead ÷ Henry Hub).
6. Henry Hub spot.
7. NYMEX natural gas front-month futures (forward measurement).

## 3. Discovery universe (`universe4.py`)

40 external series:
- **D1 direct physical drivers (10):** gas, temperature, demand, demand forecast, wind, solar, gas generation, nuclear output, storage.
- **D2 wider energy complex (10):** crude, TTF, the LNG exporter, other regions' demand, wind and temperatures.
- **D3 industrial and financial (6):** copper, the Canadian dollar, the Mexican peso, utilities, a Texas generator, dry-bulk freight.
- **D4 remote (2):** El Niño, corn.
- **D5 distant (7):** Bitcoin, two bitcoin miners, Nvidia, the semiconductor index, two data-centre operators.
- **Comparison and controls:** orange juice and lean hogs are comparison benchmarks (real distant series, not assumed to be true negatives). Three synthetic series are true negative controls.

Each external has a written admission rationale. Mechanical pairs are excluded: the heat rate against Henry Hub, and front-month futures against Henry Hub.

## 4. Lab validity (completed before this registration, exploration window only)

Six known energy relationships were tested as empirical positive controls (`lab_validity_explore.json`). All six recovered the expected sign at p < 0.001.

| Relationship | Rank correlation |
|---|---|
| Henry Hub → North day-ahead | +0.14 |
| Dallas temperature stress → North day-ahead | +0.21 |
| Dallas temperature stress → ERCOT demand | +0.55 |
| ERCOT demand → North day-ahead | +0.12 |
| Wind → North day-ahead | −0.37 |
| Storage surprise → Henry Hub, weekly | −0.14 |

One correction came out of this step and is part of the method: storage is dated by its release week. EIA publishes the week ending Friday on the following Thursday. Same-week dating had the right sign but missed the threshold.

**Synthetic checks** (`synth4.py`) found that naive lead–lag tests on differenced, seasonal, noisy energy series create false leads. The registered method below removes them. On the synthetic world, it recovered every planted relationship, produced no false lead–lag claims, and still detects planted leads of correlation 0.1 (mean-reverting series) at n ≈ 2,900.

## 5. Transformations

- **Same-period association (A):** daily changes (prices and spreads in levels; gas, market series and loads in log changes; temperature stress as degree days |T − 65°F|), with day-of-week effects removed. Weekly: end-of-week values for trending prices, weekly means for mean-reverting physical series.
- **Temporal relationships (B):** if both series mean-revert, anomalies (level minus the trailing one-year mean); otherwise changes on both sides. Trend, the annual cycle (three harmonics) and day-of-week effects are removed within each window.

## 6. Qualification paths (separate claims)

| Path | Families | Test |
|---|---|---|
| A, association | A_d (daily), A_w (weekly) | Rank correlation (robust to price spikes) with Newey–West p-values; Pearson recorded |
| B, temporal | B_d (leads 1–10 days, either direction), B_w (1–8 weeks) | Box–Jenkins prewhitening; the lagged correlation must hold, with the same sign, under both the leader's and the follower's filter. The weaker result is reported |
| Conditional and regime | S_season (June–September vs rest), S_scarcity (days when North real-time is above its trailing-year 95th percentile vs other days) | Difference in rank correlation |
| C, incremental predictive value | Only validated B claims where the external leads | Information-time rule: an external value is usable no earlier than 2 days after its date (day-ahead demand forecast: 1 day; weekly: 1 week). Baseline: the focal's own last 7 days (4 weeks). Expanding window over the confirmation period, Clark–West, out-of-sample R² > 0 |

A is never required for B, and C is never required for A or B.

## 7. Windows and gates

- **Pairs whose data start by 2012:** exploration 2011–2018, confirmation 2019 onward.
- **Later-starting pairs:** exploration from data start to 2021, confirmation 2022 onward.
- **Exploration:** Benjamini–Hochberg at q = 0.10 within each family and distance ring. The strongest lag per pair is kept.
- **Confirmation:** same sign, and Benjamini–Hochberg at q = 0.05 among that family's candidates.
- **Minimum data:** 500 days or 100 weeks per window.
- **Price spikes:** daily claims confirmed over a window containing Winter Storm Uri (8–24 Feb 2021) must also hold, same sign at p < 0.05, with those days removed.

## 8. Recorded separately for every validated relationship

- strength and 95% interval;
- exploration-to-confirmation stability;
- rolling 365-day (104-week) rank strength;
- behaviour: stable, strengthening, weakening or reversing;
- divergence z (20-day or 4-week residual from a trailing two-year reference fit);
- lag drift for temporal claims;
- in-regime and out-of-regime strength for conditional claims.

Monitoring uses only data available at each date. It is a historical replay, not live monitoring.

**Commercial relevance** is labelled separately from significance:
- short-term wholesale exposure (daily);
- short-term exposure and weekly planning (weekly);
- spread trading and hedging (day-ahead minus real-time spread, basis);
- forward and procurement (front month).

Spot relationships are not presented as forward-contract intelligence.

Any change to sections 3–8 after this commit creates R5.
