# WATCH2 pre-registration: scenario probabilities, divergence and attribution

Registered 2026-11-28, before any data for this experiment was acquired or any WATCH2 result computed. Status: protocol only. The run needs licensed intraday Bitcoin prices, which require a purchase the founder has not yet authorized. Engine V1 (`daily1/daily1.py`, frozen) is used unchanged as one input and one benchmark.

Claim under test: **Ghostlyne Watch detects changes in a trade's risk that ordinary price alerts cannot reliably capture.** The website currently says only that risk *can* change before price alerts trigger. Stronger wording is allowed only by the decision rules below.

## 1. Data
- BTC/USD OHLC from the licensed source, at the finest uniform resolution it provides over the whole sample and no coarser than 1 hour. The resolution is fixed in a dated amendment to this file before any outcome is computed.
- Sample from 2018-02-09 (first date of the source's range data) to the last complete month before the confirmation run.
- Timestamps normalized to candle close (UTC). Incomplete candles dropped. Any gap longer than 2 candles excludes every scenario that overlaps it. Fetching fails loudly; nothing is silently filled.

## 2. Scenarios (fixed grid, never selected on outcome)
- Start times: every 4 hours on the hour (00, 04, 08, 12, 16, 20 UTC).
- Horizon: 24 hours (primary); 8 hours (secondary, reported only).
- Direction: long and short.
- Stop distance: 1%, 2%, 3%. Target distance: 1%, 2%, 3%, 4%. That gives 24 scenarios per start time.
- Outcome: **target first**, **stop first**, or **neither** before expiry, read from candle highs and lows. If both levels are touched inside one candle, the outcome is stop first (conservative). A sensitivity analysis excluding those cases is reported.
- Checkpoints: the start, then every hour while the scenario is unresolved. Every forecast uses only information available at its checkpoint.
- Overlapping scenarios are correlated, so all uncertainty comes from a block bootstrap on calendar months (2,000 draws, seed 20261128).

## 3. Methods
Alert-only benchmarks (no probabilities):
- **PROX**: warn when price comes within k% of the stop.
- **ATR**: warn when the distance to the stop is below m × ATR(14) on the source's candles.

Probability benchmarks (driftless double-barrier first passage in log price, giving the three outcome probabilities):
- **CV**: volatility = trailing 30-day realized volatility, held constant for the scenario. Probabilities change only with price and time. This is what the website demonstration currently does.
- **V1**: volatility = the frozen V1 daily forecast at scenario start, held constant.

Candidate:
- **G**: the same first-passage calculation, but volatility is re-forecast at every checkpoint. The forecast is a HAR-type regression on intraday realized variance (last 1 h, 6 h and 24 h) plus the V1 daily forecast and a time-of-day factor, refit monthly. Variance over the remaining horizon reverts log-linearly toward the daily forecast. At most 8 fitted parameters.
- **Extensions**, each tested separately and kept only if section 6 allows:
  - **G+A (asymmetry)**: separate up and down scales from the trailing semivariance ratio.
  - **G+R (regime)**: a two-state flag (trailing 7-day realized volatility above its trailing one-year 80th percentile) that shifts the HAR intercept.
- Numerical check before any real data: the first-passage series is checked against Monte Carlo, with outcome probabilities matching within 0.5 pp. On simulated prices with changing volatility, G must beat CV. That only shows the code works when the model fits.

## 4. Development and confirmation
- **Development**, 2018-02-09 to 2022-12-31. Iteration is allowed here within the limits above: model form, extensions, and alert thresholds for every method.
- **Confirmation**, 2023-01-01 to the last complete month. Run once. The code's SHA-256 hash is recorded in `registry.jsonl` before the run. Nothing is changed after confirmation results are seen.
- **Prospective**: after launch, every live Watch scenario is scored and published monthly.

## 5. Hypotheses and gates (judged on confirmation data only)
- **H1 Probability skill.** Measured by the multiclass Brier score of the three outcomes over all checkpoints. G must improve on the better of CV and V1 by at least **5% relative**, with the 95% interval's lower bound above 0. Log loss is also reported.
- **H1c Calibration.** For each outcome class, use reliability bins of [0, 5, 10, 20, 30, 50, 70, 100]%. Every bin with at least 500 checkpoints must have its mean prediction inside the observed Wilson 95% interval, or within the larger of 2 pp and 20% relative. This is required before any probability from G is shown to users.
- **H2 Warning usefulness at matched false alarms.** Each method's first warning per scenario counts.
  - A false warning is a warning in a scenario where the stop is not touched before expiry.
  - Thresholds (k for PROX, m for ATR, a rise of θ pp in stop-first probability for CV and G) are set on development data so that each method has a 20% false-warning rate. Rates of 10% and 30% are reported as well.
  - Primary metric: recall, meaning the share of stop-first scenarios warned at least 30 minutes before the stop is touched.
  - G passes if its recall is at least **1.05 × the best of PROX, ATR and CV**, the 95% interval of that ratio lies above 1, and G's false-warning rate on confirmation data falls within 15–25%. Outside that band the thresholds are unstable, and that counts as a fail.
- **H3 Same price, different risk.** Take the checkpoints where price has moved at most 0.25% since the scenario started, yet G and CV disagree on the stop-first probability by at least 10 pp. On that subset, G's Brier score must beat CV's by at least 5% relative, with the interval above 0. The subset must also hold at least 1,000 checkpoints across at least 24 distinct months; otherwise the result is "insufficient evidence", not a pass.
- **H4 Attribution.** The change in stop-first probability between the start and a checkpoint is split by an exact Shapley decomposition over the factors in the final model: price, time remaining, volatility, plus asymmetry and regime only if kept.
  - Additivity: the factor contributions sum to the total change within 0.1 pp.
  - Validity: the volatility contribution must show a positive Spearman correlation with the next 6 hours' realized-volatility surprise (realized ÷ forecast), with the interval above 0. Any other kept factor gets the analogous check against its own realized quantity.
  - Attribution is labelled "model attribution, not causation".

## 6. Complexity budget
An extension (A or R) enters the confirmation model only if, on development data, adding it to G improves the multiclass Brier score by at least 1% relative, with the interval above 0. On confirmation data it must still improve the score (interval above 0), or it is removed from the product and from attribution.

## 7. Decision rules
- **H1, H1c and H2 pass**: we may say Watch's probabilities are calibrated and that it warned earlier than price and ATR alerts in historical tests, quoting the numbers. The tagline may drop "can" only if H2 passes.
- **H3 passes**: "Same price. Different risk." may be used, with the subset's numbers.
- **H4 passes for a factor**: that factor may appear in user-facing attribution. Factors that fail or were removed never appear.
- **H1 and H1c pass, H2 fails**: Watch sells calibrated probabilities and Risk Receipts, with no lead-time claims.
- **H1 fails**: dynamic volatility adds nothing measurable. Watch runs on CV or V1 as a convenience product, makes no claim of an analytical edge, and its price is reconsidered.
- **H1c fails**: no probability from G is published.
- **Any failure**: no retuning on confirmation data. A new attempt needs a new registration, tested on prospective data only.

## 8. Demonstration integrity
Website demonstrations show stop-first, target-first and neither outcomes. Until confirmation results exist, every demonstration states that it uses constant volatility and is not tested performance. After confirmation, any example shown is drawn at random from the confirmation scenarios, and the draw procedure is published. No example is selected for its outcome.
