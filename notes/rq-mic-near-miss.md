# Near-misses of the minimum-income condition: running note

Spec: [`docs/specs/2026-10-20-mic-near-miss-design.md`](../docs/specs/2026-10-20-mic-near-miss-design.md).
Plan: `docs/plans/2026-10-20-mic-near-miss-step1.md` (Task 6 is the restricted check). Ledger
and logs: `.superpowers/sdd/2026-10-20-mic-near-miss-step1/`.

## Step 1 (2026-10-20): the running variable, the checks, the fate of withdrawn plants — STOP

**In one line.** Acceptance jumps cleanly at the threshold (0 → 0.89), and a plant just
withdrawn sells about 90 MW more in the intraday auctions than one just accepted. But the
stop rule fires: there are about twice as many unit-days per €/MWh just above the threshold
as just below, and the declared variable term v jumps by €17/MWh. Neither of two mechanical
explanations accounts for it (§1.4–1.5). On days with a single plant near its threshold
(§1.7), v no longer jumps but the pile-up above the threshold remains (3×, p 8·10⁻⁶), and
there are only 264 such days. **Design 2 stops at step 1.**

### 1.1 What was built

- `fetch/fetch_omie_pdvd.py`: OMIE's PDVD (*Programa Diario Viable Definitivo*, the
  day-ahead schedule after REE's technical constraints), 2019-01 → 2025-03, 75 months,
  104 M rows. Seven fields (no unit id, no group tag). Checked on the spec's example: on
  2019-01-03 REE schedules the withdrawn Sagunto 1 at 51.7 MW on average (155 at most).
- `build/build_mic_running.py` → `outputs/tables/mic_running.parquet`: **137,417 declaring
  unit-days on 121 units, 2019-01-01 → 2025-03-18** (DST days out). r at the published
  prices; r_A, the margin had the unit run, for withdrawn units by re-clearing each hour on
  the step cache's effective curve with the unit's offers added. Days with more than four
  hours that cannot be re-cleared (split, clearing identity off, re-clear error above €0.50)
  are flagged for every unit and left out: 14.6% of days, 19,264 unit-days.
- `lib/rd.py`: the local linear jump and McCrary's density test, checked on planted data
  (`qa/check_rd.py`).
- `analysis/mic_near_miss_describe.py` → `outputs/tables/mic_near_miss_rd.csv`,
  `mic_near_miss_fate.csv` (and `_bind` versions, §1.5).

