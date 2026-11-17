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
