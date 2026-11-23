# Small-business (3.0TD) response to the June 2021 reform: options (2026-11-23)

**Status: options note, nothing run.** Question: did small businesses (tariff 3.0TD, low voltage, contracted power >15 kW, about 770,000 supply points, 2.3–3.4 TWh a month) respond to the reform's period prices? Closed designs (`docs/business-demand-evidence.md`) stay closed. Each route below is a new test, not a rescue.

## Where we stand
- **No small-business number exists.** E0 (low voltage < 1 kV, ESIOS 1201) mixes 2.0TD households and 3.0TD business; its −0.10 to −0.12 is mostly households. "Pure 3.0TD −0.163" (`2026-11-12-industry-voltage-design.md`) is E0's response divided by the 3.0TD dose, not a business response.
- What did work, for large industry (`2026-11-18-industry-regulated-price-elasticity-design.md`): (1) **period structure as the treatment**: the change in period rank by month × hour, with power terms in the dose, instead of the €/MWh toll alone; (2) a **price-free reduced form**: hour share of daily load on the rank change, −1.0 point per step (p 0.0001); (3) **six pre-reform summers (2014–2019)** as the null distribution.
- The obstacle for business is that no hourly 3.0 series exists before mid-2024 (ESIOS 2532). Verified 2026-11-23: the ESIOS catalogue has no measured-demand indicator for old 3.0A.

## The key fact this note adds: the old 3.0A calendar switched with the clock change, and the 2.0 tariffs did not
Old 3.0A (`tou_tariff_schedule.old_period_3`, every day of the week): **summer time P1 = 11–15h; winter time P1 = 18–22h**; P2 is the other hours from 8 to 24h, P3 is 0–8h. New 3.0TD: on weekdays 9–14h and 18–22h are the top period of the season all year; weekends are all P6. Households (old 2.0A was flat; new 2.0TD has one schedule all year) got **the same change in summer and in winter**.

**Worked example.** A shop's 19h hour in July: before 2021 it was P2 (mid-priced); after, it is P1 (top), so the price **rises**. The same shop's 19h hour in January was already P1 before, so nothing changes. The 12h hour goes the other way: in July it was already P1 (no change), and in January it moves from P2 to P1 (**rises**). A household's 19h and 12h hours rose the same way in July and in January. So if small businesses respond, E0 should show a **mirror pattern**: in summer the evening share falls relative to winter, and in winter the midday share falls relative to summer. A household response that is the same in every season cannot produce that pattern. On weekends the prediction is mirrored and reversed: old weekend P1 hours became P6, so the 11–15h hours of a summer weekend and the 18–22h hours of a winter weekend get cheaper for 3.0, and load there should rise.

## Every customer group, what we have (added 2026-11-23 at the user's request; numbers from the specs named)
Volumes: CNMC monthly by toll, 2021, rounded.

