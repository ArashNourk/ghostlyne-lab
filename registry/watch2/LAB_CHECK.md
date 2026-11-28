# WATCH2 lab check under Amendment 3 (2026-11-28)

These are simulated markets only; no real Bitcoin data has been used. The results replace the 10a53d4 lab check, whose favourable H1 numbers depended on comparing G only with constant volatility and on a variance floor fitted on the whole sample.

- **sv** markets have stochastic, clustered volatility (the conditions Watch is meant for).
- **const** markets have constant volatility and are negative controls: no model should beat the price-only view there, and no volatility signal should exist.

Every scenario is a 24-hour watch unless marked 8h. Figures are for the "drop" treatment of ambiguous candles. Gates require all three treatments, and the stop and target treatments give the same pattern.

## Results by seed
| market, seed | DV half-life | H1: G vs best benchmark [95% CI] | H2: G recall ratio, matched 20% | H2c: G / DV recall vs conventional alerts, matched 20% | H3: G / DV vs price-only at unchanged price | H4: volatility attribution validity [CI] | gates passed |
|---|---|---|---|---|---|---|---|
| const 201 | 96h | -0.00% vs V1 [-0.11%, +0.10%] | 0.994× vs V1-level | 1.089× / 1.091× vs PROX | +0.01% / +0.06% | -0.009 [-0.032, +0.010] | H1c H2c_G H2c_DV |
| const 202 | 96h | -0.04% vs V1 [-0.11%, +0.03%] | 0.995× vs V1-level | 1.085× / 1.085× vs PROX | +0.06% / -0.10% | -0.017 [-0.043, +0.008] | H1c H2c_G H2c_DV |
| const 203 | 96h | +0.01% vs V1 [-0.09%, +0.10%] | 1.001× vs CV-level | 1.082× / 1.080× vs PROX | +0.11% / +0.00% | +0.000 [-0.019, +0.020] | H1c H2c_G H2c_DV |
| const 204 | 96h | +0.01% vs V1 [-0.13%, +0.14%] | 1.001× vs V1-level | 1.094× / 1.092× vs PROX | -0.02% / -0.08% | -0.012 [-0.031, +0.006] | H1c H2c_G H2c_DV |
| const 205 | 96h | +0.07% vs CV [-0.02%, +0.15%] | 1.000× vs DV-level | 1.090× / 1.090× vs PROX | +0.10% / -0.00% | -0.005 [-0.022, +0.012] | H1c H2c_G H2c_DV |
| sv 101 | 6h | +0.31% vs DV [-0.24%, +0.85%] | 1.010× vs DV-level | 1.130× / 1.119× vs ATR | +13.15% / +10.88% | +0.042 [+0.009, +0.070] | H1c H2c_G H2c_DV H3_G H3_DV H4 |
| sv 102 | 6h | +0.73% vs DV [+0.35%, +1.13%] | 1.014× vs DV-level | 1.139× / 1.123× vs ATR | +15.22% / +10.57% | +0.043 [+0.019, +0.063] | H1c H2c_G H2c_DV H3_G H3_DV H4 |
| sv 103 | 6h | +0.28% vs DV [-0.16%, +0.74%] | 1.021× vs DV-level | 1.121× / 1.098× vs ATR | +13.29% / +11.24% | -0.019 [-0.045, +0.007] | H1c H2c_G H2c_DV H3_G H3_DV |
| sv 104 | 6h | +0.38% vs DV [-0.12%, +0.84%] | 1.032× vs DV-level | 1.140× / 1.105× vs ATR | +11.26% / +9.22% | +0.037 [+0.017, +0.055] | H1c H2c_G H2c_DV H3_G H3_DV H4 |
| sv 105 | 6h | +0.07% vs DV [-0.41%, +0.52%] | 1.026× vs DV-level | 1.121× / 1.093× vs ATR | +9.98% / +8.23% | +0.018 [-0.006, +0.039] | H1c H2c_G H2c_DV H3_G H3_DV |
| sv 101 (8h, reported only) | 6h | +3.41% vs DV [+2.76%, +4.08%] | 1.043× vs DV-level | 1.176× / 1.127× vs ATR | +13.38% / +9.69% | -0.015 [-0.039, +0.007] | H2c_G H2c_DV H3_G |

H1 needs at least +5% with the interval above zero. H2 and H2c need at least 1.05× with the interval above 1, plus the operational false-warning conditions. The H3 figure is the relative Brier improvement over CV at checkpoints where price is within 0.25% of the start and the model's stop-first probability has moved at least 10 pp.

## What this shows
1. **No algorithmic edge over a simple dynamic model.** G beats CV by 9–10% and V1 by 5–7% in volatile markets. Against an hourly EWMA (DV), however, it gains only 0.07–0.73% and fails H1 and H2 in every seed. Under the decision rules the product model is therefore DV, and no proprietary-model claim may be made unless real data says otherwise.
2. **The concept beats conventional alerts.** Probability alerts catch 9–14% more stop-outs than price-proximity or ATR alerts at the same 20% false-warning rate (H2c), for both G and DV.
   - In the constant-volatility controls the advantage is smaller (8–9%). That part comes from time-awareness alone: the probability accounts for how much of the watch remains.
   - The extra 3–5 points in volatile markets come from tracking volatility.
   - This is recall at equal false warnings, not earlier warning. Median lead times are reported separately in `lab/*.json`.
3. **"Same price, different risk" is real where volatility moves, and absent where it doesn't.**
   - At unchanged price, both G and DV beat the price-only view by 8–15% in every volatile seed.
   - Where they said risk rose, stop-outs were in fact more frequent, and both groups were calibrated.
   - In every control, H3 fails, as it should: there, the only change at unchanged price is time.
4. **Attribution is not reliable yet.** H4 passes in three of five volatile seeds and fails at 8h. Under the decision rules, volatility attribution cannot be shown unless real data passes it.
5. **The controls behave.** Every negative control gives H1 ≈ 0, H3 ≈ 0 and no attribution signal. On those three tests the harness does not manufacture an advantage.
6. **The 8-hour horizon** is reported only. G's advantage over DV grows to 3.4%, still under the 5% bar. Calibration of G fails in one bin there (the "neither" class at 5–10%), and DV's H3 risk-rose group was too small to judge.

## Implication for the real run
The real Bitcoin run decides which of these claims, if any, may be made publicly:
- the conventional-alert claim (H2c) for the product model;
- the headline (H3);
- the model-advantage claim (H1, H2), which is expected to fail.

The founder has asked that nothing be described as an algorithmic advantage unless H1 and H2 pass on real data.
