# Household smart-meter extension with the GoiEner data (proposal)

**Status: proposed 2026-11-17, not registered. Binding when the user confirms and this file is committed; step zero (G0, G1) runs first and decides whether anything further is estimated.** Data: `docs/data-reference/goiener-household-smart-meters.md` (fetched 2026-11-17, not yet extracted; one CSV per supply point with `timestamp, kWh, imputed`, imputed series).

**In one example.** One household in Gipuzkoa used 0.87 kWh at midnight and 0.4 kWh at 8 pm in May 2021. The same household in July 2021, after the tariff made 8 pm dear and midnight cheap, used 0.6 at midnight and 0.3 at 8 pm. By itself that is nothing: it could be the weather. Averaged over 14,000 households and compared with what each household's own weather-and-calendar model predicted, and with the same exercise in Portugal, it can be a measured response. The extension asks what a household-level sample adds to the aggregate result: (i) does the response replicate at household level, (ii) does it scale with the dose across customers on different tariffs (2.0TD against 3.0TD, aggregate doses 0.78 against 0.31), (iii) does it vary across households.

## Design
- **Sample.** Supply points of `metadata.csv` with series in both the pre-lockdown file (`imp-pre`, up to 2020-02-29) and the post file (`imp-post`, from 2021-05-31), tariff `2.0TD` or `3.0TD` (the main groups), at most 10% missing or imputed samples in the pre-period months used and in the window; `self_consumption_type` missing (no declared self-consumption) in the main run, self-consumers in a robustness run.
- **Outcome.** Weekday (non-holiday) daily kWh summed over the paper's period types: peak (10-14 and 18-22), mid, off-peak (0-8); log of the daily sum. Per household and period type, a LASSO (the paper's per-period specification: month dummies, weekend, holiday, mean, minimum and maximum temperature and their interactions; 10-fold one-SE, `tou_lasso_paper.fit_one_se`) trained on the household's pre-lockdown days; errors on the window 2021-06-01 → 2021-09-15 (out of sample). Temperature: the nearest population-weighted city series (Bilbao for Gipuzkoa, Bizkaia and Araba, Pamplona for Navarra, Madrid for Madrid; other provinces dropped from the main run).
- **Control.** Portugal's regulated-unit error for the same period types and days, cross-fitted by year (the series already built for the aggregate run); household response = (household error − Portuguese error), contrast = peak minus off-peak.
- **Dose.** The paper's convention (mean window energy price €100.8/MWh), the household's tariff as pure 2.0TD (0.784) or 3.0TD (0.311). The household retail price is not in the data (free-market contracts); the dose is an assumption, as in the aggregate run.
- **Pooled statistic.** The mean peak-minus-off response of the group divided by the group's dose contrast: a contrast elasticity, computed identically for E0 (aggregate) so the two are comparable.
- **Placebo and inference.** The same pipeline on the season-matched placebo windows of the RI run (26 windows starting within ±45 days of 1 June in 2018 and 2019; household LASSO trained leave-year-out on the other pre-lockdown days); p-values and Fisher-style intervals by rank among the placebo windows, as in `2026-11-17-randomization-inference-design.md`.
- **Heterogeneity.** A regression forest (R `grf::regression_forest`) of each household's window response on covariates: tariff, contracted power (`p1`, `p2`), baseline consumption and its peak, evening and night shares in the pre-period, the household's own temperature response, tenure (contract start), province, activity code (CNAE group), self-consumption flag, number of missing days. Calibrated against placebo windows: the same forest pipeline on each placebo window's household responses gives the null distribution of the spread of out-of-bag predictions.

## Step zero (no response is estimated or printed)
- **G0 Panel feasible.** At least 8,000 households satisfy the sample rule, and the median imputed share is at most 10%.
- **G1 Noise.** The standard deviation across the 26 placebo windows of the pooled 2.0TD peak-minus-off response gives a detectable contrast elasticity (2.8 × sd / dose contrast) of at most 0.05. If not, stop: the household sample is too noisy for even the pooled result.

