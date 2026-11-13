# Nested CES: peak against the rest, then mid against valley (pre-registration)

**Status: pre-registered 2026-11-13, before any estimation of the nested model.** Follows `2026-11-13-ces-substitution-design.md`, whose rule S5 (one σ for all three periods) was rejected and whose registration says the nested version is then the result to estimate. Branch `tou-policy-prices`.

**What was seen before this registration (disclosed).** The single-σ run (σ̂ = 0.0654); its share-level diagnostics (σ from the peak share alone 0.074, from the mid share alone −0.005); and, in debugging, the post-window means of the log-ratio residuals (peak/valley −0.063 against a log price-ratio change of 0.66; mid/valley −0.039 against 0.22), which by plain division suggest a mid/valley substitution of the order of 0.1-0.2 and a peak/rest one near 0.07. The rules below are set with that in view, and are written so that they can fail.

**In one example.** A household that finds the evening dearer does not move its use to the night in one step. It first moves some use from the evening to *any* cheaper time (the peak against the rest), and then arranges the rest of its day between the in-between hours and the night. The first margin is hard (cooking, lighting, TV at 20:00); the second is easier (the dishwasher or the water heater at 15:00 or at 03:00). Nested CES lets the two margins have different elasticities.

## Model
Periods `P` (peak: hours 10-13, 18-21), `M` (mid: 8-9, 14-17, 22-23), `V` (valley: 0-7); nest `N = {M, V}`. Taste shifters as in the single CES.
- **Within the nest** (elasticity `σ_L`): `q_M/q_V = (a_M/a_V) (p_M/p_V)^{−σ_L}`; the nest price index `P_N = (a_M p_M^{1−σ_L} + a_V p_V^{1−σ_L})^{1/(1−σ_L)}`.
- **Between the peak and the nest** (elasticity `σ_U`): `q_P/q_N = (a_P/a_N) (p_P/P_N)^{−σ_U}`, `q_N = q_M + q_V`.
- With `σ_U = σ_L` this is the single CES: the nesting restriction is `σ_U = σ_L` (one equation, a Wald test).
- **Reference form used for estimation** (prices relative to the pre-reform means `p̄`, tastes at the reference from the LASSO path as in the single CES, `ŵ0`):
  `π_M = ŵ0_{M|N} e^{−σ_L ρ_M} / (ŵ0_{M|N} e^{−σ_L ρ_M} + ŵ0_{V|N} e^{−σ_L ρ_V})`, `ρ_k = ln(p_k/p̄_k)`, `ŵ0_{M|N} = ŵ0_M/(ŵ0_M+ŵ0_V)`;
  `ln P_N/P̄_N = [1/(1−σ_L)] ln( ε_M (p_M/p̄_M)^{1−σ_L} + ε_V (p_V/p̄_V)^{1−σ_L} )`, with `ε_M, ε_V` the pre-reform mean expenditure shares of `M` and `V` within the nest (sum to one) (the limit `σ_L → 1` is the log form);
  `w_P / (1 − w_P) = [ŵ0_P/(1 − ŵ0_P)] · exp( −σ_U [ρ_P − ln P_N/P̄_N] )`; `w_M = (1 − w_P) π_M`, `w_V = (1 − w_P)(1 − π_M)`.
- **Elasticities** (η = 0): the peak is alone in its nest, so its own-price elasticity is `ε_PP = −σ_U (1 − e_P)`; the within-nest substitution is `σ_L`, the between-nest one `σ_U`. The other own and cross elasticities are reported from finite differences of the estimated share system at the pre-reform means; they are not rules.

## Estimation (identical to the single CES except the share function)
Nonlinear 2SLS on `E[Z_d ⊗ (w_{kd} − ŵ_{kd}(σ_U, σ_L))] = 0`, `k ∈ {P, M}`, instruments `[1, policy ratio (post indicator), weather, month dummies]` with dependent columns dropped, the same sample (weekdays, 2018-01-01 → 2020-12-31 without 2020-03-01 → 2020-06-30, and 2021-06-01 → 2021-09-14), the same controls (REN main), clustered by week. Two parameters; the policy regime gives two independent moment equations (the peak and the mid share), so the pair is just identified by the policy and over-identified by the weather and month instruments. Code: the share function `shares_nested` added to `scripts/analysis/tou_ces.py` beside the single CES.

