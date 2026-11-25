# Ghostlyne Odds: calibrated walk-forward backtest
Evaluation 2024-01-01 to 2026-11-24, 28 perpetuals. Calibration uses only earlier out-of-sample predictions.

| Position | Liq. distance | Base rate | Textbook Brier skill | Raw skill | Calibrated skill | Calibrated AUC | Top-decile predicted vs actual |
|---|---|---|---|---|---|---|---|
| 40x long | 2.0% | 58.09% | 0 | +0.016 | +0.013 | 0.674 (textbook 0.660) | 83.7% vs 82.7% |
| 20x long | 4.5% | 26.90% | 0 | +0.038 | +0.034 | 0.691 (textbook 0.668) | 55.4% vs 52.0% |
| 15x long | 6.2% | 15.26% | 0 | +0.046 | +0.039 | 0.706 (textbook 0.677) | 38.6% vs 36.3% |
| 10x long | 9.5% | 5.39% | 0 | +0.044 | +0.016 | 0.721 (textbook 0.678) | 16.9% vs 15.4% |
| 7x long | 13.8% | 1.79% | 0 | +0.021 | +0.011 | 0.698 (textbook 0.647) | 6.2% vs 5.8% |
| 5x long | 19.5% | 0.67% | 0 | -0.009 | +0.006 | 0.695 (textbook 0.613) | 2.8% vs 2.6% |
| 40x short | 2.0% | 53.78% | 0 | +0.020 | +0.018 | 0.651 (textbook 0.650) | 78.0% vs 74.5% |
| 20x short | 4.5% | 23.72% | 0 | +0.045 | +0.041 | 0.682 (textbook 0.672) | 50.2% vs 46.8% |
| 15x short | 6.2% | 14.14% | 0 | +0.055 | +0.052 | 0.696 (textbook 0.678) | 36.5% vs 33.6% |
| 10x short | 9.5% | 5.72% | 0 | +0.055 | +0.051 | 0.728 (textbook 0.701) | 21.1% vs 18.1% |
| 7x short | 13.8% | 2.17% | 0 | +0.034 | +0.032 | 0.744 (textbook 0.711) | 9.5% vs 7.5% |
| 5x short | 19.5% | 0.73% | 0 | +0.013 | +0.004 | 0.759 (textbook 0.700) | 3.7% vs 2.9% |