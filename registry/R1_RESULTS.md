# Ghostlyne Registry · R1 results

Run once on 2026-11-26, under pre-registration commit 1d6bcc8 (method and code unchanged).

**185 lines tested. 0 survived. 0 of 15 placebos survived.**

No variable in any ring, from power transformers to Arizona's drought, improved next-month forecasts of the five AI-infrastructure proxies enough to pass the gate. 11 of the 170 real pairs reached p < 0.05 before false-discovery control; chance alone would produce about 8.5. That is what noise looks like.

## Closest to surviving

Error cut is the share of the baseline's squared forecast error removed out of sample (positive means better than baseline).

| Line | Ring | Lead | Error cut 2016–20 | Error cut 2021– | q | Cause of death |
|---|---|---|---|---|---|---|
| Crude oil, WTI → US semiconductor and component production | D3 | 1 mo | -7.9% | +7.6% | 0.22 | not significant after the false-discovery control; no gain in 2016–2020 |
| Japanese yen per US dollar → US semiconductor prices (PPI, semiconductor devices) | D4 | 3 mo | +1.0% | +3.7% | 0.58 | opposite of the registered direction; direction flipped within 2000–2015; not significant after the false-discovery control |
| US motor vehicle production (competing chip demand) → US electronic component prices (PPI) | D5 | 12 mo | +2.6% | -0.1% | 0.58 | not significant after the false-discovery control; no gain from 2021 on |
| Aluminum price → US computer and server prices (PPI, electronic computers) | D2 | 4 mo | +0.9% | +3.1% | 0.58 | not significant after the false-discovery control |
| Copper price → US semiconductor and component production | D2 | 1 mo | +0.3% | +3.7% | 0.58 | direction flipped within 2000–2015; not significant after the false-discovery control |
| US motor vehicle production (competing chip demand) → US semiconductor prices (PPI, semiconductor devices) | D5 | 12 mo | +6.9% | -49.4% | 0.71 | not significant after the false-discovery control; no gain from 2021 on |
| Industrial electric power prices (PPI) → US computer and server prices (PPI, electronic computers) | D3 | 1 mo | -0.5% | +4.7% | 0.71 | not significant after the false-discovery control; no gain in 2016–2020 |
| Zinc price → US semiconductor and component production | D2 | 1 mo | +0.2% | +1.1% | 0.71 | direction flipped within 2000–2015; not significant after the false-discovery control |

## What R1 could and could not see

Power check on synthetic data (`power.py`), single true line among 185. R1 finds a line that explains 12% of next month's variance 70% of the time, 8% about half the time, 5% 20% of the time, and 2% 5% of the time. R1 rules out strong monthly lines from these public proxies. It does not rule out weak ones.

## One pattern, not a finding

Industrial inputs (ring D2) had a positive out-of-sample error cut in 14 of 30 pairs, against 10 of 55 in ring D4 and 1 of 15 placebos. This was not pre-registered as a test, so it is a direction for R2, not a result.

## What this means

Broad monthly price and production indices average away the memory and server cycles where remote effects would show. R2 needs memory-specific targets at weekly frequency, which means licensed data, and gets its own pre-registration before any of it is seen.
