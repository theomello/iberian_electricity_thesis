# Where did market power go? A descriptive account of price formation in MIBEL, 2018–2026 — design

**Date:** 2026-08-24
**Status:** DESIGN — approved, not yet implemented
**Supersedes:** nothing. Complements `docs/specs/2026-08-07-spain-market-data-design.md`.

## Context

Six causal designs have been built and withdrawn in this repo (`git log`: the
levy reduced form, differential renewable exposure, bid steepness, the markup
instrumental-variable, gas-cap pass-through, clawback intensity). Their own
scorecard, in [`notes/rq-heat-demand-conduct.md`](../../notes/rq-heat-demand-conduct.md)
§8.3, diagnoses the common cause:

> Every conduct estimate is null or wrong-signed; every precisely estimated
> result is merit order. … **the markup measure, not the shock, is the binding
> constraint.**

`net_load_iv.py` had a first-stage F of 184.8 and still returned nulls. The
problem was never identification power. It was that an implied marginal cost
omitting operations & maintenance, part-load efficiency and start-up costs
cannot support a markup test at this resolution.

This design takes the opposite route deliberately: **a descriptive chapter
whose every statistic is cost-free.** It is not a retreat from the causal
question. It is the step that decides which causal question is worth asking,
by establishing what actually changed and where.

---

## §1 — The question, and the identity it rests on

**RQ: As variable renewable energy (VRE) went from 21% to 38% of Spanish
generation between 2018 and 2026, how did the structure of price formation in
MIBEL change — and does aggregate concentration still describe it?**

MIBEL is the Iberian electricity market (*Mercado Ibérico de Electricidad*),
which clears Spain and Portugal jointly against one merged bid stack.

The chapter is organised around one identity — Kellogg & Reguant (2021)
eq. 23 rearranged. For firm *i* in market period *t*:

```
L_it = (p*_t − C′_it) / p*_t  =  q_it / (|RD′_it| · p*_t)  ≡  s_it / η_t
```

where `RD_it(p) = D_t(p) − Σ_{j≠i} S_jt(p)` is residual demand, `p*_t` the
clearing price, `q_it` firm *i*'s cleared volume, `s_it` its share and `η_t`
the residual demand elasticity at market scale.

Every statistic in the chapter is a facet of one of three objects:

- **s** — who supplies, and where in the stack;
- **η** — how steep residual demand is *where the price is actually set*;
- **θ** — how much output is already sold forward, which scales the incentive
  (Wolak 2000; Hortaçsu & Puller 2008; Kellogg & Reguant eq. 24).

**No marginal cost appears anywhere.** That is the design's central commitment
and the reason it does not inherit the failure mode above.

### The puzzle the chapter documents

Measured on the full bid archive (`outputs/tables/residual_demand_slope_full.parquet`,
79,036 periods), median η by year:

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| 1.83 | 1.46 | 0.97 | 1.21 | 0.89 | 0.85 | 0.66 | 0.59 | 0.45 |

Over the same window the CNMC's published Herfindahl–Hirschman Index (HHI) on
generation shares **fell** from 1314 to 1007. Under the identity these pull in
opposite directions, and the net effect is that the *bound* on markups roughly
doubled.

**The chapter's claim is that this is a relocation, not a paradox**: the
price-setting margin moved to a thinner, differently-owned part of the stack,
and aggregate concentration has become a decreasingly informative statistic
about this market.

### Why this framing rather than the alternatives

Two others were considered and rejected. "The disappearing evening
competitor" (a Jha & Leslie start-up-cost story) is sharper and more novel but
has no fallback — if the evening pattern is flat there is nothing left. A pure
"anatomy of the supply curve" is safest and most reusable but is documentation,
not a question.

The chosen framing **survives its own null**: if near-marginal concentration
does *not* rise, that is still a publishable descriptive fact — the steepening
is entirely a supply-curve-shape phenomenon rather than an ownership one — and
the chapter stands. It also contains the evening-ramp test as §4 figure 4 and
the supply-curve anatomy as its mechanism.

---

## §2 — The five measured series

| # | Series | Source | New work |
|---|---|---|---|
| 1 | `η_t` — market residual-demand elasticity at `p*` | built, 79,036 periods | none; re-used |
| 2 | `η_it`, `|RD′_it|` — **firm-specific** slope, ability and incentive indices | bids `O` + `unit_agents.parquet` | one sweep |
| 3 | `HHI_total`, `HHI_margin` | bids `C`/`O` + `unit_agents.parquet` | same sweep |
| 4 | `θ_it` — bilateral contract position | `pdbf`, `role_code == "4"` | join |
| 5 | Supply-curve anatomy | bids `O` + `cab` | partly exists |

