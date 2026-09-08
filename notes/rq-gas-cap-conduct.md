# RQ structured for the supervisor meeting — the gas cap and firm conduct

Written 2026-08-14, for the meeting on the 15th. This is the candidate I would
take. The alternative is set out at the bottom, with the reasons it is weaker.

---

## The question

> **When the Iberian gas cap subsidised the fuel cost of gas plants, did those
> plants bid their new, lower cost — or did they keep part of the subsidy as
> markup?**

And its natural second half:

> **Did the plants that were *not* capped — hydro above all — raise their offers
> in response?**

## Why it is open

The Iberian Exception is well studied, and the outcome-level questions are
settled. Do not re-do them: the ~40% fall in the spot price, the inflation
effect, the export surge to France, the congestion rents, and the direction of
the rent transfer from non-fossil to fossil producers are all published.

What no published work does — checked, see
[`literature-iberian-exception.md`](literature-iberian-exception.md) — is
**estimate the behavioural response of individual generators using unit-level
bids.** González-de Miguel et al. (2024) come closest and do use real bids, but
they reconstruct *aggregate* supply and demand curves and simulate counterfactual
market outcomes. That is an accounting exercise at market level. Nobody asks what
individual firms *did*.

## The identification, and why it does not need a control group

This is the part worth spending time on with her, because it is the design's
strongest feature and it is counter-intuitive.

**The Iberian Exception covers Portugal as well as Spain** (Decreto-Lei 33/2022;
ERSE Instruction 5/2022, effective 14 June 2022). So the entire MIBEL market is
treated, and the Spain-versus-Portugal comparison that works for the 2021 levy is
unavailable here. Every unit in the market is affected.

That would be fatal for a difference-in-differences. It is not fatal here,
because **the mechanism defines the counterfactual by construction.** The cap
sets the gas price a plant is permitted to use in its bid — €40/MWh initially,
escalating toward €65 — and compensates the plant for the difference against the
market price. The plant's economic fuel cost after 15 June 2022 is therefore a
*known number*, not something to be inferred from a control group.

So the object of interest is a markup, measured directly:

```
markup_it  =  offer_it  −  MC_it(capped gas, efficiency, carbon)
```

and the test is a passthrough test. The cap cuts marginal cost by a computable
amount ΔMC. If offers fall by exactly ΔMC, passthrough is complete and conduct
is unchanged. If they fall by less, firms retained part of the subsidy — which
is a market-power finding, per unit, per hour.

**The counterfactual comes from the policy, not from a comparison group.** That
is unusual and worth stating plainly.

## Preliminary evidence — the cap visibly bound

Volume-weighted median sell offer of combined-cycle plants, against the market
gas price. 55–58 units per month.

| month | CCGT offer | MIBGAS | ratio |
|---|---|---|---|
| 2022-01 | €201.9 | €83.6 | 2.41 |
| 2022-03 | €307.0 | €124.4 | 2.47 |
| 2022-05 | €211.7 | €77.3 | 2.74 |
| **2022-06** | €142.0 | €96.7 | **1.47** ← cap from the 15th |
| 2022-07 | €102.2 | €126.1 | **0.81** |
| 2022-08 | €108.9 | **€165.9** | **0.66** |
| 2022-10 | €103.9 | €64.8 | 1.60 |

Before the cap, offers track gas at a stable 2.4–2.7 — roughly fuel cost divided
by thermal efficiency. From July they **decouple completely**: in August gas costs
€165.9/MWh and combined-cycle plants offer €108.9. They stopped bidding the market
gas price and started bidding the capped one.

The mechanism worked as designed. The open question is the residual: €40 of capped
gas at a plausible efficiency implies a marginal cost in the low €90s once carbon
is counted, against observed offers near €105. **That gap is the thesis.**

## What still has to be built

