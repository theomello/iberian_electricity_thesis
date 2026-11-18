# Industry response to the 2021 reform, tested against six pre-reform summers (proposal)

**Status: proposed 2026-11-18, not registered. Binding when the user confirms and this file is committed. Nothing for
2014–2017 is fetched before that commit.** Follows `2026-11-12-industry-voltage-design.md` (rule 3 failed: the 2018 and
2019 placebos disagree in sign), `2026-11-16-industry-adjusted-design.md` (no industrial point estimate) and
`2026-11-17-randomization-inference-design.md` (industry descriptive: more extreme than all 26 season-matched windows,
which come from two summers). **Those verdicts stand and are not re-judged.** This is a new test that uses new data:
four more pre-reform summers (2014–2017), found on ESIOS and REN on 2026-11-18
(`docs/data-reference/ree-ren-esios-miteco.md`).

**What is not blind, stated up front.** The 2021 estimates of every series are already known (IND −0.288, 6.4 −0.533
under the 2018–20 fit). So the 6.4 common-shift correction defined below can already be computed: about **−0.155**
for IND. What is unknown, and what this design adds, is the **null distribution**: how large these numbers are in
summers with no reform. The real estimates also change slightly, because the prediction step is redone with the same
procedure for every summer (point 3 below).

## In one example
Industry's evening-versus-night load fell by about 3% (against Portugal, relative to the LASSO prediction) in summer
2021, under a reform that raised the evening price by about 12% (log 0.12). The elasticity is −0.288. Two ordinary
summers (2018, 2019) gave −0.07 and +0.02: too few to say whether −0.288 is unusual. With six ordinary summers, if the
placebo values scatter between, say, −0.10 and +0.10, then −0.288 is well outside; if they scatter to ±0.30, it is not.

## The statistic (unchanged)
`η_am` of `tou_cross_tariff.Fit.eta`: Equation 4 of the paper on LASSO prediction errors, Spanish series minus Portugal
(REN national consumption), regressor = the reform-induced change in log hourly price (the dose), fixed effects as
before (hour × weekend × area, hour × weekend × month-of-sample, weekend × area × month-of-sample), central dose
(E = €100.81). Series: **IND** (E1–E6, ESIOS 1202–1207; dose weighted by pre-period component shares), **E0** (machinery
check), and E1+E2, 6.2, 6.3, 6.4 (descriptive, and 6.4 in the correction).

## Three econometric choices, made before any data is fetched

**1. Seasonality: summer windows only, calendar- and weekday-aligned.** The placebo dose is the real dose structure laid
on the placebo calendar (`old_new_tables`, `series_dose`), so hours, day types and the summer price periods match.
- **Aligned window of summer Y:** the window of 107 days starting on the date `R0 − 7k` (weekday-aligned with
  2021-06-01, a Tuesday) closest to 1 June of Y. This is the one value per summer used in the rules.
- **Shifted windows (descriptive only):** the same with starts −4 to +4 weeks around the aligned start (9 per summer).
- No windows from other seasons enter any rule (the 17 November run showed the all-season placebo mean is drifted:
  +0.078 for IND against −0.003 in summer).

