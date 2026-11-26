# Ghostlyne Registry · Pre-registration R1

**Question.** Do variables at increasing economic distance from AI infrastructure carry information about where AI-infrastructure prices and activity go next, beyond what those series already say about themselves and the broad economy?

Committed before any data value was downloaded for analysis. The only data seen so far is a coverage audit (`coverage.json` on the `registry-data` branch): series names, first and last dates, and counts. No values.

## Universe

Five targets, all public US data. They are broad proxies for AI infrastructure, not DDR5, HBM or GPU prices. Those are licensed and belong to a later run.

| Target | Kind |
|---|---|
| PPI, semiconductor devices (PCU334413334413) | price |
| PPI, electronic components (PCU33443344) | price |
| PPI, electronic computers (PCU334111334111) | price |
| Industrial production, semiconductors and components (IPG3344S) | activity |
| New orders, computers and electronic products (A34SNO) | activity |

Thirty-four outside variables in five rings of economic distance (D1 direct dependency to D5 distant but defensible), plus three placebo series: seeded random walks with no possible connection. In total, 5 × 37 = 185 pre-registered pairs. The full list, each pair's expected direction and lag window are in `universe.py` and `hypotheses_R1.csv`.

Excluded on coverage alone, before any values were seen: the NY Fed supply-chain pressure index (download failed), the Cass freight shipments index (starts 2016, too short), and PPI other basic inorganic chemicals (starts 2010, too short).

## Method (code: `run.py`, frozen with this commit)

- Monthly data. Daily series become monthly averages. Prices, volumes and indices become monthly log changes. The El Niño index and the Arizona drought index stay as levels.
- **Baseline.** The target's own last three months, last month's change in US industrial production, and month-of-year effects.
- **Candidate.** The baseline plus the outside variable at one lag, L ≥ 1 month.
- **Lag selection.** L is chosen inside the pre-registered window (1–6 months for D1–D3, 1–12 for D4, D5 and placebos), on 2000–2015 data only, by lowest in-sample error.
- **Holdout.** January 2016 to the latest month available. One-step forecasts with expanding-window re-estimation. No holdout data is used for choosing anything.
- **Test.** Clark–West (2007) one-sided test for nested models, with Newey–West variance (3 lags). Benjamini–Hochberg false-discovery control at q = 0.10 across all 185 pairs, placebos included.

## Gate: a relationship enters the Registry only if all five hold

1. Significant after false-discovery control (q ≤ 0.10).
2. It improves forecasts in 2016–2020 (out-of-sample R² > 0).
3. It improves forecasts from 2021 on (out-of-sample R² > 0). This guards against relationships that exist only inside the AI boom.
4. Its effect points the same way in both halves of 2000–2015.
5. Where a direction was pre-registered, the effect points that way.

Everything that fails goes to the public graveyard with its cause of death. If any placebo survives, R1 is declared too loose: the gate is tightened for R2, and no R1 result is rescued.

## Limits, stated now

- Forecasts use each series' final revised values, not what was published at the time. Before a survivor becomes a live daily line, it is rechecked with publication delays respected.
- With q = 0.10, up to about one in ten survivors may still be a false discovery.
- One run. Changes to anything above create R2, with a new pre-registration.
