# From the two handbook chapters to a thesis

Notes on Hortaçsu & Perrigne (2021) ch. 11 and Kellogg & Reguant (2021) ch. 17,
written against the data inventory in `CLAUDE.md`. Page numbers are the
printed ones, matching the anchors in `papers/md/`.

Still **no research question** — this is a map of what the literature makes
possible with what is already on disk, and what is missing.

---

## 1. The headline: this repo holds the canonical Spanish-market dataset

Kellogg & Reguant's Fig. 2 (p. 696) — their illustration of the one thing that
makes electricity markets special — is built from Spanish market data, citing
Reguant (2014). The chapter's own words for why the setting matters: the
researcher observes **firms' supply curves, not just their realised supply**
(p. 695).

That is exactly `data/omie/bids/`. Three of the field's reference papers run on
this market:

| paper | what it uses | do we have it? |
|---|---|---|
| **Reguant (2014)**, startup costs from complex bids | unit-level day-ahead bids **+ minimum-income conditions** | bids yes; the conditions themselves **no — see gap G1** |
| **Fabra & Reguant (2014)**, emissions cost pass-through | bids + marginal cost + CO₂ price | bids yes; costs **no — G2** |
| **Ito & Reguant (2016)**, day-ahead vs intraday premium | day-ahead **and** intraday bids | **yes, both** — 354 M + 559 M rows |

We are not approaching this literature from outside. We are holding its data,
extended to 2026 and through a VRE share that roughly doubled.

## 2. The central object: residual demand

Both chapters build everything on the same primitive. For firm *i* in period
*t* (K&R p. 691, H&P p. 143):

```
RD_it(p) = D_t(p) − Σ_{j≠i} S_jt(p)
```

Demand, minus everyone else's supply. K&R stress that using market demand
instead makes the curve look inelastic and produces nonsense predictions about
market power (p. 691).

The profit-maximising condition (K&R eq. 23) is just Lerner with the residual
demand elasticity:

```
p = C′ − RD_it(p) / RD′_it(p)
```

**Why this matters for us specifically:** the markup term `−RD/RD′` is
computable **from bid data alone**. No costs, no technology, no capacity — all
of which we lack. The slope of residual demand at the clearing price is a
direct measure of the *incentive* to mark up, and we can construct it per firm,
per period, for 3,000 days. That is the cheapest serious thing this dataset
supports.

With forward positions (K&R eq. 24, H&P eq. 1) the condition becomes

```
p = C′ − (RD_it(p) − θ_it) / RD′_it(p)
```

and θ flips the sign of the markup: a firm short of its contract position is a
net buyer and bids *below* marginal cost (H&P p. 145). Any hour where we see
apparently irrational low bidding should be read as a contract position before
it is read as a mistake.

## 3. Three identification tricks worth stealing

**Hortaçsu & Puller (2008) — contract positions for free.** Where a firm's
supply curve crosses its marginal cost curve, the markup term is zero, so at
that quantity `θ_it` equals the offered quantity (H&P p. 146 fn. 24; K&R
p. 697). Costs → contract positions, without contract data. We now hold this
paper directly (RAND JoE 39(1), printed pp. 86–114, `papers/md/the-rand-j...`)
rather than only through the Handbook chapter's summary — worth reading in
full for the ERCOT institutional detail, since it is also the paper that
finds *small* firms bid "excessively steep" relative to the profit-maximising
benchmark, with scale economies in bidding sophistication as the explanation.
That is a second candidate mechanism (alongside market power) for any bid
that looks irrational, worth keeping distinct from the θ story above.

**Reguant (2014) — joint estimation.** With several units per firm and several
steps per unit, costs `c_jt` and the firm-level `θ_it` can be recovered
*together* from the bid function (K&R eq. 26, p. 698): costs are unit-specific,
θ is common across the firm's units. More steps than parameters and it is
identified. This is the route that needs no external cost data — and our bid
files have unit-level steps in abundance.

