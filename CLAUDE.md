# Spanish electricity market — data project

Operational instructions for this repo. Everything below is a **verified fact
about the data**. There is deliberately no research question here yet.

## Status

**Setting:** Spain / MIBEL. Candidate setting for a thesis, adopted
2026-08-07 after retiring an earlier Brazil-based question.

**Research question: none yet — intentionally.** The data came first so that
the question can be chosen against what the data can actually identify,
rather than the reverse. Do not add an RQ section here until one is chosen;
do not import framing from the previous project.

The previous Brazil project remains intact at
`~/Desktop/vre_hydro_thesis` and is not to be modified. Nothing was copied
from it. If something there turns out to be needed, port that one piece
deliberately, restated in Spanish-market terms.

## Environment

Python lives in `.venv` (Python 3.14, pandas 3.0, pyarrow 25). Always use
`.venv/bin/python`, never bare `python3`.

```bash
.venv/bin/python scripts/fetch/fetch_omie_prices.py
```

Scripts resolve the repo root from their own location — `lib/` modules use
`Path(__file__).resolve().parent.parent.parent`, since they sit two levels
below it. Never hardcode paths. See `scripts/README.md` for the layout and
`data/README.md` for what each output folder holds.

**This repo is at `~/projects/`, deliberately NOT on the Desktop.** The
Desktop is iCloud-synced, which silently evicts large data files to 182-byte
`.<name>.icloud` stubs; reads then fail with a bare "No such file or
directory" even though nothing was deleted. Keep `data/` off iCloud.

## Scripts

`scripts/` is grouped by what a script *does*, and every path below is
relative to it:

```
scripts/
  lib/       shared modules — omie_common (parsing, DST, resolution), config (tokens)
  fetch/     one script per source; each writes raw + parquet under data/
  build/     derived artefacts assembled from fetched data
  qa/        integrity checks that re-derive facts from the files
  analysis/  descriptive statistics and figures (R)
```

| Script | Source | Token | Output |
|---|---|---|---|
| `fetch/fetch_omie_prices.py` | OMIE `marginalpdbc` | no | `data/omie/prices/omie_day_ahead_prices.parquet` |
| `fetch/fetch_omie_bids.py` | OMIE `curva_pbc_uof` | no | `data/omie/bids/parquet/bids_YYYYMM.parquet` |
| `fetch/fetch_omie_intraday.py` | OMIE `curva_pibc_uof` | no | `data/omie/intraday/parquet/intraday_YYYYMM.parquet` |
| `build/build_unit_registry.py` | OMIE `pdbc`,`pdbcpt`,`pdbce` | no | `data/omie/registry/unit_registry.parquet` |
| `fetch/fetch_omie_cab.py` | OMIE `cab` | no | `data/omie/cab/parquet/cab_YYYYMM.parquet` |
| `fetch/fetch_omie_pdbf.py` | OMIE `pdbf` | no | `data/omie/pdbf/parquet/pdbf_YYYYMM.parquet` |
| `fetch/fetch_esios_units.py` | ESIOS archive 82 | **no** | `data/esios/esios_programming_units.parquet` |
| `build/build_unit_agents.py` | ESIOS + `cab` + prefixes | no | `data/omie/registry/unit_agents.parquet` |
| `fetch/fetch_ree_daily.py` | REE `apidatos` | no | `data/ree/ree_{generation,demand,balance}_daily.parquet` |
| `fetch/fetch_ree_realtime.py` | REE `demanda.ree.es` | no | `data/ree/ree_realtime_5min.parquet` |
| `fetch/fetch_ren_portugal.py` | REN `servicebus.ren.pt` | no | `data/ren/ren_{production_15min,installed_power_monthly,market_prices,consumption_supply_daily}.parquet` |
| `fetch/fetch_esios_spain.py` | ESIOS | **yes** | `data/esios/esios_{id}.parquet` |
| `fetch/fetch_entsoe_spain.py` | ENTSO-E | **yes** | `data/entsoe/entsoe_{series}_{zone}.parquet` |
| `fetch/fetch_hydro_precipitation.py` | Open-Meteo ERA5 | no | `data/weather/precipitation_basins_daily.parquet` |
| `fetch/fetch_omip_forwards.py` | OMIP | no | `data/omip/parquet/omip_forwards_{zone}_{YYYY}.parquet` |
| `fetch/fetch_hydro_reservoirs.py` | MITECO Boletín Hidrológico | no | `data/miteco/embalses_historico.parquet` |
| `fetch/fetch_jrc_ppdb_efficiency.py` | JRC-PPDB-OPEN (Zenodo) | no | `data/jrc_ppdb/jrc_spain_units.parquet` |
| `fetch/fetch_mibgas_prices.py` | MIBGAS | no | `data/mibgas/mibgas_price_index_daily.parquet` |
| `fetch/fetch_eua_carbon_price.py` | investing.com (browser-captured) | no, but not resumable | `data/investing/eua_carbon_price_daily.parquet` |
| `fetch/fetch_coal_price.py` | investing.com (browser-captured) | no, but not resumable | `data/investing/coal_price_daily.parquet` |
| `fetch/fetch_ecb_fx.py` | ECB Statistical Data Warehouse | no | `data/ecb/ecb_usd_eur_daily.parquet` |
| `build/build_jrc_cab_match.py` | JRC + `unit_agents` | no | `data/jrc_ppdb/jrc_cab_match.parquet` |
| `build/build_implied_marginal_cost.py` | MIBGAS + EUA + the match | no | `data/jrc_ppdb/implied_marginal_cost_daily.parquet` |

`lib/omie_common.py` holds shared parsing and DST/resolution logic;
`lib/config.py` loads tokens from a gitignored `.env`.

## Data inventory

Window: **2018-01-01 → 2026-05-31**, set by the bid archive's start.
Bids alone stop at **2026-05-08** (a ~3-month publication lag — see below).
All of `data/` is gitignored — it is large and fully re-fetchable.

### OMIE day-ahead prices — complete
91,247 rows, 3,073 days, zero missing. Columns: `date`, `period`,
`price_pt`, `price_es`, `utc_timestamp`, `resolution_min`.
Spain mean 73.31 €/MWh, range −15.00 to 700.00. ES and PT differ in 6.7% of
periods (market splitting).

### OMIE bid curves — complete to the publication frontier
**101/101 months, 354,247,072 rows, uniform schema.**

The bid archive ends **2026-05-08**, not 2026-05-31 like every other dataset.
This is not a fetch failure: OMIE's May 2026 zip contains only 8 days, no
daily bid files exist (the listing has none, and direct fetches 404), and the
frontier sits 91 days before the fetch date of 2026-08-07 — a **~3-month
publication lag**, as expected for commercially sensitive unit-level offers.

So the bid window is 2018-01-01 → 2026-05-08 while prices, REE and REN run to
2026-05-31. Re-running the fetcher later extends the frontier; the last ~3
months of any other series will never have matching bids.