**Withdrawing a plant moves the price it is measured at.** The re-clearing lowers a withdrawn
plant's prices by a median €0.59/MWh and its margin by €0.86/MWh. Of the 410 withdrawn plants
whose margin at the final prices was €0–0.25, 98% fall below zero once measured as if
running. The threshold becomes almost sharp: under 5% accepted below −€0.10 (20% in the last
€0.10, within the re-clearing's error), 89–99% above.

### 1.2 The checks at the threshold

Local linear each side, triangular kernel, bandwidth €2/MWh, errors clustered by date;
2,624 unit-days below, 3,670 above.

| check | jump | se | p |
|---|---|---|---|
| accepted (≥ 4 hours cleared) | **0.890** | 0.015 | 0 |
| density (McCrary, log ratio) | **0.766** | 0.068 | 10⁻²⁹ |
| v, declared variable term (€/MWh) | **+16.8** | 3.7 | 5·10⁻⁶ |
| D-1 solar forecast (MWh/h) | **+452** | 97 | 3·10⁻⁶ |
| D-1 demand forecast | −439 | 195 | 0.02 |
| F, fixed term | −1,154 | 1,362 | 0.40 |
| D-1 wind forecast | +99 | 212 | 0.64 |
| gas price at D−2 | +2.5 | 2.2 | 0.27 |
| ran on D−1 | +0.03 | 0.03 | 0.35 |
| weekend | −0.02 | 0.03 | 0.46 |

Single-unit firm-days within €2 to 2024-06-13 (the intraday panels' end): 2,272 of 3,602.

**Stop rule: STOP** (density test rejects; two covariates jump at 1%). The acceptance jump and
the count pass.

### 1.3 What a withdrawn plant does

Within €2 of the threshold, mean MW over the day:

| | n | REE schedules it | its schedule after REE | sells intraday | its net intraday sales | runs in all | idle |
|---|---|---|---|---|---|---|---|
| withdrawn | 2,624 | 40% | 27 MW | 69% | **93 MW** | 120 MW | 26% |
| accepted | 3,670 | 99% | 247 MW | 64% | 16 MW | 263 MW | 0.6% |

At the threshold (same regression as §1.2): intraday sales −91 MW (se 6) from withdrawn to
accepted; output in all +105 MW (se 8). **So a withdrawal does reach the intraday auctions**:
the plant sells about 90 MW there that it would not otherwise, more than intraday positions
usually move (tens of MW a session). By firm, a withdrawn plant sells 122 MW (Naturgy), 85
(Endesa), 69 (EDP), 53 (Iberdrola); by year, 117 MW in 2019 falling to 48 in 2024. This is
the plant's own sale, not yet its owner's net position (step 2).

### 1.4 A bug found on the way: the flag dropped only withdrawn plants

The first run flagged a unit-day when *its own* hours could not be re-cleared, which only
happens to withdrawn plants. On the same bad days, 605 withdrawn plants within €2 were
dropped and 445 accepted ones kept, which thinned the left side. The flag is now a property
of the day (`qa/check_mic_running.py` pins it). That lowers the density jump from 0.91 to 0.77
and the v jump from €19 to €17, and leaves the verdict unchanged. The numbers above are the
corrected ones.

### 1.5 The restricted check (Task 6): neither mechanical explanation holds

**1. Days when the condition cannot bind: not it.** A plant with no fixed term that offers
nothing below its v earns at least v on whatever it sells, so its margin cannot be negative
(pinned: r ≥ 0 on all 765 such unit-days). But such days are rare: the condition can bind on
**99.2%** of unit-days within €2, because combined cycles offer most of their output below v
and rely on the condition to protect them (Sagunto 1 on 2019-01-03: 5,884 of 10,015 MW·h
offered below its €68.42). Restricted to days when it can bind: density 0.762 (se 0.068), v
+16.9 (3.7), solar +446 (98). The same.

**2. The re-clearing overstating the price effect: mostly not.** Each withdrawn plant's
re-cleared price shift against its added MW over the local slope of the effective curve
(±€5 around the price), 4,623 withdrawn unit-days within €2:

| | median |
|---|---|
| re-cleared shift | −€0.585/MWh |
| added MW / local slope | −€0.425/MWh |
| ratio, p10 / median / p90 | 0.88 / 1.30 / 1.96 |
| added MW; local slope | 227 MW; 520 MW per €/MWh |

Correlation 0.92. The shift runs about 30% above the linear prediction, as a curve that steepens
below the price would make it, and the slope matches the day-ahead's usual 500. Not an
artefact large enough to empty the band below the threshold.

### 1.6 What is left: plants compete for the same slot

**Near-misses come in groups.** On days with a unit within €2, the median day has **3** such
units and 77% have two or more. The re-clearing holds the other plants' status fixed, but the
algorithm chooses which of them to accept jointly: accepting one lowers the price for the
others. Which side of the threshold a plant lands on is then partly the algorithm's choice
among competitors, not luck, and the plants it keeps may differ systematically (higher v, as
§1.2 shows). **Not tested.** The test: days with exactly one plant within €2 across the whole
market, where there is no competition to resolve; rerun the checks there.

### 1.7 Single-plant days (run 2026-10-20): still STOP

Days on which exactly one unit in the whole market is within €2 of its threshold
(`mic_near_miss_describe.py --single`; outputs `_single`): **304 of 1,444 days**, 108 unit-days
below and 196 above.

| check | jump | se | p |
|---|---|---|---|
| accepted | 0.735 | 0.077 | 10⁻²¹ |
| density (McCrary, log ratio) | **1.18** | 0.26 | **8·10⁻⁶** |
| v | +6.2 | 15.2 | 0.68 |
| F | +5,315 | 3,016 | 0.08 |
| D-1 demand / wind / solar forecast | −753 / −1,289 / +544 | 740 / 1,003 / 340 | 0.31 / 0.20 / 0.11 |
| gas price at D−2 | −16.3 | 9.7 | 0.09 |
| ran on D−1; weekend | −0.09; +0.04 | 0.13; 0.12 | 0.48; 0.73 |
| the plant's net intraday sales | −22 MW | 16 | 0.18 |
| its output in all | +116 MW | 24 | 10⁻⁶ |

- **No covariate jumps at 1%**: with nothing for the algorithm to choose between, the
  imbalance in v goes. That supports §1.6 as the source of the v jump.
- **The pile-up above the threshold stays**, larger if anything (3× against 2×). It is not
  competition, not days when the condition cannot bind, not the re-clearing's size, and not
  withdrawn plants lost for producing nothing at the recomputed price (none are). It is
  unexplained.
- **The first stage weakens too**: on these days a withdrawn plant sells 57 MW intraday
  against 15 when accepted, a jump of 22 MW (se 16), against 91 on all days.
- **264 single-unit firm-days to 2024-06-13**, against the stop rule's 1,000.

**Verdict.** The running variable fails its density test on every sample tried, and the sample
where the covariates balance is too small and has almost no first stage. Design 2 does not
continue to step 2. **What survives is descriptive**: a combined cycle just withdrawn in the
auction sells about 90 MW more of its output in the intraday auctions than one just accepted,
and REE switches 40% of them back on (§1.3), which bears on Ito & Reguant's sequential-market
question rather than on β.

### 1.8 Rulings in this step

- 2018 is left to step 5: the step cache (the re-clearing curves) and REE's D-1 forecasts
  start in 2019.
- The plan's check "r_A ≤ r for every withdrawn row" was wrong: r is a volume-weighted
  average, and a lower price can drop a plant's cheapest hours and raise it (Castejón 3,
  2022-02-13: −4.15 → −1.86; 2 of 100,843 rows). The check now pins that the price shift is
  never positive (100%).
- The flag is a property of the day (§1.4).
