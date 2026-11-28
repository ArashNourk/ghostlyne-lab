"""WATCH2 harness (see PREREGISTRATION_WATCH2.md, Amendments 1-3).

Input: hourly BTC/USD OHLC (UTC, candle-close timestamps). Missing candles stay missing (never forward-filled).
Until licensed data is bought, the lab check runs it on synthetic markets where the truth is known:
  sv     volatility clusters and has a daily rhythm (a dynamic model should be able to help)
  const  volatility never changes (negative control: no model can legitimately beat the benchmarks)

Probability models (identical first-passage mathematics and identical development-only calibration):
  CV  variance = trailing 30-day level at scenario start, held constant
  V1  variance = frozen Ghostlyne V1 daily forecast for the start day (daily1/daily1.py, unchanged), held constant
  DV  variance = EWMA of range-scaled hourly variance, updated every hour; half-life chosen on development data
      from a fixed grid; held constant over the rest of the window (a strong simple dynamic baseline)
  G   variance re-forecast every hour: HAR on log Parkinson variance (1 h, 6 h, 24 h), one daily harmonic,
      log-linear reversion toward the 30-day level; 8 fitted quantities; refit monthly on past data only
Alerts: PROX (distance to stop), ATR (distance / ATR14), probability-level rules for CV, V1, DV and G,
and (secondary) the rise rule for CV and G.
"""
import importlib.util, json, os, sys, time
import numpy as np, pandas as pd
from fp3 import fp3

SEED = 20261128
STOPS = [0.01, 0.02, 0.03]
TARGETS = [0.01, 0.02, 0.03, 0.04]
H = 24                      # horizon, hours (primary); 8 is the registered secondary horizon
START_EVERY = 4             # hours between scenario starts (pre-registered)
PK = 1 / (4 * np.log(2))    # Parkinson scale
LN = np.log
FLOOR = 1e-10               # fixed minimum hourly Parkinson variance (~0.001% hourly volatility): no sample statistic
DV_GRID = (6, 12, 24, 48, 96)   # EWMA half-lives in hours for the DV benchmark

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("daily1_frozen", os.path.join(_here, "..", "daily1", "daily1.py"))
V1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(V1)


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


# ---------------------------------------------------------------- variance inputs (past-only)
def features(d):
    pk = (PK * LN(d.high / d.low) ** 2).clip(lower=FLOOR)       # missing candles stay NaN
    f = pd.DataFrame(index=d.index)
    f["pk"] = pk
    f["m1"] = pk
    f["m6"] = pk.rolling(6, min_periods=6).mean()
    f["m24"] = pk.rolling(24, min_periods=22).mean()
    f["m720"] = pk.rolling(720, min_periods=648).mean()           # 30-day level (CV variance per hour)
    r2 = LN(d.close / d.close.shift()) ** 2
    both = r2.notna() & pk.notna()
    f["kfac"] = (r2.where(both).rolling(720, min_periods=648).sum() / pk.where(both).rolling(720, min_periods=648).sum()).clip(0.5, 3.0)
    hod = d.index.hour.values
    f["c"], f["s"] = np.cos(2 * np.pi * hod / 24), np.sin(2 * np.pi * hod / 24)
    # fut6 is a forward-looking fitting target, used only on rows ending 7+ hours before each refit cutoff
    f["fut6"] = pk[::-1].rolling(6, min_periods=6).mean()[::-1].shift(-1)
    f["miss"] = d[["open", "high", "low", "close"]].isna().any(axis=1)
    return f


def v1_hourly_var(d):
    """Frozen V1 daily volatility forecast (information to the previous UTC day) as per-hour variance, by UTC day."""
    day_of = (d.index - pd.Timedelta(hours=1)).floor("D")        # candle open time decides its UTC day
    g = d.groupby(day_of)
    day = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(), "n": g.close.count()})
    day.loc[day.n < 24, ["open", "high", "low", "close"]] = np.nan   # incomplete days are missing, not guessed
    day.index = day.index.tz_localize(None)
    sig = V1.walk(V1.prepare(day[["open", "high", "low", "close"]]))
    return sig ** 2 / 24


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
    ok = (f.m720.notna() & f.m24.notna() & f.m6.notna() & f.kfac.notna()).values
    mc = np.concatenate([[0], np.cumsum(f.miss.values)])          # a window with any missing candle is unresolved: excluded
    starts = [t for t in range(len(d) - H - 1) if d.index[t].hour % START_EVERY == 0 and ok[t]
              and mc[t + H + 1] - mc[t] == 0]
    rows, scen = [], []
    sid = 0
    for t in starts:
        p0 = cl[t]
        for side in (1, -1):
            for sd in STOPS:
                for td in TARGETS:
                    stop = p0 * (1 - side * sd); tgt = p0 * (1 + side * td)
                    out, r = 0, H + 1                            # 0 neither, 1 target first, 2 stop first, 3 ambiguous
                    for k in range(1, H + 1):
                        h_, l_ = hi[t + k], lo[t + k]
                        st = (l_ <= stop) if side == 1 else (h_ >= stop)
                        tg = (h_ >= tgt) if side == 1 else (l_ <= tgt)
                        if st and tg: out, r = 3, k; break          # both crossed inside one candle: order unknown
                        if st: out, r = 2, k; break
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