**Weighted regression on near-marginal bids.** Rather than modelling the full
price distribution, weight each bid by how close it came to setting the price
(K&R p. 697). In the limit only exactly-marginal bids are used. A tractable
first pass.

## 4. What we already found, and where it sits in the literature

Our own bid-curve work turned up a systematic wedge: on 2024-01-15 the naive
crossing of the submitted curves sat ~21 €/MWh below the actual clearing price
in all 24 hours, because ~7 GWh of in-the-money supply was withdrawn — 26 of 27
affected units cleared in **no hour of the day**.

That is Reguant (2014). Spanish firms attach **minimum daily revenue
requirements** to their bids; a unit whose requirement is not met is withdrawn
for the whole day, and modelling the optimal declaration of that requirement
identifies **startup costs** (H&P p. 147). H&P also note the consequence:
market-power screens built from bid data understate market power when startup
costs are ignored — firms look *more* powerful once they are included.

So the wedge we measured is not noise to be cleaned away. It is the object of a
published identification strategy, and we found it independently in the data.

**Update 2026-08-18.** G1 and G3 below are resolved (`cab`'s minimum-income
condition; the `unit_agents.parquet` firm mapping, 68 parent firms). G2 is
partly resolved — `implied_marginal_cost_daily.parquet` (JRC efficiency ×
MIBGAS/EUA/coal) covers 53 JRC-matched units, still a lower bound, see
CLAUDE.md. G4 is partly resolved — `pdbf` gives a physical-contract proxy for
theta. Kept below as originally written; see §9 for what a second literature
pass (14 more papers) adds on top of this.

## 5. Gaps between what we hold and what these designs need

- **G1 — complex conditions are not in our files.** `offer_type` is null in
  every one of the 2.8 M January-2024 rows. `CLAUDE.md` lists OMIE dataset
  codes `cab` and `det` ("offer header and detail") as known but unfetched.
  **If the minimum-income declarations live anywhere, that is where.** This is
  the single highest-value fetch left, because it converts a descriptive
  finding into a Reguant-style structural design.
- **G2 — no marginal costs.** No fuel, no technology, no capacity in the
  registry. Needed for Hortaçsu-Puller and for any pass-through work. Partly
  addressable via ESIOS/ENTSO-E (tokens) or unit-name matching; the joint
  estimation in §3 is the route that avoids it.
- **G3 — no firm identity.** Every design here is at the **firm** level; we
  have units. `group_tag` covers only some units with 9 tags. Aggregating 5,049
  units into owners is a prerequisite, not a detail.
- **G4 — no forward positions.** Never directly observed in any of these
  markets either; that is why the inference tricks exist.

## 6. Candidate questions, ranked by what the data can actually identify

**A. The staggered 15-minute MTU switch.** Intraday moved to 15-minute
settlement in **June 2025**; day-ahead followed on **2025-10-01**. Four months
where the two markets ran at different resolutions — a staggered design-change
we hold both sides of. Nothing in either chapter covers this; it is too recent.
Highest novelty, and it uses the sequential-markets machinery of Ito & Reguant
(K&R pp. 700–701).

**B. Residual demand elasticity across the VRE transition.** Does a supply
stack with 35% of volume offered at ≤0 €/MWh flatten residual demand, and what
does that do to the incentive to mark up? Needs G3 only, and delivers a
measure of market power that requires no cost data.

**C. The complex-condition wedge over time.** Our §4 finding, measured across
2018–2026: does the gap between the simple-curve equilibrium and actual
clearing widen as VRE grows and thermal plants run fewer hours? Descriptively
available now; structural with G1.

**D. Day-ahead / intraday premium under high VRE.** Direct extension of Ito &
Reguant (2016), who found wind generators arbitraging the forward premium.
Eight more years, double the VRE. We have both markets at unit level.

