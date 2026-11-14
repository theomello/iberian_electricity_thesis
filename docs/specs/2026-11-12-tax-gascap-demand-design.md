# Can the tax steps or the gas cap serve as demand designs? Verdicts and a pre-registered gas-cap event study

**Status: written 2026-11-12, before any estimation.** Branch `tax-gascap-demand`, cut from `tou-policy-prices` (3a3b400). The
time-of-use work stays on that branch. Nothing below has been run on the real event window; section 3.0 records the one
exploratory look I took while writing, and says what it does to the rules.

**Acronyms.** VAT = value-added tax. PVPC = *Precio Voluntario para el Pequeño Consumidor*, Spain's regulated retail tariff,
billed hour by hour on the day-ahead price. ESIOS = REE's data platform. PBF = *Programa Base de Funcionamiento*, the base
schedule. E0 = measured demand connected below 1 kV. 352 / 351 = ESIOS scheduled demand (PBF) of the reference (PVPC)
retailers / the free-market retailers. DiD = difference-in-differences. LASSO = penalised regression for the prediction errors
of Enrich, Li, Mizrahi and Reguant (JEEM 2024). MDE = minimum detectable effect. RDL = *Real Decreto-ley*. Y = the decree's
unit subsidy, (gas price − reference price) / 0.55.

## 1. Tax steps: verdict KILL for all four

**In one example.** On 26 June 2021 a household's bill went from 121 to 110 per 100 before tax, a 9.5 log-point fall in the tax
factor. If demand rose against Portugal's, the ratio is an elasticity. It did not: Spanish low-voltage demand fell 1.6% against
Portugal's, and Spanish industry, which pays no VAT cost, fell as much at the later steps. The reasons are already in
`2026-11-11-tax-change-design.md` §6–7; this section applies them step by step.

