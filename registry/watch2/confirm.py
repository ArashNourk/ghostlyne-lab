"""The single WATCH2 run on real data (Amendment 3). Refuses to run if any frozen file changed or the data fails validation.

Usage:  python3 confirm.py data/btc_hourly.csv [--asof YYYY-MM-DD]
        --asof only for testing; the real run uses today's date, and the value used is recorded in the output.
Writes: results/WATCH2_CONFIRM.json; prints the gates for the 24-hour (primary) and 8-hour (reported) horizons.
"""
import hashlib, json, os, sys
import numpy as np, pandas as pd

FROZEN = json.load(open("FREEZE.json"))
for path, digest in FROZEN["files"].items():
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != digest:
        sys.exit(f"REFUSED: {path} differs from the frozen version. A changed specification needs a new registration.")
import watch2

args = [a for a in sys.argv[1:] if not a.startswith("--")]
src = args[0] if args else "data/btc_hourly.csv"
asof = pd.Timestamp(sys.argv[sys.argv.index("--asof") + 1], tz="UTC") if "--asof" in sys.argv else pd.Timestamp.now(tz="UTC")
COLS = ["open", "high", "low", "close"]

raw = pd.read_csv(src)
if list(raw.columns[:5]) != ["ts"] + COLS:
    sys.exit("REFUSED: expected columns ts, open, high, low, close")
raw["ts"] = pd.to_datetime(raw.ts, utc=True)
v = {"rows_in_file": int(len(raw))}
# duplicates: identical rows are collapsed; conflicting rows for one timestamp stop the run
dup = raw.duplicated("ts", keep=False)
if dup.any():
    if raw[dup].drop_duplicates().ts.duplicated().any():
        sys.exit("REFUSED: conflicting duplicate candles for the same timestamp")
    raw = raw.drop_duplicates()
v["identical_duplicates_removed"] = int(dup.sum() - raw.ts.isin(raw.ts[dup]).sum()) if dup.any() else 0
# timestamps: candle close times exactly on the hour
if ((raw.ts.dt.minute != 0) | (raw.ts.dt.second != 0)).any():
    sys.exit("REFUSED: timestamps not aligned to the hour")
raw = raw.set_index("ts").sort_index()
# OHLC consistency: inconsistent candles become missing (never repaired)
o, h, l, c = (raw[k] for k in COLS)
bad = raw[COLS].isna().any(axis=1) | ~((raw[COLS] > 0).all(axis=1) & (l <= np.minimum(o, c)) & (h >= np.maximum(o, c)) & (h >= l))
v["inconsistent_candles"] = int(bad.sum())
if bad.mean() > 0.005:
    sys.exit(f"REFUSED: {bad.mean():.2%} of candles are inconsistent (limit 0.5%)")
raw.loc[bad, COLS] = np.nan
# coverage: from the registered start through the last complete month before the run
last_needed = asof.normalize().replace(day=1)                       # close of the last hour of the previous month
if raw.index[0] > pd.Timestamp("2018-02-28", tz="UTC"):
    sys.exit(f"REFUSED: data starts {raw.index[0]}, registered start is February 2018")
if raw.index[-1] < last_needed:
    sys.exit(f"REFUSED: data ends {raw.index[-1]}, must reach {last_needed} (last complete month)")
raw = raw[raw.index <= last_needed]
d = raw.reindex(pd.date_range(raw.index[0], raw.index[-1], freq="h"))   # missing hours stay missing: nothing is filled
v["missing_hours"] = int(d.close.isna().sum())
v.update({"first": str(d.index[0]), "last": str(d.index[-1]), "asof": str(asof.date())})
print("validation:", v)

dev_end = pd.Timestamp("2023-01-01", tz="UTC")
out = {"validation": v, "frozen": FROZEN["files"],
       "note": "outcomes measured on CoinGecko aggregate hourly price, not exchange execution price"}
for hz in (24, 8):
    watch2.H = hz
    out[f"horizon_{hz}h"] = watch2.full(d, dev_end, cal=True)
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/WATCH2_CONFIRM.json", "w"), indent=1, default=float)
for hz in (24, 8):
    r = out[f"horizon_{hz}h"]
    print(f"{hz}h{' (primary)' if hz == 24 else ' (reported)'}: ambiguous {r['ambiguous_share']:.2%} | gates (every ambiguity resolution): {r['gates_all_resolutions']}")