Unit-level day-ahead offers for **both** Spanish and Portuguese units, since
MIBEL clears jointly. ~2.3–3.6 M rows/month in the hourly era, ~14 M/month
from 2025-10 when the 15-minute MTU quadrupled the period count.

Columns: `date`, `period`, `hour`, `quarter`, `resolution_min`, `country`,
`unit`, `side`, `power_mw`, `price_eur_mwh`, `status`, `offer_type`.

Both accepted and rejected offers are present — that is the point. In a
single hour (2024-01-01 h12) 63,599 MWh was offered against 24,872 MWh
cleared; the gap is the unaccepted supply.

`power_mw` unifies the two eras: hourly files publish MWh over one hour,
numerically identical to average MW. Derive energy as
`power_mw * resolution_min / 60`.

### OMIE unit registry — the key to the bid data
`data/omie/registry/unit_registry.parquet`, built by
`build/build_unit_registry.py` from `pdbc` + `pdbcpt` + `pdbce`. **5,137 units**
over the window (rebuilt with `--full` on 2026-08-12; the earlier 2-day-per-month
sample gave 5,049), columns `unit, country, role_code, role, group_tag,
first_seen, last_seen, days_observed, net_cleared_mwh`.

- **country** — ES 4,960 / PT 150 / 27 unknown. The ES and PT unit sets are
  **disjoint** (zero overlap), so membership is a clean assignment. This is
  the only reliable way to select Portuguese units.
- **role** — generation 3,719, purchase_retail 770, purchase_other 354,
  generation_large 211, storage_mixed 45, pumping 22. Decoded from cleared
  quantity sign/volume, constant within a unit. Separating **generators from
  retailers** is what any supply-curve or bidding work needs.

  **Supply is spread over FOUR roles, and `generation` alone is the wrong
  filter.** `role == "generation"` reads like "keep the generators" and in fact
  drops **all 62 combined-cycle units (29.6 GW), all 7 nuclear (7.2 GW), the 44
  hydro cascade units (14.2 GW) and every pumped-storage unit** — Ascó 1 is
  `generation_large`, not `generation`. What survives is wind and solar, which
  offer at zero, so any bidding measure built on it collapses to a mass point
  at €0 and shows no merit order. Cost a day on 2026-08-18 before it was
  caught. Use `generation`, `generation_large`, `storage_mixed`, `pumping` —
  see `SUPPLY_ROLES` in `scripts/analysis/capacity_quantile_offer.py`.
- **group_tag** — corporate tags (`IB`, `REP`, `GE`, …), 9 distinct,
  populated for only some units.

Validated against Jan-2024 bids: **99.2% of units and 95.1% of cleared volume
match**, `purchase_retail` units never appear on the sell side, and
`storage_mixed` sells a small volume — all consistent with the decoding,
which was derived without reference to those tests.

**No fuel or technology, and no nameplate capacity — in the registry.** The
role code separates generation from demand and isolates storage but will not
distinguish a CCGT from a wind farm.

**Both are now available from `cab` instead** (2026-08-11), token-free — see
the OMIE offer-header section below. `cab` publishes a descriptive plant name
whose prefix encodes technology (`C.C.` ciclo combinado, `C.N.` central
nuclear, `C.T.` térmica, `UOF HIDRO`/`C.H.` hydro, `PS`/`FV` solar, `PE` wind)
and a max-power column validated against published figures. ESIOS/ENTSO-E
tokens are **not** needed for this. The registry itself has not yet been
rebuilt on `cab`.

Now built with `--full` (every day). The earlier default was a
**2-day-per-month sample** (1st and 16th), which left ~5% of cleared volume
with unmatched units. The full parse added 88 units and better first/last-seen
dates, but **not** more `group_tag` coverage — still 9 distinct tags. The tag
is sparse at source, not sparse from sampling.

### OMIE `cab` — the offer header, and what unlocks unit attributes
`data/omie/cab/parquet/`, **113 months 2017-01 → 2026-05, 5,954,579 rows**,
fetched 2026-08-11. One record per unit per day. Token-free.

This is the header accompanying the day-ahead offers in `curva_pbc_uof`, and
it carries three things nothing else token-free publishes:

- **Descriptive plant name** — `ESCCC1` → "C.C. ESCOMBRERAS 1". Technology is
  in the prefix (see the registry note above).
- **Max power in MW** — validated: Ascó 1 reads 1028.0 (published ~1032),
  Escombreras 1 reads 408.6 (~400).
- **The minimum income condition**, as a fixed term (€/day) and a variable
  term (€/MWh). This is the complex condition behind the whole-day withdrawals,
  and the primitive Reguant (2014) uses to identify startup costs.

Fixed-width, latin-1, **dot decimal** — unlike `curva_pbc_uof`, which uses a
comma. Do not share a number parser between them. **Two layouts: 169 chars
until 2025-03-18, 94 chars from 2025-03-19** — see the trap below.

**The minimum income variable term is only available to 2025-03-18.** The
narrow layout publishes two numerics where the wide one published nine: max
power (confirmed) and one unidentified field that is neither the old fixed nor
the old variable term. Anything needing declared start-up costs runs
2017-01-01 → 2025-03-18. OMIE ticket #12541 is open; ask there.

Validated on January 2024: units declaring no minimum-income condition
withdraw for a whole day **4.1%** of the time; units declaring one, **81.1%**;
and units whose variable term exceeds the day's *highest* clearing price,
**94.2%**. The condition does what the market rule says it does.

Only three of the nine numeric fields are labelled in the parser. The other
six are carried through unnamed rather than guessed at.

#### The minimum income condition is a *declared* start-up cost

Worth stating plainly, because it is the single most unusual thing in this
dataset. `cab` publishes, **per unit per day**, a firm's own statement of what
it needs to earn to run: a fixed term in €/day and a variable term in €/MWh.

The empirical literature treats that quantity as something to be *recovered*:

- Reguant (2014) models the optimal declaration of the condition in order to
  identify start-up costs structurally.
- Jha & Leslie, *Start-up Costs and Market Power: Lessons from the Renewable
  Energy Transition* (SSRN 3603627), build a dynamic competitive benchmark that
  estimates start-up costs from production data, and show that **static markups
  overstate the rents attributable to market power** when start-up costs are
  ignored. Their headline correction depends on a primitive they must estimate.

Here it is published daily. That is a genuine data advantage and it cuts both
ways for our own results: any static Lerner index computed in this repo is
**biased upward** for the same reason Jha & Leslie identify, and this file is
what would let the correction be made with a declared rather than an estimated
number.

**It is not marginal cost, and must not be used as one.** The declaration is a
strategic choice — that is precisely why Reguant models it. What it supports is
a *bound*: a firm that says it needs `fixed + variable × q` will not accept less,
so its avoidable cost is at most that, and `price − (variable + fixed/q)` is a
lower bound on realised markup, revealed by the firm itself.

Three limits on the selection. Only units that *declare* a condition give this
(53 of them on 2024-01-15, 48 of which are combined cycle — the marginal
technology, but a narrow and non-random slice). The condition binds on **daily**
revenue, not per period. And the declaring units are precisely those with
binding start-up costs, so the sample is selected on the variable of interest.

