# Water value: definition, measurement and use

Design spec, 2026-09-29. **Status: draft for discussion.** It fixes one
definition of the water value, states every assumption the midday-hydro work
rests on, and says which result depends on which. Running results live in
[`notes/rq-midday-hydro.md`](../../notes/rq-midday-hydro.md); section numbers
below (§3.x) refer to it.

---

## 1. Why this exists

Storage hydro sets the price in about three-quarters of the periods whose
marginal technology can be identified (descriptive chapter §4.4). Its marginal
cost is not a fuel cost but the **water value**, which no invoice records. Every
cost-based markup design in this repo failed on the cost measure; the
midday-hydro design avoids measuring it by differencing it out. Both routes
need the same object defined once, with the assumptions made explicit.

## 2. Definition

A storage unit i holds water S in its reservoir. Each period t it chooses
generation q_t (and, if it can pump, pumping r_t), subject to

```
S_{t+1} = S_t + w_t − q_t/ρ + η_p r_t/ρ − spill_t          (water balance)
0 ≤ S_t ≤ S̄        0 ≤ q_t ≤ q̄        0 ≤ r_t ≤ r̄           (storage, turbine, pump)
q_t ≥ q_min,t      |q_t − q_{t−1}| ≤ R                         (flow, ramp)
```

with inflow w_t, energy coefficient ρ (MWh per unit of water, set by head and
efficiency), pump efficiency η_p. The value function V_t(S_t, info_t) is the
expected discounted profit from t on.

**The water value is the shadow price of stored water:**

```
λ_t  =  ∂ E[ V_{t+1}(S_{t+1}, info_{t+1}) ] / ∂S      in €/MWh-equivalent
```

the expected marginal revenue from keeping one more MWh of water for later. It
depends on the reservoir level, expected inflows, expected future prices and
the constraints. It is an opportunity cost, and it is **not observed**.

Across periods, λ evolves as

```
λ_t  =  E_t[λ_{t+1}]  −  κ̄_t  +  κ_t
```

where κ̄_t ≥ 0 binds when the reservoir is full (extra water would spill) and
κ_t ≥ 0 when it is empty. **Where neither bound binds, λ is a martingale** —
constant in expectation from one period to the next.

## 3. What it implies for offers

A price-taker generates in period t when the price covers the water value:

```
p_t  =  λ_t  +  ν̄_t  −  ν_t          (ν̄: turbine limit binds; ν: minimum flow binds)
```

so an unconstrained storage unit **offers its water at λ**. It pumps when
p_t ≤ η_p λ_t.

With market power (Bushnell 2003; Hortaçsu and Puller 2008), firm f equates
marginal *revenue* to λ. With n_ft its **net auction position** (cleared sales
minus cleared purchases over all its units, §3.9):

```
p_t  −  λ_t  =  n_ft / |RD′_ft(p_t)|  ≡  X_ft
```

A net seller (n > 0) offers above λ; a net buyer (n < 0) offers below it, to
push the price down. β, the weight on X in the estimating equation, is 0 under
price-taking and 1 under supply-function Nash.

**X uses the net auction position, not `q − θ`.** Physical bilateral energy
never enters the auction, so it drops out of both sales and purchases.
Subtracting the bilateral schedule from auction sales counts contracts twice
(descriptive chapter §4.5, corrected 2026-09-28).

## 4. Two margins of market power

| margin | mechanism | how it shows | identified by |
|---|---|---|---|
| **within the day** | shift water between hours of different elasticity | the offer curve tilts with X across the day's hours | differencing λ out within a unit-day |
| **across days and seasons** | choose λ's *level*: hold water back to raise future prices | λ above its competitive value, flat within each day | **not** by the within-day design |

**A flat offer within the day is not evidence of competition.** It is evidence
of no *within-day* strategic shaping. A firm can bid a flat λ every day and
still exercise market power through λ's level. Every conclusion in §3.11–3.12
is about the first margin only.

## 5. Assumptions

| # | assumption | what breaks it | test | status |
|---|---|---|---|---|
| **A1** | λ is constant across the hours of a unit-day | a storage bound, turbine limit, minimum flow or ramp binding *within* the day; small reservoirs that fill and empty daily | flag unit-days where output hits 0 or q̄ in dear hours, or where the storage proxy is low; rerun without them | **not rejected, on weak proxies** (§3.13): binding-bound flags are rare and dropping them changes nothing; no reservoir data per cascade |
| **A2** | a cascade's offer curve stacks its plants' λs in the same order in every hour of the day, so a fixed point on the curve is the same plant all day | plants entering and leaving the cascade's offer within the day | stability of the step structure (count and quantities of steps) within a unit-day | **fails for Douro, Mondego, Tejo-Mondego** (half of EDP's storage hydro; §3.13); holds elsewhere, where the whole curve is usually identical all day |
| **A3** | the instrument (offered solar) moves offers only through X, not through λ or the constraint multipliers | pumping or flow rules that follow the solar profile | cascade-by-cascade estimates (§3.12); β above 1 flags a failure | **fails** for Tejo-Mondego and Mondego; holds elsewhere as far as tested |
| **A4** | the net auction position is the firm's exposure to the price | financial hedges (unobserved); co-owned plants mapped to one owner; separate retail groups | owner mapping checks | **partial**: EDP Comercial added to EDP; co-owned nuclear is a known artefact (§3.8); financial hedges unobservable |
| **A5** | λ is set on D−1 information, when the offer is made | intraday re-optimisation feeding back into day-ahead offers | none needed for the day fixed effect | assumed |

