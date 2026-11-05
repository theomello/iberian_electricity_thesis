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

## Net position and the retail legs (2026-11-05)

Script `analysis/own_wind_net_position.py` (`--verify`, then `--run`); outputs
`outputs/tables/own_wind_net_position{,_by_firm,_checks,_decision,_levels}.csv`. Same panel, instrument,
effects and clusters as "Own wind alone" above, so the numbers are comparable.

### Rules (written 2026-11-05, before the run that produces results)

**The question, by example.** Iberdrola's own wind is 100 MW higher in an hour. "Own wind alone" found it
schedules about 20 MW less from its hydro and gas, all in bilateral contracts, and nothing different in the
auction. Three things could be behind that, and generation alone cannot tell them apart:
- *The retailer did nothing* (retail purchases unchanged): the firm swapped hydro for wind in its own
  bilateral contracts and sold the rest of the wind. That is physical book balancing.
- *The retailer bought the 20 MW back in the auction* (its auction purchases up 20, its bilateral purchases
  down 20): the firm's net sales to the auction fell by 20 MW, exactly as an auction cut would. The
  bilateral cut was then a label on a net-position cut. This is the caveat in "Own wind alone".
- *The retailer's purchases fell by 20* with the generation (the cut was relabelling, net position
  unchanged).

Only the retail legs and the net position can say which. Acronyms: PDBF (*Programa Diario Base de
Funcionamiento*, the daily operating schedule: auction result plus bilateral contracts); PDBC (*Programa
Diario Base de Casación*, the day-ahead auction result); 2SLS (two-stage least squares); |RD′| (the slope of
the firm's residual demand, MW per €/MWh); Wdev (the firm's located wind capacity times its regions'
capacity-factor deviation from the peninsula, the instrument).

**Quantities** (MW, hourly, sold +; the panel `own_wind_quantity_panel.parquet` unchanged, 199,675 firm-hours).
Every leg is PDBF, the "auction" leg being PDBF rows with role code other than 4 and "bilateral" role code 4.
Checked on May 2023 against the cleared (status C) rows of `curva_pbc_uof`: the non-bilateral PDBF equals the
cleared auction quantity in 99.92% of 1.08 M unit-periods (within 0.15 MW), so "auction" is PDBC. Firms are
the five of the panel (unit to its largest owner that day, `lib/unit_ownership.py`), with regulated
pass-through suppliers excluded (`exposed=True`, `lib/omie_owner.py`), as in every firm panel.
- `R_a`, `R_b`, `R` = the firm's retail units' purchases (registry role `purchase_retail`) in the auction, in
  bilateral contracts, and both. **Positive = bought** (the panel stores them negative).
- `O_a`, `O_b`, `O` = its other purchases and pumping, by leg, positive = bought.
- Net position by leg, `N_auc`, `N_bil`, `N_tot` = all sales minus all purchases (generation incl. own wind and
  generic units, less R and O).
- **Net position excluding own wind**, `NX_x = N_x − W_s_x` for x = auction, bilateral, total. This is the
  object to test: it is what the firm does with everything that is not its own wind. `N_*` (with the wind in)
  are reported next to it; they equal `NX_* + (extra wind)` and add nothing to the reading.
- `A`, `A_auc`, `A_bil` = other generation, from "Own wind alone" (`G_other*`), unchanged.
Identity: `NX_x = A_x + generic_x − R_x − O_x` by leg; checked to 0.01 MW before anything is read.

**Estimator.** Each outcome on own scheduled wind `W_s`, instrumented by `Wdev`; date × hour and firm × month
effects, date clusters; controls 1/|RD′| and one slope per firm on each D-1 forecast (wind, solar, demand).
**One change, forced:** the original controls include own retail purchases. For any outcome that contains a
retail leg (R_a, R_b, R, N_*, NX_*) that control is the outcome itself, so it is **dropped (control set C0)**.
Other generation is estimated under both: C1 (the original, to reproduce −0.20) and C0, so the comparison
with the retail outcomes is on identical controls. A check re-runs the new outcomes under C1 and labels it a
bad control. The rest of the checks are those of "Own wind alone".

