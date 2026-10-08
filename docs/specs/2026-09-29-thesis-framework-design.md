# The thesis framework: one first-order condition, tested four ways

**Status: proposed 2026-09-29, for the supervisor.** It proposes a candidate
research question; none is adopted in `CLAUDE.md` until one is agreed.

**Revised 2026-09-30:** n is the price-exposed position (§2.4). On it leg A
holds and leg B's first pass is withdrawn for want of a first stage (§4);
legs C and D are designed (§4) and the plan reordered (§8).

**Revised 2026-10-01:** leg D is run and inconclusive: price-taking is rejected,
conduct is not separated (§4). Leg C is run: in levels β ≈ 3, which rejects a
joint hypothesis rather than conduct alone; the leading candidate is that the
price sits in the gaps of stepped offers (§4). An estimator on the offer steps is
proposed (§8 step 5b).

**Revised 2026-10-05:** leg C's β ≈ 3 is explained: the outcome contains the
market price, which falls down the merit order for every plant when renewables
rise, so it is not conduct (`rq-leg-c-thermal-cost.md` §6). Conduct is read from
the firms' own offers, net of price-takers' offers (legs A and D: β 0.02–0.14).
Every leg now runs on ownership by date and share; no conclusion moved. The next
design, with the ideas of 2026-10-02/03 assessed and ranked, is §9.

It connects the descriptive chapter
([`rq-descriptive-price-formation.md`](../../notes/rq-descriptive-price-formation.md)),
the midday-hydro work ([`rq-midday-hydro.md`](../../notes/rq-midday-hydro.md)), the
water-value spec ([`2026-09-29-water-value-design.md`](2026-09-29-water-value-design.md))
and the six withdrawn causal designs. They are not separate projects. Each one
measures or tests a term in the same equation.

## 1. Why this exists

Six causal designs were built here and withdrawn. Their own post-mortem: *every
conduct estimate is null or wrong-signed; every precisely estimated result is
merit order* (`rq-heat-demand-conduct.md` §8.3). The diagnosis was the **cost
term**: a markup measured against an engineering fuel cost that omits operation
and maintenance, part-load efficiency and start-ups cannot carry a conduct test.
The descriptive chapter then found why the problem is structural. Where the
price-setting technology can be identified, **hydro** sets it in 51% of periods
in 2019 and 76% in 2026, while combined cycle falls from 35% to 2.3% (chapter
§4.4). Hydro's cost is a water value that no invoice records (§7).

The framework below says, for each part of the market, how the cost term is
handled: **observed**, **differenced out**, or **modelled**. That choice decides
which test is possible where.

## 2. The model

### 2.1 The static condition

Firm f bids into a uniform-price auction whose price p_t it can move. Its profit
is earned on its **net auction position** n_ft: cleared sales minus cleared
purchases over every unit it owns, retail included. Maximising over its offer
curve gives, at the clearing price (Wolak 2000; Hortaçsu and Puller 2008):

```
p_t − c_ft  =  β · n_ft / |RD′_ft(p_t)|  ≡  β · X_ft
```

| symbol | meaning |
|---|---|
| p_t | the day-ahead clearing price in period t |
| c_ft | the opportunity cost of the firm's marginal MWh: fuel and carbon for thermal plant, the **water value** λ for storage hydro, about zero for wind and solar |
| n_ft | **price-exposed** net auction position (§2.4). Physical bilateral contracts never enter the auction, so they drop out of both sales and purchases. Regulated suppliers' pass-through volumes are excluded. Financial hedges would enter it and are unobserved |
| RD′_ft | slope of the demand left to the firm after every rival's offers, measured as the density of rivals' offers within ±h €/MWh of p_t |
| β | conduct: **0** price-taking, **1** the supply-function Nash benchmark |

A **net buyer** (n < 0) has X < 0 and gains from a *lower* price. It is the same
condition with the sign reversed.

The descriptive chapter's Lerner identity is this condition with β = 1 and
n = q (Kellogg and Reguant 2021, eq. 23). Its two indices are its pieces:
*ability* q/(100|RD′|) and *incentive* n/(100|RD′|), both in €/MWh per 1% of
output withheld (chapter §2, §4.5).

### 2.2 The dynamic condition, for stored water

A storage unit's cost is the shadow value of its water,
λ_t = ∂E[V_{t+1}]/∂S. Between the reservoir's bounds it is a martingale
(Bushnell 2003; water-value spec §2):

```
λ_t  =  E_t[λ_{t+1}]  −  κ̄_t  +  κ_t          (κ̄: reservoir full;  κ: empty)
```

So hydro market power has **two margins**:

- **Within the day**: moving a day's water between hours of different X, given λ.
- **Across days**: choosing λ's *level* by holding water back.

A curve that is flat within the day rules out the first and says nothing about
the second (water-value spec §4).

### 2.3 Where solar enters

Solar moves every observed term, and moves it by hour:

- **n** — retail-heavy firms become net buyers at midday, when solar floods the
  auction (Iberdrola, Endesa, Naturgy; Repsol from 2024).
- **|RD′|** — offers near the price thinned out, and the thinning is at midday,
  not in the evening ramp (chapter §4.3).
- **the price distribution λ is read against** — zero-price periods went from
  none to a quarter of Portuguese periods in 2026 (`rq-midday-hydro.md` §3.16).

So the natural question is: **does solar change how Iberian firms use market
power, and on which margin?** Solar shifts X; the four tests below ask whether β
lets that shift reach the price.

### 2.4 Which position is exposed

n is the position whose revenue moves with p. Auction volume a firm's group
clears but whose cost or revenue is passed through to a regulated tariff does
not move its profit, so it is excluded. Added 2026-09-30, after the first
passes of legs A and B.

**Two such entities sit inside the five large groups**, found by owner name in
`unit_agents.agent_owner`:

- **SU Eletricidade** (EDP; 4 units). Portugal's last-resort supplier. It sells
  the feed-in renewable output it is obliged to buy (`EDPSVD1` "VENTA RE",
  6,500 MW declared), the 2019 solar-auction plants on the fixed tariff
  (`EDPSVD3`), and buys for regulated customers (`EDPUC2`). The cost of
  feed-in output above its market value is recovered through regulated
  tariffs, so the market price does not reach EDP's profit on these volumes.
