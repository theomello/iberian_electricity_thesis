# Paper outline (2026-11-02)

A proposed structure for the paper, built from the results that stand on 2026-11-02. Not yet agreed with
the supervisor; the framework page they hold is the 2026-10-07 version. CLAUDE.md keeps "no research
question yet" until that sign-off.

**Claim.** Iberian generators mostly bid like price-takers in the day-ahead auction. Hydro departed from
that in 2019 to mid-2021, and the gas cap's subsidy was passed through.
The estimates behind each part of the claim, graded, are in
[`2026-11-08-conduct-evidence-table.md`](2026-11-08-conduct-evidence-table.md).

## Sections

1. **Introduction.**
2. **Market and data.** MIBEL's joint auction and the unit-level offers (`curva_pbc_uof`). Ownership by date
   and by share (`lib/unit_ownership.py`: co-owned reactors, sold businesses), a contribution in itself. The
   cost measures: implied gas and coal cost (`implied_marginal_cost_daily`, `_bid` columns), the hydro water
   value λ* (`hydro_cost_daily`), and the declared minimum-income cost in `cab`.
3. **Framework.** One condition, four tests: offer = cost + β × the firm's markup incentive (its share over
   the slope of its residual demand, net of contracts). β = 0 is price-taking, β = 1 is Nash.
4. **The price-taker benchmark.** The methodological core. Standard estimators give β ≠ 0 when every firm is
   a price-taker, so every estimate is read against simulated price-takers
   (`notes/rq-price-taking-simulation.md`). Without it the rest cannot be read.
5. **Thermal plants.** Bounds only: Nash rejected, price-taking not. Outage, rain and regional-wind
   instruments (`notes/rq-reactor-outages.md`). Short.
6. **Hydro.** λ* checked on EDP (within 6%, correlation 0.81–0.91). The departure of +0.25 in 2019–21H1, on
   all ten seeds, ending in June 2021, the month the clawback was announced. Robustness. The headline
   section.
7. **Gas cap** (policy section, 2026-11-05 revision; see `notes/rq-gas-cap-*.md`, `notes/rq-crisis-quantity.md` §J).
   Opens by saying what it identifies: declared costs, not offers. 7.1 mechanism and cost rule. 7.2 declared
   costs fall by 0.9-1.0 of the subsidy, within Iberia (`rq-gas-cap-declared-cost.md`). 7.3 offers against Italy:
   rho conditional on whether Iberian offers respond to gas apart from the subsidy; quote 0.73 [0.51, 1.03]
   uncontrolled, controlled 0.54-0.85, no direction of bias (`rq-gas-cap-control.md`); recovery simulations show
   why the band cannot be narrowed. 7.4 welfare: at rho 0.73 Spanish buyers lose EUR 3.2 bn, 74% transfer to
   sellers, 17% deadweight loss (dispatch), 9% leaked abroad; deadweight loss is half the loss at rho 1.
   Hydro offers did not follow the cap's cost shock (`rq-gas-cap-hydro-link.md`).
8. **Discussion.** Who sets the price (44% of hours a unit with a cost, 16% via the open France line, 23% buy
   bids) limits what β speaks to. Static markups ignoring start-up costs are biased upward (Jha & Leslie).
   Physical bilateral contracts are a proxy for hedging, not a measure of it.
9. **Conclusion.**

## Appendices

- One table of the designs that did not identify anything, each with its reason: regional holidays,
  minimum-income near-misses, France link, outage events, own wind, Great Britain.
- Italy and Great Britain as comparison markets: what was tried and why each comparison fails or only
  corroborates.
- The data traps that matter for replication.

## Before writing

- Rerun the outage regression (§6 of `notes/rq-reactor-outages.md`) on the corrected-ownership panel before
  quoting the pooled figure.
- Show the hydro departure firm by firm, since it rests on Iberdrola.
- Decide how strongly to claim the clawback timing: a dated break, or a cause.
- Supervisor sign-off on this framing.
