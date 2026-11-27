"""R5 step 1: hourly public panel (ERCOT hub prices DA/RT; EIA-930 hourly for ERCOT, SPP, MISO, PJM) and daily on-chain hashprice.
ERCOT and EIA data permit use in analyses; hashprice inputs are public blockchain statistics (terms recorded in the probe)."""
import io, json, os, re, sys, time, zipfile, numpy as np, pandas as pd, requests
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
def get(u, **kw):
    for a in range(4):
        try: r = requests.get(u, headers=UA, timeout=240, **kw); r.raise_for_status(); return r
        except Exception: time.sleep(5 * (a + 1))
    raise RuntimeError(u)
HUBS = ["HB_NORTH", "HB_WEST", "HB_HOUSTON", "HB_SOUTH"]
def ercot(rid, kind):
    docs = get(f"https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={rid}").json()["ListDocsByRptTypeRes"]["DocumentList"]; frames = []
    for d in docs:
        d = d["Document"]; z = zipfile.ZipFile(io.BytesIO(get(f"https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={d['DocID']}").content))
        for sh, x in pd.read_excel(z.open(z.namelist()[0]), sheet_name=None).items():
            sp = "Settlement Point" if "Settlement Point" in x else "Settlement Point Name"; hr = "Hour Ending" if "Hour Ending" in x else "Delivery Hour"
            x = x[x[sp].isin(HUBS)]
            if x.empty: continue
            hs = x[hr].astype(str).str.strip(); h = pd.to_numeric(hs.str.split(":").str[0], errors="coerce").fillna(pd.to_numeric(hs, errors="coerce"))
            rep = x["Repeated Hour Flag"].astype(str).str.upper().eq("Y") if "Repeated Hour Flag" in x else False
            f = pd.DataFrame({"date": pd.to_datetime(x["Delivery Date"]).values, "he": h.values, "hub": x[sp].values, "p": pd.to_numeric(x["Settlement Point Price"], errors="coerce").values})
            f = f[~np.asarray(rep)] if not isinstance(rep, bool) else f
            frames.append(f.groupby(["date", "he", "hub"]).p.mean().reset_index())
        print(kind, d["FriendlyName"], flush=True)
    a = pd.concat(frames); a["col"] = kind + "_" + a.hub
    return a.pivot_table(index=["date", "he"], columns="col", values="p")
def eia930():
    frames = []
    for y in range(2015, 2027):
        for half in ("Jan_Jun", "Jul_Dec"):
            try:
                r = get(f"https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_{y}_{half}.csv")
                if not r.text.lstrip().startswith('"Balancing'): continue
                x = pd.read_csv(io.StringIO(r.text), thousands=",", low_memory=False)
            except Exception as e: print("skip", y, half, repr(e)[:80]); continue
            x = x[x["Balancing Authority"].isin(["ERCO", "SWPP", "MISO", "PJM"])].copy()
            for fuel in ("Wind", "Solar"):
                sub = [c for c in x.columns if re.match(r"^Net Generation \(MW\) from " + fuel, c) and "(Adjusted)" not in c and "(Imputed)" not in c]
                x["__" + fuel] = x[sub].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1) if sub else np.nan
            cols = {"Demand (MW)": "LOAD", "Demand Forecast (MW)": "LOADFC", "__Wind": "WIND", "__Solar": "SOLAR", "Net Generation (MW) from Natural Gas": "GASGEN", "Net Generation (MW) from Nuclear": "NUC"}
            f = pd.DataFrame({"date": pd.to_datetime(x["Data Date"]).values, "he": pd.to_numeric(x["Hour Number"], errors="coerce").values, "ba": x["Balancing Authority"].values})
            for c, n in cols.items():
                if c in x: f[n] = pd.to_numeric(x[c], errors="coerce").values
            frames.append(f); print("eia930", y, half, flush=True)
    a = pd.concat(frames).groupby(["date", "he", "ba"]).mean().unstack("ba")
    a.columns = [f"{v}_{b}" for v, b in a.columns]; return a
def hashprice():
    """USD per TH/s per day = miners' daily revenue (USD) / network hash rate (TH/s), from public on-chain statistics."""
    out = {}
    for name in ("miners-revenue", "hash-rate"):
        j = get(f"https://api.blockchain.info/charts/{name}", params={"timespan": "all", "format": "json", "sampled": "false"}).json()
        out[name] = pd.Series({pd.to_datetime(p["x"], unit="s").normalize(): p["y"] for p in j["values"]})
    d = pd.concat(out, axis=1).dropna(); d["HASHPRICE"] = d["miners-revenue"] / d["hash-rate"]
    return d
if __name__ == "__main__":
    os.makedirs("out", exist_ok=True); miss = {}; parts = []
    for name, f in (("ercot_dam", lambda: ercot(13060, "DA")), ("ercot_rtm", lambda: ercot(13061, "RT")), ("eia930", eia930)):
        try: parts.append(f())
        except Exception as e: miss[name] = repr(e)[:200]; print("FAILED", name, e)
    H = pd.concat(parts, axis=1).sort_index(); H.to_csv("out/hourly_panel.csv.gz", compression="gzip")
    try: hp = hashprice(); hp.to_csv("out/hashprice_daily.csv")
    except Exception as e: miss["hashprice"] = repr(e)[:200]; hp = None
    terms = {}
    for k, u in (("blockchain_com_terms", "https://www.blockchain.com/legal/terms"), ("cloudminecrypto_download", "https://cloudminecrypto.com/download")):
        try: t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", get(u).text)); i = max(0, t.lower().find("data")); terms[k] = t[i:i + 1200]
        except Exception as e: terms[k] = repr(e)[:150]
    cov = {c: dict(first=str(H[c].dropna().index[0][0].date()), last=str(H[c].dropna().index[-1][0].date()), n=int(H[c].notna().sum())) for c in H.columns if H[c].notna().any()}
    if hp is not None: cov["HASHPRICE"] = dict(first=str(hp.index.min().date()), last=str(hp.index.max().date()), n=int(len(hp)))
    json.dump(dict(coverage=cov, missing=miss, terms=terms), open("out/r5_coverage.json", "w"), indent=1)
    open("out/SOURCES.md", "w").write("ERCOT NP4-180-ER / NP6-785-ER hub prices (hourly; real-time 15-minute intervals averaged to hourly by Ghostlyne). EIA-930 hourly grid monitor (public domain). Hashprice computed by Ghostlyne from blockchain.com public charts (miners-revenue, hash-rate).\n")
    print(json.dumps(dict(n=len(cov), missing=miss)))