**2. Serial correlation and few clusters: the summer is the unit of inference.** Hours, days and overlapping windows
within one summer are dependent, so they are not counted as independent draws. Inference compares the one treated
summer (2021) with S placebo summers, in the spirit of Conley and Taber (`papers/md`, `t0312`): the control summers'
estimates give the distribution of the estimator under no effect. A wild cluster bootstrap is not used: with a single
treated cluster it is known to fail (MacKinnon and Webb, `qed-wp-1314`).
- **Rank test:** p_rank = (1 + #{placebo summers with η_Y ≤ η_2021}) / (1 + S). Its floor is 1/(S+1): 0.2 for S = 4.
- **Prediction t-test (small sample):** t = (η_2021 − m) / (s · sqrt(1 + 1/S)), with m and s the mean and standard
  deviation of the S placebo-summer estimates; one-sided p from Student's t with S − 1 degrees of freedom. It assumes
  the summer estimates are roughly normal; with S = 4 that is an assumption, stated as such.
- **Interval:** 95% prediction interval for a no-effect summer, m ± t(0.975, S−1) · s · sqrt(1 + 1/S); the effect
  interval is η_2021 minus that interval.

**3. The LASSO as a generated regressor: one procedure, cross-fitted for every summer, 2021 included.** The paper's
per-hour LASSO (`tou_lasso_paper.py` specification: calendar and temperature interactions, 10-fold cross-validation,
one-standard-error rule, no trend) is fitted per series and for Portugal with **leave-one-year-out training on the
series' clean years**. The prediction error for summer Y always comes from a model trained on all clean non-COVID
years of 2014–2020 except Y. For 2021 that is all clean years (one more year than any placebo model has: the only
asymmetry, reported). The same procedure therefore produces the treated and the placebo errors, and the spread across
placebo summers includes the variation from refitting the model, not only the drift in demand.
- **Clean years:** E0, 6.2, 6.3, 6.4 and Portugal: 2014–2020. **IND and E1+E2: 2014, 2017, 2018, 2019, 2020** (E1 and
  E2 are incomplete at source in 2015–16; 6.1A cannot replace them because its definition breaks at the reform).
  COVID (2020-03-01 → 06-30) is out everywhere. So **S = 4 for IND** (2014, 2017, 2018, 2019) and **S = 6** for E0 and
  the 6.x series. 2020 is a training year only (its summer follows the lockdown).
- The 2018–2020 fit used so far (−0.288) is reported beside the new one for the record; the rules use the new one.

## The 6.4 common-shift correction
6.4TD (≥145 kV) has a dose near zero (0.042) but its 2021 evening-versus-night load also fell. If a non-price shift c
hit every voltage level equally, then for each series k, η_k·d_k = η·d_k + c. Using 6.4 to remove c:
**η_corr = (η_IND · d_IND − η_6.4 · d_6.4) / (d_IND − d_6.4)**, with d the evening-versus-night dose (`dose_ddd`).
It is computed the same way in 2021 and in each placebo summer. It assumes the shift is equal across voltage levels,
which cannot be tested here.

## Data step (X0, after the commit)
Fetch only 2014-01-01 → 2017-12-31 (ESIOS asks that data already downloaded is not requested again):
ESIOS 1201–1207 and 1216–1218 (`fetch_esios_spain.py --ids … --geo 0`), REN `fetch_ren_portugal.py`, population
temperature (`fetch_population_temperature.py`, which needs a start option), Spanish holidays 2014–2017 (four BOE
resolutions to add to `BOE_IDS`), and **Portugal's 2013–2015 holiday suspension** (Corpo de Deus, 5 October,
1 November, 1 December not holidays; Lei 23/2012, restored by Lei 8/2016) in `portugal()`.
Checks, each a gate for the year it covers: E0–E6 sum to ESIOS 1193 within 1% in every month of 2014 and 2017 (else
that year leaves IND); E0, 6.2, 6.3, 6.4 complete in every month of 2014–2017; REN 92/96/100 points a day; no hour
missing in any aligned window. `scripts/qa/audit_data.py` runs after the fetch.

## Rules, set before any 2014–2017 data is fetched
- **R0 Machinery check (gate).** E0 (households and small business, a known response) with S = 6: prediction t-test
  one-sided p ≤ 0.05. *Fails:* the extended procedure does not reproduce a known result; stop, nothing else is read.
- **R1 Detection (primary).** IND: prediction t-test one-sided p ≤ 0.05.
- **R2 Rank.** IND: the 2021 estimate is more negative than every placebo summer (p_rank = 1/(S+1), the floor).
- **R3 Null centred.** |m| for IND ≤ |η_2021| / 3.
- **R4 Not one summer.** Dropping each placebo summer in turn, R1's p stays ≤ 0.10.
- **R5 Common shift.** η_corr for IND: negative in 2021, and the prediction t-test on η_corr (its own S placebo values)
  has one-sided p ≤ 0.10.
- **Descriptive, no rule:** E1+E2 (S = 4), 6.2, 6.3, 6.4 per-summer tables; the shifted-window distributions; the
  2018–20-fit estimates against the leave-one-year-out ones; reduced forms (evening-versus-night shift in %).
A failed rule is recorded and kept; no other window, series, training span, control or correction is tried after it.

## What each outcome means
- **R0 fails:** stop; the extension is not trustworthy.
- **R1–R5 pass:** an industrial reform elasticity is reported as a **range from η_corr to η_2021**, each with its
  prediction interval, identified against six (E0) and four (IND) independent pre-reform summers, beside households.
