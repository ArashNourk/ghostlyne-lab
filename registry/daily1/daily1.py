"""DAILY1: can a public-data engine state today's Bitcoin/Ethereum range and level-touch odds honestly?

Fixed by PREREGISTRATION_DAILY1.md. Raw prices are used inside the run only; outputs are derived statistics.
Usage: python daily1.py [--synthetic]   (writes out/DAILY1.json)
"""
import json, os, sys, time, numpy as np, pandas as pd, requests

SEED = 20261127
ASSETS = ["BTC-USD", "ETH-USD"]
EVAL_START = "2018-01-01"
LEVELS = [0.5, 0.7, 0.9]                       # range coverage levels; 0.7 is the published one
TOUCH_D = [0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.18]   # level distance from the day's open, each side
BINS = [0, 0.02, 0.05, 0.10, 0.20, 0.40, 0.70, 1.01]
TRAIN_YEARS = 4                                # trailing window for standardized excursions
P = 1 / np.sqrt(4 * np.log(2))                 # Parkinson scale

def fetch(product):
    """Coinbase Exchange public daily candles (UTC days): [time, low, high, open, close, volume]."""
    rows, end = [], pd.Timestamp.utcnow().normalize()
    start0 = pd.Timestamp("2015-07-20", tz="UTC")
    while end > start0:
        start = max(start0, end - pd.Timedelta(days=299))
        for a in range(5):
            try:
                r = requests.get(f"https://api.exchange.coinbase.com/products/{product}/candles",
                                 params={"granularity": 86400, "start": start.isoformat(), "end": end.isoformat()},
                                 headers={"User-Agent": "ghostlyne-lab research"}, timeout=60)
                r.raise_for_status(); rows += r.json(); break
            except Exception:
                time.sleep(3 * (a + 1))
        end = start - pd.Timedelta(days=1); time.sleep(0.4)
    d = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"]).drop_duplicates("t")
    d["date"] = pd.to_datetime(d.t, unit="s").dt.normalize(); d = d.set_index("date").sort_index()
    d = d[(d.high > 0) & (d.low > 0) & (d.high >= d.low)]
    return d[["open", "high", "low", "close"]].astype(float)

def synthetic(n=4000, seed=1):
    rng = np.random.default_rng(seed); s, v, o, out = 0.0, 0.03, 100.0, []
    for i in range(n):
        v = np.sqrt(0.00002 + 0.90 * v ** 2 + 0.08 * (rng.standard_normal() * v) ** 2)
        path = o * np.exp(np.cumsum(rng.standard_normal(96) * v / np.sqrt(96)))
        out.append((o, max(o, path.max()), min(o, path.min()), path[-1])); o = path[-1]
    idx = pd.date_range("2015-07-20", periods=n, freq="D")
    return pd.DataFrame(out, index=idx, columns=["open", "high", "low", "close"])

def prepare(d):
    d = d.copy()
    d["pk"] = np.log(d.high / d.low) * P                      # Parkinson daily vol proxy
    d["lpk"] = np.log(d.pk.clip(lower=1e-4))
    d["f1"] = d.lpk.shift(1); d["f5"] = d.lpk.rolling(5).mean().shift(1); d["f22"] = d.lpk.rolling(22).mean().shift(1)
    d["dow"] = d.index.dayofweek
    d["up"] = np.log(d.high / d.open); d["dn"] = np.log(d.open / d.low)
    d["rv30"] = np.log(d.close / d.close.shift(1)).rolling(30).std().shift(1)
    return d

def walk(d):
    """Monthly refit, information to the previous UTC day only. Returns sigma-hat per day (M1) and baselines."""
    sig = pd.Series(np.nan, index=d.index)
    months = pd.period_range(d.index[0], d.index[-1], freq="M")
    for m in months:
        te = (d.index.to_period("M") == m); tr = d.index < m.start_time
        x = d[tr].dropna(subset=["f1", "f5", "f22", "lpk"])
        if len(x) < 500 or te.sum() == 0: continue
        X = np.column_stack([np.ones(len(x)), x.f1, x.f5, x.f22, (x.dow >= 5).astype(float)])
        beta, *_ = np.linalg.lstsq(X, x.lpk.values, rcond=None)
        res = x.lpk.values - X @ beta; adj = np.exp(0.5 * res.var())
        y = d[te]
        Xt = np.column_stack([np.ones(len(y)), y.f1, y.f5, y.f22, (y.dow >= 5).astype(float)])
        sig[te] = np.exp(Xt @ beta) * adj
    return sig