def g_variance(d, f, C, rem):
    """G: monthly expanding refits; each checkpoint uses a fit from data ending 7+ hours before its month."""
    months = d.index[C.t.values].tz_localize(None).to_period("M")
    v_g = np.full(len(C), np.nan)
    first_fit_month = d.index[0].tz_localize(None).to_period("M") + 6
    for m in sorted(set(months)):
        sel = np.flatnonzero(months == m)
        cutoff = m.to_timestamp().tz_localize("UTC")
        past = f[f.index < cutoff - pd.Timedelta(hours=7)]
        if m < first_fit_month or len(past) < 24 * 120:
            continue
        fit = fit_G(past)
        t = C.t.values[sel]
        X = np.column_stack([np.ones(len(t)), LN(f.m1.values[t]), LN(f.m6.values[t]), LN(f.m24.values[t]), f.c.values[t], f.s.values[t]])
        kf = f.kfac.values[t]
        v_now = np.exp(X @ fit["beta"] + fit["s2"] / 2) * kf
        lvl = f.m720.values[t] * kf
        h = rem[sel].astype(int)
        phi = fit["phi"]
        v_g[sel] = h * lvl + (v_now - lvl) * (1 - phi ** h) / (1 - phi)
    return v_g


def run(d, dev_end):
    f = features(d)
    S, C = scenarios(d, f)
    rem = (H - C.c.values).astype(float)
    t0 = S.t0.values[C.sid.values]
    v = {}
    v["CV"] = (f.m720 * f.kfac).values[t0] * rem
    v1 = v1_hourly_var(d)
    v["V1"] = v1.reindex(d.index[t0].tz_localize(None).floor("D")).values * rem
    v["G"] = g_variance(d, f, C, rem)
    rsv = (f.pk * f.kfac)
    ew = {hl: rsv.ewm(halflife=hl, ignore_na=True, min_periods=hl).mean().values[C.t.values] * rem for hl in DV_GRID}
    avail = np.isfinite(v["CV"]) & np.isfinite(v["V1"]) & np.isfinite(v["G"]) & np.all([np.isfinite(e) for e in ew.values()], axis=0)
    C = C[avail].reset_index(drop=True); rem = rem[avail]
    v = {k: x[avail] for k, x in v.items()}; ew = {k: x[avail] for k, x in ew.items()}
    S = S[S.sid.isin(C.sid.unique())].reset_index(drop=True)
    # embargo: a development scenario's whole window, outcome included, ends before the split; straddlers dropped
    t0_time = d.index[S.t0.values]
    S["dev"] = (t0_time + pd.Timedelta(hours=H)) < dev_end
    S = S[~((~S.dev) & (t0_time < dev_end))].reset_index(drop=True)
    keep = C.sid.isin(S.sid).values
    C = C[keep].reset_index(drop=True); rem = rem[keep]
    v = {k: x[keep] for k, x in v.items()}; ew = {k: x[keep] for k, x in ew.items()}
    Sx = S.set_index("sid")
    C["dev"] = Sx.dev.reindex(C.sid).values
    C["t0"] = Sx.t0.reindex(C.sid).values
    C["out"] = Sx.out.reindex(C.sid).values
    for name, freq in (("block", "M"), ("block_w", "W"), ("block_q", "Q")):
        C[name] = d.index[C.t0.values].tz_localize(None).to_period(freq).astype(str)
        S[name] = d.index[S.t0.values].tz_localize(None).to_period(freq).astype(str)
    lvl = (f.m720 * f.kfac).values
    cuts = np.quantile(lvl[S.t0.values[S.dev.values]], [1 / 3, 2 / 3])   # regime cut points: development only
    S["regime"] = np.digitize(lvl[S.t0.values], cuts)
    C["regime"] = S.set_index("sid").regime.reindex(C.sid).values
    P = {k: probabilities(C, x) for k, x in v.items()}
    # DV half-life chosen on development checkpoints only (ambiguous outcomes dropped for the choice)
    dev = C.dev.values & (C.out.values != 3)
    Yd = np.zeros((dev.sum(), 3)); o = C.out.values[dev]
    Yd[np.arange(dev.sum()), np.where(o == 1, 0, np.where(o == 2, 1, 2))] = 1
    best_hl = min(DV_GRID, key=lambda hl: ((probabilities(C[dev], ew[hl][dev]) - Yd) ** 2).sum(1).mean())
    P["DV"] = probabilities(C, ew[best_hl])
    extras = {"v_g": v["G"], "rem": rem, "dv_halflife": best_hl}
    return S, C, P, extras, f, d


