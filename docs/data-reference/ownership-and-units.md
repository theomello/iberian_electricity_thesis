# Ownership, agents, consumers, cogeneration, technology

_Who controls a unit's bid, OMIE's unit lists, direct consumers, cogeneration units, technology coverage. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

### Who controls a unit's bid — 88% of the near margin, rebuilt 2026-08-17
`data/esios/esios_programming_units.parquet` — **3,872 units, 738 agents, 41
technologies, EIC at 100%**, from ESIOS archive 82. **Token-free**, unlike the
ESIOS indicator API; the web page is JS-rendered with no export, the JSON is at
`api.esios.ree.es/archives/82/download_json?locale=es`. It is a **snapshot**
with no entry/exit dates — record the fetch date with anything derived from it.

**OMIE confirmed on 2026-09-03 that no historical unit listing exists for
2021.** They supplied point-in-time listings for 2024, 2025 and 2026 on request
(the 2025 one dated 31/01/2025), but stated plainly that the information is
updated continuously and no complete historical series is kept for all dates.
So every unit→agent attribution in this repo is a **forward or backward
projection from a snapshot**, and the further from the snapshot date, the
weaker it is. That bears directly on the 2021 windfall-levy question in
[`rq-clawback-size-rdd.md`](notes/rq-clawback-size-rdd.md): its treatment varies
at parent-firm level in 2021, five years before the earliest listing, and no
source has been found that would validate the mapping for that year. Check this
before building on it, not after.

`Sujeto del Mercado` is the market agent, the entity that *decides the bid*.
Nothing in the OMIE files publishes it, and it is the grouping every
market-power measure needs: residual demand facing firm *i* requires knowing
which units are *i*'s.

**Four entities, do not conflate them.** A *plant* is physical. A *unit* (UP)
is a market registration — sometimes one plant (`ASC1`), sometimes a whole
cascade (`ADOURO`), sometimes a 6,500 MW portfolio (`EDPSVD1`). An *agent* is
who submits the offer. A *firm* is the group above the agent (`IBEG`, `IGNU`,
`IBGT` are all Iberdrola); ESIOS gives agents, not groups.

ESIOS is REE's **dispatch** registry, so it omits the commercial aggregation
vehicles that exist only to bid — 592 of our codes match. `build_unit_agents.py`
layers three sources (ESIOS exact match; ESIOS agent code appearing inside a
`cab` plant name, e.g. `GREPSC1` = "REPSB GENERICA VENTA"; then a hand-checked
prefix dictionary) to reach **89.1% of near-marginal offered volume** (rerun
2026-08-17 on Jan-2024, after hand-verifying five more prefixes against OMIE's
own published agent list — `REP`→Repsol, `GAS`/`GGA`→Naturgy, `GTG`→
TotalEnergies, `IBG`→Iberdrola; see the trap below on the one wrong guess this
caught before it went in. The prefix dictionary grew substantially during the
gas-cap and levy work too, and an earlier **45.3%** figure recorded here was
stale — left as a dated note rather than silently deleted).

**`agent_owner`, added 2026-09-03, is a second opinion that covers far more.**
`build_unit_agents.py` now also carries OMIE's *published* owner from
`omie_unit_lists.parquet`, alongside the inference chain rather than replacing
it: **4,055 of 5,137 units against 2,441**, and **99.8% of near-marginal
offered volume against 89.1%**. It resolves every prefix `PREFIX_AGENTS`
deliberately left unmapped (`CEV` Energya VM, `IGV` **and** `IGN` both Ignis
Energía, `NEX` Nexus, `VGE` Repsol, `GAL` Galp, `GES` Gesternova, `PEG` Endesa,
`CLI` Holaluz-Clidom) — so three of the hand-researched conclusions recorded
below are wrong, and the `IGN` note is wrong in its reasoning even though it
was right to reject Iberdrola.

**`agent_owner` names legal entities; `build_owner_groups.py` rolls them up.**
`data/omie/registry/owner_groups.parquet` maps **1,451 owner strings to 1,090
groups** (1,096 before the 2026-10-02 merges) on three evidence layers: the independent ESIOS chain's verdict on an
entity's own units (**81.7%** of supply volume), a stem match onto a group that
layer established (2.0%), seven hand-verified cases (0.3%), and **13.3% left
standing as their own group** because no merge evidence was found.

