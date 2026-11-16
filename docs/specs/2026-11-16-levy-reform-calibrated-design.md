# Reform and levy in the paper's window: a calibrated decomposition in euros per MWh (proposal)

**Status: proposed 2026-11-16, not registered. The rules become binding when the user confirms and this file is committed; the first run follows that commit. This is a new registered check, not a rescue of H6 (which failed and stays failed in `2026-11-14-hydro-levy-simulation-design.md`).**

**In one example.** In the paper's window (1 June → 14 September 2021) two things changed at once: the time-of-use tariff moved households' load from evening to night, and hydro owners re-priced their offers after the 1 June clawback announcement. On a typical weekday evening the market cleared at about €103; with hydro offered as before the announcement it would have cleared at about €108.6 (the levy channel, −€5.6), and with the reform's load shift put back it would have cleared about €2.4 higher in the evening than at night. A consumer buying one MWh over the window pays the average of these prices weighted by when the load falls. The question is how much of the change in that average price per MWh belongs to the reform and how much to the levy, and whether the two add up.

## Why this is new
Enrich-Li-Mizrahi-Reguant measure the load response to the tariff and read it as a price elasticity. The same window contains the clawback announcement, which changed hydro's offers in the very hours the tariff targets. Our four-state re-clear (`hydro_levy_simulation.py`, H1-H3, H5, H7 passed) separates the two channels in prices; what it lacks is (i) an estimate in euros per MWh that a consumer or regulator reads, and (ii) a scenario module whose level matches the data. The nested CES overshot the estimated period shifts at the actual ratio (H6: peak −3.5 vs about −2.2, valley +7.4 vs about +4.5). The calibration below replaces the CES shares by the estimated DiD effects themselves.

