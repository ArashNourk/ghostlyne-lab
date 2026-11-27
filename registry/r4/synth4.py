"""Synthetic validation of the R4 lab (method check only, not market evidence): known drivers planted, everything else noise."""
import sys, time, json, numpy as np, pandas as pd
import universe4 as U, lab4
def world(seed=3):
    r = np.random.default_rng(seed); d = pd.date_range("2010-01-01", "2026-11-20", freq="D"); n = len(d)
    doy = d.dayofyear.values; temp = 65 + 20 * np.sin(2 * np.pi * (doy - 110) / 365) + r.normal(0, 7, n); dd = np.abs(temp - 65)
    hh = np.exp(np.cumsum(r.normal(0, .03, n))) * 3; wind = np.exp(r.normal(0, .35, n)) * 1e5
    load = 1e6 * (1 + 0.012 * dd + r.normal(0, .02, n)); fc = load * (1 + r.normal(0, .01, n))
    da = 8 * hh * (load / 1e6) ** 2 - 0.00004 * wind + r.normal(0, 3, n) + 15
    da[r.random(n) < .01] *= 8   # price spikes
    rt = da + r.standard_t(3, n) * 6
    S = {"ERCOT_N_DA": pd.Series(da, d), "ERCOT_N_RT": pd.Series(rt, d), "ERCOT_N_DART": pd.Series(da - rt, d), "ERCOT_WN_BASIS": pd.Series(r.normal(0, 4, n), d),
         "HH_SPOT": pd.Series(hh, d)[d.dayofweek < 5], "ERCOT_N_HEAT": pd.Series(da / hh, d)[d.dayofweek < 5], "DD_DFW": pd.Series(dd, d), "LOAD_ERCO": pd.Series(load, d),
         "LOADFC_ERCO": pd.Series(fc, d), "WIND_ERCO": pd.Series(wind, d)}
    w = pd.date_range("2010-01-01", "2026-11-20", freq="W-FRI"); hw = S["HH_SPOT"].resample("W-FRI").last()
    S["STORAGE_SURPRISE"] = pd.Series(-200 * np.log(hw).diff().reindex(w).fillna(0).values + r.normal(0, 8, len(w)), w)
    S["NINO34"] = pd.Series(np.cumsum(r.normal(0, .1, len(w))), w)
    for k in U.EXTERNALS:
        if k not in S:
            if lab4.stationary(k): S[k] = pd.Series(np.exp(r.normal(0, .1, n)) * 1e4, d)
            else: S[k] = pd.Series(np.exp(np.cumsum(r.normal(0, .02, n))) * 50, d)[d.dayofweek < 5]
    S["NG_FRONT"] = S["HH_SPOT"] * np.exp(r.normal(0, .01, len(S["HH_SPOT"])))
    return {k: v.dropna() for k, v in S.items()}
if __name__ == "__main__":
    S = world(); t = time.time()
    print("positive controls", [(p["focal"], p["external"], round(p["r"], 3), p["passed"]) for p in lab4.positive_controls(S)])
    T = lab4.tests(S, lab4.pairs_of(S), lab4.scarcity_flag(S["ERCOT_N_RT"])); print("tests", len(T), round(time.time() - t), "s", flush=True)
    ex, conf = lab4.screen_confirm(T); conf = lab4.uri_check(S, conf) if len(conf) else conf
    v = conf[conf.state == "Validated"] if len(conf) else conf
    print(v.groupby(["family"]).size().to_dict() if len(v) else {})
    print(v[["focal", "external", "family", "lag", "e_confirm"]].to_string() if len(v) else "none")
    P = lab4.predictive(S, conf); print(P.to_string() if len(P) else "no predictive tests")
