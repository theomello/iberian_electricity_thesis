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

## González-de Miguel et al., read in full 2026-08-18 — quantified, and it
## explicitly closes off the novelty question

The table row above described the method; having now read the paper
(`papers/md/energies-17-03102.md`) in full, here are the point estimates for
their headline window (15 June – 30 Sept 2022), which sharpen "settled, do
not re-do" from qualitative to quotable: mean subsidy 173.35 €/MWh
(72.73–346.16), 48.1 TWh subsidised, total cost €8,350M (~2.1% of Spanish
GDP); price effect −107.10 €/MWh mean (max −240); cleared-energy effect
+3,191 MWh/h mean (max 17,057, mostly gas); cross-border effect on price
+21.12 €/MWh (the interconnector limits the relief); rent transfer:
non-fossil producer surplus **−€1,885M**, extra-cleared fossil surplus
**+€447M**, infra-marginal fossil surplus **+€2,628M**; consumer surplus
**+€6,811M**; congestion rents **+€251M** (financing 3.1% of the subsidy,
independently corroborated against another source's €576M for a longer
window).

More important than the numbers: they state outright, twice, that
individual-firm conduct is outside what their method can do. Their
counterfactual *assumes* CCGTs pass the subsidy through to their bids 1:1
by construction ("CCGTs are obliged to pass through the subsidies into
their market bids", p9) rather than testing it, and on hydro they say
directly "we lack sufficient information to estimate how the bidding price
for HPPs would change" (p13). Both are exactly the two open questions this
note already lists as unaddressed — the closest existing paper confirms it
by admission, not just by absence. See `rq-gas-cap-conduct.md`'s 2026-08-18
section for what this implies for the design (in short: their passthrough
assumption is the literal null hypothesis our test is built to reject or
confirm), and for the Fabra & Reguant (2014) precedent equation and pass-
through prior it also supplies.

One incidental fact worth carrying forward for a power calculation: they
document Spanish hydro was essentially absent from the market June–Sept
2022 (drought — only Portuguese hydro cleared in that window), which may
thin the Spanish-side hydro-response sample exactly when the cap first
bound.

**Tangerås & Wolak (2021), "The Competitive Effects of Linking Electricity
Markets Across Space" (`papers/md/the-competitive-effects-of-linking-electricity-markets-across-space-april-2021.md`),
checked for fit and set aside for now.** Theory paper on US-style nodal
markets: linking local markets through a *regional forward contract* is
pro-competitive (producers internalize only 1/M of their own price-
suppressing effect on the hub price), linking *consumer prices* regionally
is anti-competitive, and multi-market producers weaken the pro-competitive
forward effect (their Prop. 7). None of this is about spot-price linkage
itself, so MIBEL's 6.7% market-splitting periods are **not** this paper's
natural experiment without a separate argument — its comparative statics
are between forward-contract *regimes*, not between hours of one regime.
Testing whether MIBEL firms active in both ES and PT behave differently
(Prop. 7's prediction) would first need confirming whether OMIP forwards
settle against a single MIBEL reference or a zone-specific one — not yet
established in this repo. Parked as a possible future question, not a fit
for the gas-cap design.

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
