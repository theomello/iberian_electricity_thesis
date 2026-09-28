# Midday hydro: do the firms that set the price at solar noon price it strategically?

Written 2026-09-28. **A sketch, not a spec.** It follows from §4.3, §4.4 and
§7 of [`rq-descriptive-price-formation.md`](rq-descriptive-price-formation.md),
and it is built to avoid the thing that killed the eight earlier conduct designs:
it needs **no marginal cost at all**, not even a water value.

Probe: `scripts/analysis/hydro_within_day_probe.py`, 30 storage-hydro sell
units, 30.2 GW. Run bare, it reproduces the 8-sample-month figures; `--all`
gives the full-archive figures (2018-01 → 2026-06). The break dating in §3.6 is
`scripts/analysis/hydro_flat_break.py`. Every number below is **[preliminary]**.

---

## 1. The question

> **When solar empties the midday market and storage hydro is left setting the
> price, do hydro owners mark up their offers in the hours where their residual
> demand is steepest — or do they bid a water value that is flat across the day?**

Why this one:

- **It is where the descriptive results point.** Residual-demand elasticity η
  fell most at solar noon (−87% at hour 12, against −63% in the evening ramp,
  §4.3). Near-margin concentration rose as a step (§5.2). Combined-cycle gas
  left the margin and hydro took about three-quarters of resolved periods (§4.4).
  So the thin, concentrated midday margin is a *hydro* margin.
- **Few firms own the hydro.** Storage hydro in the sample: EDP 11.7 GW,
  Iberdrola 10.8 GW, Endesa 3.5 GW, Movhera 2.2 GW, Naturgy 1.7 GW, Repsol
  0.3 GW. Six groups. If market power lives anywhere at the midday margin, it
  lives here.

## 2. The identification idea: difference the water value out

Every hydro design so far tried to measure water value's *level*
([`hydro-water-value-design.md`](hydro-water-value-design.md)), and all three
probes returned a wrong sign. This design never measures it.

**For a storage plant, the opportunity cost of water is a daily shadow price
λ_id.** Water released at 13:00 or at 21:00 comes out of the same reservoir, so
it has the same value at the margin. That holds when the intra-day storage
constraint does not bind and no flow or ramping limit binds (see §5).

The supply-function first-order condition of Hortaçsu & Puller (2008), with
marginal cost equal to λ, gives the offer price of unit *i*'s firm in hour *h*:

```
b_ih  =  λ_id  +  (q_fh − θ_fh) / |RD′_fh|
```

