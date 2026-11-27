"""R4 step 1: build the public daily panel (ERCOT, EIA, NOAA). These sources permit use in analyses and redistribution.
Market series from Yahoo are fetched later, inside the analysis job only, and never published."""
import io, json, os, re, time, zipfile, numpy as np, pandas as pd, requests
USED = {}
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
def get(u, **kw):
    for a in range(4):
        try: r = requests.get(u, headers=UA, timeout=180, **kw); r.raise_for_status(); return r
        except Exception: time.sleep(5 * (a + 1))
    raise RuntimeError(u)
HUBS = ["HB_NORTH", "HB_WEST", "HB_HOUSTON", "HB_SOUTH"]
def ercot(rid, kind):
    docs = get(f"https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={rid}").json()["ListDocsByRptTypeRes"]["DocumentList"]
    frames = []
    for d in docs:
        d = d["Document"]; z = zipfile.ZipFile(io.BytesIO(get(f"https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={d['DocID']}").content))
        for sh, x in pd.read_excel(z.open(z.namelist()[0]), sheet_name=None).items():
            sp = "Settlement Point" if "Settlement Point" in x else "Settlement Point Name"; hr = "Hour Ending" if "Hour Ending" in x else "Delivery Hour"
            x = x[x[sp].isin(HUBS)]
            if x.empty: continue
            hs = x[hr].astype(str).str.strip()
            h = pd.to_numeric(hs.str.split(":").str[0], errors="coerce").fillna(pd.to_numeric(hs, errors="coerce")).astype(float)
            frames.append(pd.DataFrame({"date": pd.to_datetime(x["Delivery Date"]), "hub": x[sp], "hour": h, "p": pd.to_numeric(x["Settlement Point Price"], errors="coerce")}))
        print(kind, d["FriendlyName"], flush=True)
    a = pd.concat(frames); out = {}
    for hub, g in a.groupby("hub"):
        out[f"{kind}_{hub}"] = g.groupby("date").p.mean()
        pk = g[(g.hour.between(7, 22)) & (g.date.dt.dayofweek < 5)]; out[f"{kind}_{hub}_PEAK"] = pk.groupby("date").p.mean()
    return out
def eia930():
    out = {}
    for y in range(2015, 2027):
        for half in ("Jan_Jun", "Jul_Dec"):
            u = f"https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_{y}_{half}.csv"
            try:
                r = get(u)
                if not r.text.lstrip().startswith('"Balancing'): continue
                x = pd.read_csv(io.StringIO(r.text), thousands=",", low_memory=False)
            except Exception as e:
                print("eia930 skip", y, half, repr(e)[:80], flush=True); continue
            x = x[x["Balancing Authority"].isin(["ERCO", "PJM", "MISO", "SWPP", "ISNE", "CISO"])]
            cols = {"Demand (MW)": "LOAD", "Demand Forecast (MW)": "LOADFC", "__Wind": "WIND", "__Solar": "SOLAR", "Net Generation (MW) from Natural Gas": "GASGEN", "Net Generation (MW) from Nuclear": "NUC"}
            x["date"] = pd.to_datetime(x["Data Date"])
            # From 2024 H2 EIA splits wind and solar into 'with/without integrated battery storage': sum all raw sub-columns
            for fuel in ("Wind", "Solar"):
                sub = [c for c in x.columns if re.match(r"^Net Generation \(MW\) from " + fuel, c) and "(Adjusted)" not in c and "(Imputed)" not in c]
                if sub:
                    x["__" + fuel] = x[sub].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1); USED.setdefault(f"{y}_{half}_{fuel}", sub)
            for c, n in cols.items():
                if c not in x: continue
                g = x.groupby(["Balancing Authority", "date"])[c].sum(min_count=20)
                for ba, s in g.groupby(level=0): out.setdefault(f"{n}_{ba}", []).append(s.droplevel(0))
            print("eia930", y, half, flush=True)
    return {k: pd.concat(v).sort_index() for k, v in out.items()}
def eia_xls(u, col):
    x = pd.read_excel(io.BytesIO(get(u).content), sheet_name="Data 1", skiprows=2); return pd.Series(x.iloc[:, 1].values, index=pd.to_datetime(x.iloc[:, 0])).dropna()
def noaa(st):
    x = pd.read_csv(io.StringIO(get(f"https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{st}.csv").text), usecols=["DATE", "TMAX", "TMIN"], low_memory=False)
    x = x[x.DATE >= "2009-01-01"]; t = ((x.TMAX + x.TMIN) / 2 / 10) * 9 / 5 + 32
    return pd.Series(t.values, index=pd.to_datetime(x.DATE)).dropna()
def nino():
    r = get("https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"); rows = {}
    for line in r.text.splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})", line); nums = re.findall(r"-?\d+\.\d", line[10:])
        if m and len(nums) >= 8: rows[pd.to_datetime(m.group(1), format="%d%b%Y")] = float(nums[5])
    return pd.Series(rows)
if __name__ == "__main__":
    S, miss = {}, {}
    for name, f in (("ercot_rtm", lambda: ercot(13061, "RT")), ("eia930", eia930), ("ercot_dam", lambda: ercot(13060, "DA"))):
        try: S.update(f())
        except Exception as e: miss[name] = repr(e)[:200]
    for k, u in (("HH_SPOT", "https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls"), ("STORAGE_L48", "https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls")):
        try: S[k] = eia_xls(u, k)
        except Exception as e: miss[k] = repr(e)[:200]
    for k, st in (("T_DFW", "USW00003927"), ("T_IAH", "USW00012960"), ("T_PHL", "USW00013739"), ("T_BOS", "USW00014739")):
        try: S[k] = noaa(st)
        except Exception as e: miss[k] = repr(e)[:200]
    try: S["NINO34"] = nino()
    except Exception as e: miss["NINO34"] = repr(e)[:200]
    os.makedirs("out", exist_ok=True)
    daily = pd.DataFrame({k: v for k, v in S.items() if k != "STORAGE_L48" and k != "NINO34"}).sort_index()
    daily.index.name = "date"; daily.to_csv("out/panel_daily.csv.gz", compression="gzip")
    S["STORAGE_L48"].rename("STORAGE_L48").to_csv("out/storage_weekly.csv"); S["NINO34"].rename("NINO34").to_csv("out/nino_weekly.csv")
    cov = {k: dict(first=str(v.dropna().index.min().date()), last=str(v.dropna().index.max().date()), n=int(v.notna().sum())) for k, v in S.items()}
    json.dump(dict(coverage=cov, missing=miss, eia930_wind_solar_columns=USED), open("out/panel_coverage.json", "w"), indent=1)
    open("out/SOURCES.md", "w").write("ERCOT public MIS reports NP4-180-ER and NP6-785-ER (historical DAM and RTM load zone and hub prices); ERCOT terms permit use of public raw data in compilations, charts and analyses. U.S. Energy Information Administration: EIA-930 hourly grid monitor, Henry Hub spot price, weekly working gas storage (public domain; Source: U.S. Energy Information Administration). NOAA NCEI GHCN-Daily and NOAA CPC weekly Nino 3.4 (public domain). Daily values are averages of hourly data computed by Ghostlyne.\n")
    print(json.dumps(dict(n=len(cov), missing=miss)))