def labels(C, S, resolve):
    """Outcome matrix under one resolution of ambiguous candles: 'stop', 'target' or 'drop'."""
    out = C.out.values.copy()
    keepC = np.ones(len(C), bool)
    if resolve == "stop": out[out == 3] = 2
    elif resolve == "target": out[out == 3] = 1
    else: keepC = out != 3
    Y = np.zeros((len(C), 3)); Y[np.arange(len(C)), np.where(out == 1, 0, np.where(out == 2, 1, 2))] = 1
    So = S.copy(); so = So.out.values.copy()
    if resolve == "stop": so[so == 3] = 2
    elif resolve == "target": so[so == 3] = 1
    So["out"] = so
    if resolve == "drop": So = So[So.out != 3]
    return Y, keepC, So


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


def _first_warning(df, theta):
    return df[df.sc >= theta].groupby("sid").c.min()


def alerts(S, C, P, f, d):
    """Every alert method, two ways:
    operational: thresholds fitted on development data at a 20% false-warning rate, then applied unchanged;
    matched:     thresholds set on confirmation data aiming at 10/20/30% false warnings
                 (a discrimination comparison, not an operating rule); the achieved rate and any gap
                 caused by tied scores are reported (Amendment 4)."""
    dist = np.abs(LN(C.price.values / C.stop.values))
    tr = np.maximum(d.high, d.close.shift()) - np.minimum(d.low, d.close.shift())
    atr = (tr / d.close).rolling(14, min_periods=12).mean().values[C.t.values]
    first = {k: P[k][:, 1] for k in ("CV", "V1", "DV", "G")}
    base = {k: pd.Series(x).groupby(C.sid.values).transform("first").values for k, x in first.items()}
    score = {"PROX": -dist, "ATR": -dist / atr}
    for k in first: score[f"{k}-level"] = first[k]
    score["CV-rise"] = first["CV"] - base["CV"]; score["G-rise"] = first["G"] - base["G"]
    Sx = S.set_index("sid")
    conf = ~Sx.dev
    nostop_c = conf & (Sx.out != 2); stop_c = conf & (Sx.out == 2)
    res = {}
    for name, sc in score.items():
        df = pd.DataFrame({"sid": C.sid.values, "c": C.c.values, "sc": sc})
        df = df[np.isfinite(df.sc)]
        if name.endswith("-rise"): df = df[df.c > 0]
        mx = df.groupby("sid").sc.max().reindex(Sx.index).fillna(-np.inf)
        out = {}
        def score_at(theta, target=None):
            w = _first_warning(df, theta).reindex(Sx.index)
            timely = w.notna() & (Sx.r >= w + 2)                    # stop touched no earlier than the hour after next
            false_w = w.notna() & nostop_c
            lead = ((Sx.r - 1) - w)[timely & stop_c]
            hits = pd.DataFrame({"hit": (timely & stop_c).astype(int), "n": stop_c.astype(int), "b": Sx.block})[stop_c].groupby("b").sum()
            far = float(false_w.sum() / nostop_c.sum())
            extra = {}
            if target is not None:   # Amendment 4: achieved rate and threshold ties reported, never assumed equal to the target
                extra = {"target_far": target, "achieved_far": far, "far_gap_pp": round(100 * (far - target), 3),
                         "no_stop_scenarios_tied_at_threshold": int((mx[nostop_c] == theta).sum()),
                         "tie_discrepancy": bool(abs(far - target) > 0.005)}
            return {"recall": float((timely & stop_c).sum() / stop_c.sum()), "far": far, **extra,
                    "false_per_100_scenarios": float(100 * false_w.sum() / conf.sum()),
                    "median_lead_hours": float(lead.median()) if len(lead) else float("nan"), "_blocks": hits}
        theta_dev = float(np.quantile(mx[(Sx.out != 2) & Sx.dev], 0.80))
        out["operational"] = score_at(theta_dev)
        for q in (0.10, 0.20, 0.30):
            out[f"matched_{int(q * 100)}"] = score_at(float(np.quantile(mx[nostop_c], 1 - q)), target=q)
        res[name] = out
    return res


