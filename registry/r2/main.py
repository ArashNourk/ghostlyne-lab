"""Ghostlyne R2: fetch (in GitHub Actions), analyse, write derived results only (no raw prices are published)."""
import json, os, re, sys, time, numpy as np, pandas as pd, requests
import universe as U, lab, monitor
from lab import CFG, hac_corr, bh, eid

UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
SEEDS = {"SYN_1": 11, "SYN_2": 22, "SYN_3": 33}

def yahoo(t):
    for a in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}", params={"period1": 946684800, "period2": int(time.time()), "interval": "1d"}, headers=UA, timeout=60)
            r.raise_for_status(); j = r.json()["chart"]["result"][0]
            adj = j["indicators"].get("adjclose", [{}])[0].get("adjclose") or j["indicators"]["quote"][0]["close"]
            return pd.Series(adj, index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna()
        except Exception: time.sleep(3 * (a + 1))
    raise RuntimeError("yahoo failed")

def nino():
    r = requests.get("https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for", headers=UA, timeout=60); rows = {}
    for line in r.text.splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})", line); nums = re.findall(r"-?\d+\.\d", line[10:])
        if m and len(nums) >= 8: rows[pd.to_datetime(m.group(1), format="%d%b%Y")] = float(nums[5])
    return pd.Series(rows)

def mops_revenue():
    out = {k: {} for k in U.FOCAL_MONTHLY}
    for y in range(2013, 2027):
        for m in range(1, 13):
            if pd.Timestamp(y, m, 1) > pd.Timestamp.now() - pd.DateOffset(months=1): break
            try:
                r = requests.get(f"https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{y-1911}_{m}_0.html", headers=UA, timeout=60); r.encoding = "big5"
                for k, v in U.FOCAL_MONTHLY.items():
                    g = re.search(r">\s*" + v["code"] + r"\s*</td>\s*<td[^>]*>[^<]*</td>\s*<td[^>]*>\s*([\d,]+)", r.text)
                    if g: out[k][pd.Timestamp(y, m, 1)] = float(g.group(1).replace(",", ""))
            except Exception: pass
            time.sleep(0.6)
    return {k: pd.Series(v).sort_index() for k, v in out.items()}

def fetch():
    S, miss = {}, {}
    for t in list(U.FOCAL) + [U.MARKET] + [k for k in U.EXTERNALS if not k.startswith(("SYN", "NINO"))]:
        try: S[t] = yahoo(t)
        except Exception as e: miss[t] = repr(e)[:120]
        time.sleep(0.3)
    try: S["NINO34_W"] = nino()
    except Exception as e: miss["NINO34_W"] = repr(e)[:120]
    return S, mops_revenue(), miss

def add_synthetic(S):
    idx = pd.bdate_range("2005-01-03", "2026-12-31")
    for k, sd in SEEDS.items():
        r = np.random.default_rng(sd); S[k] = pd.Series(100 * np.exp(np.cumsum(r.standard_t(4, len(idx)) * 0.012)), idx)
    return S

def monthly_track(Mrev, S):
    """Memory revenue (deseasonalised monthly log change) vs monthly log change of each external: A_total and B lead-lag (+/-1..6)."""
    E, C = ("2013-01-01", "2019-12-31"), ("2020-01-01", None); rows = []
    ext = {k: (np.log(S[k].resample("MS").last()).diff() if v["transform"] == "dlog" else S[k].resample("MS").last().diff()) for k, v in U.EXTERNALS.items() if k in S}
    for f, s in Mrev.items():
        if len(s) < 100: continue
        y = np.log(s).diff()
        for x, z in ext.items():
            for L in [0] + [s_ * k for k in range(1, 7) for s_ in (1, -1)]:
                fam = "A_total" if L == 0 else "B_leadlag"
                for wn, W in (("E", E), ("C", C)):
                    a, b = lab.window(y, W), lab.window(z, W)
                    a = a - a.groupby(a.index.month).transform("mean")  # remove the seasonal pattern within the window
                    zz = b.shift(L) if L > 0 else b; aa = a.shift(-L) if L < 0 else a
                    r, se, p, n = hac_corr(aa, zz, 3)
                    rows.append(dict(focal=f, external=x, ring=U.EXTERNALS[x]["ring"], family=fam, lag=L, win=wn, r=r, p=p, n=n))
    T = pd.DataFrame(rows); ex = T[(T.win == "E") & T.p.notna() & (T.n >= 72)].copy()
    ex["q"] = ex.groupby(["family", "ring"]).p.transform(lambda s: pd.Series(bh(s.values), index=s.index))
    cand = ex[ex.q <= CFG["q_explore"]].sort_values("p").drop_duplicates(["focal", "external", "family"])
    cf = T[T.win == "C"].set_index(["focal", "external", "family", "lag"]); out = []
    rows = [(c, cf.loc[(c.focal, c.external, c.family, c.lag)]) for _, c in cand.iterrows()]
    for (c, k), q in zip(rows, bh([k.p for _, k in rows])):
        ok = q <= CFG["q_confirm"] and np.sign(k.r) == np.sign(c.r) and k.n >= 60
        out.append(dict(focal=c.focal, external=c.external, ring=int(c.ring), family=c.family, lag=int(c.lag), r_explore=float(c.r), q_explore=float(c.q),
                        r_confirm=float(k.r), p_confirm=float(k.p), q_confirm=float(q), n_confirm=int(k.n), state="Validated" if ok else "Not Detected"))
    best = ex.sort_values("p").drop_duplicates(["focal", "external", "family"])
    return dict(tests=int(len(ex)), candidates=int(len(cand)), confirm=out,
                units=best[["focal", "external", "ring", "family", "lag", "r", "p", "q", "n"]].round(4).to_dict("records"),
                coverage={k: dict(first=str(v.index.min().date()), last=str(v.index.max().date()), n=int(len(v))) for k, v in Mrev.items() if len(v)})

