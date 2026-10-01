# The next phase: one estimator on the offer steps

**Status: proposed 2026-10-01, from the discussion that closed legs C and D.
Nothing here is built.** It extends the framework
([`2026-09-29-thesis-framework-design.md`](2026-09-29-thesis-framework-design.md),
§8 step 5b) and the water-value spec
([`2026-09-29-water-value-design.md`](2026-09-29-water-value-design.md), §6).
Statements marked *to verify* were made from memory or secondary sources and
must be checked before anything rests on them.

**In one paragraph.** The four legs share one condition, p − c = β · X, but not
one method, and leg C showed why that matters: in levels β ≈ 3, mostly because
the price sits inside the gaps of stepped offers. The proposal is one estimator,
the conditions of a step bidder estimated on each firm's offer steps, with the
cost term supplied leg by leg (observed for thermal plant, differenced out or
modelled for hydro), identified by day-ahead forecasts of wind, solar and demand
(exogenous to the firms) split by whose fleet they hit, and sharpened by two
natural experiments with predictions fixed by law: the hydro water levy and the
gas cap. Its first deliverable is one β per technology on one scale, so that
"one β everywhere" becomes a test.

---

## 1. Where the legs stand

| leg | cost term | result | where |
|---|---|---|---|
| A, hydro within the day | differenced out (unit-day effects) | EDP's three reshaping cascades: market-power sign from 2024, implied β 0.03–0.14; four cascades offer one flat curve all day; Iberdrola's allocation fits price-taking | `rq-midday-hydro.md` §3.11–3.15, §3.20; framework §4 |
| B, hydro across days | modelled (Euler equation) | withdrawn: no first stage for EDP's day-level exposed X (F 0.4–1.9) | `rq-midday-hydro.md` §3.18–3.20 |
| C, thermal in levels | observed (JRC efficiency) | β 3.10 (AR [2.59, 3.67], F 70), 3.06 heat rate estimated, 3.05 declared cost; not read as conduct (§2 below) | `rq-leg-c-thermal-cost.md` |
| D, sign of n | common, prediction reversed | price-taking rejected in every pooled specification (AR p ≤ 1.1·10⁻⁶); a Nash-signed common slope fits only with yesterday's sign uncontrolled | `rq-leg-d-sign-of-n.md` |

## 2. Why one estimator, and why on the steps

**Leg C's finding.** Thermal units offer a few steps. At a partly dispatched
unit the price sits on the unit's own step in 1.4% of rows; the median distance
above its highest accepted step is 13.41 €/MWh. β splits exactly into 2.25 from
that distance and 0.85 from the unit's own markup at its top step. One GW of
rivals' solar lowers p by 2.09 €/MWh and X by only 0.64, so the regression reads
β ≈ 3. Where the unit's own step sets p, solar alone gives β 0.89
([0.55, 1.52]), but those rows are selected on p and sit about 8 €/MWh above the
condition in levels.

**Why that is not yet an exclusion failure.** A step bidder chooses each step's
length as well as its price, and the length condition makes the smooth
condition hold in expectation over the periods in which p falls in the gap
above the step (Kastl 2011). Three things break it: surprises (the part of an
instrument the firm could not foresee), step lengths fixed by the plant, and
rows where the unit is in a gap but the firm is not. In July 2019 another unit
of the same firm offers within ±0.5 €/MWh of p in 42.1% of panel rows (final
review's scratch script, not committed). §3 fixes all three.

**Why it unifies the legs.** A and D already test offers; C tested the price.
Writing every leg as conditions on offer steps puts them on one scale, which the
current numbers are not: A's β comes through offer density, C's from levels.

## 3. The estimator

For firm f, period t, the firm's **combined** offer curve (all its units'
steps, sorted by price) faces residual demand net of all its offers.

**Price of step k**, over the periods in which k sets the price:

```
E[ 1{k sets p} · ( (b_k − c_k) · |RD′| − β · n ) | I_bid ] = 0
⇒  b_k − c_k = β · E[n | k] / E[|RD′| | k]
```

