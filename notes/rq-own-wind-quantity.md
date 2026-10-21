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

## Step 1 with slope groups (2026-10-21, design §8): STOP on power, narrowly

`--test --step 1 --slope-groups` → `own_wind_quantity_step1_groups.csv`; log `step1_groups.log`.

**In one line.** Letting the wind's response differ by thirds of each firm's hours (flat, middle,
steep) fixes the instruments (F 53 and 39). But the test still could not tell β = 0 from β = 1:
the smallest detectable β is **1.16** (auction 1.07, bilateral 1.10) against a limit of 1. The
outcome regression was not formed.

| slope group | mean 1/\|RD′\| | median slope, MW per €/MWh | own wind per MW of Wdev |
|---|---|---|---|
| 1 flat | 0.0014 | 724 | **1.33 (0.07)** |
| 2 middle | 0.0037 | 283 | **0.87 (0.02)** |
| 3 steep | 0.0120 | 107 | **0.84 (0.03)** |

- **The instruments now work**: Sanderson–Windmeijer F 53.0 (own wind), 38.9 (its price effect).
  In steep hours the price effect per MW of wind is 9 times the flat hours'. The wind's response
  is lower there (0.84 against 1.33), but it does not collapse.
- **Power**: se(b_P) under b_P = 0 is 25.7, against Nash −62.0 (s̄): smallest detectable β 1.16.
  That is a standard error on β of about 0.41, wider than the holiday quantity test's (about
  0.18: β −0.20 [−0.55, +0.15]).
- **Placebo**: own retail purchases on Wdev by group +0.03 (t 1.6), +0.09 (t 4.4), +0.07 (t 3.7).
  These are small, and retail is a control, but regional wind moves own load too.

**What it settles.** Own wind is a strong shock to a firm's output (t 20–36 in every slope group).
As a test of β it is less precise than the holidays, and below the design's power threshold.
Step 2 is not run.

**Left (each needs a yes):** variant 1 above (own wind alone: the cut per MW of own wind and its
leg; no β). It tests book balancing on the output side with a strong instrument. Pooling this
shock with the holidays into one β (the program's step 3) would be dominated by the holidays.

## Own wind alone (2026-10-21, design §9): a cut of 0.2 per MW, on the bilateral leg

`--alone` → `own_wind_quantity_alone.csv`; log `alone.log`. One regressor (own wind W_s), one
instrument (Wdev); date × hour and firm × month effects, the same controls, date clusters.

**In one line.** When a firm's own wind blows, it schedules **0.20 MW less from its other plants
per MW** (t 3.3). The cut is all on the bilateral leg; the auction does not move. That is half of
what full physical book balancing predicts, and about what market power at β = 1 predicts. With
firm × date effects it halves again and is no longer significant.

**First stage.** Own scheduled wind rises 1.00 MW per MW of Wdev (0.025, F 1,610). Of the extra
wind, **41% goes under the bilateral contract** and 59% to the auction.

Per MW of own wind:

| outcome | b_W (se) |
|---|---|
| **other generation, total** | **−0.20 (0.06)** |
| … auction | +0.01 (0.06) |
| … bilateral | **−0.21 (0.06)** |
| storage hydro | −0.10 (0.04) |
| thermal (gas, coal) | −0.08 (0.03) |
| nuclear | −0.04 (0.03) |
| the rest | +0.02 (0.01) |
| generic units (resold purchases) | −0.07 (0.01) |

| reference (design §9) | per MW of own wind | observed |
|---|---|---|
| price-taking | 0 | total −0.20: rejected (t 3.3) |
| book balancing, physical | −0.41 (the bilateral share), bilateral | about half, bilateral |
| market power, β = 1 | −0.22 (r = s/\|RD′\|), auction | auction +0.01 (0.06): rejected, 3.9 se |

**Checks on the total** (auction / bilateral in brackets):

| | total | auction | bilateral |
|---|---|---|---|
| main | −0.20 (0.06) | +0.01 | −0.21 |
| **firm × date effects** | **−0.09 (0.06)** | −0.06 (0.05) | −0.03 (0.04) |
| Spanish price above €5 | −0.28 (0.07) | −0.01 | −0.27 |
| 2022 on | −0.32 (0.08) | −0.06 | −0.27 |
| forecast version of Wdev | −0.17 (0.06) | −0.00 | −0.17 |
| week clusters | −0.20 (0.08) | +0.01 | −0.21 |

**By firm** (one regression, own wind × firm instrumented by Wdev × firm):

| firm (F) | total | auction | bilateral | book balancing ref. | Nash ref., β = 1 |
|---|---|---|---|---|---|
| Iberdrola (985) | **−0.27 (0.10)** | −0.02 (0.09) | **−0.24 (0.09)** | −0.52 | −0.40 |
| Repsol (1,386) | **−0.52 (0.13)** | **−0.40 (0.15)** | −0.12 (0.08) | −0.29 | −0.03 |
| Endesa (1,013) | −0.07 (0.32) | +0.53 (0.40) | −0.59 (0.32) | 0.00 | −0.08 |
| Naturgy (2,216) | +0.29 (0.18) | +0.13 (0.18) | +0.16 (0.09) | −0.32 | −0.05 |
| EDP (207) | +2.07 (0.86) | +1.66 (0.87) | +0.41 (0.43) | +0.04 | −0.36 |

**Reading it.**
- **A firm does cut its other plants when its own wind blows**: hydro and gas, about 0.2 MW per
  MW. Price-taking is rejected in the main specification and in every check but one.
- **The size does not separate the two stories.** It is half of full physical book balancing
  (−0.41) and close to market power at β = 1 (−0.22). The slope test was the one that could
  separate them, and it lacked power (above).
- **The leg points to book balancing, with a caveat.** The cut is where the extra wind is labelled
  bilateral, and the auction cut that market power predicts is rejected (3.9 se; 3.2 se with firm
  × date effects). But the leg is partly a label. A firm that cut bilateral output and let its
  retailer buy the gap in the auction would lower its net position just as an auction cut does.
  The retailer's legs were not examined.
- **Within a firm's day the cut is small** (−0.09, t 1.6). The cut comes from windy against calm
  days, not windy against calm hours of the same day. That fits hydro planned over the day (the
  day's water budget follows the day's own wind, and its hourly profile follows prices). It also
  fits a confounder that varies by day. The rain story predicted the opposite direction (rain
  raises hydro), so it does not explain the halving.
- **Iberdrola carries the pooled result** (−0.27, on its bilateral leg: about half its book
  balancing reference). Repsol's cut is in the auction (−0.52), against a Nash reference of
  −0.03; its located wind is 28% of its capacity, in one region. Unexplained. EDP's other output
  *rises* with its own wind (+2.1, se 0.86; the weakest first stage). Its farms and its hydro
  share the wet north-west, so this is where rain would show. Endesa and Naturgy are noise.

**What it settles.** Own wind adds the output side to the holiday result. Firms cut other output,
mostly hydro, by about 0.2 MW per MW of their own wind, through the bilateral leg, and not the
auction cut that market power at β = 1 predicts. It is weaker evidence than the holidays: it
does not separate the stories by size, and within the day it fades. No β.
