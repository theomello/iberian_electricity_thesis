# Reactor outages by cause: the instrument for n

Framework spec §9.3 (rank 1) and §9.7 step 1. Built 2026-10-05.
Script: `build/build_reactor_outages.py` (`--verify`). Outputs:
`outputs/tables/reactor_outage_hours.parquet`, `reactor_outage_dose.parquet`,
`reactor_outage_spells.csv`. First-stage probe:
`.superpowers/sdd/2026-10-05-reactor-outages/first_stage_probe.py` (not committed).

**In one line.** An unplanned reactor outage lowers each owner's exposed net position
by 0.86 MW per MW of its share of the lost output, with hour effects absorbing the
price (F 121). The outages are not preceded by unusual prices. The undeclared cuts
of 2024–2026 are price responses and are kept out.

**The offer regression, §6 (2026-10-05).** β is −0.9, 95% set [−4.2, 0.7]: β = 1
(supply-function Nash) is rejected and β = 0 (price-taking) is not. The instrument
is borderline at the unit level (F ≈ 10).
**Rain as a second instrument and an event study, §7–8.** On thermal units, rain and
outages together give β −0.9, 95% set [−4.0, 1.8] (F 13.5). Trips cut the owners' X
at once, and their offers show no jump.
**Regional wind as a third instrument, §9.** Wind on a firm's own farms above the
national rate raises its X (F 22–28, the strongest unit-level first stage so far).
Alone it gives β +0.9, set [−2.6, 4.5]; with the outages, β −1.6, [−4.3, 1.5].

## 1. What is built

- **Lost output**, hour by hour, for the seven reactors (Almaraz 1 and 2, Ascó 1 and
  2, Cofrentes, Trillo, Vandellós II): the month's `cab` max power minus the PDBF
  schedule (all role codes; fixed the day before delivery), when above 3% of capacity.
  516,257 reactor-hours, 2018-01 → 2026-05.
- **Cause**, from the OMIE `indisp` declaration covering each hour (451 declarations,
  classified by keyword, first match wins). A declaration explains at most the
  capacity it takes away; the rest of the hour's loss is **undeclared**.
- **Dose**, each owner's share of the lost MW that day (`lib/unit_ownership.py`).
  The shares are the ones the bilateral flows confirm
  (`report-ownership-mapping.md` §4).

Classes:

| class | causes | known when offers close? |
|---|---|---|
| planned | refuelling (42 spells), programmed maintenance, tests, end-of-cycle derates | yes, scheduled weeks or months ahead |
| unplanned | trips, faults, leaks, unplanned maintenance, Vandellós II's 2018 long stop, a refuelling extension | no: enters the schedule the next day |
| regulatory | waiting for authorisation (Cofrentes 2022), grid-caused trips | partly |
| economic | declared "flexible operation" (Almaraz 1 and Cofrentes, April–May 2025), the April 2020 lockdown derate | chosen |
| undeclared | lost output no declaration covers; 465 of its 601 spells fall on days `indisp` has no snapshot for | mostly chosen (§3) |

## 2. How much, and when

Lost output by class, TWh:

| year | planned | unplanned | regulatory | economic | undeclared |
|---|---|---|---|---|---|
| 2018 | 3.46 | 4.62 | 0.13 | 0 | 0.71 |
| 2019 | 4.66 | 0.53 | 0 | 0 | 1.04 |
| 2020 | 4.28 | 0.58 | 0 | 0.08 | 1.46 |
| 2021 | 5.60 | 0.84 | 0.03 | 0 | 1.18 |
| 2022 | 3.90 | 0.78 | 0.20 | 0 | 1.08 |
| 2023 | 4.67 | 0.57 | 0.26 | 0 | 1.89 |
| 2024 | 4.72 | 1.23 | 0 | 0 | **7.80** |
| 2025 | 5.26 | 0.44 | 0 | 0.92 | **5.08** |
| 2026 (to May) | 2.98 | 0 | 0 | 0 | **5.45** |

Spells of at least 50% lost: 51 planned (median 915 hours), 49 unplanned (median 41
hours), 3 regulatory, 2 economic, 601 undeclared (median 10 hours). Unplanned spells
by reactor: Cofrentes 13, Ascó 1 and 2 10 each, Vandellós II 9, Almaraz 1 3, Almaraz 2 2,
Trillo 2.

