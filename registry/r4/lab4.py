"""Ghostlyne Discovery Lab R4: energy. Rank-based association (robust to price spikes) with Newey-West inference,
daily and weekly horizons, lead-lag, seasonal and scarcity-conditional structure, predictive value with information-time rules."""
import os, sys, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r2"))
from lab import hac_corr, bh
import universe4 as U

URI = (pd.Timestamp("2021-02-08"), pd.Timestamp("2021-02-24"))
QE, QC = 0.10, 0.05
MIN = {"A_d": (500, 500), "B_d": (500, 500), "S_season": (500, 500), "S_scarcity": (500, 500), "A_w": (100, 100), "B_w": (100, 100)}
DLAGS, WLAGS = range(1, 11), range(1, 9)
POWERISH = {"power", "spread", "ratio"}

def build(panel, storage, nino, yahoo):
    P = panel; S = {}
    S["ERCOT_N_DA"] = P["DA_HB_NORTH"]; S["ERCOT_N_RT"] = P["RT_HB_NORTH"]; S["ERCOT_N_DART"] = P["DA_HB_NORTH"] - P["RT_HB_NORTH"]
    S["ERCOT_WN_BASIS"] = P["DA_HB_WEST"] - P["DA_HB_NORTH"]; S["HH_SPOT"] = P["HH_SPOT"]
    S["ERCOT_N_HEAT"] = (P["DA_HB_NORTH"] / P["HH_SPOT"]).where(P["HH_SPOT"] > 0.5)
    for k, st in (("DD_DFW", "T_DFW"), ("DD_IAH", "T_IAH"), ("DD_PHL", "T_PHL"), ("DD_BOS", "T_BOS")): S[k] = (P[st] - 65).abs()
    for k in ("LOAD_ERCO", "LOADFC_ERCO", "WIND_ERCO", "SOLAR_ERCO", "GASGEN_ERCO", "NUC_ERCO", "LOAD_PJM", "LOAD_MISO", "LOAD_SWPP", "WIND_SWPP"):
        if k in P: S[k] = P[k].where(P[k] > 0)
    st = storage.sort_index(); chg = st.diff(); woy = chg.index.isocalendar().week.values
    norm = pd.Series([chg[(woy == w) & (chg.index < t) & (chg.index >= t - pd.DateOffset(years=5))].mean() for t, w in zip(chg.index, woy)], index=chg.index)
    S["STORAGE_SURPRISE"] = (chg - norm).dropna(); S["NINO34"] = nino
    for k, v in yahoo.items(): S["NG_FRONT" if k == "NG=F" else k] = v
    idx = pd.bdate_range("2009-01-01", "2026-12-31")
    for k, sd in (("SYN_1", 11), ("SYN_2", 22), ("SYN_3", 33)):
        r = np.random.default_rng(sd); S[k] = pd.Series(100 * np.exp(np.cumsum(r.standard_t(4, len(idx)) * 0.015)), idx)
    return {k: v.dropna().sort_index() for k, v in S.items() if v is not None and v.notna().sum() > 0}

def kind(k):
    if k in U.FOCAL: return U.FOCAL[k]["kind"]
    return "ext"

def innov(k, s, weekly=False, last=None):
    tr = "diff" if (kind(k) in POWERISH) else U.EXTERNALS.get(k, {}).get("tr", "dlog")
    if k in ("STORAGE_SURPRISE",): return s if weekly else None
    if k == "NINO34": return s.diff() if weekly else None
    if weekly:  # end-of-week values for trending prices (no averaging echo); weekly means for mean-reverting physical series
        use_last = (not stationary(k)) if last is None else last
        s = s.resample("W-FRI").last() if use_last else s.resample("W-FRI").mean()
    if tr == "level": return s
    return s.diff() if tr == "diff" else np.log(s.where(s > 0)).diff()

STATIONARY_EXT = {"DD_DFW", "DD_IAH", "DD_PHL", "DD_BOS", "LOAD_ERCO", "LOADFC_ERCO", "WIND_ERCO", "SOLAR_ERCO", "GASGEN_ERCO", "NUC_ERCO",
                  "LOAD_PJM", "LOAD_MISO", "LOAD_SWPP", "WIND_SWPP", "STORAGE_SURPRISE", "NINO34"}
