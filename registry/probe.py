"""Coverage probe: records only which series exist and their date ranges. No values are written."""
import json, os, pandas as pd
from sources import fetch_all
out, errors = fetch_all()
cov = {}
for k, df in out.items():
    d = df["date"].sort_values()
    step = d.diff().dt.days.median()
    cov[k] = {"first": str(d.iloc[0].date()), "last": str(d.iloc[-1].date()), "n": int(len(d)),
              "freq": "daily" if step < 5 else "weekly" if step < 10 else "monthly" if step < 40 else "quarterly+"}
os.makedirs("registry/out", exist_ok=True)
json.dump({"coverage": cov, "missing": errors}, open("registry/out/coverage.json", "w"), indent=1)
print(json.dumps({"ok": len(cov), "missing": errors}, indent=1))
