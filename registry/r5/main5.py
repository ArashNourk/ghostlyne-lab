"""Ghostlyne R5 run (GitHub Actions). Public hourly panel + R4 public daily panel + on-chain hashprice + market series (research use only).
Publishes derived statistics only."""
import io, json, os, sys, time, numpy as np, pandas as pd, requests
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here); sys.path.insert(0, os.path.join(here, "..", "r4"))
import lab5
RAW = "https://raw.githubusercontent.com/ArashNourk/ghostlyne-lab/"
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
YAHOO = ["TTF=F", "CL=F", "LNG", "NG=F", "HG=F", "CAD=X", "MXN=X", "XLU", "VST", "BDRY", "ZC=F", "BTC-USD", "MARA", "RIOT", "NVDA", "SOXX", "DLR", "EQIX"]

def yahoo(t):
    for a in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}", params={"period1": 1420070400, "period2": int(time.time()), "interval": "1d"}, headers=UA, timeout=60)
            r.raise_for_status(); j = r.json()["chart"]["result"][0]
            adj = j["indicators"].get("adjclose", [{}])[0].get("adjclose") or j["indicators"]["quote"][0]["close"]
            return pd.Series(adj, index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna()
        except Exception: time.sleep(3 * (a + 1))
    raise RuntimeError(t)

def load():
    g = lambda br, f: requests.get(RAW + br + "/" + f, timeout=300).content
    H = pd.read_csv(io.BytesIO(g("registry-r5fetch", "hourly_panel.csv.gz")), compression="gzip", parse_dates=["date"]).set_index(["date", "he"])
    hp = pd.read_csv(io.BytesIO(g("registry-r5fetch", "hashprice_daily.csv")), index_col=0, parse_dates=True)["HASHPRICE"]
    d4 = pd.read_csv(io.BytesIO(g("registry-r4fetch", "panel_daily.csv.gz")), compression="gzip", index_col=0, parse_dates=True)
    st = pd.read_csv(io.BytesIO(g("registry-r4fetch", "storage_weekly.csv")), index_col=0, parse_dates=True).iloc[:, 0]
    ni = pd.read_csv(io.BytesIO(g("registry-r4fetch", "nino_weekly.csv")), index_col=0, parse_dates=True).iloc[:, 0]
    ch = st.diff(); woy = ch.index.isocalendar().week.values
    norm = pd.Series([ch[(woy == w) & (ch.index < t) & (ch.index >= t - pd.DateOffset(years=5))].mean() for t, w in zip(ch.index, woy)], index=ch.index)
    sur = (ch - norm).dropna(); sur.index = sur.index + pd.Timedelta(days=6)   # released Thursday after the week ending Friday
    ni.index = ni.index + pd.Timedelta(days=5)                                   # Wednesday-centred week, published the following Monday
    Y, miss = {}, {}
    for t in YAHOO:
        try: Y[t] = yahoo(t)
        except Exception as e: miss[t] = repr(e)[:100]
        time.sleep(0.3)
    return H, d4, hp, Y, sur, ni, miss

def stress_subset(D, F, base, G, rows):
    """Secondary (pre-registered, not a gate): decision value on high net-load-forecast days (top 20% by trailing distribution)."""
    nl = F["b_netload_fc"]; thr = nl.rolling(365, min_periods=200).quantile(0.8).shift(2); flag = (nl > thr)
    out = []
    for _, r in rows[(rows.window == "C") & rows.candidate].iterrows():
        a, b = lab5.CONFIRM; pb = lab5.walk(D, F, base, r.decision, a, b); pa = lab5.walk(D, F, base + G[r.group], r.decision, a, b)
        d, _ = lab5.value(D, r.decision, pb, pa); d = d[flag.reindex(d.index).fillna(False).values]
        if len(d) > 30: m, lo, hi, p = lab5.block_boot(d.values); out.append(dict(decision=r.decision, group=r.group, n_days=len(d), mean_gain=m, ci_lo=lo, ci_hi=hi, p_one_sided=p))
    return out

def sensitivity(D, F, base, G, rows, c=3.0):
    old = lab5.C_RT; lab5.C_RT = c; out = []
    for _, r in rows[(rows.window == "C") & rows.candidate & (rows.decision != "spike")].iterrows():
        a, b = lab5.CONFIRM; pb = lab5.walk(D, F, base, r.decision, a, b); pa = lab5.walk(D, F, base + G[r.group], r.decision, a, b)
        d, _ = lab5.value(D, r.decision, pb, pa); m, lo, hi, p = lab5.block_boot(d.values); out.append(dict(decision=r.decision, group=r.group, friction=c, mean_gain=m, ci_lo=lo, ci_hi=hi, p_one_sided=p))
    lab5.C_RT = old; return out

if __name__ == "__main__":
    H, d4, hp, Y, sur, ni, miss = load()
    D, F, base, G = lab5.build(H, d4, hp, Y, sur, ni)
    R, P = lab5.run(D, F, base, G)
    res = dict(meta=dict(run="R5", generated=pd.Timestamp.now("UTC").isoformat(), missing=miss, baseline_features=base, groups=G,
                         spike_rate_explore=float(D.SPIKE[(D.index >= lab5.EXPLORE[0]) & (D.index <= lab5.EXPLORE[1])].mean()),
                         spike_rate_confirm=float(D.SPIKE[D.index >= lab5.CONFIRM[0]].mean()), last_day=str(D.dropna(subset=["DA_N", "RT_N"]).index.max().date())),
               results=R.to_dict("records"), stress=stress_subset(D, F, base, G, R), sensitivity=sensitivity(D, F, base, G, R),
               feature_coverage={c: dict(first=str(F[c].first_valid_index().date()) if F[c].notna().any() else None, n=int(F[c].notna().sum())) for c in F.columns})
    os.makedirs("out", exist_ok=True)
    json.dump(res, open("out/R5.json", "w"), default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else str(o)))
    print(json.dumps(res["meta"], default=str)[:2000])
