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
| The statutory cap path (€40 → €65) | in the decree, to be transcribed |
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
