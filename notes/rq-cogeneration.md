# Cogeneration as a fourth technology (running note)

Design: [`docs/specs/2026-11-10-cogeneration-design.md`](../docs/specs/2026-11-10-cogeneration-design.md). Sources for
the legal dates: [`docs/cogeneration-sources.md`](../docs/cogeneration-sources.md). Branch `industrial-demand`.

**The idea in one example.** A paper mill's gas engine sells power and its waste heat dries the paper. Its cost is
the gas it burns minus the boiler gas the heat saves. On 15 June 2022 the gas cap lowered the power price; combined
cycles were paid a subsidy, cogeneration inside the regulated payment scheme was not, so engines stopped. From
1 October 2022 they could give up the scheme and claim the subsidy, and they restarted. The response identifies the
engine's net cost, which contains the factory's own demand for heat.

## Step 0 result (2026-11-10): built and counted, nothing estimated

Built: `data/omie/registry/cogeneration_units.parquet` (1,313 units), `outputs/tables/cogeneration_panel/`
(569,425 unit-days, 2019-01 → 2023-12), tables `outputs/tables/cogeneration_describe_*.csv`. Both check scripts pass.

**The event is in the data.** Mean scheduled MW (PDBF):

| | non-renewable thermal | renewable thermal |
|---|---|---|
| 2022-03 | 3,554 | 599 |
| 2022-06 | ~2,670 | 613 |
| 2022-09 | 1,386 (+42 in units new after the cap) | 557 |
| 2023-02 | ~2,780 (+273) | 570 |

28 non-renewable units start in October 2022 and 15 in November, against 1–6 a month before.

**Gate G0 fails: fuel is known for 12.9% of non-renewable capacity (needs 60%).** Of 289 non-renewable units
offering in January 2022 (7,236 MW), 90 match a plant in REE's register, 526 MW of it gas. Most units are
representatives' numbered units ("AXPO VENTA R. ESPECIAL 369") whose description names no plant. Matches by rule:
OMIE code = REE code 502 MW, the description names REE's programming unit 153 MW, name and capacity 151 MW,
representative and capacity 130 MW (the weakest). By the spec's rule, **E2 (the run decision) and E3 (pass-through
into offers) are not run on OMIE units**; E1 can run on OMIE's label alone.

**Gate G5 is just missed: 96 non-portfolio non-renewable units have 10 or more run/stop switches in 2022 (needs
100)**, 11 of them matched to gas. Run and stop spells under two days are 29.8% of spells, so the daily frequency
is not obviously wrong.

**Few units state a reservation price.** The share of units offering most of their MW above €1/MWh is 8–21% for
non-renewable units of unknown fuel, 10–40% for those matched to gas (rising to 40% in 2022H2), 2–19% for renewable.
Most cogeneration offers at zero and takes the price. E3 would rest on a few dozen units.

**Links from new units to old ones are thin: 7 of 104.** Units new after the cap carry code-like names ("DTVD019"),
so a plant that left a portfolio for its own unit cannot be followed in OMIE's data.

**No public list of units in the mechanism was found**; registration went through REE's customer portal.

**The April 2022 fall has a suspect.** Real Decreto-ley 6/2022 (29 March 2022) brought the update of the scheme's
payment forward to 1 January 2022 and announced a new method for the operating payment of gas-dependent plants; the
values came only in December 2022. Read from summaries, not yet from the BOE text; the December orders' tables are
not read, so the payment per plant type is still unknown.

## A better unit of observation: REE's programming units

REE's daily workbooks (I90DIA, `data/esios/i90/i90_sample_hourly.parquet`, the 15th of each month) give the final
schedule (P48) per REE programming unit. For cogeneration that unit is the plant (324 units for 357 gas plants), and
REE's register gives its fuel. On the sampled days:

