# Ghostlyne Discovery Lab · R5 research report (final bounded iteration)

Run 27 Nov 2026 under pre-registration `64c9b36`. The gates and decision rules were locked before any R5 model was fitted. Internal evaluation only.

## Verdict: R5 fails the pre-registered gates

No group of information beyond the conventional baseline produced a validated improvement in any of the three decisions. Under the authorization's terms, Ghostlyne is suspended. No R6.

## Lab validity: passed

- **The conventional baseline has real skill.** The SPIKE Brier score is 0.0485 against 0.0567 for climatology in exploration (skill 14%), and 0.0394 against 0.0409 in confirmation.
- **The planted positive controls passed every decision in both windows:**
  - Brier score −0.015 in confirmation;
  - procurement cost −$4.07/MWh;
  - sale revenue +$3.74/MWh.
- **The synthetic noise group never validated.** It looked like a candidate once in exploration (sale timing, p = 0.02) and failed in confirmation, as noise should.

So the pipeline can detect information when it exists.

## Results

Exploration (2020–2023) decides which groups are candidates. Gains are against the conventional baseline; positive means better.

| Group | Spike risk (Brier gain) | Procurement ($/MWh saved) | Sale timing ($/MWh gained) | Candidate? |
|---|---|---|---|---|
| G1 neighbouring grids | −0.0012 | −0.32 | −0.17 | no |
| G2 east and global gas | −0.0007 | −0.30 | +0.05 (p 0.31) | no |
| G3 industry and finance | −0.0007 | −0.19 | +0.12 (p 0.20) | no |
| G4 climate and agriculture | −0.0009 | +0.13 (p 0.44) | +0.50 (p 0.18) | no |
| G5 crypto and AI (incl. on-chain hashprice, miner breakeven) | **−0.0037** | +0.19 (p 0.34) | +0.31 (p 0.21) | no |
| G35 all unconventional | −0.0079 | −0.00 | −0.98 | no |

**No real group became a candidate in any decision.** Adding the crypto and AI group, including hashprice and the implied miner breakeven price, made spike-risk assessment significantly *worse*: the extra features add noise, not information.

## Confirmation window (2024 – Nov 2026): observations only

These were not candidates, so they cannot be validated under the locked rule.

- Two conventional cross-market groups showed procurement gains in 2024–2026 that they did not show in 2020–2023:
  - G2 east and global gas: +$0.53/MWh, 95% interval +$0.06 to +$1.12, CVaR95 116 → 108;
  - G1 neighbouring grids: +$0.38/MWh, interval −$0.01 to +$0.89.

  This may be an emerging relationship or chance. It is recorded as a hypothesis for prospective monitoring, not a finding.
- Nothing from G3, G4 or G5 showed a gain in confirmation either.

## What did show decision value

The conventional baseline itself. Choosing day-ahead or real time with free public information cut procurement cost against always buying day-ahead:
- $82.52 → $80.57/MWh in 2020–2023;
- $33.77 → $32.96/MWh in 2024–2026;

that is, about 2.4% in both periods. This is real but not differentiated: anyone with the same public data can build it. It fails the differentiation gate by design.

## Gate assessment

| Gate | Outcome |
|---|---|
| Independence | Failed: no group added confirmed information beyond the baseline |
| Reproducibility | Not reached |
| Economic value | Not shown for any differentiated information |
| Differentiation | Failed: no unconventional group (G3–G5) passed; nor did the conventional cross-market groups |
| Operational viability | Data feeds are current to Nov 2026; hashprice is recomputable from public chain data |
| Willingness to pay | Not tested, because the scientific gate failed |

## Limits

- The baseline lacks weather forecasts, which professionals have. That makes the test easier for the unconventional groups, not harder, and they still added nothing.
- Daily peak-block decisions only. Intraday decisions (hour-ahead, battery dispatch) were not tested.
- One market (ERCOT North and West), one friction level ($1/MWh; $3 reported as sensitivity).

## Across R1–R5

Five pre-registered runs, two markets, 9,329 experiment units in the registry and well over 30,000 statistical tests. Using free public data:
- Ghostlyne reliably recovers the conventional structure of each market.
- It finds no unconventional relationship that adds usable information beyond that structure.

The negative results are preserved in the registry.
