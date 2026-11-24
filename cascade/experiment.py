"""Cascade-adjusted wick odds. Question: does knowing how leverage is positioned (open interest build-up, funding,
long/short crowding) improve next-day liquidation-wick odds beyond the volatility texture model, and is the effect
asymmetric in the economically expected direction (crowded longs -> down-wicks, crowded shorts -> up-wicks)?
Walk-forward, monthly refit, every feature known at the prior day's close (UTC)."""
import json, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, brier_score_loss

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "data"); OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "results"); OUT.mkdir(exist_ok=True)
TEST_START = pd.Timestamp(sys.argv[3] if len(sys.argv) > 3 else "2023-01-01")
K = [0.05, 0.10, 0.15]

def load():
    kl = {p.stem: pd.read_parquet(p).set_index("date").sort_index() for p in (DATA / "klines").glob("*.parquet")}
    fu = {p.stem: pd.read_parquet(p) for p in (DATA / "funding").glob("*.parquet")}
    me = {p.stem: pd.read_parquet(p).set_index("date").sort_index() for p in (DATA / "metrics").glob("*.parquet")}
    return kl, fu, me

def build(kl, fu, me):
    idx = sorted(set().union(*[k.index for k in kl.values()]))
    O = pd.DataFrame({s: k.open for s, k in kl.items()}).reindex(idx); H = pd.DataFrame({s: k.high for s, k in kl.items()}).reindex(idx)
    L = pd.DataFrame({s: k.low for s, k in kl.items()}).reindex(idx); C = pd.DataFrame({s: k.close for s, k in kl.items()}).reindex(idx)
    down, up, rng, ret = np.log(L / O), np.log(H / O), np.log(H / L), np.log(C / C.shift())
    pk = rng ** 2 / (4 * np.log(2))
    def excl(frame, thr):
        hit = (frame <= -thr).astype(float).where(frame.notna()); tot = hit.sum(1); n = hit.notna().sum(1)
        return {s: (tot - hit[s].fillna(0)) / (n - hit[s].notna().astype(int)).clip(lower=1) for s in kl}
    dw10, dw05, uw10 = excl(down, .10), excl(down, .05), excl(-up, .10)
    rows = []
    for s, k in kl.items():
        f = pd.DataFrame(index=idx)
        f["v1"] = np.log(pk[s] + 1e-8); f["v7"] = np.log(pk[s].rolling(7).mean()); f["v30"] = np.log(pk[s].rolling(30).mean())
        f["atr14"] = np.log(rng[s].rolling(14).mean())
        f["ret1"] = ret[s]; f["ret7"] = np.log(C[s]).diff(7); f["dd30"] = np.log(C[s] / C[s].rolling(30).max()); f["ru30"] = np.log(C[s] / C[s].rolling(30).min())
        if "BTCUSDT" in kl: f["b_v7"] = np.log(pk["BTCUSDT"].rolling(7).mean()); f["b_ret1"] = ret["BTCUSDT"]
        f["mkt_dw10"] = dw10[s]; f["mkt_dw05"] = dw05[s]; f["mkt_uw10"] = uw10[s]; f["mkt_dw10_3d"] = dw10[s].rolling(3).mean()
        # positioning
        if s in fu:
            fr = fu[s].set_index("time").last_funding_rate.resample("D").mean().reindex(idx)
            f["fund1"] = fr * 1e4; f["fund3"] = fr.rolling(3).mean() * 1e4; f["fund_z"] = (fr - fr.rolling(60).mean()) / fr.rolling(60).std()
        if s in me:
            m = me[s].reindex(idx)
            oi = np.log(m.oi); f["oi_z30"] = (oi - oi.rolling(30).mean()) / oi.rolling(30).std(); f["oi_d1"] = oi.diff(); f["oi_d7"] = oi.diff(7)
            f["oi_to_vol"] = np.log(m.oi / k.quote_volume.reindex(idx).rolling(7).mean())
            f["top_ls_acct"] = np.log(m.top_ls_acct); f["top_ls_pos"] = np.log(m.top_ls_pos); f["global_ls"] = np.log(m.global_ls); f["taker_ls"] = np.log(m.taker_ls)
            f["ls_z"] = (f.global_ls - f.global_ls.rolling(60).mean()) / f.global_ls.rolling(60).std()
            f["oi_intraday"] = m.oi_intraday_range
            # crowding interactions: leverage build-up that leans one way, scaled by current texture
            f["long_crowd"] = f.oi_z30.clip(lower=0) * (f.get("fund_z", 0).clip(lower=0) + f.ls_z.clip(lower=0))
            f["short_crowd"] = f.oi_z30.clip(lower=0) * ((-f.get("fund_z", 0)).clip(lower=0) + (-f.ls_z).clip(lower=0))
        for kk in K:
            f[f"y_long_{int(kk*100)}"] = (down[s].shift(-1) <= np.log(1 - kk)).astype(float).where(down[s].shift(-1).notna())
            f[f"y_short_{int(kk*100)}"] = (up[s].shift(-1) >= np.log(1 + kk)).astype(float).where(up[s].shift(-1).notna())
        f["sym"] = s; rows.append(f)
    D = pd.concat(rows); D.index.name = "Date"
    return D.reset_index()