**Nuclear has become flexible.** Undeclared lost output rose from about 1 TWh a year
to 5–8 TWh from 2024, a fifth to a third of capacity in 2024–2026. It is a price
response (§3), and a descriptive finding in its own right: reactors now cut output at
low prices.

## 3. Are the outages timed on prices?

Price deviation from its month × hour mean, before each spell starts, €/MWh:

| class | spells | 48–25 h before | 24–1 h before |
|---|---|---|---|
| unplanned | 49 | +0.61 (3.41) | +2.69 (3.32) |
| planned | 51 | −5.76 (2.83) | −3.04 (3.20) |
| undeclared | 601 | −6.48 (0.90) | −8.70 (0.88) |

- **Unplanned outages follow ordinary prices.** Nothing suggests they are timed.
- **Planned outages follow somewhat low prices**, consistent with refuelling placed
  in cheap weeks. The date is chosen; what it does to each co-owner is fixed by the
  shares, and the timing is common to all co-owners in the period, so period effects
  absorb it.
- **Undeclared cuts follow low prices**, clearly. They are excluded from the
  instrument.

## 4. First stage

Each firm's exposed n (`firm_x.parquet`, net_mw) on its dose by class, firm × month
and hour effects (the hour effect absorbs the price and every common shock), week
clusters, five large firms:

| class | n, MW per MW lost (F) | X, €/MWh per MW lost (F) |
|---|---|---|
| **unplanned** | **−0.861 (0.078; F 121)** | −0.004 (F 35) |
| **planned** | **−0.890 (0.076; F 138)** | −0.005 (F 36) |
| regulatory | −0.981 (F 57) | −0.010 (F 15) |
| undeclared | −0.682 (F 216) | −0.001 (F 2) |
| economic | −1.629 (F 42) | −0.012 (F 22) |

Clean, priced periods only give the same (unplanned −0.871, F 117; planned −0.875,
F 146). One GW lost lowers X by about 5 €/MWh.

- **About 86–89% of the lost output reaches n.** The co-owner's retail buys in the
  auction what the reactor no longer supplies; the rest is replaced by the firm's
  own other plant.
- **The instrument is firm-specific with hour effects in**, which is what §9.2 needs.
  National forecasts are absorbed by the same effects.

## 5. Limits

- **Thin for Naturgy and EDP.** Their doses come only through Almaraz (Naturgy 11.3%)
  and Trillo (Naturgy 34.5%, EDP 15.5%), which have 7 unplanned spells between them.
  Mean unplanned dose: Endesa 94 MW, Iberdrola 44, Naturgy 2.1, EDP 0.6. Unplanned
  outages identify Endesa and Iberdrola; refuelling adds Naturgy and EDP.
- **`indisp` gaps after 2023.** 465 undeclared spells fall on days with no snapshot,
  so some unplanned trips there are counted as undeclared. They drop out of the
  instrument, which loses power but does not add bias. ENTSO-E's Article 15.1 data
  (token pending) would recover them.
- **Lead times from `indisp` are not planning horizons.** The register is seen only a
  few days ahead (median first sight 8 hours before a planned spell), while refuelling
  is scheduled months ahead.
- **PDBF is the day-ahead schedule.** A trip during day D shows from D+1; that is the
  timing that matters for day-ahead offers.
- **"Economic" moves n by more than its loss (−1.6).** Two flexible-operation spells,
  coinciding with the firms' other cuts; excluded anyway.

## 6. The offer regression (2026-10-05)

`analysis/outage_offer_panel.py` builds the panel; `analysis/outage_offer_test.py`
runs it (48 minutes) and writes `outputs/tables/outage_offer_results.csv`.

**The question, by example.** Say Endesa's reactor trips. Endesa now sells less in
the auction, so it gains less from a high price. If firms price to their net
position (β > 0), Endesa's gas and hydro plants should now offer **lower** than
Iberdrola's comparable plants in the same hour. Price-taking firms (β = 0) would
not change their offers.

**Design** (spec §9.2). 7.8 M unit-hours, 178 dispatchable units (hydro, pumped
storage, combined cycle, coal), clean periods 2018–2026.

- **Outcome:** the unit's offer price at 25% and at 50% of the volume it offers
  (steps capped at 1,000 €/MWh). For thermal units also the 50% price minus the cost
  known at bidding (`c_bid`).
