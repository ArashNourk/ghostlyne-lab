"""Backtest v2: production-equivalent information (23:15 UTC truncation), mark-price liquidation labels, leverage
monotonicity, and comparison against conventional baselines calibrated by the same procedure.
Writes results/backtest_v2.md, results/backtest_v2.json and results/odds_backtest.json (used by the site)."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
sys.path.insert(0, str(Path(__file__).parent)); import common as G

ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "results"; OUT.mkdir(exist_ok=True)
START, EVAL = pd.Timestamp("2023-01-01"), pd.Timestamp("2024-01-01")
through = pd.Timestamp.now("UTC").tz_localize(None).normalize() - pd.Timedelta(days=1)
data = G.load(ROOT / "data", through); D = G.features(data)
print("rows", len(D), "markets", D.sym.nunique(), D.Date.min().date(), D.Date.max().date(), flush=True)

sd_ewma = G.ewma_sd(D); print("ewma done", flush=True)
sd_garch = G.garch_sd(D, START); print("garch done", flush=True)
NAMES = ["Ghostlyne", "Textbook (ATR, normal)", "EWMA RiskMetrics", "GARCH(1,1)-t", "Filtered historical simulation", "Rolling 1-year frequency"]
LEV = G.LEVERAGE

def week_boot(D, ok, e_a, e_b, B=1000, seed=0):
    wk = D.Date.values[ok].astype("datetime64[W]")
    ga = pd.Series(e_a).groupby(wk).sum(); gb = pd.Series(e_b).groupby(wk).sum()
    rng = np.random.default_rng(seed); n = len(ga); sk = []
    for _ in range(B):
        i = rng.integers(0, n, n); sk.append(1 - ga.values[i].sum() / gb.values[i].sum())
    return float(np.percentile(sk, 5)), float(np.percentile(sk, 95))

res = {"start": str(START.date()), "eval_from": str(EVAL.date()), "through": str(D.Date.max().date()), "markets": sorted(D.sym.unique().tolist()),
       "rows": int(len(D)), "mmr": G.MMR, "tests": {}, "by_market": {}, "monotonic_violation_share": {}, "maxlev": {}}
site = {"eval_from": str(EVAL.date()), "through": str(D.Date.max().date()), "tests": {}, "maxlev": {}}
THR = 0.05

def maxlev_check(Pm, Y, ok):
    """Validate the 'max leverage at or below 5% modeled odds' recommendation: for every market-day, take the highest
    leverage whose forecast is <= 5%, then record whether a position at that leverage was actually liquidated."""
    lev = np.array(LEV); rows = np.where(ok)[0]; rec_L, rec_p, hit = [], [], []
    for i in rows:
        good = np.where(Pm[i] <= THR)[0]
        if len(good) == 0: rec_L.append(0); rec_p.append(np.nan); hit.append(np.nan); continue
        j = good[np.argmax(lev[good])]; rec_L.append(int(lev[j])); rec_p.append(Pm[i, j]); hit.append(Y[i, j])
    rec_L, rec_p, hit = np.array(rec_L), np.array(rec_p), np.array(hit); has = rec_L > 0
    wk = D.Date.values[rows][has].astype("datetime64[W]"); g = pd.DataFrame({"w": wk, "h": hit[has]}).groupby("w").h.agg(["sum", "count"])
    rng = np.random.default_rng(1); bs = []
    for _ in range(1000):
        i = rng.integers(0, len(g), len(g)); bs.append(g["sum"].values[i].sum() / g["count"].values[i].sum())
    by = {str(L): {"days": int((rec_L == L).sum()), "forecast": float(np.nanmean(rec_p[rec_L == L])), "realized": float(np.nanmean(hit[rec_L == L]))}
          for L in LEV if (rec_L == L).sum() >= 50}
    return {"n": int(len(rows)), "covered": float(has.mean()), "under5x_share": float((~has).mean()), "realized": float(np.nanmean(hit[has])),
            "realized_ci90": [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))], "forecast_mean": float(np.nanmean(rec_p[has])),
            "mean_leverage": float(rec_L[has].mean()), "breaches": int(np.nansum(hit[has])), "by_leverage": by}
for side in ["long", "short"]:
    P = {nm: np.full((len(D), len(LEV)), np.nan) for nm in NAMES}; Y = np.full((len(D), len(LEV)), np.nan); Ylast = np.full((len(D), len(LEV)), np.nan)
    for j, L in enumerate(LEV):
        k = G.DIST[L]
        raw, y = G.model_walk(D, side, k, START); Y[:, j] = y; Ylast[:, j] = G.target(D, side, k, "last").values
        raws = {"Ghostlyne": raw, "Textbook (ATR, normal)": G.textbook(D, side, k), "EWMA RiskMetrics": G.reflection(sd_ewma, side, k),
                "GARCH(1,1)-t": G.reflection(sd_garch, side, k), "Filtered historical simulation": G.fhs_prob(D, side, k, sd_ewma),
                "Rolling 1-year frequency": G.rolling_freq(D, side, k)}
        for nm, r in raws.items(): P[nm][:, j] = G.calibrate_walk(D, np.where(D.Date >= START, r, np.nan), y)
        print(side, L, "x done", flush=True)
    viol = {}
    for nm in NAMES:
        P[nm], bad = G.monotone(P[nm]); viol[nm] = bad
    valid = ~np.isnan(P["Ghostlyne"]).any(1)
    res["monotonic_violation_share"][side] = {nm: viol[nm] / max(valid.sum(), 1) for nm in NAMES}
    okall = (D.Date >= EVAL).values & ~np.isnan(Y).any(1)
    for nm in NAMES: okall &= ~np.isnan(P[nm]).any(1)
    res["maxlev"][side] = {nm: maxlev_check(P[nm], Y, okall) for nm in NAMES}
    m = res["maxlev"][side]["Ghostlyne"]; site["maxlev"][side] = m
    print(side, "max-lev <=5%: realized", round(m["realized"], 4), m["realized_ci90"], "mean lev", round(m["mean_leverage"], 2), flush=True)
    for j, L in enumerate(LEV):
        y = Y[:, j]; ok = (D.Date >= EVAL).values & ~np.isnan(y)
        for nm in NAMES: ok &= ~np.isnan(P[nm][:, j])
        if y[ok].sum() < 20: continue
        e = {nm: (y[ok] - P[nm][ok, j]) ** 2 for nm in NAMES}; br = {nm: float(e[nm].mean()) for nm in NAMES}
        bases = [nm for nm in NAMES if nm != "Ghostlyne"]; best = min(bases, key=lambda n: br[n])
        t = {"k": G.DIST[L], "n": int(ok.sum()), "base_rate": float(y[ok].mean()), "brier": br,
             "auc": {nm: float(roc_auc_score(y[ok], P[nm][ok, j])) for nm in NAMES},
             "skill_vs": {nm: float(1 - br["Ghostlyne"] / br[nm]) for nm in bases},
             "skill_ci90_vs": {nm: week_boot(D, ok, e["Ghostlyne"], e[nm]) for nm in bases},
             "best_baseline": best, "last_price_base_rate": float(np.nanmean(Ylast[ok, j]))}
        q = pd.qcut(P["Ghostlyne"][ok, j], 10, labels=False, duplicates="drop")
        t["deciles"] = pd.DataFrame({"q": q, "p": P["Ghostlyne"][ok, j], "y": y[ok]}).groupby("q").mean()[["p", "y"]].round(4).values.tolist()
        res["tests"][f"{side}_{L}x"] = t
        site["tests"][f"{side}_{L}x"] = {"k": t["k"], "n": t["n"], "base": t["base_rate"], "deciles": t["deciles"], "best_baseline": best,
                                         "skill_best": t["skill_vs"][best], "ci_best": t["skill_ci90_vs"][best],
                                         "auc_cal": t["auc"]["Ghostlyne"], "auc_best": t["auc"][best], "auc_textbook": t["auc"]["Textbook (ATR, normal)"],
                                         "skill_cal": t["skill_vs"]["Textbook (ATR, normal)"]}
        print(f"{side} {L}x  skill vs best ({best}) {t['skill_vs'][best]:+.3f} CI {t['skill_ci90_vs'][best]}", flush=True)
    # by market, 20x/15x/10x pooled: Ghostlyne vs the best baseline for that side
    for s in sorted(D.sym.unique()):
        em = eb = 0.0; nb = 0
        for j, L in enumerate(LEV):
            if L not in (20, 15, 10) or f"{side}_{L}x" not in res["tests"]: continue
            best = res["tests"][f"{side}_{L}x"]["best_baseline"]
            ok = (D.Date >= EVAL).values & (D.sym == s).values & ~np.isnan(Y[:, j]) & ~np.isnan(P["Ghostlyne"][:, j]) & ~np.isnan(P[best][:, j])
            em += ((Y[ok, j] - P["Ghostlyne"][ok, j]) ** 2).sum(); eb += ((Y[ok, j] - P[best][ok, j]) ** 2).sum(); nb += ok.sum()
        if nb: res["by_market"].setdefault(side, {})[s] = {"skill": float(1 - em / eb), "n": int(nb)}

json.dump(res, open(OUT / "backtest_v2.json", "w"), indent=1); json.dump(site, open(OUT / "odds_backtest.json", "w"), indent=1)
L = ["# Ghostlyne Odds: backtest v2", "",
     f"Walk-forward, model from {res['start']}, evaluated {res['eval_from']} to {res['through']}, {len(res['markets'])} Binance USD-M perpetuals.",
     "Information set: complete days before d plus day d truncated at 23:15 UTC (identical to production). Labels: Binance mark price reaching",
     f"a standardized isolated-margin liquidation level (maintenance margin {100*G.MMR:.1f}%) for a position entered at the next UTC open.",
     "Every model, including every baseline, is calibrated by the same walk-forward isotonic procedure and made monotone across leverage.",
     "Skill = 1 - Brier(Ghostlyne)/Brier(baseline). 90% intervals from a week-block bootstrap (markets on the same days resampled together).", "",
     "| Position | Liq. dist. | Base rate | Best baseline | Skill vs best (90% CI) | Skill vs textbook | AUC Ghostlyne / best |", "|---|---|---|---|---|---|---|"]
for key, t in res["tests"].items():
    b = t["best_baseline"]; lo, hi = t["skill_ci90_vs"][b]
    L.append(f"| {key.replace('_', ' ')} | {100*t['k']:.1f}% | {100*t['base_rate']:.2f}% | {b} | {t['skill_vs'][b]:+.3f} ({lo:+.3f}, {hi:+.3f}) | {t['skill_vs']['Textbook (ATR, normal)']:+.3f} | {t['auc']['Ghostlyne']:.3f} / {t['auc'][b]:.3f} |")
L += ["", "Skill against every baseline:", "", "| Position | " + " | ".join(NAMES[1:]) + " |", "|---|" + "---|" * (len(NAMES) - 1)]
for key, t in res["tests"].items():
    L.append(f"| {key.replace('_', ' ')} | " + " | ".join(f"{t['skill_vs'][n]:+.3f}" for n in NAMES[1:]) + " |")
for side in ["long", "short"]:
    bm = res["by_market"].get(side, {}); pos = sum(v["skill"] > 0 for v in bm.values())
    L += ["", f"By market ({side}, 20x/15x/10x pooled, vs best baseline): positive in {pos} of {len(bm)} markets.",
          ", ".join(f"{s.replace('USDT','')} {v['skill']:+.3f}" for s, v in sorted(bm.items(), key=lambda kv: -kv[1]['skill']))]
L += ["", "## Max leverage at or below 5% modeled odds", "",
      "For every market-day, the highest leverage whose forecast is at or below 5%. Realized = share of those recommended positions that were",
      "actually liquidated (target: at or below 5%). A better model recommends more leverage at the same realized risk.", "",
      "| Side | Method | Realized liq. rate (90% CI) | Mean forecast | Mean recommended leverage | Days with no level ≤5% |", "|---|---|---|---|---|---|"]
for side in ["long", "short"]:
    for nm in NAMES:
        m = res["maxlev"][side][nm]
        L.append(f"| {side} | {nm} | {100*m['realized']:.2f}% ({100*m['realized_ci90'][0]:.2f}, {100*m['realized_ci90'][1]:.2f}) | {100*m['forecast_mean']:.2f}% | {m['mean_leverage']:.1f}x | {100*m['under5x_share']:.1f}% |")
    L.append("")
    L.append(f"Ghostlyne {side}, by recommended leverage: " + ", ".join(f"{k}x: {v['days']} days, forecast {100*v['forecast']:.1f}%, realized {100*v['realized']:.1f}%" for k, v in res["maxlev"][side]["Ghostlyne"]["by_leverage"].items()))
    L.append("")
L += ["", "Share of forecast rows where raw calibrated odds violated leverage monotonicity before correction:",
      json.dumps({s: {k: round(v, 4) for k, v in d.items()} for s, d in res["monotonic_violation_share"].items()})]
(OUT / "backtest_v2.md").write_text("\n".join(L)); print("\n".join(L))
