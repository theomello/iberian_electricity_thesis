# The post-auction contract option and buyer-side conduct through retail bids

**Status: data checked 2026-10-21 (throwaway queries, no committed script). The premise fails,
and I recommend not building it.** §2 gives the facts and §4 what is left. Builds on the fixed
step's contract result (`notes/rq-fixed-step.md`, "Ten seeds"), `notes/rq-midday-hydro.md`
§3.8 and the book-balancing results (`notes/sharper-designs-2026-10-20.md`).

**The idea, in one example.** At noon on D−1, Iberdrola's retail arm bids its customers' load into
the auction. Red Eléctrica's rules (P.O. 3.1) let Iberdrola nominate contracts between its own
hydro and its own retailer up to 13:00, after the day-ahead results. So the firm could bid
price-sensitive demand at noon, see the price, then cover whatever did not clear with its own
hydro. If so, two things follow:

1. part of the hydro decision is made through the retail demand bids, which none of the conduct
   tests read;
2. a net buyer with market power would shade those demand bids more when its stake is larger.
   That is the markdown, measured in the instrument the firm would use for it.

The checks below ask whether the bids and contracts look like that. They do not.

---

## 1. What the design needed from the data

- **Price-sensitive demand bids**: retail demand offered at prices near the clearing price, so a
  higher price clears less of it.
- **Contracts that react to the auction**: bilateral cover that differs from what the firm could
  have fixed at noon, by an amount that tracks the price surprise.
- **A noon price expectation**, to define the surprise. OMIP's daily product exists for this
  (maturity `Day`, last traded on D−1; its D−2 reference price is known at noon on D−1). An hourly
  shape would come from the days before. This part was available.

## 2. What the data show (checked 2026-10-21)

The five firms' retail purchase units in force on the 15th of each month, by dated ownership
(`lib/unit_ownership.py`), regulated pass-through suppliers out (`omie_owner.is_pass_through`).
Day-ahead demand bids (`side` C, status O), PDBF bilateral rows (role 4) on the same units.

**Retail demand bids have no price-sensitive part** (share of offered demand MW by bid price):

| month | firm | ≤ €0 | €0–180 | ≥ €180 |
|---|---|---|---|---|
| 2019-03 | Iberdrola | 69% | 0% | 31% |
| | Endesa | 52% | 3% | 45% |
| | Naturgy | 49% | 0% | 51% |
| | EDP | 0% | 3% | 97% |
| | Repsol | 0% | **65%** (most at €60–100) | 35% |
| 2023-03 | Iberdrola | 70% | 0% | 30% |
| | Endesa | 42% | 0% | 58% |
| | Naturgy | 39% | 0% | 61% |
| 2024-10 | Iberdrola | 76% (at −€500) | 0% | 24% |
| | Endesa | 21% (at −€100) | 0% | 79% |
| | EDP | 0% | 12% | 88% |

Iberdrola, Endesa and Naturgy bid two tranches. One is at €180 or more and always clears. The
other is at €0 or below (−€100 and −€500 from 2023–2024), which clears only when the price is at
or below it. Between them, from €5 to €180, they bid nothing. Within a day, their auction
purchases follow the load they declare at €180, which is larger in dear hours. The price itself
moves them only when it falls to the placeholder's price.

**The tranche that cannot clear is the self-supply, fixed at noon** (MW, hourly means):

| month | firm | tranche at ≤ €0 (set at noon) | bilateral cover (final) | hours within 1 MW |
|---|---|---|---|---|
| 2019-03 | Iberdrola | 4,688 | 4,683 | 97% |
| 2021-03 | Iberdrola | 4,817 | 4,817 | 100% |
| 2023-03 | Iberdrola | 4,910 | 5,079 | 0% (contracts above by ~170) |
| 2024-04 | Iberdrola | 3,738 | 3,882 | 7% (above by ~150) |
| 2024-09 | Iberdrola | 5,054 | 5,053 | 100% |
| 2019-03 / 2021-03 | Endesa | 4,794 / 4,749 | 3,741 / 3,678 | 0% (a near-constant gap of ~1,060) |
| 2019–2024 | Naturgy | 40–124 | 1,650–2,180 | 0% (its contracts are not in its bids at all) |

Iberdrola bids its whole load and puts the part its own plants will supply at a price that cannot
clear. The contracts then match that part to the MW in most months. Endesa does the same with an
almost constant offset. Naturgy leaves its self-supplied load out of the auction altogether. **In
every case the self-supplied volume is fixed by noon.** In 2023-03 and 2024-04, Iberdrola's
contracts exceed the placeholder by about 150–170 MW, 3–4% of the cover. That is the only trace
of the 13:00 option.

**At negative prices the placeholder still does not clear.** In April 2024 (167–263 hours at or
below €0), 0.6% of Iberdrola's tranche cleared and none of Endesa's. Naturgy's 40 MW tranche at €0
cleared 98% of the time.

## 3. What this means for the idea

- **There is no margin for buyer-side conduct through retail bids.** The three firms' retail
  demand is inelastic at every price between €5 and €180. A markdown needs a demand curve that
  could be shaded, and their bids do not offer one.
- **The 13:00 option is barely used.** The self-supplied volume is decided at noon and declared
  (or left out) in the bids. The contracts follow it, apart from top-ups of about 3–4% in two of
  the months checked.
- **What the firms do decide is a quantity at noon**: how much of the load to supply from their
  own plants. That is the book-balancing margin the holiday and own-wind quantity tests already
  studied, and found to follow own load and output rather than the price effect
  (`rq-regional-holidays.md`, `rq-own-wind-quantity.md`). A slope test on it here would repeat
  them.
- **It explains the routing result.** Iberdrola's hydro moved MW for MW between the contracts and
  the auction (fixed-step note). That is the noon split being reset hour by hour: more load
  declared at €180 and less in the placeholder means more auction purchases and less
  self-supply. It is a quantity choice, made before the price is known.

## 4. What is left, and whether to build it

| residual | size | worth building? |
|---|---|---|
| Iberdrola's top-ups above the placeholder (2023–2024) | ~150–170 MW, 3–4% of cover | only as a check: regress the top-up on the price surprise (OMIP `Day` at D−2 × the recent hourly shape). If it tracks the surprise, the option exists, but it is small. |
| Repsol's price-sensitive retail bids (65% at €5–180 in 2019; less later) | 600–900 MW of demand | the one large retailer with a demand curve that could be shaded, but Repsol is a small net buyer, with one firm's worth of variation |
| EDP's €100–180 demand tranche (12% in 2024-10) | small | no |
| Endesa's constant gap between placeholder and contracts | ~1,060 MW | a bookkeeping question (a unit or contract outside the retail set), not conduct |

**Recommendation: do not build the design.** Record §2 as a fact about the data: the big three
retailers bid inelastic demand and fix self-supply at noon. Two consequences for the other designs:
- the retail side offers no buyer-power margin to test;
- any conduct runs through the noon quantity split, which the book-balancing designs cover.

**Left to the builder, if the top-up check is wanted:** the shape window for the hourly
expectation; whether to use REE's D−1 forecasts as well; the months beyond the five checked.