**References, per MW of own wind** (b for each outcome; computed in the script from the data: `s_b` the
bilateral share of the extra wind, `r` the Nash cut s/|RD′| weighted by |Wdev|, `x` the observed bilateral
cut of other generation, −b(A_bil) under C1):

| outcome | price-taking | (i) physical book balancing | (ii) market power β = 1 | (iii-a) label, net unchanged | (iii-b) retailer buys back |
|---|---|---|---|---|---|
| R_a (retail auction) | 0 | 0 | 0 | 0 | **+x** |
| R_b (retail bilateral) | 0 | 0 | 0 | −x | **−x** |
| R (retail total) | 0 | 0 | 0 | −x | 0 |
| NX_auc | 0 | 0 | **−r** | 0 | **−x** |
| NX_bil | offset* | **−s_b** | 0 | 0 | 0 |
| NX_tot | 0 | −s_b | −r | **0** | −x |

\* Price-taking predicts the total A = 0 with any bilateral fall offset by an auction rise (design §9), so NX_auc
and NX_bil move by opposite amounts that the theory does not fix.
(ii) and (iii-b) give the same net auction position; they differ in the route (generation withheld, or retail
buying more). For the firm's market power the net position is what matters, so **(iii-b) counts as market
power in the net-position sense**, and it is the only way "no auction cut" in generation survives a Nash firm.
**Baseline for R:** step 1's placebo found a firm buys about 0.06 MW less for its customers per MW of extra
regional wind (regional weather moves load); read R_b, R_a and R against −0.06, not against 0.

**Gates (stop before anything is read):**
- G1 first-stage F ≥ 10 pooled (it was 1,610); by firm, a firm with F < 10 is reported but not read.
- G2 data: the legs rebuilt from PDBF for May 2023 equal the panel to 0.01 MW; excluding pass-through
  suppliers changes the retail leg (so the exclusion is live); the identity above holds to 0.01 MW.
- G3 power: 2.8 × se(NX_auc) ≤ r. If not, STOP: the net auction position cannot tell 0 from the Nash cut.

**Reading, pooled, C0, 95% intervals b ± 1.96 se, in this order:**
1. NX_auc interval excludes 0 (below): the firm's net sales to the auction fall with its wind.
   - R_a ≥ +0.10 with interval above 0: **(iii-b) retailer buys back**; counts as market power in net terms.
   - else A_auc interval below 0: **(ii) generation withheld in the auction**. (Already rejected in
     "Own wind alone", +0.01 (0.06) against −0.22.)
   - else: net auction falls, route not identified.
   Also report whether the interval holds −r (Nash) or −x.
2. NX_auc interval contains 0 and excludes −r:
   - R_a interval contains 0 with |b| < 0.10, and NX_bil interval below 0: **(i) physical book balancing**;
   - else NX_tot interval contains 0 and A interval below 0: **(iii-a) label only**;
   - else: no net auction change, legs unclear.
3. NX_auc interval contains both 0 and −r: **inconclusive**, a stop for the net-position question.
The 0.10 is about half the observed bilateral cut and half of Nash: a material share of either, chosen here.

**By firm:** Iberdrola, Repsol, Endesa, Naturgy, EDP; W_s × firm instrumented by Wdev × firm in one
regression; the same outcomes, firm-specific references (own s_b, r_g, x_g), the same reading applied to each
firm. Five firms and several outcomes: **one firm crossing a threshold is weak; a claim about a firm needs its
own NX_auc interval to exclude 0 AND its reading to survive the firm × date check, or two firms to agree.**
Firms with F < 10 are not read.

**Checks the reading must survive** (NX_auc, R_a, R_b, NX_tot, A): firm × date effects; Spanish price above €5;
2022 on; Wdev_fc as the instrument; week clusters; original controls C1. The reading is "stable" if it is the
same in at least 5 of the 6. "Own wind alone" found the cut halves with firm × date effects; if the net
position does the same, the reading is about windy days against calm days only, and is written so.