**Two group-level merges: `ENEL` → `ENDESA` (2026-09-29) and `EDP COMERCIAL` →
`EDP` (2026-09-30)** (`GROUP_MERGES` in `build_owner_groups.py`; Enel is 2.1%
of supply volume). Enel Green Power España is 100%
owned by Endesa Generación, which bought the remaining 60% in 2016, so for the
whole window. Layer 1 had grouped it as `ENEL` because ESIOS labels its agent
after the legal name; two of the entity's own units (`ECY*`) carry the ESIOS
agent "Endesa Cogener y Renovables", which the chain assigns to ENDESA. Standing
apart, it made Endesa's residual-demand slope count Endesa's own renewables as a
rival's. The manual layer could not do this: it only fills entities layer 1 left
open, so a merge of two layer-1 *labels* needs its own mechanism. EDP Comercial,
EDP's Portuguese liberalised retailer (100% EDP, Integrated Annual Report 2024),
is merged on the same mechanism; the midday-hydro panels already counted it in
EDP's net position and the firm panel did not. Without the roll-up
`SU ELETRICIDADE` — 7.3% of supply volume, EDP's Portuguese regulated supplier —
reads as a firm in its own right, and Repsol splits across nine entities.

**Seven more merges on 2026-10-02, all renamings** the layers had left apart
(notes/report-ownership-mapping.md): Total → TotalEnergies, Clidom → Holaluz, both
BP entities (the stems had taken "GAS" and "GAS EUROPE"), both PH Energia
entities (the stems had taken the Portuguese legal forms "LDA" and "UNIPESSOAL"),
Aldro → Eni Plenitude. Exactly ten owner strings changed group.

