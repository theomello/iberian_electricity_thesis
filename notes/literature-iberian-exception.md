# The Iberian Exception — what has already been done

Checked 2026-08-13, before committing to a design. The point of this note is to
avoid duplicating existing work.

## The policy

**RDL 10/2022 (13 May 2022).** From **15 June 2022** the gas price used in
wholesale electricity bids was capped — €40/MWh initially, escalating monthly
toward €65 — with covered plants compensated for the difference, funded by a
levy on consumers. Initially for 12 months (to 31 May 2023), extended by
Commission approval to **31 December 2023**.

**Covered technologies**, which is the fact that decides any control group:

- combined-cycle gas turbines
- **conventional coal** — so coal is *treated*, not a control
- cogeneration **without** a regulated remuneration framework — plants under
  the specific regime (RECORE) are **excluded**

Not covered: nuclear, hydro, wind, solar, and RECORE cogeneration. The Balearic
and Canary systems are outside the mechanism, but they are also outside the
peninsular market, so they are not a usable control.

## What the literature has established

| work | data | method | finding |
|---|---|---|---|
| Haro Ruiz, Schult & Wunder (2024), *Applied Economics Letters* | country-level prices, CPI | synthetic controls | ~40% fall in the spot price Jul-22 to Jun-23; −3.5pp inflation in Spain, ~0 in Portugal |
| González-de Miguel et al. (2024), *Energies* 17:3102 | **real market bids**, subsidy data, generator data | reconstructs aggregate supply and demand curves, simulates counterfactuals | quantifies cleared energy, the export swing to France, congestion rents, and the transfer of rents from non-fossil to fossil producers |
| Cambridge CWPE 2535 / *Energy Economics* | market data | welfare accounting | cost of distorting the market during the crisis |
| Oxford Institute for Energy Studies (2023); Columbia CGEP (2023); arXiv 2309.02608 | market data | descriptive | first-100-days assessments |
| Cerdeira, *Scottish Journal of Political Economy* | Portuguese macro data | fiscal policy | inflation effects in Portugal |
| Bayesian structural time series work | flows | causal time series | exports to France up 2.3 GWh/day, saturating the interconnector |

**Settled, do not re-do:** the price effect, the inflation effect, the export
surge to France, congestion rents, and the direction of the rent transfer.

## Correcting an earlier claim of mine

I previously told Theodor that "none of them uses the bid microdata". **That is
wrong.** González-de Miguel et al. use real market bids. What they do with them
is reconstruct *aggregate* supply and demand curves and simulate counterfactual
market outcomes — an accounting and simulation exercise at market level.

The accurate statement is narrower: **no published work estimates the
behavioural response of individual generators, with a treatment and control
group, using unit-level bids.**

## What is genuinely open

Everything above measures what the policy did to *outcomes*. Nothing measures
what firms *did*, and in particular:

1. **Did capped firms bid at the cap, or below it?** The mechanism set a
   ceiling on the gas price used in the bid, not on the bid itself. Whether
   covered plants bid their capped cost or marked up over it is a conduct
   question, answerable per unit per hour.
2. **Did uncapped firms raise their offers?** Capping fossil bids pushes hydro
   and other uncapped technologies into the price-setting position more often.
   The literature notes that rents transferred toward fossil producers, but
   nobody asks whether hydro *responded strategically*. This is the interesting
   one: an intervention aimed at one group may be partly captured by another.
3. **Did the response differ by firm?** Large portfolios versus small
   independents, vertically integrated versus not.

## What this implies for the design

Treatment status is set by regulation and is observable:

- **Treated** — CCGT, coal, non-RECORE cogeneration
- **Untreated but exposed** — hydro above all: uncapped, strategic, and pushed
  toward the margin by the policy
- **Untreated and largely unexposed** — nuclear, wind, solar, which bid at or
  near zero and have little strategic margin either way

The spillover onto the untreated group is not a nuisance to be assumed away.
It is the object of study, and it is why a naive difference-in-differences with
hydro as a "clean" control would be wrong.

**One data problem to solve first.** The RECORE split within cogeneration is
not visible in ESIOS's taxonomy, which carries a single "Gas Natural
Cogeneración" category. Identifying it needs the CNMC remuneration registry.
Until then the cogeneration arm of the treatment cannot be separated.
