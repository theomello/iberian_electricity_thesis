# Clean-dirty substitution in installed capacity (proposal)

**Status: proposed 2026-11-16, not yet confirmed by the user. Nothing is estimated. Only step zero (the noise and feasibility check) is run, and the thresholds are fixed in the script header and committed before that run. The elasticity is not estimated until the user confirms this spec.**

**In one example.** Suppose Andalucía and Cantabria both see gas get dearer. Andalucía has strong sun and wind (a MW of clean capacity there produces, say, 30% more energy than the average region's MW), Cantabria weak. Gas dearer lifts the power price, so a clean MW in Andalucía earns more extra than one in Cantabria. If the clean/dirty capacity ratio grows faster in Andalucía than Cantabria, in the years after the gas rise, that is substitution toward clean capacity. How much faster per unit of relative return is the long-run clean-dirty elasticity, the investment analogue of Papageorgiou-Saam-Schulte (2017).

## Question
How strongly does the regional mix of clean (wind, PV) against dirty (combined cycle, coal) installed capacity move with the relative return to clean capacity, 2-4 years after the return changes?

## Structure
- Panel: peninsular autonomous communities × months, `data/esios/esios_installed_capacity.parquet` (ESIOS 1485 wind, 1486 PV; 1483 combined cycle, 1478 coal; pumped storage 1476 is outside). Peninsular = every region except Baleares, Canarias, Ceuta, Melilla, which leaves **15** regions, not 19. Only regions with combined-cycle capacity in every month enter, so the ratio is defined: **11** (Andalucía, Aragón, Castilla-La Mancha, Cataluña, Navarra, Valencia, Galicia, La Rioja, País Vasco, Asturias, Murcia).
- Outcome `y_rt = ln[(wind + PV)/(combined cycle + coal)]`, months 2021-01 → 2026-08 (68). Month 2026-09 is dropped (partial at source).
- Relative-return measure `x_rt = q_rt × s_t`. `q_rt`: region's realised clean resource quality, the trailing 12-month (to t−1) measured output per MW of wind and PV (provincial ESIOS 1159/1161, summed to region), each relative to the 11-region pooled value, averaged 50/50 (a technology below 100 MW average capacity in the window is left out of that region's index). `s_t`: common dirty-cost shock, `ln` of the combined-cycle running cost `MIBGAS/0.55 + 0.37 × EUA` (monthly mean), averaged over months t−35 … t−24: the shock that investors faced 2-3 years before the capacity stock at t.
- Instrument `z_rt = q_r × s_t`, with `q_r` the same resource index measured **once, on 2018-01 → 2019-12**, before the panel. Regional ranking is predetermined, the shock is common; this is shift-share.
- Equation: `y_rt = ε x_rt + region effects + month effects + u`, 2SLS, clustered by region. ε is the elasticity of the clean/dirty ratio to the dirty-cost shock for a region of average quality (`q = 1`).
- **Why levels, not logs.** If the return were `ln q_r + ln P_t`, region and month effects would absorb it completely: all identifying variation is the interaction (quality gap × shock), which exists because the return is a margin over a cost, not a ratio. Only that interaction identifies ε.

## Step zero (before any elasticity; `scripts/analysis/capacity_clean_dirty_noise.py`)
Thresholds (also in the script header, set before the run; no slope printed):
- **C1 Variation.** Residual sd of `z` after region and month effects ≥ 0.03, and the same after adding region-specific linear trends.
- **C2 Dirty side moves.** Residual sd (region and month effects) of `ln` combined-cycle capacity ≥ 0.03. Coal closures are regulated, so they do not count as a response to returns.
- **C3 First stage.** F of `x` on `z` (region and month effects, region-clustered, small-sample corrected) ≥ 10.
- **C4 Placebos.** The real first-stage F exceeds the 95th percentile of F under (a) 2,000 random permutations of `q_r` across regions and (b) every circular shift of `s_t` by 12-56 months.
- **C5 Independent shocks.** Effective number of independent time points of `s_t`, `T(1−ρ)/(1+ρ)` with ρ the lag-1 autocorrelation after a linear detrend, ≥ 8.
- **C6 Detectable elasticity.** 2.8 × the larger of (i) the region-clustered SE of ε under the null (β = 0 imposed, small-sample corrected) and (ii) the sd of the permutation-placebo reduced form scaled by the real first stage, ≤ 2.

Any failure: record it and stop; no other `s_t`, lag, region set or index is tried.

## Rules if step zero passes (registered now, not run)
- **S1** ε positive with t ≥ 2 (region-clustered, and wild-cluster bootstrap p < 0.05 because G = 11) and in [0.1, 10].
- **S2** the real |t| ranks in the top 5% of the 2,000 permutation placebos and of the circular-shift placebos.
- **S3** a lead test: capacity at t on the shock at t+12 months is zero (|t| < 2).
- **S4** robust to region-specific trends, dropping each region in turn, dropping 2021-2022 (auction builds), and PV only / wind only.

## Threats
Common trends (region-specific trends in C1 and S4); lumpy builds with 2-4 year lags (auctions 2019-22, grid-access permits: the 24-month lag block is a guess and is not searched); coal closures set by regulation (so the dirty side cannot answer to price, hence C2); grid and permitting differences by region (region effects absorb levels, not their change); few independent decisions (C5, the wild bootstrap); `q_rt` includes curtailment and cannibalisation (hence the predetermined `q_r` as instrument); the shock is a cost, not a measured return. Looked at before setting thresholds: the capacity table by region (combined-cycle capacity is nearly flat everywhere, so C2 was expected to be at risk). No slope or regression was run.
