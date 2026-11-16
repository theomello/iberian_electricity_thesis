# GoiEner placebo drift: why the household placebo is centred at -0.093 (proposal)

**Status: proposed 2026-11-16, not registered. Binding when the user confirms and this file is committed; the run follows that commit.** Follows the G2 result in `2026-11-17-goiener-household-design.md`: household raw η -0.146, placebo windows centred at -0.093 (η_RI -0.053), against E0 placebo centred at -0.003.

**In one example.** Suppose households slowly shift their evening use to off-peak by about 3% a year for reasons unrelated to the reform (heat pumps, EV charging at night, more night washing). A model trained on 2018-2019 and used to forecast summer 2021 will over-predict the peak share in 2021, and the 'response' it reports includes two years of that drift. The placebo windows (2018 and 2019, forecast from a model trained on the other year) are inside the training span, so they would show only half a year of it, or none. If that is what is happening, the placebo is centred away from zero for a reason that does not apply the same way to the real window, and the right centring is a *forward* placebo.

## What is computed (no reform window is touched)
1. **D1 Raw drift (descriptive, no model).** Per household, the mean of log(peak kWh) minus log(off-peak kWh) over weekday non-holiday days in April-October, by year 2018, 2019 and 2021 (the 2021 months restricted to June 1 -> September 15 and the same months in the other years), after removing the household's month means; the change 2018 -> 2019 and 2019 -> 2021, with the same changes for Portugal (REN) and for E0 subtracted. Standard errors clustered by household.
2. **D2 Forward placebo.** The G2 pipeline (per-household LASSO, paper specification) trained only on weekdays **before 2019-04-01** (about 15 months; households with fewer than 150 training weekdays dropped) and used on the weekdays of the 2019 season-matched windows (the 13 windows starting within ±45 days of 1 June 2019); Portugal and E0 through the same forward fit. Pooled response per window as in G2.
3. **D3 Matched-length leave-year-out.** The leave-year-out placebo of step zero repeated with the same training length (15 months before the window year-end excluded), only to separate 'forward' from 'less data'. Run only if D2's mean differs from the leave-year-out mean by 0.03 or more.

## Rules, set before the run
- **D1 reading.** The mean household drift 2018 -> 2019 (Portugal and E0 netted) is reported with its interval; no pass/fail.
- **D2 centring.** Let m_fwd be the mean pooled forward-placebo response (13 windows) and m_loy the leave-year-out mean (-0.0927). If |m_fwd - m_loy| < 0.03, the forecast direction does not explain the offset and the -0.093 is a property of the household placebo itself (selection, imputation, or the placebo years); if m_fwd is more negative than m_loy by at least 0.03, the drift is partly a forward-forecast effect and the **forward-centred η_RI is reported as the headline** with the leave-year-out one beside it.
- **D3 Reform response against the forward placebo.** The G2 real-window response minus m_fwd, divided by the dose 0.784: reported with the Fisher-style interval from the 13 forward placebos (the smallest one-sided p the 13 windows can give is 0.071, so no p-value rule; the rule is that the interval excludes zero and the point is negative).
- **D4 Aggregate check.** The same forward placebo for E0: its mean within 0.03 of zero (the E0 leave-year-out placebo was -0.003).
A failed rule is recorded and kept; no other training window is tried.

## What each outcome means
D2 'forecast direction matters' and D3 negative with interval excluding zero: the household elasticity is the forward-centred η_RI, probably between the raw -0.146 and the leave-year-out -0.053, and the thesis says why the placebo was re-centred. D2 'does not matter' and D3 fails: the -0.093 offset is not a trend and the household response after centring stays at -0.053 with the caveat that the placebo is not centred on zero for reasons unknown; the headline then relies on the aggregate E0 instead. D3 fails with D2 'matters': most of the raw household response is drift; the household data do not support a response distinct from the trend.

