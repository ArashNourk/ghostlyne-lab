"""WATCH2 harness (see PREREGISTRATION_WATCH2.md).

Input: hourly BTC/USD OHLC (UTC, candle-close timestamps). Until licensed data is bought, the
lab check runs it on synthetic markets where the truth is known:
  sv     volatility clusters and has a daily rhythm (a dynamic model should be able to help)
  const  volatility never changes (negative control: no model can legitimately beat CV)

Models
  CV  first passage with variance = trailing 30-day mean Parkinson hourly variance, held constant
  G   first passage with variance re-forecast each hour: HAR on log Parkinson variance
      (last 1 h, 6 h, 24 h), one daily harmonic, log-linear reversion toward the 30-day level.
      Fitted parameters: 4 HAR + 2 harmonic + 1 reversion = 7 (limit 8). Refit monthly, expanding.
Alerts
  PROX  distance to stop below k
  ATR   distance to stop below m x ATR(14 h)
  CV, G rise in stop-first probability since the scenario started, at least theta
"""
import json, sys, time
import numpy as np, pandas as pd
from fp3 import fp3

SEED = 20261128
STOPS = [0.01, 0.02, 0.03]
TARGETS = [0.01, 0.02, 0.03, 0.04]
H = 24                      # horizon, hours
START_EVERY = 4             # hours between scenario starts (pre-registered)
PK = 1 / (4 * np.log(2))    # Parkinson scale
LN = np.log


# ---------------------------------------------------------------- synthetic markets
def synthetic(kind, years=6, seed=1):
    rng = np.random.default_rng(seed)
    n_h = int(years * 365 * 24)
    hours = np.arange(n_h)
    base = 0.025 / np.sqrt(24)                                   # ~2.5% daily volatility
    if kind == "sv":
        x = np.zeros(n_h)
        for t in range(1, n_h):                                  # clustered log-volatility
            x[t] = 0.985 * x[t - 1] + 0.075 * rng.standard_normal()
        bursts = rng.random(n_h) < 1 / 500                       # occasional volatility shocks
        shock = np.zeros(n_h)
        for t in np.flatnonzero(bursts):
            shock[t:t + 48] += 0.8 * np.exp(-np.arange(min(48, n_h - t)) / 12)
        diurnal = 0.25 * np.cos(2 * np.pi * ((hours % 24) - 15) / 24)
        sig = base * np.exp(x + shock + diurnal - 0.5 * np.var(x))
        eps = rng.standard_t(5, size=(n_h, 12)) / np.sqrt(5 / 3)
    else:
        sig = np.full(n_h, base)
        eps = rng.standard_normal((n_h, 12))
    r = eps * (sig[:, None] / np.sqrt(12))                       # 5-minute log returns
    path = np.cumsum(r.ravel()).reshape(n_h, 12)
    prev = np.concatenate([[0.0], path[:-1, -1]])
    o, c = prev, path[:, -1]
    hi = np.maximum(path.max(1), o); lo = np.minimum(path.min(1), o)
    idx = pd.date_range("2018-02-09", periods=n_h, freq="h", tz="UTC") + pd.Timedelta(hours=1)
    p0 = 10_000.0
    return pd.DataFrame({"open": p0 * np.exp(o), "high": p0 * np.exp(hi), "low": p0 * np.exp(lo), "close": p0 * np.exp(c)}, index=idx)


# ---------------------------------------------------------------- variance forecasts
def features(d):
    pk = PK * LN(d.high / d.low) ** 2
    floor = max(pk[pk > 0].quantile(0.01), 1e-12)
    pk = pk.clip(lower=floor)
    f = pd.DataFrame(index=d.index)
    f["pk"] = pk
    f["m1"] = pk
    f["m6"] = pk.rolling(6).mean()
    f["m24"] = pk.rolling(24).mean()
    f["m720"] = pk.rolling(720).mean()                           # 30-day level (CV variance per hour)
    r2 = LN(d.close / d.close.shift()) ** 2
    f["kfac"] = (r2.rolling(720).sum() / pk.rolling(720).sum()).clip(0.5, 3.0)   # range-to-return scale, trailing
    hod = d.index.hour.values
    f["c"], f["s"] = np.cos(2 * np.pi * hod / 24), np.sin(2 * np.pi * hod / 24)
    f["fut6"] = pk[::-1].rolling(6).mean()[::-1].shift(-1)       # mean variance over the next 6 hours
    return f


