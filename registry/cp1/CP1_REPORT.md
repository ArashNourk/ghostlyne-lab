# CP1 results: calling ERCOT's monthly coincident peak from public data

Pre-registration: `PREREGISTRATION_CP1.md`, commit a3253a6. Code: `cp1.py`, unchanged after registration. Results: `results/CP1.json`. Confirmation covers 34 months (2024-01 to 2026-10), with day-ahead alerts at the primary budget of 6 alert days per month.

## Gates
| Gate | Result | Evidence |
|---|---|---|
| G1 lab validity | **Pass** | Oracle 0.91 capture (≥ 0.85); noise control 0.18 (≤ 0.40); noise Brier skill ≈ 0 |
| G2 skill | **Pass** | Brier skill vs climatology 0.149 (95% CI 0.074–0.231) |
| G3 commercial capture | **Pass, at the margin** | 29 of 34 months caught (0.853; Wilson 95% CI 0.70–0.94) at 6.4 alerts/month. One more miss would fail. |
| G4 differentiation | **Fail** | Free rule B1 caught 27 of 34 (0.794) at 7.4 alerts/month. M1 is +5.9 points with about one fewer alert a month; the gate needed +10. |

**Pre-registered consequence (G2 and G3 pass, G4 fails):** calling the peak from public data works, but it is close to a commodity. The simple "forecast beats month-to-date peak" rule does nearly as well. A forecasting edge is not a defensible product on public data. What remains defensible is the neutral, timestamped ledger and the 12CP bill-impact calculator, and building them is a founder decision.

## What else the test showed
1. **Future days, not forecast error, are the binding limit.** Even an oracle that knows today's actual peak catches only 74% of months at 3 alerts a month (91% at 6), because nobody knows whether a hotter day is coming later in the month. The lever is multi-day forecasts, which public archives don't provide historically.
2. **The alert burden is rising fast.** At the fixed threshold, M1 issued 4.3 alerts a month in 2024, 6.6 in 2025 and 8.7 in 2026. August 2026 needed 21 alert days to catch the peak. Load growth and new large loads make more days look like peak days, which industry calls "CP exhaustion". Under 12CP, this burden runs all year.
3. **The operational and official peaks don't always match.** In 2 of 14 known summer months (June and September 2024), the official settlement-based 4CP day differed from the operational peak day. Against official days, M1 caught 12 of 14 and the free rule 9 of 14 (small sample).
4. **Misses:**
   - February 2024 (tight);
   - July 2024 (Hurricane Beryl week, peak on July 1);
   - October 2024 (zero alerts);
   - February 2026 (the peak fell on the 1st, before any in-month information);
   - September 2026 (tight).
5. **Same-morning alerts** (actuals to D−1) gave the same capture, 0.853, at 6.8 alerts a month. That variant is secondary and not gated.

## Limits
- The data is hourly; the official intervals are 15 or 30 minutes.
- The forecast is ERCOT's own, as reported to EIA.
- 34 months is a small confirmation sample. The capture CI is wide.
- The 12CP rule is not final.
