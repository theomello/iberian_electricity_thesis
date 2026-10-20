# Regional holidays: a within-firm test of the buyer's markdown

**Status: step 2 run 2026-10-20: STOP (`notes/rq-regional-holidays.md`).** The holiday dose does not move a firm's exposed position (F 0.1–1.4): generation sold to its own retailer falls with its customers' load. Step 1 passed. The
dose is built with one change to §3.2: days when four or more mainland regions are off get
their own term (`ES`), scaled by the share of mainland demand off, instead of H = 1 in every
region; regions that are only ever off together are merged. No β yet. The
first of four designs chosen on 2026-10-20 for sharper identification. The others, in order:
near-misses of the minimum-income condition, the France link as a switch in the slope of
residual demand, and exits from feed-in tariffs. Framework:
[`2026-09-29-thesis-framework-design.md`](2026-09-29-thesis-framework-design.md). It reuses
the fixed-step read and its simulated price-takers ([`2026-10-19-fixed-step-design.md`](2026-10-19-fixed-step-design.md),
`notes/rq-fixed-step.md`).

**In one example.** On 11 September Catalonia has its holiday (the Diada) and the rest of
Spain works. Catalan demand falls. Endesa supplies most Catalan customers, because Catalonia
is its old distribution area, so that day Endesa's retailer buys less. On 11 September 2024
its retail schedule (auction plus bilateral contracts) fell by 457 MW (−6%) against the
Wednesdays either side. (Its auction purchases alone fell 674 MW; corrected 2026-10-20.) No
plant, fuel price or weather changed. Endesa is a net buyer in almost every hour, so it gains
from a lower price. If it shades its offers down to lower the price it pays (a markdown), it
has less reason to on the Diada, because it buys less. Its offers should rise that day, and
not on Galicia's or Madrid's holidays, where it has few customers.

---

## 1. Why this design

Every instrument so far either hits all firms at once (forecasts, fuel), which the hour
effects absorb, or is thin and partly chosen (reactor outages: F ≈ 10 at the unit level;
undeclared cuts follow prices). The buyer-side markdown (leg D: β⁻ 0.19, β⁺ ≈ 0) is the most
distinctive result, but it rests on differences between firms: Endesa is a buyer in 99.8% of
its hours, Repsol mostly a seller (`notes/rq-leg-d-sign-of-n.md`; `notes/rq-fixed-step.md`
step 1). Reactor outages were to test it within firm and were too weak (F 5).

A holiday that applies in one region only:
- **is fixed by law a year or more ahead** (each region's calendar, published in the BOE every
  October), so no firm chooses it;
- **is known when offers are submitted**, so it moves the day-ahead stake, not a surprise;
- **moves the retail side only**: plants, fuel and weather are untouched;
- **differs across firms within the hour**, by where each firm's customers are, so the hour
  effects that make the design valid stay in;
- **recurs**: each region has two to four holidays of its own a year, and Spain and Portugal
  have different national holidays.

The prediction comes from vertical integration (Bushnell, Mansur & Saravia 2008, AER): a
firm's own retail load offsets its gain from a higher price. Less load, less offset.

## 2. What the data show (one event, 2026-10-20, throwaway query)

Cleared purchases in the auction (`curva_pbc_uof`, status C, buy side), mean MW over the day,
11 September 2024 (Diada) against the mean of 4 and 18 September (Wednesdays):

| purchases | 4 Sep | 11 Sep | change |
|---|---|---|---|
| Endesa, retail units | 5,168 | 4,941 | −674 MW (−12%) |
| Iberdrola, retail units | 1,964 | 2,226 | +287 MW (+15%) |
| EDP / Acciona, retail units | 932 / 1,423 | 933 / 1,392 | 0 / 0 |
| all retail units | 16,618 | 16,877 | −251 MW |

Three things this shows, each a design rule below:
- **The dose is visible**: one holiday moves Endesa by about 670 MW, the size of a reactor
  outage dose.