def stationary(k): return kind(k) in POWERISH or k in STATIONARY_EXT

def dyn(k, s, weekly=False):
    """Form used for lead-lag: mean-reverting series as anomalies (level minus trailing one-year mean; no over-differencing),
    trending series as returns."""
    if not stationary(k): return innov(k, s, weekly)
    if k == "STORAGE_SURPRISE": return s if weekly else None
    if k == "NINO34": return s if weekly else None
    x = s.resample("W-FRI").mean() if weekly else s
    return x - x.rolling(52 if weekly else 365, min_periods=26 if weekly else 180).mean().shift(1)

def deseason(x, weekly=False):
    x = x.dropna()
    return x if weekly else x - x.groupby(x.index.dayofweek).transform("mean")

def windows(a, b):
    start = max(a.first_valid_index(), b.first_valid_index())
    if start <= pd.Timestamp("2012-12-31"): return "early", (pd.Timestamp("2011-01-01"), pd.Timestamp("2018-12-31")), (pd.Timestamp("2019-01-01"), None)
    return "late", (start, pd.Timestamp("2021-12-31")), (pd.Timestamp("2022-01-01"), None)

def cut(x, w): a, b = w; return x[(x.index >= a) & ((x.index <= b) if b is not None else True)]

def rcorr(y, z, nw, drop=None):
    d = pd.concat([y, z], axis=1).dropna()
    if drop is not None: d = d[(d.index < drop[0]) | (d.index > drop[1])]
    if len(d) < 30: return np.nan, np.nan, len(d), np.nan
    r, se, p, n = hac_corr(d.iloc[:, 0].rank(), d.iloc[:, 1].rank(), nw); rp = float(d.iloc[:, 0].corr(d.iloc[:, 1]))
    return r, p, n, rp

def nscore(x): return pd.Series(stats.norm.ppf((x.rank() - 0.5) / x.notna().sum()), index=x.index)

def lagtest(y, z, L, nw):
    """Temporal relationship beyond the same-period link and own persistence (differencing echoes removed).
    L>0: does z lead y by L?  regress y_t on z_t, z_{t-L}, y_{t-1}; L<0: does y lead z by |L|? regress z_t on y_t, y_{t-|L|}, z_{t-1}.
    Rank-based (normal scores). Effect = partial correlation of the lagged leader; p from Newey-West."""
    dep, lead = (y, z) if L > 0 else (z, y); k = abs(L)
    d = pd.concat([dep.rename("d"), lead.rename("x0"), lead.shift(k).rename("xk"), dep.shift(1).rename("d1"), dep.shift(2).rename("d2")], axis=1).dropna()
    if len(d) < 60: return np.nan, np.nan, len(d), np.nan
    d = d.apply(nscore); X = np.column_stack([np.ones(len(d)), d.x0, d.xk, d.d1, d.d2]); Y = d.d.values
    b = np.linalg.lstsq(X, Y, rcond=None)[0]; e = Y - X @ b; XtXi = np.linalg.pinv(X.T @ X); u = X * e[:, None]; Sg = u.T @ u
    for l in range(1, nw + 1): G = u[l:].T @ u[:-l]; Sg += (1 - l / (nw + 1)) * (G + G.T)
    se = np.sqrt((XtXi @ Sg @ XtXi)[2, 2]); t = b[2] / se; dfree = len(d) - 5
    return float(t / np.sqrt(t * t + dfree)), float(2 * stats.norm.sf(abs(t))), len(d), float(b[2])

def fourier_resid(x, weekly=False):
    """Remove trend, annual cycle (3 harmonics) and, for daily data, day-of-week effects, within the window."""
    x = x.dropna()
    if len(x) < 60: return x
    t = (x.index - x.index[0]).days.values / 365.25; doy = x.index.dayofyear.values / 365.25
    cols = [np.ones(len(x)), t] + [f(2 * np.pi * k * doy) for k in (1, 2, 3) for f in (np.sin, np.cos)]
    if not weekly: cols += [(x.index.dayofweek == d).astype(float) for d in range(1, 7)]
    X = np.column_stack(cols); b = np.linalg.lstsq(X, x.values, rcond=None)[0]; return pd.Series(x.values - X @ b, index=x.index)

