"""Ghostlyne Registry R1: run the pre-registered test once. Input: raw/*.csv (date,value). Output: results/R1.json"""
import json, os, sys, numpy as np, pandas as pd
from scipy import stats
from universe import TARGETS, EXTERNALS, PLACEBOS, CONTROL, pairs

DEV_END = pd.Timestamp("2015-12-01"); HOLD_START = pd.Timestamp("2016-01-01"); SPLIT = pd.Timestamp("2021-01-01")
DEV_START = pd.Timestamp("2000-01-01"); MIN_DEV = 96; Q = 0.10; AR = 3

def monthly(path):
    s = pd.read_csv(path, parse_dates=["date"]).set_index("date")["value"].astype(float)
    return s.resample("MS").mean().dropna()

def placebo(seed, index):
    r = np.random.default_rng(seed)
    return pd.Series(np.exp(np.cumsum(r.normal(0, 0.03, len(index)))), index=index)

def transform(s, how): return np.log(s).diff() if how == "dlog" else s

def design(y, c, x, L, dates):
    d = pd.DataFrame({"y": y})
    for j in range(1, AR + 1): d[f"y{j}"] = y.shift(j)
    d["c1"] = c.shift(1)
    if x is not None: d["x"] = x.shift(L)
    d = d.loc[d.index.isin(dates)].dropna()
    m = pd.get_dummies(d.index.month, prefix="m", drop_first=True, dtype=float); m.index = d.index
    X = pd.concat([pd.Series(1.0, index=d.index, name="k"), d.drop(columns="y"), m], axis=1)
    return X, d["y"]

def ols(X, y):
    b, *_ = np.linalg.lstsq(X.values, y.values, rcond=None)
    e = y.values - X.values @ b
    n, k = X.shape; s2 = e @ e / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.values.T @ X.values)))
    return b, se, e

def oos(y, c, x, L, idx_all, hold):
    """Expanding-window one-step forecasts over the holdout months."""
    Xb, yb = design(y, c, None, L, idx_all); Xc, yc = design(y, c, x, L, idx_all)
    common = Xb.index.intersection(Xc.index); Xb, yb, Xc = Xb.loc[common], yb.loc[common], Xc.loc[common]
    rows = []
    for t in [d for d in common if d >= HOLD_START and d in hold]:
        tr = common[common < t]
        if len(tr) < MIN_DEV: continue
        bb, *_ = np.linalg.lstsq(Xb.loc[tr].values, yb.loc[tr].values, rcond=None)
        bc, *_ = np.linalg.lstsq(Xc.loc[tr].values, yb.loc[tr].values, rcond=None)
        fb, fc = float(Xb.loc[t].values @ bb), float(Xc.loc[t].values @ bc)
        rows.append((t, float(yb.loc[t]), fb, fc))
    return pd.DataFrame(rows, columns=["date", "y", "fb", "fc"]).set_index("date")

def clark_west(f):
    """One-sided Clark-West (2007) test for nested models, Newey-West variance with 3 lags."""
    adj = (f.y - f.fb) ** 2 - ((f.y - f.fc) ** 2 - (f.fb - f.fc) ** 2)
    a = adj.values - adj.values.mean(); n = len(a); v = a @ a / n
    for l in range(1, 4): v += 2 * (1 - l / 4) * (a[l:] @ a[:-l]) / n
    t = adj.mean() / np.sqrt(v / n) if v > 0 else 0.0
    return float(t), float(1 - stats.norm.cdf(t))

def r2(f): return float(1 - ((f.y - f.fc) ** 2).sum() / ((f.y - f.fb) ** 2).sum()) if len(f) else float("nan")

def bh(p):
    p = np.asarray(p); n = len(p); o = np.argsort(p); q = np.empty(n)
    q[o] = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.minimum(q, 1)

def main(raw="raw", out="results"):
    S = {f[:-4]: monthly(os.path.join(raw, f)) for f in os.listdir(raw) if f.endswith(".csv")}
    months = pd.date_range("1990-01-01", max(s.index.max() for s in S.values()), freq="MS")
    for k, seed in PLACEBOS.items(): S[k] = placebo(seed, months)
    c = transform(S[CONTROL], "dlog")
    res = []
    for h in pairs():
        t, xid = h["target"], h["external"]
        r = dict(h)
        if xid not in S: r.update(status="no data", reason="series unavailable"); res.append(r); continue
        y = transform(S[t], "dlog"); x = transform(S[xid], h["transform"])
        idx = y.dropna().index.intersection(x.dropna().index).intersection(c.dropna().index)
        start = max(DEV_START, idx.min() + pd.DateOffset(months=h["lag_hi"] + AR))
        dev = idx[(idx >= start) & (idx <= DEV_END)]; hold = idx[idx >= HOLD_START]
        if len(dev) < MIN_DEV: r.update(status="no data", reason=f"only {len(dev)} development months"); res.append(r); continue
        # 1. lag chosen on development data only: lowest in-sample error within the pre-registered window
        best = None
        for L in range(h["lag_lo"], h["lag_hi"] + 1):
            X, yy = design(y, c, x, L, dev); b, se, e = ols(X, yy)
            j = list(X.columns).index("x")
            if best is None or e @ e < best[0]: best = (e @ e, L, b[j], se[j])
        _, L, coef, se = best
        # 2. sign stability across the two halves of the development period
        mid = dev[len(dev) // 2]
        signs = []
        for part in (dev[dev < mid], dev[dev >= mid]):
            X, yy = design(y, c, x, L, part); b, *_ = ols(X, yy); signs.append(np.sign(b[list(X.columns).index("x")]))
        # 3. out-of-sample, expanding window, holdout only
        allidx = idx[idx >= start]
        f = oos(y, c, x, L, allidx, hold)
        tstat, p = clark_west(f)
        r.update(lag=L, coef_dev=float(coef), t_dev=float(coef / se), sign_halves=[int(s) for s in signs],
                 n_dev=int(len(dev)), n_hold=int(len(f)), hold_from=str(f.index.min().date()), hold_to=str(f.index.max().date()),
                 r2_oos=r2(f), r2_2016_2020=r2(f[f.index < SPLIT]), r2_2021_on=r2(f[f.index >= SPLIT]), cw_t=tstat, p=p)
        res.append(r)
    tested = [r for r in res if "p" in r]
    for r, q in zip(tested, bh([r["p"] for r in tested])): r["q"] = float(q)
    for r in tested:
        sgn = int(np.sign(r["coef_dev"])); why = []
        if r["direction"] in "+-" and sgn != (1 if r["direction"] == "+" else -1): why.append("opposite of the registered direction")
        if r["sign_halves"][0] != r["sign_halves"][1]: why.append("direction flipped within 2000–2015")
        if r["q"] > Q: why.append("not significant after the false-discovery control")
        if not r["r2_2016_2020"] > 0: why.append("no gain in 2016–2020")
        if not r["r2_2021_on"] > 0: why.append("no gain from 2021 on")
        r["status"] = "survived" if not why else "graveyard"; r["reason"] = "; ".join(why) if why else "passed every gate"
    os.makedirs(out, exist_ok=True)
    meta = dict(run="R1", generated=pd.Timestamp.now("UTC").isoformat(), family=len(tested), q=Q,
                survived=sum(r["status"] == "survived" for r in res),
                placebo_survived=sum(r["status"] == "survived" and r["external"] in PLACEBOS for r in res))
    json.dump({"meta": meta, "pairs": res}, open(os.path.join(out, "R1.json"), "w"), indent=1, default=float)
    print(json.dumps(meta))

if __name__ == "__main__": main(*sys.argv[1:])
