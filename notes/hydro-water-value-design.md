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