a slope-weighted mean of X, not E[X | k], which the convexity of 1/|RD′|
inflates (the mean of 1,000/|RD′| is 5.12 against 1,000/median 2.13 in leg C's
sample).

**Length of step k**, over the periods in which p falls in the gap above it:

```
E[ (p − c − β · X) · 1{p in the gap above k} | I_bid ] = 0
```

**The three fixes, built in.**

1. **Surprises: condition on what the firm knew at the noon deadline (I_bid).**
   Instruments are measurable at bidding time: day-ahead forecasts (§5). The
   expectations are built by resampling residual demand (Wolak 2007; Reguant
   2014) conditional on those forecasts, so the surprise is integrated out.
2. **Fixed step lengths: inequalities at technical bounds.** A cheap first block
   whose length repeats day after day is minimum load (leg C's `min_load` flag
   finds them); a last step ending at `cab` max power is the capacity bound.
   Price moments hold for every step that can set the price; length moments
   only at freely chosen boundaries; at a bound the condition is an inequality
   (Pakes, Porter, Ho and Ishii 2015), giving a set for β. Steps that never set
   the price (withholding blocks) give inequalities only. Start-up costs and the
   minimum-income condition enter as in Reguant (2014), from `cab`.
3. **Unit vs firm: the condition is on the firm's combined curve.** The cost of
   step k is the firm's own marginal cost at that quantity, which for mixed
   portfolios includes hydro's water value (§6). Staged: firm-periods whose
   steps near p are all thermal first, hydro once λ exists.

