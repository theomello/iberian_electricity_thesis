# Replication on the paper's unit of observation: regulated retailers' demand by area

**Status: pre-registered 2026-11-12, before any estimation on the panel.** Branch `tou-policy-prices`. Panel: `scripts/build/build_regulated_area_panel.py` (`d261245`, `docs/tou-policy-sources.md`, last section). Paper: Enrich, Li, Mizrahi and Reguant (JEEM 2024), `papers/md/4-time-of-use-impacts-enrich-li-mizrahi-reguant.md`.

**In one example.** The paper does not study one national series. It studies the hourly demand of each distribution group's regulated retailer (Endesa, Iberdrola, Naturgy, EDP, Repsol) against Portugal's regulated supplier, one LASSO per area and hour, errors compared before and after 1 June 2021. We now hold those units, so the same design can run on the same kind of object, with five treated units instead of one.

**Goals.** (1) Replicate the paper's period effects (their LASSO, weekdays: mid-peak −6.4%, peak −9.5%; off-peak not significant) and their elasticity range (−0.082 to −0.135) on the rebuilt panel. (2) Test that our national results (E0 −3.8% evening versus night; regulated-only −3.9%) are consistent with the area results. **Not goals:** per-capita figures (counts not on disk), industry, anything after 2021-09-14.

## Data and what differs from the paper
Panel: five Spanish areas (`ENDESA, IBERDROLA, NATURGY, EDP, REPSOL`), Portugal (`EDPUC2`), hourly, 2018-01 → 2021-09-14, PDBF purchases (a schedule, not metered load; they sum to ESIOS 352 within 1%). Not in our version: **(a) consumer counts** (the paper's per-capita variable and regression weights: CNMC data not on disk; the CNMC's published supervision reports give annual counts, quarterly by group not found); **(b) area weather**: baseline here is the national population-weighted temperature (ERA5) with area fixed effects; area-specific weather by territory is a sensitivity only if the territory mapping is verified from a source; **(c)** Portugal's unit is the regulated supplier's purchases, as the paper's, rather than national consumption. Weights: the mean of the area's load over the pre-window (a stand-in for consumer counts), with unweighted beside.

## Design
- **Step 1:** the paper's LASSO (`tou_lasso_paper.area_errors`): one model per area and hour, calendar and temperature interactions, 10-fold cross-validation with the one-standard-error rule, no trend, trained 2018-01-01 → 2020-12-31 without March–June 2020; log load in place of log load per capita.
- **Step 2:** DiD on the errors, Spain's five areas against Portugal, period types as the paper (off-peak, mid-peak, peak by the new 2.0TD schedule; weekends and holidays off-peak), post 2021-06-01 → 2021-09-14, weekdays and weekends separately (their Table 5), clustered by area × month-of-sample. Evening-versus-night triple difference as in the national work, for comparison with E0 and ESIOS 352.
- **Elasticity (their Equation 4):** error on ln PVPC price (ESIOS 1013 to May 2021, 1001 from June 2021; one price for all Spanish areas, constant for Portugal), instrument ln(charge + average pre-policy energy cost) (`tou_elasticity_paper` machinery), fixed-effect columns 1 to 4 as before, area-month clusters.
- **Placebo:** the 18 fake break dates of the national work applied to the area errors (cross-fitted), and the 2019 calendar with the real charge pattern.

## Stop rules, set before any run
1. **Panel validity.** The Spanish areas' monthly mean sums to ESIOS 352 within 1.5% in every month 2018-01 → 2021-09 (checked at build: passes; re-checked on the final sample).
2. **Period effects.** Weekdays: peak effect negative with t ≤ −2 and between −3% and −15%; mid-peak negative with t ≤ −2; off-peak absolute effect below 3%.
3. **Placebo.** The real weekday peak effect ranks in the top 3 of the 18 placebo break dates by absolute size, and the 2019 calendar placebo has t > −2.
4. **Areas.** The weekday peak effect is negative in at least four of the five Spanish areas (EDP and Repsol are small and noisy; a sign flip there alone does not fail the rule).
5. **Elasticity.** Column 4: negative, t ≤ −2, between −0.20 and −0.05 (the paper's range is a check, not the bound); first-stage F ≥ 10. Columns 1 to 3 reported; the earlier national finding (weak first stages in 1 to 3) is stated as a prior, not a rule.
6. **Consistency with the national result.** The evening-versus-night DDD of the pooled areas is within 1.5 points of the ESIOS 352 paper-LASSO value (−3.9%, se about 0.4; same units, so a failure here is a coding error or a weighting artefact).
7. **Robustness.** Dropping Endesa (largest area) moves the pooled peak effect by less than 2 points; unweighted and pre-mean-weighted effects differ by less than 2 points; Portugal's national consumption in place of the regulated unit changes the peak effect by less than 2 points.

## What each outcome means
All pass: the paper's design reproduces on its own unit of observation and the national results are consistent with it; the thesis can carry the area panel as the main replication and E0 as the extension to all low-voltage customers. Rule 2 or 3 fails: the replication does not hold on schedule data, and the likely cause (a retailer schedule is a forecast of load, see the replication spec) is stated; E0 (measured demand) remains the headline. Rule 6 fails: coding error first, then weighting.

## Threats
PDBF is a day-ahead schedule: a retailer's load forecast, which cannot show a response it had not forecast (the paper uses REE's hourly demand of the same units, which may be a later stage). Customer counts are not in the panel; regulated customers left the segment (the paper: −4% January to September 2021) and Portugal's share moved differently, which area-month fixed effects absorb only if common; counts would fix this. National weather in place of area weather loses regional heat and cold. Three areas have source gaps of whole days (EDP 6 days, Repsol 18, other 9; Portugal 1). Five treated units give few clusters for inference on the area-level rule (rule 4) and none for area-level standard errors.
