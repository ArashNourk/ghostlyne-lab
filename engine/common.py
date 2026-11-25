"""Ghostlyne Odds engine (v2).

What a forecast is: the modeled probability that Binance's mark price reaches a standardized isolated-margin
liquidation level for a position entered at the next UTC open, before that UTC day ends.

Information set (identical in backtest and production): every complete day before day d, plus day d truncated at
23:15 UTC (15-minute candles opened 00:00-23:00). Production publishes shortly after 23:15 UTC on day d for day d+1.
"""
import io, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np, pandas as pd, requests
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","BCHUSDT",
        "TRXUSDT","SUIUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","ATOMUSDT","FILUSDT","ETCUSDT","UNIUSDT","AAVEUSDT",
        "1000PEPEUSDT","1000SHIBUSDT","XLMUSDT","ALGOUSDT"]
SPOT = {"1000PEPEUSDT": ("PEPEUSDT", 1000), "1000SHIBUSDT": ("SHIBUSDT", 1000)}
CUT = pd.Timedelta(hours=23, minutes=15)
MMR = 0.005                                  # standardized maintenance margin rate (Binance tier-1 is 0.4%-1% depending on market and size)
LEVERAGE = [40, 20, 15, 10, 7, 5]            # descending leverage = ascending distance
# The max-leverage recommendation never names 40x: in the backtest, the rare days where 40x looked safe were liquidated 7-10% of the time.
MAXLEV_CAP = 20
DIST = {L: round(1 / L - MMR, 4) for L in LEVERAGE}
TEX = ["v1", "v7", "v30", "ret1", "ret7", "dd30", "ru30", "b_v7", "b_ret1"]
BASE = "https://data.binance.vision/data/futures/um"
S = requests.Session(); S.headers["User-Agent"] = "ghostlyne"

# ---------------------------------------------------------------- data
def _get(url):
    for _ in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404: return None
            if r.status_code == 200: return r.content
        except Exception: time.sleep(1)
    return None

def _rows(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z: raw = z.read(z.namelist()[0])
    first = raw.split(b"\n", 1)[0].decode(errors="ignore").lower()
    d = pd.read_csv(io.BytesIO(raw), header=0 if "open" in first else None)
    d = d.iloc[:, :5]; d.columns = ["t", "o", "h", "l", "c"]
    d["t"] = pd.to_datetime(pd.to_numeric(d.t), unit="ms")
    return d.astype({"o": float, "h": float, "l": float, "c": float})

def series(sym, kind, interval, cache: Path, through: pd.Timestamp, start="2021-01-01"):
    """Raw candles (open time t, o/h/l/c) for complete UTC days up to `through`, cached incrementally.
    kind: 'klines' (traded price) or 'markPriceKlines' (mark price)."""
    p = cache / f"{kind}_{interval}" / f"{sym}.parquet"; p.parent.mkdir(parents=True, exist_ok=True)
    have = pd.read_parquet(p) if p.exists() else pd.DataFrame({"t": pd.Series(dtype="datetime64[ns]"), **{c: pd.Series(dtype=float) for c in "ohlc"}})
    nxt = (have.t.max().normalize() + pd.Timedelta(days=1)) if len(have) else pd.Timestamp(start)
    frames = [have]; cur_month = through.replace(day=1)
    for m in pd.date_range(nxt.replace(day=1), through, freq="MS"):
        if m < cur_month and nxt <= m:                       # whole month needed and archived monthly
            b = _get(f"{BASE}/monthly/{kind}/{sym}/{interval}/{sym}-{interval}-{m:%Y-%m}.zip")
            if b: frames.append(_rows(b)); continue
        for d in pd.date_range(max(m, nxt), min(m + pd.offsets.MonthEnd(0), through)):
            b = _get(f"{BASE}/daily/{kind}/{sym}/{interval}/{sym}-{interval}-{d:%Y-%m-%d}.zip")
            if b: frames.append(_rows(b))
    out = pd.concat(frames).drop_duplicates("t", keep="last").sort_values("t")
    out = out[out.t < through + pd.Timedelta(days=1)]
    out.to_parquet(p); return out

def daily_from(raw):
    g = raw.assign(date=raw.t.dt.normalize()).groupby("date")
    return pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last()})

