# Leg D — the sign of n

Framework spec §4, leg D. Run 2026-10-01 on branch `leg-d`.
Scripts: `build/build_rival_solar.py`, `analysis/iv_two_endog.py`,
`analysis/leg_d_panel.py`, `analysis/leg_d_sign_test.py`; checks in `qa/`
(`check_rival_solar.py`, `check_iv_two_endog.py`, `check_leg_d_panel.py`).
Results: `outputs/tables/leg_d_results.csv`.

*Supersedes the first version of this note (commit `4289880`), whose verdict,
"neither conduct model fits", was withdrawn on 2026-10-01: its rejection of
Nash rested on rivals' solar moving offers only through X, which the placebo
(§4) contradicts.*

**Rerun 2026-10-02 with REE's day-ahead forecasts as the instruments (§7).**
Net of the fringe's response to the same forecasts, one common slope fits both
forecasts and has the market-power sign, but it is small: β = 0.03 (AR set
0.01–0.06; F 60). Letting the first stage differ by firm separates the two
slopes (F 40/35): no markup when selling (β⁺ 0.00), a markdown when buying
(β⁻ 0.19), unequal at p < 0.001. Sections 1–6 describe the first run.

**In one line.** With these instruments leg D rejects price-taking in every
pooled specification and cannot tell the conduct models apart. A Nash-signed
common slope fits only where yesterday's sign of n, the interaction
instrument's own main effect, is left uncontrolled. With it controlled, the
common slope is undetermined, absent or of the wrong sign, on weak first
stages.

## 1. Design, as run

For each dispatchable unit-hour of the five firms (EDP, Endesa, Iberdrola,
Naturgy, Repsol):

```
y_uh = α_ud + α_hym + γ⁺ · X⁺_fh + γ⁻ · X⁻_fh + c · fcst_h + ε_uh
```

- **y** is the §3.14 measure: the share of the unit's capacity offered at or
  below the unit-*day*'s volume-weighted median offer price, in percentage
  points (s50; s25 and s75 as robustness). Capacity is `cab` max power that day.
- **X⁺, X⁻** are the hourly means of max(X, 0) and min(X, 0). X = n/|RD′| is the
  firm's exposed net position over rivals' residual-demand slope, in €/MWh
  (`firm_x.parquet`). γ is in pp of capacity per €/MWh of X; γ < 0 is the
  market-power sign.
