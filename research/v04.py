"""v0.4 candidates: smoother calibration (resolution) and a max-leverage rule whose internal threshold is set walk-forward so
realized liquidations land near the chosen limit (replacing the fixed halving on stress days)."""
import numpy as np, pandas as pd
from sklearn.isotonic import IsotonicRegression
import lab
G = lab.G

def logit(p): p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))

class SmoothIso:
    """Isotonic regression, then linear interpolation (in logit-raw space) between the centres of its constant blocks.
    Same monotone fit, but neighbouring inputs no longer collapse onto one identical probability."""
    def __init__(self, raw, y, ymin=1e-4, ymax=0.999):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=ymin, y_max=ymax).fit(raw, y)
        fit = iso.predict(raw); x = logit(raw)
        df = pd.DataFrame({"x": x, "f": np.round(fit, 10)}).groupby("f").x.mean().reset_index().sort_values("x")
        self.cx, self.cy = df.x.values, df.f.values
        if len(self.cx) < 2: self.cx, self.cy = np.array([x.min(), x.max() + 1e-9]), np.array([fit.mean()] * 2)
    def predict(self, raw): return np.interp(logit(raw), self.cx, self.cy)

def iso_step(raw, y): return IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999).fit(raw, y)

def calibrate_walk_regime(D, raw, y, stress, smooth=False, cal_months=12, stress_months=24):
    """Exactly the v0.3 regime calibration (research/candidates.py), optionally with SmoothIso maps."""
    mk = (lambda a, b: SmoothIso(a, b)) if smooth else iso_step
    cal = np.full(len(D), np.nan)
    for ms in pd.date_range(D.Date.min().replace(day=1), D.Date.max(), freq="MS"):
        mon = (D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)); ok = ~np.isnan(raw)
        hist = (D.Date < ms - pd.Timedelta(days=1)) & ok & ~np.isnan(y)
        pn = np.where(hist & (D.Date >= ms - pd.DateOffset(months=cal_months)) & ~stress)[0]
        ps = np.where(hist & (D.Date >= ms - pd.DateOffset(months=stress_months)) & stress)[0]
        pa = np.where(hist & (D.Date >= ms - pd.DateOffset(months=cal_months)))[0]
        if len(pa) <= 1000 or y[pa].sum() < 20: continue
        pooled = mk(raw[pa], y[pa])
        tn = np.where(mon & ok & ~stress)[0]; ts = np.where(mon & ok & stress)[0]
        if len(tn): cal[tn] = (mk(raw[pn], y[pn]) if len(pn) > 1000 and y[pn].sum() >= 20 else pooled).predict(raw[tn])
        if len(ts):
            if len(ps) > 300 and y[ps].sum() >= 15: cal[ts] = mk(raw[ps], y[ps]).predict(raw[ts])
            elif len(ps) > 100:
                f = (y[ps].sum() + 1) / (pooled.predict(raw[ps]).sum() + 1); cal[ts] = np.clip(pooled.predict(raw[ts]) * max(f, 1.0), 1e-4, 0.999)
            else: cal[ts] = pooled.predict(raw[ts])
    return cal

TAU_GRID = np.round(np.arange(0.0025, 0.2001, 0.0025), 4)

def tuned_thresholds(D, Pm, Ym, stress, limit, months_n=12, months_s=24, min_n=300, margin=0.9):
    """Walk-forward, monthly: for normal and stress rows separately, the largest internal threshold tau whose recommended
    positions over the lookback were liquidated at or below margin x `limit` (a 10% safety margin). Fallback tau = limit (normal) or limit/2 (stress)."""
    tau = np.full(len(D), np.nan); okrow = ~np.isnan(Pm).any(1) & ~np.isnan(Ym).any(1)
    for ms in pd.date_range(D.Date.min().replace(day=1), D.Date.max(), freq="MS"):
        mon = ((D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1))).values
        for grp, months, fb in [(~stress, months_n, limit), (stress, months_s, limit / 2)]:
            te = np.where(mon & grp)[0]
            if not len(te): continue
            past = np.where(((D.Date < ms - pd.Timedelta(days=1)) & (D.Date >= ms - pd.DateOffset(months=months))).values & grp & okrow)[0]
            t_best = fb
            if len(past) >= min_n:
                ok_t = []
                for t in TAU_GRID:
                    lev, hit, _ = lab.rule_outcomes(Pm, Ym, past, t)
                    if np.isfinite(hit).sum() >= min_n / 3 and np.nanmean(hit) <= margin * limit: ok_t.append(t)
                t_best = max(ok_t) if ok_t else TAU_GRID[0]
            tau[te] = t_best
    return tau

def rule_tau(Pm, Ym, rows, tau, cap=20):
    """Max-leverage rule with a per-row internal threshold."""
    P = Pm[rows]; ok = (P <= tau[rows][:, None] + 1e-12) & (lab.LEV <= cap)[None, :]
    lev = np.where(ok, lab.LEV[None, :], 0).max(1); col = np.array([list(lab.LEV).index(l) if l else -1 for l in lev])
    has = col >= 0; hit = np.full(len(rows), np.nan); p = np.full(len(rows), np.nan)
    hit[has] = Ym[rows[has], col[has]]; p[has] = P[has, col[has]]
    return lev, hit, p

def hybrid_thresholds(D, Pm, Ym, stress, limit):
    """The v0.4 rule: tuned threshold on normal days; on stress days the fixed limit halved (as in v0.3). In development the
    tuned stress threshold overshot in 2024 (stress samples are too thin to tune), the halved limit did not."""
    return np.where(stress, limit / 2, tuned_thresholds(D, Pm, Ym, stress, limit))
