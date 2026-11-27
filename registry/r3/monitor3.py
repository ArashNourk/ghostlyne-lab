"""R3 monitoring with information available at each date (historical replay, not live monitoring)."""
import numpy as np, pandas as pd
from lab3 import lagged

def fisher(r, n):
    z = np.arctanh(np.clip(r, -0.999, 0.999)); h = 1.96 / np.sqrt(max(n - 3, 1)); return float(np.tanh(z - h)), float(np.tanh(z + h))

def behaviour(ref, r, n):
    lo, hi = fisher(r, n)
    if np.sign(r) != np.sign(ref) and (lo > 0 or hi < 0): return "reversing"
    if lo <= ref <= hi: return "stable"
    return "strengthening" if abs(r) > abs(ref) else "weakening"

def rolling(y, x, win, ref_win, cum, start, ref):
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna(); hist = []
    for i in range(win, len(d)):
        t = d.index[i]; ts = t.to_timestamp() if hasattr(t, "to_timestamp") else t
        if ts < pd.Timestamp(start): continue
        w = d.iloc[i - win + 1:i + 1]; r = float(w.y.corr(w.x)); lo, hi = fisher(r, win); row = [str(ts.date()), round(r, 3), round(lo, 3), round(hi, 3), None]
        if i >= ref_win + cum:
            tr = d.iloc[i - ref_win:i + 1]; b = np.polyfit(tr.x, tr.y, 1); e = tr.y - np.polyval(b, tr.x); c = e.rolling(cum).sum().dropna()
            row[4] = round(float((c.iloc[-1] - c.mean()) / c.std()), 2)
        hist.append(row)
    if not hist: return dict(history=[], state={})
    last = hist[-1]; st = dict(correlation=behaviour(ref, last[1], win))
    dz = [h[4] for h in hist if h[4] is not None]
    if dz:
        prev = dz[-5] if len(dz) > 5 else np.nan
        st["divergence"] = "diverging" if abs(dz[-1]) > 2 and abs(dz[-1]) >= abs(prev) else "converging" if abs(prev) > 2 and abs(dz[-1]) < abs(prev) else "within normal range"
    return dict(history=hist, state=st, latest=dict(date=last[0], r=last[1], lo=last[2], hi=last[3], div_z=last[4]))

def lag_drift(y, x, L, months=60):
    d = {}
    for k in [s * j for j in range(1, 13) for s in (1, -1)]:
        a, b = lagged(y, x, k); z = pd.concat([a, b], axis=1).dropna().iloc[-months:]
        if len(z) > 24: d[k] = float(z.iloc[:, 0].corr(z.iloc[:, 1]))
    if L not in d: return {}
    best = max(d, key=lambda k: abs(d[k])); se = np.sqrt(2 / (months - 3))
    drift = best != L and abs(np.arctanh(abs(d[best])) - np.arctanh(abs(d[L]))) > 1.96 * se
    return dict(best_lag_now=int(best), r_best=round(d[best], 3), r_at_validated_lag=round(d[L], 3), state="lag drift" if drift else "lag stable")

def monitor(D, v, start="2017-01-01"):
    f, x, fam, L, ref = v["focal"], v["external"], v["family"], v["lag"], v["e_confirm"]
    if fam == "A_w": return rolling(D["RW"][f], D["RW"][x], 52, 104, 13, start, ref)
    if fam in ("A_m", "A_q"): return rolling(D["RM"][f], D["RM"][x], 36, 60, 3, start, ref)
    if fam in ("B_m", "R_yoy"):
        R = D["RM"] if fam == "B_m" else D["YY"]; y, z = lagged(R[f], R[x], L)
        out = rolling(y, z, 36, 60, 3, "2020-01-01" if fam == "R_yoy" else start, ref); out["lag"] = lag_drift(R[f], R[x], L); return out
    if fam == "X_shock":
        rx = D["RW"][x]; rf = D["RW"][f]; lo = rx.rolling(260, min_periods=156).quantile(0.05).shift(1); hi = rx.rolling(260, min_periods=156).quantile(0.95).shift(1)
        ev = rx[(rx > hi)] if v["dir"] == "up" else rx[(rx < lo)]
        fwd = sum(rf.shift(-k) for k in range(1, 5)); last = ev.index.max() if len(ev) else None
        recent = [[str(t.date()), round(float(rx[t]), 4), (round(float(fwd[t]), 4) if pd.notna(fwd.get(t)) else None)] for t in ev.index[-8:]]
        return dict(history=[], state=dict(last_shock=str(last.date()) if last is not None else None), shocks=recent)
    return dict(history=[], state={})