**What it nests.**
- **Leg A**: the same estimator with a unit-day effect in place of c.
  Exception: units that submit one curve per day (EDP's flat cascades) need a
  day-level condition summed over hours.
- **Leg D**: the same estimator split by the sign of E[n | k] (a step's
  price-setting periods can mix signs).
- **The ex-post optimal bid** (`rq-gas-cap-conduct.md`, 2026-08-18; Hortaçsu and
  Puller 2008) is its one-draw case.
- **The counterfactual** (framework §7): re-clear with each firm's offers at
  β = 0.

**Cost of the build.** Resampling and re-clearing per firm-period, 2018–2023,
about 12 thermal-owning firms, 50–100 draws: large in total, cheap per draw;
start on a sample of days.

## 4. One β across legs

X is firm-level: in a given hour every unit of a firm faces the same n and
|RD′|, so the condition says each unit's marginal step carries the same β · X
over its own cost.

- **Test:** estimate β by technology on one scale and test equality, within
  firm-hour where a firm owns both (Endesa, Iberdrola, Naturgy own hydro and
  thermal), where X is identical and its measurement error common.
- **Reading:** equal βs support the model; β_thermal ≠ β_hydro means firms
  exercise power through particular plants (how, not only whether); βs that
  differ by the sign of n answer leg D on the same scale.
- **Coverage:** storage hydro (cost from unit-day effects or λ, §6), pumped
  storage on both legs (pumping bids are purchases, so the condition applies
  with the sign reversed), combined cycle and coal (cost observed). Hydro sets
  the price in 51% of resolved periods in 2019 and 76% in 2026; combined cycle in
  35% and 2.3% (chapter §4.4).
- **Nuclear and renewables carry no information about β here.** Wind and
  solar offer at about zero and set the price only where rivals' supply is very
  flat, so X ≈ 0 and any β fits a step at zero; their roles are in n, as
  instruments (§5) and in the re-clearing. Nuclear almost never sets the price;
  its margin is on/off (refuelling, and stops at low prices since 2024, *to
  verify*), an extensive-margin decision the step conditions do not cover. Its
  cost is mostly per-MWh levies set by law, so a stopping test is a possible
  separate design; parked.

## 5. Identifying variation

### 5.1 Day-ahead forecasts (the main instrument)

The system operators' day-ahead forecasts of wind, solar and demand are known
before the noon deadline and are not the firms' choices.

- **Fixes:** offered volume is partly a choice (framework §8 step 6) and
  realised output carries surprises; forecasts are neither.
- **Does not fix exclusion:** a windy forecast changes which plants run, hence
  start-ups and minimum-load costs; the fringe placebo stays and the start-up
  terms of §3 take the cost side.
- **Split by whose fleet it hits.** A forecast for the firm's own wind and solar
  moves n (the shifter of the sign of n that leg D lacks, and the day-level
  shifter leg B lacks); a forecast for rivals' fleets moves |RD′| and p. The
  model requires the same β from both: an overidentification test with two
  exogenous instruments.
- **Firm-level variation, coarse to fine:**
  1. **Spain and Portugal separately**: ENTSO-E's day-ahead wind and solar
     forecasts per bidding zone; the Portuguese forecast falls mostly on EDP's
     fleet and on Endesa's and Iberdrola's Portuguese assets.
  2. **National forecast × each firm's predetermined share of installed
     capacity**: variation from differences in fleet shares; cheap, coarse.
  3. **Site-level weather forecasts × each farm's capacity and owner**: the
     spatial instrument (framework §8 step 6), built from forecasts. Open-Meteo's
     archive of past forecasts likely covers only recent years (*to verify*);
     for 2018–2023, ECMWF's TIGGE ensemble archive is free for research after
     registration (*to verify*). Needs farm locations matched to OMIE units:
     RAIPEE (MITECO's register of generating installations), OpenStreetMap,
     Global Energy Monitor.
- **Demand forecast**: REE's day-ahead forecast is on disk
  (`ree_demand_forecast_5min.parquet`); it shifts the level of residual demand.

### 5.2 Planned outages of a firm's other units

A planned outage of one of the firm's plants lowers its sales, so n and X move,
while its other plants' costs do not; it hits the firm's hydro and thermal units
in the same hours, which is the within-firm-hour comparison §4 needs.

- **Exogeneity from timing:** `indisp` records when each outage was declared;
  outages declared weeks ahead were fixed before the day's demand, weather and
  prices were known. Season of maintenance is chosen: week or month effects.
- **Short-notice outages are excluded** (strategic withholding hides there).
- **Coverage:** large conventional units, 80.9% of the plant-specific thermal
  units; planned outages survive `indisp`'s post-2023 gaps because each
  snapshot carries the forward register.

### 5.3 Plant sales (a showcase, not the main identification)

The same plant moves to an owner with a different X; its cost stays put.

| event | technology |
|---|---|
| Viesgo → Repsol, 2018-11-02 | hydro (VIES), Aguayo pumped storage, Algeciras 3 and Escatrón 3 combined cycle, on the same day |
| EDP → TotalEnergies, 2020-12-01 | Castejón 1 and 3, combined cycle |
| Plana del Vent 1, by the 2019-07-18 listing | combined cycle |
| Bizkaia → Axpo, by the 2022-02-08 listing | Amorebieta (represented, not owned) |
| EDP's Douro dams → Movhera | hydro, as a new unit (DOUSUP) from 2022-01 |

Viesgo → Repsol moves hydro, pumped storage and combined cycle to one buyer on
one day: the cleanest hydro-vs-thermal comparison. Limits: one event, ten months
of bids before it, deals bundled retail customers (so ΔX may be small), and the
repo assigns Viesgo's units to Repsol for the whole window until dated
ownership (task_7d2e874c) lands.

## 6. The cost terms

**Thermal.** Implied cost from JRC efficiency, fuel and carbon. Spec 2's
validation checks only the gas cost level (permuted efficiencies score 0.69
against 0.67); coal fails it (median h·eff 0.615). **The gas cap window**
(2022-06-15 → 2023-12-31; 40 €/MWh through December 2022 while market gas
peaked above 200) is when a capped plant's gas cost is set by law: the
sharpest period for the thermal leg.

**Hydro: recover the water value λ, without the offers.** A λ revealed from
offers absorbs any day-level markup, so it cannot test the across-day margin.
Three offer-free routes, cheapest first:

1. **Spill days: λ = 0 observed.** When a reservoir spills, its marginal water is
   worth about zero; SNIRH records daily spill at EDP's and Movhera's dams. Use
   the most downstream dam of a cascade (water spilled upstream can be turbined
   below). A new method, M6 beside the water-value spec's M1–M5.
2. **Forward proxy (M5).** λ ≈ the forward price over the unit's storage horizon
   (storage hours built) times its capture ratio; offers already track forwards
   one-for-one (1.11, 1.22, 0.95). Crude: no option value, no turbine limits.
3. **Competitive water value (M4).** Solve the reservoir's dynamic program with
   SNIRH's weekly storage, inflows and turbined flow, heads from energy per m³
   (Alto Lindoso 284 m), turbine capacity from `cab`, price scenarios from
   forwards and the hourly shape. EDP's Portuguese cascades first; Spain has only
   MITECO's weekly storage per reservoir unless ENTSO-E's per-plant generation
   arrives with the token.

It is the **competitive** λ: a firm with market power values water at future
marginal revenue, so p − λ_comp measures within-day and across-day power
together. What it unlocks: hydro in the cost-observed leg (most of the margin),
leg B without its missing instrument, the one-β test and the levy multiplier in
levels, the counterfactual with hydro's real cost.

## 7. Natural experiments with a known prediction

### 7.1 The hydro water levy (canon hidroeléctrico)

Ley 15/2012 (art. 112 bis of the Water Law) taxes Spanish hydro at **22% of the
revenue** from energy produced, from 2013; plants ≤ 50 MW and the pumped-water
share of large pumped-storage plants get a 90% reduction (2.2%). **From
2022-04-11** (Ley 7/2022) the rate is **25.5%**, small plants 92% off (about
2.04%), pumping 90% off. RD 198/2015 develops it for basins spanning several
regions; the Supreme Court annulled its 2013–14 retroactivity in 2021. Thermal
plants do not pay it; Portugal has no equivalent revenue levy (*to verify*).

**Prediction.** A revenue tax enters unit u's condition as
(1 − τ_u)(p − c_u) = β · (the firm's common term): the firm equalises after-tax
margins, so in price terms a taxed unit's markup is 1/(1 − τ) times an untaxed
unit's facing the same X: **1.28 at 22%, 1.34 at 25.5%**. Withholding through
taxed plants is cheaper, so a profit-maximiser should exercise power there
first. The multiplier is set by law; showing it is "how" with a predicted
number, and its absence is a clean rejection. The water value scales by (1 − τ)
too, so the multiplier survives within-day differencing.

**Variation.** Within firm-hour (X identical): EDP's Spanish hydro (taxed;
Asturias, *to verify*) against its Portuguese hydro (untaxed); Iberdrola's
Spanish hydro against Tâmega (from 2022); every owner's units above and below
50 MW. Over time: the 2022 rate rise (+4.7% on the multiplier), a small effect.

**Threats.** Large dams are both taxed and flexible (size confound): answered by
the Spain–Portugal comparison of similar large dams and by units near 50 MW.
OMIE units are often cascades, so τ per unit needs a plant map (JRC hydro;
Spain's map not built). Basins wholly inside one region may fall under other
rules (*to verify*).

### 7.2 The gas cap (RDL 10/2022)

Policies shift cost, not n, so in this framework they mostly validate c rather
than identify β. The gas cap is the exception worth building on: its window
gives the thermal leg a statutory cost (§6), and within the step estimator the
causal question is **did conduct change when the cap hit?** The benchmark nets
out the cap's mechanical reshaping of residual demand; the date is sharp.
Confounders: the 2022 crisis and the surge of exports to France. The earlier
pass-through design (`gas_cap_passthrough.py`) was not identified with unit and
month effects.

### 7.3 The 2021 windfall levy (RDL 17/2021): as a shifter of n

As a cost shock it is exhausted (`levy_contract_exposure*.py`). New angle,
speculative: RDL 23/2021 exempted fixed-price forward contracts, so the levy
gave firms a reason to contract outside the auction, and it ended on
2023-12-31; Endesa moved its hydro back into the auction in 2024. A
policy-timed shift in the exposed n. The levy is also a per-MWh cost, which must
go into c (it is set by law, so it can).

### 7.4 Parked

The 10 MW threshold design for the windfall levy: renewables offer at zero,
hydro and nuclear are too thin (about 5 units within ±2 MW), and it needs the
CNMC registry of regulated remuneration. Coal closures of June 2020: a
regulatory deadline removed a thermal channel, but it coincides with COVID.
Reservoir spills as a closed hydro channel: storage is partly a choice (spill
days are used instead as a cost anchor, §6).

## 8. Other outcomes the policies make testable

| outcome | policy and variation | data |
|---|---|---|
| firm-level bilateral share (`pdbf` role 4): contracting out of the auction | windfall levy's contract exemption (2021-09-16), the gas cap's exemption for contracts signed before 2022-04-26 (*to verify*), the levy's end (2024-01-01) | in hand |
| declared minimum-income variable term: does it fall one-for-one with the cap's known cost cut? | gas cap; `cab` covers its first 21 months (to 2025-03-18) | in hand |
| bunching of plant capacity at 50 MW and 10 MW | water levy, windfall levy | JRC hydro, `cab` max power |
| within-firm output shifted from taxed to less-taxed hydro | water levy | `pdbf` schedules; per-plant hourly generation from ENTSO-E (token) |
| pumping at mixed plants (pumped water 2.2%, natural inflow 22%) | water levy, 2022 rise | OMIE pumping bids |
| short-notice unavailability of capped thermal or levied hydro | gas cap, windfall levy | `indisp` (thinning from 2023-02) |
| forward premium (forward minus realised spot) | both | OMIP |
| technical-constraints market, unit programmes, the daily adjustment price | gas cap | ESIOS (token) |

Already published: the cap's price effect, exports to France, congestion rents.

## 9. Data

| item | status |
|---|---|
| ENTSO-E day-ahead wind and solar forecasts (ES, PT); per-plant generation; unavailability (Art. 15.1) | token requested 2026-10-01 (ticket #9472601); `fetch/fetch_entsoe_spain.py` written, never run; 400 requests per minute |
| ESIOS forecasts (indicators 541, 542, demand), unit programmes | token requested 2026-10-01 (`notes/email-esios-token.md`); `fetch/fetch_esios_spain.py` written, never run |
| REE demand forecast | on disk |
| SNIRH spill, storage, inflows, turbined flow | on disk (LMU eduVPN only) |
| farm locations and owners (RAIPEE, OSM, GEM); site forecasts (Open-Meteo, TIGGE) | to fetch; coverage *to verify* |
| hydro plant map for Spain (τ per unit) | to build from JRC hydro |
| dated unit ownership in `firm_x` | task_7d2e874c |

## 10. Sequence

1. **Decisions** (user, then supervisor): confirm this direction; confirm the
   framework's §8 step 5b.
2. **Read-only probes, now:** firm-level gap frequency 2018–2023 (one month per
   year); share of steps at a technical bound; spill days per cascade against
   EDP's margin hours; contract shares around the policy dates; capacity
   bunching at 50 and 10 MW; τ per unit and how many firm-hours hold both taxed
   and untaxed hydro.
3. **When the tokens arrive:** fetch the forecasts; first-stage probe of own-fleet
   and rivals'-fleet forecasts on each firm's n, |RD′| and X.
4. **Build the step estimator** on thermal firm-periods, gas-cap window first.
5. **Water value**: spill anchor and forward proxy; the dynamic program for EDP's
   Portuguese cascades as its own project.
6. **Hydro and the one-β test**, then the levy multiplier.
7. **The counterfactual price** (framework §7).

## 11. To verify before use

- Open-Meteo's historical-forecast coverage; TIGGE's research access.
- The gas cap's exemption date for contracts (2022-04-26).
- Portugal has no revenue levy equivalent to the canon; EDP's Spanish hydro is in
  Asturias; the canon's coverage of basins inside one region.
- Spanish nuclear stopping at low prices since 2024.
- ESIOS token header (`x-api-key` or `Authorization: Token`).
