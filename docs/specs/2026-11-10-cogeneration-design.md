# Cogeneration as a fourth technology: a cost that contains the factory's demand

**Status: proposed 2026-11-10. Nothing here is built or estimated.** The counts in §1 come from
one-off queries in the session that produced this spec, not from committed scripts; step 0
re-derives them. Branch `industrial-demand`. It replaces the direct-consumer design
(`notes/rq-direct-consumers.md`, stopped at step 2) as the demand-side chapter.

**In one example.** A paper mill has a gas engine. Running it costs gas, but the engine's waste
heat dries the paper, so the mill fires its boiler less. With gas at €100 per MWh of heat, an
engine at 35% electrical efficiency burns €286 of gas per MWh of power; the heat it supplies
saves about €143 of boiler gas; its net cost is about €143. The mill runs the engine when the
power price is above that, and stops it and buys from the grid when it is below. On 15 June 2022
the gas cap lowered the power price. Combined cycles were paid a subsidy to make up for it; most
cogeneration was not. The mill's engine stopped. From 1 October it could claim the subsidy, and
it started again.

**Why.** The thesis measures, technology by technology, the gap between a cost known when offers
close and what the unit offers: gas and coal (fuel and carbon), storage hydro (the water value),
nuclear (the reservation price). Cogeneration (*cogeneración*: producing power and useful heat
together at an industrial site) adds a fourth, and it is the one technology whose cost contains
an industrial consumer's own demand, through the heat. That is the link between the demand side
and the supply side that the direct-consumer bids could not give: a day-ahead bid is a purchasing
decision, and 91% of its response was re-routing between channels.

**Goals.**
1. A cost for each cogeneration unit and day, on the same footing as the other three technologies.
2. How strongly output responds to the power price relative to that cost (a supply elasticity,
   and for the few sites where load is observed, the substitution between self-made and grid power).
3. How much of the gas-cap subsidy reached these units' offers, as a row beside the combined
   cycles' in `docs/specs/2026-11-08-conduct-evidence-table.md`.

**Not goals.** A welfare number for the cap. A counterfactual price path. An elasticity for
consumers with no generation (stated as out of reach, with the reason). Portugal.

**What would make it a failure even if it runs.** Attributing the June 2022 fall to the cap when
gas prices or the March 2022 change to the regulated scheme explain it; treating the opt-in group
as randomly assigned; quoting a cost for units whose regulated payment is unknown as if it were
complete.

---

## 1. What was found on 2026-11-10

**The law (three groups).** Real Decreto-ley 10/2022, article 2.1.c (consolidated text in
`papers/md/boe-rdl-10-2022-consolidado.md`): gas cogeneration with **no regulated payment** is
inside the mechanism from the start, 15 June 2022. Cogeneration inside the regulated scheme
(*régimen retributivo específico*, the payment scheme for renewables, cogeneration and waste under
Real Decreto 413/2014) is outside. Real Decreto-ley 17/2022 (20 September 2022, in force 22
September) lets those plants give up the scheme temporarily and join the mechanism, effective the
first day of the month after they notify: **1 October 2022 at the earliest**. Biomass and waste
plants burn no gas and are never eligible.

**The decree requires a separate offer unit** for a subsidised plant (several cogeneration plants
may share one only if all are eligible). So a new OMIE unit after the cap marks a plant entering
the mechanism.

**Units.** OMIE's listing labels them "RE Mercado Térmica no renovable" (non-renewable thermal in
the special regime) and "RE Mercado Térmica Renovable". In January 2022, 269 non-renewable units
offer, 6.3 GW by `cab` maximum power, median 14 MW: close to plant level, with some portfolios
(the largest 331 MW).

**Scheduled output (PDBF, mean MW):**

| | non-renewable, existing units | non-renewable, units new from June 2022 | renewable thermal | active non-renewable units |
|---|---|---|---|---|
| 2021 | 3,520–3,800 | 0 | 490–630 | 258–287 |
| 2022-03 | 3,549 | 0 | 599 | 279 |
| 2022-04 | 3,154 | 0 | 638 | 271 |
| 2022-06 | 2,662 | 5 | 613 | 260 |
| 2022-08 | 1,498 | 12 | 610 | 169 |
| 2022-09 | 1,386 | 44 | 557 | 181 |
| 2022-11 | 2,213 | 124 | 570 | 262 |
| 2023-02 | 2,775 | 277 | 570 | 292 |

New non-renewable units by month of first appearance: 1–6 a month from January to September 2022,
**28 in October, 15 in November**, 12 in January 2023.

**Fuel.** OMIE's label does not separate gas from fuel oil or refinery gas. REE's physical-unit
register (ESIOS archive 81) names 357 "Gas natural cogeneración" plants, 4.4 GW, but only 7 of
their 324 programming units are OMIE units: these plants sell through representatives' OMIE
units, as wind farms do. MITECO's producer register (`ElectraExp.csv`) has name, regime and
region only.

