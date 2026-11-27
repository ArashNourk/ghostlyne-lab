"""CP1: can public data call ERCOT's monthly coincident-peak day a day ahead, within a curtailment budget?

Input: hourly_panel.csv.gz from branch registry-r5fetch (EIA-930 ERCO demand and day-ahead demand forecast, local hour).
Usage: python cp1.py <hourly_panel.csv.gz> <out.json> [--cutoff YYYY-MM-DD]
Everything below is fixed by PREREGISTRATION_CP1.md.
"""
import json, sys, numpy as np, pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, Holiday, USMemorialDay, USLaborDay, USThanksgivingDay, nearest_workday)
from sklearn.linear_model import LogisticRegression

SEED = 20261127
EXPLORE = ("2018-07", "2023-12")          # scored exploration months (walk-forward)
CONFIRM = ("2024-01", "2026-10")          # confirmation months (last complete month in the panel)
BUDGETS = [2, 3, 4, 6]                    # mean alert days per month, calibrated on exploration
PRIMARY_K = 6
FEATS = ["x1", "x2", "x3", "x4", "x1x3", "x2x3", "win", "x2win"]

# Official ERCOT 4CP intervals (settlement), from ERCOT 4CP reports filed at the PUCT and vendor reports citing them.
OFFICIAL_4CP = {"2023-06": "2023-06-27", "2023-07": "2023-07-31", "2023-08": "2023-08-10", "2023-09": "2023-09-08",
                "2024-06": "2024-06-30", "2024-07": "2024-07-01", "2024-08": "2024-08-20", "2024-09": "2024-09-20",
                "2025-06": "2025-06-19", "2025-07": "2025-07-30", "2025-08": "2025-08-18", "2025-09": "2025-09-04",
                "2026-07": "2026-07-22", "2026-08": "2026-08-24"}