| step | date | Δ ln tax factor | what the data say | why it cannot be revived | verdict |
|---|---|---|---|---|---|
| S1 VAT 21→10% (≤ 10 kW) | 2021-06-26 | −9.5 | E0 vs Portugal −1.6 (se 0.9), wrong sign; industry +0.1 (VAT is recoverable, so a clean placebo here) | direction rule fails; timing a response to the wholesale price (RDL 12/2021 applies only above €45/MWh); pre-tax PVPC price rose 6% across the step | **kill** |
| S2 electricity tax 5.11→0.5% | 2021-09-16 | −4.5 | E0 −2.7 (0.8), wrong sign; industry −5.7 | **applies to industry too** (it is not VAT), so industry is not a placebo; the pre-tax PVPC price rose 46% across the step (gas escalation, the decree's own stated reason) | **kill** |
| S3 VAT 10→5% | 2022-07-01 | −4.7 | E0 −2.3 (1.2); industry −7.2. E0 − industry = +4.9, the right sign, but an elasticity of about −1.0 | size outside the −0.5 to 0 rule (rule 5); industry fell for its own price reason, so the gap is not clean; step falls in the price crisis (€291→€331→€395) | **kill** |
| S4 VAT 5→10%, electricity tax 0.5→2.5% | 2024-01-01 | +6.6 | E0 −6.6 by DiD but −1.7 by LASSO and by the 12-month DiD; industry −7.6 | estimator-dependent size; industry falls as much; both taxes move, the second also for industry. Closest to exogenous (scheduled phase-out, RDL 8/2023), but legislated on the price path | **kill** |

The two later 2024 steps (March, July) are triggered by the wholesale price and were never candidates.

**Is any angle left?** Three were checked; none can be run on data that exist here.
1. **The 10 kW threshold.** The 2021 VAT cut covered contracts up to 10 kW only, so customers just above the threshold are a
   within-low-voltage control with the same weather, retailer mix and wholesale price. It is the only variation the tax alone
   moves. It needs hourly or daily load by contracted power, or by access tariff, in 2021–22. ESIOS 1209 (2.0TD, below 15 kW)
   exists only from 2024, and ESIOS 10268 (the tariff total) is empty for the low-voltage tariffs before 2024
   (`CLAUDE.md`, demand by segment). Data that would settle it: meter-level or distributor-aggregated load by contracted power
   (the distributors' open data, or the CNMC retail-market supervision files), not checked for availability and not public as far
   as this repo knows. The group between 10 and 15 kW is also small, so power would be a question even with the data.
2. **Hourly variation.** A tax multiplies every hour's price by the same factor, so there is no within-day contrast to exploit.
3. **A Portuguese retail price series** to difference out pass-through: only semiannual Eurostat prices exist (10 points,
   `2026-11-11-hourly-price-design.md`), too few.

**Revive condition:** the load-by-contracted-power series in point 1, and only for S1 (the one VAT-only step with a clean
industry placebo and the 10 kW cut). Otherwise closed.

## 2. The gas cap as a demand event: what it would have to be, and one fact that changes the design

The design the brief asked for assumes the cap **lowered** the regulated price, most in the evening hours where gas sets the
price. The decree also **charges** the cost of the subsidy to buyers, and PVPC customers pay it as a component of their hourly
price (RDL 10/2022 art. 13.1; `notes/rq-crisis-quantity.md` §E3). Reference suppliers paid about **twice** the per-MWh charge of
the free market in summer 2022, because free-market contracts signed before 26 April 2022 at fixed prices were exempt
(`rq-crisis-quantity.md` Correction 2). So for a PVPC customer the cap is a wholesale fall **plus** a flat-ish charge, and the net
sign is an empirical question.

**In one example (exploratory, two weeks either side of 15 June 2022, hourly means, €/MWh):**

| hour | PVPC energy term (ESIOS 1001), 1–14 June → 15–28 June | day-ahead price | cap charge (ESIOS 1909) |
|---|---|---|---|
| 03:00 | 241 → 342 (+101) | 192 → 151 | 0 → 130 |
| 13:00 | 271 → 290 (+19) | 178 → 133 | 0 → 67 |
| 20:00 | 323 → 349 (+26) | 221 → 159 | 0 → 91 |

The wholesale price fell by €40–60 and the charge added €67–130, so the **regulated price rose on net, most at night, and the
evening-minus-midday gap barely moved** (52 → 60). The premise "the cap lowered PVPC most in the evening" is wrong on this
look. What the event offers is a **net price rise of 10–30% for regulated customers on a known day, with the night dearer
relative to midday by about €80**.

### 2.1 What ρ is needed for, and what it is not

The elasticity uses the **price actually paid**, observed hourly in ESIOS 1001, not ρ (the pass-through of the subsidy into
Iberian offers, `notes/rq-crisis-quantity.md`, central band 0.5–0.85). ρ only matters for how much of the price jump the cap
caused rather than weather. That is handled by instrumenting with **Y × post** (Y from MIBGAS gas prices, already in
`implied_marginal_cost_daily.parquet` as `subsidy_eur_mwh`), which moves with world gas prices and the decree's formula, not with
Spanish household load.

## 3. Pre-registered design: event study at 2022-06-15

### 3.0 Exploratory look already taken (disclosed)

The table above was computed before this spec was written. It is a descriptive price check on 28 days; no demand series was
touched. It is why the design tests the **net** price and is built around gate G1–G3; the thresholds below were set from the
tax history and the hourly design (0.10 log points), not tuned to these numbers. Anyone reading the gates as blind should
discount G1 accordingly.

### 3.1 Units and data (all on disk except as noted)

- **Treated outcome, primary: ESIOS 352**, scheduled demand of the reference retailers (100% exposed to the PVPC price).
  **It is a retailer forecast of load, not measured load**, and the retailers' forecast of PVPC load embeds temperature and
  habit, so a real response is damped and lagged in it. Moreover customers leave PVPC for fixed-price contracts through 2022,
  moving load from 352 to 351.
- **Controls:** (a) Portugal's total consumption (REN, as in `tou_did.py build()`), regulated retail price flat within the
  window (ERSE sets annual tariffs; mid-2022 update dates to be confirmed in step 1); (b) **ESIOS 351**, Spain's free-market
  retailers, mostly exempt from the charge and on fixed prices, so a Spain-specific, same-source control that absorbs the
  heatwave, the economy and any saving campaign. Switching 352 → 351 moves load between them; the within-day contrast (3.3)
  differences it out.
- **Consistency series: E0 (ESIOS 1201), measured.** PVPC is about a quarter of E0, so a true effect is a quarter the size.
  E0 is read as a check, not as the headline.
- **Price:** ESIOS 1001 (2.0TD energy term including the cap charge, peninsula); **cap charge** ESIOS 1909; Y from
  `subsidy_eur_mwh`; day-ahead price from OMIE; temperatures `temperature_population_hourly`. The tax factor is constant in
  the window (VAT 10%, electricity tax 0.5%); the VAT cut of 1 July 2022 is outside it.
- **Window:** 28 days before (2022-05-18 → 06-14) and 14 days after (06-15 → 06-28). Short on purpose: it ends before the
  VAT cut (07-01), the Aug 2022 demand-saving decree (RDL 14/2022, 1 Aug) and the start of mass switching to fixed prices.

### 3.2 Estimators

1. **Primary DiD:** ln(352) − ln(control) at the same local hour, on post × hour-block, with hour, weekday and holiday effects
   and temperature differences, clustered by day.
2. **Paper-style LASSO errors:** per series, trained 2021-10-01 → 2022-05-17 (after the June 2021 time-of-use reform and its
   autumn adjustment), predicting the window; the DiD of the errors. Only one training year, so it cannot learn June
   seasonality: it is the secondary estimator and is reported with that caveat.
3. **Elasticity:** two-stage least squares, outcome the log difference, regressor ln PVPC price, instrument **post × Y**, and
   as a second version post alone; reported next to the reduced form.
4. **Within-day components (hour blocks fixed now):** night 00–07, midday 11–14, evening 19–22 (local). Contrasts:
   evening − midday and night − midday, each a triple difference (post × block × treated), which removes anything that moves
   a whole day (heat, switching, saving) and keeps only what moves the block's relative price.
5. **Reverse event, symmetry check:** the charge falls to zero when Y reaches zero (last positive day 2023-02-25). The same
   estimators on 2023-02-26 ± the same window. Weaker (winter to spring, gas-price-driven timing) and labelled so.

### 3.3 Threats, written before the run

| threat | handling |
|---|---|
| **Heatwave 11–18 June 2022** straddles the start | temperature differences in every spec; a version dropping 11–18 June; the 351 control shares the heat |
| 1 July 2022 VAT cut | window ends 28 June |
| Demand-saving campaigns | the EU campaign and RDL 14/2022 (1 Aug) are after the window; 351 control; checked by 2021 same-date placebo |
| **Only ~25% exposure** (PVPC share of E0) | 352 is the primary outcome (100% exposed); E0 scaled by 0.25 as a check |
| **352 is a forecast** | stated; the measured-load check is E0; a response to price within two weeks may not enter the retailer's forecast, which biases toward zero |
| **Customers switching out of PVPC** | within-day contrast; report the 352/351 share path before and after |
| Uncertain cap-caused share of the price change | use the observed price and instrument with post × Y (§2.1); never ρ |
| Billing: prices published a day ahead, bills monthly, attention small | state; Fabra et al. (2021) find household elasticity near zero on this tariff, so the prior is a null |
| Control group's own price | Portugal's regulated tariff passes the charge through on a lag; confirm the update dates; 351 is the second control |
| The charge is one number added across hours | an artefact: hourly 1909 differs by hour (67–130), and the within-day contrast needs the net 1001 shape, gate G2 |

### 3.4 Steps and stop rules (set now; each step waits for the user's go-ahead)

**Step 1: price gates, no demand series.** Descriptive. Over the full window and as a placebo set of the same 28/14-day windows
at the 1st and 15th of each month from 2021-10 → 2022-04 and 2022-08 → 2023-01 (none touching 2022-06-15 or 2022-07-01).
- **G0** 1001 contains 1909: a regression of the hourly change in 1001 on the changes in 1909 and in the day-ahead price gives a
  coefficient on 1909 within 0.8–1.2. If not, the net price is not what 1001 reports and the design stops.
- **G1** Net level: |Δ ln 1001| in the window ≥ 0.10 **and** above the 95th percentile of the placebo windows' |Δ|.
- **G2** Within-day: a block contrast is tested only if its relative price change ≥ 0.10 log points and above the placebo 95th
  percentile; otherwise that component is dropped and not rescued by a different block.
- **G3** First stage: post × Y on ln 1001, F ≥ 10 clustered by day, in the cap period 2022-06-15 → 2023-02-25 (243 days).
- **G4** Switching: the 352 share of (351 + 352) does not fall by more than 3% of itself across the window. A larger fall means
  the series changes composition; then only the within-day contrast is read.

**Step 2: power gate, placebo breaks only; real post-window outcomes sealed (as in `rq-crisis-quantity.md` step K1).** DiD and
LASSO errors of 352 against Portugal and against 351, and E0 against Portugal, at the placebo breaks above. MDE = 2.8 × placebo
sd. Implied effect = −0.10 × the window's Δ ln price (the hourly design's upper bound on the elasticity).
- **P1** MDE (352) ≤ half the implied effect → run the real date as an estimate.
- **P2** otherwise, if MDE ≤ the effect implied by an elasticity of −0.5 → run the real date **as a bound only**, reported as
  "elasticity above x", never as an estimate.
- **P3** otherwise **kill**: report the MDE and stop. (Expected, honestly: a 28/14-day window is noisier than the four-month
  windows of the tax design, whose placebo sd was 1.1–1.6%; a −0.1 elasticity on a +20% price is −2%. This gate may well fail.)

**Step 3: the real event.** Only if Step 2 passes. Rules, in order:
1. **Sign and size:** the 2SLS elasticity between −0.5 and 0; a positive sign or below −0.5 is read as confounding.
2. **Placebo rank:** the real DiD lies outside the placebo 5–95% range and ranks in the top 2 of the placebo set plus itself.
3. **Controls agree:** the Portugal and 351 versions agree in sign and differ by less than two combined standard errors.
4. **Consistency:** E0's reduced form has the same sign and a size within two standard errors of 0.25 × the 352 effect.
5. **Heat:** dropping 11–18 June leaves the sign unchanged.
6. **Within-day:** the triple difference has the sign the price predicts (a dearer night relative to midday lowers night load
   relative to midday), and the 2021 same-date window (15 June 2021 ± the same days) shows nothing larger than its placebo sd.
7. **Symmetry:** the 2023 charge withdrawal moves the same series the opposite way, within a factor of two. Reported; failure of
   this rule alone does not kill (weaker event), failure of 1–6 does.

Verdict: stop unless 1–6 all pass. If they pass, the elasticity is reported with the scaling by exposure, the 25% E0 share, and
the statement that it is a short-run response of regulated households to a known step in their hourly price.

## 4. Verdicts

- **Tax steps S1–S4: kill.** One door (the 10 kW threshold) needs load by contracted power that does not exist here.
- **Gas cap as a demand event: not killed, but doubtful.** The premise in the brief (a price fall largest in the evening) fails
  on the first look; the event is a net rise with a within-day shape change at night. It is worth a cheap Step 1–2 because it is
  the one remaining setting where the date and the instrument (Y) do not come from Spanish demand. The probable outcome, given
  352's noise and the near-zero prior from the hourly design, is a power failure at Step 2.
- **Authorship:** unlike the tax and time-of-use work, this does not replicate the paper's own policy.

## 5. Asked of the user

Go-ahead for **Step 1 only** (price gates, descriptive, no demand series), then a second go-ahead for Step 2 after its result.
New scripts would be `scripts/analysis/gascap_demand_price_gates.py` and `gascap_demand_power.py`, reusing `tou_did.build()`
(`src='352'` and a new `'351'` source) and `tou_lasso_paper.py`.

## 6. Step 1 results (2026-11-12, user's go-ahead; `scripts/analysis/gascap_demand_price_gates.py` → `outputs/tables/gascap_demand_gates*.csv`)

Window 28 days before, 14 after 2022-06-15; 24 placebo windows. Δ ln PVPC energy term (ESIOS 1001), post minus pre.

| gate | result | rule | verdict |
|---|---|---|---|
| G0 1001 contains 1909 | coefficient 0.86 (se 0.09) on hourly changes, 1.18 (0.03) in levels | 0.8–1.2 | **pass** |
| G1 net level | +0.163 | ≥ 0.10 and above placebo 95th pct of \|Δ\| (0.458) | **fail**: the placebo windows (autumn 2021 to winter 2023) move as much or more |
| G2 evening − midday | +0.006 | ≥ 0.10 and above p95 (0.230) | **fail, component dropped** |
| G2 night − midday | +0.290 | same | **pass** (placebo sd 0.136) |
| G3 first stage, post × Y | F 73 (243-day cap period plus pre-cap months, weekday effects, trend) | ≥ 10 | **pass** |
| G4 switching | 352 share of 352 + 351: 7.92% → 8.08% (+2.1%) | no fall over 3% | **pass** |

Reading: the cap's net price jump is not unusual for a two-week window in this volatile period (G1), and the evening-versus-midday
component has no price variation (G2). What survives is the **night-versus-midday relative price** (+29 log points, outside the
placebo range). G1's rule had no stated consequence; I treat the level component as not testable on price grounds, as with G2.
The scaling for Step 2: implied effect on the night − midday contrast = −0.10 × 0.29 ≈ −2.9%. G1 is not blind (section 3.0).

## 7. Step 2 results (2026-11-12, user's go-ahead; `scripts/analysis/gascap_demand_power.py` → `outputs/tables/gascap_demand_power*.csv`; real window not computed)

DiD of ln(series) − ln(control) on post × block (night, midday, evening), hour and weekday effects, temperature and holiday
differences, clustered by day, at 26 placebo breaks (Step 1 reported 24; two windows had too few days for its price filter but
not for this one). MDE = 2.8 × placebo sd of the **night − midday** contrast. Implied effect of elasticity −0.10 on a +29 log-point
relative price: −2.9%; of −0.5: −14.5%.

| series | control | placebo sd | MDE | P1 (MDE ≤ 1.45%) | P2 (MDE ≤ 14.5%) |
|---|---|---|---|---|---|
| **352 (primary)** | Portugal | 4.1% | **11.4%** | fail | pass |
| 352 | 351 | 4.1% | 11.5% | fail | pass |
| E0 (measured) | Portugal | 2.5% | 7.1% | fail | pass |
| 351, 353, industry (**added after the user's question, not in the spec**) | Portugal | 2.1%, 5.3%, 1.6% | 5.8%, 14.9%, 4.5% | fail | pass, fail (353), pass |

**Verdict under the pre-set rules: P1 fails, P2 passes narrowly for 352 (MDE 11.4% against 14.5%), so the real date may be run
only as a bound.** The bound would say "elasticity above about −0.4", which is no tighter than the literature's −0.1 to −0.4 and
already implied by the hourly design's ceiling. The design cannot separate −0.1 from zero (needs an effect of 11%, against an
implied 3%). **Recommendation: kill** as an estimate; running the real date adds only a weak bound. Level contrast placebo sds
are larger (352: 7.9%), so the level component is hopeless too.
