# Heat, demand and conduct — a framework for weather designs, and its first test

Written 2026-08-21, after four hydro probes failed and the drought was shown to
be a control rather than an instrument. This note sets out a general shape for
weather-based designs here, then reports the first test run inside it.

---

## 1. Why the earlier designs failed, which is what the framework has to fix

All four hydro probes used weather to shift a **supply-side state variable**
(water value) and read the response off offers. They failed the same three ways:

1. **The state variable is also the firm's choice variable.** Reservoir storage
   is the outcome of past bidding, so reverse causality was always available —
   and the 2026-08-18 probe's positive sign is exactly what that path predicts.
2. **Weather's effect on the price level swamped everything else.** The national
   fill anomaly correlates −0.41 with the clearing price and essentially zero
   with residual-demand steepness at either market or firm level.
3. **Realised weather was treated as a surprise.** Bids are submitted at noon on
   D−1 against a forecast. A rainfall "shock" the operator already knew about is
   not a shock to anyone's information set.

## 2. The framework: exogenous state shock × predetermined firm characteristic

**Demand inverts all three.** It is not a firm's choice variable. A demand
shifter is the classical instrument for tracing out supply — and because the bid
files *are* the supply functions, the shifter is not needed to recover a curve
but to test whether the curve moves when it should not. And anticipation flips
from defect to requirement: a forecast heatwave is precisely the state the firm
conditions its day-ahead bid on.

The general form:

```
y_it = b1 * Shock_t + b2 * (Shock_t x Char_i) + alpha_i + tau_ym + controls
```

Three components, each doing one job:

- **Shock_t** — an exogenous state shock, defined identically across event
  classes as a percentile **within a cell** (basin × month, or calendar month
  for national temperature). The within-cell definition matters: a 30 °C day is
  unremarkable in August and a genuine shock in May, and only the second is news
  to a dispatch plan. Event classes are stackable: heat, cold, wind drought,
  inflow.
- **Char_i** — a **predetermined** firm characteristic that theory says mediates
  the response. For market power that is size, because the markup is
  `q_i / |RD_i'|`. This is where the cross-sectional variation comes from — not
  from the weather, which is national. Every failed design lacked this.
- **Stacking** — the reason to use many events rather than one. With a single
  event, the coincident gas-price path *is* the event and cannot be separated
  from it. With 135 heat episodes spread over nine years, each coincides with a
  different macro path, so event-specific confounds average out. That is the
  Hsiang & Jina logic (6,700 cyclones), and it is why single-storm event studies
  in a single-price-zone market are not identified.

**The event study is mandatory, not a robustness check.** The spill-window
design produced a correctly signed interaction that cleared a wild cluster
bootstrap and was still wrong — the event study put the entire effect in the arm
where the mechanism predicted nothing.

## 3. Data built for this

| dataset | what it is |
|---|---|
| `data/weather/temperature_population_index.parquet` | population-weighted Iberian temperature, 21 cities, with cooling/heating degree hours |
| `data/omie/indisp/parquet/` | declared unit unavailability with cause and declaration timestamp, 44,636 records |

The temperature index exists because `fetch_weather.py`'s points were sited for
**wind and solar capacity**, not population. **It turned out to barely matter**:
+0.993 correlation with the renewable-sited mean, and 34.1 °C against 34.3 °C
even in the top 1% of hours. Right on principle, empirically almost identical —
recorded because the opposite was predicted.

## 4. The first test: does a thermal plant's markup respond to heat?

68 units with a **plant-specific** JRC efficiency (46 gas, 22 coal), 97,727
unit-days, 12 firms. Markup is offer minus `gas/eff + 0.2020*co2/eff`.

**A measurement decision that had to be made first.** 15.2% of unit-days carry a
submitted median above 500 €/MWh with a 99th percentile at the 2,999 price cap —
deliberately unclearable bids expressing an intention *not* to run. Pooling them
is what made the levy design's estimates swing 0.13 → 1.82 under trimming. The
primary outcome is therefore the **marginal accepted** offer (revealed
willingness to run), with the submitted median reported only on unit-days when
the unit actually cleared. Both winsorised at 1/99.

