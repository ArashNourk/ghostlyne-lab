"""R4.1: recompute monitoring for R4's validated relationships with the corrected method. No re-validation."""
import io, json, os, sys, numpy as np, pandas as pd, requests
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import main4, lab4, monitor_fix
P, st, ni, Y, miss = main4.load(); S = lab4.build(P, st, ni, Y)
r4 = requests.get("https://raw.githubusercontent.com/ArashNourk/ghostlyne-lab/main/registry/r4/results/R4.json", timeout=120).json()
out = []
for v in r4["validated"]:
    m = monitor_fix.monitor(S, v); out.append(dict(focal=v["focal"], external=v["external"], family=v["family"], lag=v["lag"], monitor=m))
os.makedirs("out", exist_ok=True); json.dump(dict(run="R4.1-monitoring", generated=pd.Timestamp.now("UTC").isoformat(), monitors=out), open("out/R4_monitoring_v2.json", "w"),
                                             default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print("done", len(out))