def prewhiten_test(dep, lead, k, nw, pmax):
    """Box-Jenkins prewhitening: fit an AR(p) to the leader (AIC, p<=pmax), filter both series with it, then test the
    cross-correlation of filtered dependent at t with filtered leader at t-k. Echoes of same-period links, shared
    seasonality and own persistence do not create lagged correlation under this filter."""
    d = pd.concat([dep.rename("y"), lead.rename("x")], axis=1).dropna()
    if len(d) < 120: return np.nan, np.nan, len(d), np.nan
    return _pw(d, k, nw, pmax, "x")

def _pw(d, k, nw, pmax, base):
    x = d[base].values; best = None
    for p in range(1, pmax + 1):
        X = np.column_stack([x[p - i - 1:len(x) - i - 1] for i in range(p)]); Y = x[p:]
        phi = np.linalg.lstsq(X, Y, rcond=None)[0]; e = Y - X @ phi; aic = len(Y) * np.log(e @ e / len(Y)) + 2 * p
        if best is None or aic < best[0]: best = (aic, p, phi)
    _, p, phi = best
    filt = lambda v: v[p:] - np.column_stack([v[p - i - 1:len(v) - i - 1] for i in range(p)]) @ phi
    yf, xf = pd.Series(filt(d.y.values), index=d.index[p:]), pd.Series(filt(d.x.values), index=d.index[p:])
    a, b = yf, xf.shift(k)
    r, se, pv, n = hac_corr(nscore(a.where(b.notna())), nscore(b.where(a.notna())), nw)
    return r, pv, n, float(p)

def lead_test(dep, lead, k, nw, pmax):
    """Lead-lag claim must hold under both prewhitening filters (the leader's and the follower's): same sign, and the
    weaker of the two p-values is reported. Guards against lags created by measurement noise on either side."""
    d = pd.concat([dep.rename("y"), lead.rename("x")], axis=1).dropna()
    if len(d) < 120: return np.nan, np.nan, len(d), np.nan
    r1, p1, n1, _ = _pw(d, k, nw, pmax, "x"); r2, p2, n2, _ = _pw(d, k, nw, pmax, "y")
    if not (np.isfinite(r1) and np.isfinite(r2)): return np.nan, np.nan, n1, np.nan
    return (r1 if abs(r1) < abs(r2) else r2), (max(p1, p2) if np.sign(r1) == np.sign(r2) else 1.0), n1, r2

def scarcity_flag(rt):
    thr = rt.rolling(365, min_periods=200).quantile(0.95).shift(1); return (rt > thr).where(thr.notna())

def fisher_diff(y, z, flag):
    d = pd.concat([y.rename("y"), z.rename("z"), flag.rename("f")], axis=1).dropna(); a, b = d[d.f == 1], d[d.f == 0]
    if len(a) < 30 or len(b) < 30: return np.nan, np.nan, len(d), np.nan, np.nan
    r1, r0 = stats.spearmanr(a.y, a.z)[0], stats.spearmanr(b.y, b.z)[0]
    zz = (np.arctanh(r1) - np.arctanh(r0)) / np.sqrt(1.06 / (len(a) - 3) + 1.06 / (len(b) - 3))
    return float(r1 - r0), float(2 * stats.norm.sf(abs(zz))), len(d), float(r1), float(r0)

MECH = {("ERCOT_N_HEAT", "HH_SPOT"), ("NG_FRONT", "HH_SPOT")}

