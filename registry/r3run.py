import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "r3"))
from main3 import fetch, analyse
S, miss = fetch(); res = analyse(S, miss)
os.makedirs("out", exist_ok=True)
json.dump(res, open("out/R3.json", "w"), default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (None if o is pd.NaT else str(o)))
print(json.dumps(res["meta"], default=str)[:3000])