def truncated_from_15m(raw, min_bars=85):
    """Each day aggregated over 15-minute candles opened 00:00-23:00 UTC, i.e. information available at 23:15 UTC."""
    r = raw[(raw.t - raw.t.dt.normalize()) < CUT]
    g = r.assign(date=r.t.dt.normalize()).groupby("date")
    d = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(), "n": g.o.size()})
    return d[d.n >= min_bars].drop(columns="n")

def spot_truncated_today(sym, day: pd.Timestamp):
    """Production only: today's 00:00-23:15 candle from the public spot market-data API (futures API is geo-restricted
    from GitHub's runners). Ranges and returns are scale-free; 1000x contracts are rescaled."""
    spot, mult = SPOT.get(sym, (sym, 1))
    t0 = int(day.value // 10**6); t1 = int((day + CUT).value // 10**6) - 1
    r = S.get("https://data-api.binance.vision/api/v3/klines", params={"symbol": spot, "interval": "15m", "startTime": t0, "endTime": t1, "limit": 100}, timeout=30)
    if r.status_code != 200: return None
    k = pd.DataFrame(r.json()).iloc[:, :5]; k.columns = ["t", "o", "h", "l", "c"]
    k["t"] = pd.to_datetime(k.t, unit="ms"); k[["o", "h", "l", "c"]] = k[["o", "h", "l", "c"]].astype(float) * mult
    k = k[(k.t - day) < CUT]
    if len(k) < 85: return None
    return pd.Series({"o": k.o.iloc[0], "h": k.h.max(), "l": k.l.min(), "c": k.c.iloc[-1]}, name=day)

def load(cache: Path, through: pd.Timestamp, symbols=SYMS):
    """Complete days up to `through`: traded daily candles, mark-price daily candles, 23:15-truncated daily candles."""
    def one(s):
        full = daily_from(series(s, "klines", "1d", cache, through))
        mark = daily_from(series(s, "markPriceKlines", "1d", cache, through))
        tr = truncated_from_15m(series(s, "klines", "15m", cache, through))
        return s, full, mark, tr
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, symbols))
    return {s: {"full": f, "mark": m, "trunc": t} for s, f, m, t in res if len(f) > 60 and len(t) > 60}