def ratio_ci(a, b, draws=2000, seed=SEED):
    A, B = a["_blocks"], b["_blocks"].reindex(a["_blocks"].index).fillna(0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(A), size=(draws, len(A)))
    ra = A.hit.values[idx].sum(1) / A.n.values[idx].sum(1)
    rb = B.hit.values[idx].sum(1) / np.maximum(B.n.values[idx].sum(1), 1)
    r = ra / np.maximum(rb, 1e-9)
    return float(np.quantile(r, 0.025)), float(np.quantile(r, 0.975))


def calibration_bins(p, y, min_n=500):
    bins = [0, .05, .10, .20, .30, .50, .70, 1.0001]
    g = pd.DataFrame({"p": p, "y": y, "b": pd.cut(p, bins, right=False)}).groupby("b", observed=True).agg(n=("y", "size"), pm=("p", "mean"), ym=("y", "mean"))
    out = []
    for b, r in g.iterrows():
        if r.n < min_n: continue
        z = 1.96; den = 1 + z * z / r.n; ctr = (r.ym + z * z / (2 * r.n)) / den
        half = z * np.sqrt(r.ym * (1 - r.ym) / r.n + z * z / (4 * r.n * r.n)) / den
        ok = (ctr - half <= r.pm <= ctr + half) or abs(r.pm - r.ym) <= max(0.02, 0.2 * r.ym)
        out.append({"bin": str(b), "n": int(r.n), "pred": round(r.pm, 4), "obs": round(r.ym, 4), "ok": bool(ok)})
    return out


