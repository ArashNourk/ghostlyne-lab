# WATCH2 lab check under Amendment 4 (2026-11-28)

These are simulated markets only; no real Bitcoin data has been used.

- The Amendment 4 corrections change how results are judged and reported, not the underlying numbers. Every figure below matches the Amendment 3 run (commit 72ad7b1) exactly.
- The 10a53d4 lab check is superseded: its favourable H1 numbers depended on comparing G only with constant volatility, and on a variance floor fitted on the whole sample.

**Markets:**
- **sv** markets have stochastic, clustered volatility, the conditions Watch is meant for.
- **const** markets have constant volatility and are negative controls: no model should beat the price-only view there, and no volatility signal should exist.

**How to read the figures:**
- Every scenario is a 24-hour watch unless marked 8h.
- Figures are for the "drop" treatment of ambiguous candles. Gates and the production decision require all three treatments, and the stop and target treatments give the same pattern.
- "Production" applies the Amendment 4 rule: G only if H1 and H2 both pass, otherwise DV. It lists what that model is authorized to claim.

## Results by seed
| market, seed | DV half-life | H1: G vs best benchmark [95% CI] | H2: G recall ratio, matched 20% | H1c calibration, G / DV | H2c: G / DV recall vs conventional alerts, matched 20% | H3: G / DV vs price-only at unchanged price | production model: authorized |
|---|---|---|---|---|---|---|---|
| const 201 | 96h | -0.00% vs V1 [-0.11%, +0.10%] | 0.994× vs V1-level | pass / pass | 1.089× / 1.091× vs PROX | +0.01% / +0.06% | DV: publish probabilities, conventional alert claim |
| const 202 | 96h | -0.04% vs V1 [-0.11%, +0.03%] | 0.995× vs V1-level | pass / pass | 1.085× / 1.085× vs PROX | +0.06% / -0.10% | DV: publish probabilities, conventional alert claim |
| const 203 | 96h | +0.01% vs V1 [-0.09%, +0.10%] | 1.001× vs CV-level | pass / pass | 1.082× / 1.080× vs PROX | +0.11% / +0.00% | DV: publish probabilities, conventional alert claim |
| const 204 | 96h | +0.01% vs V1 [-0.13%, +0.14%] | 1.001× vs V1-level | pass / pass | 1.094× / 1.092× vs PROX | -0.02% / -0.08% | DV: publish probabilities, conventional alert claim |
| const 205 | 96h | +0.07% vs CV [-0.02%, +0.15%] | 1.000× vs DV-level | pass / pass | 1.090× / 1.090× vs PROX | +0.10% / -0.00% | DV: publish probabilities, conventional alert claim |
| sv 101 | 6h | +0.31% vs DV [-0.24%, +0.85%] | 1.010× vs DV-level | pass / pass | 1.130× / 1.119× vs ATR | +13.15% / +10.88% | DV: publish probabilities, conventional alert claim, same price headline |
| sv 102 | 6h | +0.73% vs DV [+0.35%, +1.13%] | 1.014× vs DV-level | pass / pass | 1.139× / 1.123× vs ATR | +15.22% / +10.57% | DV: publish probabilities, conventional alert claim, same price headline |
| sv 103 | 6h | +0.28% vs DV [-0.16%, +0.74%] | 1.021× vs DV-level | pass / pass | 1.121× / 1.098× vs ATR | +13.29% / +11.24% | DV: publish probabilities, conventional alert claim, same price headline |
| sv 104 | 6h | +0.38% vs DV [-0.12%, +0.84%] | 1.032× vs DV-level | pass / pass | 1.140× / 1.105× vs ATR | +11.26% / +9.22% | DV: publish probabilities, conventional alert claim, same price headline |
| sv 105 | 6h | +0.07% vs DV [-0.41%, +0.52%] | 1.026× vs DV-level | pass / pass | 1.121× / 1.093× vs ATR | +9.98% / +8.23% | DV: publish probabilities, conventional alert claim, same price headline |
| sv 101 (8h, reported only) | 6h | +3.41% vs DV [+2.76%, +4.08%] | 1.043× vs DV-level | fail / pass | 1.176× / 1.127× vs ATR | +13.38% / +9.69% | DV: publish probabilities, conventional alert claim |

## Thresholds
- H1 needs at least +5% with the interval above zero.
- H2 and H2c need at least 1.05× with the interval above 1, plus the operational false-warning conditions.
- H3 is the relative Brier improvement over CV at checkpoints where price is within 0.25% of the start but the model's stop-first probability has moved at least 10 pp.

## What this shows
1. **No algorithmic edge over a simple dynamic model.**
   - In volatile markets, G beats CV by 9–10% and V1 by 5–7%.
   - Against the hourly EWMA (DV), it gains only 0.07–0.73%, and fails H1 and H2 in every seed.
   - The production model is DV in every run, and the model-advantage claim is never authorized. This negative result is accepted.
2. **DV passes its own calibration gate in every run,** under all three treatments of ambiguous candles, at 24 hours and at 8 hours. G fails calibration at 8 hours, which would not matter here because G is not the production model.
3. **The concept beats conventional alerts.**
   - At the same 20% false-warning rate, DV alerts catch 9.3–12.3% more stop-outs than price-proximity or ATR alerts in volatile markets (G: 12–14%).
   - In the constant-volatility controls the advantage is 8–9%. That part comes from time-awareness alone; tracking volatility adds the rest.
   - This is recall at equal false warnings, not earlier warning.
4. **"Same price, different risk" holds where volatility moves, and only there.**
   - DV beats the price-only view by 8.2–11.2% at unchanged price in every volatile seed, and is calibrated where it said risk rose and where it said risk fell.
   - In every control, H3 fails, as it should.
   - At 8 hours, too few checkpoints showed DV risk rising to judge, so the headline is not authorized there.
5. **Attribution is reported only.** H4 passes in three of five volatile seeds, but it measures uncalibrated G. It authorizes nothing, and the initial release shows no attribution.
6. **The controls behave.** Every negative control gives H1 ≈ 0, H3 ≈ 0 and no attribution signal.

## Achieved false-warning rates (Amendment 4, point 4)
- **At the 20% gate level,** every method's achieved rate is within 0.005 pp of 20% in every run, so tied thresholds do not affect any H2 or H2c result.
- **At the reported 30% level,** price-proximity alerts overshoot: they achieve 31.4–32.8%, a gap of 1.4–2.8 pp. Many scenarios share the same starting distance to the stop, so their scores tie at the threshold. The gap favours the proximity rule, which gets the extra recall that comes with the extra false warnings. It is flagged in the results (`tie_discrepancy`) and is not a gate.
- No other method or level has a gap above 0.5 pp.

## Implication for the real run
The production model will almost certainly be DV. On real Bitcoin data, the run decides three things:
- whether DV is calibrated (H1c_DV), which decides whether we publish probabilities;
- whether its alerts beat conventional alerts (H2c_DV);
- whether the headline holds (H3_DV).