**E. Market splitting as competition variation.** ES and PT prices diverge in
6.7% of periods. Wolak (2015) and Ryan (2021) use exactly this — congestion
shrinks the effective market and steepens residual demand (K&R pp. 701–702).
MIBEL gives a clean binary version of that with two well-defined zones.

**F. Regime-stable supply curves without bids.** Sánchez Canales et al. (2026,
*Energy Economics*, `papers/md/main.md`) estimate supply curves from price/
quantity equilibria alone by detecting windows where fundamentals (fuel
prices, plant availability) are stable, so short-run demand shocks trace out
the supply curve — a PELT changepoint segmentation over daily drivers. We
don't need the bid-free version of this (we have `cab`/`curva_pbc_uof`
directly), but the regime-stability argument is a clean, citable way to
partition the 2018–2026 window into periods where a single supply relationship
plausibly holds, before pooling data across them for any of A–E. The paper
explicitly flags the Iberian gas-price mechanism (`docs/` — see
`literature-iberian-exception.md`) as a natural application of its own
framework, which makes it a direct competitor/complement to whatever design
gets chosen for the levy/gas-cap work already underway on this branch.

**G. Day-ahead / intraday arbitrage and who has power over the gap.**
Borenstein, Bushnell, Knittel & Wolfram (2008, *JIE*,
`papers/md/jie08arbitrage.md`) is the reference case for candidate D: before
treating a day-ahead/intraday premium as a pure risk-aversion or forecast-error
story, check whether specific agents have enough scale to hold a persistent
gap open rather than arbitrage it away. Their finding — a dominant buyer
(PG&E) and a dominant arbitrageur (Enron) both had market power *in the spread
itself* — has a direct MIBEL analogue given how concentrated `unit_agents.parquet`
shows generation ownership to be (§ "Who controls a unit's bid" in
`CLAUDE.md`). Worth pairing with Ito & Reguant (2016) rather than substituting
for it.

---

## 7. What to read thoroughly

About 25 pages of the 223 carry almost all the value. In order:

1. **K&R §4.2, pp. 691–702** — the core. Read §4.2.2 *"Taking electricity
   auctions to heart"* (pp. 695–698) slowly: eqs. 23–26 are the whole toolkit,
   and Fig. 2 (p. 696) is our data. §4.2.4 (pp. 699–700) on dynamics and
   §4.2.5 (pp. 700–701) on sequential markets are the two most relevant
   subsections after that.
2. **H&P §7, pp. 143–149** — the auction-theoretic derivation K&R skip. Eq. (1)
   on p. 144 and the markup discussion on p. 145 (the contract-position sign
   flip) are worth working through by hand. §7.3 (p. 147) is the Reguant (2014)
   summary — the paragraph that describes our wedge.
3. **H&P §8.1 and §8.1.1, pp. 149–152** — Treasury auctions. Same mathematics,
   and the part electricity papers gloss over: **real bids are discrete step
   functions, so marginal values are only partially identified** (McAdams 2008,
   Hortaçsu & McAdams 2010), and with a cap on the number of steps it can be
   optimal to bid *above* marginal value (Kastl 2011). Our bids are discrete
   steps. Read this before trusting any point estimate.
4. **K&R §4.3.2, pp. 704–707** — market impacts of renewables. Bushnell & Novan
   (2018) on average price falling while evening prices rise is the closest
   published analogue to our net-load-by-year figure.
5. **K&R §6, pp. 728–729** — the open-questions list. Storage integration into
   wholesale markets is flagged as unresolved, and our REE data has battery
   charge/discharge at 5-minute resolution from 2025.

Skip on a first pass: all of K&R §2 (oil and gas), §3 (vehicles), §5
(environmental regulation); H&P §§2–6 and §§9–10. Come back to H&P §3.4 and
§2.5 only if collusion becomes a theme.

## 8. Immediate next steps this implies

1. **Fetch `cab`/`det` from OMIE** and check whether complex conditions are in
   them. Everything structural depends on it (G1).
2. **Build a unit → firm mapping** (G3). Nothing at the firm level is possible
   without it.
