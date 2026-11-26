"""Build the Ghostlyne Observatory page from R2 results (real validated findings only)."""
import json, sys, numpy as np
sys.path.insert(0, "r2")
import universe as U
d = json.load(open("r2/results/R2.json"))
SEMI = {"AMAT", "8035.T", "ASML", "3436.T", "4063.T", "ENTG"}
def hyp(v):
    if v["family"] == "A_total": return "Includes the shared global-market factor, which drives most total associations."
    x = v["external"]
    if x in SEMI: return "Shared semiconductor-industry factor: memory makers buy these tools, wafers and materials, and both sides move with the chip cycle. The global adjustment does not remove it."
    if x == "XLU": return "Growth-versus-defensive style factor. Not evidence of an electricity link."
    if x == "2603.TW": return "Taiwan home-market factor: both are listed in Taipei. Not evidence of a shipping link."
    if x == "ABBN.SW": return "Shared industrial-cycle exposure."
    return "No explanation proposed."
def ci(r, n): z = np.arctanh(r); h = 1.96 / np.sqrt(n - 3); return [round(float(np.tanh(z - h)), 3), round(float(np.tanh(z + h)), 3)]
rels = []
for v in d["validated"]:
    if v["family"] not in ("A_total", "A_adjusted"): continue
    m = v["monitor"]; step = 2 if v["family"] == "A_adjusted" else 4; H = m["history"][::step] + ([m["history"][-1]] if m["history"] and (len(m["history"]) - 1) % step else [])
    rels.append(dict(f=v["focal"], x=v["external"], fam=v["family"], ring=v["ring"], rc=round(v["r_confirm"], 3), ci=ci(v["r_confirm"], v["n_confirm"]),
                     re=round(v["r_explore"], 3), q=v["q_confirm"], n=v["n_confirm"], st=m.get("state") or {}, last=m.get("latest") or {},
                     h=[[h["date"], h["r"], h["lo"], h["hi"]] for h in H], why=U.EXTERNALS[v["external"]]["why"], hyp=hyp(v)))
U_ = d["units"]; C = {(c["focal"], c["external"], c["family"]): c for c in d["confirm"]}
table = {}
for fam in ("A_total", "A_adjusted", "B_leadlag", "S_stress"):
    row = []
    for ring in (1, 2, 3, 4, 5, 0):
        us = [u for u in U_ if u["family"] == fam and u["ring"] == ring]
        cs = [C[(u["focal"], u["external"], fam)] for u in us if (u["focal"], u["external"], fam) in C]
        row.append([len(us), len(cs), sum(c["state"] == "Validated" for c in cs)])
    table[fam] = row
ev = d["replay"]["events"]
data = dict(focal={k: v["name"].replace(" (share price)", "") for k, v in U.FOCAL.items()}, ext={k: v["name"] for k, v in U.EXTERNALS.items()},
            rels=rels, table=table, tests=d["meta"]["tests_explore"], monthly=dict(tests=d["monthly"]["tests"], cand=d["monthly"]["candidates"], val=sum(c["state"] == "Validated" for c in d["monthly"]["confirm"])),
            replay=dict(cand=sum(e["to"] == "Candidate" for e in ev), conf=sum(e["frm"] == "Candidate" and e["to"] == "Validated" for e in ev),
                        under=sum(e["to"] == "Under Reassessment" for e in ev), inval=sum(e["to"] == "Invalidated" for e in ev)),
            power=[[8, 20], [12, 40], [16, 60], [20, 80], [25, 100]], unavailable=U.UNAVAILABLE, events=1868,
            prereg="3c36251", generated=d["meta"]["generated"][:10])
html = open("r2/observatory_template.html").read().replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
open(sys.argv[1] if len(sys.argv) > 1 else "../docs/index.html", "w").write(html); print("bytes", len(html), "relationships", len(rels))