# ---------------------------------------------------------------- features and labels
def features(data):
    """One row per (symbol, day d): features from complete days < d plus day d truncated at 23:15; labels from day d+1
    (entry at the traded open, barrier tested on mark price; last-price labels kept for comparison)."""
    def parts(s):
        f, t, m = data[s]["full"], data[s]["trunc"], data[s]["mark"]
        idx = t.index
        F = f.reindex(idx.union(f.index)).sort_index()
        pk_f = np.log(F.h / F.l) ** 2 / (4 * np.log(2)); rng_f = np.log(F.h / F.l)
        pk_t = (np.log(t.h / t.l) ** 2 / (4 * np.log(2))).reindex(F.index); rng_t = np.log(t.h / t.l).reindex(F.index); c_t = t.c.reindex(F.index)
        prevC = F.c.shift(1)
        out = pd.DataFrame(index=F.index)
        out["v1"] = np.log(pk_t + 1e-8)
        out["v7"] = np.log((pk_f.shift(1).rolling(6).sum() + pk_t) / 7)
        out["v30"] = np.log((pk_f.shift(1).rolling(29).sum() + pk_t) / 30)
        out["atr14"] = np.log((rng_f.shift(1).rolling(13).sum() + rng_t) / 14)
        out["ret1"] = np.log(c_t / prevC); out["ret7"] = np.log(c_t / F.c.shift(7))
        hi = np.maximum(F.c.shift(1).rolling(29).max(), c_t); lo = np.minimum(F.c.shift(1).rolling(29).min(), c_t)
        out["dd30"] = np.log(c_t / hi); out["ru30"] = np.log(c_t / lo)
        out["ret_full"] = np.log(F.c / prevC); out["sq_ret_full"] = out.ret_full ** 2      # complete-day returns, for baselines
        nO = F.o.shift(-1); M = m.reindex(F.index)
        out["next_down"] = np.log(M.l.shift(-1) / nO); out["next_up"] = np.log(M.h.shift(-1) / nO)
        out["next_down_last"] = np.log(F.l.shift(-1) / nO); out["next_up_last"] = np.log(F.h.shift(-1) / nO)
        out["trunc_ok"] = c_t.notna()
        return out
    P = {s: parts(s) for s in data}
    rows = []
    for s, o in P.items():
        o = o.copy(); b = P["BTCUSDT"].reindex(o.index)
        o["b_v7"] = b.v7; o["b_ret1"] = b.ret1; o["sym"] = s; rows.append(o)
    D = pd.concat(rows); D.index.name = "Date"; D = D.reset_index()
    D = D[D.trunc_ok & D.v30.notna() & D.b_v7.notna() & D.atr14.notna()].drop(columns="trunc_ok")
    return D.sort_values(["Date", "sym"]).reset_index(drop=True)

def target(D, side, k, price="mark"):
    col = ("next_down" if side == "long" else "next_up") + ("" if price == "mark" else "_last")
    v = D[col]; hit = (v <= np.log(1 - k)) if side == "long" else (v >= np.log(1 + k))
    return hit.astype(float).where(v.notna())

# ---------------------------------------------------------------- model, calibration, monotonicity
def fit(X, y):
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=4000)).fit(X, y)

def calibrate_walk(D, raw, y, cal_months=12):
    """Isotonic map refit each month on the previous cal_months of out-of-sample (raw, y); applied to the next month."""
    cal = np.full(len(D), np.nan)
    for ms in pd.date_range(D.Date.min().replace(day=1), D.Date.max(), freq="MS"):
        te = np.where((D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)) & ~np.isnan(raw))[0]
        past = np.where((D.Date >= ms - pd.DateOffset(months=cal_months)) & (D.Date < ms - pd.Timedelta(days=1)) & ~np.isnan(raw) & ~np.isnan(y))[0]
        if len(te) and len(past) > 1000 and y[past].sum() >= 20:
            cal[te] = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999).fit(raw[past], y[past]).predict(raw[te])
    return cal

def model_walk(D, side, k, start):
    y = target(D, side, k).values; raw = np.full(len(D), np.nan)
    for ms in pd.date_range(start, D.Date.max(), freq="MS"):
        te = np.where((D.Date >= ms) & (D.Date < ms + pd.offsets.MonthBegin(1)))[0]
        tr = np.where((D.Date < ms - pd.Timedelta(days=1)) & ~np.isnan(y))[0]
        if len(te) == 0 or np.nansum(y[tr]) < 25: continue
        raw[te] = fit(D.loc[tr, TEX], y[tr]).predict_proba(D.loc[te, TEX])[:, 1]
    return raw, y

def pav_increasing(v):
    """Pool-adjacent-violators: closest non-decreasing sequence (least squares, equal weights)."""
    vals, wts = [], []
    for x in v:
        vals.append(x); wts.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            w = wts[-2] + wts[-1]; m = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / w
            vals[-2:] = [m]; wts[-2:] = [w]
    return np.repeat(vals, wts)

