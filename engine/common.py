"""Ghostlyne Odds engine: shared data access, features and the calibrated texture model.
Question each forecast answers: what is the probability that price moves far enough against a position opened at
today's UTC open to reach its liquidation level before the UTC day ends?"""
import io, zipfile, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd, requests
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","BCHUSDT",
        "TRXUSDT","SUIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","ATOMUSDT","FILUSDT","ETCUSDT","UNIUSDT","AAVEUSDT",
        "1000PEPEUSDT","1000SHIBUSDT","XLMUSDT","ALGOUSDT"]
SPOT = {"1000PEPEUSDT": "PEPEUSDT", "1000SHIBUSDT": "SHIBUSDT"}   # ranges are scale-free, so spot top-ups work for these
# leverage -> distance to liquidation for isolated margin with ~0.5% maintenance margin (exact level varies by exchange and size)
LEVERAGE = [40, 20, 15, 10, 7, 5]
DIST = {L: round(1 / L - 0.005, 4) for L in LEVERAGE}
TEX = ["v1", "v7", "v30", "ret1", "ret7", "dd30", "ru30", "b_v7", "b_ret1"]
BASE = "https://data.binance.vision/data/futures/um"
S = requests.Session(); S.headers["User-Agent"] = "ghostlyne"
KCOLS = ["open_time","open","high","low","close","volume","close_time","quote_volume","count","taker_buy_volume","taker_buy_quote_volume","ignore"]

def _get(url):
    for _ in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404: return None
            if r.status_code == 200: return r.content
        except Exception: pass
    return None

def _zip_csv(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z: raw = z.read(z.namelist()[0])
    first = raw.split(b"\n", 1)[0].decode(errors="ignore")
    hdr = 0 if "open" in first.lower() else None
    d = pd.read_csv(io.BytesIO(raw), header=hdr, names=None if hdr == 0 else KCOLS)
    d.columns = KCOLS[:d.shape[1]]; return d

def _norm(d):
    d = d.copy(); d["date"] = pd.to_datetime(pd.to_numeric(d.open_time), unit="ms").dt.normalize()
    for c in ["open", "high", "low", "close"]: d[c] = d[c].astype(float)
    return d[["date", "open", "high", "low", "close"]]

def candles(sym, cache: Path, through: pd.Timestamp):
    """Daily futures candles: monthly archives, then daily archives, then a spot top-up for the latest days."""
    cache.mkdir(parents=True, exist_ok=True); p = cache / f"{sym}.parquet"
    have = pd.read_parquet(p) if p.exists() else pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), **{c: pd.Series(dtype=float) for c in ["open", "high", "low", "close"]}})
    last = have.date.max() if len(have) else pd.Timestamp("2020-12-31")
    frames = [have]
    month_start = (last + pd.Timedelta(days=1)).replace(day=1)
    for m in pd.date_range(month_start, through, freq="MS"):
        if m + pd.offsets.MonthEnd(0) < through.replace(day=1):
            b = _get(f"{BASE}/monthly/klines/{sym}/1d/{sym}-1d-{m:%Y-%m}.zip")
            if b: frames.append(_norm(_zip_csv(b))); continue
        for d in pd.date_range(max(m, last + pd.Timedelta(days=1)), min(m + pd.offsets.MonthEnd(0), through)):
            b = _get(f"{BASE}/daily/klines/{sym}/1d/{sym}-1d-{d:%Y-%m-%d}.zip")
            if b: frames.append(_norm(_zip_csv(b)))
    out = pd.concat(frames).drop_duplicates("date", keep="last").sort_values("date")
    got = out.date.max() if len(out) else last
    if got < through:   # latest days not yet archived: public market-data API (spot)
        try:
            r = S.get("https://data-api.binance.vision/api/v3/klines", params={"symbol": SPOT.get(sym, sym), "interval": "1d", "limit": 10}, timeout=30)
            if r.status_code == 200:
                k = pd.DataFrame(r.json(), columns=KCOLS); k = _norm(k)
                k = k[(k.date > got) & (k.date <= through)]
                if len(out) and len(k) and sym in SPOT:   # rescale spot units to the 1000x contract
                    k[["open", "high", "low", "close"]] *= 1000
                out = pd.concat([out, k]).drop_duplicates("date", keep="first").sort_values("date")
        except Exception: pass
    out["date"] = pd.to_datetime(out["date"]); out[["open", "high", "low", "close"]] = out[["open", "high", "low", "close"]].astype(float)
    out = out[out.date <= through]
    out.to_parquet(p); return out.set_index("date")

