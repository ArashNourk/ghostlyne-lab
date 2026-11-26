"""Synthetic validation of the R2 lab: implementation correctness, power and false-discovery behaviour.
Synthetic results validate the method. They are not evidence about real markets."""
import sys, time, json, numpy as np, pandas as pd
import universe as U, lab

def world(seed, plantsA, plantsB):
    """Weekly levels for every id. Everything loads on a global factor; plants add idiosyncratic links."""
    r = np.random.default_rng(seed); idx = pd.date_range("2008-01-04", "2026-11-20", freq="W-FRI"); n = len(idx)
    m = r.standard_t(4, n) * 0.02; ids = list(U.FOCAL) + list(U.EXTERNALS); eps = {k: r.standard_t(4, n) * 0.03 for k in ids}
    ret = {k: r.uniform(0.5, 1.4) * m + eps[k] for k in ids}
    for f, x, rho in plantsA: ret[f] = ret[f] + rho / np.sqrt(1 - rho ** 2) * eps[x]          # same-week idiosyncratic link
    for f, x, rho in plantsB: ret[f] = ret[f] + rho / np.sqrt(1 - rho ** 2) * np.roll(eps[x], 2)  # external leads by 2 weeks
    S = {k: pd.Series(100 * np.exp(np.cumsum(v)), idx) for k, v in ret.items()}
    S[U.MARKET] = pd.Series(100 * np.exp(np.cumsum(m)), idx); S["NINO34_W"] = pd.Series(np.cumsum(r.normal(0, .1, n)), idx)
    return S

def trial(seed, rhos):
    r = np.random.default_rng(1000 + seed); F = list(U.FOCAL); X = [k for k, v in U.EXTERNALS.items() if v["role"] == "candidate" and k != "NINO34_W"]
    xs = r.choice(X, 2 * len(F), replace=False)
    A = [(f, xs[i], rhos[i % len(rhos)]) for i, f in enumerate(F)]; B = [(f, xs[len(F) + i], rhos[(i + 1) % len(rhos)]) for i, f in enumerate(F)]
    S = world(seed, A, B); T, ex, conf = lab.run(S, dict(focal=U.FOCAL, externals=U.EXTERNALS))
    val = conf[conf.state == "Validated"] if len(conf) else conf
    hitA = [(rho, ((val.focal == f) & (val.external == x) & (val.family == "A_adjusted")).any()) for f, x, rho in A]
    hitB = [(rho, ((val.focal == f) & (val.external == x) & (val.family == "B_leadlag") & (val.lag == 2)).any()) for f, x, rho in B]
    planted = {(f, x) for f, x, _ in A + B}
    false = val[[(a, b) not in planted and fam != "A_total" for a, b, fam in zip(val.focal, val.external, val.family)]] if len(val) else val
    total_val = int((val.family == "A_total").sum()) if len(val) else 0
    # A_total on planted pairs is also a true finding (the link survives in raw returns); count only adjusted/lead-lag/stress false hits
    return hitA, hitB, len(false), false[["focal", "external", "family", "lag"]].values.tolist() if len(false) else []

if __name__ == "__main__":
    t0 = time.time(); rhos = [0.08, 0.12, 0.16, 0.20, 0.25, 0.30, 0.40]; HA, HB, FP, FL = [], [], [], []
    for s in range(int(sys.argv[1]) if len(sys.argv) > 1 else 3):
        a, b, fp, fl = trial(s, rhos); HA += a; HB += b; FP.append(fp); FL += fl; print("trial", s, round(time.time() - t0), "s", fp, "false", fl[:5], flush=True)
    df = lambda H: pd.DataFrame(H, columns=["rho", "hit"]).groupby("rho").hit.agg(["mean", "size"]).round(2).reset_index().values.tolist()
    out = dict(assoc=df(HA), leadlag=df(HB), false_validations_per_run=FP, false_examples=FL[:20])
    json.dump(out, open("synthetic_power.json", "w"), indent=1, default=str); print(json.dumps(out, default=str))
