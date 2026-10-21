# Own wind as the shock: running note

Design: `docs/specs/2026-10-21-own-wind-quantity-test-design.md`. Plan:
`docs/plans/2026-10-21-own-wind-quantity-test-step1.md`. Script `analysis/own_wind_quantity_test.py`
(`--panel`, `--test --step 1`), check `qa/check_own_wind_quantity.py`. Outputs:
`own_wind_quantity_panel.parquet` (gitignored), `own_wind_quantity_step1.csv`. Logs
`.superpowers/sdd/2026-10-21-own-wind-quantity-test-step1/`.

## Step 1 (2026-10-21): STOP. The instruments cannot separate the wind from its price effect

**In one line.** Where a firm's farms sit moves its scheduled wind strongly, but less in steep
hours. So the slope-scaled instrument adds no movement of its own. The test cannot tell "cut
with the wind" (book balancing) from "cut with the wind's price effect" (market power): both
first-stage F are below 10 (3.7 and 2.5), and the smallest detectable β is 2.1. The outcome
regression (b_W, b_P) was not formed.

**By example.** Galicia is windier than the peninsula, by enough to give Iberdrola 100 MW more on
its located farms. Iberdrola then schedules about 115 MW more wind (first stage 1.15, t 30). The
test also needs that wind's price effect, P_W = W_s / |RD′|, to move on its own:
- in a steep hour (|RD′| 30 MW per €/MWh), 100 MW is a €3.3 move along the firm's residual demand;
- in a flat hour (900), it is €0.11.

If the 1.15 held in every hour, Wdev / |RD′| would carry that difference. It does not:
- in steep hours own wind follows its regional deviation less (W_s on Wdev / |RD′| −22.7, t −7).
  At the steepest 1% of hours (1/|RD′| ≥ 0.033) the response falls to about 0.4;
- once Wdev is in, P_W does not move with Wdev / |RD′| (0.04, se 0.10). About 1.15 would be
  expected if the response were the same in every hour.

**The panel.** The holiday quantity panel's 199,840 firm-hours with a slope and an own offer slope,
less 165 without own wind: **199,675 firm-hours, 1,758 weekdays**. Other generation + own wind +
generic units equals the holiday panel's generation on every row, by leg (0.0000 MW).

| | EDP | Endesa | Iberdrola | Naturgy | Repsol |
|---|---|---|---|---|---|
| own scheduled wind, MW | 558 | 656 | 1,259 | 431 | 206 |
| … bilateral share | 0% | 19% | 71% | 35% | 24% |
| located own wind (W_real), MW | 394 | 587 | 1,359 | 472 | 90 |
| sd of its regional deviation, MW | 38 | 82 | 160 | 71 | 57 |
| corr(schedule, located wind) | 0.91 | 0.88 | 0.91 | 0.85 | 0.79 |

**Step 1.** Date × hour and firm × month effects; controls 1/|RD′|, own retail purchases, a slope
per firm on each D-1 forecast (wind, solar, demand); date clusters.

| | on Wdev | on Wdev / \|RD′\| | Sanderson–Windmeijer F |
|---|---|---|---|
| first stage: own wind W_s | **1.148 (0.039)** | **−22.7 (3.3)** | **3.7** |
| first stage: P_W = W_s / \|RD′\| | 0.0045 (0.0006) | 0.04 (0.10) | **2.5** |
| placebo: own retail purchases | **+0.060 (0.016)**, t 3.8 | +0.79 (1.38) | |

| power (b_P = 0) | se(b_P) | s̄ (MW per €/MWh) | smallest detectable β |
|---|---|---|---|
| other generation | 47.2 | 62.0 | **2.13** |
| … auction | 39.8 | 62.0 | 1.80 |
| … bilateral | 38.8 | 62.0 | 1.75 |

**Stop rule: STOP** on all three counts (both F < 10, smallest detectable β > 1).

- **Why the interaction is weak.** 1/|RD′| is heavy-tailed: median 0.0035, 99th percentile 0.033.
  The steepest 1% of hours carry 23% of Wdev / |RD′|'s variation, and in those hours own wind
  responds least. Why it responds less there is not checked.
- **The placebo moves.** A firm buys 0.06 MW less for its own customers per MW of extra regional
  wind (regional weather moves load too). That is small next to the 1.15, and retail purchases
  are a control, but it is not zero.
- **What it settles.** As designed, own wind cannot test β: its regional deviation moves the wind
  but not the wind's price effect separately.

**Variants (each needs a yes; neither is in the design yet):**
1. **Own wind alone.** b_W only, instrumented by Wdev (one regressor, one instrument, the
   t-30 first stage). This tests book balancing on the output side: does a firm cut its other
   plants when its own wind blows, and through which leg? Book balancing predicts the bilateral
   leg, market power the auction. It gives no β.
2. **Slope groups.** Instruments Wdev × each tercile of 1/|RD′|. This lets the wind's response
   differ by slope group and identifies b_P from how the cut per MW changes from flat to steep
   hours, without forcing the response to be linear in 1/|RD′|. Its F and power are unknown
   until step 1 is rerun with it.