def evaluate(S, C, Y, P, f, d):
    conf = ~C.dev.values
    br = {k: ((x - Y) ** 2).sum(1) for k, x in P.items()}
    ll = {k: -(Y * LN(np.clip(x, 1e-9, 1))).sum(1) for k, x in P.items()}
    out = {"checkpoints_confirm": int(conf.sum()), "scenarios_confirm": int((~S.dev).sum())}
    out["brier"] = {k: float(x[conf].mean()) for k, x in br.items()}
    out["log_loss"] = {k: float(x[conf].mean()) for k, x in ll.items()}
    bench = min(("CV", "V1", "DV"), key=lambda k: out["brier"][k])
    rel, lo, hi = boot_rel(br["G"][conf], br[bench][conf], C.block.values[conf])
    out["H1"] = {"benchmark": bench, "rel_improvement": rel, "ci": [lo, hi], "abs_improvement": float(br[bench][conf].mean() - br["G"][conf].mean()),
                 "vs_each": {k: round(boot_rel(br["G"][conf], br[k][conf], C.block.values[conf])[0], 4) for k in ("CV", "V1", "DV")},
                 "pass": rel >= 0.05 and lo > 0}
    out["H1_block_sensitivity"] = {nm: [round(x, 4) for x in boot_rel(br["G"][conf], br[bench][conf], C[col].values[conf])[1:]]
                                   for col, nm in (("block_w", "weekly"), ("block", "monthly"), ("block_q", "quarterly"))}
    out["H1_by_regime"] = {}
    for g_, nm in ((0, "low_vol"), (1, "mid_vol"), (2, "high_vol")):
        m_ = conf & (C.regime.values == g_)
        if m_.sum() > 1000:
            r_, l_, h_ = boot_rel(br["G"][m_], br[bench][m_], C.block.values[m_])
            out["H1_by_regime"][nm] = {"rel": round(r_, 4), "ci": [round(l_, 4), round(h_, 4)], "abs": round(float(br[bench][m_].mean() - br["G"][m_].mean()), 5), "checkpoints": int(m_.sum())}
    for m in ("G", "DV"):   # Amendment 4: each model has its own calibration gate
        cal = []
        for cls, name in ((0, "target"), (1, "stop"), (2, "neither")):
            for b in calibration_bins(P[m][conf, cls], Y[conf, cls]): cal.append({"class": name, **b})
        out[f"H1c_{m}"] = {"bins": cal, "pass": all(c["ok"] for c in cal)}
    # H2: discrimination at matched false-warning rates (gate), plus operational rates with development thresholds
    al = alerts(S, C, P, f, d)
    benches = ("PROX", "ATR", "CV-level", "V1-level", "DV-level")
    bestA = max(benches, key=lambda k: al[k]["matched_20"]["recall"])
    lo2, hi2 = ratio_ci(al["G-level"]["matched_20"], al[bestA]["matched_20"])
    ratio = al["G-level"]["matched_20"]["recall"] / max(al[bestA]["matched_20"]["recall"], 1e-9)
    g_op, b_op = al["G-level"]["operational"]["far"], al[bestA]["operational"]["far"]
    out["H2_methods"] = {m: {kind: {k_: (round(v_, 4) if isinstance(v_, float) else v_) for k_, v_ in r.items() if k_ != "_blocks"} for kind, r in x.items()} for m, x in al.items()}
    out["H2"] = {"benchmark": bestA, "matched20_recall_ratio": ratio, "ci": [lo2, hi2],
                 "matched20_achieved_far": {"G-level": al["G-level"]["matched_20"]["far"], bestA: al[bestA]["matched_20"]["far"]},
                 "operational_far_G": g_op, "operational_far_benchmark": b_op,
                 "pass": bool(ratio >= 1.05 and lo2 > 1 and 0.15 <= g_op <= 0.25 and g_op <= b_op + 0.02)}
    # H2c and H3 are computed for G (the registered candidate) and for DV (the simpler model the product would use if H1 fails)
    moved = np.abs(LN(C.price.values / C.p0.values))
    bestC = max(("PROX", "ATR"), key=lambda k: al[k]["matched_20"]["recall"])
    for m in ("G", "DV"):
        loc, hic = ratio_ci(al[f"{m}-level"]["matched_20"], al[bestC]["matched_20"])
        rc = al[f"{m}-level"]["matched_20"]["recall"] / max(al[bestC]["matched_20"]["recall"], 1e-9)
        m_op, gC = al[f"{m}-level"]["operational"]["far"], al[bestC]["operational"]["far"]
        out[f"H2c_{m}"] = {"benchmark": bestC, "matched20_recall_ratio": rc, "ci": [loc, hic],
                           "matched20_achieved_far": {f"{m}-level": al[f"{m}-level"]["matched_20"]["far"], bestC: al[bestC]["matched_20"]["far"]},
                           "operational_far": m_op, "operational_far_benchmark": gC,
                           "pass": bool(rc >= 1.05 and loc > 1 and 0.15 <= m_op <= 0.25 and m_op <= gC + 0.02)}
        # H3: price within 0.25% of the start, yet the model's stop-first probability moved 10+ pp since inception;
        # the model must beat the price-only view (CV) there, and be calibrated for rises and falls separately
        p0m = pd.Series(np.where(C.c.values == 0, P[m][:, 1], np.nan)).groupby(C.sid.values).transform("first").values
        chg = P[m][:, 1] - p0m
        sub = conf & (moved <= 0.0025) & np.isfinite(p0m) & (np.abs(chg) >= 0.10)
        rep = {"checkpoints": int(sub.sum()), "months": int(C.block[sub].nunique()), "enough_evidence": bool(sub.sum() >= 1000 and C.block[sub].nunique() >= 24)}
        if sub.sum() >= 50:
            rep["rel_vs_CV"] = boot_rel(br[m][sub], br["CV"][sub], C.block.values[sub])
            groups = {}
            for nm, mm in (("risk_rose", sub & (chg > 0)), ("risk_fell", sub & (chg < 0))):
                if mm.sum() >= 200:
                    pm, ym = float(P[m][mm, 1].mean()), float(Y[mm, 1].mean())
                    groups[nm] = {"n": int(mm.sum()), "pred_stop_first": round(pm, 4), "obs_stop_first": round(ym, 4),
                                  "cv_pred": round(float(P["CV"][mm, 1].mean()), 4), "ok": abs(pm - ym) <= max(0.02, 0.2 * ym)}
            rep["groups"] = groups
            direction = ("risk_rose" in groups and "risk_fell" in groups and groups["risk_rose"]["obs_stop_first"] > groups["risk_fell"]["obs_stop_first"])
            rep["pass"] = bool(rep["enough_evidence"] and rep["rel_vs_CV"][0] >= 0.05 and rep["rel_vs_CV"][1] > 0
                               and direction and all(g["ok"] for g in groups.values()))
        else:
            rep["pass"] = False
        out[f"H3_{m}"] = rep
    # H3a (reported): G and CV disagree by 10+ pp while price is within 0.25% of the start
    sub = conf & (moved <= 0.0025) & (np.abs(P["G"][:, 1] - P["CV"][:, 1]) >= 0.10)
    out["H3a_disagreement"] = {"checkpoints": int(sub.sum()), "months": int(C.block[sub].nunique()),
                               "rel_vs_CV": (boot_rel(br["G"][sub], br["CV"][sub], C.block.values[sub]) if sub.sum() >= 50 else None)}
    return out


