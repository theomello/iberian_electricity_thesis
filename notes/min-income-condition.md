# The declared minimum-income condition, wired in — and what the literature says
# to do next

Written 2026-08-21. Six conduct tests had returned null or wrong-signed
estimates, and the diagnosis in
[`rq-heat-demand-conduct.md`](rq-heat-demand-conduct.md) §8.3 was that the
**cost measure**, not the shock, was the binding constraint. This wires in
`cab`'s declared minimum-income condition — the repo's one genuine data
advantage — and then reads the literature for designs that avoid the constraint
altogether.

`scripts/analysis/min_income_conduct.py`.

---

## 1. The validation is the strongest result here

Before any test: the **declared variable term** (a firm's own statement of what
it needs per MWh) was compared against `implied_marginal_cost_daily`
(`gas/eff + 0.2020*co2/eff`, built from JRC efficiency × MIBGAS × EUA). These
share no input and no source.

| | |
|---|---|
| overlap | 83,133 unit-days on 68 units |
| corr(declared variable, implied MC) | **+0.800** |
| corr in logs | **+0.869** |
| ratio declared/implied | median **1.34**, p25 1.18, p75 1.55 |

Two independent constructions of the same quantity agree at 0.87 in logs, and
the declaration sits a stable ~34% above pure fuel cost — which is exactly what
it should do, since it is meant to cover more than fuel. **This is the best
validation of the implied marginal-cost series in the repo**, and it is only
possible because this market publishes both. Worth reporting on its own terms
whatever happens to the conduct question.

## 2. The floor does the exclusion the engineering cost could not

Evaluating the declaration at full-day capacity, `AC = variable + fixed/q_max`,
gives the most favourable threshold a unit can face — so a price below it cannot
meet the firm's own stated requirement at *any* output, and failing it is
genuine unprofitability rather than withholding.

| measure | on implied MC | on declared floor |
|---|---|---|
| unit-days "in the money" | 60.8% | **40.3%** |
| withholding rate given in the money | 76.3% | **52.7%** |

The vacuous measure from §8.1 is materially repaired. Median declared AC is
86.4 €/MWh against an implied MC median of 58.8.

**But the fixed term is mostly absent.** Median declared fixed term is **0
€/day** (p90 = 65,240), and it changes on only **1.1% of days**, against 87.8%
for the variable term. So the condition is in practice a *variable* floor that
is re-declared daily, not a start-up charge. Any result resting on the fixed
term — including the `net load -> log fixed term` estimate of −0.050 (t = −9.76)
below — is fitted on a near-constant series and should be treated as fragile
rather than as a finding.

## 3. The tests: still null, and one near-miss worth dissecting

**Withholding against the declared floor.** CDH → −0.0198 (t = −7.19), size
interaction −0.0008 (t = −0.03). Same sign as every earlier version. The better
cost measure did not change the conclusion.

**The declaration as an outcome** — Reguant (2014)'s own object, and a test that
needs no cost model because it explains the firm's own stated requirement. The
variable term does not respond to scarcity: instrumented by net load, −0.052
(t = −0.26). If conduct responded to tightness anywhere in this market it should
have been visible here, and it is not.

**The near-miss, and why it is not a finding.** Instrumented by net load, the
markup over the declared floor gives **+1.197 (t = 7.74, first-stage F = 162.8)**
— the first positive, significant, conduct-consistent estimate in the entire
sequence. It is not evidence of market power, and the discriminating test says
so:

| | β per GW of net load | t |
|---|---|---|
| net load → daily market price | **+4.355** | 10.21 |
| net load → unit's marginal accepted offer | +1.966 | 6.89 |
| net load → markup over declared floor | +1.197 | 7.74 |
| net load → **markup minus the market price** | **−1.924** | **−4.59** |

Under competition an inframarginal unit's rent rises **one-for-one with the
clearing price**. The market price rises 4.36 €/MWh per GW of net load; these
units' markups rise 1.20. They capture *less* than the price movement, not more.
Reported as a bare coefficient this would have been a false positive; the
comparison against the price is what settles it, and it is the same discipline
the event study provided for the spill window.

## 4. What the literature says to do instead

Read for designs that **avoid the cost measure**, since that is what has bound
every test here.

### 4.1 Sequential markets — the design that needs no marginal cost at all

