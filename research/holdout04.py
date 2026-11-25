"""Run once: the pre-registered v0.4 test on 2023 (see PREREGISTRATION_v04.md). Writes research/HOLDOUT_v04_RESULTS.md."""
import sys, os
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import lab, candidates as C, v04
G = lab.G
TABLE = sys.argv[1]; OUT = Path(__file__).parent / "HOLDOUT_v04_RESULTS.md"
START, E0, E1 = pd.Timestamp("2021-03-01"), pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31")
if os.environ.get("GL_CODE_CHECK"):          # code check on development data only (2024), never the test year
    START, E0, E1 = pd.Timestamp("2022-03-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"); OUT = Path("/tmp/code_check04.md")

D = C.add_regime_features(lab.load_table(TABLE)); D = D[D.Date <= E1].reset_index(drop=True)
P, _ = lab.predictions(D, START)                      # GARCH-t etc. (pooled calibration, as in development)
dates = D.Date.values; pr = lambda x: "n/a" if x is None or not np.isfinite(x) else f"{100*x:.2f}%"
L = ["# Ghostlyne v0.4: 2023 test results", "", f"Run once on the pre-registered rules. Evaluation {E0.date()} to {E1.date()}, walk-forward from {START.date()}.", ""]
crit = {}
for side in ["long", "short"]:
    st = C.stress_flag(D, side); R, Yc = [], []
    for Lv in lab.LEV:
        raw, y = G.model_walk(D, side, G.DIST[Lv], START); R.append(np.where(D.Date >= START, raw, np.nan)); Yc.append(y)
    R = np.column_stack(R); Y = np.column_stack(Yc)
    step = G.monotone(np.column_stack([v04.calibrate_walk_regime(D, R[:, j], Y[:, j], st) for j in range(6)]))[0]
    smo = G.monotone(np.column_stack([v04.calibrate_walk_regime(D, R[:, j], Y[:, j], st, smooth=True) for j in range(6)]))[0]
    GA = P["GARCH(1,1)-t"][side]
    ok = ((D.Date >= E0) & (D.Date <= E1)).values & ~np.isnan(Y).any(1) & ~np.isnan(step).any(1) & ~np.isnan(smo).any(1) & ~np.isnan(GA).any(1)
    rows = np.where(ok)[0]; s = st[rows]
    L += [f"## {side.capitalize()}s", "", f"{len(rows)} market-days, {len(set(D.sym.values[rows]))} markets, stress days {s.mean():.1%}.", "",
          "| Rule | Limit | Realized (90% CI) | Stress-day realized (90% CI) | Mean leverage | Abstained |", "|---|---|---|---|---|---|"]
    res = {}
    for lim in [0.02, 0.05, 0.10]:
        l1, h1, _ = lab.rule_outcomes(step, Y, rows, lim); l2, h2, _ = lab.rule_outcomes(step, Y, rows, lim / 2)
        tv = v04.hybrid_thresholds(D, smo, Y, st, lim); tg = v04.hybrid_thresholds(D, GA, Y, st, lim)
        runs = {"v0.4 (smooth, tuned)": v04.rule_tau(smo, Y, rows, tv)[:2], "v0.3 (step, halved on stress)": (np.where(s, l2, l1), np.where(s, h2, h1)),
                "GARCH-t, same tuned rule": v04.rule_tau(GA, Y, rows, tg)[:2]}
        for nm, (lev, hit) in runs.items():
            r, ci = lab.week_boot_rate(dates[rows], hit); rs, cis = lab.week_boot_rate(dates[rows][s], hit[s]); res[(nm, lim)] = (r, rs, lev.mean())
            L.append(f"| {nm} | {lim:.0%} | {pr(r)} ({pr(ci[0])}, {pr(ci[1])}) | {pr(rs)} ({pr(cis[0])}, {pr(cis[1])}) | {lev.mean():.2f}x | {np.mean(lev == 0):.1%} |")
        if lim == 0.05:
            lev, hit = runs["v0.4 (smooth, tuned)"]; by = pd.DataFrame({"lev": lev, "hit": hit}).groupby("lev").hit.agg(["size", "mean"])
            by_txt = ", ".join(f"{int(k)}x: {int(r['size'])} days, realized {pr(r['mean'])}" if k else f"none: {int(r['size'])} days" for k, r in by.iterrows())
    e = lambda Pm: ((Y[rows] - Pm[rows]) ** 2).mean(0); sk = 1 - e(smo) / e(step)
    df = pd.DataFrame({"d": dates[rows], "p": np.round(smo[rows, 3], 4)}); dup = (df.groupby(["d", "p"]).p.transform("size") > 1).mean()
    df2 = pd.DataFrame({"d": dates[rows], "p": np.round(step[rows, 3], 4)}); dup2 = (df2.groupby(["d", "p"]).p.transform("size") > 1).mean()
    L += ["", "v0.4 at 5%, by recommended leverage: " + by_txt,
          "Brier skill, smooth vs step calibration (40x..5x): " + " ".join(f"{x:+.4f}" for x in sk),
          f"10x forecasts identical to another market's the same day: step {dup2:.1%}, smooth {dup:.1%}", ""]
    v4, v3, ga = res[("v0.4 (smooth, tuned)", 0.05)], res[("v0.3 (step, halved on stress)", 0.05)], res[("GARCH-t, same tuned rule", 0.05)]
    crit[side] = {"H1": v4[0] <= 0.05, "H2": v4[0] >= 0.03, "H3": v4[1] <= 0.05, "H4": v4[2] > v3[2],
                  "H5": all(sk[j] >= -0.002 for j in [1, 2, 3]) and dup < 0.30, "H6": v4[2] > ga[2] and v4[0] <= ga[0] + 0.005}
L += ["## Pre-registered criteria", "", "| # | Longs | Shorts |", "|---|---|---|"]
for h in ["H1", "H2", "H3", "H4", "H5", "H6"]:
    L.append(f"| {h} | {'pass' if crit['long'][h] else 'FAIL'} | {'pass' if crit['short'][h] else 'FAIL'} |")
go = all(crit[s][h] for s in crit for h in ["H1", "H2", "H3", "H4", "H5"])
L += ["", f"Decision rule (H1 to H5 on both sides): **{'v0.4 goes live' if go else 'v0.4 does not go live'}**."]
OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))
