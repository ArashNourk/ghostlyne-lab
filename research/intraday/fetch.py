"""Intraday research data: one hourly table per market, built from Binance's public archive (data.binance.vision) and
Deribit DVOL. Raw minute data is processed per market and discarded; only the hourly table is kept.

Per (market, hour t), all values use data with timestamps before t except the targets:
  mark o/h/l/c          1-hour mark-price candle that opened at t-1h (known at t)
  rv1                   sum of squared 1-minute log mark returns in that hour
  vol, qvol, trades, taker_buy_qvol, last o/h/l/c   1-hour futures candle that opened at t-1h
  prem_o/h/l/c          1-hour premium-index (perp vs index) candle that opened at t-1h
  oi, oi_val, top_ls_acct, top_ls_pos, ls_acct, taker_ls   last 5-minute metrics sample before t
  funding               most recent funding rate settled at or before t
  entry                 mark open of the minute starting at t (the position's entry)
  dn_1/4/8, up_1/4/8    TARGETS: log(min mark low / entry) and log(max mark high / entry) over minutes [t, t+h)
  cov_1/4/8             share of the horizon's minutes present (targets kept only when >= 0.95)
Usage: python fetch.py OUTDIR [--smoke]
"""
import sys, io, zipfile, json, time, datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests

BASE = "https://data.binance.vision/data/futures/um"
SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","BCHUSDT",
        "TRXUSDT","SUIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","ATOMUSDT","FILUSDT","ETCUSDT","UNIUSDT","AAVEUSDT",
        "1000PEPEUSDT","1000SHIBUSDT","XLMUSDT","ALGOUSDT"]
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2026-10-31")
HORIZONS = {1: 60, 4: 240, 8: 480}
S = requests.Session(); S.mount("https://", requests.adapters.HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=3))

def get_zip_csv(url):
    """CSV inside a Binance zip, or None if the file does not exist. Probes the CDN directly (listings are stale)."""
    for k in range(4):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404: return None
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content)); raw = z.read(z.namelist()[0]).decode()
            df = pd.read_csv(io.StringIO(raw), header=None, low_memory=False)
            if str(df.iloc[0, 0])[:1].isalpha(): df = df.iloc[1:]                       # header row (newer files)
            return df.reset_index(drop=True)
        except Exception:
            time.sleep(2 * (k + 1))
    return None

def ts(x):
    x = pd.to_numeric(x, errors="coerce"); unit = "us" if x.dropna().gt(1e14).any() else "ms"
    return pd.to_datetime(x, unit=unit)

def months():
    return [d.strftime("%Y-%m") for d in pd.date_range(START, END, freq="MS")]

def monthly(kind, sym, interval=None):
    urls = [f"{BASE}/monthly/{kind}/{sym}/{interval + '/' if interval else ''}{sym}-{interval + '-' if interval else ''}{m}.zip" for m in months()]
    if kind == "fundingRate": urls = [f"{BASE}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip" for m in months()]
    with ThreadPoolExecutor(16) as ex: parts = [p for p in ex.map(get_zip_csv, urls) if p is not None]
    return pd.concat(parts, ignore_index=True) if parts else None

def klines(df):
    k = pd.DataFrame({"t": ts(df[0]), "o": pd.to_numeric(df[1]), "h": pd.to_numeric(df[2]), "l": pd.to_numeric(df[3]), "c": pd.to_numeric(df[4])})
    if df.shape[1] > 10:
        k["vol"] = pd.to_numeric(df[5]); k["qvol"] = pd.to_numeric(df[7]); k["trades"] = pd.to_numeric(df[8]); k["taker_buy_qvol"] = pd.to_numeric(df[10])
    return k.dropna(subset=["t"]).drop_duplicates("t").sort_values("t").set_index("t")

def targets(m1):
    """Hourly origins with entry and forward excursions from a 1-minute mark-price frame indexed by minute."""
    idx = pd.date_range(m1.index.min().ceil("h"), m1.index.max().floor("h"), freq="h")
    full = m1.reindex(pd.date_range(m1.index.min(), m1.index.max(), freq="min"))
    L, H, O = full.l, full.h, full.o; out = pd.DataFrame(index=idx); out["entry"] = O.reindex(idx)
    for h, n in HORIZONS.items():
        fmin = L[::-1].rolling(n, min_periods=1).min()[::-1]; fmax = H[::-1].rolling(n, min_periods=1).max()[::-1]
        cnt = L.notna().astype(float)[::-1].rolling(n, min_periods=1).sum()[::-1]
        # window [t, t+n): the forward rolling value at t covers t..t+n-1; drop windows that run past the data
        last_ok = full.index[-1] - pd.Timedelta(minutes=n - 1)
        out[f"dn_{h}"] = np.log(fmin.reindex(idx) / out.entry); out[f"up_{h}"] = np.log(fmax.reindex(idx) / out.entry)
        out[f"cov_{h}"] = (cnt.reindex(idx) / n).where(idx <= last_ok)
        bad = out[f"cov_{h}"].isna() | (out[f"cov_{h}"] < 0.95)
        out.loc[bad, [f"dn_{h}", f"up_{h}"]] = np.nan
    return out