| Group | Tariff / series | Size | Best estimate | Status | Source |
|---|---|---|---|---|---|
| Regulated households (PVPC, the paper's population) | 2.0TD ≤ 10 kW on the regulated price | 23–30% of E0 | −0.064 (paper design) | identified (replication) | `notes/tou-headline-outline.md` |
| Households, metered micro data | GoiEner 2.0TD, 14,000 points | Basque cooperative | about −0.05 [−0.07, −0.03] (first-difference DiD; LASSO after placebo centring −0.053) | identified, not representative | `2026-11-17-goiener-*` |
| **Households + small business** | E0 (< 1 kV) | ~100 TWh/yr | **−0.11 [−0.21, −0.01]**, p 0.019, six summers | identified (headline) | six-summer spec |
| **Small business** | 3.0TD (> 15 kW, low voltage) | ~33 TWh/yr, 770k points, 26–36% of E0 | none. Hint only: the non-regulated part of E0 shifted −5.7% against −3.9% for regulated households | **not identified**: route A below | — |
| Services, one city | Barcelona Serveis (2.0/3.0/6.1 mix) | ~3.5 TWh/yr | −0.004 [−0.080, +0.071] (calendar) | failed, bounded null | calendar-boundary spec |
| **Medium firms** | 6.1TD (E1+E2, 1–36 kV) | ~67 TWh/yr | −0.08 [−0.25, +0.09] reform dose; −0.084 [−0.20, +0.06] regulated price (S = 3, p 0.077); +0.013 [−0.06, +0.08] calendar | **not identified** | evidence table rows 1, 11; regulated-price spec |
| **Large industry** | 6.2–6.4TD (≥ 30 kV) | ~52 TWh/yr | **−0.15 (trend null) to −0.32 (mean null)**; reduced form −1.0 point per period step, p 0.0001. By tariff: 6.2 −0.06, 6.3 −0.23, 6.4 −0.34 | identified, caveats (drifted null, not proportional) | regulated-price spec |
| Industry, hourly wholesale price | E3–E6, wind-speed IV | | +0.0001 [−0.021, +0.028] | precise zero | evidence row 13 |
| Direct market consumers | ESIOS 353 (buy in the day-ahead market) | 12.7% of E3–E6 | wholesale −0.033 [−0.12, +0.02]; reform period shift seen in purchases (descriptive) | wholesale null | evidence row 15; regulated-price spec |
| Process-industry and refinery units | OMIE purchase units | 0.5–2 TWh/yr | −0.007 / −0.069 (wholesale) | not detected | evidence row 16 |
| Interruptibility participants | metered, 2019 | | uninformative (consumption floor in the contract) | — | evidence row 19 |

So the gaps are **small business (3.0TD)** and **medium firms (6.1TD)**: they sit between two identified ends.

## Routes

| # | Route | What it identifies | Data | Detectable effect (MDE = 2.8 × SE) | Verdict |
|---|---|---|---|---|---|
| **A** | **Season mirror within E0**: hour share of daily E0 load, by date type × hour × old season (summer or winter time), post-reform year minus the placebo-year mean, regressed on the **3.0 rank change**, with **hour × day-type fixed effects** that absorb any season-invariant (household) response. Null distribution: the same statistic for each placebo year 2014–2019, prediction t-test and rank (six-summer machinery). Elasticity: the reduced form divided by the 3.0 load share of E0 in that cell (measured hourly mix from ESIOS 1209 and 2532, 2024–26, scaled by CNMC monthly shares) and by the 3.0 regulated-price dose (toll + power term per period, old 3.0A against new 3.0TD) | 3.0TD response to the period calendar; the elasticity to the regulated period price | **All on disk** (E0 hourly from 2014, holidays, schedule module). The old 3.0A power terms must be read from the BOE (as Z1 for 6.x) | **Not measured yet.** Rough guess from the 6.x reduced form (placebo spread about ±0.1 point per step): if E0's season-varying slope is that quiet, MDE ≈ 0.28 point per step in E0 ≈ 0.8 point per step for 3.0 at a 35% share, i.e. elasticity ≈ −0.12 to −0.26. Dilution by households (3.0 is only 26–36% of E0) is the main risk. **Step zero (placebo years only) is needed to know** | **Recommended** |
| A′ | Validity rule for A: **GoiEner 2.0TD households** (14,000 metered points, pre and post, to June 2022) run through the same mirror statistic | Whether households' own response differs by season (the main threat to A) | On disk (needs extraction, about 4 GB) | n/a (placebo outcome) | Part of A |
| B | **Subtraction**: business = (E0 − scaled household proxy) / 3.0 share, with the proxy taken from PVPC regulated schedules (REE P48) or GoiEner | 3.0TD level response | PVPC only from 2018 (two placebo years); schedules, not meters; GoiEner is a Basque cooperative, not representative | Any 1% error in the proxy becomes about 3% in the business series; probably worse than A | Not recommended |
| C | **Barcelona services, season mirror in six-hour bands** (18–24h and 12–18h) | The same mirror on a direct business series | On disk, but **2019 is the only clean pre-year** (no six-year null) | Not testable by randomization inference | Corroboration only, described, no rule |
| D | Old-regime **clock-change boundaries** (3.0A steps at each clock change 2014–2020; none after) | 3.0A response at a boundary | On disk | — | **Excluded**: same family as the calendar-boundary design closed "for good" on 2026-11-16 |
| E | **Ask REE** for hourly measured demand by access tariff (2.0A/DHA, 3.0A) for 2014–2024: the settlement system computes it, and ESIOS publishes it only from 2024 | A direct 3.0 series with a pre-period, which would make B and A sharp | External; no date | — | Send in parallel; does not block A |

## Data checked for this note (2026-11-23)
- **CNMC electricity indicator bulletin, addendum** (IS/DE/012/24, 012/25): national **monthly** energy (GWh), consumer counts and contracted power by access toll, January 2021 →. 3.0TD share of low-voltage energy is 25.6% (Jan 2021) to 35.6% (Jul 2021). Monthly only, no periods or hours, so it is a weight, not an outcome. Recorded in `docs/data-reference/ree-ren-esios-miteco.md`.
- **Datadis** has no national open aggregate that we found; Barcelona's dataset is a city product built on it. Other cities: none found. Bank of Spain firm data: annual, no electricity by hour; not useful for this margin.

## Recommendation
**Route A**, pre-registered in two stages like the earlier designs: **step zero** (placebo years 2014–2019 only: noise of the mirror slope, MDE, and the GoiEner household mirror on pre-reform years), with the gate set in advance at **elasticity MDE ≤ 0.15** (the bar used for the calendar designs). Then the estimation rules (detection against six placebo years, rank, null centred, leave-one-year-out, summer and winter legs both with the predicted sign, weekend leg reversed, GoiEner households show no mirror) only if step zero passes. Send the REE request (E) in parallel.

What is not blind: E0's summer-2021 evening-versus-night shift is known (E0 −5.7%; regulated households −3.9%). `tou_extended_months.csv` also has E0's monthly evening path through winter 2021–22, so the working-day evening half of the mirror is known.

## Decisions (2026-11-23)
- **The user chose route A.** The spec is `docs/specs/2026-11-23-small-business-season-mirror-design.md`. After review,
  the confirmatory leg is **non-working days**: households' weekend price is flat before and after, and the
  RDL 17/2021 charge cut does not reach weekends. Working-day midday is a secondary rule, and working-day evening
  (already seen) is description only. Months are June–September and January–February. The gate stays at an
  elasticity MDE ≤ 0.15, as above.
- **The user added medium firms (6.1TD, E1+E2).** They have no clock-season mirror: their old 6.1A calendar changed by
  month, with August all off-peak and June split on the 16th. The design is large industry's reduced form
  (hour share on the period step), with hour fixed effects and six placebo summers. 2014 enters under its own gate,
  and 2015–16 come from the 6.1A series 1369 as a stand-in, gated on the overlap years (the user's choice). Spec:
  `docs/specs/2026-11-23-medium-firms-period-calendar-design.md`.
