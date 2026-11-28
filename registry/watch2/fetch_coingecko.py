"""Download hourly BTC/USD OHLC from CoinGecko Analyst into data/btc_hourly.csv (local only, never committed).

Usage:  COINGECKO_API_KEY=... python3 fetch_coingecko.py
CoinGecko's terms discourage long-term storage: the file is for this research run and is deleted when the plan ends.
"""
import os, sys, time, json, urllib.request
import pandas as pd

KEY = os.environ.get("COINGECKO_API_KEY")
if not KEY:
    sys.exit("COINGECKO_API_KEY is not set (keep it in an environment secret, never in the repository).")
BASE = "https://pro-api.coingecko.com/api/v3/coins/bitcoin/ohlc/range"
start = pd.Timestamp("2018-02-09", tz="UTC")
end = pd.Timestamp.now(tz="UTC").normalize().replace(day=1)          # last complete month ends here
rows, t = [], start
while t < end:
    u = min(t + pd.Timedelta(days=31), end)
    url = f"{BASE}?vs_currency=usd&interval=hourly&from={int(t.timestamp())}&to={int(u.timestamp())}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"x-cg-pro-api-key": KEY, "accept": "application/json"})
            data = json.load(urllib.request.urlopen(req, timeout=60))
            break
        except Exception as e:
            if attempt == 4:
                sys.exit(f"fetch failed for {t.date()}..{u.date()}: {e}")      # fail loudly, never fill silently
            time.sleep(2 ** attempt)
    if not data:
        sys.exit(f"empty response for {t.date()}..{u.date()}")
    rows += data
    t = u
    time.sleep(0.25)
df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"]).drop_duplicates("ts").sort_values("ts")
df["ts"] = pd.to_datetime(df.ts, unit="ms", utc=True)                    # close time of each candle
df = df[df.ts <= end]
gaps = df.ts.diff().dt.total_seconds().div(3600).fillna(1)
print(f"{len(df)} candles {df.ts.iloc[0]} .. {df.ts.iloc[-1]}; spacing other than 1h: {(gaps != 1).sum()}; largest gap {gaps.max():.0f}h")
os.makedirs("data", exist_ok=True)
df.to_csv("data/btc_hourly.csv", index=False)
