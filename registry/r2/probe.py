"""R2 data feasibility probe: coverage only (first/last date, count). No values are written."""
import io, json, re, time, requests, pandas as pd
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
YAHOO = ["MU","000660.KS","005930.KS","2408.TW","2344.TW","3260.TWO","4967.TW","ACWI","SOXX",
 "AMAT","8035.T","ASML","ETN","ABBN.SW","HG=F","SI=F","ALI=F","PA=F","LIN","APD","4063.T","3436.T","ENTG","REMX",
 "CL=F","NG=F","1919.HK","MAERSK-B.CO","2603.TW","FDX","UNP","XLU","BHP","FCX","CAT","URA",
 "BTC-USD","ZC=F","TM","ALB","OJ=F","HE=F","LE=F"]
FRED = ["DEXKOUS","DEXTAUS","DEXJPUS","DEXCHUS","DTWEXBGS","DCOILWTICO","DHHNGSP"]
def yahoo(t):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}"
    r = requests.get(u, params={"period1": 946684800, "period2": int(time.time()), "interval": "1d", "events": "split,div"}, headers=UA, timeout=60)
    r.raise_for_status(); j = r.json()["chart"]["result"][0]
    ts = pd.to_datetime(j["timestamp"], unit="s"); adj = j["indicators"].get("adjclose", [{}])[0].get("adjclose") or j["indicators"]["quote"][0]["close"]
    return pd.Series(adj, index=ts).dropna()
def stooq(t):
    r = requests.get("https://stooq.com/q/d/l/", params={"s": t, "i": "d"}, headers=UA, timeout=60); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text)); return pd.Series(df["Close"].values, index=pd.to_datetime(df["Date"]))
def fred(s):
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": s}, headers=UA, timeout=60); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text)); v = pd.to_numeric(df.iloc[:, 1], errors="coerce"); return pd.Series(v.values, index=pd.to_datetime(df.iloc[:, 0])).dropna()
def nino_weekly():
    r = requests.get("https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for", headers=UA, timeout=60); r.raise_for_status()
    rows = []
    for line in r.text.splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})", line)
        if m:
            nums = re.findall(r"-?\d+\.\d", line[10:])
            if len(nums) >= 8: rows.append((pd.to_datetime(m.group(1), format="%d%b%Y"), float(nums[5])))  # Nino3.4 anomaly
    return pd.Series(dict(rows))
def mops(roc_year, month):
    u = f"https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_{roc_year}_{month}_0.html"
    r = requests.get(u, headers=UA, timeout=60); r.raise_for_status(); r.encoding = "big5"
    return ("2408" in r.text, "2344" in r.text, len(r.text))
cov, miss = {}, {}
def rec(k, s, src):
    s = s.sort_index(); cov[k] = {"src": src, "first": str(s.index[0].date()), "last": str(s.index[-1].date()), "n": int(len(s))}
for t in YAHOO:
    try: rec(t, yahoo(t), "yahoo")
    except Exception as e:
        miss[t] = "yahoo: " + repr(e)[:120]
        try: rec(t, stooq(t.lower().replace(".ks", ".kr")), "stooq"); miss.pop(t)
        except Exception as e2: miss[t] += " | stooq: " + repr(e2)[:120]
    time.sleep(0.4)
for s in FRED:
    try: rec(s, fred(s), "fred")
    except Exception as e: miss[s] = repr(e)[:150]
try: rec("NINO34_W", nino_weekly(), "noaa-cpc")
except Exception as e: miss["NINO34_W"] = repr(e)[:150]
mo = {}
for y, m in [(102, 1), (108, 6), (114, 9)]:
    try: mo[f"{y}_{m}"] = mops(y, m)
    except Exception as e: mo[f"{y}_{m}"] = repr(e)[:150]
try: rb = requests.get("https://www.trendforce.com/robots.txt", headers=UA, timeout=30).text[:1500]
except Exception as e: rb = repr(e)
import os; os.makedirs("out", exist_ok=True)
json.dump({"coverage": cov, "missing": miss, "mops_monthly_revenue": mo, "trendforce_robots": rb}, open("out/r2_coverage.json", "w"), indent=1)
print(json.dumps({"ok": len(cov), "missing": miss, "mops": mo}, indent=1))
