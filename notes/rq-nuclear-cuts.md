# Nuclear cuts: saving fuel, or holding back output?

Design: `docs/specs/2026-10-19-nuclear-cuts-design.md`. Running note.
Script: `analysis/nuclear_cuts_describe.py` → `outputs/tables/nuclear_cuts_daily.parquet`
(one row per reactor-day), `nuclear_cuts_summary.csv` (every table below). Log:
`.superpowers/sdd/2026-10-19-outage-runs/nuclear_t1.log`.

**In one line (T1, 2026-10-19).** Most of the cut output is cut when the price expected
two days ahead is below even the lowest bound on a reactor's cost. In 2024–2026 that is
49% of partial-cut volume, 60% below the cost with fuel at book value, and 86% below the
upper bound. About 1.5 TWh (14%) is cut above every bound, 0.9 TWh of it in cuts of at
least a tenth of capacity, on about 80 reactor-days. Those days are what the conduct
test (T3) has to explain.

**T2 in one line (2026-10-19).** A price-taker valuing fuel at book cost would cut as much
as the reactors did in 2024–2026 (11.8 TWh against 11.0), but on different days: under
half of the actual cut volume is shared. Reactors cut 4.3 TWh on days expected above that
cost and keep running through 6.5 TWh of cuts the price-taker would make. Valuing fuel at
the end-of-cycle price would mean cutting 3–26 times more than they do, so that bound is
rejected.

**T3 in one line (2026-10-19).** Not answered. The owners' instruments move their stake
only weakly (F < 7), and they are almost always net buyers. In 2024–2026 two instruments
point the market-power way (refuelling elsewhere → fewer cuts; own wind above the
national rate → more cuts), but by 2–4 times what full market power implies (§6). Split by operator (§6.1),
refuelling at another operator's reactor matters as much as the same operator's, so it is
not operator fleet management. Its size, about 14 times full market power, says it is not
the price stake either: owners seem to keep their remaining nuclear running for their own
retail. The slope test (§6.2) confirms it: the cut follows the lost output,
not how much that loss moves the price, and full market power is rejected (p ≈ 0.01).

## 1. Definitions

- **Cut** = the reactor-hour's lost output that no declaration covers, plus declared
  flexible operation. Reactor-days with any other declared loss (refuelling, faults,
  weather, ramps) are left out: 63,846 of 516,257 reactor-hours.
- **Partial** cut: the reactor is scheduled above 0 at some hour of the day. **Whole
  stop**: scheduled at 0 all day.
- **Expected price** for day D: OMIP's Spanish base-load price for D (finest contract),
  on the latest trade date ≤ D − 2, so it is known before offers close at noon on D − 1.