### `cab` names identify the bidding **agent**, not the plant owner
Unit codes carry a 3-character alphabetic mnemonic (`EDP`, `IBE`, `GGN`,
`GRE`, `EGE`) that identifies the market agent. **344 distinct prefixes across
3,940 generation units; 54 prefixes cover 80% of generation volume, 100 cover
94%** — so a hand-built mnemonic→firm dictionary is bounded work.

It cannot be learned from OMIE's own labels: `group_tag` covers 121 units
(18.8% of volume), and propagating it along prefixes reaches only **22.4%**,
because the labelled set excludes the largest players.

Two cautions. Several large prefixes are **traders representing third-party
assets** — `EGV` is Axpo, 394 units and 6.7% of volume — and unit names like
"UOF REPRESENTADA DE ARRUBAL 1" say so explicitly. And the largest units are
**owner-level portfolios**, not plants: `EDPSVD1` "VENTA RE" at 6,500 MW,
`IBEVD11` "EÓLICA HABILITADA" at 5,906 MW. For market power that is arguably
the right object — the agent controlling the bid — but it is *not* plant
ownership, and the two must not be conflated.

### Who controls a unit's bid — 88% of the near margin, rebuilt 2026-08-17
`data/esios/esios_programming_units.parquet` — **3,872 units, 738 agents, 41
technologies, EIC at 100%**, from ESIOS archive 82. **Token-free**, unlike the
ESIOS indicator API; the web page is JS-rendered with no export, the JSON is at
`api.esios.ree.es/archives/82/download_json?locale=es`. It is a **snapshot**
with no entry/exit dates — record the fetch date with anything derived from it.

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

### Technology coverage is a separate, weaker mapping than ownership
Ownership reaches 89.1% of near-marginal offered volume. **Technology reaches
41.2%** — a different problem with different sources, and the binding
constraint on anything that asks *which technology sets the price*. This gap
did not close when ownership coverage did — the two are genuinely different
problems, not the same 12% of volume.

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

### OMIE `pdbf` — the operating schedule, and the contract position
`data/omie/pdbf/parquet/`, fetched 2026-08-13, token-free. Same field layout as
`pdbce`, so no new parsing was needed. One row per unit per period.

Columns: `date`, `period`, `resolution_min`, `unit`, `unit_id`, `schedule_mw`,
`role_code`, `group_tag`.

**Why it is here.** It publishes the **physical contract position** — energy
committed at a price fixed outside the auction. That is the `theta` term in
Wolak (2000) and Hortaçsu & Puller (2008): volume already sold forward earns
nothing extra when the day-ahead price rises, so a heavily contracted firm has
a weaker incentive to withhold whatever its share. Jha & Leslie spend an
appendix inferring it because Australian contracts are not public.

**`role_code == "4"` is the bilateral contract — read it directly, do not
compute PDBF minus PDBC.** Its sell and buy legs are exactly equal (0.0000 gap
in every month tested 2018–2026), which is the matching identity a bilateral
contract must satisfy and the subtraction cannot check.

| year | scheduled sell | under bilateral contract |
|---|---|---|
| 2018 | 413.6 TWh | **46.5%** |
| 2022 | 416.3 TWh | **48.5%** |
| 2024 | 346.7 TWh | **38.9%** |

**PDBF has several rows per unit-period, one per role code**, so
`(date, period, unit)` is *not* a key — joining cleared volume onto it without
aggregating first fans the auction volume across those rows. That produced a
spurious "36% → 5% collapse" in an early cut; the measured decline is 8pp.
Only role 4 carries a `group_tag`, and on those rows `unit_id` is the contract
id rather than the registration id.

**Still a proxy for theta, not theta.** It captures *physical* bilateral
contracts only and misses **financial** hedges entirely — an OMIP future or a
financially settled PPA fixes revenue while the energy still clears in the
auction. Since what matters is whether *revenue* is fixed rather than whether
electrons flow bilaterally, that omission is the more serious one. Bound it; do
not claim to measure it.

`--verify` re-derives PDBF against the auction per month and flags any month
where PDBF sell falls below cleared sell, which would be a parse failure rather
than a market fact. January 2024 gives **1.73×**, independently reproducing the
figure below.

**`schedule_mw` is average MW, not MWh** — see the trap below.

### CNMC publishes shares on PDBF, not on the day-ahead auction
**PDBF** = *Programa Diario Base de Funcionamiento*, the daily operating
schedule: the day-ahead auction result (**PDBC**, *Programa Diario Base de
Casación*) **plus bilateral physical contracts and self-scheduling**. On
January 2024 the PDBF sell total is **1.73×** day-ahead cleared volume.

Comparing CNMC's shares to day-ahead cleared shares therefore makes firms look
under-mapped when they are not. Measured on PDBF our mapping gives Iberdrola
22.2% against CNMC's 20%, Naturgy 5.2% against 6%, Acciona 4.3% against 4%.

This is economically substantive, not bookkeeping. For market power **in the
day-ahead auction** the relevant share is day-ahead exposure: volume sold
forward at a fixed price earns nothing extra when the day-ahead price rises —
the contract-position term in Wolak (2000) and Hortaçsu & Puller (2008). Using
PDBF-based shares **overstates** the day-ahead markup incentive.

OMIE publishes `pdbf` as its own dataset, same schema as `pdbce`, so a
like-for-like comparison needs no new parsing.

### The intraday session regimes overlap — they did not switch cleanly
MIBEL's own 6-7 intraday sessions and the European IDA auctions **ran in
parallel from 2025-03 to 2025-06**, and the two are distinguished only by the
width of the session digits in the filename: two digits (`01`..`07`) for the
old sessions, one (`1`..`3`) for IDA1-IDA3. Full changeover is 2025-07.

This bites twice. A regex requiring two digits returns **zero rows** for
2025-07 onward — which fails loudly — but during the overlap it silently
parses *part* of a month and reports success: 2025-06 yielded only 22 of 90
files that way, 2025-03 90 of 101, 2025-05 91 of 96. Audit member counts
against the zip rather than trusting a clean exit.

`session` is therefore **not comparable across the boundary**: 1-7 before,
1-3 after, with different meanings and an overlap period where both appear.

**Intraday also adopted the 15-minute MTU in June 2025, four months before
the day-ahead market did (2025-10-01).** The two markets run at different
resolutions in between, so read `resolution_min` per file rather than
inferring it from the date.

### OMIE intraday bid curves — complete
**101/101 months, 558,797,498 rows**, uniform schema — larger than the
day-ahead archive. Unit-level offers for each intraday **session**, where
wind and solar forecast errors get corrected after the day-ahead auction.

Same row format as the day-ahead files, so `parse_member` is shared; the
session index exists **only in the filename**
(`curva_pibc_uof_YYYYMMDD<SS>.1`) and is added as a `session` column. Rows
carry their own delivery date, which can differ from the filename date — the
row date is authoritative.

