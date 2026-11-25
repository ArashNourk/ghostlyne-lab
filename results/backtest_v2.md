# Ghostlyne Odds: backtest v2

Walk-forward, model from 2023-01-01, evaluated 2024-01-01 to 2026-11-23, 28 Binance USD-M perpetuals.
Information set: complete days before d plus day d truncated at 23:15 UTC (identical to production). Labels: Binance mark price reaching
a standardized isolated-margin liquidation level (maintenance margin 0.5%) for a position entered at the next UTC open.
Every model, including every baseline, is calibrated by the same walk-forward isotonic procedure and made monotone across leverage.
Skill = 1 - Brier(Ghostlyne)/Brier(baseline). 90% intervals from a week-block bootstrap (markets on the same days resampled together).

| Position | Liq. dist. | Base rate | Best baseline | Skill vs best (90% CI) | Skill vs textbook | AUC Ghostlyne / best |
|---|---|---|---|---|---|---|
| long 40x | 2.0% | 56.95% | Textbook (ATR, normal) | +0.014 (+0.006, +0.023) | +0.014 | 0.672 / 0.657 |
| long 20x | 4.5% | 25.99% | GARCH(1,1)-t | +0.014 (+0.003, +0.025) | +0.024 | 0.688 / 0.669 |
| long 15x | 6.2% | 14.55% | GARCH(1,1)-t | +0.010 (-0.011, +0.026) | +0.023 | 0.702 / 0.676 |
| long 10x | 9.5% | 5.00% | GARCH(1,1)-t | -0.025 (-0.094, +0.018) | -0.017 | 0.716 / 0.680 |
| long 7x | 13.8% | 1.60% | Textbook (ATR, normal) | -0.019 (-0.059, +0.011) | -0.019 | 0.702 / 0.613 |
| long 5x | 19.5% | 0.59% | Textbook (ATR, normal) | -0.002 (-0.017, +0.008) | -0.002 | 0.681 / 0.566 |
| short 40x | 2.0% | 53.15% | GARCH(1,1)-t | +0.005 (-0.003, +0.013) | +0.008 | 0.651 / 0.646 |
| short 20x | 4.5% | 23.32% | GARCH(1,1)-t | +0.011 (+0.002, +0.020) | +0.021 | 0.684 / 0.670 |
| short 15x | 6.2% | 13.88% | GARCH(1,1)-t | +0.014 (+0.006, +0.022) | +0.026 | 0.695 / 0.677 |
| short 10x | 9.5% | 5.50% | GARCH(1,1)-t | +0.012 (+0.003, +0.020) | +0.023 | 0.723 / 0.696 |
| short 7x | 13.8% | 2.06% | GARCH(1,1)-t | +0.001 (-0.028, +0.023) | +0.007 | 0.740 / 0.714 |
| short 5x | 19.5% | 0.71% | Filtered historical simulation | -0.017 (-0.103, +0.030) | -0.013 | 0.748 / 0.678 |

Skill against every baseline:

| Position | Textbook (ATR, normal) | EWMA RiskMetrics | GARCH(1,1)-t | Filtered historical simulation | Rolling 1-year frequency |
|---|---|---|---|---|---|
| long 40x | +0.014 | +0.017 | +0.016 | +0.016 | +0.060 |
| long 20x | +0.024 | +0.016 | +0.014 | +0.016 | +0.055 |
| long 15x | +0.023 | +0.012 | +0.010 | +0.012 | +0.041 |
| long 10x | -0.017 | -0.023 | -0.025 | -0.021 | -0.006 |
| long 7x | -0.019 | -0.017 | -0.015 | -0.015 | -0.015 |
| long 5x | -0.002 | +0.002 | +0.003 | +0.002 | -0.000 |
| short 40x | +0.008 | +0.008 | +0.005 | +0.008 | +0.033 |
| short 20x | +0.021 | +0.019 | +0.011 | +0.020 | +0.048 |
| short 15x | +0.026 | +0.023 | +0.014 | +0.023 | +0.043 |
| short 10x | +0.023 | +0.022 | +0.012 | +0.023 | +0.034 |
| short 7x | +0.007 | +0.009 | +0.001 | +0.006 | +0.010 |
| short 5x | -0.013 | -0.007 | -0.005 | -0.017 | -0.007 |

