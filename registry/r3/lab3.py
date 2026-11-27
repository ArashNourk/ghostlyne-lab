"""Ghostlyne Discovery Lab, run R3: total association at three horizons, monthly lead-lag (1-12 months),
shock transmission, revenue (fundamentals) lead-lag, pre-specified chains, predictive value, monitoring."""
import sys, os, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "r2"))
from lab import hac_corr, bh, eid

W_EQ = (("E", "2008-01-01", "2016-12-31"), ("C", "2017-01-01", None))
W_REV = (("E", "2014-01-01", "2019-12-31"), ("C", "2020-01-01", None))
MIN = {"A_w": (300, 300), "A_m": (72, 72), "A_q": (24, 24), "B_m": (72, 72), "X_shock": (300, 300), "R_yoy": (48, 48), "chain": (72, 72)}
QE, QC = 0.10, 0.05

def win(s, a, b):
    i = s.index.to_timestamp() if isinstance(s.index, pd.PeriodIndex) else s.index
    m = (i >= pd.Timestamp(a)) & ((i <= pd.Timestamp(b)) if b else True); return s[m]

def returns(s, rule, tr):
    w = s.sort_index().resample(rule).last()
    if rule != "W-FRI": w.index = w.index.to_period("M" if rule == "ME" else "Q")
    return w.diff() if tr == "diff" else np.log(w.where(w > 0)).diff()

def yoy(s, tr):
    m = s.sort_index().resample("ME").last(); m.index = m.index.to_period("M")
    return m.diff(12) if tr == "diff" else np.log(m.where(m > 0)).diff(12)