- **R1–R4 pass, R5 fails:** industry's 2021 shift is unusual, but it cannot be separated from a shift common to all
  voltage levels; reported as a reduced-form change, not as a price elasticity.
- **R1 or R2 fails:** no detected industrial response; the prediction interval is the bound that is reported.
- **R3 or R4 fails alone:** the result rests on a drifted null or one summer; reported as such, not as an estimate.

## Threats
- S = 4 summers for IND is still few: the rank floor is 0.2, so detection rests on the t-test's normality assumption.
- 2014–2017 come under the same old tariff (Orden ITC/2794/2007 periods), but toll levels changed in 2014; the shape
  test is insensitive to the level, not to every change.
- 2021 is also a COVID-recovery summer, and the wholesale price rose through it; both are common to the control only
  in part.
- The 6.4 correction assumes an equal shift at every voltage level.
- Training sets differ in length by one year between 2021 and the placebo summers.

## Code and outputs
Fetchers as above; new `scripts/analysis/tou_industry_six_summer.py` reusing `tou_cross_tariff` (Fit, make_stack,
series_dose, old_new_tables) and the LASSO of `tou_lasso_paper.py`; cache `data/cache_tou/six_summer_errors.parquet`;
outputs `outputs/tables/tou_industry_six_summer{,_summary}.csv`. Deterministic (no random draws).

## Results (run 2026-11-18; `scripts/analysis/tou_industry_six_summer.py`, committed in b9b0183 before the run; outputs `outputs/tables/tou_industry_six_summer{,_summary}.csv`; 43 LASSO fits, about 10 minutes)

**Data step X0.** E0, 6.2, 6.3, 6.4 complete 2014–2017 (pass); REN 92/96/100 points (pass); aligned windows have no
missing hour. **The E0–E6 = 1193 gate passes 2017 and fails 2014** (July 2014: +2.6%; other months within 0.04%), so by
the registered gate **2014 leaves IND and E1+E2: S = 3 for industry (2017, 2018, 2019)**, not 4. Deviation recorded:
the gate's first computation summed the voltage series with index alignment, so the gaps in E5 (1206, which is not
empty: 650 days missing from spring 2014) produced a spurious ratio of 0; fixed to treat absent E5 hours as zero before
the run (the verdict, failure on July 2014, is the same either way). Some LASSO fits print scikit-learn convergence
warnings (duality gaps of order 1e-3), as in the earlier runs; not acted on.

| series | S | η 2021 | placebo summers | m (sd) | t | p_t | p_rank | 95% interval |
|---|---|---|---|---|---|---|---|---|
| E0 | 6 | −0.116 | 2014 −0.047, 2015 +0.061, 2016 +0.004, 2017 −0.008, 2018 −0.012, 2019 −0.028 | −0.005 (0.037) | −2.78 | 0.019 | 0.143 | [−0.213, −0.008] |
| **IND** | 3 | **−0.288** | 2017 +0.024, 2018 −0.056, 2019 +0.041 | +0.003 (0.052) | −4.85 | **0.020** | 0.250 | **[−0.549, −0.033]** |
| E1+E2 | 3 | −0.182 | 2017 −0.006, 2018 −0.086, 2019 −0.021 | −0.038 (0.043) | −2.93 | 0.050 | 0.250 | [−0.357, +0.068] |
| 6.2 | 6 | +0.050 | −0.085 … +0.179 | +0.016 (0.096) | +0.33 | 0.62 | 0.714 | [−0.232, +0.301] |
| 6.3 | 6 | −0.250 | +0.134 … +0.524 | +0.336 (0.143) | −3.79 | 0.006 | 0.143 | [−0.984, −0.189] |
| 6.4 | 6 | −0.548 | +0.560 … +1.192 | +0.816 (0.220) | −5.72 | 0.001 | 0.143 | [−1.975, −0.751] |
| IND corrected by 6.4 | 3 | −0.148 | 2017 −0.267, 2018 −0.476, 2019 −0.442 | −0.395 (0.112) | +1.91 | 0.90 | 1.000 | [−0.310, +0.804] |

**Rules.** R0 E0 machinery **pass** (p 0.019). R1 IND detection **pass** (p 0.020). R2 rank **pass** (2021 below all
three summers; p_rank 0.25, the floor). R3 null centred **pass** (|m| 0.003 ≤ 0.096). R4 leave-one-summer-out **pass**
(p 0.093, 0.015, 0.080). **R5 common shift fails** (η_corr −0.148 is negative, but above every corrected placebo
summer; p 0.90).