| input | status |
|---|---|
| Unit-level bids, 2018–2026 | in hand |
| Which units are capped (combined cycle, coal, unregulated cogeneration) | in hand — technology coverage ~97% |
| Which firm owns each unit | in hand — ~97% |
| Market gas price (MIBGAS) | in hand |
| The statutory cap path (€40 → €65) | **in hand, 2026-09-04** — transcribed from the consolidated BOE-A-2022-7843 art. 3 into `build_implied_marginal_cost.py`; `marginal_cost_capped_eur_mwh` and `cap_binding` ship in the panel |
| Plant thermal efficiency | **needed** — JRC database, or estimated per unit from pre-cap bidding |
| Carbon price (EUA) | **needed** — straightforward to fetch |

Estimating efficiency from each plant's *pre-cap* bidding is attractive on its own
terms: regress offer on the market gas price before June 2022 to recover an implied
heat rate per unit, then use it to predict the capped-period marginal cost. It uses
the data we have, and it means the efficiency assumption is disciplined by the
plant's own revealed behaviour rather than by an engineering table.

## Threats, honestly

1. **Compensation is paid outside the auction.** A plant's revenue is the market
   price plus a compensation payment; only the fuel cost entering the bid is
   capped. The markup calculation must use the capped cost, and the incentive
   analysis must account for the compensation — these are not the same thing.
2. **Selection into bidding.** The cap made gas plants cheaper, so they ran more.
   The set of units offering in a given hour changes with the policy, and the
   composition shift must not be read as a conduct change. Unit fixed effects
   handle the level; the extensive margin needs care.
3. **The 2021 levy is simultaneously in force**, on the *uncapped* technologies —
   hydro and nuclear. For the second question, that means the comparison group has
   its own ongoing treatment. It is in force on both sides of 15 June 2022, so it
   differences out of a comparison across that date, but it cannot be ignored.
4. **The export surge to France** is a known consequence and changes residual
   demand facing Iberian plants. It is settled in the literature as an outcome;
   here it is a confound for the quantity margin, less so for the price margin.
5. **Efficiency is estimated, not observed**, under either route.

## How it compares to the alternative — both are now live

**Updated 2026-08-14, after the levy question acquired a working design.** An
earlier version of this note argued that the levy route was exhausted. That was
premature: only the *cross-country* route was.

Three designs comparing Spanish to Portuguese hydro all failed, and failed the
same way — any regressor shaped like the gas-price path predicts the ES–PT gap
in years when no levy existed, because the two fleets differ in mix, hydrology
and capture rate. The monthly level test appeared to pass its placebo only
because that outcome is seven times noisier than the alternatives; a sharper
outcome exposed the same contamination at t = 2.21.

A fourth design, using **differential contract exposure within Spain**, gets
closest. RDL 23/2021 exempted forward-contracted energy, so unhedged plants
faced a much larger effective levy than hedged ones facing the same gas price.
Exposure is predetermined (measured before September 2021) and close to bimodal
across the 23 units. Portugal never enters, and **both placebos pass** — the
only design here that manages that.

It still cannot produce a reportable estimate, because the sign depends on which
outcome variable is chosen:

| outcome | β | t | across trimming rules |
|---|---|---|---|
| log(median submitted offer) | +0.0067 | 3.76 | stable |
| median submitted offer, levels | +0.31 | 0.43 | 0.13 → 1.82 |
| marginal accepted offer, levels | −0.73 | −1.96 | −0.69 → +0.17 |

A per-MWh levy predicts an *additive* shift, so levels is the correct functional
form — and in levels nothing survives sample choice. The marginal accepted offer
is additionally censored by the clearing price: if the levy pushes
high-water-value plants out of the market, the units still clearing are the
low-value ones and the measured threshold falls with no behavioural response at
all, which would generate the negative sign mechanically.

**The binding problem is measurement, not identification.** Design 4 identifies
cleanly and still yields nothing, because hydro's opportunity cost is
unobservable and every proxy for it has turned out to be contaminated, censored
or unstable. That is precisely the case for estimating a water-value function —
and precisely why the levy question is structural-or-nothing.