## Rules for the estimates (only if G0 and G1 pass)
- **G2 Replication.** The pooled 2.0TD contrast elasticity is in [−0.20, −0.03] with one-sided randomization p ≤ 0.05; the E0 value from the same transformation is reported beside it, with the difference between the two (no band on the difference).
- **G3 Dose-response.** The 3.0TD contrast elasticity (637 households) minus the 2.0TD one, with its randomization p and interval, and the ratio of responses against the dose ratio 2.5. Classification fixed now: *consistent with a common elasticity* if the gap's two-sided p > 0.10 and the detectable gap is below 0.10; *different* if p ≤ 0.10 in all-window and season-matched sets; *uninformative* if the detectable gap exceeds 0.10 (as in the group comparison).
- **G4 Implied household mix.** If G2 and G3 pass without a 'different' result, the 2.0 share `w` implied by the E0 response and the GoiEner elasticity (`R_E0 = η (w d2 + (1−w) d3)`), with an interval from the placebo windows; descriptive, because GoiEner customers are not representative.
- **G5 Heterogeneity.** Out-of-bag spread of the forest's predictions above the 95th percentile of the placebo spreads, `test_calibration` differential coefficient > 0 with p ≤ 0.05, and stability (second seed rank correlation ≥ 0.7). If any fails, no household-heterogeneity claim.
- **G6 Robustness.** G2's sign and band hold excluding households with declared self-consumption, with at least 24 pre-months, and with 2.0TD households of Gipuzkoa and Bizkaia only.
No other specification is tried after a failure.

## What each outcome means
G0-G2 pass: the paper's household elasticity is replicated on household data with a randomization test, the first micro-level support. G3 'consistent': the dose scale is common across tariff groups, which supports the dose construction and narrows the range of the aggregate (G4). G3 'different' or 'uninformative': the aggregate dose assumption cannot be refined with this sample and is reported as it is. G5 passes: a heterogeneity result the paper does not report, tied to named household characteristics. G1 fails: the household sample adds no power over the aggregate and the design stops there.

## Threats
Cooperative members on free-market contracts in the north: selection and unknown pass-through of the reform to the energy price they paid; the household tariff is the current one, not necessarily the pre-reform one (2.0DHA, 2.0A households appear as 2.0TD only after the reform); imputed series (the `imputed` flag allows dropping days; the flag share is a G0 check); one reform window and the 2022 price crisis begin soon after (the window ends 2021-09-15); temperature from a city series, not the household's location; the Portuguese control is an aggregate, not matched households; with only two dose values, the dose-response is a two-group comparison.

