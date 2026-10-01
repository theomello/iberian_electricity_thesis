# The thesis framework: one first-order condition, tested four ways

**Status: proposed 2026-09-29, for the supervisor.** It proposes a candidate
research question; none is adopted in `CLAUDE.md` until one is agreed.

**Revised 2026-09-30:** n is the price-exposed position (§2.4). On it leg A
holds and leg B's first pass is withdrawn for want of a first stage (§4);
legs C and D are designed (§4) and the plan reordered (§8).

**Revised 2026-10-01:** leg D is run and inconclusive: price-taking is rejected,
conduct is not separated (§4). Leg C is run: in levels β ≈ 3 measures where the
price sits in the gaps of stepped offers, not conduct (§4); an estimator on the
offer steps is proposed (§8 step 5b).

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
| n_ft | cleared sales − purchases over every unit a firm owns | `firm_incentive_rebuild.py`, `firm_net_position.py` | built. Ownership groups from OMIE's published owner (Enel Green Power merged into Endesa, 2026-09-29). **To rebuild on the exposed position (§2.4)** |
| c, thermal | gas or coal / efficiency + carbon, gas-cap adjusted | `implied_marginal_cost_daily.parquet` | built for 68 plant-specific units. **Omits O&M and start-ups** |
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

### Leg B — hydro across days: cost modelled by the Euler equation. **First pass withdrawn; untested.**

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
- **Second pass, 2026-09-30 (§3.19): zero-price middays included — withdrawn with the first.** X is
  rebuilt from the bids for every clean period and reproduces the panel's X
  exactly where the panel has it. At a zero price, X ≈ 0: rivals' slope is nine
  times flatter and EDP is a net buyer half the time. Pooled large-storage β =
  0.13, AR [−0.43, 0.77], F = 35: a firmer rejection of Nash. 2024–26 gains 73
  days and F rises to 16, but the set [−0.72, 1.13] still contains β = 1. The
  solar era needs a stronger instrument, not more periods.

### Leg C — thermal plant: cost observed. **Run 2026-10-01; β ≈ 3 reflects step gaps.**

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
are both rejected, but β is not conduct: units offer in steps, the price sits on
the unit's own step in 1.4% of rows, and 2.25 of the 3.10 is the price's distance
above the unit's highest accepted offer, which rivals' renewables move directly.
Where the unit's own step sets the price, β is 0.87–0.89 and full Nash is not
rejected with solar alone (set [0.55, 1.52]), but those rows are selected on the
price. An estimate needs the condition written for step offers (§8 step 5b).

### Leg D — the sign of n: cost common, prediction reversed. **Run 2026-10-01; inconclusive, price-taking rejected.**

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
5b. **Leg C on the offer steps: an estimate, not a diagnostic.** Each step a unit
   offers is chosen before the auction, at a price b_k observed whether or not the
   price lands on it. A step bidder's condition holds in expectation:
   b_k − c = β · E[X | step k sets the price] (Wolak 2007; Reguant 2014, on this
   market). The expectation is built by resampling: draw residual-demand curves
   from rivals' actual offers on comparable periods, clear each against the firm's
   own offer, and record which step sets the price and X there. Every step of every
   unit-period enters, so nothing is selected on the price, and the regressor is
   what the firm could expect, not what happened. The same estimator with a
   unit-day effect in place of c is leg A on the step scale, and split by the sign
   of n it is leg D, so it gives **one β across legs**, whose equality is itself a
   test. The ex-post optimal bid (`rq-gas-cap-conduct.md`, 2026-08-18) is its
   one-draw case; the gas cap's statutory cost (2022-06-15 to 2023-12-31) is its
   sharpest window.
6. **A spatial weather instrument**, for legs C and D. Offered renewable volume is
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