| test | β | se | t |
|---|---|---|---|
| CDH → markup, marginal accepted **(primary)** | +0.96 | 1.20 | 0.80 |
| CDH → Lerner | +7.35 | 4.67 | 1.58 |
| CDH → markup, submitted \| unit ran | −3.96 | 2.59 | −1.53 |
| hot day → markup, marginal accepted | −2.33 | 4.76 | −0.49 |
| **CDH → P(unit clears at all)** | **+0.019** | 0.003 | **5.60** |
| hot day → P(unit clears at all) | +0.044 | 0.016 | 2.69 |
| CDH × size → markup, marginal accepted | −6.30 | 3.47 | −1.82 |
| CDH × size → markup [firm-clustered, 12] | −6.30 | 5.55 | −1.14 |

**Null on conduct.** The primary coefficient carries the right sign and is
nowhere near significant. The size interaction — which market power requires to
be **positive** — is negative in every specification.

**The event study confirms it is not a power problem being hidden.** On the
marginal accepted markup the coefficients are positive throughout, including
k = −5 (+5.45) and k = −4 (+8.37, t = 2.37), and k = 0 is +3.69 (t = 0.45),
*below* the pre-period. A pre-trend with no step — the same shape that killed
the spill window.

**The one robust finding is the extensive margin**, and it is merit order rather
than conduct: units clear more often on hot days (+4.4pp), building with a lag
(k = 2 and k = 3 significant). Higher demand dispatches more thermal plant. That
is the model working, not firms behaving differently.

## 5. How far this null goes, honestly

**It is imprecise, not tight.** The primary 95% interval is roughly
[−1.4, +3.3] €/MWh per CDH unit, so over a 1-sd CDH move (3.28) it is
[−4.6, +10.9] €/MWh. Against a median accepted markup of −6.2 €/MWh that is
wide. The design cannot rule out an economically meaningful conduct response; it
can only say there is no evidence of one, and that what evidence there is points
the wrong way on the size interaction.

**The treatment is small.** Spanish demand rises ~0.5%/°C at 30 °C, and CDH has
sd 3.28, so a one-sd heat shock is roughly 1.6% of demand — far smaller than the
day-of-week or seasonal swing a firm routinely bids against. Temperature may
simply be too weak a demand instrument in this market to move a markup
detectably, independent of whether conduct responds to demand at all.

**Two threats are not yet controlled**, and both would only matter if there were
an effect to explain:

- Heat is also a **supply** shock — turbine derating, cooling-water limits, and
  Ascó and Vandellós are river-cooled on the Ebro. `indisp` is now fetched and
  covers 55 of these 68 units, but is not wired in.
- **Start-up costs** make even a competitive firm condition its offer on
  expected demand (Jha & Leslie). `cab`'s declared minimum-income condition is
  the primitive that separates the two and is likewise not wired in.

**A level result worth noting separately.** The median markup on the marginal
accepted offer is **−6.2 €/MWh** — these units clear below their implied
marginal cost about half the time. Three candidate explanations, all live: the
implied cost overstates the true one (it is a full-load engineering bound and
omits contracted gas at below-index prices); firms short of their contract
position bid below cost by design (Hortaçsu & Puller); and a committed unit bids
below cost to avoid a shutdown-restart cycle. Unit fixed effects absorb this for
the movement test, but it means the markup **level** here is not interpretable
without theta and start-up costs.

## 6. What the framework is worth after one null

The framework survives the test that failed. Its value is that it made this
question cheap — one script, one afternoon, a decisive event study — and that it
generalises: the same shape takes cold snaps, wind droughts and inflow shocks as
alternative `Shock_t` with no redesign. What it cannot fix is a weak treatment
or the ~30-firm ceiling on `Char_i`.

The obvious next `Shock_t` is not weather at all: **wind forecast error**, which
is larger in demand-equivalent terms than temperature, is genuinely unanticipated
at gate closure, and shifts net load rather than load. That is the one shock in
this market big enough to move a markup if anything does.

---

## 7. Two follow-ups, 2026-08-21

### 7.1 Wind forecast error is several times larger than the heat shock

Measured on a common net-load basis in MW, which is the only way to compare a
demand shifter with a supply shifter:

| shock | MW |
|---|---|
| 1-sd heat shock, through demand (137.2 MW per CDH unit × sd 3.92) | **537** |
| 1-sd wind output swing | 3,814 |
| 1-sd wind "forecast error", 24/48/72h persistence residual | 2,859 |

That is 5.3×, and the heat shock is only **1.85% of mean load**.

