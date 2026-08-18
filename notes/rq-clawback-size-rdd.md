# A size-threshold RDD on the RDL 17/2021 clawback

Written 2026-08-18, alongside the ex-post-optimal-bid refinement added to
`rq-gas-cap-conduct.md` the same day. This is the second candidate design
flagged there — a companion to the gas-cap conduct question, not a
replacement, and it targets the harder-to-identify half of the market: hydro,
nuclear and merchant renewables, where `hydro-water-value-design.md` has
already spent three probes failing to find a clean reduced-form cost proxy.

## The policy and why a threshold, not a date

RDL 17/2021 (16 September 2021 → 31 December 2023, see
`candidate-natural-experiments.md`) claws back revenue from peninsular
non-emitting generation **above 10 MW** that has no specific remuneration
framework and won no renewable auction — in practice nuclear, hydro, and
merchant (unsubsidised) renewables. Installations **under 10 MW** are exempt.

Every date-based design on this policy inherits the same problem: RDL
17/2021 runs to 31 December 2023 and the gas cap (RDL 10/2022) begins 15 June
2022, so the two overlap for **18.5 months**. In the overlap, the clawback's
treated group (hydro, nuclear, merchant renewables) is simultaneously exposed
to the gas cap's spillover effect on the price they face — neither policy
serves as a clean control for the other in event-study time (see
`candidate-natural-experiments.md`'s "this was recorded backwards" section).

**A size-threshold RDD does not have this problem, because it isn't a time
comparison at all.** A unit just above 10 MW versus just below it, compared
in the *same* week, is a valid contrast regardless of what else is happening
in time — both units face the same gas cap spillover, the same demand
shocks, the same everything except treatment status. This is the design's
whole appeal: it sidesteps the overlap by construction rather than by
argument.

## The power question, checked directly rather than assumed

`candidate-natural-experiments.md` flagged this as open: "whether enough
small units bid near the margin is an open empirical question." Checked
2026-08-18 against `unit_agents.parquet`'s `max_power_mw` (from `cab`,
already validated against published capacity):

| technology group | units within ±5 MW of 10 MW | ±3 MW | ±2 MW | ±1 MW |
|---|---|---|---|---|
| hydro + hydro_ugh + nuclear | 26 | 9 | 5 | 3 |
| wind + solar | 254 | 137 | 103 | 74 |
| **all candidate-treated tech** | **280** | **146** | **108** | **77** |

**Density is not the constraint — classification is.** Hydro and nuclear
alone are too thin for a standalone RDD (5 units within ±2 MW, out of 144
hydro/nuclear units total — most Spanish hydro is small: median unit size is
8.05 MW, so the bulk of the fleet sits *below* the threshold already, which
is itself worth knowing). Wind and solar supply ample mass — 108 units within
±2 MW — but **we cannot yet tell which of them are actually treated.**
RDL 17/2021 exempts renewables under a specific remuneration framework
(RECORE), and neither `cab`, ESIOS, nor `unit_agents.parquet`'s `regime`
column (which encodes the older *régimen especial/ordinario* split, not the
post-2014 RD 413/2014 remuneration-framework distinction) carries that flag.
This is the identical gap already logged in `literature-iberian-exception.md`
for the cogeneration side of the gas cap: "the RECORE split... is not visible
in ESIOS's taxonomy... needs the CNMC remuneration registry." It now binds
here too, and harder, because it gates the entire wind/solar half of the
running-variable mass rather than one narrow technology.

**So the concrete next step is not more data density — it's the CNMC
remuneration-framework registry**, to split wind/solar units into merchant
(treated) versus RECORE-remunerated (untreated, control-group-ineligible).
Until that's in hand, the RDD is only demonstrably powered on hydro/nuclear,
and thinly (n≈5–9 near the threshold) — worth running as a first pass to see
whether the coefficient is even estimable, but not worth over-interpreting
a null from that alone.

## Outcome variable — two tiers, and an honest caveat on the second

**Tier 1, no cost model needed.** Raw offer level or bid steepness at the
threshold — does a unit just above 10 MW bid systematically higher (softer,
i.e. resembling curtailment-avoidance under the clawback's tax on
inframarginal rent) than one just below. Buildable now from `curva_pbc_uof`
alone, restricted to non-splitting hours.

**Tier 2, the `PctAchieved`/ex-post-optimal-bid-gap outcome from
`rq-gas-cap-conduct.md`'s 2026-08-18 section.** This is a materially harder
transplant here than on the gas-cap's CCGT/coal side, and it does **not**
carry over cleanly to wind/solar:

- For **hydro**, the ex-post optimal bid needs `MC_i(q)` — hydro's water
  opportunity cost — which is exactly the object three reduced-form probes
  in `hydro-water-value-design.md` have failed to recover, and which is
  currently "structural or nothing." Tier 2 for hydro is gated on that model
  existing, not on anything specific to this design.
- For **nuclear**, marginal cost is close to a known engineering constant
  (fuel cost per MWh is small and stable) — Tier 2 is plausible here with
  little new work, though the sample is the thinnest of all (a handful of
  Spanish nuclear units, most far from 10 MW in nameplate terms — worth
  checking whether *any* nuclear unit sits near the threshold before
  building this).
- For **wind and solar**, "marginal cost" in the HP2008 sense barely applies.
  Their private marginal cost of production is at or near zero; what
  disciplines their bidding near the margin is a different object entirely —
  curtailment risk, negative-price avoidance, or (post-clawback) the
  incentive to bid strategically to reduce metered inframarginal revenue.
  An ex-post-optimal-bid benchmark built on a near-zero `MC_i` would mostly
  just recover "bid at zero," which is not an interesting benchmark to test
  conduct against. **Tier 2 is not a good fit for the wind/solar side of
  this design and should not be forced onto it** — Tier 1 (raw bid level) is
  the right outcome for that half, at least until a wind/solar-specific
  theory of what "optimal" bidding even means under the clawback is worked
  out separately.

## Specification

Sharp RDD, local linear, running variable `max_power_mw` centred at 10:

```
y_i = α + τ·1[max_power_mw_i ≥ 10] + β1·(max_power_mw_i − 10)
        + β2·(max_power_mw_i − 10)·1[max_power_mw_i ≥ 10] + tech_i + ε_i
```

with a data-driven bandwidth (Calonico-Cattaneo-Titiunik or similar) rather
than the fixed ±1/±2/±5 MW windows used above for the power check only.
`tech_i` fixed effects (hydro vs. nuclear vs. merchant wind/solar, once
classified) given the technology composition changes across the window in
the density table above.

**Two checks to run before trusting any estimate, both standard for a
size-threshold RDD and both worth taking seriously in this specific
institutional context:**

1. **A density/manipulation check (McCrary-style) on `max_power_mw` at 10.**
   Plant sizing to sit just under a regulatory MW threshold is a well-known
   phenomenon in Spanish renewables (10 MW and other round-number thresholds
   also gate environmental-permitting simplifications, connection-cost rules,
   and other unrelated regimes) — bunching just below 10 could easily
   predate RDL 17/2021 for reasons that have nothing to do with this policy.
2. **The same density check run on a pre-policy sample (before 16 September
   2021).** If bunching at 10 MW already existed before the clawback, it is
   not evidence the clawback itself is being gamed, and does not disqualify
   the design — sorting has to be attributable to *this* policy specifically,
   not to the threshold in general, since developers cannot retroactively
   resize plants built years earlier in response to a 2021 decree.

## Threats

1. **Classification of the wind/solar treated group — see above.** The
   binding constraint on this whole design; needs the CNMC registry.
2. **`max_power_mw` from `cab` may not exactly match the regulatory
   "potencia instalada" the decree uses as its running variable** — `cab`'s
   figure is validated against published nameplate capacity (Ascó 1, 1028.0
   vs. published ~1032), but has not specifically been checked against the
   legal definition RDL 17/2021 itself uses, which could differ (net vs.
   gross capacity, or measured at a different point).
3. **Portfolio units break the running variable.** Some OMIE units are
   whole-cascade or portfolio registrations well above 10 MW even when
   individual plants inside them are not (`ADOURO`, `EDPSVD1` — see
   CLAUDE.md's "cab names identify the bidding agent, not the plant owner").
   The regulatory threshold is presumably applied per *plant*, not per OMIE
   bidding unit, so a portfolio unit's `max_power_mw` may not correctly
   locate it relative to 10 MW even if the number itself is accurate at the
   unit level. Worth checking how many of the units near the threshold are
   single-plant registrations versus portfolios before trusting the running
   variable.
4. **Manipulation, per the density checks above** — not yet run.

## Build order

1. Run the McCrary-style density check on `max_power_mw` at 10, pre- and
   post-policy, before anything else — this is cheap and could kill the
   design outright.
2. Hydro/nuclear Tier 1 (raw offer level) as the first estimate — thin
   sample, but needs nothing new and tells us quickly whether there's
   anything here at all.
3. Scope the CNMC remuneration-framework registry fetch for the wind/solar
   classification — the actual unlock for the design's statistical power.
4. Tier 2 stays gated on the structural water-value model (hydro) or a
   separate wind/solar bidding-motive model (not started) — not a near-term
   next step.
