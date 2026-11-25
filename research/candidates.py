"""Competing improvements, each tested out of sample against the current model. Nothing here is live."""
import numpy as np, pandas as pd
from scipy.stats import genpareto
import lab
G = lab.G

def add_regime_features(D):
    """Market-wide state at 23:15 (known at forecast time): breadth of big down / up days, cross-sectional mean return,
    and today's range relative to the month."""
    D = D.copy()
    D["br_dn"] = D.groupby("Date").ret1.transform(lambda s: (s < -0.05).mean())
    D["br_up"] = D.groupby("Date").ret1.transform(lambda s: (s > 0.05).mean())
    D["mkt_ret1"] = D.groupby("Date").ret1.transform("mean")
    D["v1_rel"] = D.v1 - D.v30
    D["dn1"] = np.minimum(D.ret1, 0); D["up1"] = np.maximum(D.ret1, 0)          # asymmetric shock terms
    sd30 = np.sqrt(np.exp(D.v30))
    big = (D.ret_full.abs() > 3 * sd30).astype(float)
    D["jumps30"] = big.groupby(D.sym).transform(lambda s: s.shift(1).rolling(29, min_periods=10).sum()) + (D.ret1.abs() > 3 * sd30)
    D["jumps30"] = D.jumps30.fillna(0)
    return D

REGIME_FEATS = G.TEX + ["br_dn", "br_up", "mkt_ret1", "v1_rel", "dn1", "up1"]
JUMP_FEATS = REGIME_FEATS + ["jumps30"]

def model_walk_feats(D, side, k, start, feats):
    y = G.target(D, side, k).values; raw = np.full(len(D), np.nan)
    for ms in pd.date_range(start, D.Date.max(), freq="MS"):
        te = np.where((D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)))[0]
        tr = np.where((D.Date < ms - pd.Timedelta(days=1)) & ~np.isnan(y))[0]
        if len(te) == 0 or np.nansum(y[tr]) < 25: continue
        raw[te] = G.fit(D.loc[tr, feats], y[tr]).predict_proba(D.loc[te, feats])[:, 1]
    return raw

def gjr_sd(D, start):
    """GJR-GARCH(1,1,1)-t: negative shocks may raise variance more than positive ones."""
    from arch import arch_model
    out = np.full(len(D), np.nan)
    for s, g in D.groupby("sym"):
        idx = g.index.values; dates = g.Date.values; rf = g.ret_full.values * 100; rt = g.ret1.values * 100
        for ms in pd.date_range(start, g.Date.max(), freq="MS"):
            tr = np.where(dates < np.datetime64(ms - pd.Timedelta(days=1)))[0]
            te = set(np.where((dates >= np.datetime64(ms)) & (dates < np.datetime64(ms + pd.offsets.MonthBegin(1))))[0])
            if not te or len(tr) < 250: continue
            x = rf[tr]; x = x[~np.isnan(x)][-1500:]
            try: res = arch_model(x, vol="GARCH", p=1, o=1, q=1, dist="t", mean="Zero").fit(disp="off")
            except Exception: continue
            w, a, gm, bb = res.params["omega"], res.params["alpha[1]"], res.params["gamma[1]"], res.params["beta[1]"]
            s2 = float(res.conditional_volatility[-1] ** 2)
            for j in range(tr[-1] + 1, max(te) + 1):
                e = rf[j - 1] if not np.isnan(rf[j - 1]) else 0.0
                s2 = w + (a + gm * (e < 0)) * e ** 2 + bb * s2
                if j in te and not np.isnan(rt[j]):
                    e2 = rt[j]; out[idx[j]] = np.sqrt(w + (a + gm * (e2 < 0)) * e2 ** 2 + bb * s2) / 100
    return out