def forecasts(d, sig):
    """For each eval day: range multipliers per coverage level, touch probabilities per level (M1, B0, B1)."""
    out = []
    ev = d.index >= EVAL_START
    for t in d.index[ev]:
        s = sig.get(t)
        if not np.isfinite(s) or not np.isfinite(d.at[t, "rv30"]): continue
        tr = d[(d.index < t) & (d.index >= t - pd.Timedelta(days=365 * TRAIN_YEARS))]
        st = sig[tr.index]; ok = st.notna()
        tr, st = tr[ok], st[ok]
        if len(tr) < 365: continue
        zu, zd = (tr.up / st).values, (tr.dn / st).values
        zmax = np.maximum(zu, zd)
        rec = dict(date=str(t.date()), sigma=float(s), up=float(d.at[t, "up"]), dn=float(d.at[t, "dn"]))
        for L in LEVELS:
            k = np.quantile(zmax, L); rec[f"k{int(L*100)}"] = float(k)
            rec[f"in{int(L*100)}"] = bool(d.at[t, "up"] <= k * s and d.at[t, "dn"] <= k * s)
        last = tr[tr.index >= t - pd.Timedelta(days=365)]
        rv = d.at[t, "rv30"]; zu_b1, zd_b1 = (tr.up / tr.rv30).values, (tr.dn / tr.rv30).values
        for dist in TOUCH_D:
            lu, ld = np.log(1 + dist), np.log(1 / (1 - dist))
            for side, z, zb1, raw, lv in (("u", zu, zu_b1, last.up.values, lu), ("d", zd, zd_b1, last.dn.values, ld)):
                rec[f"m1_{side}{dist}"] = float(np.mean(z >= lv / s))
                rec[f"b0_{side}{dist}"] = float(np.mean(raw >= lv))
                rec[f"b1_{side}{dist}"] = float(np.nanmean(zb1 >= lv / rv))
                rec[f"hit_{side}{dist}"] = bool((d.at[t, "up"] if side == "u" else d.at[t, "dn"]) >= lv)
        out.append(rec)
    return pd.DataFrame(out)

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)

def evaluate(f, rng):
    r = dict(n_days=int(len(f)))
    f["year"] = f.date.str[:4]
    for L in LEVELS:
        c = f[f"in{int(L*100)}"]
        r[f"coverage{int(L*100)}"] = dict(pooled=float(c.mean()), ci=wilson(c.sum(), len(c)), by_year={y: float(g.mean()) for y, g in c.groupby(f.year)})
        # by volatility regime (tercile of sigma)
        q = pd.qcut(f.sigma, 3, labels=["calm", "normal", "wild"])
        r[f"coverage{int(L*100)}"]["by_regime"] = {str(k): float(g.mean()) for k, g in c.groupby(q, observed=True)}
    cols = [(s, dd) for s in "ud" for dd in TOUCH_D]
    long = pd.concat([pd.DataFrame({"date": f.date, "m1": f[f"m1_{s}{dd}"], "b0": f[f"b0_{s}{dd}"], "b1": f[f"b1_{s}{dd}"], "y": f[f"hit_{s}{dd}"].astype(float)}) for s, dd in cols])
    rel = []
    b = pd.cut(long.m1, BINS, right=False)
    for k, g in long.groupby(b, observed=True):
        lo, hi = wilson(g.y.sum(), len(g))
        rel.append(dict(bin=str(k), n=int(len(g)), predicted=float(g.m1.mean()), observed=float(g.y.mean()), ci=[float(lo), float(hi)],
                        ok=bool(lo <= g.m1.mean() <= hi or abs(g.y.mean() - g.m1.mean()) <= max(0.02, 0.25 * g.m1.mean()))))
    r["touch_reliability"] = rel
    def brier(col): return ((long[col] - long.y) ** 2).groupby(long.date).sum()
    bm, b0, b1 = brier("m1"), brier("b0"), brier("b1")
    def bss(a, base):
        idx = np.arange(len(a)); blocks = [idx[i:i + 30] for i in range(0, len(idx), 30)]; vals = []
        A, B = a.values, base.values
        for _ in range(2000):
            pick = np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), len(blocks))])
            vals.append(1 - A[pick].sum() / B[pick].sum())
        return dict(bss=float(1 - A.sum() / B.sum()), ci=[float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))])
    r["brier_vs_b0"], r["brier_vs_b1"] = bss(bm, b0), bss(bm, b1)
    tail = long[long.m1 <= 0.03]
    exp_, obs = float(tail.m1.sum()), float(tail.y.sum())
    from scipy.stats import poisson
    r["tail"] = dict(n=int(len(tail)), expected=exp_, observed=obs, ratio=obs / exp_ if exp_ else None,
                     poisson_ci=[float(poisson.ppf(0.025, obs)) / exp_ if exp_ else None, float(poisson.ppf(0.975, obs + 1)) / exp_ if exp_ else None])
    c70 = r["coverage70"]
    r["gates"] = dict(
        G1_coverage=bool(0.66 <= c70["pooled"] <= 0.74 and all(0.60 <= v <= 0.80 for v in c70["by_year"].values())),
        G2_touch_calibration=bool(all(x["ok"] for x in rel if x["n"] >= 200)),
        G3_skill=bool(r["brier_vs_b0"]["ci"][0] > 0 and r["brier_vs_b1"]["ci"][0] > 0),
        G4_tail=bool(r["tail"]["ratio"] is not None and 0.67 <= r["tail"]["ratio"] <= 1.5))
    return r

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True); rng = np.random.default_rng(SEED); res = {}
    for a in ASSETS:
        d = synthetic(seed=1 if a == "BTC-USD" else 2) if "--synthetic" in sys.argv else fetch(a)
        d = prepare(d); sig = walk(d); f = forecasts(d, sig)
        r = evaluate(f, rng); r["first_date"], r["last_date"] = str(d.index[0].date()), str(d.index[-1].date())
        res[a] = r; print(a, json.dumps(r["gates"]), flush=True)
    json.dump(res, open("out/DAILY1.json", "w"), indent=1, default=str)
    open("out/SOURCES.md", "w").write("Coinbase Exchange public daily candles (BTC-USD, ETH-USD), used inside the run only; only derived statistics are published.\n")