- **Curenergía** (Iberdrola; 11 units). The last-resort supplier for Spain's
  regulated household tariff, which passes the day-ahead price through
  (`IBCUC01`), and the seller of renewables it represents as representative of
  last resort (`ICUVD*`), whose revenue belongs to the plant owners.

The equivalent entities of Endesa (Energía XXI), Naturgy (Comercializadora
Regulada), Repsol (Regsiti) and Baser already stand as their own groups, so the
rule changes nothing for them. It is one rule, applied by every computation of
n. **To confirm against ERSE and CNMC texts** before the thesis relies on it.

It matters for EDP above all. Net-buyer share of clean periods by year,
2018–2026 (`firm_x.py`; EDP includes EDP Comercial, merged 2026-09-30):

| | as built | exposed | mean pass-through net volume |
|---|---|---|---|
| EDP | 14–43% | **72–89%** | SU Eletricidade, +1,810 MW |
| Iberdrola | 60–97% | 49–85% | Curenergía, −790 MW |

EDP, read as a mostly net seller in legs A and B, is a net buyer in most
periods: its liberalised retail load in Portugal and Spain exceeds its own
generation. Its median X is negative in every hour, most of all at midday
(about −10 €/MWh from 2021). Legs A and B and the chapter's net-buyer shares
(§4.5) were rerun on the exposed position on 2026-09-30 (§4, and
`rq-midday-hydro.md` §3.20).

## 3. Measurement: every term is built

