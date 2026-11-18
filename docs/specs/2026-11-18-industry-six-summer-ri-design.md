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
