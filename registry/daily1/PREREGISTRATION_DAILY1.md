# DAILY1 pre-registration: the Morning Line engine

Committed before any real-price result was computed. Code: `daily1/daily1.py` (this commit). Promise under test: "Know your risk before the day begins."

## Data
Coinbase Exchange public daily candles, BTC-USD and ETH-USD, UTC days, from 2015-07-20 (ETH from listing). Prices are used inside the run only; outputs are derived statistics. (Publication rights for a live product are a separate check.)

## Engine (M1, fixed)
- Daily volatility proxy: Parkinson range. Forecast for day t from information to day t-1: HAR regression on log Parkinson (lag 1, 5-day mean, 22-day mean, weekend flag), refit monthly on all prior data, log-normal bias correction.
- Standardized excursions from the open, z_up = ln(High/Open)/sigma, z_dn = ln(Open/Low)/sigma, over the trailing 4 years.
- Range at coverage L: open x exp(+/- k*sigma), k = L-quantile of max(z_up, z_dn). "In range" means the whole day's high and low stay inside. Published level: 70%; 50% and 90% reported.
- Touch probability for a level d% above or below the open (d = 1, 2, 3, 5, 8, 12, 18): share of trailing standardized excursions reaching ln-distance/sigma.

## Baselines
- B0: trailing 365-day raw frequency of reaching that distance (no volatility model).
- B1: trailing 30-day close-to-close volatility in place of the HAR forecast.

## Evaluation
Walk-forward, 2018-01-01 to the last complete day. Coverage pooled, by year, and by volatility tercile. Touch reliability in bins [0,2,5,10,20,40,70,100]%. Brier skill of M1 vs B0 and B1, day-block bootstrap (30-day blocks, 2,000 draws, seed 20261127). Tail: all touch forecasts at or below 3%, observed/expected with Poisson interval.

## Gates (each asset)
- G1 coverage: 70% range pooled coverage in [66%, 74%] and every calendar year in [60%, 80%].
- G2 touch calibration: every bin with at least 200 forecasts has its predicted mean inside the observed Wilson 95% interval, or within max(2 pp, 25% relative).
- G3 skill: Brier skill lower 95% bound > 0 against both B0 and B1.
- G4 tail: observed/expected ratio for forecasts at or below 3% in [0.67, 1.5].

## Lab check (done before registration)
On synthetic GARCH-like prices the code recovers calibration (70% coverage 0.698/0.690; all reliability bins pass; tail ratio 1.09/1.23). This shows the code works when the model fits; it says nothing about real markets.

## Decision rule
All four gates pass on BTC: build the live shadow run (publicly timestamped daily lines, not yet sold). G1 or G2 fails: the published probabilities would mislead; redesign before any public line. G3 fails alone: the line is honest but no better than a simple rule, so the product competes on experience only, and we say so.
