"""Daily production run (v2). Same information set as the backtest: complete days before the information day,
plus the information day truncated at 23:15 UTC. Forecasts cover the next UTC day.

Timing:
- run at or after 23:15 UTC on day d  -> forecast day d+1 (expected to be public before d+1 00:00, i.e. on time)
- run after midnight (00:00-12:00)     -> forecast the current day from yesterday's 23:15 information; it will be late
- run between 12:00 and 23:15          -> no forecast is due; score past forecasts and refresh the site only
Publication time is not recorded here: engine/publish_check.py records when the forecast is verifiably public."""
import hashlib, json, os, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import common as G

ROOT = Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / "engine/config.json"))
LEDGER, OUTCOMES, PUBS = ROOT / "ledger/forecasts.jsonl", ROOT / "ledger/outcomes.jsonl", ROOT / "ledger/publications.jsonl"
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
read = lambda p: [json.loads(l) for l in open(p)] if p.exists() else []
NAME = lambda s: s.replace("USDT", "").replace("1000", "")
START = pd.Timestamp("2023-01-01")

def ts(x): t = pd.Timestamp(x); return t.tz_convert(None) if t.tzinfo else t

def forecast(D, info_day):
    """Calibrated, leverage-monotone odds for rows dated info_day."""
    rows = np.where(D.Date == info_day)[0]; out = {}; method = {}
    for side in ["long", "short"]:
        Pm = np.full((len(rows), len(G.LEVERAGE)), np.nan); norm = {}; tb = {}
        for j, L in enumerate(G.LEVERAGE):
            k = G.DIST[L]; y = G.target(D, side, k).values
            raw, _ = G.model_walk(D, side, k, (info_day - pd.DateOffset(months=13)).replace(day=1))
            past = np.where((D.Date > info_day - pd.DateOffset(months=12)) & (D.Date < info_day) & ~np.isnan(raw) & ~np.isnan(y))[0]
            from sklearn.isotonic import IsotonicRegression
            tr = np.where(~np.isnan(y) & (D.Date < info_day))[0]
            if np.nansum(y[tr]) >= 25:
                pr = G.fit(D.loc[tr, G.TEX], y[tr]).predict_proba(D.loc[rows, G.TEX])[:, 1]
            else:
                pr = G.textbook(D.loc[rows], side, k); method[f"{side}_{L}"] = "textbook (too few events to fit)"
            if len(past) >= 500 and y[past].sum() >= 10:
                iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999).fit(raw[past], y[past]); Pm[:, j] = iso.predict(pr)
            else:
                iso = None; Pm[:, j] = pr; method.setdefault(f"{side}_{L}", "uncalibrated (too few recent events)")
            if L == 10:
                rec = np.where((D.Date > info_day - pd.Timedelta(days=90)) & (D.Date < info_day) & ~np.isnan(raw))[0]
                norm = pd.Series(iso.predict(raw[rec]) if iso is not None else raw[rec], index=D.sym.values[rec]).groupby(level=0).mean().to_dict()
                tb = dict(zip(D.sym.values[rows], G.textbook(D.loc[rows], side, k)))
        Pm, _ = G.monotone(Pm)
        for i, r in enumerate(rows):
            s = D.sym.values[r]; o = out.setdefault(s, {"long": {}, "short": {}, "normal10": {}, "textbook10": {}, "safe": {}})
            for j, L in enumerate(G.LEVERAGE): o[side][str(L)] = round(float(Pm[i, j]), 5)
            o["normal10"][side] = round(float(norm[s]), 5) if s in norm else None
            o["textbook10"][side] = round(float(tb[s]), 5)
            safe = [L for L in G.LEVERAGE if L <= G.MAXLEV_CAP and o[side][str(L)] <= 0.05]; o["safe"][side] = max(safe) if safe else None
    return out, method

# Risk levels (shared with the page). Ratio = today's modeled 10x odds / that market's 90-day normal 10x odds.
#   severe   ratio >= 2.5 and 10x odds >= 10%   neon pink
#   elevated ratio >= 1.5 and 10x odds >= 3%    soft pink
#   calm     ratio <  0.8                       electric green
#   normal   everything else                    white
def level(p, r):
    if r is None: return "normal"
    if r >= 2.5 and p >= 0.10: return "severe"
    if r >= 1.5 and p >= 0.03: return "elevated"
    if r < 0.8: return "calm"
    return "normal"

