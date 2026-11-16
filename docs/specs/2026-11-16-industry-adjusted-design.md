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
