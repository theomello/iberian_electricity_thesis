# Email to supervisor — the Spanish setting

Draft, 2026-08-14. Written in English; say the word and I'll produce a
Portuguese or Spanish version.

---

**Subject:** The Spanish/Iberian setting — what I've established so far

Dear [Professor],

Following your advice to study the Spanish setting before fixing a question, I
spent the past weeks doing exactly that. Below is what I've established. It is
longer than a status update because the institutional detail turned out to
matter more than I expected — several things I assumed were true are not.

**The market.** Spain and Portugal do not run two markets that trade with each
other. They run **one** day-ahead auction, MIBEL, clearing a single merged
supply curve. The two take different prices only when the interconnection binds
— 5% of hours in 2018, rising to 15% by 2026. Portuguese plant is therefore
part of the same market object as Spanish plant, not a neighbouring system.
This matters for identification: Portugal shares Spain's prices and demand
shocks but not its regulator.

It is a uniform-price auction, so all accepted offers are paid the price set by
the most expensive accepted one. That is what makes bidding above cost
profitable and market power measurable.

**What has changed, 2018–2026.** Renewables went from 23.9% to 41.8% of Spanish
generation. Coal disappeared entirely. Prices ran €57/MWh (2018) to €167 (2022)
and back to €46 (2026) — but what persists after the crisis is different from
what preceded it: **a fifth of all periods now clear at zero or below**, against
none at all before 2023.

**Who sets the price.** I can now identify the marginal technology in ~95% of
periods, using OMIE's own unit registry. Hydro sets the price more often than
any other technology in every year except the 2022 gas crisis — 26% to 47% of
periods. This is the single most important descriptive finding, because a hydro
plant's marginal cost is not fuel: it is the opportunity cost of water it
chooses not to use, which is unobservable and forward-looking.

**Two emergency interventions frame the window**, and both are more complicated
than the summaries suggest:

- A **clawback on non-emitting generation** (RDL 17/2021), a per-MWh levy on
  nuclear, hydro and merchant renewables above 10 MW, whose rate scales with the
  gas price. I had recorded it as ending March 2022; checking the statute, it
  was extended four times and ran to **31 December 2023**.
- The **Iberian gas price cap** (RDL 10/2022), June 2022 to December 2023,
  subsidising the marginal cost of gas and coal.

They therefore **overlap by 18.5 months**, which rules out treating them as
mirrored episodes. The same decree that introduced the clawback also extended
the suspension of the 7% generation tax, so the September 2021 change is a
bundle rather than a single treatment. And Portugal's own clawback was set to
zero over almost exactly the same window. None of this is in the secondary
literature I found; it came from the consolidated statutes.

Spain never separately implemented the EU-wide inframarginal revenue cap — the
existing national mechanism bound tighter — so that adds no further date.

**Two things this market publishes that others do not.** Both are unusual enough
to be worth a paragraph:

1. **Declared start-up costs.** Firms state, per unit per day, a fixed term
   (€/day) and a variable term (€/MWh) they require in order to run. The
   literature closest to my question estimates this quantity from engineering
   data because their market does not publish it. It is a strategic declaration
   rather than an engineering measurement, which makes the comparison
   interesting rather than awkward.
2. **The contract position.** Volume committed outside the auction is published
   per unit per day. That is the term Wolak (2000) and Hortaçsu & Puller (2008)
   need and cannot see; the closest recent paper spends an appendix inferring
   it. Around 39–48% of scheduled sales are under bilateral contract.

**The one result I have.** Residual demand elasticity — how far a firm can move
the price — fell from 1.83 to 0.45 between 2018 and 2026, while the competition
authority's concentration index *fell* from 1,314 to 1,007. Concentration down,
price-setting power up. Instrumenting renewable output with weather reanalysis
gives the same answer as OLS to within 4%.

**Where I need your judgement.** I have two candidate directions and they are
not equally safe. One extends the elasticity result to firm-level market power —
nearly finished, but with no treatment and control group, in a crowded
literature. The other asks how the 2021 clawback changed hydro's opportunity
cost of storing water — a better question with a real control group (Portuguese
hydro, same market, different regulator), but it cannot be done reduced-form.
I tested that directly: the levy produced no dose-response in bidding, and the
natural proxy for the timing margin fails its own placebo test. So that route
means committing to estimate an opportunity-cost function, with no descriptive
fallback.

I've put the evidence for both, side by side, in a short deck — happy to send it
or walk through it whenever suits you.

Best regards,
[Name]
