"""Every morning (after the UTC day closes): forecast today's liquidation odds for each perpetual, score yesterday,
append to the hash-chained ledger, and write docs/data.json for the live page."""
import json, hashlib, os, sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.isotonic import IsotonicRegression
sys.path.insert(0, str(Path(__file__).parent)); import common as G

ROOT = Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / "engine/config.json"))
LEDGER, OUTCOMES = ROOT / "ledger/forecasts.jsonl", ROOT / "ledger/outcomes.jsonl"
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
def read_jsonl(p): return [json.loads(l) for l in open(p)] if p.exists() else []
NAME = lambda s: s.replace("USDT", "").replace("1000", "")

def odds_today(D, side, lev, through):
    """Model fit on everything known; isotonic map learned from the last 12 months of out-of-sample predictions."""
    k = G.DIST[lev]; start = (through - pd.DateOffset(months=13)).replace(day=1)
    raw, cal, y = G.walk_calibrated(D, side, k, start, cal_months=12)
    past = np.where((D.Date > through - pd.DateOffset(months=12)) & ~np.isnan(raw) & ~np.isnan(y))[0]
    y_all = G.target(D, side, k).values; tr = np.where(~np.isnan(y_all))[0]
    m = G.fit(D.loc[tr, G.TEX], y_all[tr]); today = np.where(D.Date == through)[0]
    rt = m.predict_proba(D.loc[today, G.TEX])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=0.999).fit(raw[past], y[past])
    p = iso.predict(rt)
    norm90 = {}   # "normal" odds for each coin: mean calibrated out-of-sample odds over the prior 90 days
    recent = np.where((D.Date > through - pd.Timedelta(days=90)) & ~np.isnan(raw))[0]
    pr = pd.Series(iso.predict(raw[recent]), index=D.sym.values[recent])
    for s, v in pr.groupby(level=0).mean().items(): norm90[s] = float(v)
    tb = G.textbook(D.loc[today], side, k)
    return {D.sym.values[i]: {"p": float(pj), "normal": norm90.get(D.sym.values[i]), "textbook": float(tj)} for i, pj, tj in zip(today, p, tb)}

