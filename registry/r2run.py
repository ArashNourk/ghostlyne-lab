import sys, os, json, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "r2"))
from main import fetch, analyse
S, Mrev, miss = fetch(); res = analyse(S, Mrev, miss)
os.makedirs("out", exist_ok=True)
json.dump(res, open("out/R2.json", "w"), default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print(json.dumps(res["meta"], default=str))
