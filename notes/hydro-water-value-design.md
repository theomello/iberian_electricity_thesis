# The hydro water-value design: what is settled, what it costs

Written 2026-08-13. **Nothing is decided.** This exists to be put to the
supervisor as a trade-off, not as a recommendation.

## What the data settles

Checked directly, not assumed:

- **44 hydro storage units (UGH)**, 19 pumped, 69 of unresolved class.
- **They bid informatively.** Volume-weighted median offer prices for storage
  hydro move €154/MWh (2021-06) → €615 (2022-03) → €100 (2024-03). A unit
  bidding its water value rather than a near-zero marginal cost is exactly what
  the design needs, and this is that signature.
- **The run-of-river control is real.** The unresolved class collapses to
  €0.00/MWh in some months — the run-of-river signature, since it cannot
  store and must sell. That validates the UGH split empirically rather than by
  assertion.
- **Hydro is the marginal technology more often than anything else.** 26–47%
  of periods in every year except 2022, when gas takes it during the crisis.
  See the corrected table below; the earlier version of this finding was an
  artifact and understated hydro badly.

## What the data does *not* settle

**The policies overlap.** RDL 17/2021's clawback runs to 31 December 2023, not
to March 2022 as recorded earlier, so it coincides with the gas cap for 18.5
months. See [`candidate-natural-experiments.md`](candidate-natural-experiments.md).
The mirrored-episodes framing does not survive this.

**Hydro's price peak is in March 2022 — with the gas price, not on a policy
date.** This is the central obstacle. Storage hydro bids the opportunity cost
of water, which is a function of the *expected future price*, and the expected
future price moved violently for reasons that have nothing to do with Spanish
policy. A reduced-form event study around a policy date therefore picks up the
gas-price channel and the policy channel together, and cannot separate them.

## The consequence: structural, not reduced-form

This is not a reason to drop the design — it is the reason the structural model
is **necessary rather than optional**. Estimating an opportunity-cost function

```
c(pf, Vol, Snow)
```

— forward price, reservoir volume, snowpack — exists precisely to net out the
expected-price channel, so that what remains in the residual is the policy
response. Arzhintar, Leslie, Neill and Wyrwoll estimate exactly this object.

So the choice is not "structural or reduced-form". It is "structural or not
this question".

## The honest risk

Stated plainly, because this is what the supervisor should weigh:

- **44 units**, aggregated into cascades, several of which are whole river
  systems registered as a single bidding unit (`ADOURO`, `TEMON`).
- **One structural model**, whose estimates carry the whole result.
- **A confound that only that model can remove** — no descriptive fallback if
  the estimation is weak.
- **Three data series still to fetch**: reservoir levels, ERA5 snow depth
  (same source as the existing weather fetch), and OMIP forward prices.

That is a materially more ambitious thesis than the descriptive elasticity
result, which is already in hand and does not depend on any of it: residual
demand elasticity fell 1.83 → 0.85 between 2018 and 2023 while CNMC's
Herfindahl index *fell* 1,314 → 1,007, with the weather instrument agreeing
with OLS to within 4%.

**The question for the supervisor is whether a master's thesis should take that
trade.** It is a real trade, not a formality.

## Two advantages worth stating up front

Both are things Jha & Leslie have to work around and we do not:

1. **Declared start-up costs are published.** They estimate start-up costs from
   daily plant-level gas metering because their market does not publish them;
   `cab` publishes a declared minimum income condition per unit per day. Caveat:
   **only to 2025-03-18** — the file format changed and the variable term is no
   longer published. See the `cab` trap in CLAUDE.md.
2. **The contract position is observable.** They devote an appendix to
   inferring it because Snowy Hydro's contracts are not public. In Spain the
   gap between the operating schedule (PDBF) and the auction result (PDBC) is
   published per unit per day, and that gap *is* the forward position — the
   `theta` term in Wolak (2000) and Hortaçsu & Puller (2008). On January 2024
   PDBF sell volume is 1.73x day-ahead cleared volume, so the wedge is large
   and measurable.

## Marginal technology, corrected

Share of periods whose price is set by each technology. 14,164 periods sampled
across 14 months. `regime` fills in where the specific technology is unknown.

| year | hydro | gas CCGT | coal/thermal | nuclear | wind | solar | cogen | special reg. | unknown |
|---|---|---|---|---|---|---|---|---|---|
| 2018 | **26.1** | 6.0 | 22.3 | 0.0 | 0.0 | 0.4 | 0.7 | 8.8 | 9.8 |
| 2020 | **36.9** | 21.2 | 1.8 | 0.0 | 0.8 | 0.7 | 1.8 | 7.9 | 14.8 |
| 2022 | 27.6 | **33.6** | 4.7 | 0.0 | 0.1 | 0.8 | 3.6 | 2.3 | 16.9 |
| 2024 | **46.6** | 2.8 | 0.1 | 3.2 | 4.6 | 3.1 | 1.0 | 6.1 | 24.5 |
| 2026 | **36.9** | 0.9 | 0.0 | 3.8 | 8.1 | 5.1 | 2.9 | 6.5 | 24.1 |

Unknown is 19% overall; the marginal unit's *firm* is known 81% of the time.

**An earlier version of this table showed hydro falling and a 32–63% unknown
share, and was wrong on both counts.** Two causes, both fixed: hydro cascades
carry river names that the technology patterns did not match, and the `cab`
parser was silently broken from 2025-03-19. Hydro is not declining as a
marginal technology — the apparent decline was the seven largest Portuguese
cascades dropping out of the classification.

