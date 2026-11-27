"""R4.1 monitoring correction (no re-validation). Fixes found in external review:
1. behaviour(): a change of sign is never called strengthening. A sign change whose interval includes zero is
   'possible sign change (direction uncertain)'; one whose interval excludes zero is 'reversed'.
2. Lead-lag monitoring now uses the same statistic as validation: Fourier-deseasonalised, dual-filter prewhitened
   lagged correlation on trailing windows. Divergence is computed for same-period associations only.
3. Same-period monitoring removes day-of-week effects inside each trailing window (no full-sample means).
Validated relationships, their confirmation statistics and their states are unchanged from R4."""
import numpy as np, pandas as pd
import lab4
from scipy import stats

def fisher(r, n):
    z = np.arctanh(np.clip(r, -0.999, 0.999)); h = 1.96 / np.sqrt(max(n - 3, 1)); return float(np.tanh(z - h)), float(np.tanh(z + h))

def behaviour(ref, r, n):
    lo, hi = fisher(r, n)
    if np.sign(r) != np.sign(ref):
        return "reversed" if (lo > 0 or hi < 0) else "possible sign change (direction uncertain)"
    if lo <= ref <= hi: return "stable"
    return "strengthening" if abs(r) > abs(ref) else "weakening"

def _dow(x): return x - x.groupby(x.index.dayofweek).transform("mean")

def monitor_assoc(S, v):
    f, x, weekly = v["focal"], v["external"], v["family"].endswith("_w")
    y, z = lab4.innov(f, S[f], weekly), lab4.innov(x, S[x], weekly); d = pd.concat([y.rename("y"), z.rename("z")], axis=1).dropna()
    win, ref_win, cum, step = (104, 104, 4, 1) if weekly else (365, 730, 20, 7); start = pd.Timestamp("2019-01-01" if v["split"] == "early" else "2022-01-01")
    hist = []
    for i in range(max(win, ref_win), len(d), step):
        t = d.index[i]
        if t < start: continue
        w = d.iloc[i - win + 1:i + 1]
        if not weekly: w = w.apply(_dow)
        r = float(w.y.corr(w.z, method="spearman")); lo, hi = fisher(r, len(w))
        tr = d.iloc[i - ref_win:i + 1]; tr = (tr if weekly else tr.apply(_dow)).rank(); b = np.polyfit(tr.z, tr.y, 1); e = tr.y - np.polyval(b, tr.z); c = e.rolling(cum).sum().dropna()
        hist.append([str(t.date()), round(r, 3), round(lo, 3), round(hi, 3), round(float((c.iloc[-1] - c.mean()) / c.std()), 2)])
    return finish(hist, v, len(w) if hist else win, divergence=True)

def monitor_lead(S, v):
    f, x, weekly, L = v["focal"], v["external"], v["family"].endswith("_w"), v["lag"]
    both = lab4.stationary(f) and lab4.stationary(x)
    g = (lambda k: lab4.dyn(k, S[k], weekly)) if both else (lambda k: lab4.innov(k, S[k], weekly, last=True))
    y, z = g(f), g(x); d = pd.concat([y.rename("y"), z.rename("z")], axis=1).dropna()
    win, step, pmax, nw = (104, 1, 8, 4) if weekly else (365, 7, 14, 5); start = pd.Timestamp("2019-01-01" if v["split"] == "early" else "2022-01-01")
    hist = []
    for i in range(win, len(d), step):
        t = d.index[i]
        if t < start: continue
        w = d.iloc[i - win + 1:i + 1]; yw, zw = lab4.fourier_resid(w.y, weekly), lab4.fourier_resid(w.z, weekly)
        r, p, n, _ = lab4.lead_test(yw, zw, L, nw, pmax) if L > 0 else lab4.lead_test(zw, yw, -L, nw, pmax)
        if not np.isfinite(r): continue
        lo, hi = fisher(r, n); hist.append([str(t.date()), round(float(r), 3), round(lo, 3), round(hi, 3), None])
    return finish(hist, v, win, divergence=False)

def finish(hist, v, n, divergence):
    if not hist: return dict(history=[], state={})
    last = hist[-1]; st = dict(correlation=behaviour(v["e_confirm"], last[1], n))
    if divergence:
        dz = [h[4] for h in hist if h[4] is not None]; prev = dz[-5] if len(dz) > 5 else np.nan
        st["divergence"] = "diverging" if abs(dz[-1]) > 2 and abs(dz[-1]) >= abs(prev) else "converging" if abs(prev) > 2 and abs(dz[-1]) < abs(prev) else "within normal range"
    return dict(history=hist, state=st, latest=dict(date=last[0], r=last[1], lo=last[2], hi=last[3], div_z=last[4]), method="R4.1")

def monitor(S, v):
    if v["family"].startswith("S_"): return dict(history=[], state={}, note="conditional: in-regime and out-of-regime strengths only; regime definition under review (R5)")
    return monitor_lead(S, v) if v["family"].startswith("B_") else monitor_assoc(S, v)
