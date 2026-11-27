"""Build the Ghostlyne energy Observatory (R4) from actual validated findings only.
Usage: build_observatory4.py R4.json out.html histdir"""
import json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import universe4 as U

HYP = {
 "HH_SPOT": "Gas plants usually set the marginal price of Texas power.", "DD_DFW": "Heating and cooling demand in North Texas.",
 "DD_IAH": "Cooling demand in Houston, linked to North through the shared grid.", "LOAD_ERCO": "Demand moves up the supply stack to costlier plants.",
 "LOADFC_ERCO": "The day-ahead market prices the expected demand.", "WIND_ERCO": "Zero-cost wind displaces gas on the margin.",
 "SOLAR_ERCO": "Solar shifts the shape and level of daily prices.", "GASGEN_ERCO": "More gas on the margin when demand is high or renewables are low.",
 "NUC_ERCO": "Nuclear outages remove baseload supply.", "STORAGE_SURPRISE": "Storage builds and draws reveal the gas balance.",
 "CL=F": "Oil and gas share macro and substitution drivers.", "BZ=F": "Global energy price level.", "TTF=F": "European gas pulls US LNG exports, tightening US gas.",
 "LNG": "LNG export economics link US gas to world prices.", "LOAD_PJM": "Eastern power demand burns gas from the same national market.",
 "LOAD_MISO": "Neighbouring demand and shared weather systems.", "LOAD_SWPP": "Neighbouring demand and shared weather systems.",
 "WIND_SWPP": "Shared wind regime with West Texas.", "DD_PHL": "Eastern heating demand draws on national gas supply.", "DD_BOS": "New England winter gas demand.",
 "HG=F": "Industrial activity and the broad commodity cycle.", "CAD=X": "Canadian gas trade and commodity-currency moves.", "MXN=X": "Pipeline exports from Texas to Mexico.",
 "XLU": "Utility equities price expected power demand and rates.", "VST": "A Texas generator's equity reflects Texas power margins.", "BDRY": "Global industrial freight and commodity demand.",
 "NINO34": "Pacific temperatures shift Texas weather regimes.", "ZC=F": "The broad commodity cycle; ethanol and farm load.",
 "BTC-USD": "Bitcoin miners in Texas are a large flexible load that curtails when power is expensive.", "MARA": "Miner economics track Bitcoin and power costs.",
 "RIOT": "A large Texas miner whose load responds to ERCOT prices.", "NVDA": "The AI build-out and data-centre demand expectations.", "SOXX": "The chip cycle and data-centre build-out.",
 "DLR": "Data-centre operators' power costs and demand.", "EQIX": "Data-centre operators' power costs and demand.",
}

def ci(r, n):
    z = np.arctanh(np.clip(r, -0.999, 0.999)); h = 1.96 / np.sqrt(max(n - 3, 1)); return [round(float(np.tanh(z - h)), 3), round(float(np.tanh(z + h)), 3)]

def name(k):
    if k in U.FOCAL: return U.FOCAL[k]["name"]
    return U.EXTERNALS.get(k, {}).get("name", k)

def build(res, out, histdir):
    asof = min(res["inventory"][k]["last"] for k in ("ERCOT_N_DA", "HH_SPOT") if k in res["inventory"])
    fixd = lambda d: d if d <= asof else asof
    pred = {(p["focal"], p["external"], p["family"], p["lag"]): p for p in res.get("predictive", [])}
    rels, hist = [], {}
    for v in res["validated"]:
        if U.EXTERNALS[v["external"]]["role"] != "candidate": continue
        m = v.get("monitor") or {}; key = f"{v['family']}|{v['external']}|{v['lag']}"
        if m.get("history"): hist.setdefault(v["focal"], {})[key] = [[fixd(h[0])] + list(h[1:]) for h in m["history"]]
        p = pred.get((v["focal"], v["external"], v["family"], v["lag"]))
        last = dict(m.get("latest") or {});
        if last.get("date"): last["date"] = fixd(last["date"])
        rels.append(dict(f=v["focal"], x=v["external"], fam=v["family"], lag=v["lag"], ring=v["ring"], split=v["split"], e=round(v["e_confirm"], 4), ee=round(v["e_explore"], 4),
                         ci=None if v["family"].startswith("S_") else ci(v["e_confirm"], v["n_confirm"]), q=v["q_confirm"], n=v["n_confirm"], st=m.get("state") or {}, last=last, hk=key,
                         stable=v.get("stable_E_to_C", True), pred=dict(state=p["state"], r2=p["r2_oos"], q=p["q"]) if p else None, use=v.get("relevance", ""),
                         why=U.EXTERNALS[v["external"]]["why"], hyp=HYP.get(v["external"], "No explanation proposed."), rin=v.get("r_in"), rout=v.get("r_out")))
    os.makedirs(histdir, exist_ok=True)
    for f, h in hist.items(): json.dump(h, open(os.path.join(histdir, f + ".json"), "w"), separators=(",", ":"))
    pcs = []
    for a, b in zip(res["positive_controls"]["explore"], res["positive_controls"]["confirm"]):
        pcs.append(dict(f=a["focal"], x=a["external"], sign=a["expected"], rE=a["r"], rC=b["r"], passE=a["passed"], passC=b["passed"]))
    units, val = {}, {}
    for u in res["units"]:
        if u.get("ok"): units.setdefault(u["family"], {}).setdefault(u["ring"], 0); units[u["family"]][u["ring"]] += 1
    for v in res["validated"]: val.setdefault(v["family"], {}).setdefault(v["ring"], 0); val[v["family"]][v["ring"]] += 1
    data = dict(names={k: name(k) for k in list(U.FOCAL) + list(U.EXTERNALS)}, focal={k: 1 for k in U.FOCAL}, rels=rels, pc=pcs, units=units, val=val,
                pred=res.get("predictive", []), unavailable=U.UNAVAILABLE, asof=asof, prereg="dda8c2c")
    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "observatory4_template.html")).read().replace("/*DATA*/null", json.dumps(data, separators=(",", ":"), default=float))
    open(out, "w").write(html); return len(html), len(rels)

if __name__ == "__main__":
    print(build(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]))
