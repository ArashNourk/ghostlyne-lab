# ghostlyne-lab

Research lab for Ghostlyne: calibrated odds that a leveraged crypto position gets liquidated.

## cascade/ — cascade-adjusted wick odds
Question: does knowing how leverage is positioned (open interest build-up, funding, long/short crowding) improve
next-day liquidation-wick odds beyond the volatility texture model, asymmetrically (crowded longs -> down-wicks)?

- `fetch.py` downloads free Binance USD-M history from data.binance.vision (daily candles, funding, 5-minute positioning metrics).
- `experiment.py` builds features known at the prior day's close, fits walk-forward models (monthly refit, test from 2023),
  scores them against the textbook ATR random-walk model, and writes `results/report.md` and `results/results.json`.
- The workflow in `.github/workflows/cascade.yml` runs both on every push and commits the results.

## engine/ — Ghostlyne Odds (live)
Every day at 00:07 UTC `engine/daily.py` forecasts, for 28 perpetuals, the probability that a position opened at the
UTC open is liquidated before the UTC close at 40x / 20x / 15x / 10x / 7x / 5x (isolated margin, ~0.5% maintenance),
scores the previous day, appends both to the hash-chained ledger in `ledger/`, and writes `docs/data.json`.
The page in `docs/` is served by GitHub Pages. `engine/backtest.py` is the walk-forward calibration check (`results/odds_backtest.md`).
Set `waitlist_url` or `contact_email` in `engine/config.json` to open early-access requests.