**What would change the reading:** (a) R total moving by more than 0.10 beyond the −0.06 baseline would mean
retail load, not scheduling, is responding, and the retail split cannot be read as a choice; (b) O (other
purchases and pumping) absorbing the generation change would make N, not NX, the thing to read; (c) the C1
and C0 estimates of A differing by more than one se would mean the retail control was carrying the result.

**Stop rules, in short:** G1, G2 or G3 fail → STOP, nothing read. Reading 3 → STOP on the question. Nothing
here produces β; the test is of the route and the sign of the net-position response.

### Amendments to the rules (2026-11-05, both before any regression result was seen)

The rules above are kept as written. The first `--verify` run (gate G2) and the stored panel's levels showed
two things the rules did not anticipate. Neither involved an estimate of b.

**Amendment 1: the retail-side outcome is B, not R.** The registry role `purchase_retail` carries some firms'
retail arms and not others. Mean MW bought, stored panel: Iberdrola 7.1 GW and Endesa 7.8 GW sit in
`purchase_retail`. Naturgy's `purchase_retail` auction purchases are 74 MW, while 2,092 MW of its buying is in
other purchases (its unit `GGNCOC1`, role `storage_mixed`, matched by 2,092 MW of "generic" resale); Repsol's
buying is mostly other purchases (576 MW against 293); EDP's split between the two moves by year (other
purchases 2,392 MW in 2019, 3 MW in 2023, the retail leg moving the other way). So R cannot be the retail side
for every firm. Amended definitions (everything else as in the rules):
- `B_a`, `B_b`, `B` = every buying unit of the firm except pumping, auction / bilateral / both (R plus other
  purchases X). **The reading order uses B_a wherever it said R_a** (the +0.10 materiality, the "contains 0"
  conditions, the baseline). R stays as a secondary row (what "retail units" means in the registry), with X,
  `Bnet` = B minus generic units' resale (bought energy resold), and PM (pumping) beside it.
- The net positions already contained every leg, so NX_* and N_* are unchanged; they are the
  classification-free outcomes. Identity: NX_x = A_x + generic_x − B_x − PM_x.
- The −0.06 baseline was measured for R. It is applied to B only as a flag (rule (a)); B has no placebo of its own.
- G2's pass-through check is on the purchase legs: the regulated suppliers (SU Eletricidade, Curenergía) are
  registry role `purchase_other`, so they sit in X, not in R.

**Amendment 2: the stored panel is stale for EDP; the main run uses a refreshed panel.** G2's first run found the
stored panel's `other_buy_bilateral` for EDP differing from a rebuild of May 2023 by up to 276 MW. The panels
(`holiday_quantity_panel` 2026-10-20, `own_wind_quantity_panel` and `self_supply_panel` 2026-10-21 morning)
predate the ownership fixes committed on 2026-10-21 at 16:54 and 17:20 (Movhera's Douro dams, EDP Energia's sale,
Castejón's represented units). A full rebuild of the legs (`--legs`) against the stored panel, 199,675 firm-hours:
EDP only. 14% of EDP's firm-hours differ on `gen_auction` (mean gap +129 MW; +674 MW in 2021, the Douro dams that
moved to Movhera) and 35% on `other_buy_bilateral` (mean −84 MW). **Endesa, Iberdrola, Naturgy and Repsol are
identical on every leg to 0.01 MW.**
- **Main = "refreshed":** the stored panel's rows, instrument, slopes, controls, with every PDBF leg and the
  wind / generic / other-generation split rebuilt on the ownership module as it stands. Gate: the rebuilt legs
  equal `holiday_quantity_test.month_legs` for May 2023, and the rebuilt class split equals the stored one for
  the four unchanged firms (this tests the rebuild).
- **"stored"** is also run and reported, since it is what "Own wind alone" used. The pooled reading is given
  for both; if they differ, that is stated.
- Consequence for the earlier section: its EDP row (+2.07, the weakest first stage) and its pooled numbers
  rest on the stale legs. The refreshed run reports A again, so the size of the change is visible.

### Results (run 2026-11-05; `--run`, logs in `.superpowers/sdd/2026-11-05-own-wind-net-position/`; tables `own_wind_net_position*.csv`)

