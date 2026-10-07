# Leg B in levels: hydro offers against the price-taking water value

Run 2026-10-07. Script `analysis/leg_b_levels.py`; results
`outputs/tables/leg_b_levels_results.csv` and `leg_b_paper_method.csv`. Inputs: the
hydro step rows of `step_estimator_hydro.py` (`rq-step-estimator.md` §6) and λ*30s from
`build_water_value_forward.py` (`rq-water-value-forward.md` §5.2). Framework spec §2.2,
leg B.

**In one line.** Measured from the price-taking water value, hydro step prices do not
rise with the firm's stake in a higher price across days either: with reactor outages as
the instrument (F 21.5, against 5.6 within the day) β is −0.26, 95% set [−0.72, 0.04].
Full market power (β = 1) is rejected in every specification that compares firms on the
same hour and has a usable first stage; price-taking is not. **With the at-cost
instrument (§5, F 90–410) the bound tightens to β ≤ 0.12 outside 2019 – 2021H1, and
2024–2025 is identified for the first time: −0.16 [−0.25, −0.06].** The negative values are not
caused by the firm's own zero-priced output or its water (§6.1), and the paper's wrong
storage sign comes from comparing years, not from incomplete storage data (§6.2).

## 1. The idea, with an example

Iberdrola's Duero unit offers a step at €110 on a day when the price-taking water value
λ* is €100: a gap of €10. If, at the price that step sets, Iberdrola gains from a higher
price by X̃ = €20 (its net position over the slope of its residual demand), full market
power predicts a gap of €20 and price-taking predicts zero on average. Leg A asked this
within a day, with each unit's day level removed. Here the day's level stays in:

    b_k − λ*_ud = β · X̃_k + e,     e = (λ_ud − λ*_ud) + error

A firm holding water back raises the level of its offers for whole days, which unit ×
day effects absorb. With λ* as the cost, unit × month effects suffice, so the variation
across days within a month enters.

## 2. Instruments

The firm × forecast instruments again fail the overidentification test in every sample
(empty Anderson–Rubin sets), as in §6 of the step note, and are not read. Two remain:

- **Reactor outages by ownership share** (unplanned and planned dose). Multi-week, so they
  barely move within a day (F 5.6 with unit × day effects) but move the day level:
  **F 21.5 with unit × month effects**. This is the first stage leg B lacked since its
  first pass was withdrawn (spec §4, §9.3).
- **Regional wind deviation** (third location pass). F 16.8 within the day, 8.8 across
  days.

## 3. Results

