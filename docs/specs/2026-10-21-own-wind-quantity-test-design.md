# Own wind as the shock: does book balancing hold for the firm's own output?

**Status: step 1 STOP, 2026-10-21** (`notes/rq-own-wind-quantity.md`): Wdev moves own wind (1.15, t 30) but less in steep hours, so Wdev / |RD′| adds no separate movement in P_W; Sanderson–Windmeijer F 3.7 (W_s) and 2.5 (P_W), smallest detectable β 2.1. Step 2 not run. Step 2 of the program proposed after the holiday
quantity test (`docs/specs/2026-10-20-holiday-quantity-test-design.md`; with own wind held fixed,
`notes/rq-regional-holidays.md`: cut −0.27 per MWh of lost load, β −0.20 [−0.55, +0.15]). The
holidays shocked the firms' **load**; this design shocks their **output**, in every hour instead of
on 133 dates.

**In one example.** At 15:00 on some Tuesday, Galicia is windier than the rest of Spain and
Aragón calmer. Iberdrola's farms sit more in Galicia than Endesa's, so Iberdrola has, say, 200 MW
more wind than the national weather alone would give it. Three stories:
- **Price-taking.** Iberdrola's other plants run if their cost is below the price, and the price
  is the same for everyone in that hour. Its own wind changes nothing else it does.
- **Book balancing.** Iberdrola covers its customers with its own plants. With 200 MW more of its
  own wind it needs 200 MW less from its reservoirs for them, and holds that water back, steep
  hour or flat.
- **Market power.** With 200 MW more wind Iberdrola sells more, so it gains more from a higher
  price and holds back its other plants, by more in a steep hour (few rival offers near the
  price, so each MW held back moves the price a lot).

So, as on the holidays: the cut should follow P = W / |RD′| (the extra wind as a move along the
firm's residual demand) under market power, and W itself under book balancing.

---

## 1. Why this test

- **The holiday result rests on 133 dates and one kind of shock** (to load). An output shock tests
  whether the same rule covers the other side of the book, as the nuclear refuelling test did
  (`rq-nuclear-cuts.md` §6.2) for nuclear only.
- **The shock is in every hour**, so the interval on β should be much narrower than the holidays'.
- **The pieces exist**: own wind by firm and hour from located farms and ESIOS output by province
  (`self_supply_cost.own_wind_hourly`, `regional_wind_offer_test.regional_cf`), the hourly firm
  panel with slopes and own offer slopes (`holiday_quantity_panel.parquet`), generation by plant
  class and leg (`self_supply_panel.parquet`).

## 2. The test

**Panel.** The five firms (Endesa, Iberdrola, Naturgy, EDP, Repsol) by date and hour, weekdays,
2019-01 → 2025-09: the holiday quantity panel's rows (slope ≥ FLOOR, s defined), joined to the
self-supply panel's generation by class and leg and to own wind.

**Outcome.** The firm's **other generation**: PDBF schedule (both legs, MW) of its units other than
wind and generic units; and each leg apart.

**The shock.** W_s, the firm's own scheduled wind (PDBF, both legs, MW), instrumented by where its
farms sit:
- **Wdev** = Σ_r K_gr × (cf_rt − cf_t), MW: its located onshore wind capacity by region times each
  region's measured capacity factor less the peninsula's (`regional_wind_offer_test`). Zero when
  the wind blows in proportion to capacity everywhere; the national level, which moves every
  firm's other plants through the merit order in its own way, is left out.
- **P_W** = W_s / |RD′| (€/MWh), instrumented by Wdev / |RD′|.

**Controls.** 1/|RD′|; each firm's own retail purchases (PDBF, both legs: weather moves regional
load too, and the holidays showed own load moves own generation); one slope per firm on REE's D-1
forecasts of wind, solar and demand (ESIOS 1777, 1779, 1775), as in `regional_wind_offer_test`.

**Effects.** Date × hour and firm × month; errors clustered by date (week as a check).

**Regression** (two-stage least squares, `iv_two_endog.tsls_k`, first-stage F by
Sanderson–Windmeijer `sw_f`):

  G_other = b_W · W_s + b_P · P_W + controls + effects + e

**Predictions, fixed before the run.**