def analyse(S, Mrev, miss):
    S = add_synthetic(dict(S)); uni = dict(focal=U.FOCAL, externals=U.EXTERNALS)
    T, ex, conf = lab.run(S, uni)
    valB = conf[(conf.family == "B_leadlag") & (conf.state == "Validated")] if len(conf) else conf
    P = lab.predictive(S, uni, valB) if len(valB) else pd.DataFrame()
    R = {k: lab.weekly_returns(s, U.EXTERNALS.get(k, {}).get("transform", "dlog")) for k, s in S.items()}; M = R[U.MARKET]
    val = conf[conf.state == "Validated"].to_dict("records") if len(conf) else []
    for v in val: v["monitor"] = monitor.monitor(R, M, v) if v["family"] != "S_stress" else dict(history=[], state=None, note="no monitoring definition registered yet for conditional relationships")
    pairs = [(f, x) for f in U.FOCAL for x in U.EXTERNALS if f in R and x in R]
    events, final = monitor.replay(R, M, pairs, {p: U.EXTERNALS[p[1]]["ring"] for p in pairs}, ["2021-12-31", "2022-12-30", "2023-12-29", "2024-12-27", "2025-12-26", str(M.index.max().date())])
    # one registry unit per focal x external x family: exploration summary (best lag for B)
    units = ex.sort_values("p").drop_duplicates(["focal", "external", "family"]).copy()
    insuff = T[T.state == "Insufficient Data"] if "state" in T else T.iloc[0:0]
    mt = monthly_track(Mrev, S) if any(len(v) for v in Mrev.values()) else None
    inv = {k: dict(first=str(v.index.min().date()), last=str(v.index.max().date()), weeks=int(v.resample("W-FRI").last().notna().sum())) for k, v in S.items()}
    return dict(meta=dict(run="R2", generated=pd.Timestamp.now("UTC").isoformat(), cfg={k: v for k, v in CFG.items()}, missing=miss,
                          tests_explore=ex.groupby("family").size().to_dict(), candidates=conf.groupby("family").size().to_dict() if len(conf) else {},
                          validated=conf[conf.state == "Validated"].groupby("family").size().to_dict() if len(conf) else {}),
                inventory=inv, units=units[["focal", "external", "ring", "role", "family", "lag", "r", "p", "q", "n"]].round(4).to_dict("records"),
                insufficient=insuff[["focal", "external", "reason"]].to_dict("records") if len(insuff) else [],
                confirm=conf.drop(columns=[c for c in ("extra",) if c in conf]).to_dict("records") if len(conf) else [], validated=val,
                predictive=P.to_dict("records") if len(P) else [], replay=dict(events=events, final={f"{a}|{b}": s for (a, b), s in final.items() if s != "Not Detected"}),
                monthly=mt)

if __name__ == "__main__":
    S, Mrev, miss = fetch()
    res = analyse(S, Mrev, miss)
    os.makedirs("out", exist_ok=True)
    json.dump(res, open("out/R2.json", "w"), default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
    print(json.dumps(res["meta"], default=str))
