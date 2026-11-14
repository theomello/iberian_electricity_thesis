# Extension sketch: what the time-of-use shift did to the wholesale price (not yet pre-registered)

**Status: sketch, 2026-11-13. Nothing run. Becomes a pre-registration (with numbers for the rules) before any estimation.**

**In one example.** On a June 2021 weekday the reform makes households use, say, 4% less at 20:00 and a little more after midnight. At 20:00 the market is on the steep part of the supply curve (gas combined cycles at the margin), so a few hundred MW less demand lowers the price by some euros; at 03:00 it is on the flat part, so the same MW raises the price by less. The replication measures the MW. Our bid curves say how many euros.

## Question
1. **Mechanical:** by how much did the estimated load shift change the day-ahead price in each hour, holding the day's offers fixed?
2. **Behavioural (only if 1 is credible):** did firms' offers at the margin change because the residual demand they face changed (Lerner, `L_i = 1/|ε_i|`)?
Outcome that matters for the thesis: the euros per MWh, and consumers' bill saving, that the reform produced through the wholesale market, next to the demand response the paper reports.

## Theory (two-period model, to be written out in the spec)
- Consumers: CES over peak and off-peak consumption, elasticity of substitution σ. The reform moves the toll ratio by a known amount, so the load shift is `ΔQ_peak = −σ · s · Δln(p_peak/p_off) · Q` (s a share). **This is where the CES / NLS estimator enters**: estimate σ from the within-day allocation (shares sum to one), which is exactly the part of the data the control's level drift cannot touch.
- Supply: the observed day-ahead offer curve `S_d(p)` (convex merit order), taken from the bids, not assumed.
- Equilibrium: `D_h(p) = S_d(p)` hour by hour. The price change from a demand shift ΔQ_h is `Δp_h ≈ ΔQ_h / S_d'(p)`; computed exactly by re-clearing on the effective curve (CLAUDE.md trap: units withdrawn by minimum income and `MIEU` must be handled as in `analysis/step_curves.py`).
- Feedback: PVPC households pay the day-ahead price in their energy term, so a lower evening price lowers their evening price a little and dampens the shift. With σ and `S_d'` the fixed point can be solved; first pass ignores it and bounds it.
- Behavioural part: a strategic firm marks up by `1/|RD_i'|`; the shift moves the clearing point along the curve and changes `RD_i'`. Testable as a change in markup over the cost of the marginal gas unit (`implied_marginal_cost_daily`, `_bid` columns).

## Data (all on disk)
Hourly load effects from the replication (per hour, not per period type: needs the per-hour version of the area-panel DiD); OMIE bid curves `curva_pbc_uof` status `O` and `C` and prices; `implied_marginal_cost_daily` (`_bid`); MIBGAS and EUA; unit ownership.

## What would count as a result (numbers fixed at pre-registration)
- **R1 Validity of the curve:** re-clearing the actual demand reproduces the published price within €0.50 in at least 80% of the post-window hours (the repo's own bar for the re-clear).
- **R2 Sign and size:** evening price falls, night price falls by less or rises, evening-minus-night change negative, with a confidence interval that carries the load-effect uncertainty (resample the DiD).
- **R3 Placebo:** the same exercise on the 18 placebo windows gives an evening-minus-night change whose spread is below the real effect.
- **R4 Level robustness:** the claim is the evening-minus-night contrast, which is not moved by the gas-price level (the common component is shared by all hours), as in the replication.
- **R5 Behavioural (separate, weaker):** the markup contrast between hours does not change by more than the placebo spread. If it does not pass, report the mechanical effect only.

## Threats found already
- **Offer limits changed inside the post window**: €0–180.30 until 2021-07-06, −€500 to €3,000 from 2021-07-07 (CLAUDE.md). Barely binding at 2021 prices, but a break; test with and without July.
- **The clawback was announced on 1 June 2021**, the same day as the reform, and hydro offers changed then (`thesis-framework-adopted` memory). It does not touch the mechanical part (actual curves are used) but **does confound R5**; so R5 is secondary.
- Gas prices rose through summer 2021: handled by the contrast.
- The load effects carry the replication's own caveats (control dependence of the level; the contrast is solid).

## Estimator option raised 2026-11-13: CES by nonlinear least squares
Estimate σ directly from the share equations (`s_h = β_h p_h^{1−σ} / Σ_k β_k p_k^{1−σ}`), by NLS, instead of OLS/IV on log loads. It uses only within-day allocation, so the control's level drift drops out by construction; it gives one structural σ for all six tariff periods that feeds the theory above; and it is the parameter another country's reform would need. **It does not recover the total-level effect** (that is the part that is not identified). First step: a pre-registered check that it reproduces column 4's sign and size when restricted. Not run.

## Heterogeneity inside Spain (user wants to do this)
Households against industry (E1–E6 against E0; the industry design needs hand-built 3.0TD/6.xTD charges, an open item), and hot against cold days (area weather is on disk). It feeds this extension directly: the shift in MW by segment is what gets priced.
