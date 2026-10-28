# The gas cap read on the cost plants declare: running note

Started 2026-10-28 from the second repo-wide idea sweep (the two top-ranked items). Builds on the
gas-cap design (`docs/specs/2026-10-28-gas-cap-conduct-design.md`) and `notes/rq-gas-cap-conduct.md`.
Script `scripts/analysis/gas_cap_declared_cost.py` (descriptive, no estimation); outputs
`outputs/tables/gas_cap_declared_cost_{daily,event,monthly,firm}.csv`.

## 1. The pre-cap "withholding swing" starts from an offer ceiling (verified 2026-10-28)

**In one line.** Before July 2021 no offer could be priced above €180.30, so the design's "0% of
unit-hours priced far above cost in mid-2021" was a rule, not restraint.

| delivery days | lowest offer | highest offer |
|---|---|---|
| to 2021-07-06 | €0 | €180.30 (no sell offer above it in May or June 2021) |
| from 2021-07-07 | −€500 | €3,000 |

- **The rule**: CNMC resolution of 6 May 2021 (BOE-A-2021-8362) replaced MIBEL's offer limits (€0
  and €180) with the European day-ahead coupling's harmonised limits. OMIE set the start as 6 July
  2021, the auction for delivery on the 7th, which is when the data changes.
- **First uses**: a sell offer at −€120 on 2021-07-07; sell offers above €180.30 from 2021-07-10
  (7 units that day). Sell offer rows above €180.30: 1,462 in July 2021, 9,879 in August, 146,377 in September.
- **The blocks rarely bind**: before the cap the Spanish price reached €450 in 48 of 6,168 hours from
  2021-10-01 (one hour at €700). The high-priced blocks mostly price capacity that would not run anyway.

**Italy and Britain, same check (2026-10-28).** Offered sell prices, a day a week:
- **Italy (GME)**: ceiling already €3,000 in June 2021, with 11% of offer rows above €180.30 then; €4,000 from
  May 2022; floor €0 → −€500 in September 2021. The share of rows above €180.30 rises from 11% (mid-2021) to
  31–39% (October 2021 – June 2022) and falls back to 9% by June 2023, so Italy has its own swing, inside
  limits that never bound.
- **Britain (balancing offers)**: up to £9,999 throughout; the 90th percentile swings (£729 in June 2021,
  £3,950 in September 2021, £1,000 in December 2021, £4,000 in June 2022), with no rule change.
- So the €180.30 ceiling is an Iberia-only break, and only at the very start of the pre-period (to
  2021-07-06). It explains why Iberia's high blocks start at zero, not their rise from October 2021, which
  Italy shares in part.

What it changes: the swing that sank the Italian and British comparisons, and that the drift model of
§10 would explain, is partly the new room to post high prices, not a change in conduct. Recorded as a
trap in CLAUDE.md and as a correction in the design's §6 and §10.

## 2. The declared cost passes through about nine-tenths of the subsidy

**By example.** On 14 June 2022 the median Iberian combined cycle's fuel-and-carbon cost was €173/MWh,
and it declared a minimum-income variable cost of €205 (1.18 times). On 15 June the cap began and paid
it €71/MWh (bid-time). Keeping its ratio, passing on none of the subsidy would mean declaring about
€216; passing on all of it, about €131. It declared **€133.5**. From the third day it sat at €135–143
against €132–134 for full pass-through.

**What the term is.** The variable term of each plant's minimum-income condition in `cab`, declared per
unit per day. It is not an offer price: it binds on daily revenue. But it moves with fuel cost daily (0.95%
per 1%, `ivpee_tax_test.py`), so a sharp event shows on it, unlike the step offers.

**Sample.** 50 Iberian gas units (43 Spanish, 7 Portuguese) with a plant-specific efficiency, Turbogás
out, 2021-06 → 2023-06, unit-days declaring a term below the "never run" 999.

**Before the cap it is steady.** Median declared/gross cost 1.15–1.22 every month from July 2021 to May
2022, right through the months when the step offers "swung".

**The jump on day one, against placebo dates.** J = the change in each unit's mean log(declared/gross) from
the 7 days before a date to the 7 days from it (median over units):

| | J |
|---|---|
| 2022-06-15 | **−0.544** |
| full pass-through would give | −0.721 |
| 273 placebo dates, 2021-09-08 → 2022-06-07: 2.5% / median / 97.5% | −0.125 / +0.005 / +0.124 (most negative −0.291) |

The first week's jump is four times the widest placebo band. It is three-quarters of full pass-through in
logs because the first days lag (day 3: €165.5 against €132.7), not because the level stays apart.

**Pass-through share ρ by month** (each unit's own March–mid-June 2022 ratio held fixed; days with a
subsidy of at least €20):

| month | 2022-06 | 07 | 08 | 09 | 10 | 11 | 12 | 2023-01 |
|---|---|---|---|---|---|---|---|---|
| ρ, bid-time subsidy | 0.92 | 0.95 | 0.94 | 0.92 | 1.00 | 0.76 | 0.88 | 0.74 |
| ρ, delivery-day subsidy | 0.93 | 0.95 | 0.95 | 0.92 | 0.98 | 0.85 | 0.88 | 0.72 |
| median subsidy (bid), €/MWh | 71 | 161 | 190 | 145 | 54 | 23 | 130 | 28 |

**By firm, June–October 2022** (bid-time): TotalEnergies 1.02, Axpo 0.99, Repsol 0.96, Endesa 0.96,
Naturgy 0.95 (16 units), EDP 0.95, Cepsa 0.94, Bahía 0.93, RWE 0.91, **Iberdrola 0.83 (8 units), Engie
0.83 (4)**. Spain 0.93, Portugal 0.96.

**The end is not an event.** The subsidy had already shrunk to €0–6/MWh by mid-February 2023 and was last
positive on delivery day 2023-02-25. The declared cost simply follows the gross cost across it.

## 3. Caveats

- **ρ depends on the reference ratio.** After the cap the declared cost sits higher relative to cost than
  before: 1.25–1.36 times the net cost in June 2022 – January 2023, and 1.24–1.28 times the gross cost in
  March–June 2023, against 1.15–1.22 before. With the post-cap ratio as the reference, ρ would be about 1.
  So "about nine-tenths" bounds pass-through from below. The 2022–23 rise in the ratio is not explained here.
- **A declaration, not an offer.** It shows the firms' own statement of cost moved with the subsidy. Whether
  the offers that set the price moved the same way is the question the price outcomes could not answer.
- **Small-subsidy months are noisy** (November 2022, January 2023), since ρ divides by the subsidy.
- **Iberdrola's and Engie's lower ρ** rest on 8 and 4 units, read from one ratio each.
- Descriptive only: no standard errors on ρ, and the placebo is a distribution of dates, not a test.

## 4. Next (each needs a yes)

- Read the subsidy column against MIBGAS's official reference gas price (sheet `PGN_RD_10_2022` in its
  2022 workbook), since every number here uses it.
- Decide the reference for ρ (before the cap, after it, or both as bounds) and write it into the design as
  the gas-cap outcome, with the placebo rule fixed before any regression.
- Restate the design's §10 drift question on an outcome the limits change does not move.