def fit_G(f):
    """HAR + daily harmonic on log variance; reversion speed chosen on the same (past-only) data."""
    ok = f[["m1", "m6", "m24", "m720", "fut6"]].notna().all(1)
    g = f[ok]
    X = np.column_stack([np.ones(len(g)), LN(g.m1), LN(g.m6), LN(g.m24), g.c, g.s])
    y = LN(g.fut6)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    s2 = np.var(y - X @ beta)
    best = None
    pk = g.pk.values
    for phi in (0.80, 0.85, 0.90, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995):
        v6 = np.exp(X @ beta + s2 / 2)
        err = 0.0
        for h in (6, 12, 24):
            pred = variance_path(v6, g.m720.values, phi, h)
            real = np.convolve(pk, np.ones(h), "full")[h:h + len(pk)][: len(pred)]
            m = min(len(pred), len(real))
            err += np.mean((LN(pred[:m]) - LN(np.maximum(real[:m], 1e-12))) ** 2)
        if best is None or err < best[0]:
            best = (err, phi)
    return {"beta": beta, "s2": s2, "phi": best[1]}


def variance_path(v_now, level, phi, h):
    """Integrated variance over the next h hours: per-hour variance reverts from v_now to level."""
    j = np.arange(h)
    return h * level + (v_now - level) * (phi ** j).sum()


# ---------------------------------------------------------------- scenarios and checkpoints
def scenarios(d, f):
    hi, lo, cl = d.high.values, d.low.values, d.close.values
    ok = f.m720.notna().values & f.m24.notna().values & f.kfac.notna().values
    starts = [t for t in range(len(d) - H - 1) if d.index[t].hour % START_EVERY == 0 and ok[t]]
    rows, scen = [], []
    sid = 0
    for t in starts:
        p0 = cl[t]
        for side in (1, -1):
            for sd in STOPS:
                for td in TARGETS:
                    stop = p0 * (1 - side * sd); tgt = p0 * (1 + side * td)
                    out, r = 0, H + 1                            # 0 neither, 1 target first, 2 stop first
                    for k in range(1, H + 1):
                        h_, l_ = hi[t + k], lo[t + k]
                        st = (l_ <= stop) if side == 1 else (h_ >= stop)
                        tg = (h_ >= tgt) if side == 1 else (l_ <= tgt)
                        if st: out, r = 2, k; break                 # same-hour double touch counts as stop first
                        if tg: out, r = 1, k; break
                    scen.append((sid, t, side, sd, td, out, r))
                    for c in range(0, min(r, H)):                    # checkpoints while unresolved
                        rows.append((sid, t + c, c, side, stop, tgt))
                    sid += 1
    S = pd.DataFrame(scen, columns=["sid", "t0", "side", "sd", "td", "out", "r"])
    C = pd.DataFrame(rows, columns=["sid", "t", "c", "side", "stop", "tgt"])
    C["price"] = cl[C.t.values]
    C["p0"] = cl[S.t0.values[C.sid.values]]
    return S, C


def probabilities(C, var_rem):
    side, P = C.side.values, C.price.values
    up_lvl = np.where(side == 1, C.tgt.values, C.stop.values)
    dn_lvl = np.where(side == 1, C.stop.values, C.tgt.values)
    pu, pd_, pn = fp3(LN(up_lvl / P), LN(P / dn_lvl), var_rem)
    p_t = np.where(side == 1, pu, pd_); p_s = np.where(side == 1, pd_, pu)
    return np.column_stack([p_t, p_s, pn])