def tests(S, pairs, scar):
    T = []
    for f, x in pairs:
        base = dict(focal=f, external=x, ring=U.EXTERNALS[x]["ring"], role=U.EXTERNALS[x]["role"])
        for weekly in (False, True):
            yf, zx = innov(f, S[f], weekly), innov(x, S[x], weekly)
            if yf is None or zx is None: continue
            yf, zx = deseason(yf, weekly), deseason(zx, weekly); split, E, C = windows(yf, zx); nw = 4 if weekly else 5
            both = stationary(f) and stationary(x)  # same integration form on both sides: levels if both mean-revert, else changes
            yd, zd = (dyn(f, S[f], weekly), dyn(x, S[x], weekly)) if both else (innov(f, S[f], weekly, last=True), innov(x, S[x], weekly, last=True))
            yd = deseason(yd, weekly) if yd is not None else None; zd = deseason(zd, weekly) if zd is not None else None
            fa, fb = ("A_w", "B_w") if weekly else ("A_d", "B_d")
            for wn, W in (("E", E), ("C", C)):
                y, z = cut(yf, W), cut(zx, W)
                r, p, n, rp = rcorr(y, z, nw); T.append(dict(base, family=fa, lag=0, dir="", win=wn, split=split, r=r, p=p, n=n, r_pearson=rp))
                for L in (WLAGS if weekly else DLAGS):
                    for s in (1, -1):
                        yw, zw = fourier_resid(cut(yd, W), weekly), fourier_resid(cut(zd, W), weekly)
                        r, p, n, bcoef = (lead_test(yw, zw, L, nw, 8 if weekly else 14) if s > 0 else lead_test(zw, yw, L, nw, 8 if weekly else 14)); T.append(dict(base, family=fb, lag=s * L, dir="", win=wn, split=split, r=r, p=p, n=n, r_pearson=bcoef))
                if not weekly:
                    season = pd.Series((y.index.month >= 6) & (y.index.month <= 9), index=y.index).astype(float)
                    for fam, flag in (("S_season", season), ("S_scarcity", scar)):
                        dr, p, n, r1, r0 = fisher_diff(y, z, flag); T.append(dict(base, family=fam, lag=0, dir="", win=wn, split=split, r=dr, p=p, n=n, r_in=r1, r_out=r0))
    T = pd.DataFrame(T); T["ok"] = [n >= MIN[f][0 if w == "E" else 1] for n, f, w in zip(T.n, T.family, T.win)]
    return T

def screen_confirm(T):
    ex = T[(T.win == "E") & T.p.notna() & T.ok].copy()
    ex["q"] = ex.groupby(["family", "ring"]).p.transform(lambda s: pd.Series(bh(s.values), index=s.index))
    cand = ex[ex.q <= QE].sort_values("p").drop_duplicates(["focal", "external", "family"])
    cf = T[T.win == "C"].set_index(["focal", "external", "family", "lag"]); rows = []
    for fam, g in cand.groupby("family"):
        pr = []
        for _, c in g.iterrows():
            k = (c.focal, c.external, fam, c.lag)
            if k in cf.index: v = cf.loc[k]; pr.append((c, v.iloc[0] if isinstance(v, pd.DataFrame) else v))
        for (c, k), q in zip(pr, bh([k.p if np.isfinite(k.p) else 1 for _, k in pr])):
            why = []
            if not k.ok: why.append("insufficient confirmation data")
            if np.sign(k.r) != np.sign(c.r): why.append("direction changed in confirmation")
            if q > QC: why.append("not significant in confirmation after false-discovery control")
            rows.append(dict(focal=c.focal, external=c.external, ring=int(c.ring), role=c.role, family=fam, lag=int(c.lag), split=c.split,
                             e_explore=float(c.r), q_explore=float(c.q), e_confirm=float(k.r), p_confirm=float(k.p), q_confirm=float(q), n_confirm=int(k.n),
                             r_pearson_confirm=float(k.get("r_pearson", np.nan)) if pd.notna(k.get("r_pearson", np.nan)) else None,
                             r_in=float(k["r_in"]) if "r_in" in k and pd.notna(k["r_in"]) else None, r_out=float(k["r_out"]) if "r_out" in k and pd.notna(k["r_out"]) else None,
                             state="Validated" if not why else "Not Detected", reason="; ".join(why) or "passed exploration and confirmation"))
    return ex, pd.DataFrame(rows)

def uri_check(S, conf):
    """Validated daily claims whose confirmation window includes Winter Storm Uri must hold without it."""
    for i, v in conf[(conf.state == "Validated") & conf.family.isin(["A_d", "B_d"]) & (conf.split == "early")].iterrows():
        g = dyn if (v.family == "B_d" and stationary(v.focal) and stationary(v.external)) else innov
        y, z = deseason(g(v.focal, S[v.focal])), deseason(g(v.external, S[v.external])); y = cut(y, (pd.Timestamp("2019-01-01"), None)); z = cut(z, (pd.Timestamp("2019-01-01"), None))
        if v.family == "A_d": r, p, n, _ = rcorr(y, z, 5, drop=URI)
        else:
            yw, zw = fourier_resid(y[(y.index < URI[0]) | (y.index > URI[1])]), fourier_resid(z[(z.index < URI[0]) | (z.index > URI[1])])
            r, p, n, _ = lead_test(yw, zw, v.lag, 5, 14) if v.lag > 0 else lead_test(zw, yw, -v.lag, 5, 14)
        if not (np.sign(r) == np.sign(v.e_confirm) and p < 0.05):
            conf.loc[i, "state"] = "Not Detected"; conf.loc[i, "reason"] = "does not hold without Winter Storm Uri (Feb 2021)"
    return conf

