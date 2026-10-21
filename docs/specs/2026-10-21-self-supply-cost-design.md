# What does self-supply cost? Book balancing priced at each plant's cost

**Status: step 1a run 2026-10-21, STOP on power (`notes/rq-self-supply-cost.md`).** The € test's
smallest detectable effect is €53 per MWh of lost load against a reference of €17; step 1b not run.
Self-supply runs on cheap plants, is below cost about as often as auction sales and timed as well
(except Naturgy's flat hydro); the holiday cut falls on hydro and wind. Generic units resell
bought energy (232 TWh) and are not output.

Designed 2026-10-21. Follows the holiday quantity test
(`docs/specs/2026-10-20-holiday-quantity-test-design.md`, `notes/rq-regional-holidays.md`):
firms cut output on their customers' holidays by about a third of the lost load, steep hour or
flat, so the cut is book balancing, not market power. This design asks what that rule costs.

**In one example.** On the Diada, Endesa's Catalan customers use about 450 MW less, and Endesa
produces about 150 MW less. A price-taker would have kept producing and sold the 150 MW in the
auction. What Endesa gave up depends on which plant it cut:
- **a reactor** (cost about €25/MWh) at a price of €60: it gave up 150 × (60 − 25) = €5,250 an hour,
  and the rivals' plants that replaced it cost about €60. A real loss.
- **a reservoir**, whose water is worth about €60 kept for later (its water value): it gave up
  almost nothing. The water is still there.
- **a gas plant** costing €70 at a price of €60: it *saved* €1,500 an hour. The plant was running
  at a loss to serve its own customers.

So the cost is each cut MW times (price − that plant's cost). One sum, with three possible
signs, each with a different reading.

---

## 1. What the data already show (first look, 2026-10-21, scratch, not committed)

Nine sample months (January and July of 2019, 2022–2024; January of 2021, 2023, 2025), the
five firms, PDBF (the daily operating schedule: auction plus bilateral contracts), each unit to
its largest owner that day:

| technology | sold bilaterally (share of its output) |
|---|---|
| nuclear | 82% |
| solar | 72% |
| storage and other hydro | 48% |
| wind | 40% |
| coal | 7% |
| combined cycle (gas) | **1%** |

Bilateral share of each firm's output: Iberdrola 73%, Naturgy 66%, Endesa 55%, Repsol 26%, EDP 2%.
Naturgy's and Repsol's include generic sale units (`GGNCOV1` "UNIDAD GENERICA ESPAÑA", `GREPSV1`
"REPSB GENERICA VENTA"; 17% of all bilateral output) with no plant behind them in the registry.

- **Self-supply runs on cheap plants.** The firms cover their own customers with nuclear, hydro,
  wind and solar. Gas plants almost never sell under bilateral contracts. So "own plants running
  above cost for own customers" can only happen with hydro at prices below its water value and
  nuclear at prices below its fuel cost.
- **Within the day, self-supplied hydro follows the price, not the customers.** April 2024,
  weekdays: Iberdrola's bilateral hydro falls from 2,800 MW at 20:00 (€28) to 1,000 MW at midday
  (€4–5). Its customers' load is about as high at midday as in the evening (7.4 against 7.7 GW).
  The retail leg of the bilateral contract moves with the generation, and the rest of the load
  is bought in the auction. Endesa's hydro follows the price the same way. **Naturgy's bilateral
  hydro is flat** (760–830 MW in every hour), which could be timing or a full river.

So the cost of book balancing should lie mainly in **levels**: plants cut when own load falls.
The holidays measure that causally. Timing and above-cost self-supply get a descriptive check.

## 2. The measure

For each firm f, day d and hour h, over the units it owns that day (largest owner, as in the
quantity test):

  **m_fdh = Σ_u q_udh × (p_dh − c_ud)**, € per hour

with q the scheduled MW (PDBF, both legs), p the day-ahead price in the unit's country
(`price_es` or `price_pt`; they differ in 6.7% of hours), and c the unit's
cost that day:

| class | c | source |
|---|---|---|
| nuclear | fuel at book value, `c_acct` (bounds `c_lo`, `c_hi`) | `nuclear_cuts_benchmark_daily.parquet` |
| storage hydro | water value λ*, `cost_eur_mwh` (check `cost_90_eur_mwh`) | `hydro_cost_daily.parquet`, not `pumped` |
| other hydro (no water value) | 0 (run-of-river) | check: left out |
| wind, solar | 0 | — |
| gas, coal | `marginal_cost_capped_bid_eur_mwh`, plant-specific efficiency only | `implied_marginal_cost_daily.parquet` |
| pumped storage, cogeneration, biomass, generic and unlabelled units | none | reported in MW, outside m |

At fixed prices m is the firm's operating margin. A MW cut from a plant below the price, and
replaced by a rival at about the price, is also lost to the market as a whole (to first order),
so the private and the efficiency readings agree.

## 3. Steps, each with a stop rule (each run needs a yes first)

### Step 1a. Who supplies own customers, at what margin (all hours, descriptive)

Window 2019-01 → 2025-09, weekdays and weekends, the five firms.
1. **Composition**: own output by class × leg × firm × year (MWh), and the share with a cost.
2. **Above-cost self-supply**: bilateral MWh with c > p, and its € (Σ q (c − p)), by class,
   firm and year; the same for auction output, as the comparison (start-up and minimum-load
   hours put some auction output there too).
3. **Timing of hydro**: each firm's storage hydro, bilateral and auction separately, as a
   capture ratio (Σ p q / (Σ q × the day's mean price)), by firm and year; EDP (98% auction) as
   the reference. A unit-day version on its bilateral share, unit × month effects, is
   descriptive only: a full river raises both the bilateral share and flat running.
4. **Power for step 1b**: the holiday daily panel (step 1b), the MWh split of the cut by class
   (b_k below), the reference A, and se(b) computed from the outcome residual only (as in the
   quantity test), without forming b.

*Stop* if the classes with a cost cover less than 80% of the five firms' output in any year
(the margin would miss too much; a single firm below 80% is reported but gets no b of its
own), or if the minimum detectable b (2.8 × se) exceeds |A| (the
test could not tell harmless from costly). Otherwise continue.

### Step 1b. What the holiday cut costs (causal)

Firm × day panel, weekdays, 2019-01 → 2025-09, from the quantity test's dose
(`holiday_dose.parquet`). Daily, because hydro moves water between hours of the same day.

- **€ test**: M_fd = Σ_h m_fdh on Z_fd = Σ_h dose_fdh (MWh), date and firm × month effects,
  date clusters. **b is € of margin per MWh of lost own load.**
- **Split**: the same regression on each class's MWh, G_k,fd → b_k (MWh per MWh of dose; they
  sum to the total generation response, about −0.5 daily in the holiday design's step 2).
- **Reference A = Σ_k b_k × m̄_k**, with m̄_k the dose-weighted mean of (p − c) over class k's
  running units on dosed days: the cost if every cut MW were lost at its plant's margin.

**Predictions, fixed before the run.**

| reading | MWh cut (Σ b_k) | b, € per MWh of dose |
|---|---|---|
| price-taking, no book balancing | 0 | 0 |
| book balancing, harmless (cuts plants at about the price: hydro near λ*) | < 0 | ≈ 0 |
| book balancing, costly (cuts plants well below the price: nuclear, renewables) | < 0 | ≈ A < 0 |
| book balancing that saves money (cuts plants above the price) | < 0 | > 0 |

*Stop* (report the MWh split only) if b's 95% interval contains both 0 and A.

**Size.** b × the year's holiday dose (MWh), by firm and in total, against the firms' market
revenue. A second figure, labelled as an illustration and not an estimate, applies b to the
firm-specific part of own-load variation over a year (own retail net of date and firm × month
effects), since the holidays are one source of that variation, not all of it.

## 4. Threats and checks

- **λ* is a lower bound on the water value** (no option value beyond the month), so the margin of
  cut hydro is overstated and the test leans toward "costly". Check: `cost_90_eur_mwh`; storage
  hydro left out.
- **Water moved to later days**: λ* prices the kept water, so b already counts it. Check: hydro
  MWh on the dose with leads and lags of ±7 days, and their sum.
- **Plants without a cost** (generic units above all): reported in MWh beside b. If they carry
  much of the cut, say so; the € test is then partial.
- **Ownership**: largest owner, for comparability with the quantity test; a co-owned reactor counts
  wholly with one owner. Check: owners by share (`attach_owners`).
- **Hours**: the € test hourly, with date × hour effects, as a check on the daily one.
- **Days next to holidays dropped; Spain-wide and regional holidays apart; without March–June
  2020; week clusters** (as in the quantity test).
- **Nuclear cost**: `c_lo` and `c_hi` in place of `c_acct`.
- **2022–2023**: gas and coal at the capped cost (CLAUDE.md, the gas cap).

## 5. Data

All on disk: PDBF, `unit_registry`, `unit_agents` (technology: `tech_omie`, else
`tech_omie_early`), `lib/unit_ownership.py`, `holiday_dose.parquet`, `hydro_cost_daily.parquet`,
`implied_marginal_cost_daily.parquet`, `nuclear_cuts_benchmark_daily.parquet`, day-ahead prices.

## 6. Goals and limits

- **Goal:** a € figure for book balancing on holidays, with its sign: a real efficiency loss,
  harmless bookkeeping, or a saving; and a descriptive check that self-supply does not run plants
  above cost or at bad hours.
- **Not a goal:** the effect on the price (re-clearing, as in `rq-counterfactual-hydro.md`); why
  firms balance their books (contracts, risk rules); hours other than holidays causally.
- **Limits:** the five firms only; at fixed prices; costs are bounds (λ* low, nuclear between
  `c_lo` and `c_hi`, thermal without start-up costs); generic units have no plant.

## 7. Left to the builder

- Script `analysis/self_supply_cost.py` (`--describe` for 1a, `--test` for 1b), check
  `qa/check_self_supply_cost.py` (a synthetic panel where planted b and b_k are recovered; m
  reproduces Σ q (p − c) on a hand-computed unit-day). Unit-level PDBF as in
  `holiday_quantity_test.month_legs`, with class and cost attached before aggregating.
- PDBF is quarter-hourly from 2025-03-19: average the four quarters to the hour.
- Identify what `GGNCOV1` and `GREPSV1` sell (registry, `cab`, OMIE listings) and record it; do
  not give them a cost.
- Units in more than one class over the window (`tech_omie` changes): the day's label.