### 2.1 Concentration: measured twice, inside the same data

The existing supervisor slide pairs an internally measured η with CNMC's
**externally published** HHI. That is apples-to-oranges in a chapter whose
whole point is the two series moving apart, and it truncates the window at 2023.
Worse, per `CLAUDE.md`, CNMC computes shares on **PDBF** — the operating
schedule, which is 1.73× day-ahead cleared volume on January 2024 — not on the
day-ahead auction.

Both are therefore rebuilt from our own data:

- **`HHI_total`** — from cleared day-ahead volume per period, firm-attributed
  through `unit_agents.parquet`.
- **`HHI_margin`** — restricted to offers within ±h €/MWh of the clearing
  price, i.e. concentration *among the suppliers who could have set the price*.

**The testable prediction:** `HHI_total` falls, matching CNMC, while
`HHI_margin` rises. If it holds, the divergence resolves into a single story.
CNMC's series is retained as external validation only, never as the headline.

### 2.2 Firm-level residual demand, and why it is cheap

The existing η is the residual demand facing an *infinitesimal* participant —
a lower bound on every real firm's steepness. The theory object is
firm-specific. Building it is much cheaper than it looks:

```
|RD′_it| = (band MW, all offers) − (firm i's own sell MW in band)
```

so **one extra `groupby(date, period, firm)` inside the band yields every
firm's slope at once** — not one sweep per firm. And because the market clears
at `p*`, residual demand there equals firm *i*'s own cleared volume:
`RD_i(p*) = q_it`. Both McRae & Wolak indices follow directly:

```
ability    η_i   = q_it / (100 · |RD′_it|)              €/MWh per 1% withheld
incentive  η_i^C = η_i · (q_it − θ_it) / q_it
```

Built for the parent firms flagged `is_major` in `unit_agents.parquet` — the
~8–12 with meaningful dispatchable plant.

### 2.3 θ is a proxy and must be labelled one

`pdbf`'s `role_code == "4"` is the bilateral contract, read directly (its sell
and buy legs match to 0.0000 in every month tested — the identity a subtraction
of PDBF minus PDBC cannot check). But it captures **physical** bilateral
contracts only and misses financial hedges entirely. Since what matters is
whether *revenue* is fixed, not whether electrons flow bilaterally, that
omission is the more serious one. Bound θ; do not claim to measure it.

---

## §3 — Pipeline and components

Four new scripts under `scripts/analysis/`, each with one job, following
existing repo conventions. Nothing re-fetches. Nothing writes to `data/`.

| Script | Job | Output |
|---|---|---|
| `residual_demand_firm.py` | the one expensive sweep: firm-specific slope, ability, incentive | `outputs/tables/firm_residual_demand_full.parquet`, keyed `(date, period, firm)` |
| `concentration_margin.py` | `HHI_total` and `HHI_margin` per period | `outputs/tables/concentration_panel.parquet` |
| `supply_curve_anatomy.py` | stack shape by year: offered MW by price bucket, share ≤0 €/MWh, band density, marginal technology, whole-day withdrawals | `outputs/tables/supply_anatomy_panel.parquet` |
| `descriptive_figures.py` | all six figures, re-derived from the panels above | `outputs/figures/` |

**`residual_demand_firm.py` extends `month_slopes()` in the existing
`residual_demand_slope.py` rather than duplicating it** — same band logic, same
filters, one extra firm grouping. The existing vectorised structure (merge `p*`
onto offer rows, band test as one boolean column, each bandwidth a single
groupby) is what makes the full archive tractable; a per-period loop does not
survive 89,000 periods.

### Traps this pipeline must respect

Each is documented in `CLAUDE.md` and each fails silently:

- **`O` and `C` rows are not additive.** `O` is the full submitted curve, `C`
  the cleared portion. Filter to `O` for supply functions, `C` for cleared
  quantities; summing both double-counts every accepted bid.
- **Supply is spread over four roles.** Use `generation`, `generation_large`,
  `storage_mixed`, `pumping` — see `SUPPLY_ROLES` in `capacity_quantile_offer.py`.
  Filtering on `generation` alone drops all 62 combined-cycle units, all 7
  nuclear, and every pumped-storage unit, leaving only wind and solar, which
  offer at zero.
- **PDBF has several rows per unit-period, one per role code.** `(date, period,
  unit)` is not a key. Aggregate before joining or the auction volume fans out.
- **`schedule_mw` is average MW, not MWh.** Energy is
  `schedule_mw * resolution_min / 60`.
- **`country` in the bid files does not identify a unit's country** — ~95% is
  tagged `MI`. Use `unit_registry.parquet`.

---

