# The exposed subgroup: purchases of direct-market industrial consumers (pre-registration)

**Status: registered 2026-11-17, before any run. Nothing below has been estimated.** Motivation: the aggregate bound (+0.0001 [-0.021, +0.028], `2026-11-17-industry-iv-wind-speed-estimation-design.md`) is for all E3-E6 load, most of which is bought through retailers on fixed or indexed contracts and does not see the hourly price. The literature (Herter et al.: 18% of customers give 75% of the response; Schwarz et al.: response from self-generators and batch processes) says the response, if any, sits in a small exposed group. ESIOS 353 (direct market consumers, scheduled day-ahead) is about 481 MW on average, roughly 3% of load, so even a response of -0.3 in that group is only -0.01 in the aggregate and cannot show there.

**In one example.** A steel plant buys directly in the day-ahead market. When wind pushes the price from EUR 100 to EUR 80, it may run its furnace more. In E3-E6 total load that is a rounding error; in the plant group's own purchases it is a visible change. We look at that group directly.

## Outcome series (hourly, week-on-week log differences, as the aggregate design)
- **G1** ESIOS 353: scheduled day-ahead demand of direct market consumers (all).
- **G2** sum of `total_buy_mw` (day-ahead + bilateral + intraday net purchases) of the **process-industry** units in `data/omie/registry/direct_consumers.parquet` (`sample == process`, 76 units, no own generation).
- **G3** same for the **refinery** units (`sample == refinery`, 4 units, own generation).
Units are summed as registered; composition changes (units entering or leaving) are a known source of noise and are not corrected. The panel's `total_buy_mw` is purchases, not metered consumption (the 91% offset finding): estimates are **purchase responses**, an upper bound on consumption response.

## Method (as the wind-speed estimation, nothing else changed)
Common sample, instrument C1 (d_pc, d_pc^2), double ML on the group's own lags (d ln series at lags 7/14/28 days) with the same predictors, randomization inference (1,000 permutations, seed 20261117), elasticity = slope x mean price (92.41). Per group: the real outcome; the placebo outcome (7-day-lagged difference, residualised without its own lag); planted responses beta = -0.1 and -0.3 (d ln y* = d ln y + (beta / pbar) x d p, residual refitted) to report what the group's series can detect.

## Rules
- **X1 Power.** A group is informative only if its planted -0.3 is detected (p <= 0.05, interval excludes zero) and recovered (interval contains -0.3). *Fails:* the group's series is too noisy or too thin for an instrument-based estimate; its real result is reported as uninformative and not read.
- **X2 Placebo.** Placebo p above 0.05. *Fails:* the group's estimate is not interpreted.
- **X3 Detection.** Real-outcome p at most 0.05 and interval excluding zero in an informative group (X1, X2 passed): a purchase response of that group is reported with its interval, translated to the aggregate by multiplying by the group's mean share of E3-E6 load. Otherwise the group's interval is reported as a bound.
- **X4 Context (no pass/fail).** The group's interval next to Hirth et al. (-0.2 to -0.5 for the exposed share) and the literature range (-0.04 to -0.6).

## What each outcome means
A detected negative purchase response in an informative group: the response sits in the exposed customers and the aggregate null is consistent with a small exposed share. An informative group with a tight interval around zero: even exposed purchasers do not move purchases with wind-driven prices (offset or inflexibility). An uninformative group: the data on disk cannot answer the question, and the I90 P48 panel (on hold, disk space) or metered data would be needed.

## Data and code
Script `scripts/analysis/industry_iv_exposed_subgroup.py` (committed before it runs); reuses the settlement frame and second-settlement helpers. Outputs `outputs/tables/industry_iv_exposed_subgroup{,_checks}.csv`.

## Results (run 2026-11-17, script `industry_iv_exposed_subgroup.py`, committed before the run; outputs `outputs/tables/industry_iv_exposed_subgroup{,_checks}.csv`)
Purchase responses to the day-ahead price with C1 (first stage F 90 / 93 / 60), 95% randomization intervals; share = mean of the group in E3-E6 load.

| Group (share of E3-E6) | Real estimate | Placebo p | Planted -0.1 | Planted -0.3 |
|---|---|---|---|---|
| G1 ESIOS 353 direct consumers (12.7%) | **-0.033 [-0.116, +0.017]**, p 0.13 | 0.64 | -0.133 [-0.211, -0.078] detected | -0.342 [-0.407, -0.286] detected |
| G2 process units (2.6%) | -0.007 [-0.091, +0.118], p 0.85 | 0.36 | -0.110 [-0.192, +0.011] not detected (p 0.014, interval touches zero) | -0.313 [-0.389, -0.204] detected |
| G3 refinery units, own generation (4.1%) | -0.069 [-0.157, +0.064], p 0.21 | 0.34 | -0.169 [-0.251, -0.036] detected | -0.399 [-0.495, -0.258] detected |

**Rules.** X1 (power: planted -0.3 detected and recovered): all three groups informative. X2 (placebo p above 0.05): all pass. **X3 (detection): none; no group has a detected purchase response.** Per the rules the results are bounds: G1 rules out purchase elasticities more negative than about **-0.12** (and G3 more negative than -0.16, G2 -0.09), which excludes the -0.2 to -0.5 range that Hirth et al. imply for the exposed share. G1's planted -0.1 is recovered and detected, so a purchase response of -0.1 in the exposed group would have been found. Translated to the aggregate, G1's bound is -0.116 x 0.127 = -0.015, consistent with the aggregate bound of -0.021. These are purchase responses (day-ahead, bilateral and intraday net purchases; ESIOS 353 is scheduled day-ahead): the 91% offset finding means consumption responses could be smaller, not larger. Not examined: heterogeneity among units inside the groups (composition changes are uncorrected), regimes (the 30/72 weighting applies), and responses to sustained price levels rather than wind-driven hours.