## 2026-08-17: the cheap version was tried, and doesn't work

Before committing to the structural model above, a much cheaper probe was
run: does basin-level rainfall move a storage unit's own offers at all?
(`scripts/fetch/fetch_hydro_precipitation.py`,
`scripts/analysis/hydro_water_value_precip.py`.) 25 of the 44 `hydro_ugh`
units have their river basin identifiable from the `cab` name; a 90-day
trailing rainfall anomaly in each unit's own basin was regressed against its
monthly offer, unit + month FE, with a wrong-basin placebo as the check.

| outcome | regressor | β | t |
|---|---|---|---|
| median submitted offer | own-basin rain | +0.142 | 1.61 |
| median submitted offer | placebo-basin rain | +0.049 | 0.44 |
| marginal accepted offer | own-basin rain | +0.020 | 0.60 |
| marginal accepted offer | placebo-basin rain | −0.010 | −0.24 |

Nothing clears significance. Where there's a hint of own-basin beating
placebo (median offer), the sign is **wrong** — more rain should lower the
opportunity cost of water and lower the offer, and it comes out positive. On
the marginal accepted offer (the outcome this design actually needs), own-
and placebo-basin are indistinguishable.

**Consistent with, not contradicting, the point above about the March 2022
price spike.** Hydro's offer swung roughly 4–6x with the gas-price cycle in
2021–2024; a 90-day rainfall anomaly is a second-order input against that,
and rainfall is only one input into reservoir *volume* — the actual state
variable, which a large reservoir can buffer through a wet or dry quarter
without its marginal value moving much. This closes off the cheap shortcut
rather than opening one: the structural model (reservoir levels, snowpack,
forward price, jointly estimated) is still the only route in, not an
alternative to it.

## 2026-08-18: the actual state variable was tried, and it's a different
## kind of failure — sign, not power

The rain probe tested a proxy one step removed from the state variable. This
tests the state variable directly. `fetch_hydro_reservoirs.py` pulls MITECO's
Boletín Hidrológico Semanal historical archive — 720,099 rows, 401
reservoirs, 16 hydrographic demarcations, weekly, 1987–2026, token-free — and
`hydro_water_value_reservoir.py` reruns the identical own-basin-vs-placebo
design from the rain probe with basin-aggregate fill ratio (stored/capacity,
seasonally de-meaned by ISO week) in place of rainfall anomaly.

One data problem surfaced and was worth recording: MITECO's own
`ELECTRICO_FLAG`, meant to mark hydroelectric reservoirs, is not trustworthy
for this purpose — it flags **0% of Guadiana's reservoirs**, despite `GDNA`
("UGH. GUADIANA") being a real storage cascade in our own unit registry, and
under 20% in Guadalquivir, Segura and Tajo, baskets that plainly contain
generating reservoirs. Restricting to it drops real hydro storage rather than
excluding irrigation-only reservoirs as intended, so the script's default is
all reservoirs in the basin; the restricted version is kept behind
`--hydro-only` for comparison, not because it's preferred.

| outcome | regressor | β | t |
|---|---|---|---|
| median submitted offer | own-basin fill anomaly | +203.2 | **2.00** |
| median submitted offer | placebo-basin fill anomaly | +33.5 | 0.38 |
| marginal accepted offer | own-basin fill anomaly | +52.0 | **1.65** |
| marginal accepted offer | placebo-basin fill anomaly | −6.2 | −0.23 |

This is a genuinely different result from the rain probe, not a repeat of it.
Own-basin fill **does** beat placebo-basin fill, on both outcomes — the
basin-specific signature the rain probe never produced. But the sign is
**positive**, the opposite of the cost-shifter prediction (fuller reservoir →
lower opportunity cost → lower offer, i.e. negative).

**A positive sign here is not neutral evidence — it points at a specific,
different mechanism.** A plant that expects water to be worth more later can
bid high now *specifically to avoid being dispatched*, which mechanically
both raises its offer and keeps its reservoir fuller, with no cost-shifter
story required. That reverse-causality path predicts exactly this sign, and a
single reduced-form regression cannot tell it apart from a fill level that
moves offers through some entirely different channel. So this result doesn't
resurrect the reduced-form route — if anything it sharpens the case against
it: fill level looks endogenous to the plant's own bidding strategy, which is
precisely why Arzhintar, Leslie, Neill and Wyrwoll estimate `c(pf, Vol,
Snow)` jointly rather than regressing offer on `Vol` directly.

## 2026-08-18, Stage B: partialling reservoir fill out of Design 4 changes
## almost nothing — the instability is not an omitted-variable problem

The natural next step, given fill level carries real (if ambiguous) signal:
does controlling for it stabilise Design 4's beta, whose sign flips across
functional form and trimming in `levy_contract_exposure.py`? Method: the same
Frisch-Waugh-Lovell orthogonalisation that script already uses internally
(`treat_rel` against `treat`) — partial the reservoir fill anomaly out of the
treatment variable (`exposure x intensity`), unit+month FE absorbed on both
sides, then rerun the same levels/trimming battery. Script:
`levy_contract_exposure_reservoir.py`. Sample: the 17 (of Design 4's
exposure-measured units) whose basin is identifiable, smaller than the
original 23 because it's a different filter (basin-name-in-`cab` vs. pre-levy
PDBF volume) — so baseline is rerun on this same restricted sample, not taken
from the original script, to isolate the effect of the control.

