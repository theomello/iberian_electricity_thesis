# Does sunshine move load directly? A probe of the solar instrument on plants that cannot respond to price (pre-registration)

**Status: registered 2026-11-18, before any run and before the script exists. Nothing below has been estimated.** Follows `2026-11-17-industry-iv-price-shape-design.md`: in the price-shape design the solar instrument (S1, midday radiation) gave σ = -0.065 [-0.141, -0.030] and the wind-shape instrument (W1) -0.016 [-0.047, +0.005] on 2019-23 (Hansen p 0.029); in the 2024-25 extension, boosting (N1) carries S1 because W1's first stage is 8.0. S1's registered threat is a **direct effect**: sunshine lowers *metered* midday load (behind-the-meter solar self-supply, cooling), which raises ln(L_E / L_M) on sunny days whatever the price does, and would mimic a negative σ.

**In one example.** A cement plant in the interruptibility service must keep consuming at least its declared floor (Orden IET/2013/2013), so it cannot move its load when the price ratio changes. If on sunny days its evening-to-midday load ratio still rises, sunshine moves load directly (onsite solar, cooling), not through the price. If it does not, that channel is not visible in plants of this kind.

## Estimand and data
- **Probe outcome:** week-on-week change in ln(L_E / L_M) of the **metered load of the interruptibility-service participants** (ESIOS 836-846, peninsular; E = hours 19-22, M = hours 11-15; blocks as the price-shape design), non-holiday weekdays, complete 24-hour days, **2019 only** (the series is flat at about 3 GW through 2019, halves in January 2020 and ends in July 2020), the frame of `industry_iv_metered.py` with the price-shape variables.
- **Probe quantity:** the **reduced form** of an instrument on that outcome: slope of the (residualised) outcome on the (residualised, standardised) instrument, for **S1** and for **W1**, separately. No price enters. Residualisation by the **N2** learner (OLS on weekday and month dummies, E and M block temperature and demand-forecast changes, own lags of the outcome at 7/14/28 days and gas; the OLS learner because the sample is about 210 days and boosting is unreliable at that size). Inference: 1,000 permutations of the instrument residuals across days within year-month, seed 20261117, randomization interval by test inversion (`industry_iv_estimation.run_sub` with the instrument as its own regressor, scale 1).
- **Benchmark direct effect D** (an instrument-step quantity, no outcome of the probe): if S1's excess negativity over W1 were entirely a direct effect δ of S1 on the aggregate ln(L_E / L_M), then the IV slope of S1 would exceed the true slope by δ / π_S, where π_S is the first-stage coefficient of the price-ratio change on S1. So **D = (slope_S1 - slope_W1) x π_S**, with slope_S1 = +0.0647 and slope_W1 = +0.0164 (the slopes of the outcome on the ratio, which are σ-hat with the sign reversed, from the primary step 1 with N2) and π_S computed in the script from the primary sample (price-ratio change on S1, N2 residuals). D is in log-ratio points per standard deviation of S1.

## Rules (each says what a failure would tell us)
- **P1 Power.** Plant D (direct, no price) into the probe outcome, y* = y + D x S1 (S1 the raw standardised change; the residual of the planted outcome refitted by N2): the reduced form must be **detected** (p at most 0.05, interval excludes zero) and **recovered** (interval contains D). *Fails:* the probe cannot see a direct effect of the size that would explain S1's behaviour; it is **uninformative** and condemns nothing; P2-P4 are not read.
- **P2 Wind is clean.** The reduced form of W1 on the probe outcome has p above 0.05. *Fails:* wind shape also moves these plants' ratio directly (a weather channel such as temperature or cloud correlated with wind), so neither instrument is clean and the shape design is closed with that diagnosis.
- **P3 Solar direct effect.** The reduced form of S1 on the probe outcome is **detected** (p at most 0.05, interval excludes zero) **and** has the sign of D. *Passes (that is, the direct effect is present):* S1 is **dropped** as an instrument in every sample; the extension's step 1 then rests on **W1 under N2** (its gate passed under N2: F 14.7, planted 0.15 recovered at 0.172 [0.132, 0.226]), which is registered here as the consequence of P3 and replaces the N1-first order for that sample only.
- **P4 Context (no pass/fail).** The reduced forms of S1 and W1 on the aggregate E3-E6 outcome in the same 2019 sample, beside the probe's, with D.