def attribution(C, P_raw_unused, extras, f, d, n=60_000):
    """H4: exact Shapley split of the change in G's stop-first probability since inception into price, time and volatility."""
    conf = ~C.dev.values
    vg, rem = extras["v_g"], extras["rem"]
    vbar = vg / rem
    first = pd.DataFrame({"sid": C.sid.values, "c": C.c.values, "vbar": vbar, "price": C.price.values})
    inc = first[first.c == 0].set_index("sid")
    vbar0 = inc.vbar.reindex(C.sid).values
    rows = np.flatnonzero(conf & (C.c.values > 0) & np.isfinite(vbar0))
    t_next = C.t.values + 6
    okn = t_next < len(d)
    rows = rows[okn[rows]]
    fut = np.array([np.nansum(f.pk.values[t + 1:t + 7]) if not f.miss.values[t + 1:t + 7].any() else np.nan for t in C.t.values[rows]])
    rows = rows[np.isfinite(fut)]; fut = fut[np.isfinite(fut)]
    rng = np.random.default_rng(SEED)
    if len(rows) > n:
        pick = rng.choice(len(rows), n, replace=False); rows, fut = rows[pick], fut[pick]
    Cs = C.iloc[rows].reset_index(drop=True)
    P1, P0 = Cs.price.values, Cs.p0.values
    r1, r0 = rem[rows], np.full(len(rows), float(H))
    s1, s0 = vbar[rows], vbar0[rows]
    def ps(price, rr, ss):
        tmp = Cs.copy(); tmp["price"] = price
        return probabilities(tmp, ss * rr)[:, 1]
    val = {}
    for mask in range(8):
        val[mask] = ps(P1 if mask & 1 else P0, r1 if mask & 2 else r0, s1 if mask & 4 else s0)
    w = {0: 1 / 3, 1: 1 / 6, 2: 1 / 3}
    phi = {}
    for i, nm in ((0, "price"), (1, "time"), (2, "volatility")):
        tot = np.zeros(len(rows))
        for mask in range(8):
            if mask & (1 << i): continue
            k = bin(mask).count("1")
            tot += w[k] * (val[mask | (1 << i)] - val[mask])
        phi[nm] = tot
    total = val[7] - val[0]
    add_err = float(np.abs(sum(phi.values()) - total).max())
    surprise = LN(fut * f.kfac.values[Cs.t.values] / np.maximum(s1 * 6, 1e-15))
    blocks = Cs.block.values
    def spear(x, y):
        return float(pd.Series(x).rank().corr(pd.Series(y).rank()))
    rho = spear(phi["volatility"], surprise)
    ub = np.unique(blocks); bi = {b: np.flatnonzero(blocks == b) for b in ub}
    draws = []
    for _ in range(300):
        pickb = rng.choice(ub, len(ub)); ix = np.concatenate([bi[b] for b in pickb])
        draws.append(spear(phi["volatility"][ix], surprise[ix]))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {"rows": int(len(rows)), "additivity_max_error_pp": add_err * 100,
            "mean_abs_contribution_pp": {k: round(float(np.abs(v).mean() * 100), 3) for k, v in phi.items()},
            "volatility_validity_spearman": rho, "ci": [float(lo), float(hi)],
            "pass": bool(add_err <= 0.001 and lo > 0)}


