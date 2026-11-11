# Replicating the time-of-use response in Spain (Enrich, Li, Mizrahi and Reguant, JEEM 2024)

**Status: proposed 2026-11-11. Nothing here is built or estimated.** To be built on a fresh branch from `main`
after PR #8 merges. Paper: `papers/md/4-time-of-use-impacts-enrich-li-mizrahi-reguant.md`.

**In one example.** Before June 2021 a household on the regulated tariff paid the same network charge at every hour.
From 1 June 2021 the charge is three-part: peak (10–14h and 18–22h on working days) about 200% dearer, off-peak
(00–08h on working days, all weekend) about 86% cheaper. If a household's evening load falls 9% when the evening
price triples, that is a price response with no need to separate it from weather, because the price change is set
by the government, not by the market. Portugal had no such reform, shares the wholesale market and the weather, and is the control.

**Why.** Every aggregate design in this repo has failed on a common demand component that moves with the instrument
(the Italian placebo, `notes/rq-cogeneration.md`). Here the price variation comes from a policy with a known date
and a known shape by hour, and the paper gets elasticities of −0.08 to −0.135 on aggregate (distribution-area) data
with Portugal as the control. This is the one aggregate design the literature has shown to work in Spain.

**Goals.** (1) Replicate the peak, mid-peak and off-peak effects on regulated-tariff load, with the paper's
prediction-error difference-in-differences. (2) A price elasticity from the policy-moved price. (3) Compare with the
paper's −0.08 to −0.135 as a replication check, not as a target.

**Not goals.** An elasticity for industry (the reform changed their access tariffs too, so there is no clean control). A
welfare number. Free-market households.

## 1. Data

| need | on disk | source |
|---|---|---|
| Treated load: regulated (reference) retailers' schedule, hourly | `data/esios/esios_352.parquet` (2018 →) | ESIOS 352. A **schedule** (PBF), not measured load; the paper has measured load by distribution area |
| Control load: Portugal hourly consumption | `data/ren/ren_production_15min.parquet`, series `Consumption` (15-minute, 2018 →, mean 5.8 GW) | REN |
| Second control: France | `data/rte/eco2mix_national.parquet` (`consommation`) | RTE |
| Weather | `data/weather/temperature_population_index.parquet` (Spain), city files for Lisbon and Porto | Open-Meteo |
| Regulated price by hour | **not on disk**: ESIOS 1013 (PVPC, old 2.0A), 1001/1003–1005 (PVPC 2.0TD, total and P1–P3), 1876 and 1018 (charges component) | ESIOS, token, small; fetch needs the user's go-ahead |
| Holidays (peak definition) | `data/holidays/holidays_es_pt.parquet` | BOE |

The paper's sample is regulated households in five distribution groups, 2018 to September 2021. ESIOS 352 is their
total, and the reference retailers' schedule is a retailer forecast of load, so it cannot show a response the retailer
had not forecast. That is the main weakness; it is not checked yet.

## 2. Design

- **Window** 2018-01-01 → 2021-09-30, break 2021-06-01 (as the paper). Hourly outcome: log load, by period type
  (peak, mid-peak, off-peak, with weekends and holidays off-peak).
- **Step 1, difference-in-differences:** log load of Spain 352 against Portugal, treated × post by period type, with
  hour, weekday, month and temperature effects.
- **Step 2, prediction-error version** (Burlig et al. 2020, as the paper): LASSO on the pre-period to predict each
  series' load, prediction errors in the post-period, then errors on treated × post by period type with the same effects.
- **Step 3, weekday against weekend:** the paper's lower bound (weekend "fake peaks").
- **Step 4, elasticity:** the paper instruments log price with the policy-built price (the charges component under
  the TOU plus the prior average energy cost). With the PVPC price series this is the same construction.

## 3. Checks and stop rules, set before any run

1. **The price shape.** From ESIOS 1013, 1001 and 1003–1005, the peak price rises and the off-peak price falls on 1
   June 2021 by roughly the paper's +200% and −86% (charges component). If not, stop and find the difference.
2. **Placebo dates.** The same DiD on every fake break at the 1st of each month 2018-06 → 2020-12: the real peak
   effect must lie outside the placebos' 5th–95th percentile and rank in the top 5% by absolute size.
3. **Control tracks the treated before the break.** Pre-period prediction errors of Spain 352 and Portugal
   have the same trend: reported as the prediction-error trend by period type; a gap trending more than a third of the
   real effect per year is a stop.
4. **Weekend placebo.** Fake peaks on weekends reproduce the paper's pattern (an effect there too); reported, not a stop.
5. **Sign and size.** Peak effect negative, in the paper's range (1–9%). A positive or implausibly large effect
   (> 20%) is read as confounding, not a result.
