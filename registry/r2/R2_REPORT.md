# Ghostlyne Discovery Lab · R2 research report (semiconductor memory)

Run 26 Nov 2026 under pre-registration `3c36251` (committed 18:39 ET, before any confirmatory evaluation). Code, configuration and the append-only registry (`registry/registry.jsonl`, 1,868 events across R1 and R2) are in this repository. Internal evaluation only. Nothing here has been independently validated.

## What was done

- **Audit.** R1 tested forecasting value only (Qualification C), on broad monthly US indices. It did not test the discovery proposition. R2 adds separate paths for association, lead–lag, stress-conditional structure and predictive value, plus an append-only registry, monitoring and a lifecycle replay.
- **Focal market: semiconductor memory.** Memory product prices (DDR4, DDR5, DRAM, NAND, HBM) need a paid DRAMeXchange licence and were not bought (founder approval required). R2 therefore uses:
  - seven memory-company share prices, weekly. These are labelled as financial instruments, not memory prices;
  - Nanya and Winbond monthly revenue, from Taiwan Stock Exchange disclosures.
- **Universe.** 42 outside variables in rings D1–D5, each with a written admission rationale, plus six negative controls (three unrelated commodities, three synthetic series). In total 294 weekly pairs and 70 monthly pairs.
- **Tests.**
  - Weekly: 5,586 in exploration (2012–2019), with false-discovery control per family and per distance ring. Candidates were then confirmed on 2020–Nov 2026.
  - Monthly: 1,040 tests.

## Findings

### Data inventory

There was no gap in the weekly universe: all 49 instrument series plus the global factor were obtained. Monthly revenue runs Jan 2013 – Oct 2026 (166 months each). Unavailable variables and reasons are listed in `r2/universe.py`.

### Validated statistical associations (Qualification A)

| Family | D1 | D2 | D3 | D4 | D5 | Negative controls |
|---|---|---|---|---|---|---|
| Total association (raw weekly returns), validated of tested | 28/35 | 35/70 | 46/84 | 13/35 | 8/28 | 0/42 |
| Market-adjusted association, validated of tested | 14/35 | 10/70 | 4/84 | 0/35 | 0/28 | 0/42 |

**Total association is mostly the global market.** Almost everything that trades co-moves with world equities. That is true and descriptive, but not a discovery. It is kept in the registry and labelled as such.

**After removing the global factor, 28 associations validated, all in D1–D3:**

- **24 link memory makers to chip-equipment and wafer suppliers:** Applied Materials, Tokyo Electron, ASML, SUMCO, Shin-Etsu and Entegris. Confirmation-window correlations run from 0.13 to 0.46. The most plausible explanation (a hypothesis) is a shared semiconductor-industry factor that the global adjustment does not remove. These are reliable but conventional.
- **Micron and US utilities, −0.25.** Hypothesis: a growth-versus-defensive style factor, not an electricity link.
- **Taiwan memory makers and Evergreen Marine, 0.17–0.23** (ADATA, TeamGroup, Winbond). Hypothesis: the Taiwan home-market factor, since all are listed in Taipei. Not established as a shipping link.
- **Micron and ABB, 0.13.** Hypothesis: shared industrial-cycle exposure.

**No remote relationship (D4, D5) survived adjustment.** One D4 candidate (Winbond and the won) failed confirmation.

### Lead–lag structure (Qualification B)

None found. 0 of 4,704 lag tests passed exploration. Weekly memory-share returns showed no detectable lead or lag with any outside variable at ±1–8 weeks.

### Stress-conditional structure

None found: 0 of 294 tests.

### Incremental predictive value (Qualification C)

Not tested, because no lead–lag relationship qualified.

### Monthly memory revenue

10 exploration candidates, 0 confirmed. The track is underpowered: with about 80 months per window, only correlations above roughly 0.35 are reliably detectable.

### Controls

- No negative control was validated in any family.
- The synthetic positive controls behaved as designed.
- The real positive control (Micron with Applied Materials) validated, as expected.

### Lifecycle replay

The replay ran at year-end checkpoints from 2021 to Nov 2026, using only data available at each date. It recorded 153 candidate registrations, 25 confirmations to Validated, 18 moves to Under Reassessment and 7 invalidations, with every transition preserved. This demonstrates the lifecycle on past data. It is not live monitoring and not additional evidence.

### Monitoring at the latest week

- Of the 28 validated adjusted associations, 27 are stable and one is strengthening (Samsung with Applied Materials).
- Three show a divergence z-score below −2: Micron/Entegris, Samsung/Shin-Etsu and ADATA/Evergreen. The memory stock has lagged what the relationship implies over the last 13 weeks. This is descriptive only, and convergence is not implied.

## Detection limits

Synthetic power, 10 simulated worlds:
- **Adjusted association:** true correlations of 0.20 are found 80% of the time and 0.12 about 40%.
- **Lead–lag:** needs about 0.20 to be found 90% of the time.

Weaker relationships may exist and were not detectable here. Absence of evidence is not evidence of absence.

## Assessment

The lab now does what the specification asks: discovery separated from prediction, controls, a permanent registry, reassessment and monitoring. On the data available without a licence, it found reliable associations, but they are conventional (shared industry, style and home-market factors). It found no unconventional or remote relationship and no lead–lag structure.

## Proposed R3 (justified corrections; not yet registered)

1. **Remove the obvious common factors before calling anything unconventional.** Adjust for a semiconductor-industry factor and each instrument's home-market index. Only then will an association with freight, currency or weather mean something new.
2. **Memory product prices.** Weekly DRAM and NAND spot and contract prices are the specification's preferred focal variables. They require a DRAMeXchange licence: a founder decision.
3. **More power for slow relationships.** Use the monthly revenue of all Taiwan memory and module makers (about 10 companies) as a panel, rather than two series alone.
