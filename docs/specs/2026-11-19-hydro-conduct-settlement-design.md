# Settling the hydro conduct cells: gates before any run (pre-registration, 2026-11-19)

**Status: registered 2026-11-19 with this commit. Gates G1 and G3 were computed from stored outputs before any new
estimate (`scripts/analysis/hydro_settlement_gates.py` → `outputs/tables/hydro_settlement_gates.csv`). Both fail, so
by the rule below no estimation run follows.** Answers for the chapter: `notes/hydro-conduct-settlement.md`.

Conduct condition (as `notes/rq-price-taking-simulation.md`): offer − cost = β·X, X = net auction position / |slope
of residual demand| (the Nash markup, €/MWh). β = 0 price-taking, β = 1 Nash. Estimator: step estimator, at-cost
instrument Zb, unit × month effects, `level` selection control. Read against ten simulated price-taker seeds.

## Why gates, and why only on unread data
The pooled hydro estimate (+0.06 [−0.05, 0.15]) and the 2024–25 cell (+0.19 [0.08, 0.33]) were read on 2026-10-28.
A new rule chosen now and applied to the same rows would be chosen knowing the answer. So the rules are the ones
already fixed (2026-10-08), and a run is justified only if it could change the answer with adequate probability:
either a new design on the same rows whose acceptance does not depend on the known estimate, or new data.

## Rules (unchanged, fixed 2026-10-08)
- **Differs** (`rq-price-taking-simulation.md` §5): the actual Anderson–Rubin (AR) 95% set misses the band [min, max]
  of the seeds' estimates.
- **Price-taking within δ = 0.1** (§7, the rule that accepted thermal, row 1.1 / O7): accept when
  AR_hi − min(seeds) < 0.1. One-sided; allows any bias inside the band.

## Gates (fixed here)
- **G1 (item 1, pooled hydro).** A run that aims to establish price-taking goes ahead only if, **with the firms exact
  price-takers** (actual centred on the seeds' mean), the §7 rule accepts with probability ≥ 0.80.
- **G3 (item 3, 2024–25).** A run that aims to decide the borderline cell goes ahead only if, **on data not yet read**
  (2025-10-01 → 2026-05-31, 15-minute day-ahead periods), the reading rule detects a departure of the cell's own
  size (β = +0.19) with probability ≥ 0.80.
- Approximations (stated in the script): AR set ≈ b ± 1.96 se (F 79–530); se and seeds' spread scale with
  1/√months; a new month carries as much information as an old one (the 4× count for 15-minute months is reported as
  an optimistic bound). 200,000 draws.

## Results (computed 2026-11-19, before any run)

**G1 fails.** Probability the rule accepts, if hydro is exactly price-taking:

| scenario | se | P(accept) |
|---|---|---|
| current data, 10 seeds | 0.054 | **0.18** |
| 20 seeds / 50 seeds | 0.054 | 0.13 / 0.09 |
| bids to 2026-05 (89 months) | 0.051 | 0.20 |
| same, 15-minute months counted 4× (113) | 0.046 | 0.27 |
| perfect bias correction (band shrunk to the seeds' mean) | 0.054 | 0.46 |
| needed for 0.80 | 0.027 | 4.1× today's data |

More seeds *lower* the probability: the rule subtracts the band's minimum, which can only fall as seeds are added.
Extending the bids adds 10% of the rows. Even a perfect bias correction leaves the AR set's own width
(±0.11) too wide for δ = 0.1.

**G3 fails.** Probability the reading rule finds a departure:

| data | if β = +0.19 (cell's point) | if β = +0.25 (2019–21H1 size) | if price-taking |
|---|---|---|---|
| 8 fresh months alone | **0.10** | 0.23 | 0.00 |
| 29 months, reusing the 21 already read (not a clean test) | 0.60 | 0.76 | 0.14 |

Also: under the reading rule "does not differ" is final with respect to seeds, since more seeds only widen the band.

**Consequence: no run.** Extending the step engine to 15-minute periods (it is hour-based; caches end 2025-09) is not
warranted for either cell. Items 2 and 4 need no run (`notes/hydro-conduct-settlement.md` §2, §4).

## What would change this
Only a design with about four times the information per cell, or a sharper selection control that also narrows the AR
set. Neither is in hand. Not pursued: the thesis headline is demand-side (decision 2026-11-19); hydro conduct enters
only the descriptive chapter.
