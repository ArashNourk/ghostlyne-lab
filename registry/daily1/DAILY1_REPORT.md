# DAILY1 results: the Morning Line engine passes every gate

Pre-registration: `PREREGISTRATION_DAILY1.md`, commit c7bef9b. Code unchanged after registration. Results: `results/DAILY1.json` (derived statistics only). Walk-forward evaluation from 2018-01-01: 3,253 days for BTC, 2,949 for ETH.

| Gate | BTC | ETH |
|---|---|---|
| G1 coverage of the 70% range | Pass: 71.2% pooled; years 68.0% to 74.2% | Pass: 70.7% pooled; years 65.8% to 74.2% |
| G2 touch calibration (7 bins) | Pass: every bin | Pass: every bin |
| G3 Brier skill vs raw frequency / simple volatility | Pass: 8.2% (CI 6.5–10.1%) / 4.2% (3.4–5.1%) | Pass: 6.0% (4.7–7.3%) / 4.4% (3.5–5.3%) |
| G4 tail (forecasts at or below 3%) | Pass: observed/expected 0.84 (120 vs 143) | Pass: 1.16 (134 vs 116) |

The 50% and 90% ranges are also on target: BTC 50.7% and 90.8%; ETH 49.3% and 90.2%.

## What this does and does not mean
- It means the engine's probabilities can be stated publicly: when it says 7 in 10, the day stayed in range about 7 times in 10, in every year from 2018 to 2026, for both assets.
- It does not mean an edge in direction or returns. The skill over simple rules is real but modest (4–8% Brier improvement). The product's promise is honest risk, not prediction.

## Where it is imperfect (to improve before or during the live shadow run)
- **Regime tilt:** the range is slightly too narrow on calm days (BTC 68.4%, ETH 67.2% coverage) and slightly too wide on wild days (75.1%, 74.9%).
- **BTC touch odds run slightly high** in the 2–20% bins, e.g. 3.2% forecast vs 2.6% observed. That errs on the cautious side.
- **ETH's 2025 coverage was 65.8%,** inside the gate but the lowest year.
- **Days are UTC.** The product publishes at each reader's local morning, so the live engine must re-anchor the 24-hour window to the publish time (hourly data).
- **The last day in the run (2026-11-27) was incomplete** when fetched. One day in roughly 3,000; it will be excluded going forward.

## Decision (pre-registered)
All gates pass on BTC, so the next step is the live shadow run. Publicly timestamped daily lines are kept on the score wall and not sold, while we fix the regime tilt and the local-time anchor. Publication rights for live price data are checked before the first public line.