def main():
    # Timing rule: a forecast for UTC day X must be published before X 00:00 UTC.
    # Normal run (scheduled 23:15 UTC on X-1): X-1 is ~97% complete, so its in-progress candle stands in for the full day.
    # Late run (after midnight): forecast still targets the current day but is flagged late and excluded from calibration statistics.
    now = pd.Timestamp(os.environ.get("GL_NOW") or pd.Timestamp.now("UTC").tz_localize(None))
    today = now.normalize()
    if now.hour >= 12: last_complete, partial = today - pd.Timedelta(days=1), today
    else: last_complete, partial = today - pd.Timedelta(days=1), None
    kl = G.load_all(ROOT / "data/candles", last_complete, partial)
    D = G.features(kl); latest = D.Date.max()
    through = latest; day = (through + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    if partial is not None and through != partial:
        sys.exit(f"In-progress candle for {partial.date()} unavailable; not publishing a stale forecast. Rerun the workflow.")
    if partial is not None and through == partial:   # the day before the partial one has an incomplete "next day": not a valid label
        D.loc[D.Date == through - pd.Timedelta(days=1), ["next_down", "next_up"]] = np.nan
    window_start = pd.Timestamp(day)
    on_time = now < window_start
    led = read_jsonl(LEDGER); outs = read_jsonl(OUTCOMES)
    # 1) score every past forecast whose day has now closed
    scored = {o["date"] for o in outs}
    for r in led:
        d = pd.Timestamp(r["date"])
        if r["date"] in scored or d > last_complete: continue
        res = {}
        for s in r["forecasts"]:
            if s not in kl or d not in kl[s].index or (partial is not None and d == partial): continue
            c = kl[s].loc[d]; dn, up = float(np.log(c.low / c.open)), float(np.log(c.high / c.open))
            res[s] = {"down": dn, "up": up, "long": {L: bool(dn <= np.log(1 - G.DIST[int(L)])) for L in r["forecasts"][s]["long"]},
                      "short": {L: bool(up >= np.log(1 + G.DIST[int(L)])) for L in r["forecasts"][s]["short"]}}
        ontime = pd.Timestamp(r["published_utc"]).tz_localize(None) if pd.Timestamp(r["published_utc"]).tzinfo is None else pd.Timestamp(r["published_utc"]).tz_convert(None)
        o = {"date": r["date"], "forecast_hash": r["hash"], "scored_at_utc": pd.Timestamp.now("UTC").isoformat(), "on_time": bool(ontime < d), "results": res}
        outs.append(o); OUTCOMES.parent.mkdir(exist_ok=True)
        with open(OUTCOMES, "a") as fh: fh.write(canon(o) + "\n")
    # 2) forecast today (once per day)
    if not any(r["date"] == day for r in led):
        F = {s: {"long": {}, "short": {}, "normal10": {}, "textbook10": {}} for s in sorted(D[D.Date == through].sym.unique())}
        for side in ["long", "short"]:
            for lev in G.LEVERAGE:
                o = odds_today(D, side, lev, through)
                for s, v in o.items():
                    F[s][side][str(lev)] = round(v["p"], 5)
                    if lev == 10: F[s]["normal10"][side] = round(v["normal"], 5) if v["normal"] else None; F[s]["textbook10"][side] = round(v["textbook"], 5)
        for s in F:
            for side in ["long", "short"]:
                safe = [L for L in G.LEVERAGE if F[s][side][str(L)] <= 0.05]
                F[s].setdefault("safe", {})[side] = max(safe) if safe else None
        cands = [(F[s][side]["10"], F[s][side]["10"] / F[s]["normal10"][side], s, side) for s in F for side in ["long", "short"] if F[s]["normal10"].get(side)]
        hot = sorted([c for c in cands if c[0] >= 0.05 and c[1] >= 1.5], reverse=True)
        if hot:
            p10, ratio, s, side = hot[0]; safe = F[s]["safe"][side]
            others = len(hot) - 1
            line = (f"{NAME(s)} {side}s carry the most risk today: {100*p10:.0f}% odds of a 10x liquidation, {ratio:.1f}× normal. "
                    f"At or below 5% odds, the most leverage is {str(safe)+'x' if safe else 'under 5x'}." + (f" {others} other market{'s' if others != 1 else ''} also elevated." if others else ""))
        else:
            p10, ratio, s, side = sorted(cands, reverse=True)[0]
            line = (f"A calm day: no market has elevated 10x liquidation odds. The highest is {NAME(s)} {side}s at {100*p10:.1f}%"
                    f"{', ' + format(ratio, '.1f') + '× normal' if ratio >= 1.2 else ''}.")
        rec = {"date": day, "published_utc": pd.Timestamp(now).tz_localize("UTC").isoformat(), "window_start_utc": window_start.strftime("%Y-%m-%dT%H:%M:%SZ"), "on_time": bool(on_time),
               "data_through": str(through.date()) + (f" (in progress, as of {now:%H:%M} UTC)" if partial is not None and through == partial else ""), "model_version": CFG["model_version"],
               "liq_distance": {str(L): G.DIST[L] for L in G.LEVERAGE}, "line": line, "line_target": {"symbol": s, "side": side, "leverage": 10, "p": p10, "ratio": round(ratio, 3)},
               "forecasts": F, "prev_hash": led[-1]["hash"] if led else "0" * 64}
        rec["hash"] = hashlib.sha256((rec["prev_hash"] + canon({k: v for k, v in rec.items() if k != "hash"})).encode()).hexdigest()
        led.append(rec); LEDGER.parent.mkdir(exist_ok=True)
        with open(LEDGER, "a") as fh: fh.write(canon(rec) + "\n")
        print(line)
    # 3) site data
    od = {o["date"]: o for o in outs}
    bins = np.array([0, .01, .02, .05, .1, .2, .35, 1.0]); agg = [[0, 0, 0] for _ in range(len(bins) - 1)]
    hist = []
    for r in led:
        o = od.get(r["date"])
        if not o: continue
        ok_cal = o.get("on_time", False)
        for s, f in (r["forecasts"].items() if ok_cal else []):
            if s not in o["results"]: continue
            for side in ["long", "short"]:
                for L, p in f[side].items():
                    b = int(np.searchsorted(bins, p, side="right") - 1); b = min(b, len(agg) - 1)
                    agg[b][0] += 1; agg[b][1] += p; agg[b][2] += int(o["results"][s][side][L])
        t = r["line_target"]; res = o["results"].get(t["symbol"])
        hist.append({"date": r["date"], "line": r["line"], "p": t["p"], "hit": None if res is None else bool(res[t["side"]][str(t["leverage"])]), "on_time": o.get("on_time", False), "hash": r["hash"][:12]})
    bt = {}
    btp = ROOT / "results/odds_backtest.json"
    if btp.exists():
        b = json.load(open(btp)); bt = {"eval_from": b["eval_from"], "through": b["through"], "tests": {k: {kk: v[kk] for kk in ["k", "n", "base", "skill_cal", "auc_cal", "auc_textbook", "deciles"]} for k, v in b["tests"].items()}}
    tdy = led[-1]
    site = {"generated_utc": pd.Timestamp.now("UTC").isoformat(), "published_utc": tdy["published_utc"], "on_time": tdy.get("on_time"), "day": tdy["date"], "data_through": tdy["data_through"], "line": tdy["line"],
            "liq_distance": tdy["liq_distance"], "leverage": G.LEVERAGE, "forecasts": tdy["forecasts"], "hash": tdy["hash"],
            "ledger": {"days": len(led), "scored_days": len(outs), "calibration": [{"lo": float(bins[i]), "hi": float(bins[i + 1]), "n": a[0], "pred": a[1] / a[0] if a[0] else None, "actual": a[2] / a[0] if a[0] else None} for i, a in enumerate(agg)], "recent": hist[-30:][::-1]},
            "backtest": bt, "waitlist_url": CFG.get("waitlist_url", ""), "contact_email": CFG.get("contact_email", "")}
    (ROOT / "docs").mkdir(exist_ok=True); json.dump(site, open(ROOT / "docs/data.json", "w"), separators=(",", ":"))
    # public copy of the ledger next to the page, so it stays verifiable even if the engine repo goes private
    (ROOT / "docs/ledger").mkdir(exist_ok=True)
    for src in [LEDGER, OUTCOMES]:
        if src.exists(): (ROOT / "docs/ledger" / src.name).write_text(src.read_text())

if __name__ == "__main__": main()
