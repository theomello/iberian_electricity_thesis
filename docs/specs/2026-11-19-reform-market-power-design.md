# T2: did the June 2021 reform change generators' market power? (pre-registration, proposed; contains D1)

**Status: proposed 2026-11-19, not registered. Binding when the user confirms and this file is committed; the run
follows that commit.** Framework: `notes/thesis-demand-supply-link.md` §2 (equation S). Inputs: the counterfactual
load shift and re-clearing of `2026-11-13-tou-price-effect-design.md` (done, R1–R4 pass) and the firm incentive of
`scripts/analysis/firm_incentive_rebuild.py`. Firm table: `notes/hydro-departure-by-firm.md`.

**In one example.** At 20:00 on a June 2021 weekday Iberdrola is a net seller of 2,000 MW in the auction, and rivals'
offers plus buy bids add 400 MW per €/MWh around the clearing price. A Nash firm would add 2,000 / 400 = €5/MWh: that
is its Nash markup X. Without the reform, demand at 20:00 would have been a few hundred MW higher, the market would
have cleared slightly further up the curve, where the curve may be steeper or flatter, and Iberdrola's net position
would differ. Recompute X there. If X moves from €5.0 to €4.9, the reform did not change what market power was worth.

## Estimand
For firm j and hour h: X_jh = n_jh / |RD'_jh| (€/MWh), the Nash markup, with n the net auction position and RD' the
slope of j's residual demand at the clearing price, exactly as `incentive_net` / `_exp_` in
`firm_incentive_rebuild.py` (own buy bids removed from the band, regulated pass-through volume out of n, its offers
given to rivals; band ±h as there; ownership from `lib/unit_ownership.py`). Markup = β · X, the scale of the conduct
estimates (`price_taking_simulation_hydro_size.csv`: markup = β × x).

**ΔX_jh = X_jh(actual) − X_jh(no reform)**, both computed by the same new code on the same day's bids:
- actual: at the re-cleared actual price p*_h;
- no reform: at p^cf_h, the re-cleared price with the buy side moved by −ΔQ_h (the main energy-neutral counterfactual
  of the price-effect test), and with n_j and the band evaluated at p^cf_h (j's own cleared sales and purchases from
  its own offers at that price).

## Sample
Weekdays that are not holidays, 2021-06-01 → 2021-09-14, the 1,761 `valid` hours of the price-effect test.
Firms: Iberdrola, Endesa, Naturgy, EDP, Repsol (all units), and the same five restricted to hydro units for D1.

## Rules (set before the run)
- **G0 Coverage:** X computable (slope above `MIN_SLOPE`) in at least 70% of window hours for each firm, at both
  prices. A firm failing it is reported and leaves M1–M2.
- **G1 Reproduction:** on the actual curve, the new code's X matches the stored `firm_incentive_net` (`_exp_` column)
  with correlation ≥ 0.99 and median absolute difference ≤ €0.05/MWh. Fail: stop and fix the code before anything else
  is computed (a code fix, not a design change; recorded).
- **M1 Market power unaffected:** for each firm, |mean ΔX| over the window is at most **10% of the standard deviation
  of X_jh** across the window's hours, overall and in the evening (18–21) and night (0–7) blocks separately.
- **M2 Markup bound:** at β = 1 (Nash, the upper bound), |mean ΔX| per firm is below **€0.50/MWh**, a fifth of the
  reform's evening-minus-night price effect (€2.39). The markup at the estimated β (thermal 0.01, hydro 0.25) is
  reported.
- **D1 The hydro stop:** for each firm's hydro on its net-seller hours, |mean ΔX| is at most **10% of that firm's
  2019–21H1 Nash markup on seller hours** (Iberdrola 5.1, EDP 2.9 €/MWh; `hydro-departure-by-firm.md` §2), in June
  2021 and in June–August 2021. Iberdrola is the decisive row (the departure rests on it).

## What each outcome means
- **M1, M2 pass:** the reform moved demand along the supply curve without changing what market power was worth; the
  thesis states "market power unaffected" with the ΔX as its size.
- **D1 passes:** the reform changed Iberdrola's (and EDP's) Nash markup by at most a tenth of its pre-June level, so
  it gave hydro no incentive reason to stop marking up in June 2021. The stop is a change of conduct with the reform's
  incentive held fixed; the clawback announcement (same day) remains the dated candidate, still a coincidence of dates,
  not a test of the clawback.
- **D1 fails:** the reform moved the hydro incentive enough to be a candidate; the timing of the stop cannot be
  attributed to the clawback, and the thesis says so.
- **Logic stated in advance:** β is estimated on X measured on the actual (post-reform) curves, so a firm with
  unchanged conduct shows an unchanged β whatever the reform did to X. A drop of β in June is a change of conduct.
  D1 asks only whether the reform changed the incentive enough to give a reason for it.
- No other window, band, counterfactual level or firm grouping is tried after a failure.

## Reported, no rule
- ΔX under the regulated-unit (M) and REN (F) levels of the shift (the price-effect test's sensitivity levels).
- ΔX by hour of the day, by firm.
- Hydro water value: λ* is computed from forward prices that already contain the reform; the reform's effect on the
  evening-minus-night spread (−€2.4) is compared with the spread that λ* arbitrage rests on, descriptively.

## Threats
- Offers are held fixed by construction: ΔX is the incentive change at given offers, not an equilibrium.
- The band ±h and `MIN_SLOPE` make X noisy hour by hour; the rules use means over the window and the window's own sd.
- The counterfactual level of the shift is not identified (energy-neutral is an assumption; M and F reported).
- Offer limits changed on 2021-07-07 (€0–180.30 → −€500–3,000); June alone is reported for D1 for that reason.
- Only the peninsula; hours with a split price are not `valid` and are out.

## Outputs
`scripts/analysis/tou_reform_market_power.py`; `outputs/tables/tou_reform_market_power{,_hours,_checks}.csv`.
Reads the step cache, the bid archive and the price-effect counterfactual; changes none of them.