Cleared intraday sell volume is ~18% of day-ahead (Jan 2024), as expected for
an adjustment market. The frontier is 2026-05-11, three days past the
day-ahead bid frontier. A few session files are published **empty** (e.g.
session 4 on 2020-04-01) and correctly yield no rows.

Parsing is streamed one row-group per source file: the IDA-era months are
~17 M rows each and buffering a month in memory exhausts it.

### REE daily generation / demand / balance — complete
Daily only (see the hourly limitation below), 2018-01-01 → 2026-05-31, no
empty months. Generation 49,201 rows / 17 series (one being the aggregate);
demand 3,073 rows, exactly one per day, matching the price day count;
balance 70,060 rows / 25 series nested under four groups.

Validated: generation components sum to REE's published total at 0.00% gap
every year, and annual output (~260 TWh) matches published figures. Wind +
solar rose from 23.9% of generation in 2018 to 41.8% in 2024.

### REE realtime — 5-minute generation, demand and flows — complete
`demanda.ree.es`, token-free. **885,085 rows, all 3,073 days present**, zero
duplicate instants, monotonic in UTC. 33 fields: demand, generation by
technology (PV and thermal solar separately), batteries, pumped storage, and
**bilateral** flows with France, Portugal, Morocco and Andorra. Units are
**MW** (instantaneous power), not MWh.

Records per day: 288 normally, 276 on the 9 spring DST days, 300 on the 8
autumn ones — matching the transitions in the window exactly.

This is the primary sub-hourly source and is strictly better than the hourly
series originally sought.

### REN Portugal — complete
`servicebus.ren.pt/datahubapi/electricity`, token-free, documented at
https://datahub.ren.pt/pt/instrucoes-api/. Portugal is **inside** MIBEL, not
a neighbour: it clears jointly with Spain against one merged bid stack, so
the Portuguese series belong to the same market object as the Spanish ones.

| file | rows | content |
|---|---|---|
| `ren_production_15min.parquet` | 3,801,736 | 15 series, **15-min**, all 3,073 days |
| `ren_market_prices.parquet` | 147,502 | hourly ES and PT |
| `ren_consumption_supply_daily.parquet` | 77,834 | 28 balance types |
| `ren_installed_power_monthly.parquet` | 887 | capacity by technology |

Points per day 92/96/100 — the 9 spring and 8 autumn DST days match Spain's
counts exactly, which cross-validates both timezone implementations.

Validated: annual generation 44–55 TWh matches published figures; coal runs
11.2 TWh (2018) → **0.0 from 2022**, matching the closure of Pego, the last
Portuguese coal plant, in late 2021. Solar capacity 577 → 5,028 MW and solar
generation 0.8 → 6.1 TWh over the window; VRE share 23.8% → 41.6%.

`ElectricityInstalledPowerMonthly` matters disproportionately: installed
capacity has **no token-free Spanish source**, but Portugal publishes it.

The price series is also the independent check on the OMIE parse — see the
trap below.

### ESIOS / ENTSO-E — installed capacity only
Only **installed capacity** still lacks a source: REE's `potencia-instalada`
returns HTTP 500 under every parameter combination tried. Tokens are needed
for that alone; see `config.py`. Both scripts are written but never executed.

### MITECO reservoir levels — the missing water-value state variable
`data/miteco/embalses_historico.parquet`, fetched 2026-08-18, token-free.
**720,099 rows, 401 reservoirs, 16 hydrographic demarcations, weekly,
1987-10-06 → present.** Source: MITECO's Boletín Hidrológico Semanal, the
same weekly bulletin published since 1988; the only downloadable
distribution is a zipped Access database
(`BD-Embalses.zip` → one table, `T_Datos Embalses 1988-2026`), not a
CSV/API — confirmed against the `datos.gob.es` catalogue entry too. Parsed
with `access_parser` (pure-Python MDB reader) rather than `mdbtools`, to
avoid a slow from-source Homebrew build chain.

Columns: `date`, `ambito` (demarcation), `embalse` (reservoir name),
`capacity_hm3`, `stored_hm3`, `hydro_flag`. Exists to supply `Vol` in the
hydro opportunity-cost function `c(pf, Vol, Snow)` that
[`hydro-water-value-design.md`](notes/hydro-water-value-design.md) argues is
necessary for the 2021 windfall-levy question — `pf` (OMIP forwards) and
`Snow` (ERA5) were already fetched; this was the missing piece. MITECO's own
label is "provisional, unvalidated."

**`ELECTRICO_FLAG` is not a reliable hydroelectric marker — do not filter on
it without checking coverage first.** It flags 0% of Guadiana's reservoirs
despite `GDNA` ("UGH. GUADIANA") being a real storage cascade in
`unit_agents.parquet`, and under 20% in Guadalquivir, Segura and Tajo, all
baskets that plainly contain generating reservoirs. Whatever it actually
encodes at MITECO, it under-covers real hydro storage; basin-level analysis
should aggregate all reservoirs in a demarcation, not just flagged ones.

A first probe against bidding data is in
[`hydro-water-value-design.md`](notes/hydro-water-value-design.md#2026-08-18-the-actual-state-variable-was-tried-and-its-a-different-kind-of-failure--sign-not-power):
basin-aggregate fill level (seasonally de-meaned) shows a real basin-specific
relationship with hydro storage units' offers — own-basin beats a
placebo-basin rotation at t = 2.00 on the median offer — but with a
**positive** sign, opposite the simple cost-shifter prediction. Read there,
not as a green light for a reduced-form regression: the sign is consistent
with reverse causality through storage strategy (a plant conserving water
bids high and stays fuller for the same reason), which is exactly why the
opportunity-cost function needs joint, not single-equation, estimation.

### Implied CCGT marginal cost — the first real cost primitive, not a declared one
Built 2026-08-18 from three separate fetches plus a matching layer, in
response to CLAUDE.md's own cost section noting that nothing token-free here
gives an actual engineering marginal cost — `cab`'s minimum-income condition
is a *declared*, strategic number (see above), not a fuel cost. This
constructs `gas_price / efficiency + 0.2020 * co2_price / efficiency` per
unit per day — 0.2020 tCO2/MWh(th) being the EU ETS MRR Annex VI default
emission factor for natural gas, a regulatory constant, not fetched data.

**Three inputs, three different fetch problems:**

- **Efficiency** — `data/jrc_ppdb/jrc_spain_units.parquet`, from the JRC's
  open power-plant database (Zenodo, CC-BY, static, no registration).
  **1,827 Spanish generating units, 456 with a non-null efficiency** — but
  only 66 of the underlying generator rows are `OEM_derived` (from real
  equipment specs); most of the rest are `Class_derived`, a technology-class
  *average*, not a measurement — see the trap below. JRC identifies units by
  ENTSO-E EIC code, sharing no key with any OMIE dataset.
- **Gas price** — `data/mibgas/mibgas_price_index_daily.parquet`, MIBGAS's
  own "Market Results" workbook, found by fetching the page's AJAX fragment
  directly (`/es/ajax/node/1184`) since the page itself is a JS SPA with no
  visible static link. **3,152 days, 2018-01-01 → 2026-08-18, 100% coverage,**
  mean 38.75 €/MWh, range 4.17–225.03 (the August 2022 gas crisis).
- **CO2 price** — `data/investing/eua_carbon_price_daily.parquet`. Took
  eight sources to find: CBAM Guide (spot only), Sandbag's "Carbon Price
  Viewer" (a static cropped JPEG, not the interactive chart it looks like),
  ICAP, Ember (real API, wrong quantity — carbon *intensity*, not *price*),
  EEX's free widget (real EUA auction data, but capped to a rolling ~6-week
  window no matter what date range is requested), KRBN (a real proxy, but
  only from 2020-07-31), and EUTL registry data (annual, not a price
  series) were all tried and ruled out before investing.com's own
  historical-data page (ticker `CFI2Z6`, the front-month ICE ECX EUA
  future) turned up the real thing. **2,217 days, 2018-01-02 → 2026-08-18,**
  mean 55.38 €/tCO2, range 8.07–98.01. See the trap below on why this one
  fetcher is not resumable.

