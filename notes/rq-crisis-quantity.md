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
  *Corrected 2026-11-05 (`notes/rq-gas-cap-control.md`, part 3):* the controlled ρ is not one number. It is
  0.54–0.85 depending on which gas series is the control (delivery-day or bid-time MIBGAS, PSV), all within noise,
  and no control set is favoured. Quote **0.73 [0.51, 1.03]**, with a central band of **0.5–0.85** and no known
  direction of bias. The euro figures below were computed on 0.55–0.75 and are not recomputed; ρ = 1 is reported
  beside them, and 0.85 lies between, so every net stays negative (break-even ≥ 1.05).
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

### E3. The documents (2026-11-03): what the decrees say, and three corrections to the above

A background workflow read the primary texts, each claim then re-read independently (4 agents, 9 of 10 Spanish and
8 of 9 Portuguese claims verified, one unverifiable: the 2023 extension decree). Sources: RDL 10/2022 (BOE-A-2022-7843);
Decreto-Lei 33/2022 of 14 May 2022 (Diário da República); ERSE Diretiva 11/2022 and its technical note; Commission
decision C(2022) 3942 (SA.102454 Spain, SA.102569 Portugal) and press release IP/22/3550 (8 June 2022).

**Coverage.** Spain, art. 2.1: peninsular gas combined cycles, conventional coal, and gas cogeneration under the
general remuneration modality (regulated CHP excluded). Portugal, DL 33/2022 art. 2(1): gas combined cycles and
market-regime cogeneration; **coal not covered**. **Portuguese plants were inside the mechanism, under their own
decree**; the Spanish RDL names no Portuguese plant. Physical bilateral output gets no compensation in either
(RDL art. 2.2; DL art. 2(2)). Formula, RDL art. 3.1: Y = (PGN − PRGN) / 0.55, zero when PGN < PRGN; 0.55 the assumed
55% efficiency (the 0.55 in the clawback's FMIG is a separate use). Confirms the subsidy used here.

**Who pays.** Spain, art. 7.4: the market operator spreads the cost over all purchasing units of Iberian market
agents in proportion to scheduled energy after the continuous market; art. 7.6 the system operator's leg on energy
at plant busbars. **Portugal, DL art. 5(2): attributable exclusively to Portuguese-area buyers**, each side
settling in its own system. Exempt in both: storage and pumping consumption, ancillary services, and
**energy under fixed-price supply contracts signed before 26 April 2022** (RDL art. 8; DL art. 7), with the exemption
lost on renewal or repricing and the cost phased in for hedged energy. The Commission: the charge starts on 41% of
Spanish and 30% of Portuguese consumption. PVPC users get the cost as a component of the hourly price (art. 13.1,
7.8). **Part of the cost is paid from France-border congestion rents** (art. 14), so buyers pay less than plants
receive. Exports: no article charges or exempts them (checked); whether coupling export units count as purchasing
units is not answered by the text.

**Correction 1: Portuguese buyers did pay.** I wrote that the saving going to Portuguese buyers (22%, €0.70 bn at
ρ 0.73) came at no cost to them. Under DL 33/2022 they paid for the Portuguese plants. The 10 Portuguese units'
subsidy B is **€965 m** (19.5% of B; Spanish units €3,972 m), so Portuguese buyers' bill is up to that, less the
hedged share (30% at the start), against a saving of €0.70 bn. The official Spanish charge, €5.27 bn, lines up with
the **Spanish** plants (54-unit Spanish part 3.97 bn; with coal and the other combined cycles, the 97-unit set net
of the Portuguese units is about 4.9 bn): consistent with each country charging its own buyers for its own
plants, not proven. The 54-unit B in the tables above includes the Portuguese units.

**Correction 2: the free ÷ reference ratio is the hedging exemption, not the spot share.** The free-market charge is
lower because contracts at a fixed price signed before 26 April 2022 are exempt, and the exempt share shrinks as the
contracts expire: the ratio rises from 0.48 (June) to 0.76 (February), as observed. The day-ahead ÷ scheduled
demand share of free-market retailers did not rise (0.51 → 0.43). My earlier reading (a spot share) is withdrawn.
Its group-net numbers stand (they use the official charge and the actual day-ahead purchases), but a free-market
MWh under an exempt contract paid no charge and got no price fall either.

**Correction 3: exports.** "Exports probably did not pay" rested on the group totals reproducing the cost; the
documents do not settle it, and with the congestion-rent financing and the coal and cogeneration plants the cost
total is not pinned down to the unit. Treat exports as unresolved.

Also: the Commission's budget (€8.4 bn: €6.3 bn Spain, €2.1 bn Portugal) is a ceiling to 31 May 2023, not an outturn.
Gas cogeneration under the general modality was eligible in both countries, which is why the cogeneration set
overshoots the charge: only part of it qualified.

## F. The net with Spain and Portugal separated — definition fixed before running (2026-11-03)

After E3 (each country charges its own buyers for its own plants; the price fall is joint). Over the valid hours,
at ρ in {0.55, 0.73, 0.75, 1.00}, for two plant sets (the 54 modelled gas units, and the 97 OMIE-listed gas CCGT
and coal units ∪ the 54), with the same counterfactual re-clear as D (all subsidised units moved up by ρS):
- **Saving by buyer's country**, from the day-ahead buys by category (`gas_cap_group_net.py`): Spanish buyers =
  reference suppliers + free-market retail + generic units + other Spanish + pumping; Portuguese buyers = registry
  country PT; exports / unregistered units reported apart.
- **Spanish bill** = the official ESIOS charge × scheduled demand over all three groups (1908 × 351 + 1909 × 352 +
  1907 × 353). **Portuguese bill**: not observed; bounded above by B_PT = S × cleared MWh of the Portuguese
  plants (the cost to be recovered; congestion rents and phase-in lower it).
- **Net_ES** = saving to Spanish buyers − Spanish bill. **Net_PT** = saving to Portuguese buyers − B_PT (a
  lower bound on the net; the net is at most the saving itself). Also B_ES = S × cleared MWh of the Spanish plants,
  against the Spanish bill (the part of the plants' receipts not charged to Spanish buyers).
No decision rule. Limits as in D: the same ρ for every plant (extrapolated beyond the 54 and across countries),
fixed other offers, bilateral energy gets no saving, exports unresolved.

### F results (2026-11-03)

`scripts/analysis/gas_cap_net_by_country.py [--units panel|ccgt_coal]` → `outputs/tables/gas_cap_net_by_country{,_ccgt_coal}.csv`
(`gas_cap_consumer_saving.py --units ccgt_coal` regenerated so its hourly file carries every ρ). € m, valid hours.

| plant set | ρ | saving to Spanish buyers | Spanish bill (ESIOS) | **net Spain** | saving to Portuguese buyers | Portuguese bill ≤ | **net Portugal ≥** | exports / unregistered |
|---|---|---|---|---|---|---|---|---|
| 54 gas units | 0.55 | 1,579 | 5,427 | **−3,848** | 489 | 965 | −476 | 178 |
| | 0.73 | 2,255 | 5,427 | **−3,172** | 699 | 965 | −266 | 256 |
| | 0.75 | 2,332 | 5,427 | **−3,095** | 722 | 965 | −243 | 265 |
| | 1.00 | 3,278 | 5,427 | **−2,149** | 1,016 | 965 | +51 | 375 |
| 97 gas CCGT + coal | 0.55 | 1,723 | 5,427 | **−3,704** | 536 | 965 | −429 | 195 |
| | 0.73 | 2,483 | 5,427 | **−2,944** | 773 | 965 | −192 | 283 |
| | 0.75 | 2,568 | 5,427 | **−2,858** | 800 | 965 | −165 | 293 |
| | 1.00 | 3,690 | 5,427 | **−1,737** | 1,149 | 965 | +184 | 421 |

Spanish bill = ESIOS 1908 × 351 + 1909 × 352 + 1907 × 353 (the direct consumers add €160 m to the earlier €5,266 m).
Subsidy on the plants: Portuguese plants €965 m (8,149 GWh, same in both sets); Spanish plants €3,972 m (54 set) and
€4,905 m (97 set), so the Spanish bill is 1.37 and 1.11 times what the Spanish plants earn in the day-ahead market
in these sets: the rest is intraday and balancing receipts and plants outside the sets (cogeneration under the
general regime), the congestion rents pull the other way.

**Reading.**
- **Spanish buyers lose €2.9–3.8 bn at ρ 0.55–0.75 and still €1.7–2.1 bn at full pass-through** (ρ = 1). Break-even
  would need ρ of roughly 1.4–1.5, above any admissible value. Separating the countries makes Spain's net **about €0.7–1.2 bn
  worse** than the combined −1.9 to −3.0 bn: a third of the price fall goes to buyers who do not pay the Spanish charge.
- **Portuguese buyers are roughly at break-even to slightly behind:** −€0.2 to −0.5 bn at ρ 0.55–0.75 on the
  worst-case bill (the whole subsidy to the Portuguese plants), about zero at ρ = 1; the true bill is lower
  (congestion rents, phase-in), so these are lower bounds.
- Exports / unregistered units take €0.2–0.4 bn; whether they paid is unresolved (E3).
- The joint price fall comes from every plant's pass-through, so "Spain's saving" is what Spanish buyers received
  of a fall that the Portuguese plants also helped cause; no split by the plants' own country is attempted.

## G. Ideas for sizing B3 (2026-11-03, proposed, not run)

The interval [0.51, 1.03] is limited by about a dozen Iberian firms as bootstrap clusters; none of these adds firms.
Ranked by what each buys:
1. **Specification curve.** Report ρ over every defensible choice (run10 / run20 / run50, margin €20 / €50 / all hours, r = 0…5,
   gas controls on or off, 54 or 97 units, window end) as one distribution, and quote its range as the size
   uncertainty instead of picking. Cheap; makes the 0.54–0.73 spread a result.
2. **Paired test against the declared costs.** The same units give a declared-cost ρ (≈ 0.95) and an offer ρ (B3).
   Estimate the difference with the firm-block bootstrap on the pairs: common noise drops out, and it turns the
   "offers pass through less than declared costs" tension into a test.
3. **Daily dose.** g_w averages away day-to-day swings in S inside a week (S moved from 70 to 140 within June 2022).
   A unit-day Xu panel with g_ud (permutation over days) gives the slope more usable variation; inference still
   clusters on firms, so it sharpens the estimate more than the interval.
4. **Linear-in-S price outcome.** Offer price at p25 / p50 / p75 minus cost, ATT in € per € of S, weekly, with
   the permutation and gas controls. Natural units and continuous. The earlier price designs failed their
   pre-cap checks, so it needs the placebo first.
5. **Regulatory steps in the reference price** (PRGN 40 → 45 → 50 → 55 on 1 January, 1 February, 1 March 2023): S falls
   by about €9 each time at a given gas price, independent of plants and market. A check on the declared-cost ρ, not
   on B3; the steps are small.
Not worth it: more pre-cap weeks (the offer limits changed on 2021-07-07), more small plants (efficiency unknown),
a second control country (Great Britain failed).

## G1. Specification curve and paired test — rules fixed before running (2026-11-03)

User asked to resume the sizing ideas (1 and 2 of section G). Nothing below has been run.

**G1a. Specification curve** (`gas_cap_quantity_b3_curve.py`). Point estimates of B3's ρ = 1 + b over a grid, no bootstrap
(a bootstrap per cell would multiply cost 199-fold and the grid is the uncertainty being reported here):
- margin for the predicted in-money condition: €20, €50 (main), €100, every hour; the B1 ends are recomputed for each
  (`gas_cap_quantity_b1.ends`, run20 only);
- r = 0 … 5 (Xu 2017 factors; the CV choice is one of them);
- gas controls: none / MIBGAS / MIBGAS + PSV − MIBGAS spread;
- time trend: without / with;
- window end: 2023-06-30 (main) / 2023-02-25 (last week with a subsidy).
Not in the grid, because the stored panel carries only `run20` and the 54 modelled units: run10 / run50 thresholds and the
97-unit set. Say so when quoting. For each cell also the timing permutation p (cyclic shifts, as in the B3 checks).
Reading, fixed now: no pass/fail. Quote (i) the range of the middle half of cells (25th–75th percentile) as the size
uncertainty across specifications, (ii) the full min–max, (iii) the share of cells whose ρ lies inside B3's bootstrap
interval [0.51, 1.03], (iv) the share with permutation p ≤ 0.05, and (v) by axis, the range of cell medians, to show which
choice moves ρ most. If the middle half lies wholly inside [0.51, 1.03] the bootstrap interval is the binding uncertainty;
if it spills outside, specification uncertainty is at least as large and must be quoted with it.

**G1b. Paired test against the declared costs** (`gas_cap_quantity_b3_paired.py`). One firm-block bootstrap, 199 draws,
resampling firms within country as in B3. In each draw: ρ_offer = 1 + b of B3 (r by CV on the full sample, no controls,
the ATT re-estimated on the draw, g_w fixed); ρ_decl = the median over the drawn Iberian firms' unit-days with S ≥ €20,
2022-06-15 → 2023-02-25, of `rho_bid` from `gas_cap_declared_cost.panel()` (a firm drawn twice counts twice). d = ρ_decl − ρ_offer.
Report mean d, the 95% percentile interval and the share of draws with d > 0. Rule: offers pass through less than declared
costs only if the interval of d lies wholly above 0; wholly below 0 the reverse; otherwise no difference is detectable.
Caveats stated in advance: the declared sample is 50 units in 11 firms, B3's 54 units in 12; the two ρ's are not the same
object (declared term of the minimum-income condition vs the share of capacity offered near cost), so a difference can
also be a difference in what is measured.

### G1 results (2026-11-03)

**Deviation from the rule above:** the €100 margin could not be built (no Iberian unit-hours more than €100 in the money in the
8 weeks before the cap, so the reference curve for the ends is empty). Grid run: margin €20 / €50 / every hour × r 0…5 ×
controls (none, MIBGAS, both) × trend × window end = 216 cells. The main cell (€50, r = 0, no controls, no trend, to
2023-06-30) reproduces B3: ρ 0.726, permutation p 0.000, 46 weeks.

**G1a. Specification curve.** All 216 cells: ρ min −0.25, 25% 0.32, median 0.70, 75% 0.87, max 1.38. 53% of cells inside
B3's bootstrap interval [0.51, 1.03]; 71% have permutation p ≤ 0.05. By the reading rule the middle half spills below 0.51, so
specification uncertainty is at least as large as the bootstrap interval and both must be quoted.
Median ρ (25–75%) by axis:
- margin: €20 0.30 (0.10–0.73); **€50 0.56 (0.37–0.68)**; every hour 0.96 (0.78–1.07);
- controls: none 0.79 (0.72–1.01); MIBGAS 0.48 (0.25–0.78); both 0.45 (0.23–0.75);
- r: 0.58–0.81 across 0…5; trend and window end: 0.67–0.71, they barely move it.
Margin × controls (median ρ; share with permutation p ≤ 0.05): €20 none 0.74 (58%), MIBGAS 0.16 (92%), both 0.12 (92%);
€50 none 0.73 (100%), MIBGAS 0.45 (100%), both 0.41 (100%); every hour none 1.07 (0%), MIBGAS 0.83 (46%), both 0.80 (50%).
At the main margin (€50, 72 cells): min −0.02, quartiles 0.37 / 0.56 / 0.68, max 0.79; every cell passes the permutation; 57%
inside [0.51, 1.03]. Main margin, no controls, no trend, to June 2023, by r: 0.73, 0.70, 0.69, 0.63, 0.54, 0.57 for r = 0…5.
Reading: the choices that move ρ are the margin and whether gas-price controls are in; r, trend and window end do not.
The cells are not equally credible. Every-hour fails the permutation without controls (it failed B3's checks too) and €20 was
never run through B1's power check. E2 found that the placebo does not justify the gas controls (low power), yet two thirds of
the cells carry them. So the curve widens the honest range at the main margin to about 0.4–0.75 (0.73 without controls,
0.41–0.45 with them), not to the full 0.1–1.1.

**G1b. Paired test.** Main sample, r = 0, 199 draws; 8 of the 10 Iberian firms declare a term. Offer ρ 0.73 (95% [0.53, 1.02]),
declared ρ 0.91 ([0.86, 0.96]), d = declared − offer = +0.19 (mean +0.16, 95% [−0.12, +0.38]), 87% of draws d > 0, correlation
of the two across draws +0.29. Rule: no difference detectable. Pairing removed little noise (the correlation is small); the
interval of d is almost the offer interval, since the declared ρ is much tighter. Offers sit below declared costs by a point
estimate, not by a significant margin.

## G2. Daily dose — rules fixed before running (2026-11-03)

Idea 3 of section G, chosen by the user. B3 averages the subsidy over a week, but S moves a lot inside a week (about €70 to
€140 within June 2022). A unit-day panel gives the slope that variation.
- **Outcome:** per unit and day, the mean of `run20` over the unit's predicted in-money hours that day (main margin €50, same
  sample as B1/B3: essential units out, cost defined). **Dose:** g_d = mean over units of the day's full − none gap, from the
  B1 ends computed by day instead of by week (same reference curve, same K); the weekly code is reused with `by="date"`.
- **Estimator:** Xu (2017) `gsc` on the unit × day matrix, pre = days before 2022-06-15, r by cross-validation on the pre days.
  Unit rule as in the weekly matrix: at most 30% of days missing (50% if fewer than 25 Iberian units pass; stop below 25).
  Then ATT_d = a + b·g_d over post-cap days carrying g_d, ρ = 1 + b.
- **Inference:** firm block bootstrap within country, 199 draws, ATT re-estimated each draw (whole firm series resampled, so
  serial correlation within a firm is kept); timing permutation over cyclic day shifts, pass if one-sided p ≤ 0.05; with a
  linear trend, ρ must stay inside the main interval; gas controls (daily MIBGAS, daily PSV − MIBGAS) reported, not decisive.
- **Reading, fixed now:** the daily dose sharpens the estimate only if the permutation passes AND the 95% interval is narrower
  than the weekly [0.51, 1.03] (width 0.52). Report the point estimate beside the weekly 0.73; if they differ, say so and do
  not choose between them. Stop if the permutation fails or fewer than 25 Iberian units survive the missing-days rule.

### G2 results (2026-11-03)

Unit × day panel, main margin: 41 Iberian and 39 Italian units × 638 days after the missing-days rule (the 30% threshold left
fewer than 25 Iberian units, so the 50% fallback applied; 38% of cells missing), 10 Iberian and 10 Italian firms. 207 post-cap
days carry g_d (182 with g > 0, max 0.671). Xu CV r = 3.
- ρ = 0.82, 95% firm-block bootstrap [0.63, 1.01], width 0.38 (weekly B3: 0.73 [0.51, 1.03], width 0.52).
- Timing permutation over 206 day shifts: shifted 5th percentile −0.201, **p 0.117 → fails**.
- With a linear trend ρ 0.96 [0.84, 1.09], inside the main interval. Gas controls: MIBGAS 0.84, spread 0.87, both 0.89.
- Rule: the daily dose does NOT sharpen the estimate (permutation fails). Stop; the narrower interval is not to be quoted.
Why it does not carry over: the daily panel keeps fewer units (41 against 49 Iberian) and 38% of its cells are missing, since a
unit has an in-money hour on only some days; the day-level outcome is noisy and the daily dose is mostly the same slow path of
S as the weekly one, so the extra variation does not identify the slope against shifted timing. The point estimate (0.82)
sits above the weekly 0.73 and the controls move it little, unlike in the weekly curve; both are inside each other's
intervals, so they are not told apart. `ends()` in `gas_cap_quantity_b1.py` gained a `by` argument (default "w", unchanged).

## H. The counterfactual: what the factors do (2026-11-03)

### H1. Descriptive diagnostics of the factor model (`gas_cap_quantity_factors.py`, run 2026-11-03)
Weekly run20 matrices, 92 weeks (38 pre-cap). In-money main sample: 49 Iberian, 44 Italian units, 16% of cells missing.
Every-hour sample: 51 Iberian, 53 Italian units, 9% missing.
- **Bai & Ng's IC_p2 on the Italian matrix falls monotonically to k_max = 8 in both samples**: uninformative, as on the earlier
  markup outcome. Xu's cross-validation is the only guide, and it is flat: in-money MSE 0.0202 (r = 0) against 0.0205–0.0218
  for r = 1…5, best r = 0; every hour 0.0160 (r = 0), 0.0155, **0.0148 (r = 2)**, 0.0153, 0.0155, 0.0154 (7% below r = 0).
- Share of the Italian two-way residual variance, factors 1–6: in-money 28 / 15 / 11 / 9 / 7 / 6%; every hour 19 / 16 / 12 / 11 /
  7 / 6%. No clean elbow.
- **The factors carry the gas path.** In-money: factors 3 and 4 correlate −0.35 / −0.34 with weekly MIBGAS and −0.16 / −0.39 with
  the dose. Every hour: factor 2, the one cross-validation adds at r = 2, correlates −0.63 with MIBGAS, −0.67 with PSV and −0.55
  with the dose.
- **Iberian pre-cap R² of the counterfactual, by r = 0…5: in-money −0.35, −0.27, −0.20, −0.06, −0.00, +0.03; every hour −0.63,
  −0.36, −0.19, −0.13, −0.05, +0.03.** At r = 0 the Italian week path adds noise to an Iberian plant (negative R² = worse than the
  plant's own mean): Italy's common weekly movement does not describe Iberian offers in the 38 pre-cap weeks, and even five
  factors reach only 0.03.
- Mean gap after the subsidy ends (should be about 0): in-money +0.13 to +0.18 at every r (the drift B3's intercept absorbs);
  every hour −0.02 to −0.06.
- ρ by r: in-money 0.73, 0.70, 0.69, 0.63, 0.54, 0.57 (falls as factors 3 and 4, the gas-correlated ones, enter); every hour 1.27,
  1.38, 1.18, 1.18, 1.16, 1.16 (above 1 at every r).
Reading: the control group is a weak counterfactual for the level path, and the factors that improve it are gas-price factors
whose Iberian loadings are estimated on pre-cap gas prices and extrapolated to the 2022 spike. That is the channel by which
ρ moves with r. Whether it is bias or information is what H2 tests.

### H2. Recovery simulation — rules fixed before running (`gas_cap_quantity_recovery.py`)
Question: if the true pass-through is known, does the B3 estimator (gsc at the cross-validated r̂, and at each fixed r) return it,
and does ρ̂ fall as r grows when nothing in the data-generating process makes it fall?
Data-generating process, built from the real in-money matrix (same missing cells, same g_w, same units):
1. Italian block: EM fit of rank k (k = true r ∈ {0, 2}) gives a_i, b_w, F_w; Italian units get their fitted values plus
   independent normal noise with each unit's own residual sd.
2. Iberian counterfactual: gsc's imputation at rank k (intercept and loadings from pre-cap weeks).
   **Scenario S1** Iberia follows Italy's week path exactly (the model's own assumption). **Scenario S2** Iberia also has its own
   weekly path η_w added: pre-cap η is the Iberian cross-unit mean's residual from the Italian path (calibrated to the observed
   pre-cap fit); post-cap η is a moving-block resample (4-week blocks) of the demeaned pre-cap η, independent of the dose.
3. Planted effect on Iberian post-cap weeks with g_w observed: (ρ0 − 1)·g_w, plus a constant drift +0.13 (as observed), ρ0 ∈ {0.5, 1.0}.
4. Independent normal noise with each unit's pre-cap residual sd. Serial correlation within unit is NOT simulated, so spread
   (not bias) is optimistic.
Grid: true r {0, 2} × scenario {S1, S2} × ρ0 {0.5, 1.0}; reps per cell to be set after timing one (target 100).
Per replication: r̂ by Xu's CV; ρ̂ = 1 + b of B3 (no controls, no trend) at r̂ and at each fixed r = 0…5.
Reported per cell: mean, sd and RMSE of ρ̂ − ρ0 by estimator; share of replications where r̂ = true r; and the slope of mean ρ̂ on r.
Reading, fixed now: recovery is adequate if at the CV-chosen r̂ the mean |ρ̂ − ρ0| ≤ 0.10 in every cell. If mean ρ̂ falls with r by
more than 0.10 between r = 0 and r = 5 in a cell where truth is not confounded, the fall is the estimator's, and the real-data
fall (0.73 → 0.57) cannot be read as information; if mean ρ̂ is flat in r in all cells, the real fall comes from structure in
the data (factors correlated with the gas path and the dose). The DGP uses the estimator's own model class, so this checks the
estimator, not the model assumption. A confounded scenario (η correlated with the dose) is not run here.

### H3. Idea for later (not run): an hour-of-day counterfactual
Match Iberian and Italian plants on hour of day (unit × hour-of-day × week cells, or the 24 hourly profiles as extra factors),
since offers differ between night and midday. The weekly Italian path has negative Iberian pre-cap R² (H1); this may track the
Iberian level better. To build and test (pre-cap R², cross-validation, the permutation) before any estimate. User agreed to do it later.

### H2 results (2026-11-03; 8 cells × 100 draws, 44 minutes on 4 workers)
Bias of ρ̂ − ρ0 at Xu's cross-validated r̂ (and sd of ρ̂ across draws):
| true r | scenario | ρ0 | bias at r̂ | sd | share r̂ = true r | bias at r = 0 / r = 5 |
|---|---|---|---|---|---|---|
| 0 | S1 | 0.5 | +0.007 | 0.026 | 100% | +0.007 / +0.003 |
| 0 | S1 | 1.0 | +0.001 | 0.026 | 100% | +0.001 / +0.003 |
| 0 | S2 | 0.5 | −0.004 | 0.057 | 97% | −0.004 / −0.004 |
| 0 | S2 | 1.0 | +0.003 | 0.064 | 98% | +0.002 / +0.001 |
| 2 | S1 | 0.5 | +0.027 | 0.042 | 48% | +0.040 / +0.016 |
| 2 | S1 | 1.0 | +0.024 | 0.044 | 59% | +0.041 / +0.020 |
| 2 | S2 | 0.5 | +0.020 | 0.078 | 14% | +0.027 / −0.000 |
| 2 | S2 | 1.0 | +0.017 | 0.074 | 10% | +0.019 / −0.000 |
- **Recovery adequate by the rule**: mean |bias| ≤ 0.03 at r̂ in every cell (rule: ≤ 0.10).
- **No mechanical fall with r**: the slope of mean ρ̂ on r is −0.004 or closer to zero in every cell; the largest difference between
  r = 0 and r = 5 is 0.04 (true r = 2, S1). The rule's reading: flat in r where nothing is confounded, so the real fall (0.73 → 0.57,
  −0.16) is not the estimator's doing; it comes from structure in the data that is related to the dose (the gas-correlated factors,
  H1). The simulation cannot say whether the lower ρ is bias removed or bias added; that needs the confounded scenario.
