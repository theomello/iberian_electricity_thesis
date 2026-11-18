# Scope: what caused the high-voltage evening shift in summer 2021?

**Status: scoping note, 2026-11-18. Only a price check was computed (no demand outcome). Nothing is registered.**
Source of the puzzle: `docs/specs/2026-11-18-industry-six-summer-ri-design.md` (results). In evening-versus-night
shift terms, summer 2021 against the pre-reform summers: 6.4TD (toll dose 0.04) about −5 to −6 points, 6.3TD about
−3 to −4, industry E1–E6 (dose 0.12) about −3.5. The shift does not scale with the toll dose, so R5 failed and no
price elasticity was reported.

## Check done: did the wholesale price shape move? No.
Working days, evening (18–21h) over night (0–7h), log ratio of the Spanish day-ahead price, aligned summer windows
(REN's Spanish price series, which now runs from 2014; scratch script, not kept):

| summer | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | **2021** |
|---|---|---|---|---|---|---|---|
| mean price €/MWh | 54 | 58 | 42 | 50 | 64 | 47 | **104** |
| ln(evening / night), wholesale | 0.076 | 0.077 | 0.050 | 0.047 | 0.094 | 0.103 | **0.082** |
| same, all-in 6.4 (wholesale + tolls) | 0.129 | 0.125 | 0.115 | 0.102 | 0.137 | 0.161 | **0.148** |

2021 minus the placebo mean: wholesale +0.008 (placebo sd 0.023), all-in 6.4 +0.020 (sd 0.020). **The price level
doubled, but the evening-to-night price ratio was ordinary.** A response to the wholesale *shape* cannot produce an
unusual evening-to-night load shift when that shape did not move, and there is no first stage from which to compute
a shape elasticity. What remains open is a response to the *level*. If firms facing a doubled price cut evening or
second shifts but keep continuous night processes, a level shock shows up as a shape change. That cannot be told
apart from an output change for other reasons without plant-level or production data.

## Working back from the effect to the cause
Each candidate predicts a different fingerprint. All the checks below use data on disk and are descriptive.

| candidate | predicts | check |
|---|---|---|
| **A. The reform's power (capacity) term**: new 6.xTD demand charges by period, not in our energy-term dose | a break **on 1 June 2021**; fall concentrated in the new top-period hours (9–14h, 18–22h on working days), largest in July (high season); weekends unchanged | event-time plot of daily evening/night (and each hour) around 1 June 2021 against 2017–19; power-charge change by period and tariff from the toll orders |
| **B. Level response to the wholesale price** (doubling) | a **gradual** shift tracking the price level through summer and autumn 2021; continuing into the 2022 crisis; no break at 1 June | same plot, extended to Dec 2021, against the monthly price level |
| **C. Cogeneration**: high gas prices cut industrial cogeneration, changing grid demand net of own generation | the shift appears in plants with cogeneration; cogeneration output falls in the evening hours in 2021 | PDBF schedules of cogeneration units by hour, summer 2021 against 2017–19 (`rq-cogeneration.md`, `unit_ownership`) |
| **D. Specific plants or sectors** (a smelter, a refinery changing schedules) | the shift is concentrated in a few units | direct-consumer panel (322 units, hourly cleared MW, 2018–2026): which units' evening/night ratio moved; sector |
| **E. Post-COVID schedules** | a gradual return to a 2019 shape (2020–21 was the anomaly) | 2020 H2 and 2021 H1 against 2019 on the same plot |
| **F. A data definition break** | an exact step on 1 June in a tariff series but not in its voltage twin | E4 against 6.3 and E6 against 6.4 (equal to 1.000 in June–September 2021; check before June too) |

Order proposed: F (minutes) → event-time plot (separates A from B and E) → A's charge table → C and D only if
A and B do not explain it.

## Could any of this give an elasticity?
- **Wholesale shape:** no. No first stage (above).
- **Wholesale level:** only if the level is instrumented and the outcome is a level. The wind-speed IV already gives
  a precise same-hour zero; a summer-level comparison has one treated summer and a price level confounded with the
  gas crisis. Not promising.
- **Power term (if A holds):** possibly a *demand-charge* elasticity, the response of peak-period load to the
  capacity price. That is a different object from the energy-price elasticity, but it is a price response of
  industry to a regulated tariff, and it is identified by the same reform and design. It needs the power-charge
  change by period and tariff as a second dose (registered before use).

## Results of the first two checks (2026-11-18, descriptive)

**F. Definition break: none.** E4/6.3 = 1.0000 and E6/6.4 = 1.0000 in every month of 2020-10 → 2021-12 (and
2017–19), so the 6.3 and 6.4 shift is not a change of definition. (E3/6.2 moved from 1.0 to about 0.77 during
2017–19, not at the reform.)

**A data bug found on the way (affects every IND estimate since 2026-11-16).** E5 (ESIOS 1206) has no rows in many hours,
apparently those in which it is zero. `tou_cross_tariff.esios_load` sums components with index alignment, so IND is
NaN whenever E5 is absent: **1,548 of the 2,568 hours of the 2021 window (60%; June 680 of 720)**, against 0 in the
2017–2019 aligned windows. The IND 2021 estimate (−0.288, in `2026-11-16-industry-adjusted-design.md`, the
randomization run of 2026-11-17 and the six-summer test) therefore rests on a selected 40% of hours. E0, E1+E2 and the
tariff series 6.2–6.4 do not include E5 and are unaffected. Fix: treat absent E5 hours as zero (E5 is at most 228 MW
against about 12 GW of IND). Not rerun yet.

**Event time (figure `outputs/figures/hv_shift_2021_by_month.png`).** Working days, evening-minus-night LASSO error,
Spain minus Portugal, 2021 minus the mean of normal years (2014–19; 2017–19 for E1+E2), percentage points:

| | Jan | Feb | Mar | Apr | May | **Jun** | Jul | Aug | Sep | normal-year sd (Jun–Sep) |
|---|---|---|---|---|---|---|---|---|---|---|
| E0 | −5.7 | −3.9 | −2.7 | +0.9 | −2.4 | **−9.4** | −6.2 | −7.8 | −9.8 | 2–3 |
| E1+E2 | −8.9 | −7.2 | −4.3 | −2.9 | −3.1 | **−5.3** | −7.2 | −7.4 | −6.0 | 0.5–1.5 |
| 6.3 | +2.3 | +5.4 | +0.5 | −0.6 | −0.3 | **+2.7** | +2.1 | −10.9 | −3.6 | 1.4–4.6 |
| 6.4 | −5.8 | −1.3 | −1.1 | +3.4 | +1.7 | **+0.9** | −9.5 | −7.8 | +1.0 | 1.3–2.5 |

Weekends, June–September (no tariff incentive at any voltage: all hours are the lowest period): 6.3 −2.7, 6.4 −2.2
in 2021 against +0.3 to +2.0 and −0.1 to +1.9 in normal years.

**What the fingerprints say.**
1. **Households and small business (E0) break at 1 June**: about −3 before, −8 after. This is the reform effect,
   seen month by month.
2. **E1+E2 was already off in January–May 2021** (−9 to −3), before the reform. The June–September level (−6) is
   only about 2 points beyond the January–May average. Most of what the summer comparison attributes to the reform
   was there before it. The 2021 pre-period was never in the summer-to-summer design.
3. **6.3 and 6.4 show no break at 1 June.** Their shift sits in July and August only (6.4: −9.5 and −7.8; 6.3:
   August −10.9), June and September are normal, and weekends also moved. That rules out the power-term reading
   (A), which predicts a break on 1 June, the largest fall in July, nothing at weekends, and an effect lasting
   through September. It also argues against a response to the wholesale level (B): prices were highest in September,
   when 6.4 was back to normal.
4. What fits 6.3 and 6.4: an event confined to July–August 2021 at the largest plants, on all days of the week.
   Candidates for the next check: specific plants (D, the direct-consumer panel), cogeneration (C), and the August
   2021 heat wave at industrial sites (the LASSO uses population-weighted city temperature).

## Cause found (2026-11-18, descriptive): the July and August change of the 6.x period calendar
Working days, load by hour as a share of the daily mean, 2021 minus the 2017–19 mean (percentage points), against the
period of each hour under the old (ITC/2794/2007) and new (Circular 3/2020) calendars:
- **6.4, July** (old A1 → new high season): hours 9–10 (period 2 → 1) −7, −6; hours 14–17 (1 → 2) +3 to +5; hours 19–21
  (2 → 1) −6, −8, −8; hours unchanged in period move little (11–13 −2 to −3, 22 −1); night +3 to +5. Normal-year sd
  about 1.1.
- **6.4, August** (old: every hour period 6; new: 9–14h and 18–22h period 3, other daytime period 4): night +3 to +5,
  every daytime hour −1 to −4.
- **6.3, August:** night +5 to +7, every daytime hour −3 to −4 (sd 0.9). 6.3 July: weak (sd 1.8).
- **June and September** (old B → new medium: small changes): 6.4 and 6.3 within about ±3, no matching pattern.
- E1+E2: July and August night +3, day −2 to −3; but June and September show a smaller version of the same, and
  January–May 2021 was already off, so its pattern mixes the calendar with the pre-reform deviation.

**Reading.** The largest plants moved load out of exactly the hours that became dearer *periods*, and into the hours
that became cheaper ones, in the two months where the calendar changed most. That is a response to the reform, but
**not to the energy toll in €/MWh**, which for 6.3 and 6.4 is a few euros (dose 0.04–0.06). The incentive must come
from what follows the period calendar: the **power (capacity) term by period** and **supply contracts priced by
period** (CNMC: about a third of industrial energy is fixed by period, a third mixed). So:
1. **The dose is mismeasured for large industry**: it counts only the energy toll, so η = response / dose is inflated
   where the toll is small, and does not scale across tariffs.
2. **The R5 correction assumed 6.4 was untreated. It was treated.** R5's failure says nothing about a common non-price
   shift.
3. An identification route follows: the **change in period by month and hour** (old versus new calendar) is a sharp,
   known treatment with many cells (24 hours × 12 months × day types) and an old-calendar placebo in every pre-reform
   year. Turning the response into a price elasticity needs the price of each period as large consumers pay it:
   power charges from the toll orders, and per-period contract prices (retailer price sheets or CNMC data), not yet in
   the repo.
