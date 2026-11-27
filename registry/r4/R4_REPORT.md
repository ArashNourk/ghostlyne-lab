# Ghostlyne Discovery Lab · R4 research report (North American power and natural gas)

Run 27 Nov 2026 UTC under pre-registration `dda8c2c`, committed before confirmatory evaluation. The registry (`registry/registry.jsonl`) now holds 9,636 append-only events across R1–R4. Internal evaluation only; nothing here has been independently validated.

## Scope

**Seven focal measurements:**
1. ERCOT North day-ahead price.
2. ERCOT North real-time price.
3. North day-ahead minus real-time spread.
4. West minus North day-ahead basis.
5. North implied heat rate.
6. Henry Hub spot.
7. NYMEX front-month futures.

**External series:** 40, in five distance rings plus benchmarks and synthetic controls.

**Volume:** 21,516 tests across 1,606 experiment units.

**Data:** ERCOT public reports, EIA (grid monitor, Henry Hub, storage), NOAA, and market series used for research only. Raw market values are not published.

## 1. Lab validity (known energy relationships)

| Known relationship | Exploration | Confirmation |
|---|---|---|
| Henry Hub → North day-ahead | +0.14, recovered | +0.05, **not recovered at p < 0.001** |
| Dallas temperature stress → North day-ahead | +0.21 | +0.23 |
| Dallas temperature stress → ERCOT demand | +0.55 | +0.53 |
| ERCOT demand → North day-ahead | +0.12 | +0.17 |
| Wind → North day-ahead | −0.37 | −0.50 |
| Storage surprise → Henry Hub, weekly | −0.14 | **+0.05, reversed** |

The lab recovers the physical relationships: weather, demand and wind. Two known market relationships weakened or disappeared from 2019:
- **Gas to power.** Since 2019, day-to-day North prices have been driven more by scarcity and renewables than by gas.
- **Storage.** Our "surprise" is measured against the five-year average, not against analysts' expectations, which are licensed survey data. The market prices most of that information before the report.

These are findings in their own right: relationships everyone assumes can change.

## 2. Validated relationships (validated / tested)

| Relationship | D1 physical | D2 energy complex | D3 industry, finance | D4 climate, agriculture | D5 AI, crypto | Benchmarks, controls |
|---|---|---|---|---|---|---|
| Moves together, daily | 31 | 14 | 0 | 1 | 0 | 0 |
| Moves together, weekly | 23 | 8 | 0 | 0 | 0 | 0 |
| Lead–lag, daily | 3 | 3 | 0 | 0 | 0 | 0 |
| Lead–lag, weekly | 1 | 0 | 0 | 0 | 0 | 0 |
| Conditional on season | 15 | 8 | 0 | 0 | 0 | 0 |
| Conditional on scarcity | 6 | 0 | 0 | 0 | 0 | 0 |

That is 113 validated relationships. No benchmark or synthetic control was validated.

## 3. Conventional findings (D1)

Gas-fired generation, wind, solar, demand and temperature dominate, with confirmed rank correlations up to ±0.69. These are what an energy desk already knows; they confirm the lab works.

## 4. Unconventional findings (D2–D5)

- **Neighbouring grids.**
  - SPP wind moves against the ERCOT West–North basis: −0.45 daily, −0.56 weekly.
  - SPP wind also moves against North prices and the heat rate (−0.34 to −0.38).
  - MISO and SPP demand move with ERCOT North prices at the weekly horizon (+0.19 to +0.28).

  Hypothesis: shared wind and weather systems across the central US.
- **Eastern weather → West Texas basis.** Boston and Philadelphia temperature stress move with the West–North basis (small, −0.06), and the link is strengthening.
- **European gas.** TTF moves with Henry Hub (+0.09) and the NYMEX front month (+0.14), consistent with LNG export linkage. Cheniere moves with the front month (+0.13).
- **Corn and the gas front month,** +0.06 daily: weak, and the only D4 result.
- **Nothing from D3 or D5.** Copper, currencies, utilities, Vistra, freight, Bitcoin, the miners, Nvidia, the chip index and data-centre operators showed no validated relationship with ERCOT North or Henry Hub, daily or weekly. That holds within this run's power: daily tests can detect correlations of about 0.05–0.1.

## 5. Timing

Seven lead–lag relationships were validated, and they show **markets leading the physical data**:
- Henry Hub leads realised Philadelphia temperature stress by a day.
- The West–North basis leads realised eastern temperatures by two days.
- Henry Hub leads the storage surprise by two weeks.

This is consistent with prices responding to weather forecasts before the weather is observed. Henry Hub leading North day-ahead by one day, and solar leading the basis by one day, reflect auction timing.

No validated lead gives an external signal at least two days ahead. So incremental predictive value was not tested, and none is claimed.

## 6. Conditional structure

**Scarcity:** on the days ERCOT real-time prices are in their top 5%, the normal links weaken:
- Wind's dampening effect on North prices falls from −0.51 to −0.21.
- Gas generation's link to price falls from +0.62 to +0.36.

**Season:** 23 relationships differ between summer and the rest of the year.

For anyone exposed to price spikes, knowing that the usual relationships break down exactly when it matters is useful.

## 7. Stability

31 of the 113 changed significantly between exploration and confirmation, while keeping the same direction. Monitoring flags strengthening, weakening and divergence weekly, using only data available at each date. That is a historical replay, not live monitoring.

## Commercial relevance (separate from significance)

- **Most useful today:**
  - scarcity-conditional breakdowns, for anyone with short-term wholesale exposure;
  - neighbouring-grid wind and demand links to the West–North basis, for spread trading and hedging;
  - drift monitoring of relationships desks rely on, such as gas-to-power weakening since 2019.
- **For procurement:** front-month links to European gas and LNG are the only forward-relevant findings, and they are weak.
- **Not established:** any distant or AI-related driver of Texas power or US gas at daily or weekly horizons, or any actionable lead.

## Limitations

- ERCOT wind and solar series end in June 2024 because of an EIA format change; fixing this is the first data task for R5.
- PJM and Mass Hub need a registered API key and a terms check respectively.
- Regional gas hubs, power forwards and historical weather forecasts are licensed.
- Storage expectations (analyst consensus) are licensed. The storage surprise used here is a proxy.

## Proposed R5 (not registered)

1. Fix the wind and solar feed. Add PJM West (key) and Mass Hub (terms).
2. Test at the hourly and peak-hour level, where scarcity and renewables act.
3. Pre-register the scarcity-conditional and neighbouring-grid findings as confirmatory claims on fresh data as it arrives (prospective monitoring).
4. Test whether weather forecasts lead prices, if a forecast archive can be licensed.
