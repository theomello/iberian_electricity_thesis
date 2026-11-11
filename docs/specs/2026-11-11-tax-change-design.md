# A retail price elasticity from Spain's electricity tax changes, 2021–2025

**Status: proposed 2026-11-11. Nothing here is built or estimated; the tax dates below come from a web search and
are not yet confirmed in the BOE.** Branch `tou-policy-prices`. Method: the prediction-error difference-in-differences of
Enrich, Li, Mizrahi and Reguant (JEEM 2024), replicated in `2026-11-11-tou-replication-design.md`, applied to a setting the
paper does not cover.

**In one example.** On 26 June 2021 the government cut VAT on electricity from 21% to 10% for households and small
consumers (contracted power up to 10 kW). A bill of 100 before tax went from 121 to 110, a fall of 9.1%, on one known day, for
every such customer whichever retailer they use. Portugal had no such cut. If low-voltage demand in Spain rises by 1% relative
to Portugal's after the cut, the elasticity is about −0.11. The price change is set by decree, not by the wholesale market, so
it does not move with demand.

**Why this setting.** Every wind-instrument aggregate design in this repo failed on a common demand component (the Italian
placebo, `notes/rq-cogeneration.md`). A tax change has a known date, a known size, and applies to all consumers of a type,
free-market included, so it does not depend on the weak 352 series the time-of-use replication leans on. It also gives
several steps in both directions (cuts in 2021–22, reversals from 2024), which allows a within-Spain placebo.

**Goals.** (1) The effect of each tax step on measured low-voltage demand (E0) relative to Portugal, with the
prediction-error difference-in-differences. (2) A price elasticity: the percentage change in tax-inclusive price against the
percentage change in demand, with the tax step as instrument. (3) A bound for the whole market by the exposed share (Lijesen
2007).

**Not goals.** An elasticity for industry (VAT is recoverable for businesses, so industry's price did not change). A
welfare number. Anything on the long-run.

## 1. The tax steps (to be confirmed in the BOE before any run)

From a search 2026-11-11 (Endesa, Moncloa, Hacienda, Eurofound; the sources disagree on some 2024 dates):

| date | step | note |
|---|---|---|
| 2021-06-26 | VAT 21% → 10%, contracted power ≤ 10 kW | conditional on the wholesale price above €45/MWh |
| 2021-07-01 | the 7% generation tax (IVPEE) suspended | a producer tax, passed to price through bids; tested in `analysis/ivpee_tax_test.py` |
| 2021-09-16 (?) | special electricity tax cut from 5.11% to 0.5% | date not confirmed |
| 2022-07-01 | VAT 10% → 5% (RDL 11/2022) | to end 2022, extended through 2023 (RDL 20/2022) |
| 2024-01-01 | VAT 5% → 10% | later 2024 movement conditional on the wholesale price (sources differ: 21% in March, 10% from July) |
| 2025-01-01 | VAT back to 21% | |

The 2024 steps are triggered by the wholesale price, so they are not exogenous and would be used only after
the date, trigger and direction are confirmed, and flagged as such.

## 2. Data

| need | on disk |
|---|---|
| Treated load | measured low-voltage demand E0 (`data/esios/esios_1201.parquet`, to 2026-04; hourly) and the regulated and free-market schedules (351, 352) |
| Control | Portugal's hourly consumption (`data/ren/ren_production_15min.parquet`, `Consumption`) to 2026-05 |
| Second control | France (RTE) |
| Price | the retail price including tax: the PVPC energy term (ESIOS 1001/1013) plus charges, times (1 + VAT) and the electricity tax; needs the tax rates by date from the BOE |
| Weather | Spain and Portugal city temperatures (on disk) |

**What E0 is not:** it includes consumers above 10 kW (not eligible for the VAT cut) and some small businesses, so the
treated share is partial; the exposed share has to be estimated (customer counts by contracted power: CNMC, not fetched).

## 3. Design

For each step, a window of 4 months after and the whole prior period (as in the replication): (a) the difference of log E0
and log Portuguese load at the same local hour, on post × hour type with hour, weekday and month effects; (b) the
LASSO prediction-error version (Burlig et al. 2020). Then an IV: log tax-inclusive price on the step, outcome log
E0 difference. Hour-type contrasts are not needed here (a tax cut has no hourly pattern), which removes the weekend
problem of the time-of-use design.

## 4. Checks and stop rules, set before any run

1. **Dates and sizes** confirmed in the BOE; the tax-inclusive price rises or falls by the stated percentage. If a date is wrong,
   stop and re-set.
2. **Placebo dates.** The same DiD at the 1st of every month on 2018-01 → 2021-05 (before any step), with the pre-window
   at least 12 months and the COVID months (March–June 2020) excluded in advance. The real effect must lie outside the placebos'
   5th–95th percentile and rank in the top 5% by absolute size.
3. **Control tracks the treated.** Pre-step ratio E0 / Portugal has a year-to-year variation reported as its sd; an effect smaller
   than twice that sd is not read as an effect.
4. **Direction and symmetry.** Cuts raise Spanish demand relative to Portugal, reversals lower it, with sizes within a
   factor of two of each other (price-inclusive steps are comparable in log points). A cut that lowers demand, or a
   reversal that raises it, is read as confounding.
5. **Sign and size.** Elasticity between −0.5 and 0; outside it is read as confounding.
6. **Power.** The step's effect on demand against the placebos' sd, before the IV.
7. **Exposed share.** Reported next to any whole-market figure.

## 5. What would make it a failure even if it runs

- The 2021 steps coincide with the start of the 2021–23 price crisis. Retail prices rise 60% in the same months through
  the wholesale price. Portugal shares the wholesale price, so the difference removes it, but pass-through to retail
  differs by tariff (the regulated one passes it through at once, free-market contracts lag).
- The steps come in a package (VAT, electricity tax, generation tax, later the cap's retail effect), so separate effects
  cannot be read from one date.
- Portugal had its own measures (the 2022 energy-cost support, social tariffs); the control's price is not constant.
- E0 includes consumers who are not exposed to the VAT change, so the effect is diluted by the exposed share.
- Demand responds to the tax-inclusive price only if consumers see it on the bill, which takes a billing cycle: the first
  weeks after a step may show nothing.
