# What we know about business demand, and what the data does not identify

**Status: synthesis of committed results, written 2026-11-16 (route R2). No new estimate. Every number below is in the spec or output named in its row; nothing here is re-run.** Elasticities are of load to price (negative = load falls when price rises) unless a row says 'stated'.

## The evidence, by what each design measures

| # | Design (margin) | Estimate | 95% interval | Validity verdict | Source |
|---|---|---|---|---|---|
| 1 | Reform-dose DiD with per-hour LASSO, E1+E2 (6.1TD, month-scale reform response), placebo-adjusted | -0.082 | [-0.252, +0.088] | passes the placebo guard; **not detected** | `2026-11-16-industry-adjusted-design.md` |
| 2 | Same, pooled industry IND (E1-E6) | -0.265 | [-0.408, -0.122] | **fails the guard** (2018 placebo -0.069, 2019 placebo +0.023); no point estimate reported | same |
| 3 | Same, 6.2 / 6.3 / 6.4 | -0.013 / -0.477 / -1.384 | very wide | placebos as large as the estimates; noise | same |
| 4 | Group comparison, gap against households (-0.10) | E1+E2 -0.068; IND -0.187 | detectable gap 0.158 / 0.189 (season-matched) | **uninformative**: detectable gap above the household elasticity | `2026-11-17-group-comparison-design.md` |
| 5 | Noise check: detectable elasticity of substitution | E1+E2 0.32; 6.2 0.54; 6.3 0.57; 6.4 0.88 | | **infeasible** for a household-sized response (dose 0.04-0.16 against household 0.64) | `2026-11-13-industry-noise-check.md` |
| 6 | Spot-price IV, hourly impact margin, forecast instruments (V3) | +0.005 | [-0.005, +0.023] | placebo outcome fails (-0.022, p 0.002); years unstable | `2026-11-17-industry-iv-estimation-design.md` |
| 7 | Spot-price IV, forecast error | (stopped) | | first stage F 6.95 | `...forecast-error-design.md` |
| 8 | Spot-price IV, **bid-curve instrument** | -0.036 | [-0.080, +0.010] | placebo and balance pass; t-rank p 0.010 against AR p 0.178; B3 (raw pass-through 0.13) fails | `...bid-curve-design.md` |
| 9 | Same, one weight-fixed instrument, original weekday sample | -0.031 | [-0.055, +0.006] | placebo clean; both-tests rule not met | `...power-design.md` |
| 10 | Same, extended 2019-2025 all days | +0.017 | [-0.063, +0.175] | detectable 0.091; 2024-25 heterogeneity widens the interval | same |
| 11 | Calendar boundaries, Barcelona services, month-scale | -0.004 | [-0.080, +0.071] | E1-E5 fail; Portugal control gives -0.143 | `2026-11-17-calendar-boundary-design.md` |
| 12 | **Stated bid-curve elasticity** of direct consumers (arc, absolute value), process industry | 0.36 (2019-21H1), 0.34 (2021H2-22), 0.06 (2023-26) | not an inference object | movement along a fixed curve; curve shift (E3) stopped: **91% of extra auction purchases offset elsewhere** | `notes/rq-direct-consumers.md` |

Literature read this session: Jessoe and Rapson (2015): mandatory TOU for commercial and industrial firms, no or very little change in usage or load (aggregate decreases above 1% ruled out); Blonz (2022): critical-peak pricing, small businesses reduce peak use by 13.5% (elasticity -0.119) at about tripled prices; Hausman and Rapson (2018): practitioners' guide to regression discontinuity in time. Von Graevenitz and co-authors (German manufacturing, own-price elasticity -0.4 to -0.6 from network-charge variation) is cited from `notes/idea-calendar-boundary-business-tariffs.md` and was not re-read here.

## What is identified, and what is not

1. **No business elasticity is identified as a point estimate** under every validity check we set. The reform-dose designs fail on dose-to-noise (rows 1-5); the spot-price IV passes the placebo only with the bid-curve instrument and then fails the two-test detection rule (rows 8-9); the calendar design fails and is sensitive to the control (row 11).
2. **What the data does support is a bound on realised load response.** The impact (same-hour) response to the day-ahead price is small: the preferred design gives -0.03 [-0.055, +0.006] on 2019-2023 weekdays; the month-scale calendar response is -0.004 [-0.080, +0.071]. Both rule out business responses of the size Blonz finds for critical-peak pricing (-0.12) at the 95% level. Two independent margins give a consistent picture: business load barely moves with the price in the hour or the month.
3. **The reform-evening shift in industry is about the same in percent as in households and is not proportional to the dose.** The adjusted reduced form (evening against night, working against weekend) is -4.4% for E0 households, -4.1% for E1+E2 and -3.1% for IND, at doses 0.64, 0.16 and 0.12. This is descriptive (rows 1-2): either industrial flexibility per unit of price is several times larger, or something other than the price moved industry in 2021. It cannot be separated with these data.
4. **Stated flexibility is not realised flexibility.** The stated curves of large buyers give 0.14-0.36 in 2019-2022 (row 12), several times the realised-load bound. The curve-shift test shows why: the extra day-ahead purchases on windy days are bought back through intraday or bilateral purchases (91% offset), so the auction demand curve overstates how much real consumption moves.

## The link to the supply side
The day-ahead demand curve the supply side faces has price-responsive industrial steps that are stated but not realised in consumption. For market-power analysis this matters: the residual-demand elasticity a generator faces (the Lerner-index denominator) depends on whether those steps move quantity. A realised elasticity near zero with a stated elasticity of 0.2-0.4 says the auction's residual demand is more elastic than the economy's; a markup computed from the stated curve would be lower than one computed from realised load response. (Implication only; no markup estimate is made here.)