- `q_fh`: the firm's total output in hour *h*
- `θ_fh`: its contract position, from PDBF (OMIE's daily operating schedule),
  role code 4
- `|RD′_fh|`: the slope of the residual demand the *firm* faces, which is
  already computed in `firm_residual_demand_full_owner.parquet`

**A unit × day fixed effect removes λ_id completely.** What remains is:

```
b_ih − b̄_i,d  =  β · [ (q−θ)/|RD′| ]_fh − mean over the day  +  ε
```

This makes a **point prediction**, not only a sign:

| conduct | prediction |
|---|---|
| price-taking | β = 0: the offer curve is flat across the day at λ |
| supply-function Nash | β = 1 |
| in between | 0 < β < 1 |

That is a sharper test than anything else in this repo, and the cost problem is
gone by construction. The competitive benchmark is **a flat offer curve**, and
that is observable directly.

**The FOC itself is not new here.** `scripts/analysis/hortacsu_puller_test.py`
(commit `6c900ec`) already measures every term and **inverts** it to recover an
implied marginal cost per firm-period. What is new is using it the other way
round: difference the cost out within a unit-day and test β, instead of solving
for the cost. Two things carry over directly:

- **`q` is total scheduled output from PDBF, not day-ahead cleared volume.**
  Contracted energy never enters the auction, so cleared volume is already
  roughly `q − θ`, and using it as `q` subtracts the contracts twice. The first
  pass of that script made this mistake and got θ/q = 2.91 for Iberdrola.
- **That script's result supports the premise.** Imposing θ moved implied
  costs toward plausible, stable values, so the contract term belongs in X.

## 3. What the probe found

### 3.1 Flat curves are the norm, and becoming less so

Share of unit-days where the offer price at 50% of capacity is identical in
every hour:

| 2019-01 | 2019-07 | 2021-04 | 2022-04 | 2024-04 | 2024-07 | 2025-04 | 2026-04 |
|---|---|---|---|---|---|---|---|
| 0.64 | 0.74 | 0.62 | 0.69 | 0.66 | 0.51 | 0.59 | **0.46** |

The median within-day SD is **0.00 €/MWh**, against a median between-day SD of
0.8–50. So **most of a hydro unit's price variation is between days, not within
them**, which is what bidding a daily water value predicts. The within-day
channel exists on about half the unit-days and is growing.

**On the full archive it is a step, not a slide.** The flat share by year is
0.65, 0.67, 0.64, 0.71, 0.73, 0.72 for 2018–2023, then 0.55, 0.44 and 0.51 for
2024–2026.

### 3.2 The firms differ, and Iberdrola's behaviour changed

Flat share by group and year, full archive:

| group | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| **Iberdrola** | 0.79 | 0.79 | 0.87 | 0.91 | 0.91 | 0.87 | **0.56** | **0.34** | **0.43** |
| Repsol | 0.74 | 0.55 | 0.73 | 0.62 | 0.68 | 0.65 | **0.28** | 0.41 | 0.21 |
| EDP | 0.38 | 0.37 | 0.33 | 0.36 | 0.29 | 0.32 | 0.35 | 0.38 | 0.39 |
| Naturgy | 0.16 | 0.25 | 0.14 | 0.23 | 0.13 | 0.17 | 0.13 | 0.10 | 0.22 |
| Endesa | 0.09 | 0.16 | 0.14 | 0.10 | 0.09 | 0.01 | 0.07 | 0.07 | 0.17 |
| Movhera | — | — | — | 0.30 | 0.18 | 0.18 | 0.04 | 0.04 | 0.14 |

The two groups that were mostly flat, Iberdrola and Repsol, both change in
2024. The others were never mostly flat and do not change. §3.6 dates
Iberdrola's change.

### 3.3 The midday deviation reversed sign, peaked in 2023, and is fading

On non-flat unit-days, mean deviation of the p50 offer from the unit's own daily
mean, in €/MWh, full archive:

| hour | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| 13 | −7.4 | −1.0 | +0.5 | +5.2 | +13.7 | **+32.8** | +19.0 | +7.5 | +6.8 |
| 16 | +1.3 | +4.9 | +5.6 | +9.1 | +27.1 | +30.3 | +14.8 | +6.4 | +0.1 |
| 21 | −15.2 | −9.9 | −13.2 | −24.1 | **−62.1** | −33.7 | −27.5 | −20.2 | −5.1 |

Before the solar build-out, midday offers sat at or below the daily mean; from
2021 hydro units asked more at solar noon and less in the evening. That is the
direction market power predicts if residual demand is steepest at midday. But
it is also consistent with the physical constraints in §5, so it is a
motivating fact, not a result.

**The first draft of this section, on 8 sample months, overstated 2024–25.**
The midday premium peaked in 2023 at +32.8 and has fallen back since, to
+19.0 in 2024, +7.5 in 2025 and +6.8 in 2026. The
selected non-flat days also exaggerate it (see §3.6: across *all* of
Iberdrola's unit-days the midday shift is about 3 €/MWh).

### 3.4 No withholding on quantity by hour

Offered volume as a share of capacity moves only ±1–3 percentage points across
the day. The hour-to-hour margin is **price, not quantity**. Two consequences:

- the outcome variable is the offer price;
- withholding, if present, shows up as a price rather than as missing
  megawatts.

### 3.5 The naive link has the right sign and almost no size

Within unit-day, regressing the p50 deviation on the deviation of
log |RD′_fh| gives −1.31 (2019–2022 months) and −1.01 (2024–2026) on the sample
months, and −1.18 (before 2024) and −1.36 (2024 on) on the full archive. The
sign is correct: a flatter residual demand means a lower offer. The
correlations are −0.02 to −0.04, and this is OLS on an endogenous regressor
with no instrument, no (q−θ) term and no clustering. It also covers only
**83,180 of 180,862** unit-periods on the sample months (46%), and 978,299 of
2,115,754 on the full archive. Two filters compound: the firm slope panel keeps
only periods with p* > 0 and no market splitting (threat 7), which 77% of
unit-periods survive, and p50 is then undefined wherever a unit offers under
half its capacity. **Do not read anything into it except that it is not
wrong-signed.**

### 3.6 Dating Iberdrola's break: a staggered rollout in mid-2024, not an event

`hydro_flat_break.py`, on the six Iberdrola units present across the whole
archive (Tâmega was commissioned in 2022 and is reported but not pooled).
Least-squares single mean shift on the daily share of flat unit-days, with
Bai's (1994) 95% interval.

**The robust break is in the price at 50% of capacity: 2024-06-29, interval
2024-06-24 → 2024-07-04.** The flat share falls from 0.92 to 0.39 and the step
explains 70% of the daily variance. The week-by-week share goes 0.71, 0.62, 0.43,
0.33 through the weeks of 23 June to 14 July 2024. The share of unit-days on
which p50 can be scored stays at 0.62–0.97 throughout, so this is not a change
in censoring.

**But the units did not move together.** Per-unit breaks in the same measure:

| unit | break | flat share before → after |
|---|---|---|
| Tajo | 2023-12-02 | 0.84 → 0.21 |
| Tâmega (PT) | 2024-01-29 | 0.85 → 0.48 |
| La Muela | 2024-02-08 | 0.96 → 0.54 |
| **Ebro** | **2024-06-25** (±5 days) | **0.99 → 0.20** |
| Duero | 2024-08-14 | 0.90 → 0.21 |
| Sil | 2024-08-16 | 0.94 → 0.19 |
| Júcar | 2025-02-14 | 1.00 → 0.80 (barely moves) |

So "Iberdrola's break" is a rollout over about nine months, with the bulk in
June–August 2024. **No dated event lines up.** The rollout *starts* within weeks
of the clawback (RDL 17/2021) and the gas cap (RDL 10/2022) both ending on
2023-12-31, but the group date is 180 days after that, and nothing else on the
list (the 2025 SDAC and MTU changes, the blackout) is close.

**One apparent earlier break was an artefact.** A first version measured
whether the unit used the same *set* of step prices all day, and found a sharp
break on 2023-01-03, with Ebro and Júcar changing on that exact date. It was a
**0.1 MW step at 0 €/MWh** that Iberdrola adds in some hours and not others: on
2023-03-15 Ebro offers its whole 183 MW at 498 €/MWh in every hour, and the
token step is the only thing that varies. Ignoring steps under 1 MW removes
most of that break (the step's share of explained variance falls from 0.50 to
0.20) and Ebro's and Júcar's entirely.

**What changed, a year either side of 2024-06-29**, as the mean deviation of the
p50 offer from its unit-day mean, across *all* unit-days:

| hour | 02 | 05 | 08 | 11 | 13 | 15 | 18 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|---|---|
| before | −1.2 | −3.1 | +3.5 | −0.5 | −1.1 | −1.6 | −2.7 | −1.1 | +6.0 | +7.9 |
| after | −4.1 | −3.7 | +0.9 | +2.6 | +2.0 | +1.5 | +0.2 | +4.3 | +4.2 | +4.9 |

Midday offers rose by about 3 €/MWh relative to the day and the evening premium
shrank. That is the direction §2 predicts, but the average is small because it
averages large, discrete switches (next paragraph) over many unchanged days.

**The within-day variation is bimodal, not a smooth markup.** Where Iberdrola's
offers vary, the same point on the curve jumps by roughly 300–490 €/MWh between
hours of one day: a tranche is offered cheaply in some hours and at a price-out
level (384–498 €/MWh) in others. On 2024-03-13 Tajo offers 265 MW at 10 €/MWh
in periods 11–18, clearing in the two where the price reaches it (10.00 and
21.62 €/MWh), and prices itself out in periods 20–23, when the clearing price
is 68–134 €/MWh. That is the
unit choosing its own hours rather than letting a flat water value choose them.
It looked like the *opposite* of what either competitive water-value bidding or
midday market power predicts for a storage plant. §3.7 resolves it: in those
evening hours Tajo was running at 1,403 MW on a bilateral contract.

### 3.7 Where the energy goes: Iberdrola's auction offer is a residual

`hydro_schedule_routes.py`, full archive, 1,506,249 unit-hours. Each storage
unit's scheduled energy is split into three published routes: the physical
bilateral contract schedule (PDBF role 4), day-ahead cleared volume, and net
intraday volume. PDBF's own auction row matches the bid files' cleared volume
to 0.00%.

**The groups use completely different routes:**

| group | bilateral share of scheduled energy | change |
|---|---|---|
| Iberdrola | 0.54–0.73 every year | none at the 2024 break |
| Endesa | 0.77–0.93 to 2023 | **0.50, 0.38, 0.34 in 2024–2026** |
| Naturgy | ~0.00 to 2021 | **0.80–0.97 from 2022** |
| EDP, Movhera, Repsol | 0.00–0.07 | none |

Intraday net volume is small everywhere (Iberdrola 0–8%), so priced-out
capacity is not being moved to intraday.

**At midday, almost none of Iberdrola's hydro clears in the auction.** A year
either side of its break, the auction carries 18–19 MWh per unit-hour at
midday against 154–172 MWh of bilateral schedule. The bilateral schedule does
the within-day shaping: 344 MWh per unit-hour in the evening against 172 at
midday.

**The direct test: within a unit-day, priced-out hours are the hours the unit
runs most.** In Iberdrola's 864 unit-days that contain both kinds of hour, the
bilateral schedule sits **+166 MWh** above its unit-day mean in hours where the
p50 offer is priced out (≥ 300 €/MWh and more than 100 above p*), against
**−111** in the others. Total scheduled output is +154 against −104. For EDP
(840 unit-days, no bilateral) and Naturgy (71), priced-out hours have *lower*
output: EDP −27 against +36, Naturgy −47 against +80. Endesa has too few mixed
days (56) to say.

**So for Iberdrola a price-out marks capacity already committed on contract,
not withholding, and its auction offers are the residual after the water has
been allocated.** Iberdrola's 2024 break is a change in how it offers that
residual, not in how it allocates water, since its bilateral share does not
move. For EDP, Movhera and Repsol the auction offer *is* the allocation
decision.

### 3.8 The bilateral route is self-supply, and can be nominated after the auction

**Who is on the other side: Iberdrola itself.** In March 2024, Iberdrola's six
storage units sell through exactly two bilateral contracts (PDBF role 4). Their
only buy legs are two Iberdrola retail purchase units: `ICLIC01` "IBERDROLA
CLIENTES COMPRA" (2.03 TWh) and `IBRM01` "IBERDROLA SERVICIOS ENERGETICO"
(0.12 TWh), both owned by Iberdrola Energía España. Sell and buy legs balance to
0.000 MW in every contract-period, at 2.14 TWh a side. So the bilateral route is
**Iberdrola's hydro serving Iberdrola's own retail customers**, outside the
auction. One month checked; the other months and the other groups' contracts
still need the same trace.

**When it is nominated: optionally after the auction.** Red Eléctrica's
operating procedure P.O. 3.1 (BOE-A-2024-11535, §6.2 and §6.4; the same windows
appear in REE's November 2020 guide to physical bilateral contracts):

| window | deadline, D−1 | what can be nominated |
|---|---|---|
| before the auction | 10:15 | domestic bilaterals that opt for a firm pre-market nomination |
| after the auction | 13:00, or 20 minutes after the day-ahead results | domestic bilaterals without that option, and *increases* to firm ones |
| by default | set 2+ business days ahead | a standing profile over a period |

Day-ahead gate closure is 12:00. **Firm pre-market nomination is optional**, so
a domestic contract can be nominated after the day-ahead prices are known.

**Is the allocation committed at gate closure? Tested — partly, and not the
way first inferred.** The inference was that Iberdrola's retail units, which bid
their demand into the auction by 12:00, would bid for less in the hours where
they expect hydro self-supply, so the allocation would be committed before the
13:00 nomination. `scripts/analysis/iberdrola_self_supply.py` regresses, within
a day, each retail outcome on the hour's hydro self-supply and REE's day-ahead
demand forecast. It sums over all ten Iberdrola purchase units: the two contract
counterparties alone bid almost nothing before 2023 (11–143 MWh per hour), when
Iberdrola's retail demand went through `IBCUC01` (its regulated reference
supplier) and `IGESC01`.

| response to 1 MWh more hydro self-supply | 8 sample months, 2019-03 → 2025-03 |
|---|---|
| demand **bid** volume | −0.15 to +0.14: **not cut** |
| demand **cleared** | **−0.33 to −0.87** in six months, significant; −0.09 (2022-03) and −0.15 (2025-03) in the others |
| intraday net purchases | −0.01 to +0.01: **no correction** |

So in high-self-supply hours Iberdrola buys less in the auction, but not by
bidding for less. The cut runs through the price of its demand bids or through
the market price itself, and the two cannot be separated here: self-supply
peaks in the evening, when the price does, so a price-elastic demand bid clears
less then with no anticipation at all. And since intraday does not absorb it,
0.13–0.67 of each self-supplied MWh is unaccounted for by these three routes in
most months. Iberdrola's other bilateral contracts, or imbalance settlement,
are the remaining candidates. **The allocation is not shown to be committed at
gate closure, and the net-position framing below rests on that.**

**Why it matters for the design.** For a vertically integrated firm that
self-supplies, the price incentive in an hour runs through its *net* auction
position: generation sold minus retail demand bought. The descriptive chapter
already bounds Iberdrola as a net day-ahead **buyer** (§4.5 there). A net buyer
gains from a *lower* price, so shifting its own water into the evening
self-supply, and buying less in the auction then, is the direction a net buyer
with market power would choose. It is also what a price-taker would do, since
evening prices are higher. Only a benchmark allocation separates the two.

## 4. Specification (to build)

```
b_ih − b̄_i,d = β · X̃_fh + γ_i,hour-of-day + δ_hour × month + ε_ih
X_fh = (q_fh − θ_fh) / |RD′_fh|,   tilde = deviation from the firm-day mean
```

- **Outcome.** The offer price at fixed quantiles of *capacity* (p25, p50),
  and at fixed quantiles of *offered* volume. p50 of capacity is censored on
  35–50% of unit-periods, because units offer less than half their capacity.
- **Unit × hour-of-day fixed effects (γ).** They absorb stable hydraulic
  profiles: environmental minimum flows, habitual ramps, cascade coordination.
  After them, β is identified from **day-to-day changes in the shape of the
  day**, not from the average midday-versus-evening contrast.
- **Instrument for X̃.** |RD′| is built from rivals' bids submitted at the
  same time, so it is endogenous. Use the **clear-sky solar profile** (pure
  astronomy, hour × day of year) × installed solar capacity. It shifts where
  residual demand meets the rival stack, and so its slope. It needs no
  forecast, which avoids the realised-weather flaw that sank the rain probes.
  Installed capacity has no token-free Spanish source; use the monthly maximum
  of REE's 5-minute solar output as a proxy.
- **Inference.** Cluster on date. There are only six firms, so any difference
  *between* firms is descriptive (the 32-firm ceiling, §7 of the descriptive
  note, binds harder here).
- **The outcome may need to be discrete.** §3.6 shows the variation is a tranche
  switching between a low price and a price-out level, not a continuous
  markup. A linear β on the p50 deviation averages those switches. The better
  object may be the probability that a given tranche is priced out in hour *h*,
  set against X̃_fh. Decide this before building.

## 5. Threats, and how each is handled

1. **Physical constraints make a competitive curve non-flat.** Ramping, turbine
   limits, minimum flows and cascade coupling all do this. Stable ones are
   absorbed by γ. Variable ones (floods, drought release rules) must be
   controlled for. The spill-window probe found plants **cut offered volume by
   13% in floods**, so flood days need a flag.
2. **Water value is not constant within the day for small reservoirs.** A
   daily-regulation pondage fills overnight and must release by evening, so its
   λ varies by hour competitively. Split the fleet by storage size (MITECO
   capacity ÷ turbine MW, i.e. hours of storage). **The prediction is that β is
   larger for large seasonal reservoirs**, where the constant-λ assumption
   holds. If β is larger for small ones, the constraint story wins.
3. **Pumped storage is a different object.** La Muela's pumping leg and the
   Portuguese bombagem units buy at midday, and are not in the sample. La
   Muela's *turbine* leg (MUEL) is in the descriptive sample, but pumping refills
   it, so its λ is tied to the pumping price rather than to a fixed daily water
   budget: treat it separately in estimation. The pumping bids are a natural
   second object, as the mirror image.
4. **A firm's portfolio moves X.** Iberdrola's midday solar output raises
   `q_fh` exactly at noon. That is not a threat, because it is the incentive
   the FOC says matters. But it means the **(q−θ) term must be computed on the
   whole firm portfolio**, not on hydro alone.
5. **Flat days are a mass point.** Half the unit-days have zero within-day
   variation. Model the extensive margin separately (does a unit-day go
   non-flat when the day's X profile is steeper?) before pooling.
6. **Intraday re-optimisation.** Hydro can re-trade in the intraday sessions,
   so the day-ahead curve may partly anticipate them. The intraday bids are on
   disk, so check whether the midday premium is unwound there.
7. **Sample selection.** The firm slope panel keeps only periods with p* > 0 and
   no market splitting, which drops the high-solar hours (66% retention in
   2026). The *offer* is defined in every hour, but |RD′| at p* is not.
   Evaluating RD′ at the unit's own offer price rather than at p* would recover
   those hours. This is a design choice to settle before building.
8. **Complex conditions — checked, not a threat.** Daily-linked offers would
   break the hour-by-hour FOC. But in `cab`, **none** of the 30 units declares a
   minimum-income term or an SCO (Scalable Complex Order) in 2019-07, 2024-04 or
   2026-04 (0 of 806, 900 and 894 unit-days). Storage hydro submits simple
   hourly offers.
9. **Capacity allocated through another route — confirmed for Iberdrola,
   2026-09-28 (§3.7).** Its price-outs are hours already running on bilateral
   contract, not withholding, and intraday is too small to matter. **The design
   as written fails for Iberdrola, Endesa before 2024 and Naturgy from 2022**,
   because their auction offers are residuals. It stands for EDP, Movhera and
   Repsol, whose auction offers carry the allocation. What is still unseen is
   reserve and redispatch after the intraday market (ESIOS, token required),
   Timing is now settled (§3.8): domestic bilaterals may be nominated after the
   auction, and Iberdrola's are self-supply to its own retail units.

## 6. What would kill it

- **γ absorbs nearly all the within-day variation**, leaving nothing
  identified from day-to-day changes in shape.
- **β is not distinguishable from 0 with a tight interval.** That would be a
  result, not a failure: hydro prices competitively at the midday margin,
  which relocates the market-power question away from the technology that sets
  the price.
- **β is larger for small reservoirs than for large ones** (threat 2). That
  would mean physics, not conduct.

## 7. Build order

1. ~~**Full-archive unit-hour offer panel**~~ — done 2026-09-28,
   `hydro_within_day_probe.py --all`, 2,115,754 unit-periods.
2. ~~**Descriptive first:** the flat share by firm and year, and when
   Iberdrola's break happened~~ — done 2026-09-28, §3.2 and §3.6. The answer
   is a staggered rollout across units in 2024, not one date.
2b. ~~**Threat 9 before anything else**~~ — done 2026-09-28, §3.7. It
   changes the design; see 2c.
2c. **Re-base the design on quantities, not offers.** The water allocation is
   observable directly: each unit's total scheduled energy by hour, summed
   across all three routes (`hydro_schedule_routes.parquet`). Testing whether
   that hour profile tilts away from the hours where the firm's residual demand
   is steepest is route-agnostic, so it covers Iberdrola too. The offer-based
   test (§2, §4) survives as a second test on EDP, Movhera and Repsol. The
   nomination rules are settled (§3.8). For Iberdrola the quantity to model is
   the **net** auction position, so it needs `ICLIC01`'s demand bids as well as
   the hydro schedule.
2d. ~~**Check the self-supply inference**~~ — done 2026-09-28, §3.8. Partly
   supported: cleared purchases fall with self-supply, bid volumes do not, and
   part of it is unaccounted for. Still open: Iberdrola's other bilateral
   contracts (do they offset the hydro one hour by hour?), and the bilateral
   counterparties for Endesa before 2024 and Naturgy from 2022.
3. **X_fh:** join the firm slope panel, and compute (q−θ) on the whole
   portfolio, with q from PDBF as in `hortacsu_puller_test.py`.
4. **Storage-hours per unit**, from MITECO reservoir capacity. Needs a
   reservoir → OMIE unit match, which is new work.
5. **Clear-sky instrument**, then the first stage.
6. **Estimate**, with placebos: run-of-river units (no daily λ, so they should
   be flat at about €0), and pumping units as the mirror image.
