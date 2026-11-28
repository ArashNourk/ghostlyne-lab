"""The single WATCH2 run on real data. Refuses to run if any frozen file changed.

Usage:  python3 confirm.py data/btc_hourly.csv
Writes: results/WATCH2_CONFIRM.json and prints the gates.
"""
import hashlib, json, os, sys
import numpy as np, pandas as pd

FROZEN = json.load(open("FREEZE.json"))
for path, digest in FROZEN["files"].items():
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != digest:
        sys.exit(f"REFUSED: {path} differs from the frozen version. A changed specification needs a new registration.")
import watch2

src = sys.argv[1] if len(sys.argv) > 1 else "data/btc_hourly.csv"
raw = pd.read_csv(src, parse_dates=["ts"]).set_index("ts").sort_index()
idx = pd.date_range(raw.index[0], raw.index[-1], freq="h")
d = raw.reindex(idx)
d = d.ffill(limit=2)                                   # gaps of up to 2 candles are bridged
d["bad"] = d.close.isna()                              # longer gaps: every scenario overlapping them is excluded
d[["open", "high", "low", "close"]] = d[["open", "high", "low", "close"]].ffill()
if d.bad.any():
    print(f"note: {int(d.bad.sum())} hours inside gaps longer than 2 candles; overlapping scenarios excluded")
if raw.index[0] > pd.Timestamp("2018-03-01", tz="UTC") or raw.index[-1] < pd.Timestamp("2024-01-01", tz="UTC"):
    sys.exit("REFUSED: data does not cover the registered development and confirmation periods")
dev_end = pd.Timestamp("2023-01-01", tz="UTC")
dd = d
rep = watch2.full(dd, dev_end, cal=True)
rep.update({"source": src, "first": str(dd.index[0]), "last": str(dd.index[-1]), "frozen": FROZEN["files"],
            "note": "outcomes measured on CoinGecko aggregate hourly price, not exchange execution price"})
os.makedirs("results", exist_ok=True)
json.dump(rep, open("results/WATCH2_CONFIRM.json", "w"), indent=1, default=float)
print("ambiguous share:", f"{rep['ambiguous_share']:.2%}")
print("gates (must pass under every ambiguity resolution):", rep["gates_all_resolutions"])
