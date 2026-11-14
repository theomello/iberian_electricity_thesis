# A retail price elasticity from Spain's electricity tax changes, 2021–2025

**Status: proposed 2026-11-11. Nothing is estimated. The 2021, 2022 and 1 January 2024 steps are confirmed in the BOE
(section 1b); the 2025 return to 21% is not.** Branch `tou-policy-prices`. Method: the prediction-error difference-in-differences of
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

The 1 January 2024 step is fixed by law (RDL 8/2023); the later 2024 steps (March, July) are triggered by the
wholesale price, so they are not exogenous and are flagged as such (see 1b).

### 1b. Check 1 result (2026-11-11): dates and rates against the BOE and the price shape

Confirmed in the BOE (searched 2026-11-11): **VAT 21% → 10% from 26 June 2021** (RDL 12/2021, contracts up to 10 kW, only when
the previous month's mean wholesale price is above €45/MWh); **electricity tax 5.11269632% → 0.5% from 16 September 2021**
(RDL 17/2021, to 31 December 2021, extended by RDL 29/2021 to 30 April 2022 and on through 2022 by RDL 11/2022); VAT 10%
extended to 30 April 2022 (RDL 29/2021). Not confirmed in the BOE: VAT 10% → 5% on 1 July 2022 (RDL 11/2022: a secondary
source only), the electricity tax steps of 2023–24 (a commercial site gives 0.5% to 2023, 2.5% in Q1 2024, 3.8% in Q2, then
5.11%), and the 2025 return to 21%. The 2022–25 rows stay unconfirmed and are not used until they are.

The VAT condition (previous month above €45) held in every month June 2021 → January 2024 (OMIE monthly means, all above €63
from 2021-05 to 2023-12). It first fails for February 2024 (€40), when VAT went back to 21% in March, and again April–June, back
to 10% in July. So **the 2021–22 steps are not triggered by the price and the 2024 ones are**, as flagged.

Tax factor (1 + electricity tax)(1 + VAT), `analysis/tax_price_shape.py` → `outputs/tables/tax_price_shape.csv`: 1.2719 before
26 June, 1.1562 after the VAT cut (−9.5 log points), 1.1055 after 16 September (a further −4.5), −14.0 in all. The pre-tax PVPC
energy term (ESIOS 1001) averaged €150 in June, €175 in July–mid-September, €266 from 16 September to December (+57 log points
from June). So **the tax-inclusive price rose 6% across the VAT step and 46% across the electricity-tax step**: both tax
cuts were smaller than the wholesale-driven rise in the same weeks. This is the price-crisis problem in numbers (section 5).
**Follow-up, same day: the 2022–24 steps confirmed in the BOE, and the price path fetched.** BOE-A-2022-10557 (RDL 11/2022,
published 26 June 2022): electricity tax 0.5% extended to 31 December 2022 (art. 17), **VAT 5% from 1 July 2022** (art. 18,
extended in the consolidated text to 31 December 2023); RDL 20/2022 (BOE-A-2022-22685) extends the 0.5% to 31 December 2023;
RDL 8/2023 (BOE-A-2023-26452): VAT 10% from 1 January 2024 (to 31 December 2024, with the €45 condition), electricity tax 2.5% in
the first quarter of 2024 and 3.8% from 1 April to 30 June. Not confirmed from the BOE: the 5.11% from 1 July 2024 (assumed:
the normal rate). The return of VAT to 21% on 1 January 2025 is reported by several news and consumer-association sources as
the rule lapsing with no extension (RDL 9/2024 of late December 2024 extended other measures, not this one), and the Tax Agency
reports the revenue effect to April 2025; the BOE text of 28 December 2024 was not read. ESIOS 1001 now on disk 2021-06 → 2024-12 (`esios_1001.parquet`, merged with the old
file after the fetcher overwrote it with the new range only).

Tax factor and tax-inclusive pre-tax-weighted price (`analysis/tax_price_shape.py`, monthly means of the daily path):

| step | date | tax factor | log points | pre-tax energy term, month before → month of | timing not set by the price? |
|---|---|---|---|---|---|
| VAT 21 → 10% | 2021-06-26 | 1.272 → 1.156 | −9.5 | €149 → €158 (July) | size fixed by law, but a **response to the price rise** (RDL 12/2021); condition held |
| electricity tax 5.11 → 0.5% | 2021-09-16 | 1.156 → 1.106 | −4.5 | €218 (Sep) → €258 (Oct) | size fixed by law, but a **response to the gas-price escalation** (RDL 17/2021's own title) |
| VAT 10 → 5% | 2022-07-01 | 1.106 → 1.055 | −4.7 | €291 (June) → €331 (July) | size fixed by law, a **crisis-package extension** (RDL 11/2022) |
| VAT 5 → 10% and electricity tax 0.5 → 2.5% | 2024-01-01 | 1.055 → 1.128 | +6.7 | €128 (Dec) → €140 (Jan) | closest to yes: a scheduled phase-out fixed on 27 December 2023 (RDL 8/2023), though it too was legislated in response to the price path |
| VAT → 21% | 2024-03-01 | 1.128 → 1.240 | +9.5 | €107 (Feb) → €90 (Mar) | **no**: triggered by the February price (€40) |
| VAT → 10%, electricity tax → 5.11% | 2024-07-01 | 1.256 → 1.156 | −8.3 | €117 → €133 | **no**: triggered by the June price |

The previous-month price was above €45 in every month from June 2021 to December 2023 (so the 2021–22 cuts were never
withdrawn by the rule). Reading: **the 2024-01-01 step is the best test**: a reversal of +6.7 log points with the wholesale price
roughly steady and in the same direction, against the cuts of 2021–22, when the wholesale price rose 10 to 20 log points in
the same month. In 2021–22 every tax cut coincided with a rise in the pre-tax price; the tax-inclusive price rose after every
cut. The 2022-07-01 step falls in a month of rising prices (€291 → €331 → €395). **Check 1 now passes on dates and tax
factors for the steps of 2021, 2022 and 1 January 2024.**

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

## 6. First run (2026-11-11, user's go-ahead): the tax steps fail the direction rule

`analysis/tax_did.py` → `outputs/tables/tax_did_{estimates,placebo}.csv`. Measured low-voltage demand (E0, ESIOS 1201) against
Portugal's consumption (REN), log difference at the same local hour, 2018-01-01 → 2024-12-31 (61,353 hours); DiD with a post
dummy and hour, weekday and month effects (V1), with temperature and holiday differences (V3), clustered by week; LASSO
prediction errors. Post window 4 months, cut at the next step (S1 82 days, S4 two months, to the price-triggered step of
March 2024). Pre window A = the whole prior period (the spec), March–June 2020 excluded; B = the 12 months before. Placebos:
19 fake steps, 1st of each month 2019-01 → 2021-02, none touching March–June 2020. Effects in % (log points), standard errors
in brackets.

| step | Δ ln tax factor | DiD V1 | DiD V3 | LASSO errors | Wald (V1, per unit Δ ln factor) |
|---|---|---|---|---|---|
| S1 VAT 21 → 10%, 2021-06-26 | −9.5 | −1.57 (0.94) | −1.91 (0.69) | −1.66 (0.78) | **+0.16** |
| S2 electricity tax → 0.5%, 2021-09-16 | −4.5 | −2.67 (0.83) | −2.82 (0.75) | −2.60 (0.81) | **+0.59** |
| S3 VAT 10 → 5%, 2022-07-01 | −4.7 | −2.34 (1.15) | −2.77 (0.95) | −0.79 (1.05) | **+0.50** |
| S4 VAT → 10%, tax → 2.5%, 2024-01-01 | +6.6 | −6.58 (0.81) | −6.71 (0.77) | −1.71 (0.60) | −0.99 |

Placebo sd 1.1 (DiD V1), 5–95% range −1.75 to +0.98; LASSO sd 1.6, range −2.0 to +3.1. Rank by absolute size among the 19
placebos and the step itself (DiD V1): S1 4/20, S2 1/20, S3 2/20, S4 1/20; LASSO 7, 3, 14, 6 of 20. With the 12-month pre window
the LASSO placebos have sd 7.4%: unusable, so variant B is reported for the DiD only (S1 −1.6, S2 −2.3, S3 −0.5, S4 −1.7).

Stop rules from section 4, in order: (1) dates confirmed: **pass**. (2) placebos: the DiD effects of S2, S3 and S4 sit outside
the placebo 5–95% range and rank in the top 2 to 3, but see 4; the LASSO version does not rank. (3) control noise: **not
computed**. (4) **Direction: fails.** All three cuts *lower* Spanish low-voltage demand relative to Portugal (−1.6 to −2.7 %), the
wrong sign; the one rise (S4) lowers it by 6.6% by DiD but 1.7% by LASSO and by the 12-month DiD, so its size depends on the
estimator. (5) **Sign and size: fails.** The Wald ratios for the three cuts are +0.16 to +0.59, positive. (6) power: effects are
1.5 to 2.5 placebo sd for the DiD, so small relative to noise. (7) exposed share: not computed.

**Verdict: stop, as pre-set.** A tax cut that lowers demand is read as confounding (rule 4). The likeliest confounder is the one
named in section 5, not tested here: in the same weeks Spanish regulated retail prices followed the wholesale price up (pre-tax
PVPC energy term +46 % across the autumn 2021 steps) while Portugal's did not, so Spanish demand fell relative to Portugal's
for a reason unrelated to the tax. That is itself a price response, to the wholesale-driven pre-tax price; it would be tested
by putting the pre-tax price in beside the tax factor, which needs a Portuguese retail price series as control. Not run.

**Correction (2026-11-11, user's question).** I called the 2021–22 steps "exogenous". The size of each cut was set by law and did
not respond to Spanish low-voltage demand, but the timing was a policy response to the rise in wholesale prices, so the steps
are endogenous to the price path, the confounder named in section 5. Controlling for the pre-tax price handles the price
itself; it does not rule out other reasons for the dates, so only a design that predicts the same sign from the tax alone
(section 7 below) can carry a causal claim.

## 7. Does the pre-tax price explain the fall? (2026-11-11, user's go-ahead; no rules set in advance, so the readings are post hoc)

`analysis/tax_pretax_price.py` → `outputs/tables/tax_pretax_price.csv`. Daily mean of ln E0 − ln Portuguese load on ln pre-tax
PVPC energy term (ESIOS 1001) and ln tax factor, with month, weekday, holiday and temperature-difference effects, Newey–West
14 lags, 2021-06-01 → 2024-12-31 (1,310 days) and → 2023-12-31 (944). Placebo outcome: industry (E1–E6, ESIOS 1202–1207), not
on the regulated tariff. Placebo period: 2018-01 → 2021-05 with the tax constant, March–June 2020 out. Coefficients are the
change in ln(E0 / Portugal) per unit of the log regressor (an elasticity-like number; a negative price response would be negative).

| outcome | window | spec | ln pre-tax price | ln tax factor |
|---|---|---|---|---|
| E0 | 2021-06 → 2024-12 | price only / tax only | +0.025 (0.005) | +0.063 (0.051) |
| E0 | same | both | +0.030 (0.005) | +0.143 (0.049) |
| E0 | same | both + trend | +0.027 (0.006) | +0.148 (0.048) |
| E0 | 2021-06 → 2023-12 | both | +0.023 (0.006) | +0.239 (0.069) |
| industry (placebo) | 2021-06 → 2024-12 | both | +0.049 (0.009) | +0.263 (0.094) |
| industry (placebo) | 2021-06 → 2023-12 | both | +0.017 (0.009) | +1.047 (0.125) |
| industry, both + trend | 2021-06 → 2024-12 | | +0.006 (0.011) | +0.361 (0.082) |
| E0, 2018-01 → 2021-05, tax constant | | PVPC 2.0A | +0.038 (0.017) | |
| industry, same | | PVPC 2.0A | +0.088 (0.033) | |

**Both coefficients are positive, and the placebo shows the same sign and a similar or larger size.** The pre-tax price coefficient
for E0 (+0.03) is positive, not the negative of a demand response; it is positive in 2018–21 before any tax step (+0.04), and for
industry, which is not on the regulated tariff, as large or larger (+0.05, +0.09). The tax factor coefficient is positive too
(a higher tax factor goes with higher relative Spanish demand: the wrong sign), larger for industry (+0.26 to +1.05) than for
E0 (+0.14 to +0.24). Reading: the positive price coefficients are the old simultaneity (Spanish demand high relative to
Portugal's raises the Spanish price), and the tax-factor coefficients are a staircase that falls through 2021–23 while Spanish
load, E0 and industry alike, drifts down against Portugal's. Neither says anything about a retail price response.

**Step DiD with industry as the outcome** (`outputs/tables/tax_did_industry_placebo.csv`, DiD V1, same windows): S1 +0.1%
(0.75), S2 −5.7% (1.6), S3 −7.2% (0.8), S4 −7.6% (2.5); LASSO +3.3, −3.0, −2.5, +0.6. Industry falls against Portugal at
the 2021-09, 2022-07 and 2024-01 steps by more than E0 does (−2.7, −2.3, −6.6). So **the fall in E0 at the tax steps is not
specific to the customers whose price the tax changed.** E0 minus industry rises at S2 (+3.0) and S3 (+4.9), the sign a tax cut
predicts, but industry has its own price response in 2022 (its price rose with the wholesale price and demand fell), so the
difference is confounded the other way; not estimated, no standard errors.

**Conclusion.** The tax-step design does not identify a price elasticity on this data: the E0 fall relative to Portugal is shared
by industry, the pre-tax price coefficient has the wrong sign and shows up in a pre-period with no tax change, and the dates
of the cuts were set in response to the price path. Nothing is left that the tax alone moves and the price path does not. What
would help: a Portuguese retail price series (to difference out the pass-through), an E0-minus-industry design with an
industry price control, or hourly variation within the day (the real-time pricing design of Fabra et al.). None is run.