TEX = ["v1", "v7", "v30", "ret1", "ret7", "dd30", "ru30", "b_v7", "b_ret1"]
CONT = ["mkt_dw10", "mkt_dw05", "mkt_uw10", "mkt_dw10_3d"]
POS = ["fund1", "fund3", "fund_z", "oi_z30", "oi_d1", "oi_d7", "oi_to_vol", "top_ls_acct", "top_ls_pos", "global_ls", "taker_ls", "ls_z", "oi_intraday", "long_crowd", "short_crowd"]

def walk(D, cols, y, kind="logit"):
    pred = np.full(len(D), np.nan)
    for ms in pd.date_range(TEST_START, D.Date.max(), freq="MS"):
        te = np.where((D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)))[0]
        tr = D[(D.Date < ms - pd.Timedelta(days=1))].dropna(subset=cols + [y])
        if tr[y].sum() < 30 or not len(te): continue
        m = (make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=4000)) if kind == "logit"
             else HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=200, l2_regularization=1.0, random_state=0))
        m.fit(tr[cols], tr[y]); X = D.loc[te, cols]; ok = X.notna().all(1).values
        if ok.any(): pred[te[ok]] = m.predict_proba(X[ok])[:, 1]
    return pred

def textbook(D, kk, side):
    sd = np.exp(D.atr14) / 1.6; b = -np.log(1 - kk) if side == "long" else np.log(1 + kk)
    return np.clip(2 * (1 - norm.cdf(b / sd)), 1e-4, 0.9999)

def boot(D, ok, e_a, e_b, n=2000):
    mo = D.Date.values[ok].astype("datetime64[M]"); g = pd.Series(e_a - e_b).groupby(mo).sum()
    rng = np.random.default_rng(0); b = [g.values[rng.integers(0, len(g), len(g))].sum() for _ in range(n)]
    return float(np.mean(np.array(b) > 0))

