# Direct consumers: how large buyers respond to the day-ahead price (running note)

Data: `data/omie/registry/direct_consumers.parquet`, `outputs/tables/direct_consumer_panel/` (CLAUDE.md, "Direct market
consumers"). Branch `industrial-demand`.

## Design (2026-11-09, proposed; nothing estimated yet)

Drafted as three independent designs (wind-forecast IV; stated-curve decomposition; price shocks and regime changes)
and refereed against this repo's past failures. The referee's plan is adopted below.

### The point the design turns on
A direct consumer's bid curve is observed. Its realised purchase is that curve evaluated at the price, so a change in
purchases splits exactly into
- **E2, movement along a fixed curve**: read off the stated curve, no estimation needed;
- **E3, the curve shifting**: the consumer re-bidding because it expects a different price. This is the only
  behavioural parameter, and the only part that needs an instrument.

A 2SLS of cleared quantity on price (E1 = E2 + E3) adds nothing beyond the two and gives a noisier E3.

### What the drafts measured (quick descriptives, own + represented, refineries out)
- First stage of the daily price on the D-1 wind forecast (ESIOS 1777): −2.0 €/MWh per GW in 2019–21H1, −6.8 in
  2021H2–23, −5.6 in 2024–26; F 100–430 by period. Strong.
- Most quantity variation is production scheduling: within unit × month × weekday, the sd of log daily q is 0.44–0.53.
- Before 2021 realised variation is mostly movement along the curves (curve level explains 10–48% of within-month
  variance in 2018–2020); from 2022 almost all of it is the curve level (89–108%).
- Concentration: the top 5 units carry 37–69% of cleared volume (Celsa, El Corte Inglés, Ence, Zaragoza council,
  Extremadura health service). Only 36 units are active > 180 days in every year 2019–2024.
- Load moves between procurement channels: Celsa's offered MW went ~20 → 106 → 2 between 2021 and 2025.

### Rejected
- **Any event study (crisis, gas cap, 2021-07-07 limit change) as a source of an elasticity.** Gas is an input for
  these industries; units exit and switch channels; buyers paid the gas-cap adjustment charge (ESIOS 10403: €27/MWh in
  June 2022, €67 in July), which offsets the cap; the limit change is a rule change. No untreated control exists
  (ESIOS E1–E6 contains these consumers; Italy and GB failed for the gas cap).
- **Gas price and outages as instruments.** Gas is a feedstock and cogeneration fuel; most outages are declared after
  bids close (F ≈ 10).
- **A forecast-error placebo.** Bids and the price are fixed before the error is known, so it cannot fail
  (`rq-intraday-surprise.md`).
- **The curve's position measured relative to p\*** (q at p ± 10): a fixed curve read at a lower p shows more MW, so
  it confounds E2 with E3 (the price-taking simulation lesson, `rq-price-taking-simulation.md`).

### Steps (each needs a go-ahead)

**Step 0, build, no estimation.**
1. Each unit-hour's curve at absolute prices (€20 / 50 / 80 / 120 / 180.30) from `curva_pbc_uof` O rows, with a flag
   for bids at the ceiling.
2. Total purchases: PDBF across all role codes (role 4 ≈ 21% of direct consumers' schedule in June 2023; codes 6/7
   to decode first) plus net intraday purchases from `curva_pibc_uof`. A day-ahead drop bought back intraday is not a
   demand response.
3. Own generation: match each consumer to sell-side units its group owns, cogeneration included (the registry's
   ≥ 50 MW flag catches only Repsol and Bon Preu). Net purchases = buys − own sales.
4. Samples: **process industry** (steel, paper, chemicals, food, glass, ceramics, metals) as the main sample;
   weather-exposed loads (retail, councils, health, irrigation, transport) as a comparison group; refineries and
   ceiling bidders reported apart.

Step 0 done 2026-11-09: items 1, 2 and 4 in the panel; item 3 as `own_gen_group` and `own_gen/` (CLAUDE.md,
"Own generation"). Own generation matters for Ence, Repsol and Sniace only.

**Step 1, E2, the stated elasticity (descriptive, the core deliverable).** Per regime (2019–21H1, 2021H2–22,
2023–26), evaluate each unit's stated curve at p\* ± the first-stage price change (wind-forecast sd × first-stage
coefficient), weighted by quantity. Report with the top-5 share and a balanced panel.

**Step 2, E3, the curve shift, reduced form, 2019–21H1 only.** Outcomes: quantity at fixed absolute prices, offered
quantity in levels (zeros kept), total purchases. Regressor: D-1 wind forecast. Controls: demand forecast,
temperature, HDH/CDH, regional holidays, weekday, unit × year-month FE; clustered by week.

