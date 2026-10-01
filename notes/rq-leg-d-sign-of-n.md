# Leg D — the sign of n

Framework spec §4, leg D. Run 2026-10-01 on branch `leg-d`.
Scripts: `build/build_rival_solar.py`, `analysis/iv_two_endog.py`,
`analysis/leg_d_panel.py`, `analysis/leg_d_sign_test.py`; checks in `qa/`
(`check_rival_solar.py`, `check_iv_two_endog.py`, `check_leg_d_panel.py`).
Results: `outputs/tables/leg_d_results.csv`.

**In one line.** Offers respond to X, but not as either model of conduct says:
no common slope fits, and where the instruments are strong the two slopes have
opposite signs, γ⁺ > 0 > γ⁻. For hydro the response is the fringe's, so it is
cost, not conduct.

## 1. Design, as run

For each dispatchable unit-hour of the five firms (EDP, Endesa, Iberdrola,
Naturgy, Repsol):

```
y_uh = α_ud + α_hym + γ⁺ · X⁺_fh + γ⁻ · X⁻_fh + c · fcst_h + ε_uh
```

- **y** is the §3.14 measure: the share of the unit's capacity offered at or
  below the unit-*day*'s volume-weighted median offer price, in percentage
  points (s50; s25 and s75 as robustness). Capacity is `cab` max power that day.
- **X⁺, X⁻** are the hourly means of max(X, 0) and min(X, 0), where X = n/|RD′|
  is the firm's exposed net position over rivals' residual-demand slope, in
  €/MWh (`firm_x.parquet`). γ is in pp of capacity per €/MWh of X.
