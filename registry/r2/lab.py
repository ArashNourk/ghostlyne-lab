"""Ghostlyne Discovery Lab, run R2.
Separate qualification paths: A association (total and market-adjusted), B lead-lag, S stress-conditional, C predictive.
Exploration window -> candidates (BH per family) -> confirmation window (BH among candidates).
Everything is written to an append-only registry of events."""
import hashlib, json, numpy as np, pandas as pd
from scipy import stats

CFG = dict(explore=("2012-01-01", "2019-12-31"), confirm=("2020-01-01", None), q_explore=0.10, q_confirm=0.05,
           lags=list(range(1, 9)), nw=4, min_explore=260, min_confirm=200, market="ACWI")

def eid(*parts): return "GL-" + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8].upper()

def weekly_returns(s, kind):
    w = s.sort_index().resample("W-FRI").last()
    if kind == "diff": return w.diff()
    w = w.where(w > 0)
    return np.log(w).diff()

def hac_corr(y, x, nw=4):
    """Correlation with a Newey-West p-value (slope of standardized y on standardized x)."""
    d = pd.concat([y, x], axis=1).dropna()
    n = len(d)
    if n < 30: return np.nan, np.nan, np.nan, n
    a = (d.iloc[:, 0] - d.iloc[:, 0].mean()) / d.iloc[:, 0].std(); b = (d.iloc[:, 1] - d.iloc[:, 1].mean()) / d.iloc[:, 1].std()
    r = float((a * b).sum() / (n - 1)); e = (a - r * b).values; u = e * b.values
    s = u @ u
    for l in range(1, nw + 1): s += 2 * (1 - l / (nw + 1)) * (u[l:] @ u[:-l])
    se = np.sqrt(s) / (b.values @ b.values)
    p = float(2 * (1 - stats.norm.cdf(abs(r / se)))) if se > 0 else np.nan
    return r, float(se), p, n

def rank(s): return s.rank()

def bh(p):
    p = np.asarray(p, float); n = len(p)
    if n == 0: return p
    o = np.argsort(p); q = np.empty(n); q[o] = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.minimum(q, 1)

def residualize(r, m):
    """Remove the global market factor (same week and previous week) within one window."""
    d = pd.concat([r.rename("r"), m.rename("m"), m.shift(1).rename("m1")], axis=1).dropna()
    X = np.column_stack([np.ones(len(d)), d.m, d.m1]); b, *_ = np.linalg.lstsq(X, d.r.values, rcond=None)
    return pd.Series(d.r.values - X @ b, index=d.index)

CLOSE = {"asia": 1, "europe": 2, "us": 3}  # order of the Friday close
def region(t):
    if any(t.endswith(s) for s in (".KS", ".TW", ".TWO", ".T", ".HK")): return "asia"
    if any(t.endswith(s) for s in (".CO", ".SW")): return "europe"
    return "us"

def stress_flags(m):
    vol = m.rolling(26).std().shift(1); thr = vol.rolling(156, min_periods=104).quantile(0.67)
    return (vol > thr).where(thr.notna())

def window(s, w): a, b = w; return s[(s.index >= a) & ((s.index <= b) if b else True)]

