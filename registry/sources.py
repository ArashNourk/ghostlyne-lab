"""Ghostlyne Registry: free, reusable sources for pilot R1. Downloads only; no analysis."""
import io, re, time, requests, pandas as pd

UA = {"User-Agent": "ghostlyne-registry/0.1 (research; github.com/ArashNourk/ghostlyne-lab)"}

FRED = [
 # candidate targets (AI-infrastructure proxies, public US data)
 "PCU33443344","PCU334413334413","IPG3344S","A34SNO","PCU334111334111","IPG334S","A34SVS",
 # control
 "INDPRO",
 # D2 industrial inputs
 "PCOPPUSDM","PALUMUSDM","PNICKUSDM","PTINUSDM","PZINCUSDM","PCU325120325120","PCU325180325180","PCU335311335311",
 # D3 indirect: mining, machinery, freight, energy
 "IPMINE","PCU333333","PCU483111483111","PCU481112481112","FRGSHPUSM649NCIS","TSIFRGHT","DCOILWTICO","MHHNGSP","PCU221122221122","WPU0543","IPG2211S",
 # D4 remote: exchange rates, trade flows
 "DEXKOUS","DEXTAUS","DEXJPUS","DEXCHUS","DTWEXBGS","IMP5830","IMPKR","IMPCH","IMPJP",
 # D5 distant: competing demand
 "IPG3361T3S","ALTSALES","HOUST","PMAIZMTUSDM","PWHEAMTUSDM","PURANUSDM",
]

def fred(sid):
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": sid}, headers=UA, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]); df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()

def oni():
    r = requests.get("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", headers=UA, timeout=60); r.raise_for_status()
    seas = ["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"]
    rows = []
    for line in r.text.splitlines()[1:]:
        p = line.split()
        if len(p) >= 4 and p[0] in seas:
            m = seas.index(p[0]) + 1  # centre month of the season (DJF -> Jan)
            rows.append((pd.Timestamp(int(p[1]), m, 1), float(p[3])))
    return pd.DataFrame(rows, columns=["date", "value"])

def gscpi():
    u = "https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx"
    r = requests.get(u, headers=UA, timeout=60); r.raise_for_status()
    x = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None, engine="openpyxl")
    for name, s in x.items():
        s = s.dropna(how="all")
        d = pd.to_datetime(s.iloc[:, 0], errors="coerce"); v = pd.to_numeric(s.iloc[:, 1], errors="coerce")
        df = pd.DataFrame({"date": d, "value": v}).dropna()
        if len(df) > 200: return df
    raise ValueError("no GSCPI sheet")

def arizona_pdsi():
    base = "https://www.ncei.noaa.gov/pub/data/cirs/climdiv/"
    idx = requests.get(base, headers=UA, timeout=60).text
    f = sorted(set(re.findall(r'climdiv-pdsist-v[\d.]+-\d{8}', idx)))[-1]
    t = requests.get(base + f, headers=UA, timeout=120).text
    rows = []
    for line in t.splitlines():
        code = line[:10]
        if code[:3] == "002" and code[3:6] == "005":  # state 02 Arizona, element 05 = PDSI
            yr = int(code[6:10]); vals = line[10:].split()
            for m, v in enumerate(vals[:12], 1):
                v = float(v)
                if v > -99: rows.append((pd.Timestamp(yr, m, 1), v))
    return pd.DataFrame(rows, columns=["date", "value"])

OTHER = {"ONI": oni, "GSCPI": gscpi, "AZ_PDSI": arizona_pdsi}

def fetch_all():
    out, errors = {}, {}
    for sid in FRED:
        for attempt in range(3):
            try: out[sid] = fred(sid); break
            except Exception as e: errors[sid] = repr(e)[:200]; time.sleep(2)
        else: continue
        errors.pop(sid, None); time.sleep(0.5)
    for k, f in OTHER.items():
        try: out[k] = f()
        except Exception as e: errors[k] = repr(e)[:200]
    return out, errors