- **α_ud** is a unit × day effect (it removes the water value or the day's fuel
  price). **α_hym** is an hour × year-month effect (it removes the solar
  profile's growth). **fcst** is REE's day-ahead demand forecast, in GW.
- **Instruments**: z, rivals' offered solar for the firm, in GW; and z · s_prev,
  where s_prev = 1 if the firm was a net seller in the same hour the day before.
  The model is just identified (two instruments, two regressors).
- **Errors** are clustered by ISO week (439 weeks).

**Inference that survives weak instruments.** 2SLS (two-stage least squares)
is read only when both Sanderson–Windmeijer conditional first-stage F statistics
are at least 10 (status `ok`); otherwise the row is `weak`. The following are
valid however weak the instruments:

- the Anderson–Rubin (AR) test of γ⁺ = γ⁻ = 0, which is price-taking;
- the exact AR set of common slopes c with γ⁺ = γ⁻ = c, the roots of a
  quartic; empty means no common slope fits, which rejects supply-function
  Nash;
- each coefficient's AR projection, whose sign is the robust sign test. It
  separates Nash (γ⁻ < 0) from output-based conduct (γ⁻ > 0).

**β scale.** Nash is symmetric in β, and γ = −β × the curve's offer density at
the reference price. So β⁺ and β⁻ divide γ by the mean density in seller and
buyer hours separately (§3.14 scale: β = 1 is full Nash). Their equality and
their common-value AR set are reported beside the γ ones.

**Rules added in implementation** (each recorded in the plan's ledger):

1. **Hours.** Periods are averaged to hours, so a day weighs the same before
   and after the 15-minute switch of 2025-10-01 (15-minute periods are 25.6%
   of all periods in the window).
2. **Absent offers score 0.** In a unit-day the unit is present in, a period
   with no offer scores 0, not missing. Dropping those periods selected on the
   instrument's hours: Endesa's pumped storage offers at midday on 28% of
   unit-days against 90% in the evening.
3. **Over-capacity drop.** A unit-day is dropped if its offered volume exceeds
   1.02 × capacity. From 2025-04 these are combined-cycle alternative complex
   orders (C04), for which the capacity share is undefined.
4. **Dated ownership.** A unit-day is kept only when the OMIE listing in force
   that day (the nearest preceding snapshot; a co-owned unit follows its
   majority owner) puts the unit in the firm X is built for. Repsol is dropped
   before 2018-11-02, the date of its Viesgo purchase.
5. **Fringe placebo.** Units owned outside the five, of 50 MW or more
   (`FRINGE`), have small X. Their reduced form estimates how solar reshapes
   offers through cost alone. It is read against the five firms by technology.
6. **Flags.** `WEAK` marks a conditional F below 10. `FEW-WEEKS` marks
   s_prev = 1 or 0 in fewer than 100 weeks, where AR over-rejects (28% at 3
   weeks, 6% at 100, in the Task 2 review's simulation).
7. **A seven-day lag.** s_prev is a lagged outcome, so a robustness row uses
   the sign seven days before (zs7).

## 2. Sample

Panel `outputs/tables/leg_d_panel.parquet`: **8,083,768 unit-hours**,
2018-01-02 → 2026-05-31. The estimation sample is the five firms' 5,954,775
unit-hours on 134 units, after dropping rows with no s_prev (DST days and the
days after them).

| firm | unit-hours | share on firm-days with both signs of X |
|---|---|---|
| EDP | 1,246,409 | 0.611 |
| Endesa | 1,493,689 | 0.049 |
| Iberdrola | 1,269,590 | 0.790 |
| Naturgy | 1,467,317 | 0.342 |
| Repsol | 542,094 | 0.366 |
| FRINGE (placebo) | 2,064,669 | — |

Units in the panel's unit table, by class:

| firm | CCGT | coal | hydro | pumped |
|---|---|---|---|---|
| EDP | 8 | 8 | 9 | 6 |
| Endesa | 7 | 12 | 11 | 9 |
| Iberdrola | 10 | 3 | 9 | 6 |
| Naturgy | 18 | 4 | 4 | 2 |
| Repsol | 2 | 2 | 20 | 2 |
| FRINGE | 19 | 4 | 24 | 4 |

The table counts 21 pumping legs that never offer to sell (18 of the five
firms', 3 of the fringe's), so 134 of the five firms' units and 48 fringe units
have rows.

**Dropped unit-days.** Ownership: Repsol 4,239 (2018, before Viesgo), Naturgy
322 and 184 (2018, 2019), and FRINGE up to 721 a year. Over capacity: CCGT 1,343
(2025) and 561 (2026), plus two pumped-storage days (MLTG, 2025-03-23 and -25:
520 MW offered against a `cab` max power of 221.4 MW).

**Only units whose curve moves within the day identify.** Share of unit-days
whose s50 moves within the day (sd > 0.5 pp):

| firm | class | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| EDP | CCGT | 0.88 | 0.79 | 0.85 | 0.87 | 0.72 | 0.80 | 0.88 | 0.56 | 0.68 |
| | coal | 0.39 | 0.67 | 0.78 | 0.35 | 0.35 | 0.59 | 0.61 | 0.60 | 0.81 |
| | hydro | 0.51 | 0.54 | 0.61 | 0.58 | 0.45 | 0.46 | 0.43 | 0.46 | 0.40 |
| Endesa | CCGT | 0.95 | 0.92 | 0.90 | 0.80 | 0.60 | 0.73 | 0.95 | 0.52 | 0.92 |
| | coal | 0.39 | 0.76 | 0.67 | 0.85 | 0.28 | 0.51 | — | — | — |
| | hydro | 0.54 | 0.45 | 0.46 | 0.50 | 0.62 | 0.17 | 0.49 | 0.62 | 0.71 |
| | pumped | 0.98 | 0.96 | 0.93 | 0.78 | 0.80 | 0.94 | 0.91 | 0.85 | 0.90 |
| Iberdrola | CCGT | 0.86 | 0.91 | 0.98 | 0.94 | 0.93 | 0.92 | 0.95 | 0.98 | 0.98 |
| | coal | 0.75 | 0.91 | 0.93 | — | — | — | — | — | — |
| | hydro | 0.59 | 0.63 | 0.65 | 0.68 | 0.75 | 0.77 | 0.75 | 0.74 | 0.74 |
| | pumped | 0.01 | 0.01 | 0.00 | 0.01 | 0.03 | 0.17 | 0.40 | 0.54 | 0.34 |
| Naturgy | CCGT | 0.99 | 0.95 | 0.93 | 0.89 | 0.60 | 0.27 | 0.03 | 0.04 | 0.00 |
| | coal | 0.77 | 0.97 | 0.46 | — | — | — | — | — | — |
| | hydro | 0.75 | 0.75 | 0.83 | 0.81 | 0.81 | 0.72 | 0.62 | 0.55 | 0.57 |
| | pumped | 0.01 | 0.00 | 0.15 | 0.00 | 0.01 | 0.00 | 0.00 | 0.02 | 0.12 |
| Repsol | CCGT | 0.08 | 0.18 | 0.36 | 0.23 | 0.39 | 0.64 | 0.60 | 0.64 | 0.09 |
| | coal | 0.66 | — | — | — | — | — | — | — | — |
| | hydro | 0.19 | 0.17 | 0.15 | 0.11 | 0.14 | 0.15 | 0.30 | 0.38 | 0.32 |
| | pumped | 0.50 | 0.32 | 0.66 | 0.67 | 0.72 | 0.88 | 0.99 | 0.93 | 0.97 |

## 3. Results

γ in pp of capacity per €/MWh of X; robust sign from the AR projection
("both signs, 0 out": a set of two pieces, one on each side of 0, which
excludes 0 and leaves the sign open); β on the §3.14 scale.

| sample | n | γ⁺ (se) | γ⁻ (se) | p(γ⁺=γ⁻) | SW F⁺/F⁻ | AR p(0,0) | AR common γ | robust sign γ⁺ / γ⁻ | β⁺ / β⁻ | status |
|---|---|---|---|---|---|---|---|---|---|---|
| **pooled** | 5,954,775 | +3.393 (1.912) | −1.379 (0.279) | 0.009 | 8.9/25.0 | 0.000 | empty (min p 0.023) | 0 inside / **−** | −0.83/+0.38 | weak |
| pooled, s25 | 5,954,775 | +2.457 (1.359) | −0.946 (0.189) | 0.009 | 8.9/25.0 | 0.000 | empty (0.020) | 0 inside / − | −0.60/+0.26 | weak |
| pooled, s75 | 5,954,775 | +0.987 (0.531) | −0.324 (0.077) | 0.010 | 8.9/25.0 | 0.000 | empty (0.009) | 0 inside / 0 inside | −0.25/+0.09 | weak |
| hydro + pumped | 2,718,618 | +1.505 (0.798) | −0.395 (0.094) | 0.012 | 8.0/18.1 | 0.000 | empty (0.008) | 0 inside / 0 inside | −0.39/+0.13 | weak |
| CCGT + coal | 3,236,157 | +4.689 (2.099) | −1.080 (0.404) | 0.008 | 9.0/39.0 | 0.000 | empty (0.001) | **+** / 0 inside | −1.06/+0.26 | weak |
| EDP | 1,233,123 | +5.960 (3.752) | −2.165 (1.681) | 0.123 | 2.5/2.3 | 0.000 | empty (0.000) | both, 0 out / both, 0 out | −1.72/+0.65 | weak |
| Endesa | 1,477,802 | +1.003 (1.527) | −0.162 (0.169) | 0.444 | 7.4/7.2 | **0.463** | [−3.335, 0.302] (0.810) | 0 inside / 0 inside | −0.28/+0.05 | weak, few weeks |
| **Iberdrola** | 1,255,748 | +0.721 (0.209) | −0.498 (0.165) | 0.000 | 15.2/15.2 | 0.000 | empty (0.000) | **+ / −** | −0.17/+0.12 | **ok** |
| Naturgy | 1,451,494 | +2.429 (1.114) | −0.913 (0.714) | 0.006 | 5.8/5.3 | 0.000 | [−∞, −4.365] ∪ [5.966, +∞] (0.089) | 0 inside / 0 inside | −0.62/+0.24 | weak |
| Repsol | 536,608 | −0.008 (1.162) | −7.791 (4.588) | 0.061 | 7.4/3.7 | 0.000 | empty (0.010) | 0 inside / both, 0 out | +0.00/+1.78 | weak |
| 2018–2021 | 3,155,243 | +100.0 (96.1) | −4.849 (3.804) | 0.285 | **1.1**/16.9 | 0.000 | empty (0.002) | both, 0 out / 0 inside | −24.19/+1.40 | weak |
| 2022–2023 | 1,351,505 | +8.120 (8.656) | −0.528 (0.412) | 0.334 | **1.3**/18.7 | 0.000 | empty (0.000) | both, 0 out / 0 inside | −2.24/+0.15 | weak |
| 2024–2026 | 1,448,027 | +3.889 (8.219) | +0.819 (3.113) | 0.560 | **0.2/0.2** | 0.000 | [−∞, −0.371] ∪ [122.6, +∞] (0.489) | 0 inside / 0 inside | −0.85/−0.19 | weak |
| **firm-days with both signs** | 2,508,556 | +4.724 (3.006) | −1.416 (0.572) | 0.081 | 3.2/5.6 | 0.000 | empty (0.000) | both, 0 out / both, 0 out | −1.17/+0.35 | weak |
| **no zero-price hours** | 5,775,173 | +5.036 (1.526) | −0.981 (0.234) | 0.000 | 22.0/176.5 | 0.000 | empty (0.000) | **+ / −** | −1.23/+0.27 | **ok** |
| pooled, sign 7 days before | 5,945,332 | +3.489 (1.906) | −1.328 (0.266) | 0.012 | 8.5/144.8 | 0.000 | empty (0.010) | 0 inside / − | −0.85/+0.36 | weak |

The AR projections behind the signs:

- **pooled**: γ⁺ [−1.025, 29.402], γ⁻ [−2.545, −0.340];
- **CCGT + coal**: γ⁺ [1.195, 69.291];
- **Iberdrola**: γ⁺ [0.360, 1.955], γ⁻ [−1.380, −0.205];
- **no zero-price hours**: γ⁺ [2.680, 15.385], γ⁻ [−2.100, −0.520];
- **seven-day lag**: γ⁻ [−2.905, −0.380].

The β-scale common set is empty in every row except Endesa ([−0.093, 0.869])
and the unbounded weak rows (Naturgy, 2024–2026).

**What the table says.**

- **Price-taking is rejected in every sample but Endesa.** Endesa is a net
  buyer in all but 58 weeks, and its row is flagged weak and few-weeks.
- **No common slope fits** in any row but Endesa's (whose set contains 0) and
  the two unbounded weak rows (Naturgy, 2024–2026). That holds in the γ scale
  and in the β scale.
- **The pattern is the same in the two rows with strong instruments**
  (Iberdrola, and the pooled sample without zero-price hours): γ⁺ > 0 > γ⁻,
  each sign robust.
  - A buyer offers more capacity cheap the more it buys: the markdown, at
    β⁻ = 0.12–0.27 of Nash.
  - A seller *also* offers more capacity cheap the more it sells: β⁺ < 0, the
    opposite of a markup.
  - Read together, s50 rises with |X| on both sides of n = 0.
- **The seller first stage does not survive splitting by era** (F⁺ 1.1, 1.3,
  0.2). In 2024–2026 neither first stage exists (0.2/0.2). The pooled F⁺ of
  8.9 is far more than the three eras' 2.6 together, so most of the seller
  first stage comes from differences between eras that the hour × year-month
  effects do not absorb.
- **The zero-price filter matters.** Dropping the 3.0% of unit-hours with a
  zero price lifts the first stage from 8.9/25.0 to 22.0/176.5.

## 4. Placebo

Reduced forms, s50 on rivals' solar (pp per GW), same fixed effects and
control:

| sample | n | coefficient (se) |
|---|---|---|
| FRINGE, all | 2,064,108 | −0.101 (0.033) |
| FRINGE, hydro | 1,121,215 | −0.084 (0.035) |
| five firms, hydro | 2,747,476 | −0.096 (0.020) |
| FRINGE, thermal | 942,893 | −0.119 (0.057) |
| five firms, thermal | 3,270,127 | −0.289 (0.059) |

- **Hydro.** The five firms' reduced form equals the fringe's: a difference of
  0.012, well inside two standard errors. By the plan's rule, solar reshapes
  hydro offers through cost alone, and the five firms' hydro rows say nothing
  about conduct.
- **Thermal.** The five firms respond 2.4 times as strongly as the fringe. The
  difference of 0.169 is 2.9 of the five firms' standard errors, or 2.1 of the
  difference's own (treating the two as independent; they share weeks). So the
  thermal response is not cost alone, but only just.

The placebo bounds the z channel only. It says nothing about z · s_prev, the
instrument that separates γ⁺ from γ⁻ (§6).

## 5. Verdict

The plan's rules (Task 5, Step 1), applied mechanically:

| rule | pooled | firm-days with both signs |
|---|---|---|
| 1. 2SLS readable (both F ≥ 10)? | no: F⁺ 8.9; read AR only | no: F 3.2/5.6; read AR only |
| 2. Price-taking not rejected (AR p(0,0) ≥ 0.05)? | rejected (0.000) | rejected (0.000) |
| 3. Nash on n (common set non-empty with negatives)? | fails: set empty, smallest AR p 0.023 | fails: set empty, smallest AR p 0.000 |
| 4. Output conduct (readable, γ⁻/se > 1.96, γ⁺ < 0)? | fails: not readable; γ⁻'s robust set is negative, [−2.545, −0.340], which excludes the γ⁻ > 0 it predicts | fails: not readable; γ⁻'s robust set (−∞, −0.705] ∪ [1.290, +∞) leaves its sign open |
| verdict | inconclusive by rule 5 | inconclusive by rule 5 |

**Pooled.** Rule 5's "inconclusive", but not for lack of power: each of the
three predictions is rejected by a test that holds under weak instruments.

- Price-taking is rejected by AR at p = 0.000.
- Nash on n is rejected by the empty common set. That test is a conservative
  χ²(2) projection, so the rejection is, if anything, understated.
- Output conduct is rejected by γ⁻'s robust negative sign.

**Firm-days with both signs** (the kink sample). Price-taking and the common
slope are rejected. The instruments are too weak (F 3.2/5.6) to sign γ⁻, so
output conduct can be neither accepted nor rejected here.

**What leg D says about conduct on the net position.** The five firms' offers
respond to X, but in a way neither model predicts: a markdown when buying and
the opposite of a markup when selling. For hydro, that response is the
fringe's, so it is cost. Only thermal plant responds beyond the fringe, at two
standard errors. Leg D therefore gives no support to supply-function Nash on
n, and none to market power on output either. The result to carry is
"price-taking rejected; neither conduct model fits; hydro's response is cost".

## 6. Limits

**Identification**

- **Flat-offering units carry no information.** Iberdrola's and Naturgy's
  pumped storage, Naturgy's CCGTs from 2023 (0.27 → 0.00), Repsol's hydro
  (0.11–0.38) and Repsol's CCGTs in 2018 and 2026 sit near 0 in the variation
  table. The test runs on the units that reshape.
- **Exclusion restriction, thermal.** Rival solar moves cycling and start-up
  costs. The placebo bounds that for z, but not for z · s_prev: a firm that
  sold yesterday has units running, and solar's cost effect on a running unit
  differs. That channel would load on γ⁺ and γ⁻ with opposite signs, which is
  the pattern found. It is the leading alternative reading, untested here.
- **Era instability.** γ⁺ is identified mainly by differences between eras
  (seller F ≤ 1.3 within each). From 2024 there is no first stage at all.

**Inference**

- **s_prev is a lagged outcome.** With errors persistent across days, a one-day
  lag over-rejects AR (Task 2 review: 11/40 against 5/40). The seven-day-lag
  row gives the same picture (AR p 0.000, common set empty at min p 0.010,
  γ⁻ robust negative).
- **The empty-set test is a χ²(2) projection**, conservative for a
  one-parameter common slope.
- **Endesa is flagged few-weeks** (58 seller weeks). Its non-rejection of
  price-taking is not evidence for it.

**Data**

- **X uses one static owner per unit** (`firm_x`). EDP's X from 2018 to about
  2021 omits Castejón, which it owned then; X's sign flips in about 3.7% and
  4.9% of 2019 and 2020 periods. The panel's unit-days are dated, but X is not.
  Dating `firm_x` (separate task) requires rebuilding this panel and rerunning.
- **The Repsol–Viesgo date** (2018-11-02) is from the public record, not yet
  verified against a filing.
- **Combined cycle from 2025-04 is thinned** by the over-capacity drop (1,904
  unit-days). Repsol's ALG3 and ECT3 lose 93.8% of their unit-days from 2025-03;
  the 55 kept days are a selected remainder.
- **The FRINGE placebo includes pass-through and legacy-contract units**
  (ICUVD05 Curenergía, E21VD03, GNSUVD3, REN Trading RPG01/02, RTG01–03),
  whose offers are not cost-driven in the usual sense.
- **On the ~34 days of 23 or 25 hours**, `hour` is not the clock hour after
  02:00. This affects only the hour × year-month effects.
- **s_prev is built from all periods**, including the ~63 days on which the
  clearing identity fails (fine by definition; optionally NaN after them).
- **Financial hedges are unobserved** (spec §6), so X overstates the exposed
  position of a firm hedged financially.