def monotone(P):
    """P: array [n, len(LEVERAGE)] ordered 40x..5x (decreasing leverage). Odds must not increase as leverage falls."""
    out = P.copy(); bad = 0
    for i in range(len(P)):
        row = P[i]
        if np.isnan(row).any(): continue
        if np.any(np.diff(row) > 1e-12): bad += 1
        out[i] = pav_increasing(row[::-1])[::-1]
    return out, bad

# ---------------------------------------------------------------- baselines (all on the same information set)
def reflection(sd, side, k):
    b = -np.log(1 - k) if side == "long" else np.log(1 + k)
    return np.clip(2 * (1 - norm.cdf(b / sd)), 1e-5, 0.9999)

def ewma_sd(D, lam=0.94):
    """RiskMetrics EWMA of squared daily returns over complete days, updated with today's 23:15 return."""
    out = np.full(len(D), np.nan)
    for s, g in D.groupby("sym"):
        sq = g.sq_ret_full.shift(1).fillna(g.sq_ret_full.median())    # complete-day returns through d-1
        prev = sq.ewm(alpha=1 - lam, adjust=False).mean()
        out[g.index] = np.sqrt(lam * prev.values + (1 - lam) * (g.ret1.values ** 2))
    return out

def garch_sd(D, start):
    """GARCH(1,1) with Student-t errors per market, refit monthly on complete-day returns before the month.
    Variance is filtered daily on complete days; the forecast for day d+1 uses day d's 23:15 return as the last shock."""
    from arch import arch_model
    out = np.full(len(D), np.nan)
    for s, g in D.groupby("sym"):
        idx = g.index.values; dates = g.Date.values; rf = g.ret_full.values * 100; rt = g.ret1.values * 100
        for ms in pd.date_range(start, g.Date.max(), freq="MS"):
            tr = np.where(dates < np.datetime64(ms - pd.Timedelta(days=1)))[0]
            te = set(np.where((dates >= np.datetime64(ms)) & (dates < np.datetime64(ms + pd.offsets.MonthBegin(1))))[0])
            if not te or len(tr) < 250: continue
            x = rf[tr]; ok = ~np.isnan(x); x = x[ok][-1500:]
            try:
                res = arch_model(x, vol="GARCH", p=1, q=1, dist="t", mean="Zero").fit(disp="off")
            except Exception: continue
            w, a, bb = res.params["omega"], res.params["alpha[1]"], res.params["beta[1]"]
            s2 = float(res.conditional_volatility[-1] ** 2)
            for j in range(tr[-1] + 1, max(te) + 1):
                prev = rf[j - 1] if not np.isnan(rf[j - 1]) else 0.0
                s2 = w + a * prev ** 2 + bb * s2                        # day d variance given complete days through d-1
                if j in te and not np.isnan(rt[j]): out[idx[j]] = np.sqrt(w + a * rt[j] ** 2 + bb * s2) / 100
    return out

def fhs_prob(D, side, k, sd, window=730):
    """Filtered historical simulation: empirical distribution of the market's past standardized next-day barrier moves."""
    col = "next_down" if side == "long" else "next_up"; out = np.full(len(D), np.nan)
    b = np.log(1 - k) if side == "long" else np.log(1 + k)
    for s, g in D.groupby("sym"):
        z = (g[col] / sd[g.index]).values; thr = b / sd[g.index]
        for j, i in enumerate(g.index):
            past = z[max(0, j - window):max(0, j - 1)]; past = past[~np.isnan(past)]
            if len(past) < 250: continue
            out[i] = ((past <= thr[j]).mean() if side == "long" else (past >= thr[j]).mean())
    return np.clip(out, 1e-5, 0.9999)

def rolling_freq(D, side, k, window=365):
    y = target(D, side, k); out = np.full(len(D), np.nan)
    for s, g in D.groupby("sym"):
        out[g.index] = y.loc[g.index].shift(1).rolling(window, min_periods=120).mean().values
    return out

def textbook(D, side, k):
    return reflection(np.exp(D.atr14.values) / 1.6, side, k)