- **Technology × date × hour effects** absorb the market price, so the merit order
  that inflated leg C cannot enter.
- **Unit × week effects:** the comparison is across days within a week.
- **Instruments:** X instrumented by the firm's unplanned and planned doses (GW).
- **Inference:** week clusters, and Anderson–Rubin sets, which stay valid when the
  instrument is weak.

**First stage.** One GW of own outage lowers X by 3.3 €/MWh (unplanned, se 0.9) and
3.9 (planned, se 1.1). Joint F ≈ 10, borderline. The firm-level first stage was far
stronger (n, F 121) because the unit × week effects absorb outages that last whole
weeks, as refuelling does. Only the starts and ends of spells are left.

| sample | offer at | β | 95% set (AR) | p, β = 0 | p, β = 1 | F |
|---|---|---|---|---|---|---|
| all units | 25% | −0.88 | [−4.20, 0.66] | 0.11 | **0.03** | 10.2 |
| all units | 50% | −0.73 | [−3.95, 1.25] | 0.14 | 0.06 | 10.2 |
| five firms only | 25% | −0.81 | [−3.84, 0.69] | 0.12 | **0.03** | 11.1 |
| month clusters | 25% | −0.88 | [−4.19, 0.33] | 0.07 | **0.02** | 11.4 |
| no zero-price hours | 25% | −0.87 | [−4.05, 0.78] | 0.14 | **0.04** | 10.6 |
| unplanned dose only | 25% | −2.79 | [−7.86, −0.17] | **0.04** | **0.01** | 9.8 |
| planned dose only | 25% | +0.47 | [−3.11, 4.16] | 0.74 | 0.71 | 9.0 |
| hydro | 50% | +0.41 | [−1.78, 2.18] | 0.33 | 0.28 | 8.4 |
| combined cycle | 50% | −2.38 | [−8.70, 1.98] | 0.17 | 0.10 | 10.5 |
| coal | 50% | +3.48 | [−3.85, 12.05] | 0.45 | 0.68 | 7.4 |
| thermal, offer − c_bid | 50% | −1.59 | [−6.98, 2.78] | 0.28 | 0.17 | 11.2 |

**Reading.**

- **No sign that offers follow the net position across days.** Every pooled set
  contains 0, and its upper end lies between 0.3 and 1.3. β = 1 is rejected at 5% on
  the 25% offer in every pooled variant, and at 4–7% on the 50% offer.
- **This agrees with legs A and D** (β 0.02–0.14) and with §9.1's reading of leg C:
  once period effects remove the price, the β ≈ 3 is gone.
- **The point estimates are negative**, from unplanned outages and combined cycles.
  - One GW of unplanned own outage raises the firm's other offers by 7.5 €/MWh
    (se 3.8, 25% point).
  - By technology (50% point, the 86 located thermal units of the check below):
    combined cycles +16 €/MWh (se 9), coal −4.5 (se 3.4).
  - Planned outages: −0.4 (se 4.9).
  - The unplanned and planned β differ by about 3.3, with a standard error near 2,
    so they are not shown to disagree.

**Two explanations of the negative sign, tested and rejected.**

1. **Withdrawal from the auction.** A firm covering a lost reactor's contracts with
   its other plant would take that plant's volume out of the auction, and the
   offered share would fall. It does not: +0.004 per GW (se 0.003), combined cycles
   +0.003 (se 0.0015).
2. **Location.** A stopped reactor may make nearby gas plant necessary for grid
   constraints (*restricciones técnicas*, paid as bid), and owners' plants sit near
   their own reactors. The test adds the dose of every reactor within 150 or 300 km
   of the unit, whoever owns it (`analysis/outage_offer_location_check.py`,
   `outputs/tables/outage_offer_location_check.csv`; 86 of 97 thermal units located
   through JRC). Nothing changes:
   - the nearby dose is close to zero (50% offer, within 150 km: −2.3, se 4.6);
   - the own dose is unchanged (+12.1 against +11.8 without it).

**Sellers against buyers.** Splitting X into X⁺ and X⁻, with the doses split by the
firm's sign in the previous week, gives X⁺ +3.7 (F 5.0) and X⁻ −1.3 (F 10.1). Too
weak to read.

**Limits.**

- **Precision.** F ≈ 10, and the sets span 4–5 €/MWh per €/MWh of X. The design
  bounds β below 1. It does not separate 0 from 0.5.