| outcome | spec | β | t |
|---|---|---|---|
| median offer, levels | baseline | +0.127 | 0.18 |
| median offer, levels | controlled | +0.136 | 0.19 |
| marginal accepted, levels | baseline | −0.673 | −1.80 |
| marginal accepted, levels | controlled | −0.671 | −1.80 |
| log(offer/market) | baseline | +0.00663 | 3.61 |
| log(offer/market) | controlled | +0.00670 | 3.63 |

**Barely moves.** Beta changes in the third decimal place on every
specification; the trimming instability that broke the levels specs before
(median offer: p99 −0.08 → p95 +1.42 → p90 +1.69) reproduces almost exactly
under the control (−0.08 → +1.42 → +1.69). The placebo is likewise unchanged
(−0.0024 baseline vs. −0.0023 controlled, both null).

**This is a real negative result, not a non-result.** The reservoir probe
(above) showed fill level is not noise — it has a genuine own-basin
signature against offers. That it does almost nothing to Design 4's
treatment coefficient means it is close to orthogonal to `exposure x
intensity` in this sample, so whatever is producing the sign instability is
not the thing this control removes. That rules out the simplest version of
the omitted-variable diagnosis — "hydro's opportunity cost moves with fill
level and that's what's contaminating beta" — cleanly enough to stop
pursuing a linear control for it. What's left standing is the harder
reading `rq-gas-cap-conduct.md` already gave this design: the instability is
a measurement problem in the outcome itself (censoring by the clearing price,
a strategic bid deliberately unclearable and mixed in with genuine marginal
offers), which a control variable — reservoir-based or otherwise — cannot
fix, because it isn't omission, it's the wrong latent object being averaged
into "the offer." Structural or nothing, now tested three ways rather than
argued once.

**Practical consequence: all three structural inputs are now in hand.**
`pf` (OMIP forwards, ES 2018–2026), `Snow` (ERA5, `fetch_hydro_precipitation.py`)
and now `Vol` (MITECO, this fetch) are all fetched. Two independent reduced-form
probes on two different pieces of that input set have now failed for two
different reasons — no signal at all (rain) and the wrong-signed signal for
a plausible reason (fill level) — which is a cleaner argument for "structural
or nothing" than either probe alone: it isn't that the data has no
information in it, it's that a single-equation regression on any one input
can't separate the cost-shifter channel from the strategy channel. That is
exactly the job the joint estimation is for.

## 2026-08-18: the paper this note names has now been read, and "structural"
## turns out to mean something much cheaper than assumed

Arzhintar, Leslie, Neill & Wyrwoll, "Inferring the Value of Stored Water in
Hydroelectric Schemes" (working paper, 11 Nov 2025, SSRN 5736763,
`papers/md/ssrn-5736763.md`) — the paper this note has cited by name since
2026-08-13 without anyone having actually read it. Full findings on request;
this is what changes for the design.

**It is plain OLS, not a dynamic program.** They explicitly reject the
stochastic-reservoir-optimization literature (Tilmant et al., Aubin et al.)
and instead (1) restrict to intervals where their own scheme is the
price-setting unit — the Fabra & Reguant (2014) marginal-unit trick, imported
wholesale, identified from AEMO's own published "Price Setter" feed — (2)
construct an FOC-implied opportunity cost from price, quantity and a
kernel-smoothed residual-demand slope, and (3) regress that construction on
forward price, reservoir volume and snowpack, **additively, never
interacted**, by ordinary least squares (their footnote 35 calls the
residual "statistical, not structural" and explicitly declines to claim a
causal interpretation for β2/β3). The appendix robustness battery (log
transforms, quartile dummies, quarter-of-year interactions) never once
multiplies Vol × Snow or nests one inside the other — if the working
assumption here was that `c(pf, Vol, Snow)` needs some joint index blending
fill and snowpack, that assumption is not what this paper does.

**The mechanism that actually nets out the price-co-movement confound is not
exotic: `pf` sits in the same regression as `Vol`.** Both of this design's
own reduced-form probes (rain anomaly, then reservoir-fill anomaly) regressed
the offer on the water-state variable *alone*, with unit+month FE but no
control for the expected-price channel. The paper's equivalent step puts the
forward price in the same equation, so its Vol/Snow coefficients are
identified net of forward-price variation rather than off the raw univariate
correlation that conflates the two channels. That is a much smaller lift
than "structural or nothing" implied, and it's buildable from data already
on disk (OMIE bids for the residual-demand slope, OMIP for `pf`, MITECO for
`Vol`, ERA5 for `Snow`) plus one piece of new engineering: OMIE does not
publish AEMO's "who is marginal right now" feed, so it would have to be
derived from the bid/clearing data directly — the `capacity_quantile_offer.py`
marginal-technology work already does a coarser version of this (26–47%
hydro-marginal share by year).

**What it does not solve: Vol's own endogeneity.** The paper never claims to
— it disclaims causal interpretation outright (footnote 35) precisely
because reservoir volume is the outcome of the operator's own past release
decisions, which is the identical reverse-causality path the 2026-08-18 fill
regression above already surfaced (a plant that expects water to be worth
more later bids high now and stays fuller for the same reason). If this
thesis needs a causal claim about the levy/gas-cap response, that
endogeneity is inherited whole from this template, not resolved by it.

