# Cascade-adjusted wick odds
59236 coin-days, 28 perpetuals, test 2023-01-01 to 2026-10-31 (walk-forward, monthly refit).

| Test | Base rate | Textbook AUC | Texture skill | +Positioning skill | All skill | All boosted skill | Positioning > texture (bootstrap) |
|---|---|---|---|---|---|---|---|
| long_5 | 0.214 | 0.681 | +0.038 | +0.019 | +0.012 | -0.021 | 9% |
| long_10 | 0.042 | 0.679 | +0.034 | -0.010 | -0.052 | -0.025 | 19% |
| long_15 | 0.013 | 0.638 | +0.007 | +0.003 | -0.025 | +0.005 | 34% |
| short_5 | 0.197 | 0.684 | +0.044 | +0.032 | +0.029 | +0.025 | 1% |
| short_10 | 0.049 | 0.717 | +0.049 | +0.036 | +0.035 | +0.038 | 2% |
| short_15 | 0.016 | 0.716 | +0.031 | +0.040 | +0.038 | +0.035 | 72% |

Skill = 1 - Brier/Brier(textbook ATR random-walk model). Crowding coefficients (standardized, 10% wicks):
```
{
 "long": {
  "long_crowd": 0.07007408010385179,
  "short_crowd": 0.05633722222337996,
  "fund_z": 0.034164569561566396,
  "ls_z": 0.07663701227030706,
  "oi_z30": -0.1470562675878351,
  "oi_d1": 0.04807651520465577
 },
 "short": {
  "long_crowd": 0.034267446843508804,
  "short_crowd": -0.024226547267197057,
  "fund_z": 0.08194710189873339,
  "ls_z": 0.010252837340167277,
  "oi_z30": 0.2602082349041298,
  "oi_d1": -0.033075515030577915
 }
}
```