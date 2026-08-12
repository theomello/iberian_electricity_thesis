# Preliminary result: market power rose while concentration fell

**Spain / MIBEL day-ahead market, 2018–2023.** Reproduce with:

```bash
.venv/bin/python scripts/analysis/residual_demand_slope.py --full --save
.venv/bin/python scripts/analysis/markup_from_shares.py
```

## The finding

Between 2018 and 2023 the **elasticity of residual demand in the Iberian
day-ahead market fell by more than half**, from 1.83 to 0.85. Over the same
period CNMC's Herfindahl index for generation **fell** from 1,314 to 1,007.

Concentration and market power moved in opposite directions.

For the average of Iberdrola and Endesa, the implied floor on the Lerner index
rises from **11% in 2018 to 21% in 2023**, and to **34% in the highest-VRE
third of 2023 hours**. In euro terms the implied markup for Iberdrola goes from
6.3 €/MWh to 22.4 €/MWh, peaking at 33.4 €/MWh in 2022.

The standard concentration measure misses this because it is computed on
*shares*. Shares barely moved. What moved is the **slope of the residual demand
curve** each firm faces — and that is what determines whether a given share can
be converted into a markup.

## Method

Two measured inputs, no assumed conduct.

**Elasticity, from the bid curves.** OMIE publishes every submitted offer,
accepted and rejected. Aggregating them gives the supply and demand curves
period by period; residual demand facing an infinitesimal participant is
`RD(p) = D(p) − S(p)`, and its slope at the clearing price gives

```
eta = |RD'(p*)| · p* / Q
```

Computed for all 79,036 usable market periods, 2018–2026. The derivative is a
local difference over a ±h €/MWh window; results are stable across
h = 2, 5, 10 (Spearman 0.92–0.94).

**Shares, from the regulator.** CNMC publishes generation share by business
group in the PDBF across MIBEL, annually, 2008–2023.

**Combined.** A profit-maximising firm's Lerner index is `L_i = s_i / eta`.

| | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|
| eta, all hours | 1.83 | 1.46 | 0.97 | 1.21 | 0.89 | 0.85 |
| eta, high-VRE third | 1.35 | 1.17 | 0.73 | 0.82 | 0.74 | **0.52** |
| Iberdrola, implied L | 10.4% | 13.0% | 20.7% | 16.5% | 20.3% | **23.7%** |
| Endesa, implied L | 10.9% | 11.6% | 16.5% | 13.2% | 19.1% | 18.9% |
| CNMC HHI | 1,314 | 1,190 | 1,190 | 1,144 | 1,142 | **1,007** |

## Mechanism: thin markets, not bigger firms

Within every year, eta falls as the renewable share rises — mean within-year
Spearman correlation **−0.47**. The gradient has steepened sharply: the ratio of
eta in the top VRE tercile to the bottom went from 0.64 in 2018 to 0.14 in 2025.

The interpretation is that renewables displace thermal plant near the margin.
Wind and solar bid at or below zero and sit far inframarginal, so they do not
flatten the curve where the price is set; they push the crossing point into a
region where fewer flexible units remain. Same firms, same shares, fewer
competitors *at the margin*.

Dispersion tells the same story: the ratio of median eta to its 10th percentile
rose from 2.2 to 5.6. Market power is concentrating into fewer, more extreme
hours rather than rising uniformly.

## What this is, and is not

**It is a lower bound.** eta is built from the market-wide curve, i.e. the
residual demand facing an infinitesimal participant. A real firm's own supply is
excluded from its own residual demand, which can only make that curve steeper.
So `L_i ≥ s_i / eta`.

**It is not evidence that firms exercised this power.** It measures what the
market structure and the submitted curves made available, not what was taken.
Establishing the latter needs marginal costs.

**Two exclusions push the same way.** Market-splitting hours (6.6%) are dropped,
and those are the congested hours when residual demand is steepest. Zero-price
hours (4.5%, rising to 21% by 2026) are dropped because the Lerner index is
undefined at p = 0. Both mean the true figures are worse than reported.

**The share data is annual and MIBEL-wide.** Firm shares move within the year
with hydrology and outages. The within-year splits are indicative.

## The open problem

**The renewable share is not randomly assigned.** High-VRE hours are also mild,
low-demand, often weekend hours. The correlation above does not by itself
establish that renewables *cause* the thinning rather than merely coinciding
with hours that are thin anyway.

Resolving this needs an instrument. The established approach in this literature
(Cullen 2013; Kaffine et al. 2013; Novan 2015) uses **weather** — wind speed and
installed capacity — as an instrument for renewable output, on the argument that
weather shifts supply without otherwise affecting the market. That data has not
been collected yet and is the next step.

Until then the descriptive claim stands — the elasticity fell, and it fell most
in high-VRE hours — but the causal claim does not.

## Firm shares at market-period resolution

`scripts/analysis/firm_shares_hourly.py` replaces CNMC's annual shares with
shares computed per market period from cleared volume — 1,101,980 firm-period
observations over 79,036 periods. Within-year share dispersion runs from a
coefficient of variation of 0.24 to 1.55, so treating a share as constant
across a year was never innocuous.

**The within-year VRE gradient at firm level** (median Lerner in the top VRE
tercile divided by the bottom, mean over 2023–2026):

| firm | all tiers | confirmed only |
|---|---|---|
| Iberdrola | 3.89 | 1.46 |
| Endesa | 2.64 | 2.64 |
| EDP | 3.19 | 6.29 |
| Acciona | 6.16 | 6.13 |
| Axpo | 6.94 | 6.98 |

Every firm, under both mappings, faces a markedly higher implied markup in
high-VRE hours, and the gradient grows over the window. Firms mapped entirely
from confirmed evidence (Acciona, Axpo, Endesa) are identical across tiers.
Iberdrola and EDP move substantially, so **their magnitudes depend on the
inferred prefix assignments while the sign and the trend do not.**

**Do not read time trends off these shares.** Mapped coverage rises from 49.0%
of cleared sell volume in 2018 to 70.1% in 2026, because ESIOS is a snapshot
and units that exited early are absent, so measured shares climb mechanically.
Within-year comparisons hold coverage fixed and are sound; across-year trends
must come from the CNMC-based estimates above, which do not use this mapping.

## Data

All from public, token-free sources. 354 M unit-level day-ahead offers
(OMIE `curva_pbc_uof`), 5.95 M offer headers (OMIE `cab`), REE 5-minute system
data, CNMC published shares. See `CLAUDE.md`.
