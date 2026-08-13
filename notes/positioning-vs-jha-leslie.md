# Jha & Leslie is the paper to beat

*Start-up Costs and Market Power: Lessons from the Renewable Energy Transition*
(SSRN 3603627). Read 2026-08-13. This note states their argument, why it
threatens our headline, and where we stand differently.

## Their argument, in their own structure

Plants face an engineering trade-off: **lower marginal cost comes with higher
start-up cost**. Formally `MC_i < MC_j` but `S_i > S_j` for `i < j`.

Solar reduces *wholesale* demand during daylight without reducing it in the
evening. A mid-merit plant that would once have run through the day is now
pushed off midday and must restart for the evening peak. It will only do that
if evening prices cover the start-up cost.

So the **dynamic competitive price exceeds the static marginal cost of the
marginal unit**. A positive static markup, `P > MC`, is then *fully consistent
with perfect competition* — it is start-up cost recovery, not rent. And the
wedge grows with solar penetration, because penetration is what forces the
cycling.

## Why this threatens our result specifically

We report a static Lerner index rising from 11% to 21% as renewables grow, and
we interpret the rise as market power. **Their model predicts exactly that
pattern under perfect competition.** That is not a peripheral caveat; it is a
competing explanation for our central finding.

Worse, it may reach our elasticity result too. If firms must recover start-up
costs, they bid higher near the margin — which **steepens the submitted supply
curve** and mechanically lowers `eta`. So the fall in `eta` from 1.83 to 0.85
could in part be competitive start-up recovery rather than thinning
competition. The weather instrument does not help here: it identifies the
effect of renewables on `eta`, not the reason for it.

**We must address this head-on. It cannot be a footnote.**

## Where we stand differently

**1. We observe the primitive they estimate.** They recover start-up costs by
regressing daily plant-level gas metering on output, start-up events and
running hours:

```
G_it = a_V · O_it  +  a_S · 1[start-up]  +  a_R · 1[running]  +  e_it
```

estimated by OLS per unit, using AEMO half-hourly output and Gas Bulletin Board
daily gas use. **`cab` publishes a declared fixed term in €/day and variable
term in €/MWh, per unit per day.** Different object, no estimation step.

**2. The two objects differ, and the difference is interesting rather than
awkward.** Theirs is *engineering*: the fuel physically burned starting up.
Ours is *economic and strategic*: what the firm says it must earn. Reguant
(2014) models the declaration precisely because it is chosen. So ours embeds
conduct while theirs does not — which means comparing them, where both exist,
measures the strategic component of the declaration directly. That is a
contribution neither paper can make alone.

**3. Different renewable, different mechanism.** Theirs is **rooftop** solar:
behind the meter, it *subtracts from wholesale demand* and never bids. Ours is
utility-scale wind and solar that *bids into the supply curve* at or below
zero. Their mechanism runs through the demand curve; ours runs through the
supply stack. The distinction is real and defensible, and it should be stated
early.

**4. Different market structure.** Western Australia is small, isolated, and
dominated by one firm. MIBEL is large, interconnected with France and Morocco,
spans two countries clearing jointly, and has several comparable majors. Their
mechanism is about a dominant firm's cycling decisions; ours can be about
strategic interaction between rivals.

**5. We have policy shocks; they have none.** Both Spanish interventions —
the 2021 clawback on non-emitting generation and the 2022–23 gas cap — change
the *cost* side sharply while start-up technology is unchanged. That is exactly
the variation needed to separate start-up recovery from market power: under
their mechanism a plant's cycling requirement is a technology fact and cannot
jump on 15 June 2022, whereas a strategic response can.

## What to do about it

**Adopt the correction rather than fight it.** Compute the dynamic competitive
benchmark using the declared minimum-income terms and report the static and
dynamic markups side by side. If the VRE gradient survives the correction, the
result is much stronger for having been tested against the best competing
explanation. If it does not, that is itself a finding worth reporting — and it
would be a replication of Jha & Leslie in a large interconnected market, which
is publishable in its own right.

**Do not report a static Lerner index without this caveat attached.** The
existing figure in `notes/result-markups-vs-hhi.md` should carry it.

## Could we replicate their estimation?

Probably not directly, and it does not matter much.

Their identification needs **daily plant-level gas metering**, which Western
Australia's Gas Bulletin Board publishes and Spain does not appear to. Enagás
publishes system-level gas flows; per-plant daily consumption is not obviously
public and would need checking. EU ETS verified emissions are per installation
but **annual**, which cannot separate start-up fuel from variable fuel within a
year at unit level.

The honest position is that we do not need to. They estimate start-up costs
because their market does not publish them; ours does. The right move is to use
the declaration, state clearly that it is a strategic statement rather than an
engineering measurement, and treat the gap between the two concepts as
something to discuss rather than assume away.
