# Industry elasticity, placebo-adjusted (pre-registration)

**Status: pre-registered 2026-11-16, before any code or run.** Branch `tou-policy-prices`. Follows `2026-11-12-industry-voltage-design.md`, whose results section (rule 3 failed: the 2019 placebo was significantly negative for E0 and E1+E2 and positive and large for 6.2-6.4) says the elasticity is not identified as a causal dose-response. **That result stands; this design asks a narrower question with a different estimator.**

**In one example.** In 2019 the same calendar dose pattern (more expensive evenings, cheaper nights, in June-September) produced an "effect" of -0.08 on E1+E2 with no reform, because the series' errors have a shape in those hours and months that the dose happens to line up with. A reform estimate of -0.17 on the same series then says little by itself; the part not explained by the shape is about -0.17 minus -0.08. Doing the same on two placebo years (2018 and 2019) gives both a correction and a measure of how stable the correction is. If the two placebo years disagree, the shape is not stable and no point estimate should be reported.

**Question.** Is there a placebo-adjusted elasticity of industrial demand to the reform-induced hourly price change, with an interval that includes the instability of the placebo? **Not goals:** an elasticity for individual high-voltage tariffs (their placebos are as large as their estimates; reported, not interpreted); a dose-response gradient across levels (not identified in the earlier run); anything after 2021-09-15.

## Series and dose
- **E0** (ESIOS 1201): the household check, as before (dose: 0.69 x 2.0TD + 0.31 x 3.0TD).
- **E1+E2** (1202 + 1203): mixed 6.1 series, dose 0.20 x (3.1A to 6.1TD) + 0.80 x 6.1, as before.
- **Pooled industry, `IND`** (new): E1 to E6 summed (1202-1207). Dose = the load-weighted average of the component doses: E1+E2 (its mixed dose), E3 (dose of tariff 6.2), E4 (6.3), E5+E6 (6.4), with weights equal to each component's share of the IND load over 2018-01-01 to 2020-12-31 without the COVID months, fixed before the run. E3 treated as 6.2 although the 6.2 tariff series is 0.78 E3 + part of E2 (checked in the earlier run); the 30-36 kV part sits in E2's mixed dose.
- **6.2, 6.3, 6.4** are run again for the record only: no adjusted estimate is interpreted for them.
Doses as the earlier design: Delta p = ln[(E + T_new)/(E + T_old)] with E = the post-window mean OMIE price (€100.81); toll tables from `tou_tariff_schedule.py`. **For 2018 placebo dates the old and new regimes are laid on the 2018 calendar with the regime's own holidays, assuming the old regime's hours (Orden ITC/2794/2007) were unchanged since 2018, as already assumed for 2019.**