| | b_W (MW per MW of own wind) | b_P (MW per €/MWh) |
|---|---|---|
| price-taking | 0 | 0 |
| book balancing | < 0 (about the own wind's self-supplied share), mostly bilateral | 0 |
| market power, β | 0 beyond what P carries | **−β · s̄**, mostly in the auction |

s and s̄ as in the holiday test: the firm's own sell offers within ±€5 of the price per €/MWh,
weighted here by |Wdev| (where the instrument moves the firm's wind). β = −b_P / s̄, with its interval: 0 against 1.
**Refinement** (as the holiday test's step 2): s · P_W in place of P_W, instrumented by
s · Wdev / |RD′|; Nash −1.

## 3. Steps, each with a stop rule (each run needs a yes first)

1. **Panel, first stage, placebo, power.** Build the panel. First stage: W_s and P_W on Wdev and
   Wdev / |RD′| with the controls and effects; Sanderson–Windmeijer F for each. Placebo: own retail
   purchases on Wdev (should be about 0). Power: se(b_P) under b_P = 0, from the outcome residual
   only. *Stop* if either first-stage F < 10, or if the smallest detectable β (2.8 se(b_P) / s̄)
   exceeds 1.
2. **The slope test** (§2): pooled, by leg, by firm (Iberdrola, Endesa, the rest); the outcome
   split by plant class (hydro, nuclear, gas and coal) as a description; the checks of §4.

## 4. Threats and checks

- **Storms bring rain.** A windy Galicia is often a wet Galicia, and rain fills the same firm's
  reservoirs and rivers, raising its hydro output: a positive bias against book balancing.
  Check: firm × date effects in place of firm × month, so that only the hour-to-hour movement of
  wind within a firm's day is used; the day's water, outages and inflows drop out.
- **Wind that is curtailed or relabelled.** W_s is the firm's schedule, instrumented, so wind cut
  at low prices does not drive it; check: hours priced above €5 only. On the holidays some wind
  moved from the bilateral contract to the auction; the bilateral and auction shares of W_s are
  reported, not used.
- **Located capacity is the 2026 register** (78.5% of onshore wind): farms built later count from
  the start. Error in the instrument, not a reason for it to be wrong; check: 2022 on.
- **Steep hours are tight hours** (as in the holiday test): date × hour effects; check: the slope
  at cost (`slope_cost`) in P_W.
- **Grid constraints in windy regions** act after PDBF (`pdvd`), so they do not reach the outcome.
- **Forecast version**: Wdev_fc (REE's D-1 national forecast split across regions by the measured
  shares) as the instrument, as a check.
- **Weekdays only**, as the holiday panel; a weekend panel is left out (§7).

## 5. Data

All on disk: `holiday_quantity_panel.parquet` (slope, s, slope_cost, retail legs),
`self_supply_panel.parquet` (generation by class and leg), `renewable_unit_locations_v3`, ESIOS
1159 by province and 1485 capacity by region, ESIOS 1775/1777/1779.

## 6. Goals and limits

- **Goal:** β on the quantity margin from an output shock in every hour, and whether the firms
  cut their other plants when their own wind blows (book balancing on the output side).
- **Not a goal:** β on offer prices (the regional wind offer test did that:
  `regional_wind_offer_test.py`, β +1.5 [−1.6, 5.0]); the price effect.
- **Limits:** the five firms; Repsol has 28% of its wind located; the instrument is the regional
  split of realised wind, not known when offers close (the schedule W_s carries what the firm
  expected).

## 7. Left to the builder

- Script `analysis/own_wind_quantity_test.py` (`--panel`, `--test --step 1|2`), check
  `qa/check_own_wind_quantity.py`: a synthetic panel where planted book balancing (b_W −0.5,
  b_P 0) and Nash (b_P −s̄) are recovered through the two-stage fit; the panel's generation equals
  the holiday panel's `gen` once wind and generic units are added back.
- Hour alignment: own wind on the Madrid date and hour (`own_wind_hourly`); the holiday panel has
  no DST days.
- Hours where own wind is missing (fewer than 30 provinces reporting): dropped.
- My call: weekdays only, to reuse the holiday panel's slopes and own offer slopes unchanged;
  adding weekends would mean rebuilding them.

## 8. Amendment (2026-10-21, after step 1): instruments by slope group

**Why.** Step 1 stopped: Wdev moves own wind (1.15, t 30), but less in steep hours (about 0.4 at
the steepest 1%), so Wdev / |RD′|, which assumes the same response in every hour, carries no
separate movement in P_W (Sanderson–Windmeijer F 3.7 and 2.5; `notes/rq-own-wind-quantity.md`).

**The change.** The instruments become Wdev × D_k, k = 1, 2, 3, where D_k marks the k-th third of
the firm's own hours by 1/|RD′| (flat, middle, steep). The wind's response to Wdev may then differ
by group. b_P is identified from how the cut per MW of own wind changes from flat to steep groups,
since 1/|RD′| differs between them. Everything else in §2 is unchanged: outcome, W_s and P_W
endogenous, controls, effects, clusters, predictions.

**Calls made here.**
- **Thirds within each firm**, not pooled, so every firm contributes flat and steep hours.
- **D_2 and D_3 enter as controls** (D_1 the reference), alongside 1/|RD′|.
- Three instruments for two endogenous regressors: the Sanderson–Windmeijer F has 2 numerator
  degrees of freedom.

**Step 1 again, with the same stop rule.** Stop if either F < 10, or if the smallest detectable β
exceeds 1. Also report: the first stage of W_s on Wdev within each group, mean 1/|RD′| by group,
and the placebo (own retail on the three instruments).
