# ghostlyne-lab

Research lab for Ghostlyne: calibrated odds that a leveraged crypto position gets liquidated.

## cascade/ — cascade-adjusted wick odds
Question: does knowing how leverage is positioned (open interest build-up, funding, long/short crowding) improve
next-day liquidation-wick odds beyond the volatility texture model, asymmetrically (crowded longs -> down-wicks)?

- `fetch.py` downloads free Binance USD-M history from data.binance.vision (daily candles, funding, 5-minute positioning metrics).
- `experiment.py` builds features known at the prior day's close, fits walk-forward models (monthly refit, test from 2023),
  scores them against the textbook ATR random-walk model, and writes `results/report.md` and `results/results.json`.
- The workflow in `.github/workflows/cascade.yml` runs both on every push and commits the results.
