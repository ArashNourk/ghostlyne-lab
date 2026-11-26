# Ghostlyne Discovery Lab · Pre-registration R2 (semiconductor memory)

Governing document: the Ghostlyne Governing Product Vision and Research Specification (26 Nov 2026). This run replaces nothing. R1 and its data snapshot (branch `registry-r1-data`) stay as they are.

## 1. Audit of R1 against the specification

R1 asked one question: does a monthly outside variable improve out-of-sample forecasts of broad US price and production indices? That is Qualification C alone. It did not test statistical association (A) or lead–lag structure (B) as separate claims. Its targets were aggregated proxies, not memory or GPU markets. It required a pre-set direction. In short, R1 was a forecasting test, not a discovery test. Its negative result stands as a record of that specific question. R2 is built to address the discovery proposition.

## 2. Data feasibility (probe results: `r2_coverage.json`, coverage only, no values seen)

**Focal market: semiconductor memory.** Memory product prices (DDR4, DDR5, DRAM, NAND, HBM) are not obtainable without a paid DRAMeXchange licence. Buying one requires founder approval, so they are recorded as unavailable. R2 uses what is available, labelled for what it is:

- **Weekly, financial instruments (not memory prices):** Micron, SK hynix, Samsung Electronics, Nanya, Winbond, and memory-module makers ADATA and TeamGroup.
- **Monthly, memory-market activity:** Nanya and Winbond monthly revenue, from Taiwan Stock Exchange mandatory disclosures (2013 onward).

The full list of unavailable variables and reasons is in `universe.py` under `UNAVAILABLE`.

**Licensing.** Share prices and futures are fetched inside GitHub Actions for research only. Raw prices are not committed or published. Only derived statistics are. Taiwan revenue disclosures and NOAA data are public records.

## 3. Universe

There are 7 weekly focal instruments and 42 outside variables. The outside variables span D1 (5), D2 (10), D3 (12), D4 (5) and D5 (4). Each has a written admission rationale in `universe.py`.

There are 6 negative controls:
- 3 real but unrelated series: orange juice, lean hogs, live cattle.
- 3 synthetic random walks.

The global equity factor is MSCI ACWI. The semiconductor index is excluded from the universe because it contains the focal stocks.

## 4. Transformations

- Weekly Friday closes. Weekly log returns for prices and FX. Weekly change for the El Niño index. No interpolation.
- **Total association:** raw weekly returns.
- **Adjusted association:** residuals after removing the global factor (same week and previous week), estimated within each window.
- **Monthly track:** monthly log change of revenue with the calendar-month pattern removed within each window, and monthly log change of each outside variable.

## 5. Qualification paths (separate claims, never collapsed)

- **A_total.** Contemporaneous Pearson correlation of raw returns, with a Newey–West p-value (4 lags). The rank correlation must agree in sign.
- **A_adjusted.** The same, on market-adjusted returns.
- **B_leadlag.** Correlation of adjusted returns at lags ±1 to ±8 weeks. Either side may lead. One lag per pair and direction is kept: the strongest in exploration. A 1-week lead from a market that closes later on Friday is treated as a probable trading-hours artifact and is not validated.
- **S_stress.** Difference in adjusted correlation between stress weeks and calm weeks (Fisher z test). Stress weeks are those where global-factor volatility over the trailing 26 weeks is above its trailing 3-year 67th percentile, using past data only.
- **C_predictive.** Only for validated lead–lag pairs where the outside variable leads. Baseline: the focal's previous week and the market's previous week. One-step expanding-window forecasts over the confirmation window, Clark–West test, out-of-sample R² must be above 0.
- **Monthly track.** A_total and B_leadlag (±1 to ±6 months) for the two revenue series.

## 6. Windows and gates

- **Exploration** 2012–2019 (monthly track: 2013–2019).
  - Benjamini–Hochberg at q = 0.10 within each family **and each distance ring**, so remote rings get their own discovery budget and are not crowded out by close ones.
  - Minimum 260 exploration weeks and 200 confirmation weeks per pair, otherwise Insufficient Data. Monthly track: 72 and 60 months.
- **Confirmation** 2020 onward. These data have not been examined for any of these pairs: R1 used different, monthly, US-index targets.
  - A candidate is **Validated** if the confirmation estimate has the same sign and survives Benjamini–Hochberg at q = 0.05 among that family's candidates.
  - For A claims, the rank correlation must also agree.
  - Everything else is **Not Detected** and goes to the Dormant Registry.

## 7. Detection limits (synthetic, `synthetic_power.json`, 10 simulated worlds)

| True correlation | Adjusted association found | Lead–lag (2 weeks) found |
|---|---|---|
| 0.08 | 20% | 0% |
| 0.12 | 40% | 10% |
| 0.16 | 60% | 30% |
| 0.20 | 80% | 90% |
| 0.25+ | 100% | 100% |

False validations: 1 in 10 simulated runs, outside total association (which is real by construction in a world with a common factor). These synthetic results validate the method. They are not evidence about real markets.

## 8. Monitoring and lifecycle

**Monitoring.** For each validated relationship, these use only information available at each week:
- rolling 52-week correlation with a 95% interval;
- correlation behaviour: stable, strengthening, weakening or reversing, judged against the confirmation estimate's position relative to that interval;
- for association claims, a divergence z-score. This is the 13-week cumulative residual from a trailing 104-week reference regression. Above 2 and rising is "diverging". Falling back from above 2 is "converging". Convergence is never implied to be inevitable.

**Lifecycle replay** (historical replay, not live monitoring), A_adjusted family, at year-end checkpoints 2021–2025 and the latest week:
- screen every dormant pair on the trailing 3 years (Benjamini–Hochberg q = 0.10 per ring) and mark hits as Candidates;
- at the next checkpoint, confirm candidates on the weeks since (q = 0.05, same sign);
- reassess validated relationships on the fresh weeks. Not significant: Under Reassessment. Not significant twice, or significant in the opposite direction: Invalidated, and returned to dormant.

The replay overlaps the confirmation window. It demonstrates the lifecycle and is not additional evidence.

## 9. Registry

Every experiment unit (focal × outside variable × family) gets a persistent ID and an append-only event. Each event records state, best lag, effect size, p, q and n. That includes negative and insufficient-data results. R1 results are imported as their own events.

Any change to sections 3–8 after this commit creates R3.