def run(d, dev_end):
    f = features(d)
    S, C = scenarios(d, f)
    rem = (H - C.c.values).astype(float)
    # CV: constant per-hour variance from the trailing 30 days, frozen at scenario start
    level0 = (f.m720 * f.kfac).values[S.t0.values[C.sid.values]]
    P_cv = probabilities(C, level0 * rem)
    # G: monthly expanding refits; each checkpoint uses the fit from data before its month
    months = d.index[C.t.values].tz_localize(None).to_period("M")
    v_g = np.empty(len(C))
    first_fit_month = d.index[0].tz_localize(None).to_period("M") + 6
    for m in sorted(set(months)):
        sel = np.flatnonzero(months == m)
        cutoff = m.to_timestamp().tz_localize("UTC")
        past = f[f.index < cutoff - pd.Timedelta(hours=7)]
        if m < first_fit_month or len(past) < 24 * 120:
            v_g[sel] = np.nan; continue
        fit = fit_G(past)
        t = C.t.values[sel]
        X = np.column_stack([np.ones(len(t)), LN(f.m1.values[t]), LN(f.m6.values[t]), LN(f.m24.values[t]), f.c.values[t], f.s.values[t]])
        kf = f.kfac.values[t]
        v_now = np.exp(X @ fit["beta"] + fit["s2"] / 2) * kf
        lvl = f.m720.values[t] * kf
        h = rem[sel].astype(int)
        phi = fit["phi"]
        v_g[sel] = h * lvl + (v_now - lvl) * (1 - phi ** h) / (1 - phi)
    keep = ~np.isnan(v_g)
    C, P_cv, rem, v_g = C[keep].reset_index(drop=True), P_cv[keep], rem[keep], v_g[keep]
    P_g = probabilities(C, v_g)
    S = S[S.sid.isin(C.sid.unique())].reset_index(drop=True)
    out = S.set_index("sid").out.reindex(C.sid).values
    Y = np.zeros((len(C), 3)); Y[np.arange(len(C)), np.where(out == 1, 0, np.where(out == 2, 1, 2))] = 1
    C["dev"] = d.index[S.set_index("sid").t0.reindex(C.sid).values] < dev_end
    S["dev"] = d.index[S.t0.values] < dev_end
    C["block"] = d.index[S.set_index("sid").t0.reindex(C.sid).values].tz_localize(None).to_period("M").astype(str)
    S["block"] = d.index[S.t0.values].tz_localize(None).to_period("M").astype(str)
    return S, C, Y, {"CV": P_cv, "G": P_g}, f, d


# ---------------------------------------------------------------- calibration layer (lab amendment candidate)
def recalibrate(Pm, Y, dev, bins=40):
    """Per-class monotone map from predicted to observed frequency, learned on development data only
    (pool-adjacent-violators on equal-count bins), then renormalized across the three outcomes."""
    out = np.empty_like(Pm)
    for k in range(3):
        p, y = Pm[dev, k], Y[dev, k]
        q = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
        b = np.clip(np.searchsorted(q, p, side="right") - 1, 0, len(q) - 2)
        cnt = np.bincount(b, minlength=len(q) - 1).astype(float)
        mx = np.bincount(b, weights=p, minlength=len(q) - 1) / np.maximum(cnt, 1)
        my = np.bincount(b, weights=y, minlength=len(q) - 1) / np.maximum(cnt, 1)
        keep = cnt > 0; mx, my, w = mx[keep], my[keep], cnt[keep]
        vals, wts = list(my), list(w)                          # pool adjacent violators -> nondecreasing
        blocks = [[v, wt, 1] for v, wt in zip(vals, wts)]
        i = 0
        while i < len(blocks) - 1:
            if blocks[i][0] > blocks[i + 1][0]:
                a, c = blocks[i], blocks[i + 1]
                tot = a[1] + c[1]; blocks[i] = [(a[0] * a[1] + c[0] * c[1]) / tot, tot, a[2] + c[2]]; del blocks[i + 1]
                i = max(i - 1, 0)
            else:
                i += 1
        fitted = np.concatenate([[bl[0]] * bl[2] for bl in blocks])
        out[:, k] = np.interp(Pm[:, k], mx, fitted)
    out = np.clip(out, 1e-6, 1); return out / out.sum(1, keepdims=True)


