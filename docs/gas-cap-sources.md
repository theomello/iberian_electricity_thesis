# The Iberian gas cap — what the sources say, checked against our data

2026-10-28. One place for every fact the gas-cap design (`docs/specs/2026-10-28-gas-cap-conduct-design.md`)
rests on: which source states it, where, and whether our own files agree. Primary sources first;
secondary sources only where no primary one states the fact. PDFs are in `papers/` (gitignored).

## 1. The legal sources

| document | file in `papers/` | what it settles |
|---|---|---|
| Real Decreto-ley 10/2022, 13 May 2022, consolidated text (BOE-A-2022-7843, incl. RDL 3/2023) | `BOE_RDL_10_2022_consolidado.pdf` | eligible plants (art. 2.1), bilateral energy excluded (art. 2.2), Y per MWh produced and the PRGN path (art. 3), Y = 0 when PGN < PRGN (art. 3), MIBGAS supplies PGN (art. 3) |
| Orden TED/517/2022, 8 June 2022 (BOE-A-2022-9435) | `BOE_Orden_TED_517_2022.pdf` | start: agents internalise Y from the day-ahead auction of **14 June 2022**, i.e. delivery from 15 June |
| European Commission, SA.102454 (Spain) and SA.102569 (Portugal), C(2022) 3942 final, 8 June 2022, public version | `EC_2022_SA102454_iberian_mechanism_decision.pdf` | the formula **in text** (the BOE prints it as an image), the meaning of 0.55, the intended bidding behaviour, the beneficiaries |
| CNMC, *Nota aclaratoria* on RDL 10/2022 (October 2022) | `CNMC_2022_nota_aclaratoria_RDL10.pdf` | how the cost is passed to consumers; not needed for the supply side |

## 2. What the mechanism is

| fact | source, exact place | quote or content |
|---|---|---|
| The subsidy formula | EC decision, recital (36) | "Y = (P_GN – P_GNT) / 0.55 … Y is the unit amount of support, in EUR per MWh (for electricity production)" |
| What 0.55 is | EC decision, recital (36); also (146) | "0.55 reflects the assumed average efficiency (55 %) of gas-fired power plants that influence prices most often in the Iberian electricity market" |
| Same subsidy for every eligible plant | EC decision, recital (39) | "all technologies eligible under the measure will receive the same amount of compensation, regardless of their input fuel or production costs" |
| Who is eligible | EC decision, recitals (24), (29), (33); RDL art. 2.1 | gas-fired plants, coal plants, and CHP plants without regulated remuneration |
| Eligible CHP is identifiable | EC decision, recital (42) | each eligible CHP plant gets "an independent bidding and scheduling unit" |
| Physical bilateral energy gets no subsidy | RDL art. 2.2; EC decision, recital (33) | only energy offered to the market operator |
| Subsidy also on intraday and balancing output | EC decision, recital (33) | "also be granted for their production in the intraday and balancing markets" |
| **Bids are meant to fall by Y** | EC decision, recitals (33), (36) | the aim is reducing "their production costs and, correspondingly, the bids they submit"; beneficiaries "are expected to submit bids … taking into account the amount of support they will receive" |
| Y = 0 when gas is below the reference | RDL art. 3 | "Si el precio del gas natural (PGN) … es inferior al precio de referencia … (PRGN), el importe de la cuantía unitaria diaria del ajuste, Yi, será nulo" |
| PRGN path | RDL art. 3 (consolidated) | 40 €/MWh to December 2022; 2023: 45, 50, 55, 56.1, 57.2, 58.3, 59.4, 60.6, 61.7, 62.8, 63.9, 65 |
| Start | Orden TED/517/2022 | "se fija como fecha de inicio del mecanismo de ajuste el 14 de junio de 2022", for the day-ahead auction held that day |
| End | RDL art. 1 as amended by RDL 3/2023 | 31 December 2023 (first set at 31 May 2023) |

**Correction to earlier notes.** `notes/rq-gas-cap-conduct.md` (2026-08-14) and the `marginal_cost_capped_*`
columns describe the cap as fixing "the gas price a plant is permitted to use in its bid". The decree does
not do that: it pays a per-MWh subsidy at a fixed 0.55, the same for gas and coal. The difference for a gas
plant is (PGN − PRGN)(1/eff − 1/0.55), about €13/MWh for an efficiency of 0.52 in August 2022; for coal it
is the whole subsidy, which the capped columns left out. Fixed 2026-10-28 by `subsidy_eur_mwh` and
`marginal_cost_subsidised_*` in `implied_marginal_cost_daily.parquet`; the capped columns are unchanged so
that earlier results reproduce.

