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
