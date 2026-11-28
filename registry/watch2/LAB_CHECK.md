# WATCH2 lab check (simulated markets, not evidence about Bitcoin)

Run 2026-11-28, before any real data. Purpose: show that the harness finds a real advantage when one exists, and does not invent one when none does. Every number below comes from the frozen code (`FREEZE.json`), with Amendments 1 and 2 in force.

## Formula
The three-outcome first-passage formula agrees with Monte Carlo (continuity-corrected) within **0.23 pp** across five cases. The limit is 0.5 pp. Run: `python3 fp3.py`.

## Markets
- **sv**: volatility clusters with shocks and a daily rhythm, and returns are fat-tailed (Student t, 5 degrees of freedom).
- **const**: volatility never changes. This is the negative control.

Each market is 6 years of 5-minute paths, seen by the models only as **hourly candles**, the resolution Analyst provides. Development is the first 3.5 years; a scenario's whole window must end before the split. Confirmation is the rest, about 131,000 scenarios. Seeds 101–105 and 201–205 were used for nothing else. Calibration, thresholds and regime cut points are fitted on development scenarios only.

## Results on confirmation data (ambiguous candles counted as stop first; gates use the worst of all three resolutions)
| market, seed | Brier G vs CV, relative [95% CI, monthly blocks] | absolute | worst ambiguity resolution | by volatility regime, low / mid / high | recall with ≥1 h warning, G vs ATR and PROX | G vs best benchmark | false warnings per 100 scenarios, G vs ATR | median lead, G vs best | H3 same price, different risk | gates passed |
|---|---|---|---|---|---|---|---|---|---|---|
| sv 101 | +10.5% [+8.6%, +12.6%] | +0.047 | +10.5% | +11.4% / +8.3% / +11.7% | 61% vs 54% ATR, 52% PROX | 1.07× (CV-level) | 12.5 vs 12.5 | 3 h vs 4 h | +21.0% | all pass |
| sv 102 | +9.0% [+7.0%, +11.0%] | +0.042 | +9.0% | +7.6% / +7.5% / +10.7% | 62% vs 55% ATR, 49% PROX | 1.06× (CV-level) | 13.2 vs 13.5 | 3 h vs 4 h | +19.8% | all pass |
| sv 103 | +9.6% [+8.1%, +11.3%] | +0.043 | +9.6% | +10.1% / +8.4% / +10.0% | 63% vs 57% ATR, 50% PROX | 1.06× (CV-level) | 13.4 vs 13.5 | 3 h vs 4 h | +20.4% | all pass |
| sv 104 | +9.5% [+7.9%, +11.1%] | +0.042 | +9.5% | +12.2% / +7.6% / +9.2% | 62% vs 55% ATR, 53% PROX | 1.14× (ATR) | 12.4 vs 12.5 | 3 h vs 3 h | +20.2% | all pass |
| sv 105 | +8.7% [+6.6%, +10.8%] | +0.039 | +8.7% | +7.7% / +8.1% / +10.6% | 60% vs 53% ATR, 52% PROX | 1.12× (CV-level) | 12.1 vs 11.9 | 3 h vs 3 h | +19.0% | all pass |
| const 201 | +0.1% [-0.0%, +0.1%] | +0.000 | +0.1% | +0.1% / -0.0% / +0.1% | 58% vs 55% ATR, 55% PROX | 0.99× (CV-level) | 11.2 vs 11.8 | 3 h vs 3 h | never triggered | H1c |
| const 202 | +0.1% [-0.0%, +0.1%] | +0.000 | +0.1% | +0.1% / -0.0% / +0.1% | 59% vs 54% ATR, 55% PROX | 1.01× (CV-level) | 11.5 vs 11.5 | 3 h vs 3 h | never triggered | H1c |
| const 203 | +0.1% [+0.0%, +0.2%] | +0.000 | +0.1% | +0.2% / -0.0% / +0.1% | 60% vs 55% ATR, 56% PROX | 1.00× (CV-level) | 11.6 vs 11.7 | 3 h vs 3 h | never triggered | H1c |
| const 204 | +0.1% [-0.0%, +0.1%] | +0.000 | +0.1% | +0.1% / -0.1% / +0.1% | 60% vs 55% ATR, 56% PROX | 1.01× (CV-level) | 11.7 vs 12.0 | 3 h vs 3 h | never triggered | H1c |
| const 205 | +0.1% [-0.0%, +0.1%] | +0.000 | +0.1% | +0.1% / +0.0% / +0.1% | 61% vs 55% ATR, 55% PROX | 0.99× (CV-level) | 12.3 vs 12.3 | 3 h vs 3 h | never triggered | H1c |

Weekly and quarterly bootstrap blocks give intervals within ±0.6 pp of the monthly ones in every run (`lab/*.json`, `H1_block_sensitivity`). Ambiguous candles were 0.00–0.03% of simulated scenarios. Real Bitcoin hours with 2% or more of range will produce more of them, which is why every gate must pass under all three resolutions.

## What this shows
- **Where volatility clusters**, G is 9–11% more accurate than constant volatility. It is better in every volatility regime, calibrated, and the "same price, different risk" subset improves by about 20%. Every gate passes under every ambiguity resolution in all five independent markets.
- **Where it doesn't**, G's advantage is 0.05–0.11%. It is sometimes statistically above zero, probably from using fresher range information, but 50 times smaller than the 5% gate. Every advantage gate correctly fails.
- **Warnings.** G catches 60–63% of stop-outs with at least one hour of warning, versus 53–57% for ATR alerts and 49–53% for proximity alerts, at the same false-warning count (about 12–13 per 100 scenarios). Its median warning is 3 hours, the same as or 1 hour shorter than the constant-volatility level rule: it catches more stop-outs, not earlier ones.
- **Not everything is from dynamic volatility.** Even in the control market, probability-level alerts (CV or G) beat ATR and proximity alerts (58–61% versus about 55%), because they account for time remaining.

## What it doesn't show
Anything about Bitcoin. Whether Bitcoin's volatility clusters enough, measured on CoinGecko's hourly aggregate prices, to pass these gates is answered only by `confirm.py` on licensed data.