def pp_corr(y, x, maxlag=24):
    """Correlation with a p-value using the Pyper-Peterman effective sample size (autocorrelated series)."""
    d = pd.concat([y, x], axis=1).dropna(); n = len(d)
    if n < 30: return np.nan, np.nan, np.nan, n
    a = d.iloc[:, 0].values - d.iloc[:, 0].mean(); b = d.iloc[:, 1].values - d.iloc[:, 1].mean(); r = float(a @ b / np.sqrt((a @ a) * (b @ b)))
    ac = lambda v, k: (v[k:] @ v[:-k]) / (v @ v)
    s = sum((n - k) / n * ac(a, k) * ac(b, k) for k in range(1, min(maxlag, n // 5) + 1))
    ne = max(5.0, min(n, n / (1 + 2 * s))); t = r * np.sqrt((ne - 2) / max(1e-12, 1 - r * r))
    return r, np.nan, float(2 * stats.t.sf(abs(t), ne - 2)), n

def lagged(y, x, L):
    """L>0: x leads y by L periods; L<0: y leads x by |L|."""
    return (y, x.shift(L)) if L > 0 else (y.shift(-L), x) if L < 0 else (y, x)

_TH = {}
def thresholds(key, rx):
    if key not in _TH: _TH[key] = (rx.rolling(260, min_periods=156).quantile(0.05).shift(1), rx.rolling(260, min_periods=156).quantile(0.95).shift(1))
    return _TH[key]

def shock_test(rf, rx, wE, h=4, key=None):
    """Focal cumulative return over the 4 weeks AFTER an extreme weekly move in the external (thresholds from the trailing 5 years only)."""
    lo, hi = thresholds(key, rx) if key else (rx.rolling(260, min_periods=156).quantile(0.05).shift(1), rx.rolling(260, min_periods=156).quantile(0.95).shift(1))
    fwd = sum(rf.shift(-k) for k in range(1, h + 1))
    d = pd.concat([fwd.rename("y"), (rx > hi).astype(float).where(hi.notna()).rename("up"), (rx < lo).astype(float).where(lo.notna()).rename("dn")], axis=1).dropna()
    d = win(d, *wE)
    out = {}
    for k in ("up", "dn"):
        n_ev = int(d[k].sum())
        if n_ev < 10: out[k] = dict(effect=np.nan, p=np.nan, n=len(d), events=n_ev); continue
        X = np.column_stack([np.ones(len(d)), d.up, d.dn]); b, *_ = np.linalg.lstsq(X, d.y.values, rcond=None); e = d.y.values - X @ b
        j = 1 if k == "up" else 2; XtXi = np.linalg.pinv(X.T @ X); u = X * e[:, None]; Sg = u.T @ u
        for l in range(1, h + 1): G = u[l:].T @ u[:-l]; Sg += (1 - l / (h + 1)) * (G + G.T)
        se = np.sqrt((XtXi @ Sg @ XtXi)[j, j]); out[k] = dict(effect=float(b[j]), p=float(2 * (1 - stats.norm.cdf(abs(b[j] / se)))), n=len(d), events=n_ev)
    return out

def mediation(X, M, Y, reps=999, block=6, seed=0):
    d = pd.concat([X.rename("x"), M.rename("m"), Y.rename("y")], axis=1).dropna(); n = len(d)
    def est(v):
        a = np.polyfit(v[:, 0], v[:, 1], 1)[0]; Z = np.column_stack([np.ones(len(v)), v[:, 1], v[:, 0]]); b = np.linalg.lstsq(Z, v[:, 2], rcond=None)[0]
        c = np.polyfit(v[:, 0], v[:, 2], 1)[0]; return a * b[1], a, b[1], c, b[2]
    V = d.values; ind, a, b, c, cp = est(V); r = np.random.default_rng(seed); boots = []
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) % n for s in r.integers(0, n, n // block + 1)])[:n]; boots.append(est(V[idx])[0])
    boots = np.array(boots); p = float(min(1, 2 * min((boots <= 0).mean(), (boots >= 0).mean())))
    sx, sy = d.x.std(), d.y.std()
    return dict(indirect=float(ind), indirect_std=float(ind * sx / sy), a=float(a), b=float(b), total=float(c), direct=float(cp), lo=float(np.percentile(boots, 2.5)), hi=float(np.percentile(boots, 97.5)), p=max(p, 1 / (reps + 1)), n=n)

def screen_confirm(T, sign_key="r"):
    """Exploration BH per family x ring; keep the best lag/direction per unit; confirmation BH per family among candidates."""
    ex = T[(T.win == "E") & T.p.notna() & T.ok].copy()
    ex["q"] = ex.groupby(["family", "ring"]).p.transform(lambda s: pd.Series(bh(s.values), index=s.index))
    cand = ex[ex.q <= QE].sort_values("p").drop_duplicates(["focal", "external", "family", "dir"])
    cf = T[T.win == "C"].set_index(["focal", "external", "family", "lag", "dir"]); rows = []
    for fam, g in cand.groupby("family"):
        pairs = []
        for _, c in g.iterrows():
            key = (c.focal, c.external, fam, c.lag, c.dir)
            if key in cf.index: k = cf.loc[key]; pairs.append((c, k.iloc[0] if isinstance(k, pd.DataFrame) else k))
        for (c, k), q in zip(pairs, bh([k.p if np.isfinite(k.p) else 1 for _, k in pairs])):
            why = []
            if not k.ok: why.append("insufficient confirmation data")
            if np.sign(k[sign_key]) != np.sign(c[sign_key]): why.append("direction changed in confirmation")
            if q > QC: why.append("not significant in confirmation after false-discovery control")
            if fam.startswith("A") and pd.notna(k.get("r_rank")) and np.sign(k.r_rank) != np.sign(k.r): why.append("rank correlation disagrees")
            rows.append(dict(focal=c.focal, external=c.external, ring=int(c.ring), family=fam, lag=int(c.lag), dir=c.dir,
                             e_explore=float(c[sign_key]), q_explore=float(c.q), e_confirm=float(k[sign_key]), p_confirm=float(k.p), q_confirm=float(q),
                             n_confirm=int(k.n), events=int(k.get("events") if pd.notna(k.get("events")) else 0), state="Validated" if not why else "Not Detected",
                             reason="; ".join(why) or "passed exploration and confirmation"))
    return ex, pd.DataFrame(rows)

def run(S, U):
    tr = {k: v["transform"] for k, v in U.EXTERNALS.items()}
    RW = {k: returns(s, "W-FRI", tr.get(k, "dlog")) for k, s in S.items() if not k.startswith("REV_")}
    RM = {k: returns(s, "ME", tr.get(k, "dlog")) for k, s in S.items() if not k.startswith("REV_")}
    RQ = {k: returns(s, "QE", tr.get(k, "dlog")) for k, s in S.items() if not k.startswith("REV_")}
    YY = {k: yoy(s, tr.get(k, "dlog")) for k, s in S.items()}
    T = []
    def add(base, fam, lag, dir_, w, r=np.nan, p=np.nan, n=0, **kw):
        lo, hi = MIN[fam]; T.append(dict(base, family=fam, lag=lag, dir=dir_, win=w, r=r, p=p, n=n, ok=n >= (lo if w == "E" else hi), **kw))
    for f in U.FOCAL:
        for x, m in U.EXTERNALS.items():
            base = dict(focal=f, external=x, ring=m["ring"], role=m["role"])
            if f not in RW or x not in RW: continue
            for (w, a, b) in W_EQ:
                for fam, R, nw in (("A_w", RW, 4), ("A_m", RM, 3), ("A_q", RQ, 2)):
                    y, z = win(R[f], a, b), win(R[x], a, b); r, se, p, n = hac_corr(y, z, nw); rr, _, _, _ = hac_corr(y.rank(), z.rank(), nw)
                    add(base, fam, 0, "", w, r, p, n, r_rank=rr)
                for L in [s * k for k in range(1, 13) for s in (1, -1)]:
                    y, z = lagged(RM[f], RM[x], L); r, se, p, n = hac_corr(win(y, a, b), win(z, a, b), 3); add(base, "B_m", L, "", w, r, p, n)
                sh = shock_test(RW[f], RW[x], (a, b), key=x)
                for k, v in sh.items(): add(base, "X_shock", 0, k, w, v["effect"], v["p"], v["n"] if v["events"] >= 10 else 0, events=v["events"])
    for f in U.REVENUE:
        for x, m in U.EXTERNALS.items():
            if f not in YY or x not in YY or YY[f].dropna().empty: continue
            base = dict(focal=f, external=x, ring=m["ring"], role=m["role"])
            for (w, a, b) in W_REV:
                for L in [0] + [s * k for k in range(1, 13) for s in (1, -1)]:
                    y, z = lagged(YY[f], YY[x], L); r, se, p, n = pp_corr(win(y, a, b), win(z, a, b)); add(base, "R_yoy", L, "", w, r, p, n)
    T = pd.DataFrame(T)
    ex, conf = screen_confirm(T)
    # chains: pre-specified, so screened on exploration with BH across chains, confirmed on confirmation window
    CH = []
    for (x, m_, y) in U.CHAINS:
        if not all(k in RM for k in (x, m_, y)): CH.append(dict(chain=[x, m_, y], state="Insufficient Data")); continue
        rE = mediation(win(RM[x], *W_EQ[0][1:]), win(RM[m_], *W_EQ[0][1:]), win(RM[y], *W_EQ[0][1:]))
        rC = mediation(win(RM[x], *W_EQ[1][1:]), win(RM[m_], *W_EQ[1][1:]), win(RM[y], *W_EQ[1][1:]))
        CH.append(dict(chain=[x, m_, y], E=rE, C=rC))
    ok = [c for c in CH if "E" in c]; qE = bh([c["E"]["p"] for c in ok])
    cands = [c for c, q in zip(ok, qE) if q <= QE]
    for c, q in zip(ok, qE): c["q_explore"] = float(q)
    qC = bh([c["C"]["p"] for c in cands])
    for c in ok: c["state"] = "Not Detected"; c["reason"] = "not significant in exploration"
    for c, q in zip(cands, qC):
        c["q_confirm"] = float(q); same = np.sign(c["C"]["indirect"]) == np.sign(c["E"]["indirect"])
        c["state"] = "Validated" if (q <= QC and same) else "Not Detected"; c["reason"] = "passed exploration and confirmation" if c["state"] == "Validated" else ("direction changed" if not same else "not significant in confirmation")
    return T, ex, conf, CH, dict(RW=RW, RM=RM, RQ=RQ, YY=YY)

def predictive(D, conf):
    """Qualification C for validated monthly lead-lag where the external leads (equities: B_m; fundamentals: R_yoy)."""
    out = []
    for _, v in conf[(conf.state == "Validated") & conf.family.isin(["B_m", "R_yoy"]) & (conf.lag > 0)].iterrows():
        R = D["RM"] if v.family == "B_m" else D["YY"]; y = R[v.focal]; L = v.lag
        h = 12 if v.family == "R_yoy" else 1  # YoY targets: baseline uses the value 12 months earlier is overlapping; use last known own value
        d = pd.concat([y.rename("y"), y.shift(1 if v.family == "B_m" else 1).rename("y1"), R[v.external].shift(L).rename("x")], axis=1).dropna()
        t0 = pd.Period("2017-01" if v.family == "B_m" else "2020-01", "M"); fb, fc, ys = [], [], []
        for t in d.index[d.index >= t0]:
            tr = d[d.index < t]
            if len(tr) < 48: continue
            Xb = np.column_stack([np.ones(len(tr)), tr.y1]); Xc = np.column_stack([Xb, tr.x])
            bb = np.linalg.lstsq(Xb, tr.y, rcond=None)[0]; bc = np.linalg.lstsq(Xc, tr.y, rcond=None)[0]; row = d.loc[t]
            fb.append(bb @ [1, row.y1]); fc.append(bc @ [1, row.y1, row.x]); ys.append(row.y)
        if len(ys) < 24: continue
        fb, fc, ys = map(np.array, (fb, fc, ys)); adj = (ys - fb) ** 2 - ((ys - fc) ** 2 - (fb - fc) ** 2); a = adj - adj.mean(); n = len(a); s = a @ a / n
        for l in range(1, 7): s += 2 * (1 - l / 7) * (a[l:] @ a[:-l]) / n
        out.append(dict(focal=v.focal, external=v.external, family=v.family, lag=int(L), r2_oos=float(1 - ((ys - fc) ** 2).sum() / ((ys - fb) ** 2).sum()), p=float(1 - stats.norm.cdf(adj.mean() / np.sqrt(s / n))), n=n))
    P = pd.DataFrame(out)
    if len(P): P["q"] = bh(P.p.values); P["state"] = np.where((P.q <= QC) & (P.r2_oos > 0), "Validated", "Not Detected")
    return P