6. **Power.** The peak effect in MW (about 6–9% of 352's peak load) against the placebos' standard deviation, before
   the elasticity step.

## 3b. Check 1 result (2026-11-11)

Fetched ESIOS 1013, 1001–1005, 1018 and 1876 (2018-01-01 → 2021-12-31, peninsular; `data/esios/esios_<id>.parquet`;
`analysis/tou_price_shape.py` → `outputs/tables/tou_price_shape.csv`). The access charge of the old 2.0A tariff is a flat
€44.0/MWh; the new 2.0TD charges component is €83.7 (peak), €31.9 (mid-peak), €3.4 (off-peak), average €28.8. Against the old
flat charge that is +90%, −28% and −92%; against the new tariff's own average +190%, +11% and −88%, which is the paper's
"+200% and −86%". So the paper's percentages appear to be relative to the new average, not the old flat charge (my reading, not
confirmed in the paper). The peak-to-off-peak ratio is 24.6. **Check 1 passes on shape.**

## 3c. Replication results (2026-11-11, user's go-ahead)

`analysis/tou_did.py` → `outputs/tables/tou_did_{estimates,placebo}.csv`. Spain's regulated-retail schedule (ESIOS 352) against
Portugal (REN `Consumption`), 32,847 hours 2018-01-01 → 2021-09-30, break 2021-06-01, each country on its own clock, difference of
logs at the same local hour; clustered by week. scikit-learn 1.9.1 installed for LASSO.

| log-point effect, % | peak | mid-peak | off-peak | peak − off |
|---|---|---|---|---|
| DiD V1 (hour, weekday, month effects) | −10.5 (se 1.1) | −6.4 (1.2) | −4.7 (1.1) | −5.8 (0.9) |
| V2 (+ linear trend) | −13.0 | −6.8 | −2.4 | −10.7 |
| V3 (+ temperature, holidays) | −13.8 | −7.2 | −1.6 | −12.2 |
| V4 (year-month effects, contrasts only) | | | | −5.8 (0.9), mid − off −1.7 |
| LASSO prediction errors (Burlig et al.) | −11.6 | −6.9 | −3.2 | |
| Paper, standard / ML | −8.9 / −9.5 | −5.7 / −6.4 | n.s. | |

Weekend and holiday days with fake peaks (same hours): DiD −9.3 / −5.7 / −1.5 (peak − off −7.8); LASSO −10.9 / −6.8 / +0.1.

Stop rules from section 3, in order:
2. **Placebo dates: fails by the letter, passes outside the COVID months.** 24 fake breaks at the 1st of each month 2019-01 →
   2020-12 (4-month post window): DiD V1 peak placebo sd 5.4%, 5–95% range −5.2 to +12.1; the real −10.5 lies outside it
   but ranks 3 of 25 by absolute size, because two COVID windows (breaks March and April 2020, Spain and Portugal locked
   down differently) give +12.7 and +13.1. Dropping the seven breaks whose window touches March–June 2020, the real effect
   is larger than all 17 others (largest −6.1): rank 1 of 18. LASSO: 5–95% −0.3 to +17.5, rank 4 of 25. The exclusion
   is a choice made after seeing the placebos.
3. **Control tracks the treated: weak.** Pre-break placebos run mostly negative in 2019 (−1 to −6%): Spain's regulated
   load falls relative to Portugal's as customers leave the regulated tariff (ESIOS 352 shrinks), so a drift is in
   the difference. The trend variants raise the peak effect (−13%).
4. **Weekend placebo: not separable.** Fake peaks on weekends fall about as much as real ones on working days (−9.3 against
   −10.5; peak − off −7.8 against −5.8), as in the paper (−8.3 and −7.3 on weekends). So the all-hours fall is a level shift
   or habit, and the policy-specific part (the contrast between periods on working days) is not distinguishable
   from the weekend one.
5. **Sign and size: passes.** Negative, below 20%; mid-peak −6.4% matches the paper's −6.4% exactly, peak −10.5 against −8.9.
6. **Power.** Peak effect se 1.1% against a placebo sd of 5.4% (3.7% outside COVID); about 10% of 352's roughly 2 GW is
   about 200 MW.

**Verdict.** The magnitudes replicate. The identification is thin: the fall appears in every hour type including
weekends, and the control drifts. The price elasticity step has not been run.

## 4. What would make it a failure even if it runs

The schedule (352) is not the load; the 2021 reform coincides with the post-lockdown recovery and a doubling of
wholesale prices, which Portugal shares but whose pass-through to the two countries' regulated consumers differs;
Portuguese national load includes industry, unlike the Spanish regulated segment, so the control's weather
sensitivity differs; ESIOS 352 includes social-tariff customers.
