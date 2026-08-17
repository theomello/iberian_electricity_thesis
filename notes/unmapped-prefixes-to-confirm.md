# What still needs confirming, and why

Every unmapped prefix carrying ≥1.5% of cleared sell volume, with the
hypothesis, the evidence for it, and the specific thing that would settle it.

**None of these are encoded in `build_unit_agents.py`.** They are written down
so the reasoning is auditable and so nobody quietly promotes a hypothesis to a
fact. Volume shares are cleared sell volume, January 2024.

## 2026-08-17: five resolved, checked against OMIE's own agent list

`REP`→Repsol, `GAS`/`GGA`→Naturgy, `IBG`→Iberdrola and `GTG`→TotalEnergies
are now in `PREFIX_AGENTS`, each checked against OMIE's published agent list
(`www.omie.es/informes_mercado/listados/LISTA_AGENTES.PDF`) rather than
asserted from the mnemonic alone. **`GTG` is the cautionary case**: the
mnemonic and the plant name ("TGPL") both suggested Tarragona Power, which is
50%+ Iberdrola-owned — a plausible-looking wrong answer. The official list
shows Tarragona Power's real code is `TAPOW`, and `TGPL` is instead the exact
code for TotalEnergies Gas and Power Limited. Worth remembering before trusting
any mnemonic match here, including the ones already in the "inferred" tier.

Three more were tried by hand this session and **explicitly withdrawn**, not
merely left unstudied:

- **`IGN`** (hypothesised Iberdrola, "Iberdrola Generación") — its cab names
  never mention Iberdrola, and Ignis Energía's real codes per the official
  list (`IGNIS`, `IGNS1`, `MORTE`, `CYDDP`) don't include `IGN` either. This
  matches a withdrawal already on record in `PREFIX_AGENTS`'s comments from an
  earlier pass — independently re-derived, same answer.
- **`GAL`** — Extresol I/II/III (a named plant inside this prefix) is
  ACS/Cobra Energía per public reporting, but `GAL` is not itself an OMIE
  agent code and the rest of the prefix (Montegordo, Tesosanto, Carbas) is
  unverified. A competing hypothesis already in `UNIT_PATTERNS`'s comments
  (`GAL`→GALP, the Portuguese oil major) suggests this prefix is genuinely
  mixed ownership, not a guess worth resolving either way.
- **`CLI`** — SEAT's Martorell cogeneration plant, named inside this prefix,
  is run by Cofely España (part of ENGIE) per Cofely's own filings — but
  Cofely's actual OMIE code is `ELYM`, not `CLI`, and the rest of the prefix
  (solar and wind assets) is unverified.
- **`IGV`** — "MOLINOS DEL EBRO, S.A." traces to Grupo Samca, but a second
  unit in the same prefix ("Renovables del Cierzo") was sold to Statkraft in
  2023–24 (from Enerfín). Genuinely mixed and time-varying ownership within
  one prefix; not a single-firm answer even if each unit is individually
  identifiable.

## The corroborating evidence: CNMC vs our mapping

`data/cnmc/cnmc_generation_shares.parquet` (CNMC *Cuadro 10*, generation share
by business group in the PDBF across MIBEL, 2008–2023) gives an independent
target. Comparing 2023 shares against what we attribute:

| firm | CNMC | ours | gap |
|---|---|---|---|
| IBERDROLA | 20% | 4.1% | **+15.9** |
| EDP | 13% | 0.0% | **+13.0** |
| ENDESA | 16% | 4.2% | **+11.8** |
| NATURGY | 6% | 1.1% | +4.9 |
| NEXUS | 4% | 0.0% | +4.0 |
| REPSOL | 4% | 2.9% | +1.1 |
| **AXPO** | **7%** | **7.1%** | **−0.1** |
| WIND_TO_MARKET | 2% | 2.9% | −0.9 |
| ACCIONA | 4% | 6.8% | −2.8 |

Two things follow. **AXPO matches almost exactly**, which is real validation of
the layer-3 dictionary — that entry was inferred purely from a plant name and
it lands within 0.1pp of the regulator's figure. And **ACCIONA is over by
2.8pp**, which says the three Acciona prefixes (`EGE`, `EDR`, `ACC`) may be
over-assigned; worth re-checking before relying on it.

The large positive gaps are the budget the unmapped prefixes have to fill.
That is corroboration, **not proof** — matching a prefix to a firm because the
volumes happen to fit is curve-fitting, and it would be circular to then use
the result as evidence about concentration. Use it to prioritise which
hypotheses to verify, never as the verification itself.

## Priority, measured over the WHOLE archive

Earlier versions of this list were computed on January 2024 alone. Recomputed
across all 101 months (`outputs/tables/unmapped_near_marginal_full.csv`), the
total near-marginal gap is **20.2%**, and it splits into two very different
kinds of target.

**A handful of large named plants — 21 units for 7.6pp of coverage:**