**Ownership by date and by share — `lib/unit_ownership.py` (2026-10-02).** Until
then the firm panels gave each unit its latest listed owner for the whole window.
That put each **co-owned nuclear reactor whole with one co-owner, not always the
largest**: Almaraz 1 (Iberdrola 52.7%, Endesa 36.0%, Naturgy 11.3%) and Trillo
(Iberdrola 49%, Naturgy 34.5%, Iberenergía 15.5%, Endesa 1%) went to Naturgy,
Vandellós II (Endesa 72%, Iberdrola 28%) to Iberdrola. Over 2018–2026 that
overstated Naturgy's average net position by about 315 MW, half its mean, and
understated Endesa's by about 268 MW. It also left sold businesses with their
buyer for the whole window: EDP Comercializadora (EDP's Spanish retail, sold to
TotalEnergies on 2020-12-01) and Viesgo (Repsol's only from 2018-11-02).

The module gives the owners in force on any date: each listing's owners from its
date to the next listing naming the unit, shares normalised to 1, spells split at
the dated sales in `ENTITY_CHANGES`, and the inference chain's owner (share 1) for
units no listing names. `attach_owners` splits a row across owners with its volume
times each share. **A dormant registration keeps a stale owner in the listings**, so
a dated unit sale (`UNIT_CHANGES`) takes effect at the first later listing whose group
differs from the seller's, not at the next listing. Castejón's represented units
`CTJON1R`/`CTJON3R` are the case: BAJA and listed under EDP España to 2022-02-08,
TotalEnergies' on 2025-01-31, offering from 2024-02-01. The next-listing rule gave
that year of Castejón to EDP, 120 MW of its mean net position (fixed 2026-10-22). `firm_x.py`, `firm_incentive_rebuild.py` and
`residual_demand_firm.py --tier owner` use it; `qa/check_unit_ownership.py` pins the
reactors' shares, the sale dates, and that January 2024 rebuilt through each of the
three differs from the static attribution by exactly the share changes.
**The stored panels and legs C and D were rebuilt on it on 2026-10-03**
(`.superpowers/sdd/2026-10-02-ownership-rerun/chain.sh`, 19 steps, all checks pass;
old against new in `notes/handoff-2026-10-05.md`). Every builder of the leg C/D panels
and instruments uses it. **Leg A and the descriptive scripts followed on
2026-10-05** (`edp_hydro_panel.py`, `hydro_within_day_probe.py`,
`hydro_schedule_routes.py`, `firm_net_position.py`, `own_demand_in_band.py`,
`firm_shares_hourly.py --tier owner`, `markdown_contract_test.py`,
`iberdrola_contract_trace.py`, `iberdrola_self_supply.py`; old against new in the
running notes). Older designs still read the static owner.
**The listed shares are confirmed by the bilateral flows**: a co-owned reactor's
bilateral output goes to each co-owner's retail arm in about its ownership share
(Almaraz 1, June 2023: 0.557 / 0.330 / 0.113 to Iberdrola / Endesa / Naturgy
against 0.527 / 0.360 / 0.113).
Iberenergía (Trillo's 15.5%) is merged into EDP (`GROUP_MERGES`): a 100% subsidiary
of Hidroeléctrica del Cantábrico (CNMC INF/DE/0178/14). Under dated ownership
Endesa's Energía XXI and Repsol's Regsiti are caught as regulated pass-through
suppliers too (Endesa: −282 MW mean), which the static owner missed.

**Regulated pass-through suppliers are excluded from every firm's net position**
(`is_pass_through` / `exposed_group` in `lib/omie_owner.py`, pinned by
`qa/check_exposed_position.py`). SU Eletricidade (in EDP) and Curenergía (in
Iberdrola) buy and sell volume whose cost is passed through to regulated
tariffs. Left in, they made EDP look like a net seller when it is a net buyer in
72–89% of periods, and they carried the first stage of the withdrawn leg B
(`notes/rq-midday-hydro.md` §3.20). `analysis/firm_x.py` is the one place X is
computed for the five large firms; `firm_incentive_rebuild.py` computes the same
correction for all firms, and the two agree exactly.

Two gates in that script are load-bearing, both learned from real failures.
Layer 1 refuses a modal ESIOS firm supported by too few of an entity's own units
(`GALP ENERGÍA`: 41 units, **one** carrying a firm, reading IGNIS). Layer 2 sets
a higher bar still, because stem propagation *amplifies* thin evidence
(`ENERGYA VM GESTIÓN` reads CENTE on 3 of 25 units; propagating that would
relabel a sibling holding 392 units and 2.3% of supply volume). `VIESGO` →
Repsol survives both, on 6 independently-agreeing units.

**It is not a drop-in replacement for `agent`, because it names a different
entity** — the commercialising entity that submits the offer, where `agent` is
the registered operator. `ABA1` is Barbo Energías Renovables in ESIOS and Wind
to Market in the listing; `ACE4` is Naturgy Ciclos Combinados and Gas Natural
Comercializadora. For market power the listing's entity is usually the one you
want. Companion columns `agent_owner_pct`, `agent_owner_snapshot` and
`agent_owner_changed` come with it; **548 units change owner across snapshots**,
so do not treat the column as static. Full detail in
[`docs/unit-agent-mapping.md`](docs/unit-agent-mapping.md).

**Measure coverage on the near-marginal band, never on total volume.** Price is
set at the margin: a 5 GW unit offering at 0 €/MWh is inframarginal almost
always and contributes nothing to the slope of residual demand, so
total-volume coverage flatters the mapping for the units that matter least.

`build_unit_agents.py` also rolls agents up to a **parent firm** using the
legal names in ESIOS archive 83 (`IBEG`, `IGNU`, `IBGT` are three agents and
one Iberdrola). **68 parent firms, 82.4% of generation volume** (rerun
2026-08-18; an earlier "17 firms, 39.1%" recorded here was stale for the same
reason as above, and 81.9% predates the twin layer below). Top eight: EDP 15.5%, Endesa 13.9%, Naturgy 9.5%, Iberdrola
9.3%, Axpo 6.8%, Acciona 5.2%, Repsol 3.5%, Wind to Market 2.4%. **EDP is now
the largest attributed firm, not Axpo** — an earlier note here naming Axpo as
largest predates the prefix-dictionary expansion.

**Layer 4, the twin layer (added 2026-08-18): a plant registered twice
inherits its own owner.** OMIE registers the pumping leg of a hydro cascade and
the *representada* version of a plant as separate units, and frequently
attributes the owner to one registration and not the other — `ALIMA` "LIMA"
resolves to EDP while `ALIMAB` "BOMBAS DO LIMA" did not. Two rules, each
requiring positive evidence that this is a second registration: the unit code
is a mapped code plus a trailing `B` (*bombagem*) or `R` (*representada*), or
the description contains a pumping/represented marker and matches a mapped
unit's name once that marker is stripped. It fills 12 units and refuses 8
ambiguous names.

**A shared description alone is deliberately NOT a rule.** The first version
allowed it and proposed `SOECC01` "BUY BID UNIT" from `TOECC01` "BUY BID UNIT",
`FENVD03` "EOLICA" from `IBGEVD1` "EÓLICA", and `DCESC01` "UNIDAD DE
COMERCIALIZACION" — boilerplate labels shared by unrelated agents. Every
accepted pairing is printed with both descriptions at build time; read them.

**Measure firm coverage by capacity, not by unit count.** On the 383
dispatchable units the two differ enormously: **62.9% of units but 96.0% of
capacity** (up from 91.3% before the twin layer). The unmapped residual is
almost entirely small cogeneration and micro-hydro.

**Only 32 parent firms own dispatchable plant at all** — 26 with a computable
pre-2021 renewable exposure, 11 above 1,000 GWh. That is the population, not a
sample, and it is a hard ceiling: any design whose treatment varies at
parent-firm level has at most a few dozen clusters. It is why the differential
renewable exposure design was withdrawn (see `a2a8c7a`), and it should be
checked *before* building any further cross-firm design, not after.

**These firm shares are not market shares.** They are the share of *generation*
volume that could be attributed; **18.1% is unattributed** at the firm level
(more once retailers/purchasers are counted). Do not substitute them for s_i
in Lerner = s/eta without saying so. Axpo remains a **representative** trading
third-party assets rather than a producer -- see `agent_type` in archive 83,
which flags 11 of 739 agents as `Representante`.

Prefixes whose owner could not be established *from the data* are left
unmapped on purpose. As of the 2026-08-17 rebuild the largest are `CEV`
(2.4% of generation volume), `IGV` (1.5%), `NEX` (1.4%), `IGN` (1.4%), `VGE`
(0.9%), `GAL` (0.9%), `GES` (0.7%), `PEG` (0.7%) — `GAS`/`GGA`/`GTG`/`IBG`
are now resolved (see above). Several of the rest were tried by hand against
OMIE's own agent list and explicitly **withdrawn** on inspection rather than
left silently unmapped:

- **`IGN` was hypothesised as Iberdrola** ("Iberdrola Generación") and
  withdrawn — its cab names ("UOF XALLAS I", "SOLAR MULA", "GALICIA VENTO")
  never mention Iberdrola, and OMIE's own agent list gives Ignis Energía's
  actual codes as `IGNIS`/`IGNS1`/`MORTE`/`CYDDP`, none of which is `IGN`.
  See `PREFIX_AGENTS` in `build_unit_agents.py`.
- **`IGV`** ("MOLINOS DEL EBRO, S.A.") is genuinely mixed ownership within
  one prefix — some units trace to Grupo Samca, one ("Renovables del
  Cierzo") to Statkraft (post-2023 acquisition of Enerfín) — so a single
  prefix→firm assignment would be wrong for part of the bucket.
- **`GAL`/`CLI` have one verified plant each, not a verified prefix**: `GAL`
  contains Extresol I/II/III (ACS/Cobra Energía per public reporting); `CLI`
  contains SEAT's Martorell cogeneration plant (Cofely España, part of
  ENGIE, per its own filings — but Cofely's actual OMIE code is `ELYM`, not
  `CLI`). Neither generalises to the rest of its prefix's units without
  checking each one, so neither is encoded.

A guess across the rest would silently corrupt every market-share and markup
figure downstream.

`det` (offer detail) was checked and carries **no** agent field — it is
price/quantity steps keyed by the same 7-digit unit id as `cab`.

Full documentation of the mapping — layers, fields, coverage, glossary and the
five ways it can mislead — is in [`docs/unit-agent-mapping.md`](docs/unit-agent-mapping.md).

### Direct market consumers — 322 buyers' own demand curves (2026-11-09)
Large consumers can buy in the day-ahead auction themselves instead of through a retailer (ESIOS 353 is their total,
~6 TWh a year). Their units are in the bid archive like any other, so **each has a stated buy curve every hour**.

`build/build_direct_consumers.py` → `data/omie/registry/direct_consumers.parquet`: **473 units** typed CONSUMIDOR
DIRECTO in any OMIE listing or "Consum. directos a mercado" in ESIOS, **338 with an offer header in `cab`**. OMIE's
listing labels each (`omie_kind`: Cliente cualificado, Compras Consumo Directo, Consumo de productores, Consumos
Auxiliares, Compras Cons. Directo Balance), and often names the end consumer when a representative bids for it
("PLASTICOS BIOSCA" bid by Gaia Global Energy). `kind`, by rule plus a hand table for the largest units (`HAND`):

| kind | units bidding | TWh 2018–2026 | what the bids are |
|---|---|---|---|
| own | 133 | 24.7 | a consumer bidding its own load |
| represented | 94 | 7.2 | a representative bidding for one named consumer |
| portfolio | 73 | 11.9 | a representative or aggregator for several consumers, or an unnamed code |
| balance | 10 | 4.2 | demand response / balance units (SRAD, from 2022) |
| auxiliary | 28 | 1.9 | generating plants' own consumption: supply side, not demand |

`sector` (keyword rule on the consumer's name, hand-set for the largest) covers 91% of own + represented volume;
refining dominates it (Repsol Petróleo, 16.7 TWh). `group` is the evidence-based owner group, else the legal entity;
`consumer_generates` flags consumers whose firm owns ≥ 50 MW of supply units (Repsol, Bon Preu).

**The 'self' groups in `owner_groups.parquet` merge unrelated small owners** by first word: five companies become
`COMPANIA` (Compañía Española de Laminación — Celsa — among them), every town council `AYUNTAMIENTO`. Harmless for
the large generators (grouped on evidence), wrong for any small-owner grouping; `firm_of` here avoids it.

`build/build_direct_consumer_panel.py` → `outputs/tables/direct_consumer_panel/`: **8.8 M unit-hours, 322 units,
2018-01-01 → 2026-05-31** (bids past the price frontier are skipped), 1.5 s a month. Per unit-hour: cleared MW, offered
MW, the offered curve at the clearing price and at ±€10 and ±€50 around it (`q_m50 … q_p50`), MW-weighted bid
price; 15-minute periods averaged to the hour. Checks: cleared ≤ demand at the price, and the curve is monotone, in
every unit-hour of the test months.

**Own generation (2026-11-09).** `own_gen_group` marks 8 consumers whose own legal entity also sells generation in
OMIE (`OWN_GEN` in `build_direct_consumers.py`; pairs matched on owner, ESIOS physical unit and name, each checked by a
second pass). The panel builder writes `own_gen/own_gen_YYYYMM.parquet`: the group's own sales per hour (PDBF, all
roles, plus net intraday sales). Net purchases = the consumer units' `total_buy_mw` minus it. GWh a year: Ence sells
700–830 (2018–22) and is a net seller throughout; Repsol Petróleo's refinery cogeneration sells 1,100–2,100, net
seller in 2018 and net buyer 600–1,000 from 2022; Sniace (to 2020) and Repsol Química (to 2019) net sellers; Guissona,
Tradebe, Rivas small. Name matches on place or fuel words ("PETRÓLEO" aggregates, San Pedro, La Plata) were rejected.

**Their stated price sensitivity collapsed in 2022** (`analysis/direct_consumer_describe.py`). Own + represented
units would give up 27–37% of their demand at the price for €50 more in 2018–2021, 4.5% in 2022 and 1–2% from 2023;
the share of units with any such sensitivity went 93–99% → 5–25%. The bids moved, not the limits: half the MW was bid
at ≤ €180.30 (the old cap) in June 2019, with a quarter at ≤ €80; in June 2023 the 10th percentile was €250. Realised
too: 16% of offered MW went uncleared in 2018, 11% in 2021, 0.1% in 2025. Hours where the old cap would bind are
excluded from the 2018–2021 figures. Repsol's refineries (half the volume) bid everything at €500 throughout.

**Repsol's refineries are already netted into its position** (checked 2026-11-09). Its direct-consumer units
(`REPEC01`, `REPRC01`, `REPQC01`, `RLNRC01`, portfolio `VGERC01/02`) carry a REPSOL ownership spell, and `firm_x.py`
counts every owned unit on both sides, so their 200–300 MW of cleared buys are in `net_mw`. They make Repsol a net
buyer from 2024 (mean −263 MW in 2024, −291 in 2025; +59 and +26 without them). An audit of the 38 scripts that
compute or use a firm position found no undocumented difference: the scripts that leave purchase units out do so on
purpose (`residual_demand_firm.py`'s supply-only q and slope, the solar instruments, the market shares), and the rest
compute n as `firm_x` does or read it. `firm_incentive_net` covers 100% of every firm's clean, non-zero-price periods.

**Interruptibility demand by industrial sector, ESIOS 836–846** (fetched 2026-11-09, `--geo 0 --start 2015-01-01`):
the consumption of the large industrial consumers in REE's interruptibility service, **every 10 minutes, mean MW**, by
sector: wood 836, steel 837, paper 838, desalination 839, metallurgy 840, chemicals 841, machinery 842, glass 844,
cement 845, other 846. **Peninsular sectors run 2015-01 → early 2020 only** (the service was wound down): yearly means
in 2015 steel 1,336 MW, metallurgy 969, chemicals 484, paper 351, cement 237, all sectors ~3,570 MW; 2019 ~2,930 MW;
2020 a quarter of that; zero from 2021. Desalination continues, mostly in the Canaries. 10059 "Sectores" is the same
data with the Canaries (928,804 rows). **847, labelled the total, is published by autonomous community** (15 regions;
Galicia, Asturias, Cataluña, País Vasco largest): its regional sum equals the sector sum exactly (ratio 1.0000 over
39,169 ten-minute points). ESIOS answers HTTP 504 to most monthly requests for it, so only 18 months are cached
(`data/esios/raw/847/`, 2015) and no parquet is written; fetching it needs shorter chunks.

**Active demand response (SRAD), ESIOS 1929–1932**: activated MW, marginal price, energy allocated, payments;
quarter-hourly, **only 15 activation days, 2023-09-04 → 2026-10-06** (121 rows). Too few for any estimate.

### Cogeneration offer units — 1,313 units, fuel known for 13% (2026-11-10)
`build/build_cogeneration_units.py` → `data/omie/registry/cogeneration_units.parquet`: every unit OMIE's listing labels
"RE Mercado Térmica no renovable" (1,041, `nonren`) or "RE Mercado Térmica Renovable" (`renew`) in any snapshot; the
label exists from 2022-02-08 only. 289 non-renewable units offer in January 2022, 7,236 MW (267 units, 6,319 MW on the
2022-02-08 label alone), median 14 MW. `build/build_cogeneration_panel.py` → `outputs/tables/cogeneration_panel/`:
569,425 unit-days 2019-01 → 2023-12 (PDBF energy, load factor, sell offers, share offered at ≤ €1); 6 minutes.
Design and results: `docs/specs/2026-11-10-cogeneration-design.md`, `notes/rq-cogeneration.md`.

- **Non-renewable thermal output fell from 3,554 MW (March 2022) to 1,386 MW (September 2022)** and was back near
  2,800 MW in February 2023; renewable thermal stayed at 560–610 MW. Gas cogeneration inside the regulated payment
  scheme was outside the gas-cap subsidy from 15 June 2022 and could opt in from 1 October (RDL 17/2022). The decree
  requires a separate offer unit for a subsidised plant: 28 new non-renewable units appear in October 2022, 15 in
  November, against 1–6 a month before.
- **OMIE's cogeneration units mostly cannot be tied to a plant.** They are representatives' numbered units ("AXPO
  VENTA R. ESPECIAL 369"). Matching to REE's physical units (ESIOS archive 81) reaches 90 units, 12.9% of
  non-renewable capacity; some descriptions do name REE's programming unit ("UOF PARA UP TTECQU"). Units new after
  the cap have code-like names, so only 7 of 104 can be linked to the unit their plant left.
- **REE's programming units for cogeneration are plants, with fuel** (324 units for 357 gas plants; 7 are OMIE codes).
  In the I90 sample, gas cogeneration's final schedule is 2,100–2,250 MW in 2021, 640 MW on 2022-09-15, 2,161 MW on
  2023-02-15; 20 new gas programming units in October 2022. For plant-level cogeneration use I90, not OMIE units.
- **Every day 2022-04-01 → 2023-03-31 is on disk** (fetched 2026-11-10/11; 365 workbooks, 2.0 GB; with the monthly
  sample, 435 files, 2.3 GB). `build/build_cogeneration_ree_panel.py` (13 minutes) keeps every programming unit's
  daily P48 and PDBF, 2021–2023. Gas cogeneration falls on the cap's first day: 1,960 MW on 14 June 2022, 1,579 on
  the 15th, 1,119 on the 19th; it returns from Monday 3 October (921 → 1,305 MW in five days). Only 26 gas units
  (159 MW) are new in October: the plants keep their REE unit through both dates. 165 of 231 gas units have at least
  10 run/stop switches in the year. These units are 0.58–0.76 of OMIE's non-renewable thermal schedule.
- **Every day of 2021 is on disk too** (fetched 2026-11-11, 365 workbooks, 1.5 GB), for placebo breaks on plants.
  Not yet built into `outputs/tables/cogeneration_ree/days/` (rerun the builder) and the placebos not yet run.
- **`.venv` broke on 2026-11-11**: Homebrew removed `python@3.14` as an unused dependency during an uninstall, and it
  no longer compiles on macOS 13. `.venv/bin/python3.14` and `home` in `.venv/pyvenv.cfg` must point at another
  CPython 3.14 (the packages in `.venv/lib/python3.14` are intact). Check `.venv/bin/python -c "import pandas"` first.
- **A stopped unit can have no row in the workbook that day**: fill missing days as zero before counting stops.
- **Most cogeneration offers at zero**: 8–21% of non-renewable units offer most of their MW above €1/MWh.
- `cab` capacity of a represented unit changes as plants join and leave: the registry's `max_power_mw` is the median
  day, `cap_max_mw` the largest (8,831 MW summed against 7,236 MW in January 2022).

### OMIE's *Listado de Unidades Ofertantes* — the authoritative registry
`data/omie/registry/omie_unit_lists.parquet`, built by
`build/build_omie_unit_lists.py` from 12 dated PDFs in `data/omie/unit_lists/`.
**51,703 rows, one per unit per snapshot.** Columns: `snapshot`, `unit`,
`descr`, `agent_owner`, `ownership_pct`, `unit_type`, `status`, `zone`,
`technology`.

Obtained by asking OMIE directly (ticket #12541), not scraped. This settles
what the rest of this file spends pages reconstructing: `agent_owner` is the
owning company **published by OMIE with an ownership percentage**, and
`technology` is OMIE's own label. Undocumented here until 2026-09-03 although
eight analysis scripts already read it.

| snapshot | units | technology | agent_owner |
|---|---|---|---|
| 2014-09-24 … 2020-03-09 (8 snapshots) | 3,656–5,102 | **0%** | 100% |
| 2022-02-08 | 5,899 | 93.0% | 100% |
| 2023-05-16 / 2023-12-30 / 2025-01-31 | 2,803 / 2,978 / 3,331 | ~99.4% | 100% |

**They are snapshots, not spells.** A unit's agent between two snapshots is
unobserved; an ownership change is locatable only to the bracketing interval.
The builder prescribes the nearest *preceding* snapshot when attributing a bid,
which is right for **ownership**. For **technology** the rule is the nearest
snapshot in *either* direction, since the first one carrying a technology at all
is 2022-02-08 — see the backward-projection argument below.
`marginal_technology.py` took the latest snapshot for every year until
2026-09-03, which pushed the 2025-01-31 relabelling back onto 2018; it now
labels each period from the nearest snapshot per unit.

**No 2021 snapshot exists and none can be obtained** — see the ESIOS section
above for OMIE's statement that no historical series is kept.

**These 12 PDFs are the only genuinely irreplaceable files in `data/`.** The
gitignore convention rests on `data/` being re-fetchable; that is false here,
because OMIE does not keep history. About 6 MB. Back them up.

### Technology coverage — superseded from 2022 by OMIE's own listings
**Read this before believing the 41.2% figure below.** Everything in this
section describes `unit_agents.parquet`, the hand-built inference chain, and it
is still accurate *about that file*. It is **no longer the repo's ceiling**:
`data/omie/registry/omie_unit_lists.parquet` (see the section above) publishes
OMIE's own technology label, and eight analysis scripts — including
`marginal_technology.py`, the very script that asks which technology sets the
price — already read it instead.

Measured 2026-09-03 on offered sell volume, nearest-preceding snapshot:

| month | cab `tech` | OMIE listing | union |
|---|---|---|---|
| 2018-06 | 81.1% | **0.0%** | 81.1% |
| 2020-01 | 77.4% | **0.0%** | 77.4% |
| 2024-01 | 78.1% | 99.5% | 99.7% |
| 2025-05 | 80.3% | 99.1% | 99.4% |

**The listings carry no technology before 2022-02-08.** All eight snapshots from
2014-09-24 to 2020-03-09 are 0% technology and 100% ownership — OMIE added the
column to the listing format later.

**That gap is closed by projecting the 2022-02-08 label backwards, and unlike
ownership the projection is defensible** — `tech_omie_early` in
`unit_agents.parquet`, added 2026-09-03. Technology changes for 2.07% of units
across the four technology-bearing snapshots against 6.19% for ownership; most
apparent instability is OMIE renaming its own categories; and the projected
class agrees with the independent `cab`-name technology on 93.3% of units, or
**98.7%** once sub-classes differing in granularity rather than kind are
collapsed. Coverage of near-marginal offered sell volume, against `cab` alone:

| year | projected from 2022-02-08 | `cab` names alone |
|---|---|---|
| 2018 | **100.0%** | 94.9% |
| 2019 | 99.9% | 92.4% |
| 2020 | 99.6% | 93.7% |
| 2021 | 94.9% | 77.9% |

**Do not project ownership the same way** — it changes three times as often, and
548 units change owner across the snapshots. The asymmetry is the whole argument;
see `attach_listing_tech` in `build_unit_agents.py` for the full statement,
including the one assumption that cannot be tested.

**The 41.2% and 63.3% figures below do reproduce**, but only on one specific
basis, which was never written down: `abs(net_cleared_mwh)` summed over the four
`SUPPLY_ROLES`, with the share being units carrying `tech` (or `regime`) —
exactly what `build_unit_agents.py` prints. Other readings of "of generation
volume" give materially different answers (positive cleared volume only:
47.7%/74.9%; `role == "generation"` alone: 22.8%/63.6%), so state the filter
when quoting them.

ESIOS is close to exhausted for this: only **128 of our 3,930 generation units**
appear in its programming-unit registry, because REE registers dispatchable
plant and the registry is dominated by retailers (933 of 6,627 physical units
are `Comercializadores mercado libre`). Archive 81 carries a `up` field linking
physical units to programming units, but it inherits the same 128.

So technology comes from `cab` names, in two tiers:

- **`tech`** — a specific technology, from an explicit marker in the name.
  1,474 units, 41.2% of generation volume.
- **`regime`** — *Régimen Especial* (renewables, cogeneration, waste) versus
  *Régimen Ordinario* (conventional thermal, hydro, nuclear), read off names
  like "AXPO VENTA R. ESPECIAL 042". 2,037 units, **63.3% of volume**
  (2026-08-17 rebuild; was 59.9%). A weaker claim than a technology, kept in
  its own column rather than folded into `tech`, but it still rules out half
  the stack for a marginal unit.

**Hydro is named after rivers, not after technology.** `ALIMA` is "LIMA",
`ACAVADO` is "CAVADO", `TEMON` is "SISTEMA TEJO-MONDEGO", `GUADIA` is "BACIA
HID. DO GUADIANA". Matching only `HIDRO`/`C.H.` left the seven largest
Portuguese cascades unclassified — together ~41% of all unidentified marginal
periods — and made hydro look like a declining marginal technology when it is
not. River and basin names are now matched explicitly.