- **Cost bounds, provisional** (rates from press and industry sources, *to verify*;
  design §3): c_lo = (Enresa fee + spent-fuel tax 5.4 + regional tax) / (1 − IVPEE);
  c_acct = c_lo + 6 €/MWh fuel; c_hi = max(c_acct, expected price in the 30 days before
  the reactor's next refuelling). Means: c_lo 17–22, c_acct 23–28, c_hi 42–167 €/MWh
  (it follows the forward curve: 167 in 2022).

## 2. How much, and in what form

| year | partial, TWh | whole stops, TWh (on register-gap days) |
|---|---|---|
| 2018–2023 | 0.6–1.6 a year | 0–0.19 (nearly all) |
| 2024 | 4.66 | 2.68 (2.22) |
| 2025 | 3.34 | 2.37 (1.50) |
| 2026, to May | 2.95 | 2.50 (2.50) |

- **Whole stops are mostly on days the outage register (`indisp`) has no snapshot for**,
  so they may be outages the register missed. They stay out of the main sample, as the
  design says.
- **By reactor, 2024–2026**, the partial cut is 3–43% of capacity a year. Ascó 1 cut the
  most (29% in 2024, 43% in 2026 to May); Almaraz 2 cut little until 2026.
- **Spring and Sundays.** Share of capacity cut, 2024–2026: April 25%, March 18%, May 16%,
  February 11%, July–January 3%. Sunday 12.6% against 7.5–9.6% on other days.
- **It follows the D-1 renewable forecast.** By decile of REE's (wind + solar) / demand
  forecast for the day, 2024–2026: 0.7–3% cut in the bottom three deciles, 11% in the
  ninth, 18% in the top. In 2019–2023 the top decile cut 5.6%, the others 1–3%.

**Two ways of cutting, by operator** (2024–2026, mean MW per reactor, cut days against
full days):

| reactor | bilateral, full → cut | auction schedule, full → cut | offered on cut days at a reservation price / prohibitive price |
|---|---|---|---|
| Almaraz 1 (CNAT) | 776 → 619 | 226 → 261 | 25 / 23 |
| Almaraz 2 (CNAT) | 781 → 573 | 215 → 269 | 62 / 31 |
| Trillo (CNAT) | 849 → 298 | 138 → 361 | 22 / 230 |
| Cofrentes (Iberdrola) | 934 → 599 | 121 → 195 | 18 / 122 |
| Ascó 1 (ANAV) | 30 → 121 | 974 → 794 | 294 / 25 |
| Ascó 2 (ANAV) | 264 → 94 | 725 → 755 | 442 / 24 |
| Vandellós II (ANAV) | 267 → 190 | 773 → 676 | 334 / 31 |

- **The Iberdrola-run reactors cut through the bilateral leg.** At Almaraz, Trillo and
  Cofrentes the bilateral schedule to the co-owners' retailers falls. Part of that energy
  moves into the auction, some of it offered at a prohibitive price (€250–427) and not
  accepted, and the rest is not offered at all. A quantity decision, taken the day before.
- **The Endesa-run reactors cut through a reservation price.** At Ascó and Vandellós the
  cut capacity is offered in the auction at a price, and accepted when the price is
  above it.
- **The €200 cut-off is clean.** Of all MW reactors offered above €0 (2023–2026), 82% are
  at €20–40, 4% below €20, 1.5% at €40–200 and 12% above €300.

**Reservation prices** (MW-weighted median on days offering one):

| | 2018–2021 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| Ascó 1, Ascó 2, Vandellós II (ANAV) | 98–150 | 45–180 | 35 | 18–35 | 35 |
| Almaraz 1 and 2, Trillo (CNAT) | 18–180, few days | 18–23 | 22–23 | 23–44 | 23–28 |
| Cofrentes | 20–180, few days | 30 | 20.5 | 52.6 | — |

- Before 2022 ANAV offered a small top step at €98–150 on most days; that is not a cut.
- **From 2024 ANAV's reservation price is €35 almost every day**, and CNAT's €22–23. Next
  to the provisional cost bounds (c_lo 23 and c_acct 30 for the Catalan reactors,
  c_lo 22 and c_acct 29 for Almaraz), CNAT's price sits at the fees and taxes, with fuel
  worth about nothing. ANAV's sits about €5 above fees, taxes and book fuel.
- **A reservation price that is the same every day cannot follow the owner's position
  from day to day.** For Endesa's reactors, market power could only show in the level of
  the €35 or in its occasional changes, not in a day-by-day slope. CNAT's quantity cuts
  could follow it.

## 3. At what prices

Share of capacity cut, partial days, by the expected daily price:

| expected price, €/MWh | <10 | 10–20 | 20–30 | 30–40 | 40–50 | 50–70 | ≥70 |
|---|---|---|---|---|---|---|---|
| 2018–2023 | 26.5% | 9.4% | 3.2% | 1.6% | 1.1% | 1.1% | 1.9% |
| 2024–2026 | 33.3% | 32.9% | 22.2% | 10.4% | 7.4% | 3.1% | 2.3% |

The realised price gives the same pattern. **From 2024 the cut rate at €10–30 has tripled
to sevenfold**; at €50 and above it stays at 2–3%.

Partial-cut volume against the provisional cost bounds, 2024–2026 (10.9 TWh):

| expected price | TWh | share |
|---|---|---|
| below c_lo (fees and taxes, fuel worth 0) | 5.36 | 49% |
| c_lo to c_acct (fuel at book value) | 1.17 | 11% |
| c_acct to c_hi (fuel worth the end-of-cycle price) | 2.89 | 26% |
| above c_hi | 1.53 | 14% |

- **Below c_lo is efficient under any reading of the fuel's value.** So is below c_acct
  unless saved fuel is worth less than its book cost.
- **Between c_acct and c_hi, efficiency depends on what the saved fuel is worth.** If
  fuel not burned in spring lets the reactor run longer at the end of its cycle, the cut
  saves it for a higher price. If the refuelling date is fixed and the fuel is carried
  into the next core, it is worth about its book cost and the cut loses money.
- **Above c_hi: 1.53 TWh.** 0.61 TWh of it is cuts under a tenth of capacity, which may
  be the `cab` max power overstating what a reactor can run at (summer derates, a few
  per cent). The other 0.93 TWh is about 80 reactor-days at 10% of capacity or more,
  spread over all reactors (1–16 days each) and months. **These are the candidates.**
- In 2018–2023, 1.3 TWh of the 1.8 TWh above c_hi is cuts under a tenth of capacity.

## 4. What this means for T2–T3

- **Most cuts look efficient on their face.** Half the volume needs no fuel value at all
  to be efficient; another 37% needs the fuel to be worth between its book cost and the
  end-of-cycle price.
- **The test has a narrow target.** If market power drives cuts, it should show in two
  places: in the c_acct-to-c_hi band, where the efficient story needs a particular fuel
  value, and on the 80 above-c_hi days. And it should come through CNAT's quantity cuts,
  since ANAV's €35 does not move day to day.
- **The cost rates are provisional.** Everything in §3 that compares with c_lo or c_acct
  needs the official rates (BOE, regional gazettes) before it is quoted. The price-bin
  tables do not depend on them.
- **Not yet done:** T3 (the conduct test), T4 (whose position).

## 5. T2: what a price-taking reactor would cut (2026-10-19)

`analysis/nuclear_cuts_benchmark.py` → `nuclear_cuts_benchmark_daily.parquet`,
`nuclear_cuts_benchmark.csv`; log `.superpowers/sdd/2026-10-19-outage-runs/nuclear_t2.log`.

**The rule, by example.** Almaraz 1's cost with fuel at book value (c_acct) is about
€29 in 2025. If OMIP expects €25 for tomorrow, a price-taker goes down to Almaraz 1's
minimum load (52% of capacity), at most 36% of capacity a day. If OMIP expects €40, it
runs in full. Then compare that with what Almaraz 1 did. The rule looks one day ahead
(myopic).

**Limits, from each reactor's own record** (2018–2026): minimum load (2nd percentile of
hourly schedule on its partial-cut hours) 0.24–0.67 of capacity, Almaraz 1 0.52, Trillo
0.39, Cofrentes 0.41, Ascó 1 0.67; daily ramp (95th percentile of its moves) 0.36–0.44
of capacity at CNAT and Cofrentes, 0.73–0.82 at ANAV.

