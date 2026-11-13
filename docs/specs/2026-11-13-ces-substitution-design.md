# Elasticity of substitution across tariff periods: theory and estimation design (draft)

**Status: pre-registered 2026-11-13 (rules S1-S6 confirmed by the user the same day), before any estimation of the CES share system.** The rules are binding once this file is committed; the first run happens after that commit. Follows `2026-11-13-tou-price-effect-design.md` (which used the reform-specific load effects directly) and the load replication.

**In one example.** A household pays €60/MWh at 20:00 and €45/MWh at 03:00. After the reform the evening price rises to €70 and the night price falls to €35: the ratio moves from 1.33 to 2.0, a log change of 0.41. If the household's evening-to-night use ratio falls by 6.7% (log points) in response, then, holding everything else fixed, a 0.41 move in the log price ratio buys a 0.067 move in the log quantity ratio: **σ = 0.067/0.41 = 0.16**. This number does not say how much the household uses in total, only how it splits the day. That is the object here.

## 1. Two different objects (the user's question)
- **Price elasticity** (the paper's headline, column 4 of its Equation 4): the response of log load in an hour to the log price of that hour. A mixture, derived below: own-hour elasticity `ε_kk = −σ(1−e_k) + η e_k`.
- **Elasticity of substitution** `σ`: how the *allocation* across periods responds to the *relative* price, `σ = −∂ ln(q_k/q_j) / ∂ ln(p_k/p_j)`. It governs the shape of the day.
- **Upper-tier elasticity** `η`: how total energy responds to the general price level. It needs the level of the shift and is the quantity the replication cannot pin down (control dependence). **σ does not need the level**, which is why this design is robust to the problem that stopped the area panel.

## 2. Model
Weekday `d`, period types `k ∈ {P (peak), M (mid), V (valley)}`, `q_{kd}` = energy in the period (MWh), `p_{kd}` = the marginal variable price per MWh the customer faces (energy + tolls and charges). Two-tier demand:
- Upper tier: composite energy service `Q_d = D(P_d)`, elasticity `η ≤ 0`, `P_d` the price index below.
- Lower tier (CES): minimise `Σ_k p_{kd} q_{kd}` subject to `Q_d = [Σ_k a_{kd}^{1/σ} q_{kd}^{(σ−1)/σ}]^{σ/(σ−1)}`. Solution
  `q_{kd} = a_{kd} (p_{kd}/P_d)^{−σ} Q_d`, `P_d = [Σ_k a_{kd} p_{kd}^{1−σ}]^{1/(1−σ)}`, with `a_{kd}` taste shifters, `Σ_k a_{kd} = 1`, `ln a_{kd} = δ_k + γ_k' z_d` (z: temperature terms, month, holiday).
- **Quantity shares** `w_{kd} = q_{kd}/Σ_j q_{jd} = a_{kd} p_{kd}^{−σ} / Σ_j a_{jd} p_{jd}^{−σ}`. **(A)**
- **Log ratios** `ln(w_{kd}/w_{Vd}) = ln(a_{kd}/a_{Vd}) − σ ln(p_{kd}/p_{Vd})`. **(B)** Total energy `Q_d` and the control's level drift have disappeared.
- **Elasticities.** With expenditure shares `e_k = p_k q_k / Σ_j p_j q_j` (and `∂ ln P/∂ ln p_k = e_k`): `ε_kk = −σ(1−e_k) + η e_k`; `ε_kj = (σ+η) e_j`. Example: `e_P = 0.4`, `η = 0`: the paper's column 4 of −0.086 gives `σ ≈ 0.086/0.6 ≈ 0.14` (illustrative arithmetic, not an estimate). `σ < 1` means the periods are complements: the shape of the day is hard to move.

## 3. Equilibrium with the wholesale market (the link to the price-effect run)
`p_{kd} = τ_{kd} + φ_k π_{kd}`: policy part `τ` (tolls, charges; exogenous) and the wholesale price `π` passed through with share `φ_k` (PVPC customers: near 1; fixed-price contracts: 0). Wholesale reacts to quantity: `d π_k = m_k dQ_k` (the slope of the effective curve, € per MW, measured in the bid data), so `ψ_k ≡ m_k q_k/π_k` is the price elasticity of supply seen by the customers. Then `d ln p_k = dτ_k/p_k + θ_k ψ_k d ln q_k` with `θ_k = φ_k π_k/p_k`.
Two periods (P, V), energy conserved within the day (`w_P Δ ln q_P + w_V Δ ln q_V = 0`), `x = Δ ln(q_P/q_V)`, `Δρ` the log change in the policy price ratio:
`x = −σ [Δρ + Φ x]`, so **`x = −σ Δρ / (1 + σ Φ)`**, `Φ = θ_P ψ_P w_V + θ_V ψ_V w_P ≥ 0`.
- The reform's observed shift is the partial-equilibrium response **attenuated by `1/(1+σΦ)`**: a lower evening price from the shift itself dampens the shift.
- OLS of `x` on the *observed* price ratio is biased (the wholesale part is endogenous); the policy ratio is the instrument, as in the paper (`z = ln(charge + ē)`).
- Orders of magnitude from the price-effect run (rough): `ψ_evening ≈ 0.25`, `ψ_night ≈ 0.55`; with `θ` well below 1 and `σ ≈ 0.15`, `σΦ` is a few per cent. The feedback is small in 2021; it would not be at other tariff ratios or in tighter markets. Three periods are solved numerically.

## 4. Estimator
- **Moment conditions** (nonlinear IV / GMM, which is NLS with instruments): `E[ Z_d ⊗ ( w_{kd} − ŵ_{kd}(σ, δ, γ) ) ] = 0` for `k ∈ {P, M}` (V by adding up), with `ŵ` from (A), `Z_d` = policy price ratios `ln(τ_P+ē)/(τ_V+ē)`, `ln(τ_M+ē)/(τ_V+ē)`, weather terms, month dummies, holiday. Minimise the weighted sum of squared moments; standard errors clustered by week (as the replication).
- **Tastes** `a_{kd}`: pre-reform fit (the replication's pre-period, 2018-01 → 2020-12 without the lockdown), flexible in temperature as the paper's LASSO (a LASSO on `ln(w_k/w_V)` in place of the per-hour log-load LASSO); the post window then identifies σ from departures of the shares from the taste path.
- **Control:** Portugal's log share ratio enters as the common-shape control (rooftop solar, teleworking, EV charging move the shape in both countries); Portugal's ratio uses no policy change. Dropping it must not change the sign.
- **Why NLS and not OLS on (B):** the three shares sum to one and are bounded, so a joint system with one σ is more efficient and respects the adding-up; OLS on two log ratios gives the same σ only if the errors are uncorrelated and ignores the restriction that both share σ. The test of the CES restriction (`σ_{PV} = σ_{MV} = σ_{PM}`) is a Wald test on a nested-CES version (peak vs non-peak, then mid vs valley).
- **What the data allow:** one policy break for households (2021-06-01), so identification is one event plus the variation of wholesale prices within the day (instrumented away). Inference by placebo windows, as before. **Households against industry** is where it gets stronger: the 2021 tolls moved industrial peak/valley ratios by far more (`tou_tariff_hourly_change.csv`: tariff 3.0, weekday hour 8-20, log change in price 1.5 to 1.8 against 0.08 in the valley), so `σ` by segment is identified from a larger shock (the heterogeneity extension). Hot against cold: let `σ` interact with a temperature indicator, or estimate on split samples.

## 5. What it adds beyond the replication
- A **structural parameter** that transfers: any tariff ratio (France's off-peak shift, a deeper valley discount, industry) can be simulated, with the supply side pricing the response (section 3).
- **Level-free**: the unidentified level problem (η) is not needed.
- **Welfare-relevant**: the ideal price index `P_d` gives the cost of living of the tariff shape.

## 6. Rules, set before the run (confirmed 2026-11-13)
- **S1 Identification:** first stage of the observed price ratio on the policy ratio, F ≥ 10.
- **S2 Sign and size:** `σ > 0`, 95% interval excludes zero, `0.02 ≤ σ ≤ 3`.
- **S3 Consistency:** the implied own-hour elasticity with `η = 0`, `−σ(1−e_P)`, lies within one standard error of the replication's column 4 (−0.086 on E0).
- **S4 Placebo:** in the nine 2019 windows with a fake reform date and the fake policy ratio of the same size, the real `|σ̂|` ranks in the top 2 of 10.
- **S5 Restriction:** equal pairwise σ (CES) not rejected at 5%; if rejected, the nested version is the result.
- **S6 Control:** the sign of σ is the same without the Portuguese ratio, with the REN and the regulated-unit controls, and excluding July.
No other specification is tried after a failure.

**Fixed details for the run.** Sample: weekdays that are not holidays; pre-reform fit 2018-01-01 → 2020-12-31 without 2020-03-01 → 2020-06-30; post window 2021-06-01 → 2021-09-14; E0 (ESIOS 1201) against Portugal's consumption (REN), the series of the price-effect run; period types and hours as in the replication (peak 10-13 and 18-21, valley 0-7, mid the rest); price per period `p_k` = the tariff's toll and charge for the period plus the reference energy price `ē` of the replication (`tou_elasticity_paper.prices`), so the policy ratio is the instrument and the main regressor. **S4 placebo:** in each of the nine windows of 106 days starting 2019-01 → 2019-09 the real post-reform policy-ratio path is assigned to the window's days by position (day 1 of the window takes the ratio of 2021-06-01, and so on), shares come from the cross-fitted taste fit, and the same estimator gives `σ̂`; the rank is on `|σ̂|`. **S3** compares to column 4 of `tou_area_panel_pc_elasticity.csv`-style E0 output (`tou_elasticity_paper`, E0 against Portugal), with `e_P` the pre-window mean expenditure share of the peak period and the standard error of `σ̂` by the delta method. The household-versus-industry and hot-versus-cold versions, the nested CES and the markup test of section 7 each get their own pre-registration before they run; this one covers the pooled household E0 run only.

## 7. The markup test with the windfall levy controlled (the third candidate)
**Who the levy hits.** RDL 17/2021 (law of 16 September 2021, in force to 31 December 2023) claws back revenue of peninsular non-emitting generation above 10 MW without a specific remuneration framework: in practice nuclear, hydro and merchant renewables (`notes/rq-clawback-size-rdd.md`). The repo's notes date the hydro offer behaviour change to its announcement on 1 June 2021, the reform date. Gas units are not charged by it.
**Where it enters.** Not the mechanical price effect (the day's actual curves already contain whatever hydro and nuclear did). It enters the markup test through the residual demand facing a gas owner: if the levy changed hydro and nuclear offers in some hours, the marginal gas unit's markup changes without any reform response.
**Control, by owner exposure.** Unit-step panel of every plant-specific gas unit's offered steps in the competitive range, markup `m = offer − cost (_bid)`; regress the evening-minus-night markup change (post against pre) on the owner's levy exposure `E_f` (non-emitting MW above 10 MW over total MW, from `unit_ownership`):
`Δ(m_eve − m_night) = β0 + β1 E_f + u`. The reform acts on all gas owners alike; the levy acts through `E_f`. **`β0`, the effect for an owner with no exposure, is the reform's behavioural effect with the levy channel removed.** Limit: about a dozen owning firms, so inference by wild-bootstrap or randomisation over owners; the hour-shaping of hydro (evening dispatch) is a second-order concern absorbed by `E_f` only if exposure is proportional to shaping. Also report the version with hydro offered MW and `hydro_cost_daily` as covariates by hour.
