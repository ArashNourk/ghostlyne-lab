"""Walk-forward check that calibrated odds mean what they say. Writes results/odds_backtest.json and .md"""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
sys.path.insert(0, str(Path(__file__).parent)); import common as G

cache = Path("data/candles"); out = Path("results"); out.mkdir(exist_ok=True)
through = pd.Timestamp.utcnow().tz_localize(None).normalize() - pd.Timedelta(days=1)
D = G.features(G.load_all(cache, through)); print("rows", len(D), D.Date.min().date(), D.Date.max().date(), flush=True)
EVAL = pd.Timestamp("2024-01-01"); res = {"rows": int(len(D)), "eval_from": str(EVAL.date()), "through": str(D.Date.max().date()), "tests": {}}
L = ["# Ghostlyne Odds: calibrated walk-forward backtest", f"Evaluation {EVAL.date()} to {D.Date.max().date()}, {D.sym.nunique()} perpetuals. Calibration uses only earlier out-of-sample predictions.", "",
     "| Position | Liq. distance | Base rate | Textbook Brier skill | Raw skill | Calibrated skill | Calibrated AUC | Top-decile predicted vs actual |", "|---|---|---|---|---|---|---|---|"]
for side in ["long", "short"]:
    for lev in G.LEVERAGE:
        k = G.DIST[lev]; raw, cal, y = G.walk_calibrated(D, side, k, "2023-01-01")
        tb = G.textbook(D, side, k); ok = (D.Date >= EVAL).values & ~np.isnan(y) & ~np.isnan(cal)
        if y[ok].sum() < 20: continue
        b = lambda p: brier_score_loss(y[ok], p[ok]); ref = b(tb)
        q = pd.qcut(cal[ok], 10, labels=False, duplicates="drop"); dec = pd.DataFrame({"q": q, "p": cal[ok], "y": y[ok]}).groupby("q").mean()
        r = {"k": k, "n": int(ok.sum()), "base": float(y[ok].mean()), "skill_raw": float(1 - b(raw) / ref), "skill_cal": float(1 - b(cal) / ref),
             "auc_cal": float(roc_auc_score(y[ok], cal[ok])), "auc_textbook": float(roc_auc_score(y[ok], tb[ok])), "deciles": dec[["p", "y"]].round(4).values.tolist()}
        res["tests"][f"{side}_{lev}x"] = r; top = r["deciles"][-1]
        L.append(f"| {lev}x {side} | {100*k:.1f}% | {100*r['base']:.2f}% | 0 | {r['skill_raw']:+.3f} | {r['skill_cal']:+.3f} | {r['auc_cal']:.3f} (textbook {r['auc_textbook']:.3f}) | {100*top[0]:.1f}% vs {100*top[1]:.1f}% |")
        print(L[-1], flush=True)
json.dump(res, open(out / "odds_backtest.json", "w"), indent=1); (out / "odds_backtest.md").write_text("\n".join(L))