def load_all(cache: Path, through: pd.Timestamp):
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda s: (s, candles(s, cache, through)), SYMS))
    return {s: d for s, d in res if len(d) > 60}

def features(kl):
    idx = sorted(set().union(*[k.index for k in kl.values()]))
    O, H, L, C = [pd.DataFrame({s: k[c] for s, k in kl.items()}).reindex(idx) for c in ["open", "high", "low", "close"]]
    down, up, rng, ret = np.log(L / O), np.log(H / O), np.log(H / L), np.log(C / C.shift())
    pk = rng ** 2 / (4 * np.log(2)); rows = []
    for s in kl:
        f = pd.DataFrame(index=pd.DatetimeIndex(idx, name="Date"))
        f["v1"] = np.log(pk[s] + 1e-8); f["v7"] = np.log(pk[s].rolling(7).mean()); f["v30"] = np.log(pk[s].rolling(30).mean())
        f["atr14"] = np.log(rng[s].rolling(14).mean()); f["ret1"] = ret[s]; f["ret7"] = np.log(C[s]).diff(7)
        f["dd30"] = np.log(C[s] / C[s].rolling(30).max()); f["ru30"] = np.log(C[s] / C[s].rolling(30).min())
        f["b_v7"] = np.log(pk["BTCUSDT"].rolling(7).mean()); f["b_ret1"] = ret["BTCUSDT"]
        f["next_down"] = down[s].shift(-1); f["next_up"] = up[s].shift(-1); f["close"] = C[s]; f["sym"] = s
        rows.append(f)
    D = pd.concat(rows).reset_index()
    return D.dropna(subset=["v30", "atr14", "b_v7"]).reset_index(drop=True)

def target(D, side, k):
    v = D.next_down if side == "long" else D.next_up
    hit = (v <= np.log(1 - k)) if side == "long" else (v >= np.log(1 + k))
    return hit.astype(float).where(v.notna())

def fit(X, y):
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=4000)).fit(X, y)

def walk_calibrated(D, side, k, start, cal_months=12):
    """Out-of-sample probabilities: monthly refit on all prior data; isotonic calibration fitted on the
    previous cal_months of genuinely out-of-sample predictions (none for the first cal_months)."""
    y = target(D, side, k).values; raw = np.full(len(D), np.nan); cal = np.full(len(D), np.nan)
    for ms in pd.date_range(start, D.Date.max(), freq="MS"):
        te = np.where((D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)))[0]
        tr = np.where((D.Date < ms - pd.Timedelta(days=1)) & ~np.isnan(y))[0]
        if len(te) == 0 or np.nansum(y[tr]) < 25: continue
        m = fit(D.loc[tr, TEX], y[tr]); raw[te] = m.predict_proba(D.loc[te, TEX])[:, 1]
        past = np.where((D.Date >= ms - pd.DateOffset(months=cal_months)) & (D.Date < ms - pd.Timedelta(days=1)) & ~np.isnan(raw) & ~np.isnan(y))[0]
        if len(past) > 2000 and y[past].sum() >= 20:
            iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999).fit(raw[past], y[past]); cal[te] = iso.predict(raw[te])
    return raw, cal, y

def textbook(D, side, k):
    from scipy.stats import norm
    sd = np.exp(D.atr14) / 1.6; b = -np.log(1 - k) if side == "long" else np.log(1 + k)
    return np.clip(2 * (1 - norm.cdf(b / sd)), 1e-4, 0.9999)