## §4 — Cuts and figures

Every series from §2 is reported three ways: **by year** (the spine), **by year
× hour-of-day** (the duck curve — midday solar trough against evening ramp),
and **by year × net-load decile** (the system state that determines who is
marginal). Separating the last two matters: it shows whether an hour-of-day
pattern is economics or a clock artefact.

| # | Figure | What it shows |
|---|---|---|
| 1 | The divergence, rebuilt internally | η, `HHI_total`, `HHI_margin` on a common 2018 = 100 base; CNMC overlaid as external validation; policy windows shaded |
| 2 | Where the price is set | offered MW density within ±h of `p*`, by year — the mechanism behind η in one picture |
| 3 | The stack's shape | offered supply by price bucket, by year; mass accumulating at ≤0 €/MWh |
| 4 | η by hour × year | the Jha & Leslie test: does the collapse concentrate in the evening ramp? |
| 5 | Firm ability and incentive | η_i and η_i^C for major firms — whose position steepened |
| 6 | Demand predictability | forecast and schedule error dispersion by year (see §7) |

### The crisis window

2021–2023 holds the gas crisis, the levy (RDL 17/2021, 16 Sep 2021 → 31 Dec
2023) and the gas cap (RDL 10/2022, 15 Jun 2022 → 31 Dec 2023). η is **not
monotone** through it — it rises to 1.21 in 2021 before falling again.

The chapter reports the full series with both policy windows and the gas spike
marked, then **re-estimates the time trend on 2018–2020 + 2024–2026 only**. If
the decline holds on the clean years, the crisis is an episode on top of a
secular trend rather than the cause of it. That is a claim the chapter must
defend before anyone reads a mechanism into the series.

---

## §5 — Validation: what would falsify each claim

Four checks, each able to kill a claim rather than decorate it.

**Bandwidth sensitivity.** Every η and `HHI_margin` reported at
h ∈ {1, 2, 5, 10} €/MWh. If the divergence appears at only one bandwidth it is
an artefact of the band, not of the market.

**Clean-years trend.** As §4. If the decline vanishes without 2021–2023, the
chapter's spine is a crisis story and must be rewritten as one.

**The 15-minute break.** 2025-10-01 quadruples the period count and
mechanically thins any fixed-€ band. η is reported separately for the two
resolution eras, and any 2026 claim is checked against a 15-minute-only sample.
Note that each dataset has its own resolution date — intraday June 2025, PDBF
2025-03-19, day-ahead 2025-10-01 — so `resolution_min` is read per file.

**Coverage, measured on the near-marginal band.** The firm mapping reaches
89.1% of near-marginal offered volume, not 100%. `HHI_margin` is computed on
mapped volume only and the unmapped share is reported per year; if it drifts,
the HHI trend is partly a mapping artefact. Coverage is measured on the band,
never on total volume — a 5 GW unit offering at 0 €/MWh is inframarginal almost
always and flatters any total-volume coverage figure.

### Selection effects stated in the text, not silently filtered

- **Market-splitting periods** (~6.7%) are dropped by the existing filters, and
  they are precisely the congested hours when residual demand is steepest and
  ownership most concentrated. Every concentration and steepness figure is
  therefore a **lower bound**.
- **The 61-day 2025 dropout cluster** (2025-03-19 → 2025-06-09) is not randomly
  distributed, so dropping those days thins 2025 in a correlated way.
- **Zero-price periods** are excluded upstream because η and the Lerner index
  are undefined at `p* = 0`. Their share grows toward 21% of periods by 2026,
  so the recent years describe a shrinking subset of hours. **The share itself
  is reported as a result**, not hidden as a filter.

---

## §6 — Deliverables

- This spec.
- Four scripts and four panels, per §3.
- Six figures under `outputs/figures/`.
- `notes/rq-descriptive-price-formation.md` — the running research note in this
  repo's existing style, where results and failures get recorded as they land.

---

## §7 — The demand-forecast probe: one design withdrawn, one demoted, one fact kept

A forecast-residual design was proposed during brainstorming: take the residual
of a demand forecast and study its effect on a realised outcome. It was probed
before being written in. The probe wrote nothing permanent; its findings are
recorded here so neither design is re-attempted from scratch.

### 7.1 Vintage: passes

REE's demand forecast (`data/ree/ree_demand_forecast_5min.parquet`) has mean
absolute error **297.5 MW** against the market's own day-ahead schedule at
**292.1 MW** — a ratio of 1.02. A nowcast would be dramatically better than a
D−1 schedule; this one is no better at all. The within-hour check agrees: the
forecast's intra-hour deviations correlate 0.81 with realised and have *larger*
amplitude (464 vs 422 MW) — a smooth modelled ramp overshooting the real one,
not a tracking nowcast. **It is a day-ahead vintage.**

