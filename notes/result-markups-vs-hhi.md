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

**This has now been tested.** ERA5 weather was fetched (10 sites, hourly, full
window) and used to instrument the renewable share, following Novan (2015) and
Fabra, Rapson, Reguant and Wang (2021).

```
log(eta_t) = b · vre_share_t + log demand + temp + temp²
             + hour + month + year + day-of-week FE
```

instrumented with wind speed at the wind sites, its cube, and irradiance at the
solar sites. Standard errors clustered by day.

| | coefficient | per +1pp VRE share |
|---|---|---|
| OLS | −0.0291 (0.0007) | −2.87% |
| **2SLS** | **−0.0280 (0.0002)** | **−2.76%** |

First stage is strong — partial F on the excluded instruments is 29,240, R² 0.71.

**OLS and IV agree to within 4%.** Conditional on demand, temperature and the
fixed effects, the endogeneity of renewable output was not driving the
association. A one-standard-deviation rise in the renewable share (18.1 pp)
implies a **39.7% fall in eta**.

The remaining caveat is the exclusion restriction, which is an assumption
rather than a result: wind is correlated across Iberia and France, so windy
periods may shift interconnector flows directly, and extreme weather affects
thermal availability as well as renewable output. Temperature is treated as a
control throughout, never an instrument, because it moves demand directly.

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

**The time-trend caveat is lifted for 2018–2024, on the `owner` tier only**
(2026-09-04). It previously read: coverage "rises from 49.0% of cleared sell
volume in 2018 to 70.1% in 2026… across-year trends must come from the
CNMC-based estimates". Two things were wrong with that.

**The stated mechanism no longer exists.** Re-measured on the current build,
inference-chain coverage of cleared sell volume runs **75.6% in 2018 to 73.9%
in 2026** — flat and slightly falling, not 49→70. The 49% figure describes a
build of `unit_agents.parquet` that predates the 2026-08-17/18 prefix
expansion. Residual drift is 70.4–80.3%, a 10-point range rather than 21.

**And OMIE's published owner removes most of what remains.** `agent_owner`,
added 2026-09-03, covers 92.7–95.7% of cleared sell volume across 2018–2024 —
a 3-point range — falling to 90.1% (2025) and 85.0% (2026) only because the
unit listings stop at the 2025-01-31 snapshot. Run
`firm_shares_hourly.py --tier owner` for anything across years.

| | 2018 | 2020 | 2022 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| inferred `firm` | 75.6% | 75.3% | 80.3% | 71.7% | 70.4% | 73.9% |
| `agent_owner` | 92.9% | 93.7% | 95.7% | 94.8% | 90.1% | 85.0% |

**Three conditions on using it.** Trends stop at **2024** — 2025–26 still carry
a coverage decline, and only a newer OMIE listing fixes that. The direction of
any remaining bias is now known and *opposes* the headline: coverage falls
across 2024–26 while measured Lerner rises (Iberdrola 12.8% → 23.3%), so that
rise cannot be a coverage artefact, which is what the old caveat feared. And
the tier's **share levels** depend on rolling legal entities up to firms, which
`agent_owner` does not do for you — see the grouping note below.

**Grouping is the new weak point, and it is smaller but real.** `agent_owner`
names legal entities, not groups. On 2023 cleared sell volume, `SU ELETRICIDADE`
is 7.96% and is EDP's Portuguese regulated supplier; `GAS NATURAL
COMERCIALIZADORA` is 2.83% and is Naturgy. `OWNER_ALIASES` in
`firm_shares_hourly.py` encodes four such cases, each corroborated twice from
the data (unit codes plus the independent ESIOS chain) rather than asserted —
`SU ELETRICIDADE`'s units are coded `EDPSVD1–3`, `CURENERGÍA`'s `IBCUC01`.
Adding them moved Naturgy from absent to 7.6–8.6%, against CNMC's 6–8%. **The
list is not exhaustive**, so treat owner-tier *levels* as diagnostic until a
proper group mapping exists; the *coverage* claim above does not depend on it.

Within-year comparisons remain valid on every tier, as before.

## CNMC measures PDBF, not the day-ahead auction — and it matters

CNMC's *Cuadro 10* is computed on the **PDBF** (programa diario base de
funcionamiento), which includes bilateral contracts and self-scheduling, not
only day-ahead cleared volume. On January 2024 the PDBF sell total is **1.73×**
day-ahead cleared volume.

Measured on PDBF, our mapping matches CNMC closely:

| firm | our day-ahead share | our PDBF share | CNMC |
|---|---|---|---|
| Iberdrola | 7.3% | **22.2%** | 20% |
| Endesa | 4.9% | 11.5% | 16% |
| EDP | 23.6% | 15.4% | 13% |
| Naturgy | 1.0% | 5.2% | 6% |
| Acciona | 6.5% | 4.3% | 4% |

So the "missing half of Iberdrola" was a **definitional mismatch, not missing
units**. Iberdrola sells a large share bilaterally and through its retail arm,
so its day-ahead cleared volume is far below its total generation programme.

**This has a direct consequence for the headline result.** `L = s/eta` for the
*day-ahead auction* should use the firm's day-ahead exposure, not its total
programme: volume already sold forward at a fixed price earns nothing extra
when the day-ahead price rises. That is the contract-position term `theta` in
Wolak (2000) and Hortaçsu & Puller (2008). Using CNMC's PDBF-based shares
therefore **overstates** the day-ahead markup incentive, in the same way that
ignoring forward contracts overstates market power in Bushnell, Mansur &
Saravia (2008).

The Lerner figures above should be read as an upper bound *on this dimension*
even while they remain a lower bound on the elasticity dimension. Recomputing
them on day-ahead shares is the obvious next step.

## The contract position is directly observable

Only **7.0%** of Spanish nuclear output passes through the day-ahead auction.
The rest is nominated bilaterally straight into the operating schedule:

| unit | day-ahead cleared | PDBF | % via auction |
|---|---|---|---|
| Ascó 1 | 540 MWh | 739,959 MWh | **0.1%** |
| Ascó 2 | 10,624 | 737,057 | 1.4% |
| Vandellós II | 201,447 | 775,957 | 26.0% |
| Cofrentes | 29,467 | 753,591 | 3.9% |
| Trillo | 21,589 | 733,865 | 2.9% |

Nuclear is 12.4% of PDBF sell volume and 1.5% of day-ahead cleared volume.

This explains why Endesa's day-ahead share (4.9%) sits so far below CNMC's 16%:
Endesa is the most nuclear-heavy and most vertically integrated of the majors,
so the largest share of its output is pre-contracted and never reaches the
auction. Nothing is wrong with the mapping of its plants.

**And it hands us something the literature has to infer.** The markup condition
is `p = C' − (RD_i − θ_i)/RD'_i`, where `θ_i` is the firm's forward position;
a firm short of its position bids *below* marginal cost. Hortaçsu and Puller
(2008) identify `θ` indirectly, from the quantity at which a firm's supply
curve crosses its marginal cost curve. Here **`θ` is observable directly** as
PDBF minus day-ahead cleared volume, per unit per period, because OMIE
publishes both schedules.

That is worth pursuing: it would let the contract position be measured rather
than inferred, and it is the single largest correction still missing from the
Lerner estimates.

## Data

All from public, token-free sources. 354 M unit-level day-ahead offers
(OMIE `curva_pbc_uof`), 5.95 M offer headers (OMIE `cab`), REE 5-minute system
data, CNMC published shares. See `CLAUDE.md`.