def positive_controls(S, window="E"):
    out = []
    for f, x, fam, sgn in U.POSITIVE_CONTROLS:
        weekly = fam == "A_w"; y, z = innov(f, S[f], weekly), innov(x, S[x], weekly)
        y, z = deseason(y, weekly), deseason(z, weekly); split, E, C = windows(y, z)
        r, p, n, rp = rcorr(cut(y, E if window == "E" else C), cut(z, E if window == "E" else C), 4 if weekly else 5)
        out.append(dict(focal=f, external=x, family=fam, expected=sgn, window=window, r=r, p=p, n=n, r_pearson=rp, passed=bool(np.sign(r) == sgn and p < 0.001)))
    return out

def predictive(S, conf):
    """C: for validated lead-lag where the external leads. Information-time rule: market and observed data usable from the next
    day at the earliest; lags below 2 days are not used except ERCOT's published day-ahead demand forecast (lag >= 1)."""
    res = []
    for _, v in conf[(conf.state == "Validated") & conf.family.isin(["B_d", "B_w"]) & (conf.lag > 0)].iterrows():
        weekly = v.family == "B_w"; L = v.lag
        if not weekly and L < (1 if v.external == "LOADFC_ERCO" else 2): continue
        bothst = stationary(v.focal) and stationary(v.external)
        y = deseason(dyn(v.focal, S[v.focal], weekly) if bothst else innov(v.focal, S[v.focal], weekly, last=True), weekly)
        x = deseason(dyn(v.external, S[v.external], weekly) if bothst else innov(v.external, S[v.external], weekly, last=True), weekly)
        lags = range(1, 8 if not weekly else 5)
        d = pd.concat([y.rename("y")] + [y.shift(k).rename(f"y{k}") for k in lags] + [x.shift(L).rename("x")], axis=1).dropna()
        t0 = pd.Timestamp("2019-01-01" if v.split == "early" else "2022-01-01"); idx = d.index[d.index >= t0]
        if len(idx) < 60: continue
        Xb = np.column_stack([np.ones(len(d))] + [d[f"y{k}"] for k in lags]); Xc = np.column_stack([Xb, d.x]); Y = d.y.values
        fb, fc, ys = [], [], []; step = 1 if weekly else 5
        bb = bc = None
        for j, t in enumerate(idx):
            i = d.index.get_loc(t)
            if bb is None or j % step == 0: bb = np.linalg.lstsq(Xb[:i], Y[:i], rcond=None)[0]; bc = np.linalg.lstsq(Xc[:i], Y[:i], rcond=None)[0]
            fb.append(Xb[i] @ bb); fc.append(Xc[i] @ bc); ys.append(Y[i])
        fb, fc, ys = map(np.array, (fb, fc, ys)); adj = (ys - fb) ** 2 - ((ys - fc) ** 2 - (fb - fc) ** 2); a = adj - adj.mean(); n = len(a); s = a @ a / n
        for l in range(1, 6): s += 2 * (1 - l / 6) * (a[l:] @ a[:-l]) / n
        res.append(dict(focal=v.focal, external=v.external, family=v.family, lag=int(L), r2_oos=float(1 - ((ys - fc) ** 2).sum() / ((ys - fb) ** 2).sum()), p=float(stats.norm.sf(adj.mean() / np.sqrt(s / n))), n=n))
    P = pd.DataFrame(res)
    if len(P): P["q"] = bh(P.p.values); P["state"] = np.where((P.q <= QC) & (P.r2_oos > 0), "Validated", "Not Detected")
    return P

def pairs_of(S):
    return [(f, x) for f in U.FOCAL for x in U.EXTERNALS if f in S and x in S and f != x and (f, x) not in MECH]