## 6. Ways to measure it

| | method | gives | status |
|---|---|---|---|
| **M1** | **difference it out** (unit-day fixed effects) | the within-day conduct test, with no λ needed | done for EDP (§3.11); rests on A1–A5 |
| **M2** | **reveal it from the offers**: the unit-day's volume-weighted offer-price quantiles | a daily λ series, **if** the unit is price-taking within the day | **built** for EDP, Movhera and Repsol (`water_value_revealed.py`, §3.16); within-day markup bound ≤ 2 €/MWh at p90; circular as a test of conduct on its own |
| **M3** | **FOC-implied** (Arzhintar, Leslie, Neill and Wyrwoll 2025): λ̂ = p* − X at the firm's marginal offers, then regressed on the forward price, reservoir level and snowpack | λ's determinants, and a residual for the across-day margin | first build (`hydro_water_value_structural.py`) invalid: contracts subtracted twice, price-setting periods only. **Rebuilt 2026-09-29** on M2's λ̂ over every day, with X subtracted as a bound (§3.16): pass-through of the forward 1.11 (EDP stable), 1.22 (reshaping), 0.95 (Repsol) |
| **M4** | **structural dynamic program**: solve §2 with plant data | the competitive λ, the only true benchmark for the across-day margin | needs plant-level capacities, inflows and heads; Spain has basin-level reservoirs (MITECO), Portugal's data is geo-blocked (APA offered an IP whitelist) |
| **M5** | **forward-price anchor**: λ ≈ the expected price in the hours the water will be used, from OMIP forwards | a benchmark for λ's level, without plant data | OMIP forwards on disk; not built |

## 7. What each result depends on

| result | depends on | reading |
|---|---|---|
| Iberdrola's routes and self-supply (§3.7–3.8) | none: accounting | established |
| EDP: four cascades offer an identical curve all day (§3.13) | none: descriptive | no within-day shaping there, whatever the incentive |
| EDP: the middle of the curve is flat, rejecting Nash (§3.11) | A1, A2, A3, A4, A5 | **A2 fails in three cascades**: pooled estimate mixes identical-curve days with tranche reshaping |
| EDP: the three reshaping cascades offer more below their median price when X is low, from 2024; implied β 0.03–0.12 (§3.14) | A1, A3, A4, A5 — **not A2** | correctly signed, far below Nash; A3 in doubt for Mondego and Tejo-Mondego |
| EDP: 2024 top-tranche response (§3.12) | A3 fails in the two cascades that carry it | not interpreted as conduct |
| Iberdrola: its hourly allocation fits price-taking, Nash fits worse (§3.15, test 1) | A1, A4 | preliminary: validated on EDP's flat bidders; descriptive |
| Iberdrola: IV on the deviation from the benchmark (§3.15, test 2) | A1, A3, and a benchmark without ramping | **fails validation**: read only relative to EDP's flat bidders |
| forward price passes through to λ about one-for-one: 1.11 / 1.22 / 0.95 (§3.16) | M3 rebuilt: A1, A5, and a within-day β ≤ 0.12 | established for the λ as offered; the first build's 0.94 is superseded |
| EDP's λ holds its quantile position in the month's price distribution, 2018–26; its rise against baseload is the price shape (§3.16) | M3 rebuilt | consistent with no across-day withholding; **not a test of it** — inflows unobserved |

## 8. How it serves the research

1. **Within-day conduct.** EDP is done (M1). Iberdrola needs the quantity
   version, because its auction offers are residuals (§3.7): given the unit-day's
   observed energy E and turbine limit q̄, a price-taker under A1 fills the
   dearest hours first. The water value is the threshold price that exhausts E.
   Iberdrola's actual allocation against that benchmark, set against X, is the
   test. It needs no λ level.
2. **Across-day conduct.** Compare the revealed λ level (M2) with the
   forward-price anchor (M5) and the reservoir state, by firm and over time. This
   is the margin the within-day design cannot see. It is harder, and for Portugal
   it needs the APA data.
3. **The cost gap in the descriptive chapter.** It explains why every
   fuel-cost markup failed: the marginal unit's cost is λ, not fuel.

## 9. Plan

In order, cheapest first:

1. ~~**A2**~~ and 2. ~~**A1**~~ — done 2026-09-29 (§3.13).
2b. ~~**Quantity-at-fixed-price test**~~ — done 2026-09-29 (§3.14).
3. ~~**Iberdrola quantity test**~~ — done 2026-09-29 (§3.15).
4. ~~**Rebuild M3**~~ — done 2026-09-29 (§3.16). Next: decide whether the
   across-day margin (§8.2) is in scope. If it is, the cheapest test is the
   day-level one (`rq-midday-hydro.md` §7, item 10), which needs storage-hours
   per unit to split by reservoir size.
5. **APA IP whitelist**, only if the across-day margin is in scope for Portugal.

**Open question for the supervisor:** is the thesis about the within-day margin
(tractable now), or the level of λ (the larger question, which needs M4 or M5)?
