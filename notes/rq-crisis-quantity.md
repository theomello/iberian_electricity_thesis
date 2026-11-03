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
