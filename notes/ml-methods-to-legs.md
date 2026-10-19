# ML-in-econometrics course material → the thesis legs

Written 2026-10-08. Source: the nine lecture decks in `~/projects/ML/` (04 LASSO
theory, 05 alternatives, 06 trees, 07 neural nets, 08 sparsity, 09 causality,
10 inference in HD, 11 IV in HD, 12 heterogeneity). Written from the decks' slide
titles and the standard results they cover (double/debiased ML, Chernozhukov et al.;
double selection, Belloni et al.), **not from a close read of the slides**: check
notation and the exact estimator against decks 10–12 before coding anything.
Design context: `docs/specs/2026-09-29-thesis-framework-design.md` (legs, §9) and
`docs/specs/2026-10-01-step-offer-design.md`.

**In one line.** Two things in this thesis are prediction problems, and ML is the
right tool for them: *what did the firm know at the noon deadline* (the conditional
expectations the step estimator needs) and *what would a price-taker have offered*
(the non-strategic benchmark of §9.1). Neither is a problem of too many
controls, which is what the course's headline method (double LASSO) solves. The
binding limit on every leg is the number of independent firm-level shocks (five
or six firms, shocks correlated 0.94–0.98), and no learner fixes that.

---

## 1. What the course gives, in one table

| tool (deck) | what it does | where it would enter here |
|---|---|---|
| Double LASSO / partialling out (10) | residualise y and the treatment on many controls, regress residual on residual; Neyman-orthogonal, so first-stage selection errors do not bias β | leg C and leg D regressions with a long list of continuous controls (fuel, carbon, demand, rivals' output, lags) |
| Cross-fitting (10) | fit nuisance functions on one fold, predict on another; allows forests/boosting as nuisance learners | any ML nuisance function below. **Folds must be blocks of weeks or months, not random hours**: offers and prices are serially correlated, and random folds leak |
| Double ML for IV (11) | orthogonal moment for β with an instrument; residualise y, n (or X) and Z on controls, then IV on residuals | legs B, C, D when instruments are many (forecasts W, S, D; rain; reactor doses; regional wind) |
| Many instruments, orthogonal TSLS (11) | collapse a high-dimensional Z to its predicted value E[n or X \| Z, controls] estimated by ML, then use it as the instrument | the **optimal instrument**: one scalar fitted from all of §9.3's instruments instead of picking one |
| ATE / CATE, DML for heterogeneity (12) | orthogonal estimate of average effect; effects by pre-specified groups; causal forest for data-driven groups | β by firm, technology, sign of n, year (legs C and D differ across all four) |
| Ridge / elastic net / lava, sparsity (05, 08) | shrinkage when not sparse | first stages with weather variables, which are dense, not sparse (deck 08's "illusion of sparsity") |
| Trees, forests, boosting, nets (06, 07) | flexible E[y \| x] | nuisance learners and the forecasting uses in §4 |

## 2. Leg by leg

Status lines are from `CLAUDE.md` and the framework spec; check them against
`notes/handoff-2026-10-05.md` before quoting.

### Leg A: hydro within the day (done, holds on the exposed position)
Unit-day effects already difference out cost, and technology × period effects absorb
common shocks, so the design controls for confounders by fixed effects, not by
selection. **DML adds little.** One use: the "β is not shown to be small" worry is
about day-level strategy (EDP's flat cascades), not about controls.

### Leg B: hydro across days (levels: β −0.26 [−0.72, 0.04]; Nash rejected)
The problem is the first stage (F 0.4–1.9 on day-level X before reactor outages and
rain) and the cost term (water value λ). Two ML routes:
- **Orthogonal TSLS with many instruments** (deck 11): reactor outages, own-catchment
  rain, forecast stocks, and the 2021-levy contract shift all move day-level n. The
  rain index is the weak one (pooled F 11.6–21.3, wild-bootstrap p 0.044 over six
  firms). Collapsing them to one fitted instrument is the textbook remedy for "many
  weak instruments", but it cannot create independent variation: six firms with rain
  correlation 0.94–0.98 stay six firms (Borusyak, Hull and Jaravel).
- **λ itself** is a forecasting problem; see §4.5.

### Leg C: thermal in levels (β ≈ 3.09, F 69; read as the merit order, not conduct)
β ≈ 3 is a ratio of slopes (rivals' |RD′| over the firm's own supply response), not
a flawed control set, so partialling out more does not change it. Where DML does
help is the *repair*: §9.1 says the estimator must net out how price-takers' offers
respond to the same shock. That is a prediction of the non-strategic ladder (§4.3).

### Leg D: sign of n (β 0.03 net of fringe; markdown when buying β⁻ 0.19)
- **Weak instruments by firm:** F 12 (Iberdrola), weaker elsewhere; the optimal
  instrument (deck 11) is the right way to combine W, S, D, outages and regional
  wind, with the caveat above.
- **Heterogeneity is the result:** β⁺ ≈ 0 against β⁻ 0.19 rests on differences
  between firms (Endesa nearly always a buyer, Repsol mostly a seller). Deck 12's
  group-average effects (sorted by predicted dose, framework §9.4) is the planned
  presentation; reactor outages that move one firm across n = 0 are the within-firm
  test. An instrumental forest (parked in §9.4) adds little with five strategic
  firms and weekly dependence.

### Step estimator and the one-β test (proposed, nothing built)
The conditional expectations E[n | k], E[|RD′| | k] and the resampled residual demand
are conditional on I_bid. That is a **conditional-distribution prediction** and the
single best fit for ML in the thesis (§4.1).

### Policy tests (water levy multiplier 1.28/1.34, IVPEE, gas cap)
These are tests of c with a predicted number set by law. Standard errors and
placebos matter more than controls. DML is not needed; use deck 12 only for
by-group effects (taxed against untaxed, above against below 50 MW).

### Sequential markets (anticipated against surprise; DA–ID premium)
The Romer–Romer step, "residualise the forecast on what was predictable earlier",
is a prediction problem, and the day-ahead placebo currently **fails** (F 6–31):
firms know part of REE's forecast error. A better model of the firm's information set
is the fix (§4.4).

## 3. Where it would not help, so we do not oversell

1. **Controls are mostly fixed effects already.** §9.2 absorbs unit-week and
   technology × date × hour effects. High-dimensional selection among controls
   (the case double LASSO exists for) is a minor part of this design.
2. **The limit is the effective number of shocks.** Five or six firms, rain
   indices correlated 0.94–0.98, shift-share exposure from a handful of reactors.
   Better learners raise first-stage F only when the extra variation is real and
   firm-specific; common instruments are absorbed by the period effects.
3. **ML-predicted prices must not be plugged in as a regressor.** A flexible fit of
   p (or of n) used naively as a regressor is a generated regressor with
   first-order bias; it has to enter through an orthogonal moment with cross-fitting.
4. **Hourly data are not i.i.d.** Cross-fit by week or month blocks; cluster by
   week or firm. Random k-fold hurts exactly where the data are thickest.
5. **Prediction accuracy is not the objective.** The deck's tuning (CV on
   mean-squared error) targets prediction; for first stages and nuisance functions
   that is acceptable, but report the first-stage F and the AR set, not the R².

## 4. Where forecasting could actually help

Ranked by how directly each fixes something the notes already flag as broken.

### 4.1 Learn the firm's information set: the conditional expectations of the step estimator (strongest)
The step estimator's moments take expectations "given I_bid", built by resampling
residual demand conditional on the day-ahead forecasts (spec §3, after Wolak 2007 and
Reguant 2014). Presently that means binning on W, S, D. A learner for the
conditional distribution of (RD, n, |RD′|) given everything known at 11:00 on D-1 (the
three forecasts, hour, season, lagged prices, forwards, scheduled outages, the
capacity factor) does that without ad hoc bins, and the resample can draw residuals
from the learner's out-of-fold errors.
- *Method:* gradient-boosted or random-forest quantile regression, or a conditional
  bootstrap on forest-similar days; cross-fit by month.
- *Why it matters:* the length-of-step condition holds only in expectation over
  the periods in which p falls in the gap above the step, so a bad forecast moves β.
- *Risk:* a forecast sharper than the firm's own makes surprises look foreseen.
  Calibrate against firms' realised behaviour (§4.4).

### 4.2 Optimal instrument for n (medium; legs B and D)
Estimate E[X_f | all instruments, controls] with a regularised learner and use it as
the instrument (deck 11). Dense weather features suggest ridge or elastic net over
LASSO (decks 05, 08). A forest buys non-linearity: displacement of gas and hydro by
wind is a merit-order effect, which is convex in the forecast, not linear (the
forecast first stage found that a windy forecast *lowers* n, `rq-forecast-first-stage.md`).
Gain is real on the strong firms (EDP, Iberdrola, Endesa), small on Naturgy, Repsol.

### 4.3 Forecast the non-strategic ladder: the benchmark of §9.1 (medium; fixes the step estimator and leg C)
The note's own diagnosis is that offer ladders slope up without market power, so the
estimator must net out how price-takers of the same technology respond to the same
shock. Train, on price-takers only (fringe thermal and hydro of the same technology,
with period effects as in §9.2), a model of offer-minus-cost as a function of
the shocks; predict it for each strategic firm's units and subtract. Using ML
instead of the linear control is justified because the response is non-linear.
- *Caveat in the notes:* the fringe's thermal responds like the five firms'; its hydro
  does not. So the benchmark exists for thermal and not (yet) for hydro.
- *Risk:* this *is* a forbidden-regression situation (a fitted nuisance enters β);
  use the orthogonal form and cross-fit.

### 4.4 Anticipated against surprise (medium; fixes a failing placebo)
Two forecasts of the same quantity: REE's D-1 forecast, and a model built on what
the firm could know earlier (normal weather, yesterday's output, forwards, capacity).
Residual = the unanticipated part. The day-ahead placebo failing says firms already
know part of REE's error, so the estimator needs the *firm's* forecast, not REE's.
- *Method:* boosted trees on lagged information; test against the firms' own revealed
  forecast, i.e. whether their offers respond to the model's prediction of the error.
- *If it works:* the shift-share on the intraday surprise (F 3.3) may recover
  strength once the surprise is the part firms could not foresee.
- *If it does not:* it supports the reading that the intraday route is closed.

### 4.5 Water value inputs (medium; leg B, §6 of the step design)
M4/M5 need inflow and price-scenario forecasts, not new estimation theory: inflows
from rain and catchment state (SNIRH, E-OBS, HydroBASINS), the forward price over the
storage horizon, the hourly shape. The dynamic program takes these as inputs. A forest
or small net for inflows is reasonable; a deep net is not (a few hundred weekly
observations per cascade). **The competitive λ must not be fitted to offers**, or
it absorbs the markup being tested; only offer-free data enter the forecast.

### 4.6 Not worth it
- **Predicting the price** as a goal in itself: it is not the target, and published
  work on OMIE-type prices is plentiful without the identification this thesis needs.
- **Neural nets (deck 07):** about 70,000 hours but five firms; the deck's
  approximation guarantees rest on a structured-sparsity assumption we cannot verify.
  Trees and boosting do the same job with fewer tuning choices.
- **Surrogate model of the clearing algorithm** to speed the 50–100 resampling draws:
  the clearing is deterministic and cheap per draw; only worth it if run time bites.
- **Instrumental forest for heterogeneity:** parked in framework §9.4 for good reason.

## 5. A plausible order

1. **§4.1 and §4.4 together**, since both are "forecast what the firm knew at 11:00",
   built once as a shared module in `scripts/lib` with month-blocked cross-fitting.
   Test it first on thermal firm-periods in the gas-cap window, where cost is statutory.
2. **§4.3**, because the step estimator needs the benchmark before its first result.
3. **§4.2** as a robustness exercise on legs B and D (does the optimal instrument
   narrow any Anderson–Rubin set?). Expect modest change; report either way.
4. **Double ML with an orthogonal moment** as a cross-check on legs C and D with the
   long control list. It is the course's own method, and a null result (β does not
   move) is informative: it shows controls were never the issue.

## 6. To verify

- Slide-level details in decks 10–12: the exact orthogonal moments, the
  recommended nuisance learners and tuning, and the cross-fitting scheme.
- Whether OMIE-published information at 11:00 on D-1 (ESIOS 1775/1777/1779,
  forwards, scheduled outages in `indisp`) is all the firm sees, or the firms have
  private weather forecasts. Private forecasts would make the placebo fail
  whatever model we fit.
- Whether blocked cross-fitting by month leaves enough data for the five firms in
  the gas-cap window (2022-06-15 to 2023-12-31, 18 months).