## What it does not say
It does not say business demand is inelastic in the long run, or at higher doses (the reform doses are 0.04-0.16 and the calendar doses 0.15-0.34 in Barcelona); all designs are short-run, one price margin at a time. It does not use Portuguese business data (only REN's national load); and the Barcelona result is one city, services only, with the dose approximated at 2021 tolls and charges.

## Methodology, honestly stated
This note is a synthesis; it has no estimator of its own. The paper's method (per-hour LASSO prediction errors, triple difference, Wald ratio) is used directly only in rows 1-5. Rows 6-10 use instruments and double machine learning; row 11 uses year-over-year differencing, because month dummies in a LASSO would absorb the season steps; row 12 uses the market's own bids. The randomization inference (many shifted windows, rank p-values, Fisher intervals) is common to most rows and is ours.

## Unit-panel check (2026-11-16, descriptive, no estimate): would direct-consumer units reduce the noise?
Panel `outputs/tables/direct_consumer_panel/` (OMIE unit-hours, 2018-01 to 2026-05; registry of 473 units, 76 classified process industry). **Process-industry units active at least 180 days in a year: 21-32 (2018-2025), 22 in 2023, 21 in 2025; the top 5 carry 71-84% of volume (64% in 2026); total purchases about 1.0 TWh a year in 2019, 1.96 in 2021, 0.59 in 2023, 0.45 in 2025.** Noise, sd of the log of daily purchases within month x weekday, 2019-2023: **single unit 0.40; sum of the process units 0.139** (an effective number of independent units of about 8, because of concentration); national series for comparison: **E1+E2 0.086, 6.4TD 0.067**. The unit panel is **noisier than the national aggregate** and shrinking, and purchases move between procurement channels (the 91% offset), so it does not solve the noise problem; its value is the stated bid curve (row 12), not more power for realised load.

## Update 2026-11-17: instrument settlement, wind-speed IV, planted-effect test, exposed subgroups
Every number is in the spec or output named; elasticities are of load (or purchases) to the day-ahead price, same-hour, week-on-week differences, double ML, randomization intervals.

| # | Design | Estimate | 95% interval | Validity verdict | Source |
|---|---|---|---|---|---|
| 13 | **Wind-speed IV (C1), industrial load E3-E6, 2019-23 weekdays** (first stage F 93) | **+0.0001** | **[-0.021, +0.028]** | placebo, overidentification and variant agreement pass; **not detected**; years differ (2019-21H1 +0.038 [-0.013, +0.107], 2021H2-23 -0.014 [-0.029, +0.009]); regimes weighted about 30/72 | `2026-11-17-industry-iv-wind-speed-estimation-design.md`, `...planted-effect-design.md` |
| 14 | Planted-effect test of that pipeline | recovers planted -0.03, -0.05, -0.10 pooled | -0.03 detected, -0.02 not | detectable elasticity about -0.03; a response in one regime is partly averaged out (P3 fails) | `...planted-effect-design.md` |
| 15 | Exposed group with C1: ESIOS 353 direct consumers (12.7% of E3-E6) | -0.033 | [-0.116, +0.017] | informative (planted -0.3 recovered, placebo clean); **not detected**; purchase response, an upper bound on consumption response | `...exposed-subgroup-design.md` |
| 16 | Process-industry units (76) / refinery units (4, own generation) | -0.007 / -0.069 | [-0.091, +0.118] / [-0.157, +0.064] | informative at -0.3; **not detected** | same |

**Status of the earlier bid-curve estimate (row 8): -0.036 [-0.080, +0.010]. Kept as the researcher's preferred earlier estimate, with the following recorded beside it, not instead of it.** The interval contains zero; its randomization t-rank p was 0.010 against an Anderson-Rubin p of 0.178; its pass-through check (B3, raw 0.13) failed; and in the instrument settlement (`2026-11-17-industry-iv-instrument-settlement-design.md`, `...bid-instrument-second-settlement-design.md`) the offer-curve instrument family fails the idle-wind zero-first-stage test (idle-hour first stage about 1.6 times the full-sample one) and the 2019-21H1 placebo (B1 p 0.008, B2 0.023, X1 0.015; B0 0.073). A diagnostic (`...placebo-diagnostic-design.md`) located the placebo failure in the wind forecast-miss component, concentrated in winter and in 2021H1, with no named driver. **It is therefore not an identified negative estimate**; it is the earlier result of an instrument that did not pass the validity checks registered afterwards.

**Instrument record.** Nine instrument sets were scored (C0-C4, B0-B2, X1) after the placebo flaw in the first settlement was found and fixed (recorded in its Results section); one passes (C1, realised wind speed, following Hirth, Khanna and Ruhnau 2024). No further candidates.

**What the update changes in the sections above.**
1. **Identified or not.** Still no business elasticity identified as a negative point estimate. The wind-speed IV gives a bounded null: an aggregate industrial same-hour response more negative than about -0.02 is excluded; for exposed groups, more negative than about -0.12 (direct consumers) to -0.16 (refineries). The design would have detected -0.03 (aggregate planted test) and -0.1 (direct consumers).
2. **Not said.** This is not a statement that firms are inelastic: responses to sustained price levels, multi-day substitution and consumption (as opposed to purchases) are not tested, and the regimes are weighted about 72% on 2021H2-23.
3. **Literature read for this update (abstracts and summaries only, except Hirth et al.):** Hirth, Khanna and Ruhnau (2024, full text in `papers/`: first stage F 930, 38,448 hours, zero-first-stage test); Herter et al. (18% of customers give 75% of the response); Schwarz et al. and the ERCOT study (response from self-generators and batch processes). Full-text reading of Patrick and Wolak (NBER 8213) and von Graevenitz and Rottner remains to do.