def build(sym, out_dir):
    f = out_dir / f"{sym}.parquet"
    if f.exists(): return sym, "cached"
    m1 = monthly("markPriceKlines", sym, "1m")
    if m1 is None: return sym, "no mark data"
    m1 = klines(m1)
    T = targets(m1)
    r = np.log(m1.c).diff(); rv = (r ** 2).groupby(m1.index.floor("h")).sum()
    mh = m1.resample("h").agg({"o": "first", "h": "max", "l": "min", "c": "last"})
    feat = pd.DataFrame(index=T.index)
    feat[["m_o", "m_h", "m_l", "m_c"]] = mh.shift(1, freq="h").reindex(T.index).values   # candle that opened at t-1h
    feat["rv1"] = rv.shift(1, freq="h").reindex(T.index)
    del m1
    k = monthly("klines", sym, "1h")
    if k is not None:
        k = klines(k).shift(1, freq="h").reindex(T.index)
        feat[["l_o", "l_h", "l_l", "l_c", "vol", "qvol", "trades", "taker_buy_qvol"]] = k[["o", "h", "l", "c", "vol", "qvol", "trades", "taker_buy_qvol"]].values
    p = monthly("premiumIndexKlines", sym, "1h")
    if p is not None:
        p = klines(p).shift(1, freq="h").reindex(T.index); feat[["prem_o", "prem_h", "prem_l", "prem_c"]] = p[["o", "h", "l", "c"]].values
    fr = monthly("fundingRate", sym)
    if fr is not None:
        fr = pd.DataFrame({"t": ts(fr[0]), "rate": pd.to_numeric(fr[2], errors="coerce")}).dropna().sort_values("t")
        feat["funding"] = pd.merge_asof(pd.DataFrame({"t": T.index}), fr, on="t", direction="backward").rate.values
    days = pd.date_range(max(START, pd.Timestamp("2021-06-01")), END, freq="D")
    urls = [f"{BASE}/daily/metrics/{sym}/{sym}-metrics-{d.strftime('%Y-%m-%d')}.zip" for d in days]
    with ThreadPoolExecutor(32) as ex: parts = [x for x in ex.map(get_zip_csv, urls) if x is not None]
    if parts:
        mt = pd.concat(parts, ignore_index=True)
        mt = pd.DataFrame({"t": pd.to_datetime(mt[0], errors="coerce"), "oi": pd.to_numeric(mt[2], errors="coerce"), "oi_val": pd.to_numeric(mt[3], errors="coerce"),
                           "top_ls_acct": pd.to_numeric(mt[4], errors="coerce"), "top_ls_pos": pd.to_numeric(mt[5], errors="coerce"),
                           "ls_acct": pd.to_numeric(mt[6], errors="coerce"), "taker_ls": pd.to_numeric(mt[7], errors="coerce")}).dropna(subset=["t"]).sort_values("t")
        # last sample strictly before t (a sample stamped exactly at t may be published after t)
        q = pd.DataFrame({"t": T.index - pd.Timedelta(seconds=1)})
        feat[["oi", "oi_val", "top_ls_acct", "top_ls_pos", "ls_acct", "taker_ls"]] = pd.merge_asof(q, mt, on="t", direction="backward", tolerance=pd.Timedelta("30min"))[["oi", "oi_val", "top_ls_acct", "top_ls_pos", "ls_acct", "taker_ls"]].values
    tab = pd.concat([feat, T], axis=1); tab.index.name = "t"; tab["sym"] = sym
    tab = tab[(tab.index >= START) & (tab.index <= END + pd.Timedelta(days=1))].astype({c: "float32" for c in tab.columns if c != "sym"})
    tab.to_parquet(f); return sym, f"{len(tab)} hours, metrics days {len(parts)}"

def dvol(out_dir):
    f = out_dir / "DVOL.parquet"
    if f.exists(): return "cached"
    rows = []
    for cur in ["BTC", "ETH"]:
        end = int(END.timestamp() * 1000) + 86400000; start = int(pd.Timestamp("2021-03-01").timestamp() * 1000)
        while end > start:
            r = S.get("https://www.deribit.com/api/v2/public/get_volatility_index_data", params={"currency": cur, "start_timestamp": start, "end_timestamp": end, "resolution": "3600"}, timeout=60).json()
            data = r["result"]["data"]
            if not data: break
            rows += [(cur, d[0], d[1], d[2], d[3], d[4]) for d in data]
            cont = r["result"].get("continuation")
            if not cont or cont >= end: break
            end = cont
    d = pd.DataFrame(rows, columns=["cur", "t", "o", "h", "l", "c"]); d["t"] = pd.to_datetime(d.t, unit="ms")
    d = d.drop_duplicates(["cur", "t"]).sort_values(["cur", "t"]); d.to_parquet(f); return f"{len(d)} rows"

if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    if "--smoke" in sys.argv:
        START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-29"); SYMS = ["BTCUSDT", "1000PEPEUSDT"]
    try: print("DVOL", dvol(out), flush=True)
    except Exception as e: print("DVOL failed:", repr(e), flush=True)
    for s in SYMS:
        t0 = time.time(); print(*build(s, out), f"{time.time() - t0:.0f}s", flush=True)