3. **Compute residual demand curves and their slopes** for a sample of hours.
   It is the object both chapters are built on, it needs nothing we lack, and
   it will tell us quickly whether the market-power route has any bite here.

---

## 9. Second literature pass (2026-08-18): 14 more papers

Five agents read the rest of `papers/` — everything not already covered
above. Full per-paper detail (citation, method, what it's worth) is now in
`papers/README.md`'s table; the two most load-bearing findings went straight
into the design notes they bear on (`hydro-water-value-design.md`,
`rq-gas-cap-conduct.md`, `literature-iberian-exception.md` — see those for
detail, not repeated here). What's below is what belongs at the toolkit
level: general identification tricks, not tied to one design.

### 9.1 Two more identification tricks worth stealing, beyond §3

**A directly implementable residual-demand-slope recipe for step-function
bids**, from McRae & Wolak, "How do firms exercise unilateral market power?
Empirical evidence from a bid-based wholesale electricity market" (book
chapter, New Zealand; `papers/mrae_wolak_how_do_firms_exercise_market_power.pdf`
— scanned, no text layer, rendered to page images to read). Their eq. 3.6
(printed p.399): take a ±10% price window around the clearing price, find
the nearest residual-demand step outside it on each side, `DR'(P*) =
(Q1−Q2)/(P1−P2)` — a finite-difference procedure built for exactly the
discretization problem OMIE's step-function offers have, not an abstract
elasticity formula assuming a continuous curve. Two indices follow: ability
`η_i = -(1/100)·DR_i(P*)/DR'_i(P*)` (their eq. 3.4) and a contract-adjusted
incentive version `η_i^C = η_i·[(DR_i(P*)−Q_C)/DR_i(P*)]` (eq. 3.10, `Q_C`
the firm's net position — ours is `pdbf`'s theta proxy). Then a regression
with **no cost data on either side**: offer level on η/η^C with day×hour
fixed effects absorbing unobserved marginal cost entirely (their eq. 4.1–4.2,
coefficients $0.46–$22.86/MWh per unit across their 8 units, incentive always
dominating ability). A companion market-power *hypothesis test*, not a
markup calculation: regress a unit's own offer on its own cost shifters plus
**rivals'** hydro storage level — storage shouldn't predict a unit's own
price under no market power, and it does for all 8 of their tested units
(§18.5, eq. 5.1, β −2.34 to −24.31 $/MWh per TWh). This whole apparatus is
buildable now from `curva_pbc_uof` (status `O`) + `unit_agents.parquet`, no
new fetch, and is the cheapest concrete next step for candidate question B
(residual demand elasticity across the VRE transition) — arguably cheaper
than the aggregate elasticity already computed, since it's firm-specific.

**A structural explanation, and a reduced-form fallback, for the "small
firms bid excessively steep" finding already flagged in §3.** Hortaçsu,
Luco, Puller & Zhu (2019, *AER* 109(12): 4302–4342,
`papers/md/hortasu-strategicabilityaffect-2019.md`) model this as a
cognitive-hierarchy (CH) type distribution — level-0 bidders bid their
contract position, level-k best-respond assuming rivals are Poisson-
distributed over levels 0..k−1 — identified by matching observed ERCOT bids
to CH-predicted bids across every possible type (p4328–4329), using
*observed* marginal cost (heat rate × fuel price) to separate type from
cost, something we lack at scale. Firm size is the dominant driver of
sophistication (p4330). **The reduced-form design is the portable part**:
a two-month 2002 nuclear outage steepened aggregate marginal cost, and large
firms' bids got measurably steeper in response while small firms' did not
(Table 3, p4336) — a falsification test using a public, common, non-firm-
specific cost/capacity shock. Spain has ready-made shocks of this kind: a
large plant outage, or the VRE-driven residual-demand steepening itself
(candidate B again) — testing whether large vs. small Spanish firms respond
differently in bid slope needs only `unit_agents.parquet`'s firm-size
information and no new cost data.