661,575 hydro steps set the price in at least one resampled draw, 46 units, 2019 →
2025-09; 77% on units with a storage series; flat unit-days kept (their choice is the
day's level).

| fixed effects | instruments | β | F | 95% set (Anderson–Rubin) | p(β = 1) |
|---|---|---|---|---|---|
| unit × day (leg A; λ* cancels) | outages | −0.07 | 5.6 | [−0.78, 0.24] | 0.001 |
| unit × day | regional wind | −0.31 | 16.8 | [−0.78, 0.04] | <0.001 |
| **unit × month** | **outages** | **−0.26** | **21.5** | **[−0.72, 0.04]** | <10⁻¹⁴ |
| unit × month | regional wind | −1.16 | 8.8 | [−3.78, −0.37] | <0.001 |
| unit × month | outages + wind | −0.35 | 17.3 | [−0.83, −0.15] | <10⁻¹⁵ |
| unit | outages | −0.30 | 15.3 | [−0.80, 0.31] | <0.001 |
| unit | outages + wind | −0.35 | 10.3 | [−0.40, 0.20] | <0.001 |
| unit, clock-hour effects only | outages | +0.30 | 15.1 | [−1.99, 2.36] | 0.52 |

Least squares is +0.29 to +0.33 throughout (biased upward, step note §3). Every row but
the last has class × hour-of-sample effects, so firms are compared on the same hour; the
last relies on λ* alone for the common cost and is too noisy to read.

**Checks, unit × month, outages** (outages + wind in brackets):

| sample | β | 95% set |
|---|---|---|
| λ*90 instead of λ*30 | +0.07 (−0.06) | [−0.46, 0.43] (empty) |
| λ* without storage | −0.27 (−0.35) | [−0.75, 0.03] ([−0.86, −0.14]) |
| units with a storage series | −0.07 (−0.09) | [−0.97, 0.34], F 10 (empty, F 7) |
| flat unit-days left out | −0.18 (−0.28) | [−0.91, 0.21] ([−0.98, −0.39]) |
| storage hydro only, no pumped | −0.13 (−0.23) | [−0.82, 0.23] ([−0.93, −0.08]) |
| six owners only | −0.24 (−0.33) | [−0.71, 0.05] ([−0.82, −0.16]) |
| 2019–2023 | −0.17 (−0.25) | [−0.56, 0.12] ([−0.67, −0.04]) |
| 2024 – 2025-09 | −1.00 (−1.15) | weak, F 3 (F 2) |
| two slopes, β⁺ and β⁻ | | weak, F < 1 |

- **Full market power is rejected across days** in every specification with hour
  effects and F above 10, as it is within the day (leg A) and for thermal plant. The
  upper end of every such set is at most 0.43.
- **Price-taking is not rejected with outages alone** in any sample with F above 10.
- **With outages and wind together the sets lie below zero** (−0.9 to −0.1), but that
  set is empty with λ*90 and with the storage units alone, so the negative sign rests on
  the instrument combination and the benchmark horizon. Not read as a finding. The point
  estimates are negative in the same way as thermal plant after own reactor outages
  (`rq-reactor-outages.md` §6): a firm that loses its own nuclear output prices its other
  plant higher relative to cost, which the static condition does not predict.
- **Storage in the benchmark changes nothing** (−0.26 with, −0.27 without).
- **The solar years are not identified**: 2024–2025 has F 2–3.

## 4. The paper's method on the same data

Arzhintar, Leslie, Neill & Wyrwoll (2025, SSRN 5736763) recover the water value of the
Snowy scheme from its offers: in intervals where its own plant sets the price, they
assume full market power, λ̂ = p − n/|RD′| with contracts estimated, and fit λ̂ by
least squares on futures, reservoir volume and snow. They find a futures coefficient of
1.26 (Murray), negative on volume and snow.

**The two approaches go in opposite directions.** They assume conduct (β = 1) and recover
λ; this leg builds λ* without the offers and tests conduct. Their method cannot test
β, and if β is below 1, as every test here finds, their λ̂ is biased down by
(1 − β) · X.

**Applied here** (steps that set the realised price, 19,059 unit-hours, 28 storage units):

| group | hours | X at the price, median | λ* | λ̂ at β = 0 (the price) | λ̂ at β = 1 (the paper) |
|---|---|---|---|---|---|
| all | 19,059 | −0.49 | 93.3 | 76.2 | 77.6 |
| EDP | 10,644 | −0.93 | 72.6 | 65.9 | 67.4 |
| Iberdrola | 4,203 | +0.29 | 106.5 | 99.5 | 94.5 |
| Endesa | 958 | −5.71 | 60.7 | 59.0 | 66.6 |
| Naturgy | 919 | −2.07 | 52.5 | 50.5 | 52.6 |
| Movhera | 1,557 | +1.89 | 120.2 | 105.0 | 104.4 |

- **In the hours a storage unit sets the price, its firm's X is under €1–6/MWh.** So
  assuming β = 1 or 0 changes λ̂ by a euro or two: the method recovers the price, and
  in Iberia it could not tell conduct apart even if it tried.
- **λ̂ tracks the forward one for one**, as in the paper: coefficient 1.10 (β = 1)
  and 1.07 (β = 0) on the D−2 forward with unit effects, against 1.26 for Murray. It
  correlates 0.92 with λ*.
- **The storage coefficient has the wrong sign**: fuller reservoirs go with higher λ̂
  (+0.9 €/MWh per 10 points of fill, se 0.45; Iberdrola +2.9, Naturgy +3.0, EDP +0.1), where
  the paper finds lower (λ*s: −2.6 per 10 points, by construction). This is the
  2026-08-18 finding again
  (`hydro-water-value-design.md`): a firm that values its water highly offers high and
  stays full for that reason, so volume in an ex post regression is a consequence of
  the water value as well as its cause.
- **Selection**: λ̂ sits 3–18% below λ* in these hours (EDP 9%, Iberdrola 7%), because a
  storage unit sets the price when its step is cheap relative to its usual level.
- **On the same days it agrees with the water value EDP's offers reveal**
  (`water_value_revealed`, 12,817 unit-hours): λ̂ over λ̂50 has median 0.95, correlation
  0.79 (Cávado 69 against 71, Guadiana 89 against 92, Tejo-Mondego 83 against 83). On
  those days λ̂50 over λ* is 1.01, against 1.05 on all days. They are low-water-value
  days (Cávado's λ̂50 is 71 there, 102 over all days), and λ* is lower on them too.
- **Movhera and Hidrocantábrico are the exception**: the paper's λ̂ is 104 and 65, the
  revealed λ̂50 225 and 119. λ̂50 is the price at half of the offered volume, which for
  these units lands on capacity with no water behind it (`rq-water-value-forward.md`
  §5.3). The step that sets the price is the marginal water, and it sits near λ*.

## 5. The at-cost instrument on hydro (2026-10-07)

`step_engine.py --kind hydro --comp` re-clears the same 40 resampled draws with each
firm's hydro steps above €1 moved to its units' λ*30s (hcompcost_YYYYMM, 81 months,
~100,000 unit-hours each), and reads X over the 5 draws whose price is nearest the cost
point, as for thermal plant (`rq-step-estimator.md` §7). **Zb** takes the cost point at
the day's median λ* of the hydro class, so no unit's own benchmark error enters it; **Zc**
at the unit's own λ*. `leg_b_levels.py --atcost`; `leg_b_atcost_results.csv`. Defined on
98% of price-setting rows; correlation with X̃ 0.44.

| fixed effects | instrument | β | F | 95% set (Anderson–Rubin) |
|---|---|---|---|---|
| unit × day (within the day) | Zb | −0.37 | 322 | [−0.52, −0.25] |
| unit × day | Zb + outages | −0.37 | 115 | [−0.50, −0.20] |
| **unit × month (across days)** | **Zb** | **−0.22** | **407** | **[−0.30, −0.15]** |
| unit × month | Zc | −0.20 | 260 | [−0.30, −0.11] |
| unit × month | Zb + outages | −0.23 | 151 | [−0.34, −0.12] |
| unit (every day) | Zb | −0.01 | 349 | [−0.12, 0.09] |
| unit | Zb + outages | −0.02 | 131 | [−0.15, 0.12] |
| unit | Zc | −0.61 | 415 | [−0.72, −0.52] |

Unit × month, Zb:

| sample | β | F | 95% set |
|---|---|---|---|
| units with a storage series | −0.16 | 255 | [−0.27, −0.05] |
| flat unit-days left out | −0.23 | 321 | [−0.32, −0.15] |
| storage hydro only, no pumped | −0.22 | 331 | [−0.30, −0.14] |
| six owners only | −0.23 | 399 | [−0.31, −0.15] |
| 2019 – 2021H1 | **+0.14** | 297 | [0.02, 0.26] |
| 2021H2 – 2023 | −0.25 | 321 | [−0.36, −0.15] |
| **2024 – 2025-09** | **−0.16** | **91** | **[−0.25, −0.06]** |
| 2024 – 2025-09, unit × day | −0.40 | 94 | [−0.51, −0.30] |
| by sign: β⁺ (net sellers) / β⁻ (net buyers) | −0.35 (0.08) / −0.02 (0.06) | 179 / 597 | equal rejected, p 0.004 |
| by sign, 2024 – 2025-09 | −0.28 (0.07) / +0.04 (0.08) | 93 / 218 | p 0.002 |

- **The instrument is strong where the others were weak**, including 2024–2025, where
  outages gave F 2–3. The solar years are now identified.
- **Full market power is rejected everywhere** (p below 10⁻¹⁵); the highest upper bound
  in any row is 0.26 (2019 – 2021H1), and 0.12 in the rest.
- **The outages agree with it**: used together the overidentification test passes and the
  set barely moves (unit × month [−0.34, −0.12]).
- **The sign moves with the fixed effects and the period, as for thermal plant**
  (thermal: −0.27 unit × month, −0.08 unit × day, +0.10 fuel × date; in 2019 – 2021H1
  −0.03, +0.12 and +0.46). Here: negative within the day and within the month, zero across all days,
  and **positive in 2019 – 2021H1 (+0.14, set [0.02, 0.26])**, about a seventh of Nash,
  close to what EDP's within-day response gave (3–14% of Nash, leg A). From 2021H2 on,
  negative.
- **The negative values come from net sellers' steps** (β⁺ −0.35, β⁻ ≈ 0). The
  candidate that the firm's own zero-priced volume and water drive them is ruled out (§6.1).
- Zc in pure levels (−0.61) uses each unit's own λ*, so its error enters; not read.

**Reading.** On hydro, across days as within them: β is bounded well below Nash
(upper 0.12 outside 2019 – 2021H1), in every period including the solar years. Whether
it is zero, slightly positive (as before mid-2021) or slightly negative depends on which
variation is used, as for thermal; the cause of the negative values is open.

## 6. Two checks: the negative sign and the storage sign (2026-10-07)

`analysis/leg_b_water_checks.py`; `outputs/tables/leg_b_water_checks.csv`.

### 6.1 The negative β is not the firm's own zero-priced volume or its water

**The candidate.** On a wet or windy day a firm sells more energy offered at zero
(run-of-river, wind), so its net position n and X are high; if its water is worth less
than λ* on the same days, its steps sit below λ* exactly when X is high, and β is
pulled down. The at-cost curve keeps that volume, so Zb would carry it too.

**The test.** Add controls known when offers close:
- **V0**: the firm's own sell offers at or below €1 in the hour (nuclear, wind, solar,
  run-of-river, cogeneration), GW, less its storage and pumped hydro offered there (a
  water-value choice, not weather).
- **Unit rain**: rain over the catchments of the unit's own plants in the 90 and 30 days
  to D−2 (E-OBS, `build_catchment_rain.py`), as a z-score against 1991–2020.
- **Firm rain H90**: the same over the firm's whole hydro fleet, GW × ownership share.

The first link holds: X̃ and Zb rise by about 2 per GW of V0, and hydro steps sit €2.7
lower against λ* per GW. Rain moves neither within a month. But **the controls do not
move β**:

| | controls | β | 95% set |
|---|---|---|---|
| hydro, unit × month | none / V0 | −0.22 / −0.21 | [−0.30, −0.15] / [−0.29, −0.13] |
| hydro, six owners, unit × month | none / V0 + rain + H90 | −0.21 / −0.20 | [−0.29, −0.13] / [−0.28, −0.12] |
| hydro, unit × day | none / V0 | −0.37 / −0.38 | [−0.52, −0.25] / [−0.54, −0.25] |
| hydro, net sellers β⁺ | none / V0 / V0 + rain + H90 (six owners) | −0.35 / −0.33 / −0.37 | |
| hydro, unit only, six owners | none / V0 + rain + H90 | +0.17 / +0.17 | [0.04, 0.30] / [0.05, 0.30] |
| thermal, unit × month | none / V0 | −0.27 / −0.26 | [−0.37, −0.18] / [−0.36, −0.17] |
| thermal, five firms, unit × month | none / V0 + H90 | −0.25 / −0.25 | [−0.35, −0.15] both |
| thermal, unit × day | none / V0 | −0.08 / −0.09 | [−0.19, 0.02] / [−0.20, 0.02] |

So the negative sign is not water and not the firm's own zero-priced output, in hydro
or in thermal plant. Its cause is still open; what is known is that it sits in net
sellers' steps and appears only when comparisons are within a month or a day. (With unit
effects only, the six owners give +0.17 where all owners give −0.01: the small owners'
units pull that row down, not the controls.)