**But the 2,859 figure overstates it**, and by an unknown amount. It is the
residual from a persistence model with R² = 0.264 — a poor forecast, far worse
than the market's own. The true unanticipated component at gate closure is
smaller.

**An attempt to measure the market's realised error from data on disk failed
and should not be repeated in that form.** Day-ahead *cleared* volume of
wind-tagged units against REE realtime actual wind covers only **29%** of actual
wind output, because the technology mapping reaches 41% of volume overall and
less for wind specifically. Scaling a 29% sample up to national totals
multiplies its sampling noise, not just its error, which is why that route
returned an implausible MAE of 29% of mean output — real day-ahead wind
forecasts are far better than that.

**What survives is a bound, and it is enough to act on.** Any plausible real
forecast error — even half the persistence residual — leaves wind at 2.6× or
more of the heat shock. Wind is the larger shock and worth pursuing. Measuring
it properly needs either a published day-ahead forecast (ESIOS indicator 541,
**token required**, unlike archive 82) or a fix to wind-unit identification.
Do not build the design on the persistence proxy.

### 7.2 The extensive margin: also null, and the test is too coarse to be decisive

`withholding_extensive_margin.py`. The price margin found nothing, but
withholding is an extensive-margin decision — a firm can withdraw capacity
rather than reprice it — so this tests **in-the-money non-clearing**, with
declared outages netted out using the `indisp` data fetched for exactly this.

| test | β | se | t |
|---|---|---|---|
| CDH → withheld \| ITM at day max, available | **−0.018** | 0.004 | **−4.80** |
| hot day → withheld \| ITM at day max, available | −0.036 | 0.018 | −2.08 |
| CDH → withheld \| ITM at day mean, available | −0.011 | 0.004 | −2.96 |
| CDH × size → withheld (firm-clustered, 12) | +0.036 | 0.049 | 0.73 |

Market power predicts β > 0. The main effect is **negative and strongly
significant**: in-the-money units withhold *less* when demand is high. That is
merit order again, now measured conditional on being in the money. The size
interaction carries the right sign and is nowhere near significant. The event
study is flat at k = 0 (−0.007, t = −0.44).

**The reason not to treat this as decisive: the daily ITM measure is nearly
vacuous.** 85.9% of unit-days are "in the money" against the day's maximum
price, and **73.7% of those clear nothing**. A mid-merit unit is in the money
for a handful of hours a day, and start-up costs and minimum run times make
running unprofitable anyway — so daily "should have run" captures almost
everything and identifies almost nothing. Settling this needs a **period-level**
in-the-money measure, which is a real build.

**The placebo is a warning, not a pass.** Regressing *declared outage* on the
shock gives +0.0041 on a hot day (t = 2.02) against a 2.2% base — small, but
significant. Either heat genuinely causes outages (derating and cooling-water
limits, the supply-shock threat this design has flagged from the start) or
outages are declared strategically. Both readings say heat is **not** a clean
demand shifter, which is the third independent piece of evidence for that.

### 7.3 Where this leaves the framework

Two shocks tested on two margins, four nulls. The framework is doing its job —
each test was cheap and each was killed by its own diagnostic rather than by
wishful reading — but heat is now exhausted as a shock in this market: too small
(1.85% of load), and not clean (it moves availability too).

The two things worth doing next, in order:

1. **A period-level in-the-money measure.** Daily aggregation is what made §7.2
   vacuous, and the fix is mechanical rather than conceptual.
2. **Wind forecast error as the shock**, once a real forecast is in hand. It is
   several times larger, genuinely unanticipated at gate closure, and shifts net
   load rather than load — the one shock in this market big enough to move a
   markup if anything is.

---

## 8. Period-level withholding, and the combined design, 2026-08-21

### 8.1 The period-level measure does not rescue the daily one

`withholding_period_level.py`. In-the-money is now evaluated **period by
period** against that period's clearing price, aggregated back to unit-day as a
share of the unit's own in-the-money periods (shares, not counts, because the
15-minute switch quadruples period counts).

It is a real sharpening — 73.3% of a day's periods are in the money against
85.9% of unit-days under the daily measure, median 18 of 24 — and it changes
nothing:

| test | β | se | t |
|---|---|---|---|
| CDH → withholding rate | **−0.0133** | 0.0026 | **−5.03** |
| hot day → withholding rate | −0.0310 | 0.0139 | −2.23 |
| CDH × size → withholding rate (firm-clustered, 12) | +0.032 | 0.047 | 0.68 |