class NERC(AbstractHolidayCalendar):
    rules = [Holiday("NewYear", month=1, day=1, observance=nearest_workday), USMemorialDay,
             Holiday("July4", month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
             Holiday("Christmas", month=12, day=25, observance=nearest_workday)]

def daily(path, cutoff=None):
    h = pd.read_csv(path, usecols=["date", "he", "LOAD_ERCO", "LOADFC_ERCO"], parse_dates=["date"])
    for c in ("LOAD_ERCO", "LOADFC_ERCO"):
        h.loc[(h[c] < 15000) | (h[c] > 130000), c] = np.nan          # physically implausible for ERCOT
    if cutoff: h = h[h.date <= cutoff]
    g = h.groupby("date")
    A = g.LOAD_ERCO.max(); F = g.LOADFC_ERCO.max()
    Ah = h.loc[h.LOAD_ERCO.notna()].sort_values("LOAD_ERCO").groupby("date").tail(1).set_index("date").he
    Fh = h.loc[h.LOADFC_ERCO.notna()].sort_values("LOADFC_ERCO").groupby("date").tail(1).set_index("date").he
    d = pd.DataFrame({"A": A, "F": F, "Ah": Ah, "Fh": Fh})
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"))
    return d

def features(d, F, mode="da"):
    """mode 'da': alert issued on D-1; actuals known to D-2, forecasts for D-1 and D.
       mode 'sd': alert issued morning of D; actuals known to D-1, forecast for D."""
    d = d.copy(); d["Fx"] = F
    d["ym"] = d.index.to_period("M"); d["dim"] = d.index.days_in_month; d["dom"] = d.index.day
    lag = 2 if mode == "da" else 1
    # month-to-date reference from information available at decision time
    Aknown = d.A.shift(lag); same = d.ym.shift(lag) == d.ym
    mtdA = Aknown.where(same).groupby(d.ym).cummax()
    ref = mtdA
    if mode == "da":
        Fprev = d.Fx.shift(1).where(d.ym.shift(1) == d.ym)
        ref = pd.concat([mtdA, Fprev], axis=1).max(axis=1, skipna=True)
    # climatological reference: last year's same-month actual max, scaled by trailing load growth (info to D-lag)
    mmax = d.A.groupby(d.ym).max()
    lastyr = d.ym.map(lambda p: mmax.get(p - 12, np.nan))
    r365 = d.A.rolling(365, min_periods=300).mean().shift(lag)
    growth = r365 / r365.shift(365)
    C = lastyr * growth
    ref = ref.fillna(C)
    d["x1"] = np.log(d.Fx / ref); d["x2"] = np.log(d.Fx / C)
    d["x3"] = (d.dim - d.dom) / d.dim
    hol = NERC().holidays(d.index.min(), d.index.max())
    d["x4"] = ((d.index.dayofweek >= 5) | d.index.isin(hol)).astype(float)
    d["x1x3"] = d.x1 * d.x3; d["x2x3"] = d.x2 * d.x3
    d["win"] = d.index.month.isin([12, 1, 2]).astype(float); d["x2win"] = d.x2 * d.win
    # outcome: realised monthly peak day (operational, EIA-930)
    pk = d.A.groupby(d.ym).transform(lambda s: s.idxmax() if s.notna().any() else pd.NaT)
    d["y"] = (d.index == pk).astype(float)
    d["complete"] = d.A.groupby(d.ym).transform(lambda s: s.notna().mean()) > 0.9
    return d

def walk(d):
    """Expanding-window monthly refit; predictions for each month use only months that ended before it."""
    months = sorted(d.ym.unique()); p = pd.Series(np.nan, index=d.index)
    ok = d[FEATS].notna().all(axis=1) & d.complete
    for m in months:
        if m < pd.Period(EXPLORE[0], "M"): continue
        tr = ok & (d.ym < m); te = ok & (d.ym == m)
        if tr.sum() < 300 or d.loc[tr, "y"].sum() < 8 or te.sum() == 0: continue
        X = d.loc[tr, FEATS].values; mu, sd = X.mean(0), X.std(0) + 1e-9
        lr = LogisticRegression(C=1.0, max_iter=2000).fit((X - mu) / sd, d.loc[tr, "y"].values)
        p[te] = lr.predict_proba((d.loc[te, FEATS].values - mu) / sd)[:, 1]
    return p

def clim(d):
    """B0: peak-day frequency by weekday/weekend-holiday, from months before the scored month."""
    p = pd.Series(np.nan, index=d.index)
    for m in sorted(d.ym.unique()):
        tr = (d.ym < m) & d.complete & d.x4.notna(); te = d.ym == m
        if tr.sum() < 300: continue
        r = d.loc[tr].groupby("x4").y.mean()
        p[te] = d.loc[te, "x4"].map(r)
    return p

def inperiod(d, per):
    return (d.ym >= pd.Period(per[0], "M")) & (d.ym <= pd.Period(per[1], "M")) & d.complete

def threshold(score, d, k):
    s = score[inperiod(d, EXPLORE)].dropna(); nm = d.loc[s.index, "ym"].nunique()
    n = int(round(k * nm)); return np.sort(s.values)[::-1][min(n, len(s)) - 1]

def evaluate(score, d, tau, per, target=None):
    m = inperiod(d, per); x = d[m].copy(); x["s"] = score[m]; x["alert"] = x.s >= tau
    rows = []
    for ym, g in x.groupby("ym"):
        pkday = g.A.idxmax() if target is None else pd.Timestamp(target[str(ym)]) if str(ym) in target else None
        if pkday is None: continue
        hit = bool(g.alert.get(pkday, False))
        hr = hit and abs(g.Fh.get(pkday, np.nan) - g.Ah.get(pkday, np.nan)) <= 1
        top2 = np.sort(g.A.dropna().values)[::-1][:2]; tight = bool((top2[0] - top2[1]) / top2[0] < 0.01)
        rows.append(dict(ym=str(ym), peak=str(pkday.date()), hit=hit, hour_hit=bool(hr), alerts=int(g.alert.sum()), tight=tight, winter=int(ym.month in (12, 1, 2)), summer=int(ym.month in (6, 7, 8, 9))))
    r = pd.DataFrame(rows)
    if r.empty: return dict(n=0)
    def sub(q): return dict(n=int(len(q)), capture=float(q.hit.mean()) if len(q) else None, hour_capture=float(q.hour_hit.mean()) if len(q) else None, alerts_per_month=float(q.alerts.mean()) if len(q) else None)
    return dict(**sub(r), winter=sub(r[r.winter == 1]), summer=sub(r[r.summer == 1]), tight=sub(r[r.tight]), months=r.to_dict("records"))

def bss(pm, pb, d, per, boot=2000):
    m = inperiod(d, per) & pm.notna() & pb.notna(); x = d[m]
    em = ((pm[m] - x.y) ** 2).groupby(x.ym).sum(); eb = ((pb[m] - x.y) ** 2).groupby(x.ym).sum()
    point = 1 - em.sum() / eb.sum(); rng = np.random.default_rng(SEED); idx = np.arange(len(em)); bs = []
    for _ in range(boot):
        i = rng.choice(idx, len(idx)); bs.append(1 - em.values[i].sum() / eb.values[i].sum())
    return dict(bss=float(point), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), months=int(len(em)))

