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

**What it needs:** the workbooks for every day of the window (ESIOS archive 34, token, about 5–8 MB a day in 2022).
Not fetched. A decision for the user.

## Where the design stands

- E1 (the event by group) is feasible now on OMIE's label, and far better on REE's units with the daily workbooks.
- E2 (the run decision and the cost) needs fuel and plant-level units: REE's units, or nothing.
- E3 (pass-through into offers) rests on a few dozen units that state a price; a lead, not a chapter.
- The regulated payment per plant is still the main unknown (spec §6).
