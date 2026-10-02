# The unit → firm mapping: a report (2026-10-02)

Script: `analysis/ownership_mapping_report.py`. Tables:
`outputs/tables/ownership_mapping_report_{year,firm,pairs,coowned}.csv`. How the
mapping is built: [`docs/unit-agent-mapping.md`](../docs/unit-agent-mapping.md).

**Status, 2026-10-02: fixed in code, panels not yet rebuilt.** `lib/unit_ownership.py`
attributes by date and share (§6, item 1) and the renamings are merged (item 2);
`firm_x.py`, `firm_incentive_rebuild.py` and `residual_demand_firm.py --tier owner`
use it, pinned by `qa/check_unit_ownership.py`. The stored panels and every result
built on them predate the fix until the rebuild (item 3).

**In one line.** The mapping covers 90–98% of cleared volume (2018–2025), but the firm panels
use each unit's latest listed owner for the whole window. That misplaces 2–5% of
sell volume a year and up to 9% of buy volume in 2018–2019. One case is a bug, not
a timing issue: **each co-owned nuclear reactor is attributed whole to one of its
co-owners, not always the largest**. That overstates Naturgy's average net position
by about 315 MW, half its mean, and understates Endesa's by about 268 MW.

## 1. The four entities

- A **unit** is what an offer is for: one reactor, one gas turbine group, a whole
  hydro cascade (Iberdrola's DUER is the Duero), or a portfolio (EDP's EDPSVD1 is
  6.5 GW of renewables). 5,137 units, 2018–2026: 3,997 sell, 1,124 buy.
- An **agent** submits the offers (~738 in REE's registry snapshot).
- An **owner** is a legal entity in OMIE's listings (*Listado de Unidades*, 12
  snapshots 2014-09-24 → 2025-01-31, none for 2021), with an ownership share.
- A **firm** is the group the owners roll up to (`build_owner_groups.py`): 1,096
  groups before the 2026-10-02 merges (1,091 after), 156 owning sell units, 49 owning
  dispatchable plant, 21 with ≥ 100 MW of it. (A first version said 1,092, counted
  on the wrong column.)

## 2. Coverage

Share of cleared volume whose unit has an owner group:

| year | sell | buy |
|---|---|---|
| 2018 | 0.930 | 0.984 |
| 2020 | 0.944 | 0.970 |
| 2022 | 0.974 | 0.936 |
| 2024 | 0.941 | 0.960 |
| 2025 | 0.902 | 0.951 |
| 2026 (Jan–Jun) | 0.812 | 0.935 |

The 2026 sell figure falls because units registered after the last listing
(2025-01-31) have no owner yet.

How the groups were formed, by cleared volume (both sides): the ESIOS chain's
verdict on an entity's own units 66.3%, standing alone ("self") 18.2%, a stem
match 7.8%, group-level merges 2.1%, hand-verified 0.2%, no group 5.3%.

## 3. Today's owner for the whole window

`firm_x.py` and `firm_incentive_rebuild.py` read `unit_agents.agent_owner`, the
latest listing naming the unit. Share of cleared volume whose group then differs
from the group in force at the time (nearest preceding listing):

| year | sell | buy |
|---|---|---|
| 2018 | 0.034 | 0.092 |
| 2019 | 0.053 | 0.086 |
| 2020 | 0.045 | 0.034 |
| 2021 | 0.043 | 0.046 |
| 2022 | 0.019 | 0.022 |
| 2023 | 0.018 | 0.006 |
| 2024 | 0.037 | 0.001 |
| 2025 | 0.035 | 0.000 |

What is behind it (largest pairs, TWh over 2018–2026):

