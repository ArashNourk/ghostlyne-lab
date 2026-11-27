# Ghostlyne Discovery Lab · R3 research report (the AI-infrastructure stack)

Run 27 Nov 2026 UTC under pre-registration `aaf2869`, committed before any confirmatory evaluation. The registry (`registry/registry.jsonl`) now holds 8,022 append-only events across R1–R3. Internal evaluation only; nothing here has been independently validated.

## Why R3

R2 removed the global cycle before looking for distant links, tested only weekly moves, conditioned on stock-market stress, and covered memory alone. R3 corrects each of these:

- It measures total co-movement at weekly, monthly and quarterly horizons.
- It tests leads of 1–12 months.
- It tests shock transmission keyed to the distant variable itself.
- It tests 12 multi-hop chains as single structures.
- It covers seven layers of the AI stack, with fundamentals from ten Taiwan supply-chain revenue series.

## Data

Every pre-registered series was obtained: 26 instruments, 10 revenue series, 31 distant variables, and 3 real plus 3 synthetic controls. Product prices (DRAM, GPU, HBM) and licensed freight indices remain unavailable; see `universe.py`.

## Findings by qualification path

Validated over tested pairs with enough data:

| Relationship | D2 inputs | D3 energy, mining, logistics | D4 currencies, weather | D5 competing demand | Controls |
|---|---|---|---|---|---|
| Moves together, weekly | 133/144 | 276/360 | 33/120 | 21/48 | 11/144 |
| Moves together, monthly | 71/144 | 180/360 | 14/120 | 3/48 | 0/144 |
| Moves together, quarterly | 22/144 | 82/360 | 5/120 | 0/48 | 1/144 |
| Lead–lag, 1–12 months | 0/138 | 0/341 | 0/120 | 0/48 | 0/144 |
| Shock transmission (4 weeks after) | 0/237 | 0/621 | 0/240 | 0/95 | 0/288 |
| Revenue vs distant growth | 0/53 | 0/128 | 0/40 | 0/19 | 0/48 |

### 1. Distant markets do move with AI infrastructure

There are 840 validated co-movement relationships, 76 of them with currencies, El Niño or competing demand. Medians of the confirmed correlations:
- weekly: 0.23–0.27;
- monthly: about 0.3;
- quarterly: 0.34–0.46.

The strongest D4 relationships involve the Taiwan dollar and the won. AI equipment, chip and data-centre stocks fall when Asian currencies weaken: correlations of −0.30 to −0.44 monthly and quarterly, stable in the latest 36 months.

### 2. Most of it is the shared global cycle

The negative controls show it. Live cattle validated weekly against 11 AI stocks (r 0.08–0.20), and one synthetic random series passed quarterly. That is within the false-discovery rate the gate allows. Total co-movement is therefore real but not specific: unrelated markets also reach it through the cycle.

Each relationship is marked against a **control line**: the 95th percentile of correlation between the same stocks and unrelated control series. That is 0.19 weekly and 0.30 monthly; at the quarterly horizon the controls are too noisy for a line. 498 relationships clear it. The control line is a descriptive benchmark added after the run, not a pre-registered gate.

### 3. Timing did not replicate

In 2008–2016 there were 119 lead–lag candidates, mostly involving the Taiwan dollar. None was confirmed from 2017, and 53 reversed direction. Shock transmission produced 4 candidates (two of them controls) and none confirmed. The revenue track produced no candidates: it can only see very strong links, because year-on-year growth is persistent. With no validated lead, predictive value was not tested.

### 4. Two multi-hop paths validated

- **Brent → COSCO Shipping → Hon Hai.** Standardised indirect effect 0.05 from 2017 (95% interval in raw units 0.005 to 0.074), against 0.19 in 2008–2016. The path held but weakened.
- **Copper → Eaton → Equinix.** Standardised indirect effect 0.11 from 2017 (interval 0.024 to 0.262), against 0.19 in 2008–2016.

These are statistical paths consistent with transmission through the middle market, not proof of cause. The other ten chains were not confirmed, including Brent → Maersk → Quanta and the African copper miner routes.

### 5. Monitoring

Every validated co-movement is tracked weekly:
- **rolling strength:** stable, strengthening, weakening or reversing against the confirmed value;
- **divergence:** a z-score with diverging or converging labels;
- **chains:** the indirect effect on a rolling five-year window.

All of it uses only data available at each date. This is a historical replay, not live monitoring.

## Assessment

On the evidence:
- **The lab can now map how distant markets co-move with every layer of the AI stack, at three horizons, with uncertainty, against a control line, and monitored.** This is real, broad and auditable.
- **Specific timing edges between distant markets and AI share prices were not found.** Candidates from 2008–2016 did not survive 2017–2026. That is consistent with equity markets pricing these links quickly.
- **Multi-hop transmission exists in at least two cases,** both through the physical economy: shipping, and power equipment.

## Proposed R4 (not registered)

1. Use AI-specific product and activity targets where timing can exist: memory prices if licensed, and the ten-company revenue panel pooled for power.
2. Make the control line a pre-registered gate, so "above the control line" becomes a confirmed claim.
3. Extend the chains to start from revenue, where physical transmission should show with a delay.