# ---------------------------------------------------------------- metrics
def boot_rel(b_new, b_old, blocks, draws=2000, seed=SEED):
    """Relative Brier improvement 1 - new/old with a month-block bootstrap."""
    df = pd.DataFrame({"n": b_new, "o": b_old, "b": blocks}).groupby("b").sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(df), size=(draws, len(df)))
    n, o = df.n.values[idx].sum(1), df.o.values[idx].sum(1)
    rel = 1 - n / o
    return float(1 - df.n.sum() / df.o.sum()), float(np.quantile(rel, 0.025)), float(np.quantile(rel, 0.975))


def alerts(S, C, P, f, d):
    """First warning per scenario for each method; thresholds set on development data at 20% false warnings."""
    dist = np.abs(LN(C.price.values / C.stop.values))
    tr = np.maximum(d.high, d.close.shift()) - np.minimum(d.low, d.close.shift())
    atr = (tr / d.close).rolling(14).mean().values[C.t.values]
    first = {"CV": P["CV"][:, 1], "G": P["G"][:, 1]}
    base = {k: pd.Series(v).groupby(C.sid.values).transform("first").values for k, v in first.items()}
    score = {"PROX": -dist, "ATR": -dist / atr, "CV": first["CV"] - base["CV"], "G": first["G"] - base["G"],
             "CV-level": first["CV"], "G-level": first["G"]}
    res = {}
    Sx = S.set_index("sid")
    for name, sc in score.items():
        df = pd.DataFrame({"sid": C.sid.values, "c": C.c.values, "sc": sc})
        if name in ("CV", "G"): df = df[df.c > 0]                 # a rise needs a starting point
        mx = df.groupby("sid").sc.max().reindex(Sx.index).fillna(-np.inf)
        nostop_dev = (Sx.out != 2) & Sx.dev
        theta = float(np.quantile(mx[nostop_dev], 0.80))         # 20% of non-stop scenarios warned
        warned = df[df.sc >= theta].groupby("sid").c.min().reindex(Sx.index)
        conf = ~Sx.dev
        stop_c = conf & (Sx.out == 2)
        timely = warned.notna() & (Sx.r >= warned + 2)            # warned before the hour preceding the touch (>= 30 min lead at hourly resolution)
        far = float((warned.notna() & conf & (Sx.out != 2)).sum() / (conf & (Sx.out != 2)).sum())
        rec_by_block = pd.DataFrame({"hit": (timely & stop_c).astype(int), "n": stop_c.astype(int), "b": Sx.block})[stop_c].groupby("b").sum()
        res[name] = {"theta": theta, "recall": float((timely & stop_c).sum() / stop_c.sum()), "far": far, "_blocks": rec_by_block}
    return res


def recall_ratio_ci(a, b, draws=2000, seed=SEED):
    A, B = a["_blocks"], b["_blocks"].reindex(a["_blocks"].index).fillna(0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(A), size=(draws, len(A)))
    ra = A.hit.values[idx].sum(1) / A.n.values[idx].sum(1)
    rb = B.hit.values[idx].sum(1) / np.maximum(B.n.values[idx].sum(1), 1)
    r = ra / np.maximum(rb, 1e-9)
    return float(np.quantile(r, 0.025)), float(np.quantile(r, 0.975))


