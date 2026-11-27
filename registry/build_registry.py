"""Append R1 and R2 outcomes to the append-only Relationship Registry (registry.jsonl). Existing events are never rewritten."""
import json, os, sys
sys.path.insert(0, "r2")
from lab import eid
import universe as U2
P = "registry.jsonl"
seen = set()
if os.path.exists(P):
    for line in open(P): e = json.loads(line); seen.add((e["exp_id"], e["run"], e.get("event", "result"), e.get("date", ""), e.get("frm", ""), e.get("state", "")))
new = []
def add(e):
    k = (e["exp_id"], e["run"], e.get("event", "result"), e.get("date", ""), e.get("frm", ""), e.get("state", ""))
    if k not in seen: seen.add(k); new.append(e)
r1 = json.load(open("results/R1.json"))
for r in r1["pairs"]:
    add(dict(exp_id=eid(r["target"], r["external"], "C_predictive_monthly"), run="R1", date="2026-11-26", event="result", focal=r["target"], external=r["external"],
             ring=r["ring"], family="C_predictive_monthly", lag=r.get("lag"), effect=r.get("r2_oos"), p=r.get("p"), q=r.get("q"),
             state="Not Detected" if r["status"] == "graveyard" else "Validated", reason=r.get("reason")))
r2 = json.load(open("r2/results/R2.json")); conf = {(c["focal"], c["external"], c["family"]): c for c in r2["confirm"]}
for u in r2["units"]:
    k = (u["focal"], u["external"], u["family"]); c = conf.get(k)
    st = c["state"] if c else "Not Detected"
    add(dict(exp_id=eid(*k), run="R2", date="2026-11-26", event="result", focal=u["focal"], external=u["external"], ring=u["ring"], role=u["role"], family=u["family"],
             lag=c["lag"] if c else u["lag"], effect_explore=u["r"], p_explore=u["p"], q_explore=u["q"], n_explore=u["n"],
             effect_confirm=c["r_confirm"] if c else None, q_confirm=c["q_confirm"] if c else None, n_confirm=c["n_confirm"] if c else None,
             state=st, reason=c["reason"] if c else "not a candidate in exploration (false-discovery control)"))
mt = r2["monthly"]; mconf = {(c["focal"], c["external"], c["family"]): c for c in mt["confirm"]}
for u in mt["units"]:
    k = (u["focal"], u["external"], u["family"] + "_monthly"); c = mconf.get((u["focal"], u["external"], u["family"]))
    add(dict(exp_id=eid(*k), run="R2", date="2026-11-26", event="result", focal=u["focal"], external=u["external"], ring=u["ring"], family=u["family"] + "_monthly",
             lag=u["lag"], effect_explore=u["r"], q_explore=u["q"], n_explore=u["n"], effect_confirm=c["r_confirm"] if c else None, q_confirm=c["q_confirm"] if c else None,
             state=c["state"] if c else "Not Detected"))
for e in r2["replay"]["events"]:
    add(dict(exp_id=eid(e["focal"], e["external"], "A_adjusted"), run="R2-replay", date=e["date"], event="replay_transition", focal=e["focal"], external=e["external"],
             family="A_adjusted", frm=e["frm"], state=e["to"], effect=e["r"], p=e["p"], note="historical replay, not live monitoring"))
with open(P, "a") as f:
    for e in new: f.write(json.dumps(e) + "\n")
print("appended", len(new), "events; total", len(seen))

# ---- R3 ----
if os.path.exists("r3/results/R3.json"):
    n0 = len(new)
    sys.path.insert(0, "r3")
    r3 = json.load(open("r3/results/R3.json")); c3 = {(c["focal"], c["external"], c["family"], c.get("dir", "")): c for c in r3["confirm"]}
    for u in r3["units"]:
        k = (u["focal"], u["external"], u["family"], u.get("dir", "")); c = c3.get(k)
        st = c["state"] if c else ("Insufficient Data" if not u.get("ok") else "Not Detected")
        add(dict(exp_id=eid(*k), run="R3", date="2026-11-27", event="result", focal=u["focal"], external=u["external"], ring=u["ring"], role=u["role"], family=u["family"],
                 dir=u.get("dir", ""), lag=c["lag"] if c else u["lag"], effect_explore=u["r"], p_explore=u["p"], q_explore=u.get("q"), n_explore=u["n"],
                 effect_confirm=c["e_confirm"] if c else None, q_confirm=c["q_confirm"] if c else None, n_confirm=c["n_confirm"] if c else None,
                 state=st, reason=c["reason"] if c else ("insufficient data" if st == "Insufficient Data" else "not a candidate in exploration (false-discovery control)")))
    for ch in r3["chains"]:
        add(dict(exp_id=eid(*ch["chain"], "chain"), run="R3", date="2026-11-27", event="result", focal=ch["chain"][2], external=ch["chain"][0], via=ch["chain"][1], family="chain",
                 effect_explore=ch.get("E", {}).get("indirect_std"), effect_confirm=ch.get("C", {}).get("indirect_std"), q_explore=ch.get("q_explore"), q_confirm=ch.get("q_confirm"),
                 state=ch.get("state"), reason=ch.get("reason")))
    with open(P, "a") as f:
        for e in new[n0:]: f.write(json.dumps(e) + "\n")
    print("R3 appended", len(new) - n0)