def daily_line(F):
    c = [(F[s][sd]["10"], F[s][sd]["10"] / F[s]["normal10"][sd], s, sd) for s in F for sd in ["long", "short"] if F[s]["normal10"].get(sd)]
    lv = {(s, sd): level(p, r) for p, r, s, sd in c}
    sev = sorted([x for x in c if lv[(x[2], x[3])] == "severe"], reverse=True)
    ele = sorted([x for x in c if lv[(x[2], x[3])] == "elevated"], reverse=True)
    calm_share = sum(v == "calm" for v in lv.values()) / max(len(lv), 1)
    if sev or ele:
        day = "severe" if sev else "elevated"; p, r, s, sd = (sev or ele)[0]; safe = F[s]["safe"][sd]; others = len(sev) + len(ele) - 1
        line = (f"{'Severe' if sev else 'Elevated'} risk. {NAME(s)} {sd}s lead: {100*p:.0f}% modeled odds of a 10x liquidation, {r:.1f}× normal. "
                + (f"At or below 5% odds, the most leverage is {safe}x." if safe else "No tested leverage (5x to 20x) is at or below 5% odds.") + (f" {others} other market side{'s' if others != 1 else ''} also elevated." if others else ""))
    else:
        p, r, s, sd = sorted(c, reverse=True)[0]
        day = "calm" if calm_share >= 0.5 else "normal"
        line = (f"{'A calm day' if day == 'calm' else 'A normal day'}: no market has elevated 10x liquidation odds"
                f"{', and most are below their usual level' if day == 'calm' else ''}. The highest is {NAME(s)} {sd}s at {100*p:.1f}%.")
    return line, {"symbol": s, "side": sd, "leverage": 10, "p": p, "ratio": round(r, 3), "day_level": day,
                  "levels": {f"{a}|{b}": v for (a, b), v in lv.items()}}

