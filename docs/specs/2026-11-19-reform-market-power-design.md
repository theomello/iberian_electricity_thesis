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

## Results (run 2026-11-19; `scripts/analysis/tou_reform_market_power.py`, committed in 0a5940e before the run; outputs `outputs/tables/tou_reform_market_power{,_hours,_checks}.csv`)

**Implementation, stated.** Band h = 5 €/MWh, as the stored panel's default. "Actual" is evaluated at the published
p* (the stored panel's price) and the counterfactual at p* − Δp_h, Δp_h the price-effect test's point effect (actual
re-clear minus counterfactual re-clear), so the curve error cancels as registered. 1,761 hours; mean Δp +€0.22.
X = Nash markup in €/MWh = 100 × stored `incentive_exp_h5`. D1 uses each firm's whole-firm X on the hours it is a net
seller (the markup any of its units would add depends on the firm's whole position).

**Gates.** G1 pass: corr 1.0000, median |difference| €0.0000 on 8,805 firm-hours. G0 pass for all five firms (X
defined in 100% of hours at both prices).

| Firm | Net seller (share of hours) | X mean | X sd | ΔX all hours | ΔX evening 18–21 | ΔX night 0–7 | ΔX, REN level | ΔX, regulated-unit level |
|---|---|---|---|---|---|---|---|---|
| Iberdrola | 53% | +0.12 | 4.37 | −0.004 | −0.32 | +0.42 | −0.37 | −0.94 |
| Endesa | 0% | −8.80 | 5.94 | +0.16 | −0.06 | **+0.75** | −0.21 | −0.84 |
| Naturgy | 1% | −5.17 | 4.14 | +0.06 | −0.09 | **+0.44** | −0.31 | −0.79 |
| EDP | 8% | −6.82 | 7.27 | +0.14 | −0.23 | **+0.84** | −0.44 | −1.33 |
| Repsol | 94% | +0.97 | 0.97 | −0.005 | −0.01 | −0.01 | −0.00 | −0.01 |

(€/MWh; ΔX = X with the reform minus X without it. Bold: above the M1 bar.)

**Rules.**
- **M1 fails for Endesa, Naturgy and EDP** (night block: ΔX +0.75, +0.44, +0.84 against 10% of sd 0.59, 0.41, 0.73);
  passes for Iberdrola (night +0.42 against 0.44, narrowly) and Repsol.
- **M2 passes for all five** (largest |mean ΔX| at Nash 0.16 against 0.50). At the estimated conduct the markup
  change is at most €0.04/MWh (β 0.25) or €0.002 (β 0.01).
- **D1 passes.** Iberdrola's X on its net-seller hours moved +0.11 in June 2021 and +0.02 in June–August, against a bar
  of 0.51 (a tenth of its 2019–21H1 seller-hour level, 5.1). EDP: +0.04 and +0.14 against 0.29. Endesa is never a net
  seller in the window, so its D1 row is empty (not a failure).

**Verdict, as registered.**
- **The hydro stop (D1):** the reform moved Iberdrola's Nash markup on its selling hours by about 2% of its pre-June
  level. It gave Iberdrola's hydro no incentive reason to stop marking up in June 2021. The stop is a change of conduct
  with the reform's incentive held fixed; the clawback announcement of the same day remains the dated candidate (a
  coincidence of dates, not a test of the clawback).
- **Market power (M1, M2):** "unaffected" holds on average (M2, all firms) but **not hour by hour** (M1 fails for three
  firms). The reform moved the incentive across the day: at night, where it added demand and raised the price, the
  three large net buyers' (negative) Nash markups became less negative by €0.4–0.8/MWh; in the evening and at midday
  they moved the other way by €0.1–0.6. Over the day these offset. The thesis states: the reform shifted the market-
  power incentive between hours by under a euro, nets to about zero over the day, and at the estimated conduct
  changes markups by a few cents.

**Reported, no rule.**
- Level of the shift: at the REN (F) and regulated-unit (M) levels ΔX is negative for every large firm (−0.2 to
  −1.3 at M): the window-average sign depends on the unidentified level, as the price effect's evening value did;
  the between-hours pattern (night up, evening down) does not.
- Charging each firm its share of the added demand (its retailers buy household load): ΔX all hours Iberdrola −0.01,
  Endesa +0.12, Naturgy +0.04, EDP +0.10, Repsol −0.01: the same reading.
- By hour (neutral level): positive in hours 0–7 for every firm but Repsol (Endesa up to +1.4 at hour 0), negative in
  hours 10–13 and 18–21; near zero 14–17 and 22–23.
- The M1 bar (10% of the window's own sd) was set without knowing how X's sd compares with the reform's between-hour
  swing; it turned out strict. This is stated, not used to rescue M1.
