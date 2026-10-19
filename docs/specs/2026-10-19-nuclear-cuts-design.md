# Nuclear cuts: saving fuel, or holding back output?

**Status: proposed 2026-10-19. Nothing here is built or run.** A companion to
[`2026-10-19-outage-events-design.md`](2026-10-19-outage-events-design.md), whose
fault doses serve as instruments here (§5, T3). Framework:
[`2026-09-29-thesis-framework-design.md`](2026-09-29-thesis-framework-design.md).
Statements marked *to verify* come from press or industry sources and must be checked
against the official text (BOE, regional gazettes) before anything rests on them.

**In one example.** On 5 March 2024 at 13:00, Almaraz 1 (1,011 MW) offered 646.5 MW at
€0 and the other 357.2 MW at €250/MWh, a price that day never came near (it peaked at
€129). So the reactor ran at about two-thirds of capacity by choice. That cut is
efficient if the price was below what one more MWh from the reactor costs. It is market
power if the price was above that cost and Almaraz's owners gained more from the higher
price on the rest of their sales than they lost on the MWh they held back.

**The test.** Both stories fit a cut at a low price. They differ on one point: whether
the cut depends on how much else the owner is selling. A price-taker cuts when the price
falls below its own cost, whatever else it owns. A firm with market power cuts more when
it is a large net seller, because then a higher price is worth more to it. The firm's
net position is the one thing the efficient story says should not matter.

**Why this design is worth building.** Every earlier design struggled with the cost
term. A reactor's cost per MWh (fees, taxes, fuel) barely moves within a month, so
reactor × month effects remove it, and β is identified from day-to-day movement in the
owner's position. The cost level is needed only to describe the cuts (§4, T1–T2), and
there a lower and an upper bound are enough.

---

## 1. What is already measured

From `outputs/tables/reactor_outage_hours.parquet` (`build_reactor_outages.py`;
`notes/rq-reactor-outages.md` §2–3):

| year | undeclared lost output, TWh |
|---|---|
| 2018–2023 | 0.7–1.9 a year |
| 2024 | 7.80 |
| 2025 | 5.08 |
| 2026 (to May) | 5.45 |

- **The cuts follow low prices.** In the 24 hours before a spell begins, the price sits
  8.7 €/MWh below its month × hour mean (se 0.9).
- **They are not an hourly decision.** In 2024–2026 every local hour carries 2.9–5.0% of
  the cut volume, night and midday alike. So a reactor cuts for whole days at a time;
  it does not follow the solar dip within the day.
- **Some "undeclared" hours may be real outages.** 48,558 of the 135,750 undeclared
  reactor-hours fall on days the outage register (`indisp`) has no snapshot for, since
  43 of its monthly zips are partial at source. Example: Almaraz 1 schedules 0 MW from
  9 to 15 March 2024, and the March 2024 zip holds one day.

**How a cut shows up in the offers** (measured 2026-10-19, 13:00 on two days):

| reactor | 2024-03-05 | 2024-03-20 |
|---|---|---|
| Almaraz 1 | 646.5 MW at €0, 357.2 at €250 | 50 at €0, 961.3 at €427.16 |
| Trillo | 594.5 at €0, 400.5 at €250 | 594.5 at €0, 408.9 at €427.16 |
| Almaraz 2 | 368 at €0 | 347.2 at €0 |
| Ascó 1 | 688 at −€1, 307.8 at €50.51 | 995.8 at €35 (not accepted) |

Two forms, and they are different evidence:

- **Withdrawal at a prohibitive price** (Almaraz, Trillo: the two reactors run by the
  same operating company, CNAT). This is a quantity decision taken the day before. The
  €250 and €427.16 prices carry no information about cost.
