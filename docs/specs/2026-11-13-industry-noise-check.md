# Industry CES: noise check before any registration

**Status: rule written 2026-11-13, before the check was computed.** Uses only pre-reform data (2018-01-01 → 2020-12-31 without 2020-03-01 → 2020-06-30), so no post-reform effect is looked at. Follows the finding that the cross-tariff run of 2026-11-12 (`2026-11-12-industry-voltage-design.md`) gave noisy, dose-unrelated results for the high-voltage series.

**Question.** Is the pre-reform noise in the evening-to-night load ratio of each industrial series small enough to detect an elasticity of substitution of household size, given the dose that series received?

**Method.** For each series (E0 as the anchor, E1+E2 = ESIOS 1202+1203, 6.2 = 1216, 6.3 = 1217, 6.4 = 1218): weekdays that are not holidays in Spain and Portugal; `y = ln(q_evening / q_night)` with evening hours 18-21 and night hours 0-7; the paper's taste LASSO of `y` on weather and month (as `tou_ces.py`), **fitted leaving each pre-reform year out in turn** (2018, 2019, 2020) so that residuals are out-of-sample as they will be in the post window; the same for Portugal's REN ratio; residual `r` = Spain's minus Portugal's. Noise = the standard deviation across all windows of 74 consecutive eligible weekdays (the post window has 74; step of 5 days) of the window-mean of `r`: it contains the day-to-day noise and the slow drift that failed the placebo of the earlier design. The detectable effect is `2.8 × noise` (80% power, 5% two-sided), the detectable elasticity `MDE_σ = 2.8 × noise / dose`, with `dose` the series' reform-induced change in ln price of evening against night from `tou_cross_tariff_dose.csv`.

**Rule, set before the run.** A series is **feasible** if `MDE_σ ≤ 0.15` (about twice the household peak margin 0.074 and below the mid-valley one 0.167), **marginal** if `MDE_σ ≤ 0.30`, **infeasible** above 0.30. The industry CES is pre-registered only for feasible series (marginal ones as exploratory, reported apart); if none is feasible, the industry extension stops at this check and the finding is "the 2021 reform does not identify an industrial substitution elasticity at this resolution".

## Result (run 2026-11-13, `scripts/analysis/tou_industry_noise.py`, `outputs/tables/tou_industry_noise.csv`; 670 eligible weekdays, window of 74 days, step 5)
| Series | Dose (ln points) | Daily sd | Window-mean sd | Detectable effect (2.8 sd) | **Detectable σ** | Signal/noise if σ = 0.074 / 0.167 | Verdict |
|---|---|---|---|---|---|---|---|
| E0 (anchor) | 0.637 | 0.0385 | 0.0098 | 0.027 | **0.043** | 4.8 / 10.9 | feasible |
| E1+E2 | 0.163 | 0.0543 | 0.0186 | 0.052 | **0.320** | 0.65 / 1.46 | infeasible (marginal bar 0.30, missed by 0.02) |
| 6.2 | 0.074 | 0.0428 | 0.0143 | 0.040 | **0.544** | 0.38 / 0.86 | infeasible |
| 6.3 | 0.062 | 0.0502 | 0.0125 | 0.035 | **0.566** | 0.37 / 0.83 | infeasible |
| 6.4 | 0.042 | 0.0609 | 0.0131 | 0.037 | **0.881** | 0.24 / 0.53 | infeasible |

**By the rule written before the run, the industry CES stops here.** No high-voltage series can detect a household-sized elasticity of substitution with the reform of 2021: the noise in the evening-to-night ratio (1.3-1.9 points over a 74-day window, drift included) is about as large as the effect a household-sized σ would produce on their doses (0.5-1.2 points), and the dose is a quarter to a twentieth of the household one. E1+E2 is the nearest miss (detectable σ 0.32 against a bar of 0.30) and would detect only an elasticity twice the household mid-valley margin; the rule is not bent for it. The anchor E0 is detectable down to σ = 0.043, which is why the household estimates are readable.
**Finding to report:** the 2021 reform does not identify an industrial substitution elasticity at this resolution (daily national series by voltage level). What would: a much larger dose (a reform that changed industrial price ratios by an order of magnitude more), firm- or sector-level hourly data with their own noise, or a source with the 3.0TD customers separated from households (the 3.0TD dose is 0.31 to 0.40, about half the household one, but the customers sit inside E0).
