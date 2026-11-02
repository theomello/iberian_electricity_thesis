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
