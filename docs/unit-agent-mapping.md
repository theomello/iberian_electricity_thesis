# The unit → agent → firm mapping

What `data/omie/registry/unit_agents.parquet` is, how it was built, how far it
goes, and every way it can mislead you.

Built by `scripts/build/build_unit_agents.py`. Rebuild with:

```bash
.venv/bin/python scripts/build/build_unit_agents.py --tier all
.venv/bin/python scripts/build/build_unit_agents.py --tier confirmed
```

---

## Glossary

Spanish market vocabulary, because almost everything below is an acronym.

| term | expansion | what it actually is |
|---|---|---|
| **OMIE** | Operador del Mercado Ibérico de Energía | the *market* operator — runs the day-ahead and intraday auctions, publishes the bid data |
| **REE** | Red Eléctrica de España | the *system* operator — dispatches the grid, publishes ESIOS |
| **ESIOS** | Sistema de Información del Operador del Sistema | REE's transparency platform |
| **CNMC** | Comisión Nacional de los Mercados y la Competencia | the Spanish competition and markets regulator |
| **MIBEL** | Mercado Ibérico de Electricidad | the joint Spanish–Portuguese market; both countries clear against one merged bid stack |
| **UP** | Unidad de Programación | a *programming unit* — the registered entity that bids. Sometimes one plant, sometimes a whole cascade, sometimes a 6,500 MW portfolio |
| **UOF** | Unidad de Oferta Física | physical offer unit; OMIE's term for the same bidding entity |
| **UF** | Unidad Física | a *physical* unit — an actual generating asset, one level below the UP |
| **SM** | Sujeto de Mercado | the *market agent* — the legal entity that submits the offer and therefore decides the bid |

### The schedule ladder

Spanish market schedules are published in sequence, each refining the last.
Knowing which one a number refers to matters enormously — see the PDBF warning
below.

| code | expansion | content |
|---|---|---|
| **PDBC** | Programa Diario Base de Casación | the raw day-ahead auction result — what cleared in the auction, nothing else |
| **PDBF** | Programa Diario Base de **Funcionamiento** | PDBC **plus bilateral physical contracts and self-scheduling**. The starting point for system operation. Roughly **1.73×** the day-ahead cleared volume |
| **PDVP** | Programa Diario Viable Provisional | after technical/network constraints are resolved |
| **PDVD** | Programa Diario Viable Definitivo | after ancillary services |
| **PHF** | Programa Horario Final | the final hourly schedule, after intraday markets |

### File codes used here

| code | what it holds |
|---|---|
| `curva_pbc_uof` | the day-ahead bid curves — every offer, accepted and rejected |
| `cab` | *cabecera* — the offer **header**: plant name, maximum power, minimum-income condition |
| `det` | *detalle* — the offer detail: price/quantity steps. **No agent field** |
| `pdbce` | the day-ahead cleared schedule broken out **by company**, carrying a sparse `group_tag` |

### Econometric shorthand

| term | meaning |
|---|---|
| **HHI** | Herfindahl–Hirschman Index — sum of squared market shares, the standard concentration measure |
| **IV / 2SLS** | instrumental variables / two-stage least squares — used here to address the fact that renewable output is not randomly assigned |
| **η (eta)** | residual demand elasticity at the clearing price; `L = s/η` |

---

## Why this file exists

Market power is a property of the **firm**, not the unit. The residual demand
facing firm *i* is total demand minus *everyone else's* supply, so excluding
"firm *i*'s own units" requires knowing which units are *i*'s. OMIE publishes
5,137 unit codes and no ownership. This file supplies the grouping.

## Fields

