"""CR1: are history-based curtailment ratings calibrated out of sample?

A flexible load curtails whenever the real-time price at its settlement point exceeds a threshold T.
For each year Y, a rating is issued using only years before Y: q10/q50/q90 of annual curtailed hours (H)
and of the longest continuous curtailment (L). The rating is then scored against what happened in Y.
Usage: python cr1.py <hourly csv(.gz) with date,he,<point columns>> <out.json> [--points LZ_WEST,LZ_NORTH,...]
Fixed by PREREGISTRATION_CR1.md.
"""
import json, sys, numpy as np, pandas as pd

SEED = 20261127
THRESHOLDS = [200, 500, 1000]            # $/MWh
FIRST_HIST, EVAL = 2011, (2016, 2025)    # history starts 2011; ratings scored 2016-2025 (>= 5 prior years)
PROSPECTIVE = 2026                       # Jan-Oct 2026, rated from 2011-2025 Jan-Oct paths
NDRAW = 5000
QS = (0.1, 0.5, 0.9)

def runs(x):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best

def seg(x):
    """summary of one month's boolean path: hours, length, leading run, trailing run, max run, all-true"""
    x = np.asarray(x, bool); n = len(x); h = int(x.sum())
    lead = n if h == n else int(np.argmin(x)); trail = n if h == n else int(np.argmin(x[::-1]))
    return (h, n, lead, trail, runs(x), h == n)

def month_paths(s, years, months):
    """{(year, month): summary of hours above threshold}"""
    out = {}
    for (y, m), g in s.groupby([s.index.year, s.index.month]):
        if y in years and m in months: out[(y, m)] = seg(g.values)
    return out

def chain(segs):
    """H and longest run of months laid end to end (runs spanning month boundaries are joined)"""
    H = sum(s[0] for s in segs); best = cur = 0
    for h, n, lead, trail, mx, full in segs:
        if full: cur += n
        else: best = max(best, cur + lead, mx); cur = trail
    return H, max(best, cur)

def rate(paths, past, months, rng, ndraw=NDRAW):
    """M1 month-block bootstrap: each calendar month drawn from a random past year."""
    pick = {m: [paths[(y, m)] for y in past if (y, m) in paths] for m in months}
    idx = {m: rng.integers(0, len(pick[m]), ndraw) for m in months}
    H = np.empty(ndraw); L = np.empty(ndraw)
    for i in range(ndraw):
        H[i], L[i] = chain([pick[m][idx[m][i]] for m in months])
    return {"H": np.quantile(H, QS).tolist(), "L": np.quantile(L, QS).tolist()}

def rate_m0(actual, past):
    """M0: empirical quantiles of past annual values."""
    v = {k: np.array([actual[y][k] for y in past]) for k in ("H", "L")}
    return {k: np.quantile(v[k], QS).tolist() for k in v}

CONF_START = 2014                         # residual pool for M2 begins with ratings issued for 2014 (>= 3 prior years)

def m2_band(r1_q50, resid):
    """M2: M1 median, with the band set by empirical quantiles of past log errors log(1+actual)-log(1+M1 median)."""
    if len(resid) < 2: return None
    lo, hi = np.quantile(resid, [0.1, 0.9]); c = np.log1p(r1_q50)
    return [float(max(0.0, np.expm1(c + lo))), float(r1_q50), float(np.expm1(c + hi))]

def pinball(q, y):
    return float(sum(max(t * (y - qq), (t - 1) * (y - qq)) for t, qq in zip(QS, q)))

def score_point(price, rng):
    res = []
    for T in THRESHOLDS:
        above = (price > T)
        for period, months, years_eval in (("year", list(range(1, 13)), range(EVAL[0], EVAL[1] + 1)), ("jan_oct", list(range(1, 11)), [PROSPECTIVE])):
            yrs = set(range(FIRST_HIST, PROSPECTIVE + 1))
            paths = month_paths(above, yrs, months)
            full = [y for y in yrs if all((y, m) in paths for m in months)]
            actual = {y: dict(zip(("H", "L"), map(float, chain([paths[(y, m)] for m in months])))) for y in full}
            resid = {"H": [], "L": []}
            for Y in sorted(set(range(CONF_START, max(years_eval) + 1)) & set(actual)):
                past = [y for y in full if y < Y]
                if len(past) < 3: continue
                r1, r0 = rate(paths, past, months, rng), rate_m0(actual, past)
                for k in ("H", "L"):
                    a = actual[Y][k]; r2 = m2_band(r1[k][1], resid[k])
                    if Y in years_eval and len(past) >= 5 and r2 is not None:
                        res.append(dict(T=T, period=period, year=Y, metric=k, actual=a, m1=r1[k], m0=r0[k], m2=r2,
                                        m1_in80=bool(r1[k][0] <= a <= r1[k][2]), m1_over90=bool(a > r1[k][2]),
                                        m0_in80=bool(r0[k][0] <= a <= r0[k][2]), m0_over90=bool(a > r0[k][2]),
                                        m2_in80=bool(r2[0] <= a <= r2[2]), m2_over90=bool(a > r2[2]),
                                        m1_pin=pinball(r1[k], a), m0_pin=pinball(r0[k], a), m2_pin=pinball(r2, a)))
                    resid[k].append(float(np.log1p(a) - np.log1p(r1[k][1])))
    return res