## Design
- **Four states** as before on each valid weekday hour's effective offer curve: actual (AA), reform removed (AR), hydro as before the announcement (HA), both (HR). Reform removed = the DiD period effects `B_k` (peak, mid, valley) from `tou_price_effect` put back as extra demand, energy neutral by day.
- **Consumer cost per MWh in state s:** `C_s = Σ_h L_{s,h} p_{s,h} / Σ_h L_{s,h}` over the valid weekday hours of the window, `L_s` = actual national load for AA and HA, actual load plus the extra demand for AR and HR. Reform effect `R = C_AA − C_AR`, levy effect `H = C_AA − C_HA`, interaction `I = (C_AA − C_AR) − (C_HA − C_HR)`.
- **Calibrated scenarios:** tariff dose `m` times the actual (m ∈ {0, 0.5, 1, 1.5, 2}) as load shifts `L_m = L_actual × exp(−(1−m)·B_k − c_day(m))`, `c_day(m)` chosen so that daily energy is unchanged. At m = 0 this is exactly the reform-removed state, at m = 1 it is the actual state. It assumes the DiD period effects scale linearly in the log tariff ratio (the paper's own log-linear Equation 4); the CES is not used.
- **Uncertainty:** 2,000 draws of `B` from the estimated covariance; week-block bootstrap (2,000) for the hydro effect; the curves and the pre-announcement ratios are taken as known.
- **Placebo:** the nine 106-day windows starting 2019-01 → 2019-09, with the fake policy path of the price-effect run and pre-announcement ratios from the 105 days before each window (hydro placebo only where at least 56 pre-days exist), as in the first run.

## Rules, set before the run
- **K1 Anchors.** At m = 0 the calibrated state reproduces AR and at m = 1 it reproduces AA in every hour (identity to 1e-6).
- **K2 Reform effect in euros.** `R` under actual hydro is negative (the tariff lowers the average cost per MWh by moving load to cheaper hours) with a 95% interval excluding zero.
- **K3 Levy effect in euros.** `H` is negative with a 95% interval excluding zero and lies in [−€10, −€0.10]/MWh.
- **K4 Additivity.** `|I| ≤ 25%` of `|R|`. Pass: the two channels add and the split is reported as additive. Fail: both are reported and the interaction is the finding.
- **K5 Shape in the dose.** The cost-per-MWh effect of the reform is monotone in `m` under both hydro regimes and negative at every `m > 0`.
- **K6 Placebo.** The real `|R|` ranks in the top 2 of 10 against the nine placebo windows' reform effect in the same units, and the placebo levy effect has mean absolute value at most a third of the real `|H|`.
- **K7 Robustness.** `R` and `H` keep their signs and `H` stays within a factor of two when (a) July 2021 is dropped (offer limits changed on 2021-07-07), (b) the pre-announcement ratios use 2021-03-01 → 2021-05-31 instead of 2021-01-01 → 2021-05-31.
No other specification is tried after a failure.

## What each outcome means
K1-K7 pass: a euro decomposition of the average price per MWh in the paper's window into a reform channel and a levy channel, with a scenario module (the dose curve) anchored to the data, usable for "what if the tariff ratio were twice as large". K4 fails: the reform's effect depends on the hydro regime and a single reform number is misleading; reported with both. K2 or K3 fails: that channel leaves no trace in the average cost per MWh even though it moves prices by hour. K6 fails: the real effect cannot be told from placebo windows and is reported as descriptive.

## Threats
Static re-clear (no strategic reaction, water budget held fixed); the 2021 bilateral share is held as it was; the pre-announcement pattern is estimated on five months; the announcement and the tariff share a date, so the hydro offer change is attributed to the clawback by timing, not proven; national load stands in for PVPC households' load; the DiD effects carry the replication's level caveat (the contrast is robust, the level is not) but the energy-neutral shift removes the level; linear scaling in `m` is an assumption.

## Data and code
All on disk (`outputs/cache/step`, `hydro_cost_daily`, the load-model errors). New code: `scripts/analysis/levy_reform_calibrated.py`, importing `hydro_levy_simulation` and `tou_price_effect`. Outputs `outputs/tables/levy_reform_calibrated_*.csv`.

## Results (run 2026-11-17, `scripts/analysis/levy_reform_calibrated.py`, seed 20261117; outputs `outputs/tables/levy_reform_calibrated_*.csv`)
K1, K2, K3, K6 and K7 pass; **K4 and K5 fail**. Nothing was tried after the failures.

| Rule | Result | Verdict |
|---|---|---|
| K1 anchors | dose 0 equals the reform-removed state, dose 1 the actual one | pass |
| K2 reform effect R | −€0.016/MWh [−0.018, −0.011] on a cost of €103.66/MWh | pass (tiny) |
| K3 levy effect H | −€5.60/MWh [−6.50, −4.86] | pass |
| K4 additivity | interaction +0.036 = 229% of \|R\| (bar 25%); the reform effect is −0.051 with hydro as before the announcement and −0.016 with hydro as offered | **fail** |
| K5 dose shape | actual hydro: 0, +0.008, −0.015, −0.092, −0.172 at m = 0, 0.5, 1, 1.5, 2 (the half dose is slightly positive); pre-announcement hydro monotone: 0, −0.044, −0.053, −0.082, −0.135 | **fail** (non-monotone at m = 0.5 under actual hydro) |
| K6 placebo | reform effect ranks 1 of 10; placebo mean \|levy\| 0.81 vs a third of the real 1.87 | pass |
| K7 robustness | July dropped: R −0.008, H −5.96; pre-announcement ratios 2021-03 → 05: H −5.87 | pass |

**Reading.** In euros per MWh over the whole window the two channels are not comparable in size: the levy channel lowers the average cost by about €5.6, the tariff by about 1.6 cents, a ratio of about 350 to 1. The tariff moves load between hours at constant daily energy, so it reshapes prices within the day (evening-minus-night contrast about −€2.4, H3 of the earlier run) and leaves the load-weighted average almost where it was. The paper's window is therefore, in its average price, almost entirely a levy window; the reform's footprint is in the shape. The reform effect also depends on the hydro regime (K4): with hydro as before the announcement, the load shift saves three times as much, because the same shift runs against a steeper supply at higher hydro offers.
K5 is a shape failure of a tiny quantity: the half-dose point under actual hydro is +€0.008, within the second decimal, and sits on a flat part of the offer curve; read the dose table as nearly flat below m = 1 and falling after. The calibrated scenarios are anchored (K1) but the euro value of a different tariff ratio is of the order of cents per MWh averaged over national load.
Limits: national load stands in for household load, so the level of R understates the saving per MWh bought by the households whose profile moved (the same shift divided by household load only would be larger by the inverse of the household share); the pre-announcement ratios, the static re-clear and the common timing of announcement and tariff are as in the first run.
