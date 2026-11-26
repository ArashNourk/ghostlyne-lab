"""Lifecycle replay and relationship monitoring (historical replay, not live monitoring)."""
import numpy as np, pandas as pd
from scipy import stats
from lab import hac_corr, bh, residualize, weekly_returns, CFG

def rolling_resid(r, m, win=104):
    """Market-adjusted return using only betas estimated on the trailing window (no look-ahead)."""
    d = pd.concat([r.rename("r"), m.rename("m"), m.shift(1).rename("m1")], axis=1).dropna(); out = {}
    for i in range(win, len(d)):
        tr = d.iloc[i - win:i]; X = np.column_stack([np.ones(win), tr.m, tr.m1]); b, *_ = np.linalg.lstsq(X, tr.r.values, rcond=None)
        row = d.iloc[i]; out[d.index[i]] = row.r - b @ [1, row.m, row.m1]
    return pd.Series(out)

def fisher_ci(r, n):
    z = np.arctanh(r); h = 1.96 / np.sqrt(max(n - 3, 1)); return float(np.tanh(z - h)), float(np.tanh(z + h))

def behaviour(ref, r, n):
    lo, hi = fisher_ci(r, n)
    if np.sign(r) != np.sign(ref) and (lo > 0 or hi < 0): return "reversing"
    if lo <= ref <= hi: return "stable"
    return "strengthening" if abs(r) > abs(ref) else "weakening"

def monitor(R, M, v, start="2020-01-01"):
    """v: one validated relationship (dict). Returns weekly history of measurements using information to date."""
    f, x, fam, L = v["focal"], v["external"], v["family"], v["lag"]
    if fam == "A_total": y, z = R[f], R[x]
    else: y, z = rolling_resid(R[f], M), rolling_resid(R[x], M)
    if L > 0: z = z.shift(L)
    elif L < 0: y = y.shift(-L)
    d = pd.concat([y.rename("y"), z.rename("z")], axis=1).dropna()
    hist = []
    for i in range(52, len(d)):
        t = d.index[i]
        if t < pd.Timestamp(start): continue
        w = d.iloc[i - 51:i + 1]; r = float(w.y.corr(w.z)); lo, hi = fisher_ci(r, 52)
        row = dict(date=str(t.date()), r=round(r, 3), lo=round(lo, 3), hi=round(hi, 3))
        if fam.startswith("A") and i >= 104 + 13:
            tr = d.iloc[i - 104:i + 1]; b = np.polyfit(tr.z, tr.y, 1); e = tr.y - np.polyval(b, tr.z)
            c13 = e.rolling(13).sum().dropna(); row["div_z"] = round(float((c13.iloc[-1] - c13.mean()) / c13.std()), 2)
        hist.append(row)
    H = pd.DataFrame(hist)
    if H.empty: return dict(history=[], state=None)
    last = H.iloc[-1]; st = dict(correlation=behaviour(v["r_confirm"], last.r, 52))
    if "div_z" in H and pd.notna(last.get("div_z")):
        dz = H.div_z.dropna(); prev = dz.iloc[-5] if len(dz) > 5 else np.nan
        st["divergence"] = "diverging" if abs(last.div_z) > 2 and abs(last.div_z) >= abs(prev) else "converging" if abs(prev) > 2 and abs(last.div_z) < abs(prev) else "within normal range"
    return dict(history=H.to_dict("records"), state=st, latest=dict(last))

def replay(R, M, pairs, rings, checkpoints, q_screen=0.10, q_conf=0.05, look=156):
    """Run the lab lifecycle at past checkpoints using only data available at each one (A_adjusted family)."""
    state = {p: "Not Detected" for p in pairs}; sign = {}; events = []; pend = {}; under = set()
    for i, c in enumerate(checkpoints):
        c = pd.Timestamp(c); prev = pd.Timestamp(checkpoints[i - 1]) if i else None
        Mw = M[M.index <= c]
        # confirm last checkpoint's candidates and reassess validated ones on the fresh weeks since then
        if prev is not None:
            fresh = lambda s: s[(s.index > prev) & (s.index <= c)]
            todo = [p for p in pairs if state[p] in ("Candidate", "Validated", "Under Reassessment")]
            res = {}
            for p in todo:
                f, x = p; a = residualize(fresh(R[f]), fresh(M)); b = residualize(fresh(R[x]), fresh(M)); r, se, pv, n = hac_corr(a, b)
                res[p] = (r, pv)
            cands = [p for p in todo if state[p] == "Candidate"]; qs = dict(zip(cands, bh([res[p][1] for p in cands])))
            for p in todo:
                r, pv = res[p]; old = state[p]
                if old == "Candidate":
                    new = "Validated" if (qs[p] <= q_conf and np.sign(r) == sign[p]) else "Not Detected"
                elif pv < 0.05 and np.sign(r) == sign[p]: new = "Validated"
                elif pv < 0.05 and np.sign(r) != sign[p]: new = "Invalidated"
                else: new = "Invalidated" if old == "Under Reassessment" else "Under Reassessment"
                if new != old or old == "Validated":
                    events.append(dict(date=str(c.date()), focal=p[0], external=p[1], frm=old, to=new, r=round(float(r), 3), p=float(pv)))
                state[p] = "Not Detected" if new == "Invalidated" else new
        # screen everything dormant on the trailing window
        dorm = [p for p in pairs if state[p] == "Not Detected"]; stats_ = {}
        for p in dorm:
            f, x = p; w = lambda s: s[(s.index <= c) & (s.index > c - pd.Timedelta(weeks=look))]
            a = residualize(w(R[f]), w(M)); b = residualize(w(R[x]), w(M)); r, se, pv, n = hac_corr(a, b); stats_[p] = (r, pv, n)
        for ring in set(rings.values()):
            ps = [p for p in dorm if rings[p] == ring and stats_[p][2] >= 120 and np.isfinite(stats_[p][1])]
            for p, q in zip(ps, bh([stats_[p][1] for p in ps])):
                if q <= q_screen:
                    state[p] = "Candidate"; sign[p] = np.sign(stats_[p][0])
                    events.append(dict(date=str(c.date()), focal=p[0], external=p[1], frm="Not Detected", to="Candidate", r=round(float(stats_[p][0]), 3), p=float(stats_[p][1])))
    return events, state