Gates, fixed before anything is read:
- **G1** first-stage F ≥ 50 in the regime (met).
- **G2 weather**: the unit's provincial wind (ESIOS 1159) net of the national forecast moves local weather but not the
  price, so its coefficient on process-industry offered quantity must have |t| < 2 and be below one third of the main
  reduced form. The weather-exposed group must not respond more than process industry. Leads and lags: the D+7
  forecast and the D−7 realisation must not move q_D.
- **G3 power**: 2.8 · se(E3) < |E2| in the regime, else E3 is reported as an interval only.
- **G4**: the sign of E3 survives dropping each of the top 5 units.
- **G5 channels**: if ≥ 50% of the auction response is offset in total purchases, it is re-routing, not demand
  response.

Stop rules: G2 fails → stop E3; the result is E2 plus the descriptives. G3 fails → E2 is the realised elasticity, E3
an interval.

**Step 3, only if step 2 passes:** 2021H2–22. For 2023–26 a bound only: the curves are vertical, yet offered quantity
moves with the wind forecast (t 5.5) for reasons G2 must attribute first. No 2018 (ESIOS forecasts start 2019) unless
the ENTSO-E forecast arrives and matches 1777.

## Step 1 result: E2, the stated elasticity (2026-11-10)

`analysis/direct_consumer_stated_elasticity.py` → `outputs/tables/direct_consumer_stated_elasticity.csv`. Each unit-hour's
offered curve held fixed and read at p* ± dp, dp = the price move from one sd of the D-1 wind forecast (first stage on
daily prices, year-month and weekday FE, demand-forecast control): **€5.7 in 2019–21H1 (β −1.96/GW, F 501), €19.4 in
2021H2–22 (−6.51, F 177), €18.1 in 2023–26 (−5.37, F 1,471)**. Own + represented units, weighted by demand at the price.

| regime | all | process | weather-exposed | without top 5 | process, balanced (12 units) |
|---|---|---|---|---|---|
| 2019–21H1 | 0.14 | 0.36 | 0.18 | 0.19 | 0.42 |
| 2021H2–22 | 0.35 | 0.34 | 0.74 | 0.38 | 0.43 |
| 2023–26 | 0.03 | 0.06 | 0.16 | 0.02 | 0.02 |

Arc elasticity of the stated curve (absolute value). Refineries are 0 throughout (they bid at the ceiling). The top 5
units carry 67–80% of the weight. Share of units with any stated response (> 0.5% of demand per dp): 61% → 96% → 15%.
Between the offsets at ±10 and ±50 the curve is interpolated linearly, so the €18–19 figures are approximate.

Reading: in 2019–2022 a process-industry buyer's stated curve gives up about 0.35–0.43% of its demand per 1% rise in
the price; from 2023 almost none, because the curves went vertical. This is movement along a fixed curve only; how
much the curves themselves shift with the expected price (E3) is step 2.

## Step 2 result: E3, the curve shift — STOP at G2 (2026-11-10)

`analysis/direct_consumer_curve_shift.py` → `outputs/tables/direct_consumer_curve_shift.csv`. Unit-day panel,
2019-01 → 2021-06, process sample (43 units), unit × year-month and weekday FE, demand forecast, temperature, HDH/CDH,
holiday share; SE clustered by week. Regressor: D-1 wind forecast (GW).

Main outcome q_a50 (MW bid at ≥ €50): b = −0.017 MW per GW (t −2.6), an elasticity of **+0.10 (se 0.04): the wrong
sign for a demand response** — buyers bid for *less* when wind is forecast to lower the price.

| gate | result | |
|---|---|---|
| G1 first stage | F 501 | pass |
| G2a weather-exposed vs process | 0.108 vs 0.101 (unclassified 0.095) | **fail**: every group moves alike |
| G2b D+7 forecast placebo | t −0.44 | pass |
| G2b D−7 realised wind placebo | t +2.84 | **fail** |
| G2c provincial wind | not run: the registry holds no consumer locations | — |
| G3 power | 2.8 se = 0.11 < 0.36 | pass |
| G4 drop each top-5 unit | sign holds; dropping all five: b −0.0007 (t −0.3) | pass, but it is Ence's ENERC03 |
| G5 channels | auction purchases +0.030 MW/GW (t 3.2, the E2 movement), total purchases +0.003 | **fail**: 91% offset |

Reading: the curve's position co-moves with wind for weather/seasonal reasons common to all buyers (last week's wind
predicts it as well), not with the expected price, and it rests on five units. The extra day-ahead purchases on windy
days are bought back elsewhere (intraday, bilateral), so they are re-routing, not extra consumption.

**Stop rule applies: no E3.** The result of this design is E2 (step 1) plus the descriptives. Step 3 is not run.