**Updated 2026-08-18.** Tested directly rather than left as an inference: a
new MITECO reservoir-level fetch supplies the actual state variable (not
rainfall, tried and null earlier), and partialling its fill-level anomaly out
of Design 4's treatment variable moves beta in the third decimal place on
every specification — the sign instability across trimming reproduces almost
exactly under the control. So it is not an omitted-variable problem that a
reservoir-based control can fix; whatever is producing the instability lives
in the outcome measurement (censoring by the clearing price mixing genuine
marginal offers with deliberately unclearable ones), not in something linear
that was left out. See
[`hydro-water-value-design.md`](hydro-water-value-design.md) for the full
run. This closes off the cheapest remaining fix rather than opening one —
structural estimation is now the only route left untried, not one option
among several.

|  | Gas cap | Levy and water value |
|---|---|---|
| Counterfactual | given by the statute | must be estimated |
| Control group | none needed | none that works |
| Units carrying it | 55–58 combined-cycle plants | 18–23 hydro plants |
| Status | untested, data 90% ready | reduced form exhausted, 4 designs |
| Reduced-form fallback | the conduct result itself | **none** |
| Still to build | efficiencies, carbon prices, cap path | a structural water-value model |

## What I would put to her

1. Does the passthrough framing hold up — is "the mechanism defines the
   counterfactual" a sufficient identification argument, or does she want a
   comparison group anyway?
2. Estimated efficiencies from pre-cap bidding, or engineering values from JRC?
3. Is the second question (did uncapped hydro raise its offers?) a separate
   chapter or the same one? It is the more novel half and the harder to identify.

## 2026-08-18: a literature pass supplies the precedent equation, a
## pass-through prior, and a cheap complementary test for question 2

