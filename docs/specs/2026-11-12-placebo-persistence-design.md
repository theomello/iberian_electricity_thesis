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