By market (long, 20x/15x/10x pooled, vs best baseline): positive in 21 of 28 markets.
TRX +0.098, ETH +0.028, BTC +0.027, NEAR +0.025, OP +0.021, ALGO +0.020, ARB +0.014, APT +0.014, INJ +0.014, BCH +0.013, LTC +0.010, FIL +0.010, SOL +0.009, SUI +0.007, LINK +0.005, XLM +0.005, 1000PEPE +0.004, ETC +0.004, ATOM +0.004, AAVE +0.002, XRP +0.000, ADA -0.002, 1000SHIB -0.004, DOT -0.004, BNB -0.006, AVAX -0.009, DOGE -0.010, UNI -0.015

By market (short, 20x/15x/10x pooled, vs best baseline): positive in 23 of 28 markets.
TRX +0.140, DOT +0.028, SUI +0.024, ARB +0.022, SOL +0.021, 1000PEPE +0.020, ETC +0.020, 1000SHIB +0.020, FIL +0.019, ATOM +0.018, BCH +0.018, APT +0.016, UNI +0.015, AAVE +0.013, AVAX +0.012, XRP +0.012, ADA +0.011, INJ +0.006, NEAR +0.004, OP +0.004, ALGO +0.004, BTC +0.003, DOGE +0.002, LINK -0.001, LTC -0.001, ETH -0.003, BNB -0.008, XLM -0.023

## Max leverage at or below 5% modeled odds

For every market-day, the highest leverage whose forecast is at or below 5%. Realized = share of those recommended positions that were
actually liquidated (target: at or below 5%). A better model recommends more leverage at the same realized risk.

| Side | Method | Realized liq. rate (90% CI) | Mean forecast | Mean recommended leverage | Days with no level ≤5% |
|---|---|---|---|---|---|
| long | Ghostlyne | 3.11% (2.43, 3.81) | 2.75% | 10.0x | 1.2% |
| long | Textbook (ATR, normal) | 3.14% (2.38, 3.90) | 2.97% | 9.8x | 0.0% |
| long | EWMA RiskMetrics | 2.98% (2.26, 3.74) | 2.97% | 9.8x | 0.2% |
| long | GARCH(1,1)-t | 2.98% (2.31, 3.69) | 2.83% | 9.6x | 0.3% |
| long | Filtered historical simulation | 3.13% (2.41, 3.91) | 2.95% | 9.9x | 0.1% |
| long | Rolling 1-year frequency | 3.22% (2.45, 4.05) | 2.57% | 9.3x | 0.1% |

Ghostlyne long, by recommended leverage: 40x: 145 days, forecast 2.1%, realized 6.9%, 20x: 1401 days, forecast 2.7%, realized 3.4%, 15x: 2284 days, forecast 3.4%, realized 3.5%, 10x: 14476 days, forecast 3.0%, realized 3.2%, 7x: 9913 days, forecast 2.3%, realized 2.6%, 5x: 254 days, forecast 2.8%, realized 9.8%

| short | Ghostlyne | 3.40% (2.94, 3.90) | 3.03% | 10.1x | 1.2% |
| short | Textbook (ATR, normal) | 3.32% (2.81, 3.89) | 3.11% | 9.6x | 1.4% |
| short | EWMA RiskMetrics | 3.24% (2.75, 3.78) | 3.06% | 9.4x | 1.1% |
| short | GARCH(1,1)-t | 3.23% (2.77, 3.76) | 2.97% | 9.6x | 1.4% |
| short | Filtered historical simulation | 3.20% (2.70, 3.74) | 2.92% | 9.3x | 0.7% |
| short | Rolling 1-year frequency | 3.33% (2.74, 3.98) | 2.95% | 9.2x | 1.1% |

Ghostlyne short, by recommended leverage: 40x: 63 days, forecast 2.7%, realized 9.5%, 20x: 1934 days, forecast 2.7%, realized 3.7%, 15x: 3197 days, forecast 3.6%, realized 4.5%, 10x: 13370 days, forecast 3.1%, realized 3.5%, 7x: 8483 days, forecast 2.9%, realized 3.0%, 5x: 2037 days, forecast 2.4%, realized 2.2%


Share of forecast rows where raw calibrated odds violated leverage monotonicity before correction:
{"long": {"Ghostlyne": 0.033, "Textbook (ATR, normal)": 0.0631, "EWMA RiskMetrics": 0.0781, "GARCH(1,1)-t": 0.1724, "Filtered historical simulation": 0.0644, "Rolling 1-year frequency": 0.1071}, "short": {"Ghostlyne": 0.0085, "Textbook (ATR, normal)": 0.0408, "EWMA RiskMetrics": 0.0791, "GARCH(1,1)-t": 0.0849, "Filtered historical simulation": 0.0667, "Rolling 1-year frequency": 0.1142}}