### 9.2 A candidate extension of Jha & Leslie, now with Spain's own advantage
### made concrete

Jha & Leslie (SSRN 3603627) is already extensively summarised in CLAUDE.md's
`implied_marginal_cost` section; a second, closer read
(`papers/md/ssrn-3603627.md`) surfaced the operational equations CLAUDE.md
didn't have (production function eq.1–2 p.-44; cost function p.-43/-42;
dynamic dispatch problem eq.3–8 p.-38/-36; competitive-pricing rule with
dynamic + static rationality constraints eq.9–11 p.-34/-33; the solar-lag
regression eq.12 p.-23/-22, which uses **48 half-hourly lags** of demand
interacted with hour-of-day — dropping the lags badly mispredicts the
evening effect, per their own appendix F.1). Their mechanism: daytime VRE
displacement forces thermal plants to stop, and some choose not to re-incur
start-up costs at the evening ramp, softening competition and raising
evening markups as VRE grows. **They corroborate this firm-by-firm using
McRae & Wolak's own η measure (§9.1 above)** — a direct bridge between the
two paper groups this pass covered separately.

This is a directly testable prediction on our 2018–2026 window (VRE share
23.9%→41.8%) — and Spain has a genuine advantage over their Western
Australia setting the note should say plainly: Jha & Leslie *estimate*
start-up costs from gas-metering data because their market doesn't publish
them; `cab`'s minimum-income condition is a firm's own **declared** start-up-
recovery number (to 2025-03-18). Testing their mechanism on CCGT units that
declare a minimum-income condition would use a real number where their own
paper had to use an estimated one — a genuine methodological improvement on
the source paper, not just a replication. Not yet built; flagged here as a
concrete next step alongside candidate question B, complementary to but
distinct from the gas-cap and hydro-water-value designs already underway.

### 9.3 Citation-only or low-relevance — read, and honestly not more than that

- **Tangerås & Wolak (2021)**, linking markets across space — real theory,
  doesn't map onto MIBEL's spot-price splitting without a separate argument;
  detail and why in `literature-iberian-exception.md`.
- **Fabra, Rapson, Reguant & Wang (2021)**, real-time pricing elasticity —
  on-setting (Spain) but the wrong market side (retail households, not
  wholesale agents); elasticity ≈ 0, useful only as background support for
  treating demand as inelastic. Detail in `rq-gas-cap-conduct.md`.
- **Leslie, Stern, Shanker & Hogan**, VRE market design (Australia NEM) —
  citation value for framing `cab`'s minimum-income condition as the
  "missing dynamic-cost instrument" the NEM literature says is needed; also
  flags a cheap, immediate check with data already in hand — a duck-curve /
  evening-price-ramp test on OMIE prices + REE realtime 5-min generation,
  no new fetch.
- **Wolak (EEPE)**, long-term resource adequacy (California Aug 2020, Texas
  Feb 2021 shortfalls) — no Spain analogue event confirmed, but the paper's
  own method (distribution of low-combined-wind+solar-output durations,
  their Tables 3–6) is directly reusable on REE realtime data as a cheap
  descriptive check of whether Spain's multi-hour VRE-shortfall tail risk
  grew with VRE share — independent of whether resource adequacy becomes an
  actual thesis question.
- **McRae & Wolak, "Reliability Options..." (NBER w32616)**, Colombia — the
  policy mechanism (reliability options with capped forward-contract
  settlement) has no Spanish counterpart; two techniques are transferable
  regardless — the unilateral-scarcity-triggering test and the water-
  opportunity-cost-by-dispatch-matching approach, both worth a pointer for
  whoever works the residual-demand or hydro-water-value designs.
- **Thurber et al.**, SFPFC game-based study — an experimental/behavioral
  study with fictional players, no real market microdata; citation-only
  companion to the Wolak SFPFC proposal, no methodological overlap with an
  observational bid-microdata thesis.
