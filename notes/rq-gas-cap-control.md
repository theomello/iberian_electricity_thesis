# Is the gas-price control in the gas-cap dose-response right? (started 2026-11-05)

Task D of the crisis-quantity work. Context: `notes/rq-crisis-quantity.md` B3 and H5-H6. B3 regresses the weekly Iberian-minus-Italian
gap in run20 (the share of a gas plant's capacity offered within €20/MWh of its own cost) on the dose g_w (what the subsidy would have
done to the share at full against no pass-through, 0 to 0.6), over the 46 post-cap weeks that carry a dose. ρ = 1 + b. Without
controls ρ = 0.73 [0.51, 1.03]; with the weekly MIBGAS price (the Iberian gas hub index) and the PSV − MIBGAS spread (PSV, the
Italian gas hub) 0.54 [0.10, 0.87]. The two differ because the Iberian gas price and the dose correlate 0.97-0.98 in the post-cap weeks:
if Iberian offers respond to gas apart from the subsidy, the uncontrolled ρ is biased up by that response times the way gas moves with
the dose.

**Plain worked example of the problem.** Suppose the true pass-through is ρ = 0.55, and in addition every extra €100/MWh of gas makes
Iberian plants offer 9 percentage points more of their capacity near cost, for reasons unrelated to the subsidy. In the post-cap weeks gas
rises when the dose rises, so the regression on the dose alone credits the dose with the gas response and reads ρ ≈ 0.73. Adding the gas
price removes that, but because gas and dose move together the estimate gets about 1.5 times noisier (H6). The question: is there such a
gas response? A week with gas variation and **no dose** answers it directly: there the dose cannot take the credit.

## Rules, fixed before any coefficient is computed (2026-11-05)

Script: `scripts/analysis/gas_cap_control_tests.py`, stages `draws`, `nodose`, `confounders`, `controls`. Outputs
`outputs/tables/gas_cap_control_*.csv`. Nothing below was run when written. Only counts of weeks, ranges of the gas series and the
regression of gas on the dose (needed to size the "gap world", below) were looked at; no coefficient of the outcome on any candidate.

### Common objects

- **Outcome ATT_w:** the weekly Iberian-minus-counterfactual gap from Xu's (2017) generalised synthetic control exactly as B3 builds it
  (`panel()`, `matrix(h, "run20")`, `gsc`, main margin €50, 93 matrix rows, 92 weeks 2021-09-27 → 2023-06-26), factor count r by Xu's
  cross-validation on the pre-cap weeks (the script asserts it picks r = 0, as in B3; if not it stops and says so).
- **Reproduction check before anything else:** the script must return B3's ρ = 0.726 and H6's 0.583 (MIBGAS) and 0.544 (both controls)
  with the same existing weekly series (`weekly_gas`, delivery-day means), and H6's bootstrap intervals from the same seed (20261102).
  If not, stop and fix.
- **Firm draws:** 199 firm-block bootstrap draws within country (10 Iberian, 12 Italian firms), seed 20261102, the same draws as H6,
  ATT_w re-estimated each draw. Stored once and reused by every stage, so every interval below rests on the same draws.
- **Gas series, bid-time** (what a bidder knew at noon on D-1): `mibgas_bid`, `psv_bid` from `gas_cap_weekly_conditions.parquet`;
  spread_bid = psv_bid − mibgas_bid. The existing B3 controls are delivery-day means (`weekly_gas`); both families are reported.
  Note: MIBGAS + spread spans the same space as MIBGAS + PSV, so the existing "both" control already contains PSV. What is new in
  stage (3) is the vintage (bid-time) and PSV alone.

### (1) No-dose tests

