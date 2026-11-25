"""Ghostlyne research harness: predictions for every method, the max-leverage rule, conditional calibration and the
matched-risk leverage frontier. Development evaluation is 2024-01-01 onward; 2022 is the untouched holdout and is only
evaluated by holdout.py after the rules are locked."""
import sys, json, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT / "engine")); import common as G

LEV = np.array(G.LEVERAGE)            # 40, 20, 15, 10, 7, 5
CAP = 20
BASES = ["Textbook (ATR, normal)", "EWMA RiskMetrics", "GARCH(1,1)-t", "Filtered historical simulation", "Rolling 1-year frequency"]

def load_table(path):
    D = pd.read_parquet(path).sort_values(["Date", "sym"]).reset_index(drop=True); return D

def predictions(D, start, extra=None):
    """P[method][side] -> array [n, 6] calibrated + monotone; Y[side] -> [n, 6] outcomes."""
    sd_e = G.ewma_sd(D); sd_g = G.garch_sd(D, start)
    P, Y = {}, {}
    for side in ["long", "short"]:
        Ys = np.full((len(D), 6), np.nan); raws = {}
        for j, L in enumerate(LEV):
            k = G.DIST[L]; raw, y = G.model_walk(D, side, k, start); Ys[:, j] = y
            r = {"Ghostlyne": raw, BASES[0]: G.textbook(D, side, k), BASES[1]: G.reflection(sd_e, side, k), BASES[2]: G.reflection(sd_g, side, k),
                 BASES[3]: G.fhs_prob(D, side, k, sd_e), BASES[4]: G.rolling_freq(D, side, k)}
            if extra: r.update(extra(D, side, k, start, sd_e, sd_g))
            for nm, v in r.items(): raws.setdefault(nm, np.full((len(D), 6), np.nan))[:, j] = np.where(D.Date >= start, v, np.nan)
        for nm, R in raws.items():
            C = np.column_stack([G.calibrate_walk(D, R[:, j], Ys[:, j]) for j in range(6)])
            P.setdefault(nm, {})[side] = G.monotone(C)[0]
        Y[side] = Ys; print(side, "done", flush=True)
    return P, Y

# ---------------------------------------------------------------- the max-leverage rule
def recommend(Pm, thr, cap=CAP):
    """Highest leverage <= cap whose odds are <= thr; 0 = abstain. Returns (lev, column index or -1)."""
    ok = (Pm <= thr + 1e-12) & (LEV <= cap)[None, :]
    lev = np.where(ok, LEV[None, :], 0).max(1); col = np.array([list(LEV).index(l) if l else -1 for l in lev])
    return lev, col

def rule_outcomes(Pm, Ym, rows, thr, cap=CAP):
    lev, col = recommend(Pm[rows], thr, cap); has = col >= 0
    hit = np.full(len(rows), np.nan); p = np.full(len(rows), np.nan)
    hit[has] = Ym[rows[has], col[has]]; p[has] = Pm[rows[has], col[has]]
    return lev, hit, p

def week_boot_rate(dates, hit, B=2000, seed=0):
    """Rate with a 90% interval from a week-block bootstrap (all markets in a week resampled together)."""
    m = ~np.isnan(hit); g = pd.DataFrame({"w": pd.to_datetime(dates[m]).to_period("W"), "h": hit[m]}).groupby("w").h.agg(["sum", "count"])
    if len(g) < 5: return float(np.nanmean(hit)) if m.any() else np.nan, (np.nan, np.nan)
    rng = np.random.default_rng(seed); s, c = g["sum"].values, g["count"].values; i = rng.integers(0, len(g), (B, len(g)))
    bs = s[i].sum(1) / c[i].sum(1); return float(s.sum() / c.sum()), (float(np.percentile(bs, 5)), float(np.percentile(bs, 95)))

# ---------------------------------------------------------------- regimes (all known at forecast time)
def regimes(D):
    """vol_pct: today's 7-day vol vs the market's own trailing 365 days (percentile). Stress: market-wide breadth of
    big down days. btc_pct: BTC 7-day vol percentile."""
    R = pd.DataFrame(index=D.index)
    R["vol_pct"] = D.groupby("sym").v7.transform(lambda s: s.rolling(365, min_periods=120).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True))
    br = D.groupby("Date").ret1.transform(lambda s: (s < -0.05).mean()); R["breadth_down"] = br
    bu = D.groupby("Date").ret1.transform(lambda s: (s > 0.05).mean()); R["breadth_up"] = bu
    R["v1_rel"] = D.v1 - D.v30                                   # today's range vs the month
    return R

def bucket(x, edges, labels):
    return pd.cut(x, edges, labels=labels, include_lowest=True).astype(str)

# ---------------------------------------------------------------- matched-risk frontier
def frontier(Pm, Ym, rows, grid=np.round(np.arange(0.005, 0.1501, 0.0025), 4), cap=CAP):
    """For each threshold: realized liquidation rate of recommended positions and mean leverage offered (abstain = 0)."""
    out = []
    for t in grid:
        lev, hit, _ = rule_outcomes(Pm, Ym, rows, t, cap)
        out.append((t, np.nanmean(hit) if np.isfinite(hit).any() else np.nan, lev.mean(), (lev > 0).mean()))
    return pd.DataFrame(out, columns=["thr", "realized", "mean_lev", "coverage"])

def lev_at_rate(F, target):
    f = F.dropna().sort_values("realized")
    if f.realized.min() > target or f.realized.max() < target: return np.nan
    return float(np.interp(target, f.realized.values, f.mean_lev.values))

def matched_boot(Pa, Pb, Ym, rows, dates, target, B=300, seed=0):
    """Difference in mean leverage offered at the same realized rate (a minus b), week-block bootstrap."""
    grid = np.round(np.arange(0.005, 0.1501, 0.0025), 4)
    def per_week(Pm):
        wk = pd.to_datetime(dates[rows]).to_period("W"); res = []
        for t in grid:
            lev, hit, _ = rule_outcomes(Pm, Ym, rows, t)
            g = pd.DataFrame({"w": wk, "h": np.nan_to_num(hit), "n": ~np.isnan(hit), "l": lev}).groupby("w")[["h", "n", "l"]].sum()
            res.append(g.values)
        return np.stack(res), len(rows)
    A, n = per_week(Pa); Bm, _ = per_week(Pb); W = A.shape[1]; cnt = pd.Series(pd.to_datetime(dates[rows]).to_period("W")).value_counts().sort_index().values
    rng = np.random.default_rng(seed); diffs = []
    def lev_rate(M, idx):
        h = M[:, idx, 0].sum(1); nn = M[:, idx, 1].sum(1); l = M[:, idx, 2].sum(1); tot = cnt[idx].sum()
        F = pd.DataFrame({"realized": h / np.maximum(nn, 1), "mean_lev": l / tot}); return lev_at_rate(F, target)
    full = lev_rate(A, np.arange(W)) - lev_rate(Bm, np.arange(W))
    for _ in range(B):
        idx = rng.integers(0, W, W); diffs.append(lev_rate(A, idx) - lev_rate(Bm, idx))
    d = np.array(diffs); d = d[np.isfinite(d)]
    return float(full), (float(np.percentile(d, 5)), float(np.percentile(d, 95))) if len(d) > 50 else (np.nan, np.nan)
