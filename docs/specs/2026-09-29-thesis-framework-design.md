# The thesis framework: one first-order condition, tested four ways

**Status: proposed 2026-09-29, for the supervisor.** It proposes a candidate
research question; none is adopted in `CLAUDE.md` until one is agreed.

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
| n_ft | net auction position. Physical bilateral contracts never enter the auction, so they drop out of both sales and purchases. Financial hedges would enter it and are unobserved |
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

## 3. Measurement: every term is built

| term | object | where | status |
|---|---|---|---|
| p_t | Spanish or Portuguese clearing price, by the unit's zone | `omie_day_ahead_prices.parquet` | complete 2018–2026 |
| \|RD′_ft\| | rivals' offer density within ±h of p, own sell **and** buy offers removed | `firm_residual_demand_full_owner.parquet`, `firm_incentive_net.parquet` | built, 5.5 M firm-periods |
| n_ft | cleared sales − purchases over every unit a firm owns | `firm_incentive_rebuild.py`, `firm_net_position.py` | built. Ownership groups from OMIE's published owner (Enel Green Power merged into Endesa, 2026-09-29) |
| c, thermal | gas or coal / efficiency + carbon, gas-cap adjusted | `implied_marginal_cost_daily.parquet` | built for 68 plant-specific units. **Omits O&M and start-ups** |
| c, thermal, bound | the minimum-income condition plants declare | `cab` | 2017 → 2025-03-18 on one basis |
| c, hydro (λ) | the unit-day's volume-weighted offer-price quantiles | `water_value_revealed.parquet` (§3.16) | built for the auction-route owners (EDP, Movhera, Repsol) |
| storage | hours of full output per cascade | `storage_hours.parquet` (§3.17) | Portugal only, lower bound |
| solar | day-ahead offered solar of non-EDP units | `build_solar_instrument.py` (§3.10) | built; the clear-sky version failed |

## 4. Identification: four legs

Each leg uses a different source of variation and handles the cost term
differently. The first gives a result; the rest are tests with a plan.

### Leg A — hydro within the day: cost differenced out. **Done.**

Under A1, λ is constant across a unit-day, so a unit-day fixed effect removes it
and the curve's movement across hours identifies β. X varies within the day
with solar, which is the instrument. Assumptions A1–A5 are in the water-value
spec §5.

- **EDP.** Four cascades offer an identical curve all day, which rules out
  within-day shaping for any incentive (§3.13). The three that reshape respond
  with the market-power sign from 2024, at an implied β of 0.03–0.12 (§3.14).
  They are also the small or partly run-of-river ones (§3.17), which favours a
  physical reading.
- **Iberdrola.** It sells storage hydro mainly through bilateral self-supply, so
  its auction offer is a residual (§3.7–3.8). Its hourly water allocation fits
  price-taking and fits supply-function Nash clearly worse, in every era (§3.15).

**Verdict: within-day market power in storage hydro is at most small.**

### Leg B — hydro across days: cost modelled by the Euler equation. **First pass done.**

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
- **Result, 2026-09-29 (§3.18).** On the large reservoirs, β = 0.09, with an
  Anderson–Rubin set of [−0.50, 0.79]. That rejects Nash and does not
  distinguish small β from zero. It is robust across quantiles and to the
  independent-owner instrument. 2024–26 alone cannot reject Nash (F = 12), and a
  slow, weeks-long withholding is absorbed by the week fixed effect and left
  untested.

### Leg C — thermal plant: cost observed. **To redo.**

For a gas or coal unit c is measured, so β comes directly from the condition at
the firm's thermal offers.

- **Why the earlier attempts failed.** They compared offer levels with a
  cost that omits O&M and start-ups.
- **The fix.** Unit fixed effects absorb the constant part of the omitted cost,
  leaving the response of (offer − c) to X over time. The declared
  minimum-income condition bounds start-ups up to 2025-03-18.
- **What must change in the old test.** `hortacsu_puller_test.py` inverts the
  condition for an implied cost, and found that imposing contracts moves those
  costs toward plausible values. It has to move to the net auction position and
  the gas-capped cost before it is reused.
- **Where it is informative.** Combined cycle set the price in 35% of resolved
  periods in 2022 and 2.3% in 2026. So this leg speaks mostly to 2018–2022.

### Leg D — the sign of n: cost common, prediction reversed. **To build.**

The condition predicts a markup for a net seller and a **markdown** for a net
buyer, with the same β. The identifying variation is **within a firm**, because
only 32 parent firms own dispatchable plant.

- **Iberdrola** is a net buyer in 96% of periods in 2018 and 49% in 2026.
- **Repsol** turns from seller (1%) to buyer (90%).
- **EDP** is a buyer in 1–35% of periods, by year.

Periods where the same firm switches sign test whether offers move with X
through zero. This is the sharpest prediction the theory makes. It needs no cost
level, only a cost that is constant within the day (A1 for hydro, the day's fuel
price for thermal), because it compares the same units' offers either side of
n = 0 within a day. In that sense it is legs A and C read at the sign change:
the same regression, with the question put where the prediction is sharpest.

## 5. What each existing result becomes

| result | term or leg | reading |
|---|---|---|
| market η fell 1.83 → 0.45 | \|RD′\| | ability to move the price rose; established |
| near-margin concentration stepped up +79% across 2021–23 | who owns \|RD′\| near p | the margin was re-owned around the crisis; a step, not a trend |
| the thinning is at midday | \|RD′\| by hour | where solar acts; motivates legs A and B |
| gas → hydro at the margin | c | why fuel-cost markups failed; why λ is the cost to model |
| firm ability peaked in 2022 | \|RD′_f\| | established, rebuilt |
| Iberdrola, Endesa and Naturgy net buyers; Repsol from 2024 | n | the sign in leg D |
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

1. ~~**Leg B**~~ — first pass done (§3.18). Strengthen 2024–26 by computing X
   for the zero-price middays the firm panel drops.
2. **Leg D**: offers either side of n = 0 within Iberdrola, Repsol and EDP.
3. **Leg C**: rebuild the thermal test on the net position and the capped cost,
   with unit fixed effects, 2018–2022.
4. **The counterfactual price** (§7), once one β is credible.

**For the supervisor.** Is the thesis the within-day margin alone (done,
publishable as a null against Nash), or all four legs with the counterfactual?
Leg B is what decides whether the across-day margin is worth the full effort.