Samples (a week's dose is exactly zero in both):
- **Pre-cap:** weeks starting 2021-10-04 … 2022-06-06 (ATT observed; the week of 2021-09-27 has none). The week of 2022-06-13 is
  excluded because five of its seven days are capped and it carries g = 0.26, although B3 counts it as pre-cap (`cols < CAP0`);
  the version with it is a sensitivity.
- **Post-subsidy:** weeks starting on or after 2023-02-27 with ATT observed (the subsidy is positive to 2023-02-25 and MIBGAS fell
  below the reference price afterwards). The week of 2023-02-20 is excluded: it holds days with positive subsidy.
- **Pooled:** both, with a separate intercept for each sample (the post-cap drift, B3's +0.14, is a level shift), common slope.

Regressions of ATT_w (run20 units) on, one specification at a time: (i) `mibgas_bid`; (ii) `psv_bid`; (iii) the spread; (iv) mibgas_bid
and psv_bid together. Slope per €/MWh. Variants beside the main (not decisive): a linear trend; pre-cap ending 2022-03-21 (before the
EU Council's late-March 2022 endorsement of the Iberian exception, from memory, not on disk; an announcement could move offers before
the cap); the pre-cap sample with the week of 2022-06-13; ATT at r = 1, 2.

Intervals: (A) **double bootstrap** (main): for each of the 199 firm draws, resample the sample's weeks in moving blocks of 4 (each
sample separately), refit; percentile 95%. (B) firm bootstrap alone (weeks fixed). (C) Newey-West standard error, 3 lags in
calendar weeks, within sample. Power: SE = sd of the double-bootstrap slopes; minimum detectable slope (80% power, 5% two-sided) = 2.8 SE.

**What the two worlds predict.** Let δ_M = slope of delivery-day MIBGAS on g_w over the 46 post-cap weeks (≈ 203 €/MWh per unit of g,
seen in the preliminary look) and likewise δ_S for the spread (≈ 96). Omitting x biases b by c·δ, so a gas response of c per €/MWh
explains the H6 gap of 0.182 (0.726 → 0.544) if c* = 0.182/δ_M (all through MIBGAS), about **+0.0009** per €/MWh, i.e. +9 percentage points of run20
per +€100/MWh (and 0.143/δ_M = +0.0007 for the MIBGAS-only gap 0.726 → 0.583).
- **No gas response:** c = 0 on MIBGAS and PSV in both no-dose samples, signs unstable across samples, controlled ρ differs from
  uncontrolled by noise only.
- **Gap world:** c ≈ +0.0009 on MIBGAS, positive and of similar size in both samples (a stable coefficient).

**Verdict, applied to the pooled double-bootstrap interval for MIBGAS (i), main specification:**
- *Gas response detected:* interval excludes 0 AND the Newey-West 95% interval excludes 0. If the sign is positive the control is
  supported and the controlled ρ is the better centre; if negative the sign is the wrong one for the confound that pulls ρ down, and the
  control would push ρ up, which contradicts the data in B3 (reported, then read case by case).
- *Gap world rejected:* the interval excludes c* and power at c* is at least 80% (SE ≤ c*/2.8). Then the uncontrolled 0.73 is preferred
  on this evidence.
- *Uninformative:* anything else, in particular an interval holding both 0 and c*, or power at c* below 80%. Then the no-dose tests do
  not choose between 0.73 and 0.54 and both are quoted, as in H6.
Stable coefficient: the pre-cap and post-subsidy slopes are called compatible if the bootstrap interval of their difference holds 0.
What would change the reading: sign or size flipping with the trend, the 2022-03-21 cut or r (then the result is specification, not
evidence); disagreement between the double bootstrap and Newey-West (counted as not detected). A limit stated now: the no-dose samples
cover MIBGAS only up to about €160/MWh before the cap and about €25-48 after the subsidy, while the dose weeks run to €210 and
spreads of €100+; a response that exists only at high gas prices or only when the Iberian price is cut off from the Italian one is
outside what these samples can see.

### (2) Confounder search

A confounder must move with the dose and with the Iberian-relative run20. Candidates (weekly, the same 92 weeks): carbon (`eua_bid`),
net load forecast, Spanish and Italian temperature, PSV, MIBGAS, the spread (all from the conditions file); from files already on disk,
built in the script: wind forecast (ESIOS 1777), PV forecast (1779), Iberian demand forecast (1775), national reservoir fill from
MITECO (all reservoirs) and its deviation from the same week's 2000-2021 mean, ESIOS 623 stored hydro energy (peninsular), the French
link (RTE/OMIE-based predictors known at bid time: French nuclear output lag, French load forecast, predicted import-full and
export-full probabilities), and an annual harmonic (sine and cosine of the day of year) as a catch-all for seasonal drivers. Omitted
on purpose: the Iberian day-ahead price and the share of units in the money (outcomes of the same bids).

For each candidate x (standardised):
- (a) correlation with g_w over the 46 post-cap weeks (B3's regression sample);
- (b) correlation with ATT_w in each no-dose sample and the pooled within-sample correlation, with the pooled slope's double-bootstrap
  95% interval; "moves with the outcome" if that interval excludes 0;
- (c) ρ when x is added alone to B3 (r = 0), with the contrast to 0.726 and its firm-bootstrap 95% interval.
- Consistency check: the shift predicted from the no-dose slope, −c_x · δ_x (δ_x = slope of x on g_w in the post-cap weeks), against the shift observed in (c).
**Flag** a candidate that passes all three: |corr(a)| ≥ 0.30 (the 5% critical value for 46 weeks is 0.29), (b) as above, and |Δρ| ≥ 0.10 in (c).
The gas variables themselves are reported in the same table and read separately. 19 candidates, so one or two (b) hits by chance are
expected; a flag is a lead, not a finding. **A confounder that is unobserved cannot be found this way**, and nothing here can
test an Italian-side confounder beyond Italian temperature (no Italian demand, wind or hydro series are on disk).

### (3) Better controls

ρ (r = 0, same ATT and draws) under: none; existing MIBGAS; existing MIBGAS + spread; bid-time MIBGAS; bid-time MIBGAS + PSV; PSV alone;
the conditions without gas (carbon, net load, both temperatures); the conditions with both bid-time gas prices; and the survivors of
(2) (flagged non-gas candidates, together with bid-time MIBGAS + PSV; if none is flagged, the set is not built and the note says so).
Each with the firm-bootstrap 95% interval, width against the uncontrolled one, and the contrast with it.

**Which set the no-dose tests favour:** blocked cross-validation on the pooled no-dose weeks — folds are blocks of 4 consecutive weeks within
each sample, sample-specific intercepts, fit on the other folds, mean squared error on the held-out weeks, against intercept-only. A set is
favoured if it has the lowest error AND beats intercept-only by at least 10%; if none does, the no-dose tests favour no set and both
estimates are quoted. Also reported: fit on pre-cap weeks only, predict the post-subsidy weeks with the intercept re-centred (the stable-coefficient
test).

Not fetched, listed as unavailable: Enagás LNG send-out and Iberian gas storage. They would add the physical side of the Iberian gas
market (when LNG supply, not price, tightens Iberian gas-fired dispatch) and separate a response to the price from a response to supply
conditions that move with it; they cannot be added without fetching.

### Reading rule for the closing six lines

The paper's ρ: the controlled value if "gas response detected"; the uncontrolled value if "gap world rejected"; both (central band
0.5-0.75 from H6) otherwise. Whichever set (3) favours is named, with its interval.

## Results (2026-11-05; `gas_cap_control_tests.py --stage all`, about 1 minute; no rule was changed after seeing results)

**Reproduction passed.** B3 0.726, MIBGAS 0.583 [0.118, 0.941], both 0.544 [0.097, 0.872], uncontrolled [0.510, 1.031]: H6's numbers to the
third decimal, from the same seed. Xu's cross-validation picks r = 0 (errors 0.02023, 0.02093, 0.02086, 0.02049, 0.02102, 0.02182).
Two small differences from the rules as written: (i) δ_M, the slope of MIBGAS on the dose, is 209 (delivery-day; 211 bid-time) and the spread's 102,
over the 46 B3 weeks, not the 203 and 96 of the preliminary look, which used the 35 weeks with a positive dose; so c* = **+0.00087** per €/MWh (+8.7 percentage
points of run20 per +€100/MWh), not "about 0.0009"; (ii) the sample counts are pre-cap 36 weeks (37 less the week of 2021-09-27, which has
no ATT) and post-subsidy 11 weeks (the other 7 weeks after 2023-02-27 have no Iberian unit in the money).

### (1) No-dose tests: the gas response has the wrong sign for the confound, but the samples cannot rule the gap world out by the rule

Slope of ATT_w (run20 units) on bid-time MIBGAS, per €/MWh; "per 100" is percentage points per €100/MWh. Gap world: +0.00087 (+8.7).
`outputs/tables/gas_cap_control_nodose.csv`.

| sample | n | sd of MIBGAS | slope (per 100) | Newey-West 95% | firm bootstrap 95% | double bootstrap 95% | smallest detectable slope (80%) | power at +0.00087 |
|---|---|---|---|---|---|---|---|---|
| pre-cap | 36 | €22 | −0.00044 (−4.4) | [−0.00094, +0.00005] | [−0.00125, +0.00005] | [−0.00213, +0.00031] | 0.0019 | 25% |
| post-subsidy | 11 | €7 | −0.00523 (−52) | [−0.00885, −0.00160] | [−0.00927, 0.00000] | [−0.01761, +0.00835] | 0.018 | 5% |
| **pooled** | 47 | €30 | **−0.00057 (−5.7)** | [−0.00112, −0.00002] | [−0.00138, −0.00002] | **[−0.00232, +0.00028]** | **0.0020** | **22%** |

- **Verdict by the rule: uninformative.** The pooled double-bootstrap interval holds 0 (so "detected" fails; the Newey-West and firm-bootstrap
  intervals both exclude 0, on the negative side), and power at c* is 22%, far below the 80% the rule asks for before calling the gap world rejected.
- **Beside the rule (not a change to it):** all three intervals for the pooled slope lie below c*: the largest upper end is +0.00028
  (double bootstrap), a third of c*. The same holds in every variant: trend, pre-cap cut at 2022-03-21, with the week of 2022-06-13, ATT at r = 1 and 2 (pooled slope
  −0.00057 … −0.00059, double-bootstrap upper ends +0.00022 … +0.00067). So the data point away from a positive gas response of the size that would explain
  0.73 against 0.54, even though by the pre-set power criterion they cannot rule it out. Power is low because c* is only 1.2 standard errors
  of the double bootstrap (0.00073), which is wide on purpose (block resampling of 47 weeks with a March-2022 gas spike).
- **Wrong sign for the confound.** The sample slope is negative: when gas is dearer, Iberian plants offer *less* of their capacity near cost relative to Italian ones.
  A negative response would raise the controlled ρ above the uncontrolled one (predicted shift +0.12 for bid-time MIBGAS, `pred_d_rho` below), but delivery-day MIBGAS
  lowers ρ by 0.14. The two do not line up.
- **PSV and the spread.** PSV alone: pooled −0.00080 (NW [−0.00153, −0.00006], firm [−0.00149, −0.00021], double [−0.00365, +0.00004]); the Iberia-Italy spread: −0.00275, intervals
  wide ([−0.0119, +0.0034] double), smallest detectable slope 0.011 against the gap-world value 0.0018 (power under 10%): the spread hardly varies outside the post-cap
  weeks (sd €7 pre-cap, €2 post-subsidy), so these samples say nothing about a response to it. MIBGAS and PSV together (the "both" version) are too collinear
  to separate (coefficients +0.0022 and −0.0028, intervals ±0.01).
- **Stable coefficient?** Post-subsidy minus pre-cap slope, MIBGAS: −0.0048, 95% [−0.0166, +0.0089]: compatible with 0, but because the 11-week sample is too short to say anything, not because the two agree. The post-subsidy slope (−0.0052) is large and
  falls to −0.0011 with a trend: it is the slow decline of the ATT and of gas together over spring 2023, not a gas response.
- **Limits.** The pre-cap ATT is an in-sample residual (intercept-only at r = 0), so the pre-cap slope is the Iberian-minus-Italian differential response to a common gas
  movement; the post-cap dose weeks run MIBGAS to €210 and spreads to €100+, outside what the no-dose weeks contain (pre-cap to €160, post-subsidy €25-48). A response that
  exists only at those prices, or only when the Iberian price is cut off from the Italian one, is not tested here.

### (2) Confounder search: nothing observable is flagged

`outputs/tables/gas_cap_control_confounders.csv`, 21 candidates (the rules said 19: wind, PV, demand forecasts and the net load were all kept, and the gas series count in both
vintages). ρ (uncontrolled) 0.726. Selected rows (full table in the file); (a) correlation with the dose over the 46 post-cap weeks, (b) pooled no-dose slope per sd of x with its double-bootstrap 95%,
(c) ρ with x added alone and the firm-bootstrap 95% of the shift.

| candidate | (a) corr dose | (b) slope per sd [95%] | (c) ρ with x | shift [95%] | shift predicted from (b) |
|---|---|---|---|---|---|
| MIBGAS, bid-time | 0.98 | −0.022 [−0.088, +0.011] | 0.722 | −0.005 [−0.41, +0.30] | +0.12 |
| MIBGAS, delivery-day | 0.98 | −0.011 [−0.068, +0.027] | 0.583 | **−0.144** [−0.52, +0.14] | +0.06 |
| PSV, bid-time | 0.92 | −0.045 [−0.206, +0.002] | 0.847 | **+0.120** [−0.09, +0.26] | +0.25 |
| spread PSV − MIBGAS, bid-time / delivery-day | 0.61 / 0.81 | −0.082 / −0.051 (both span 0) | 0.765 / 0.699 | +0.04 / −0.03 | +0.29 / +0.24 |
| carbon (EUA) | −0.14 | +0.006 [−0.018, +0.058] | 0.730 | +0.003 | +0.003 |
| net load forecast | 0.53 | −0.002 [−0.037, +0.037] | 0.714 | −0.012 | +0.006 |
| Spanish / Italian temperature | 0.63 / 0.65 | +0.013 / +0.012 (span 0) | 0.725 / 0.730 | −0.002 / +0.004 | −0.04 |
| wind / PV / demand forecast | −0.35 / 0.13 / 0.36 | all span 0 | 0.717 / 0.733 / 0.740 | −0.009 / +0.006 / +0.014 | ≈ 0 |
| reservoir fill (MITECO) / its anomaly / ESIOS 623 | −0.45 / −0.51 / −0.59 | all span 0 | 0.709 / 0.718 / 0.708 | −0.02 / −0.01 / −0.02 | ≈ 0 |
| French nuclear lag / French load / import-full / export-full | −0.64 / −0.27 / −0.23 / −0.07 | all span 0 | 0.705 … 0.725 | −0.02 … 0 | ≈ 0 |
| annual harmonic (sin / cos) | −0.60 / −0.48 | span 0 | 0.694 / 0.741 | −0.03 / +0.01 | ≈ 0 |

- **Flags (all three of: |corr| ≥ 0.30, (b) excludes 0, |shift| ≥ 0.10): none.** Sixteen candidates pass (a); no candidate passes (b), not even the gas variables (PSV's upper end is +0.002); only
  delivery-day MIBGAS and PSV pass (c), and they shift ρ in opposite directions (−0.14, +0.12). So no survivor set is built.
- The observed shift matches the one the no-dose slope predicts for none of the gas controls in sign and size (bid-time MIBGAS −0.005 against +0.12; PSV +0.12 against +0.25; delivery-day MIBGAS −0.14 against +0.06).
  The relation between the outcome and gas after the cap is not the one before it, or the post-cap estimate is too noisy to show it.
- **What this does not show.** An *unobserved* confounder that moves with the dose and with Iberian-relative offers cannot be found by this search, and nothing here tests Italian-side conditions apart from temperature
  (no Italian demand, wind or hydro on disk). The post-subsidy correlations in (b) for every slow-moving series (reservoirs, season, French nuclear) are around −0.5 to −0.7 only because 11 trending weeks
  correlate with anything trending; they are not read.
- One thing the search *did* show: the two vintages of the "same" MIBGAS control give different ρ (see (3)).

### (3) Better controls: the controlled ρ is not one number

`outputs/tables/gas_cap_control_sets.csv`. ρ at r = 0, same ATT and draws, firm-bootstrap 95%; width ratio against the uncontrolled interval (0.52); blocked cross-validation gain over intercept-only
on the 47 no-dose weeks.

| control set | ρ | 95% | width ratio | shift vs none [95%] | CV gain |
|---|---|---|---|---|---|
| none | 0.726 | [0.510, 1.031] | 1.00 | | |
| existing MIBGAS (delivery-day), H6 | 0.583 | [0.118, 0.941] | 1.58 | −0.144 [−0.52, +0.14] | −0.5% |
| existing MIBGAS + spread (delivery-day), H6 | 0.544 | [0.097, 0.872] | 1.49 | −0.182 [−0.58, +0.12] | −23% |
| bid-time MIBGAS | 0.722 | [0.237, 1.128] | 1.71 | −0.005 [−0.41, +0.30] | +0.8% |
| bid-time MIBGAS + PSV | 0.823 | [0.334, 1.206] | 1.68 | +0.097 [−0.36, +0.39] | −14% |
| PSV alone (bid-time) | 0.847 | [0.622, 1.085] | 0.89 | +0.120 [−0.09, +0.26] | +0.4% |
| conditions without gas (carbon, net load, both temperatures) | 0.714 | [0.508, 1.015] | 0.97 | −0.013 [−0.10, +0.11] | −33% |
| conditions with both bid-time gas prices | 0.810 | [0.421, 1.137] | 1.37 | +0.083 [−0.36, +0.40] | −38% |
| survivors of (2) | not built: none flagged | | | | |

- **Which set the no-dose tests favour: none.** The lowest blocked-CV error is bid-time MIBGAS, with a gain of 0.8% over intercept-only; the rule asks for 10%. Fitting on the pre-cap
  weeks and predicting the post-subsidy weeks with the intercept re-centred improves on the intercept-only error by 1-11% for the gas sets and worsens it by 11-37% for the condition sets; neither is a stable explanation.
- **The controlled estimate depends on which gas series is used.** Changing MIBGAS from the delivery-day mean to the D-2 price a bidder knew at noon moves ρ from 0.58 to 0.72; PSV in place of MIBGAS gives 0.85; MIBGAS and PSV bid-time
  give 0.82. All lie inside the uncontrolled interval, and the contrast intervals all hold 0. The reason is in `gas_cap_control_identification.csv`: the dose explains 95.7% of the variance of MIBGAS in the post-cap weeks (variance inflation 23);
  the controlled slope is identified from the other 4.3% (sd about €9), and that remainder is correlated only 0.76 between the two vintages of the same price. The "0.54" of the paper's range
  rests on one vintage of a regressor identified from 4% of its variance.
- Intervals under control are 1.4-1.7 times wider (H5's simulation said 2.4-5.8 without clustering), except PSV alone, which is less collinear with the dose (corr 0.92, 15% of variance left) and has a slightly *narrower*
  interval than the uncontrolled one (0.62-1.09).

### What was not done

Enagás LNG send-out and Iberian gas storage (not on disk, not fetched). They would add the physical side of the gas market: whether Iberian plants offer differently when LNG supply or storage, rather than the price, is tight. That
is the one story where a gas-linked Iberian response need not show up in MIBGAS; it would separate "responds to the price" from "responds to supply conditions that happened to rise and fall with the subsidy". They cannot be added without a fetch.
The Iberian day-ahead price and the share of units in the money were left out as outcomes of the same bids.

### Plain reading (six lines)

1. In the weeks with no subsidy, higher gas did not make Iberian plants offer *more* capacity near cost relative to Italian ones; if anything slightly less (−5.7 points per +€100, intervals from −23 to +3 on the widest, mostly negative on the narrower ones).
2. A response of the size that would explain 0.73 against 0.54 (+8.7 points per +€100) lies above every interval I computed; by the pre-set power rule these samples are still "uninformative" (power 22%), so the rule's answer is: quote both.
3. No observable confounder (carbon, load, temperature, wind, solar, reservoirs, France, season) moves with both the dose and the outcome; an unobserved one cannot be found this way.
4. The "controlled" ρ is not stable: 0.58 with MIBGAS as averaged over the delivery days, 0.72 with the price known at noon, 0.85 with PSV, 0.82 with both bid-time prices; each is inside the others' intervals, and no control set explains the no-dose weeks.
5. So the 0.54 is not better supported than 0.73: the dose and the gas price are 98% collinear, and the lower number comes from one vintage of one regressor.
6. Which ρ to quote: the uncontrolled **0.73 [0.51, 1.03]**, with the statement that gas controls move it anywhere from 0.54 to 0.85 depending on the series, all within noise (so the H6 "central band 0.5-0.75" should read 0.5-0.85, and no direction of bias is established); the no-dose test does not favour a control set.

## LNG and storage: rules, fixed before running (2026-11-05)

**Plain worked example.** Compare two weeks. In the week of 2022-08-15 the dose g was 0.54, bid-time MIBGAS was €151, Iberian LNG tanks were 76% full and storage was 84% full. In the week of 2022-11-07 g was 0.02, MIBGAS €47, tanks 84% and storage 97%. So between August and November the dose fell and the physical gas system got fuller. Suppose plants holding contracted LNG offer more capacity near cost when tanks are full, because the gas has to be burned, whatever the price. Then run20 moves for a physical reason that the dose regression partly credits to the dose. Across all 46 weeks, tank fill rises slightly with the dose (corr +0.36) and the storage anomaly falls with it (−0.72). The sign of any bias is therefore set by those slopes, not by the story. A physical shock that works *through* MIBGAS is already inside the dose, because own cost is built from MIBGAS. The confound tested here is a channel that bypasses the price.

**What was looked at.** Only the GIE series, their correlations and slopes with g_w and with bid-time MIBGAS, their ranges, and week counts. Nothing involving ATT_w, run20, offers or any outcome coefficient was computed.

### Construction (every series: Iberia = ES + PT summed before dividing)
- **Vintage: gas day D−3.**
  - A gas day runs 06:00–06:00 CET. GIE publishes it in the evening of the following day. This is GIE's stated schedule, from memory, not on disk.
  - So at 12:00 on D−1, when offers for D close, the newest published gas day is D−3. That is one day older than MIBGAS `_bid` (D−2), which settles by noon.
  - Code: `bwc.lagged(daily, 3)` (five-day forward fill), then `bwc.weekly` (Monday-start weeks, mean over the seven delivery days), the same as every `_bid` series.
  - Sensitivities: lag 1 (shippers know their own nominations sooner) and lag 7.
- **Main candidates** (decisive in stage 1, flaggable in stage 2, used in control sets):
  - **P1 LNG tank fill** = Σ`inventory.gwh` / Σ`dtmi.gwh`. Used as a level, because the physical limit is how full the tanks are in absolute terms (full tanks mean ships queue offshore).
  - **P2 storage fill anomaly** = Σ`gasInStorage` / Σ`workingGasVolume`, minus the 2018–2021 mean for the same ISO week (clipped at 52). The anomaly is computed on daily data before lagging. This is the construction the MITECO anomaly in `build_series` already uses.
  - **P3 LNG arrivals** = 7-day sum ending D−3 of (Δ`inventory.gwh` + `sendOut`), in GWh.
- **Send-out's mechanical link, handled by an identity.** Send-out = arrivals − Δtank stock.
  - Arrivals (P3) are set by cargo schedules fixed weeks ahead.
  - The tank stock (P1) is a state at D−3.
  - Send-out itself is driven by gas burned for power, i.e. by the same bids, and lagging does not cure this: weekly send-out at D−3 correlates 0.91 with the delivery week's own.
  - So **send-out, Sines utilisation (PT `sendOut`/`dtrs`), days of cover (inventory / 7-day mean send-out) and storage net withdrawal (`withdrawal` − `injection`, also gas burned) are diagnostic rows only**. They are reported in stages 1–2, cannot be flagged, and never enter a control set.
  - Iberian utilisation is dropped: Spain's `dtrs` is 1,910.4 GWh/d on 670 of 677 window days, so utilisation is send-out rescaled.
- **Screen-only rows:** P1 as an anomaly (same baseline as P2) and P2 as a level.

### Descriptives (recomputed; 46 = B3's post-cap weeks 2022-06-20 → 2023-06-19, 34 with g > 0; the week of 2022-06-13 counts as pre-cap)
- **δ** is the slope of x on g.
- **c\*** = 0.182/δ is the response that would by itself explain 0.73 → 0.54, shown per within-no-dose standard deviation. That sd is taken over 36 pre-cap weeks plus 18 calendar post-subsidy weeks. The script recomputes it on the 11 post-subsidy weeks with ATT.
- **R²** is the share of x's variance in the 46 weeks explained by g and MIBGAS together.

| x | corr g | corr MIBGAS | R² (g, MIBGAS) | c\* per sd | g>0 range | pre-cap range | post-subsidy range |
|---|---|---|---|---|---|---|---|
| P1 tank fill | +0.36 | +0.32 | 0.15 | **+0.117** | 0.42–0.84 | 0.38–0.84 | 0.43–0.76 |
| P2 storage anomaly | **−0.72** | −0.71 | 0.52 | **−0.034** | 0.05–0.22 | −0.11–0.03 | 0.17–0.29 |
| P3 arrivals | +0.12 | +0.06 | 0.09 | +0.30 | | | |
| tank-fill anomaly (screen) | +0.47 | +0.44 | 0.23 | +0.093 | | | |
| storage fill level (screen) | −0.41 | −0.41 | 0.17 | −0.088 | 0.74–0.98 | 0.59–0.82 | 0.81–0.97 |
| send-out (diag.) | +0.07 | +0.03 | 0.04 | +0.45 | | | |
| Sines utilisation (diag.) | +0.41 | +0.36 | 0.22 | +0.062 | | | |
| net withdrawal (diag.) | −0.46 | −0.38 | 0.30 | −0.10 | | | |
| days of cover (diag.) | +0.15 | +0.18 | 0.04 | +0.19 | | | |

- **Lag barely matters.** Lag 1 against lag 3 correlates 0.95–1.00 weekly for every row except arrivals (0.89); lag 7 against lag 3 correlates 0.68–1.00. Correlations with g move by at most 0.10 across lags 1, 3 and 7.
- **Unlike MIBGAS, these can be separated from the dose.** MIBGAS keeps 4% of its variance after the dose (variance inflation 23). P2 keeps 48% (variance inflation about 2.1). The others keep 70–96%.

### Where they enter (existing thresholds, same 199 draws, seed 20261102, r = 0)
1. **No-dose tests.**
   - Samples, intercepts, intervals (double bootstrap as main, firm bootstrap, Newey-West with 3 lags) and the 80% power rule are all unchanged.
   - P1, P2 and P3 are run one at a time, standardised, then together, then each with bid-time MIBGAS.
   - For each candidate:
     - **Detected:** the double-bootstrap and Newey-West intervals both exclude 0.
     - **Gap world rejected:** the interval excludes c\*_x and power at c\*_x is at least 80%.
     - **Uninformative:** anything else.
   - The sign that would make 0.73 too high is **c > 0 for P1 and P3, and c < 0 for P2**.
   - Expected power, stated now from the published MIBGAS test (smallest detectable slope about 0.07 per sd): P1 and P3 are testable. **P2's c\* (0.034) is below it, so "uninformative" is the expected verdict for storage.**
   - Variants (not decisive): the existing ones (trend, 2022-03-21 cut, the week of 2022-06-13, r = 1 and 2), plus:
     - pre-cap from 2021-11-01 (32 weeks), after the Maghreb–Europe pipeline closed (Iberian send-out 785 GWh/d in October 2021 against 994 in December 2021–May 2022);
     - lags 1 and 7;
     - the level and anomaly versions swapped.
2. **Confounder screen.**
   - P1–P3 and the two screen rows are added to the 21-row table at lag 3 only, with the same gates: |corr g| ≥ 0.30, the no-dose interval excludes 0, and |Δρ| ≥ 0.10.
   - P3 fails the first gate already.
   - With 5 new flaggable rows, about 0.25 chance hits are expected at 5%.
   - Diagnostic rows and the other lags are reported, not flagged.
3. **Control sets.**
   - New sets:
     - {P1, P2, P3};
     - the same plus bid-time MIBGAS and PSV;
     - P1 alone;
     - P2 alone.
   - Flagged rows join the existing survivors set.
   - Each set gets the firm-bootstrap ρ, the width ratio and the shift against 0.726. "Favoured" keeps its meaning: lowest blocked-CV error and a gain of at least 10% over intercept-only.
4. **Contamination checks (fixed now).**
   - **Lead placebo:** the candidate built from the delivery week itself (lag 0), or from the following week, must not have a lower blocked-CV error on the no-dose weeks than the lag-3 version. If it does, the series carries feedback from the bids and is not used as a control.
   - **Lag stability:** a sign flip between lags 1, 3 and 7 makes the candidate's result "specification, not evidence", as in the existing rule.

### What each outcome means for the ρ the paper quotes
- **A main candidate is detected with the sign that makes 0.73 too high, and passes both checks.**
  - Centre: the favoured physical set's ρ, or {P1, P2, P3} + MIBGAS + PSV if no set is favoured.
  - 0.73 [0.51, 1.03] is quoted beside it.
- **Detected with the opposite sign:** 0.73 stays the centre and is called conservative on this channel. The physical-controlled ρ is reported beside it.
- **Gap world rejected for P1 and P3:**
  - The LNG channel is ruled out at the pre-set power, and the "one open confound" sentence is withdrawn for LNG.
  - Storage keeps whatever verdict P2 gets.
  - Quote 0.73 with the 0.54–0.85 gas-vintage band.
- **Uninformative, or nothing flagged:** no change. Quote 0.73 [0.51, 1.03] with the 0.54–0.85 band, and state that physical supply could be tested only at low power (for storage, as predicted here).

### Limits, stated in advance
- **Revised data, not what bidders saw.**
  - Every window LNG row was last updated 2023-10-26 (PT) or 2025-05-13 (ES).
  - Portuguese storage rows have a median update 115 days after the gas day.
  - Spanish storage rows have a median of 1 day, so they are close to first release.
  - Revisions can carry information bidders lacked, which tilts the test toward detection.
- **Country totals, not shippers' own positions.** The large owners are LNG shippers and knew their own cargoes earlier and more precisely, which biases a detected response toward 0. A firm-specific take-or-pay story is beyond this test.
- **Stocks still carry past dispatch.** Tank fill at D−3 is cumulative past send-out, so lagging removes same-week feedback but not persistence.
- **Storage was policy-driven.** Storage after the cap followed the EU filling rule (Regulation 2022/1032, from memory) and the season: P2 correlates 0.71 with the annual sine over the 46 weeks. Its g > 0 weeks (0.05–0.22) lie above the whole pre-cap range and only partly inside the post-subsidy one, so with sample intercepts its dose-week values are largely extrapolated.
- **Italy is not covered.** No Italian LNG or storage is on disk. GIE has them, but fetching them would need a new rule.
- **Short post-subsidy sample.** It is 11 weeks with MIBGAS at €25–48, so a response that exists only under 2022-level tightness is outside what it can see.

**Reviewer notes**
- **Which 46 weeks.** Drafts B and C said B3's 46 weeks drop an unknown week. It is 2022-06-13: `core()` reindexes g to the matrix weeks and treats weeks before `CAP0` (2022-06-15) as pre-cap. 34 of the 46 have g > 0 (B said 35 of 47).
- **`dtrs` is not quite constant.** A and C said Spain's is constant. It is 1,910.4 on 670 of 677 days and 2,132.3 on 7. Dropping Iberian utilisation still stands.
- **Send-out and net withdrawal.** A kept net withdrawal as a candidate, and B made Sines utilisation a main candidate. Both are gas-burn flows, i.e. bad controls, so they were made diagnostic rows. The mechanical link is handled by the identity send-out = arrivals − Δstock, with A's and C's "report only" status.
- **Storage baseline.** B used 2018–2020, A and C 2018–2021. I chose 2018–2021 by ISO week to match the existing MITECO anomaly. B's own check shows the two correlate 0.997.
- **Tank fill level or anomaly.** C made the anomaly the main version, A and B the level. I chose the level as main, because the must-burn story is about absolute fullness. The anomaly is a screen row.
- **Which lags can flag.** C made other lags flaggable. Only lag 3 can flag here, to keep the number of chance hits down; the other lags are reported.
- **Dropped checks.** C's dispatch check (send-out on lagged combined-cycle output) is dropped: that output comes from the same bids, and the identity already handles the problem. C's lead placebo is kept.
- **Coverage claim.** A said 82–100% of dose-week values lie inside the no-dose ranges. That misleads under sample intercepts, so the table gives each sample's range separately instead.
- **Arrivals count.** C reported 66 of 644 days with arrivals below −50 GWh. It is 71 of 677 days on 2021-09-01 → 2023-07-09; it depends on the window.
- **What I verified.** All kept numbers were recomputed: c\* per sd (A's and B's agree with mine to rounding), R², ranges, lag correlations, revision dates. Scratch script: /private/tmp/claude-501/-Users-theodor-projects-vre-spain-thesis/53005151-88f1-46f1-9e65-a5d2c166c2b5/scratchpad/review/gie_review.py

*Drafted by three independent drafts merged by a reviewer (workflow wf_15171db0-f0b, 2026-11-05), read before committing. Nothing above was run on the outcome.*
