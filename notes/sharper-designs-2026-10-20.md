# Four designs for sharper identification: what they showed

2026-10-20. The user asked for designs with sharper identification than the repo's so far,
free to use new data and literature beyond the repo. Four were chosen and taken in this order.
**All four stopped before estimating β**, each for a specific reason, and each left something
usable. Detail in the four running notes; this page is the summary.

**What sharp meant.** A shock that changes one firm's stake in the price, X = n/|RD′|, without
touching its costs or plants; that the firm cannot choose but knows before bidding; and that
recurs, so that the contrast between firms within the same hour carries the estimate (the hour
effects absorb everything common). Every design kept the same first-order condition,
p − c = β · n/|RD′|, the same outcomes (offers at fixed points of each plant's ladder, read
against simulated price-takers) and stop rules fixed before each run.

| | design | the shock | stopped at | why |
|---|---|---|---|---|
| 1 | Regional holidays | a region's holiday cuts the load of the firm whose retailer serves it | step 2, first stage | firms absorb it in bilateral self-supply; their auction position does not move (F 0.1–1.4) |
| 2 | Minimum-income near-misses | a combined cycle withdrawn by a few cents is idle but free to sell intraday | step 1, validity | plants pile up just above the threshold on every sample (2–3×) |
| 3 | The France link | an open line flattens every firm's residual demand, more for large positions | step 2, power | an open line absorbs only a sixth of a shock; smallest detectable β 2–10 |
| 4 | Feed-in tariff exits | EDP's Portuguese wind starts earning the market price on a date fixed at licensing | before a spec | the tariffs run on, with a floor and a cap, until 2027–2032 |

## 1. Regional holidays (`rq-regional-holidays.md`)

**Idea.** On 11 September Catalonia rests and the rest of Spain works; Endesa supplies most
Catalan customers, so it buys less that day. A buyer that shades prices down should shade less.

**Built.** The holiday table 2018–2026 from the BOE's XML and Portugal's law; REE's regional
demand; each firm's retail exposure by region, leaving each year out. Step 1 passed: the
exposures are clear (Endesa: all of mainland Spain 1,147 MW, Catalonia 414, Madrid 302).

**Why it stopped.** The holiday does not move a firm's position in the auction. Per MW of
holiday dose: retail bought bilaterally −0.69 MW, generation sold bilaterally −0.54, generation
sold in the auction +0.02; net auction position +0.27 (se 0.17). Firms cover their own customers
with their own plants and adjust by quantity.

**What survives.** The third appearance of "book balancing by quantity", after the reactor
owners covering their own retail and Iberdrola's routing. A quantity test is open (§6).

## 2. Near-misses of the minimum-income condition (`rq-mic-near-miss.md`)

**Idea.** A combined cycle that misses its declared minimum income by a few cents is withdrawn
for the whole day; one that clears it by a few cents runs. The withdrawn plant is idle but can be
sold in the intraday auctions, which moves its owner's intraday stake.

**Built.** OMIE's PDVD (the schedule after REE's grid-security step); the margin each declaring
plant would have earned had it run (re-clearing each hour with its offers added), 137,417
unit-days 2019–2025-03; regression-discontinuity tools.

**Why it stopped.** The threshold is almost sharp (acceptance 0 → 0.89), but there are 2–3 times
as many unit-days per €/MWh just above it as just below, on every sample: all plants, plants
whose condition can bind, and the 304 days with a single plant near its threshold. The declared
cost term jumps €17 at the threshold until competing plants are removed. Not explained by days
when the condition cannot bind, by the size of the re-clearing, or by a bug found and fixed on
the way (withdrawn plants were dropped on bad days, accepted ones were not).

**What survives.** A plant just withdrawn sells about 90 MW more of its output in the intraday
auctions than one just accepted (se 6), and REE switches 40% of them back on.

## 3. The France link (`rq-france-link.md`)

**Idea.** If Iberdrola withholds 100 MW while the line to France is full, the price rises; while
it has room, imports fill the gap. So stakes are large in congested hours and small in open ones,
for reasons outside Iberian control (published capacity, French nuclear output and demand).

**Built.** French prices (Ember) and system data (RTE éCO2mix); the line's state by hour (open 31%
of hours; Spanish and French prices equal in 99.7% of open hours); its prediction from French
conditions, then split into an Iberian part (control) and a French part (instrument).

**Why it stopped.** A GW of Iberian residual demand moves the price €4.26/MWh when the line is
predicted full and €3.58 when open, although open hours have a median 1.2 GW of room: French
supply adds only about 60–90 MW per €/MWh against Iberia's 326. The instrument moves the stake
(F 17–93), but the smallest detectable β is 2.7 (hydro) and 9.9 (thermal) against 1.

**What survives.** The repo's single-market slope overstates stakes in open hours by only about
16–21%, which was the measurement worry behind this design. (Measured on GW-scale shocks; the
French slope for a firm's last MW is not measured.)

## 4. Feed-in tariff exits (`rq-fit-exits.md`)

**Idea.** When an EDP wind farm's guaranteed tariff ends, its output starts earning the market
price for EDP, a net buyer, on a date fixed when the farm was licensed.

**Why it was not built.** EDPR's 2012 briefing: its 615 MW of old-regime Portuguese wind took a
7-year extension (years 16–22), paid the daily average price but never below €74 or above €98
(2020 terms, indexed). Inside the window the stake exists only on the fifth of days when the
average price is in that band, and moves by about €0.3/MWh; full exposure starts in 2027–2032.

**What survives.** e2p's register of Portuguese plants (268 wind farms, 6.0 GW, owners and start
years) and a data request to DGEG and ERSE, drafted and on hold.

## 5. What the four say together

- **Firms balance their own books by quantity.** Shocks to a firm's own load or output reach its
  bilateral schedule, not its auction position (designs 1 and, earlier, the reactor and Iberdrola
  results). Instruments built on a firm's retail or generation move the stake much less than the
  shock's size. This is now a result, not a nuisance.
- **The stake is hard to move from outside.** Every exogenous source tried shifts X by about
  €0.3–3.4/MWh at most, and with the noise in offers that leaves the smallest detectable β at 2 or
  more (holidays 27–297, France 2–10), against 1 for Nash. The across-firm, within-hour design that
  makes these tests valid also leaves them underpowered.
- **The single-market slope is a fair approximation** (design 3), which supports the earlier
  estimates that used it.
- **Algorithmic thresholds are not coin flips** when the algorithm chooses among competing units
  (design 2).

## 6. Where this leaves the next step (proposals, none run)

1. **The holiday quantity test** — **run the same day: book balancing.** The cut follows the
   lost load, not its price effect; β on the quantity margin −0.16 [−0.52, +0.20], full market power
   rejected (p 4·10⁻¹⁰) (`rq-regional-holidays.md`, quantity test). The original proposal: Within the hour, a
   price-taker's output does not depend on its own customers' load, yet firms cut about half a MW
   per MW of holiday dose. Under market power the cut should grow with 1/|RD′| and stay below one;
   under a rule that matches own generation to own load it should not depend on the slope. The
   holiday dose already exists, and the slope test is the one that settled the nuclear cuts
   (`rq-nuclear-cuts.md` §6.2). **My pick**: it turns the pattern every design ran into into a test.
2. **Feed-in tariff exits from 2027**, when EDP's farms leave their extensions; the DGEG request
   would then be sent.
3. **The France correction** applied to the earlier estimates as a robustness check (stakes 16–21%
   lower in open hours).