**Verdict, as registered (R1–R4 pass, R5 fails):** industry's evening-versus-night shift in summer 2021 is unusual
against the pre-reform summers, but it **cannot be separated from a shift common to all voltage levels**, so it is
reported as a reduced-form change, **not as a price elasticity**. The reduced form (η × evening-versus-night dose): IND
**−3.4%** in 2021 against +0.3%, −0.7%, +0.5% in 2017–2019.

**Why R5 fails (descriptive, not a rule).** The near-zero-dose series move most. In evening-versus-night shift terms
(η × d): 6.4 (dose 0.04) is −2.3% in 2021 against +2.3% to +4.9% in every placebo summer; 6.3 (dose 0.06) −1.5% against
+0.8% to +3.2%; IND (dose 0.12) −3.4% against −0.7% to +0.5%. Relative to its own normal summer, the ≥145 kV tariff,
whose tolls barely changed, dropped by about 5–6 points, more than industry as a whole. A response to the tolls would
scale with the dose; this does not. Consistent readings (none tested here): a non-price change in large-industry
operation in summer 2021 (post-COVID schedules), or a response to the **wholesale** price, which rose through summer
2021 and is not in the dose. The 6.4 correction is also noisy: 6.4's placebo values are large and positive (mean
+0.82), and the formula carries them into every corrected placebo.

**Other descriptive points.** The leave-one-year-out fit moves the 2021 estimates little (E0 −0.101 → −0.116, IND
−0.288 → −0.288, E1+E2 −0.168 → −0.182; 6.2 −0.08 → +0.05). Shifted-window placebo sd: E0 0.033, IND 0.060, E1+E2
0.050, 6.2 0.13, 6.3 0.18, 6.4 0.29. E0 with six summers: households' p 0.019, rank 1/7 (the floor).

## Erratum (2026-11-18, after the results): the IND series lost 60% of its 2021 hours
Found while scoping the cause of the shift (`notes/scope-2021-high-voltage-shift.md`). E5 (ESIOS 1206) has no rows
in many hours; `esios_load` sums with index alignment, so IND is NaN wherever E5 is absent: 1,548 of 2,568 hours of
the 2021 window (June 680 of 720), none in the 2017–2019 aligned windows. **The IND rows of the results above (R1–R4,
and the corrected R5) compare a selected 40% of 2021 hours with complete placebo summers, and are not valid as
written.** The same applies to IND in `2026-11-16-industry-adjusted-design.md` and the 2026-11-17 randomization run.
E0, E1+E2, 6.2, 6.3, 6.4 are unaffected. The fix (absent E5 hours as zero) and any rerun wait for the user.

## Corrected results (rerun 2026-11-18 after the E5 fix, committed in 4409d97 before the run; same rules)
IND now has no missing hour in any window (2021 mean 14.3 GW). The placebo summers are unchanged (2017–2019 had no
gaps); only the 2021 estimate moves. E0, E1+E2 and 6.2–6.4 are identical to the first run.

| series | S | η 2021 | m (sd) | p_t | p_rank | 95% interval |
|---|---|---|---|---|---|---|
| **IND** | 3 | **−0.189** (was −0.288) | +0.003 (0.052) | 0.043 | 0.250 | **[−0.449, +0.067]** |
| IND corrected by 6.4 | 3 | +0.005 (was −0.148) | −0.395 (0.112) | 0.955 | 1.000 | [−0.157, +0.957] |

**Rules (corrected run).** R0 pass (E0 p 0.019). R1 pass (p 0.043). R2 pass (rank floor). R3 pass (|m| 0.003 ≤ 0.063).
**R4 fails** (leave-one-summer-out p 0.139, 0.022, 0.122). **R5 fails** (corrected +0.005, p 0.95).

**Verdict, as registered (R4 and R5 fail): no industrial price elasticity is identified.** The 2021 industry
shift is below all three placebo summers, but it rests on which summers are used, its two-sided interval includes
zero, and after the 6.4 common-shift correction nothing remains. Together with the event-time evidence
(`notes/scope-2021-high-voltage-shift.md`: E1+E2 already −3 to −9 points in January–May 2021, before the reform; 6.3
and 6.4 move only in July–August, at weekends too), the industrial summer-2021 shift is not attributable to the
reform's tolls. **This supersedes the first-run IND rows above.**