## Threats
Only 2019 windows (13, overlapping, about one independent season) are available for the forward placebo, so intervals are wide; 15 months of training is much less than the 24+ months used for the real window, so forward errors are noisier; the 2019 seasonal pattern may differ from 2021 (COVID aftermath, 2021 weather); the cooperative's customer base changed over time (selection by contract start is partly handled by requiring pre-lockdown presence).

## Data and code
`data/goiener/daily/daily.parquet`, the G2 outputs, the Portuguese and E0 series as in `goiener_household.py`. New code `scripts/analysis/goiener_drift.py` (imports `goiener_household.py`); outputs `outputs/tables/goiener_drift.csv`. Seed 20261117, same 3,000-household subsample.

## Amendment 2026-11-16 (after discussion with the user): D1 runs first, and a first-differencing DiD is added. Binding when committed; both are cheap (no LASSO).

**Order and stop rule.** D1 and the first-differencing DiD (F1-F3 below) run first. D2 and D3 (forward LASSO placebo) run only if the gate **D0** says drift is a live explanation.

**Sample for D1 and F.** Household days = weekday, non-holiday (national) days of the three windows **June 1 -> September 15 of 2018, 2019 and 2021**; households need at least 40 such days in each of the three windows. Outcome per day: log(peak kWh) minus log(off-peak kWh). Households: (a) the G2 subsample (the same 3,000 selected households, those with enough days) as the primary, (b) all eligible 2.0TD households as a check. Portugal (REN, same period types, Portuguese holidays) and E0 (Spanish regulated load, national holidays) through the same daily log ratio. Dose 0.784 (pure 2.0TD) for households and Portugal, 0.609 (E0 mix) for E0, as in G2.

- **D1 Raw levels and drift (descriptive).** Household mean log(peak/off) in each window, the change 2018 -> 2019 (**drift19**, one year, window dates identical) and 2019 -> 2021 (**change21**), each net of Portugal's change; household-cluster bootstrap intervals (2,000 draws; Portugal and E0 treated as fixed numbers).
- **F1 First-differencing DiD.** eta_FD = change21 (net of Portugal) / 0.784 with its bootstrap interval. No weather adjustment.
- **F2 Drift-adjusted.** eta_FD_adj = (change21 - 2 × drift19) / 0.784 (two years of drift assumed linear, as drift19 is one year), with its bootstrap interval; also reported with one year of drift subtracted (assumes drift stops after 2019).
- **F3 Comparison (description, no pass/fail).** Whether the F1 and F2 intervals contain the G2 raw value (-0.146) and the G2 centred value (-0.053); the same transformation for E0 (G2: -0.106 centred, -0.109 raw) as a check that the DiD reproduces the aggregate answer.
- **D0 Gate for D2/D3.** Drift is a live explanation, and D2/D3 are then run, if the household drift19 net of Portugal, converted to elasticity units (drift19 / 0.784), is larger than 0.02 in absolute value **or** its 95% interval excludes zero. If both conditions fail (|drift| <= 0.02 and the interval contains zero), drift over one year does not explain the placebo offset, D2 and D3 are not run, and the -0.093 offset is recorded as a property of the household placebo whose cause is unknown.

**What each outcome means.** D0 'live': a year-to-year trend in the household peak/off ratio exists; F2 then gives a drift-robust elasticity and the forward LASSO placebo (D2) is the like-for-like check. D0 'not live': the placebo offset is not an annual trend; the headline is the centred η_RI -0.053 with the caveat, and F1 is the cross-check. F1 close to -0.146: the raw response is largely real. F1 close to -0.053: the centring was right.

**Threats of F.** Weather differs between the three summers (the LASSO adjusts for it, this DiD does not); the drift estimate comes from one year-pair (2018 -> 2019) and is noisy; 2021 had COVID aftermath in working-from-home patterns, which may move the peak/off ratio of households independent of the reform (Portugal nets part of it); cooperative customers may have changed over time (composition), partly handled by requiring days in all three windows.

Code: `scripts/analysis/goiener_drift_d1.py`; output `outputs/tables/goiener_drift_d1.csv`; seed 20261117.