- **Cross-validation under-picks**: with two true factors it finds r = 2 in 48–59% of draws under S1 and only 10–14% under S2
  (Iberia has its own weekly path), so the cross-validated r = 0 in the real data is weak evidence that no factors exist. With
  nothing confounded this costs ≤ 0.03 of bias.
- **The spread is far too small** (sd 0.03–0.08 against a real bootstrap width of 0.52): no serial correlation and no firm
  clustering were simulated. Inference rests on the firm bootstrap, not on these sds.
- Not run: a scenario with η correlated with the dose (the case that could make ρ̂ depend on r).

### H4. Recovery simulation with a dose-correlated confound — rules fixed before running (`gas_cap_quantity_recovery_confound.py`)
Question: if Iberian plants respond to the gas price in a way Italy's matrix does not carry, how far does B3's ρ̂ move at r = 0 and
at the cross-validated r̂, and do added factors repair it? This is the one case where ρ̂ can depend on r (H2 found no such
dependence without a confound).
DGP as H2, scenario S1 (Iberia follows Italy's week path, η = 0) plus an Iberian-only gas response in every week:
κ·z_w, with z_w the weekly MIBGAS price standardised by its pre-cap mean and sd (so it runs well above 1 after the cap),
κ = sign × sqrt(share × variance of the Iberian pre-cap cross-unit residual path η_pre). Grid: true r {0, 2} × sign {+, −} ×
share 0.5 × ρ0 {0.5, 1.0} = 8 cells; reps set after timing (target ≤ 60 per cell). The correlation of z_w with the dose g_w over post
weeks is printed. Same planted effect (ρ0 − 1)·g_w, drift +0.13, noise as H2.
Reported per cell: mean bias of ρ̂ − ρ0 at r = 0, at r̂ and at r = 5, and the share of r̂ = true r.
Reading, fixed now: the weekly estimator is vulnerable to a gas-correlated Iberian response of this size if |bias at r = 0| ≥ 0.10 in any
cell. Factors repair it if |bias at r̂| < 0.10 where |bias at r = 0| ≥ 0.10. The real pattern (ρ falls 0.16 from r = 0 to r = 5) is
matched by a cell if its mean ρ̂ falls by ≥ 0.10 over the same range; the sign of κ in such a cell says which way the real r = 0 estimate
would be biased if that scenario were true. This brackets the problem; it does not identify which scenario holds.
Addition made after the one timing cell (k = 0, sign +, share 0.5, ρ0 0.5, 10 draws; not part of the results): the confound was so
strong there (bias of ρ̂ at r = 0 of +0.57, with the weekly MIBGAS price correlated 0.98 with the dose over the post-cap weeks) that share 0.5 cannot
bracket the size. Cells with share 0.05 are added, so the grid is true r {0, 2} × sign {+, −} × share {0.5, 0.05} × ρ0 {0.5, 1.0} = 16
cells. Rules unchanged. Timing: 2 s a draw with one thread per worker (H2's 44 minutes was mostly threads fighting for four cores).

### H4 results (2026-11-03; 16 cells × 60 draws, about 6 minutes)
Mean bias of ρ̂ − ρ0 (identical for ρ0 0.5 and 1.0 to within 0.02, so one row per cell); weekly MIBGAS and the dose correlate **0.978** over the post-cap weeks.
| true r | κ sign | share | bias at r = 0 | at r̂ | at r = 5 | share r̂ = true r |
|---|---|---|---|---|---|---|
| 0 | + | 0.05 | +0.17 / +0.18 | +0.17 / +0.18 | +0.17 / +0.18 | 98–100% |
| 0 | + | 0.50 | +0.56 | +0.56 | +0.56 | 97–98% |
| 0 | − | 0.05 | −0.18 | −0.18 | −0.18 | 100% |
| 0 | − | 0.50 | −0.55 | −0.55 | −0.55 | 97–100% |
| 2 | + | 0.05 | +0.21 | +0.20 | +0.19–0.21 | 48–50% |
| 2 | + | 0.50 | +0.58–0.59 | +0.59–0.60 | +0.59 | 35–38% |
| 2 | − | 0.05 | −0.14 | −0.15 / −0.16 | −0.17 | 45–50% |
| 2 | − | 0.50 | −0.51 | −0.53 | −0.56 | 28–30% |
- **Rule readings:** the weekly estimator IS vulnerable (|bias at r = 0| ≥ 0.10 in all 16 cells, 0.13–0.59); factors do NOT repair it
  (|bias at r̂| ≥ 0.15 in every cell, and at r = 5 as large as at r = 0); no cell reproduces the real fall of 0.16 from r = 0 to r = 5 (the
  largest fall is 0.05). The sign of the bias follows the sign of the Iberian gas response.
- **Size of the weak confound.** Share 0.05 means κ = 0.017 of the run20 share per pre-cap sd of MIBGAS; the weekly gas price reaches 5.8 pre-cap
  sds in the summer of 2022, so the Iberian share is shifted by at most 0.10 (mean Iberian run20 0.69 before the cap; the dose g peaks at
  0.625, mean 0.19 post-cap). A gas response of 0.10 at the peak biases ρ̂ by about 0.17.
- **What it means.** An Iberian-only response to the gas price is almost the same signal as the subsidy, and Italy's factors, which are
  estimated on Italian plants, cannot remove it. So the weekly ρ is exposed to exactly the confound the gas controls address, in either
  direction, by a few tenths. The factors' fall with r in the real data is not this: it needs a gas-linked factor shared by Italian and
  Iberian plants whose Iberian loading, estimated on pre-cap gas prices, extrapolates differently after the cap (H1). Not simulated.
- **Not run:** the same confound with a gas-price control in the regression (does it repair the bias, and at what cost in spread; does it
  bias the unconfounded worlds?). That decides between ρ = 0.73 without and 0.41–0.45 with the controls.

### H5. Does a gas-price control repair the confounded worlds? — rules fixed before running (`gas_cap_quantity_recovery_control.py`)
H4 left open whether adding the weekly gas price to B3's regression repairs the bias a gas-linked Iberian response causes, and what it
costs. Same data-generating process as H4 (S1 plus κ·z_w), grid true r {0, 2} × [sign {+, −} × share {0.5, 0.05}, plus share 0 (no confound)]
× ρ0 {0.5, 1.0} = 20 cells, 60 draws each. Per draw: ρ̂ = 1 + b of ATT_w = a + b·g_w, without and with z_w (the standardised weekly MIBGAS) as a regressor,
at Xu's r̂ and at fixed r = 0…5.
Reading, fixed now:
- **Repairs** the confound if |bias with the control at r̂| < 0.10 in every share 0.05 and 0.5 cell (the uncontrolled bias is ≥ 0.10 there, H4).
- **Harmless** where nothing is confounded if |bias with the control at r̂| ≤ 0.05 in every share-0 cell.
- **Cost:** report the ratio of the spread of ρ̂ with the control to without it, and the RMSE of both, per cell; the control is preferred in a
  cell if its RMSE is lower.
- If it repairs and is harmless, the uncontrolled 0.73 cannot be preferred without an argument that Iberian offers do not respond to the gas
  price independently of the subsidy, and the controlled value (0.41–0.45 in the curve, G1) becomes the better-supported centre. If it repairs
  but its RMSE is higher in the share-0 cells, report both. If it does not repair, controls give no protection.
Limits stated in advance: the simulated confound is exactly linear in the controlled variable, which favours the control; a real response
(offers relative to cost, kinked at the cap) need not be linear in MIBGAS. A control that works here is necessary, not sufficient.

### H5 results (2026-11-03; 20 cells × 60 draws, about 10 minutes)
Mean bias of ρ̂ − ρ0 at r̂, uncontrolled (u) and with the weekly MIBGAS control (c); sd across draws; ranges over the two ρ0 and the two signs.
| world | bias u | bias c | sd u | sd c | sd ratio | RMSE u | RMSE c |
|---|---|---|---|---|---|---|---|
| true r 0, no confound | 0.00 | +0.005 / +0.007 | 0.03 | 0.12–0.13 | 4.4–4.7 | 0.03 | 0.12–0.13 |
| true r 2, no confound | +0.02 | +0.003 / +0.018 | 0.04 | 0.12–0.13 | 3.0–3.7 | 0.04 | 0.11–0.13 |
| true r 0, share 0.05 | ±0.17–0.18 | −0.03 … +0.02 | 0.03 | 0.12–0.15 | 3.9–5.7 | 0.17–0.19 | 0.12–0.15 |
| true r 0, share 0.5 | ±0.55–0.56 | −0.01 … −0.00 | 0.02–0.03 | 0.12–0.14 | 3.9–5.8 | 0.55–0.56 | 0.12–0.14 |
| true r 2, share 0.05 | ±0.15–0.21 | −0.03 … +0.04 | 0.04–0.05 | 0.11–0.13 | 2.4–2.9 | 0.16–0.21 | 0.11–0.13 |
| true r 2, share 0.5 | ±0.54–0.59 | −0.04 … +0.04 | 0.05 | 0.13–0.15 | 2.6–3.0 | 0.54–0.60 | 0.14–0.15 |
- **Rules:** the control repairs the confound (largest |bias c| 0.044 in any confounded cell, rule < 0.10) and is harmless where nothing is
  confounded (largest |bias c| 0.018, rule ≤ 0.05). **Cost:** the spread of ρ̂ is 2.4–5.8 times larger (sd 0.11–0.15 against 0.02–0.05), because
  the gas price and the dose correlate 0.98; the control's RMSE is lower in every confounded cell and higher (0.11–0.13 against 0.03–0.04) in the
  unconfounded ones. Two clauses of the rule fired together (repairs and harmless: the uncontrolled estimate cannot be preferred without an
  argument; repairs but higher RMSE where nothing is confounded: report both) — applied here as: report both.
- **Applied to the real estimates** (main specification, r = 0, `gas_cap_quantity_b3_checks.csv`): without controls 0.73; MIBGAS 0.58; MIBGAS and the
  PSV − MIBGAS spread 0.54; the permutation holds with each. The gap, 0.15–0.19, is about the bias a weak positive Iberian gas response (share 0.05) would
  put into the uncontrolled estimate (+0.17–0.18), and about one to one and a half controlled sds (0.12–0.15), so the data cannot tell the two apart.
- **Reading:** the controlled estimate is unbiased in every simulated world, the uncontrolled only if Iberian offers do not respond to the gas price
  apart from the subsidy. Quoting 0.73 alone rests on that assumption. Limits: the simulated confound is exactly linear in MIBGAS, which favours the
  control. The real firm-block bootstrap interval WITH the controls has not been computed.

### H6. Bootstrap of B3 with the gas controls — rules fixed before running (`gas_cap_quantity_b3_boot_controls.py`)
Firm-block bootstrap within country as B3 (199 draws, seed as B3, ATT re-estimated each draw, g_w fixed, r = 0 as chosen by cross-validation on the
full sample). In each draw ρ̂ is computed without controls, with MIBGAS, and with MIBGAS and the PSV − MIBGAS spread; the same draws serve all three.
Report each version's point estimate and 95% percentile interval, and the contrast d = ρ_uncontrolled − ρ_controlled (both controls) per draw:
its mean and 95% interval. Rule, fixed now: an Iberian gas response apart from the subsidy is detectable only if the 95% interval of d lies wholly
above 0 or wholly below 0; otherwise it is not detectable and the two estimates are quoted together. A controlled interval wider than the uncontrolled
one is expected (H5); report the ratio of widths.

### H6 results (2026-11-03; 199 draws, 10 Iberian and 12 Italian firms, r = 0)
| version | point ρ | bootstrap mean | 95% interval | width |
|---|---|---|---|---|
| no control | 0.726 | 0.732 | [0.510, 1.031] | 0.52 |
| MIBGAS | 0.583 | 0.560 | [0.118, 0.941] | 0.82 |
| MIBGAS + spread | 0.544 | 0.527 | [0.097, 0.872] | 0.78 |
| contrast d = none − both | +0.182 | +0.206 | [−0.119, +0.584] | 0.70 |
Rule: d's interval includes 0, so a gas response apart from the subsidy is **not detectable**; quote both. Widths: both-controls / none 1.49,
MIBGAS / none 1.58 (H5's simulated spread ratio of 2.4–5.8 overstates it: the simulation had no firm clustering, which dominates the real interval).
Reading: the controlled interval [0.10, 0.87] contains the uncontrolled point and the uncontrolled interval [0.51, 1.03] contains the controlled
point; they overlap on 0.51–0.87. Full pass-through (ρ = 1) is inside the uncontrolled interval and outside the controlled one; no pass-through
(ρ = 0) is outside both, just. The break-even ρ of the net (Spain 1.4–1.5; Iberia with both bills about 1.05–1.1) lies above both intervals, so the
negative net does not depend on which is quoted. Quoting range for the paper: 0.5–0.75 as the central band, with 0.10–1.03 as the union of the two 95% intervals.
*Corrected 2026-11-05:* the central band is **0.5–0.85**, not 0.5–0.75: with bid-time MIBGAS or PSV as the control, ρ is
0.72–0.85 (`notes/rq-gas-cap-control.md`, part 3). The union of the intervals widens to 0.10–1.21. No direction of bias is established.

### H7. Hour-of-day counterfactual — rules fixed before running (user chose it, 2026-11-03; `gas_cap_quantity_hod_fit.py`, stage 2 later)
Why: H1 found Italy's weekly path adds noise to an Iberian plant before the cap (R² −0.35 at r = 0); offers at night and at midday behave differently,
so a week effect averaged over all hours may be the wrong control. Idea: match Iberian and Italian plants within the same hour-of-day block.
**Blocks:** four six-hour blocks of the local delivery hour (periods 1–6, 7–12, 13–18, 19–24; quarter-hours in 2025 are not in the window). One matrix per block:
rows units, columns weeks, the weekly mean of run20 over the unit's predicted in-money hours in that block (main margin €50, essential units out, cost defined);
same unit rule as `matrix()` (≤ 30% of weeks missing, 50% fallback, at least 25 Iberian units, else the block is dropped and said so). Each block gets its own
Italian week effect and factors (`em_factor` on that block's Italian rows).
**Stage 1 (diagnostic only; nothing about ρ is estimated):** for each block and r = 0…5, the Iberian pre-cap R² of the counterfactual (the H1 definition),
Xu's cross-validation error, and the unit counts; next to the baseline (all hours pooled, H1: −0.35, −0.27, −0.20, −0.06, 0.00, +0.03).
**Rule for stage 2, fixed now:** go on to estimate ρ only if at r = 0 the median across the surviving blocks of the pre-cap R² exceeds the baseline's
(−0.35) by at least 0.15 AND at least three of four blocks improve on it. Otherwise stop: matching on the hour of day does not make the Italian path track the
Iberian level. If it passes, stage 2 (rules to be written into this note before it runs, not before): the dose by block (`ends` by block), ATT_{w,block}
on g_{w,block} with block intercepts, ρ = 1 + b, timing permutation shifting weeks jointly across blocks, firm-block bootstrap, and the gas-control version.

### H7 stage 1 results (2026-11-03; no ρ estimated)
Main sample (predicted in-money hours, margin €50): the night (1–6) and afternoon (13–18) blocks are **dropped** — fewer than 25 Iberian gas units have
enough in-money weeks there (cheap hours are out of the money at night and at midday). Surviving blocks, Iberian pre-cap R² at r = 0 / best r by cross-validation:
7–12: −0.22 (r = 1; r = 4 reaches +0.16); 19–24: −1.18 (r = 2). Pooled baseline −0.35. Median across the two blocks −0.70, one of two improves.
**Rule: STOP.** Added after the stop, diagnostic only and outside the rule (every hour, no in-money condition, all four blocks kept): R² at r = 0 pooled −0.63;
blocks 1–6 −1.23, 7–12 −0.24, 13–18 −1.32, 19–24 −0.90; median −1.06, one of four improves; the same STOP.
Reading: matching on the hour of day does not make the Italian path track the Iberian level; the morning ramp (7–12) is the only block that improves and
the others are worse (fewer hours per cell mean noisier weekly means on both sides). The weak tracking is not hour-of-day mixing; Iberian offers are driven by
something Italy's common path does not carry (the minimum-load, near-cost and withholding blocks of `rq-gas-cap-conduct.md`). Stage 2 is not run.
Next candidate if the counterfactual is to be improved: a within-Iberia prediction of run20 from conditions known before the auction (gas price relative to cost,
residual demand, wind and solar forecasts), fitted before the cap and extrapolated, with Italy kept as a check rather than the control. Not built.

## I. Open questions closed or narrowed (2026-11-03)

### I1. Did exports pay the charge? (decree text, `papers/BOE_RDL_10_2022_consolidado.pdf`; indicators 10406–10408)
- Art. 7.4: the market operator's settlement is distributed "entre todas las unidades de adquisición de los agentes del mercado ibérico", pro rata to the
  energy scheduled after the continuous market. Art. 7.7 excludes storage and pumping units, ancillary-service units and hedged energy (art. 8); **no article
  mentions exports**. The decree's own rule on offer units (the OMIE rules it amends) defines import and export units as *"unidades externas al sistema ibérico"*, one
  per agent and border (France, Andorra, Morocco), and the France coupling flow appears in the bids only as the pseudo-unit `MIEU`, which is not an agent's purchase
  unit. Art. 12 spends extra congestion rents on the France border to reduce the total cost. So the text neither charges nor exempts exports; a plausible reading is
  that coupling exports (France) were not charged and that exports by Iberian agents to Andorra and Morocco may have been.
- ESIOS 10406 / 10408 do NOT help: their monthly values (27.5, 66.9, 88.8, 65.0, 22.5, 7.1, 32.2, 2.9, −0.7 for 2022-06 → 2023-02) equal the monthly mean of the hourly
  1907 component (43.2, 55.9, 81.8, 61.3, 27.8, 3.9, 26.8, 1.4, −1.1), so they are €/MWh prices, not euro totals, and cannot pin down the charged base.
- **It does not matter for the Spanish net.** The Spanish bill is what Spanish buyers were charged (ESIOS price × their scheduled demand, €5.43 bn), observed whoever
  else paid. Whether exporters also paid only changes the exporters' own net (saving of €0.2–0.4 bn less any charge), not Spain's or Portugal's. It would matter if the
  total were fixed and shared (it is not read that way here). Status: unresolved in law, immaterial for the headline.

### I2. The Portuguese bill (web search 2026-11-03; ERSE's clarification page unreadable as fetched)
- No source found with a euro figure for the cost charged to Portuguese buyers. The Portuguese government reports a "benefit" of €570 m from entry into force to 31 January 2023
  (Lusa, 8 March 2023; market price reduction €43.78/MWh) and DGEG publishes "custo médio do ajustamento" and "benefício líquido" separately (Observador, 10 August 2022),
  so the figure is probably net of the average adjustment cost, by the government's own three-price counterfactual, not mine. In December 2022 the secretary of state called
  the 2022 net benefit positive but small and expected a much larger one in 2023 because the cost is spread over more consumers (Sábado, Lusa). The adjustment cost is charged
  only to buyers exposed to wholesale prices (hedged and exempt consumption is excluded; ERSE Instrução 6/2022).
- Comparison, with the caveat that counterfactuals differ: my saving to Portuguese buyers is €0.5–1.0 bn at ρ 0.55–1.0 (bill ≤ €0.97 bn, net −0.5 … +0.05 bn); the government's +€570 m
  net to January 2023 lies at the top of my net range and above it at ρ 0.55–0.75. Nothing here pins the Portuguese bill; it stays an upper bound. Lead: DGEG's daily series of the
  average adjustment cost (not fetched).

### I3. Idea 5, the reference-price steps on the declared cost — rule fixed before running (`gas_cap_declared_cost_steps.py`)
PRGN rose from €40 to 45 on 1 January 2023, to 50 on 1 February and to 55 on 1 March (decree art. 3 as amended by RDL 3/2023), cutting the subsidy
S = (PGN − PRGN)/0.55 by €9.1/MWh at a given gas price, whatever the plants do. A plant passing a share ρ of S into its declared cost (the `cab` minimum-income variable term v,
the same units and sample as `gas_cap_declared_cost.py`) should see v/gross change by Δ mean log(1 − ρS/gross) across the step, relative to its reference ratio.
For each step date D: the actual J(D) as in that script (median over units of the change in mean log(v/gross) from the seven days before D to the seven from D); the J predicted at
ρ = 0 and ρ = 1 from the same unit-days' S and gross; the implied ρ (the value on a grid −1 … 2 whose predicted J equals the actual).
**Power rule, fixed now:** report an implied ρ only if |J(ρ=1) − J(ρ=0)| at that step is at least twice the standard deviation of J over the 273 pre-cap placebo dates (`gas_cap_declared_cost_event.csv`);
otherwise write that the step cannot size ρ. A step with S = 0 on the dates inside its windows is skipped (the cap stopped binding in March 2023). No decision rule on the value: it is a check on the 0.91–0.96
day-one and monthly declared-cost ρ, read as consistent if inside [0.5, 1.5] where it is reported.

### I3 results (2026-11-03)
Placebo J (273 pre-cap dates) sd 0.056, so the power bar is |J(ρ=1) − J(ρ=0)| ≥ 0.112.
- **1 January 2023 (PRGN 40 → 45):** 48 units, mean S €41.0. J actual +0.106; predicted +0.000 at ρ = 0 and +0.148 at ρ = 1; gap 0.148 ≥ 0.112 → powered. **Implied ρ = 0.78.** One placebo
  standard deviation of J moves the implied ρ by about 0.38 (0.056 / 0.148), so the band is roughly 0.4–1.2; inside the rule's [0.5, 1.5] read as consistent with the day-one 0.91–0.96, and below it by a point estimate.
- **1 February 2023 (45 → 50):** 49 units, mean S €15.3; gap 0.057 < 0.112 → the step cannot size ρ (the implied 0.63 is not reported).
- **1 March 2023 (50 → 55):** skipped, S > 0 on only 15% of unit-days in the windows.
Reading: the one step with power gives a point estimate under the day-one figure, with a band that contains it. A single event cannot separate 0.78 from 0.93; it adds one more independent angle (a
regulatory change in S, unrelated to plants and the market) that does not contradict the declared-cost ρ near 0.9 and is nearer the offer-side central band. Idea 4 (offer price in euros per euro of subsidy) is the only sizing idea left.

### I4. Idea 4, the offer price in euros per euro of subsidy — rule fixed before running (`gas_cap_quantity_price.py`)
An offer at net cost plus a markup m sits at p = cost_gross − ρS + m, so y = p − cost_gross falls by ρ euros per euro of S. The earlier price designs (`rq-gas-cap-conduct.md`, steps 2 and 2c) failed their
post-cap check (mean gap after the subsidy ended +€168) as a level; as in B2 → B3, the slope on the dose with an intercept absorbs a constant drift, so the same move is made here.
- **Outcomes:** y50 = min(p50, 1000) − cost_gross (the price at half of the unit's offered volume) and ymid = min(p_mid, 1000) − cost_gross; per unit and week the **median** over the predicted in-money
  hours (margin €50, essential units out, cost defined), the sample, unit rule and weeks of B1–B3 (`panel()`, `matrix()`, Italy as control).
- **Dose:** S̄_w = mean subsidy over the Iberian main-sample unit-hours of week w (zero in weeks without a subsidy).
- **Estimate:** Xu (2017) `gsc`, r by cross-validation; ATT_w = a + c·S̄_w over the post-cap weeks; ρ = −c (full pass-through c = −1, none c = 0); firm-block bootstrap (199).
- **Gates, as B3 (decisive):** the timing permutation over cyclic shifts of S̄_w, one-sided p ≤ 0.05 (the real c at or below the 5th percentile of shifted c's); ρ with a linear trend inside the main interval;
  ρ with the MIBGAS control reported, not decisive. If a gate fails: STOP and say the price outcome does not size ρ.
- **Reading:** compare ρ and its interval with the share-based B3 (0.73 [0.51, 1.03]; 0.54 [0.10, 0.87] with gas controls) and the declared-cost ρ (0.91–0.96); say whether the intervals overlap, and nothing more.

### I4 results (2026-11-03; 199 bootstrap draws, r = 1 by cross-validation for both outcomes)
| outcome | Iberian / Italian units | ρ = −c | 95% interval | permutation p | ρ with trend | ρ with MIBGAS |
|---|---|---|---|---|---|---|
| y50 = p50 − cost_gross | 49 / 28 | 1.17 | [0.71, 1.74] | 0.000 | 1.05 [0.74, 1.39] | 0.62 |
| ymid = p_mid − cost_gross | 48 / 25 | 1.34 | [0.95, 1.90] | 0.000 | 1.11 [0.87, 1.54] | 0.60 |
Gates (permutation, trend inside the main interval): ALL PASS for both. Italian units fall to 28 and 25 because the weekly median needs enough in-money weeks per unit.
Reading: the offer price falls by about 1.2–1.3 euros per euro of subsidy without a gas control, which is a ρ above 1 and an interval that overlaps the share-based B3 (0.73 [0.51, 1.03]) only on
0.71–1.03 for y50; with the MIBGAS control it falls to 0.60–0.62, next to the share-based controlled value (0.54–0.58). Same pattern as H4–H5 shows in two outcomes: the uncontrolled slope absorbs
whatever co-moves with the gas price (here the cost_gross term enters y directly), and the control brings the two outcomes to the same place. The two outcomes come from the same panel, so their agreement is
not independent evidence. Other angles: declared-cost ρ 0.91–0.96 (relative to a pre-cap ratio), reference-price step 1 January 2023 implied ρ 0.78 (band about 0.4–1.2).
All five sizing ideas of section G have now been run or ruled out; the binding limit remains about ten firm clusters.

### I2 addendum. DGEG's daily balance fetched (2026-11-04; `scripts/fetch/fetch_dgeg_mecanismo_iberico.py`, `data/dgeg/`)
DGEG's workbook (`dgeg-mie-20240103.xlsx`, open download; the DGEG page itself now redirects to the home page, the link comes from an Internet Archive capture) gives per day, 2022-06-15 → 2023-12-31
(565 days), in EUR/MWh and **with no volumes or totals**: the Portuguese OMIE spot, `adjust_cost` (OMIE's daily average adjustment charge per MWh bought by the buyers who pay it), their sum, MIBGAS, and
DGEG's counterfactual `price_no_mech` = spot + (gas − cap)/0.55, which is a formula on the already-capped spot price, not a re-clearing. The "differential" is price_no_mech − final price.
- Adjust cost is positive on 194 days, 2022-06-15 → 2023-02-03: mean €67.00/MWh over 2022-06-15 → 2023-01-31 (€65.43 weighted by Portuguese demand); by quarter 92 (from 15 June), 124, 28, then 0.
  Differential mean 42.95 over the same days (the Lusa figure of 43.78 does not reproduce exactly).
- **The €570 m does not reproduce** from the file with REN consumption (32.0 TWh): differential × all consumption = €1.37 bn; adjust cost × all consumption = €2.10 bn (an upper bound on the Portuguese charge).
  €570 m / €43.78 = 13.0 TWh, about 40% of consumption: if both figures refer to the same exposed volume (not stated anywhere), the Portuguese bill is about adjust cost × 13.0 TWh = **€0.85–0.87 bn**,
  below my plant-side upper bound of €0.965 bn. That is an inference from two press figures, not a published number.
- DGEG's cap path in the workbook (40 to 2023-03-31, then 55 / 56.1) is not the decree's. The consolidated RDL 10/2022 art. 3 (read again 2026-11-04) gives 40 initially and from January 2023 45, 50, 55, 56.1 (April) rising to 65 in December,
  which is the path this repo uses; DGEG's counterfactual is therefore wrong in January–March 2023 and is not used for anything here beyond its adjust-cost column.
- Portuguese net with this bill: my saving to Portuguese buyers (all day-ahead purchases, exempt buyers included) €0.49–1.02 bn at ρ 0.55–1.0 minus about €0.86 bn = about −€0.37 … +€0.16 bn; the earlier bound was −0.48 … +0.05.
  The government's +€570 m is a formula benefit (the subsidy added in full to the price without the mechanism, ρ = 1 and no re-clearing) on the exposed volume, not comparable with a re-cleared saving.

### H8. A within-Iberia counterfactual — rules fixed before running (2026-11-04; user chose it; an independent design review and a predictor inventory shaped it)
Why: H1 shows Italy's weekly path adds noise to an Iberian plant before the cap (R² −0.35), and H4–H5 show the weekly ρ is exposed to any Iberian-only response to the gas price (which correlates 0.98 with the dose). Here the no-cap path of
each Iberian unit's run20 is predicted from conditions known at bid time, fitted on the pre-cap weeks only; Italy is a check, not the control.
**What the review found, and how the design answers it** (all five of its fatal flaws bind and are kept in view):
(1) identification is by extrapolation, because g_w is zero before the cap and the post-cap gas prices lie partly outside the pre-cap range → report the in-range count and the in-range result; (2) the gas dilemma (in x: extrapolation, MIBGAS moved by the cap; out of x: the Iberian gas response loads on the dose) →
two variants, gas in and gas out, with the **non-Iberian gas price PSV**, and ρ reported as the span of both; (3) the outcome's cost definition: run20 is measured against net cost after the cap, so the prediction target is the no-cap path measured against gross cost; ATT = 0 under full pass-through and −g under none, the B1 ends, unchanged;
(4) the errors are week-level, not unit-level → the bootstrap resamples firms AND moving blocks of weeks (training and post); (5) predictors changed by the cap are excluded: MIBGAS, Spanish, Portuguese and French day-ahead prices, OMIP forwards, interconnection occupation, the capped or subsidised costs, every outcome column.
**Sample and weeks:** as B1–B3 (predicted in-money hours at margin €50, essential units out, 49 Iberian and 44 Italian units, weekly unit mean of run20). Fit weeks 2021-10-04 → 2022-06-06 (36 weeks); the week of 2022-06-13 (two days before the cap, five after) is dropped from fit and
regression; post weeks 2022-06-20 → 2023-06-26 (54 weeks, about 37 with g_w > 0). The in-money classification is the panel's (actual lagged price minus net cost): a known limit, kept for comparability with B3.
**Predictors,** weekly means of daily values known by 12:00 on D−1 (prices with the D−2 rule, as the `_bid` costs): PSV (GME reference price), EUA, the ESIOS day-ahead residual-load forecast (demand − wind − PV forecasts; Spain only), population-weighted temperature (Spain; Italy for Italy).
Gas in: {PSV, EUA, residual load, temperature}; gas out: {EUA, residual load, temperature}. Italy (no Italian load forecast in the repo): gas in {PSV, EUA, temperature}, gas out {EUA, temperature}.
**Model:** y_iw = a_i + x_w'β + e, unit intercepts free, common slopes, ridge on standardised x with penalty λ ∈ {0.1, 1, 10} chosen by rolling-origin cross-validation inside the fit weeks (expanding window; origins at fit weeks 20, 24, 28, 32, horizon 4 weeks); predictions clipped to [0, 1].
ATT_w = mean over Iberian units with y observed of (y − ŷ).
**Stage 1 (no ρ computed):** per variant, (a) out-of-sample R² relative to the unit-mean-only model > 0 in at least 3 of the 4 origins; (b) the high-gas holdout (fit on fit weeks with PSV at or below its fit-week median, predict the weeks above) has R² relative to the unit-mean-only model > 0;
(c) the out-of-sample MAE on the same predictions at least 20% below that of the Italy-based `gsc` at r = 0 fitted on the same training weeks. A variant that fails any of the three is dropped and said so; if both fail the exercise STOPS.
**Stage 2 (only for variants that passed):** ρ = 1 + b of ATT_w = a + b g_w over post weeks with g_w observed (and with a linear trend); timing permutation over cyclic shifts of g_w (one-sided p ≤ 0.05); firm-block bootstrap 999 draws, each resampling firms within country,
resampling the fit weeks in moving blocks of 6 for the refit (λ fixed at its full-sample choice), predicting the full path with actual x, and moving-block resampling (6) of the post weeks for the final regression; percentile 95% interval.
Fake-cap placebo: fake cap dates every two weeks from 2021-12-27 to 2022-04-18; refit on the weeks before each, predict the 12 weeks after, regress ATT on the first 12 values of the real dose sequence, b_fake; the real b must lie outside the 5th–95th percentile range of the b_fake.
Diagnostics, all reported: dose-positive post weeks with PSV and residual load inside the fit-week min–max; the partial R² of g_w on x over the post weeks; the mean ATT in post weeks with g_w = 0 and PSV inside the fit range (model-validity check: |mean| < 0.05 in run20 units).
Italy placebo (only if the Italian recipe passes the same Stage-1 gate): the Italian ATT regressed on the Iberian g_w; passes if its 90% block-bootstrap interval lies inside [−0.25, +0.25] and is narrower than 0.6 (a pass without that width has no power).
**Uninformative, said in advance:** Stage 1 fails for both variants; fewer than 15 dose-positive post weeks inside the fit range; partial R² of g_w on x above 0.9; mean |ATT| in the in-range g_w = 0 weeks at or above 0.05; the real b inside the fake-date range; the Italy placebo fails or lacks power;
the gas-in and gas-out ρ intervals overlap by less than half of the narrower width. In any of these cases the result is reported as a bound on the predictive model, not as pass-through. Even if everything passes it is corroboration only: it shares B3's dose and the gas-dose collinearity.

### H8 stage 1 results (2026-11-04; `gas_cap_quantity_predictive_stage1.py`, no ρ computed)
49 Iberian and 44 Italian units, 36 fit weeks (2021-10-04 → 2022-06-06), 54 post weeks of which 34 carry a positive dose. Penalty λ = 0.1 (the least shrinkage) was chosen in every case.
| country, variant | (a) R² vs unit mean, four origins | (b) high-gas holdout R² | (c) MAE model / gsc r = 0 (rolling origins; high-gas holdout) | gate |
|---|---|---|---|---|
| Iberia, gas in | +0.175, +0.126, +0.042, +0.085 (4 of 4) | +0.017 | 0.1075 / 0.1203 = 0.89; 0.1054 / 0.1000 = 1.05 | **FAIL (c)** |
| Iberia, gas out | +0.003, +0.050, +0.055, +0.092 (4 of 4) | +0.002 | 0.1117 / 0.1203 = 0.93; 0.0971 / 0.1000 = 0.97 | **FAIL (c)** |
| Italy, gas in | −0.012, +0.004, +0.125, −0.025 (2 of 4) | −0.037 | not defined for Italy | FAIL (a), (b) |
| Italy, gas out | −0.008, +0.005, +0.084, −0.015 (2 of 4) | +0.020 | not defined for Italy | FAIL (a) |
**Rule: both Iberian variants fail gate (c) (needs ≤ 0.80 of the Italy-based MAE on both sets of cells), so the exercise STOPS; stage 2 is not run, and the Italy placebo cannot be run either (its recipe fails the gate).**
Reading: conditions known at bid time do explain some of the Iberian out-of-sample variation around each unit's own mean (R² 0.04–0.18 with gas, 0.00–0.09 without) and they beat Italy's path by 7–11% on average, but on the one test of extrapolation to
high gas prices (the high-gas holdout) they are no better than the Italian path (1.05 and 0.97 of its MAE). The pre-cap run20 of an Iberian unit is mostly unit-specific noise that neither the Italian path nor the weekly conditions describe. This is a fact about the
data, not about one counterfactual: with no better counterfactual of the level available, B3's intercept absorbs the level error and the slope on the dose keeps its one exposure, an Iberian response to the gas price that tracks the dose (H4–H6).
Built for this: `scripts/build/build_weekly_conditions.py` (weekly bid-time conditions, `outputs/tables/gas_cap_weekly_conditions.parquet`, not committed), `scripts/analysis/gas_cap_predictive.py` (model code).

## J. Welfare accounting of the pass-through: who gains, who loses, and the dispatch distortion (rules fixed before running, 2026-11-05)

User asked (2026-11-05) to investigate the deadweight loss as well as the transfers. Section D priced the pass-through as a change in the
price times cleared volume. That counts a euro paid by buyers and received by a plant as zero, and it holds volume fixed. This section
keeps the same re-clear and adds what D leaves out: who receives the money, and what the lower offers do to which plants run.

**Plain example (one hour).** The observed price is €100. If the 54 gas units had not lowered their offers by ρS, the price would have been
€110, and the units would have been paid €110. At €100 the buyers of 30,000 MWh pay €300,000 less; every plant paid the price loses €10 a MWh;
the gas units are repaid by the subsidy. Those are **transfers**: one party's loss is another's gain. A **deadweight loss** appears only if
the lower offers change *what runs*: a gas unit whose true fuel cost is €105 runs and pushes out a coal unit costing €95. Society then burns €10
more fuel per MWh of that swap, and nobody gains it. Likewise, if the €100 price lets a buyer worth €102 take a MWh that costs €105 to
produce, society loses €3.

### J1. Definitions (fixed now)

- **Two worlds, same hours.** *Observed* world = the effective curve of `step_curves.py` (accepted rows below the price, offered rows at and
  above it), with the offers as they were: already net of the pass-through ρS for the modelled gas units. *Counterfactual* world = the same
  curve with every sell row of the modelled gas units (the 55 panel units with a cost; 54 have a subsidy day) raised by ρS_day. Both are
  re-cleared by the same rule as `gas_cap_consumer_saving.py` (lowest price at which supply covers the buy volume strictly above it: demand
  is the buy bids, so volume responds to price). ρ takes every value of the saving script's `RHOS` (0.51, 0.54, 0.55, 0.73, 0.75, 1.00, 1.03); the
  headline reads 0.55, 0.73 and 1.00. Δ always means observed minus counterfactual: the effect of the pass-through.
- **Hours.** The saving script's valid hours (2022-06-15 → 2023-02-25, 24-period days, S > 0, unsplit Spain/Portugal, clearing identity
  holds, re-clear within €0.5 of the published price). I report the hours kept and dropped, per month and in total, and the bill (S times
  cleared MWh of the 54 units) in the dropped hours. Every euro figure covers the valid hours only; nothing is scaled up.
- **Quantity each unit gets.** At the clearing price p, sell rows priced below p run in full; sell rows priced at p are cut pro rata to fill
  the volume Q = min(supply at or below p, buy volume at or above p); the same on the buy side. This is the volume-maximising allocation. It
  need not equal the actual allocation at the margin; the observed world here is the *re-cleared* observed world, and I report how far its
  volume is from the actual cleared buy volume.
- **True resource cost (a proxy, stated as one).** A modelled gas step costs its counterfactual offer price, offer + ρS: the cost the plant
  would have offered without the subsidy. Every other step costs its own offer price. For non-gas plants an offer is not a cost: hydro offers a
  water value, a coal or older plant may add a markup. So "dispatch distortion" means *relative to the plants' own offers*, with only gas
  moved. It leaves out distortions among non-modelled plants (other gas, cogeneration, coal under the mechanism, whose offers I do not move).
  With ρ < 1, (1 − ρ)S per MWh stays in the plant's profit, and is a transfer.
- **Buyers' gross benefit** = the area under the accepted buy bids, Σ accepted MW × bid price (one hour = 1 h). Extra volume taken in the
  observed world is valued at the bid of the marginal buyers.
- **Welfare** W = gross benefit − true cost of the accepted sell rows. In the counterfactual world the dispatch is the cheapest one for
  the true-cost ladder, by construction, so W_cf ≥ W_obs hour by hour, and **DWL = W_cf − W_obs ≥ 0** (reported as a positive loss).

### J2. Exports, imports and the interconnection legs (stated treatment)

The coupled flow with France is the pseudo-unit `MIEU` (and `MIE`/`MIP`, which appear only in split hours; the valid screen removes those).
In August 2022 it is an export bid at €1,500 in 743 of 744 hours, and one import offer at −€300; these prices are not valuations or costs. Its
volume is **held fixed in both worlds** (it is accepted at any price reached, so a different Iberian price would in fact move the flow; this
design cannot represent that). I report two treatments, and check that they differ only by a transfer:
- **(A) Exports as part of demand.** Export bids are buy rows valued at their bid, and imports sell rows at their offer. Because the volumes are the
  same in both worlds, their gross benefit and cost cancel exactly in every Δ. I check that volumes are identical.
- **(B) Separately, Iberian view.** Exports earn p per MWh, and imports cost p per MWh, to the Iberian system. The change is Δp × (exports − imports):
  the price fall is a **gain to the foreign buyer** of Iberian exports. This is the part that "leaked abroad" through the interconnection.
  Congestion rent (the French price differs from p when the line is full) is **not** modelled; it would enter the bill (decree art. 12).

### J3. What is computed, per ρ (€ m, valid hours)

1. **Buyers' payment change** ΔPay = p_obs × Q − p_cf × Q_cf, by buyer class: *Spanish* (every buy unit not Portuguese and not an interconnection
   pseudo-unit; units absent from the registry are counted Spanish and their volume reported), *Portuguese* (registry country PT) and *exports*
   (`MIEU`, `MIE`, `MIP`). Also the change in gross benefit, so that the quantity response is not hidden in the payment.
2. **Buyers' subsidy charge.** For Spanish buyers the ESIOS charge (the existing `gas_cap_net_by_country.py` figure: 1908 × 351 + 1909 × 352 + 1907 × 353,
   same valid hours). For Portuguese buyers the upper bound (S × MWh of the Portuguese modelled plants), as in F. The model-consistent subsidy to the
   Spanish modelled plants (S × observed re-cleared MWh) is also computed; **ESIOS charge − that** is carried as its own line, "charge not tied
   to modelled plants" (goes to plants I do not model, and its dispatch effect is not in the DWL).
3. **Revenue changes by seller class:** modelled gas units, Spain and Portugal (market revenue, and separately the subsidy they receive in the
   observed world, which is zero in the counterfactual), other generators Spain and Portugal, and the interconnection import leg.
4. **Party ledger.** Each party's net change = ΔGross benefit − ΔPayment − charge (buyers) and ΔRevenue − ΔTrue cost + subsidy received (sellers). Parties:
   Spanish buyers, Portuguese buyers, exporters, modelled gas (Spain), modelled gas (Portugal), unmodelled recipients of the rest of the Spanish
   bill, other generators (Spain, Portugal), importers.
5. **Decomposition of the DWL.** Let TCmin(Q) = the cheapest true cost of supplying volume Q (integral of the true-cost ladder, which is the
   counterfactual's sell side).
   - **(b) Allocation effect** = true cost of the observed dispatch − TCmin(Q_obs): the extra cost of running the wrong plants *at the observed volume*. ≥ 0.
   - **(a) Quantity effect** = [GB(Q_cf) − TCmin(Q_cf)] − [GB(Q_obs) − TCmin(Q_obs)]: the loss from taking more (or less) volume than the efficient
     point, with the cheapest plants. Because the counterfactual is efficient, this is ≥ 0 as a loss.
   - By construction **DWL = allocation + quantity.** The sample month tests this and the other identities before totals are trusted.

### J4. Checks, and what each failure means (fixed now)

- **C1 re-clear.** My observed and counterfactual prices equal the saving script's `p_clear` and `p0_ρ` (`gas_cap_consumer_saving_hourly.parquet`)
  within €0.011 in at least 99.9% of valid hours, every ρ. Below that: find the cause (float ties) before any total is used.
- **C2 market balance.** In every hour, accepted buy volume equals accepted sell volume within 0.01 MW (at least 99.9% of hours), and Σ buyers'
  payments = Σ sellers' revenue within €1 per hour. A failure is a bug in the allocation: STOP, no totals.
- **C3 identity (sample month).** ΔW computed from gross benefit and true cost = the sum of the party ledger (with the charge and the subsidy
  netting) = allocation + quantity effect, each within €0.01 m. A failure: STOP.
- **C4 efficiency property.** The counterfactual welfare is not below the observed in more than 0.1% of hours, and the sum of the negative hourly
  DWL is under 0.1% of total DWL (float ties and pro rata cuts at the margin make tiny exceptions). A failure means the true-cost ladder and the
  clearing rule disagree: report and do not interpret the split.
- **C5 volume.** The observed world's re-cleared volume against the actual cleared buy volume (bids, status C): report the mean and the 95th
  percentile of the gap; flag it if the mean |gap| exceeds 0.5% of volume. It affects levels, not the Δ; reported, not a stop.
- **C6 fixed legs.** Interconnection volumes identical in both worlds (A); otherwise (A) and (B) are not comparable: STOP.
- **C7 monotone in ρ.** DWL non-decreasing in ρ across the 7 values, hour totals; reported, not a stop.
- **Timing.** One month first (August 2022, the largest), time reported, then all nine months (202206 → 202302) with single-thread BLAS.

**Reading rules.** The headline is three numbers per ρ, all of the Spanish buyers' net loss N = −(their net change): the part that is a transfer
to Spanish sellers, the part that is deadweight loss, and the part that leaks outside Spain (Portugal + exporters + importers + Portuguese plants).
They add to N by the identity (N = DWL + net gain of Spanish sellers + net gain outside Spain). I will not call DWL "small" or "large" against a
threshold set after the fact; I will state it in euros and as a share of N, and that it is a proxy-based figure that covers only the modelled
gas units' offers. **What would change my reading:** a DWL that is not stable across ρ in sign or order of magnitude; an allocation effect that
vanishes if non-gas offers are costs (it cannot be tested here); any C-check failing.

### J5. Amendments after the one-month test (2026-11-05; the original rules above stay as written)

The test month (August 2022, 681 valid hours) ran in 13 s and passed C1–C4 and C6 (price match 100%, no unbalanced hour, no hour with W_cf < W_obs, identities
to 1e-8 m). I saw its headline numbers before writing this, so these amendments are not blind to them; none relaxes a check.
- **A1. First-order reconciliation (new check C8).** The saving of D is (p_cf − p_obs) × cleared buys, volume held fixed. J computes the surplus change, which also
  counts the volume response. For each ρ I report both for all buyers; the first-order figure must equal D's gross saving `G(ρ)` in `gas_cap_consumer_saving.csv`
  within €1 m (same hours, same prices). Their difference is the volume response, not an error.
- **A2. Allocation effect = the DWL under fixed volume.** It depends only on the observed volume and the true-cost ladder, not on the counterfactual price. The quantity
  effect is the extra loss from the buy bids' response. In the test month the counterfactual volume is 3–4% below the observed in every hour: buy bids sit at round
  prices (€250–500) that a higher counterfactual price crosses. The quantity effect therefore rests on the submitted bid ladder, not on an estimated elasticity, and
  is reported apart.
- **A3. Sensitivity on the plant set (no gate).** `--units ccgt_coal` repeats everything with the 97 units of D's wider set moved (the 54 plus every gas CCGT and coal unit of
  OMIE's listing); their class label stays "modelled gas". It removes part of the limit in J1 (subsidised plants whose offers were not moved) and is reported beside
  the main result. The 54-unit run is the main one.

### J6. Results (2026-11-05; `scripts/analysis/gas_cap_dispatch_welfare.py` → `outputs/tables/gas_cap_dispatch_welfare{,_headline,_ledger,_monthly,_hours,_checks}.csv`, `_hourly.parquet`; `_ccgt_coal` twins)

**Timing.** One month (August 2022, 7 values of ρ): 13 s. All nine months, single thread: 100 s (the wider set, 124 s). No multiprocessing needed.

**Hours.** 5,808 hours in the cap months, **5,397 valid (92.9%)**, 411 dropped (split Spain/Portugal, identity failures, re-clear off by more than €0.5): the saving script's screen, same hours. The
bill on the modelled units in the dropped hours is €331 m against €4,937 m in the valid ones (6.3% of €5,268 m), so every euro figure below covers about 94% of the subsidy and is not scaled up.
Dropped by month: Jun 11, Jul 71, Aug 63, Sep 25, Oct 66, Nov 42, Dec 29, Jan 68, Feb 36.

**Checks (all nine months; both unit sets).** C1 passes: the observed and every counterfactual price equal the saving script's in 100.0% of hours. C2: no hour where volume bought differs
from volume sold by more than 0.01 MW; payments equal revenue to €0.6 in total. C3: the ledger total equals the welfare change, DWL equals allocation + quantity, and N equals DWL + Spanish sellers + outside
Spain, all to 1e-8 m. C4: no hour with W_cf below W_obs; the counterfactual dispatch costs the same as the ladder's cheapest supply of its volume to 1e-8. C5: the re-cleared observed volume is within 0.005% of the actual
cleared buys (mean gap). C6: the interconnection volumes are identical in both worlds, so exports and imports drop out of every difference (their gross benefit and cost change by exactly 0). C7: DWL rises with ρ at every step.
**C8 passes**: my first-order saving over all buyers equals D's gross saving (€3,211 m at ρ 0.73) to 1e-12. Bill: S times the re-cleared observed MWh of the 54 units is €4,938 m against €4,937 m from actual cleared MWh. **No check failed.**

**Result, 54 modelled gas units (€ m, valid hours; Δ = observed − counterfactual).** N is the Spanish buyers' net loss: the ESIOS charge (€5,427 m) less their surplus gain.

| ρ | Spanish buyers' net loss N | transfer: net gain of Spanish sellers | **deadweight loss** (allocation + quantity) | leaks outside Spain (exporters + Portugal + importers) |
|---|---|---|---|---|
| 0.55 | 3,880 | 3,374 (87%) | **274** (7%) = 215 + 59 | 233 (6%) = 178 + 56 − 1 |
| 0.73 | 3,229 | 2,397 (74%) | **539** (17%) = 441 + 98 | 294 (9%) = 256 + 39 − 2 |
| 0.75 | 3,157 | 2,283 (72%) | **574** (18%) = 471 + 103 | 299 (9%) = 265 + 36 |
| 1.00 | 2,265 | 805 (36%) | **1,127** (50%) = 922 + 204 | 334 (15%) = 375 − 39 − 2 |

The columns add to N in every row (checked). Across the full interval of B3 (ρ 0.51–1.03): DWL €229–1,206 m, N €4,025–2,164 m.

**The ledger** (€ m, net change of each party, observed minus counterfactual; ρ 0.55 / 0.73 / 1.00):

| party | 0.55 | 0.73 | 1.00 |
|---|---|---|---|
| Spanish buyers (surplus gain less the ESIOS charge) | −3,880 | −3,229 | −2,265 |
| modelled gas plants, Spain (market revenue − true cost + subsidy) | +3,128 | +2,678 | +1,908 |
| the rest of the Spanish bill, to plants not modelled (ESIOS charge − subsidy on the 54 units) | +1,454 | +1,454 | +1,454 |
| other generators, Spain (lower price, same offers) | −1,209 | −1,736 | −2,557 |
| *Spanish sellers together* | *+3,374* | *+2,397* | *+805* |
| Portuguese buyers (charge taken as the upper bound, the subsidy on Portuguese plants, €965 m) | −488 | −284 | +17 |
| modelled gas plants, Portugal | +786 | +699 | +547 |
| other generators, Portugal | −242 | −375 | −603 |
| exporters (lower price on fixed export volume) | +178 | +256 | +375 |
| importers | −1 | −2 | −2 |
| **all parties = −DWL** | **−274** | **−539** | **−1,127** |

The gross flows are larger than the net. At ρ 0.73 the gas plants and unmodelled recipients gain €4.1 bn and the other Spanish generators lose €1.7 bn through the lower price; buyers
save €2.2 bn of wholesale cost and pay €5.4 bn. Portugal's net does not depend on the charge assumed: the charge and the subsidy on its plants are equal and cancel (+€38 m at ρ 0.73, −€39 m at ρ 1).

**What the dispatch distortion is.** At ρ 0.73 the observed world runs the 54 gas units for 10.2 TWh more than the counterfactual (37.1 against 26.9 TWh; at ρ 1, 14.7 TWh) and other plants for 7.5 TWh less;
the 2.7 TWh left over is the extra volume (observed volume is 2.0% above the counterfactual's, 137.0 against 134.3 TWh). The allocation effect (€441 m) is the extra true cost of the 7.5 TWh of substitution at the
observed volume: about €59 for each MWh swapped, the gap between gas's true cost (offer + ρS) and the offers of the plants it displaced. The quantity effect (€98 m) is buyers taking 2.7 TWh that the cheapest supply would not serve at the
true cost; it rests on the submitted bid ladder (buy bids at round prices of €250–500 that the higher counterfactual price crosses), not on an estimated elasticity. DWL by month at ρ 0.73 (€ m): Jun 41, Jul 128,
**Aug 205**, Sep 105, Oct 14, Nov 6, Dec 39, Jan 1, Feb 0.2: the same months as the subsidy (Aug and Sep carry 58%).

**Reconciliation with F and D.** N differs from F's net Spain (−3,848 / −3,172 / −2,149) by €32–116 m (1–5%): F is first-order (volume fixed) and leaves unregistered units outside Spain; J counts the volume
response (it lowers the all-buyer surplus gain from D's €2,246 / 3,211 / 4,670 m to €2,202 / 3,135 / 4,519 m) and puts unregistered buyers in Spain. I did not split that gap further.

**Exports as demand, and the Iberian view (J2).** (A) with exports and imports as fixed-volume rows, welfare falls by the DWL: €274 / 539 / 1,127 m. (B) Iberian welfare, which also loses the
exporters' gain (and the importers' loss), falls by **€451 / 794 / 1,500 m**; the difference is the leak through the interconnection (€177 / 255 / 373 m net).

**Sensitivity, 97 units moved (54 + OMIE gas CCGT and coal; no gate).** DWL €294 / 578 / 1,221 m at ρ 0.55 / 0.73 / 1.00 (+7 to +8% on the main run); N €3,741 / 3,012 / 1,878 m;
transfer 85% / 70% / 15% of N; DWL 8% / 19% / 65%; outside Spain 7% / 11% / 20%. The bill not tied to modelled plants shrinks from €1,454 m to €522 m. The ranking of the three shares at each ρ
is unchanged; the transfer shrinks and the DWL grows as the set widens, most at ρ = 1.

### J7. Statement, and what it does not show

**At ρ 0.73 (B3 main), Spanish buyers lose €3.2 bn net of the saving they got.** About **€2.4 bn (74%) is a transfer** to Spanish sellers: the gas plants and the other recipients of the bill gain €4.1 bn,
and the other Spanish generators lose €1.7 bn of that back through the lower price. About **€0.54 bn (17%) is deadweight loss** from dispatch: gas running ahead of cheaper plants (€0.44 bn) and buyers
taking volume that costs more than they value it at the true cost (€0.10 bn). About **€0.29 bn (9%) leaks outside Spain**, almost all of it (€0.26 bn) to the foreign buyers of Spanish exports through
the lower price; Portugal's net is +€0.04 bn. On B3's range (ρ 0.55–0.75) the shares are transfer 72–87%, DWL 7–18%, outside Spain 6–9%. They move steeply with ρ: at full pass-through the buyers get
most of the subsidy back in price, so N falls to €2.3 bn, but DWL rises to €1.1 bn and is half of N. **The DWL is not small at the high end of ρ**, and it grows faster than the price saving does.

**Limits, all in the figures above.** (1) The true-cost proxy: non-gas offers are not costs (a hydro or coal markup would change which swaps are inefficient). Only the 54 (or 97) units' offers
are moved; other subsidised plants' lowered offers stay as observed in both worlds, so distortions among them are missing. The 97-unit run raises DWL by 7–8%, the 54-unit run is a lower figure for that
reason. (2) The interconnection volumes are fixed; a higher Iberian price would cut exports and raise imports, so the exporters' gain is conditional on the observed flows. French congestion rent is not
modelled. (3) The quantity effect uses the submitted buy ladder. (4) The pro rata cut at the margin is the model's, not OMIE's allocation. (5) ρ is B3's, estimated on 54 units with a wide interval, and
the subsidy bill in the counterfactual is zero by design, so this compares the cap with pass-through ρ against a world with neither. (6) Valid hours only (92.9% of hours, 94% of the subsidy). (7) The Spanish
charge is ESIOS's and the Portuguese one an upper bound; nothing here tests the decree's allocation of the bill to exports or Portuguese buyers (I1, I2).

### I1b. Exports, settled from Annex I (2026-11-05; `scripts/analysis/gas_cap_exports_split.py`)

**The decree does decide it, by bidding zone.** OMIE rule 51 bis.3 (inserted by Annex I of RDL 10/2022) charges the cost to "unidades de
adquisición establecidas en las zonas española y portuguesa" held by market agents, minus storage, auxiliaries and hedged energy. The same
rules say import and export units are "unidades externas al sistema ibérico" and that **units trading with Andorra and Morocco belong to the
Spanish bidding zone**; France is not in that sentence. The France coupling flow is settled with the French NEMOs (rule 52.2), not with an
agent's purchase unit. So: **exports to Morocco and Andorra were charged; exports to France were not.** (I1's "plausible reading" now has a
textual basis; I1's point that this does not move the Spanish or Portuguese net stands.)

**Euros, valid hours 2022-06-15 → 2023-02 (the J sample; ESIOS 32/34/35, PBF scheduled exports):**

| border | TWh | gain from the price fall, ρ 0.55 / 0.73 / 1.0 (€ m) | charge at ESIOS 1907 / 1909 rate (€ m) | net at ρ 0.73 |
|---|---|---|---|---|
| France | 10.47 | 176 / **254** / 371 | not charged (would be 419 / 762) | **+254** |
| Morocco | 1.35 | 24 / 35 / 51 | 55 / 95 | −20 … −60 |
| Andorra | 0.19 | 2.5 / 3.6 / 5.2 | 6 / 10 | −2 … −6 |

- France's €254 m matches J's interconnection row (€256 m, the `MIEU` pseudo-unit), so the leak abroad through exports is essentially
  **France: €0.18–0.37 bn, uncharged.** Had France-bound energy paid the full rate it would have borne €0.4–0.8 bn.
- Morocco and Andorra exporters paid more than they saved, like Spanish buyers. The 1909 (reference-supplier, unhedged) rate is the upper
  end; 1907 averages over hedged energy and is the lower. Small: €0.06–0.11 bn charged in all.
- **Offset not counted here:** the France-border congestion rents spent on the cost (art. 14, rule 52.2) are the decree's own partial
  recovery of the export pull. ESIOS 1117/1118 carry them; not fetched.
- **Effect on J:** Morocco/Andorra export units were counted with Spanish buyers in the price fall (€39 m at ρ 0.73) but their charge is not
  in the ESIOS group bill. Moving them changes no total (transfers only; DWL unchanged) and Spanish buyers' net by under €0.1 bn.

### I1c. France: the gain went to the border, not to French buyers (2026-11-05; `scripts/analysis/gas_cap_france_rents.py`)

Fetched ESIOS 1117/1118 (day-ahead implicit congestion rents on the France line, import / export direction, € per hour, **gross for
both systems**, split 50/50 under Reg. 1222/2015), 2021-06-01 → 2023-12-31. Output `outputs/tables/gas_cap_france_rents.csv`.

**Mechanism.** J books Δp × (scheduled France export) as a gain to "exporters". Under coupling, when the line is export-full the French price
does not follow the Iberian fall; the extra gap × flow is collected as congestion rent, half to each side. Only in open hours does a lower
Iberian price reach French buyers.

**Line state in the 5,397 valid hours: export-full 87.9%, open 9.1%, import-full 3.0%.** So at ρ 0.73 (ρ 0.55 / 1.0 in brackets):

| who gets the €254 m (176 / 371) | € m |
|---|---|
| congestion rent, export-full hours | 251 (175 / 368) |
| of which Spanish half: reduced the cap's cost (rule 51 bis.2, RENTAFR) | **126** (87 / 184) |
| of which French half: to the French side of the border | **126** (87 / 184) |
| French buyers, through a lower French price (open hours) | **2** (2 / 3) |

**Check.** Over 2022-06-15 → 2023-02, ESIOS 1118 is €1,108 m against €1,974 m for (French − Spanish price) × PBF scheduled export, hourly
correlation 0.943. The level gap fits PBF exports including flow nominated on long-term transmission rights, whose share of the gap is paid to
rights holders out of the rent rather than counted in it (the decree deducts that remuneration from RENTAFR). So part of each "half" above
may go to long-term rights holders instead; not separable from this data. Gross rent over the valid hours: €1,036 m, Spanish half €518 m — the
whole rent, of which the cap's own price fall accounts for about €126 m on the Spanish side.

**Reading.**
- **French buyers gained almost nothing (≈ €2 m).** The line was full nearly every hour, so the cap's price fall widened the border spread
  instead of lowering French prices. "France got cheap Iberian power for free" is wrong as stated; the French *side of the border* gained
  ~€0.09–0.18 bn of rent.
- **Leak abroad through France: €0.25 bn → ≈ €0.13 bn** at ρ 0.73. The Spanish half is already inside the observed ESIOS charge (it lowered it),
  so in J it sits in the "rest of the Spanish bill" residual. Totals and DWL unchanged (transfers).
- Supersedes I1b's "French buyers gained €254 m". Morocco and Andorra rows of I1b stand (not coupled; no implicit rent).

### I1d. Would exports have responded to the higher no-cap price? (2026-11-08; descriptive check, no rule fixed in advance)

J holds export volumes at their observed level (J2). Check: in the valid hours, compare J's counterfactual (no-cap) Iberian price
`p_c` (`gas_cap_dispatch_welfare_hourly.parquet`) with the observed French price (`france_link_hours.parquet`). In an export-full hour
the flow stays at capacity as long as the Iberian price stays below the French one, so a fixed volume is then exact.

| ρ | export-full hours | of which no-cap price ≥ French | export capacity in those hours | median French − no-cap price |
|---|---|---|---|---|
| 0.55 | 4,716 of 5,397 | 53 (1.1%) | 0.13 of 10.27 TWh | €157 |
| 0.73 | 4,716 | 82 (1.7%) | 0.20 TWh | €150 |
| 1.0 | 4,716 | 131 (2.8%) | 0.33 TWh | €139 |

**Reading.** Without the cap the line would still have been export-full in 97–99% of the hours it was full: Iberia would still have
been about €140–160 cheaper than France. So fixing exports misstates the volume in at most the 511 open hours (9.5%) and 1–3% of the
full hours, about 2–3% of the export volume. The "exports held fixed" limit in J7 is therefore small, and the leak abroad is the
congestion-rent split of I1c (French side ≈ €0.13 bn at ρ 0.73; French buyers ≈ €2 m). Ad hoc; French prices are held at their
observed level (they would barely move in full hours, by coupling).

## K. Plant-level dose: within Iberia, Italy as a triple difference — rules fixed before running (2026-11-08; user chose it)

**Why.** B3 compares one Iberian weekly average with a synthetic Italy, so its slope rests on 46 post-cap weeks and on
Italy's level tracking Iberia's — which Italy's March 2022 break undermines, and which the gas-control question (E2, H6)
could not settle. But the dose differs by plant within a week: the subsidy S is the same €/MWh for all, and what it does
to a plant's run20 under no pass-through depends on how much of that plant's capacity it offered at a markup between
20 − S and 20. With week fixed effects the gas price, the invasion and everything else common to a week drop out, and
Italy is not needed for the level at all.

**Objects (same units, weeks and outcome as B3):** 49 Iberian and 44 Italian gas units, weekly unit means of `run20` over
predicted in-money hours (margin €50, essential units out), weeks 2021-10 → 2023-06 (`gas_cap_quantity_b1.panel`, `matrix`).

**Dose g_iw.** For a date D (the cap, 2022-06-15, or a placebo): unit i's own offer curve over the 8 weeks before D
(markups over gross cost, in-money hours, pooled by hour of day, all of the unit's hours if a cell has fewer than 5 days —
exactly B1's `ends`), F_i(x) = mean share of K offered at markup ≤ x. In each in-money hour from D on,
g = F_i(20) − F_i(20 − S_d); g_iw = its weekly mean; g = 0 before D.
- Iberia, real: S_d = the bid-time subsidy. Italy: the same Iberian S_d by date applied to the Italian unit's own curve
  (a would-be dose; Italian outcomes have no subsidy, so a slope on it is pure confound).
- Placebo D = P: S on P + k is the real S on 2022-06-15 + k, for P + k ≤ 2022-06-14.

**Estimator, per country:** y_iw = α_i + δ_w + b·g_iw, OLS on unit-weeks with an outcome, the 8 reference weeks before D
excluded (they built F, so keeping them invites regression to the mean). Full pass-through b = 0, none b = −1, ρ = 1 + b.
Triple difference: b_IB − b_IT. Inference: firm block bootstrap within country, 199 draws, seed 20261108, doses held fixed.

**Step 1 (this run): no ρ, and no post-cap outcome is read.**
(a) Spread, real dose, post-cap weeks with S > 0: mean g; median over weeks of the cross-unit sd of g_iw; share of the
variance of g_iw left after removing unit and week means (the identifying variation). Iberia and Italy (would-be).
(b) Placebos P = 2022-01-01 and 2022-03-01: b_IB, b_IT, b_IB − b_IT, each with 95% interval and MDE = 2.8 × bootstrap sd.

**Rules, fixed now:**
1. **Power.** STOP the design if the within-Iberia MDE exceeds 0.5 at either placebo (B1's "either" convention; 0.5 =
   telling ρ = 1 from ρ = 0.5). If only the triple difference's MDE exceeds 0.5 at either date, it can be a check, not the
   main estimate.
2. **Flatness.** Iberian placebo interval includes 0 at both dates → the within-Iberia slope is the main estimate, the
   triple difference a check. Iberian interval excludes 0 at either date but the triple difference includes 0 at both →
   the triple difference is the main estimate. Both exclude 0 at some date → STOP.
3. Step 2 (the real ρ) only after step 1 passes and its rule is written here.

**Limits stated in advance.** Placebo windows are short (about 23 and 15 weeks against 54 post-cap), so the MDE is
conservative. The 2022-01-01 placebo has about five Iberian weeks before its reference window (Iberia enters the money in
October 2021). The Iberian in-money sample is defined on net cost, so it widens at the cap; unit effects do not remove that.
About 10 Iberian firms bind the interval. This is a fifth design using Italy, though a different identifying variation
from B1–B3: say so in any write-up.

### K step 1 results (2026-11-08; `gas_cap_quantity_unit_dose.py`, 199 draws, seed 20261108; no ρ, no post-cap outcome read)

Files: `outputs/tables/gas_cap_quantity_unit_dose_{spread,placebo}.csv`. Units as B3: 49 Iberian (10 firms), 44 Italian (12).

**(a) The dose differs across plants.** Post-cap weeks with S > 0 (38):

| | mean g | median within-week sd | unit mean g, 10% / 90% | variance left after unit and week means |
|---|---|---|---|---|
| Iberia | 0.25 | 0.187 | 0.078 / 0.357 | 22.7% |
| Italy (would-be) | 0.14 | 0.180 | 0.002 / 0.301 | 20.6% |

**(b) Placebos** (b, 95% firm-block interval, MDE; 28 weeks each after dropping the reference window):

| placebo | Iberia | Italy (would-be) | triple (IB − IT) |
|---|---|---|---|
| 2022-01-01 | +0.061 [−0.014, +0.223], MDE 0.15 | −0.159 [−0.270, +0.015], MDE 0.20 | **+0.219 [+0.044, +0.386]**, MDE 0.25 |
| 2022-03-01 | −0.049 [−0.155, +0.111], MDE 0.19 | −0.123 [−0.745, +0.207], MDE 0.68 | +0.073 [−0.266, +0.729], MDE 0.70 |

**Reading, by the rules:**
- Rule 1 (power): within-Iberia MDE 0.15 and 0.19, under 0.5 at both → **passes**. The triple difference's MDE is 0.70 at
  2022-03-01 → **check only, not the main estimate**.
- Rule 2 (flatness): the Iberian placebo includes 0 at both dates → **the within-Iberia slope is the main estimate**.
- So step 1 passes; step 2 (the real ρ, within Iberia) needs its rule written here first.

**Worth noting, not decisive:** the Italian would-be slope is negative at both dates (−0.16, −0.12): Italian plants that
offered more capacity just around cost drift down relative to others over the following months, with no subsidy. Iberia
shows no such drift, so the triple difference at 2022-01-01 *excludes* 0 (+0.22) only because Italy moves. That is the
same lesson as before: Italy has its own dynamics, and here it would bias the triple difference, not the within-Iberia
slope. A reason to keep the triple difference as a check only, which the power rule already says.

### K step 2. The real ρ within Iberia — rules fixed before running (2026-11-08; user's go-ahead)

**Main:** D = 2022-06-15, real S, Iberian units, y_iw = α_i + δ_w + b·g_iw over every week 2021-10 → 2023-06 except those
overlapping the reference window (2022-04-20 → 2022-06-14; this drops the cap week too), g = 0 before the cap.
ρ = 1 + b; 95% firm block bootstrap (199 draws, seed 20261108, doses fixed).

**Checks, fixed now:**
1. **Unit trends (stop rule):** add a linear trend per unit. If that ρ falls outside the main 95% interval → STOP (the slope
   picks up plant-specific drift, not the subsidy).
2. **Timing permutation:** recompute g with the post-cap S path shifted cyclically by 1…k whole weeks (every shift that
   moves it), re-estimate b. One-sided p = share of shifted b ≤ real b. Binding only for a claim of incomplete pass-through:
   if the main interval excludes ρ = 1, that claim needs p ≤ 0.05, else it STOPS. If the interval includes 1, report p.
3. **Triple difference (check):** b_IB − b_IT with the Italian would-be dose, same bootstrap. Reported, not decisive
   (step 1: MDE 0.70, Italy drifts). Say whether it agrees with the main estimate.
4. **Reported beside, not decisive:** the reference weeks kept; the Iberian sample restricted in every week to hours
   in the money on *gross* cost (removes the sample's widening at the cap; same units, more missing cells).

**Reading, fixed now:** quote the main ρ beside B3's 0.73 [0.51, 1.03]. Say whether the intervals overlap; do not choose
between them on the point estimate. If the main interval is narrower than B3's (width 0.52) and checks 1–2 hold, it is the
sharper estimate and the one whose identification does not rest on Italy.

### K step 2 results (2026-11-08; `gas_cap_quantity_unit_dose.py --stage 2`, 199 draws → `gas_cap_quantity_unit_dose_rho.csv`)

49 Iberian units, 10 firms, 83 weeks, 3,307 unit-weeks.

| estimate | ρ | 95% |
|---|---|---|
| **main, within Iberia** | **0.87** | **[0.62, 1.03]** (width 0.41) |
| with unit trends (check 1) | 0.87 | [0.59, 1.10] — inside the main interval: holds |
| timing permutation (check 2) | 53 shifts, shifted 5th pct b −0.122, real b −0.134 | p 0.019 |
| triple difference (check 3) | 1.08 | [0.71, 1.36]; Italy's would-be b −0.21 [−0.47, −0.07] |
| reference weeks kept | 0.87 | — |
| gross-cost in-money sample | 1.02 | — (2,203 unit-weeks) |

**Reading, by the rules:** check 1 holds; the interval includes ρ = 1, so full pass-through is not rejected, and the
permutation (p 0.019) is reported, not binding. The interval (0.41) is narrower than B3's (0.52) and checks 1–2 hold, so
**this is the sharper estimate, and the one whose identification does not rest on Italy.** It overlaps B3's 0.73
[0.51, 1.03]; the point estimates differ by 0.14, inside both intervals — not told apart.
- On the sample whose in-money hours do not widen at the cap (gross cost), ρ is 1.02: the widening pulls the main estimate
  down, if anything. Reported only.
- The triple difference sits higher (1.08) because Italy's would-be slope is negative; see the drift below.

### K: the Italian drift (2026-11-08; descriptive, user asked; `gas_cap_quantity_unit_dose_drift.py` + a gas-price cut)

Why Italian plants with a high would-be dose drift down with no subsidy. Two things, both checked by dose terciles
(run20 minus each week's cross-unit mean):

1. **Regression to the mean, at the January placebo.** Italy's high tercile: +0.140 before the reference window, **+0.255
   in it** (Nov–Dec 2021), +0.119 after. The plants picked as high-dose were unusually high exactly in the weeks that
   picked them, and then went back. Iberia's high tercile shows a smaller bump (0.113 → 0.158 → 0.128). At the March
   placebo neither country shows a bump (Italy 0.220 / 0.197 / 0.190), and Italy's slope there is noise ([−0.75, 0.21]).
2. **The gap between high- and low-dose plants narrows when gas is dear — in Italy, before the cap too.** Weekly
   high-minus-low gap (terciles of the real-cap dose) against the gas price:

   | | pre-cap weeks | post-cap weeks |
   |---|---|---|
   | Italy vs PSV | corr −0.36, −0.18 per €100 | corr −0.62, −0.10 per €100 |
   | Iberia vs MIBGAS | corr −0.17, −0.04 per €100 | (treatment: not evidence) |

   After the cap the would-be dose rises with the gas price (S does), so this compression is what makes Italy's post-cap
   would-be slope −0.21. It is not cheap vs expensive plants: the dose is uncorrelated with plant cost (−0.16, −0.01); it
   is the plants that usually offer much capacity near cost (Edison, Eni, A2A, mostly NORD) offering less of it near cost
   when gas is dear.

**What it means for the main estimate.** Iberia's pre-cap compression is a fifth of Italy's per € and has no interval
(37 weeks, the reference weeks included, so mean reversion is mixed in). If it is real, it works in the same direction as
the effect: part of the within-Iberia b (−0.13) would be gas, not subsidy, and ρ would sit closer to 1. Rough size: at
S ≈ €100, b·g ≈ −0.13 × 0.25 = −0.034, and −0.04 per €100 of gas is the same order. So 0.87 is better read as a lower
end than a centre; it cannot be pushed below by this channel. **Corrected by step 3 (below): with the gas term ρ is 0.84, not
higher; the 'lower end' reading does not hold.** Not tested with a rule; a test would put weekly gas into
the within-Iberia regression interacted with each plant's dose curve.

### K step 3. Does gas itself move high-dose plants? — rules fixed before running (2026-11-08; user's go-ahead)

**The worry (from the drift):** plants that usually offer much capacity near cost may offer less of it near cost when gas
is dear, subsidy or not. After the cap the dose rises with gas, so that would load onto b and pull ρ down.

**Term added:** c · (gas_w × z_i), where z_i = F_i(20) − F_i(20 − 100) is the plant's dose at a fixed S = €100 from its
own reference curve (unit-level, all hours: time-invariant "near-cost mass"), and gas_w is the weekly mean of the daily
gas price lagged two days (prices final at bid time): MIBGAS for Iberia, PSV for Italy, in €100/MWh.
y_iw = α_i + δ_w + b·g_iw + c·gas_w·z_i, same weeks (reference window out), same 199 draws, seed 20261108.
c is identified mostly from weeks without a subsidy (38 pre-cap, ~17 after February 2023), where gas moves and g = 0.

**Reported:** ρ_gas = 1 + b with the term and its interval; c with its interval; c estimated on pre-cap weeks only (no
subsidy anywhere, the clean test); the correlation between g_iw and gas_w·z_i after removing unit and week means.
Italy (would-be dose, PSV): b and c with the term — if the term captures Italy's drift, Italy's b moves toward 0.

**Rules, fixed now:**
1. **Separability:** if the residual correlation between g_iw and gas_w·z_i exceeds 0.9 in absolute value → STOP, the two
   cannot be told apart; quote 0.87 with this as an unresolved caveat.
2. **c's interval excludes 0, negative** → the gas channel is present in Iberia: ρ_gas becomes the main estimate, 0.87 the
   version without it. **Includes 0** → not detected: 0.87 stays main, ρ_gas reported beside. **Excludes 0, positive** →
   opposite to the drift hypothesis: reported, 0.87 stays main.
3. The pre-cap-only c and the Italian rows are reported, not decisive.

### K step 3 results (2026-11-08; `--stage 3`, 199 draws → `gas_cap_quantity_unit_dose_gas.csv`)

z (near-cost mass at S = €100): Iberia mean 0.29, sd 0.21; Italy 0.18, sd 0.18. Residual correlation of g with gas·z:
Iberia +0.42, Italy +0.69 — separable (rule 1 passes).

| | b with the term → ρ_gas | c per €100 of gas × z | c, pre-cap weeks only |
|---|---|---|---|
| **Iberia** | −0.164 [−0.419, −0.011] → **0.84 [0.58, 0.99]** | **+0.09 [−0.21, +0.33]** | −0.01 [−0.17, +0.32] |
| Italy (would-be) | −0.064 [−0.276, +0.068] → 0.94 [0.72, 1.07] | −0.17 [−0.33, +0.05] | **−0.23 [−0.51, −0.04]** |

**Reading, by the rule:** c's interval includes 0 in Iberia → **the gas channel is not detected; ρ 0.87 [0.62, 1.03]
stays the main estimate**, ρ_gas 0.84 [0.58, 0.99] beside it.
- **The term does capture Italy's drift.** Italy's c is negative and, before the cap, excludes 0; with it in, Italy's
  would-be slope goes from −0.21 [−0.47, −0.07] to −0.06 [−0.28, +0.07]. So the drift found above is a gas response
  of near-cost plants, as described, and in Italy the term absorbs it.
- **In Iberia the point estimate has the other sign** (+0.09; −0.01 before the cap), and adding the term moves ρ down
  slightly (0.87 → 0.84), not up. The earlier guess that 0.87 is a lower end is wrong.
- **Power is limited:** Italy's c (−0.17 to −0.23) lies inside Iberia's interval, so an Italian-sized gas channel in
  Iberia is not excluded. What the data say is that Iberia shows no sign of it, and that controlling for it does not
  move ρ much either way (0.84–0.87).
- ρ_gas's interval just excludes 1 (upper end 0.99); the main interval includes it (1.03). The quote: pass-through
  0.84–0.87, near full, intervals reaching from about 0.6 to 1.
- Arithmetic only, not estimated with its own bootstrap: a triple difference with the term in both countries would be
  1 + (−0.164 + 0.064) ≈ 0.90.

### K step 4. Robustness of the headline, and a re-weighted triple difference — rules fixed before running (2026-11-08; user's go-ahead; literature in `notes/literature-triple-difference.md`)

The main estimate stays K step 2's ρ 0.87 [0.62, 1.03] unless a rule below says otherwise. Same units, weeks, doses,
bootstrap seed (20261108) and 199 firm-block draws unless stated.

**4a. Bound with Italy's gas response imposed.** Subtract c·gas_w·z_i from y with c fixed at Italy's −0.17 (full window)
and −0.23 (pre-cap), re-estimate b. Reported: answers "if Iberia reacted to gas as Italy did, where would ρ be?".

**4b. Split-sample near-cost mass.** z_early from the reference curve before 2022-01-01 (8 weeks to 2021-12-31), used as
an instrument for gas·z (2SLS, with g exogenous). Rule: if the IV c's interval excludes 0 and is negative, ρ from this
regression becomes the main estimate; otherwise 0.87 stays.

**4c. Imputation (Borusyak, Jaravel & Spiess; Strezhnev).** Plant effects estimated only from untreated weeks (pre-cap
outside the reference window, and post-cap weeks with S = 0), then (y − α_i) on g with week effects over dosed weeks.
Rule: reported; if b falls outside the main interval, say so and quote both.

**4d. Heterogeneity (Caron; Callaway, Goodman-Bacon & Sant'Anna).** The slope across plants is causal only if plants with
different doses would respond alike to the same dose (no selection on gains). Separate b for terciles of (i) the plant's
mean post-cap dose, (ii) plant efficiency; and Spain vs Portugal; per firm, point estimates and each firm's share of the
regression's weight (its share of Σ residualised g²). Rule: if the 95% interval of any tercile difference (top minus
bottom) excludes 0, state that 0.87 is a weighted average, give the weights, and quote the tercile estimates beside it.

**4e. Inference with 10 clusters (MacKinnon et al.).** Besides the firm-block bootstrap: CV3 (leave-one-firm-out
jackknife) standard error with a t(G − 1) interval; wild cluster restricted bootstrap with Webb six-point weights, 9,999
draws, interval by test inversion, and p-values for ρ = 1 and ρ = 0. Rule: quote the widest of the three intervals.

**4f. Honest bound (Rambachan & Roth, relative magnitudes, conservative form).** Let V = the largest absolute Iberian
placebo slope from step 1 (0.061). Allow a post-cap bias in b of up to M̄·V and widen the interval of 4e by that on each
side, for M̄ = 0.5, 1, 2. Reported; it is the union-bound version, wider than their optimal interval.

**4g. Re-weighted triple difference (Leventer; Ortiz-Villavicencio & Sant'Anna).** Italian units kept at the 50%
missing-week rule (Iberia stays at 30%). Italian plants entropy-balanced (Hainmueller) to Iberia's means of: plant mean
dose after the cap (would-be for Italy), near-cost mass z, efficiency. Gas·z term per country. b_IT on the weighted Italian
regression; triple ρ = 1 + b_IB − b_IT, bootstrap within country.
- Placebos first (2022-01-01, 2022-03-01), same weights, gas term in: the triple ρ is read only if its placebo MDE ≤ 0.5
  at both dates and both placebo intervals include 0. Otherwise STOP at the placebos.
- If read, it is a check on 0.87, never the main estimate (fixed now): say whether the intervals overlap.
- Balance is reported (weighted Italian means against Iberian) and the effective number of Italian plants.

### K step 4 results (2026-11-08; `gas_cap_quantity_unit_dose_robust.py`, 199 draws, 9,999 wild draws → `gas_cap_quantity_unit_dose_robust.csv`, `_triple_balance.csv`)

| | ρ | 95% | rule |
|---|---|---|---|
| main (step 2, reproduced) | 0.87 | [0.62, 1.03] | |
| 4a Italy's c imposed (−0.17 / −0.23) | 0.92 / 0.94 | [0.61, 1.09] / [0.65, 1.08] | reported |
| 4b 2SLS, gas·z instrumented by the early near-cost mass | 0.72 | [0.23, 1.00]; c +0.47 [−0.33, +1.85]; z vs z_early corr 0.62 | c not negative-significant → 0.87 stays |
| 4c imputation (plant effects from untreated weeks) | 0.86 | [0.49, 1.02] | inside the main interval |
| 4d dose terciles low / mid / high | 1.03 / 0.81 / 0.90 | high − low in b −0.12 [−0.52, +0.23] | no difference detected |
| 4d efficiency terciles low / mid / high | 0.86 / 0.89 / 0.83 | high − low −0.03 [−0.16, +0.20] | no difference detected |
| 4d Spain (40 units) / Portugal (9) | 0.87 / 0.84 | [0.61, 1.08] / [0.49, 1.09] | |
| 4e CV3 jackknife, t(9) | 0.87 | [0.62, 1.11] | |
| 4e wild cluster restricted, Webb | 0.87 | **[0.48, 1.00]**; p(ρ = 1) 0.054, p(ρ = 0) 0.0004 | **widest → quoted** |
| 4f honest bound, M̄ = 0.5 / 1 / 2 | 0.87 | [0.45, 1.03] / [0.42, 1.06] / [0.36, 1.12] | reported |
| 4g re-weighted triple difference | — | placebos: 2022-01-01 b +0.66 [+0.11, +1.15], MDE 0.83; 2022-03-01 +0.70 [−0.21, +1.66], MDE 1.53 | **STOP at the placebos** |

**Reading, by the rules:**
- **The headline stays ρ 0.87, now quoted with the wild-bootstrap interval [0.48, 1.00]** (the widest of the three).
  Full pass-through sits at the edge (p 0.054); ρ = 0 is firmly rejected. The CV3 interval reaches 1.11, so the upper end
  depends on the method: say "about 0.5 to 1".
- **No sign of selection on gains** (Callaway, Goodman-Bacon & Sant'Anna; Caron): plants with high and low doses, and
  efficient and inefficient plants, give the same ρ within noise. The tercile intervals are wide (each about ±0.3), so
  this is "not detected", not "ruled out".
- **The gas channel cannot pull ρ down much.** Imposing Italy's response *raises* ρ (0.92–0.94). The split-sample IV
  gives a positive, very imprecise c and ρ 0.72 [0.23, 1.00]: the early near-cost mass is only a moderate instrument
  (correlation 0.62), and the estimate is too wide to inform.
- **Firms:** Iberdrola carries 34% of the regression's weight and has the lowest firm ρ (0.51, own slope); Naturgy 17%,
  TotalEnergies 15%. Leaving one firm out gives 0.79 (without Iberdrola) to 0.94 (without Endesa).
- **The triple difference cannot be rescued.** Matching Italy to Iberia's doses needs extreme weights: Italian plants'
  would-be dose averages 0.13 against Iberia's 0.25, so balancing leaves **5.7 effective plants of 54** (largest weight
  18). Its placebos then fail on both counts (January excludes 0; both MDEs above 0.5). Italy has too few plants that
  look like Iberia's, which is what the conduct comparison found too (`7611791`). It stays out of the paper except as
  a reported failure.

### K step 5. Unweighted triple difference with gas terms and a gap before the reference window — rules fixed before running (2026-11-08; the user asked for it after 4g stopped)

**Declared:** the **sixth specification using Italy** (B1, B2, B3, K's step-1 triple, 4g, this one), chosen after seeing
4g fail. Any write-up must list all six. It can corroborate the headline; it can never replace it.

**Changes from 4g:** no entropy weights (overlap was the failure); Italian units at the 50% missing-week rule as in 4g;
gas·z term per country (MIBGAS / PSV, as step 3); the reference curve (dose and z) built from the 8 weeks ending
**4 weeks before** D, and both the reference and the 4 gap weeks dropped from the regression, against the regression to
the mean seen at the January placebo. The same construction in both countries; so Iberia's b here differs slightly from
the headline's.

**Placebos first** (2022-01-01, 2022-03-01; S path shifted as in step 1): triple b = b_IB − b_IT with 95% firm-block
interval (199 draws within country, seed 20261108) and MDE = 2.8 × bootstrap sd.
**Rule:** read the triple ρ only if both placebo intervals include 0 **and** both MDEs are ≤ 0.5. Otherwise STOP.
**If read:** ρ_triple = 1 + b_IB − b_IT with interval; Italy's b alone (the falsification test); say whether the interval
overlaps the headline's [0.48, 1.00]. Check only.

### K step 5 results (2026-11-08; `gas_cap_quantity_unit_dose_triple.py`, 199 draws → `gas_cap_quantity_unit_dose_triple.csv`)

| placebo | Iberia b | Italy b | triple b | MDE |
|---|---|---|---|---|
| 2022-01-01 (48 / 55 units) | +0.056 [−0.027, +0.148] | −0.015 [−0.202, +0.259] | +0.071 [−0.211, +0.274] | 0.37 |
| 2022-03-01 (49 / 56 units) | −0.012 [−0.141, +0.200] | −0.170 [−0.490, +0.225] | +0.159 [−0.280, +0.592] | **0.62** |

**Reading, by the rule: STOP.** Both placebos are now flat — the gas term and the gap removed the January failure
(step 1: +0.22 excluding 0; here +0.07 [−0.21, +0.27]) — but the March MDE is 0.62, above 0.5. The triple ρ is not read.
What limits it is Italian noise around the March 2022 break (Italy's own interval at that date spans 0.7). The design
is now valid in its assumptions as far as the placebos can tell, but cannot tell ρ = 1 from ρ = 0.4 at that date.
In the paper: six Italian specifications, the last with flat placebos and insufficient power; Italy's role is the
falsification test (step 3: would-be slope −0.06 [−0.28, +0.07] with the gas term).

## L. Dispatch response: did the subsidy make gas plants run more? — rules fixed before running (2026-11-08; user chose it, Italy included)

**Question.** The welfare section (J) re-clears the offer curves, so it assumes subsidised plants were dispatched exactly
by merit order. This measures the realised dispatch shift and compares it with that mechanical one.

**Objects, per plant and hour, 2021-10-01 → 2023-06-30, all hours:**
- **Outcome** y = output / K: Iberia, PDBF schedule summed over role codes (auction + bilateral); Italy, GME accepted
  sell quantity (status ACC, bilateral rows included). K = 99th percentile of hourly offered MW before the cap (the
  panel's K). Weekly plant mean.
- **Margin** x = same zone-hour price the day before − the plant's bid-time gross cost (Iberia ES/PT price; Italy the
  unit's zonal price).
- **Dose** flip(S) = 1[x ≤ 0 < x + S]: the subsidy moves the plant from out of the money to in it. g_iw = weekly mean
  of flip(S_d) after the date, 0 before. Italy: the Iberian S_d applied (would-be dose).
- **Near-margin propensity** z_i = mean flip(€100) over the plant's hours from 2021-10-01 to the day before the date.
- **Controls** (weekly, standardised, each × z_i, per country): Iberia: MIBGAS (lag 2); peninsular demand − wind − solar
  D-1 forecasts (ESIOS 1775 − 1777 − 1779); stored hydro energy (ESIOS 623). Italy: PSV (lag 2); national accepted
  purchases (GME BID ACC); implicit net imports (accepted purchases − accepted sales). **Limit:** Italy has no wind,
  solar or hydro series on disk, so its drought channel is only proxied through demand and imports.
- **Mechanical benchmark** m (per country, pre-cap): within plant-week, the slope of hourly y on 1[x > 0]. Merit-order
  dispatch predicts b ≈ m; κ = b / m is the share of the mechanical shift realised.
- **Estimator:** y_iw = α_i + δ_w + b·g_iw + Σ c_k·control_kw·z_i, per country. Triple: b_IB − b_IT. Firm-block bootstrap
  within country, 199 draws, seed 20261108. Italian essential units out; plants with output data in ≥ 70% of weeks.

**Step 1 (this run): no post-cap estimate.**
(a) Overlap: plant mean post-cap dose and z, Iberia vs Italy (quantiles); entropy-balance Italian plants to Iberia's
means of both; effective number of Italian plants.
(b) Italy and Iberia, monthly mean capacity factor Sep 2021 → Jun 2022: is there a March 2022 break in Italian dispatch?
(c) m for each country.
(d) Placebos 2022-01-01 and 2022-03-01 (S path shifted as in K): b_IB, b_IT, triple; 95% intervals; MDE = 2.8 × sd.

**Rules, fixed now:**
1. **Within Iberia (main):** STOP if its placebo interval excludes 0 at either date or its MDE exceeds 0.5·m_IB at either.
2. **Triple (check, seventh specification using Italy, first on this outcome):** read in step 2 only if the effective
   number of Italian plants is ≥ 20, both triple placebo intervals include 0, and both triple MDEs are ≤ 0.5·m_IB.
   Otherwise it is reported as not usable, and Italy's own placebo slope serves as the falsification test.
3. (b) is descriptive and decides nothing.

### L step 1 results (2026-11-08; `gas_cap_dispatch_dose.py`, 199 draws → `gas_cap_dispatch_dose_{overlap,monthly,placebo}.csv`): STOP

Iberia 55 plants (12 firms), Italy 71 (13). Implementation detail not in the rule: ESIOS 623 storage lagged two weeks
(its publication delay).

- **(c) Mechanical benchmark is small:** m = 0.067 (Iberia), 0.137 (Italy). Within a plant-week, hours predicted in the
  money by yesterday's price run only 7 points of capacity more than hours predicted out of it: combined cycles run in
  blocks across days, and yesterday's hourly price is a weak predictor of a given hour's dispatch.
- **(a) The dose barely differs across Iberian plants:** plant mean post-cap dose 0.47 (10th pct) to 0.52 (90th). In
  2022 the gross cost of every Iberian CCGT sat above the price in most hours and within S of it, so the subsidy
  "flips" about half the hours of every plant alike. Italy's would-be dose is 0.12–0.26; entropy balancing leaves
  **2.0 effective Italian plants** (largest weight 35).
- **(b)** Italian capacity factor 0.41–0.46 to March 2022, then 0.30–0.32 in April–May; Iberia 0.10–0.29, with no common
  break. Descriptive.
- **(d) Placebos:** every interval includes 0, but within-Iberia MDE 0.87 at both dates = **13× m**; triple MDE 15× m.

**Reading, by the rules: rule 1 STOP (MDE far above 0.5·m); rule 2 triple not usable (overlap 2.0 < 20, MDE).** The
dispatch effect cannot be measured with this dose: the subsidy hit every Iberian combined cycle's hourly margin almost
equally, so there is no cross-plant variation to use, and the hourly in-money flag barely predicts dispatch. The welfare
section's dispatch shift stays an assumption of the re-clearing model, stated as such. Italian wind, solar and hydro
data would not change this: neither failure involves the Italian controls.

## M. Regulated cogeneration as an untreated group — feasibility count (2026-11-08; descriptive, user asked)

The decree (RDL 10/2022 art. 2.1.c) subsidised gas cogeneration only **without** a regulated remuneration regime (RECORE);
cogeneration inside RECORE burned the same gas, sold in the same auction and got nothing. Art. 2.2 also excludes
bilateral-contract energy, but combined cycles schedule 0.0–0.2% of their output bilaterally in every month 2021-06 →
2023-12 (0–2 units): that exclusion is empty.

Cogeneration = OMIE listing technology "RE Mercado Térmica no renovable" (858 units listed 2022-02-08, 443 on 2023-05-16).

| | count / volume |
|---|---|
| Units first seen 2022-05-13 → 2023-03 (new registrations, art. 3.1), or named "…MECANISMO" (4) | **81** |
| Their output (PDBF, mean MW) | 5 (Jun 2022) → 124 (Nov 2022) → 218–277 (2023) |
| All other cogeneration units: output | 3,419 MW (Jan 2022) → **1,387 (Sep 2022)** → 2,467–2,777 (2023) |
| Offered at ≤ €1/MWh, April 2022 / Nov 2022 | others 80% / 80%; new eligible 93% |
| JRC efficiency: units matched / plant-specific | 7 / **0** |
| Declaring a minimum-income variable term (cab, April 2022) | 1 of 280 |

**Reading:**
1. **Eligibility is not observed for most cogeneration.** Only 81 units are visibly new; eligible plants that already bid
   through single-plant units only had to be *identified* to OMIE and REE (art. 3.3), which leaves no trace in the
   public files. So "the rest" mixes eligible and ineligible plants. OMIE holds the list (agents notified it).
2. **Cogeneration offers as a price-taker** (80–93% of offered MW at ≤ €1): capacity near cost (run20) does not describe
   it, so it cannot serve as a control for the combined cycles' ρ on that outcome.
3. **No plant cost**: no plant-specific efficiency and almost no declared cost. A cost could be **constructed** from the
   regulatory "instalaciones tipo" parameters of RD 413/2014 (efficiency by power range and fuel, published by ministerial
   order), but only per type, not per plant.
4. **Its own shock**: output of the non-new cogeneration fell 3.4 → 1.4 GW from January to September 2022 — the 2022
   cogeneration shutdown as gas rose faster than the regulated operating payment — so it is not an untouched group either.

Feasible use: an **output (participation) comparison** of eligible vs RECORE cogeneration, once OMIE supplies the list of
units identified as beneficiaries with dates. That measures whether the subsidy kept plants running, not ρ.
