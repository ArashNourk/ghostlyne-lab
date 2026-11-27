"""Synthetic end-to-end check for R3 (method validation only, not market evidence)."""
import sys, time, json, numpy as np, pandas as pd
import universe as U, main3
def world(seed=1):
    r = np.random.default_rng(seed); idx = pd.date_range("2005-01-07", "2026-11-20", freq="W-FRI"); n = len(idx)
    m = r.standard_t(4, n) * 0.02; ids = list(U.FOCAL) + [k for k in U.EXTERNALS if not k.startswith("SYN")]
    eps = {k: r.standard_t(4, n) * 0.03 for k in ids}; ret = {k: r.uniform(.5, 1.4) * m + eps[k] for k in ids}
    ret["NVDA"] = ret["NVDA"] + 0.35 * eps["BZ=F"] / np.sqrt(1 - .35 ** 2)                       # plant: same-week association
    big = np.abs(eps["KRW=X"]) > np.quantile(np.abs(eps["KRW=X"]), 0.94)
    ret["MU"] = ret["MU"] + np.roll(np.where(big, -np.sign(eps["KRW=X"]) * 0.03, 0), 1)          # plant: shock transmission
    S = {k: pd.Series(100 * np.exp(np.cumsum(v)), idx) for k, v in ret.items()}
    mi = pd.date_range("2005-01-28", "2026-10-28", freq="ME") ; cu = np.log(S["HG=F"].resample("ME").last()).diff(12)
    for k in U.REVENUE:
        g = r.normal(0, .08, len(mi)).cumsum() * 0.3
        if k == "REV_2308": g = g + 0.8 * cu.shift(6).reindex(mi).fillna(0).values                 # plant: copper leads Delta revenue by 6 months
        S[k] = pd.Series(1e9 * np.exp(g + r.normal(0, .03, len(mi))), mi + pd.Timedelta(days=-3))
    return S
if __name__ == "__main__":
    t = time.time(); res = main3.analyse(world(), {}); print("secs", round(time.time() - t))
    print(json.dumps(res["meta"]["validated"]), json.dumps(res["meta"]["candidates"]))
    for v in res["validated"]:
        if v["family"] != "A_w" and v["family"] != "A_m" and v["family"] != "A_q" or v["focal"] == "NVDA" and v["external"] == "BZ=F":
            print(v["focal"], v["external"], v["family"], v["lag"], v["dir"], round(v["e_confirm"], 3), v["monitor"].get("state"), v["monitor"].get("lag"))
    print("chains", [(c["chain"], c["state"]) for c in res["chains"]][:4]); print("pred", res["predictive"])
    json.dump(res, open("/tmp/R3_synth.json", "w"), default=str)
