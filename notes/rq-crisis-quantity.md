# Quantity withholding through the crisis: running note

Design: `docs/specs/2026-10-28-crisis-quantity-design.md`. Results in order of the design's steps.

## B0. Gross-cost twin and essential flag (2026-10-28, bbfb7d3)

`run{10,20,50}_gross` and `essential` added to `gas_cap_offer_panel.parquet`; `qa/check_gas_cap_offer_panel.py`
passes (twin = original on all 1,374,568 unsubsidised unit-hours; ≥ original on the 285,955 subsidised ones,
higher on 23.8%; Porcari and Sarlux flagged). Earlier in-money results reproduce unchanged.

## B1. The two ends and the minimum detectable effect (2026-10-28): STOP, narrowly on run20

`scripts/analysis/gas_cap_quantity_b1.py` → `outputs/tables/gas_cap_quantity_b1_{ends,mde}.csv`.

**The two ends** (each Iberian unit's last eight pre-cap weeks of markups over gross cost, carried forward;
main sample; mean over the 35 weeks with a subsidy, mean S €102):

| | full pass-through | none | gap |
|---|---|---|---|
| run20 (near net cost) | 0.646 | 0.388 | **0.257** |
| run20_gross (near gross cost) | 0.720 | 0.646 | 0.074 |

The ends coincide on all 12 post-cap weeks without a subsidy (check). By month the run20 gap follows the
subsidy: 0.44 in July 2022 and 0.53 in August (S €164 and €225), 0.01–0.04 in January–February 2023.

**Minimum detectable effect** (estimator B, placebo caps, weeks before 2022-06-15 only; 49 Iberian and
44 Italian units, missing-week limit 30%; firm block bootstrap 199; MDE = 2.8 × se):

| outcome | placebo | r | placebo gap (se) | MDE | half the gap | rule |
|---|---|---|---|---|---|---|
| run20 | 2022-01-01 | 0 | +0.004 (0.047) | 0.133 | 0.129 | fails |
| run20 | 2022-03-01 | 3 | −0.019 (0.047) | 0.133 | 0.129 | fails |
| run20_gross | 2022-01-01 | 0 | +0.009 (0.044) | 0.123 | 0.037 | fails |
| run20_gross | 2022-03-01 | 3 | −0.011 (0.046) | 0.129 | 0.037 | fails |

**Rule: STOP for both outcomes.** run20 misses by 0.004 (MDE 0.133 against 0.129); run20_gross is far off
(its gap is small: offers near gross cost barely move whether or not the subsidy is passed on).

**What the placebos do show:** the counterfactual fits the pre-period (placebo gaps +0.004 and −0.019, well
inside one se). The failure is power (about a dozen Iberian firms as bootstrap clusters), not bias.

**Descriptive, not Branch B** (no Italian counterfactual; pre-cap behaviour carried forward is itself the
counterfactual): Iberia's actual means over the subsidy weeks are run20 0.665 and run20_gross 0.750, at or
above the full pass-through end on both (0.646, 0.720). Read by linear interpolation, ρ ≈ 1.1 on run20.

**Not done, each the user's decision (changing the rule after seeing the result):**
- the gap over the high-subsidy months only (June–September and December 2022: run20 gap 0.29–0.53, well
  above the MDE) — a different averaging from the one fixed;
- the within-Iberia reading above as the Q2 answer, with Italy dropped from Q2.

## B1 amended (2026-10-28, the user's decision after seeing the result above)

**The rule's average is restricted to the high-subsidy months: June–September and December 2022** (19 weeks
with a subsidy, mean S €160; the excluded months have mean S €10–51, where the two ends nearly coincide and
there is nothing to detect). **Chosen after seeing B1; any write-up must say so.** The placebo MDEs are
unchanged (their post windows, 23 and 15 weeks, bracket the 19 weeks).

| outcome | gap, high-subsidy months | half | MDE (worse placebo) | rule |
|---|---|---|---|---|
| run20 | 0.410 | 0.205 | 0.133 | **passes** |
| run20_gross | 0.099 | 0.050 | 0.129 | fails |

So B2 runs on **run20 only**, over the same five months; run20_gross is dropped from Q2.

## B2. Pass-through against Italy (2026-10-28): STOP, the counterfactual fails after the subsidy

`scripts/analysis/gas_cap_quantity_b2.py` → `outputs/tables/gas_cap_quantity_b2{,_weekly}.csv`. 49 Iberian and 44
Italian units × 92 weeks; 19 high-subsidy weeks; 18 weeks after 2023-02-25. Xu's cross-validation picks r = 0
(MSPE nearly flat across r = 0…5).

| | estimate | 95% (firm block bootstrap, 10 Iberian / 12 Italian firms) |
|---|---|---|
| ATT, high-subsidy weeks | +0.025 | [−0.053, +0.118] |
| ρ = 1 + ATT / 0.410 | 1.06 | [0.87, 1.29] |
| **ATT after 2023-02-25 (should be ~0)** | **+0.134** | [+0.019, +0.197] |