def evaluate(S, C, Y, P, f, d):
    conf = ~C.dev.values
    br = {k: ((v - Y) ** 2).sum(1) for k, v in P.items()}
    out = {"checkpoints_confirm": int(conf.sum()), "scenarios_confirm": int((~S.dev).sum())}
    rel, lo, hi = boot_rel(br["G"][conf], br["CV"][conf], C.block.values[conf])
    out["brier"] = {k: float(v[conf].mean()) for k, v in br.items()}
    out["H1"] = {"rel_improvement": rel, "ci": [lo, hi], "pass": rel >= 0.05 and lo > 0}
    # calibration of G, stop-first class, reliability bins with >= 500 checkpoints
    bins = [0, .05, .10, .20, .30, .50, .70, 1.0001]
    cal = []
    for cls, name in ((0, "target"), (1, "stop"), (2, "neither")):
        p, y = P["G"][conf, cls], Y[conf, cls]
        cut = pd.cut(p, bins, right=False)
        g = pd.DataFrame({"p": p, "y": y, "b": cut}).groupby("b", observed=True).agg(n=("y", "size"), pm=("p", "mean"), ym=("y", "mean"))
        for b, r in g.iterrows():
            if r.n < 500: continue
            z = 1.96; k = r.ym * r.n
            den = 1 + z * z / r.n; ctr = (r.ym + z * z / (2 * r.n)) / den
            half = z * np.sqrt(r.ym * (1 - r.ym) / r.n + z * z / (4 * r.n * r.n)) / den
            okb = (ctr - half <= r.pm <= ctr + half) or abs(r.pm - r.ym) <= max(0.02, 0.2 * r.ym)
            cal.append({"class": name, "bin": str(b), "n": int(r.n), "pred": round(r.pm, 4), "obs": round(r.ym, 4), "ok": bool(okb)})
    out["H1c"] = {"bins": cal, "pass": all(c["ok"] for c in cal)}
    al = alerts(S, C, P, f, d)
    best = max(("PROX", "ATR", "CV"), key=lambda k: al[k]["recall"])
    lo2, hi2 = recall_ratio_ci(al["G"], al[best])
    ratio = al["G"]["recall"] / max(al[best]["recall"], 1e-9)
    out["H2"] = {m: {"recall": round(v["recall"], 4), "false_warning_rate": round(v["far"], 4)} for m, v in al.items()}
    out["H2"]["best_benchmark"] = best
    out["H2"]["G_over_best"] = {"ratio": ratio, "ci": [lo2, hi2], "pass": ratio >= 1.05 and lo2 > 1 and 0.15 <= al["G"]["far"] <= 0.25}
    bestL = max(("PROX", "ATR", "CV-level"), key=lambda k: al[k]["recall"])
    loL, hiL = recall_ratio_ci(al["G-level"], al[bestL])
    rL = al["G-level"]["recall"] / max(al[bestL]["recall"], 1e-9)
    out["H2_level_rule"] = {"best_benchmark": bestL, "G_level_over_best": {"ratio": rL, "ci": [loL, hiL], "pass": rL >= 1.05 and loL > 1 and 0.15 <= al["G-level"]["far"] <= 0.25}}
    moved = np.abs(LN(C.price.values / C.p0.values))
    sub = conf & (moved <= 0.0025) & (np.abs(P["G"][:, 1] - P["CV"][:, 1]) >= 0.10)
    nmonths = C.block[sub].nunique()
    if sub.sum() >= 50:
        r3, l3, h3 = boot_rel(br["G"][sub], br["CV"][sub], C.block.values[sub])
    else:
        r3 = l3 = h3 = float("nan")
    out["H3"] = {"checkpoints": int(sub.sum()), "months": int(nmonths), "rel_improvement": r3, "ci": [l3, h3],
                 "pass": bool(sub.sum() >= 1000 and nmonths >= 24 and r3 >= 0.05 and l3 > 0), "enough_evidence": bool(sub.sum() >= 1000 and nmonths >= 24)}
    return out


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "sv"
    t0 = time.time()
    d = synthetic(kind, years=6, seed=7 if kind == "sv" else 8)
    dev_end = d.index[0] + pd.Timedelta(days=int(365 * 3.5))
    S, C, Y, P, f, d = run(d, dev_end)
    if "--cal" in sys.argv:
        dev = C.dev.values
        P = {"CV": recalibrate(P["CV"], Y, dev), "G": recalibrate(P["G"], Y, dev)}   # same layer on both: a fair comparison
    res = evaluate(S, C, Y, P, f, d)
    res["market"] = kind; res["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(res, indent=1, default=float))
    json.dump(res, open(f"lab_{kind}{'_cal' if '--cal' in sys.argv else ''}.json", "w"), indent=1, default=float)