**2024–2026, TWh** (actual 10.95):

| price-taker's cost | price-taker cuts | both cut (share of actual) | actual only (excess) | price-taker only (missing) |
|---|---|---|---|---|
| c_lo (fuel worth 0) | 8.98 | 4.13 (38%) | 6.82 | 4.85 |
| **c_acct (fuel at book value)** | **11.77** | **5.04 (46%)** | **5.91** | **6.73** |
| c_hi (fuel worth the end-of-cycle price) | 36.88 | 7.49 (68%) | 3.46 | 29.40 |

- **At book-value fuel, a price-taker cuts as much as the reactors do**: 11.8 TWh against
  11.0, and year by year 4.9 / 3.8 / 3.0 against 4.7 / 3.3 / 3.0. The jump in cuts from
  2024 is what price-taking predicts once prices fall to those levels.
- **But on different days.** Under half of the actual cut volume falls where the
  price-taker cuts too. Daily correlation 0.44 (2018–2023: 0.28). Of the 2024–2026 days
  with a cut of at least a tenth of capacity, both cut on 480; the reactors alone on 276;
  the price-taker alone on 440.
- **The end-of-cycle fuel value is rejected by the reactors' own behaviour.** Had the
  fuel been worth the end-of-cycle forward price, a price-taker would cut 3–26 times what
  they cut, every year (2019: 24.4 TWh against 0.9). The reactors act as if saved fuel is
  worth about its book cost, which fits the reservation prices of §2 (€22–35).
- **2020 is the one year the price-taker cuts far more** (6.4 TWh against 1.4 at c_acct):
  the reactors kept running through the spring 2020 price collapse. The limits are pooled
  over 2018–2026 and come mostly from 2024–2026; reactors may simply have been less
  flexible then (flexible operation is first declared in 2025).

**Where the two disagree** (2024–2026, at c_acct):

