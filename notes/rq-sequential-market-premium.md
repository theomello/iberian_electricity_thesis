# The day-ahead / intraday premium: Ito & Reguant (2016) on 2018–2026

Written 2026-08-21. `scripts/analysis/sequential_market_premium.py`.

**This is the first design in this repo to produce a robust, correctly signed
result.** It is also the first that needs no marginal cost.

---

## 1. Why this design

Six conduct tests failed on the same thing — the marginal-cost measure — and
wiring in `cab`'s declared minimum-income condition (cross-validated at 0.87 in
logs against independent engineering data) did not rescue any of them. See
[`min-income-condition.md`](min-income-condition.md).

Ito & Reguant (2016, *AER* 106(7): 1921–57) study this exact market and use **no
marginal cost at all**. Their object is the price premium between the forward
(day-ahead) and spot (intraday) markets.

## 2. The design, formally

For delivery period `t`, intraday session `s`:

```
π_ts = p^DA_t − p^ID_ts
```

Under risk-neutral, unconstrained arbitrage, `E[π] = 0`. Firm `i` solving

```
max  p^F q^F + p^S q^S − C(q^F + q^S)
```

has forward-market first-order condition

```
p^F − C′(q) = − q^F_i / RD^F′_i(p^F),    RD^F_i(p) = D(p) − Σ_{j≠i} S_j(p) − A(p)
```

Arbitrage supply `A(p)`, with `A′(p) < 0`, enters residual demand additively, so
`|RD^F′_i| = |D′| + Σ|S′_j| + |A′|`. More arbitrage capacity means a flatter
markup term:

```
∂π / ∂|A′| < 0
```

If arbitrageurs are capacity-constrained, `π > 0` survives. **Wind is the
arbitrageur** in their account. Wind and solar went 23.9% → 41.8% of generation
over this window — after their sample — so `|A′|` grew several-fold. That is the
testable extension.

Estimating equation, hour-of-day and year-month fixed effects, clustered on
month:

```
π_ts = β·VRE_t + γ·log D_t + α_h + τ_m + ε_ts      prediction β < 0
```

## 3. Measurement: the published prices were necessary

The intraday clearing price was first **derived** from the bid archive, since in
a uniform-price auction `max(cleared sell) ≤ p* ≤ min(cleared buy)`. That is not
good enough here — see the estimator table in CLAUDE.md. Against the published
files the derived price is off by median 0.000 but **p95 4.26 and mean +0.62
€/MWh**, on an object worth about 1 €/MWh.

Worse, `max(cleared sell)` is a *lower* bound whose error cannot be positive, and
it was positive on 10% of rows. The cause: **the intraday market splits
independently of the day-ahead market** — ES and PT intraday prices differ on
8.4% of periods against the day-ahead's 5.6% — and the bid archive tags nearly
every unit `MI` rather than by zone, so pooling both zones in a split period
picks up the wrong price. Filtering on day-ahead splitting, as the first cut did,
does not remove this.

`fetch_omie_intraday_prices.py` now fetches OMIE's published `marginalpibc`:
411,263 rows, 2017-12-31 → 2026-08-20. `price_a` is Portugal and `price_b` Spain,
**confirmed from the data**, not assumed from the `marginalpdbc` analogy — on the
30,760 intraday-splitting periods `price_b` sits 6.59 €/MWh from the day-ahead ES
price against `price_a`'s 16.96.

Sample: drop day-ahead splitting, drop intraday splitting, and drop the 9,118
rows where the two markets ran at **different resolutions** (intraday adopted the
15-minute MTU in June 2025, day-ahead on 2025-10-01).

## 4. The premium exists, and it is not a tail

308,840 period-sessions, 2018-01-01 → 2026-05-11.

| | |
|---|---|
| mean | **+0.950 €/MWh** |
| SE clustered on month (95 clusters) | 0.163, **t = +5.84** |
| SE clustered on day (2,853 clusters) | 0.103, t = +9.22 |
| trimmed means | 1%: +0.908, 5%: +0.766, **10%: +0.656** |
| positive / negative / exactly zero | 49.8% / 38.1% / 12.1% |
| positive tail mean / negative tail mean | +5.78 / −5.05 |