**Recommended next step, before building anything bigger:** re-run
`hydro_water_value_reservoir.py` with the OMIP forward price added as a
control alongside the fill-level regressor — the cheap version of the
paper's actual move, at a fraction of the cost of reconstructing a
marginal-unit sample and a kernel-smoothed residual-demand-slope estimator.
If the wrong sign and cross-trimming instability survive that control, that
is real evidence the problem is the endogenous-bidding-strategy channel the
paper doesn't solve either — worth knowing before investing in the larger
build, since the full apparatus is unlikely to fix what a forward-price
control doesn't.

**Stage C, tried immediately after (2026-08-18): the forward price, done
properly, doesn't move Design 4's beta either.** `levy_contract_exposure_forward.py`
partials `exposure_i × forward_price_t` out of `treat`, the same FWL move as
Stage B. First attempt used the forward price level and looked like a big
effect (log spec t: 3.61 → 1.10) — but `corr(treat, control) = 0.81`, because
the levy's intensity and the forward price both just track the 2021–22 gas
crisis. That's collinearity eating power, not a clean test. Redone with
`forward_price − spot_price` (the term-structure spread, stripped of the
common trend, `corr = 0.27` — genuinely separate variation): **beta barely
moves at all**, same as Stage B (log spec 0.00663 → 0.00659, t 3.61 → 3.20;
marginal-accepted-offer levels −0.673 → −0.707; trim instability pattern
unchanged in both). Placebo still null under the control.

**Two independent reduced-form controls (reservoir fill, forward-price
spread) now both fail to explain Design 4's sign instability.** Neither
omitted-variable story survives contact with the data. This narrows, not
widens, what's left: the instability is very unlikely to be a linear omitted
cost-shifter of either kind tried so far, which is further support for
`rq-gas-cap-conduct.md`'s "measurement, not identification" diagnosis (the
outcome itself — a bid that mixes genuine marginal offers with deliberately
unclearable ones — is the more likely source) over a still-untried linear
control fixing it.

> **2026-09-29 — the structural model below is invalid until rebuilt.** Its
> cost `c = p* − (q_i − Q_C_i)/|RD′_i|` takes `q_i` from auction-cleared volume
> and `Q_C_i` from the bilateral schedule, so it subtracts contracts twice — and
> Iberdrola's cascades, about 70% of its sample, carry the largest bilateral
> schedules. It also conditions on price-setting periods, the selection problem
> that invalidated the price-setting test in `rq-midday-hydro.md` §3.11. Every
> coefficient in this section, including the 0.94 forward-price pass-through,
> should be re-estimated on the net auction position before it is cited. See
> [`docs/specs/2026-09-29-water-value-design.md`](../docs/specs/2026-09-29-water-value-design.md), M3.

**2026-08-18, the structural model, first build:**
`hydro_water_value_structural.py`. Scoped first (`hydro_marginal_hours.py`):
12,470 marginal-hydro periods 2018-2026, present every month, but 70%
concentrated in 4 cascades (Duero, Tajo, Sil, Hidrocantábrico) — read
everything below as those cascades' behaviour, not "hydro in general".
Built the FOC-implied opportunity cost `c = p* - (q_i - Q_C_i)/|RD'_i(p*)|`
for every marginal-hydro period (residual-demand slope reused from
`residual_demand_slope.py`, a documented **aggregate-market** simplification,
not netted for unit i's own offers — a lower bound for large cascades, see
the script's own docstring), regressed on `pf` (OMIP front-quarter forward,
national monthly) and `Vol` (MITECO basin-aggregate stored volume, monthly),
no Snow (Iberian hydro isn't snow-driven and the rain probe already found
nothing there). 14,433 unit-periods, 19 units.

| spec | b1 (pf) | b2 (Vol) |
|---|---|---|
| pooled | 0.961 (t=14.8) | +0.0019 (t=1.23, ns) |
| pooled, trimmed p1-p99 | 0.861 (t=11.8) | +0.0018 (t=1.23, ns) |
| **with unit fixed effects** | 0.949 (t=12.6) | **-0.0039 (t=-2.23, p=0.026)** |

`pf`'s coefficient is stable at ~0.86-0.96 across every specification — close
to complete passthrough of the forward price, the same direction and even
closer to 1.0 than Arzhintar et al.'s own 1.260 (their Table 1, p.28).

**`Vol` only gets the textbook sign — and becomes significant — once unit
fixed effects are added.** Pooled, it repeats the same wrong-signed,
insignificant result every reduced-form probe before this one has found
(rain, reservoir-fill-on-offer, both Design-4 FWL controls). With unit FE,
comparing each cascade's own fill level to its own history rather than
pooling across cascades of very different scale, it flips to negative and
significant — fuller reservoir, lower opportunity cost, exactly the
cost-shifter prediction, for the first time in this project's whole hydro
water-value line of work.

