"""Ghostlyne Discovery Lab R5: does unconventional information improve defined energy-market decisions beyond conventional drivers?
Three decisions, made at 09:00 Central on day D-1 (before the 10:00 day-ahead market deadline) for delivery day D:
  1. SPIKE   risk assessment: probability that North real-time prices spike on D (Brier score)
  2. PROCURE procurement timing for a 1 MW North peak block: buy day-ahead or stay in real time (cost per MWh, CVaR)
  3. SELL    sale timing for a 1 MW West-hub peak block: sell day-ahead or in real time (revenue per MWh)
Information-time rule: realised prices and grid data up to D-2; day-ahead prices up to D-1; the published day-ahead demand
forecast for D; market closes up to D-2. No realised weather, wind or load for D-1 or D is ever used."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

PEAK = range(7, 23); C_RT = 1.0  # $/MWh friction charged whenever real time is chosen
TRAIN_START, EXPLORE, CONFIRM = pd.Timestamp("2018-07-01"), (pd.Timestamp("2020-01-01"), pd.Timestamp("2023-12-31")), (pd.Timestamp("2024-01-01"), None)

def peak_daily(H, col):
    h = H[col].dropna(); h = h[h.index.get_level_values("he").isin(PEAK)]; return h.groupby(level="date").mean()

def build(H, daily4, hashp, yahoo, storage_rel, nino):
    """H: hourly panel indexed (date, he). daily4: R4 daily panel (temperatures, Henry Hub). Returns targets and info-time features by delivery day."""
    D = pd.DataFrame(index=pd.date_range("2016-01-01", H.index.get_level_values("date").max(), freq="D"))
    g = lambda c: peak_daily(H, c).reindex(D.index)
    D["DA_N"], D["RT_N"], D["DA_W"], D["RT_W"] = g("DA_HB_NORTH"), g("RT_HB_NORTH"), g("DA_HB_WEST"), g("RT_HB_WEST")
    rtmax = H["RT_HB_NORTH"].groupby(level="date").max().reindex(D.index)
    D["DART_N"], D["DART_W"] = D.DA_N - D.RT_N, D.DA_W - D.RT_W
    thr = rtmax.rolling(365, min_periods=200).quantile(0.95).shift(2)          # threshold known at decision time
    D["SPIKE"] = (rtmax > thr).astype(float).where(thr.notna() & rtmax.notna())
    F = pd.DataFrame(index=D.index)
    lag2 = lambda s: s.reindex(D.index).shift(2); lag1 = lambda s: s.reindex(D.index).shift(1)
    # conventional baseline (what any ERCOT participant has for free)
    F["b_da_n_l1"], F["b_da_w_l1"] = lag1(D.DA_N), lag1(D.DA_W)
    F["b_rt_n_l2"], F["b_rt_w_l2"] = lag2(D.RT_N), lag2(D.RT_W)
    F["b_dart_n_l2"], F["b_dart_w_l2"] = lag2(D.DART_N), lag2(D.DART_W)
    F["b_spike_l2"], F["b_rtmax_l2"] = lag2(D.SPIKE), lag2(np.log1p(rtmax.clip(lower=0)))
    for c in ("LOAD_ERCO", "WIND_ERCO", "SOLAR_ERCO", "GASGEN_ERCO", "NUC_ERCO"):
        if c in H: F["b_" + c.lower() + "_l2"] = lag2(peak_daily(H, c))
    if "LOADFC_ERCO" in H:
        fc = peak_daily(H, "LOADFC_ERCO").reindex(D.index); F["b_loadfc_d"] = fc; F["b_loadfc_chg"] = fc - F.get("b_load_erco_l2")
        F["b_netload_fc"] = fc - F.get("b_wind_erco_l2", 0) - F.get("b_solar_erco_l2", 0)
    F["b_hh_l2"] = lag2(daily4["HH_SPOT"].reindex(D.index).ffill(limit=4))
    for k, st in (("b_dd_dfw_l2", "T_DFW"), ("b_dd_iah_l2", "T_IAH")): F[k] = lag2((daily4[st] - 65).abs())
    dow = D.index.dayofweek
    for d in range(1, 7): F[f"b_dow{d}"] = (dow == d).astype(float)
    doy = D.index.dayofyear.values / 365.25
    for k in (1, 2, 3): F[f"b_sin{k}"], F[f"b_cos{k}"] = np.sin(2 * np.pi * k * doy), np.cos(2 * np.pi * k * doy)
    # unconventional groups (pre-registered)
    G = {}
    def add(group, name, s): F[name] = s; G.setdefault(group, []).append(name)
    for c in ("WIND_SWPP", "LOAD_SWPP", "LOAD_MISO", "WIND_MISO"):
        if c in H: add("G1_neighbour_grids", "u_" + c.lower() + "_l2", lag2(peak_daily(H, c)))
    for c in ("LOADFC_SWPP", "LOADFC_MISO"):
        if c in H: add("G1_neighbour_grids", "u_" + c.lower() + "_d", peak_daily(H, c).reindex(D.index))
    if "LOAD_PJM" in H: add("G2_east_and_global_gas", "u_load_pjm_l2", lag2(peak_daily(H, "LOAD_PJM")))
    for k, st in (("u_dd_phl_l2", "T_PHL"), ("u_dd_bos_l2", "T_BOS")): add("G2_east_and_global_gas", k, lag2((daily4[st] - 65).abs()))
    cal = lambda s: s.reindex(pd.date_range(s.index.min(), D.index.max(), freq="D")).ffill(limit=5).reindex(D.index)
    ret5 = lambda s: lag2(np.log(cal(s)).diff(7))
    for t, grp in (("TTF=F", "G2_east_and_global_gas"), ("CL=F", "G2_east_and_global_gas"), ("LNG", "G2_east_and_global_gas"), ("NG=F", "G2_east_and_global_gas"),
                   ("HG=F", "G3_industry_finance"), ("CAD=X", "G3_industry_finance"), ("MXN=X", "G3_industry_finance"), ("XLU", "G3_industry_finance"), ("VST", "G3_industry_finance"), ("BDRY", "G3_industry_finance"),
                   ("ZC=F", "G4_climate_agriculture"),
                   ("BTC-USD", "G5_crypto_ai"), ("MARA", "G5_crypto_ai"), ("RIOT", "G5_crypto_ai"), ("NVDA", "G5_crypto_ai"), ("SOXX", "G5_crypto_ai"), ("DLR", "G5_crypto_ai"), ("EQIX", "G5_crypto_ai")):
        if t in yahoo: add(grp, "u_" + t.lower().replace("=", "").replace("-", "") + "_r7", ret5(yahoo[t]))
    if storage_rel is not None: add("G2_east_and_global_gas", "u_storage_surprise", cal(storage_rel).shift(1))
    if nino is not None: add("G4_climate_agriculture", "u_nino", cal(nino).shift(7))
    if hashp is not None:
        hpd = cal(hashp); add("G5_crypto_ai", "u_hashprice_chg7", lag2(np.log(hpd).diff(7)))
        be = hpd / (25 * 24 / 1e6)  # breakeven power price ($/MWh) for a 25 J/TH fleet: 1 TH/s uses 0.0006 MWh per day
        add("G5_crypto_ai", "u_miner_breakeven_l2", lag2(be)); add("G5_crypto_ai", "u_breakeven_minus_da", lag2(be) - F["b_da_n_l1"])
    # controls: three synthetic noise features (must not pass) and one planted informative feature (must pass)
    r = np.random.default_rng(7)
    for i in (1, 2, 3): add("G0_synthetic_negative", f"s_noise{i}", pd.Series(r.normal(size=len(D)), D.index))
    from scipy.stats import norm
    z = lambda s: pd.Series(norm.ppf((s.rank() - 0.5) / s.notna().sum()), index=s.index)  # rank-normal scores, robust to spikes
    add("GP_synthetic_positive", "s_planted_spike", D.SPIKE.fillna(0) + 0.5 * pd.Series(r.normal(size=len(D)), D.index))
    add("GP_synthetic_positive", "s_planted_dart_n", z(D.DART_N).fillna(0) + 1.0 * pd.Series(r.normal(size=len(D)), D.index))
    add("GP_synthetic_positive", "s_planted_dart_w", z(D.DART_W).fillna(0) + 1.0 * pd.Series(r.normal(size=len(D)), D.index))
    G["G35_all_unconventional"] = G.get("G3_industry_finance", []) + G.get("G4_climate_agriculture", []) + G.get("G5_crypto_ai", [])
    base = [c for c in F if c.startswith("b_")]
    return D, F, base, G

def _fit_predict(kind, X, y, Xp):
    sc = StandardScaler().fit(X); Xs, Xps = sc.transform(X), sc.transform(Xp)
    if kind == "spike":
        if len(np.unique(y)) < 2: return np.full(len(Xp), y.mean())
        return LogisticRegression(C=0.5, max_iter=2000).fit(Xs, y).predict_proba(Xps)[:, 1]
    return Ridge(alpha=10.0).fit(Xs, y).predict(Xps)

def walk(D, F, cols, kind, start, end):
    """Expanding window from TRAIN_START, refit at each month start; predictions for every day in [start, end]."""
    tgt = {"spike": "SPIKE", "procure": "DART_N", "sell": "DART_W"}[kind]
    X = F[cols].copy(); X = X.fillna(X.median()); y = D[tgt]
    days = D.index[(D.index >= start) & ((D.index <= end) if end is not None else True) & y.notna()]
    out = pd.Series(np.nan, index=days)
    for m, chunk in pd.Series(days, index=days).groupby(days.to_period("M")):
        cut = chunk.index[0] - pd.Timedelta(days=2)        # target of D is known only after D; train on days <= D-2
        tr = D.index[(D.index >= TRAIN_START) & (D.index <= cut) & y.notna()]
        if len(tr) < 365: continue
        out[chunk.index] = _fit_predict(kind, X.loc[tr].values, y.loc[tr].values, X.loc[chunk.index].values)
    return out.dropna()

def value(D, kind, p_base, p_aug):
    """Per-day improvement of the augmented model over the baseline model, in the decision's own units (positive = better)."""
    idx = p_base.index.intersection(p_aug.index)
    if kind == "spike":
        y = D.SPIKE.loc[idx]; return ((p_base[idx] - y) ** 2 - (p_aug[idx] - y) ** 2), None
    if kind == "procure":
        da, rt = D.DA_N.loc[idx], D.RT_N.loc[idx]
        cost = lambda p: np.where(p > C_RT, rt + C_RT, da)     # predicted DA-RT above the friction -> stay in real time
        cb, ca = cost(p_base[idx]), cost(p_aug[idx]); return pd.Series(cb - ca, idx), (pd.Series(cb, idx), pd.Series(ca, idx), da)
    da, rt = D.DA_W.loc[idx], D.RT_W.loc[idx]
    rev = lambda p: np.where(p < -C_RT, rt - C_RT, da)          # sell in real time only if expected to beat day-ahead by more than the friction
    rb, ra = rev(p_base[idx]), rev(p_aug[idx]); return pd.Series(ra - rb, idx), (pd.Series(rb, idx), pd.Series(ra, idx), da)