- **Few events.** Unplanned spells fall mostly on Endesa and Iberdrola (§5).
- **Unexplained sign.** The combined-cycle response to the firm's own unplanned trips
  is unexplained. At t 1.7 it may be noise.

**Next.**

- **Rain as the second instrument** (spec §9.3 rank 2), stronger for hydro.
- **An event study of unplanned trips:** the owner's units against rivals' units, day
  by day around the trip. It shows the combined-cycle response directly, without the
  week effects that cost power here.

## 7. Rain as a second instrument (2026-10-05)

`analysis/outage_rain_offer_test.py` → `outputs/tables/outage_rain_offer_results.csv`.

**Index.** Each group's own-catchment rain, as in `rq-hydro-rain-first-stage.md`,
but daily and for every group owning linked hydro (six do). H is the rain over the
k days before day t, standardised against 1991–2020, weighted by GW × ownership
share.

**Thermal units only.** Rain changes a hydro unit's own cost (the value of its
water), so it cannot be excluded from hydro offers. A gas or coal plant's cost does
not depend on rain.

**Effects.** A 30-day rain sum barely moves within a week, so unit × week effects
leave it nothing. The rain runs use unit × month effects and month clusters.

84 thermal units with a plant-specific cost, 3.6 M unit-hours, 2018-04 → 2026-05.
The outcome is the offer price at 50% of offered volume (the 25% point and offer
minus `c_bid` agree):

| instruments | effects | first stage | β | 95% set (AR) | p, β = 1 | F |
|---|---|---|---|---|---|---|
| outages | unit × week | −3.7 per GW (unpl.) | −1.78 | [−7.26, 2.65] | 0.15 | 11.0 |
| outages | unit × month | −3.3 per GW (unpl.) | −0.14 | [−4.03, 4.31] | 0.44 | 14.9 |
| rain, 30 days | unit × month | +0.20 per unit of H (se 0.07) | −2.46 | [−7.18, 1.52] | 0.08 | 9.5 |
| rain, 90 days | unit × month | +0.28 (se 0.10) | −4.34 | [−10.68, 0.12] | 0.03 | 7.7 |
| **outages + rain 30** | unit × month | | **−0.85** | **[−3.96, 1.83]** | 0.17 | 13.5 |
| outages + rain 90 | unit × month | | −1.27 | [−4.77, 1.53] | 0.09 | 12.1 |

- **Rain works as a first stage.** More rain in a firm's catchments raises its X
  (its hydro sells more), with F 9.5 alone.
- **Rain also gives a negative β.** Two independent instruments now point the same
  way: a shock that cuts a firm's cheap own output (a trip, a dry month) raises its
  thermal offers. The simple condition predicts the opposite.
- **Combined, the set is [−4.0, 1.8].** It contains both 0 and 1. Thermal units
  alone do not separate price-taking from Nash. The all-unit run of §6 rejected
  β = 1, but it includes hydro, whose offers rain would also move.

## 8. Event study of unplanned trips (2026-10-05)

`analysis/outage_event_study.py` → `outputs/tables/outage_event_study.csv`,
`outputs/figures/outage_event_study.png`.

**Events.** 21 unplanned trips of at least 24 hours, of reactors that ran normally
in the 7 days before. Ten other spells were dropped because the reactor was already
down: six continue a refuelling or another stop (Almaraz 1 in June 2020, Ascó 1 in
November 2021, Vandellòs II in November 2022), and four are stretches of reduced
output.

**Design.** Stacked by event, unit-day means:

- owners' units against rivals' units of the same technology on the same day;
- intensity = owner's share × reactor capacity (GW);
- day −1 is the reference;
- controls: the group's planned dose and its unplanned dose from other reactors;
- clusters: event.

Per GW of the owner's share:

| | days −7..−2 | days 0–3 | days 4–14 |
|---|---|---|---|
| X, all units | −1.3 (2.8) | **−3.5 (1.6)** | −1.7 (2.6) |
| offer at 50%, all units | +12.4 (8.4) | +6.3 (5.5) | −1.9 (6.1) |
| combined cycles | +12.6 (17.5) | +9.3 (11.8) | −1.1 (13.5) |
| coal | +5.0 (3.2) | **−4.8 (2.3)** | −4.5 (3.4) |
| hydro | +16.6 (9.2) | +8.5 (9.2) | −1.5 (6.4) |
| offered share of capacity | 0.00 (0.01) | 0.00 (0.00) | +0.01 (0.01) |