This matters because it could not be established from the data directly: the
series was fetched retrospectively on 2026-08-21, one vintage per day.

### 7.2 Design 1 — forecast level as a day-ahead demand shifter: WITHDRAWN

The idea was to instrument the *movement-along-the-curve* channel that
`eta_shift_share.py` currently separates with a counterfactual-price device.

**It fails on the exclusion restriction, not on vintage.** Suppliers observe
the same D−1 demand forecast the retailers do. It therefore shifts the clearing
point **and** the submitted supply curve simultaneously — which is precisely the
mechanical-versus-behavioural distinction it was meant to break. The only
component genuinely unknown to suppliers at gate closure is the residual, and
that is revealed *after* the day-ahead auction has cleared.

There is no wedge here to identify with. Do not re-attempt in this form.

### 7.3 Design 2 — residual as an intraday surprise: DEMOTED, kept as one fact

The residual is revealed after day-ahead gate closure, so it cannot move
day-ahead bids; it is exactly what the intraday market exists to correct.
Regressing the day-ahead/intraday premium on the signed surprise, standard
errors clustered by day:

| | €/MWh per GW of surprise | % of price per GW |
|---|---|---|
| 2018–2020 | −0.694 (0.248), t = −2.80 | −0.822 (0.715), t = −1.15 |
| 2023–2025 | −1.407 (0.487), t = −2.89 | −3.584 (4.525), t = −0.79 |

Negative is the economically correct sign: demand above forecast must be bought
in intraday, pushing the intraday price up against the day-ahead.

**But the apparent doubling is mostly a price-level artefact** — median price
went 35–61 €/MWh early to 67–93 late — and once scaled by price neither period
is significant. The sample also ends **2025-09-30**, because the
`resolution_min == 60` filter excludes the whole 15-minute era, which is exactly
where the margin is thinnest.

So: *"a demand surprise moves the intraday price by roughly 0.7–1.4 €/MWh per
GW, correctly signed"* is defensible and belongs in §5 as supporting evidence.
*"Absorption capacity changed as VRE grew"* is **not** supported and must not be
claimed.

### 7.4 The fact worth keeping: Spanish demand became harder to forecast

Hourly forecast-error standard deviation, clean sample (excluding from
2025-12-12, 2025Q2 and 2023Q1 — see `CLAUDE.md`):

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|
| 143 | 127 | 155 | 157 | **708** | 260 | 313 | 369 |

**Two independent predictors degraded in step.** The market's own schedule
error follows the same path (sd 250 → 421 MW on the same sample). When two
unrelated forecasters get worse together, the thing being predicted got harder
rather than one model decaying. That is a clean descriptive fact requiring no
identification claim, and it becomes §4 figure 6.

Likely candidates — behind-the-meter solar making *net* demand noisier, and
2022's price-driven demand response — are **unverified** and are to be stated
as candidates, not causes.

### 7.5 What would revive the forecast idea

The shock that matters is wind, not demand. Wind forecast error is ≥2.6× the
heat shock on a common net-load basis, while the demand residual's clean-quarter
sd (127–369 MW) is *smaller than* the 537 MW heat shock that already returned a
null. Measuring it properly needs ESIOS indicator 541, which requires a token —
`notes/email-esios-token.md` is already drafted for it. Do not build on the
persistence-residual proxy (R² = 0.264).

---

## References anchoring the design

- Kellogg, R. & Reguant, M. (2021), Handbook ch. 17 §4.2, pp. 691–702 —
  eqs. 23–26, the residual-demand toolkit. Fig. 2 (p. 696) is Spanish data.
- Hortaçsu, A. & Perrigne, I. (2021), Handbook ch. 11 §7, pp. 143–149 — the
  auction-theoretic derivation and the contract-position sign flip.
- Hortaçsu, A. & Puller, S. (2008), *RAND J. Econ.* 39(1) — contract positions
  from bid data; small firms bid "excessively steep".
- McRae, S. & Wolak, F., "How do firms exercise unilateral market power?" —
  eq. 3.6, the finite-difference slope recipe for step-function bids; eqs. 3.4
  and 3.10, the ability and contract-adjusted incentive indices.
- Jha, A. & Leslie, G., "Start-up Costs and Market Power" (SSRN 3603627) —
  static markups overstate rents when start-up costs are ignored; the evening
  ramp mechanism tested in §4 figure 4.
- Ito, K. & Reguant, M. (2016), *AER* 106(7) — sequential markets, the source of
  §7.3's premium.
- Reguant, M. (2014) — the minimum-income condition as a declared start-up cost.
