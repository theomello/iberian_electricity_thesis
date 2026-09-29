# Midday hydro: do the firms that set the price at solar noon price it strategically?

Written 2026-09-28. **A sketch, not a spec.** The water value itself — its
definition, the two margins of market power, and the assumptions every result
below rests on — is specified in
[`docs/specs/2026-09-29-water-value-design.md`](../docs/specs/2026-09-29-water-value-design.md). It follows from §4.3, §4.4 and
§7 of [`rq-descriptive-price-formation.md`](rq-descriptive-price-formation.md),
and it is built to avoid the thing that killed the eight earlier conduct designs:
it needs **no marginal cost at all**, not even a water value.

Probe: `scripts/analysis/hydro_within_day_probe.py`, 25 storage-hydro sell
units, 26.3 GW (stated as 30 units and 30.2 GW until 2026-09-28, when five
Portuguese pumping legs were found in the sample; they submit no sell offers,
so no offer figure below changed). Run bare, it reproduces the 8-sample-month figures; `--all`
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
- **Few firms own the hydro.** Storage hydro in the sample: Iberdrola
  10.8 GW, EDP 8.3 GW, Endesa 3.5 GW, Movhera 1.7 GW, Naturgy 1.7 GW, Repsol
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

**Measured, `q − θ` is the firm's net auction position**: cleared sales minus
cleared purchases, over every unit it owns. Physical bilateral energy never
enters the auction, so it drops out of both terms; and for a firm with a retail
arm, the retail load bought in the auction is the fixed-price commitment that
offsets its sales. It is **not** the firm panel's `(q − θ)`, which takes q from
auction-cleared sales and θ from the bilateral schedule and so subtracts the
contracts twice (§3.9, and the correction in the descriptive chapter's §4.5).

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

`hydro_schedule_routes.py`, full archive, 1,469,205 unit-hours (rerun
2026-09-28 without the pumping legs; the only material change is EDP's intraday
share, now −0.10 to +0.03). Each storage
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
0.13–0.67 of each self-supplied MWh looked unaccounted for by these three routes
in most months. **The allocation is not shown to be committed at gate closure,
and the net-position framing below rests on that.**

**2026-09-29: the gap closes on Iberdrola's other bilateral contracts.** The
retail position below is the NET bilateral inflow into Iberdrola's ten purchase
units (PDBF role 4, buy legs minus sell legs), so transfers between those units
cancel; per 1 MWh more hydro self-supply within a day:

| month | auction bought | net other contracts | intraday | **total retail position** |
|---|---|---|---|---|
| 2019-03 | −0.33 | −0.54 | −0.01 | +0.13 |
| 2019-10 | −0.63 | −0.23 | 0.00 | +0.14 |
| 2021-03 | −0.70 | −0.29 | +0.01 | +0.01 |
| 2022-03 | −0.09 | −0.78 | 0.00 | +0.13 |
| 2023-03 | −0.83 | −0.33 | +0.01 | −0.15 |
| 2024-03 | −0.87 | −0.19 | −0.01 | −0.07 |
| 2024-10 | −0.50 | −0.49 | 0.00 | +0.01 |
| 2025-03 | −0.15 | −0.85 | −0.01 | −0.01 |

The hydro self-supply displaces **auction purchases and Iberdrola's other
bilateral contracts together**, and the retail arm's total scheduled position
moves by only −0.15 to +0.14 — which is what it should do once demand is
controlled for. What remains is small enough for imbalances. So Iberdrola's
within-day balance is **traceable in published data**; the quantity design (2c)
does not rest on an unobserved residual.

*A first version counted only buy legs and gave −0.15 to +0.23. It double-counted
an internal pass-through (below) before 2023; netting tightened the result.*

**Who sells on those contracts** (`iberdrola_contract_trace.py`, TWh over Feb,
Jun and Oct of each year):

- **Until 2022 the largest flow was internal routing, not generation.**
  `IGESC01` "IBERDROLA GENERACION ESPAÑA C", itself one of Iberdrola's purchase
  units, bought in the auction and passed the energy to the other retail units
  by bilateral contract — 11–12.7 TWh a year over the sample months, **zero from
  2023**. REE's rules allow exactly this: contracts between retailers can only
  be nominated after the day-ahead market, once the energy has been bought. From
  2023 the retail units buy directly, which is when `ICLIC01`'s auction bids jump
  (11–143 MWh per hour before, about 5,700 after). An earlier claim here, that
  Iberdrola's contracting "fell from 9–10 GWh per hour to 1–4" in 2023, was this
  pass-through ending, and is **withdrawn**; the net outside inflow runs at about
  3–4 GWh per hour in most sample months.
- **The generation sold to Iberdrola retail is mostly nuclear.** Iberdrola's own
  Cofrentes, Almaraz 2 and Vandellós II supply about 3.5 TWh a year over the
  sample months; then wind (1.1–2.2), the storage hydro traced above (0.5–3.6),
  solar from 2022 (up to 1.1) and cogeneration from 2023 (about 0.3).
- **About 1.5–2 TWh comes from co-owned nuclear registered to Naturgy or Endesa**
  (Almaraz 1, Trillo, Ascó 2). That is Iberdrola's share of plants whose OMIE
  owner is another firm — an artefact of mapping a co-owned plant to a single
  owner, not a third-party purchase. Any firm-level quantity built on the owner
  mapping inherits it.

**Why it matters for the design.** For a vertically integrated firm that
self-supplies, the price incentive in an hour runs through its *net* auction
position: generation sold minus retail demand bought. The descriptive chapter
already bounds Iberdrola as a net day-ahead **buyer** (§4.5 there). A net buyer
gains from a *lower* price, so shifting its own water into the evening
self-supply, and buying less in the auction then, is the direction a net buyer
with market power would choose. (The chapter's evidence for that was the
double-subtracted index; on the correct measure, §3.9, Iberdrola is still a net
buyer in every year.) It is also what a price-taker would do, since
evening prices are higher. Only a benchmark allocation separates the two.

### 3.9 EDP: the auction-route panel, and the first look at the test

`scripts/analysis/edp_hydro_panel.py` → `outputs/tables/edp_hydro_panel.parquet`,
**811,913 unit-periods**, 2018-01-01 → 2026-06-29. EDP's seven storage units
(8.3 GW: the Douro, Lima, Cávado, Guadiana, Mondego and Tejo-Mondego cascades in
Portugal, and Hidrocantábrico's UGH in Spain) plus Movhera's Douro
Internacional and Repsol's Viesgo. Per unit-period it carries the offer shape
(price at 25/50/75% of capacity and of offered volume, steps, price-out share),
cleared volume, the pumping twin's purchase, the unit's own-zone price, the
owner's residual-demand slope, and the owner's net auction position.

**Measurement.**

- **Use offered-volume quantiles, not capacity quantiles, for EDP.** The price
  at 50% of capacity is undefined on 31% of unit-periods, and for whole
  unit-years (Lima 2018–23, Douro from 2022, Hidrocantábrico 2022–25), because
  those units usually offer under half their capacity. The price at 50% of
  offered volume (`o50`) is always defined.
- **Six of EDP's seven units have a pumping twin.** Five by name (`…B`), and
  `TANB` (Tanes bombeo) for Hidrocantábrico's `HCHI` by owner and plant, a hand
  match. Only Tejo-Mondego has none.
- Own-zone price defined on 96.9% of unit-periods (the rest is June 2026, which
  has bids but no prices yet); firm slope on 81.5%.

**What EDP's offers look like.**

- **Flat days vary by unit.** Same set of step prices all day: Guadiana
  0.88–0.94 to 2022, falling to 0.18 in 2025; Cávado 0.13–0.89; Douro 0.19–0.59;
  Hidrocantábrico 0.00 to 2020, then 0.84–1.00 from 2022.
- **Where it varies, it is mostly a smooth tilt, not price-outs.** On non-flat
  unit-days the within-day range of `o50` is under 5 €/MWh on 36–60% of them and
  over 100 €/MWh on at most about 20%. Unlike Iberdrola (§3.6), a continuous
  outcome fits.
- **The midday tilt came and went.** Mean `o50` deviation from the unit-day
  mean, €/MWh: 2018–20 night +6.7, midday −4.9, evening −7.5; 2021–23 night +5,
  midday +1.7 to +3.8, evening −6 to −8; 2024–26 within ±2 everywhere. EDP clears
  least at midday in 2024–26 (−71 to −90 MW against the daily mean, zone price
  6–14 €/MWh) and most in the evening (+139 MW).
- **Pumping moved from night to midday.** Twins' cleared purchases, MW per
  unit-period: 55–64 at 03:00–06:00 in 2018–20; 5–6 at night and 24–34 at
  midday in 2024–26.

**EDP is a net seller overall and a net buyer at midday.** Median net auction
position of all EDP units (EDP Comercial, its Portuguese retailer, included):
+200 to +1,700 MW across the day in 2018–20; since 2021 **negative at midday**
(−207 to −477 MW in 2021–23, −655 to −840 MW in 2024–26) and +400 to +1,450 MW in
the other hours. So X = net / |RD′| is negative at midday and +2 to +7 €/MWh
otherwise. With market power, EDP would want the midday
price *lower*.

**The first look at the test: not identified yet.**

- **On the median offer, EDP looks price-taking.** Within a unit-day, X moves
  about ±20–35 €/MWh across its end deciles while `o50` moves about ±2, slightly
  *negatively* in 2018–23 and not at all in 2024–26. β = 1 would mean swings of
  about ±40. But the median offer is not the object the FOC is about.
- **On price-setting periods, correctly signed and between 0 and 1.** Where an
  EDP unit's top cleared step is the zone price (3.6% of unit-periods; 3,438
  unit-days with 2+ such periods), the offer equals p*, so the FOC reads
  p* = λ_day + X. Within unit-day slopes of p* on X: **0.26** (2018–20), **0.04**
  (2021–23; about 0.13 on quintile bins), **0.26** (2024–26; about 0.5 on bins),
  monotone in every era. (0.32, 0.05, 0.26 on the uncorrected slope; see 3b.)
- **That relation is expected under price-taking too.** A price-taking hydro
  unit sells more in high-price hours, which raises EDP's net position, and so
  X, exactly when p* is high. The positive slope is mechanical until X is
  instrumented. This is the job of the clear-sky instrument (§4); nothing here
  is evidence of conduct yet.

**The midday offer premium of 2021–23 is not EDP market power.** It sits in the
hours where EDP is a net buyer, when market power would push its offers *down*.
It coincides with the shift of pumping to midday, which is the more natural
reading: a cascade that is pumping at noon has little reason to also generate.

### 3.10 The solar instrument: offered solar survives, clear-sky does not

`scripts/build/build_solar_instrument.py` →
`outputs/tables/solar_instrument.parquet`, one row per day-ahead period, three
candidates:

- `z_clear` — clear-sky irradiance (Haurwitz model on its own solar geometry,
  averaged over the four `solar` sites of `fetch_weather.py`) × installed solar
  capacity.
- `z_weather` — ERA5 surface irradiance at the same sites × capacity.
- `z_offered` — solar volume offered in the day-ahead auction by the 1,526
  solar-labelled supply units not owned by EDP. Solar-labelled units clear
  88–96% of REE's realised Spanish solar, so the bids record the D−1 forecast
  directly. Offered, not cleared, because clearing depends on the price.

Checks: the ERA5 stamp is the mean over the preceding hour, tested against the
clear-sky model rather than assumed (correlation 0.907, against 0.83–0.89 for
shifted readings); correlations with realised solar 0.88, 0.92 and 0.95;
capacity proxy — the running maximum of REE's peak solar output plus Portugal's
published installed solar — 6.4 GW (2018) to 31.9 GW (2026), below published
capacity as a peak-output proxy should be.

**First stage** (`scripts/analysis/solar_first_stage.py`): EDP's X on each
instrument, REE demand-forecast control, day or unit-day fixed effects, errors
clustered on date. The trend test swaps hour × calendar-month fixed effects for
hour × year-month, which absorb capacity growth at every hour.

| | all EDP periods, F | | price-setting periods, F | |
|---|---|---|---|---|
| instrument | hour × month | **hour × year-month** | hour × month | **hour × year-month** |
| `z_clear` | 257 | 19.6 | 85 | **3.2** ✗ |
| `z_weather` | 375 | 97 | 103 | 10.0 |
| **`z_offered`** | 587 | **180** (t = −13.4) | 122 | **26.4** (t = −5.1) |

- **`z_clear` identified from the capacity trend** and collapses once it is
  absorbed. Rejected.
- **`z_offered` survives**: day-to-day solar weather moves X. One more GW of
  offered solar lowers X by about 1.1–1.6 €/MWh, the direction expected when
  more solar lowers midday residual demand where EDP is a net buyer. By era, on
  all periods: F = 118, 44, 124. On the price-setting sample: 45, **5.1**
  (2021–23, 2,838 observations — weak), 17.
- **`z_weather` adds nothing once `z_offered` is in**, as expected if the
  bidders' forecast is the channel.

**Exclusion — what remains open.** (1) Heat: controlled with the demand
forecast, not ruled out. (2) `z_offered` is a *bid* quantity; the large
owners' solar offers are partly a choice and may respond to the same price
expectations. Robustness: rebuild it from independent solar owners only. (3)
Within-day solar shape should not move a storage plant's daily water value,
which the day fixed effect absorbs; a daily-cycling reservoir (threat 2) is the
exception.

### 3.11 The second stage: EDP prices its water flat, except its top tranche from 2024

`scripts/analysis/midday_hydro_iv.py`. X instrumented by `z_offered`; unit-day
and hour × year-month fixed effects; REE demand-forecast control; errors
clustered on date; Anderson–Rubin 95% sets in closed form (valid however weak
the instrument; checked against grid inversion). β = 0 is price-taking, β = 1
supply-function Nash. **[preliminary]**

**The price-setting version (§2's original test) is invalid, and is kept on the
record.** On periods where an EDP unit sets the price, 2SLS gives β = **3.6**
(AR [2.52, 5.95]) — outside [0, 1], so the specification is broken, not the
market. Two reasons. **Selection**: the sample keeps only price-setting periods,
and the solar instrument changes which periods those are, so it conditions on
an outcome of the instrument. **Movement along the unit's own stepped curve**:
real — 1 GW more solar lowers the marginal unit's cleared volume by 16 MW
(t = −6.0), and p* rises 0.013 €/MWh per MW of it within a unit-day — but that
explains only about 5% of the −3.95 €/MWh per GW reduced form.

**The test of record: where EDP's offer curve sits at fixed points**, over all
550,883 EDP unit-periods. Demand cutting the curve elsewhere cannot move a fixed
point, and nothing is conditioned on. Offered volume does not move with the
instrument (−0.0002 of capacity per GW, t = −0.7), so the offered-volume points
are not a composition artefact.

| point on the curve | 2SLS β | AR 95% set |
|---|---|---|
| 25% of offered volume | 0.12 | [0.01, 0.23] |
| **50% of offered volume** | **0.08** | **[−0.11, 0.27]** |
| 75% of offered volume | 0.94 | [0.47, 1.45] |
| 25% of capacity (fixed MW) | 0.14 | [−0.24, 0.56] |
| 50% of capacity | −0.05 | [−0.65, 0.54] |
| 75% of capacity | 0.94 | [0.09, 1.82] |

By era, and robustness:

| | 50% of offered | 75% of offered |
|---|---|---|
| 2018–20 | −0.05 [−0.63, 0.54] | −0.07 [−0.53, 0.39] |
| 2021–23 | −0.02 [−0.20, 0.16] | 0.05 [−0.27, 0.37] |
| **2024–26** | 0.11 [−0.16, 0.41] | **1.47 [0.75, 2.28]** |
| independent-owner instrument | 0.10 [−0.10, 0.31] | 1.02 [0.53, 1.56] |
| hour × calendar-month FE | −0.24 [−0.35, −0.13] | 0.48 [0.20, 0.77] |

**What is established, preliminarily.**

- **The bulk of EDP's storage hydro is offered at a flat water value.** At the
  bottom and middle of the curve β ≈ 0 and β = 1 is rejected in every era and
  every specification. The exact value in the middle depends on the fixed
  effects — slightly negative under the calendar-month version that fails the
  trend test — so read it as *rejects Nash*, not as *precisely zero*.
- **From 2024 the top quarter of EDP's offered volume moves with its markup
  term**, roughly one-for-one (β = 1.47, AR [0.75, 2.28]; zero rejected in every
  specification pooled). Nothing like it before 2024. On sunny middays, when
  EDP is a net buyer and X is low, those tranches come in cheaper — the
  direction a net buyer with market power would choose.

**What it cannot yet separate.** EDP's "units" are whole river cascades (Douro,
Lima, Cávado …), each many plants with different reservoirs. The upper tranches
may be the small-storage plants in a cascade, whose water cannot wait — a
competitive within-day water value (threat 2) that would produce the same
pattern. Only plant-level storage separates the two, and the offers are
published per cascade, not per plant. The 2024 onset also coincides with EDP's
pumping having moved to midday (§3.9).

### 3.12 The cascade split: two neighbouring cascades, and a response too large to be a markup

`scripts/analysis/edp_cascade_split.py`: the §3.11 regression one cascade at a
time. Storage per MW is not available — Portugal's reservoir data is
geo-blocked outside Portugal (`email-apa-reservoir-data.md`) — so the storage
measure is a behavioural proxy, **predetermined** (2018–2023, before the
effect): the share of a cascade's daily cleared energy that falls in the day's
8 dearest hours. A plant that cannot shift water scores about 0.33; one that
can, about 1. It ranks the cascades the way their layout suggests: the Douro
main stem, largely run-of-river, low; the Guadiana, behind Alqueva, highest.

Response of the price at 75% of offered volume, 2024–26 (first-stage F 114–124
for every cascade):

| cascade | storage proxy | β | AR 95% set |
|---|---|---|---|
| Hidrocantábrico (ES) | 0.46 | 0.00 | [0.00, 0.00] — its offers do not vary |
| Douro | 0.54 | 1.58 | [−1.05, 4.50] |
| **Tejo-Mondego** | 0.57 | **5.91** | **[2.29, 9.97]** |
| Cávado | 0.74 | −0.03 | [−0.30, 0.25] |
| **Mondego** | 0.79 | **3.77** | **[1.53, 6.09]** |
| Lima | 0.81 | −0.01 | [−0.14, 0.12] |
| Guadiana | 0.92 | −1.06 | [−2.81, 0.60] |

The middle of the curve (price at 50% of offered volume) responds in none of
them at 95%; Tejo-Mondego comes closest (0.84, AR [−0.01, 1.73]).

**What it rules out.**

- **The pooled 2024 result (β ≈ 1.5) is not EDP-wide.** It is an average of
  about zero in five cascades and a large response in two neighbouring ones in
  central Portugal, Tejo-Mondego and Mondego.
- **It is not a markup.** Supply-function Nash puts β at 1 for any unit at the
  margin; a strategic offer cannot move 3.8–5.9 € per € of its own markup term.
  Something specific to those two cascades responds to sunny days directly —
  which is a failure of the exclusion restriction *for those units*, not
  evidence of conduct.
- **Nor is it simply small storage.** The two cascades with the least
  shiftable output — Hidrocantábrico and the Douro — show nothing significant,
  and across the seven the correlation of β with the storage proxy is only
  −0.32 (seven points, a description).

**The likelier reading is local and operational.** Mondego has a pumping twin
(`MONDEGB`, Aguieira), and both cascades share the Mondego/Zêzere system. A
pumping schedule or a flow rule on those rivers that follows the solar profile
would move their upper tranches directly. Not tested; the offers are published
per cascade, not per plant.

**Where this leaves the design, for EDP: no evidence of supply-function market
power in how it offers its storage hydro within the day.** The bulk of the
curve is flat in every cascade and era (§3.11), and the one signal against
that is confined to two cascades and too large to be a markup. Preliminary,
and specific to EDP: Iberdrola, the firm whose break started this line of
work, allocates through self-supply and needs the quantity-based design (2c).

### 3.13 Assumptions A2 and A1: EDP's cascades come in two kinds

`scripts/analysis/water_value_assumptions.py`, testing
[`docs/specs/2026-09-29-water-value-design.md`](../docs/specs/2026-09-29-water-value-design.md)
§5. **[preliminary]**

**A2 — is a fixed point on the curve the same tranche all day?** Each
unit-period's *quantity signature* is its step quantities (≥ 1 MW) in price
order, prices ignored; a unit-day is A2-stable when the signature never changes.

| cascade | A2-stable unit-days | distinct signatures per day, median 2024–26 |
|---|---|---|
| Douro | 0–2% | 16–24 |
| Mondego | 0–15% | 14–24 |
| Tejo-Mondego | 0–8% | 12–14 |
| Lima | 60–95% | 1 |
| Guadiana | 19–94% | 1–4 |
| Cávado | 13–85% | 1–3 |
| Hidrocantábrico | 0–2% to 2021, 84–100% from 2022 | 1 |

**Where A2 holds, the curve does not move at all.** 97.8% of A2-stable unit-days
also keep the same prices all day, so the whole curve is identical hour to hour.
The near-exact zeros on A2-stable days (price at 50% of offered volume 0.013,
AR [−0.02, 0.05]; at 75%, 0.006, [−0.02, 0.03]) are therefore mechanical. The
genuinely informative subsample — fixed tranches, varying prices — is 1.8% of
unit-periods (first-stage F = 10.8): 0.11 [−0.91, 1.32] in the middle,
uninformative; **−0.10 [−0.69, 0.40] at the top, rejecting β = 1**, and the same
for 2024–26 ([−0.58, 0.36]).

**So EDP's within-day behaviour takes two forms, and §3.11 mixes them.**

- **Lima, Guadiana, Cávado — and Hidrocantábrico from 2022 — mostly offer an
  identical curve all day.** That rules out within-day shaping directly, for
  any value of the incentive, without an instrument. It is the strongest EDP
  evidence, and it is descriptive.
- **Douro, Mondego and Tejo-Mondego (about 4 GW, half of EDP's storage hydro)
  reshape their tranche quantities within the day on nearly every day, and far
  more from 2024** (3–8 signatures a day before, 12–24 after). The price at a
  fixed point is not the same tranche across hours there, so **the §3.11 and
  §3.12 estimates are not valid curve-shift tests for these three**. The 2024
  top-tranche signal came from them, and where tranches hold still the top does
  not respond.

**A1 — is the water value constant within the day? Not rejected, on weak
proxies.** Flags for a binding storage bound are rare: forced release (≥ 80% of
capacity in the day's 8 cheapest hours) at most 1.9% of unit-days (Tejo-Mondego),
near-empty (offering < 10% of capacity in half the periods) 25% for
Hidrocantábrico and none elsewhere, turbine at its limit in the dearest hours at
most 3.6% (Lima). Dropping forced-release and near-empty days (4.5% of
unit-periods) changes nothing: 0.08 in the middle, 0.96 at the top, 1.47 at the
top in 2024–26. Without reservoir data per cascade this is a weak test.

**What follows for the design.** Within-day strategy, if EDP has any, lives in
the three reshaping cascades, and the price-at-fixed-point outcome cannot see it
there. The natural outcome is its mirror image: **the quantity offered at or
below a fixed price in each hour** — the supply curve read horizontally. It
needs no A2, and under a constant water value and price-taking it too is flat
within the day.

## 4. Specification (to build)

```
b_ih − b̄_i,d = β · X̃_fh + γ_i,hour-of-day + δ_hour × year-month + ε_ih
X_fh = net_fh / |RD′_fh|,   net = cleared sales − cleared purchases, all the firm's units
tilde = deviation from the firm-day mean
```

- **Outcome.** The offer price at fixed quantiles of *capacity* (p25, p50),
  and at fixed quantiles of *offered* volume. p50 of capacity is censored on
  35–50% of unit-periods, because units offer less than half their capacity.
- **Unit × hour-of-day fixed effects (γ).** They absorb stable hydraulic
  profiles: environmental minimum flows, habitual ramps, cascade coordination.
  After them, β is identified from **day-to-day changes in the shape of the
  day**, not from the average midday-versus-evening contrast.
- **Instrument for X̃: day-ahead offered solar (`z_offered`), with hour ×
  YEAR-month fixed effects — revised 2026-09-28, §3.10.** The first plan was
  the clear-sky profile × installed capacity. Under the fixed effects that is
  almost entirely absorbed, and what survives is capacity *growth* — a trend,
  and a weak exclusion restriction. It fails the trend test (§3.10). The
  instrument that survives is the solar volume offered in the day-ahead auction
  by solar units other than EDP's: the D−1 forecast as bid, so it varies with
  the weather day to day. Hour × year-month fixed effects (not hour × calendar
  month) take out capacity growth at every hour. REE's day-ahead demand
  forecast is a control throughout, because sunny days are hot and heat moves
  prices through demand.
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
3. **Pumped storage: sharpened 2026-09-28.** Pumping alone does *not* break
   the flat benchmark. A competitive pumped-storage plant still offers
   generation at one daily water value λ and pumps whenever the price falls
   below ηλ, so its turbine curve is still flat. What breaks it is a small upper
   reservoir that fills and empties within the day, which makes λ vary by hour —
   threat 2, not a separate threat. This matters for EDP, where six of seven
   units have a pumping twin and pumping moved to midday (§3.9): split them by
   upper-reservoir hours of storage, not by whether they pump. La Muela's
   turbine leg (MUEL) is the extreme case of a daily-cycling plant. The pumping
   bids themselves remain a natural second object.
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
2d. ~~**Check the self-supply inference**~~ — done 2026-09-28/29, §3.8. Cleared
   purchases fall with self-supply, bid volumes do not, and Iberdrola's other
   bilateral contracts close the rest: the retail total position moves by
   −0.15 to +0.14. The other contracts are traced (mostly nuclear; an internal
   pass-through via `IGESC01` until 2022). Still open: the bilateral
   counterparties for Endesa before 2024 and Naturgy from 2022, and co-owned
   nuclear in the owner mapping.
2e. ~~**EDP full-archive panel**~~ — done 2026-09-28, §3.9.
3. ~~**X_fh**~~ — done for EDP, Movhera and Repsol in the panel (§3.9), on the
   net auction position rather than `q − θ`.
3b. ~~**Check EDP's own demand bids near the margin**~~ — done 2026-09-28,
   `own_demand_in_band.py`. The firm panel removes a firm's own *sell* offers
   from the band and maps only supply-role units, so a firm's own demand bids
   were counted as everyone else's. For EDP they are 0.9–7.6% of the band on
   average — its pumping legs, peaking at night in 2018–20 and at midday in
   2021–23 — with no correction in the median period and a 31–45% slope
   overstatement in the worst 10% of periods in 2018–22 (≤ 10% from 2024). X now
   uses the corrected `slope_net`, floored at 5 MW per €/MWh because a band the
   firm's own demand nearly fills produced |X| up to 2.8 × 10⁸ (0.08% of
   periods). Nothing substantive changes (§3.9). **Iberdrola is the firm it
   matters for**: 4–13% of the band, and a slope overstated 2.1–2.5× in its worst
   decile of periods from 2023.
4. **Storage-hours per unit**, from MITECO reservoir capacity. Needs a
   reservoir → OMIE unit match, which is new work.
5. ~~**Clear-sky instrument**, then the first stage~~ — done 2026-09-28, §3.10.
   The clear-sky version is rejected; `z_offered` is the instrument.
5b. ~~**Second stage**~~ — done 2026-09-28, §3.11. The price-setting version is
   invalid (selection); the curve-position version is the test of record.
6. ~~**Separate the 2024 upper-tranche response from small-storage physics**~~
   — (a) done 2026-09-29, §3.12: confined to Tejo-Mondego and Mondego, too
   large to be a markup, not explained by the storage proxy. (b) and (c) are no
   longer needed for the EDP verdict; (c), Mondego's pumping leg, would test
   the local-operational reading if that ever matters.
6b. ~~**A2 and A1**~~ — done 2026-09-29, §3.13. A2 fails for Douro, Mondego and
   Tejo-Mondego; A1 is not rejected on weak proxies.
6c. **Quantity-at-fixed-price test on the three reshaping cascades**: MW offered
   at or below fixed prices (relative to the unit-day's own offer level) by
   hour, on X instrumented. The outcome that does not need A2.
7. **Placebos**: run-of-river units (no daily λ, so they should be flat at about
   €0), and pumping units as the mirror image.
8. **Iberdrola by quantities** (2c). The EDP test is done; the firm whose break
   started this line of work has not been tested at all.
