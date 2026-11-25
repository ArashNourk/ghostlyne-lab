# Ghostlyne intraday: go / no-go gate for the paid tier

Written and committed **before any intraday data has been downloaded or examined**. The commit time is the proof. The
gate decides whether "live odds for your position" (liquidation and stop-loss survival over 1 to 8 hours) is built as a
paid product. If it fails, the paid intraday tier is not built.

## The question

Can a Ghostlyne intraday model estimate the probability that a position's price moves against it by at least a distance
*d* within *h* hours, clearly better than strong standard models, in a crash year, a calm year and the most recent period?

## Target

- For each market *i* (the 28 Binance USD-M perpetuals), each origin *t* (every hour on the hour, UTC) and each horizon
  *h* in {1, 4, 8} hours: the maximum adverse excursion of the **mark price** over (t, t+h], from 1-minute mark-price
  candles, relative to the mark price at *t*. Downward for longs, upward for shorts.
- The model forecasts the whole survival curve P(excursion ≥ d). It is scored at fixed distances
  d ∈ {1%, 2%, 3%, 5%, 8%, 12%}: 1 to 3% is the stop-loss zone, 5 to 12% the liquidation zone (about 20x down to 8x isolated).
- Information: only data with timestamps before *t*.

## Opponents (the bar to beat)

1. **Intraday GARCH(1,1)-t** on 1-hour returns, converted to barrier probabilities by simulation of intra-horizon paths.
2. **HAR range model**: heterogeneous autoregressive model of Garman-Klass variance (1h, 4h, 24h, 7d components) with an
   intraday seasonal pattern, converted by the reflection principle with a discrete-monitoring correction.

Both get the identical walk-forward calibration as Ghostlyne. For each (distance, horizon) the **better opponent on the
test data** is the comparator, so Ghostlyne has to beat the best standard answer, not a straw man.

## Periods

- **Development** (all model building, feature choice, tuning): 2024-01-01 to 2025-06-30.
- **Test**, run once after the model is frozen in a second pre-registration:
  T1 = 2022 (crash regime), T2 = 2023 (calm regime), T3 = 2025-07-01 to 2026-10-31 (most recent).
  No intraday model has been evaluated on any of them. 2022 and 2023 were used for daily-horizon tests; that is disclosed.
- Walk-forward: models refit monthly on earlier data only.

## Gate: all must pass in each of T1, T2 and T3

| # | Criterion | Pass if |
|---|---|---|
| G1 | Accuracy, all distances and horizons pooled | Brier skill vs the best opponent ≥ +5%, 90% interval above zero |
| G2 | Accuracy in the liquidation zone (d ≥ 5%, h = 4 and 8) | Brier skill vs the best opponent > 0, 90% interval above zero |
| G3 | Breadth | positive skill in at least 78% of the markets with data in that period (22 of 28 when all trade; for example 17 of 22 in 2022) |
| G4 | Calibration of the product rule | the tightest distance with forecast ≤ 5% has a realized hit rate between 3.5% and 6.5%, with no regime-specific rules |

Intervals: week-block bootstrap (all markets and hours in a week resampled together). Also reported without pass/fail:
CRPS of the full excursion distribution, tail log score, PIT histograms by period, results by horizon and distance.

Why +5% and not more or less: the daily model's edge over GARCH-t was about 1 to 1.5%, too small for anyone to notice
or pay for. +5% across all three regimes is a margin a trader can feel in fewer surprise stop-outs and liquidations.
Requiring it in a crash year, a calm year and the recent period rules out an edge that only exists in one regime.

## Build order (development period only)

Each step is kept only if it improves development out-of-sample scores over the previous step.

1. Data: 1-minute mark-price, 5-minute futures and spot candles, open interest (5-minute), funding, Deribit DVOL.
2. Opponents 1 and 2.
3. Ghostlyne base: range-based variance (Garman-Klass, HAR horizons), intraday seasonality, recent excursions, a
   continuous excursion model.
4. Additions, tested one at a time: open-interest velocity, perp–spot basis, Deribit BTC/ETH implied volatility as a
   market-wide regime and event signal, order-book depth if a clean history exists.
5. Tail model (extreme value / self-exciting jumps) only if steps 3 and 4 show tail miscalibration.

## Amendment 1 (before any intraday data was downloaded)

- G3 clarified: several markets (PEPE, SUI, ARB, APT, OP and others) did not trade on Binance Futures for all of 2022 or
  2023. The breadth criterion is 78% of the markets with data in each test period, rounded up.
- Data sources fixed: perp–spot gap from Binance premium-index candles (no spot join); open interest from Binance's daily
  5-minute metrics files (from about December 2021 for most markets; earlier periods have no open-interest features and
  the positioning step is evaluated only where data exist); Deribit DVOL from April 2021.