**Gates.** G1: first-stage F 1,609 (own wind on Wdev 1.000, se 0.025). G2 (`--verify`): PASS on the refreshed panel
(identity to 0.00001 MW; legs equal `month_legs` for May 2023; class split equal to the stored one for the four
unchanged firms; excluding pass-through suppliers moves purchases by 315 MW for EDP and 599 MW for Iberdrola in
May 2023, so the exclusion is live). G3: 2.8 × se(NX_auc) = 0.202 against Nash r = 0.217, so it passes, narrowly.
Reproduction: other generation A under the original controls (C1) is **−0.202 (0.061)**, the "alone" −0.20; under
C0 (no retail control) −0.218 (0.062), a shift of −0.26 se. **Refreshed against stored panel:** pooled results
match to within 0.002; only EDP moves (A +1.92 → +1.77, NX_auc +2.01 → +1.85, both with se about 0.9).

**References this run:** bilateral share of the extra wind s_b = 0.408; Nash r = 0.217; observed bilateral cut of
other generation x = 0.210.

**Pooled, per MW of own wind** (2SLS on Wdev, C0, 199,675 firm-hours; b with se):

| outcome | b (se) | 95% interval | price-taking | (i) book bal. | (ii) Nash | (iii-a) label | (iii-b) buy-back |
|---|---|---|---|---|---|---|---|
| A other generation | −0.218 (0.062) | −0.34, −0.10 | 0 | −0.41 | −0.22 | −0.21 | −0.21 |
| … auction | +0.004 (0.058) | −0.11, +0.12 | | | −0.22 | | |
| … bilateral | −0.222 (0.057) | −0.33, −0.11 | | −0.41 | | | |
| **B_a** buying units, auction | **−0.233 (0.064)** | −0.36, −0.11 | 0 | 0 | 0 | 0 | **+0.21** |
| B_b buying units, bilateral | +0.082 (0.065) | −0.04, +0.21 | 0 | 0 | 0 | −0.21 | −0.21 |
| B buying units, both | −0.151 (0.017) | −0.18, −0.12 | 0 | 0 | 0 | −0.21 | 0 |
| R_a retail-role units, auction | −0.141 (0.064) | −0.27, −0.02 | | | | | |
| R retail-role units, both | −0.065 (0.014) | −0.09, −0.04 | | | | | |
| X other purchases | −0.085 (0.007) | −0.10, −0.07 | | | | | |
| Bnet (B less generic resale) | −0.061 (0.014) | −0.09, −0.03 | | | | | |
| **NX_auc** | **+0.275 (0.072)** | +0.13, +0.42 | | 0 | **−0.22** | 0 | **−0.21** |
| NX_bil | −0.393 (0.041) | −0.47, −0.31 | | −0.41 | 0 | 0 | 0 |
| NX_tot | −0.119 (0.066) | −0.25, +0.01 | 0 | −0.41 | −0.22 | 0 | −0.21 |
| N_auc (wind in) | +0.868 (0.066) | +0.74, +1.00 | | | | | |
| N_bil (wind in) | +0.013 (0.022) | −0.03, +0.06 | | | | | |
| N_tot (wind in) | +0.881 (0.066) | +0.75, +1.01 | | | | | |

**The reading the rules give.** None: the net auction position (excluding own wind) *rises* with the firm's wind,
+0.275 [+0.13, +0.42], and the reading order had no branch for a rise (I wrote it for a fall or no change; the
script labels it "not in the rules' tree"). What the pre-specified tests do settle:
- **Buy-back (iii-b) is rejected.** It needs B_a ≥ +0.10 with the interval above 0 and NX_auc below 0. B_a is
  **−0.233 [−0.36, −0.11]**, negative in every check, and NX_auc is positive.
