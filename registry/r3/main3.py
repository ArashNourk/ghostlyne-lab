"""Ghostlyne R3: fetch in GitHub Actions, analyse, publish derived statistics only."""
import json, os, re, sys, time, numpy as np, pandas as pd, requests
sys.path.insert(0, os.path.dirname(__file__))
import universe as U, lab3, monitor3
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}

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

def revenue():
    codes = {k: k.split("_")[1] for k in U.REVENUE}; out = {k: {} for k in codes}
    for y in range(2013, 2027):
        for m in range(1, 13):
            if pd.Timestamp(y, m, 1) > pd.Timestamp.now() - pd.DateOffset(months=1): break
            try:
                r = requests.get(f"https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{y-1911}_{m}_0.html", headers=UA, timeout=60); r.encoding = "big5"
                for k, c in codes.items():
                    g = re.search(r">\s*" + c + r"\s*</td>\s*<td[^>]*>[^<]*</td>\s*<td[^>]*>\s*([\d,]+)", r.text)
                    if g: out[k][pd.Timestamp(y, m, 28)] = float(g.group(1).replace(",", ""))
            except Exception: pass
            time.sleep(0.5)
    return {k: pd.Series(v).sort_index() for k, v in out.items() if v}

def synthetic(S):
    idx = pd.bdate_range("2005-01-03", "2026-12-31")
    for k, sd in {"SYN_1": 11, "SYN_2": 22, "SYN_3": 33}.items():
        r = np.random.default_rng(sd); S[k] = pd.Series(100 * np.exp(np.cumsum(r.standard_t(4, len(idx)) * 0.012)), idx)
    return S

def fetch():
    S, miss = {}, {}
    for t in list(U.FOCAL) + [k for k in U.EXTERNALS if not k.startswith(("SYN", "NINO"))]:
        try: S[t] = yahoo(t)
        except Exception as e: miss[t] = repr(e)[:100]
        time.sleep(0.3)
    try: S["NINO34_W"] = nino()
    except Exception as e: miss["NINO34_W"] = repr(e)[:100]
    S.update(revenue()); return S, miss

def analyse(S, miss):
    S = synthetic(dict(S))
    T, ex, conf, CH, D = lab3.run(S, U)
    P = lab3.predictive(D, conf) if len(conf) else pd.DataFrame()
    val = conf[conf.state == "Validated"].to_dict("records") if len(conf) else []
    for v in val: v["monitor"] = monitor3.monitor(D, v)
    units = ex.sort_values("p").drop_duplicates(["focal", "external", "family", "dir"])
    allunits = T[T.win == "E"].sort_values("p").drop_duplicates(["focal", "external", "family", "dir"])
    inv = {k: dict(first=str(v.index.min().date()), last=str(v.index.max().date()), n=int(len(v))) for k, v in S.items() if len(v)}
    for c in CH:
        if c.get("state") == "Validated":
            x, m, y = c["chain"]; RM = D["RM"]; d = pd.concat([RM[x], RM[m], RM[y]], axis=1).dropna(); hist = []
            for i in range(60, len(d), 3):
                w = d.iloc[i - 60:i]; a = np.polyfit(w.iloc[:, 0], w.iloc[:, 1], 1)[0]; Z = np.column_stack([np.ones(60), w.iloc[:, 1], w.iloc[:, 0]]); b = np.linalg.lstsq(Z, w.iloc[:, 2], rcond=None)[0][1]
                hist.append([str(d.index[i - 1].to_timestamp().date()), round(float(a * b * w.iloc[:, 0].std() / w.iloc[:, 2].std()), 3)])
            c["history"] = hist
    summ = T[T.win == "E"].groupby(["family", "ring"]).agg(tests=("p", "size"), usable=("ok", "sum")).reset_index().to_dict("records")
    return dict(meta=dict(run="R3", generated=pd.Timestamp.now("UTC").isoformat(), missing=miss, tests=summ,
                          candidates=conf.groupby("family").size().to_dict() if len(conf) else {},
                          validated=conf[conf.state == "Validated"].groupby("family").size().to_dict() if len(conf) else {}),
                inventory=inv, confirm=conf.to_dict("records") if len(conf) else [], validated=val, chains=CH,
                predictive=P.to_dict("records") if len(P) else [],
                units=allunits[["focal", "external", "ring", "role", "family", "lag", "dir", "r", "p", "n", "ok"]].merge(units[["focal", "external", "family", "dir", "q"]], how="left").round(5).to_dict("records"))

if __name__ == "__main__":
    S, miss = fetch(); res = analyse(S, miss); os.makedirs("out", exist_ok=True)
    json.dump(res, open("out/R3.json", "w"), default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (None if o is pd.NaT else str(o)))
    print(json.dumps(res["meta"], default=str)[:3000])