def block_boot(d, reps=2000, block=14, seed=0):
    d = np.asarray(d, float); n = len(d); r = np.random.default_rng(seed); means = np.empty(reps)
    for i in range(reps):
        idx = np.concatenate([np.arange(s, s + block) % n for s in r.integers(0, n, n // block + 1)])[:n]; means[i] = d[idx].mean()
    return float(d.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float((means <= 0).mean())

def cvar(costs, q=0.95, higher_is_worse=True):
    c = np.sort(np.asarray(costs, float)); k = int(np.ceil(q * len(c)))
    return float(c[k:].mean()) if higher_is_worse else float(np.sort(costs)[: len(c) - k].mean())

def bh(p):
    p = np.asarray(p, float); n = len(p)
    if not n: return p
    o = np.argsort(p); q = np.empty(n); q[o] = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]; return np.minimum(q, 1)

def run(D, F, base, G, decisions=("spike", "procure", "sell"), windows=(("E", EXPLORE), ("C", CONFIRM))):
    rows, preds = [], {}
    for kind in decisions:
        for wn, (a, b) in windows:
            pb = walk(D, F, base, kind, a, b); preds[(kind, wn, "baseline")] = pb
            for gname, gcols in G.items():
                if not gcols: continue
                pa = walk(D, F, base + gcols, kind, a, b); d, extra = value(D, kind, pb, pa)
                m, lo, hi, p = block_boot(d.values)
                row = dict(decision=kind, group=gname, window=wn, n_days=int(len(d)), mean_gain=m, ci_lo=lo, ci_hi=hi, p_one_sided=p)
                if extra is not None:
                    cb, ca, da = extra; hw = kind == "procure"
                    row.update(base_mean=float(cb.mean()), aug_mean=float(ca.mean()), always_da_mean=float(da.mean()),
                               base_cvar95=cvar(cb if hw else -cb), aug_cvar95=cvar(ca if hw else -ca))
                else:
                    y = D.SPIKE.loc[d.index]; clim = y.expanding().mean().shift(1).fillna(y.mean())
                    row.update(brier_base=float(((pb[d.index] - y) ** 2).mean()), brier_aug=float(((pa[d.index] - y) ** 2).mean()), brier_climatology=float(((clim - y) ** 2).mean()))
                rows.append(row)
    R = pd.DataFrame(rows)
    E, C = R[R.window == "E"].copy(), R[R.window == "C"].copy()
    E["candidate"] = (E.mean_gain > 0) & (E.p_one_sided < 0.10)
    cand = E[E.candidate][["decision", "group"]]
    C = C.merge(cand.assign(candidate=True), how="left", on=["decision", "group"]); C["candidate"] = C.candidate.fillna(False)
    sel = C[C.candidate].index; C["q"] = np.nan
    C.loc[sel, "q"] = bh(C.loc[sel, "p_one_sided"].values)
    C["state"] = np.where(C.candidate & (C.q <= 0.05) & (C.ci_lo > 0), "Validated", np.where(C.candidate, "Not Detected", "Not a candidate"))
    return pd.concat([E, C], ignore_index=True), preds