| column | meaning |
|---|---|
| `unit` | OMIE bidding unit code, joins to the bid files |
| `agent` | Sujeto de Mercado — who submits the offer |
| `firm` | parent group above the agent (`IBEG`, `IGNU`, `IBGT` → IBERDROLA) |
| `agent_name` | agent's legal name, from ESIOS archive 83 |
| `agent_type` | `Productor`, `Comercializador`, `Representante`, … |
| `source` | which layer produced the agent: `esios` / `name` / `prefix` |
| `confidence` | `authoritative` / `confirmed` / `inferred` / `group_tag` |
| `tech_esios` | technology from ESIOS's 41-level taxonomy (registered units only) |
| `tech_cab` | technology parsed from the `cab` plant name |
| `max_power_mw` | nameplate capacity from `cab` |
| `agent_owner` | **OMIE's own published owner**, from the *Listado de Unidades* snapshots — independent of the four layers below |
| `agent_owner_pct` | ownership percentage OMIE states (6 units below 100%) |
| `agent_owner_snapshot` | which snapshot the label came from |
| `agent_owner_changed` | owner is not constant across the snapshots naming this unit (548 units) |
| `tech_omie` | OMIE's technology, normalised, from the latest snapshot — use for 2022 onward |
| `tech_omie_early` | same, from 2022-02-08 — **the backward projection for 2018–2021** |
| `tech_omie_stable` | the two agree, or only one exists (39 units disagree) |

### `agent_owner` is a second opinion, not a better `agent`

Added 2026-09-03. It comes from `omie_unit_lists.parquet` and deliberately does
**not** fill `agent` or `firm`, so a disagreement between OMIE's label and our
inference stays visible rather than being silently resolved.

It covers far more: **4,055 of 5,137 units against 2,441**, and **99.8% of
near-marginal offered sell volume against 89.1%** (January 2024). It also
resolves every prefix `PREFIX_AGENTS` left unmapped on purpose — `CEV` is
Energya VM, `IGV` and `IGN` are both Ignis Energía, `NEX` Nexus, `VGE` Repsol,
`GAL` Galp, `GES` Gesternova, `PEG` Endesa, `CLI` Holaluz-Clidom.

**But it answers a different question.** `agent` names the registered operator;
`agent_owner` names the commercialising entity that submits the offer. `ABA1` is
Barbo Energías Renovables in ESIOS and **Wind to Market** here; `ACE4` is
Naturgy Ciclos Combinados and **Gas Natural Comercializadora**. Both are true,
and for market power the listing's entity is usually the one you want — it is
who decides the bid. Of the 866 units carrying both a legal name and an owner,
a naive string comparison agrees on 57.4%, but most of the gap is formatting
(accents, `S.L.U.` suffixes) rather than a real conflict.

**Do not treat it as static.** 548 units change owner across snapshots, and the
column carries the latest one. Use `agent_owner_changed` to exclude them, or go
back to `omie_unit_lists.parquet` for the nearest-preceding snapshot.

### Why technology may be projected backwards and ownership may not

Only four of the twelve snapshots carry a technology — 2022-02-08, 2023-05-16,
2023-12-30, 2025-01-31 — so under the nearest-*preceding* rule that ownership
uses, **2018–2021 has none at all**. Projecting the 2022-02-08 label backwards
fills it. The argument, measured 2026-09-03, is four claims and one admission.

**1. Technology is three times more stable than ownership.** Same units, same
four snapshots: normalised class changes for **2.07%** of units, `agent_owner`
for **6.19%**. This is the asymmetry the whole thing rests on, and it is why the
same move is *not* licensed for ownership.

**2. Most apparent instability is OMIE relabelling itself.** 78 units change raw
label; only 41 change normalised class. Of the 24 raw changes among dispatchable
units, **21 are pure renames** — "VENTA GENERICA" → "Unidad Generica",
"RE Tar. CUR Eólica" → "RE Mercado Eólica" (same technology, different tariff
regime), "Cliente cualificado" → "Rep. de consumidores directos". Normalising
through `lib/omie_tech.classify` removes them.