**Novelty check closed.** González-de Miguel, van Wunnik & Sumper (2024,
*Energies* 17:3102, `papers/md/energies-17-03102.md`) — the closest existing
paper, already flagged in `literature-iberian-exception.md` as using real
bids for an aggregate counterfactual — turns out to *assume* full CCGT
pass-through by construction ("CCGTs are obliged to pass through the
subsidies into their market bids", their p9) and to say outright they lack
the data to model how hydro would have bid absent the subsidy (their p13).
So the passthrough test here is not just unattempted elsewhere, it is the
literal null hypothesis the closest paper builds in rather than tests. One
data point worth keeping for the power calculation on question 2: they
document Spanish hydro was essentially absent from the market June–Sept
2022 (drought), with only Portuguese hydro clearing in that window — the
Spanish-side hydro-response sample may be thin exactly when the cap first
bound, though Portuguese hydro bids into the same MIBEL stack.

**Fabra & Reguant (2014, AER 104(9), `papers/md/fabra-passthroughemissionscosts-2014.md`)
is the direct precedent for the whole design**, applied to the 2004–2006
EU ETS Phase 1 start rather than the gas cap. Their structural decomposition
(p2884–2885) is essentially the equation already sketched above:
```
bid_it(q) = mc_it(q) + markup_it(q)
mc_it(q) = marginal_emissions_cost_it(q) + marginal_input_cost_it(q)
markup_it(q) = -q_it · dP_it/dq_it        (residual-demand slope × net quantity)
```
and their reduced-form test (p2881, their eq. 1):
```
p_th = ρ·τ_t·e_th + β0·X_th^common + β1·X_th^demand + β2·X_th^supply + β3·ι_h + ε_th
```
— price on the marginal unit's emissions cost, instrumented by the EUA permit
price itself (naive OLS gives a *negative* coefficient, −0.17 to −0.22,
because the marginal unit's identity correlates with demand — an artefact
worth guarding against in our own specification too). Their engineering
marginal-cost construction (heat rate × fuel price + emissions rate × permit
price, from national plant registries) is the same category of object as
`implied_marginal_cost_daily.parquet` (JRC efficiency × MIBGAS × EUA/coal),
including the identical caveat that plant efficiency may be stale or
generic.

**Headline pass-through ≈ 86% (77–86% across specs, Table 1), near 100% at
peak, ~60% off-peak** (dynamic/start-up costs cited as the off-peak friction).
**Why it's high is the load-bearing part for setting our prior, not just the
number**: their own explanation (p2894) is that pass-through is high when
(a) the cost shock hits every price-setting firm together (a market-wide EUA
move, not firm-idiosyncratic) and (b) demand can't respond, so there's no
differential margin worth protecting. **The gas cap violates (a) by design**
— it is asymmetric across technology (CCGT/coal/non-RECORE cogen capped,
hydro/nuclear not), which is exactly the kind of *relative*-cost shift that
gives a firm a markup-adjustment incentive Fabra & Reguant's mechanism says
is otherwise absent. So 86% is a reasonable *null* prior ("no markup, same
mechanism as EUA") but not a mechanical prediction — a materially lower
pass-through would be consistent with, not contrary to, this precedent's own
logic. Fabra, Rapson, Reguant & Wang (2021, AER P&P, real-time pricing
elasticity, `papers/md/fabra-et-al-2021-...md`) is a useful supporting fact
here too, from the same setting: Spanish *retail* demand elasticity to
real-time price is essentially zero (point estimates 0 to −0.02, no
detectable RTP-vs-non-RTP difference) — background support for treating
demand as price-inelastic in this market, consistent with condition (b)
above.

**A cheap complementary test for question 2 that needs no cost benchmark at
all.** McRae & Wolak's residual-demand market-power design — both the 2017
Colombia draft (`papers/md/mcrae-and-wolak-columbia-0.md`) and the fuller
Handbook chapter (`papers/mrae_wolak_how_do_firms_exercise_market_power.pdf`,
scanned, no text layer) — never estimates opportunity cost at all. It
constructs, per firm per hour, the residual demand curve from rivals'
*observed* offers plus system demand (`DR_j(p) = Q_D − Σ_{k≠j} S_k(p)`, ours
buildable now from OMIE `status == 'O'` bids + `unit_agents.parquet`), then
two indices: an inverse semi-elasticity `η_i = -(1/100)·DR_i(P*)/DR'_i(P*)`
and a contract-adjusted incentive version `η_i^C = η_i·[(DR_i(P*)−Q_C)/DR_i(P*)]`
netting out the firm's forward/contract position (their eq. 3.4, 3.10 —
`Q_C` is exactly what `pdbf`'s theta proxy already gives us). The test:
regress each hydro firm's own offer level on its own η/η^C with day×hour
fixed effects absorbing unobserved marginal cost entirely (their eq. 4.1–4.2)
— coefficients answer "does a firm bid higher exactly when its own
residual-demand shape says it can," with no cost data required on either
side of the equation. Sharper still for our exact question: their §18.5
exclusion-restriction test regresses each unit's offer on its *own* cost
shifters plus *rivals'* hydro storage level — under no market power, a
rival's storage shouldn't predict a unit's own price, and all eight of their
tested units reject that null (β −2.34 to −24.31 $/MWh per TWh). The gas cap
gives a mechanically clean version of the same exclusion test: does capped
CCGT rivals' cost (or the cap's bite, directly observable) predict hydro's
own offer, controlling for hydro's own fundamentals? This is buildable now,
cheaper than the passthrough regression (no marginal-cost construction
needed on the hydro side), and answers the "did uncapped hydro exploit the
cap" question directly rather than through the opportunity-cost detour that
`hydro-water-value-design.md` already found expensive. Worth raising to the
supervisor as a first cut at question 2, ahead of (not instead of) the
structural water-value route.

Peña (2024, *Utilities Policy* 87, `papers/md/pena.md`) is the closest
existing Spain-specific paper making a version of the question-2 claim
already (hydro priced 3–12% above a CCGT-lag opportunity-cost proxy in
2021–Q1 2022) but it: (a) stops before the gas cap (window ends 31 March
2022, cap starts 15 June), so it says nothing about either policy directly;
and (b) its opportunity-cost proxy is *yesterday's* CCGT marginal cost, which
shares the exact price-co-movement confound this design's own reduced-form
probes were built to avoid — good for citation and for motivating why a
cruder proxy isn't good enough, not a method to reuse.

---

## 2026-08-18: a sharper design — test conduct against the ex-post optimal
## bid, not against a raw markup

Written after building the marginal-cost side out with the supervisor's HP2008
question in mind. This is a refinement of question 1 above (did capped firms
retain part of the subsidy), not a replacement — it uses the same 45-unit
engineering marginal cost, but changes what the outcome variable *is*, and the
change matters for identification.

### The problem with a raw markup regression

The design as written above tests `offer_it − MC_it(capped gas) = markup_it`
and asks whether `markup_it` moves at 15 June 2022. But `MC_it` is not the only
thing the cap changes. Capping every rival CCGT's cost also flattens the
supply stack in the price range those units occupy, which mechanically changes
each firm's **residual demand slope** — the object that sets the
profit-maximizing markup in the first place (Kellogg & Reguant eq. 23, §2
above). A raw markup regression at the cutoff conflates two things: firms
behaving differently, and firms facing a different profit-maximization problem
even if their behaviour (conduct) hasn't changed at all. A stable or shifting
`markup_it` is consistent with either story, and the design as written cannot
tell them apart.

### The fix: difference against the firm's own ex-post optimal bid

Hortaçsu & Puller (2008, `papers/md/the-rand-j-of-economics-2008-...md`,
their eq. 2 and Proposition 3, printed p.86ff) construct exactly the object
that nets this out: given a firm's realized residual demand `RD_i(p)` that
hour (computed from rivals' *actual* submitted offers — mechanically observed,
not modelled), its contract position `Q_C_i`, and its marginal cost `MC_i(q)`,
the **ex-post optimal bid** is the point where marginal revenue implied by
`RD_i` equals marginal cost:

```
p*(q) − MC_i(q) = −(q − Q_C_i) · dp/dq |_{RD_i}          (their eq. 2, rearranged)
```

Because `RD_i(p)` is recomputed fresh every hour from rivals' actual offers,
this benchmark **automatically re-prices the profit-maximization problem**
every time the cap changes a rival's cost, a rival exits the price range, or
demand shifts. It is, by construction, "what a purely profit-maximizing firm
should bid given everything that actually happened that hour" — cost shock,
demand shock, and residual-demand-slope shock all included. What is left over
after differencing the actual bid against it is conduct, not environment.

**Outcome variable**, following HP2008's own scale-normalized metric so firms
of very different size are comparable (their Percent Achieved, adapted):

```
PctAchieved_iht = (π_actual_iht − π_avoid_iht) / (π*_iht − π_avoid_iht)
```

`π_actual` = realized profit under the firm's actual bid; `π*` = profit under
the ex-post optimal bid at the same realized `RD_i`, `Q_C_i`, `MC_i`;
`π_avoid` = profit from bidding to avoid being dispatched at all (HP2008's own
finding — see §4 above — is that this, not marginal-cost bidding, is the
relevant floor: units that fail their minimum-income condition withdraw for
the whole day rather than bid competitively). `PctAchieved = 1` is exactly
optimal; `PctAchieved = 0` is "did not do better than not participating."

### Data mapping — everything needed is already in hand

| object | Spain source |
|---|---|
| `MC_i(q)` | `implied_marginal_cost_daily.parquet`, capped gas price substituted for the market price where the cap binds (post 15 June 2022, 45 units with real efficiency) |
| `RD_i(p)` | constructed per firm per hour from `curva_pbc_uof` `status=='O'` rows of every *other* agent, aggregated by `unit_agents.parquet` |
| `Q_C_i` | `pdbf` role_code `'4'` rows, aggregated to firm level |
| actual bid | `curva_pbc_uof` `status=='O'`, the firm's own units |
| firm size / sophistication proxy | `unit_agents.parquet` parent-firm generation share (HLPZ2019's own finding: size is the dominant driver of CH type — no need to estimate a cognitive-hierarchy type distribution ourselves, a size rank is the same variable they find actually does the work) |

Nothing new to fetch. The one piece of new engineering is computing
`RD_i(p)` and the FOC crossing per firm-hour at scale — mechanical, not a new
data problem.

### Specification

Event study around 15 June 2022, unit and firm fixed effects, restricted to
non-splitting periods (drop the 6.7% ES/PT-split hours, same restriction
HP2008 use for their own congestion exclusion):

```
PctAchieved_iht = Σ_k β_k · 1[week = k] + α_i + τ_h + ε_iht
```

k indexed relative to the cutoff week; `α_i` unit or firm fixed effects,
`τ_h` hour-of-day fixed effects. A flat `β_k` across the cutoff is evidence
that conduct, not just cost, passed through unchanged — a genuinely different
and stronger claim than "offers fell by the capped amount," since it is
already conditioning on the fact that offers *should* fall by the capped
amount.

**The sophistication interaction (HLPZ2019, extending §9.1 in
`literature-to-thesis.md`):**

```
PctAchieved_iht = β1·Post_t + β2·Post_t·Size_i + α_i + τ_h + ε_iht
```

`Size_i` = firm's pre-period generation share (predetermined, avoiding the
obvious reverse-causality problem of using a post-period size measure). A
negative `β2` — small firms' gap from optimal widening more than large firms'
right at the cap — would be a "policy complexity" finding: the compensation
mechanism (paid outside the auction, on a different schedule than the bid
itself) is more costly for less sophisticated agents to price correctly into
their bid, distinct from and additional to the market-power story the level
regression already targets.

### Threats specific to this design, on top of the four already listed in §
### "Threats, honestly" above

1. **`RD_i(p)` is itself measured with the same whole-day-dropout
   contamination flagged in CLAUDE.md's known-anomaly section** — 63 affected
   days, concentrated 2025-03-19 to 2025-06-09, well outside this window, but
   the general point (a unit's absence from the bid file must be checked
   against the clearing identity, not assumed to mean "not available") applies
   to whichever agents are used to construct rivals' supply that hour.
2. **The ex-post optimal bid assumes the firm has full information on rivals'
   realized offers when it bids — which it does not, ex ante.** HP2008's own
   defence (§2 above, "ex post optimality") is that this is a valid benchmark
   for *ex post* rationality, not a claim about what the firm could have known
   in advance; the same defence applies here, but it is worth stating rather
   than assuming.
3. **`Q_C_i` is a physical-contract proxy for theta, not theta** (misses
   financial hedges — the same caveat `pdbf`'s own documentation carries).
   `PctAchieved` inherits that measurement error whole.
4. **The 45-unit marginal-cost set is not a random sample of the treated
   fleet** — see the "binding constraint" from the earlier HP2008-methodology
   discussion (only 31 of 62 CCGT units, 14 of the coal fleet, have real
   rather than generic JRC efficiency). Firm-level `PctAchieved` aggregates
   only over a firm's units that are in this set; a firm with no covered
   units cannot be scored at all, and the sophistication interaction should
   be checked for whether covered-unit ownership correlates with size in a
   way that would bias `β2`.

### Relationship to the existing design

Not a replacement for the passthrough test in "The identification, and why it
does not need a control group" above — a complement that answers a different
question with a cleaner counterfactual. Run both: the raw markup regression
is the easier, first-pass, more interpretable result ("firms kept X €/MWh of
the subsidy"); `PctAchieved` is the harder, second-pass result that says
whether that X €/MWh is explained by the environment changing (residual
demand, rivals' costs) or by conduct changing, which is the sharper causal
claim and the one no existing paper (see §"González-de Miguel..." above)
comes close to.

## 2026-08-21: the 2022 drought — a usable control, not identifying variation

Raised because the Iberian Exception took effect 15 June 2022 in the middle of a
severe Iberian drought (national reservoir fill ~0.48 and falling; published
assessments of the cap say the drought and the cap **jointly** explain the
summer-2022 fall in hydro generation and are hard to separate — see
[`literature-extreme-weather-economics.md`](literature-extreme-weather-economics.md)
§5). Two questions, tested in order, both answered.

### It is separable from the gas-price path — which is not obvious

The 2021 levy design died because *any* regressor shaped like the gas-price path
predicted the outcome (`levy_contract_exposure.py`). That trap was checked
before building anything this time:

| measure, cap window 2022-06-15 → 2023-12-31 | corr with MIBGAS, levels | corr, daily changes |
|---|---|---|
| national reservoir fill | −0.31 | −0.09 |
| fill anomaly (de-meaned by ISO week) | −0.32 | −0.03 |
| weekly change in fill | −0.19 | −0.06 |

Fill moves **non-monotonically** inside the window (0.314 → 0.517, sd 0.065)
while gas collapses monotonically from 92.3 to 31.1 €/MWh. The high-frequency
components are orthogonal. So reservoir state **can** be entered alongside the
gas path without one absorbing the other, and it is a legitimate control for
question 2 — did the uncapped technologies raise their offers — where hydro's
untreated behaviour was being moved by an unrelated shock.

That is the useful result, and it is modest.

### It is not an instrument for market power — the first stage is absent

The attractive version was: drought → less hydro competing → steeper residual
demand → more market power → less pass-through of the cap. Weather-driven
variation in the *incentive to mark up*, inside the treated period, needing no
before/after comparison at all. It does not survive its first stage.

**Market level** (`residual_demand_slope_full.parquet`, hour + year-month FE,
controls for log demand and VRE share): fill anomaly on residual-demand
elasticity gives β = −0.645 (se 0.932) full sample. The channel needs β > 0.

**Firm level** (`firm_residual_demand_drought.py`, built for this: the same
band-density estimator with the firm's *own* offers removed from the ±5 €/MWh
band, 888,815 firm-periods, 350,995 after dropping split periods and
clearing-identity failures, 10 firms). The market-level object is the slope
facing an *infinitesimal* participant and averages over firms, so whether
drought steepens the residual demand facing **Iberdrola specifically** — which
depends on whether *Iberdrola's rivals* hold the hydro — is a different
question. It is answered the same way:

| | β on log(price impact) | se | t |
|---|---|---|---|
| pooled, firm × hour + year-month FE | **+1.14** | 1.64 | 0.70 |
| all ten firms individually | **+0.17 to +2.93** | — | max t = 1.49 |
| cap window only (19 month clusters) | +1.67 | 8.18 | 0.20 |

The channel needs β < 0 (drought = low fill anomaly should *raise* price
impact). Every one of the ten firm-specific estimates is **positive** — drought
makes residual demand *flatter*. None is significant, and there is no gradient
with rival hydro exposure: Axpo, with the highest rival hydro share (19.1%),
gives +1.03; EDP, with the lowest (12.1%), gives +1.11.

Scale, so the null is not overread: fill anomaly sd = 0.0883, so β = 1.14 is
+10.1% on price impact per 1-sd drier-to-wetter move, 95% CI roughly
[−18.3%, +38.5%]. That is **not a precise zero** — it is a wide interval
centred on the wrong sign, with no firm-level heterogeneity available to
rescue it.

**Why the heterogeneity was always thin.** Rival hydro exposure across the top
ten firms spans only 12.1% (EDP) to 19.1% (Axpo). No Spanish firm is large
enough for its own hydro to move the *rivals'* aggregate much, so every large
firm faces close to the same rival technology mix. Own hydro share varies far
more (0.05% to 32.8%) but by construction does not enter a firm's own residual
demand. This is a structural feature of the market, and it caps any design that
wants cross-firm variation in exposure to a technology-specific shock.

### What this leaves

Hydrology moves the **price** strongly (corr of the fill anomaly with the
clearing price = −0.41) and firms' **residual-demand steepness** not at all.
That is a merit-order effect, not a competition effect. The drought therefore
enters this design as a control on question 2 and nothing more; it is not a
route to a conduct result.

Two bugs found and fixed while establishing this, both of the silent kind:
`hour_utc` in the slope panel is a full timestamp, not an hour, so factorising
it directly creates one fixed effect per row and absorbs the regressor
completely (first run returned exact zeros with zero standard errors); and
selecting a duplicated column name — `fe2` and the cluster variable are both
`ym` — returns a DataFrame rather than a Series.
