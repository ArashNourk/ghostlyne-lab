"""Order-book depth history (Binance USD-M bookDepth daily archive) aggregated to the hour, development window only.
Per (market, hour t): the last snapshot strictly before t, cumulative notional within 1%, 2% and 5% of the price on the
bid (negative percentage) and ask (positive) sides. Usage: python fetch_depth.py OUTDIR START END [SYMBOL ...]"""
import sys, io, zipfile, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests

BASE = "https://data.binance.vision/data/futures/um/daily/bookDepth"
SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","BCHUSDT",
        "TRXUSDT","SUIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","ATOMUSDT","FILUSDT","ETCUSDT","UNIUSDT","AAVEUSDT",
        "1000PEPEUSDT","1000SHIBUSDT","XLMUSDT","ALGOUSDT"]
S = requests.Session(); S.mount("https://", requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=3))

def day(sym, d):
    url = f"{BASE}/{sym}/{sym}-bookDepth-{d}.zip"
    for k in range(4):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404: return None
            r.raise_for_status(); z = zipfile.ZipFile(io.BytesIO(r.content))
            x = pd.read_csv(io.StringIO(z.read(z.namelist()[0]).decode()))
            x.columns = [c.strip().lower() for c in x.columns]
            x["t"] = pd.to_datetime(x["timestamp"]); x["pct"] = pd.to_numeric(x["percentage"]); x["notional"] = pd.to_numeric(x["notional"])
            x = x[x.pct.isin([-5, -2, -1, 1, 2, 5])]
            w = x.pivot_table(index="t", columns="pct", values="notional", aggfunc="last")
            w.columns = [f"{'bid' if c < 0 else 'ask'}{abs(int(c))}" for c in w.columns]
            # last snapshot strictly before each hour boundary
            hrs = pd.date_range(pd.Timestamp(d) + pd.Timedelta(hours=1), pd.Timestamp(d) + pd.Timedelta(hours=24), freq="h")
            return pd.merge_asof(pd.DataFrame({"t": hrs - pd.Timedelta(seconds=1)}), w.reset_index().sort_values("t"), on="t",
                                 direction="backward", tolerance=pd.Timedelta("10min")).assign(t=hrs)
        except Exception as e:
            err = e; time.sleep(2 * (k + 1))
    print("failed", sym, d, repr(err), flush=True); return None

if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); a, b = sys.argv[2], sys.argv[3]; syms = sys.argv[4:] or SYMS
    days = [x.strftime("%Y-%m-%d") for x in pd.date_range(a, b)]
    for s in syms:
        f = out / f"{s}.parquet"
        if f.exists(): continue
        t0 = time.time()
        with ThreadPoolExecutor(32) as ex: parts = [p for p in ex.map(lambda d: day(s, d), days) if p is not None]
        if not parts: print(s, "no depth data", flush=True); continue
        x = pd.concat(parts).set_index("t").sort_index(); x = x[~x.index.duplicated()]
        x.astype("float32").to_parquet(f); print(s, len(parts), "days", f"{x.notna().all(1).mean():.0%} complete", f"{time.time() - t0:.0f}s", flush=True)