| expected price minus c_acct | actual cut | price-taker | excess | missing |
|---|---|---|---|---|
| below −€5 | 5.66 | 9.43 | 1.38 | 5.16 |
| −€5 to 0 | 0.88 | 2.05 | 0.17 | 1.34 |
| €0 to +10 | 1.30 | 0.12 | 1.27 | 0.08 |
| above +€10 | 3.11 | 0.18 | 3.08 | 0.15 |

- **Excess:** 4.3 TWh is cut on days expected above book cost, 2.1 TWh of it more than €20
  above. A price-taker would have run in full.
- **Missing:** 6.5 TWh is not cut on days expected below book cost. A price-taker would
  have cut.
- **By reactor:** Ascó 1 carries 2.3 TWh of the excess (its €35 reservation price lets the
  auction cut it hour by hour on days whose average is above €30). Trillo's cuts fit best
  (74% shared).

**Check, hour by hour on realised prices, no ramp limit** (an upper bound on how much
price-taking flexibility can explain, since realised prices are moved by the cuts): at
c_acct the shared share is 47–52% in 2024–2026, the same as the daily rule. At c_hi it
is 57–63%.

**What T2 leaves for T3.** The misfit runs both ways: reactors cut on days a price-taker
would run, and run on days it would cut. That is exactly what the market-power story
predicts, if the sign follows the owner's position:
- a large net seller gains from a higher price, so it cuts more than the price-taker
  (excess);
- a net buyer gains from a lower price, so it keeps running below cost (missing).

**T3's outcome is therefore the deviation from the price-taker**, actual minus simulated
cut at c_acct. The test is whether it rises with n_full / |RD′|, reactor × month effects,
instrumented. Technical limits and contracts can produce both kinds of misfit too, but
they have no reason to follow the owner's position.

## 6. T3: does the departure from price-taking follow the owners' stake? (2026-10-19)

`analysis/nuclear_cuts_conduct.py` → `nuclear_cuts_conduct_panel.parquet`,
`nuclear_cuts_conduct.csv`; log `.superpowers/sdd/2026-10-19-outage-runs/nuclear_t3.log`.

**In one line.** Not answered. The instruments barely move the owners' X at the
reactor-day level (F 0.1–6.4). Two of them point the market-power way in 2024–2026, but
by 2–4 times what full market power (β = 1) implies. The strongest signal, the owners'
other reactors' refuelling, has a plausible reason that is not the price stake.

**Set-up.** 16,326 reactor-days, 2019-01 → 2026-05. Outcome: actual cut minus the
c_acct price-taker's (T2), MW. Regressor: the owners' n_full / |RD′|, share-weighted,
€/MWh. Reactor × month and day-of-week effects, week clusters. Instruments: the owners'
shares of other reactors' unplanned (Z_unpl) and planned (Z_plan) outages, same site
excluded; their regional wind deviation (Z_wind); their 30-day catchment rain (Z_rain).

**The owners are almost always net buyers.** Days following a week in which the
reactor's owners were net sellers: Cofrentes 31%, Trillo 10%, Almaraz 2%, Ascó and
Vandellós 0–0.3%. Mean X is negative for every reactor (−2 to −11 €/MWh). So the sign
test has almost nothing to work with, and a market-power reading of T2's "missing" cuts
(running below cost to keep the price down) cannot be told apart from inflexibility.

| specification | first-stage F | γ, MW per €/MWh (se) | AR 95% set | AR p(γ = 0) |
|---|---|---|---|---|
| all four, 2019–2026 | 2.8 | +3.0 (4.7) | [23.5, 76.5] | 0.003 |
| outages | 3.4 | +22.8 (12.4) | [5.2, 382] | 0.005 |
| regional wind | 0.1 | −16.8 (62.3) | everything | 0.20 |
| rain | 3.1 | −11.7 (9.0) | (−∞, 0] ∪ [106, ∞) | 0.05 |
| with p_exp as control | 3.0 | +5.6 (4.9) | [4.2, 69.5] | 0.03 |
| all four, 2024–2026 | 3.7 | **+14.3 (6.0)** | [10.5, 62.2] | 0.003 |
| regional wind, 2024–2026 | 6.4 | **+15.2 (8.0)** | [2.8, 64.8] | 0.02 |