## 3. Facts checked against our data

| claim | source | their figure | ours | agrees? |
|---|---|---|---|---|
| MIBGAS mean, Jan–May 2022 | EC decision, recital (5) | €92/MWh | €91.4 (`mibgas_price_index_daily`) | yes |
| MIBGAS mean, 2015–2020 | EC decision, recital (5) | €18/MWh | €16.7 for 2018–2020 only (our series starts 2018) | not comparable |
| Iberian day-ahead price, Jan–May 2022 | EC decision, recital (5) | €213/MWh | €213.2 ES, €213.4 PT (`omie_day_ahead_prices`) | yes |
| Iberian day-ahead price, 2021 / 2019 | EC decision, recital (5) | €112 / €48 | €111.9 / €47.7 | yes |
| Price-setting technology in Spain, 2021 | EC decision, recital (22), from OMIE | hydro 54.9%, renewables/CHP/waste 23.6%, gas 15.9%, coal 1.5% | hydro 52.2%, gas 13.2%, coal 1.5%, cogeneration 9.5%, wind 10.3%, pumped storage 9.4% (`marginal_technology.csv`, sample months, MIBEL-wide) | close; categories differ (we split pumped storage out) |
| The subsidy's binding window | RDL art. 3 with MIBGAS | positive while PGN > PRGN | positive on 243 days, **2022-06-15 → 2023-02-25**, max €336.4/MWh (`subsidy_eur_mwh`) | consistent |
| Exports to France rose | Hidalgo-Pérez et al. 2024 (over 80%); Lou et al. 2026 | rise | net scheduled export on the France line: −480 MW (2021-06-15 → 2022-06-14), +94 MW (2022-01-01 → 06-14), **+1,679 MW** (2022-06-15 → 2023-02-25); line export-full 82% of hours while binding against 32% before (`omie_interconnection_capacity`, `france_link_hours`) | yes, in direction; a percentage is meaningless on a near-zero base |
| Gas offers fell at the start | regulator's intent (EC (36)) | fall by Y | median offered price of the 46 plant-specific-efficiency gas units, capacity-weighted: €145.0 (delivery 14 June) → €103.2 (15 June) → €91.2 (16 June) (OMIE bids, status `O`) | yes, in direction; the size is the design's question |

## 4. Secondary sources, and what each is used for

| paper | file | used for |
|---|---|---|
| Haro Ruiz, Schult & Wunder (2024), IWH DP 5/2024; Applied Economics Letters | `HaroRuiz_Schult_Wunder_2024_IWH_DP.pdf` | the price effect (~40%), the target the re-clearing check must reproduce |
| Lou, Pollitt, Robinson & Arcos-Vargas (2026), Energy Economics | `The-Iberian-exception--What-was-the-cost-of-distorting-electri_2026_Energy-E.pdf` | re-clearing without the subsidy; exports; gas burn (+25% Iberian) |
| González-de Miguel, van Wunnik & Sumper (2024), Energies 17:3102 | `energies-17-03102.pdf` | assumes full pass-through ("CCGTs are obliged to pass through the subsidies", p. 9): the null we test |
| Robinson, Arcos-Vargas, Tennican & Núñez (2023), arXiv 2309.02608 | `Robinson_ArcosVargas_et_al_2023_arXiv_2309.02608.pdf` | first 100 days; demand response |
| Oxford Institute for Energy Studies (2023), EL 50 | `OIES_2023_EL50_Iberian_exception.pdf` | first 100 days |
| Columbia CGEP commentary (May 2023) | `CGEP_2023_Iberian_exception_commentary.pdf` | secondary statement of the formula |
| Hidalgo-Pérez, Collado, Galindo & Mateo (2024), Energy Policy | **not obtained** (EsadeEcPol refused the download; journal paywalled) | price and exports; cited from its abstract only |

## 5. Not yet checked

- OMIE or REE's published daily value of Y (the decree has MIBGAS supply PGN and the market operator
  compute Y, art. 3). No public file found in OMIE's catalogue; ESIOS 10403–10411 and 1900–1927 are the
  consumers' cost, not Y. Our Y uses MIBGAS's daily index, which averages every session for the gas day;
  the decree's PGN is the D+1 product on the day-ahead session.
- Which CHP units were eligible: identifiable from their separate bidding units (EC (42)), not yet mapped.
