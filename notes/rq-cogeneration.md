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

## Where the design stands

- E1 (the event by group) and E2 (the run decision and the cost) now have their data: REE's units by day,
  2022-04-01 → 2023-03-31, fuel known, plants followed through both dates. Neither has been estimated.
- E3 (pass-through into offers) rests on a few dozen units that state a price; a lead, not a chapter.
- The regulated payment per plant is still the main unknown (spec §6).