| term | object | where | status |
|---|---|---|---|
| p_t | Spanish or Portuguese clearing price, by the unit's zone | `omie_day_ahead_prices.parquet` | complete 2018–2026 |
| \|RD′_ft\| | rivals' offer density within ±h of p, own sell **and** buy offers removed | `firm_residual_demand_full_owner.parquet`, `firm_incentive_net.parquet` | built, 5.5 M firm-periods |
| n_ft | cleared sales − purchases over every unit a firm owns | `firm_x.py`, `firm_incentive_rebuild.py` | built on the exposed position (§2.4) and on owners by date and share (`lib/unit_ownership.py`, 2026-10-02; shares confirmed by the reactors' bilateral flows) |
| c, thermal | gas or coal / efficiency + carbon, gas-cap adjusted | `implied_marginal_cost_daily.parquet` | built for 68 plant-specific Spanish units and, from 2026-10-05, Portugal's 16; `_bid` columns use prices final at 12:00 on D-1. **Omits O&M and start-ups** |
| c, thermal, bound | the minimum-income condition plants declare | `cab` | 2017 → 2025-03-18 on one basis |
| c, hydro (λ) | the unit-day's volume-weighted offer-price quantiles | `water_value_revealed.parquet` (§3.16) | built for the auction-route owners (EDP, Movhera, Repsol) |
| storage | hours of full output per cascade | `storage_hours.parquet` (§3.17) | Portugal only, lower bound |
| solar | day-ahead offered solar of non-EDP units | `build_solar_instrument.py` (§3.10) | built; the clear-sky version failed |

## 4. Identification: four legs

Each leg uses a different source of variation and handles the cost term
differently. The first gives a result; the rest are tests with a plan.

### Leg A — hydro within the day: cost differenced out. **Done; holds on the exposed position.**

Rerun 2026-09-30 on the exposed position (§2.4; `rq-midday-hydro.md` §3.20).
Within the day the exposed X keeps nearly the as-built shape, so every
conclusion below stands. The figures quoted are the exposed ones.

Under A1, λ is constant across a unit-day, so a unit-day fixed effect removes it
and the curve's movement across hours identifies β. X varies within the day
with solar, which is the instrument. Assumptions A1–A5 are in the water-value
spec §5.

- **EDP.** Four cascades offer an identical curve all day, which rules out
  within-day shaping for any incentive (§3.13). The three that reshape respond
  with the market-power sign from 2024, at an implied β of 0.03–0.14 (§3.14,
  §3.20).
  They are also the small or partly run-of-river ones (§3.17), which favours a
  physical reading.
- **Iberdrola.** It sells storage hydro mainly through bilateral self-supply, so
  its auction offer is a residual (§3.7–3.8). Its hourly water allocation fits
  price-taking and fits supply-function Nash clearly worse, in every era (§3.15).

**Verdict: within-day market power in storage hydro is at most small.**

### Leg B — hydro across days: cost modelled by the Euler equation. **First pass withdrawn; run in levels 2026-10-07: β −0.26 [−0.72, 0.04] with reactor outages (F 21.5); at-cost instrument −0.22 [−0.30, −0.15] (F 407), 2024–25 −0.16; Nash rejected (`rq-leg-b-levels.md`).**

**Withdrawn 2026-09-30** (`rq-midday-hydro.md` §3.20). On the exposed position
the day's offered solar has no first stage for EDP's day-mean X (F 0.4–1.9 in
every sample; every Anderson–Rubin set is the whole line). The earlier first
stage came from SU Eletricidade: its pass-through sales fall by 334 MW per GW of
rivals' solar (t −9.1), while EDP's own exposed position does not move with the
day's solar. So the results below tested a regulated supplier's weather-driven
volume, not EDP's incentive. **The across-day margin is untested** and needs an
instrument that moves EDP's day-level exposed X. The design and the history are
kept below.

EDP's stable cascades submit one curve per day, so any market power they
exercise sits in the day's **level**. Within a unit-week, λ moves only with news
(the martingale). The test is λ̂₅₀(u, d) on the day's mean X, instrumented by the
day's offered solar, with unit × week fixed effects and the forward price as a
control.

- **Confounder.** A sunny day leaves water in the reservoir, which lowers λ with
  the same sign as market power. Its size falls with storage.
- **Where it can be read.** Only on units holding two weeks or more: Guadiana,
  Tejo-Mondego and the Cávado–Lima pair (§3.17).
- **What was known before the test.** λ̂ tracks the forward price one-for-one
  (1.11, 1.22, 0.95 by group) and holds its place in the month's price
  distribution (§3.16).
- **Result, 2026-09-29 (§3.18) — withdrawn, see above.** On the large reservoirs, β = 0.09, with an
  Anderson–Rubin set of [−0.50, 0.79]. That rejects Nash and does not
  distinguish small β from zero. It is robust across quantiles and to the
  independent-owner instrument. 2024–26 alone cannot reject Nash (F = 12), and a
  slow, weeks-long withholding is absorbed by the week fixed effect and left
  untested.
- **The water value's level, 2026-10-07** (`rq-water-value-forward.md`): a price-taker's
  λ* from OMIP forwards, last year's hourly price shape and the unit's usual capacity
  factor (λ* = the 1 − cf percentile of expected prices over 30 or 90 days). It matches
  the water value EDP's four big cascades reveal within 6% (correlations 0.81–0.91);
  Iberdrola, Naturgy and Movhera offer half again to double it. Leg B in levels can use
  λ̂ − λ*; the at-cost instrument can use λ* on hydro. With reservoir storage in it
  (MITECO by basin, SNIRH), every group offers 0.90–1.19 × λ* at the volume it expects
  to run: the 2–3× gap was turbine capacity without water (§5.3 of that note). Net of
  bilateral contracts (§5.5, 2026-10-08) Iberdrola's gap narrows (1.16 → 1.11), Naturgy's
  stays (1.22) and Endesa's widens (1.35). The capacity Endesa and Naturgy leave unoffered
  is mostly not declared out of service (17% is; Iberdrola's 96%, §5.6) nor offered in the
  intraday sessions (Endesa 2–4% of the rest, Naturgy 16–42%, §5.7).
- **Leg B in levels, 2026-10-07** (`rq-leg-b-levels.md`). The hydro step condition with
  λ*30s as the cost, b_k − λ* = β·X̃_k, unit × month and class × hour effects, so the
  day's level stays in. Reactor outages move the day level (F 21.5, against 5.6 within
  the day): β −0.26, Anderson–Rubin [−0.72, 0.04]; with regional wind too −0.35
  [−0.83, −0.15], a sign that does not survive λ*90. Nash rejected in every usable
  specification, upper bound ≤ 0.43; price-taking not rejected with outages alone.
  2024–2025 not identified (F 2–3). The stored-water paper (Arzhintar et al.
  2025) recovers λ by assuming β = 1; on the hours a storage unit sets the price here,
  X is under €1–6, so that assumption moves λ̂ by a euro or two and cannot test conduct.
- **The at-cost instrument on hydro, 2026-10-07** (`rq-leg-b-levels.md` §5). X re-read
  with each firm's hydro at λ*30s (`step_engine.py --kind hydro --comp`), at the day's
  median λ*: F 90–410. Unit × month −0.22 [−0.30, −0.15]; unit × day −0.37; unit only
  −0.01 [−0.12, 0.09]; outages agree (overidentified set nonempty). **2024–2025
  identified: −0.16 [−0.25, −0.06].** 2019 – 2021H1 +0.14 [0.02, 0.26]. Nash rejected
  everywhere; upper bound 0.12 outside 2019 – 2021H1. The sign moves with the fixed effects
  and period exactly as for thermal plant; the negative values come from net sellers'
  steps (β⁺ −0.35, β⁻ ≈ 0), cause open. **Not the firm's own zero-priced output or its
  water** (§6.1): controls for its zero-priced offers and its catchments' rain leave β at
  −0.20 (hydro) and −0.26 (thermal). **The paper's wrong storage sign is the years, not
  incomplete storage data** (§6.2): with year effects fill gives −0.9 per 10 points, and
  90-day catchment rain in its place −2.4 per sd; across years λ̂ rose €15 against the
  baseload forward as solar moved hydro's price-setting hours to the evening, while
  2023–2025 were wetter than 2019–2022.
- **Second pass, 2026-09-30 (§3.19): zero-price middays included — withdrawn with the first.** X is
  rebuilt from the bids for every clean period and reproduces the panel's X
  exactly where the panel has it. At a zero price, X ≈ 0: rivals' slope is nine
  times flatter and EDP is a net buyer half the time. Pooled large-storage β =
  0.13, AR [−0.43, 0.77], F = 35: a firmer rejection of Nash. 2024–26 gains 73
  days and F rises to 16, but the set [−0.72, 1.13] still contains β = 1. The
  solar era needs a stronger instrument, not more periods.

### Leg C — thermal plant: cost observed. **Run 2026-10-01; β ≈ 3, explained 2026-10-05 as the merit order, not conduct (§9.1).**

For a gas or coal unit c is measured, so the condition can be tested in
**levels**, which no other leg can do. The design is route 2 of three
considered; route 3 is its robustness check and route 1 is folded into leg D.

**Why the earlier attempts failed** (`markdown_contract_test.py`, verdict "not
identified"). Four reasons, each now handled:

| failure | handling here |
|---|---|
| simultaneity: a unit that marks down clears more, which raises measured n | X instrumented by rivals' offered wind and solar |
| n persistent within a firm, so fixed effects absorbed it | X varies by period with rivals' slope, not only with n |
| efficiency error, multiplicative, growing with the gas price | unit-specific fuel-cost slope, with JRC efficiency as validation |
| start-up costs priced into cheap first tranches | only periods with the unit online the period before and after |

**Sample.** Firm-periods in which one of the firm's gas or coal units is
**partly dispatched**: some of its offered volume cleared and some did not, so p
lies within that unit's curve and its cost is the firm's marginal cost. The unit
must also be cleared in t−1 and t+1, so any start-up is sunk. Each such unit-period
is one observation; a firm with two units at its margin contributes both. Firms: every
group owning matched thermal plant (`jrc_cab_match.parquet`, 77 units). Years
2018–2023; from 2022-06-15 the gas-capped cost (`marginal_cost_capped_eur_mwh`).
Combined cycle set the price in 35% of resolved periods in 2022 and 2.3% in
2026, so later years add little.

**Two specifications.**

1. **Cost imposed.** p_t − c_ut = a_u + β · X_ft + ε, with c from JRC
   efficiency. a_u absorbs O&M and any constant bias.
2. **Heat rate estimated.** p_t = a_u + h_u · (gas_t + 0.202 · co2_t) + β · X_ft
   + ε. The unit-specific slope h_u absorbs a multiplicative efficiency error.
   **Validation:** ĥ_u must sit near 1/eff for the 46 gas units with a
   plant-specific JRC efficiency. If it does not, specification 1 is not
   trusted.

X uses the exposed n (§2.4) and rivals' slope within ±5 €/MWh, own offers
removed. Instruments: rivals' offered wind and solar, built as `z_offered` is
(§3.10) from units the firm does not own. Wind is the main one here, since
offered solar was small before 2022. Errors clustered by week, Anderson–Rubin
sets.

**The markdown, seen directly.** For a net buyer X < 0, so the condition
predicts p < c at the firm's thermal margin. Tabulate p − c by the sign of X
alongside the regression: a price below observed cost when the firm is buying,
and above it when selling, is the sign prediction of leg D in levels.

**Route 3, the check.** Replace c with the declared minimum-income variable
term (`cab`, declaring units, to 2025-03-18). It is a strategic declaration, so
it bounds rather than measures. `markdown_contract_test.py` found the median
declaring unit's 75th-percentile tranche exactly at it.

**Result, 2026-10-01** ([`rq-leg-c-thermal-cost.md`](../../notes/rq-leg-c-thermal-cost.md)).
In levels β is 3.10 (Anderson–Rubin set [2.59, 3.67], first-stage F 70; 3.06 with
the heat rate estimated, 3.05 with declared cost), so price-taking and full Nash
are both rejected, but the joint hypothesis fails rather than conduct alone: β
moves with which part of X moves, with the slope floor and across years, and the
price sits on the unit's own offer step in 1.4% of rows, where a step bidder's
condition holds only in expectation. Where the unit's own step sets the price,
both instruments give an empty set and solar alone gives β 0.89 without
rejecting β = 1, but those rows are selected on the price and sit about 8 €/MWh
above the condition in levels. An estimate needs the conditions of a step bidder
(§8 step 5b).

### Leg D — the sign of n: cost common, prediction reversed. **Run 2026-10-01; inconclusive, price-taking rejected. Rerun 2026-10-02 with REE's forecasts: β 0.03 net of the fringe (0.024 on owners by date); markdown when buying (β⁻ 0.19), no markup when selling (`rq-leg-d-sign-of-n.md` §7–8).**

The condition predicts a markup for a net seller and a **markdown** for a net
buyer, with the same β. The identifying variation is **within a firm**, because
only 32 parent firms own dispatchable plant.

**Step 0 is the exposed position (§2.4).** On it, the firms whose n changes sign
within a day are the sample. Before the fix: Iberdrola 1,759 firm-days,
EDP 1,614, Repsol 1,139, Naturgy 1,035, Endesa 137. They are recounted after it;
EDP will have fewer. Endesa, a net buyer almost throughout, is the check.

**Units.** Each firm's storage hydro, pumped-storage turbines, combined cycle
and coal. Not nuclear, wind or solar, which offer at or near zero.

**Outcome.** The §3.14 measure: the share of capacity a unit offers at or below
the unit-*day*'s own median offer price. The reference price is fixed within the
day, so no tranche needs to be the same across hours. Units whose curve is
identical all day give no variation; they are uninformative, not biasing.

**Model.**

```
y_ut  =  α_ud  +  γ⁺ · X⁺_ft  +  γ⁻ · X⁻_ft  +  ε_ut        X⁺ = max(X, 0),  X⁻ = min(X, 0)
```

α_ud is a unit × day fixed effect, which removes the water value (A1) or the
day's fuel price. Errors clustered by week.

**Instruments.** Rivals' offered solar z_t, and z_t × s_f, where s_f = 1 if the
firm was a net seller in the same period the day before. s_f is fixed when the
offer is made.

**Predictions.** A higher X lifts the curve, so less capacity sits below a fixed
price: γ < 0 is the market-power sign.

| conduct | γ⁺ | γ⁻ |
|---|---|---|
| price-taking | 0 | 0 |
| supply-function Nash on n | < 0 | **equal to γ⁺** |
| market power on output q, ignoring purchases | < 0 | **> 0** |

The last row is the alternative leg D exists to reject: a firm that acts on its
output marks up even while it is a net buyer, so thinner rivals raise its offers
whatever the sign of n. The test is γ⁺ = γ⁻, with the sign of γ⁻. γ is put on
the β scale by the curve's local offer density, as in §3.14.

**Limits.** Flat-offering units make it a test on the reshaping units and on
thermal plant. Firm-days with both signs carry the kink; the rest identify γ⁺ or
γ⁻ alone.

**Result, 2026-10-01** ([`rq-leg-d-sign-of-n.md`](../../notes/rq-leg-d-sign-of-n.md)).
Price-taking is rejected in every pooled specification (Anderson–Rubin p ≤
1.1·10⁻⁶ over 5.95 M unit-hours); Endesa alone, with 58 seller weeks, does not
reject it. A Nash-signed common slope fits only where yesterday's sign of n, the
interaction instrument's own main effect, is left uncontrolled (β 0.45–0.58);
with it controlled the common slope is undetermined, absent or of the wrong
sign, on weak first stages. Separating Nash from output conduct needs an
instrument for the sign of n that is not a lagged outcome.

## 5. What each existing result becomes

| result | term or leg | reading |
|---|---|---|
| market η fell 1.83 → 0.45 | \|RD′\| | ability to move the price rose; established |
| near-margin concentration stepped up +79% across 2021–23 | who owns \|RD′\| near p | the margin was re-owned around the crisis; a step, not a trend |
| the thinning is at midday | \|RD′\| by hour | where solar acts; motivates legs A and B |
| gas → hydro at the margin | c | why fuel-cost markups failed; why λ is the cost to model |
| firm ability peaked in 2022 | \|RD′_f\| | established, rebuilt |
| Endesa, Naturgy and EDP net buyers; Iberdrola in most periods to 2023; Repsol from 2024 | n (exposed) | the sign in leg D (§2.4) |
| Endesa's 2024 "flip" | n | withdrawn: contracts subtracted twice |
| EDP flat curves; small β in reshaping cascades | leg A | β_within ≈ 0 |
| Iberdrola's allocation is price-taking | leg A | β_within ≈ 0 |
| λ tracks the forward; quantile position stable | c = λ, leg B | the benchmark leg B tests against |
| storage-hours | leg B | where the confounder is small |
| six withdrawn designs | c | each measured a markup against a fuel cost; this framework replaces that term |

## 6. Limits

- **Financial hedges are unobserved.** n captures physical positions only, so X
  is measured with error, most for firms that hedge on OMIP. Bound it; do not
  claim to measure it.
- **Representation is visible only where the owner says so.** Regulated
  suppliers are excluded by name (§2.4). Third-party plants a large firm sells
  as an ordinary representative, under its own entity name, stay in its n and
  cannot be separated.
- **Few firms.** β has to be identified within firms over time, never across
  32 firms.
- **Selection.** The firm panel drops market splitting (6.7% of periods),
  clearing-identity failures (0.7%) and p* ≤ 1 €/MWh (5.0%). The last is
  where solar bites hardest, so late years describe a shrinking subset
  (chapter §5.6).
- **Water value.** Measured only for units that sell through the auction.
  Storage is Portugal only, and a floor. EDP's Cávado and Lima units swapped
  about 1,000 MW in March 2024 (§3.17).
- **It is a conduct test, not an equilibrium model.** It says whether firms
  exercise power and on which margin. It does not predict prices under a
  different market design.

## 7. The payoff: a counterfactual price

With β estimated, each firm's offers can be shifted down by β̂·X and the auction
re-cleared on the archived bid curves. The price with market power removed is
then **observed p minus re-cleared p**, by hour and year, and can be split into
the part due to solar-driven changes in X. This needs nothing beyond the bid
archive and β̂.

**Hydro, run 2026-10-07** (`rq-counterfactual-hydro.md`). β is small, so the β̂·X shift
moves little; the counterfactual run instead re-clears each valid hour with storage hydro
offered at the frozen hydro cost (`hydro_cost_daily.parquet`). Holding each unit's monthly
water at what it used and pricing it as a price-taker: −€0.83/MWh on average (1.0%), −€2.2
(3.1%) in 2025, all in the evening peak (−€9 to −15 at 20:00–22:00 in 2024–2025); EDP and
Iberdrola most of it. An upper bound on the pricing of given water (it assumes a cascade
can run full capacity at the peak); not shown to be market power (leg B). Most of
Iberdrola's, Endesa's and Naturgy's hydro is sold bilaterally, outside the auction.

## 8. Plan

1. ~~**Leg B**~~ — first and second passes done 2026-09-29/30 (§3.18–3.19),
   then **withdrawn** on the exposed position (§3.20): no first stage.
2. ~~**The exposed position**~~ (§2.4) — done 2026-09-30. The rule is
   `is_pass_through` / `exposed_group` in `lib/omie_owner.py`, pinned by
   `qa/check_exposed_position.py`. n is computed in `firm_x.py` (the five large
   firms, every period) and `firm_incentive_rebuild.py` (all firms, the
   chapter), which agree to a correlation of 1.000000. The hydro panels read
   `firm_x`; `own_demand_in_band.py` and `firm_net_position.py` remain as
   diagnostics of the as-built measure. EDP Comercial merged into EDP.
3. ~~**Rerun legs A and B**~~ — done 2026-09-30 (§3.20; chapter §4.5). Leg A
   holds; leg B's first pass is withdrawn.
4. ~~**Leg D**~~ — run 2026-10-01; inconclusive: price-taking rejected, conduct not separated (`rq-leg-d-sign-of-n.md`).
5. ~~**Rivals' offered wind**, then **leg C**~~ — run 2026-10-01; β ≈ 3 reflects step
   gaps, not conduct (`rq-leg-c-thermal-cost.md`).
5b. **Leg C on the offer steps: an estimate, not a diagnostic.** *Proposed
   2026-10-01, after the user asked for an estimate rather than the selected
   own-step rows; to be confirmed before it is built.* The full design, with the
   forecast instruments, the one-β test, the water value and the natural
   experiments, is [`2026-10-01-step-offer-design.md`](2026-10-01-step-offer-design.md). Each step a unit offers is
   chosen before the auction, at a price b_k and a length, observed whether or not
   the price lands on it. A step bidder's conditions hold in expectation over the
   residual demand it could face (Wolak 2007; Kastl 2011; Reguant 2014, on this
   market):
   - **price of step k**, over the periods in which k sets the price:
     E[1{k sets p} · ((b_k − c) · |RD′| − β · n)] = 0, so
     b_k − c = β · E[n | k] / E[|RD′| | k], a slope-weighted mean of X (not
     E[X | k], which the convexity of 1/|RD′| inflates);
   - **length of step k**, over the periods in which p falls in the gap above it:
     E[(p − c − β · X) · 1{p in the gap above k}] = 0.

   The expectations are built by resampling: draw residual-demand curves from
   rivals' actual offers on comparable periods, smooth them as Wolak and Reguant
   do, clear each against the firm's own offer, and record which step sets the
   price, n and |RD′| there. The unconditional moments weight each step by its
   probability of setting the price, so nothing is selected on the realised
   price; steps that never set it (minimum-load tranches, withholding blocks)
   give inequalities only. Reguant also puts the minimum-income condition and
   start-up costs into the bidder's problem, which this market's offers carry
   (`cab`). **One β across legs** follows with two qualifications: units that
   submit one curve per day (EDP's flat cascades) need a day-level condition
   summed over hours, and leg D's split is by the sign of E[n | k], since a
   step's price-setting periods can mix signs. The ex-post optimal bid
   (`rq-gas-cap-conduct.md`, 2026-08-18) is the one-draw case; the gas cap's
   statutory cost (2022-06-15 to 2023-12-31) is its sharpest window.
6. **A spatial weather instrument**, for legs C and D (now built from forecasts:
   step-offer design §5.1). Offered renewable volume is
   partly a choice, so a firm's own offered renewables are not an instrument. In a
   scratch probe (2026-10-01, not committed; corrected for an hour misalignment by
   the final review) a firm's own offered solar and wind moved X down on both sides
   of n = 0 (X⁺ −0.85, X⁻ −1.33 €/MWh per GW), where more own supply should raise
   n; own wind alone moved X⁻ down (t −2.4) and X⁺ not at all. Rivals' offered wind
   carries a milder version of the same doubt. Weather at each farm's own site times capacity fixed in advance cannot
   respond to strategy, and it differs by firm because fleets sit in different
   regions. Needs farm locations and owners (MITECO's RAIPEE register, OpenStreetMap,
   or Global Energy Monitor's tracker) matched to OMIE units, then ERA5 at each site.
   OMIE's interconnection capacity (fetched 2026-10-01) looked no better in the same
   probe: it barely moved X (|t| ≤ 1.3), and the fringe's offers responded to it about
   as much. The probe's hour alignment was off, so that is a lead, not a result.
7. **The counterfactual price** (§7), once one β is credible.

**For the supervisor.** Is the thesis the within-day margin alone (done,
publishable as a null against Nash), or all four legs with the counterfactual?
Leg B was to decide whether the across-day margin is worth the full effort;
it now needs a new instrument first (§3.20).

## 9. The next design: one condition for every firm, read from offers (2026-10-05)

From the 2026-10-02/03 discussion (`notes/handoff-2026-10-05.md` §4) and the
diagnosis of leg C. Each idea is assessed against what the data have shown; the
ranking is a proposal.

### 9.1 What the diagnosis of β ≈ 3 changes

Leg C's β ≈ 3 and the "invalid" β = 3.6 of leg A's price-setting version
(`rq-midday-hydro.md` §3.11) are one artefact. A plant's p − c moves with the market
price, which other plants set in 98.6% of rows. One GW of rivals' renewables lowers
it by about 2 €/MWh (1 GW over a rivals' slope of about 500 MW per €/MWh) for every
plant: the other owners' p − c falls 2.56 / 1.31 per GW of wind / solar while their
X does not move (0.00 / −0.02). With n alone moving, β̂ equals rivals' slope over
the firm's own supply response, 504 / 52 ≈ 10 (estimate 10.9): a ratio of slopes, as
in Bresnahan (1982), not conduct.

**The rule this gives.** A parameter that differs by firm is read from an outcome
that differs by firm (the firm's own offers), net of how price-takers' offers respond
to the same shock, with instruments known when offers are submitted. Legs A and D
follow it and give β 0.02–0.14. Two consequences:

- **The step estimator (§8 step 5b) needs the benchmark too.** On the rows where
  the unit's own step sets the price, the other owners' offer minus cost still falls
  1.7–2.2 €/MWh per GW of forecast with X fixed: a lower step of the same ladder sets
  the price. Offer ladders slope up without market power, so the estimator must net
  out a non-strategic ladder (from price-takers of the same technology) or put it in
  c(q). Without it the step moments inherit part of the bias.
- **Within-day β is small; β is not shown to be small.** Within-day estimates
  cannot see a day-level strategy (EDP's flat cascades submit one curve a day), and
  the across-day margin (leg B) has no instrument yet. §9.3 gives it one.

### 9.2 The model, stated once

For every dispatchable unit u of every firm f, in period t of day d:

```
y_ut = α_ud + δ_(tech × t) + γ · X_ft + ε_ut,        β = −γ / (offer density at the reference price)
```

- **y**: the unit's own offer at fixed points, either quantity offered below the
  unit-day's own price quantiles (legs A and D; all technologies) or, for thermal
  plant, offer price at fixed shares of capacity minus c (levels; known-at-bidding
  cost, `_bid` columns).
- **δ_(tech × t)** absorbs the merit-order movement and every common shock
  (national forecasts, fuel, demand). What it does not absorb is variation in X
  across firms within the period, so **only firm-specific shocks identify γ**. That
  is why the shift-share instruments matter: common instruments are absorbed by the
  period effects that make the design valid.
- **The fringe** enters as the low-dose end of X, not as an untreated group.

### 9.3 Instruments for n, ranked

| rank | instrument | dose by firm | evidence so far | threat | verdict |
|---|---|---|---|---|---|
| 1 | **outages of co-owned reactors, by share** | lost MW × listed share (Almaraz 1 down: Iberdrola −52.7%, Endesa −36%, Naturgy −11.3%) | 2018-01 → 2026-05 from PDBF: 145 outage spells of ≥ 2 days, 2,687 reactor-days, 79 of ≤ 10 days; Endesa's and Iberdrola's daily doses correlate 0.65. Shares confirmed by the bilateral flows (`report-ownership-mapping.md` §4) | output modulation and economic shutdowns at low prices since about 2023 are price responses, not shocks; refuelling dates are chosen months ahead | **first.** Keep declared refuelling and unplanned trips only (`indisp` reasons, PDBF schedules where `indisp` has gaps). The date choice is common to every co-owner in the period, so only the difference in doses identifies. Multi-week, so it also moves day-level X: **leg B's missing first stage** |
| 2 | own-catchment rain × share | GW × share × catchment anomaly | complete data: pooled F 21.3 (90 days), quarter clusters 11.9, wild bootstrap over firms p 0.044 (`rq-hydro-rain-first-stage.md`) | six firms; EDP's, Iberdrola's, Movhera's and Naturgy's indices correlate 0.94–0.98, so the effective number of independent shocks (Borusyak, Hull & Jaravel 2022) is small | second; mostly for leg B and for EDP / Iberdrola |
| 3 | own regional wind and solar | own capacity by region × regional weather | national forecasts lower every firm's n (displacement beats own fleet); with period effects only (own share − mean) × weather is left. **Locations 2026-10-05:** 54% of wind GW and 16% of PV matched by name to OSM and WRI; owner via the REE agent (2026 snapshot, undated), since REE's farm units are not OMIE units. **Regions 2026-10-05:** each farm and turbine placed in its autonomous community from Eurostat's NUTS polygons; located wind is 49–70% of ESIOS's capacity in the five largest wind regions (Cataluña 15%). **Run 2026-10-05** (`rq-reactor-outages.md` §9): own wind above the national rate, by region (ESIOS measured output by province), raises X by about 4 €/MWh per GW, F 22–28 at the unit level; thermal offers give β +0.9, set [−2.6, 4.5]; with the outages −1.6, [−4.3, 1.5]; weak from 2022 (F 3–8) | local grid constraints (answered by region × hour effects); the 2026 farm snapshot; PV coverage | third; strongest unit-level first stage, does not narrow β |
| 4 | rivals' shocks for \|RD′\| | rivals' outages, interconnector capacity | moving only the slope gave β −16 at F 7 (leg C); interconnector capacity barely moved X in a probe | rival outages shift residual demand rather than rotate it | low; a rotation instrument has not been found |

**Built 2026-10-05** (`notes/rq-reactor-outages.md`). 49 unplanned and 51 planned
outage spells; with firm × month and hour effects, each MW of a firm's unplanned dose
lowers its exposed n by 0.86 MW (F 121; planned 0.89, F 138), and X by about 5 €/MWh
per GW. Unplanned outages follow ordinary prices (+0.6 €/MWh two days before, se 3.4).
The undeclared cuts of 2024–2026 (5–8 TWh a year) follow low prices and are excluded.
Thin for Naturgy and EDP, whose doses come only through Almaraz and Trillo.

**§9.2 run on it, 2026-10-05** (`rq-reactor-outages.md` §6). Offer price at 25% of
offered volume, unit × week and technology × date × hour effects: **β −0.88, 95%
Anderson–Rubin set [−4.20, 0.66]**. β = 1 is rejected (p 0.03) and β = 0 is not; at
the 50% point, [−3.95, 1.25]. At the unit level the first stage is only F ≈ 10,
because week effects absorb multi-week outages. Point estimates are negative, from
combined cycles after unplanned trips (t 1.7). Neither withdrawal from the auction
(offered volume does not move) nor location (the dose of nearby reactors, any owner,
has no effect) explains it. So the across-day margin bounds β below 1 and does not
separate 0 from 0.5.

### 9.4 Heterogeneity and the control group

- **The fringe is an assumption, not a fact.** Hortaçsu and Puller (2008) found
  small Texas firms bidding far from their best response, so "the fringe responds
  as a price-taker" must be tested. The fringe's thermal offers respond to the
  forecasts as the five firms' do (leg D §7.2), but its hydro does not.
- **The theory already specifies the heterogeneity**: the response is β times X, and
  X carries 1/|RD′|. The parametric model is the test; sorted groups by predicted
  dose (Chernozhukov, Demirer, Duflo & Fernández-Val) are the way to show it.
- **An instrumental forest** (Athey, Tibshirani & Wager 2019) adds little with five
  strategic firms and weekly dependence. Parked.
- **The buyer–seller asymmetry** (β⁻ 0.19, β⁺ ≈ 0) is the most distinctive result,
  but it rests on differences between firms (Endesa a buyer almost always, Repsol
  mostly a seller). Reactor outages move the same firm across n = 0, which tests it
  within firm.

### 9.5 Sequential markets: anticipated against surprise

The monetary-policy distinction (Romer & Romer 2004; Kuttner 2001; Nakamura &
Steinsson 2018) maps onto the two auctions:

- **Day-ahead offers** respond to the D-1 forecast, which is in the firm's
  information set. Residualising it on what was predictable earlier (normal weather
  for the hour and date, yesterday's output, capacity) is a robustness check: it
  removes slow confounders, not the merit-order effect, which anticipated and
  unanticipated wind both cause.
- **Placebo**: day-ahead offers must not respond to the realised forecast error
  (realised − D-1 forecast), which arrives after they are locked. A response would
  mean firms forecast better than REE.
- **Intraday offers** come after the day-ahead positions are fixed, so the forecast
  error moves each firm's intraday position by its fleet exposure: its wind share ×
  the national surprise, a shift-share across firms within the hour. Same condition,
  intraday n. Data on disk (`curva_pibc_uof`, `marginalpibc`, REE forecasts).
  **Run 2026-10-06; fails** (`rq-intraday-surprise.md`). The surprise reaches each firm
  through its whole fleet: hydro owners buy back output (EDP −52, Iberdrola −30 MW per
  GW of wind surprise), Acciona sells (+38), so the wind-share shift-share has F 3.3.
  Firm-specific instruments have a first stage (F 28 at firm level, 5–6 at unit level)
  but an empty Anderson–Rubin set on thermal offers, and the day-ahead placebo fails
  (F 6–31, also at prices above 40 €/MWh): firms know part of REE's forecast error.
- **The buyers' test** (Ito & Reguant 2016): the day-ahead − intraday price premium
  should rise with the five firms' combined exposed n and turn negative when they are
  net buyers. Cheap; a market-level time series, so a description, not an estimate.
  Control for the forecast errors, which also move the premium.
  **Run 2026-10-06** (`rq-da-id-premium.md`): the premium is +0.6 €/MWh on average
  although the five are net buyers in 92.5% of hours, and flat in N (−0.03 €/MWh per
  GW, se 0.035). With N moved by planned reactor outages (F 17.9) it rises the
  predicted way, +0.95 (0.39) per GW: a lead, one instrument.

### 9.6 Policies with a known prediction: tests of c, not of β

A tax or a cap moves cost, not n, so it validates the cost term and pass-through.
That is what leg C in levels needs.

- **The 7% tax on the value of Spanish generation (IVPEE)**: suspended from
  2021-07-01 to 2023-12-31; back at 3.5% in 2024 Q1, 5.25% in Q2, and 7% from
  2024-07-01 (RDL 12/2021 and extensions; RDL 8/2023). It taxes Spanish units only,
  so a Spanish unit's condition becomes b = c/(1 − τ) + β · X, and its offer moves
  by c · τ/(1 − τ) (about 6 €/MWh at c = 80) relative to a Portuguese unit in the
  same auction. That gives four dated events with known doses, and Portugal's ten
  combined cycles now have costs (JRC, 2026-10-05). Threats: July 2021 is the start
  of the gas crisis (common to both countries, absorbed by period effects); prices
  split by zone (use the zone price); Portugal's CESE levy is on assets, not output.
  **The main threat, found 2026-10-05: Portugal's clawback** (*mecanismo de
  equilíbrio concorrencial*, Decreto-Lei 74/2013, Portaria 282/2019) charges
  Portuguese producers per MWh injected, by technology, for ERSE's estimate of the
  price effect of Spain's IVPEE. It was suspended over the same months (2021 H2 →
  2023) and came back in 2024 (ERSE, public consultation 129, documento
  justificativo §2–4). So the Portuguese units are not untreated: the predicted
  Spain − Portugal gap is c·τ/(1 − τ) minus the expected clawback per MWh (e.g. 2019
  advance payment 2.71 €/MWh coal, 4.18 others; final 2019 2.24 renewables).
  Combined cycles pay only above 2,000 equivalent hours a year, so a CCGT's marginal
  MWh may be exempt. The government decided to abolish it on 2025-12-17. To check
  before running: the clawback's yearly values, and whether it was also suspended
  in 2018 Q4 – 2019 Q1 (RDL 15/2018 suspended the IVPEE then).
  **The 2024 steps escape it (checked 2026-10-06).** From PDBF, every Portuguese
  combined cycle ran under 1,200 equivalent hours in 2024 (14–1,190), against
  1,400–5,700 in 2018–2022: none of their 2024 output reached the 2,000-hour
  threshold, so they were untreated when the IVPEE came back (3.5% from 2024-01-01,
  5.25% from 04-01, 7% from 07-01). The earlier events need the clawback's values.
  **Use the declared minimum-income variable term as the outcome**, not the offer
  price: Portuguese combined cycles offered at a median 0 €/MWh at half their volume
  in 2024, while 89–100% of combined cycles in both countries declared a variable
  term (`cab`, median 79–144 €/MWh in 2023–2024), until it ended on 2025-03-18. The
  tax is on revenue, so the declared term should rise by τ/(1 − τ) relative to
  Portugal's: +3.6%, +5.5%, +7.5% at the three steps. Raw quarterly medians show no
  obvious jump; that is before any control.
  **Run 2026-10-06** (`rq-ivpee-tax-test.md`): pass-through θ 0.04 (se 0.56; p 0.18
  for θ = 1), with unit cost slopes, since the declared term does not scale with fuel
  cost. On the step days the gap moves by about the predicted amount in July (+2.1%
  against +1.9%), but ordinary month starts jump with an sd of 3.5–5.5%: the 2024
  steps are too small to test c. **The full 7% steps do** (`ivpee_2019_test.py`,
  same note §5): on 2019-04-01, 2018-10-07 and 2021-07-01 the gap moves the
  predicted way by more than on 95–100% of ordinary month starts; stacked θ 1.45
  (p < 0.001 for θ = 0, 0.18 for θ = 1). Spanish declared costs move 5–10% the
  predicted way at every event and fuel (coal on 1 April 2019: +8.0% on the day,
  cost flat, Portugal flat); Portuguese moves on the same days, unexplained, make
  the gap overshoot.
- **The gas cap** (2022-06-15 → 2023-12-31): dose per unit (gas − reference) /
  efficiency; the sharpest window for the cost in levels.
- **The 2021 windfall levy**: it acts through contracting (n via θ) and needs 2021
  ownership, which no listing gives. Parked.
- **Changes-in-changes** (Athey & Imbens 2006) is a way to show whole distributions;
  the known-dose prediction is in means.

### 9.7 Sequence

1. ~~**Outage table**~~ — built 2026-10-05: first stage F 121 (unplanned), trips not
   timed on prices (`rq-reactor-outages.md`).
2. ~~**The §9.2 regression with outage doses as instruments**~~ — run 2026-10-05:
   β −0.9, set [−4.2, 0.7], F ≈ 10; β⁺/β⁻ too weak (F 5). Rain added as a second
   instrument (thermal units, unit × month effects): combined β −0.85, set
   [−4.0, 1.8], F 13.5; rain alone also negative. Event study of 21 clean trips: X
   falls at once (−3.5 per GW, days 0–3), offers show no break
   (`rq-reactor-outages.md` §7–8). Regional wind added as a third instrument
   (thermal units, unit × week effects): first stage F 22–28, β +0.9, set
   [−2.6, 4.5]; with the outages β −1.6, [−4.3, 1.5] (§9). Every thermal set
   contains 0 and 1.
3. **IVPEE test** on thermal offers, Spanish against Portuguese, with `_bid` costs.
   It validates c before any levels estimate. *2024 steps run 2026-10-06*
   (`rq-ivpee-tax-test.md`): declared variable cost of combined cycles, θ 0.04
   (se 0.56); steps of 1.8–3.6% are inside the month-start noise (sd 3.5–5.5%).
   *Full 7% steps run 2026-10-06*: 2019-04-01, 2018-10-07, 2021-07-01 all move the
   predicted way; stacked θ 1.45, zero pass-through rejected, full not. The
   declared minimum-income term behaves like a cost.
4. **Day-ahead − intraday premium** against combined n (descriptive). *Run
   2026-10-06* (`rq-da-id-premium.md`): flat in N; +0.95 (0.39) per GW when N is
   moved by planned reactor outages.
5. **Intraday surprise design.** *Run 2026-10-06, fails* (`rq-intraday-surprise.md`):
   no first stage on wind shares, contradictory instruments firm by firm, and the
   day-ahead placebo fails. *The firm's own surprise, run 2026-10-06*
   (`rq-intraday-surprise.md` §6): located farms' output minus its own day-ahead wind
   schedule (`pdbf`, bilateral included). First stage strong (intraday n F 120, unit
   level F 24), but X moves only 0.40 €/MWh per GW (thermal set [−19.2, 13.6]), and the
   day-ahead placebo fails with the schedule and the forecast levels held (five firms'
   day-ahead X F 12, 18 at prices above 40). Stopped after three variants.
6. **Step estimator** with the non-strategic ladder netted (§9.1), once steps 2–3
   pin β's range and c. *Run 2026-10-06* (`rq-step-estimator.md`), gas and coal
   2019–2023. Offered curves re-clear to the published price only on the effective
   curve (accepted rows below the price, offered rows above; France's coupling flow
   is in the accepted rows only). Residual demand is resampled: 40 nearby hours per
   firm-hour, shifted to the target hour's forecasts. **Price of a step**, with
   reactor outages as instruments: β +0.07, set [−0.68, 1.01] (F 9.9); 2019 – 2021 H1
   −0.16, [−0.60, 0.19] (F 23), full Nash rejected. **Length of a step** fails
   (β −0.84, [−1.58, −0.17]): units repeat yesterday's step boundaries on 48–82% of
   days, so lengths follow the plant and their condition is an inequality.
   *Hydro, run 2026-10-06* (`rq-step-estimator.md` §6), 2019-01 → 2025-09, the water
   value differenced out by unit × day effects: reactor outages β +0.06, set
   [−0.73, 0.37] (F 5); regional wind −0.17, [−0.83, 0.38] (F 11); Nash rejected by
   both. Firm × forecast instruments (F 45–127) give an empty set in every sample: they
   reach hydro offers by routes other than X. Regional wind on 78.5% located wind
   (2026-10-06): −0.12, [−0.61, 0.31] (F 14).
   *At-cost instrument, run 2026-10-07* (`rq-step-estimator.md` §7): X̃ on the curve
   the firm would offer with its gas and coal at cost, the same draws. F 200–700;
   full Nash rejected in every specification (p < 10⁻¹¹). With unit × day effects
   β −0.08, [−0.19, 0.02]; the sign moves with the fixed effects (−0.27 to +0.10 on all
   years, +0.46 in 2019–2021 H1 with fuel × date and hour), so it bounds β from above
   (below 0.6 everywhere) and leaves the sign open. Outages agree with it. Start-up cost
   does not explain the sign (§7.1): on running units declaring a minimum-income
   condition the same pattern holds (−0.32, −0.04, +0.10).

*To verify before use*: the IVPEE decree chain and dates; the reasons OMIE's
`indisp` gives for each reactor outage; whether Portugal's CESE has any per-MWh
component.