**Rule (fixed): the gap after the subsidy is outside ±0.05 → STOP.** It is +0.13 to +0.18 at every r = 0…5, so
after the cap Iberian plants offer more capacity near cost than the Italian-built counterfactual predicts,
with no subsidy to explain it. The same drift may sit inside the high-subsidy ATT, so ρ cannot be read off.
For scale only, not a result: subtracting the after-gap would give ρ ≈ 0.73.

Sensitivity (B, ATT high / after / ρ): r 1 +0.020 / +0.148 / 1.05; r 3 −0.015 / +0.153 / 0.96; r 5 −0.027 /
+0.168 / 0.93. Bai's θ on Iberia × high weeks −0.18 to +0.09, sign changing with r.

Checks at r = 0 (point estimates): all hours ATT high +0.114, after −0.017; margin > €20 +0.066 / +0.058;
pre-cap hour-of-day mix +0.056 / +0.132. **Only the all-hours sample passes the after-check**, which suggests the
post-cap drift is partly which hours count as in the money in 2023 (prices fell, so the in-money sample shrinks
and changes). Not tested.

Ruling (builder's): check (c) reweights to the pre-cap **hour-of-day** mix only; the design said hour × month,
but months before and after the cap do not overlap.

Reading: the third Italian comparison to fail its own check after the cap ended (p_mid +€168; now run20
+0.13). The within-Iberia description stands (actual run20 at the full pass-through end, B1 section).

## B2 on all hours (2026-11-02, the user's decision after the main B2 stopped)

**A sample change made after seeing the result; any write-up must say so.** Main sample = every hour of each
unit (no in-money condition), Italian essential units still out; same units rule, same high-subsidy months,
same stop rules. `gas_cap_quantity_b1.py --all-hours` and `gas_cap_quantity_b2.py --all-hours` → the same
tables suffixed `_allhours`. 51 Iberian and 53 Italian units × 92 weeks; 20 high-subsidy weeks.

**B1 on all hours: STOP on power.** Full − none gap over the high-subsidy months 0.339 (full 0.529, none
0.190), so half is 0.170. Placebo MDEs 0.117 (2022-01-01, r 0) and **0.207** (2022-03-01, r 3): the worse one
fails. The pre-period fit is also weaker than in-money hours: placebo gaps +0.053 and +0.063 (in-money +0.004,
−0.019), each about one se.

**B2 on all hours: the after-check holds at the chosen r.** Xu's cross-validation picks r = 2.

| | estimate | 95% (firm block bootstrap, 12 Iberian / 13 Italian firms) |
|---|---|---|
| ATT, high-subsidy weeks | +0.058 | [−0.011, +0.171] |
| ρ = 1 + ATT / 0.339 | 1.17 | [0.97, 1.50] |
| ATT after 2023-02-25 (should be ~0) | −0.030 | [−0.150, +0.108] |

Sensitivity (r, ATT high / after / ρ): 0 +0.110 / −0.017 / 1.32; 1 +0.103 / **−0.064** / 1.30; 3 +0.036 /
−0.036 / 1.11; 4 +0.016 / **−0.055** / 1.05; 5 +0.012 / **−0.054** / 1.04. The after-gap is outside ±0.05 at
r = 1, 4, 5, so the check holds at the chosen r but not robustly. Bai's θ on Iberia × high weeks −0.05 to
+0.10, sign changing with r. Checks: the in-money sample inside this run gives ATT high +0.007, after +0.143
(the main B2's failure, reproduced); the hour-of-day reweighting does nothing here (every hour is present on
both sides of the cap).

**Reading.** On all hours the Italian counterfactual no longer drifts after the cap, which supports the lead
that the main B2's post-cap gap came from which hours count as in-money in 2023. But the design is
underpowered on this sample (B1 fails) and the after-check is fragile across r. ρ = 0 (no pass-through) is
far outside the interval at every r; ρ = 1 (full pass-through) is inside it. So: **the pass-through estimate
is consistent with full pass-through and rejects none, with a wide interval, on a sample chosen after seeing
the result.** It agrees with the within-Iberia description (ρ ≈ 1.1) and the declared-cost result (~0.9–1.0).
Not a stand-alone estimate; usable as corroboration.

## B3. Dose-response against Italy — design fixed before running (2026-11-02)

The user's request after the all-hours B2 (a fourth Italian specification; say so in any write-up). Instead of
the mean gap over high-subsidy weeks, test the shape the two ends predict week by week. With g_w = full − none
(B1 ends) and ATT_w the weekly Iberia − counterfactual gap from estimator B (Xu 2017, as B2):

    ATT_w = a + b · g_w,  over every week from 2022-06-13 to 2023-06-30 (weeks with g_w = 0 included)

Full pass-through gives b = 0, none gives b = −1, so **ρ = 1 + b**. The intercept a absorbs any constant post-cap
drift (what broke the in-money B2: +0.13 with no subsidy). g_w rises to 0.6 in August 2022, falls to ~0 in late
October–November, returns to 0.4 in December, and is 0 from late February 2023: the dip and the December
return separate the slope from slow drift.

- **Main:** in-money sample (the design's fixed sample), r by Xu's cross-validation as in B2, OLS weighted
  equally by week, 95% interval from the same firm block bootstrap within country (199 draws; ATT_w
  re-estimated each draw, g_w held fixed).
- **Check (stop rule, fixed):** add a linear time trend over the same weeks. If the trend version's ρ falls
  outside the main 95% interval, the slope is picking up time, not subsidy → STOP.
- **Reported beside, not decisive:** r = 0…5; the all-hours sample with its own ends (chosen after seeing B2).

### B3 results (2026-11-02): the check holds on both samples; in-money ρ ≈ 0.75

`scripts/analysis/gas_cap_quantity_b3.py [--all-hours]` → `outputs/tables/gas_cap_quantity_b3{,_allhours}.csv`.

| sample | r | intercept a | ρ = 1 + b, 95% | ρ with linear trend, 95% | rule |
|---|---|---|---|---|---|
| **in-money (main, fixed)** | 0 | +0.142 | **0.73 [0.51, 1.03]** | 0.79 [0.66, 0.91] | holds |
| all hours (chosen after B2) | 2 | +0.000 | 1.18 [0.78, 1.50] | 0.96 [0.76, 1.19] | holds |

Firm block bootstrap, 199 draws: 10 Iberian / 12 Italian firms in-money, 12 / 13 all hours. Sensitivity, ρ
(trend) at r = 0…5: in-money 0.73, 0.70, 0.69, 0.63, 0.54, 0.57 (0.79, 0.79, 0.79, 0.77, 0.74, 0.75); all
hours 1.27, 1.38, 1.18, 1.18, 1.16, 1.16 (0.99, 1.06, 0.96, 1.07, 0.97, 1.01).

**Reading.**
- On the main sample the dose-response works where the mean did not: the intercept takes the post-cap drift
  (+0.142, the +0.134 that stopped B2), and the slope, identified off the October–November dip and the December
  return, gives ρ 0.73. No pass-through (ρ = 0) is rejected at every r; full pass-through is just inside the
  interval (upper end 1.03) without the trend and rejected with it (0.66–0.91). ρ falls as r rises (0.54–0.73),
  so the point estimate is not tight. Read: **about three-quarters of the subsidy reached offers near cost**,
  full pass-through borderline.
- On all hours ρ is 1.18, and 0.96–1.07 with the trend; full pass-through not rejected, none rejected.
- **The two samples disagree on the point (0.73 against 1.18); the intervals overlap on [0.78, 1.03].** The
  in-money sample is the design's and was fixed first. All hours was chosen after B2 and its power check
  (B1) fails.
- Against the other gas-cap results: declared minimum-income cost 0.9–1.0, within Iberia ρ ≈ 1.1. B3 in-money
  sits below both. A difference between what plants declare and what they offer near cost would be a finding
  in itself, but these intervals do not establish it.
- A fourth Italian specification, requested after three failed; any write-up must say so.

## B3 checks — rules fixed before running (2026-11-03)

On the main (in-money, r = 0) B3; the all-hours sample reported beside, not decisive. Main interval
[0.51, 1.03].

1. **Timing permutation.** Shift g_w cyclically by k = 1 … n−1 weeks within the post-cap weeks that carry
   g_w (n = 46), re-estimate b each time (ATT_w fixed). Pass if the real b is at or below the 5th percentile
   of the shifted b's (one-sided p ≤ 0.05).
2. **Leave one episode out.** Re-estimate without the weeks starting in December 2022, then without those
   starting in October–November 2022. Pass if both ρ lie inside the main interval.
3. **Gas price controls.** Add the weekly mean MIBGAS price (bid-time day-ahead index) and the weekly mean PSV
   − MIBGAS spread as regressors. Pass if ρ lies inside the main interval.

All three pass → B3 enters the paper as the Italian estimate. Any fails → B3 is corroboration only.

### B3 check results (2026-11-03): ALL PASS on the main sample

`scripts/analysis/gas_cap_quantity_b3_checks.py [--all-hours]` → `outputs/tables/gas_cap_quantity_b3_checks{,_allhours}.csv`.

| check | in-money (main, r 0; interval [0.51, 1.03]) | all hours (r 2; [0.78, 1.50]) |
|---|---|---|
| 1. timing permutation: real b vs cyclic shifts | b −0.274; shifted median +0.018, 5th pct −0.189; p 0.000 (45 shifts) **pass** | b +0.178; p 1.000 (53 shifts): FAIL by the one-sided rule; the real b is above every shift |
| 2. without December 2022 | ρ 0.74 **pass** | 1.19 pass |
| 2. without October–November 2022 | ρ 0.73 **pass** | 1.20 pass |
| 3. control MIBGAS | ρ 0.58 pass | 0.77 FAIL |
| 3. control PSV − MIBGAS | ρ 0.70 pass | 1.08 pass |
| 3. control both (decisive) | ρ 0.54 **pass** | 0.70 FAIL |

**Reading.**
- **Main sample: B3 enters the paper as the Italian estimate.** No shifted alignment of the subsidy path gives
  a slope as negative as the real one (p < 1/45), so the slope follows the subsidy's timing, not chance. It does
  not rest on one episode (0.73–0.74 without either).
- **The gas price control moves the point down**, 0.73 → 0.54 with both controls, close to the interval's lower
  end. So the plain ρ partly carries a different response of Iberian and Italian offers to the gas price level.
  Quote the range: **ρ ≈ 0.55–0.75, no pass-through rejected, full pass-through at the edge without controls
  and outside with them.**
- **All hours fails as an estimate in its own right**: its slope is positive and above every shifted one, and
  the MIBGAS control removes most of it (1.18 → 0.70–0.77). With both controls the two samples come closer
  (0.54 in-money, 0.70 all hours). All hours drops to a footnote.
- Resolution of the permutation p is 1/45; cyclic shifts keep ATT_w fixed, so they test the alignment only.

## C. The cap's pass-through in euros — definition fixed before computing (2026-11-03)

The design's end goal (§3): ρ × subsidy × in-money volume. **This is the offer-side figure, not the consumer's
saving.** V = Σ over Iberian unit-hours of the main sample (predicted in-money at margin €50, essential units
out, cost defined, 2022-06-15 → 2023-02-25, subsidy > 0) of S_day × offered MW × 1 h (hourly periods; the
panel's `offered_mw` is average MW). V is the subsidy attached to the capacity offered in hours the plant can
expect to run; ρ × V is the part of it that went into those offers. Units: the 54 Iberian gas units with a
plant-specific efficiency, so it **leaves out** other gas and coal plants. `offered_mw` is offered, not cleared,
so V overstates what was paid out.

Reported: V by month; ρ × V for ρ = 0.54 and 0.73 (B3 main, with and without gas controls), the interval ends
0.51 and 1.03, and the declared-cost 0.9–1.0 for comparison. Not done here: the consumer's saving, which
needs the price-setting step (how often a subsidised unit sets the price, times cleared demand) and a check
against the observed price drop. No hour-level setter table is on disk.

### C results (2026-11-03)

`scripts/analysis/gas_cap_pass_through_eur.py` → `outputs/tables/gas_cap_pass_through_eur{,_monthly}.csv`.
54 Iberian gas units, 1,558 in-money hours, 27,146 GWh of in-money offered capacity, **V = €4,122 m**. By
month (€ m): Jun 344, Jul 622, **Aug 1,421**, Sep 1,116, Oct 258, Nov 60, Dec 286, Jan 13, Feb 2; August and
September are 61% of V.

| ρ | source | ρ × V (€ m) |
|---|---|---|
| 0.51 – 1.03 | B3 95% interval | 2,102 – 4,246 |
| 0.54 | B3 with gas controls | 2,226 |
| 0.55 – 0.75 | quoted B3 range | 2,267 – 3,092 |
| 0.73 | B3 main | 3,009 |
| 0.90 – 1.00 | declared costs | 3,710 – 4,122 |

**Reading.** The part of the subsidy that reached these plants' offers is **about €2.3–3.1 bn** on B3's range
(the interval runs €2.1–4.2 bn). The share not reflected is €1.0–1.9 bn at the same range, with the same
caveat: ρ is estimated with a wide interval, and the uncertainty in ρ is the larger part of the uncertainty
here.

**What it is not.** (1) Not the consumer's saving: that is the price falling in hours these units set it, times
cleared demand, and needs the price-setting step and a check against the observed price drop (not done; no
hour-level setter table on disk). (2) V uses offered MW, not cleared, so it overstates the subsidy actually
paid on these units' output; the euros are an upper bound on the offer side. (3) Only the 54 modelled gas
units; other gas and coal plants are out. (4) ρ is B3's, a fourth Italian specification (see above).

## D. The consumer's saving — re-clearing the day-ahead curve without the pass-through (design fixed before running, 2026-11-03)

User asked for the price-setting step after C. **A first-order count (hours a subsidised plant sets the price × ρS
× demand) is wrong in both directions** (raising a unit's offers can also move the price when it was *not* the
setter: it drops out below another unit, and a dearer one is needed). So the saving is a **counterfactual
re-clear**, using the effective curve of `step_curves.py` (accepted rows on the accepted side of the price, offered
rows at and beyond it).

For each ρ in {0.51, 0.54, 0.55, 0.73, 0.75, 1.00, 1.03}:
1. Hours: 2022-06-15 → 2023-02-25, days with S_d > 0 (panel `subsidy`, Iberian), 24-period days, **valid** hours
   only (unsplit Spain/Portugal, clearing identity holds, re-clear of the actual curve within €0.5 of the
   published price). Split hours are left out and reported (share of the hours and of V).
2. Counterfactual "no pass-through of the part ρ": every sell row of the 54 modelled gas units (the set of C and
   B1) is moved up by ρ·S_d; the hour is re-cleared; p0 is the new price. Actual price p_a = re-clear of the
   unmoved curve. Hourly gross saving (p0 − p_a) × cleared buy MW × 1 h.
3. G(ρ) = Σ hourly gross saving (€ m). B = Σ S_d × cleared sell MW of the 54 units (€ m): the subsidy bill on
   the modelled units, which the mechanism charged to buyers. **Net saving = G − B** (indicative: the quantities
   are the actual world's in both terms, and B is a floor, only 54 units and auction-cleared energy).

Also reported: share of valid hours in which any move changes the price, mean and 95th percentile of the price
change, and how many of the units sat at the margin (an accepted sell row within €0.011 of the price).
**Limits stated now:** units' ladders are the effective rows (accepted below the price), as in `step_curves.py`;
the price effect of moving only the 54 units, not other gas or coal plants; demand is all cleared buy volume,
exports included; the counterfactual keeps every other offer fixed. Not checked against an observed price drop:
there is none to check against (no cap-free Iberia).

### D results (2026-11-03)

`scripts/analysis/gas_cap_consumer_saving.py` → `outputs/tables/gas_cap_consumer_saving.csv` (by ρ) and
`gas_cap_consumer_saving_hourly.parquet` (ρ 0.73). 55 Iberian gas units with a cost (54 with subsidy days);
5,808 hours in the cap months, **5,397 valid (92.9%)**; the split Spain/Portugal and identity-failing hours are
left out, so every euro figure covers 93% of the hours. Re-clear of the unmoved curve reproduces the published
price within €0.5 in all valid hours by construction (the validity rule).

| ρ | gross wholesale saving G (€ m) | net of the bill B = €4,937 m | price falls in … of hours | mean fall (€/MWh) |
|---|---|---|---|---|
| 0.51 | 2,033 | −2,905 | 74% | 14.5 |
| 0.54 | 2,192 | −2,745 | 74% | 15.6 |
| 0.55 | 2,246 | −2,692 | 75% | 16.0 |
| 0.73 | 3,211 | −1,727 | 78% | 22.8 |
| 0.75 | 3,319 | −1,618 | 78% | 23.6 |
| 1.00 | 4,670 | −267 | 80% | 33.2 |
| 1.03 | 4,825 | −112 | 81% | 34.3 |

B = Σ S_d × cleared sell MWh of the 54 units (€4,937 m in valid hours; €5,268 m in all hours).

**Reading.**
- The modelled units sit exactly at the price in only **0.5% of valid hours**, yet the price moves in 74–81%:
  moving their offers up takes them out of the merit order below dearer units, which is why a count of
  "hours a subsidised plant sets the price" would have been wrong.
- **On B3's range (ρ 0.55–0.75) the gross saving is €2.2–3.3 bn, less than the subsidy bill on the same
  units (€4.9 bn): net −€1.6 to −2.7 bn.** Break-even needs ρ ≈ 1.05, just above full pass-through. The gross
  saving is the same order as C's ρ × V (€2.3–3.1 bn) — a consistency, not a check (different bases).
- **The net figure is the part to distrust most.** It assumes (i) the bill fell on buyers; the decree's
  allocation between domestic buyers, exporters and bilateral contracts is not checked here; (ii) only the 54
  units are moved and billed (other gas and coal plants out); (iii) B is not compared with REE's published
  adjustment cost; (iv) buy-side demand is fixed and every other offer unchanged; (v) the counterfactual is
  "undo the passed-through part ρ", with the subsidy itself unchanged. It contradicts the public account of a
  net consumer saving, so it needs those checks before it is quoted.

### D, bill check and wider unit sets — rules fixed before running (2026-11-03)

**Bill check (done first, ESIOS fetched 2026-11-03: 1907, 10403, 10406–10408, `--geo 0`, 2022-06-01 → 2023-06-30).**
ESIOS 1907 is REE's hourly average price component of the RD-L 10/2022 mechanism for the day-ahead and intraday
markets (€/MWh charged to buyers); 10403 the same with the mechanism's name; 10406–10408 the monthly values.
Check: Σ_h charge_h × cleared buy MWh_h over the valid hours, against B (S × cleared sell MWh of the 54 units).
Pass if within 15%. If the ESIOS figure is much larger, the 54 units miss a material share of the subsidised
energy and the unit-set rerun matters for the bill; if close, it matters little.

**Wider sets** (`gas_cap_consumer_saving.py --units`): `ccgt_coal` = every unit OMIE's listing labels gas CCGT
or coal (`tech_omie`, early label where missing) ∪ the 54; `thermal` = that ∪ cogeneration. Same S_d, same ρ
(extrapolated beyond the 54, which is the only units ρ was estimated on); same hours and re-clear. Eligibility of
cogeneration for the mechanism is **not checked**, so `thermal` is a sensitivity, `ccgt_coal` the main wider set.
Reported beside the 54-unit result; no decision rule: the question is whether G and B move.

### D, bill check and wider sets: results (2026-11-03)

**Bill check passes.** ESIOS 1907 (REE's hourly price component of the mechanism, €/MWh charged to buyers) × cleared
buy MWh over the valid hours = **€5,184 m**, against B = €4,937 m for the 54 units: ratio 1.05, inside the 15%
rule. By month (ESIOS / B, € m): Jun 485 / 409, Jul 1,117 / 1,073, Aug 1,536 / 1,504, Sep 1,114 / 1,115, Oct 358 /
333, Nov 99 / 115, Dec 476 / 359, Jan 13 / 16, Feb −14 / 14. The implied subsidised energy (charge × buys / S) is
35.5 TWh against 37.1 TWh cleared by the 54 units, so **they carry about the whole subsidised energy**. Monthly
average component (10406): Aug €88.8/MWh, Jul €66.9, Sep €65.0, Jun €27.5, Dec €32.2. Not checked: the decree's
allocation of the bill between domestic buyers, exporters and bilateral contracts; ESIOS also splits the component by
free-market supply and reference suppliers (1908/1909, 10404/10405), not fetched.

**Wider unit sets** (`--units`): bill and gross saving (€ m), valid hours.

| set | units | B | G at ρ 0.55 | G at 0.73 | G at 0.75 | G at 1.00 | net at 0.55 – 0.75 |
|---|---|---|---|---|---|---|---|
| 54 modelled gas (main) | 54 | 4,937 | 2,246 | 3,211 | 3,319 | 4,670 | −2,692 – −1,618 |
| + OMIE gas CCGT and coal | 97 | 5,870 | 2,455 | 3,539 | 3,661 | 5,260 | −3,415 – −2,208 |
| + cogeneration | 623 | 6,836 | 2,543 | 3,660 | 3,788 | 5,500 | −4,293 – −3,048 |

**Reading.**
- The official charge (€5.2 bn) sits **between the 54-unit bill (4.9) and the 97-unit one (5.9)**, and the cogeneration
  set overshoots it by a third (6.8): cogeneration was largely not charged, or ran little under the mechanism. So
  the wider main set is `ccgt_coal`, and the gross saving rises 9–10% for it against 17–18% for the bill.
- **Widening the set makes the net more negative, not less.** G rises by about €0.2–0.4 bn and B by €0.9 bn: the
  added plants add bill faster than they add saving. Against the official bill (5,184) the 54-unit net is
  −€2.9 to −1.9 bn at ρ 0.55–0.75 and −€0.5 bn at ρ = 1.
- Break-even needs ρ above about 1.1 on every set. The sign of the net figure does not depend on the unit set; its
  size does. Remaining unchecked: who the bill fell on (exports, bilateral), fixed other offers, buy bids fixed.

### D, who bore the bill: ESIOS splits the charge by buyer type (2026-11-03)

Fetched 1908 (free-market supply), 1909 (reference suppliers), 10404, 10405, same window. Monthly mean of the
hourly day-ahead and intraday component, €/MWh:

| month | all (1907) | free market (1908) | reference suppliers (1909) | free ÷ reference |
|---|---|---|---|---|
| 2022-06 | 26.1 | 24.2 | 49.9 | 0.48 |
| 2022-07 | 62.2 | 57.3 | 116.3 | 0.49 |
| 2022-08 | 86.5 | 79.5 | 163.3 | 0.49 |
| 2022-09 | 62.5 | 58.8 | 109.3 | 0.54 |
| 2022-10 | 21.6 | 20.5 | 37.1 | 0.55 |
| 2022-11 | 5.8 | 5.5 | 9.2 | 0.60 |
| 2022-12 | 25.9 | 24.5 | 39.9 | 0.61 |
| 2023-01 | 1.1 | 1.1 | 1.4 | 0.74 |

**Reading.** Reference suppliers (the regulated tariff) paid about **twice** the per-MWh charge of the free market
in the summer. A natural reading, **not checked against the decree text**: the charge falls on energy bought in
the spot market, reference suppliers buy nearly all of theirs there, and free-market retailers buy about half in
the spot market and the rest by bilateral contract, so the ratio is the free-market spot share (0.48 in summer
to 0.74 in January). That is the size of the physical bilateral share in PDBF (39–49% of scheduled sell in
2018–2024, computed for earlier years, not for these months). If right, (i) the bill is a charge on spot
purchases, which is the same base the wholesale saving applies to, so G − B compares like with like; (ii) energy
under bilateral contracts bore neither the charge nor, unless indexed, got the saving; (iii) the reference
suppliers' customers are the clear net losers per MWh (€163 in August against a mean price fall of about €49 at
ρ 0.73). Exports and the allocation by buyer type of the 1907 total are still not separated from this data.

### D, scheduled demand by buyer group and exports (ESIOS, fetched 2026-11-03)

Fetched 351 (free-market retailers), 352 (reference suppliers), 353 (direct consumers in the market), 10141 (total) —
all "Demanda programada PBF" (the base schedule, bilateral contracts included) — and 32–35 (PBF exports to France,
Portugal, Morocco, Andorra), peninsular, hourly, 2022-06-01 → 2023-06-30. Over the 5,397 valid hours:

| | GWh | share of group demand |
|---|---|---|
| free-market retailers (351) | 126,637 | 88.4% |
| reference suppliers (352) | 12,445 | 8.7% |
| direct consumers (353) | 4,108 | 2.9% |
| three groups / total (10141) | 143,190 / 143,273 | 99.94% |
| exports (32–35; ESIOS signs them negative) | 17,201 | — |
| cleared day-ahead buy volume (bids, status C) | 136,984 | — |

**Three routes to the bill, valid hours (€ m):** 1908 × free + 1909 × reference suppliers = **5,266** (free market
4,463; reference suppliers 803); 1907 × cleared buys = 5,184; B (S × cleared sell MWh of the 54 units) = 4,937.
They agree within 7%. By month the group-priced bill reproduces B closely (Aug 1,580 against 1,504; Sep 1,110
against 1,115; Nov 99 against 115) and exceeds it in Dec (472 against 359).

**Reading.**
- The group-priced bill adds the three groups' own charges and needs no assumption about the cleared-buy base:
  it supports a total cost of **€5.3 bn**, 6% above the 54 units' B. The saving-net-of-bill therefore stays
  between −€3.0 and −€1.9 bn at ρ 0.55–0.75 (54 units), as before.
- Reference suppliers are 8.7% of group demand and **15% of the bill** (803 of 5,266).
- Exports: charging them the 1907 rate on top would add about €0.7 bn (bill €6.0 bn), above every unit-set
  bill built (4.9 / 5.9 for 54 / 97 units). The groups alone already reproduce the cost, which fits exports
  **not** bearing the charge, but the totals cannot prove it (decree text not read).
- Not done: the net for each group (its charge against its own share of the price fall), which needs the
  group's spot-purchase share; the free ÷ reference ratio of 0.48–0.74 is an inference for that share, not
  data.

### D, net by buyer group — definition fixed before running (2026-11-03)

For group g in {reference suppliers, free-market retailers}, over the valid hours, at ρ in {0.55, 0.73, 0.75, 1.00}
(54 units):
- **Bill_g** = Σ_h charge_g,h × PBF demand_g,h (ESIOS 1909 × 352; 1908 × 351): the official figures.
- **Saving_g** = Σ_h (p0_h − p_h) × cleared day-ahead buy MWh of g's units in h (from the bids, status C buys by
  unit). Reference-supplier units: Spanish units whose OMIE listing owner is a regulated pass-through supplier
  (`is_pass_through`); free-market retailers: Spanish registry role `purchase_retail` not in that set. The
  group's saving thus applies only to its day-ahead purchases, not to bilateral energy.
- **Net_g** = Saving_g − Bill_g, in € m and per MWh of the group's PBF demand.
- **Test of the spot-share inference:** the day-ahead buys of each group over its PBF demand, by month; the
  inference says the free-market share ÷ reference share equals the charge ratio (0.48–0.74).
Not decided in advance: any threshold. Limits: unit-to-group by the listing's owner (latest snapshot, not dated);
retailers' bilateral energy gets no saving here (indexed contracts would); exports and Portugal excluded.

### D, net by buyer group: results (2026-11-03)

`scripts/analysis/gas_cap_group_net.py` → `gas_cap_group_net.csv`, `gas_cap_group_share_monthly.csv`,
`gas_cap_saving_by_category.csv` (needs `gas_cap_consumer_saving.py` first; that script now stores the
counterfactual price for ρ 0.51–1.03). 54 units, 5,397 valid hours. The unit groups are finer than fixed above:
the first pass left a large "other" (36% of day-ahead buys), so it is split into reference suppliers, free-market
retail (`purchase_retail`), generic units (`storage_mixed`, retailers' resale units, e.g. Naturgy's `GGNCOC1`),
pumping, other Spanish, Portugal (registry country PT) and unknown (not in the registry: the interconnection
pseudo-units, i.e. exports). The categories cover all cleared buys (asserted).

**Net by group** (saving on the group's day-ahead buys − the official charge × its scheduled demand):

| group | ρ | saving | bill | net | per MWh of its scheduled demand |
|---|---|---|---|---|---|
| reference suppliers | 0.55 / 0.73 / 0.75 / 1.00 | 160 / 228 / 236 / 332 | 803 | −644 / −575 / −568 / −472 | −€52 / −46 / −46 / −38 |
| free-market retail | 0.55 / 0.73 / 0.75 / 1.00 | 1,014 / 1,449 / 1,498 / 2,108 | 4,463 | −3,449 / −3,014 / −2,965 / −2,356 | −€27 / −24 / −23 / −19 |

With the generic units counted as free-market (ambiguous; they are retailers' resale units): saving +€398 m at ρ 0.73,
net −€2,616 m. **Both groups are net losers at every ρ up to 1.** Even at full pass-through reference suppliers
lose €38/MWh and the free market €19/MWh.

**Who receives the wholesale saving (ρ 0.73, total €3,211 m):** free retail 45%, generic units 12%, reference
suppliers 7%, other Spanish 4%, pumping 1%, **Portugal 22% (€699 m)**, **unknown / exports 8% (€256 m)**. About a
third (€0.96 bn) goes to buyers outside the Spanish scheduled-demand base. The Spanish bill is the groups' charge
only (exports and Portugal apparently did not pay, §above), so the same price fall that Spanish buyers
financed lowered what Portuguese and exporting buyers paid. Not checked against the decree: whether Portuguese
buyers or exports bore any charge, and in split hours (7% excluded) Portuguese price is separate.

**Spot-share inference (day-ahead buys ÷ scheduled demand):** reference suppliers 0.79–0.84, not 1; free-market
retail 0.43–0.53 (0.54–0.66 with the generic units). Ratio free ÷ reference 0.51–0.66 (0.65–0.84 with generic)
against the charge ratio 0.48–0.76: the right level and direction in summer, loose in January–February where the
charge is near zero. Supported roughly, not exactly.

**Reading.** The wholesale price fall, even if every euro of the subsidy had been passed on, does not return the
bill to Spanish buyers: about a third of the saving leaves the Spanish demand base and bilateral energy gets none.
Limits: unit-to-group by the listing's latest owner; retail-owned generic units unresolved; exports sign and
treatment as above; ρ is B3's.

## E. Portugal's plants and the choice of gas controls — rules fixed before running (2026-11-03)

The user asked for three things after the unit-set rerun: look into the Portuguese side, test whether Portuguese
plants were subsidised, and pin down which gas-control set to quote for B3. Documentation search runs as a
background workflow (Spain's RDL 10/2022 and Portugal's counterpart, with a verification pass); results come
separately.

**E1. Were the Portuguese plants subsidised? (declared-cost event, existing data).** The declared-cost
script already carries 7 Portuguese units (Turbogás `RTG*` out): `gas_cap_declared_cost_firm.csv` shows ρ(bid) 0.96
for Portugal (715 unit-days), 0.93 for Spain. New here, `gas_cap_declared_cost_pt.py`: the event statistic J(D)
(median over units of the change in mean log(declared ÷ gross) from the 7 days before D to the 7 days from D)
on Portuguese units alone, for 2022-06-15 against placebo dates 2021-09-08 → 2022-06-07, and the same for Spanish
units. **Rule:** the Portuguese plants count as subsidised if J(2022-06-15) lies below the 2.5th percentile of their
placebo J's and within 0.15 of the J a full pass-through would give. Otherwise they are not shown to be.

**E2. Which control set for B3?** `gas_cap_quantity_b3_spec.py`. (a) Placebo: before the cap there is no subsidy,
so the out-of-sample weekly gap (Xu 2017, treated as capped from 2022-01-01 and from 2022-03-01, r by cross-
validation as in B1 and also r = 0) should not move with gas prices unless Iberian and Italian plants respond to
them differently. Regress it on the weekly MIBGAS price and on the PSV − MIBGAS spread, firm-block bootstrap, 199
draws. **Rule:** controls justified if the 95% interval of the MIBGAS slope excludes zero with the same sign at both
placebo dates; not justified if it includes zero at both; mixed otherwise (report both ρ). (b) The timing
permutation of B3's slope under both controls (45 cyclic shifts), pass if p ≤ 0.05.

### E results (2026-11-03)

**E1, Portuguese plants' declared cost (`gas_cap_declared_cost_pt.py` → `gas_cap_declared_cost_pt.csv`).** 7 Portuguese units
(Lares 1–2, Pego 3–4, Ribatejo 1–3; Turbogás out as before) against 45 Spanish. J(2022-06-15): **Portugal −0.609**
(full pass-through −0.744; placebo 2.5 / 50 / 97.5% = −0.161 / +0.005 / +0.121, min −0.276, 273 dates): **rule met**.
Spain −0.544 (full −0.721; placebo −0.123 / +0.005 / +0.124): outside the placebo range, but 0.177 from full
pass-through, so it misses the rule's closeness leg (0.15) — the closeness criterion is too tight to discriminate
and is not repeated. On the day, the Portuguese median declared term falls from €177.5 (14 June) to €114.6 (15 June)
against a net cost of €105.9, as the Spanish one does. **The Portuguese plants' declared costs responded to the
subsidy exactly as the Spanish ones did, which fits their being covered by the mechanism.** Eligibility itself
still needs the documents (workflow running).

**E2, gas controls (`gas_cap_quantity_b3_spec.py` → `gas_cap_quantity_b3_spec.csv`).** (a) Placebo, out-of-sample
weekly gap before the cap on MIBGAS and on the PSV − MIBGAS spread: no slope excludes zero at either placebo date
(2022-01-01, 24 weeks; 2022-03-01, 15 weeks), r by cross-validation or 0. MIBGAS slope at 2022-01-01: −0.0002
[−0.0016, +0.0008]; at 2022-03-01: −0.0025 [−0.0041, +0.0017]. **Rule: controls not justified.** (b) The timing
permutation under both controls passes (real b −0.456, ρ 0.54; shifted 5th percentile −0.092; p < 1/45).

**Reading.** By the rule the uncontrolled ρ 0.73 is the one to quote, with 0.54 as the sensitivity; the controlled
estimate also survives its own permutation test, so the range does not narrow. **The placebo has little power for
the size that matters**: an MIBGAS slope of −0.0016 per €/MWh over the ~€100/MWh the price rose between the
placebo window and summer 2022 would move the gap by 0.16, against a B3 shift of 0.11 (b × g at b = −0.27,
g = 0.4). So "not justified" is "not shown to be needed", not "shown to be unneeded".
