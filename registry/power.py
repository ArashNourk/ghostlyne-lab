"""Power check for the R1 gate: how strong must a relationship be for R1 to find it? Synthetic data only."""
import numpy as np, pandas as pd, run
idx = pd.date_range("1995-01-01", "2026-09-01", freq="MS")
def one(share, seed, family=185, q=0.10):
    r = np.random.default_rng(seed); n = len(idx)
    x = pd.Series(r.normal(0, 1, n), idx); c = pd.Series(r.normal(0, 1, n), idx)
    b = np.sqrt(share / (1 - share)); y = pd.Series(r.normal(0, 1, n), idx) + b * x.shift(3).fillna(0)
    dev = idx[(idx >= run.DEV_START) & (idx <= run.DEV_END)]; hold = idx[idx >= run.HOLD_START]
    best = min(((run.ols(*run.design(y, c, x, L, dev))[2] @ run.ols(*run.design(y, c, x, L, dev))[2], L) for L in range(1, 7)))
    f = run.oos(y, c, x, best[1], idx[idx >= dev[0]], hold); _, p = run.clark_west(f)
    return p <= q / family and run.r2(f[f.index < run.SPLIT]) > 0 and run.r2(f[f.index >= run.SPLIT]) > 0
for share in (0.02, 0.05, 0.08, 0.12):
    print(share, np.mean([one(share, s) for s in range(40)]))