### 6.2 The wrong storage sign comes from the years, not from incomplete storage data

The paper's fit (§4) gives fuller reservoirs a higher λ̂: +0.9 €/MWh per 10 points of
fill. The fill series are incomplete: MITECO is the whole demarcation, irrigation and
supply dams included; SNIRH covers only EDP's and Movhera's own reservoirs; and 9 of the
28 units (2,118 of 19,059 hours) have no series, among them Iberdrola's Tâmega (986 hours)
and Repsol's Viesgo (616). Classical noise in fill would only
shrink the coefficient toward zero, not flip it; error correlated with the water value
could. Catchment rain needs no storage data, covers 23 of the 28 units, and is not
chosen by the firm.

| fit of λ̂ (β = 1) | water term | coefficient | se |
|---|---|---|---|
| fill, unit effects (§4) | per 10 points | +0.90 | 0.45 |
| fill, units with own-reservoir data (SNIRH, 7 units) | per 10 points | +0.33 | 0.43 |
| fill, units with basin data (MITECO, 12 units) | per 10 points | +2.71 | 0.83 |
| **fill, unit + year effects** | per 10 points | **−0.94** | 0.41 |
| **rain over 90 days instead of fill** (23 units) | per sd | **−2.41** | 0.81 |
| fill instrumented by 90-day rain (F 122) | per 10 points | −5.12 | 1.97 |
| rain over 365 days | per sd | +1.50 | 0.92 |
| 90- and 365-day rain, unit + year effects | per sd of 90-day rain | −4.48 | 0.78 |

