# WATCH2: independent review guide

Repository: https://github.com/ArashNourk/ghostlyne-lab, folder `registry/watch2/`. The frozen state is the commit that adds `FREEZE.json`, recorded as event `GL-WATCH2-FREEZE` in `registry/registry.jsonl`.

## Files
| file | role |
|---|---|
| `PREREGISTRATION_WATCH2.md` | protocol, gates, decision rules, Amendments 1–2 (frozen) |
| `fp3.py` | three-outcome first-passage formula plus Monte Carlo check (frozen) |
| `watch2.py` | scenarios, models CV and G, calibration, alerts, metrics, bootstrap (frozen) |
| `confirm.py` | the single real-data run; refuses if any frozen file's SHA-256 differs (frozen) |
| `fetch_coingecko.py` | downloads hourly BTC/USD OHLC to `data/` (local only, git-ignored) (frozen) |
| `FREEZE.json` | SHA-256 of the five frozen files |
| `LAB_CHECK.md`, `lab/*.json` | simulated-market results |

## Environment
Python 3.13, numpy 2.5, pandas 3.0. No other dependencies. About 45 seconds and under 4 GB of memory per market; run one at a time.

## Reproduce
```
cd registry/watch2
sha256sum PREREGISTRATION_WATCH2.md watch2.py fp3.py confirm.py fetch_coingecko.py   # compare with FREEZE.json
python3 fp3.py                     # expected: worst difference 0.23 pp
python3 watch2.py sv 101           # expected: H1 +10.53%, all gates True
python3 watch2.py sv 105           # expected: H1 +8.67%,  all gates True
python3 watch2.py const 201        # expected: H1 +0.05%,  H1 False, H1c True, H2_level False, H3 False
```
Results are deterministic for a given seed. Full output is written to `lab/<market>_seed<seed>.json`. Expected values for all ten seeds are in `LAB_CHECK.md`.

## Real data (after the founder authorizes the purchase)
```
COINGECKO_API_KEY=...  python3 fetch_coingecko.py     # writes data/btc_hourly.csv; prints candle count and gaps
python3 confirm.py data/btc_hourly.csv                # writes results/WATCH2_CONFIRM.json; prints gates
```
`confirm.py` refuses to run if any frozen file has changed, or if the data does not span 2018-03 to 2024-01. The development period (to 2022-12-31) is used only to fit what the procedure defines. Gates are judged on 2023-01-01 onward, under all three treatments of ambiguous hourly candles.

## Points a reviewer should check
1. Leakage. Calibration, thresholds and regime cut points use `C.dev` or `S.dev` only. HAR refits stop 7 hours before each forecast month.
2. Ambiguous candles are never ordered: see `labels()` and `gates_all_resolutions`.
3. Gate arithmetic in `evaluate()` against section 5 of the pre-registration and its amendments.
4. The negative control: `watch2.py const <seed>` must not pass H1, H2 or H3.