About **1.3% of the mean day-ahead price**. It survives 10% trimming, so it is
not a handful of outliers; the asymmetry is genuine, with both more positive
periods than negative and larger ones.

**The median is zero.** This is a skewed distribution with a systematic positive
mean, not a uniform wedge — worth stating plainly, because "there is a premium"
overstates what half the periods look like.

## 5. The mechanism: right sign cross-sectionally, contradicted in the time series

| | β | se | t |
|---|---|---|---|
| VRE share → premium | **−0.0482** | 0.0073 | **−6.62** |
| VRE share → premium, % of day-ahead price | −0.0008 | 0.0002 | −3.60 |
| intraday depth (units trading) → premium | +0.0042 | 0.0016 | +2.65 |

The predicted sign, significant, and robust to the price correction. Within a
month, a 10pp higher VRE share compresses the premium by 0.48 €/MWh against a
mean of 0.95.

**And the time series says the opposite.** Over the window VRE nearly doubled and
intraday participation went **129 → 318 units (2.5×)**, and the premium did not
fall:

| year | units in intraday | mean premium |
|---|---|---|
| 2018 | 129 | +0.470 |
| 2020 | 124 | +0.135 |
| 2022 | 147 | +1.339 |
| 2024 | 200 | +0.617 |
| 2026 | 318 | +0.967 |

Nor did the IDA changeover compress it — the premium is **larger** after it
(pre-IDA +0.869, t = 4.97; IDA +1.517, t = 3.61), with IDA session 3 at +2.48.

**That tension is the finding, not a defect.** Entry more than doubled without
eliminating the premium, which is precisely Ito & Reguant's claim that arbitrage
does not compete it away — but the within-month `β < 0` and the flat secular path
cannot both be the whole story. The candidate reconciliation is that the price
*level* rose over the same period (the gas crisis) and the premium scales with
it; the `% of day-ahead price` specification is a first attempt at netting that
out and keeps the sign.

## 6. What this does not establish

A positive premium is **necessary, not sufficient**, for the market-power
account. Three competitive mechanisms generate one:

1. **Risk premia** — day-ahead sellers paying for certainty.
2. **Forecast errors** — if wind is systematically under-forecast at gate
   closure, intraday supply is systematically higher and its price lower. This is
   the serious one here, because it is *also* correlated with VRE share, and
   would produce `β < 0` with no conduct at all.
3. **Unit commitment** — a started unit's intraday offers are its avoidable cost,
   below its day-ahead offer, mechanically.

Ito & Reguant's identification comes from how the premium varies with
concentration and arbitrage entry, not from its existence. **The concentration
side is not built here.** That is the next step and the machinery exists:
`unit_agents.parquet` gives firm identity, `firm_residual_demand_drought.py`
already computes firm-level residual demand slopes in the day-ahead market, and
the same construction applied to intraday would give the interaction their model
predicts.

Distinguishing (2) from conduct needs a day-ahead wind **forecast** — ESIOS
indicator 541, token required. That is now the binding data gap for this design,
and unlike everything else in this repo it cannot be got token-free.

---

## 7. The concentration side, 2026-08-21

`scripts/analysis/sequential_premium_concentration.py`. Session 1, 71,441
period-days, hour + year-month FE, clustered on month.

### 7.1 Market power: the share measures work, the elasticity measures do not

| measure | β | se | t |
|---|---|---|---|
| **top firm share** | **+8.139** | 2.472 | **+3.29** |
| HHI (mapped firms) | +8.307 | 4.261 | +1.95 |
| 1 / eta (inverse RD elasticity) | −0.014 | 0.019 | −0.74 |
| max firm-level Lerner | −0.017 | 0.051 | −0.34 |

Prediction is β > 0 throughout. **A 10pp higher top-firm share raises the premium
by 0.81 €/MWh, against a mean premium of 0.95** — large, correctly signed, and
significant. That is Ito & Reguant's central comparative static, reproduced.

The two elasticity-scaled measures are null and wrong-signed, and they are built
from the *same* share data divided by `eta`. The likely reason is measurement
error in `eta` itself: it is a band-density estimate over a ±5 €/MWh window
(`residual_demand_slope.py`), and dividing by a noisy denominator attenuates a
signal the numerator carries cleanly. **Do not read the disagreement as evidence
against the mechanism until `eta` is measured better** — but do not read the
share result as structural either, because the share is not the FOC object.

