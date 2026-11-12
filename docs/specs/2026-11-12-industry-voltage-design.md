# Did demand respond to the 2021 tariff reform by voltage level? (cross-tariff dose-response)

**Status: pre-registered 2026-11-12, written before any code or run.** Branch `tou-policy-prices`. Follows the household replication (`2026-11-11-tou-hardening-design.md`) and the legal sources (`docs/tou-policy-sources.md`, schedule module `analysis/tou_tariff_schedule.py`).

**In one example.** On 1 June 2021 every access tariff moved to new prices by hour, on the same date and in the same season, but by very different amounts. In a July evening a 3.0TD customer's toll rose from about €13 to €77/MWh while night stayed near €5; a 6.4TD customer's evening toll rose from about €7 to €13 and the night price barely moved. On an energy price of about €100 that is a change of +0.40 in the log relative price of evening against night for 3.0 and +0.06 for 6.4. If demand responds to that price, the evening response at 3.0 should be several times the response at 6.4, in the same weeks, with the same weather and the same economy. That cross-section does not need the season to be held constant, which the charge-over-time tests could not do.

**Question.** Does measured demand at each voltage level (E0 to E6) respond to the reform-induced hourly price change, and does the response scale with the dose across levels? **Not goals:** a household elasticity (done), welfare, anything after 2021-09-15 (the cargos cut of RDL 17/2021 changed every tariff's charges on 16 September 2021 and the post-cut charges for segments 2–6 were not read).

## Data
| need | on disk |
|---|---|
| Spain, hourly measured demand by voltage level | ESIOS 1201 (E0 < 1 kV), 1202 (E1 1–14 kV), 1203 (E2 14–36 kV), 1204 (E3 36–72.5 kV), 1205 (E4 72.5–145 kV), 1206 (E5 145–220 kV), 1207 (E6 ≥ 220 kV), peninsular |
| Controls | Portugal total consumption (REN, includes Portuguese industry), France (RTE `consommation`) |
| Old and new hourly toll prices, periods | `tou_tariff_schedule.py`, `outputs/tables/tou_tariff_prices_2021.csv`, `docs/tou-policy-sources.md` |
| Energy price base | OMIE day-ahead Spanish price (`data/omie/prices`), mean over the post window |
| Weather, holidays | temperature index (ES, PT), holiday table |

**Tariff mapping, by voltage level (dose, July working days, change in ln relative price evening 18–22h against night 0–8h, energy base €100):** E0 mixes 2.0TD households (+0.61) and 3.0TD (+0.40); E1 mixes 3.1A→6.1TD (+0.34) and 6.1A→6.1TD (+0.22); E2 (14–36 kV) the same plus 6.1B→6.2 at the 30 kV boundary; **E3 = 6.2 (+0.12), E4 = 6.3 (+0.09), E5 and E6 = 6.4 (+0.06)**, single tariffs. For mixed series two regressions are run, one for each tariff in the mix, and the result is reported as a bracket (the tariff mix inside a series is not published).

## Design
- **Window.** Pre: 2018-01-01 → 2020-12-31 without March–June 2020 (the COVID months); January–May 2021 out. Post: **2021-06-01 → 2021-09-15** (the paper's window; after 16 September the charges of every tariff changed). Control: Portugal (primary), France.
- **First step: the paper's LASSO** (`tou_lasso_paper.py`): one model per area and hour, calendar and temperature interactions, 10-fold cross-validation with the one-standard-error rule, no trend, trained on the pre-window; prediction errors of log load for Spain's series and the control.
- **Dose regressor.** For every post-window date and hour, Δp = ln[(E + T_new(period, tariff)) / (E + T_old(period, tariff))], with E the post-window mean OMIE price, T_old from the old regime and T_new from the new one (the schedule module); zero before June 2021 and for the control. Sensitivities: E = €60 and E = the hour's own OMIE price.
- **Estimating equation (the paper's Equation 4, policy-induced price as regressor):** error(i,h,t) = η_k · Δp(h,t) · 1[Spain series k] + hour × weekend × area effects + hour × weekend × month-of-sample effects + weekend × area × month-of-sample effects (the paper's Table 6, column 4 set), clustered by area × month-of-sample; weekly clusters beside. Because Δp is set by the regulator, the regressor needs no instrument; η_k is the elasticity of series k's demand to the reform-induced price change. A reduced-form version (Spain series k × post) is reported beside.
- **Placebo:** the same regression for 2019 (post 2019-06-01 → 2019-09-15) with the real dose pattern laid on that calendar and errors cross-fitted (leave-year-out, as in the events test).
- **Pooled test:** stack the readable series with series-specific η_k, clustered by calendar week (series share the control), and test equality of the η_k (Wald).

## Stop rules, set before any run
1. **Readability.** A series is read only if the within-day standard deviation of its Δp over the post window is at least 0.02 (ln points). Series below it (likely E5 and E6) are reported as not readable, not as failures.
2. **Household anchor.** For E0, η is negative with t ≤ −2 and between −0.25 and −0.03, with either tariff of its mix (the household column-4 elasticity was −0.100).
3. **Placebo.** For each readable series the 2019 placebo η has t > −2 (not significantly negative) and the real η lies below it.
4. **Industry responds.** For at least one single-tariff series (E3, E4, E5 or E6, whichever are readable), η is negative with t ≤ −2. If every single-tariff series has |t| < 2, the conclusion is "no detectable industrial response", reported with the 95% bound on η, not as a failure of the design.
5. **Common elasticity.** The Wald test of equal η_k across readable series is not rejected at 5%. If rejected, the elasticities are reported by series and the response is read as heterogeneous (flexibility differs by customer type).
6. **Dose ordering.** The reduced-form effect on the evening-versus-night contrast is ordered like the dose across the readable series: Spearman rank correlation of at least 0.7 (with at least five series, counting bracketed series at their midpoint).
7. **Controls agree.** With France as control, every readable series has the same sign of η as with Portugal.

## What each outcome means
All pass: demand at every readable level responds to the reform-induced price in proportion, with one elasticity; the thesis reports it by customer type. Rule 5 fails with 4 passing: industry responds but less or more than proportional to the dose (flexibility, contract type); the elasticities are the result. Rule 4 fails: industry did not respond measurably; reported with the bound. Rules 2 or 3 fail: the design does not identify; stop.

## Threats and limits
(a) **Flexibility and dose both fall with voltage.** A response that falls with voltage is also what rigid large processes produce with no price response; the proportionality test (rule 5) and the placebo are the guard, not a proof. (b) The tariff mix inside E0, E1 and E2 is unobserved; the bracket is the honest answer. (c) Many industrial contracts are fixed-price per period, so the effective dose may be smaller than computed (energy-price base only), and contract exposure is not measured. (d) Portugal's total includes its industry, which has its own 2021 recovery; France is the second control; Spain's industrial recovery from COVID in 2021 differs by sector and the 2018–2020 LASSO cannot know it; the placebo year is the only guard. (e) The old-regime hours were read from the consolidated Orden ITC/2794/2007 and assumed unchanged to May 2021; the 2019 and 2020 toll orders were not read. (f) August 2021 is in the post window: it was off-peak all month in the old regime and a medium-season month in the new one, which the dose already encodes. (g) The measured demand series are by voltage of connection, so they include self-generation effects and non-industrial users (services, transport) at each level. (h) Seven series, one reform, one summer.

## Amendment 2026-11-12, before any code or run: use tariff series and measured mix weights

Found after the registration while answering whether the tariff mix inside E0, E1 and E2 can be separated. ESIOS publishes measured demand **by access tariff** as well as by voltage level, and the high-voltage tariff series run for the whole window: **1369 (6.1A, 1–30 kV), 1216 (6.2, 30–72.5 kV), 1217 (6.3, 72.5–145 kV), 1218 (6.4, ≥145 kV)**, 2017-12-31 → 2026-04. The low-voltage tariff series (1209 for 2.0TD, 2532 for 3.0TD, 2531 for the EV tariff) start only in mid-2024.

**Checks (June–September 2021, TWh; computed from the files on disk):**
- **E4 equals the 6.3 series (ratio 1.000) and E5 + E6 equals the 6.4 series (1.000)**: E5 (145–220 kV) is empty and E6 is the whole of 6.4. So E4 and E6 are clean single-tariff series.
- **E3 is 0.78 of the 6.2 series** (6.2 starts at 30 kV, E3 at 36 kV); the 30–36 kV part sits in E2. The tariff series 1216 is the right outcome for 6.2.
- **E1 + E2 over the 6.1A series is 1.39 in 2018–2020 and 1.08 from 2022.** Before June 2021 the 6.1A series excluded the old 3.1A tariff; the new 6.1TD includes it. That break identifies the mix inside E1 + E2 before the reform: **about 72% 6.1A, 20% 3.1A and 7% 6.1B** (solved from the 1.385 and 1.08 ratios; approximate).
- **E0 mix (2.0TD against 3.0TD), from 2024-07 → 2026-03, the first months both series exist:** **69% 2.0TD, 31% 3.0TD, EV tariff 0.1%.** Taken as a proxy for 2021 (assumes the mix was stable).

**Changes to the design (nothing was run):**
1. **Outcomes (five series):** E0; E1 + E2 combined (voltage series, mixed); **tariff series 1216 (6.2), 1217 (6.3) and 1218 (6.4)** in place of E3, E4 and E5/E6. E6 is not a separate series (it is 6.4).
2. **Dose for mixed series = the weighted average of the tariffs' hourly Δp** with the measured weights above: E0 = 0.69 × Δp(2.0TD) + 0.31 × Δp(3.0TD) (July evening-against-night dose about +0.55); E1 + E2 = 0.20 × Δp(3.1A→6.1TD) + 0.79 × Δp(6.1A/6.1B→6.1TD or 6.2TD) (about +0.24). The earlier bracket (each pure tariff in turn) is kept as a sensitivity, plus ±10 points on the weights.
3. **Rules 1 to 7 stand**, with "series" meaning these five (rule 6 needs at least five, so none can drop out of rule 6 except by failing rule 1).

**What the weights do not fix.** They put a number on the mix, not on the customers' flexibility within it: a 3.0TD customer and a 2.0TD household differ in how they respond, and the weights are shares of energy, not of the price-responsive load. The 2.0TD/3.0TD weights are from 2024–26 and the 3.1A weights from the break in a series definition; both are approximations, so the bracket is the honest range and the weighted dose is the central case.