**3. What genuine change remains sits at the far end, away from the target
period.** Nearly every class change lands at the **2025-01-31** snapshot, and is
dominated by biomass↔cogeneration on small *Régimen Especial* aggregation units.
The 2022-02-08 and latest labels differ on **1.22%** of units, and units whose
class ever changed account for **0.45%** of near-marginal offered volume. Note
the direction: projecting *backwards from the earliest* technology-bearing
snapshot avoids the 2025 relabelling entirely, which is why `tech_omie_early`
exists rather than reusing `tech_omie`.

**4. It survives a check against a genuinely independent source.** Against the
`cab`-name technology — different file, different extraction, no shared
input — the projected class agrees on **93.3%** of the 522 units carrying both,
and on **85.6%** of testable 2018 near-marginal volume. Collapsing sub-classes
that differ in granularity rather than kind (`coarsen`) raises that to
**98.7%**: the residual conflicts are hydro vs pumped storage and waste vs
biomass, not gas vs wind.

**The admission.** Stability is only *observable* from 2022 onward, so the
extrapolation into 2018–2021 is exactly the thing the evidence cannot reach. The
`cab` cross-check is evidence for it, not proof, and a plant that changed fuel
before 2022 is invisible. Spain's coal fleet largely closed rather than
converted over the window, which makes that risk small rather than zero.

What it buys, on near-marginal offered sell volume:

| year | projected from 2022-02-08 | `cab` names alone |
|---|---|---|
| 2018 | **100.0%** | 94.9% |
| 2019 | 99.9% | 92.4% |
| 2020 | 99.6% | 93.7% |
| 2021 | 94.9% | 77.9% |

It also gains *specificity*, not just coverage: `ABO1` is only "thermal" from its
`cab` name and **coal** in the listing.

**For callers.** `tech_omie_early` implements the argument above for 2018–2021;
`tech_omie` is the one to use from 2022 on. `marginal_technology.py` does this
without the columns, labelling each period from the snapshot **nearest it in
time** per unit — one rule that resolves to 2022-02-08 for 2018–2021 and to a
contemporaneous snapshot later. It took the latest snapshot for every year until
2026-09-03, which pushed the 2025 relabelling back onto 2018; correcting it moved
**60 of 22,067** periods, 55 of them pre-2022 and 48 a single
cogeneration→biomass reversal. Post-2021 the choice is immaterial (0.19% of
periods at worst) because the near-marginal band is large persistent plant.

## How it is built — four layers, descending evidence

1. **`authoritative`** — exact match of the unit code to REE's programming-unit
   registry (ESIOS archive 82), which publishes the Sujeto de Mercado directly.
   592 units.
2. **`confirmed`** — an ESIOS agent code appears inside the `cab` plant name
   (`GREPSC1` is named "REPSB GENERICA VENTA"), or the name states the company
   ("AXPO VENTA R. ESPECIAL"). 1,229 units.
3. **`inferred`** — the unit-code mnemonic corroborated by an independent
   signal, usually the CNMC share gap. `EDP`, `IBE`, `GGN`, `NXV`, the
   Portuguese hydro cascades, `GED`. 611 units.
4. **`group_tag`** — OMIE's own corporate tag in `pdbce`, six of nine tags
   mapped. 26 units that nothing else reaches.

## Coverage

Measured on the **near-marginal band** (offers within ±5 €/MWh of the clearing
price), because price is set at the margin. A 5 GW unit offering at 0 €/MWh is
inframarginal in almost every period and contributes nothing to the slope of
residual demand, so total-volume coverage flatters the mapping for exactly the
units that matter least.

| stage | near-marginal coverage |
|---|---|
| starting point (`group_tag` alone) | 37.7% |
| + ESIOS, names, confirmed prefixes | 47.4% |
| + inferred prefixes | ~78% |

---

## Five ways this can mislead you

### 1. CNMC measures PDBF; the bid data measures the day-ahead auction

This is the trap that cost the most time. CNMC's published shares are computed
on the **PDBF**, which includes bilateral contracts. Comparing them to
day-ahead cleared shares makes firms look under-mapped when they are not:

| firm | our day-ahead | our PDBF | CNMC |
|---|---|---|---|
| Iberdrola | 7.3% | **22.2%** | 20% |
| Naturgy | 1.0% | 5.2% | 6% |
| Acciona | 6.5% | 4.3% | 4% |

Iberdrola looked half-missing for hours of work. It was not missing; it sells
most of its output bilaterally rather than into the day-ahead auction.

**And this is economically substantive, not just bookkeeping.** For market
power in the day-ahead auction the relevant share is day-ahead *exposure*:
volume sold forward at a fixed price earns nothing extra when the day-ahead
price rises. That is the contract-position term in Wolak (2000) and Hortaçsu &
Puller (2008). Using PDBF-based shares **overstates** the day-ahead markup
incentive.

### 2. Coverage drifts — in opposite directions depending on the weighting

This one is easy to get backwards, and I did.

**On total cleared sell volume, coverage rises**: 49.0% in 2018 to 70.1% in
2026. ESIOS is a snapshot of today's registry, so units that traded early and
exited are absent, and a firm's measured share climbs mechanically.

**On the near-marginal band, coverage falls**: 88.4% in 2018 to 69.8% in 2026,
whole-archive average 79.8%. Early-window marginal offers came from thermal
plants REE registers; recent marginal offers increasingly come from commercial
renewable vehicles nobody registers.

The near-marginal figure is the one that governs eta, so **the worst-covered
years are 2024–2026 — exactly where the renewable effect is strongest**.

- Within-year comparisons hold coverage fixed and are **valid**.
- Across-year trends in these shares are **contaminated** either way. Use the
  CNMC-based estimates, which do not depend on this mapping.
- Always state which weighting a coverage number uses. A single-month figure
  happens to be representative of the archive average (January 2024 reads 80.5%
  against 79.8%) but says nothing about the trend.

### 3. An inferred assignment was wrong, and will not be the last

`IGN` was assigned to Iberdrola on the mnemonic "Iberdrola Generación" and
**withdrawn** on inspection: across its 55 units the names are "UOF XALLAS I",
"SOLAR MULA", "GALICIA VENTO", "PE CABEZA MESÁ" — a mixed wind and small-hydro
portfolio in which "IBERDROLA" never appears and "IGNIS" appears twice. It is
almost certainly Ignis Energía. That was 2.5% of cleared sell volume.

Always run `--tier confirmed` alongside `--tier all`. A conclusion that holds
under both does not depend on any inference.

### 4. The agent is not the owner

Several large agents are **representatives** trading third-party assets — ESIOS
archive 83 flags 11 of 739 agents as `Representante`, and `EGV` is Axpo with
394 units. Unit names say so explicitly: "UOF **REPRESENTADA** DE ARRUBAL 1".

For market power the agent is arguably the *right* object, since it controls
the bid. But it is **not** plant ownership and the two must never be conflated.
Representatives do bid strategically: median offer 85 €/MWh, only 17.7% of
their volume at ≤0 €/MWh.

### 5. Firm shares from this file are lower bounds

Roughly 22–27% of volume is unattributed and stays in the denominator, so every
share is a floor. Do not substitute them for `s_i` without saying so.

---

## What is still missing, and why it is not a diligence failure

OMIE knows which agent submits each unit's offers and does not publish it. REE
publishes the agent but only for units it dispatches, which structurally
excludes the commercial bidding vehicles. Every public route was tried and is
recorded in `CLAUDE.md`: `det` has no agent field, `indisp` uses a different
code space, ESIOS archive 81 links to the same namespace as 82, the full OMIE
catalogue of 59 datasets contains no agent registry.

The residual is concentrated in small units whose **median offer price is 0.00
€/MWh** — price-takers that never set the price, and so sit outside the
near-marginal band that determines η.

One cheap thing would close much of it: if OMIE confirms that the alphabetic
prefix of the unit code is assigned per agent, the `inferred` tier becomes a
derivation. That is the primary ask in
[`../notes/omie-data-request.md`](../notes/omie-data-request.md).