Least squares: +0.01 (0.02); 2024–2026 +0.39 (0.32). Selling-week days against buying-week
days, no instrument: +5.5 MW (se 10.3). Sign test: sellers −0.9 (5.9, F 2.7), buyers
+4.9 (4.7, F 1.7). Null band (price-takers with cost c_acct + δ + ε, δ = −5, 0, +5,
ε ~ N(0, 5), five seeds): γ from −1.3 to +2.6.

**What drives the rejections** (reduced forms, dev on each instrument; first stage X):

| | 2019–2026 | 2024–2026 |
|---|---|---|
| other reactors' planned outages, per GW | dev **−50 MW (18)**; X −2.2 (0.9) | dev **−124 MW (33)**; X −1.8 (1.3) |
| own regional wind, per GW | dev +31 (25); X −1.9 (6.7) | dev **+137 (58)**; X **+9.0 (3.6)** |
| other reactors' unplanned outages | nothing | nothing |
| rain | dev −1.4 (0.7); X +0.12 (0.07) | nothing |

- **When the owners' other reactors are refuelling, this reactor cuts less than a
  price-taker would.** In 2024–2026 that is 124 MW less per GW of refuelling. The owners
  are then shorter, so a market-power owner should want the price lower and cut less.
  The sign fits. But an operator that avoids cutting while a sister reactor is down (for
  staff, grid or contract cover) produces the same pattern without any price motive.
- **When the owners' own wind blows above the national rate, the reactor cuts more**
  (2024–2026: +137 MW per GW). The owners are then longer and gain more from a higher
  price. The sign fits again, from an independent source.
- **The size does not fit.** On the price-taker's own scale, Nash (β = 1) implies a γ
  equal to the price-taker's response to its cost: 1.5 MW per €/MWh over 2019–2026, 3.3
  in 2024–2026 (linear, same effects). The estimates imply β ≈ 2 (2019–2026, se 3) and
  β ≈ 4.4 (2024–2026, se 1.8; regional wind alone 4.7, se 2.5). That is more than full
  market power, which is not believable as conduct. So either the instruments reach the
  cut other than through X, or X mismeasures the stake the decision responds to.
- **The AR sets lie away from the 2SLS estimates.** With four weak instruments that
  disagree, the AR test rejects most values: the instruments do not tell one story.

**What would separate the stories.** Split the refuelling instrument by operator.
Almaraz's owners also own Trillo (same operator, CNAT) and Cofrentes or Vandellós (other
operators). If a sister reactor's refuelling matters only when the same operator runs
it, that is fleet management. If it matters in proportion to its effect on the owners'
position, whoever runs it, that is the price stake.

### 6.1 Refuelling elsewhere, by who runs the other reactor (2026-10-19)

`nuclear_cuts_conduct.py --operator-split` → `nuclear_cuts_operator_split.csv`; log
`nuclear_t3_opsplit.log`. The owners' planned-outage dose split three ways: the same
operator at another site (Trillo for Almaraz, Vandellós for Ascó, and back), another
operator, and the reactor's own site (Almaraz 1 for 2, Ascó 1 for 2; a check, outside the
instruments). Shares of reactor-days with a dose: 10.5%, 29.6%, 4.9%. Cofrentes has no
same-operator reactor.

**Reduced forms, per GW of the owners' dose**, jointly with the other instruments
(dev in MW; X in €/MWh):

| sample | same site | same operator, other site | other operator |
|---|---|---|---|
| all, 2019–2026 | dev −33 (23); X −3.7 (1.2) | dev **−44 (18)**; X −1.5 (1.2) | dev **−55 (22)**; X **−2.7 (1.0)** |
| all, 2024–2026 | dev +37 (91); X −4.9 (1.6) | dev **−156 (43)**; X −3.3 (1.5) | dev **−108 (44)**; X −1.2 (1.4) |
| CNAT reactors | dev **−114 (33)**; X −6.3 (1.6) | dev **−161 (45)**; X −5.2 (2.1) | dev −1 (20); X −1.0 (1.3) |
| ANAV reactors | dev +3 (28); X −2.5 (1.7) | dev −16 (19); X −0.8 (1.4) | dev −65 (54); X −2.7 (1.4) |

IV on the other-operator dose alone, 2019–2026: F 7.5, γ +21.0 (11.8), AR [4.2, 86.0].

- **It is not operator fleet management alone.** Pooled, refuelling at another operator's
  reactor lowers the cut as much as refuelling at the same operator's, and the two move
  dev in about the same proportion to X (ratios +21 and +30). An owner whose nuclear
  output is partly down keeps its other reactors running, whoever runs them.
