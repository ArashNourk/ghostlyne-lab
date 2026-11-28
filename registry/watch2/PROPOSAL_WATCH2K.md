# WATCH2-K: proposed external validation on Kraken data (2026-11-28)

**Status: proposal only.** Nothing is registered, downloaded or run. Registration requires both:
- Kraken's written confirmation that this use is permitted (section 1);
- the founder's approval.

The frozen WATCH2 experiment (commit 039b8c1, event `GL-WATCH2-RESEARCH-FROZEN`) is not changed by this proposal.

## 1. Licensing finding
- **The download page sets no terms.** Kraken's free OHLCVT download page states no licence, permitted use, attribution or redistribution terms for the data.
- **The general Terms of Service apply.** The Canadian Terms of Service (updated 2026-11-18) govern Kraken's content generally. They grant a limited, revocable permission to use Kraken's content for one's own benefit. They prohibit:
  - data extraction from Kraken's content;
  - copying or modifying it;
  - distributing or reselling it;
  - using it to build or support products that compete with Kraken's.
- **Conclusion: no written permission for our use.** A private feasibility study is the most defensible use. Two things are not clearly covered:
  - publishing results derived from the data;
  - carrying fitted parameters into a commercial product.
  
  Kraken offers trading and its own price alerts, so the "competitive products" clause is a real question.
- **Rule:** no download until Kraken confirms in writing. If Kraken confirms internal research only, the results stay internal. They may inform our decision to buy a commercial feed, but no public claim may rest on them.

## 2. What stays identical to the frozen experiment
- **Engine and gates.** The engine is `watch2.py` and `fp3.py`, imported unchanged; the runner checks their SHA-256 against `FREEZE.json` at 039b8c1. The gates, thresholds, production-model rule and publication rule are those of Amendments 1–4 and the founder's freeze decision. No retuning and no new models.
- **Splits.** Development data runs to 2022-12-31 and confirmation from 2023-01-01, embargo included. Calibration, thresholds and the DV half-life are fitted on development data only.
- **Data handling.** No forward-fill. Missing hours stay missing, and scenarios with gaps are excluded. Kraken omits hours with no trades, which our rules already handle. The same validation applies as in `confirm.py`: duplicates, hour alignment, OHLC consistency, and a 0.5% limit.

## 3. What necessarily differs, and how each is controlled
| difference | control |
|---|---|
| Source: Kraken XBT/USD spot (one exchange), not CoinGecko's aggregate | Reported as such; outcomes are Kraken trade prices |
| Coverage ends 2026-09-30 (Kraken's latest quarterly file), not the last complete month | Coverage window fixed in the registration: 2018-02-01 to 2026-09-30 |
| Kraken timestamps; the harness expects candle close times | The runner converts each timestamp to its candle's close time. The conversion is verified first: hourly candles rebuilt from the 1-minute file must match Kraken's hourly file (open, high, low, close), and the run is refused if more than 0.1% disagree |
| Runner | New `confirm_kraken.py`. It calls the frozen code and writes `results/WATCH2K_CONFIRM.json`; frozen `confirm.py` and `WATCH2_CONFIRM.json` stay untouched |

## 4. One-minute data: what it can and cannot do
- **It does not change whether a level was touched.** Hourly highs and lows already include every trade, so the hourly labels never miss a touch.
- **It can order ambiguous hours.** When the stop and the target are both touched within the same hour, the frozen rule never guesses the order. Instead, it requires every gate to pass under all three treatments.
- **Proposed secondary analysis, reported and never a gate:**
  1. Re-label ambiguous hours using 1-minute candles. A minute that touches both levels stays ambiguous and is dropped.
  2. Report how many hours were ambiguous, how many the minute data resolved, and every gate under the minute-resolved labels.
  3. If the minute-resolved result disagrees with the three-treatment result, say so.
- **Its value is modest if the ambiguous share is small** (0.03% in simulation). The run will measure it on real data.

## 5. How this run relates to the CoinGecko run
- **They are not independent.** Kraken and CoinGecko prices for the same months are nearly identical. Once WATCH2-K is run, it is the first real-market look at the 2023–2026 confirmation period.
- **The CoinGecko run becomes a replication.** It would check that the result holds on the commercial data source; it is not a second independent test. That is still worth doing before launch, because the product would run on that source.
- **Rules to prevent selective reporting:**
  1. WATCH2-K runs exactly once.
  2. Its results are reported in full, whatever they show.
  3. A public claim requires the gate to pass on every dataset that has been run, so we can never pick the favourable source.
  4. Buying CoinGecko afterwards is a commercial decision and does not change rules 1–3.

## 6. What the founder does if approved
1. **Send Kraken the confirmation request** in section 7 through their support form.
2. **If Kraken permits the use, download the full history.** It comes as five parts of about 2 GB each; the workspace cannot reach Kraken's file host.
3. **Extract two files,** `XBTUSD_60.csv` and `XBTUSD_1.csv`, and attach them. If the 1-minute file is too large to attach, the run goes ahead without the secondary analysis.

## 7. Confirmation request to Kraken
> We would like to download your free historical OHLCVT files for XBT/USD (hourly and one-minute) from the "Downloadable historical OHLCVT data" page. Before doing so, please confirm in writing whether your terms permit the following.
> 1. **Private research.** We would use the data privately to evaluate a statistical model of Bitcoin price behaviour. The model uses heterogeneous autoregressive (HAR) regression of realized variance, exponentially weighted moving-average (EWMA) volatility estimation, monotone statistical calibration (isotonic regression) and a first-passage probability calculation. The purpose is to decide whether to develop a commercial price-alert subscription product.
> 2. **Internal use of the outputs.** We would use the results internally (accuracy scores, alert hit rates and false-warning rates), and possibly the fitted parameters, in that decision. Would publishing those aggregate statistics, with attribution and without any Kraken prices or candles, be permitted?
> 3. **Storage.** The data would be stored privately and not redistributed.