### 7.2 Arbitrage: OLS has the wrong sign, and instrumenting flips it

| | β | se | t | F |
|---|---|---|---|---|
| log intraday units → premium, **OLS** | **+1.672** | 0.490 | +3.42 | — |
| intraday volume → premium, OLS | +0.0019 | 0.0004 | +5.23 | — |
| log intraday units → premium, **2SLS** | **−10.526** | 2.748 | **−3.83** | 16.4 |

This is the clearest result in the file. OLS says more arbitrageurs means a
*larger* premium, which is backwards — and is exactly the reverse causality the
design predicts, since a larger premium is what attracts entry. Instrumenting
participation with weather flips the sign to the predicted negative and it is
strongly significant. First-stage F of 16.4 is above the rule of thumb and not
comfortably so.

The two instrumented market-power measures stay wrong-signed (1/eta −0.238,
t = −1.65; max Lerner −1.199, t = −1.95), consistent with §7.1's measurement-error
reading.

### 7.3 Heat and rainfall: the answer is "rain yes, heat no"

The shocks that failed on markups, now on an outcome that needs no cost measure:

| shock | β | se | t |
|---|---|---|---|
| cooling degree hours (heat) | +0.011 | 0.051 | +0.22 |
| heating degree hours | +0.053 | 0.080 | +0.66 |
| wind speed cubed | **−0.0009** | 0.0004 | **−2.03** |
| 3-day national rainfall | **−0.0199** | 0.0111 | **−1.78** |
| extreme-rain day (top decile in month) | −0.241 | 0.217 | −1.11 |
| reservoir fill anomaly | +5.887 | 4.825 | +1.22 |

**Heat: still nothing, now on a third outcome.** Three designs, three margins,
three nulls. Heat is finished as a shock in this market — it is 1.85% of load and
it does not move markups, withholding, or the premium.

**Rainfall: the first correctly signed rainfall result in this repo**, at
t = −1.78. Marginal, but note *which channel it works through*. Four hydro probes
failed asking whether rain moves hydro's **cost** (the water value). This asks
whether rain moves hydro's **flexibility as an arbitrageur** between the two
auctions — a different mechanism, and the one with the right sign. The reservoir
*level* remains null (+5.887, t = 1.22), which fits: flow matters for
arbitrage capacity, stock does not.

**And the uncomfortable asymmetry.** The one channel immune to the
wind-forecast-error confound is heat, and heat shows nothing. The two channels
that do show something — wind and rain — are both plausibly forecast-error
stories: wind directly, and rain because hydro inflow forecasts also err. So §6's
threat is not just unresolved, it lands precisely on the results that survived.

## 8. The forecast: half obtainable, half not

**Obtained, token-free.** `demanda.ree.es`'s `prevProgPeninsula` publishes REE's
own **demand forecast** (`pre`) and scheduled demand (`pro`) at 5-minute
resolution back to at least 2018 — `fetch_ree_demand_forecast.py`. Against REE's
own actuals: forecast error sd **1,023 MW**, MAE 684 MW (2.31% of demand). That
is nearly double the 537 MW one-sd heat shock, and unlike temperature it is by
construction the part nobody anticipated. It closes half the §3.2 gap in
`literature-extreme-weather-economics.md` — that every weather design here
treated a *realisation* as a surprise.

**Not obtainable.** A day-ahead **wind** forecast, which is the series this design
actually needs. Checked and ruled out:

- `demanda.ree.es` has no renewable forecast endpoint —
  `prevProgRenovablePeninsula`, `prevRenovablePeninsula`,
  `prevProgEolicaPeninsula`, `eolicaPeninsula` all 404.
- ESIOS indicator 541 returns **403** without a token, as does `/archives`
  itself — so the token-free route that works for archives 82 and 83 does not
  extend to indicators.
- ENTSO-E requires a token too.

A personal ESIOS token is free but must be requested by email
(`consultasios@ree.es`, per `scripts/lib/config.py`). **This is now the single
binding data gap in the project**, and it is the one thing here that cannot be
solved by writing more code.