| prefix | units | gap | what it is |
|---|---|---|---|
| `RIB` | 3 | 1.73% | C.C. Ribatejo (PT) |
| `LAR` | 2 | 1.45% | C.C. Lares (PT) |
| `DOU` | 1 | 1.41% | Douro Internacional (PT) |
| `SIN` | 4 | 1.04% | — |
| `RPG` | 2 | 0.75% | — |
| `AMB` | 1 | 0.59% | C.C. Amorebieta (ES) |
| `RTG` | 3 | 0.58% | C.C. Turbogás (PT) |
| `ARR` | 2 | 0.37% | UOF Representada de Arrubal |
| `EGL` | 2 | 0.36% | Unidad de Oferta Portugal |
| `BAH` | 1 | 0.28% | C.C. Bahía de Bizkaia (ES) |

Named, large, individually identifiable thermal and hydro assets — the kind
covered by company reports and plant databases. Mostly Portuguese CCGTs.

**Versus the long tail — about 1,000 units for 6.6pp:**

`IGV` (177 units, 1.52%), `GNV` (164, 1.12%), `CEV` (250, 0.97%), `IGN` (91,
0.83%), `GES` (78, 0.79%), `VGE` (60, 0.61%), `GSV` (106, 0.43%), `CLI` (73,
0.35%). Aggregator portfolios with uninformative names. Poor return per unit,
and the natural target for the OMIE prefix question rather than manual work.

Top 10 prefixes are 11.7pp of the 20.2pp gap; top 20 are 16.4pp.

## The list

| prefix | vol | example name | hypothesis | evidence for | what would confirm it |
|---|---|---|---|---|---|
| `EDP` | 9.9% | "VENTA RE" | **EDP** | mnemonic is the company name; EDP has a 13pp gap and 0% attributed | OMIE reply, or an EDP report listing its Iberian bidding units |
| `ADO` | 3.9% | "HIDRO DOURO TOTAL" | EDP hydro (PT) | Douro cascade is Portuguese hydro; EDP is the main PT generator | Portuguese concession records; REN/ERSE plant lists |
| `DOU` | 3.6% | "DOURO INTERNACIONAL" | EDP hydro (PT) | same cascade, adjacent code | as above |
| `ACA` | 2.5% | "CAVADO" | EDP hydro (PT) | Cávado cascade | as above |
| `IBE` | 3.4% | "EÓLICA HABILITADA" | **Iberdrola** | mnemonic; Iberdrola has a 15.9pp gap | OMIE reply, or Iberdrola's registered-unit list |
| `IGN` | 2.6% | "SOLAR MULA" | Iberdrola renewables | `IGN` ≈ Iberdrola Generación; sits in the same gap | as above |
| `GED` | 6.3% | *(no cab name)* | Endesa? | Endesa has an 11.8pp gap; `GED` could be Generación EnDesa | **weakest hypothesis here** — no name evidence at all |
| `GGN` | 5.0% | "UNIDAD GENERICA ESPAÑA" | Naturgy (Gas Natural) | `GGN` ≈ Gas Natural; 4.9pp gap | OMIE reply |
| `NXV` | 3.3% | "UOF BIOMASA CUBILLOS DEL SIL" | **Nexus** | CNMC lists NEXUS at 4%, we attribute 0%, and `NXV` is 3.3% | Nexus Energía asset list |
| `HCG` | 2.7% | "U.O. PARQUES HABILITADOS S.A." | **EDP** (via HC) | ESIOS archive 83 has agent `HC G` = "EDP ESPAÑA, S.A." — the prefix matches an existing agent code | strongest of the unmapped set; verify the prefix↔agent link with OMIE |
| `CEV` | 2.4% | "TARIFA FOTOVOLTAICA <10" | unknown | none | — |
| `CLI` | 1.9% | "FV OURIKA" | unknown | none | — |
| `IGV` | 1.5% | "MOLINOS DEL EBRO, S.A." | unknown | name is a plant, not a group | Spanish commercial registry |

## How to close it, in order of cost

1. **`HCG` is nearly free.** `HC G` already exists as an ESIOS agent resolving
   to EDP España. If OMIE confirms that the code prefix is agent-assigned, this
   one follows immediately — and so do several others.
2. **The single question to OMIE** (option 3 in the email draft): *is the
   alphabetic prefix of the unit code assigned per agent?* A yes converts
   `EDP`, `IBE`, `GGN`, `IGN` from hypotheses into derivations, without OMIE
   releasing anything commercially sensitive.
3. **`GED` needs its own answer.** It is 6.3% of volume with no name and no
   mnemonic logic — the one entry where nothing but a direct source will do.
4. **Portuguese hydro** (`ADO`, `DOU`, `ACA`, plus `ALI`, `TAM`) is 10%+ of
   volume and turns on Portuguese concession ownership, which ERSE and REN
   document. A separate, tractable piece of work.