| day | gas cogeneration, MW (units running) | biomass and waste | oil and coal derivatives |
|---|---|---|---|
| 2021-11-15 | 2,148 (157) | 796 | 313 |
| 2022-03-15 | 2,101 (150) | 833 | 340 |
| 2022-04-15 | 1,465 (107) | 841 | 272 |
| 2022-06-15 | 1,579 (127) | 718 | 225 |
| 2022-08-15 | 749 (54) | 652 | 114 |
| 2022-09-15 | 640 (62) | 696 | 175 |
| 2022-11-15 | 1,591 (146) | 646 | 148 |
| 2023-02-15 | 2,161 (184) | 715 | 171 |

Gas programming units first seen: 1–2 a month through September 2022, **20 in October, 12 in November**, 11 in
February 2023. So fuel, plant-level output and entry are all there, where OMIE's units give 13%.

Caveats, not yet checked: the register is a 2026 snapshot, so a plant that changed programming unit after the cap
appears under its new code and its earlier output sits under a code the snapshot may not list (gas cogeneration in
the sample is 2,100–2,250 MW before the cap, against about 3,550 MW of non-renewable schedule in OMIE); one day a
month is too thin for any estimate; offers are not in these workbooks, so E3 would stay with OMIE's units.

**Fetched 2026-11-10/11** (user's go-ahead): every day 2022-04-01 → 2023-03-31, 365 workbooks, 2.0 GB, no bad
answer. `build/build_cogeneration_ree_panel.py` → `outputs/tables/cogeneration_ree/` (one row per programming unit
and day: final schedule P48, day-ahead schedule PDBF, of which bilateral; and a unit table with fuel).
`analysis/cogeneration_ree_describe.py` → `outputs/tables/cogeneration_ree_*.csv`. Counts only:

- **The break is on the day.** Gas cogeneration's final schedule, average MW: 1,875 (Mon 13 June 2022), 1,960 (14),
  **1,579 (15, the cap's first day)**, 1,485, 1,423, 1,182, 1,119 (Sun 19), then 1,050–1,250. Units running (above
  10% of their largest day): 136 → 113 → 81. 14 days before against after: 1,838 → 1,219 MW. Biomass and waste:
  721 → 771. Other fossil cogeneration falls with gas (241 → 162).
- **The return starts on the first working day of October.** 921 MW (Fri 30 Sept), 834 and 902 over the weekend,
  1,140 (Mon 3 Oct), 1,287, 1,305; units running 69 → 99 → 109. A second step on 30 January – 2 February 2023
  (1,245 → 2,038 MW, 108 → 174 units), not yet explained (the 2023 operating-payment values are a candidate).
- **Before the cap:** 2,101 MW on 15 March 2022, 2,017 on 1 April, 1,589 on 11 April; April averages 1,696. The
  fall after RDL 6/2022 (29 March) is real and precedes the cap.
- **The plants keep their unit.** Gas units first seen in the daily window: 26 in October 2022 (159 MW), 13 in
  November (40 MW), 7 in January 2023 (54 MW). So the October return (about +400 MW in two weeks) is mostly the same
  units restarting, and a plant can be followed through both dates. OMIE's new offer units are a market-side
  re-registration that REE's units mostly do not share.
- **Enough switching.** 231 gas units in the daily window; 165 (2,265 MW) have at least 10 run/stop switches, median
  17, 4 never stop. Gate G5 (100 units) passes on REE's units; it failed on OMIE's (96, 11 with fuel).
- **Coverage.** REE's gas plus other-fossil cogeneration units are 0.58–0.76 of OMIE's non-renewable thermal schedule
  month by month (0.61–0.66 in June–October 2022), so the ratio is stable through the event. The rest is plants whose
  2022 unit is not in the 2026 register (1,074 units in the window have no register entry, mostly purchase units)
  or whose register technology is not a cogeneration fuel. Not yet traced.
- Weekday pattern: 1,400–1,420 MW Tuesday–Thursday against 1,246 on Sundays; any daily comparison needs day of week.

Still open: offers are not in these workbooks; the regulated payment per plant; which plants were inside the
regulated scheme (excluded from the cap until October) and which outside it (eligible from 15 June).

## E1, the event by group (2026-11-11): the June fall is large and on the day; gate G1 fails as written

`analysis/cogeneration_event.py` → `outputs/tables/cogeneration_event_{estimates,weekly,placebo,dropping}.csv`.
Load factor (0–1) on unit and date effects and treated × after, balanced unit × day grid, capacity-weighted,
standard errors clustered by unit. Run with the user's go-ahead.

| data | treated against comparison | window | estimate (se) | comparison's change ÷ treated's (G3 < 0.20) |
|---|---|---|---|---|
| REE plants | gas against biomass and waste | cap, 1 Apr–31 Jul, break 15 Jun | **−0.219 (0.038)** | 0.02 |
| REE plants | same | cap, short: 15 May–15 Jul | −0.243 (0.043) | 0.09 |
| REE plants | other fossil against biomass and waste | cap | −0.200 (0.059) | 0.02 |
| OMIE units | non-renewable against renewable thermal | cap | −0.160 (0.026) | 0.08 |
| REE plants | gas against biomass and waste | opt-in, 1 Jul–31 Dec, break 1 Oct | +0.085 (0.044) | 0.23 |
| OMIE units | non-renewable against renewable thermal | opt-in | +0.080 (0.030) | 1.38 |

- **June.** Gas cogeneration's load factor was 0.58 before; it falls 0.22, or 38%, against a comparison group that
  does not move (−0.003). 160 gas plants (3,011 MW), 92 biomass and waste (1,285 MW). By week the gap is flat for the
  seven weeks before (within 0.05 of the last week) and −0.20, −0.31, −0.30 in the three weeks from 15 June. Weeks −9
  and −8 (Easter and the April fall) sit 0.14–0.21 lower, which is why the short window is reported.
- **G3 passes in June** (0.02) and **G4 passes** (dropping each of the five largest plants and three largest agents:
  −0.229 to −0.214).
- **G1 fails as written.** On OMIE's label, the same window shape placed on the 15th of each month 2019-04 → 2022-01
  gives 34 placebo breaks; 11 exceed one third of the real one, the largest 0.78 of it (January 2021). They are
  seasonal: industrial cogeneration stops at Christmas, Easter and in August and biomass does not. The three June
  placebos are 0.17, 0.31 and 0.33 of the real break. The real break (−0.160) is larger in size than every one of
  the 34 placebos (largest 0.125), so it is not ordinary variation, but the gate set in advance was one third and
  the spec's stop rule applies: E1 stands as description, not as a clean causal estimate, unless the gate is
  restated (for example against same-season placebos or after removing each unit's calendar pattern from 2019–2021),
  which is the user's decision.
- **October is not identified by this comparison.** Biomass and waste jumps on 1 October too (load factor 0.44 →
  0.55 in a week, gas 0.30 → 0.37), so the gap does not move at the break (−0.03 in week 0) and only widens in
  weeks 5–7 (November). G3 fails (0.23 on REE, 1.38 on OMIE) and G1 fails (22 of 33 placebos above one third).
  Something common to both groups changes on 1 October; not identified yet.

**G1 restated with the calendar pattern removed (2026-11-11, user's go-ahead): it still fails, and by more.** Each
break, real or placebo, net of the same break on the same calendar dates in other years
(`cogeneration_event_placebo_seasonal.csv`):

| cap window, OMIE's label | real break | placebos | placebo sd | above one third of real | as large as real |
|---|---|---|---|---|---|
| raw | −0.160 | 34 | 0.052 | 11 | 0 |
| net of the other years of 2019–2021 | −0.168 | 34 | 0.077 | 19 | 2 |
| net of the year before | −0.187 | 22 | 0.088 | 12 | 0 |

The placebo breaks are not a repeating calendar pattern: the same date has opposite signs in different years
(15 June: −0.05 in 2019, +0.05 in 2020, +0.03 in 2021; 15 January: −0.06 in 2020, +0.13 in 2021), so subtracting
other years adds their noise. The gap between non-renewable and renewable thermal drifts by ±0.05–0.10 over a few
months in ordinary times, which is what the cost framework predicts when gas and power prices move (2019 gas glut,
2020 lockdown, 2021 gas rise). A four-month before/after comparison cannot separate the cap from that drift at the
one-third standard. What separates it is the timing (the fall is on 15 June, within days) and a model that holds the
power and gas prices fixed, which is E2. The opt-in window fails every version (3–7 placebos as large as the real
break). **E1 stays description.**

**Narrow window, 14 days either side (2026-11-11, user's go-ahead)**: `analysis/cogeneration_event_narrow.py` →
`cogeneration_event_narrow_{estimates,placebo}.csv`. Capacity-weighted.

| data | break | estimate (se) | comparison's change ÷ treated's |
|---|---|---|---|
| REE plants, gas against biomass and waste | 15 June 2022 | **−0.239 (0.045)**, from 0.64 | 0.11 |
| OMIE units, non-renewable against renewable | 15 June 2022 | −0.100 (0.034), from 0.43 | 0.02 |
| REE plants | 1 October 2022 | −0.041 (0.052) | 1.85 |
| REE plants | 3 October 2022 | −0.011 (0.051) | 1.17 |

- **June against 165 placebos** (OMIE's label, every Wednesday 2019-01 → 2022-03, same 28-day window): placebo sd
  0.038, 5th–95th percentile −0.057 to +0.068. The real break (−0.100) is more negative than all but 2 of them (rank
  3 of 166, 1.8%). **The one-third gate still fails** (63 of 165 above it): one third of −0.100 is 0.033, less than
  one placebo standard deviation, so on OMIE's units the gate cannot be met by an effect of this size. Leaving out
  placebo windows that touch Christmas, Holy Week or August changes little (34 of 107 above one third).
- **The plant-level estimate is 2.4 times OMIE's** and has no placebos: REE's units are daily only from 2022-04-01.
  OMIE's units are representatives' portfolios whose membership and capacity change, which dilutes the effect and
  adds noise. Placebos on plants need REE's daily workbooks for an earlier year (2021: 365 files, about 1.6 GB,
  token). If placebo noise on plants is like OMIE's (0.04), a break of −0.24 would clear the one-third gate (0.08)
  in most placebo weeks; not known until run.
- **October: nothing at the break.** Gas and biomass rise together; the capacity-weighted gap does not move.

**Plant placebos run (2026-11-11, user's go-ahead).** `.venv` was already repaired; panel rebuilt with 2021 daily;
`analysis/cogeneration_event_narrow.py` → `cogeneration_event_narrow_placebo_plants.csv`. 28-day window on every
Wednesday of 2021 (48 placebos), REE's plants, gas against biomass and waste, 15 June 2022 break:

| weights | real | placebo sd | range | above one third of real | as large as real |
|---|---|---|---|---|---|
| unweighted | −0.247 | 0.032 | −0.071 to +0.089 | **1** (2021-03-03, +0.089) | 0 |
| capacity-weighted | −0.239 | 0.049 | −0.116 to +0.151 | **5** (3 outside holiday windows) | 0 |

The real break is 2.3–2.9 times the largest placebo in size, and placebo sd is 0.03–0.05 against a break of 0.24
(5–8 sd). The one-third gate, as set, still fails by a few placebos (1 unweighted, 5 weighted), so by the spec's
letter E1 stays description. The failures are small in number and not a pattern: placebo signs are mixed and the
worst weighted one (+0.151, 2021-03-03) is positive, the opposite sign to the cap effect. Gate restated for the
user's decision: a sign-aware version (placebo of the same sign as the real break and above one third) leaves 3
weighted placebos (2021-01-20 and 2021-07-28, both holiday windows, and 2021-01-27), none unweighted. Opt-in (October) fails every
version, as before. Not yet decided.

## E2 first cut: output against the wind-moved price (2026-11-11, user's go-ahead for each step)

Scripts `analysis/cogeneration_price_response{,_checks,_postcap}.py`, `cogeneration_cap_decomposition.py`,
`gas_price_at_cap.py` → `outputs/tables/cogeneration_price_response*.csv`, `cogeneration_cap_decomposition.csv`,
`gas_price_at_cap.csv`. Daily capacity-weighted load factor per group (REE's units, P48), on the day-ahead price moved by
the day's wind forecast (ESIOS 1777; first stage F 96 pre-cap), controls gas price (MIBGAS), degree hours, weekday, month;
HAC 7 lags. Days on disk only: 443 pre-cap (2021-01-01 → 2022-06-14, a gap Jan–Mar 2022), 290 post-cap.

- **Pre-cap, gas +0.012 per €10/MWh (t 4.6), elasticity 0.27; biomass and waste placebo −0.001 (t −0.8).** About 43 MW
  per €10 on 3,577 MW. Lead and lag placebo passes: own day +0.011 (t 4.8–5.5), lead +0.001 (t 0.6), lag +0.001–0.002
  (t 0.9). By switching in 2022-06-15 → 2023-03-31: frequent switchers (146 plants, 2,060 MW) +0.018 (t 4.9), stable (66,
  1,351 MW) +0.003 (t 2.0: misses the two-se rule by 0.003 se); biomass flat in both.
- **Post-cap, no window passes the placebo rule.** Biomass responds in the cap period (+0.012, t 2.8, first stage F 19),
  the opt-in period (+0.011, t 5.1) and Jan–Mar 2023 (+0.013, t 6.4); gas switchers +0.008 (cap, t 1.4), +0.023 (Jan–Mar
  2023, t 7.4). The cap-period gas slope is not significantly below the pre-cap one. Hypothesis, untested: plants that are
  off do not respond to a modest price rise.
- **Most of the June fall is plants switching off**: units running (above 10% of their peak) 131 → 87 of 237 in the 14
  days around 15 June, 64 on average to 30 September; running units' load factor 0.73 → 0.67.
- **The pre-cap model reproduces the June fall.** 14 days before → after: power price 197 → 147, MIBGAS 77 → 113; gas load
  factor −0.172 actual, −0.185 predicted (power price −0.06, gas price −0.13); biomass +0.037 actual, +0.056 predicted. The
  gas coefficient (−0.0035 per €/MWh) is extrapolated beyond the 2021 range and the model misses badly further out
  (post-cap monthly residuals −0.12 to −0.26 for gas and biomass), so it is only read in this window.
- **The gas price rise at 15 June was European, not Iberian.** MIBGAS +€36 (log +0.384), Italy's PSV +€41.5 (+0.413); the
  Iberian spread −0.029, rank 48 of 77 placebos (placebo sd 0.16, so a cap effect on the Iberian gas price up to about
  ±0.3 in logs cannot be excluded). Spanish LNG send-out +75 GWh/d, Italian +23; the Spain-minus-Italy log difference
  +0.023, rank 64 of 77. So the gas-price channel is common to Iberia and Italy, and **E1's June fall (−0.24 against
  biomass) mixes the cap with a European gas shock the same week** (PSV jumps 67 → 91 on 15 June). The power-price channel
  (−0.06 of −0.17) is what the cap can have moved through the market. Italian gas plants are a candidate control for the
  gas-cost shock; no Italian cogeneration data are on disk.

## Italy as a control (2026-11-11, user's go-ahead)

Italian hourly demand and the PUN from GME's accepted bids: `build/build_italy_demand.py` →
`data/gme/italy_demand_hourly.parquet` (2021-06-01 → 2023-06-30, 777 GWh a day in 2022, about 90% of Terna's published
consumption). No free unit or hourly Italian cogeneration data (Terna and ISPRA publish annual national CHP; ENTSO-E per-unit
needs the pending token and covers units of 100 MW or more).

- **Demand placebo FAILS** (`analysis/italy_demand_placebo.py`, 18,238 hours, controls both countries' degree hours, both gas
  prices, hour × month, hour × weekday, year-month): Italian demand against the Spanish price moved by Spanish wind −0.059%
  per €1 (t −4.3), Spanish measured demand −0.060 (t −5.3); reduced form +0.305 and +0.311% per GW of forecast wind. The
  same size in both countries: the wind instrument carries a common demand pattern, so the aggregate Spanish demand
  response (−0.06%/€) is not a price response. This closes the aggregate-demand wind design.
- **Gas plants at the cap** (`analysis/gas_plants_at_cap_iberia_italy.py`, 55 Iberian and 96 Italian gas units of 100 MW or
  more): day-ahead load factor +0.118 Iberia, +0.077 Italy in the 14 days after 15 June 2022; difference +0.041, rank 44
  of 75 placebos (5–95%: −0.13 to +0.12). No Iberia-specific change detected, power low (placebo sd 0.08). Lead, not tested:
  Iberian subsidised CCGT +0.12 in the same weeks that unsubsidised gas cogeneration fell −0.17.

## Within Iberia: subsidised combined cycles against unsubsidised cogeneration (2026-11-11)

`analysis/iberia_subsidy_contrast.py` → `outputs/tables/iberia_subsidy_contrast.csv`. 14 days after against 14 days before 15 June
2022, daily load factor: Iberian gas combined cycles (55 units, PDBF) 0.297 → 0.415 (+0.118); gas cogeneration (REE units) 0.512 →
0.341 (−0.172); difference **+0.289**, rank 1 of 46 placebos (placebo sd 0.104, 5–95%: −0.15 to +0.18); cogeneration alone −0.172
against a placebo sd of 0.046 (rank 1). Same-calendar windows in June 2021: differences −0.03, +0.01, −0.08. **Passes the pre-set
rule** (outside 5–95% and rank in the top 5%). Cautions: four placebos in Oct–Nov 2022 (the opt-in transition, not clean) reach
0.20–0.25; the combined cycles' rise is mostly heat, since Italy's rose +0.077 and Iberia minus Italy is +0.041 (rank 44 of 75), so
the contrast says cogeneration fell unusually, not that the subsidy raised the combined cycles' output.

**Status of E2 (2026-11-11): the most promising result so far.** Pre-cap gas cogeneration output rises +0.012 per €10 with the
wind-moved price (t 4.6) against a flat biomass placebo, passes the lead and lag placebo and a switchers-against-stable dose-response
(stable plants t 2.0), and the pre-cap model reproduces the June fall (−0.185 predicted, −0.172 observed, mostly through the
European gas price). Open before it is quoted: (1) the Italian demand placebo shows the wind instrument carries a common demand
pattern (+0.3% per GW in Italy and Spain), so the cogeneration response needs a check that it does not run through hosts' weather
(alternative instrument, richer weather, hourly data); (2) the post-cap windows fail the biomass placebo and are not read;
(3) 443 pre-cap days, aggregated by group, a three-month gap in 2022.

## Where the design stands

- E1 (the event by group) and E2 (the run decision and the cost) now have their data: REE's units by day,
  2022-04-01 → 2023-03-31, fuel known, plants followed through both dates. Neither has been estimated.
- E3 (pass-through into offers) rests on a few dozen units that state a price; a lead, not a chapter.
- The regulated payment per plant is still the main unknown (spec §6).

## Checks on the pre-cap result (2026-11-11, user's go-ahead: "Cogeneration checks")

Open item (1) above: does the pre-cap gas response run through hosts' electricity demand, since the wind instrument carries a
common demand pattern? Three checks, pre-cap window (443 days on disk), set before the hourly run:

- **C1 demand control** (`analysis/cogeneration_demand_checks.py` → `outputs/tables/cogeneration_demand_checks.csv`): add REE's
  day-ahead demand forecast (ESIOS 1775, daily mean) to the controls. Pass: the gas coefficient keeps its sign, at least half its
  size, t above 2; the biomass placebo stays inside |t| < 2.
- **C2 alternative instrument:** solar forecast alone; wind purged of demand; wind and solar together. Pass: same sign, within a
  factor of two of the baseline, first-stage F above 10.
- **C3 hourly, within the day** (`build/build_cogeneration_ree_hourly.py`, `analysis/cogeneration_hourly.py`): gas group hourly
  load factor (REE's P48) on the hourly day-ahead price instrumented with the hourly wind forecast, date effects (these absorb
  the gas price, the host's heat load, daily demand), hour × month and hour × weekday effects, clustered by week. Pass, all of:
  first-stage F ≥ 10; gas coefficient positive with t > 2; biomass-and-waste placebo |t| < 2; and a shifted-price placebo
  (price and instrument from each of the 20 days within ±10) in which the real coefficient lies outside the shifts' 5th–95th
  percentile and ranks in the top 2 of 21. All three checks must pass before the pre-cap result is quoted.

**C1 and C2 result (daily).** Baseline +0.012 per €10 (t 4.6, F 96). With the demand forecast as a control: **+0.012 (t 5.7, F 101)**,
biomass −0.001 (t −0.9). The wind forecast's correlation with the demand forecast is only +0.07 in these days, so the demand control
barely moves anything, and "wind purged of demand" is identical to the demand-controlled specification by construction (not an
independent check). Solar alone has no first stage (F 0.4): uninformative. Wind and solar together, demand control: +0.013 (t 5.7,
F 62), biomass −0.001. **C1 passes; C2 as far as it can be run passes (wind variants) or is uninformative (solar).**

**C3 result (hourly, within the day; 421 pre-cap days, 10,104 hours; 2022-06 days in quarter-hours skipped).**
`analysis/cogeneration_hourly.py` → `outputs/tables/cogeneration_hourly.csv`. Hourly load factor on the hourly day-ahead price, wind
forecast as the instrument, date and hour × month and hour × weekday effects, clustered by week. First stage F 65.

| outcome | per €10 | se | t | elasticity at the mean |
|---|---|---|---|---|
| gas | **+0.0074** | 0.0010 | 7.3 | 0.165 |
| biomass and waste (placebo) | **+0.0023** | 0.0004 | 5.2 | 0.056 |
| gas minus biomass | +0.0051 | 0.0010 | 5.0 | |

By time of day (gas / biomass, t): night 0–5h +0.0040 (4.3) / +0.0017 (2.6); day 6–17h +0.0071 (6.5) / +0.0020 (3.9); evening 18–23h
+0.0079 (7.7) / +0.0012 (1.9). Shifted-price placebo (20 shifts, ±10 days): median −0.0001, 5–95% −0.0011 to +0.0013, the real
+0.0074 ranks 1 of 21.

Rules, in order: first stage **passes** (F 65); gas positive, t above 2: **passes** (t 7.3); **biomass placebo: FAILS** (+0.0023, t 5.2,
against the pre-set |t| < 2); shifted-price placebo: **passes** (rank 1 of 21, the shifts sit within ±0.0013). **By the rule that all
three checks pass, the pre-cap result cannot be quoted as it stands.** What the hourly result does say: within the day, gas
cogeneration follows the price about three times as strongly as biomass and waste (elasticity 0.17 against 0.06; difference t 5.0),
the response is not a pattern any other day's price produces (the shifts are zero), and it is present in every part of the day.
What stops it: the placebo group responds too, which the daily design had flat (−0.001, t −0.8). Candidate reasons, not tested:
biomass and waste plants also shift output toward dear hours (many are paid partly by market price), or REE's technical-constraint
dispatch moves with the same wind-driven price shape.

**Status after the checks.** The daily design's three open items: (1) demand: C1 passes, C2 uninformative or by construction;
(3) hourly within-day: gas response confirmed and day-robust, but the placebo fails. So the gas-specific part is **about 70% of the
hourly gas coefficient** (0.0051 of 0.0074), still positive and significant as a difference, but the pre-set rule is not met and
I am not restating it. Item (2), the post-cap windows failing the biomass placebo, is unchanged.