def clustered_ci(df, col, rng, boot=2000):
    yrs = df.year.unique(); vals = []
    for _ in range(boot):
        s = rng.choice(yrs, len(yrs)); vals.append(pd.concat([df[df.year == y] for y in s])[col].mean())
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]

def run(path, points=None):
    h = pd.read_csv(path, parse_dates=["date"])
    h["ts"] = h.date + pd.to_timedelta(h.he.astype(int) - 1, unit="h"); h = h.set_index("ts").sort_index()
    pts = points or [c for c in h.columns if c.startswith("LZ_")]
    rng = np.random.default_rng(SEED); rows = []
    for p in pts:
        for r in score_point(h[p].dropna(), rng): rows.append(dict(point=p, **r))
    df = pd.DataFrame(rows); ev = df[df.period == "year"]; pro = df[df.period == "jan_oct"]
    out = dict(points=pts, n_eval=int(len(ev)), summary={})
    for k in ("H", "L"):
        e = ev[ev.metric == k]
        out["summary"][k] = dict(
            m1_cover80=float(e.m1_in80.mean()), m1_cover80_ci=clustered_ci(e, "m1_in80", rng),
            m1_exceed90=float(e.m1_over90.mean()), m1_exceed90_ci=clustered_ci(e, "m1_over90", rng),
            m0_cover80=float(e.m0_in80.mean()), m0_exceed90=float(e.m0_over90.mean()),
            m2_cover80=float(e.m2_in80.mean()), m2_cover80_ci=clustered_ci(e, "m2_in80", rng),
            m2_exceed90=float(e.m2_over90.mean()), m2_exceed90_ci=clustered_ci(e, "m2_over90", rng),
            m1_pinball=float(e.m1_pin.mean()), m0_pinball=float(e.m0_pin.mean()), m2_pinball=float(e.m2_pin.mean()),
            m2_band_ratio_median=float(np.median([(r[2] + 1) / (r[1] + 1) for r in e.m2])),
            by_T={int(T): dict(cover80=float(g.m1_in80.mean()), exceed90=float(g.m1_over90.mean()), n=int(len(g))) for T, g in e.groupby("T")},
            band_ratio_median=float(np.median([(r[2] + 1) / (r[1] + 1) for r in e.m1])))
    # location differentiation: realised hours above $500 across points, same year
    h500 = ev[(ev.metric == "H") & (ev["T"] == 500)].pivot_table(index="year", columns="point", values="actual")
    spread = ((h500.max(axis=1) + 1) / (h500.min(axis=1) + 1)) if h500.shape[1] > 1 else pd.Series(dtype=float)
    out["location_spread_500"] = dict(by_year={int(y): float(v) for y, v in spread.items()}, share_years_over_1_25=float((spread > 1.25).mean()) if len(spread) else None)
    out["prospective_2026"] = {m: dict(n=int(len(pro)), cover80=float(pro[f"{m}_in80"].mean()), exceed90=float(pro[f"{m}_over90"].mean())) for m in ("m1", "m2")} if len(pro) else None
    s = out["summary"]
    cal = lambda m: bool(all(0.03 <= s[k][f"{m}_exceed90"] <= 0.20 and 0.65 <= s[k][f"{m}_cover80"] <= 0.92 for k in ("H", "L")))
    best = "m2" if cal("m2") and not cal("m1") else "m1"
    out["gates"] = dict(
        G1_calibration_m1=cal("m1"), G1_calibration_m2=cal("m2"), G1_calibration=bool(cal("m1") or cal("m2")),
        G2_informative=bool(s["H"][f"{best}_pinball"] <= s["H"]["m0_pinball"]), rated_method=best,
        G3_location=bool(out["location_spread_500"]["share_years_over_1_25"] is not None and out["location_spread_500"]["share_years_over_1_25"] >= 0.5))
    out["rows"] = df.to_dict("records")
    return out

if __name__ == "__main__":
    a = sys.argv[1:]; pts = a[a.index("--points") + 1].split(",") if "--points" in a else None
    r = run(a[0], pts); json.dump(r, open(a[1], "w"), indent=1, default=str)
    print(json.dumps({"summary": r["summary"], "loc": r["location_spread_500"], "pro": r["prospective_2026"], "gates": r["gates"]}, indent=1))