Same sign, same significance, same null on the interaction, flat event study at
k = 0 (−0.011, t = −0.84).

**A measurement bug found and fixed, worth recording.** The first cut reported
"physical withholding: 0.0%", which is impossible. A unit that submits no offer
has **no row** in `curva_pbc_uof`, so a panel built by grouping bid rows contains
only unit-periods where the unit was already present — absence is unobservable
by construction. The denominator has to come from the **price grid** instead:
count all periods whose clearing price exceeded the unit's marginal cost,
present or not. Corrected, physical absence is genuinely ~0.1%: these units
essentially always submit an offer and simply price it above the clearing price.

**The measure still is not withholding, and the reason is the cost measure, not
the time resolution.** The median unit-day has a withholding rate of **100%** —
no output at all across a median 18 in-the-money periods. No plausible amount of
market power looks like that. The implied marginal cost is a full-load
engineering figure that omits O&M, part-load derating and start-up
amortisation, so "in the money" on it is systematically over-inclusive, and what
the outcome mostly records is that mid-merit units are not worth starting. Going
finer in time did not fix that and nothing about time resolution could have.

### 8.2 Combining heat, wind and rain: one channel, not one index

The wrong way to combine them is an index of weather extremity — it would net a
demand shock against a supply shock. The right way is to notice that all three
move the **same economic quantity**: how far up the thermal stack the market has
to clear, i.e. net load = demand − wind − solar. The markup is `q_i / |RD_i'|`,
and both terms are functions of that. So the three are **three instruments for
one endogenous regressor**, not three designs (`net_load_iv.py`).

**The first stage is strong** — F = 184.8 on all five instruments, and wind
alone F = 367.7. Net load has sd 4.84 GW around a mean of 20.7 GW.

| outcome | specification | β | se | t | F |
|---|---|---|---|---|---|
| markup | OLS | 0.214 | 0.379 | 0.56 | — |
| markup | 2SLS, all five | 0.345 | 0.347 | 0.99 | 184.8 |
| markup | heat only | 1.592 | 1.875 | 0.85 | 107.8 |
| markup | wind only | 0.386 | 0.371 | 1.04 | 367.7 |
| withholding | 2SLS, all five | **−0.0251** | 0.0013 | **−18.65** | 134.2 |
| withholding | heat only | −0.0293 | 0.0042 | −6.99 | 90.9 |
| withholding | wind only | −0.0249 | 0.0016 | −15.82 | 333.8 |

Three things to take from this.

**The markup is a genuine null, and now a better-measured one.** OLS and 2SLS
agree closely (0.21 against 0.345), which says endogeneity was not doing much
work — the same pattern the residual-demand elasticity result already showed.
A one-sd net-load move (4.84 GW) shifts the markup about 1.7 €/MWh, against a
median markup of −6.2. Small and insignificant.

**The withholding result is precise and points the wrong way for market power.**
t = −18.65 with a first-stage F of 134: higher net load means *less*
in-the-money non-clearing. Heat-only and wind-only agree closely (−0.029 against
−0.025), which is the overidentification check passing between the two strong
instruments. But §8.1 is why this precision does not buy a conduct conclusion —
the outcome is dominated by unit commitment, so the estimate is a well-measured
statement that units start when the system needs them.

**Rainfall has no first stage here, by construction.** Reservoir anomaly gives
F = 0.0 for the markup and 0.3 for withholding. That is not a data failure: net
load is demand − wind − solar and **hydro is not in it**, so reservoir state
cannot move the regressor. To make rainfall an instrument the endogenous
variable has to be *thermal residual* load — demand net of wind, solar, hydro
and nuclear — which is a different and defensible specification and is not built.
That is the one concrete improvement this section identifies.

### 8.3 Standing scorecard

Six tests, two shocks, two margins, two resolutions, one combined IV. Every
conduct estimate is null or wrong-signed; every precisely estimated result is
merit order. The framework keeps doing its job — each test was cheap and each
was killed by its own diagnostic — but the accumulating evidence is that **the
markup measure, not the shock, is the binding constraint**. An implied marginal
cost that omits O&M, part-load and start-up costs cannot support a markup test
at this resolution, whatever is instrumented.

The next thing worth building is therefore not another shock. It is `cab`'s
declared minimum-income condition wired into the cost measure — the repo's one
genuine data advantage, published daily, and the primitive that Jha & Leslie had
to estimate.