def run(series, universe, run_id="R2", synthetic=False):
    """series: dict id -> pd.Series (daily or weekly levels). universe: dict with focal, externals."""
    kinds = {k: v.get("transform", "dlog") for k, v in {**universe["focal"], **universe["externals"]}.items()}
    R = {k: weekly_returns(s, kinds.get(k, "dlog")) for k, s in series.items()}
    M = R[CFG["market"]]; E, C = CFG["explore"], CFG["confirm"]
    resid = {w: {k: residualize(window(v, W), window(M, W)) for k, v in R.items() if k != CFG["market"]} for w, W in (("E", E), ("C", C))}
    stress = stress_flags(M)
    tests = []
    for f in universe["focal"]:
        for x, meta in universe["externals"].items():
            base = dict(focal=f, external=x, ring=meta["ring"], role=meta["role"])
            if f not in R or x not in R:
                tests.append(dict(base, family="all", state="Insufficient Data", reason="series unavailable")); continue
            nE = len(pd.concat([window(R[f], E), window(R[x], E)], axis=1).dropna()); nC = len(pd.concat([window(R[f], C), window(R[x], C)], axis=1).dropna())
            if nE < CFG["min_explore"] or nC < CFG["min_confirm"]:
                tests.append(dict(base, family="all", state="Insufficient Data", reason=f"{nE} exploration and {nC} confirmation weeks")); continue
            for fam, fn in (("A_total", lambda w: (window(R[f], w[1]), window(R[x], w[1]))),
                            ("A_adjusted", lambda w: (resid[w[0]][f], resid[w[0]][x]))):
                for w in (("E", E), ("C", C)):
                    y, z = fn(w); r, se, p, n = hac_corr(y, z, CFG["nw"]); rs, _, ps, _ = hac_corr(rank(y), rank(z), CFG["nw"])
                    tests.append(dict(base, family=fam, lag=0, win=w[0], r=r, se=se, p=p, n=n, r_rank=rs, p_rank=ps))
            for k in CFG["lags"]:
                for sgn in (1, -1):  # +k: external leads by k weeks; -k: focal leads
                    L = sgn * k
                    for w in (("E", E), ("C", C)):
                        y, z = resid[w[0]][f], resid[w[0]][x]
                        r, se, p, n = hac_corr(y, z.shift(L) if L > 0 else z, CFG["nw"]) if L > 0 else hac_corr(y.shift(-L), z, CFG["nw"])
                        tests.append(dict(base, family="B_leadlag", lag=L, win=w[0], r=r, se=se, p=p, n=n))
            for w in (("E", E), ("C", C)):
                y, z = resid[w[0]][f], resid[w[0]][x]; d = pd.concat([y, z, stress], axis=1).dropna(); d.columns = ["y", "z", "s"]
                a, b = d[d.s == 1], d[d.s == 0]
                if len(a) > 30 and len(b) > 30:
                    r1, r0 = a.y.corr(a.z), b.y.corr(b.z)
                    zz = (np.arctanh(r1) - np.arctanh(r0)) / np.sqrt(1 / (len(a) - 3) + 1 / (len(b) - 3))
                    tests.append(dict(base, family="S_stress", lag=0, win=w[0], r=r1 - r0, r_stress=r1, r_calm=r0, p=float(2 * (1 - stats.norm.cdf(abs(zz)))), n=len(d)))
    T = pd.DataFrame(tests)
    # exploration: BH within each family and distance ring (each ring gets its own discovery budget)
    ex = T[(T.get("win") == "E") & T.p.notna()].copy()
    ex["q"] = ex.groupby(["family", "ring"]).p.transform(lambda s: pd.Series(bh(s.values), index=s.index))
    cand = ex[ex.q <= CFG["q_explore"]]
    if "B_leadlag" in set(cand.family):  # keep the single strongest lag per pair and direction
        b = cand[cand.family == "B_leadlag"].sort_values("p").drop_duplicates(["focal", "external"])
        cand = pd.concat([cand[cand.family != "B_leadlag"], b])
    # confirmation on the untouched window, BH among candidates per family
    cf = T[(T.get("win") == "C")].set_index(["focal", "external", "family", "lag"])
    out = []
    for fam, g in cand.groupby("family"):
        rows = []
        for _, c in g.iterrows():
            try: k = cf.loc[(c.focal, c.external, fam, c.lag)]
            except KeyError: continue
            k = k.iloc[0] if isinstance(k, pd.DataFrame) else k
            rows.append((c, k))
        qs = bh([k.p for _, k in rows])
        for (c, k), qc in zip(rows, qs):
            why = []
            if np.sign(k.r) != np.sign(c.r): why.append("sign changed in confirmation")
            if qc > CFG["q_confirm"]: why.append("not significant in confirmation after false-discovery control")
            if fam.startswith("A") and (np.sign(k.r_rank) != np.sign(c.r_rank) or np.sign(k.r_rank) != np.sign(k.r)): why.append("rank correlation disagrees")
            if fam == "B_leadlag" and abs(c.lag) == 1:
                lead = c.external if c.lag > 0 else c.focal; lagger = c.focal if c.lag > 0 else c.external
                if CLOSE[region(lead)] > CLOSE[region(lagger)]: why.append("1-week lead from a later-closing market: likely a trading-hours artifact")
            out.append(dict(focal=c.focal, external=c.external, ring=c.ring, role=c.role, family=fam, lag=int(c.lag),
                            r_explore=float(c.r), q_explore=float(c.q), r_confirm=float(k.r), se_confirm=float(k.get("se", np.nan)) if "se" in k else np.nan,
                            p_confirm=float(k.p), q_confirm=float(qc), n_confirm=int(k.n),
                            extra={kk: float(k[kk]) for kk in ("r_stress", "r_calm", "r_rank") if kk in k and pd.notna(k[kk])},
                            state="Validated" if not why else "Not Detected", reason="; ".join(why) or "passed exploration and confirmation"))
    return T, ex, pd.DataFrame(out)

def predictive(series, universe, validated_B):
    """Qualification C, only for validated lead-lag pairs where the external variable leads."""
    kinds = {k: v.get("transform", "dlog") for k, v in {**universe["focal"], **universe["externals"]}.items()}
    R = {k: weekly_returns(s, kinds.get(k, "dlog")) for k, s in series.items()}; M = R[CFG["market"]]
    res = []
    for _, v in validated_B.iterrows():
        if v.lag <= 0: continue
        d = pd.concat([R[v.focal].rename("y"), R[v.focal].shift(1).rename("y1"), M.shift(1).rename("m1"), R[v.external].shift(v.lag).rename("x")], axis=1).dropna()
        d = d[d.index >= CFG["explore"][0]]; t0 = pd.Timestamp(CFG["confirm"][0]); fb, fc, ys = [], [], []
        for t in d.index[d.index >= t0]:
            tr = d[d.index < t]; Xb = np.column_stack([np.ones(len(tr)), tr.y1, tr.m1]); Xc = np.column_stack([Xb, tr.x])
            bb, *_ = np.linalg.lstsq(Xb, tr.y, rcond=None); bc, *_ = np.linalg.lstsq(Xc, tr.y, rcond=None)
            row = d.loc[t]; fb.append(bb @ [1, row.y1, row.m1]); fc.append(bc @ [1, row.y1, row.m1, row.x]); ys.append(row.y)
        fb, fc, ys = map(np.array, (fb, fc, ys))
        adj = (ys - fb) ** 2 - ((ys - fc) ** 2 - (fb - fc) ** 2); a = adj - adj.mean(); n = len(a); s = a @ a / n
        for l in range(1, 5): s += 2 * (1 - l / 5) * (a[l:] @ a[:-l]) / n
        tcw = adj.mean() / np.sqrt(s / n); r2 = 1 - ((ys - fc) ** 2).sum() / ((ys - fb) ** 2).sum()
        res.append(dict(focal=v.focal, external=v.external, lag=int(v.lag), r2_oos=float(r2), p=float(1 - stats.norm.cdf(tcw)), n=n))
    P = pd.DataFrame(res)
    if len(P): P["q"] = bh(P.p.values); P["state"] = np.where((P.q <= CFG["q_confirm"]) & (P.r2_oos > 0), "Validated", "Not Detected")
    return P