def evt_fhs(D, side, k, sd, start, window=730, q=0.90):
    """Filtered historical simulation with a generalized Pareto tail (extreme value theory) beyond the 90th percentile
    of past adverse standardized moves; refit monthly per market."""
    col = "next_down" if side == "long" else "next_up"; out = np.full(len(D), np.nan)
    b = -np.log(1 - k) if side == "long" else np.log(1 + k)
    for s, g in D.groupby("sym"):
        z = (g[col] / sd[g.index]).values; z = -z if side == "long" else z            # adverse move, positive
        thr = (b / sd[g.index]); dates = g.Date.values
        for ms in pd.date_range(start, g.Date.max(), freq="MS"):
            te = np.where((dates >= np.datetime64(ms)) & (dates < np.datetime64(ms + pd.offsets.MonthBegin(1))))[0]
            past = np.where(dates < np.datetime64(ms - pd.Timedelta(days=1)))[0][-window:]
            zz = z[past]; zz = zz[~np.isnan(zz)]
            if len(te) == 0 or len(zz) < 250: continue
            u = np.quantile(zz, q); exc = zz[zz > u] - u
            try: xi, _, beta = genpareto.fit(exc, floc=0)
            except Exception: continue
            t = thr[te]; emp = np.array([(zz >= x).mean() for x in t])
            tail = (1 - q) * genpareto.sf(t - u, xi, 0, beta)
            out[g.index[te]] = np.where(t > u, tail, emp)
    return np.clip(out, 1e-5, 0.9999)

def extra(D, side, k, start, sd_e, sd_g, cache={}):
    if "gjr" not in cache: cache["gjr"] = gjr_sd(D, start)
    return {"Ghostlyne+regime": model_walk_feats(D, side, k, start, REGIME_FEATS),
            "Ghostlyne+regime+jumps": model_walk_feats(D, side, k, start, JUMP_FEATS),
            "GJR-GARCH-t": G.reflection(cache["gjr"], side, k),
            "EVT-FHS": evt_fhs(D, side, k, sd_e, start)}

# ---------------------------------------------------------------- stress-regime calibration
def stress_flag(D, side):
    """Known at 23:15: a market-wide big move in the position's adverse direction (over 30% of markets moved 5%+ that
    way today) or today's range far above the month (log Parkinson variance more than 1 above its 30-day level)."""
    br = D.br_dn if side == "long" else D.br_up
    return ((br > 0.3) | (D.v1_rel > 1)).values

def calibrate_walk_regime(D, raw, y, stress, cal_months=12, stress_months=24, min_events=15):
    """Separate walk-forward isotonic maps for stress and normal rows. The stress map uses a longer lookback; with too few
    past stress events it falls back to the pooled map scaled by the past stress-row realized/forecast ratio."""
    from sklearn.isotonic import IsotonicRegression
    cal = np.full(len(D), np.nan)
    iso = lambda a, b: IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999).fit(a, b)
    for ms in pd.date_range(D.Date.min().replace(day=1), D.Date.max(), freq="MS"):
        mon = (D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)); ok = ~np.isnan(raw)
        hist = (D.Date < ms - pd.Timedelta(days=1)) & ok & ~np.isnan(y)
        pn = np.where(hist & (D.Date >= ms - pd.DateOffset(months=cal_months)) & ~stress)[0]
        ps = np.where(hist & (D.Date >= ms - pd.DateOffset(months=stress_months)) & stress)[0]
        pa = np.where(hist & (D.Date >= ms - pd.DateOffset(months=cal_months)))[0]
        if len(pa) <= 1000 or y[pa].sum() < 20: continue
        pooled = iso(raw[pa], y[pa])
        tn = np.where(mon & ok & ~stress)[0]; ts = np.where(mon & ok & stress)[0]
        if len(tn): cal[tn] = (iso(raw[pn], y[pn]) if len(pn) > 1000 and y[pn].sum() >= 20 else pooled).predict(raw[tn])
        if len(ts):
            if len(ps) > 300 and y[ps].sum() >= min_events: cal[ts] = iso(raw[ps], y[ps]).predict(raw[ts])
            elif len(ps) > 100:
                f = (y[ps].sum() + 1) / (pooled.predict(raw[ps]).sum() + 1); cal[ts] = np.clip(pooled.predict(raw[ts]) * max(f, 1.0), 1e-4, 0.999)
            else: cal[ts] = pooled.predict(raw[ts])
    return cal