RESOLUTIONS = ("stop", "target", "drop")
DEFERRED = {"G+A asymmetry, G+R regime": "not implemented; deferred to a new registration (Amendment 3)",
            "H4 factors": "price, time and volatility only (the factors in G)",
            "user-facing attribution": "disabled for the initial release (Amendment 4); H4 is reported only"}


def full(d, dev_end, cal=True):
    S, C, P, extras, f, d = run(d, dev_end)
    report = {"horizon_hours": H, "scenarios_total": int(len(S)), "ambiguous_share": float((S.out == 3).mean()),
              "dv_halflife_hours": extras["dv_halflife"], "deferred": DEFERRED, "by_resolution": {}}
    report["H4_reported_only"] = attribution(C, None, extras, f, d)
    report["H4_reported_only"]["note"] = ("evaluates uncalibrated G, not the production model; authorizes nothing (Amendment 4)")
    for res in RESOLUTIONS:
        Y, keep, So = labels(C, S, res)
        Cc = C[keep].reset_index(drop=True); Yc = Y[keep]; Pc = {k: x[keep] for k, x in P.items()}
        if cal:   # fitted on development rows only; the held-out period never informs the map
            dev = Cc.dev.values
            Pc = {k: recalibrate(x, Yc, dev) for k, x in Pc.items()}
        report["by_resolution"][res] = evaluate(So, Cc, Yc, Pc, f, d)
    br = report["by_resolution"]
    report["gates_all_resolutions"] = {
        "H1": all(br[r]["H1"]["pass"] for r in RESOLUTIONS),
        "H1c_G": all(br[r]["H1c_G"]["pass"] for r in RESOLUTIONS),
        "H1c_DV": all(br[r]["H1c_DV"]["pass"] for r in RESOLUTIONS),
        "H2": all(br[r]["H2"]["pass"] for r in RESOLUTIONS),
        "H2c_G": all(br[r]["H2c_G"]["pass"] for r in RESOLUTIONS),
        "H2c_DV": all(br[r]["H2c_DV"]["pass"] for r in RESOLUTIONS),
        "H3_G": all(br[r]["H3_G"]["pass"] for r in RESOLUTIONS),
        "H3_DV": all(br[r]["H3_DV"]["pass"] for r in RESOLUTIONS)}
    g = report["gates_all_resolutions"]
    # Amendment 4: G is the production model only if H1 and H2 both pass; otherwise DV.
    # Every claim must then pass for the production model itself, under all three ambiguity treatments.
    pm = "G" if (g["H1"] and g["H2"]) else "DV"
    cal_ok = g[f"H1c_{pm}"]
    report["production"] = {
        "model": pm,
        "rule": "G only if H1 and H2 both pass; otherwise DV",
        "gates": {"calibration": cal_ok, "conventional_alerts_H2c": g[f"H2c_{pm}"], "same_price_H3": g[f"H3_{pm}"]},
        "authorized": {
            "publish_probabilities": cal_ok,
            "model_advantage_claim": pm == "G" and cal_ok,
            "conventional_alert_claim": cal_ok and g[f"H2c_{pm}"],
            "same_price_headline": cal_ok and g[f"H3_{pm}"],
            "user_facing_attribution": False}}
    return report


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "sv"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 101
    if "--h8" in sys.argv: H = 8
    t0 = time.time()
    d = synthetic(kind, years=6, seed=seed)
    dev_end = d.index[0] + pd.Timedelta(days=int(365 * 3.5))
    rep = full(d, dev_end, cal=True)
    rep.update({"market": kind, "seed": seed, "seconds": round(time.time() - t0, 1)})
    os.makedirs("lab", exist_ok=True)
    json.dump(rep, open(f"lab/{kind}_seed{seed}{'_h8' if H == 8 else ''}.json", "w"), indent=1, default=float)
    b = rep["by_resolution"]["stop"]
    print(f"{kind} seed {seed} H={H}h: H1 {b['H1']['rel_improvement']:+.2%} vs {b['H1']['benchmark']} | H2 {b['H2']['matched20_recall_ratio']:.3f}x vs {b['H2']['benchmark']} | "
          f"H2c G {b['H2c_G']['matched20_recall_ratio']:.3f}x / DV {b['H2c_DV']['matched20_recall_ratio']:.3f}x vs {b['H2c_G']['benchmark']} | DV half-life {rep['dv_halflife_hours']}h | gates {rep['gates_all_resolutions']} | production {rep['production']['model']} authorized {rep['production']['authorized']} | {rep['seconds']}s")