| attributed to (static) | owner at the time (dated) | TWh | what it is |
|---|---|---|---|
| Naturgy | Iberdrola | 33.6 | **co-owned nuclear: Trillo, Almaraz 1** (§4) |
| XXI | Endesa | 24.5 | Endesa's regulated supplier (pass-through, excluded from n anyway) |
| Iberdrola | Endesa | 19.3 | **co-owned nuclear: Vandellós II** (§4) |
| Eni Plenitude | Aldro | 16.4 | real: Eni bought Aldro Energía |
| TotalEnergies | Total | 10.8 | **renaming not merged**: the same firm under two groups |
| TotalEnergies | EDP | 8.2 | real: EDP sold its Spanish retail to TotalEnergies (2020-12-01) |
| Axpo | Bizkaia | 4.9 | Bizkaia Energía's plant, now represented by Axpo |
| Holaluz | Clidom | 2.4 | renaming not merged |
| Gas | Gas Europe | 1.4 | renaming not merged |
| LDA | Unipessoal | 1.5 | **grouping artifact**: Portuguese legal forms taken as names |

Three kinds, then: real ownership changes (EDP's retail, Aldro), renamings the
grouping has not merged, and the co-ownership bug.

**EDP's 2018–2020 purchases are understated.** Its retail units belong to
TotalEnergies in the static mapping for the whole window, though EDP owned them
until 2020-12-01. A by-firm table indexed on the static owner cannot show this:
the volume is missing from EDP, not added to it.

## 4. Co-owned nuclear: a bug

Five reactors are listed with several owners. The mapping kept one of them,
arbitrarily:

| reactor | owners in the 2025-01-31 listing | attributed to |
|---|---|---|
| Almaraz 1 | Iberdrola 52.7%, Endesa 36.0%, Naturgy 11.3% | **Naturgy** |
| Trillo | Iberdrola 49.0%, Naturgy 34.5%, Iberenergía 15.5%, Endesa 1.0% | **Naturgy** |
| Vandellós II | Endesa 72%, Iberdrola 28% | **Iberdrola** |
| Almaraz 2 | as Almaraz 1 | Iberdrola (largest, by chance) |
| Ascó 2 | Endesa 85%, Iberdrola 15% | Endesa (largest) |

They carry 4.2% of all cleared sell volume. Against a split by ownership share,
the static mapping shifts each group's average net position by:

| group | MW | mean exposed n in `firm_x` |
|---|---|---|
| Naturgy | **+315** (overstated) | −635 |
| Endesa | **−268** (understated) | −2,503 |
| Iberenergía | −46 | — (Trillo's 15.5%; probably EDP's stake, *to verify*) |
| Iberdrola | −2 | −586 |

Nuclear runs flat, so the error is mostly a shift in the level of n. But it is
half of Naturgy's mean position and moves the hours in which Naturgy is a net
seller. Every firm-level result so far uses these positions: legs C and D, the
forecast first stage, and the leg D rerun.

## 5. Representation and pass-through

- **Represented plant.** 75.8% of Axpo's sell volume comes from units named as
  third parties' plant (REPRESENTAD*, R. ESPECIAL), 10.1% of Cepsa's. For those,
  the group's X is not its own exposure. The name flag undercounts: Nexus,
  Gesternova and Wind to Market also trade for others without saying so in the
  unit names.
- **Pass-through.** Regulated suppliers are already excluded from the exposed n:
  29.0% of EDP's cleared volume (SU Eletricidade) and 15.9% of Iberdrola's
  (Curenergía).

## 6. What to fix, in order

1. **Ownership by date and by share.** Attribute each unit-day to the owners in
   force that day (nearest preceding listing), each with its ownership share.
   This fixes the co-owned reactors and EDP's retail together. It is
   task_7d2e874c (dated ownership in `firm_x`) widened to shares.
2. **Merge the renamings**: Total → TotalEnergies, Clidom → Holaluz, Gas Europe →
   Gas; resolve Iberenergía (EDP?) and the "LDA"/"Unipessoal" artifacts.
3. **Rebuild** `firm_incentive_net`, `firm_x`, the leg C and D panels, and rerun
   their results and today's two first stages.