- **The trip reaches the owner's position at once**: X falls about 5 €/MWh per GW
  on day 0.
- **Offers do not jump.** Relative to rivals', owners' hydro and gas offers are
  higher in the week before than on day −1, drift down through the window, and show
  no break at day 0. The positive
  reduced form of §6 is not a response to the trip. It comes from slow movement
  that unit × week effects pick up.
- **Only coal moves the predicted way.** Its offers fall by 4.8 €/MWh per GW in
  days 0–3 (se 2.3), against X −3.7: β ≈ 1.3, from 6,500 unit-days.
- **With 21 events the bands are wide.** Read the pattern, not single days.

## 9. Regional wind as a third instrument (2026-10-05)

`analysis/regional_wind_offer_test.py` → `outputs/tables/regional_wind_offer_results.csv`.

**Index.** On an hour when Galicia is windy and Aragón calm, a firm whose farms sit
in Galicia sells more than one whose farms sit in Aragón, at the same national wind.
The instrument is that difference, in GW:

    Wdev_gt = sum over regions r of  K_gr × (cf_rt − cf_t)

- K_gr: the group's located onshore wind in region r (`renewable_unit_locations`,
  54% of wind GW, regions from Eurostat's NUTS polygons);
- cf_rt: the region's measured wind output (ESIOS 1159, by province) over its wind
  capacity that month (ESIOS 1485); cf_t the same for the peninsula.

Wdev is zero when wind is spread across regions as capacity is. The forecast
version splits REE's D-1 national wind forecast (1777) by the realised regional
shares: the national level is what bidders knew, the split is realised.

**Why the deviation and not the level.** National wind lowers every firm's n by
pushing its gas and hydro out of the dispatch, by a different amount per firm
(`rq-forecast-first-stage.md`). The level of own wind carries that displacement
(F 0.1). The controls take out each group's response to REE's D-1 forecasts of
wind, solar and demand, one slope per group and forecast.

**Six groups have located wind.** Iberdrola (Castilla y León 1.5 GW, Castilla-La
Mancha 1.1, Andalucía 0.7, …), Endesa (Aragón 0.8, …), Naturgy, EDP, ENGIE, and
Repsol (Aragón 0.4 only). Hourly SD of Wdev: Iberdrola 0.13 GW, Endesa 0.08, the
others 0.02–0.06. Each group's Wdev correlates −0.14 to 0.22 with the national
forecast.

**Local grid constraints.** A region's wind can reach a thermal unit's offer through
technical constraints, not through its owner's n. Two answers:

- A: technology × date × hour effects, plus the capacity factor in the unit's own
  region as a control;
- B: technology × region × date × hour effects, so a unit is compared only with
  units of the same technology, region and hour owned by other groups.