## Data and code
`data/goiener/raw/metadata.csv`, `imp-pre.tzst`, `imp-post.tzst` (extract only the selected households' files to `data/goiener/csv/`, gitignored; about 10 GB free is needed), the RI placebo windows, the Portuguese errors (`cross_tariff_errors`, `cross_tariff_ri_errors`), temperature files. New code: `scripts/build/build_goiener_daily.py` (extract and daily period sums), `scripts/analysis/goiener_noise.py` (step zero), `scripts/analysis/goiener_household.py` (G2-G4), `scripts/analysis/goiener_forest.R` (G5). Outputs `outputs/tables/goiener_*.csv`.

## Amendment 2026-11-17 (before any response was computed): 3.0TD and the supply-side part
**G3 and G4 are not feasible.** Of the 577 selected 3.0TD supply points, 92% start in January-February 2020 (median 2020-02-07); only 34 have 250 or more pre-lockdown weekdays and 28 pass the sample rule. The raw archive shows the same start dates. No threshold change helps, because the data are absent. G3 is recorded as *uninformative (28 households)* and G4 is dropped; G2, G5 and G6 proceed on the 2.0TD sample.

## Part B: from household response to prices and euros (only if G0-G2 pass; added 2026-11-17)
Uses the offer-curve re-clear of `hydro_levy_simulation.py` and `levy_reform_calibrated.py` (four states, hour by hour, effective offer curves; H1 identity checked there).
- **B1 Swap the input.** The pooled 2.0TD response by period type (peak, mid, off-peak), scaled to the Spanish household base (the aggregate E0 load of the window hours, energy neutral by day), replaces the aggregate DiD period effects as the extra demand of the reform-removed state. The outputs are the evening-minus-night price contrast and the reform effect on the cost per MWh, with 2,000 draws of the household response from its placebo-calibrated distribution.
- **B2 Euros per household.** For each household, the pre-period hourly baseline profile times the group response gives its counterfactual no-reform load; its wholesale-cost value is `V_i = Σ_h (L_i,h^noreform p_h^noreform − L_i,h^actual p_h^actual)` over the window hours, with the prices of the two states, reported as € per household over the window and per year. If the forest passes G5, the group response is the forest's prediction; otherwise the pooled one.
- **Rules, set before the run.**
  - **B1 Consistency.** The household-based evening-minus-night contrast has the sign of the aggregate one (−€2.39/MWh [−2.59, −2.19]) and lies within a factor of two of it (−€1.2 to −€4.8); the household-based reform effect on cost per MWh has the sign of the aggregate one (−€0.016) and is reported with its interval. If the contrast is outside the factor-of-two band, both are reported and the aggregate is not replaced.
  - **B2 Value.** The mean `V_i` is positive (a saving) with a 95% interval excluding zero; its distribution across deciles of baseline evening share is reported (no pass/fail on spread unless G5 passes).
- **What it means.** B1 consistent: the price effect of the reform rests on two independent load estimates, and the household one adds who responded. B2: the first measure in euros of what the response is worth per household, under the same static re-clear caveats as the first run (national load stands in for the household base; prices of the four-state model; no strategic reaction; household pass-through unknown).


## Results of step zero (run finished 2026-11-16 14:22; no window response computed)

**G0 pass:** 9,763 usable households (bar 8,000), median imputed share 0.0 (bar 0.10). **G1 pass:** on a random subsample of 3,000 households, the standard deviation across the 26 season-matched placebo windows of the pooled peak-minus-off response is 0.00917; dose contrast 0.784; detectable contrast elasticity **0.033** (bar 0.05).

Two features of the placebo windows, recorded because they change how G2 must be read (the registered G1 rule only uses the sd): (1) the placebo response is **not centred on zero**: the 26 pooled placebo responses run from -0.048 to -0.084 (mean about -0.07), which on the 0.784 dose is an apparent elasticity of about -0.09 before any reform exists; the real-window response must be judged against this level (randomization-inference centring, as in the aggregate design), not against zero; (2) the 26 windows are 7-day shifts of a 107-day window, so neighbouring windows overlap almost fully and the sd of 0.009 reflects a smooth drift across about two independent seasons, not 26 independent draws. G2 therefore reports eta_RI = eta_real - mean placebo with the rank-based p and Fisher interval of `2026-11-17-randomization-inference-design.md`. G2, G5, G6 and Part B wait for confirmation.

## Results of G2 (run 2026-11-16; `goiener_household.py`, committed before the run; output `outputs/tables/goiener_g2.csv`)

Same 3,000-household 2.0TD subsample as step zero (2,819 households, 216,569 household-days with window data), per-household LASSO trained on all pre-lockdown weekdays, used out of sample on the window 2021-06-01 -> 2021-09-15, Portugal's error subtracted, dose contrast 0.784 (pure 2.0TD, mean window price €100.8). Randomization inference against the 26 season-matched placebo windows.

| Series | Dose | Window response | Raw eta | Mean placebo eta | **eta_RI** | One-sided p | Fisher interval for eta_RI |
|---|---|---|---|---|---|---|---|
| GoiEner 2.0TD households | 0.784 | -0.1141 | -0.1456 | -0.0927 | **-0.053** | 0.037 | [-0.077, -0.039] |
| E0 aggregate, mix dose | 0.609 | -0.0663 | -0.109 | -0.003 | **-0.106** | 0.037 | [-0.123, -0.089] |
| E0 aggregate, pure 2.0TD dose | 0.784 | -0.0663 | -0.085 | -0.002 | -0.082 | 0.037 | [-0.095, -0.069] |

**G2 passes as registered:** the household eta_RI -0.053 is inside [-0.20, -0.03] and p 0.037 <= 0.05 (raw eta -0.146 passes the same band). Difference household minus E0 (mix dose): +0.053; the household response is about half of the aggregate one after centring.

**Caveats recorded with the result.**
1. The household placebo windows are centred at **-0.093**, whereas the aggregate E0 placebo is centred at -0.003. The centring is what moves the household estimate from -0.146 to -0.053. A household-specific placebo drift of this size is not explained by the design. One candidate: the placebo errors are cross-fitted inside the training span (leave-one-year-out) while the real-window errors are forecasts forward from the end of 2019, so any trend in households' peak against off-peak use (a growing off-peak share) enters the real window and not the placebo. This is a hypothesis, not tested.
2. p = 0.037 is the smallest value 26 windows can give (the real response is below every placebo window). The windows are 7-day shifts of a 107-day window, so they carry about two independent seasons; the p-value is optimistic.
3. The household sample is cooperative members in the north on free-market contracts, a subsample of 3,000 of 9,763 usable households, with an assumed dose.

**Reading.** Household data replicate the sign and order of magnitude of the aggregate result (about -0.05 to -0.15 depending on whether the placebo drift is netted out), with the aggregate E0 at -0.106 on the same transformation. The thesis can say the response replicates at household level and gives about half the aggregate elasticity after placebo centring, with the centring explicitly flagged. G5, G6 and Part B wait for confirmation.

## G6 results (run 2026-11-16 from the saved household errors; `goiener_g6.py`, committed before the run; `outputs/tables/goiener_g6.csv`)

The shared error run finished (2,696 households with placebo errors, 2,862 with window mid errors). Rule G6 (eta_RI in [-0.20, -0.03] and p <= 0.05) **passes in all four subsets as written** (p 0.037 each), but **the 'all' row does not reproduce G2**:

| Subset | Households | eta_raw | Mean placebo | eta_RI | Fisher interval |
|---|---|---|---|---|---|
| all (G2 sample) | 2,819 | -0.146 | **-0.038** | **-0.108** | [-0.129, -0.093] |
| >= 24 pre-lockdown months | 2,190 | -0.144 | -0.040 | -0.104 | [-0.125, -0.088] |
| Gipuzkoa and Bizkaia only | 2,059 | -0.150 | -0.038 | -0.112 | [-0.133, -0.093] |

G2 reported the same raw estimate (-0.146) but a placebo mean of **-0.093** (eta_RI -0.053). The raw estimates agree; the placebo centring does not. The pooled household placebo contrast per window computed from the saved errors is about -0.029 on average (before the Portuguese series), against -0.073 for the registered step-zero windows (`goiener_step_zero_windows.csv`, after the Portuguese series, 2,460 households per window against 2,691 here). The two placebo constructions differ in household coverage and perhaps in the Portuguese component; the cause is **not yet found**. Until it is, the household elasticity is bounded by the two centrings, **-0.053 (G2 windows) and -0.108 (saved errors)**, and the first-differencing DiD (-0.047) agrees with the first. The claim 'about half the aggregate' is therefore not established; G6 passes the registered band but fails the check that its 'all' row reproduces G2 (not a registered rule; recorded as a flaw). Nothing is rescued.

### Diagnosis of the G6 / G2 placebo difference (2026-11-16)
**Cause found: the saved placebo errors were contaminated.** `goiener_save_errors.py` passed each household's pre-lockdown days **and the 2021 window days** to the leave-year-out LASSO, so the placebo model trained partly on post-reform summer days and its 2018-2019 errors shifted up (less negative). Registered step zero and G2 trained the placebo on pre-lockdown days only. Test on 32 households: placebo contrast over all April-October days **-0.060 trained on pre-lockdown days only, -0.048 with the window days in training; the saved errors reproduce the second exactly** (-0.048, 9,129 household-days). The G2 window errors and the G2 placebo windows are unaffected (pre-lockdown training only), so **G2 (-0.053) stands and the G6 table above is invalid** (its placebo centring is wrong; its raw -0.146 is the G2 raw). The 32-household gap (0.012 on all days) is smaller than the -0.038 against -0.093 gap in the table, so part of the difference may remain after the fix; G6 is rerun on corrected errors before any statement. Corrected script `goiener_save_placebo.py` (pre-lockdown training only, saves in chunks of 250 households so it resumes); `goiener_g6.py` now reads `g_placebo_errors_pre.parquet`. The first G6 table is kept above as a recorded flaw.

### G6 rerun on corrected placebo errors (2026-11-16; `goiener_save_placebo.py`, 2,489 households, 725,234 placebo household-days; `outputs/tables/goiener_g6.csv` overwritten)
**The 'all' row now reproduces G2** (eta_RI -0.0533 against -0.0528; mean placebo -0.0922 against -0.0927). The earlier table above, from contaminated errors, is superseded and kept as a recorded flaw. **G6 passes in all subsets (p 0.037 each):**

| Subset | Households | eta_raw | Mean placebo | eta_RI | Fisher interval |
|---|---|---|---|---|---|
| all (G2 sample) | 2,819 | -0.146 | -0.092 | **-0.053** | [-0.077, -0.041] |
| >= 24 pre-lockdown months | 2,190 | -0.144 | -0.093 | -0.051 | [-0.075, -0.039] |
| Gipuzkoa and Bizkaia only | 2,059 | -0.150 | -0.094 | -0.056 | [-0.080, -0.038] |

The household elasticity is stable across subsets at about -0.05. The placebo centring at about -0.09 (its cause unexplained) remains the main caveat; first-differencing (-0.047) agrees without it.

## G5 results (run 2026-11-16; `goiener_g5_prep.py` and `goiener_g5_forest.R`, committed in 03a5ef6 before the run; `outputs/tables/goiener_g5.csv`, `goiener_g5_importance.csv`)
2,433 households, 26 placebo windows (median 2,406 households each), 2,000 honest trees, seeds 20261117 and 20261118. **G5 passes all three rules:** (a) out-of-bag spread of predictions 0.0803 against a placebo 95th percentile of 0.0549 (placebo median 0.0437, max 0.0551; rank p 0.037); (b) `test_calibration` differential coefficient 0.988 (p < 0.001), mean prediction 1.001; (c) second-seed rank correlation 0.99999.
**What drives it (importance share):** share of baseline consumption at night 0.53, share at peak 0.20, share at mid 0.08, mean daily kWh 0.06, temperature slope 0.05; contracted power, tenure, activity code and province each at most 0.02.
**Descriptive, not registered and not a claim:** mean household response (window contrast, before the elasticity scaling) by quartile of baseline night share runs from -0.226 (lowest night share) to -0.036 (highest); by peak share from -0.032 to -0.220; by mean kWh from -0.069 to -0.148. **Threats to read this with:** the response is a difference of two log errors, so a household's baseline night and peak shares can predict it mechanically (log of small night consumption is noisy and mean-reverting); the placebo windows control the spread but not this mechanism by covariate; baseline shares may also proxy for heating type and occupancy. The estimate by group is not scaled by a household-specific dose (all share the pure 2.0TD dose).

## G5b Placebo check of the night-share and peak-share pattern (registered 2026-11-16 after G5, before the run; saved data only, no new fitting)
Question: does the dependence of the household response on baseline consumption shares reflect the reform, or is it mechanical (a difference of two log errors predicted by the baseline mix)? For the real window and each of the 26 placebo windows, OLS slope b of the household response y (g5 files) on the standardised baseline share (z-score across the window's households), for **share_night (C1)** and **share_peak (C2)**. Adjusted real slope = b_real - mean of the placebo slopes. **C1/C2 pass when** the adjusted real slope has the sign seen in G5 (positive for night share, negative for peak share) and two-sided rank p = (1 + #{|b_pl - mean b_pl| >= |b_real - mean b_pl|}) / 27 <= 0.05 (the real slope lies beyond every placebo slope). **If both pass,** the pattern is attributed to the reform response (descriptively); **if either fails, the G5 heterogeneity is not attributed to the reform** and is reported as a baseline-mix pattern only. Descriptive quartile gaps (top minus bottom quartile of the share) reported alongside. No other covariate or specification is tried after a failure. Code `scripts/analysis/goiener_g5b_placebo.py`.

### G5b results (run 2026-11-16; `goiener_g5b_placebo.py`, committed before the run; `outputs/tables/goiener_g5b.csv`)
| Covariate | Real slope | Placebo mean (sd) | Adjusted slope | Two-sided rank p | Quartile gap, real / placebo mean | Pass |
|---|---|---|---|---|---|---|
| share_night (C1) | +0.052 | +0.024 (0.012) | +0.028 | 0.037 | +0.189 / +0.099 | yes |
| share_peak (C2) | -0.057 | -0.021 (0.018) | -0.036 | 0.074 | -0.189 / -0.068 | **no** |

**Rule outcome: both did not pass, so the G5 heterogeneity is not attributed to the reform.** It is reported as a baseline-mix pattern. More than half of the raw slope is present in the placebo windows (night share 0.024 of 0.052; peak share 0.021 of 0.057), so most of the pattern is mechanical; the night-share excess over the placebo is beyond every placebo window, the peak-share excess is not (p 0.074). Recorded, not rescued.