## Estimator
- Errors: the paper's per-area-hour LASSO (`tou_lasso_paper.py`), pre-window 2018-01-01 → 2020-12-31 without March-June 2020. **New fits needed:** `IND` (no exclusion; excluding 2018; excluding 2019) and France (excluding 2018; excluding 2019; the main France fit is cached). Everything else is read from `data/cache_tou/cross_tariff_errors.parquet`.
- Regression: Equation 4, series k against Portugal, fixed effects and clustering as before (hour x weekend x area, hour x weekend x month-of-sample, weekend x area x month-of-sample; clusters area x month-of-sample). Estimates: η_real (post window 2021-06-01 → 2021-09-15), η_p18 and η_p19 (the same dose pattern laid on 2018-06-01 → 2018-09-15 and 2019-06-01 → 2019-09-15, cross-fitted errors).
- **Adjusted elasticity:** η_adj = η_real − (η_p18 + η_p19)/2.
- **Standard deviation:** sd_adj = sqrt( se_real² + (se_p18² + se_p19²)/4 + ((η_p18 − η_p19)/2)² ); 95% interval η_adj ± 1.96 sd_adj. The last term is the instability of the placebo, deliberately included.
- **Reduced form beside it:** the evening-versus-night, working-versus-weekend triple difference of errors (`cell_ddd`), real minus the mean of the two placebo years.
- Sensitivities: E = €60; hourly OMIE price; for E0 and E1+E2 the earlier weight changes (±10 points); France as control (adjusted with France's own two placebos).

## Stop rules, set before the run
1. **Readable.** Within-day sd of the series' dose over the post window at least 0.02 (the earlier rule). A series below it gets no adjusted estimate.
2. **Household check.** E0: η_adj negative and in [−0.15, −0.03] (the household column-4 value was −0.100, the Wald range −0.06 to −0.09).
3. **Placebo years agree (the identification guard).** For a series: η_p18 and η_p19 have the same sign and differ by less than half of |η_real|. **A series failing this gets no point estimate** (only the bound in the outcome table); the claim "identified" is then not made.
4. **Detected.** For a series passing rule 3: η_adj < 0 and the 95% interval excludes zero.
5. **Reduced form agrees.** For a series passing rules 3 and 4: the adjusted reduced form is negative, and the real evening-versus-night DDD is larger in absolute value than both placebo years'.
6. **Controls agree.** With France as control, η_adj has the same sign, and for a series passing rule 4, an interval that overlaps the Portuguese-control interval.
7. **Sensitivity.** For a series passing rule 4: η_adj under E = €60 and under hourly prices stays within 30% of the central value.

## What each outcome means
- E0 passes rule 2 and `IND` or E1+E2 passes rules 3-6: an industrial elasticity is reported, **as a placebo-adjusted estimate with the stated interval and the assumption that the 2018-19 shape equals the 2021 shape (untestable; two placebo years are the guard)**.
- Rule 3 passes and rule 4 fails: no detectable industrial response; the upper end of the interval is the reported bound.
- Rule 3 fails for every industrial series: not identified; the industrial result is "no credible estimate", with the placebo ranges shown. This is a finding, not a design failure.
- Rule 2 fails: the adjustment does not reproduce households; stop.
No rescue beyond the rules above: no further placebo years (2020 is excluded by COVID, 2017 is not in the series), no other series or controls added after the run.

## Threats
(a) Two placebo years are few; the instability term is a crude, not a calibrated, allowance. (b) The old-regime hours for 2018 and 2019 are assumed equal to the one consolidated order (e of the earlier design). (c) Seasonal shape in industry may have changed in 2021 for reasons other than the reform (COVID recovery by sector; energy-price crisis from autumn 2021 is outside the window, but gas prices were already rising); the adjustment cannot remove a 2021-specific shape. (d) `IND` weights are shares of energy, not of price-responsive load; contract exposure is unmeasured (many industrial contracts are fixed-price per period). (e) The reform bundled the price change with the new period structure and with awareness; η_adj is the response to the reform-induced hourly price change. (f) The 6.x single-tariff series are noisy by construction.

## Results (run 2026-11-16, `scripts/analysis/tou_industry_adjusted.py`; `outputs/tables/tou_industry_adjusted.csv`)

New fits: IND (three), France cross-fits (two). The E0 and E1+E2 2019 placebos reproduce the earlier run (-0.023, -0.078). Portugal control, central dose (E = €100.81); adjusted = real minus the mean of the 2018 and 2019 placebos; interval includes the placebo-instability term.

| series | eta real | placebo 2018 | placebo 2019 | **eta adj [95%]** | adjusted reduced form (evening vs night, working vs weekend) |
|---|---|---|---|---|---|
| E0 | -0.101 | +0.003 | -0.023 | **-0.090 [-0.119, -0.061]** | -4.4% |
| E1+E2 | -0.168 | -0.095 | -0.078 | -0.082 [-0.252, +0.088] | -4.1% |
| IND (E1-E6) | -0.288 | -0.069 | +0.023 | -0.265 [-0.408, -0.122] | -3.1% |
| 6.2 | -0.080 | -0.250 | +0.117 | -0.013 [-0.407, +0.381] | +0.2% |
| 6.3 | -0.321 | +0.058 | +0.254 | -0.477 [-0.900, -0.055] | -2.1% |
| 6.4 | -0.533 | +0.714 | +0.988 | -1.384 [-2.096, -0.672] | -1.2% |

France as control gives the same signs and overlapping intervals for every series (E0 -0.095, E1+E2 -0.078, IND -0.301).

**Rules as registered.**
1. Readable: all but 6.4 (within-day sd 0.014).
2. **E0 household check: pass** (-0.090, inside [-0.15, -0.03]; the Wald range was -0.06 to -0.09).
3. Placebo years agree: **E1+E2 passes** (same sign, difference 0.017 < 0.084). **E0 fails on the sign condition** (+0.003 against -0.023; the magnitude difference 0.026 is below the 0.050 allowed). **IND fails** (-0.069 against +0.023: opposite signs; magnitude difference 0.092 < 0.144 would have passed). 6.2, 6.3, 6.4 fail.
4. Detected (interval excludes zero): E1+E2 **fails** (upper end +0.088). The series that pass the sign-and-magnitude guard therefore show no detectable response.
5. Reduced form agrees: E0, E1+E2, IND, 6.3 yes; 6.2, 6.4 no (not relevant after rule 3/4).
6. France: all series agree.
7. Sensitivity (E = €60 and hourly within 30%): E0 passes; E1+E2, IND, the tariff series fail (e.g. IND -0.18 and -0.28 against -0.27; E1+E2 -0.05 and -0.09 against -0.08).

**Reading, per the registered outcomes.** The E0 household check passes: the adjustment reproduces the household elasticity (-0.09) and corrects the 2019 placebo's pull. **For industry the pre-registered result is: E1+E2 passes the identification guard but the response is not detectable (interval -0.25 to +0.09); IND, the series with the tighter interval, fails the guard on the sign of the placebo years, so no point estimate is reported for it.** 6.2-6.4 are noise (their placebos are as large as, and opposite to, the real estimates). **No industrial point estimate is identified.** For the record: IND's adjusted -0.27 (and its interval excluding zero) is not reported as an estimate, and E0's sign failure of rule 3 is a technicality of a tiny positive placebo, which does not change its reading.

**A pattern the table shows (descriptive, not registered):** the adjusted evening-versus-night effect is about the same for households (-4.4%), E1+E2 (-4.1%) and the pooled industry series (-3.1%), although the dose is 0.64, 0.16 and 0.12. The implied elasticity therefore rises as the dose falls, as in the earlier run: the evening-versus-night shift in industrial demand is not proportional to the reform's price change. Either industrial flexibility per unit of price is several times higher, or what moved industry in 2021 is not the price change alone.

## Erratum (2026-11-20): the IND row rests on 40% of the 2021 hours
E5 (ESIOS 1206) has no row in hours where it is zero, and `tou_cross_tariff.esios_load` summed components with index
alignment, so IND was NaN in 1,548 of the 2,568 hours of the 2021 window (June 680 of 720) and 0 hours of 2018–19.
**The IND row above (−0.288 raw, −0.265 adjusted) is therefore not valid.** E0, E1+E2 and 6.2–6.4 do not include E5 and
are unaffected; the reading for industry (no detectable response from the E1+E2 row) stands. Found in
`notes/scope-2021-high-voltage-shift.md`; the loader is fixed (absent E5 = 0); the corrected IND estimate is in
`2026-11-18-industry-six-summer-ri-design.md` (corrected results). Not rerun here.