## Rules, set before the run
- **N1 Identification.** Both first-stage F (peak/valley and mid/valley price ratios on the policy ratio) at least 10, and the smallest over largest singular value of the moment Jacobian in the two parameters at least **0.05**. Otherwise the pair is reported as not identified and no other rule is read.
- **N2 Sign and size.** `σ_U > 0` and `σ_L > 0`, each 95% interval excluding zero, each inside [0.02, 3].
- **N3 Nesting.** Wald test `σ_U = σ_L`, 5% level. **Rejected: the nested model is the result and the single-σ result is reported as a restriction. Not rejected: the single CES stands, and `σ̂ = 0.065` is the result.** A rule on direction, registered because the diagnostics suggest it: rejection with `σ_L > σ_U`.
- **N4 Placebo.** In the nine 2019 windows with the fake policy path of the single-CES spec (by weekday position), the real `|σ̂_U|` and the real `|σ̂_L|` each rank in the top 2 of 10.
- **N5 Robustness.** `σ̂_U > 0` and `σ̂_L > 0`, and the same ordering of the two, with no Portuguese control, with the regulated-unit control, and excluding July.
No other specification is tried after a failure.

## What each outcome means
N1-N5 pass with `σ_L > σ_U`: substitution is easier between the in-between hours and the night than between the peak and the rest; the reform's shape response is a peak-versus-rest margin with σ near 0.07 and a mid-versus-valley margin larger, and the supply-side extension simulates the two margins separately. N3 not rejected: the single-σ result stands and the S5 rejection was weak identification. N1 fails: the nested parameters are not identified from one policy regime; the household-versus-industry split (a much larger price shock) is the way to identify them, and this is recorded as a limit. N4 fails for one of the two: that margin is not distinguished from noise.

## Threats
One policy regime (74 days); two parameters from the same regime; the same pre-reference-price treatment as the single CES (the taste path absorbs pre-reform price variation, bounded by the diagnostics); the nest structure (peak against rest) is chosen because the peak is the policy's target and the data rejected equality, not tested against the other nest orders (mid against rest; valley against rest), which are not run here.

## Results (run 2026-11-13, `scripts/analysis/tou_ces_nested.py`, outputs `outputs/tables/tou_nested_ces_{summary,placebo}.csv`)
**N1-N5 all pass. The nested model is the result.** Same sample as the single CES (744 days, 74 in the post window), REN control, nonlinear 2SLS, clustered by week. Nest weights (pre-reform mean expenditure shares): mid 0.619 and valley 0.381 within the nest; the peak is 0.407 of expenditure.

| Parameter | Estimate | se | 95% interval |
|---|---|---|---|
| σ_U, peak against the rest | **0.0738** | 0.0034 | [0.067, 0.080] |
| σ_L, mid against valley | **0.1669** | 0.0129 | [0.142, 0.192] |

| Rule | Result | Verdict |
|---|---|---|
| N1 identification | first-stage F 1,486 and 453; Jacobian smallest/largest singular value 0.197 (bar 0.05) | pass |
| N2 sign and size | both positive, intervals exclude zero, both inside [0.02, 3] | pass |
| N3 nesting | Wald σ_U = σ_L: 68.9, p < 0.0001, σ_L > σ_U: **nested model is the result**; the single σ̂ = 0.065 is a restriction | rejected |
| N4 placebo | σ_U ranks 1 of 10 (placebo −0.011 to +0.006), σ_L ranks 1 of 10 (placebo −0.013 to +0.018) | pass |
| N5 robustness | both positive and σ_L > σ_U in every variant: no control σ_U 0.070 / σ_L 0.214; regulated-unit control 0.077 / 0.300; excluding July 0.075 / 0.169 | pass |

**What it says.** Households substitute about twice as readily between the in-between hours and the night (σ_L ≈ 0.17) as between the peak and everything else (σ_U ≈ 0.07). Both are far below 1: the periods are complements at either margin, but the mid-to-valley margin is the one that moves. The single σ of 0.065 was close to the peak margin because the peak share carries most of the weight in the share residuals. The own-hour elasticity of the peak with η = 0 is −σ_U(1 − e_P) = −0.044, against −0.0999 for E0 column 4, so S3's finding stands: the shape response explains under half of column 4.

**Limits, stated.**
- **σ_L's range:** it depends on the control: 0.17 (REN), 0.21 (none), 0.30 (regulated unit). The ordering and the sign do not move; the size of the mid-valley margin is known to within a factor of two, not better. σ_U is steadier, 0.070 to 0.077.
- **One regime:** both parameters come from one policy regime (74 days); the Jacobian ratio of 0.197 says the two are separately identified, but the placebo spread (about 0.01 for σ_U, 0.02 for σ_L) is the error scale to believe, not the standard errors.
- **Nest order:** peak against the rest was chosen because it is the policy's target; the other orders were not tested.
- **Level:** η is still not identified.
