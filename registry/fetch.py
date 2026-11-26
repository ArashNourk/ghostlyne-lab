"""Download every series in the R1 universe to out/raw/*.csv (date,value)."""
import os, json
from sources import fetch_all
out, errors = fetch_all()
os.makedirs("out/raw", exist_ok=True)
for k, df in out.items(): df.to_csv(f"out/raw/{k}.csv", index=False)
json.dump({"downloaded": sorted(out), "missing": errors}, open("out/manifest.json", "w"), indent=1)
open("out/SOURCES.md", "w").write("Federal Reserve Bank of St. Louis (FRED): US BLS, Federal Reserve Board, US Census Bureau, BTS and IMF primary commodity prices. NOAA Climate Prediction Center (ONI). NOAA NCEI climate divisional data (Arizona PDSI). Retrieved for research; see each source's terms.\n")
print(json.dumps({"ok": len(out), "missing": errors}))
