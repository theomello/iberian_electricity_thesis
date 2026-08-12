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

### 2. Coverage drifts upward over time

Mapped share of cleared sell volume rises from **49.0% in 2018 to 70.1% in
2026**, because ESIOS is a *snapshot* of today's registry and units that traded
early and exited are simply absent. Unmapped volume stays in the denominator,
so a firm's measured share climbs mechanically.

- Within-year comparisons hold coverage fixed and are **valid**.
- Across-year trends in these shares are **contaminated**. Use the CNMC-based
  estimates, which do not depend on this mapping.

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