- **Auction purchases are not retail load.** Iberdrola's rose, because it moves volume between
  bilateral contracts with its own retailer and the auction (`rq-fixed-step.md`, "Iberdrola's
  contracts"). The dose must be measured on the retail units' whole schedule: auction plus
  bilateral (PDBF, role 4).
- **The buy side has ladders, not one price.** Retail buy offers (status O, MW-weighted price
  quantiles, these three days): Endesa −100 at p25 and 280 at p50; Naturgy −1 and 400;
  Iberdrola −500 up to p50, 500 at p75; EDP 197 to 305. Part of each retailer's demand is bid at
  prices that can bind. So a markdown can show in the buy offers directly, not only in the
  supply offers.
- **Pumping is on the buy side too** (registry role `pumping`, `storage_mixed`): it rose on the
  Diada (cheaper hours). Keep it out of the dose.

## 3. The design

### 3.1 The shock

A table of holidays, 2018–2026, one row per date and area (`data/holidays/holidays_es_pt.parquet`,
hand-built, a source on every row):
- **Spanish regional holidays**, from the Dirección General de Trabajo's annual resolution in
  the BOE (*relación de fiestas laborales*), every region plus Ceuta and Melilla, including the
  days regions choose differently each year: Holy Thursday or Easter Monday, San José or
  Santiago, and the Monday after a national holiday that falls on a Sunday.
- **Spanish national holidays** (common to every region).
- **Portuguese national holidays** (Código do Trabalho, art. 234), which differ from Spain's:
  25 April, 10 June, 5 October, 1 December, Corpus Christi; and Spanish days Portugal works:
  6 January, 12 October, 6 December, Holy Thursday.
- **Bridge days** (*puentes*) flagged, not counted as holidays.

Municipal holidays are left out (two per municipality, too many and too small).

Main sample: **weekday holidays only** (Monday–Friday). A Saturday or Sunday holiday changes
little.

### 3.2 The dose

For firm f on day d in hour h:

```
dose_fdh = Σ_r  H_rd · e_fr · p_h
```

- **H_rd** = 1 if area r (a Spanish region, or Portugal) has a holiday on d that the rest of
  MIBEL does not share. A national Spanish holiday that Portugal works is H = 1 for every
  Spanish region at once; a Portuguese one for Portugal.
- **e_fr, the firm's exposure** = how many MW the firm's retail schedule falls on a holiday in
  r. **Estimated, leave-one-year-out**: from holidays in r in the other years, the firm's
  retail schedule (auction plus bilateral, its exposed retail units only) on the holiday
  against the same weekday one week before and after. Leaving the year out keeps the dose from
  containing the day's own purchases, which a markdown could move.
- **p_h**, the hourly profile of a holiday's demand drop, from national demand
  (`ree_realtime_5min`) on national holidays against the same weekday ±1 week. My call: one
  profile for all regions.
- **Check on e_fr**: it should follow the old distribution areas (from memory, to check against
  the distributors' own maps: Endesa: Catalonia,
  Andalusia, Aragon, Badajoz; Iberdrola: Valencia, Basque Country, Murcia, Navarra, La Rioja,
  much of Madrid and the two Castiles; Naturgy: Galicia, parts of Madrid and the Castiles;
  EDP until 2020-11, then TotalEnergies: Asturias; Repsol from 2018-11 (ex-Viesgo): Cantabria;
  EDP: Portugal). And region sizes should match REE's monthly demand by region (REData
  `demanda/evolucion`, `time_trunc=month`, `geo_limit=ccaa`: works; daily and hourly by region
  do not, checked 2026-10-20).

**Regulated pass-through suppliers carry no dose.** Energía XXI (Endesa), Curenergía
(Iberdrola), Comercializadora Regulada (Naturgy), Régsiti (Repsol), SU Eletricidade (EDP)
pass their cost on to regulated tariffs (`is_pass_through` in `lib/omie_owner.py`). A holiday
that lowers their purchases does not change the parent's stake. Only free-market retail counts.

### 3.3 The first stage

The firm's net position n (as in the fixed-step and at-cost designs: at the cost point, from
`hcompcost`, `kb_sn`) and its stake X = n / |RD′|, on dose_fdh and dose_fdh / |RD′|, with
firm × month and date × hour effects. Expected: n rises by about the dose (a net buyer buys
less).

### 3.4 The outcomes

1. **Supply offers, the main outcome.** Each unit's offer at a fixed point of its own ladder,
   minus its cost, unit × month and date × hour effects, X instrumented by the dose. Storage
   hydro: the fixed-step read at cf_s minus λ*30s, 2019-01 → 2025-09, as in
   `fixed_step_test.py`. Thermal (gas and coal): the offer price at 25% and 50% of the unit's
   offered volume minus `marginal_cost_bid_eur_mwh` (capped column in the gas-cap window), as
   in `outage_offer_test.py`, over the months with at-cost caches (`compcost`). A unit's firm is
   its largest owner that day (`majority_group`). Read against
   the simulated price-takers' offers on the same rows and the same instrument, by the rule in
   `notes/rq-price-taking-simulation.md` (differs when the 95% interval misses the seeds'
   range). The price-takers' offers already exist for hydro (ten seeds); for thermal, check
   which seeds exist before running anything new.
2. **Retail buy offers, secondary.** The retailer's buy ladder read at fixed shares of its
   expected retail load. A buyer with market power bids below what the energy is worth to it;
   on a holiday it buys less, so it shades less. There is no simulated price-taking buyer yet,
   so this outcome is read within firm only (holiday against non-holiday) until a benchmark is
   decided.

### 3.5 What is estimated, and the test

- **The main estimate: Endesa's β⁻ within firm.** Endesa is a net buyer in 99.8% of its main
  hours, so the dose moves it along the buyer side only. Prediction: its supply offers rise by
  β⁻ · Δ dose / |RD′|. Leg D's β⁻ is 0.19; Nash is 1.
