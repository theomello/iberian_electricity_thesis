# Within-day price response of regulated households (hourly design, after Fabra et al. 2021)

**Status: proposed 2026-11-11, written before any run.** Branch `tou-policy-prices`. Follows the failure of the tax-step design
(`2026-11-11-tax-change-design.md` §6–7).

**In one example.** On a day when the wholesale price is €60 at 04:00 and €140 at 20:00, a household on the regulated tariff
(PVPC) is billed hour by hour for the energy it uses, so its 20:00 price is 2.3 times its 04:00 price. If its 20:00 load, relative to
a Portuguese consumer facing the same wholesale prices, is lower on days when 20:00 is dearer against the rest of the day,
that is a price response. Every hour of a day shares the same date, weather and economy, so the comparison is within the day.

**Why.** Every aggregate design in this repo failed on a common demand component that moves with the price. Here the date is
held fixed (day effects), Portugal is differenced out, and the price variation inside a day is instrumented with the
day-ahead wind and solar forecasts, which move the hourly shape of the price and not household behaviour. Fabra et al. (2021)
find a household elasticity near zero on this setting; the design asks whether the aggregate data reproduce that.

**Goal.** The elasticity of regulated low-voltage load (E0) to its own hourly energy price, within the day. **Not goals:**
industry; any welfare number; the level elasticity across days.

## Data (all on disk)

| need | file |
|---|---|
| Outcome: ln E0 (ESIOS 1201) − ln Portuguese load (REN `Consumption`), same local hour | as `analysis/tax_did.py` |
| Price: ln of the PVPC energy term, hourly: ESIOS 1013 (2.0A, to 2021-05) and 1001 (2.0TD, from 2021-06) | `data/esios/esios_{1013,1001}.parquet` |
| Instruments: day-ahead wind (1777) and solar (1779) forecasts, hourly, from 2019-01 | `data/esios/` |
| Placebo outcome: industry E1–E6 (1202–1207) − Portugal | on disk |
| Weather: Spain and Portugal temperature differences | on disk |

## Design

y(d,h) = ln E0 − ln PT at local hour h of date d. Regress on ln price(d,h) with **date effects** and **hour × month effects**
(these absorb the fixed shape of the 2.0TD charges and the daily load shape), temperature differences by hour, clustered
by week. Two periods separately: **2019-01 → 2021-05** (PVPC 2.0A) and **2021-06 → 2023-12** (2.0TD; 2024 is out: the
PVPC energy term was partly forward-priced from 2024 and the tax steps move in that year). March–June 2020 excluded. OLS first,
then 2SLS with the wind and solar forecast deviations from the day's mean. The coefficient is the elasticity of E0 load
**among exposed households and small consumers**: E0 includes free-market customers (about 64% of supply points in 2019, CNMC),
so the whole-E0 coefficient is scaled up by the inverse of the exposed share (taken as 0.36, the CNMC's energy share of PVPC at
end 2019; not measured by hour) and both are reported.

## Stop rules, set before the run

1. **First stage.** The excluded-instrument F (clustered by week) at least 10 in each period; below that the IV is not read.
2. **Placebo outcome.** The same regression with industry (E1–E6) − Portugal. The E0 coefficient must be below the industry one by
   more than two combined standard errors; if industry responds as much, the coefficient is a shared Spain–Portugal pattern.
3. **Shifted price.** The same 2SLS with the price and instruments taken from each of the 10 days before and after (20 shifts,
   so a different day's price pattern): the real coefficient must lie outside the shifted ones' 5th–95th percentile and
   rank in the top 2 of 21 by absolute size.
4. **Sign and size.** Negative, and the exposed-share-scaled elasticity between −0.5 and 0 (Fabra et al. find about 0); positive or
   below −0.5 is read as confounding.
5. **Both periods.** The two periods must agree in sign.
6. **Power.** The standard error of the scaled elasticity against 0.1 (a typical small value): reported, and a coefficient
   whose 95% interval contains both 0 and −0.2 is called uninformative, not zero.

## Failure modes

Portugal's own wholesale-indexed customers are not zero (so a response there shrinks the difference); regulated customers are
36% of energy, so E0 dilutes the effect by two thirds and the scaling rests on a stated share; the 2.0TD's hourly energy term
carries the same hourly wholesale pattern for everyone, so industry on indexed contracts responds too (the placebo's job); the
forecasts move the price's shape through solar and wind jointly with the ramping of other plants, and wind and solar also
change net demand at the margin for households with rooftop solar (small in the window).

## Results (2026-11-11, user's go-ahead)

`analysis/hourly_price_response.py` → `outputs/tables/hourly_price_response.csv`. 2SLS elasticity of ln(E0 / Portugal) to ln hourly PVPC
energy term, date and hour × month effects, wind and solar forecasts as instruments, clustered by week; scaled = divided by the
exposed share 0.36. Industry (E1–E6) as the placebo outcome; the shift placebo takes price and instruments from the 20 days within
±10 of the date.

| period | n hours | OLS | IV | scaled IV | first-stage F | industry IV (placebo) | shifted IV: median, 5–95% | rank of real |
|---|---|---|---|---|---|---|---|---|
| 2019-01 → 2021-05 (PVPC 2.0A) | 18,236 | +0.046 (0.012) | **−0.091 (0.022)** | −0.25 (0.06) | 155 | +0.048 (0.024) | −0.056, [−0.081, −0.039] | 1 of 21 |
| 2021-06 → 2023-12 (PVPC 2.0TD) | 22,652 | −0.011 (0.003) | **−0.035 (0.008)** | −0.10 (0.02) | 130 | −0.032 (0.009) | −0.031, [−0.035, −0.023] | 2 of 21 |

Stop rules, in order. (1) First stage: **pass** in both periods (F 100–185). (2) Industry placebo: **pass in period 1** (E0 −0.091
against industry +0.048, a difference of −0.139 with combined se 0.032), **fail in period 2** (−0.035 against −0.032: industry
responds as much). (3) Shifted price: period 1 **passes by the letter** (the real −0.091 lies below the shifts' 5th percentile
−0.081 and ranks first), period 2 **fails** (−0.0353 inside [−0.0354, −0.0228] by a hair, rank 2). (4) Sign and size: negative, scaled
−0.25 and −0.10, inside −0.5 to 0: pass. (5) Both periods negative: pass. (6) Power: scaled 95% intervals [−0.37, −0.13] and
[−0.14, −0.06], which exclude 0.

**The shifted-price placebo is the important reading.** Using another day's price and instruments gives estimates that are
almost as negative as the real one: median −0.056 against −0.091 in period 1, −0.031 against −0.035 in period 2, every one of the
40 negative. So most of the coefficient is a within-day pattern that the price and the forecasts share with the Spain/Portugal
load shape on any day, not a response to that day's price. Net of the shift median the effect is about −0.035 in period 1
(scaled about −0.10) and about −0.004 in period 2 (zero). That is the same range as Fabra et al.'s near-zero household
elasticity. **Verdict:** the design passes its pre-set rules in the 2.0A period by the letter, but the shift placebo shows the
size is mostly baseline; the credible reading is a small response (0 to −0.1 scaled) not distinguishable from zero in the
2.0TD period. Not done: hour × month × weekday effects (the shape differs by weekday), which would tighten the shift baseline.