**The match: `data/jrc_ppdb/jrc_cab_match.parquet`, 77 units** (rebuilt
2026-08-18, up from an initial 53 — see below). JRC and OMIE share no key at
all, so this is name/capacity matching in the same spirit as
`build_unit_agents.py` — three paths, all requiring positive evidence,
nothing forced: 30 by exact code match (JRC's `name_g` sometimes *is* the
OMIE code, e.g. `ESCCC1`), 36 by capacity-within-6%-plus-name-similarity
(30 outright, 4 by a capacity tiebreak, 2 by a twin-registration-marker
tiebreak — both below), 11 by a hand-verified alias table. Ambiguous or
implausible candidates are printed and left unmapped, not guessed at —
Castejón's real CCGT unit (`CTJON3`, 418.5 MW) matched correctly; OMIE's
*other* Castejón-named codes (3.0 MW test units) correctly did not.

**Coverage, measured on capacity rather than plant count** (JRC's 344
candidates include hundreds of sub-5 MW cogeneration units that barely move
this number either way): of 39,427 MW JRC has an in-window efficiency for,
**32,589 MW now matches an OMIE unit — 82.7%** (80.3% of gas, 90.0% of
coal), up from 54.2% at the first cut. See the two traps below for what
closed most of that gap — one was a real bug, not a coverage limit.

**Of the 77 matches: 54 Fossil Gas, 23 Fossil Hard coal.** Of the gas
units, **46 carry a plant-specific efficiency** (`eff_is_generic ==
False`); the rest match correctly on capacity and name but their efficiency
is a generic technology-class default (see the `eff_is_generic` trap).

