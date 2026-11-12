# Two follow-ups to the cross-tariff run: a pooled placebo repair, and persistence of the household response to 2026

**Status: pre-registered 2026-11-12, before any code or run.** Branch `tou-policy-prices`. Follows `2026-11-12-industry-voltage-design.md` (results section: rule 3 failed for E0 and E1+E2; the high-voltage placebos are positive and as large as the estimates). Both parts are informed by those results, which is stated here; neither rescues the industrial gradient by changing its rules.

## Part A. Pooled placebo calendars (cross-tariff design)

**Question.** Is the 2019 placebo failure (E0 η −0.023, t −4.0; E1+E2 −0.078, t −2.8) one bad calendar or a floor in every year?

**Design.** Lay the real dose pattern (same weighted doses, same E) on the 2018 and 2019 windows 06-01 → 09-15 separately and pooled (2018 cross-fitted with 2018 left out, 2019 likewise; both years' pre-months in each sample). Same regression, column-4 fixed-effect set, clustering area × month. Report η and t per placebo year and pooled for all five series.

**Rules, set now.**
A1. Report the placebo η as a share of the real η (floor). 
A2. For each readable series the real η lies below both placebo years' η; a series "separates from the floor" if its real η is below the pooled placebo η by more than two combined standard errors.
A3. If E0 separates and E1+E2 does not, the industrial series stay not identified (no change to the earlier verdict). If neither separates, the E0 household anchor is also reported with the floor beside it and the headline carries the floor as a caveat. No series is promoted to a result by this part.

## Part B. Persistence of the E0 response, 2021 to 2026

**Question.** Does the evening-versus-night reduction of low-voltage demand persist when the charges, the energy price and the tariff mix change, summer by summer?

**Design.** E0 (ESIOS 1201) against Portugal (REN), the paper's per-hour LASSO trained on 2018-01-01 → 2020-12-31 without March–June 2020 (as in `tou_lasso_paper.py`), evening 18–21h against night 0–7h, working days against weekends and holidays. Same-season comparison only: the **June 1 → September 15 window of each of 2021, 2022, 2023, 2024, 2025** (this removes seasonality from the comparison across years). For each summer: the DDD of errors (b, se, weekly clusters) and the Wald ratio b / Δ ln relative price, where the relative price is the 2.0TD evening-versus-night price **including the year's energy price**: ln[(Ē_y,ev + T_ev)/(Ē_y,night + T_night)] against the old flat regime in 2021 as the paper's reference, with Ē from OMIE that summer and tolls+charges from ESIOS 1876 (June 2021 onward), and Spain's PVPC 1001 as a check.

**Rules, set now.**
B1. **Data.** E0, Portugal and 1876 cover all five summers; any summer missing a source is not read.
B2. **Anchor.** The 2021 window reproduces the paper-LASSO effect from the hardening spec (−3.8% evening versus night, se 0.4) within 0.5 points.
B3. **Drift guard.** A fake DDD on weekends and holidays only (the paper's weekend check, same hours) is within ±1.0 point in a summer for that summer to be read. A summer failing it is reported as not readable, not as a persistence result.
B4. **Persistence.** "Persists" if every readable later summer has a negative effect with t ≤ −2 and the effect is at least half of 2021's. "Fades" if at least two readable later summers are below half of 2021 or have |t| < 2. Anything else is "mixed", reported by summer.
B5. **Price proportionality.** Wald ratios across readable summers: report the range. If the energy-price crisis (2022) cuts the relative price change by more than a quarter and the effect does not fall by a similar share, the ratio is read as instability of the elasticity, not as a stable parameter.
B6. **Extrapolation caveat.** The LASSO is five or more years out of sample in the last summers; state this beside every number, with the drift guard (B3) as the only check. No re-training on post-reform data.

## What each outcome means
Persists with a stable ratio: the −0.06 to −0.10 range is a durable elasticity, which is the extension the paper (sample to September 2021) cannot make. Fades: the 2021 response was an adjustment or announcement effect and the long-run elasticity is smaller. Mixed or unreadable: reported by summer with the extrapolation caveat; no long-run claim.

## Threats
Self-consumption solar grew after 2021 and removes evening-adjacent load in summer; the energy-price crisis of 2022 changed behaviour for reasons other than the toll structure; free-market contracts moved toward time-of-use offers; the PVPC energy term was partly forward-priced from 2024; the cargos cut of 2021-09-16 to 2021-12-31 and later charge steps change the relative price (this is what B5 reads). Aggregate low-voltage demand mixes regulated and free customers throughout.

## Results (2026-11-12; `analysis/tou_placebo_pooled.py`, `analysis/tou_persistence.py`; `outputs/tables/tou_placebo_pooled.csv`, `tou_persistence.csv`)

### Part A: the dose laid on 2018 and 2019 (cross-fitted, area-month clusters)

| series | real eta | placebo 2018 | placebo 2019 | pooled (t) | floor share | separation z (< -2 needed) |
|---|---|---|---|---|---|---|
| E0 | -0.101 | +0.004 | -0.020 | -0.009 (-1.5) | 0.09 | **-12.4** |
| E1+E2 | -0.168 | -0.096 | -0.080 | -0.097 (-2.0) | 0.58 | -0.8 |
| 6.2 | -0.080 | -0.245 | +0.089 | -0.085 (-1.4) | 1.07 | +0.05 |
| 6.3 | -0.321 | +0.051 | +0.252 | +0.161 (+1.2) | -0.50 | -2.3 |
| 6.4 (not readable) | -0.533 | +0.705 | +0.920 | +0.876 (+3.8) | -1.64 | -4.1 |

A1: the floor is 9% of the real eta for E0 (2019 alone, -0.020, had made it look like 20%) and 58% for E1+E2. A2: the real eta lies below both placebo years for E0, E1+E2, 6.3 (and 6.4); not for 6.2. A3: **E0 separates from the floor and E1+E2 does not, so the industrial series stay not identified**; 6.3 passes the separation test narrowly (z -2.3) on placebos that are positive and noisy (se 0.10 to 0.18), and no series is promoted by this part. The earlier E0 placebo failure (rule 3 of the cross-tariff design) was a 2019 calendar effect: pooled over both years the placebo is small and not significant.

### Part B: summer by summer, E0, paper LASSO trained 2018-2020 and not retrained

| summer | DDD evening vs night (se) | t | weekend drift | change in ln relative price | Wald | Wald with PVPC energy term |
|---|---|---|---|---|---|---|
| 2021 | -3.94% (0.42) | -9.4 | -2.91 | 0.765 | -0.051 | -0.059 |
| 2022 | -1.09% (0.56) | -1.9 | -3.42 | 0.357 | -0.031 | -0.058 |
| 2023 | -1.74% (0.61) | -2.9 | -2.74 | 0.495 | -0.035 | -0.044 |
| 2024 | **-4.32%** (0.31) | -13.9 | -0.34 | 0.558 | -0.077 | -0.097 |
| 2025 | **-4.44%** (0.69) | -6.5 | +1.60 | 0.650 | -0.068 | -0.086 |

B1 pass (all five summers have errors and prices). B2 pass (2021 -3.94% against -3.79%, within 0.5). **B3: only 2024 passes the weekend drift guard** (|contrast| <= 1.0 point; 2021 itself is -2.9). **B4 as registered: "persists", on one readable summer** (2024), which is thin. B5: the 2022 relative price change is 47% of 2021's (a cut of more than a quarter) and the 2022 effect is 28% of 2021's, so the effect fell by more than the price: read as instability of the elasticity in the crisis summers, not a stable parameter.

**Reading.** The registered guard does not do what it was meant to: the weekend evening-versus-night contrast is -2.9 points in 2021 itself, which is a genuine reform response on weekends (the paper finds weekend responses too: habit formation), not drift, so it cannot separate drift from response in the reform years and classes 2021, 2022, 2023 and 2025 as not readable. Stated post hoc, not registered: the summer effects are -3.9, -1.1, -1.7, -4.3, -4.4 percent; the two crisis summers (energy at 160-170 EUR/MWh in 2022, 103-114 in 2023, evening-night relative price down by half) show weaker responses and the response is back at its 2021 size or above in 2024 and 2025, with the LASSO four to five years out of sample (B6). Wald ratios run -0.03 to -0.08 across summers. What can be said: the response did not fade; it dips when the energy price is high and returns when it falls; the size of the later effects rests on a model that cannot be retrained and on a drift guard that failed in four of five summers.