**Updated 2026-08-19: the outliers were fixed at the source, not trimmed
post hoc, and the result held — got stronger, in fact.** Two separate
mechanisms diagnosed and dropped before regressing, not after: (1) periods
where the residual-demand slope sits in its thinnest 1% (36.9 MW/EUR)
produce near-zero-slope blowups — one period alone (SIL, 2023-01-25 h20,
slope 0.08 against a sample median of 354) was the entire source of the
6,111 EUR/MWh max; (2) periods clearing at or below 1 EUR/MWh (reusing
`residual_demand_slope.py`'s own `ZERO_PRICE` convention) are curtailment or
must-run, not a cost-revealing bid, and were the source of every negative
`c` in the sample. 182 of 14,433 periods dropped (1.3%); `c` afterward is
sane — 0.95 to 651, no negatives.

| spec | b1 (pf) | b2 (Vol) |
|---|---|---|
| pooled | 0.957 (t=17.4) | +0.0018 (t=1.19, ns — same wrong sign as every reduced-form probe) |
| **with unit fixed effects** | 0.941 (t=15.2) | **-0.0043 (t=-2.74, p=0.006)** |

Both coefficients are essentially unchanged from the pre-fix run, and the
fixed-effects `Vol` result got *more* significant (t: -2.23 -> -2.74; p:
0.026 -> 0.006) — evidence the earlier result wasn't an outlier artifact.
14 of the 19 target units retain enough periods to enter after the filter;
14,251 unit-periods.

**Ported to R** (`hydro_water_value_structural.R`) as the reporting layer:
reads the panel `hydro_water_value_structural.py --save` writes, runs the
same two specifications via `lm()` + `sandwich::vcovCL` (cluster-robust,
matching statsmodels' `cov_type="cluster"` line for line), and reproduces
every coefficient to four decimal places — a clean cross-check of the whole
pipeline as a byproduct. Division of labour is deliberate: the expensive
104-month bid-archive scan stays in Python; R only re-runs the regression,
so changing the specification doesn't require repeating a two-minute build.

**Updated 2026-08-19: both remaining caveats addressed, in a complete R
port (`hydro_water_value_structural.R`, self-contained — builds the panel
from the raw archives itself, no dependency on the Python script).**

**Fix 1 — net the marginal unit's own offers out of the residual-demand
slope, instead of using the aggregate-market density as a lower bound.**
Barely moved anything: every coefficient is within 0.001-0.002 of the
un-netted version (pf 0.956 vs 0.957 pooled, 0.942 vs 0.941 with FE; vol
0.0018 vs 0.0018 pooled, -0.0042 vs -0.0043 with FE). Even the four
dominant cascades are a small enough share of total volume near any given
price point that this correction, while theoretically real, isn't doing
much empirically. Not a source of the earlier result — good news, it means
the simplification wasn't quietly propping the finding up.

**Fix 2 — a cluster (pairs) bootstrap (2,000 reps, resampling the 14
surviving cascades with replacement) in place of trusting the asymptotic
cluster-robust SE with only 14 clusters.** This is the one that changes the
read:

| spec | coefficient | asymptotic cluster SE | cluster bootstrap 95% CI |
|---|---|---|---|
| pooled | pf | 0.956 (t=16.6) | [0.78, 1.05] — excludes 0 |
| pooled | vol | 0.0018 (t=1.2, ns) | [-0.004, 0.004] — includes 0, consistent |
| FE | pf | 0.942 (t=14.6) | [0.78, 1.09] — excludes 0, holds up |
| FE | vol | -0.0042 (t=-2.63, p=0.009) | **[-0.0086, +0.0011] — includes 0** |

**The forward-price result is genuinely robust** — both specifications, both
inference methods agree. **The reservoir-volume result in the
fixed-effects spec does not survive proper few-cluster correction at 95%
confidence.** The asymptotic SE was likely overstating its own precision
with only 14 clusters; the bootstrap CI is noticeably wider and just
crosses zero.

**Accurate one-line summary: correctly signed, still probably real (point
estimate and sign are completely stable across every specification and
both fixes), but not conventionally significant once inference correctly
accounts for having only 14 cascades.** That is a real, useful result —
better than every reduced-form attempt before it, which got the sign wrong
outright — just a more modest one than the first run's asymptotic p=0.026
suggested. Two panels saved, Python and R versions, for cross-checking:
`outputs/tables/hydro_water_value_structural_panel.parquet` and
`..._panel_R.parquet`.

**2026-08-19: the first actual RQ test, run on the fitted model --
real numbers, but likely contaminated, not a result to report yet.**
`hydro_water_value_policy_test.R` adds a policy-window dummy to the
already-validated `c ~ pf + vol + unit FE` model, handling the levy/cap
overlap the way `candidate-natural-experiments.md` already prescribes: the
gas-cap test is run on the levy-active sub-sample (16 Sep 2021 - 31 Dec
2023) so the levy differences out; the levy test is run on the pre-cap
sub-sample (before 15 Jun 2022) so the cap can't contaminate it.

| test | window | n | b3 (post-policy) | cluster bootstrap 95% CI |
|---|---|---|---|---|
| gas cap | 15 Jun 2022 -> 31 Dec 2023, within levy period | 2,567 | **-40.3** (t=-5.0) | [-55.4, -17.9] -- excludes 0 |
| levy | 16 Sep 2021 -> 14 Jun 2022, before the cap | 7,129 | **+46.6** (t=4.1) | [17.9, 62.9] -- excludes 0 |

Both are robust to the cluster bootstrap, not just the asymptotic SE.

**Do not read this as "hydro exploited the cap and marked down, then marked
up during the levy" without the caveat that comes with it.** `c` is built
directly from the market clearing price -- and both windows coincide with
massive, policy-*independent* price swings: the levy window is exactly the
2021-22 gas crisis ramp-up (already flagged, this section's whole earlier
history, as hydro's price peak tracking the gas cycle "not any calendar
date"); the gas-cap window is exactly when the cap itself mechanically
suppressed spot prices by ~E100+/MWh (González-de Miguel et al.'s own
estimate, see `rq-gas-cap-conduct.md`). The model's `pf`/`vol` coefficients
are fit mostly on the "normal" 2018-2020/2023-2026 variation; there is a
real, live possibility they simply do not extrapolate correctly into these
extreme out-of-sample regimes, in which case the "policy" coefficient above
is partly or wholly the model failing to absorb an independent price shock,
not evidence of hydro conduct. This is the identical contamination problem
the whole structural-model route was built to route around, one level more
sophisticated than the raw-price reduced-form probes, not demonstrated to
be solved by it.

**The next step that would actually distinguish the two stories, not yet
built:** run the identical test on the implied cost of a *non-hydro*
marginal-setting technology during the same two windows. If other
technologies show a similarly large "unexplained" shift, the effect above
is a market-wide artifact of the price regime, not something specific to
hydro. If hydro's shift is distinctly larger, that is real evidence of
conduct. Flagged as the clear next step rather than rushed.

**What would actually move this from "probably real" to "significant":**
more clusters, which means widening past the 25 basin-identified units
(most of the other 6 target units and any of the excluded non-basin-
identified `hydro_ugh` units never set the margin in this sample, so this
needs either a longer/different marginal-unit definition or accepting the
14-cascade ceiling) — not a quick fix, flagged rather than attempted here.

**2026-08-19: two basin-matching fixes, and a much bigger find in
Portugal.**

*Fixes to the Spanish basin match.* Checked all 19 previously-unmatched
`hydro_ugh` units by hand rather than guessing. Two real issues, the rest
genuinely unmappable: (1) `AG[UÜ]ERA` (dieresis only) missed `ASIAGU`
("HYDRO CUENCA AGÚERA", acute accent) on a character mismatch — fixed to
accept both; contributes zero marginal periods on its own (3.6 MW), so this
is a correctness fix, not a sample-size one. (2) `TERE` ("UGH. TER", 150.3
MW, the Ter river in Catalonia) was dropped entirely — no basin pattern for
"TER", and MITECO's "Cuencas Internas de Cataluña" demarcation (9 real
reservoirs including Sau and Susqueda) was never wired into
`AMBITO_TO_BASIN`, on the wrong assumption that no `hydro_ugh` unit mapped
there. Fixed in `hydro_water_value_precip.py` and
`hydro_water_value_reservoir.py` (and mirrored in the R script's ported
copies). Rerunning `hydro_marginal_hours.py --country ES`: **TERE
contributes 117 marginal periods (0.9% of the sample)** — a real if modest
addition, bigger than several units already in the sample. The other 17
unmatched units are all under 13 MW with mill/place names and no river cue
— not forced, per the same discipline the twin-layer matching in
`build_unit_agents.py` already applies.

*Portugal is a much bigger opportunity than expected, gated on one missing
data source.* Scoped with the same script (`--country PT`, 14 Portuguese
`tech=="hydro"` units, basin not required — Portuguese cascade names are
already clean: LIMA, CAVADO, TAMEGA, TEMON "Sistema Tejo-Mondego", GUADIA
"Bacia Hid. do Guadiana", MONDEGO, DOUSUP "Douro Internacional"):
**25,311 marginal-hydro periods, roughly double the Spanish sample**,
present every month, 22-36% of periods per year (vs. Spain's 8-25%) — eight
real contributing cascades (`ADOURO` 2,875 MW alone is bigger than any unit
in the Spanish sample), none of the "aggregation vehicle disguised as a
unit" problem the RDD hit, since these are OMIE's own large single-cascade
registrations.

**The blocker: MITECO is Spain-only, confirmed by checking its actual list
of demarcations** — nothing Portuguese in it, and this isn't a gap that a
shared-river shortcut can close (the Portuguese stretch of the Douro is
fed by different, Portuguese-administered dams MITECO simply doesn't
track). No Portuguese reservoir-level source exists anywhere in this repo
yet. `pf` (forward price) is a cheap, separate fix — `fetch_omip_forwards.py`
already supports `--zone PT`, just never run; fetch launched 2026-08-19,
result pending.

**2026-08-19: built, and it genuinely helps but is genuinely thin.**
`fetch_snirh_reservoirs_wayback.py` -- systematically fetches every
Wayback Machine capture (from 2018 onward) of the six basin pages
(Tejo=17, Douro=12, Lima=1551779250, Mondego=47, Cávado=107,
Guadiana=23), parses the reservoir list + fill percentage out of each,
and uses the page's own stated data month/year rather than the crawl
timestamp (the two can differ by over a year -- confirmed directly: one
March-2018 crawl of the Tejo page displays December-2016 data, meaning
the live site itself had gone stale for over a year before that crawl).
**1,006 reservoir-snapshot rows, 42 distinct reservoirs, all six target
basins**, `data/snirh/reservoirs_wayback.parquet`. About one in five
captures parses to zero rows -- checked directly, not silently dropped:
those specific captures rendered the page as a clickable image map
instead of a text table, so the percentages simply are not present in
that capture's HTML.

**The coverage number that actually matters: 16-18 basin-months out of 96
possible (2018-2025), ~17-19%.** Compare Spain's MITECO, which gives
essentially complete weekly coverage across the same window. Portuguese
hydro is marginal in some period during all 101 months of the sample
(per the earlier scoping), so most marginal periods will fall in a month
with no reservoir reading and get dropped, the same way unmatched rows
already get dropped for Spain -- just at a much higher rate here.
**2024 is a near-total blackout**: every basin except Lima has zero
captures that year, removing a full year outright. The Portuguese
OMIP forward price (`--zone PT`, launched the same day) finished
2018-2025 cleanly, so `pf` is solid for Portugal even though `Vol` is
not. A Portugal-side version of the structural model is buildable on
this, but the usable sample will be a fraction of Spain's 14,251 rows,
with a real hole in 2024 -- not yet built, flagged as the next step if
worth prioritising over other open threads.

**Why this matters beyond sample size.** Portugal is not covered by RDL
17/2021 (Spain-only), which makes it the natural control group for the
levy question — but `rq-gas-cap-conduct.md` already records that three
separate ES-vs-PT comparisons **on raw offer levels** failed exactly this
way: the two fleets differ enough in hydrology and composition that a
gas-price-shaped regressor "finds" an effect even in years with no policy.
This model doesn't compare raw offers across countries — it compares each
cascade's residual after controlling for its *own* basin's fundamentals,
which is precisely the confound that broke the earlier attempts. Worth
trying once Portuguese `Vol` exists; not a guarantee, since nothing has
tested whether this specific fix survives the placebo the raw-offer
version failed.

**2026-08-19: scoped a Portuguese reservoir source via browser automation
— real, confirmed to exist, no full-history public copy found.** Two
findings, both load-bearing:

1. **`snirh.apambiente.pt` itself (Portugal's MITECO-equivalent, run by
   APA) blocks every request, including from a real Chrome browser** — not
   just a bot-fingerprint issue (the kind a `requests`-header workaround
   fixes), since a full browser session with normal JS execution still got
   a flat 403 on the root domain and every page tried. Most likely
   geo-restricted to Portuguese IPs. A sibling portal, `sniamb.apambiente.pt`,
   loads fine, but its own reservoir-status link (`Análise e Monitorização
   > Água > Albufeiras de Águas Públicas`) redirects to an ArcGIS dashboard
   tracking *administrative approval phases* for reservoir management
   plans, not water levels — a dead end, though it confirmed real dam
   names (Castelo do Bode, Crestuma-Lever, Caniçada) along the way.
2. **The actual bulletin does exist and was found, twice, but only as
   fragments, both dead ArcGIS Online publications from APA's own account
   (`source: "Agência Portuguesa do Ambiente, I.P."`):**
   - `Armazenamento_nas_Albufeiras_de_Portugal_Continental_em_setembro_de_2022`
     — a Feature Service, but a **single-month snapshot** (September 2022
     only), basin-level (`Douro`, `Lima`, `Cávado e Ribeiras Costeiras`,
     `Guadiana`, ...), fields `Capacidade_Total_10m` (total capacity) and
     `Média_Mensal____` (monthly average fill %) — structurally identical
     to what MITECO gives for Spain, confirming the bulletin's shape.
   - `Albufeiras do Boletim SNIRH`, a web map built Jan–Feb 2019 and never
     touched again, with **10 monthly layers embedded directly as static
     data** (December 2018 – September 2019 only), **per-reservoir** (61
     named dams, e.g. `Alto Lindoso` for Lima, `Aguieira` for Mondego),
     with each dam's own SNIRH station code (`Codigo`, e.g. `02H/01A`) and
     a link back to the (blocked) SNIRH detail page for it
     (`salbufeirasimbolo=02H/01A`) — real station identifiers, confirming
     the exact per-reservoir vocabulary needed if API access is ever
     restored, but covering ten months out of the eight years needed.

**No public source covering 2018–2026 was found.** What exists confirms
the data itself is real and was once shared, just not as a maintained
open archive — closer to APA occasionally publishing a derived snapshot
than to MITECO's standing bulk download. Two ways forward, neither
attempted here: contact APA directly for a bulk historical export (a
reasonable ask for a research use case, and the two dead publications are
evidence someone at APA has already extracted this shape of data before),
or accept the geo-block and route a fetch through a Portuguese network
if one becomes available. Not pursued further without a decision on
which of those is worth the effort.

**2026-09-03: APA replied, and the geo-block hypothesis was exactly right.**
The reply came from APA's own security officer (*responsável da segurança*),
and is worth quoting because it settles the question rather than working
around it: SNIRH runs on 1990s technology, *"muito vulnerável e sem
atualizações possíveis"* — very vulnerable, with no updates possible — and
**for that reason access from outside Portugal is not permitted**. The 403 was
never a bot-fingerprint problem or a misconfiguration; it is a deliberate
control on a system they cannot patch.

**They offered a route: a fixed IP of ours can be whitelisted as an
exception.** Three things follow, and the third is the one that decides it.

1. **"Fixed" is the binding word.** A residential broadband address is
   normally dynamic, and if it rotates, access dies silently mid-fetch. This
   needs the university's static egress address, or a university VPN with a
   stable exit — a question for institutional IT, not something that can be
   determined from here.
2. **Do not route around the block instead.** A Portuguese VPN exit would
   defeat a control APA has now explicitly explained, on a system they have
   told us is unpatchable. The sanctioned route is on offer and is also the
   more stable one.
3. **A whitelisted IP would make this the least portable source in the
   repo.** `CLAUDE.md`'s standing convention is that all of `data/` is
   gitignored *because it is fully re-fetchable*; a fetcher that only runs
   from one network breaks that, in the same way the two browser-captured
   investing.com fetchers do — except worse, because it cannot be re-run from
   a different machine at all.

**So the bulk historical export remains the better ask, and it is still
open.** The four regional ARH offices in
[`email-apa-reservoir-data.md`](email-apa-reservoir-data.md) were asked for a
one-off file, which requires no network access, creates no ongoing dependency,
survives being moved between machines, and — given the security officer's
stated concern — exposes SNIRH less than opening a hole in it. Pursue both,
but lead with the export; take the IP whitelist as the fallback, and only once
a genuinely static address is confirmed to exist.

Institutional fit, briefly: SHL is one operator with de facto market power
over its region, so its FOC-with-market-power framing suits Spain's handful
of large hydro-owning firms (Iberdrola, Endesa) far better than the 44
fragmented UGH units as a whole — a small cascade with a thin capacity share
is closer to a price-taker, where the residual-demand-slope machinery may
not even be well identified. Iberian hydro is also far less snowpack-driven
than the Snowy Scheme, consistent with this design's own rain probe finding
no signal — expect `Snow` to carry little weight here, if it's kept at all.
No replication code exists for the paper (checked); the estimating equations
above are the only reusable artefact.

## 2026-08-21, the spill-window design: correctly signed, bootstrap-clearing,
## and killed by its own event study

The two probes above both failed on **rainfall or fill measured smoothly**. The
2026-08-17 note's own diagnosis of why — "a large reservoir can buffer a wet or
dry quarter without its marginal value moving much" — is an argument against
*smooth* hydrology, not against hydrology. So this probe tested the sharp,
state-dependent version: the **spill constraint**. Water arriving at a reservoir
with no headroom either generates or is lost over the weir, so its opportunity
cost collapses for a few days. Three changes from the earlier probes:

1. **Daily, not monthly.** Three-day cumulative basin precipitation against
   daily offers.
2. **The interaction is the object,** not a main effect. `beta < 0` on
   `shock x antecedent wetness` — an inflow shock should cut the offer *by more*
   where there was no room to store it.
3. **Both arms weather-driven.** Antecedent wetness is cumulative own-basin
   precipitation over t−90 to t−4, not realised fill, precisely so the
   2026-08-18 reverse-causality path is cut rather than reintroduced.

Identification is unit + **date** fixed effects. Date FE absorb the gas price,
carbon, the levy, the gas cap and national demand in one stroke; precipitation
varies across the nine basins within a single day, so the rain terms survive.
That within-auction comparison is what the monthly designs could not do.

Feasibility was checked before any regression: the joint cell is populated —
2,007 unit-days of top-decile three-day rain at above-median basin fill, 219
distinct episodes, spread over all nine basins and all nine years, with the
low-fill contrast arm equally populated (2,186 unit-days). Power was not the
constraint.

`scripts/analysis/hydro_spill_window_did.py`, 58,815 unit-days.

### It looks like it works

| block | outcome | beta | t | p_wcb |
|---|---|---|---|---|
| shock × wet90 | marginal accepted | −0.173 | −2.55 | 0.148 |
| shock × wet90 | 10th-pct offer | −0.056 | −1.29 | 0.266 |
| **placebo** shock × wet90 | marginal accepted | −0.051 | −0.53 | 0.609 |
| shock × **1(fill in basin's top quartile)** | marginal accepted | **−0.302** | **−3.71** | **0.039** |

Every offer outcome carries the predicted sign, the wrong-basin placebo is null
on all four — the basin-specificity the 2026-08-17 probe never produced — and
the threshold form clears a wild cluster bootstrap on nine basins. No earlier
hydro probe in this repo got this far.

### The event study says it is not real

Split by fill regime, the shock-day coefficient in the **high-fill** arm — the
arm where a spill constraint does all of its work — is **+0.008 (t = 0.16)**.
Nothing. The whole interaction comes from the **low-fill** arm, which jumps
**+0.159 (t = 3.48)** on the shock day. A negative interaction assembled from a
positive low-fill response and a zero high-fill response is arithmetic, not a
spill constraint.

On the 10th-percentile outcome the high-fill arm carries large negative
coefficients at k = −5, −4, −3, −2 (t to −2.10) and a k = 0 sitting right on
that path: a drift already under way, not an event.

Two checks close it:

- **Not a censoring artefact.** The +0.13 shock effect on the marginal accepted
  offer is not the unit climbing its own offer curve as the shock moves its
  volume — adding log cleared MWh as a control moves it from +0.131 to +0.137.
  Rain genuinely raises the price at which these plants agree to run. Wrong sign
  for a cost shifter, and now the **third** wrong-signed hydro result here.
- **The one robust finding is physical.** In basins already in their top fill
  quartile, extreme rain cuts *offered* volume by 13% (p_wcb = 0.008, the only
  result that clears the bootstrap comfortably). Plants withdraw capacity during
  floods — spill bypass, ramping limits, flood-control operation. A supply
  restriction, not a water value, and one of ~30 tests in that file.

### Two lessons worth more than the result

**With nine clusters, a correctly signed interaction that clears a bootstrap is
not enough.** The event study is what separated a mechanism from an arithmetic
artefact. Run it before believing any single coefficient from this family.

**Day-ahead bids are submitted against a weather *forecast*.** Realised
precipitation is not a surprise to a plant bidding the day before — see
[`literature-extreme-weather-economics.md`](literature-extreme-weather-economics.md)
§3.2. Any future version of this should treat the forecast, not the realisation,
as the treatment; that is a design flaw shared by all three probes above and it
was not recognised until the literature pass.
