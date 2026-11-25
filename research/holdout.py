"""Run once: the pre-registered 2022 holdout (see PREREGISTRATION.md). Writes research/HOLDOUT_RESULTS.md."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import lab, candidates as C
G = lab.G
TABLE = sys.argv[1]; OUT = Path(__file__).parent / "HOLDOUT_RESULTS.md"
START, E0, E1 = pd.Timestamp("2021-03-01"), pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")
import os
if os.environ.get("GL_CODE_CHECK"):          # code check on development data only (2024), never the holdout
    START, E0, E1 = pd.Timestamp("2023-01-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2024-12-31"); OUT = Path("/tmp/code_check.md")

D = C.add_regime_features(lab.load_table(TABLE)); D = D[D.Date <= E1].reset_index(drop=True)
P, Y = lab.predictions(D, START)
LOCK = {}
for side in ["long", "short"]:
    st = C.stress_flag(D, side); cols = []
    for L in lab.LEV:
        raw, y = G.model_walk(D, side, G.DIST[L], START); raw = np.where(D.Date >= START, raw, np.nan)
        cols.append(C.calibrate_walk_regime(D, raw, y, st))
    LOCK[side] = G.monotone(np.column_stack(cols))[0]

def rule(Pm, Ym, rows, thr, stress=None, cap=20):
    l1, h1, p1 = lab.rule_outcomes(Pm, Ym, rows, thr, cap)
    if stress is None: return l1, h1, p1
    l2, h2, p2 = lab.rule_outcomes(Pm, Ym, rows, thr / 2, cap)
    return np.where(stress, l2, l1), np.where(stress, h2, h1), np.where(stress, p2, p1)

GRID = np.round(np.arange(0.005, 0.2001, 0.0025), 4)
def weekly(fn, rows, dates):
    wk = pd.to_datetime(dates[rows]).to_period("W"); M = []
    for t in GRID:
        lev, hit, _ = fn(t)
        M.append(pd.DataFrame({"w": wk, "h": np.nan_to_num(hit), "n": ~np.isnan(hit), "l": lev, "c": 1}).groupby("w")[["h", "n", "l", "c"]].sum().values)
    return np.stack(M)
def lev_at(M, idx, target):
    h, n, l, c = (M[:, idx, i].sum(1) for i in range(4))
    return lab.lev_at_rate(pd.DataFrame({"realized": h / np.maximum(n, 1), "mean_lev": l / c[0]}), target)
def matched(Ma, Mb, target, B=1000, seed=0):
    W = Ma.shape[1]; full = lev_at(Ma, np.arange(W), target) - lev_at(Mb, np.arange(W), target)
    rng = np.random.default_rng(seed); d = []
    for _ in range(B):
        i = rng.integers(0, W, W); d.append(lev_at(Ma, i, target) - lev_at(Mb, i, target))
    d = np.array(d); d = d[np.isfinite(d)]
    return full, (np.percentile(d, 5), np.percentile(d, 95)) if len(d) > 100 else (np.nan, np.nan)

pr = lambda x: "n/a" if x is None or not np.isfinite(x) else f"{100*x:.2f}%"
L = ["# Ghostlyne max-leverage rule: 2022 holdout results", "",
     f"Run once on the pre-registered rules. Evaluation {E0.date()} to {E1.date()}, walk-forward from {START.date()}.", ""]
crit = {}
dates = D.Date.values
for side in ["long", "short"]:
    ok = ((D.Date >= E0) & (D.Date <= E1)).values & ~np.isnan(Y[side]).any(1) & ~np.isnan(LOCK[side]).any(1)
    for m in ["Ghostlyne", "GARCH(1,1)-t"]: ok &= ~np.isnan(P[m][side]).any(1)
    rows = np.where(ok)[0]; st_all = C.stress_flag(D, side); st = st_all[rows]
    L += [f"## {side.capitalize()}s", "", f"{len(rows)} market-days, {D.sym.values[rows].tolist().__len__() and len(set(D.sym.values[rows]))} markets, stress days {st.mean():.1%}.", "",
          "| Rule | Limit | Realized (90% CI) | Stress-day realized (90% CI) | Mean forecast | Mean leverage offered | Abstained |", "|---|---|---|---|---|---|---|"]
    res = {}
    for name, Pm, gate in [("Locked (stress-calibrated + gate)", LOCK[side], True), ("Live v2 (pooled calibration, no gate)", P["Ghostlyne"][side], False),
                           ("GARCH(1,1)-t", P["GARCH(1,1)-t"][side], False)]:
        for thr in [0.02, 0.05, 0.10]:
            lev, hit, p = rule(Pm, Y[side], rows, thr, st if gate else None)
            r, ci = lab.week_boot_rate(dates[rows], hit); rs, cis = lab.week_boot_rate(dates[rows][st], hit[st])
            res[(name, thr)] = (r, ci, rs, cis, lev)
            L.append(f"| {name} | {thr:.0%} | {pr(r)} ({pr(ci[0])}, {pr(ci[1])}) | {pr(rs)} ({pr(cis[0])}, {pr(cis[1])}) | {pr(np.nanmean(p))} | {lev.mean():.2f}x | {np.mean(lev == 0):.1%} |")
    lk = res[("Locked (stress-calibrated + gate)", 0.05)]; v2 = res[("Live v2 (pooled calibration, no gate)", 0.05)]
    lev, hit, _ = rule(LOCK[side], Y[side], rows, 0.05, st)
    by = pd.DataFrame({"lev": lev, "hit": hit}).groupby("lev").hit.agg(["size", "mean"])
    L += ["", "Locked rule at 5%, by recommended leverage: " + ", ".join(f"{int(k) if k else 'none'}{'x' if k else ''}: {int(r["size"])} days, realized {pr(r['mean']) if k else '-'}" for k, r in by.iterrows())]
    # H4: the 20x cap
    lu, hu, _ = rule(LOCK[side], Y[side], rows, 0.05, st, cap=40); n40 = int((lu == 40).sum())
    r40 = float(np.nanmean(hu[lu == 40])) if n40 else np.nan
    lc, hc, _ = rule(LOCK[side], Y[side], rows, 0.05, st); rc40 = float(np.nanmean(hc[lu == 40])) if n40 else np.nan
    L += [f"20x cap: the uncapped rule would have named 40x on {n40} days; those 40x positions were liquidated {pr(r40)}; the capped recommendation on the same days was liquidated {pr(rc40)}."]
    # H5: matched risk
    Ma = weekly(lambda t: rule(LOCK[side], Y[side], rows, t, st), rows, dates); Mb = weekly(lambda t: rule(P["GARCH(1,1)-t"][side], Y[side], rows, t), rows, dates)
    mt = {t: matched(Ma, Mb, t) for t in [0.03, 0.04]}
    L += ["Matched risk, mean leverage offered (locked minus GARCH-t): " + "; ".join(f"at {t:.0%} realized: {d:+.2f}x (90% {ci[0]:+.2f} to {ci[1]:+.2f})" for t, (d, ci) in mt.items())]
    yb = Y[side][rows]; L += ["Brier skill of locked vs live v2 by leverage (40x..5x): " + " ".join(f"{1 - ((yb[:, j] - LOCK[side][rows, j])**2).mean() / ((yb[:, j] - P['Ghostlyne'][side][rows, j])**2).mean():+.3f}" for j in range(6)), ""]
    crit[side] = {"H1": lk[0] <= 0.05, "H2": lk[2] <= 0.05, "H3": lk[2] < v2[2], "H4": (n40 < 30) or (r40 > 0.05), "H5": all(np.isfinite(d) and d > 0 for d, _ in mt.values())}
L += ["## Pre-registered criteria", "", "| # | Longs | Shorts |", "|---|---|---|"]
for h in ["H1", "H2", "H3", "H4", "H5"]:
    L.append(f"| {h} | {'pass' if crit['long'][h] else 'FAIL'} | {'pass' if crit['short'][h] else 'FAIL'} |")
OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))