**The output: `data/jrc_ppdb/implied_marginal_cost_daily.parquet`, 170,402
unit-days, `fuel` column distinguishes gas/coal.** Gas (46 trustworthy
units): mean 94.27 €/MWh, range 16.51–466.41 — sits sensibly above OMIE's
73.31 €/MWh mean day-ahead price, consistent with CCGT usually setting the
margin. Coal (22 trustworthy units): mean 101.62 €/MWh, range 30.94–297.58
— close to gas, plausible given coal's lower thermal efficiency (0.29–0.38
vs. gas's 0.52–0.55) offset by cheaper fuel per MWh(th). Coal's price
converts USD/tonne (`fetch_coal_price.py`, Rotterdam API2, ICE ticker
`ATWMc1`) through `data/ecb/ecb_usd_eur_daily.parquet` (ECB's own daily
reference rate — divide, don't multiply, see the FX trap) and a cited
calorific value (API2's own 6,000 kcal/kg NAR spec = 6.978 MWh(th)/tonne,
S&P Global's CIF ARA methodology) onto the same EUR/MWh(th) basis as gas;
treat coal as a **looser** bound than gas on top of the "bound, not a
measurement" caveat both share (it omits O&M, water and startup
amortisation, and uses static full-load efficiency, not the part-load
figure a unit actually runs at) — API2 is the Rotterdam *import* benchmark,
and some plants may have burned domestic Spanish coal at a different price
before the mines closed.

---

## Traps

Each of these was hit and verified on real files on 2026-08-07. All of them
fail silently rather than raising.

### OMIE bids: `O` and `C` rows are NOT additive
The last field flags each row Ofertada (`O`) or Casada (`C`). These are two
parallel views of the same auction, not disjoint parts of it: `O` is the
**full submitted curve**, `C` is the **cleared portion**. On 2024-01-01 h12,
offered sell was 63,599 MWh and matched sell 24,872 MWh, with matched buy
also exactly 24,872 MWh — the market-clearing identity.

Filter to `status == 'O'` for supply/demand functions and `status == 'C'`
for cleared quantities. **Summing across both double-counts every accepted
bid.** `fetch_omie_bids.py --verify` re-checks the identity per month.

### Three OMIE datasets change on 2025-03-19 — treat it as a platform migration
Established 2026-08-13. Each was found separately; together they are hard to
read as coincidence:

- **`cab`** switches fixed-width layout, 169 chars to 94 (trap below).
- **`pdbf`** adopts the **15-minute MTU** — 24 periods a day through
  2025-03-18, 96 from 2025-03-19. This is *six months before the day-ahead
  auction* (2025-10-01) and three before intraday (June 2025).
- **The 61-day bid clearing-identity anomaly cluster** begins on this exact
  day and runs to 2025-06-09.

**Every dataset has its own resolution date.** Intraday June 2025, PDBF
2025-03-19, day-ahead 2025-10-01. Read `resolution_min` per file; never infer
one dataset's resolution from another's.

### PDBF `schedule_mw` is average MW, not MWh per period
Confirmed on Ascó 1 (1,028 MW nameplate): it reads 995.8 in the hourly era and
1,003.0 at 15 minutes. Had the field been MWh per quarter it would read ~250.
Summing the raw column across the 15-minute era therefore overstates energy
**fourfold** — April 2025 sums to 119.29 "TWh" against ~27 TWh in neighbouring
years, which is how this was caught. Derive energy exactly as for the bid
files: `schedule_mw * resolution_min / 60`.

### `cab` changed its fixed-width layout on 2025-03-19, mid-month
Found 2026-08-13, after 14 months of silently corrupt output. The file went
from **169 characters to 94**, and every field moved:

| field | wide (to 2025-03-18) | narrow (from 2025-03-19) |
|---|---|---|
| unit_id | `[0:7]` | `[0:10]`, now 8 digits |
| unit | `[10:17]` | `[15:22]` |
| descr | `[17:47]` | `[22:52]` |
| offer_type | `[47:50]`, `VNO`/`CNO` | `[52:54]`, `VO`/`CO` |
| numerics | nine | **two** |

The old parser did not fail. Its guard tested that `line[:7]` was all digits,
and in the narrow layout `[0:7]` is leading spaces plus digits, so it passed
and emitted unit codes `0AB`, `0AC`, `0AD` — plausible-looking, joining to
nothing. Every `cab`-derived attribute was therefore missing for 2025-03-19
onward, which is why marginal-technology coverage looked as if it collapsed in
2026: 100% of 2026 marginal units appeared to have no `cab` name.

**Dispatch on the observed line width, never on the date** — the change lands
mid-month, so a date rule mis-slices 18 days of March 2025. The parser now
raises on any unrecognised width.

`max_power_mw` is **confirmed** across the boundary: of the 2,390 units present
on both 2025-03-18 and 2025-03-19, 100% reproduce the same capacity. The other
narrow numeric is **not** identified and is carried as `narrow_numeric_0`.
ABO1 declares 24,000 €/day fixed and 127.50 €/MWh variable on 18 March and a
single 601,620 on 19 March; the declaration is chosen per unit per day, so a
day-over-day comparison cannot identify the field.

**This is the same date the 61-day clearing-identity anomaly cluster begins**
(2025-03-19 → 2025-06-09), which was recorded as unexplained because it
predates the April blackout by five weeks. A publication-system change on that
exact date is now the leading explanation for the March onset. It is a lead,
not a demonstration — a header-format change does not mechanically break the
market-clearing identity in the bid files.

### The 15-minute switch on 2025-10-01
OMIE moved from hourly to **15-minute market time units** on 2025-10-01 (the
EU-wide MTU change). Days have 96 periods from that date, 24 before. Any
code assuming 24 periods per day is wrong for every day after it. The price
parquet carries `resolution_min` (60 or 15) to make the break explicit.

### DST days have 23 or 25 periods
OMIE indexes periods 1..N within the *local* Madrid day, so N is 23 on the
March spring-forward day and 25 in October — and 92/100 in the 15-minute
era. `day_periods_utc()` derives the step from the actual local-day span,
which handles all six cases. Never assume a fixed step.

### `marginalpdbc` column order is PT then ES
Fields are `year;month;day;period;price_pt;price_es` — **Portugal first**.
Verified on 2024-01-01 h12, a splitting hour reading `29.8;3.9`: Spanish
units' highest matched sell bid was 3.90 and Portuguese units' 29.80.

Confirmed independently against REN, which labels its two price series
explicitly: over **67,919 hourly instants the match is 100.0000% exact** for
both. The decisive part is the 3,568 splitting instants where the two prices
genuinely differ — REN's `PT` still matches `price_pt` at 0.0000, while the
crossed comparison is off by up to 122 €/MWh. Getting this backwards would
silently swap the two countries in every price-based result.

### The two OMIE files use different decimal separators
`marginalpdbc` uses a **dot** (`77.7`). `curva_pbc_uof` uses a **comma**
decimal with a **dot** thousands separator (`1.500,00` = 1500.0). Do not
share a number parser between them. Both files are **latin-1**, not UTF-8.

### MITECO's reservoir file uses a comma decimal too — same trap, third source
`AGUA_TOTAL`/`AGUA_ACTUAL` in the historical reservoir database are strings
like `"38,00"`. `fetch_hydro_reservoirs.py`'s `parse_comma_decimal()` handles
it the same way `curva_pbc_uof` is handled; do not reuse `marginalpdbc`'s
dot-decimal parser here either.

### OMIE splits this dataset by age
Prices for 2018–2022 exist **only as yearly zips**; 2023+ are daily files.
Assuming the daily pattern throughout silently loses every pre-2023 day.
A few days also carry `.2`/`.3` revision suffixes instead of `.1`.

### REE `apidatos` hourly needs `geo_trunc`; generation is broken regardless
`demanda/evolucion` at `time_trunc=hour` returns HTTP 400 **unless** the full
geo triplet is supplied — `geo_trunc=electric_system&geo_limit=peninsular&
geo_ids=8741`. With it, hourly demand works.

Generation is a different matter: `estructura-generacion`,
`balance-electrico`, `estructura-renovables` and
`evolucion-renovable-no-renovable` all return HTTP 400 at `time_trunc=hour`
with or without geo parameters, while working at `time_trunc=day`. Use
`fetch/fetch_ree_realtime.py` instead — it is finer-grained anyway.

`potencia-instalada` returns HTTP 500 under every combination tried. That is
the one series with no token-free source.

### REE realtime is JSONP with a letter-coded DST hour
The body is wrapped as ``null({...});`` and must have the wrapper stripped
before JSON parsing. Timestamps are **local Madrid time**, and the repeated
hour on the autumn DST day is written ``2A`` (first pass, CEST) and ``2B``
(second pass, CET) — 25 distinct hour tokens, with no plain ``02``. The
spring day omits ``02`` entirely, giving 23. `strptime` raises on ``2A``, so
this fails loudly, but it must be handled; `parse_local_ts()` maps the
suffixes onto `fold`.

### REE realtime changed its contract on 2025-12-12
Until 2025-12-11 the request **requires** ``curva=NACIONAL``. From 2025-12-12
that value is rejected with ``curva NACIONAL no valida`` and the parameter
must be **omitted** instead. No single form works for both eras, so
`fetch_day()` tries the named curve then falls back to the bare request.
Missing this silently truncates the series at 2025-12-11 — a 171-day hole at
the end of the window, which is exactly what happened on the first run.

Three fields also change at that boundary: ``die``, ``gas`` and ``genAux``
disappear; ``aut``, ``gf`` and ``icb`` appear. Both eras carry 33 fields.
Coverage is therefore ~94% / ~6% split for the two sets, and **all six are
null on the wrong side of the boundary** — do not treat them as continuous
series. The three new names are carried through unrenamed; confirm their
meaning against REE documentation before using them.

### REE timestamps are local, not UTC
`apidatos` returns e.g. `2024-01-01T00:00:00.000+01:00`. Converting to UTC
before taking the date relabels 1 January as 31 December. Use the
`local_date` column for calendar-day work.

### REE generation includes `Total generation` as a *series*
`estructura-generacion` returns 17 series, one of which is the aggregate
`Total generation`. Summing all series double-counts, roughly halving any
share computed from it. Exclude it, then verify: the components sum to the
published total at 0.00% gap in every year 2018–2026, which is a good check
that a filter has not dropped something.

Values are in **MWh**, not GWh. Spain runs ~260 TWh/year of generation and
~700 GWh/day of demand; a "700,000" daily figure is MWh.

### REE `balance-electrico` nests its series
Unlike the other endpoints, balance returns four groups (Renewable,
Non-renewable, Almacenamiento, Demand) whose real series sit one level down
under `attributes.content`. Reading `attributes.values` at the top level
yields zero rows.

### Portugal runs one hour behind Spain — and REN mixes two clocks
Portugal is WET/WEST (UTC+0/+1); Spain is CET/CEST (UTC+1/+2). They share a
market but not a clock, so any PT↔ES join must go through UTC.

Worse, **REN uses different clocks for different endpoints**:

- `ElectricityProductionBreakdownDaily` → **Lisbon** local time
- `ElectricityMarketPricesDaily` → **Madrid** (MIBEL/CET), because the price
  is a market object shared with Spain rather than a Portuguese measurement

Both were established empirically, not assumed. Production: under the Lisbon
reading PT and ES solar noon coincide at 12:22 UTC on 2024-06-15, whereas a
Madrid reading puts Portugal 60 minutes *earlier* than Spain — impossible for
a country lying further west. Prices: mapping them as Lisbon reproduced
OMIE's value one hour late; under Madrid, REN and OMIE agree to **0.0000**
on both `PT` and `ES`.

That price agreement is also the independent confirmation that
`marginalpdbc` is PT-then-ES — REN labels its two series explicitly.

### REN point counts encode DST, but the labels do not
92 points on the spring day, 100 in autumn, 96 otherwise. The x-axis labels
still read `00:00`..`23:45` in every case, so the labels alone are useless
for DST; the **count** carries the information. `day_periods_utc(d, n, tz)`
derives the step from the local-day span, which handles it.

### `country` in the bid files does NOT identify a unit's country
Only ~4.7% of matched rows carry `ES` or `PT`; the rest are tagged `MI` for
the joint MIBEL market. That share tracks the ~6.7% market-splitting rate, so
the tag appears mainly **when the market splits**, not as a unit attribute.
Use `data/omie/registry/unit_registry.parquet` instead — see below.

### OMIE's file catalogue is larger than the guessable dataset names
Guessing dataset codes (`unidades`, `agentes`, `unidades_fisicas`) returns a
200-status HTML 404 page, which looks like success. The real catalogue is
AJAX-loaded and holds **59 datasets**; every directory page embeds the full
label→code map in its sidebar, reachable as::

    /es/file-access-list?parents=<path>&dir=<label>     -> page carries realdir=<code>
    /es/file-access-list?parents%5B0%5D=<code>&realdir=<code>   -> file listing

Codes worth knowing beyond the ones already fetched: `pdbc`/`pdbcpt`/`pdbce`
(cleared schedule: Spanish / Portuguese / by company), `indisp`/`indisppt`
(unit unavailability), `capacidad_inter_*` (interconnection capacity and
occupation), `trades`/`orders`/`precios_pibcic` (continuous intraday),
`cab`/`det` (offer header and detail).

### JRC's `eff` is not one kind of number — most of it is a class average, not a measurement
`JRC_OPEN_PERFORMANCE.csv` carries a `best_source` field easy to miss on a
first pass (a first cut of `fetch_jrc_ppdb_efficiency.py` didn't check it,
and looked done). For Spain's Fossil Gas units it splits: 66 generator rows
`OEM_derived` (mean eff 0.53, range 0.52–0.55 — a real CCGT), 620
`Class_derived` (mean eff 0.31, clustering at suspiciously round values
0.23/0.35/0.36 — a technology-class default JRC fills in when it has no
plant figure), plus 2 `emissions_*_derived` (plant-specific, back-calculated
from that plant's own reported emissions). `eff_is_generic` in
`jrc_cab_match.parquet` and `implied_marginal_cost_daily.parquet` flags the
`Class_derived`-only rows explicitly — filter on it, not just on `eff` being
non-null, or a small cogeneration plant's generic 0.23 efficiency will
divide the 2022 gas-price spike into an implied cost over 1,000 €/MWh.

### JRC's `eic_g` is not always a valid join key
A handful of Spanish units (La Muela's pumped-storage generators among
them) are registered twice in JRC's own source data — once under a
pumping-plant `eic_p`, once under a generation-plant `eic_p` — sharing the
same `eic_g`. A merge naive to this fans out into duplicate rows. Worse:
many renewable units carry a **blank** `eic_g`, and a join that treats `""`
as a valid key silently matches every Spanish blank-`eic_g` row against
every *other country's* blank-`eic_g` row — caught by hand when a first pass
returned German- and Polish-looking EIC codes on nominally-Spanish rows.
`fetch_jrc_ppdb_efficiency.py` drops blank keys before joining and
deduplicates on `eic_g` (preferring a row with a real `eff`) before merging.

### `build_jrc_cab_match.py`'s digit gate was silently inverted by a pandas coercion
Found 2026-08-18, after a first pass already looked complete (53 matches) and
was reported as done. `root_and_digit()` returns `None` for a name with no
trailing unit number, but assigning that into a DataFrame column via
`zip(*series.map(root_and_digit))` silently coerces every `None` to
`float('nan')` — confirmed on this data: 3,882 of 4,945 cab rows, 306 of 344
JRC rows. The gate meant to fire only when *both* sides carry a digit and
disagree was written as `c.digit is not None and j.digit is not None and
c.digit != j.digit` — but `nan is not None` is `True`, and `nan != nan` is
*also* always `True` in Python, so the gate fired on every pair where both
sides genuinely had **no** digit, rejecting them as if they disagreed.
Single-block plants with no trailing number in their name — Meirama,
Castelnou, Los Barrios — were silently absent from the matched set entirely,
not showing up even as a near-miss. Fixed with `has_digit()`, which checks
`isinstance(x, str)` instead of `is not None`, immune to the coercion either
way. This alone recovered several large plants; two further issues below
compounded with it.

### JRC glues a unit number onto the last word; cab always spaces it
`root_and_digit()` originally only split a name at whitespace, so "SOTO 4" (cab)
correctly gave digit `"4"`, but "SOTO5" (JRC, no space) fell through the
digit-less branch entirely, becoming a digit-less name that skirts the digit
gate above rather than a name with digit `5`. This isn't hypothetical
either: Soto de Ribera has both a unit 4 and unit 5 at similar capacity, and
the digit-less "SOTO5" briefly out-competed the *correct* "SOTORIBE 4" pairing
for OMIE's `SRI4R` (unit 4) once a capacity tiebreak was added, purely
because SOTO5's capacity happened to be closer. `root_and_digit()` now
splits a trailing digit off the last token whether or not it's glued on.

### Two Castilian plant names can be closer than they look, and capacity is the tiebreaker
"CASTELLÓN" (a city) and "CASTELNOU" (a specific plant) share enough
characters that `SequenceMatcher` rates them 0.78 similar — comfortably
over this matcher's 0.6 threshold — and with neither JRC nor cab name
carrying a digit to disambiguate (see the trap above), `CTN3`/`CTN4`
(Castellón 3/4) and `CTNU` (Castelnou) all passed the gate against *each
other's* JRC plant as well as their own, correctly reported as ambiguous
rather than guessed at. Capacity resolves it cleanly (Castellón 3 is 782.0
MW against `CTN3`'s 782.0 MW; Castelnou is 790.6 against `CTNU`'s 797.8) —
`build_jrc_cab_match.py`'s capacity tiebreak accepts a pairing only when it
is *mutually* the closest-capacity candidate on both sides, with a 1.5x
margin over the runner-up, precisely to resolve cases like this without
opening the door to a coincidental capacity match with an unrelated plant.

### Building a hand-verified alias table recovered 2.4 GW no gate combination would find
`P.G.RODR 5` (JRC) and `PGR5` "C.C. PUENTES 5" (cab) are the same 855.6 MW
plant, capacities matching to the decimal — but `P G RODR` and `PUENTES`
share almost no characters (JRC abbreviates the plant's full name, cab uses
one word from it), so no similarity threshold that also accepts genuine
spelling variants (`ESCATRÓN`/`ESCAT`, `SOTORIBE`/`SOTO`) can also reject
this one. Same story for `ESC IBER 6`/`ESC6` (Escombreras), `ESC CART
1-3`/`CTGN1-3` (Cartagena), and `CAMPGIB1/2`/`CAMGI10/CAMGI20` (Campo de
Gibraltar, which additionally uses different internal unit numbering
between the two sources). `MANUAL_ALIASES` in `build_jrc_cab_match.py`
encodes these 11 pairings by hand, each checked against capacity before
being added — the same discipline `PREFIX_AGENTS` in `build_unit_agents.py`
already uses for ownership. Combined with the two fixes above, matched
capacity went 54.2% → 82.7% without loosening either automatic gate.

### MIBGAS reshaped its own workbook twice — three layouts, not one
Checked year-by-year rather than assumed: 2018–2020 uses sheet `Indices`,
one row/day, price in `MIBGAS-ES Index`; 2021–2022 keeps the sheet name but
goes **long** — two rows/day, `Area` in `{ES, PT}`, price renamed to
`MIBGAS Index`; 2023 onward renames the sheet to `MIBGAS Indexes` (plural),
back to one row/day, with several new PVB/VTP columns alongside the old
price. `fetch_mibgas_prices.py` dispatches on the sheet name and column set
actually present per year, not on a hardcoded date, the same discipline
`cab`'s 2025-03-19 layout change already required.

### The EUA and coal price fetchers are the two non-resumable sources in this repo
`api.investing.com`'s historical-data endpoint (the only free source found
with full 2018–2026 daily coverage — see the data-inventory section above)
returns HTTP 403 to a plain `requests`/`curl` client even with a complete,
realistic browser header set (Origin, Referer, `sec-fetch-*`, `sec-ch-ua`,
a real Chrome UA) — this is TLS/behavioural fingerprinting, not a missing
header, and it only succeeds from an authenticated browser session.
`fetch_eua_carbon_price.py` (and `fetch_coal_price.py`, same instrument
family, ticker `ATWMc1`, id `1112838`) therefore do not fetch anything
themselves; they parse an already-captured raw CSV
(`data/investing/raw/eua_carbon_emissions_historical.csv` and
`coal_rotterdam_historical.csv` respectively) and exit with instructions
rather than a stack trace if that raw file is missing. Refreshing either
series needs a human (or a browser-automation session) to repeat the
capture — every other fetcher in this repo is a `requests`-only script that
re-runs unattended; these two are not.

### The ECB FX field name inverts the obvious reading
`ecb_usd_eur_daily.parquet`'s `usd_per_eur` column sits under a series keyed
`D.USD.EUR.SP00.A` (`CURRENCY=USD`, `CURRENCY_DENOM=EUR`) — read naively
that looks like "how many EUR per USD," the opposite of what it is. The
published number is USD needed to buy 1 EUR (1.2065 on 2018-01-02, correct
for that date), so converting a USD amount to EUR **divides** by it, not
multiplies. `build_implied_marginal_cost.py`'s coal-price conversion divides;
getting this backwards would move the coal-side marginal cost the wrong
direction by the square of the true adjustment.

## Known source-data anomaly: whole-day unit dropouts

A recurring class of gap in OMIE's publication — **not** a parsing artifact.
On an affected day, a block of units is simply absent from the file for all
24 hours, so matched buy no longer equals matched sell and the imbalance is a
near-constant MW offset across the day. Affected files are normal size and
parse cleanly.

A full scan of the archive on 2026-08-11 — re-deriving the market-clearing
identity for every one of the 89,039 day-ahead periods rather than spot-checking
— found **63 affected days (0.70% of periods), not the 2 previously recorded.**
They are two distinct phenomena:

**Whole-day dropouts** — all 24 periods affected, a block of units simply
absent. These are the originally documented cases:

| date | direction | offset | missing units |
|---|---|---|---|
| 2018-06-14 | buy > sell | ~2,900 MWh/h | 13 sell units, incl. the `MIEU` interconnection pseudo-unit |
| 2022-10-12 | sell > buy | ~3,098 MWh/h | 16 buy + 24 sell units |

**A 2025 cluster** — 61 days from **2025-03-19 to 2025-06-09**, *partial*-day
(1–23 periods, not all 24). Sporadic through late March and April, then every
single day of May at 10–23 periods each, decaying through early June. The
ramp-up follows the **28 April 2025 Iberian blackout** and the weeks of
reinforced grid operation after it, but the onset predates the blackout by five
weeks. Do not assume one cause.

The March start is no longer wholly unexplained: **`cab` changed its
fixed-width layout on exactly 2025-03-19** (see the trap below), so OMIE
altered something in its publication chain that day. That does not
mechanically explain a clearing-identity gap in a different dataset, but a
coincidence of exact dates across two files is worth pursuing before
attributing the cluster to the blackout.

The direction varies with which side loses more. Left as-is rather than
patched — imputing bids would be inventing data.

**Detect these from the clearing identity, never from a hardcoded date list.**
That is how the 61 new days surfaced; a date list would have silently passed
them. Note the practical consequence: they are **not randomly distributed**,
so dropping them thins 2025 in a correlated way — any 2025 result computed on
the surviving periods carries that selection.

**Always run `fetch_omie_bids.py --verify`**, which re-checks the
market-clearing identity per month and prints the maximum gap; a non-zero
value flags exactly this. Filter these days out of any design that relies on
market-wide aggregates. Analyses of individual units' bidding are unaffected
except for the units actually missing.

## Auditing

`audit_data.py` re-derives coverage, duplicates, schema uniformity and value
ranges **from the files themselves** rather than trusting fetch logs. Run it
after any re-fetch:

```bash
.venv/bin/python scripts/qa/audit_data.py
```

It exits non-zero on any problem. As of 2026-08-11 it reports **no problems**,
with four documented notes (see below). Two things it exists to catch, both of
which actually happened here: a fetcher exiting 0 after parsing a fraction of
a month, and a timestamp column silently full of NaT.

### Known, verified exceptions

- **Intraday: 2021-07-30, 2025-04-29, 2026-02-28 are absent at source.** The
  monthly zips contain *zero* members named for those dates. Listed explicitly
  in `KNOWN_ABSENT` so a genuinely new gap still fails the audit.
- **One row dated 2017-12-31** sits in the January 2018 intraday zip: session
  files carry their own delivery date, which can precede the filename date.
- **20 registry units have no country and 13 no role** — they appear in
  `pdbce` but not in the sampled `pdbc`/`pdbcpt` days. A `--full` registry
  build resolves them.

## Conventions

- Raw downloads are never modified; re-fetch instead.
- Derived outputs go to `outputs/`; raw and parsed data to `data/`.
- Fetchers are resumable — they skip what is already on disk.
  **Exception: `fetch_eua_carbon_price.py` and `fetch_coal_price.py`** —
  see the trap above.
- Commit messages: imperative, present tense, ≤72-char subject.
- Never commit `.env` or anything under `data/`.
