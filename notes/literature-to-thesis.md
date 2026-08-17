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