**The regulated payment.** Plants in the scheme receive an operating payment (*retribución a la
operación*) per MWh on top of the market price, set per standard plant type (*instalación tipo*).
The 2022 values were fixed in December 2022 (Orden TED/1232/2022, Orden TED/1295/2022), after the
fact. Which units are in the scheme, and of which type, is not in any file held here.

**The fall starts in April 2022**, before the cap. Real Decreto-ley 6/2022 (29 March 2022)
changed the scheme's adjustment for market prices; gas prices also peaked in March.

**Prior work.** No paper found on the run decision of cogeneration under the cap (two searches).
Lou, Pollitt, Robinson and Arcos-Vargas (2026) and Robinson et al. (2023) mention it in passing.

---

## 2. The cost

For unit *i* on day *t*, per MWh of electricity:

    net cost_it = k_i × c_t − R_it

- `c_t` = gas price + 0.2020 × carbon price, per MWh of heat: the same inputs, and the same
  "final at 12:00 on D−1" rule, as `implied_marginal_cost_daily.parquet`.
- `k_i` = gas burned per MWh of power, net of the boiler gas the heat replaces. In the example,
  1/0.35 − (0.45/0.35)/0.90 = 1.43. Its inverse (0.70) is the *equivalent electrical efficiency*
  Spanish regulation uses to define cogeneration, and it is directly comparable with a combined
  cycle's 0.55. It is the one unknown per unit, and it is the demand-side object: the heat credit
  exists only while the factory needs the heat.
- `R_it` = the regulated operating payment, zero for plants outside the scheme and after opting in.

The unit runs when `p_t + s_it ≥ k_i × c_t − R_it`, with `p_t` the day-ahead price and `s_it` the
gas-cap subsidy (`subsidy_eur_mwh` in the cost file) when the unit is in the mechanism, else 0.

**Why the cap identifies it.** Gas sets the power price, so `p` and `c` rise and fall together
and `k_i` cannot be read from ordinary years. The cap breaks that: from 15 June `p` falls relative
to `c` for excluded units, and from October `s` comes back for those that opt in. The D−1 wind
forecast (ESIOS 1777) moves `p` with `c` fixed and is the second source.

---

## 3. Step 0: build and count (no estimation)

1. **Sample.** Every unit ever labelled non-renewable or renewable thermal special regime in a
   listing, with `cab` maximum power. Unit-day panel 2019-01-01 → 2023-12-31 from PDBF (all role
   codes, `schedule_mw × resolution_min / 60`): energy, load factor, run = load factor above 10%.
2. **Fuel.** Match REE's gas cogeneration plants to OMIE units by name and capacity, with the
   discipline of `build_jrc_cab_match.py` (positive evidence, ambiguous pairs printed and left
   out). Report matched MW.
3. **Group.** For each unit: appears as a new single-purpose unit from 2022-06 (and when); or
   continues under its old code. Look for an OMIE or CNMC list of units in the mechanism before
   inferring it from new codes. A plant that moves from a portfolio unit to its own unit must be
   linked across the two codes by name.
4. **Offers.** From `curva_pbc_uof` (status `O`): each unit-day's offered MW and MW-weighted offer
   price. Count units that offer at a positive price (a stated reservation price) against those
   that offer at zero. This decides whether §4 E3 exists.
5. **Read** Real Decreto-ley 6/2022 and the two December 2022 orders; record what changed and
   when, and whether the operating payment by plant type can be tabulated.
6. **Sector and region** from the unit and owner names (the keyword rule in
   `build_direct_consumers.py`) and the producer register.

**Gate G0.** Fuel known for ≥ 60% of non-renewable MW. Below that, E1 runs on the label alone and
E2–E3 are not run.

---

## 4. Estimates (each needs a go-ahead)

**E1, the event, by group (descriptive, then difference-in-differences).** Daily load factor of
gas cogeneration against renewable thermal, unit and date fixed effects, in two windows chosen so
that the regulated payment is constant inside each: **2022-04-01 → 2022-07-31** around 15 June,
and **2022-07-01 → 2022-12-31** around 1 October. The comparison group removes common shocks
(August, holidays, demand); it does not remove the price fall, which is the treatment.
This is an intention-to-treat effect on all gas cogeneration: opting in is a choice, so units that
opted in are never compared with units that did not as if assigned.

**E2, the run decision (the main estimate).** Logit of run on `p_t + s_it` and `c_t`, with a
unit intercept and a unit-specific coefficient on `c_t` where the unit has enough switches, pooled
by sector otherwise; unit × half-year intercepts absorb the regulated payment. `k_i` is the ratio
of the two coefficients. Reported: the distribution of `k_i`; the elasticity of aggregate output
with respect to `(p + s)/c`; both with the wind forecast as an instrument for `p` (control
function) and without. Standard errors clustered by week and by unit.

