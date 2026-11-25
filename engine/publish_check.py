"""After the site is pushed, wait until the newest forecast is actually served at the public URL and record that
moment (verified_public_utc) in ledger/publications.jsonl. On-time means verified public before the window opens."""
import json, sys, time
from pathlib import Path
import pandas as pd, requests
ROOT = Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / "engine/config.json")); URL = CFG.get("site_data_url", "https://arashnourk.github.io/ghostlyne-lab/data.json")
LEDGER, PUBS = ROOT / "ledger/forecasts.jsonl", ROOT / "ledger/publications.jsonl"
led = [json.loads(l) for l in open(LEDGER)] if LEDGER.exists() else []
pubs = [json.loads(l) for l in open(PUBS)] if PUBS.exists() else []
if not led or any(p["forecast_hash"] == led[-1]["hash"] for p in pubs): sys.exit(0)
last = led[-1]; deadline = time.time() + 25 * 60
while time.time() < deadline:
    try:
        d = requests.get(URL, params={"v": int(time.time())}, headers={"Cache-Control": "no-cache"}, timeout=30).json()
        if d.get("hash") == last["hash"]:
            rec = {"date": last["date"], "forecast_hash": last["hash"], "url": URL, "verified_public_utc": pd.Timestamp.now("UTC").tz_convert(None).isoformat() + "Z",
                   "window_start_utc": last.get("window_start_utc", last["date"] + "T00:00:00Z")}
            rec["on_time"] = pd.Timestamp(rec["verified_public_utc"]).tz_convert(None) < pd.Timestamp(rec["window_start_utc"]).tz_convert(None)
            with open(PUBS, "a") as fh: fh.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
            (ROOT / "docs/ledger").mkdir(parents=True, exist_ok=True); (ROOT / "docs/ledger/publications.jsonl").write_text(PUBS.read_text())
            print("verified public at", rec["verified_public_utc"], "on time" if rec["on_time"] else "LATE"); sys.exit(0)
    except Exception as e: print("not yet:", e)
    time.sleep(20)
print("forecast not visible at the public URL within 25 minutes"); sys.exit(1)