def main():
    now = ts(os.environ.get("GL_NOW") or pd.Timestamp.now("UTC"))
    today = now.normalize(); cut = today + G.CUT
    if now >= cut: info_day, mode = today, "on_schedule"
    elif now.hour < 12: info_day, mode = today - pd.Timedelta(days=1), "late"
    else: info_day, mode = None, "idle"
    complete_through = (info_day if info_day is not None else today) - pd.Timedelta(days=1)
    data = G.load(ROOT / "data", complete_through)
    led, outs, pubs = read(LEDGER), read(OUTCOMES), read(PUBS)
    pub_at = {p["forecast_hash"]: ts(p["verified_public_utc"]) for p in pubs}

    # 1) score closed days (mark-price barrier, entry at the traded open)
    done = {o["date"] for o in outs}
    for r in led:
        d = pd.Timestamp(r["date"])
        if r["date"] in done or d > complete_through: continue
        res = {}
        for s in r["forecasts"]:
            if s not in data or d not in data[s]["full"].index or d not in data[s]["mark"].index: continue
            o_ = data[s]["full"].loc[d, "o"]; m = data[s]["mark"].loc[d]
            dn, up = float(np.log(m.l / o_)), float(np.log(m.h / o_))
            dist = {L: v for L, v in r.get("liq_distance", {str(L): G.DIST[L] for L in G.LEVERAGE}).items()}
            res[s] = {"down": dn, "up": up, "long": {L: bool(dn <= np.log(1 - dist[L])) for L in r["forecasts"][s]["long"]},
                      "short": {L: bool(up >= np.log(1 + dist[L])) for L in r["forecasts"][s]["short"]}}
        p = pub_at.get(r["hash"]); on_time = bool(p is not None and p < d)
        o = {"date": r["date"], "forecast_hash": r["hash"], "scored_at_utc": pd.Timestamp.now("UTC").isoformat(), "on_time": on_time,
             "verified_public_utc": p.isoformat() + "Z" if p is not None else None, "labels": "mark price", "results": res}
        outs.append(o); OUTCOMES.parent.mkdir(exist_ok=True)
        with open(OUTCOMES, "a") as fh: fh.write(canon(o) + "\n")

    # 2) forecast
    if info_day is not None:
        day = (info_day + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        if not any(r["date"] == day for r in led):
            for s in list(data):
                t = G.spot_truncated_today(s, info_day)
                if t is None: data.pop(s); continue
                data[s]["trunc"] = pd.concat([data[s]["trunc"][data[s]["trunc"].index < info_day], t.to_frame().T])
            if "BTCUSDT" not in data: sys.exit(f"No 23:15 information for {info_day.date()}; not publishing.")
            D = G.features(data)
            if not (D.Date == info_day).any(): sys.exit("No feature rows for the information day; not publishing.")
            F, method = forecast(D, info_day); line, tgt = daily_line(F)
            rec = {"date": day, "computed_utc": now.isoformat() + "Z", "information_cut_utc": (info_day + G.CUT).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "window_start_utc": f"{day}T00:00:00Z", "run_mode": mode, "model_version": CFG["model_version"],
                   "assumptions": {"barrier": "Binance mark price", "margin": "isolated", "maintenance_margin_rate": G.MMR, "entry": "traded open of the UTC day",
                                   "latest_day_source": "spot 15m candles 00:00-23:15 UTC (futures archives for earlier days)"},
                   "liq_distance": {str(L): G.DIST[L] for L in G.LEVERAGE}, "method_exceptions": method, "line": line, "line_target": tgt, "forecasts": F,
                   "prev_hash": led[-1]["hash"] if led else "0" * 64}
            rec["hash"] = hashlib.sha256((rec["prev_hash"] + canon({k: v for k, v in rec.items() if k != "hash"})).encode()).hexdigest()
            led.append(rec); LEDGER.parent.mkdir(exist_ok=True)
            with open(LEDGER, "a") as fh: fh.write(canon(rec) + "\n")
            print(mode, day, line)

    # 3) site data
    od = {o["date"]: o for o in outs}; bins = np.array([0, .01, .02, .05, .1, .2, .35, 1.0]); agg = [[0, 0.0, 0] for _ in range(len(bins) - 1)]; hist = []
    for r in led:
        o = od.get(r["date"])
        if not o: continue
        if o.get("on_time"):
            for s, f in r["forecasts"].items():
                if s not in o["results"]: continue
                for sd in ["long", "short"]:
                    for L, p in f[sd].items():
                        b = min(int(np.searchsorted(bins, p, side="right") - 1), len(agg) - 1)
                        agg[b][0] += 1; agg[b][1] += p; agg[b][2] += int(o["results"][s][sd][L])
        t = r["line_target"]; rr = o["results"].get(t["symbol"])
        hist.append({"date": r["date"], "line": r["line"], "p": t["p"], "hit": None if rr is None else bool(rr[t["side"]][str(t["leverage"])]), "on_time": o.get("on_time", False), "day_level": t.get("day_level"), "hash": r["hash"][:12]})
    tdy = led[-1]; p_now = pub_at.get(tdy["hash"])
    bt = json.load(open(ROOT / "results/odds_backtest.json")) if (ROOT / "results/odds_backtest.json").exists() else {}
    site = {"generated_utc": pd.Timestamp.now("UTC").isoformat(), "day": tdy["date"], "day_level": tdy.get("line_target", {}).get("day_level"), "computed_utc": tdy.get("computed_utc", tdy.get("published_utc")),
            "information_cut_utc": tdy.get("information_cut_utc"), "verified_public_utc": p_now.isoformat() + "Z" if p_now is not None else None,
            "assumptions": tdy.get("assumptions"), "line": tdy["line"], "liq_distance": tdy["liq_distance"], "leverage": G.LEVERAGE,
            "forecasts": tdy["forecasts"], "hash": tdy["hash"],
            "ledger": {"days": len(led), "scored_days": len(outs), "on_time_scored": sum(bool(o.get("on_time")) for o in outs),
                       "calibration": [{"lo": float(bins[i]), "hi": float(bins[i + 1]), "n": a[0], "pred": a[1] / a[0] if a[0] else None, "actual": a[2] / a[0] if a[0] else None} for i, a in enumerate(agg)],
                       "recent": hist[-30:][::-1]},
            "backtest": bt, "waitlist_url": CFG.get("waitlist_url", ""), "contact_email": CFG.get("contact_email", "")}
    (ROOT / "docs/ledger").mkdir(parents=True, exist_ok=True)
    json.dump(site, open(ROOT / "docs/data.json", "w"), separators=(",", ":"))
    for src in [LEDGER, OUTCOMES, PUBS]:
        if src.exists(): (ROOT / "docs/ledger" / src.name).write_text(src.read_text())

if __name__ == "__main__": main()