Thermal units with a plant-specific cost, unit × week effects, week clusters,
2019-01 → 2026-05 (REE's forecasts start in 2019). Offer price at 50% of offered
volume; the 25% point and offer minus `c_bid` agree in sign.

| instruments | effects | first stage (X per GW) | β | 95% set (AR) | p, β = 1 | F |
|---|---|---|---|---|---|---|
| regional wind, forecast | A | +4.18 (0.85) | +0.88 | [−2.59, 4.53] | 0.94 | 24.1 |
| regional wind, measured | A | +4.60 (0.87) | +1.37 | [−1.65, 4.70] | 0.81 | 27.8 |
| **regional (forecast) + outages** | A | | **−1.56** | **[−4.32, 1.51]** | 0.10 | 13.3 |
| regional wind, forecast | B | +3.97 (0.85) | +2.31 | [−2.13, 7.28] | 0.55 | 22.1 |
| regional wind, measured | B | +4.39 (0.87) | +2.74 | [−1.11, 7.23] | 0.37 | 25.7 |
| regional (forecast) + outages | B | | −1.21 | [−4.09, 2.99] | 0.18 | 14.2 |

A: 2.51 M unit-hours, 64 units; B: 2.39 M, 62 units (region-hour cells with a single
owner drop out).

- **The first stage is strong and the right size.** One GW more wind on a firm's
  own farms than the national rate raises its X by about 4 €/MWh (F 22–28). A GW of
  its reactors going down lowers X by about 5 (§4). Adding or removing a GW of the
  firm's own output moves X by about the same amount, from two unrelated sources.
- **Regional wind alone gives a positive β**, +0.9 to +2.7, and its set contains
  0 and 1. Outages and rain gave negative point estimates. The sets overlap, so the
  instruments do not contradict each other, and none of them narrows β.
- **With the outages, β is −1.2 to −1.6**, sets [−4.3, 1.5] and [−4.1, 3.0]: no
  narrower than outages with rain (§7).
- **From 2022 on the instrument is weak** (F 3–8: 47 units after the coal plants
  closed, half the hours). Its estimates there say nothing; the first stage,
  +2.7 (1.4), is within one standard error of the full sample's.
- **Limits.** Farm locations and owners come from a 2026 snapshot, so farms built
  after 2018 count from the start; that is error in the instrument, not a reason for
  it to move offers. Only 15% of Cataluña's wind is located.

### 9.1 Rerun with 78.5% of wind located (2026-10-06)

The table above uses the first location pass (54% of onshore wind GW). Two further
passes (`build_renewable_locations_v2.py`, `_v3.py`; OSM turbines grouped into farms,
then MITECO's Electra register by community) locate 78.5%. **The third pass is the
main specification from here on**, fixed before the rerun; `--locations=v1` reproduces
the table above (`regional_wind_offer_results_v1loc.csv`).

Each group's index on old and new locations: correlation 0.99 for Iberdrola and
Endesa, 1.00 Repsol, 0.93 Acciona, 0.89 Naturgy, **0.62 EDP**; its hourly SD rises
most for EDP (0.021 → 0.036 GW) and Acciona (0.053 → 0.079). Where the new farms sit
in the regions the old ones did, the index is only rescaled, which changes nothing.

| instruments | effects | first stage (X per GW) | β | 95% set (AR) | p, β = 1 | F |
|---|---|---|---|---|---|---|
| regional wind, forecast | A | +3.91 (0.75) | +1.49 | [−1.61, 4.99] | 0.75 | 27.0 |
| regional wind, measured | A | +4.46 (0.77) | +2.24 | [−0.34, 5.37] | 0.35 | 33.4 |
| **regional (forecast) + outages** | A | | **−1.03** | **[−3.14, 1.53]** | 0.09 | 14.1 |
| regional wind, forecast | B | +3.71 (0.74) | +2.71 | [−1.24, 7.36] | 0.39 | 25.0 |
| regional wind, measured | B | +4.26 (0.76) | +3.37 | [0.07, 7.45] | 0.16 | 31.4 |
| regional (forecast) + outages | B | | −0.80 | [−2.91, 2.99] | 0.16 | 14.8 |

- **F rises 4–22%, the sets narrow 7–20%, and no conclusion changes.** Every main
  set still contains 0 and 1. The forecast version's β moves +0.6, within one
  standard error (1.7).
- **Measured wind in B now excludes 0**, [0.07, 7.45]. It is a check, not the main
  specification, and measured output includes what farms shed at low prices.
- **From 2022 on it is still weak** (F 3–10).
- **In the step estimator** regional wind alone stays useless on thermal steps
  (F 0.08) and gains most on hydro steps: [−0.83, 0.38] → [−0.61, 0.31], F 10.8 → 14.4
  (`rq-step-estimator.md` §6), as EDP's index changed most.
- **Reading.** 45% more located capacity bought little precision for gas and coal:
  the limit is how much regional weather moves a diversified portfolio, not the
  locations.

## 10. Where this leaves the across-day margin

- **Three instruments move X and the offers do not follow clearly.** Outages (F 121
  on n at the firm level, ≈ 10–15 on X at the unit level), rain (F 9.5) and regional
  wind (F 22–28).
- **β = 1 is rejected only on all units** (§6). On thermal units every set contains
  0 and 1: outages with rain [−4.0, 1.8], regional wind [−1.6, 5.0], regional wind
  with outages [−3.1, 1.5] (§9.1; on the first location pass [−2.6, 4.5] and
  [−4.3, 1.5]).
- **The point estimates split by instrument**: negative from outages and rain,
  positive from regional wind. The negative ones do not come from withdrawal of
  volume (offered share flat), location (§6), or the timing of trips (§8). With
  sets this wide, thermal offers do not pin β between price-taking and Nash.

