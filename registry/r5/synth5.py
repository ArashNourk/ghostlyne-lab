"""Synthetic check of the R5 decision lab: conventional drivers explain prices; unconventional features are noise except the planted control."""
import time, numpy as np, pandas as pd, lab5
def world(seed=5):
    r = np.random.default_rng(seed); days = pd.date_range("2016-01-01", "2026-11-20", freq="D"); n = len(days)
    doy = days.dayofyear.values; temp = 65 + 20 * np.sin(2 * np.pi * (doy - 110) / 365) + r.normal(0, 7, n); dd = np.abs(temp - 65)
    windd = np.exp(r.normal(0, .4, n)) * 9000; load = 45000 * (1 + 0.01 * dd + r.normal(0, .03, n)); hh = np.exp(np.cumsum(r.normal(0, .03, n))) * 3
    rows = []
    for i, d in enumerate(days):
        for he in range(1, 25):
            shape = 1 + 0.3 * np.sin(np.pi * (he - 6) / 18) if 6 <= he <= 22 else 0.8
            L = load[i] * shape; W = windd[i] * (1.2 - shape / 2); net = L - W
            da = 10 * hh[i] + 0.0009 * net + r.normal(0, 3); rt = da + r.standard_t(3) * 8 + (400 if (net > 62000 and r.random() < .3) else 0)
            rows.append((d, he, da, rt, da + r.normal(-2, 4), rt + r.normal(-2, 8), L, L * (1 + r.normal(0, .02)), W, 2000.0, 20000.0, 5000.0, r.normal(30000, 3000), r.normal(9000, 2000), r.normal(70000, 5000), r.normal(90000, 6000), r.normal(30000, 3000), r.normal(70000, 5000)))
    H = pd.DataFrame(rows, columns=["date", "he", "DA_HB_NORTH", "RT_HB_NORTH", "DA_HB_WEST", "RT_HB_WEST", "LOAD_ERCO", "LOADFC_ERCO", "WIND_ERCO", "SOLAR_ERCO", "GASGEN_ERCO", "NUC_ERCO",
                                     "LOAD_SWPP", "WIND_SWPP", "LOAD_MISO", "LOAD_PJM", "LOADFC_SWPP", "LOADFC_MISO"]).set_index(["date", "he"])
    daily4 = pd.DataFrame({"HH_SPOT": hh, "T_DFW": temp, "T_IAH": temp + 3, "T_PHL": temp - 5 + r.normal(0, 5, n), "T_BOS": temp - 10 + r.normal(0, 5, n)}, index=days)
    rw = lambda: pd.Series(np.exp(np.cumsum(r.normal(0, .02, n))) * 50, days)
    yahoo = {t: rw() for t in ["TTF=F", "CL=F", "LNG", "NG=F", "HG=F", "CAD=X", "MXN=X", "XLU", "VST", "BDRY", "ZC=F", "BTC-USD", "MARA", "RIOT", "NVDA", "SOXX", "DLR", "EQIX"]}
    return H, daily4, rw() * 0.002, yahoo, None, pd.Series(r.normal(0, 1, n // 7), pd.date_range("2016-01-06", periods=n // 7, freq="W-WED"))
if __name__ == "__main__":
    t = time.time(); H, d4, hp, y, st, ni = world(); print("built", round(time.time() - t), flush=True)
    D, F, base, G = lab5.build(H, d4, hp, y, st, ni); print("features", len(base), {k: len(v) for k, v in G.items()}, "spike rate", round(D.SPIKE.mean(), 3), flush=True)
    R, P = lab5.run(D, F, base, G); print("run", round(time.time() - t), flush=True)
    pd.set_option("display.width", 220)
    print(R[["decision", "group", "window", "mean_gain", "ci_lo", "ci_hi", "p_one_sided", "candidate", "q", "state"]].round(4).to_string())