- **Market power in net-position terms (NX_auc = −r) is rejected**: +0.275 is 6.8 se above −0.217 (6.7 above −x).
  (Arithmetic, not in the rules: N_auc, the net auction position with the wind in, is +0.868, 7.6 se above the
  0.37 that a Nash cut of r from the wind's own auction sales, 0.59, would leave.)
- **Physical book balancing (i)** needs B_a around 0 and NX_auc around 0; neither holds, and **label only (iii-a)**
  needs NX_auc around 0 and fails the same way. The data fit neither exactly.
- **Post hoc, not a pre-specified reading:** the retailer buys *less* in the auction, not more. Retail-role
  purchases move from the auction to the bilateral leg (R_a −0.14, R_b +0.08, total −0.065 = step 1's placebo
  baseline −0.06); the bilateral book balances (N_bil +0.013); the extra wind and the lower auction purchases both
  show up as more net sales to the auction.

**By firm** (W_s × firm on Wdev × firm, refreshed panel, C0; b (se); F is the first stage):

| | Iberdrola (F 986) | Repsol (1,386) | Endesa (1,021) | Naturgy (2,214) | EDP (206) |
|---|---|---|---|---|---|
| A other generation | −0.26 (0.10) | −0.56 (0.13) | −0.20 (0.32) | +0.34 (0.18) | +1.77 (0.85) |
| B_a buying units, auction | **−0.29 (0.10)** | **−0.29 (0.09)** | +0.41 (0.38) | **−0.44 (0.10)** | −0.11 (0.48) |
| B_b buying units, bilateral | **+0.25 (0.10)** | −0.11 (0.10) | −0.72 (0.38) | +0.13 (0.10) | −0.25 (0.53) |
| B both | −0.04 (0.03) | −0.40 (0.05) | −0.30 (0.15) | −0.30 (0.06) | −0.36 (0.40) |
| X other purchases | +0.00 (0.02) | −0.36 (0.04) | −0.03 (0.06) | −0.33 (0.05) | +0.22 (0.30) |
| **NX_auc** | **+0.36 (0.13)** | −0.30 (0.14) | −0.11 (0.36) | **+0.83 (0.20)** | +1.85 (0.92) |
| NX_tot | −0.15 (0.12) | **−0.63 (0.14)** | −0.02 (0.35) | **+0.50 (0.19)** | +2.04 (0.92) |
| N_tot (wind in) | +0.85 (0.12) | +0.37 (0.14) | +0.98 (0.35) | +1.50 (0.19) | +3.04 (0.92) |
| Nash r (firm) / buy-back x | 0.40 / 0.24 | 0.03 / 0.12 | 0.08 / 0.59 | 0.05 / −0.16 | 0.36 / −0.41 |

Firm readings by the rules: Iberdrola "rises, not in the tree" (the firm that carries the pooled A: its retailer
moves 0.29 from auction to bilateral purchases, total B −0.04, which is its wind going bilateral to its own
retailer); Repsol, Endesa, Naturgy, EDP "STOP: power" (G3 fails: their NX_auc se is above r/2.8, Nash being
0.03–0.08 for three of them; a small Nash cut cannot be told from 0 and nothing is read from them as to β).
- **Repsol** cuts both its generation (A −0.56) and its purchases (X −0.36), net NX_tot −0.63 [−0.89, −0.36]: a net
  cut 20 times its Nash reference. Its located wind is 28% of capacity in one region; unexplained, as in "alone".
- **Naturgy**'s net position rises 1.5 MW per MW of own wind (N_tot): its trading purchases (X −0.33) fall with its
  wind and its generation does not fall (+0.34). This may be regional weather moving Naturgy's load or trading rather than conduct (not
  tested; the rules' flag (a) covers the pooled B only).
- **Endesa** is noise (se 0.35 to 0.38 on every net outcome). **EDP** is noise (F 206, se 0.9).

**Checks** (pooled, refreshed; b (se)):

| | B_a | NX_auc | NX_tot | A |
|---|---|---|---|---|
| main (C0) | −0.233 (0.064) | +0.275 (0.072) | −0.119 (0.066) | −0.218 (0.062) |
| firm × date effects | −0.374 (0.052) | +0.381 (0.072) | +0.022 (0.065) | −0.102 (0.058) |
| Spanish price above €5 | −0.208 (0.069) | +0.215 (0.079) | −0.210 (0.072) | −0.297 (0.068) |
| 2022 on | −0.170 (0.079) | +0.134 (0.095) | −0.238 (0.089) | −0.333 (0.082) |
| Wdev_fc as instrument | −0.278 (0.063) | +0.329 (0.070) | −0.068 (0.064) | −0.191 (0.060) |
| week clusters | −0.233 (0.077) | +0.275 (0.088) | −0.119 (0.083) | −0.218 (0.079) |
| C1 controls (retail as control) | −0.187 (0.064) | +0.235 (0.072) | −0.159 (0.067) | −0.202 (0.061) |

- **Stability as the rules define it is not met**: the script's reading agrees with the main one in **4 of 6**
  checks, not 5. The two that differ (2022 on, week clusters) are labelled "STOP: power" because the check's
  2.8 × se(NX_auc) (0.27, 0.25) passes r = 0.217; their sign and size are those of the main run. Beyond the rules'
  count: B_a is negative in all seven rows (−0.17 to −0.37) and never near the +0.10 buy-back threshold; NX_auc is
  positive in all seven and its interval excludes −r in all seven, 0 in six (2022 on: [−0.05, +0.32]).
- **Within a firm's day the sign holds and grows** (firm × date: B_a −0.37, NX_auc +0.38), unlike the generation cut,
  which halves there (A −0.10, as in "alone"). The retail response is not a between-day artefact.
- **The net total is not stable**: NX_tot runs from +0.02 (firm × date) to −0.24 (2022 on), with intervals that
  include 0 in four rows and −0.22 in five. It cannot tell 0 from the Nash cut.
- **Rule flags: none.** (a) R total −0.065 and B total −0.151 are within 0.10 of the −0.06 baseline (B: 0.091, just
  inside); (b) X −0.085 is under 0.10 in size, though it moves with generic resale (−0.07), so Bnet −0.061 is the
  cleaner purchase measure; (c) A shifts −0.26 se between C0 and C1.

**What this does not settle.**
- NX_tot, the one outcome that needs no label, is imprecise (−0.12 [−0.25, +0.01]): it excludes neither "no net
  cut" nor a Nash-sized cut of −0.22. The sharper results (B_a, NX_auc) are about which auction leg moves, and
  they run against buy-back and against a net auction cut; they do not show the firm's total net position is flat.
- B contains traders' purchases for resale (X, Naturgy's and EDP's `generic` pairs); it is read next to Bnet.
- "Auction" is PDBF role ≠ 4, checked against cleared (status C) bids for one month (May 2023, 99.92%), not
  all 81.
- A load confound is not ruled out: regional wind moves load (the placebo, R total −0.065 here), and the retail
  split could respond to the same weather. Firm × date effects, which absorb the day's weather, make the split
  larger, not smaller.
- No β. Power: NX_auc rejects ±0.22 only for the pooled sample; for three of the five firms it cannot.

### Plain reading (5 lines)
1. When a firm's own wind blows, its retailer does **not** buy back what the generators cut: its auction
   purchases fall by 0.23 MW per MW of wind (−0.36 to −0.11), where buy-back needs a rise of at least 0.10.
2. The buying moves from the auction to bilateral contracts (retail-role units: −0.14 and +0.08; total −0.065, the
   weather baseline), so the firm's non-wind net sales to the auction rise by 0.28, not fall by the 0.22 that
   market power at β = 1 would give (6.8 se away).
3. The pooled result is Iberdrola's (auction −0.29, bilateral +0.25, total −0.04); Repsol cuts net by 0.6 for
   reasons not found, Naturgy's net position rises 1.5 per MW, and Endesa and EDP are noise.
4. The firm's total net position excluding its wind is −0.12 (−0.25 to +0.01): it can be neither zero nor Nash, so
   the caveat survives in that form, but the specific route (retailer buying the gap in the auction) is rejected.
5. Not a clean pass: the rules had no branch for a rise, stability is 4 of 6 as defined, and EDP's legs in the
   stored panel were stale (refreshed here; pooled results unchanged).