With year effects, fill takes the right sign for EDP (−2.3), Iberdrola (−3.5) and Naturgy
(−2.1); Endesa −0.4 and Movhera +3.0 (one unit) are not different from zero.

- **Data quality matters, but it is not what flips the sign.** Basin data gives a more
  positive slope than own-reservoir data (+2.7 against +0.3), as a looser proxy would.
  But neither turns negative across years, and both do within years.
- **What flips it is a coincidence across seven years.** Year by year, within units:

| year | λ̂ less 1.10 × forward | fill (10-point units) | price-setting hours at midday | price there over the day's mean |
|---|---|---|---|---|
| 2019 | −5.6 | −0.5 | 31% | 1.05 |
| 2020 | −4.8 | +0.3 | 29% | 1.05 |
| 2021 | −4.3 | −0.2 | 25% | 1.04 |
| 2022 | +2.1 | −1.5 | 17% | 1.09 |
| 2023 | +4.9 | +0.6 | 14% | 1.11 |
| 2024 | +7.0 | +0.8 | 13% | 1.13 |
| 2025 | +9.2 | +0.7 | 9% | 1.26 |

  λ̂ rose against the forward by about €15 over the period, because solar pushed the
  hours in which storage hydro sets the price out of midday and into the evening, which
  is dearer than the baseload forward. Reservoirs happened to be fuller in 2023–2025
  than in 2019–2022 (the 2022 drought). Across years the two move together, and that is
  the +0.9.
- **Rain over a year carries the same across-year confound** (+1.5); rain over 90 days
  mostly varies within years and gives the right sign.
- **Every day, not only price-setting hours**: the offer at the expected running share
  over λ*s falls with fill (−0.021 log points per 10 points) and with rain (−0.041 per
  sd), beyond λ*s's own storage adjustment. Iberdrola (+0.07) and Naturgy (+0.05) are the
  exception, as in `rq-water-value-forward.md` §5.3.

**Reading.** The paper's method recovers the right storage sign on these data once the
comparison is within years, or with rain in place of storage. Fill is the paper's own
regressor, so the comparison with Murray (negative on volume) needs year effects here.

## 7. Limits

- e contains the benchmark's error (option value, forward risk premium, a wrong capacity
  factor). Outages are known at D−2 and partly in the forward, so they move the market's
  λ*; the class × hour effects absorb that common move, and only the difference between
  co-owners' doses identifies.
- X̃ is defined on resampled draws; the slope floor (20 MW per €/MWh) drops thin bands.
- The across-day margin is read within months; withholding spread over months is in the
  unit-effect rows only, which are less precise.