def run(path, cutoff=None):
    d0 = daily(path, cutoff); out = dict(seed=SEED, explore=EXPLORE, confirm=CONFIRM, primary_k=PRIMARY_K)
    rng = np.random.default_rng(SEED)
    # noise control: forecast shuffled within each month (keeps level, destroys day information)
    Fn = d0.F.copy(); ym = d0.index.to_period("M")
    for m in ym.unique():
        i = np.where(ym == m)[0]; Fn.iloc[i] = rng.permutation(d0.F.iloc[i].values)
    variants = {"da": (d0.F, "da"), "sd": (d0.F, "sd"), "oracle": (d0.A, "da"), "noise": (Fn, "da")}
    for name, (F, mode) in variants.items():
        d = features(d0, F, mode); pM = walk(d); pB0 = clim(d); sB1 = d.x1
        res = dict()
        for k in BUDGETS:
            tM, tB = threshold(pM, d, k), threshold(sB1, d, k)
            res[f"k{k}"] = dict(M1=dict(explore=evaluate(pM, d, tM, EXPLORE), confirm=evaluate(pM, d, tM, CONFIRM), official=evaluate(pM, d, tM, ("2023-06", CONFIRM[1]), OFFICIAL_4CP)),
                                B1=dict(explore=evaluate(sB1, d, tB, EXPLORE), confirm=evaluate(sB1, d, tB, CONFIRM), official=evaluate(sB1, d, tB, ("2023-06", CONFIRM[1]), OFFICIAL_4CP)),
                                tau=dict(M1=float(tM), B1=float(tB)))
        res["brier"] = dict(explore=bss(pM, pB0, d, EXPLORE), confirm=bss(pM, pB0, d, CONFIRM))
        out[name] = res
        if name == "da":
            # proxy validity: operational (EIA-930) monthly peak day vs official settlement 4CP day
            agree = {k: str(d.loc[d.ym == pd.Period(k, "M"), "A"].idxmax().date()) == v for k, v in OFFICIAL_4CP.items() if (d.ym == pd.Period(k, "M")).any()}
            out["proxy_vs_official"] = dict(agree=agree, rate=float(np.mean(list(agree.values()))) if agree else None)
    c = out["da"][f"k{PRIMARY_K}"]; cm, cb = c["M1"]["confirm"], c["B1"]["confirm"]
    g = dict()
    g["G1_lab_validity"] = bool(out["oracle"][f"k{PRIMARY_K}"]["M1"]["confirm"].get("capture", 0) >= 0.85 and out["noise"][f"k{PRIMARY_K}"]["M1"]["confirm"].get("capture", 1) <= 0.40)
    g["G2_skill"] = bool(out["da"]["brier"]["confirm"]["lo"] > 0)
    g["G3_capture"] = bool(cm.get("capture", 0) >= 0.85 and cm.get("alerts_per_month", 99) <= 7.0)
    g["G4_differentiation"] = bool(cm.get("capture", 0) - cb.get("capture", 0) >= 0.10 and cm.get("alerts_per_month", 99) <= cb.get("alerts_per_month", 0) + 0.5)
    out["gates"] = g
    return out

if __name__ == "__main__":
    a = sys.argv[1:]; cut = a[a.index("--cutoff") + 1] if "--cutoff" in a else None
    r = run(a[0], cut); json.dump(r, open(a[1], "w"), indent=1, default=str)
    print(json.dumps(r["gates"]))