- **A reservation price** (Ascó 1, run by ANAV, Endesa's 100%). €35 and €50.51 are
  prices at which the reactor will run, so they reveal the threshold directly.

**Almaraz 2 did not cut on either day**, although it has the same owners and operator
as Almaraz 1. So something specific to the reactor matters, plausibly where it stands in
its fuel cycle, which is the fuel value of §3.

Part of a reactor's schedule is bilateral contracts with its co-owners' retailers
(PDBF role code 4), outside the auction. Whether cuts also come out of the bilateral leg
is not yet measured (T1).

## 2. The two stories, as one condition

The same condition as the framework, on the reactor's quantity instead of an offer step.
An owner with net position n (MW sold in the auction minus MW bought) gains from one more
MWh of the reactor:

    p − c − β · n / |RD′|

where |RD′| is the slope of the residual demand the owner faces (MW per €/MWh, as in
`firm_x.py`). It runs the last MW if this is positive and cuts it otherwise:

- **Price-taking (β = 0):** cut if and only if p < c.
- **Market power (β > 0):** cut if p < c + β · n / |RD′|. A large net seller cuts at
  prices above its cost; a **net buyer** (n < 0) wants the price lower, so it should
  almost never cut above cost. That sign prediction is leg D's, now on a quantity.

**n must be the position the owner would have if the reactor ran in full.** A cut lowers
the bilateral supply to the owner's own retailer, which then buys more in the auction,
so the cut itself lowers n. Use n plus the owner's share of the cut MW (`n_full`), and
instrument it (§5).

**Co-ownership.** Almaraz 1 is Iberdrola 52.7%, Endesa 36.0%, Naturgy 11.3%. A cut one
co-owner wants may cost another. Three candidate rules, compared in T4 (my proposal):

1. the operator follows the largest owner: its n_full;
2. the co-owners maximise their joint profit: the **sum** of their n_full;
3. each owner weighs the reactor by its share: Σ sᵢ · n_full,ᵢ.

## 3. The cost of a reactor MWh

c = per-MWh fees and taxes + the value of the fuel not burned, all divided by (1 − t),
with t the generation tax rate (the IVPEE, the tax on the value of electricity
production) in force that day.

| component | size | source | status |
|---|---|---|---|
| Enresa fee (waste management, per MWh produced) | 7.98 €/MWh, raised by royal decree in 2024 to about 10.36 | Orden/RD in the BOE | *to verify: final rate and start date* |
| Spent-fuel and radioactive-waste taxes, Ley 15/2012 | per kg of heavy metal; convert per MWh with the reactor's burn-up | BOE | *to verify* |
| Regional taxes | Extremadura ~5 €/MWh (Almaraz); Catalonia ~5–6.65 (Ascó, Vandellós); Valencia ~1.8, recently removed (Cofrentes); Castilla-La Mancha (Trillo) unknown | Foro Nuclear; press | *to verify, with dates* |
| IVPEE, 7% of revenue | divides c by 0.93 when in force; suspended and reintroduced in steps | dates already in `notes/rq-ivpee-tax-test.md` | known |
| Windfall reduction, RDL 17/2021 (*minoración*) | price-dependent, on non-emitting plant from late 2021 | BOE | *to verify: whether it reached nuclear's marginal MWh* |
| Fuel, accounting cost | roughly 5–7 €/MWh | no per-plant public figure | *a bound, not a measurement* |

**The fuel is not used up by running and not saved for free by cutting.** A core is
loaded for about 18 months. Fuel not burned in a cheap week either lengthens the cycle
(the reactor runs on at a later, maybe higher, price) or is carried into the next core.
So its value lies between about 0 (if it is wasted at refuelling) and the value of the
output it allows later. That is the nuclear version of the water value. Bounds:

- **lower bound c_lo:** fees and taxes only, fuel valued at 0;
- **upper bound c_hi:** fees and taxes plus a fuel value equal to the expected price
  over the rest of the cycle (OMIP Spanish forwards, as in `build_water_value_forward.py`),
  or the accounting fuel cost if that is higher.

A price-taker with a fuel value cuts at prices above c_lo when later prices are higher.
**So the level of the threshold cannot tell the stories apart; its dependence on n can.**
A fuel value moves slowly and does not depend on the owner's other positions, so reactor
× month effects absorb it.

## 4. Tests, in order

Each is a separate run, proposed and approved before it starts. T1 and T2 need no
instrument; T3 needs the outage-events design's doses.

**T1. Describe the cuts** (no estimation).
- Reactor-days 2018-01 → 2026-05: cut MW (cab max power minus PDBF schedule) on hours
  no declaration covers, **plus** hours declared as flexible operation (the `economic`
  class: Almaraz 1 and Cofrentes, April–May 2025), which are chosen cuts too. The
  April 2020 lockdown derate is reported apart. Split into auction and bilateral legs.
- Form of the cut: MW offered at a prohibitive price (≥ €200, a *my call* cut-off to
  check against the distribution) against MW offered at a reservation price
  (> €0 and < €200).
- By year, month, reactor and operator; against the D-1 solar and wind forecasts
  (ESIOS 1777/1779) and the day's expected price.
- The share of cut volume at expected prices below c_lo, between c_lo and c_hi, and
  above c_hi.

**T2. The price-taking benchmark.** For each reactor-day, the cut a price-taker would
make: cut when the expected price is below c (each bound in turn), respecting the
reactor's observed minimum load and ramp limits (from its own record). Compare simulated
with actual cut volume, by year. If the benchmark at c_hi explains nearly all of it,
there is little left for market power to explain, and T3 is a precise zero.

**T3. The conduct test.**

    cut_rd = β · n_full / |RD′| + reactor × month + day-of-week + controls + e

- **Outcomes:** (a) cut MW on the reactor-day; (b) on reactors offering a reservation
  price, that price (Ascó's €35 and €50.51 kind).
- **Expected values:** offers close at noon on D-1, so n_full and |RD′| enter as their
  expectation given D-1 information, as in the step estimator (`rq-step-estimator.md`).
- **Instruments for n_full:** shocks to the owner's other plant: outages of its other
  reactors, its regional wind deviation (`regional_wind_offer_test.py`) and its
  own-catchment rain. Instruments for |RD′|: rivals' wind and solar forecasts.
  *(2026-10-19: the owner's gas and coal faults were to be a fourth. They are out: their
  first stage is too weak, F 3.7, and the outage-events design's stop rule applies;
  `notes/rq-outage-events.md`.)*
  **Not** outages of a reactor on the same site (Almaraz 1 for Almaraz 2, Ascó 1 for
  Ascó 2): same operator, staff and grid connection, so they can reach the decision
  other than through n.
- **Sample:** 2019-01 → 2026-05, since REE's D-1 forecasts start in 2019. Since cuts are
  rare before 2024, 2024–2026 is also reported on its own.
- **Many zeros:** most reactor-days have no cut. Main: linear in cut MW; check: the
  threshold model of §2 estimated directly (cut when the expected p − c falls below
  β · n_full / |RD′|, with c within reactor × month).
- **Sign test:** β estimated separately for net-selling and net-buying days. Market
  power predicts cuts above cost on selling days only.
- **Inference:** Anderson–Rubin sets (valid when instruments are weak), clustered by
  week. Seven reactors and four or five owners: the variation is over time, not across
  firms.
- **Null band:** run the same estimator on T2's simulated price-taking cuts, as
  `price_taking_simulation.py` does for offers. The outage instrument was biased under
  the null there (hydro −0.40), so the actual estimate is read against that band, not
  against 0.

**T4. Whose position.** Re-estimate T3 with each of §2's three co-ownership rules and
compare fit (and whether β agrees across reactors with different owner mixes: Cofrentes
is Iberdrola alone, Almaraz three owners).

**A prediction fixed in advance.** The 2024 Enresa increase raised c by about
2.4 €/MWh (*to verify*). A price-taker's threshold rises by that divided by 0.93 from the
start date. Testing it checks the cost scale with a change set by law, as the IVPEE
steps did for gas.

## 5. Threats, and the answer to each

| threat | answer |
|---|---|
| Technical limits: minimum load, ramp rates, a limited number of load changes per cycle, flexible operation needing regulator (CSN) approval | day-level outcome; each reactor's limits taken from its own record; spells as a robustness check; days near refuelling (coastdown) dropped |
| Fuel value correlates with n through the season | reactor × month effects; the fuel value from forwards as a control |
| The cut is an outage the register missed (gap days) | main sample: partial cuts only (reactor between its minimum load and capacity); whole-day stops on gap days reported apart |
| REE (the system operator) reverses or orders cuts | PDBF is before REE's technical-constraint redispatch, so its instructions are not in the outcome. Check the final schedule (P48) in the I90 sample on cut days |
| The price is moved by the cut itself | expected price from D-1 information, never the realised price |
| Few owners | stated plainly; the design identifies a time-series β per owner group, not a cross-section |

## 6. What ties it to solar

Solar pushes the spring and weekend price down for whole days, which is when the cuts
happen. T1 measures that. T3 then asks whether, on the days solar makes a cut cheap, the
cut is larger for owners who gain more from a higher price. If it is, solar changed how
firms use market power, through the nuclear margin.

## 7. Left to the builder

- The exact prohibitive-price cut-off, after looking at the distribution of nuclear
  step prices.
- The expected-price model on D-1 information (time-blocked folds if a learner is used;
  `notes/ml-methods-to-legs.md` §1).
- How minimum load and ramp limits are read from each reactor's record.

**My calls, to check:** the three co-ownership rules (rule 2 uses the market-wide
residual-demand slope, since the co-owners act jointly); the fuel-value upper bound from
forwards; dropping whole-day stops on register-gap days from the main sample; counting
declared flexible operation as a cut; leaving same-site reactor outages out of the
instruments; T1–T2 before any instrumented run.