- **Then every firm, by sign of n**: β⁺ and β⁻ from the same instrument, firm by firm where the
  first stage allows (EDP on Portuguese holidays; Naturgy on Galicia's; Iberdrola on
  Valencia's and the Basque Country's).
- **The test is between models, not only an interval on β** (Duarte, Magnolfi, Sølvsten &
  Sullivan 2024, *Quantitative Economics*): price-taking predicts no response beyond the
  band; Nash predicts the full Δ X. A Rivers–Vuong test with the dose as instrument says which
  fits better, with their diagnostic for whether the instrument is strong enough to tell them
  apart. Report it beside the Anderson–Rubin sets the repo already uses.

**What one event is worth.** At |RD′| ≈ 500 MW per €/MWh, a 670 MW dose moves Endesa's stake
by about 1.3 €/MWh. Nash then predicts +1.3 €/MWh on its offers, β⁻ = 0.19 predicts +0.25.
With roughly eight weekday holidays a year in Endesa's areas (about 60 over 2018–2025, my
rough count) plus four Spanish-only national days a year, the design should separate 0 from
Nash; whether it separates 0 from 0.19 is the power check (§4, step 2).

## 4. Steps, each with a stop rule (each run needs a yes first)

1. **Holiday table and exposures.** Build §3.1, then e_fr. Describe: each firm's retail
   schedule on its regions' holidays, by year. *Stop* if no firm's exposure is distinguishable
   from zero in at least three regions.
2. **First stage and power.** §3.3. *Stop* if the firm-level F on the dose is below 20, or if
   the minimum detectable β⁻ at 80% power exceeds 1 (it cannot tell price-taking from Nash).
3. **Main estimate.** §3.4 outcome 1, Endesa first, then by firm and sign; Rivers–Vuong test.
4. **Checks** (§5).
5. **Buy offers** (§3.4 outcome 2), if 3 finds anything.

## 5. Threats and checks

- **Island holidays are a placebo.** The Balearic and Canary Islands, Ceuta and Melilla are
  separate electrical systems; their retail load is not bought in MIBEL. Their holidays should
  move nothing.
- **Other regions' holidays are a placebo for each firm**: Endesa on Galicia's, Naturgy on
  Catalonia's.
- **Where the unit sits must not matter.** The stake is firm-wide. A firm's units outside the
  holiday region should respond as much as those inside. A response only inside it would be
  local (grid flows, technical constraints), not market power.
- **Days around the holiday**: the day before and after, and bridge days, should show no
  response beyond their own (smaller) dose.
- **Retail books change**: customers switch, and EDP's Spanish retail went to TotalEnergies on
  2020-12-01 (`lib/unit_ownership.py`). Exposures are by year; leave-one-year-out uses the
  neighbouring years.
- **COVID-19, March–June 2020**: run with and without.
- **The 15-minute day-ahead from 2025-10-01**: the step caches end 2025-09, so the sample does
  too.
- **The market-wide drop** on a holiday moves every firm's ladder read (the merit order). The
  date × hour effects take its level; the simulated price-takers take what it does to the read.

## 6. Data

| what | source | status |
|---|---|---|
| Spanish holidays 2018–2026 | BOE, *Resolución de la Dirección General de Trabajo … fiestas laborales para el año X*, published each October | to build, by hand from nine resolutions |
| Portuguese holidays | Código do Trabalho, art. 234 | to build |
| Regional demand, monthly | REE REData `demanda/evolucion`, `geo_limit=ccaa` | checked: monthly works |
| National demand, 5-minute | `ree_realtime_5min.parquet` | on disk |
| Retail schedules | PDBF (auction plus role 4), `unit_registry` roles, `lib/unit_ownership.py` | on disk |
| Offers, ladders, costs, n, \|RD′\| | bids, step caches (`hcompcost`, `compcost`), `hydro_cost_daily`, `implied_marginal_cost_daily` | on disk |
| Retail shares by region | CNMC retail supervision reports | optional cross-check; not needed, since e_fr is estimated |

## 7. Goals and limits

- **Goal**: β⁻ within one firm (Endesa), from a shock no firm chooses; then β⁺ and β⁻ by firm.
- **Not a goal**: demand elasticity. Holidays shift demand; they do not trace it. Retailers'
  buy ladders show their bid elasticity directly if that is wanted later.
- **Limit**: the dose is a few hundred MW per event. The design may bound β⁻ well below Nash
  without separating it from zero.
- **Limit**: financial hedges are still unobserved. A holiday changes physical retail load,
  not hedges, so the dose is clean, but the level of X is still measured with error.

## 8. Left to the builder

- How to treat holidays that fall next to a weekend (my call: keep them, flag them).
- The window for "the same weekday" in e_fr (my call: ±1 week; ±2 if a neighbour is itself a
  holiday or bridge day).
- Clustering: by date (the event), as the main; by week as a check.
