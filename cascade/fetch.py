"""Download free Binance USD-M futures history from data.binance.vision:
daily candles (monthly files), funding rates (monthly files) and 5-minute positioning metrics (daily files:
open interest, top-trader long/short ratios, taker buy/sell ratio). Cached under data/."""
import io, zipfile, sys, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd, requests

BASE = "https://data.binance.vision/data/futures/um"
SYMS = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","BCHUSDT",
        "TRXUSDT","ATOMUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","FILUSDT","ETCUSDT","UNIUSDT","AAVEUSDT","INJUSDT","1000SHIBUSDT",
        "1000PEPEUSDT","SUIUSDT","XLMUSDT","ALGOUSDT"]
OUT = Path("data"); S = requests.Session(); S.headers["User-Agent"] = "ghostlyne-lab research"

def get(url):
    for _ in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404: return None
            if r.status_code == 200: return r.content
        except Exception: pass
    return None

def read_zip(blob, names=None):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read(z.namelist()[0])
    first = raw.split(b"\n", 1)[0]
    header = 0 if any(ch.isalpha() for ch in first.decode(errors="ignore").replace("e-", "").replace("E-", "")) else None
    return pd.read_csv(io.BytesIO(raw), header=header, names=None if header == 0 else names)

def months(a, b):
    return [d.strftime("%Y-%m") for d in pd.date_range(a, b, freq="MS")]

KCOLS = ["open_time","open","high","low","close","volume","close_time","quote_volume","count","taker_buy_volume","taker_buy_quote_volume","ignore"]

def klines(sym, start, end):
    p = OUT / "klines" / f"{sym}.parquet"
    if p.exists(): return
    frames = []
    for m in months(start, end):
        b = get(f"{BASE}/monthly/klines/{sym}/1d/{sym}-1d-{m}.zip")
        if b: frames.append(read_zip(b, KCOLS))
    if frames:
        d = pd.concat(frames); d.columns = KCOLS[:d.shape[1]]
        d["date"] = pd.to_datetime(pd.to_numeric(d.open_time), unit="ms").dt.normalize()
        p.parent.mkdir(parents=True, exist_ok=True)
        d[["date","open","high","low","close","quote_volume","taker_buy_quote_volume"]].astype({"open":float,"high":float,"low":float,"close":float,"quote_volume":float,"taker_buy_quote_volume":float}).drop_duplicates("date").to_parquet(p)

def funding(sym, start, end):
    p = OUT / "funding" / f"{sym}.parquet"
    if p.exists(): return
    frames = []
    for m in months(start, end):
        b = get(f"{BASE}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
        if b: frames.append(read_zip(b, ["calc_time","funding_interval_hours","last_funding_rate"]))
    if frames:
        d = pd.concat(frames); d["time"] = pd.to_datetime(pd.to_numeric(d.calc_time), unit="ms")
        p.parent.mkdir(parents=True, exist_ok=True); d[["time","last_funding_rate"]].astype({"last_funding_rate":float}).to_parquet(p)

def metrics_day(sym, day):
    b = get(f"{BASE}/daily/metrics/{sym}/{sym}-metrics-{day}.zip")
    if not b: return None
    d = read_zip(b)
    d["create_time"] = pd.to_datetime(d.create_time)
    num = [c for c in d.columns if c not in ("create_time","symbol")]
    d[num] = d[num].apply(pd.to_numeric, errors="coerce")
    last = d.sort_values("create_time").iloc[-1]
    return {"date": pd.Timestamp(day), "oi": last.sum_open_interest_value, "oi_coins": last.sum_open_interest,
            "top_ls_acct": d.count_toptrader_long_short_ratio.mean(), "top_ls_pos": d.sum_toptrader_long_short_ratio.mean(),
            "global_ls": d.count_long_short_ratio.mean(), "taker_ls": d.sum_taker_long_short_vol_ratio.mean(),
            "oi_intraday_range": d.sum_open_interest_value.max() / max(d.sum_open_interest_value.min(), 1) - 1}

def metrics(sym, start, end, pool):
    p = OUT / "metrics" / f"{sym}.parquet"
    if p.exists(): return
    days = [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end)]
    rows = [r for r in pool.map(lambda dd: metrics_day(sym, dd), days) if r]
    if rows:
        p.parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_parquet(p)
    print(sym, "metrics days", len(rows), flush=True)

if __name__ == "__main__":
    start, end = sys.argv[1], sys.argv[2]
    with ThreadPoolExecutor(24) as pool:
        list(pool.map(lambda s: (klines(s, "2020-01-01", end), funding(s, "2020-01-01", end)), SYMS))
        print("klines and funding done", flush=True)
        for s in SYMS: metrics(s, start, end, pool)
