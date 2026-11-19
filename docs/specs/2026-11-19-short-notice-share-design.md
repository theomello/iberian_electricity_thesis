# T1: how much of the planned response does a day-ahead price surprise get? (pre-registration, proposed)

**Status: proposed 2026-11-19, not registered. Binding when the user confirms and this file is committed; the run
follows that commit.** Framework: `notes/thesis-demand-supply-link.md` §2. Inputs: the period-price elasticity
(`2026-11-18-industry-regulated-price-elasticity-design.md`, done) and the wind-speed instrument
(`2026-11-17-industry-iv-wind-speed-estimation-design.md`, settled as the only instrument passing every check in
`2026-11-17-industry-iv-bid-instrument-second-settlement-design.md`).

**In one example.** Tariff 6.4 plants cut period-1 load when the reform made the period-1 charge dearer, about
−0.18 per unit of log price. If they reacted to a day-ahead price surprise as fully as to a planned change, a 10%
wholesale surprise would cut load by 0.18 × 0.32 (share bought at the hourly price) × 0.75 (wholesale share of the
full price) × 10% ≈ 0.4%. If they react not at all, 0%. λ is the measured fraction: observed surprise response over
that 0.4%.

## Model and estimand
From the demand equation, the impact elasticity of load to the day-ahead price is

  ε_u = σ · λ · θ · s,   s = p̄ / r̄  (wholesale share of the full scheduled per-period price)

so **λ = ε_u / (σ θ s)**. σ comes from the reform (planned change), ε_u from the instrument (one-day notice).

## Inputs
- **σ (not re-estimated):** pooled 6.2+6.3+6.4, full dose: **−0.177**, 95% interval **[−0.544, −0.095]** (six
  placebo summers). Its two failed rules (E3 drifted null, E5 not proportional) are carried into the reading.
- **ε_u (new run):** the wind-speed instrument C1, pipeline exactly as `industry_iv_wind_speed_estimation.py`
  (V3: week-on-week differences, double ML, the same controls and permutation scheme, 1,000 draws, seed 20261117),
  **outcome changed** from E3–E6 (ESIOS 1204–1207) to the sum of the tariff series **6.2+6.3+6.4 (1216–1218)**, so σ
  and ε_u describe the same consumers. Sample: non-holiday weekdays 2019-01-01 → 2023-12-31 without 2020-03-01 →
  2020-06-30 (as the E3–E6 run). Elasticity at the sample's mean price.
- **θ:** 0.32 main (CNMC IS/DE/031/24: share of industrial contracts priced hourly); 0.49 (indexed at all) and 1.0
  (direct market consumers) as sensitivities.
- **s (step 0, no estimation):** p̄ / r̄ with r̄ = day-ahead price + energy toll + charges + power-term equivalent per
  period, from the same tables as σ's dose (`tou_power_term_6x.csv`, `tou_industry_regulated_price.tables`, full
  variant), load-weighted over 6.2–6.4 and the sample's hours. Proportional taxes cancel in logs and are left out.

## Statistic and inference
- Point: λ̂ = ε̂_u / (σ̂ θ s).
- **Upper bound (primary):** Bonferroni-combined one-sided 97.5% bounds,
  λ_U = max(0, −ε_u,lo) / (|σ|_lo · θ · s), with ε_u,lo the lower end of the 95% randomization interval and
  |σ|_lo = 0.095. The two samples are independent in their identifying variation (one summer's calendar change
  against day-to-day wind), so the bound is conservative at 95%.

## Rules (set before the run)
- **G1 Gate, first stage:** F ≥ 20 on 6.2–6.4 (the settlement's S1 bar). Fail: stop; λ is not bounded; report the
  E3–E6 bound as secondary with the series-mismatch caveat.
- **G2 Gate, placebo outcome:** lag-7-day load, randomization p > 0.05. Fail: stop, as G1.
- **L1 λ = 1 rejected:** λ_U < 1 at θ = 0.32.
- **L2 Robust to exposure:** L1 also holds at θ = 0.49 (at θ = 1 it is reported, not a rule).
- **L3 Sign:** ε̂_u ≤ 0.02 (a clearly positive impact elasticity points at a broken exclusion, as in the earlier specs).

## What each outcome means
- G1, G2, L1–L3 pass: a day-ahead surprise gets less than the planned response, with the bound as its size; the
  thesis states "consumers respond to prices they can plan around", with λ_U as the number.
- L1 fails: λ = 1 is not rejected; the thesis says the surprise response is too small to measure against a planned
  response of this size, and does not claim λ < 1.
- No other series, instrument, sample or θ is tried after a failure.

## Reported, no rule
- **The bid-curve instrument** (closed by the second settlement; F 17 < 20): its E3–E6 estimate −0.036
  [−0.080, +0.010] is placebo-clean and implies λ̂ about 0.85 at θ = 0.32. Reported beside the result with that
  reading, because it points the other way from C1.
- The E3–E6 C1 estimate (+0.0001 [−0.021, +0.028]) and its λ_U.
- C1 by period 2019–21H1 and 2021H2–23 (the period-calendar σ applies after June 2021; the old tariffs before).
- Households: no same-hour instrument exists for E0; only the qualitative point (PVPC customers, who see the
  hourly price, respond less than the rest).

## Threats
- σ's size is not pinned down (E3, E5 failed); the bound uses its interval end nearest zero, which is the
  conservative side for L1.
- θ is a contract-count share, not a volume share; exposure by volume could differ.
- s varies across periods and years (2022 prices); one load-weighted s is used.
- σ is identified in summer 2021; ε_u over 2019–23. A λ that changes over time is not identified.

## Outputs
`scripts/analysis/tou_short_notice_share.py`; `outputs/tables/tou_short_notice_share{,_checks}.csv`. Reads existing
caches; writes nothing else.
