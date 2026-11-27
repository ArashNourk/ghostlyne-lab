"""Build the Ghostlyne Observatory (R3) from real results only. Usage: build_observatory3.py results.json out.html"""
import json, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import universe as U

HYP = {
 "HG=F": "industrial and power-infrastructure demand", "ALI=F": "industrial demand and hardware costs", "SI=F": "industrial and electronics demand",
 "PA=F": "electronics materials and the industrial cycle", "LIN": "industrial production, including fabs", "REMX": "strategic-metals and electronics demand",
 "ALB": "battery and energy-storage demand", "BZ=F": "global growth and energy costs", "CL=F": "global growth and energy costs", "NG=F": "power costs and the energy cycle",
 "URA": "power demand, including data-centre load", "XLU": "defensive-versus-growth rotation and power demand", "BHP": "the global industrial and commodity cycle",
 "FCX": "copper demand from power and electrification", "IVN.TO": "copper supply and demand from electrification", "FM.TO": "copper supply and demand from electrification",
 "1919.HK": "the Asian trade and electronics shipment cycle", "MAERSK-B.CO": "the global trade cycle", "2603.TW": "the Asian electronics shipment cycle and Taiwan market",
 "2609.TW": "the Asian electronics shipment cycle and Taiwan market", "1308.HK": "intra-Asia trade in components", "FDX": "air shipments of high-value electronics",
 "CAT": "construction and capital spending, including data centres", "KRW=X": "Asian export competitiveness and dollar liquidity", "TWD=X": "Taiwan export competitiveness and capital flows",
 "JPY=X": "dollar strength and risk appetite", "CNY=X": "Chinese demand and dollar strength", "NINO34_W": "weather-driven water and power conditions in Asia",
 "BTC-USD": "risk appetite and competing demand for GPUs and power", "ZC=F": "the broad commodity cycle (no direct pathway established)", "TM": "competing chip demand and the manufacturing cycle",
}

def ci(r, n):
    z = np.arctanh(np.clip(r, -0.999, 0.999)); h = 1.96 / np.sqrt(max(n - 3, 1)); return [round(float(np.tanh(z - h)), 3), round(float(np.tanh(z + h)), 3)]

def name(k):
    if k in U.FOCAL: return U.FOCAL[k]["name"]
    if k in U.REVENUE: return U.REVENUE[k]["name"]
    return U.EXTERNALS.get(k, {}).get("name", k)

def build(res, out, histdir=None):
    asof = max(v["last"] for k, v in res["inventory"].items() if k in U.FOCAL)
    fixd = lambda d: d if d <= asof else asof
    pred = {(p["focal"], p["external"], p["family"], p["lag"]): p for p in res.get("predictive", [])}
    rels = []
    for v in res["validated"]:
        m = v.get("monitor") or {}; H = m.get("history") or []
        step = 2 if v["family"] in ("A_w",) else 1; H = H[::step] + ([H[-1]] if H and (len(H) - 1) % step else [])
        fam = v["family"]; seg = (U.FOCAL.get(v["focal"]) or U.REVENUE.get(v["focal"]))["segment"]
        p = pred.get((v["focal"], v["external"], fam, v["lag"]))
        rels.append(dict(f=v["focal"], x=v["external"], fam=fam, lag=v["lag"], dir=v.get("dir", ""), ring=v["ring"], seg=seg,
                         e=round(v["e_confirm"], 4), ee=round(v["e_explore"], 4), ci=ci(v["e_confirm"], v["n_confirm"]) if fam != "X_shock" else None,
                         q=v["q_confirm"], n=v["n_confirm"], ev=v.get("events", 0), st=m.get("state") or {}, last=dict(m.get("latest") or {}, date=fixd((m.get("latest") or {}).get("date", asof))),
                         hk=f"{fam}|{v['external']}|{v['lag']}|{v.get('dir','')}", lag_now=m.get("lag") or {}, shocks=m.get("shocks") or [],
                         pred=dict(state=p["state"], r2=round(p["r2_oos"], 4), q=p["q"]) if p else None,
                         why=U.EXTERNALS[v["external"]]["why"], hyp=HYP.get(v["external"], "no explanation proposed"), role=U.EXTERNALS[v["external"]]["role"]))
    hist = {}
    for v in res["validated"]:
        m = v.get("monitor") or {}; H = m.get("history") or []; step = 4 if v["family"] == "A_w" else 1
        H = H[::step] + ([H[-1]] if H and (len(H) - 1) % step else [])
        H = [[fixd(h[0])] + list(h[1:]) for h in H]
        hist.setdefault(v["focal"], {})[f"{v['family']}|{v['external']}|{v['lag']}|{v.get('dir','')}"] = H
    if histdir:
        os.makedirs(histdir, exist_ok=True)
        for f, h in hist.items(): json.dump(h, open(os.path.join(histdir, f.replace("=", "_") + ".json"), "w"), separators=(",", ":"))
    ctrl_line = {}
    for fam in ("A_w", "A_m", "A_q"):
        c = [abs(u["r"]) for u in res["units"] if u["family"] == fam and u["ring"] == 0 and u.get("ok") and u.get("r") is not None and np.isfinite(u["r"])]
        ctrl_line[fam] = round(float(np.percentile(c, 95)), 3) if c else None
    for r in rels: r["above"] = bool(ctrl_line.get(r["fam"]) is not None and abs(r["e"]) > ctrl_line[r["fam"]])
    bm = [c for c in res["confirm"] if c["family"] == "B_m"]
    chains = []
    for c in res["chains"]:
        if c.get("state") == "Validated":
            chains.append(dict(path=c["chain"], E=c["E"], C=c["C"], q=c.get("q_confirm"), h=c.get("history", [])))
    tests = {}
    for t in res["meta"]["tests"]: tests.setdefault(t["family"], {})[t["ring"]] = t["usable"]
    val = {}
    for v in res["validated"]: val.setdefault(v["family"], {}).setdefault(v["ring"], 0); val[v["family"]][v["ring"]] += 1
    units = {}
    for u in res["units"]:
        if u.get("ok"): units.setdefault(u["family"], {}).setdefault(u["ring"], 0); units[u["family"]][u["ring"]] += 1
    ctrl = len({v["external"] for v in res["validated"] if U.EXTERNALS[v["external"]]["role"] != "candidate"}); ctrl_rel = sum(1 for v in res["validated"] if U.EXTERNALS[v["external"]]["role"] != "candidate")
    data = dict(names={k: name(k) for k in list(U.FOCAL) + list(U.REVENUE) + list(U.EXTERNALS)},
                focal={k: v["segment"] for k, v in {**U.FOCAL, **U.REVENUE}.items()}, rels=[r for r in rels if r["role"] == "candidate"],
                ctrl_rel=ctrl_rel, ctrl_line=ctrl_line, bm=dict(cand=len(bm), flipped=sum("direction changed" in c["reason"] for c in bm), val=sum(c["state"] == "Validated" for c in bm)), shock=dict(cand=sum(c["family"] == "X_shock" for c in res["confirm"])), chains=chains, chains_tested=len(res["chains"]), units=units, val=val, ctrl=ctrl,
                pred=[dict(p, nf=name(p["focal"]), nx=name(p["external"])) for p in res.get("predictive", [])],
                unavailable=U.UNAVAILABLE, generated=asof, prereg="aaf2869")
    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "observatory3_template.html")).read().replace("/*DATA*/null", json.dumps(data, separators=(",", ":"), default=float))
    open(out, "w").write(html); return len(html), len(data["rels"])

if __name__ == "__main__":
    print(build(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
