"""Ghostlyne R4 run (GitHub Actions): public panel + market series (research use only) -> derived statistics only."""
import io, json, os, sys, time, numpy as np, pandas as pd, requests
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here); sys.path.insert(0, os.path.join(here, "..", "r3"))
import universe4 as U, lab4
from monitor3 import fisher, behaviour

def rolling(y, x, win, ref_win, cum, start, ref):
    """Rolling rank (Spearman) strength with a 95% band, and a divergence z-score from a trailing reference fit (past data only)."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna(); hist = []
    ry = d.y.rolling(win).rank() if hasattr(d.y.rolling(win), "rank") else None
    for i in range(win, len(d)):
        t = d.index[i]
        if t < pd.Timestamp(start): continue
        w = d.iloc[i - win + 1:i + 1]; r = float(w.y.corr(w.x, method="spearman")); lo, hi = fisher(r, win); row = [str(t.date()), round(r, 3), round(lo, 3), round(hi, 3), None]
        if i >= ref_win + cum:
            tr = d.iloc[i - ref_win:i + 1].rank(); b = np.polyfit(tr.x, tr.y, 1); e = tr.y - np.polyval(b, tr.x); c = e.rolling(cum).sum().dropna()
            row[4] = round(float((c.iloc[-1] - c.mean()) / c.std()), 2)
        hist.append(row)
    if not hist: return dict(history=[], state={})
    last = hist[-1]; st = dict(correlation=behaviour(ref, last[1], win)); dz = [h[4] for h in hist if h[4] is not None]
    if dz:
        prev = dz[-5] if len(dz) > 5 else np.nan
        st["divergence"] = "diverging" if abs(dz[-1]) > 2 and abs(dz[-1]) >= abs(prev) else "converging" if abs(prev) > 2 and abs(dz[-1]) < abs(prev) else "within normal range"
    return dict(history=hist, state=st, latest=dict(date=last[0], r=last[1], lo=last[2], hi=last[3], div_z=last[4]))
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
RAW = "https://raw.githubusercontent.com/ArashNourk/ghostlyne-lab/registry-r4fetch/"

def yahoo(t):
    for a in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}", params={"period1": 1230768000, "period2": int(time.time()), "interval": "1d"}, headers=UA, timeout=60)
            r.raise_for_status(); j = r.json()["chart"]["result"][0]
            adj = j["indicators"].get("adjclose", [{}])[0].get("adjclose") or j["indicators"]["quote"][0]["close"]
            return pd.Series(adj, index=pd.to_datetime(j["timestamp"], unit="s").normalize()).dropna()
        except Exception: time.sleep(3 * (a + 1))
    raise RuntimeError(t)

def load():
    P = pd.read_csv(io.BytesIO(requests.get(RAW + "panel_daily.csv.gz", timeout=120).content), compression="gzip", index_col=0, parse_dates=True)
    st = pd.read_csv(io.StringIO(requests.get(RAW + "storage_weekly.csv", timeout=60).text), index_col=0, parse_dates=True).iloc[:, 0]
    ni = pd.read_csv(io.StringIO(requests.get(RAW + "nino_weekly.csv", timeout=60).text), index_col=0, parse_dates=True).iloc[:, 0]
    Y, miss = {}, {}
    for t in U.YAHOO:
        try: Y[t] = yahoo(t)
        except Exception as e: miss[t] = repr(e)[:100]
        time.sleep(0.3)
    return P, st, ni, Y, miss

def relevance(v):
    f = U.FOCAL[v["focal"]]
    if f["use"] == "procurement": u = "forward and procurement"
    elif v["family"].endswith("_w"): u = "short-term exposure and weekly planning"
    else: u = "short-term wholesale exposure"
    if v["focal"] in ("ERCOT_N_DART", "ERCOT_WN_BASIS"): u = "spread trading and hedging (" + u + ")"
    return u

def monitor(S, v):
    f, x, fam, L = v["focal"], v["external"], v["family"], v["lag"]; weekly = fam.endswith("_w")
    if fam.startswith("S_"): return dict(history=[], state={}, note="conditional relationship: in-regime and out-of-regime strengths shown")
    both = lab4.stationary(f) and lab4.stationary(x)
    if fam.startswith("A"): y, z = lab4.deseason(lab4.innov(f, S[f], weekly), weekly), lab4.deseason(lab4.innov(x, S[x], weekly), weekly)
    else:
        g = (lambda k: lab4.dyn(k, S[k], weekly)) if both else (lambda k: lab4.innov(k, S[k], weekly, last=True))
        y, z = lab4.deseason(g(f), weekly), lab4.deseason(g(x), weekly)
        if L > 0: z = z.shift(L)
        else: y = y.shift(-L)
    start = "2019-01-01" if v["split"] == "early" else "2022-01-01"
    out = rolling(y.rank() if False else y, z, 104 if weekly else 365, 104 if weekly else 730, 4 if weekly else 20, start, v["e_confirm"])
    H = out.get("history", []); step = 1 if weekly else 7; out["history"] = H[::step] + ([H[-1]] if H and (len(H) - 1) % step else [])
    return out

if __name__ == "__main__":
    P, st, ni, Y, miss = load(); S = lab4.build(P, st, ni, Y)
    pcE, pcC = lab4.positive_controls(S, "E"), lab4.positive_controls(S, "C")
    pairs = lab4.pairs_of(S); scar = lab4.scarcity_flag(S["ERCOT_N_RT"]) if "ERCOT_N_RT" in S else pd.Series(dtype=float)
    T = lab4.tests(S, pairs, scar); ex, conf = lab4.screen_confirm(T); conf = lab4.uri_check(S, conf) if len(conf) else conf
    Pd = lab4.predictive(S, conf) if len(conf) else pd.DataFrame()
    val = conf[conf.state == "Validated"].to_dict("records") if len(conf) else []
    for v in val: v["monitor"] = monitor(S, v); v["relevance"] = relevance(v); v["stable_E_to_C"] = bool(abs(np.arctanh(np.clip(v["e_confirm"], -.99, .99)) - np.arctanh(np.clip(v["e_explore"], -.99, .99))) < 1.96 * np.sqrt(2 / max(v["n_confirm"] - 3, 1)))
    allu = T[T.win == "E"].sort_values("p").drop_duplicates(["focal", "external", "family"])
    qmap = ex.sort_values("p").drop_duplicates(["focal", "external", "family"])[["focal", "external", "family", "q"]]
    units = allu[["focal", "external", "ring", "role", "family", "lag", "split", "r", "p", "n", "ok"]].merge(qmap, how="left")
    inv = {k: dict(first=str(v.index.min().date()), last=str(v.index.max().date()), n=int(len(v))) for k, v in S.items()}
    res = dict(meta=dict(run="R4", generated=pd.Timestamp.now("UTC").isoformat(), missing=miss, n_tests=int(len(T)), n_units=int(len(units)),
                         candidates=conf.groupby("family").size().to_dict() if len(conf) else {}, validated=conf[conf.state == "Validated"].groupby("family").size().to_dict() if len(conf) else {}),
               positive_controls=dict(explore=pcE, confirm=pcC), inventory=inv, confirm=conf.to_dict("records") if len(conf) else [], validated=val,
               predictive=Pd.to_dict("records") if len(Pd) else [], units=units.round(5).to_dict("records"))
    os.makedirs("out", exist_ok=True)
    json.dump(res, open("out/R4.json", "w"), default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else (None if o is pd.NaT else str(o))))
    print(json.dumps(res["meta"], default=str)[:3000])