- **For CNAT's reactors only CNAT's own refuelling shows**, but other operators'
  refuelling barely moves the CNAT owners' X there (−1.0, se 1.3), so CNAT cannot tell
  the two stories apart. ANAV shows nothing.
- **It is not the price stake at the size X measures.** On the price-taker's scale
  (1.5 MW per €/MWh over 2019–2026), the other-operator IV implies β ≈ 14, fourteen times
  full market power. A refuelling that lowers the owners' X by 2.7 €/MWh would, under
  Nash, reduce the cut by about 4 MW; it reduces it by 55 MW.
- **Reading.** Reactors cut less when their owners' other nuclear output is down. The
  owner seems to keep physical supply for its own retail (the cuts come out of the
  bilateral leg, §2), rather than to move the price. Market power for a net buyer
  predicts the same sign. The two differ in one thing: the price motive should be
  stronger when residual demand is steep, so that each MW moves the price more, and a
  supply motive should not depend on that.

### 6.2 Supply or price? The slope test (2026-10-19)

`nuclear_cuts_conduct.py --slope-test` (on the stored T3 panel) → `nuclear_cuts_slope_test.csv`;
log `nuclear_t3_slope.log`.

**The idea, by example.** Trillo goes down for refuelling and Almaraz's owners lose 0.4 GW
of output. On a flat day (rivals offer a lot near the price) that loss barely moves the
price they face; on a steep day it moves it a lot. If Almaraz cuts less because its owners
want a lower price, it should cut much less on steep days. If it cuts less because they
want the electricity for their own customers, steep or flat makes no difference.

**Terms.** Z = the owners' dose of other reactors' refuelling, GW. P = 1000 Z / |RD′|, the
same dose as a move along the owners' residual demand, €/MWh (mean 2.7 on dosed days,
quartiles 0.6, 1.6, 3.7). Each outcome on Z and P, with 1/|RD′|, the other instruments,
reactor × month and day-of-week effects, week clusters.

| outcome (2019–2026) | on Z, per GW | on P, per €/MWh |
|---|---|---|
| owners' n_full, GW | **−0.83 (0.08)** | +0.01 (0.01) |
| owners' X, €/MWh | +3.1 (1.4) | **−0.92 (0.21)** |
| dev, MW | **−70 (24)** | +3.1 (1.8) |
| dev, cut opportunity controlled | −27 (14) | +0.3 (0.6) |
| dev, days the price-taker cuts | **−155 (59)** | +10.0 (3.2) |

- **The stake behaves as the formula says.** The lost output reaches the owners' n one
  for one, steep or flat (−0.83). Their X moves through P (−0.92 per €/MWh, against −0.86
  from the formula).
- **The cut does not follow the stake.** A price motive makes dev = γ X, so dev should load
  on Z and P as X does: positive on Z, negative on P. It loads the other way on both: it
  follows the lost output (Z), and if anything it falls a little *less* on steep days.
  With the cut opportunity controlled (the dose can only remove a cut on a day the
  price-taker would cut), P is +0.3 (0.6). At Nash it should be about −1.4 (γ 1.5 × −0.92),
  **rejected, p ≈ 0.01**.
- **Same for both kinds of operator**: same operator Z −58 (29), P +2.7 (3.3); other
  operator Z −76 (28), P +3.3 (1.9).
- **2024–2026 is less precise and points the same way**: dev Z −220 (49), P +15.1 (5.1);
  with the cut opportunity controlled Z −66 (44), P +1.8 (3.0), where Nash would be about
  −2.3 (not rejected, p 0.17). The owners' X is imprecise there (P −0.71, se 1.12).
- **One caution.** A steep day is also a tight one. The cut-opportunity controls take out
  the price-taker's cut and the expected margin, but not everything that comes with
  tightness.

**Where T3 ends.** A reactor's departure from price-taking follows the physical state of
its owners' nuclear fleet, not their price stake. When part of an owner's nuclear output
is down, its other reactors cut less, whoever operates them, by an amount tied to the lost
output and not to how much that loss moves the price. Full market power on the quantity
margin is rejected over 2019–2026. Together with T2, where a price-taker cuts about as
much in total, **the nuclear cuts show no market power that this design can detect**. They
look like price-taking at a book-value fuel cost, plus a supply rule: keep the owners'
own customers covered.