**Ito & Reguant (2016), "Sequential Markets, Market Power, and Arbitrage",
*AER* 106(7): 1921–57.** Iberian microdata. A systematic **forward-market price
premium** arises when dominant players face limited entry into arbitrage; wind
farms arbitrage part of it but do not eliminate it; and with market power, full
arbitrage is not necessarily welfare-improving — it cuts consumer costs while
raising deadweight loss.

**Why this is the strongest complement.** The premium is measured from prices
and participation. **No marginal cost enters anywhere.** Every failure recorded
in this repo traces to the cost measure, and this design sidesteps it entirely.

And the data is already here — `data/omie/bids/` (354 M rows day-ahead) and
`data/omie/intraday/` (559 M rows, *larger* than the day-ahead archive), both at
unit level, both to 2026. The paper published in 2016, so its sample cannot
include: the post-2018 VRE expansion (wind + solar 23.9% → 41.8% of generation),
the 2021 clawback, the gas cap, the 15-minute MTU, or the replacement of MIBEL's
6–7 intraday sessions by the European IDA auctions. Each of those is a reason
the premium might have changed, and the second is directly on their mechanism:
**wind is their arbitrageur, and wind is now several times larger.**

### 4.2 Sharp policy switches beat continuous weather shocks at this effect size

**Fabra & Imelda (2023), "Market Power and Price Exposure: Learning from Changes
in Renewables Regulation", *AEJ: Economic Policy* 15(4): 323–58.** Exploits
short-lived Spanish regulatory switches between fixed and market-based
remuneration for renewables. Switching from full price exposure to fixed prices
cut the average price-cost markup by **2–4%**, working directly through dominant
firms' incentives and indirectly through fringe arbitrage.

Two lessons, both uncomfortable and both useful:

- **Markups in this market do respond to policy, and can be measured.** So the
  nulls in this repo are not inevitable — they are a statement about these
  shocks and this cost measure.
- **The effect size is 2–4%.** Against a markup whose median is single-digit
  €/MWh, that is far below what a continuous weather shock resolved here: the
  best-instrumented markup test gave a confidence interval spanning several
  €/MWh. A sharp on/off regulatory switch delivers the contrast a continuous
  shock cannot.

This also connects to machinery already built: their identification runs through
**price exposure**, which is the same θ (contract position) that `pdbf`'s role-4
bilateral volume proxies.

### 4.3 Storage — on-setting and growing, but thin in this window

**Andrés-Cerezo & Fabra (2023), "Storing Power: Market Structure Matters", *RAND*
54(1): 3–53**, and **"Storage and Renewable Energies: Friends or Foes?", *EJ*
forthcoming (2025)**. Storage market power is a live theoretical and empirical
question, and the registry carries `storage_mixed` (45 units) and `pumping` (22).

The limit is the window: Spanish grid batteries were around 60 MW as late as
2025, so within this sample "storage" means pumped hydro almost exclusively —
and pumped hydro brings back the water-value problem that four probes already
failed on. Worth knowing; not worth building yet.

### 4.4 The primitive this repo publishes, restated

**Reguant (2014), "Complementary Bidding Mechanisms and Startup Costs in
Electricity Markets", *ReStud* 81(4): 1708–42.** Extends multi-unit auction
estimation to cost complementarities over time, recovering start-up costs from
Spanish bid data. Its finding that **start-up costs limit firms' ability to
change production over time** is precisely the mechanism that dominated the
withholding measure in §8.1 — a median unit-day showing no output across 18
in-the-money periods is that constraint, not conduct.

## 5. Where this leaves the project

The cost measure is now as good as this market allows: a firm's own daily
declaration, cross-validated at 0.87 in logs against independent engineering
data. It did not rescue the conduct tests. That is informative — it means the
nulls are not an artefact of bad cost data.

The ranking that follows:

1. **The sequential-markets design (§4.1).** Needs no cost measure, uses the
   larger of the two archives, has a published Iberian precedent to extend
   rather than replicate, and the mechanism's key actor — wind — has grown
   several-fold since that precedent.
2. **A sharp policy switch (§4.2)**, with the gas cap the obvious candidate
   already scoped in [`rq-gas-cap-conduct.md`](rq-gas-cap-conduct.md).
3. **The MIC validation (§1)** written up as a result in its own right,
   whichever design wins.
