# Ghostlyne Discovery Lab · Pre-registration R3 (the AI-infrastructure stack)

Governing document: Ghostlyne Governing Product Vision and Research Specification. R1 and R2 stay as recorded.

## Why R3: corrections to R2's lens

1. **R2 removed the global cycle before looking for distant links.** That cycle is how oil, copper and freight reach AI businesses. R3 measures total association and makes no market adjustment.
2. **R2 tested only weekly moves and leads of up to 8 weeks.** Distant effects travel over months. R3 tests weekly, monthly and quarterly co-movement, and monthly leads of 1–12 months.
3. **R2 conditioned on global stock-market stress.** Distant links are episodic and wake up when the distant variable is shocked. R3 tests shock transmission: what an AI-infrastructure stock does in the four weeks after an extreme move in the distant variable.
4. **R2 tested pairs only.** R3 tests 12 pre-specified multi-hop chains (distant → intermediate → AI infrastructure) as single statistical structures, never by chaining pairwise correlations.
5. **R2 covered memory only.** R3 covers the stack, plus real fundamentals: monthly revenue of ten Taiwan AI supply-chain companies.

## Universe (`universe.py`)

**26 AI-infrastructure instruments in seven segments:**
- compute;
- memory;
- networking and optics;
- servers and assembly;
- power and cooling;
- data centres;
- equipment and packaging.

These are share prices, not product prices.

**10 fundamentals series:** monthly revenue from TWSE disclosures for TSMC, Quanta, Hon Hai, Wistron, Wiwynn, Delta Electronics, Accton, Unimicron, ASE and Nanya.

**31 distant variables, D2–D5:**
- metals and gases;
- energy (Brent as the Middle East benchmark, WTI, natural gas, uranium) and utilities;
- miners, including African copper producers in DR Congo and Zambia;
- Asian and global container shipping, plus air cargo;
- Asian currencies and El Niño;
- competing demand (Bitcoin, corn, carmakers).

**6 negative controls:** orange juice, lean hogs, live cattle and three synthetic series.

D1 direct dependencies were covered in R2. R3 deliberately spends its capacity on distance.

## Families (separate claims)

| Family | Question | Data and test |
|---|---|---|
| A_w, A_m, A_q | Do they move together at a weekly, monthly or quarterly horizon? | Non-overlapping log returns, Pearson correlation with Newey–West p-value, rank correlation must agree |
| B_m | Does one lead the other by 1–12 months? Either side may lead | Monthly returns, Newey–West p-value; best lag per pair kept |
| X_shock | After an extreme weekly move in the distant variable, does the AI stock move differently over the next 4 weeks? Separate up-shock and down-shock claims | Extreme = beyond the 5th or 95th percentile of the trailing 5 years, past data only. Regression on shock indicators, Newey–West (4 lags); at least 10 shocks per window |
| R_yoy | Does a distant variable's year-on-year change line up with, or lead, a company's year-on-year revenue growth, at 0–12 months either way? | Pyper–Peterman effective-sample-size test for persistent, overlapping series |
| chain | Is there an indirect path X → M → Y? | Monthly returns; indirect effect a·b; moving-block bootstrap (6-month blocks, 999 draws) |
| C | Does a validated lead improve out-of-sample forecasts? (Only where the distant variable leads) | Clark–West, expanding window, out-of-sample R² must be above 0 |

## Windows and gates

- **Equities:** exploration 2008–2016, confirmation 2017 onward.
- **Revenue:** exploration 2014–2019, confirmation 2020 onward.
- **Exploration:** Benjamini–Hochberg at q = 0.10 within each family and distance ring, so each ring gets its own discovery budget.
- **Confirmation:** same direction, Benjamini–Hochberg q = 0.05 among that family's candidates, and rank agreement for A families. Chains: Benjamini–Hochberg across the 12 chains in exploration (0.10) and among candidates in confirmation (0.05), same sign.
- **Minimum data:** weekly 300/300; monthly 72/72; quarterly 24/24; revenue 48/48.

**Detection floor:** a single true relationship competing in a family of m tests needs p below about 0.10/m to become a candidate. With about 108 exploration months, that means correlations of about 0.4 or more for monthly lead–lag. Weaker links remain out of reach for this sample size and are not ruled out. The revenue track is the most constrained. Year-on-year growth rates are persistent, so 72 months contain only about 10–20 independent observations. In the synthetic check, a planted 6-month lead with exploration correlation 0.78 reached p = 0.004, which is not enough to pass control across 1,750 tests in its ring. Only very strong revenue links can be confirmed in R3.

## Monitoring (past data at each date, never presented as live)

- **Association and lead–lag:** rolling correlation (52 weeks or 36 months) with a 95% band; behaviour against the confirmed estimate; divergence z (13-week or 3-month residual from a trailing reference fit).
- **Lead–lag only:** lag drift, meaning the best lag over the last 60 months against the validated lag.
- **Shocks:** the latest shocks and the responses that followed.
- **Chains:** the rolling 60-month indirect effect.

## Interpretation rules

Validated relationships are statistical associations, not causes. Explanations are labelled as hypotheses. A lead is predictive only if C validates it.

Synthetic end-to-end checks (`synth3.py`) validate the implementation only. Any change to this document after its commit creates R4.
