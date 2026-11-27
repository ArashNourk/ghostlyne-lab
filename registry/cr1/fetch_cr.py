"""CR1 step 1: ERCOT historical real-time settlement point prices for all load zones and hubs (report 13061, public),
plus a no-download probe of how much nodal price history ERCOT keeps on its public MIS."""
import io, json, os, sys, time, zipfile, numpy as np, pandas as pd, requests
UA = {"User-Agent": "Mozilla/5.0 (research; ghostlyne-lab)"}
def get(u, **kw):
    for a in range(4):
        try: r = requests.get(u, headers=UA, timeout=240, **kw); r.raise_for_status(); return r
        except Exception: time.sleep(5 * (a + 1))
    raise RuntimeError(u)
def doclist(rid):
    return [d["Document"] for d in get(f"https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId={rid}").json()["ListDocsByRptTypeRes"]["DocumentList"]]
def rtm():
    frames = []
    for d in doclist(13061):
        z = zipfile.ZipFile(io.BytesIO(get(f"https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={d['DocID']}").content))
        for sh, x in pd.read_excel(z.open(z.namelist()[0]), sheet_name=None).items():
            sp = "Settlement Point" if "Settlement Point" in x else "Settlement Point Name"
            hr = "Delivery Hour" if "Delivery Hour" in x else "Hour Ending"
            x = x[x[sp].astype(str).str.startswith(("LZ_", "HB_"))]
            if x.empty: continue
            rep = x["Repeated Hour Flag"].astype(str).str.upper().eq("Y") if "Repeated Hour Flag" in x else pd.Series(False, index=x.index)
            x = x[~rep.values]
            f = pd.DataFrame({"date": pd.to_datetime(x["Delivery Date"]).values, "he": (lambda hs: pd.to_numeric(hs.str.split(":").str[0], errors="coerce").fillna(pd.to_numeric(hs, errors="coerce")))(x[hr].astype(str).str.strip()).values,
                              "sp": x[sp].values, "p": pd.to_numeric(x["Settlement Point Price"], errors="coerce").values})
            frames.append(f.groupby(["date", "he", "sp"]).p.mean().reset_index())
        print("rtm", d["FriendlyName"], flush=True)
    a = pd.concat(frames)
    return a.pivot_table(index=["date", "he"], columns="sp", values="p").sort_index()
if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    P = rtm(); P.to_csv("out/rt_zones_hourly.csv.gz", compression="gzip")
    probe = {}
    for name, rid in (("rtm_spp_nodal_15min_NP6-905", 12301), ("dam_spp_nodal_NP4-190", 12331), ("sced_60day_disclosure_NP3-965", 13052), ("rtm_lmp_bus_NP6-787", 11485)):
        try:
            ds = doclist(rid); names = sorted(d["FriendlyName"] for d in ds)
            probe[name] = dict(n_docs=len(ds), first=names[0] if names else None, last=names[-1] if names else None)
        except Exception as e: probe[name] = dict(error=repr(e)[:150])
    cov = {c: dict(first=str(P[c].dropna().index[0][0].date()), last=str(P[c].dropna().index[-1][0].date()), n=int(P[c].notna().sum())) for c in P.columns}
    json.dump(dict(coverage=cov, nodal_probe=probe), open("out/cr1_coverage.json", "w"), indent=1)
    open("out/SOURCES.md", "w").write("ERCOT report 13061 (NP6-785-ER) historical RTM load zone and hub prices, public; 15-minute prices averaged to hourly by Ghostlyne.\n")
    print(json.dumps(probe))