- **α_ud** is a unit × day effect (it removes the water value or the day's fuel
  price). **α_hym** is an hour × year-month effect (it removes the solar
  profile's growth). **fcst** is REE's day-ahead demand forecast, in GW.
- **Instruments**: z, rivals' offered solar for the firm, in GW; and z · s_prev,
  where s_prev = 1 if the firm was a net seller in the same hour the day before.
  The model is just identified (two instruments, two regressors).
- **As planned, s_prev itself is not a control.** An interaction instrument
  normally comes with its main effect, so the lagged sign also acts as an
  instrument here. §3.2 adds it.
- **Errors** are clustered by ISO week (439 weeks).

**Inference that survives weak instruments.** 2SLS (two-stage least squares)
is read only when both Sanderson–Windmeijer conditional first-stage F statistics
are at least 10 (status `ok`); otherwise the row is `weak`. The following are
valid however weak the instruments, but not if an instrument has a direct
effect on offers:

- the Anderson–Rubin (AR) test of γ⁺ = γ⁻ = 0, which is price-taking;
- the exact AR set of common slopes c with γ⁺ = γ⁻ = c, the roots of a
  quartic; empty means no common slope fits;
- each coefficient's AR projection, whose sign is the robust sign test. It
  separates Nash (γ⁻ < 0) from output-based conduct (γ⁻ > 0). The projection
  searches a grid: uniform on ±5 (step 0.005), log-spaced to ±10⁴, and dense
  around the 2SLS estimate.

**β scale.** Nash is symmetric in β, and γ = −β × the curve's offer density at
the reference price. So β = −γ / mean density, with β⁺ and β⁻ dividing by the
mean density in seller and buyer hours separately (§3.14 scale: β = 1 is full
Nash). Their equality and their common-value AR set are reported beside the γ
ones.

**Rules added in implementation** (each recorded in the plan's ledger):

1. **Hours.** Periods are averaged to hours, so a day weighs the same before
   and after the 15-minute switch of 2025-10-01 (15-minute periods are 25.6%
   of all periods in the window).
2. **Absent offers score 0.** In a unit-day the unit is present in, a period
   with no offer scores 0, not missing. Dropping those periods selected on the
   instrument's hours: Endesa's pumped storage offers at midday on 28% of
   unit-days against 90% in the evening.
3. **Over-capacity drop.** A unit-day is dropped if its offered volume exceeds
   1.02 × capacity, for which the capacity share is undefined. These start on
   2025-03-19, the date of OMIE's new offer typology (the scalable complex
   order), and are combined-cycle alternative complex orders.
4. **Dated ownership.** A unit-day is kept only when the OMIE listing in force
   that day (the nearest preceding snapshot; a co-owned unit follows its
   majority owner) puts the unit in the firm X is built for. Repsol is dropped
   before 2018-11-02, the date of its Viesgo purchase.
5. **Fringe placebo.** Units of 50 MW or more owned outside the five
   (`FRINGE`) are read as having little stake in the price; their X is not
   computed. Their reduced form estimates how solar reshapes offers through cost
   alone. It is read against the five firms by technology.
6. **Flags.** `WEAK` marks a conditional F below 10. `FEW-WEEKS` marks
   s_prev = 1 or 0 in fewer than 100 weeks, where AR over-rejects (28% at 3
   weeks, 6% at 100, in the Task 2 review's simulation).
7. **A seven-day lag.** s_prev is a lagged outcome, so robustness rows use the
   sign seven days before (zs7).
8. **After review**, rows test whether the design's conclusions survive:
   - s_prev controlled, with and without s_prev × the hour's mean solar;
   - offers net of the fringe's solar response;
   - one common slope with a solar slope per firm;
   - without Endesa;
   - a demand-forecast slope per era.

## 2. Sample

Panel `outputs/tables/leg_d_panel.parquet`: **8,083,768 unit-hours**,
2018-01-02 → 2026-05-31. The estimation sample is the five firms' 5,954,775
unit-hours on 134 units. It excludes the 64,324 unit-hours with no s_prev: the
17 days of 23 or 25 hours, and the 17 days after them.

Unit-hours in the panel, before that drop:

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

### 3.1 As designed

γ is in pp of capacity per €/MWh of X. The robust sign comes from the AR
projection; "both signs, 0 out" means a set of two pieces, one on each side of
0, which excludes 0 and leaves the sign open. β is on the §3.14 scale.

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
| no zero-price hours | 5,775,173 | +5.036 (1.526) | −0.981 (0.234) | 0.000 | 22.0/176.5 | 0.000 | empty (0.000) | + / − | −1.23/+0.27 | ok |
| pooled, sign 7 days before | 5,945,332 | +3.489 (1.906) | −1.328 (0.266) | 0.012 | 8.5/144.8 | 0.000 | empty (0.010) | 0 inside / − | −0.85/+0.36 | weak |

The AR projections behind the signs:

- **pooled**: γ⁺ [−1.025, 29.402], γ⁻ [−2.545, −0.340];
- **CCGT + coal**: γ⁺ [1.195, 69.291];
- **Iberdrola**: γ⁺ [0.360, 1.955], γ⁻ [−1.380, −0.205];
- **no zero-price hours**: γ⁺ [2.680, 15.385], γ⁻ [−2.100, −0.520];
- **seven-day lag**: γ⁻ [−2.905, −0.380].

The printed endpoints are the last grid point inside the set, so the sets are
slightly wider than shown.

**What the table says.**

- **Price-taking is rejected in every row but Endesa's.** Endesa was a net
  seller in at least one hour of only 58 of 439 weeks (s_prev = 1 in 1.1% of
  its unit-hours), and its row is flagged weak and few-weeks.
- **No common slope fits in any row but Endesa's** (whose set contains 0) and
  the two unbounded weak rows (Naturgy, 2024–2026). That holds in the γ scale
  and in the β scale.
- **γ⁻'s negative sign is robust in the pooled s25, s50 and seven-day rows,
  in Iberdrola's and in the no-zero-price row.** It is not robust at s75, in
  hydro, in thermal, or in any other firm's or era's row.
- **Iberdrola, the one row with strong instruments in its own sample, gives
  γ⁺ > 0 > γ⁻, each sign robust.**
  - γ⁻ has the sign of a markdown (β⁻ 0.12).
  - γ⁺ has the sign opposite to a markup (β⁺ −0.17).
- **The no-zero-price row shows the same pattern, but it is a robustness row,
  not a second sample.** It drops hours on the price, an outcome of the offers,
  and those are the sunniest hours: mean rival solar 12.1 GW against 3.0 in the
  rest, and 11% of 2024's and 25% of 2026's unit-hours. Its β⁺ of −1.23
  exceeds full Nash in size with the wrong sign, which argues against reading
  these slopes as conduct.
- **Within each era the two first stages are nearly collinear** (conditional
  F⁺ 1.1, 1.3, 0.2), and in different directions.
  - γ⁺ is separated from γ⁻ only by pooling eras whose first stages differ,
    which assumes both slopes are the same in every era.
  - The pooled F⁺ (8.9) is weak and fragile: letting the forecast slope vary by
    era lowers it to 5.9 (§3.2).

### 3.2 What survives

The empty common set is an over-identification failure between z and z · s_prev
for one slope. So it rejects Nash only if neither instrument moves offers
except through X. Two exclusions are in doubt:

- **z.** The placebo says solar moves offers directly (§4).
- **z · s_prev.** Within the fixed effects, z · s_prev varies mostly as s_prev
  times the hour's mean solar, so the lagged sign itself instruments.

Pooled rows, s50:

| specification | SW F⁺/F⁻ | AR p(0,0) | AR common γ (min p) | AR common β | robust sign γ⁺ / γ⁻ |
|---|---|---|---|---|---|
| as designed | 8.9/25.0 | 4·10⁻⁷⁰ | empty (0.023) | empty | 0 inside / − |
| s_prev controlled | 4.0/2.8 | 3·10⁻⁷⁵ | [−∞, −1008] ∪ [4.535, +∞] (0.224) | [−7.40, −1.02] | 0 inside / 0 inside |
| s_prev and s_prev × mean solar controlled | 8.8/1.3 | 5·10⁻¹⁵ | [0.647, 4.181] (0.864) | [−0.98, −0.16] | 0 inside / 0 inside |
| 7 days, s_prev7 controlled | 10.7/5.7 | 2·10⁻⁴⁹ | empty (0.047) | empty | 0 inside / 0 inside |
| 7 days, s_prev7 and s_prev7 × mean solar controlled | 9.2/2.3 | 6·10⁻⁷ | [0.298, 1.366] (1.000) | [−0.34, −0.08] | 0 inside / 0 inside |
| net of the fringe's solar response | 8.9/25.0 | 3·10⁻⁶³ | [−2.152, −1.594] (0.083) | [0.45, 0.58] | 0 inside / − |
| net of the fringe's solar response, s_prev and s_prev × mean solar controlled | 8.8/1.3 | 1·10⁻⁶ | [0.487, 3.363] (0.493) | [−0.78, −0.12] | 0 inside / 0 inside |
| without Endesa | 6.0/44.7 | 1·10⁻⁸⁵ | empty (0.000) | empty | both, 0 out / both, 0 out |
| forecast slope by era | 5.9/16.7 | 4·10⁻⁷² | empty (0.010) | empty | both, 0 out / 0 inside |

"Mean solar" is the hour × year-month mean of z. "Net of the fringe's solar
response" subtracts the like-for-like fringe reduced form (§4) times z from y.

**One common slope**, c on X = X⁺ + X⁻, instrumented by z · s_prev alone, with z
as a control. This imposes Nash's equality and asks what the slope is:

| controls | c (se) | F | AR p(c = 0) | AR set | β |
|---|---|---|---|---|---|
| z, one slope for all firms | −1.793 (0.262) | 60.2 | 9·10⁻⁶⁴ | [−2.466, −1.373] | 0.48 |
| z, one slope per firm | −1.831 (0.725) | 9.99, weak | 2·10⁻¹⁰ | [−5.405, −0.912] | 0.49 |
| z and s_prev | +12.564 (10.212) | 1.5, weak | 2·10⁻⁷⁰ | (−∞, −21.799] ∪ [4.777, +∞) | −3.35 |
| z, s_prev and s_prev × mean solar | +1.695 (0.980) | 4.0, weak | 4·10⁻⁵ | [0.625, 73.441] | −0.45 |

**The Nash sign does not survive controlling s_prev.** The first two rows
leave it out, so the lagged sign instruments too. With s_prev controlled the
first stage all but vanishes (F 1.5) and the AR set is two unbounded pieces,
one on each side of 0. Adding s_prev × mean solar leaves a set of the wrong
sign, [0.625, 73.4], on a weak first stage (F 4.0). Price-taking stays
rejected in both.

The slope keeps its value when each firm gets its own solar slope, but the
first stage falls from F 60 to F 9.99, just below the weak threshold. Most of z · s_prev's variation is
differences between firms in how solar reshapes their offers. Those differences
correlate with how often a firm sells (Repsol was a net seller in about three
quarters of its hours, Endesa in 1%).

**Sensitivity to the second exclusion.** Suppose z · s_prev has a direct effect
δ (pp per GW), for example because a firm's units, running after a selling day,
respond to solar differently for cost reasons. Then δ moves the pooled 2SLS by
Δγ⁺ = −2.99 δ and Δγ⁻ = +1.88 δ (Iberdrola −4.27 δ and +2.59 δ).

- A negative δ pushes γ⁺ up and γ⁻ down: the opposite-sign pattern of §3.1.
- A δ as large as z · s_prev's whole reduced form (−0.78 pp per GW, measured in
  the Task 4 review) would leave γ⁻ near 0 and γ⁺ near +1.

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

- **Hydro.** The five firms' reduced form cannot be told apart from the
  fringe's (difference 0.012, se ≈ 0.040). The placebo covers z only: hydro's
  γ's and its AR rejection come from z · s_prev, which the fringe cannot speak
  to. 12% of the fringe's hydro hours are pass-through units classed as hydro
  (ICUVD05, E21VD03, GNSUVD3). The hydro rows carry no evidence of conduct.
- **Thermal.** The five firms respond 2.4 times as strongly as the fringe. The
  difference of 0.169 is 2.9 of the five firms' standard errors, or 2.1 of the
  difference's own (treating the two as independent; they share weeks). That
  is either conduct or a cost response that differs between the fleets:
  - coal is 20.9% of the five firms' thermal hours against 9.4% of the
    fringe's;
  - REN Trading's legacy-contract units are 23.6% of the fringe's thermal hours
    and 74% of its coal.

  The placebo does not separate the two.

## 5. Verdict

The plan's rules (Task 5, Step 1), applied mechanically to the design as
planned:

| rule | pooled | firm-days with both signs |
|---|---|---|
| 1. 2SLS readable (both F ≥ 10)? | no: F⁺ 8.9; read AR only | no: F 3.2/5.6; read AR only |
| 2. Price-taking not rejected (AR p(0,0) ≥ 0.05)? | rejected (0.000) | rejected (0.000) |
| 3. Nash on n (common set non-empty with negatives)? | fails: set empty, smallest AR p 0.023 | fails: set empty, smallest AR p 0.000 |
| 4. Output conduct (readable, γ⁻/se > 1.96, γ⁺ < 0)? | fails: not readable; γ⁻'s robust set [−2.545, −0.340] excludes the γ⁻ > 0 it predicts | fails: not readable; γ⁻'s robust set (−∞, −0.705] ∪ [1.290, +∞) leaves its sign open |
| verdict | inconclusive by rule 5 | inconclusive by rule 5 |

**Pooled: inconclusive, and the rules' failures do not survive §3.2.**

- **Price-taking is rejected** in every specification of §3.2 (AR p ≤ 1.1·10⁻⁶;
  one slope, p ≤ 4·10⁻⁵).
- **Nash's equal slopes are rejected only as designed, and a Nash-signed fit
  appears only where s_prev is uncontrolled.**
  - Uncontrolled: net of the fringe's solar response a common Nash-signed slope
    fits (β 0.45–0.58), and so does one slope instrumented by z · s_prev alone
    (β 0.48, F 60).
  - With s_prev and s_prev × mean solar controlled, a common slope fits with
    the wrong sign (β −0.98 to −0.16), as two slopes and as one (AR set
    [0.625, 73.4]). Netting the fringe's response as well leaves it there
    (β −0.78 to −0.12).
  - With s_prev alone controlled, nothing is determined, as two slopes or one.
  - Every controlled row has at least one weak first stage (its smaller F is
    1.3–5.7).
  - **The netted rows use a generated outcome.** y minus the fringe's reduced
    form times z treats that coefficient as known; its standard error (0.057
    for thermal, 0.035 for hydro) is not carried into their inference, so their
    sets are too narrow.
- **γ⁻'s robust negative sign excludes output conduct as designed.** It does
  not survive controlling s_prev, or dropping Endesa.
- **The common-set test is a χ²(2) projection**, conservative for a
  one-parameter slope. But AR over-rejects with a one-day lagged outcome, so
  the two errors run in opposite directions.

**Firm-days with both signs** (the kink sample). Price-taking and the common
slope are rejected. The instruments are too weak (F 3.2/5.6) to sign γ⁻, so
output conduct can be neither accepted nor rejected.

**What leg D says about conduct on the net position.** With rivals' solar and
yesterday's sign as instruments, leg D rejects price-taking and nothing more.

- **Even that rejection rests on z · s_prev moving offers only through X**,
  which fails if units running after a selling day respond to solar
  differently for cost reasons (§3.2).
- **For hydro**, the response to solar alone is the fringe's.
- **Separating Nash from output conduct needs a different instrument**: one
  for the sign of n that is not a lagged outcome, or a cost measure that rules
  out the operating-state channel (leg C's thermal costs).

## 6. Limits

**Identification**

- **The sign instrument is a lagged outcome.** z · s_prev carries s_prev's
  own variation unless s_prev is controlled, and with s_prev controlled the
  first stages are weak (F 4.0/2.8; one slope, F 1.5). Every Nash-signed fit
  in this note leaves s_prev uncontrolled.
- **Solar's direct effect.** The fringe responds to solar. Netting its
  response changes the common-slope verdict, so the verdict depends on how
  comparable the fringe is (§4).
- **Between-firm variation.** Most of z · s_prev's first stage is differences
  between firms (§3.2), while the spec meant the identifying variation to be
  within a firm.
- **Endesa carries the pooled γ⁻ sign.** Without Endesa both projections
  split into two pieces and the sign is open.
- **Era instability.** γ⁺ is identified by pooling eras whose first stages
  point in different directions (seller F ≤ 1.3 within each). From 2024 there
  is no first stage at all.
- **Flat-offering units carry no information.** These sit near 0 in the
  variation table:
  - Iberdrola's pumped storage to 2022 (0.00–0.03);
  - Naturgy's pumped storage throughout;
  - Naturgy's CCGTs from 2024 (0.00–0.04);
  - Repsol's CCGTs in 2018 and 2026.

  Repsol's hydro is low (0.11–0.38). The test runs on the units that reshape.

**Inference**

- **AR over-rejects with a one-day lagged outcome** (Task 2 review: 11/40
  against 5/40). The seven-day rows give the same as-designed picture.
- **Endesa is flagged few-weeks.** Its non-rejection of price-taking is not
  evidence for it.

**Data**

- **X uses one static owner per unit** (`firm_x`). EDP's X from 2018 to about
  2021 omits Castejón, which it owned then; X's sign flips in about 3.7% and
  4.9% of 2019 and 2020 periods. The panel's unit-days are dated, but X is not.
  Dating `firm_x` (separate task) requires rebuilding this panel and rerunning.
- **The Repsol–Viesgo date** (2018-11-02) is confirmed by Repsol's own press
  release of that day announcing the completed purchase (700 MW of hydro and
  pumped storage, the Algeciras and Escatrón CCGTs, 750,000 retail customers).
- **Combined cycle from 2025-03-19 is thinned** by the over-capacity drop
  (1,904 unit-days). Repsol's ALG3 and ECT3 lose 93.8% of their unit-days from
  2025-03; the 55 kept days are a selected remainder.
- **The FRINGE placebo includes pass-through and legacy-contract units**
  (ICUVD05 Curenergía, E21VD03, GNSUVD3, REN Trading RPG01/02, RTG01–03). They
  are 12% of its hydro hours and 24% of its thermal hours.
- **On the 17 days of 23 or 25 hours**, `hour` is not the clock hour after
  02:00. Those days and the days after them have no s_prev, so they are outside
  every IV row; the mislabelled hour affects only the placebo reduced forms.
- **s_prev is built from all periods**, including the ~63 days on which the
  clearing identity fails.
- **Financial hedges are unobserved** (spec §6), so X overstates the exposed
  position of a firm hedged financially.

## 7. Rerun with REE's day-ahead forecasts (2026-10-02)

Script `analysis/leg_d_forecast_test.py`; results
`outputs/tables/leg_d_forecast_results.csv`; the forecasts' first stage on the
firms' n and X in [`rq-forecast-first-stage.md`](rq-forecast-first-stage.md).

### 7.1 What changes

Same panel, outcome, fixed effects (unit × day, hour × year-month), clustering
and weak-instrument-robust inference as §1. Two changes:

- **Instruments:** W and S, REE's wind and solar forecasts for D+1, published
  before 11:00 on D-1 (ESIOS 1777, 1779), in GW. They replace z (rivals' offered
  solar, partly a choice) and z · s_prev (which made yesterday's sign, a lagged
  outcome, an instrument). Offers close at 12:00, so an offer can respond to
  the forecast only by a decision of the firm.
- **Control:** D, REE's demand forecast of the same vintage (ESIOS 1775). It
  replaces `fcst`, whose publication time is not stated.

**Sample:** 2019-01-01 → 2026-05-31 (the forecasts start in 2019), on the
24-hour days of §2: 5,171,005 unit-hours of the five firms; the fringe's
1,781,113 on the same days.

**Mechanics.** The forecasts move X mostly mechanically: a windy forecast lowers
the price, so the firm's existing offers clear less and n falls with no
decision. That is what a residual-demand shifter should do. It is harmless here
because the outcome is the unit's offer shape, measured against the unit-day's
own median offer price, not against the market price. With the price as the
outcome (leg C in levels) the same forecasts would move p and X together by
construction, and must not be used that way.

### 7.2 The placebo decides which rows to read

Reduced forms, s50 on the forecasts, pp of capacity per GW:

| units | on W (t) | on S (t) |
|---|---|---|
| FRINGE, thermal | −0.221 (−6.5) | −0.253 (−4.9) |
| five firms, thermal | −0.316 (−9.8) | −0.216 (−4.1) |
| FRINGE, hydro | −0.172 (−9.0) | −0.161 (−5.0) |
| five firms, hydro | +0.038 (+3.0) | −0.028 (−1.5) |

**Thermal plants with no stake in the price respond to a windy or sunny
forecast as the five firms' do.** The forecasts reshape thermal offers through
cost (start-ups, cycling), so on raw offers they fail the exclusion. The rows
to read subtract the fringe's response, technology by technology, from y. For
hydro this assumes the fringe's response (−0.17) is what a price-taking
reservoir would do; the five firms' hydro does not respond at all, and the
difference is what the netted rows attribute to X.

### 7.3 Results

β is on the §3.14 scale (β = 1 is full Nash). "Sign of X" says which hours a β
covers: a one-slope row imposes the same β on sellers (X > 0) and buyers (X < 0).
Hours with X > 0 are 24% of the pooled sample: Endesa 0.3%, EDP 20%, Naturgy 20%,
Iberdrola 37%, Repsol 74%.

| specification | sign of X | first-stage F | slopes | AR test of price-taking | β |
|---|---|---|---|---|---|
| raw offers, one common slope | both, one β | 60 | c +0.255 (0.034); AR set [0.217, 0.300] | p 7·10⁻¹⁷ | −0.07 (wrong sign) |
| **net of the fringe, one common slope** | both, one β | **60** | **c −0.119 (0.035); AR set [−0.217, −0.041], overid p 0.998** | **p 6·10⁻⁴** | **0.03 [0.01, 0.06]** |
| net of the fringe, two slopes, pooled first stage | each | 0.7/0.7 | not separated | p 6·10⁻⁴ | — |
| **net of the fringe, two slopes, forecasts × firm** | **X > 0 (seller)** | **40** | **γ⁺ −0.001 (0.106)** | p ≈ 0 (joint) | **β⁺ 0.00** |
| | **X < 0 (buyer)** | **35** | **γ⁻ −0.682 (0.087); p(γ⁺ = γ⁻) < 0.001** | | **β⁻ 0.19** |
| Iberdrola, net, one slope | both, one β | 100 | c −0.150 (0.028); AR set [−0.202, −0.126] | p 10⁻⁹ | 0.03 [0.03, 0.05] |
| Iberdrola, raw, two slopes | each | 17/12 | γ⁺ −0.001 (0.097), γ⁻ −0.032 (0.092) | **p 0.78** | common [−0.01, 0.02] |
| EDP, net, one slope | both, one β | 87 | c +0.057 (0.026); AR set **empty** | p 2·10⁻⁸ | — |
| Endesa / Naturgy / Repsol, net, one slope | both, one β | 0.9 / 5.4 / 2.1 | weak | | |

The common 0.03 is not an average of β⁺ 0.00 and β⁻ 0.19: the rows use different
first stages (one pooled response to the forecasts against one per firm), so
they draw on different variation.

### 7.4 Reading

1. **The market-power sign appears, and β is small.** Net of the fringe's cost
   response, a single slope fits both forecasts (overidentification p 0.998)
   with β = 0.03, between 0.01 and 0.06. Leg A's within-day hydro estimate was
   0.03–0.14. Two legs, two designs, the same order of magnitude: firms behave
   close to price-takers, with a small, detectable departure.
2. **On raw offers the slope has the wrong sign** (β −0.07): the forecasts' cost
   effect on thermal offers dominates it. The placebo is what turns the sign;
   the reading depends on the fringe being a valid price-taking benchmark.
3. **The asymmetry.** With the first stage free to differ by firm, sellers'
   slope is zero and buyers' is clearly negative: firms shade their offers to
   lower the price when they are net buyers (β⁻ 0.19) and do not raise it when
   net sellers. Nash on n predicts equal slopes; output-based conduct predicts
   γ⁺ < 0 < γ⁻. This is neither: market power on the buying side only.
   Two cautions. The two slopes are separated largely by differences between
   firms (Endesa is a buyer in almost every hour, Repsol a seller in two thirds), as
   in §3.2. And with ten instruments there is no AR projection; the 2SLS is
   readable (F 40/35) only if every firm's forecasts are excluded.
4. **By firm, only Iberdrola and EDP are strongly identified.** Iberdrola gives
   0.03 net of the fringe and an interval around 0 on raw offers, where
   price-taking is not rejected (p 0.78); the difference is the hydro netting.
   For EDP no single slope fits both forecasts.
5. **The pooled two-slope design is weak** (F 0.7): within a unit-day, the
   forecasts' hourly variation moves X⁺ and X⁻ alike. Leg D's two slopes need
   the firm-specific first stage.

### 7.5 Limits

- **The netting is an assumption**: the fringe's response to the forecasts is
  taken as a price-taker's. For thermal the two fleets respond alike; for hydro
  they do not, and the netted rows read the difference as conduct.
- **The asymmetry rests on differences between firms** and on ten exclusion
  restrictions at once.
- **2019 on, Spain's forecasts only** (Portugal's needs ENTSO-E).
- The limits of §6 carry over.
