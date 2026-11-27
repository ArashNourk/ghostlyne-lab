"""R4 data feasibility probe: coverage, structure and terms. No price values are written."""
import io, json, re, time, zipfile, requests, pandas as pd
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
out = {}
def rec(k, **v): out[k] = v; print(k, json.dumps(v, default=str)[:300], flush=True)
def get(u, **kw): return requests.get(u, headers=UA, timeout=90, **kw)

# ERCOT public MIS document lists (historical DAM and RTM load-zone/hub prices)
for name, rid in (("ercot_dam_hist", 13060), ("ercot_rtm_hist", 13061)):
    try:
        j = get(f"https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={rid}").json()
        docs = j["ListDocsByRptTypeRes"]["DocumentList"]; names = [d["Document"]["FriendlyName"] for d in docs]
        d0 = docs[0]["Document"]; z = get(f"https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={d0['DocID']}")
        zf = zipfile.ZipFile(io.BytesIO(z.content)); inner = zf.namelist()
        x = pd.read_excel(zf.open(inner[0]), sheet_name=None, nrows=3) if inner[0].lower().endswith(("xlsx", "xls")) else {"csv": pd.read_csv(zf.open(inner[0]), nrows=3)}
        rec(name, ok=True, n_docs=len(docs), docs=sorted(names)[:40], sample_file=inner[0], sheets=list(x)[:14], columns=[list(v.columns) for v in list(x.values())[:1]])
    except Exception as e: rec(name, ok=False, err=repr(e)[:200])
# ERCOT hourly load archives
try:
    h = get("https://www.ercot.com/gridinfo/load/load_hist").text; links = sorted(set(re.findall(r'href="([^"]+(?:zip|xlsx?))"', h)))
    rec("ercot_load_hist", ok=bool(links), n=len(links), links=links[:30])
except Exception as e: rec("ercot_load_hist", ok=False, err=repr(e)[:200])
# EIA-930 hourly balance (demand, generation by fuel) six-month files
try:
    u = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_2024_Jan_Jun.csv"; r = get(u, stream=True)
    head = next(r.iter_lines()).decode()[:600]; rec("eia930_balance", ok=r.status_code == 200, status=r.status_code, header=head)
except Exception as e: rec("eia930_balance", ok=False, err=repr(e)[:200])
try:
    r = get("https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_2018_Jul_Dec.csv", stream=True); rec("eia930_2018", ok=r.status_code == 200, status=r.status_code)
except Exception as e: rec("eia930_2018", ok=False, err=repr(e)[:200])
# EIA natural gas: Henry Hub daily spot, weekly storage (xls downloads, no key)
for k, u in (("eia_henryhub_daily", "https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls"), ("eia_storage_weekly", "https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls")):
    try:
        r = get(u); x = pd.read_excel(io.BytesIO(r.content), sheet_name="Data 1", skiprows=2)
        rec(k, ok=True, first=str(x.iloc[0, 0])[:10], last=str(x.iloc[-1, 0])[:10], n=len(x), cols=list(x.columns))
    except Exception as e: rec(k, ok=False, err=repr(e)[:200])
# NOAA GHCN-Daily station files (DFW, Houston IAH, Philadelphia, Boston Logan)
for k, st in (("noaa_dfw", "USW00003927"), ("noaa_iah", "USW00012960"), ("noaa_phl", "USW00013739"), ("noaa_bos", "USW00014739")):
    try:
        r = get(f"https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{st}.csv"); x = pd.read_csv(io.StringIO(r.text), usecols=["DATE", "TMAX", "TMIN"], low_memory=False)
        rec(k, ok=True, first=x.DATE.iloc[0], last=x.DATE.iloc[-1], n=len(x), tmax_missing=float(x.TMAX.isna().mean()))
    except Exception as e: rec(k, ok=False, err=repr(e)[:200])
# PJM Data Miner (expect key required), ISO-NE daily LMP CSV, NRC reactor status
try: r = get("https://api.pjm.com/api/v1/da_hrl_lmps?rowCount=1"); rec("pjm_dataminer", ok=r.status_code == 200, status=r.status_code, body=r.text[:200])
except Exception as e: rec("pjm_dataminer", ok=False, err=repr(e)[:200])
try: r = get("https://www.iso-ne.com/static-transform/csv/histRpts/da-lmp/WW_DALMP_ISO_20240102.csv"); rec("isone_da_lmp", ok=r.status_code == 200, status=r.status_code, head=r.text[:300])
except Exception as e: rec("isone_da_lmp", ok=False, err=repr(e)[:200])
try: r = get("https://www.nrc.gov/reading-rm/doc-collections/event-status/reactor-status/2015/20150105ps.html"); rec("nrc_reactor_status_2015", ok=r.status_code == 200, status=r.status_code, len=len(r.text))
except Exception as e: rec("nrc_reactor_status_2015", ok=False, err=repr(e)[:200])
# Market series via Yahoo (research use only, never redistributed)
def yahoo(t):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}", params={"period1": 946684800, "period2": int(time.time()), "interval": "1d"})
    j = r.json()["chart"]["result"][0]; ts = pd.to_datetime(j["timestamp"], unit="s"); return ts
for t in ["NG=F", "TTF=F", "BZ=F", "CL=F", "HG=F", "ZC=F", "BTC-USD", "CAD=X", "MXN=X", "SOXX", "NVDA", "DLR", "EQIX", "MARA", "RIOT", "VST", "XLU", "UNG", "BDRY", "LNG", "TELL"]:
    try: ts = yahoo(t); rec("yahoo_" + t, ok=True, first=str(ts.min().date()), last=str(ts.max().date()), n=len(ts))
    except Exception as e: rec("yahoo_" + t, ok=False, err=repr(e)[:120])
    time.sleep(0.3)
# Terms pages (first 1,500 characters of text)
for k, u in (("terms_ercot", "https://www.ercot.com/help/terms"), ("terms_eia", "https://www.eia.gov/about/copyrights_reuse.php"), ("terms_isone", "https://www.iso-ne.com/participate/support/web-conditions-of-use"), ("terms_pjm", "https://www.pjm.com/about-pjm/who-we-are/terms-of-use")):
    try:
        t = re.sub(r"<[^>]+>", " ", get(u).text); t = re.sub(r"\s+", " ", t)
        i = max(0, min([t.lower().find(w) for w in ("copyright", "public domain", "reuse", "terms") if t.lower().find(w) >= 0] or [0]))
        rec(k, ok=True, excerpt=t[i:i + 1500])
    except Exception as e: rec(k, ok=False, err=repr(e)[:150])
import os; os.makedirs("out", exist_ok=True); json.dump(out, open("out/r4_feasibility.json", "w"), indent=1, default=str)
