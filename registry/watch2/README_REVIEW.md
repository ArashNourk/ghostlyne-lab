# WATCH2: independent review guide

Repository: https://github.com/ArashNourk/ghostlyne-lab, folder `registry/watch2/`.

The frozen state is the commit recorded as event `GL-WATCH2-AMEND3` in `registry/registry.jsonl`. The earlier freeze (`GL-WATCH2-FREEZE`, commit 10a53d4) is superseded but kept in history.

## What changed since 10a53d4 (Amendment 3)
| review point | where it is fixed |
|---|---|
| 1. Leakage through the full-sample floor | `watch2.py`: `FLOOR = 1e-10`, a fixed constant. Audit list in Amendment 3, point 1 |
| 2. V1 missing, no dynamic baseline | `watch2.py`: `v1_hourly_var()` imports the frozen `daily1/daily1.py`; `DV` is an EWMA with a development-chosen half-life |
| 3. False-alarm comparison | `alerts()`: operational (development thresholds) and matched 10/20/30% false-warning rates; recall and lead time reported separately |
| 4. H3 insufficient | `evaluate()` → `H3_G`, `H3_DV`: change since inception at unchanged price; the old test is kept as `H3a_disagreement` |
| 5. Forward-fill, coverage | `confirm.py`: no filling, validation of duplicates, timestamps and OHLC, coverage through the last complete month; `watch2.py` excludes scenarios with missing candles |
| 6. Omitted components | V1 restored; 8h horizon (`--h8`) and log loss reported; H4 implemented in `attribution()`; G+A and G+R formally deferred |
| Licensing | Amendment 3, point 8: written confirmation from CoinGecko is required before purchase |

## Files
| file | role |
|---|---|
| `PREREGISTRATION_WATCH2.md` | protocol, gates, decision rules, Amendments 1–3 (frozen; history is appended, never edited) |
| `fp3.py` | three-outcome first-passage formula plus Monte Carlo check (frozen) |
| `watch2.py` | scenarios, models CV, V1, DV and G, calibration, alerts, metrics, attribution, bootstrap (frozen) |
| `confirm.py` | the single real-data run; validates data and refuses if any frozen file's SHA-256 differs (frozen) |
| `fetch_coingecko.py` | downloads hourly BTC/USD OHLC to `data/` (local only, git-ignored) (frozen) |
| `../daily1/daily1.py` | frozen V1, imported unchanged (SHA-256 2a8410b6…) |
| `FREEZE.json` | SHA-256 of the six frozen files |
| `LAB_CHECK.md`, `lab/*.json` | simulated-market results under Amendment 3 |

## Environment
Python 3.13, numpy 2.5, pandas 3.0. No other dependencies. About 160–190 seconds and under 4 GB of memory per market; run one at a time.

## Reproduce
```
cd registry/watch2
python3 -c 'import json,hashlib;[print(hashlib.sha256(open(f,"rb").read()).hexdigest()==h, f) for f,h in json.load(open("FREEZE.json"))["files"].items()]'   # all True
python3 fp3.py                     # expected: worst difference 0.23 pp
python3 watch2.py sv 101           # expected: H1 +0.31% vs DV (fails); H2c and H3 pass for G and DV; H4 passes
python3 watch2.py const 201        # expected: H1 about 0; H3 and H4 fail
python3 watch2.py sv 101 --h8      # 8-hour horizon, reported only
```
Results are deterministic for a given seed. Full output is written to `lab/<market>_seed<seed>[_h8].json`. Expected values for every seed are in `LAB_CHECK.md`.

## Real data (only after the licensing confirmation and the founder's approval of the purchase)
```
COINGECKO_API_KEY=...  python3 fetch_coingecko.py     # writes data/btc_hourly.csv; prints candle count and gaps
python3 confirm.py data/btc_hourly.csv                # validates, runs 24h and 8h, writes results/WATCH2_CONFIRM.json
```
`confirm.py` refuses to run if:
- any frozen file has changed;
- the data contains conflicting duplicate candles or off-hour timestamps;
- more than 0.5% of candles are OHLC-inconsistent;
- coverage does not run from February 2018 through the start of the current month.

Development data (to 2022-12-31) is used only to fit what the procedure defines. Gates are judged on 2023-01-01 onward, under all three treatments of ambiguous hourly candles.

## Points a reviewer should check
1. **Leakage.** Calibration, thresholds, regime cut points and the DV half-life use development scenarios only. HAR refits stop 7 hours before each forecast month. V1 sees only completed previous days.
2. **Missing data.** No forward-fill anywhere (`confirm.py`, `watch2.run()`); a scenario with a missing candle in its window is excluded.
3. **Ambiguous candles** are never ordered: see `labels()` and `gates_all_resolutions`.
4. **Gate arithmetic** in `evaluate()` against section 5 and Amendment 3 points 3, 4 and 7.
5. **Alert fairness.** Matched rates are set per method on confirmation data and are labelled discrimination, not operating rules.