if __name__ == "__main__":
    kl, fu, me = load(); D = build(kl, fu, me)
    D = D.dropna(subset=["v30", "atr14", "b_v7"]).reset_index(drop=True)
    print("rows", len(D), "symbols", D.sym.nunique(), D.Date.min().date(), D.Date.max().date(), flush=True)
    res = {"rows": int(len(D)), "symbols": sorted(D.sym.unique().tolist()), "test_start": str(TEST_START.date()), "end": str(D.Date.max().date()), "tests": {}}
    for side in ["long", "short"]:
        for kk in K:
            y = f"y_{side}_{int(kk*100)}"
            P = {"textbook": textbook(D, kk, side), "texture": walk(D, TEX, y), "texture+contagion": walk(D, TEX + CONT, y),
                 "texture+positioning": walk(D, TEX + POS, y), "all": walk(D, TEX + CONT + POS, y), "all_boosted": walk(D, TEX + CONT + POS, y, "hgb")}
            Y = D[y].values; ok = (D.Date >= TEST_START).values & ~np.isnan(Y)
            for v in P.values(): ok &= ~np.isnan(v)
            ref = brier_score_loss(Y[ok], P["textbook"][ok]); r = {"n": int(ok.sum()), "base_rate": float(Y[ok].mean())}
            for nm, p in P.items():
                r[nm] = {"brier": float(brier_score_loss(Y[ok], p[ok])), "skill_vs_textbook": float(1 - brier_score_loss(Y[ok], p[ok]) / ref), "auc": float(roc_auc_score(Y[ok], p[ok]))}
            e = {nm: (Y[ok] - p[ok]) ** 2 for nm, p in P.items()}
            r["positioning_beats_texture_boot"] = boot(D, ok, e["texture"], e["texture+positioning"])
            r["all_beats_texture_boot"] = boot(D, ok, e["texture"], e["all"])
            r["boosted_beats_logit_all_boot"] = boot(D, ok, e["all"], e["all_boosted"])
            # calibration of the best logit model
            q = pd.qcut(P["all"][ok], 10, labels=False, duplicates="drop")
            r["calibration_all"] = pd.DataFrame({"q": q, "p": P["all"][ok], "y": Y[ok]}).groupby("q").mean()[["p", "y"]].round(4).values.tolist()
            res["tests"][f"{side}_{int(kk*100)}"] = r
            print(f"\n{side} wick >= {int(kk*100)}%  n={r['n']} base={r['base_rate']:.3f}", flush=True)
            for nm in P: print("  %-22s skill vs textbook %+.4f  AUC %.4f" % (nm, r[nm]["skill_vs_textbook"], r[nm]["auc"]))
            print("  positioning beats texture in %.0f%% of month-bootstraps; all features %.0f%%; boosted vs logit %.0f%%" % (100 * r["positioning_beats_texture_boot"], 100 * r["all_beats_texture_boot"], 100 * r["boosted_beats_logit_all_boot"]), flush=True)
    # direction check: are crowding coefficients signed as the cascade story predicts? (full-sample logit, standardized)
    signs = {}
    for side in ["long", "short"]:
        y = f"y_{side}_10"; d = D.dropna(subset=TEX + POS + [y])
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=4000)).fit(d[TEX + POS], d[y])
        coef = dict(zip(TEX + POS, m[-1].coef_[0])); signs[side] = {c: float(coef[c]) for c in ["long_crowd", "short_crowd", "fund_z", "ls_z", "oi_z30", "oi_d1"]}
    res["coefficients_10pct"] = signs; print("\ncrowding coefficients (10% wicks):", json.dumps(signs, indent=1))
    json.dump(res, open(OUT / "results.json", "w"), indent=1)
    L = [f"# Cascade-adjusted wick odds", f"{res['rows']} coin-days, {len(res['symbols'])} perpetuals, test {res['test_start']} to {res['end']} (walk-forward, monthly refit).", "",
         "| Test | Base rate | Textbook AUC | Texture skill | +Positioning skill | All skill | All boosted skill | Positioning > texture (bootstrap) |", "|---|---|---|---|---|---|---|---|"]
    for t, r in res["tests"].items():
        L.append(f"| {t} | {r['base_rate']:.3f} | {r['textbook']['auc']:.3f} | {r['texture']['skill_vs_textbook']:+.3f} | {r['texture+positioning']['skill_vs_textbook']:+.3f} | {r['all']['skill_vs_textbook']:+.3f} | {r['all_boosted']['skill_vs_textbook']:+.3f} | {100*r['positioning_beats_texture_boot']:.0f}% |")
    L += ["", "Skill = 1 - Brier/Brier(textbook ATR random-walk model). Crowding coefficients (standardized, 10% wicks):", "```", json.dumps(signs, indent=1), "```"]
    (OUT / "report.md").write_text("\n".join(L)); print("\n".join(L))