## What each outcome means
- **P1 passes, P2 passes, P3 present:** the self-supply or cooling channel is visible in plants with no price response; S1 is invalid, the primary-sample σ from S1 and from W1+S1 are discarded, and the extension uses W1 (N2) only.
- **P1 passes, P3 absent:** no direct effect of D's size in 2019 plants of this kind; S1 is **not condemned** but also not cleared for 2024-25 (self-consumption was larger then and the probe sample has no 2024-25 data: the series ends in 2020). The extension's step 1 is then run **both ways, reported side by side**: N1 with S1 (the registered order) and N2 with W1. A disagreement between them is read as heterogeneity or invalidity indistinguishably, and stated so.
- **P1 fails:** uninformative; the extension runs both ways as above; the S1 result keeps its flag.
- **P2 fails:** the whole price-shape design is closed (no clean shape instrument).

## Limits stated before the run
One year (about 210 days); plants under a consumption floor are not representative of industry; self-supply at these plants may differ from the aggregate's; 2024-25 cannot be probed. A probe can condemn S1 but not clear it.

## Data and code
Script `scripts/analysis/industry_iv_solar_probe.py` (one pass: P1-P4 and the benchmark D), to be written and committed before any run, reusing `industry_iv_price_shape.py` (block frame, learner N2) and `industry_iv_metered.py` (series). Output `outputs/tables/industry_iv_solar_probe{,_checks}.csv`. **Running needs the user's go-ahead ('Confirmed, run it').** The extension's step 1 waits for this probe.

## Results
(see below)

### Run 2026-11-18 (`industry_iv_solar_probe.py`, committed before the run; outputs `outputs/tables/industry_iv_solar_probe{,_checks}.csv`). A first launch stopped on a coding error (the first-stage F of a reduced form divides by a zero residual) before any result existed; the F is now undefined for reduced forms (class `RFSub`) and nothing else changed.
Benchmark **D = 0.00252** log-ratio points per sd of S1 (slope_S1 0.0647, slope_W1 0.0164, π_S 0.0522). Probe sample 212 days, 2019. Reduced forms (slope per sd of the instrument, randomization intervals):

| Item | Slope | 95% interval | p (t-rank) |
|---|---|---|---|
| S1 on the interruptible outcome, **planted D** | 0.00611 | [-0.0003, 0.0118] | 0.001 |
| W1 on the interruptible outcome | 0.00016 | [-0.0050, 0.0050] | 0.94 |
| S1 on the interruptible outcome | 0.00359 | [-0.0028, 0.0093] | 0.021 |
| W1 on aggregate E3-E6, 2019 (225 days) | 0.00043 | [-0.0019, 0.0028] | 0.50 |
| S1 on aggregate E3-E6, 2019 | 0.00322 | [0.0005, 0.0060] | 0.001 |

**P1 fails**: the planted D is detected by the t-rank (p 0.001) but its randomization interval [-0.0003, 0.0118] includes zero, and the rule requires both. The probe cannot see a direct effect of the size that would explain S1's behaviour, so it is **uninformative and condemns nothing; P2-P4 are recorded and not read**, per the registered rule. (For the record only: W1's reduced form is a precise zero on the floor plants, S1's is +0.0036 with the sign of D and p 0.021 but an interval containing zero, and the aggregate S1 reduced form +0.0032 [0.0005, 0.0060] is of the size of D.)
**Consequence, registered in advance:** the extension's step 1 runs **both ways, reported side by side**: N1 with S1 (the registered order) and N2 with W1; a disagreement between them is read as heterogeneity or invalidity indistinguishably. S1 keeps its flag in the primary sample.