**E3, pass-through into offers (only if step 0.4 finds reservation-price bidders).** For units
that enter the mechanism, the change in offer price at entry relative to the subsidy, as for the
combined cycles' ρ. Their offer price regressed on `c_t` before entry gives `k_i` a second way,
without the logit.

**E4, the demand link (secondary).** The run probability on the plant's own regional holidays
(`holidays_es_pt.parquet`) with price and cost held fixed: if the heat credit is real, engines
stop when the factory does. For the eight consumers matched to their own generation, net
purchases against `(p + s)/(k_i c)`: the substitution between self-made and grid power, reported
as a case description, not an estimate.

**Heterogeneity.** A causal forest on the E1 effect by size, sector, region and owner type is
allowed once E1 passes its gates, as description. It is not a route to significance.

---

## 5. Gates, fixed now

- **G1 pre-trends.** The gas-minus-renewable load-factor gap, monthly, 2019-01 → 2022-03: placebo
  breaks at every month must be below one third of the June 2022 break.
- **G2 April.** A logit fitted on data to 2022-03-31 must predict gas cogeneration's April–14 June
  output within its own out-of-sample error band of 2021. If it does not, something other than
  `p` and `c` moved (the March scheme change), and the June window is shortened to
  2022-05-15 → 2022-07-15 and reported as fragile.
- **G3 comparison group.** Renewable thermal's load factor must not move at either date by more
  than one fifth of the gas group's move.
- **G4 concentration.** The E1 and E2 results survive dropping each of the five largest units and
  each of the three largest representatives.
- **G5 identification of k.** At least 100 units with 10 or more run/stop switches in 2022. Fewer,
  and `k` is reported by sector only.
- **G6 plausibility.** The median `1/k_i` lies between 0.45 and 0.90. Outside that range the cost
  is mis-specified (the regulated payment is the first suspect) and E2 is not quoted.

**Stop rules.** G1 or G3 fails → the chapter is the description in §1 and step 0. G6 fails → E1
and E3 stand, the cost does not. Step 0.3 finds no way to tell scheme plants from the rest → E1
is run on all gas cogeneration only, and the three-group reading is dropped.

---

## 6. Known weaknesses, stated in advance

- **The regulated payment is not observed per unit.** Unit × half-year intercepts absorb its
  level, not a change inside a half-year, and in 2022 plants did not know its value when they
  decided. `k_i` for scheme plants is conditional on that.
- **Opting in is chosen** by the plants that gain most, and giving up the scheme also gives up
  its investment payment. The October event identifies the effect of the option, not of the subsidy.
- **Portfolio units hide single plants.** A 331 MW represented portfolio stopping half its output
  cannot be read as a run decision. Units above 60 MW with more than one plant are analysed apart.
- **Ownership and technology labels are snapshots** (2022-02-08, 2023-05-16); 526 of 856
  non-renewable units in the 2022 listing are marked withdrawn (`BAJA`).
- **Daily prices are a simplification.** Engines may follow shifts or weeks. Step 0 reports the
  share of run/stop changes that last under two days; if it is small, E2 moves to the week.
- **"Non-renewable" is not "gas"** until step 0.2 is done.

---

## 7. Left to the builder

File names (suggested: `build/build_cogeneration_panel.py`, `analysis/cogeneration_*.py`, running
note `notes/rq-cogeneration.md`); the name-matching thresholds; the logit implementation and the
minimum switches for a unit-specific coefficient; the exact form of the wind control function;
whether E2 is daily or weekly, by the rule in §6. Data facts found in step 0 go to `CLAUDE.md`;
results go to the running note.

---

## 8. Literature (index in `papers/README.md`, fourth pass)

- **The cost in §2** follows Fox-Penner (1990b), cited in Bonilla (2006, footnote 13): a
  cogeneration plant either sells to the grid or displaces its own purchases, and the sign of the
  response to power and gas prices is derived for each mode. Not held; get it before E2.
- **E1's estimator** can borrow Enrich, Li, Mizrahi and Reguant (2024): fit a LASSO model of each
  unit's output on calendar and weather using the pre-period only, then run the
  difference-in-differences on the prediction errors. It is offered as a robustness version of E1,
  not as the main one.
- **Why not households.** Fabra and Reguant (2027 draft, §4.3, footnote 6) report a short-run
  household elasticity close to zero in Spain in 2016–2017 and again in 2021–2023.
- **The benchmark for an industrial response to wholesale prices** is Hirth, Khanna and Ruhnau
  (2024): about −0.05 for German aggregate demand, with wind as the instrument. Not held.
- **Substitution across hours** (Patrick and Wolak 2001) and **between inputs** (Berndt and Wood
  1975; Pindyck 1979) are the frameworks for extensions, not used in E1–E4.
