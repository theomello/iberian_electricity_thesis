# Near-misses of the minimum-income condition: running note

Spec: [`docs/specs/2026-10-20-mic-near-miss-design.md`](../docs/specs/2026-10-20-mic-near-miss-design.md).
Plan: `docs/plans/2026-10-20-mic-near-miss-step1.md`. Ledger and logs:
`.superpowers/sdd/2026-10-20-mic-near-miss-step1/`.

## Step 1 (2026-10-20): the running variable, the checks, the fate of withdrawn plants — STOP

**In one line.** Acceptance jumps cleanly at the threshold (0 → 0.89), and a plant just
withdrawn sells about 90 MW more in the intraday auctions than one just accepted. But the
stop rule fires: there are 2.5 times as many unit-days per €/MWh just above the threshold as
just below, and the declared variable term v jumps by €19/MWh. Both look mechanical, not
manipulated (§1.4), and point to a sample restriction that has not been run.

### 1.1 What was built

- `fetch/fetch_omie_pdvd.py`: OMIE's PDVD (*Programa Diario Viable Definitivo*, the
  day-ahead schedule after REE's technical constraints), 2019-01 → 2025-03, 75 months,
  104 M rows. Seven fields (no unit id, no group tag). Checked on the spec's example: on
  2019-01-03 REE schedules the withdrawn Sagunto 1 at 51.7 MW on average (155 at most).
- `build/build_mic_running.py` → `outputs/tables/mic_running.parquet`: **137,417 declaring
  unit-days on 121 units, 2019-01-01 → 2025-03-18** (DST days out). r at the published
  prices; r_A, the margin had the unit run, for withdrawn units by re-clearing each hour on
  the step cache's effective curve with the unit's offers added. 1,363 days flagged (more
  than four hours not re-clearable) and left out.
- `lib/rd.py`: the local linear jump and McCrary's density test, checked on planted data
  (`qa/check_rd.py`).
- `analysis/mic_near_miss_describe.py` → `outputs/tables/mic_near_miss_rd.csv`,
  `mic_near_miss_fate.csv`.

**Withdrawing a plant moves the price it is measured at.** The re-clearing lowers a withdrawn
plant's prices by a median €0.58/MWh and its margin by €0.86/MWh. Of the 410 withdrawn plants whose
margin at the final prices was €0–0.25, 98% fall below zero once measured as if running.
The threshold becomes almost sharp: under 5% accepted below −€0.10 (20% in the last €0.10,
within the re-clearing's error), 89–99% above.

### 1.2 The checks at the threshold

Local linear each side, triangular kernel, bandwidth €2/MWh, errors clustered by date;
2,628 unit-days below, 4,111 above.

| check | jump | se | p |
|---|---|---|---|
| accepted (≥ 4 hours cleared) | **0.891** | 0.015 | 0 |
| density (McCrary, log ratio) | **0.912** | 0.067 | 10⁻⁴² |
| v, declared variable term (€/MWh) | **+19.2** | 3.6 | 10⁻⁷ |
| D-1 solar forecast (MWh/h) | **+491** | 97 | 10⁻⁷ |
| D-1 demand forecast | −411 | 197 | 0.04 |
| F, fixed term | −670 | 1,365 | 0.62 |
| D-1 wind forecast | +190 | 209 | 0.36 |
| gas price at D−2 | +3.7 | 2.2 | 0.09 |
| ran on D−1 | +0.02 | 0.03 | 0.52 |
| weekend | −0.01 | 0.03 | 0.82 |

Single-unit firm-days within €2 to 2024-06-13 (the intraday panels' end): 2,504 of 3,913.

**Stop rule: STOP** (density test rejects; two covariates jump at 1%). The acceptance jump and
the count pass.

### 1.3 What a withdrawn plant does

Within €2 of the threshold, mean MW over the day:

| | n | REE schedules it | its schedule after REE | sells intraday | its net intraday sales | runs in all | idle |
|---|---|---|---|---|---|---|---|
| withdrawn | 2,628 | 40% | 27 MW | 69% | **93 MW** | 120 MW | 26% |
| accepted | 4,111 | 99% | 246 MW | 64% | 15 MW | 262 MW | 0.5% |

At the threshold (same regression as §1.2): intraday sales −90 MW (se 6) from withdrawn to
accepted; output in all +104 MW (se 7). **So a withdrawal does reach the intraday auctions**:
the plant sells about 90 MW there that it would not otherwise, more than intraday positions
usually move (tens of MW a session). By firm, a withdrawn plant sells 122 MW (Naturgy), 83
(Endesa), 69 (EDP), 53 (Iberdrola); by year, 117 MW in 2019 falling to 48 in 2024. This is
the plant's own sale, not yet its owner's net position (step 2).

### 1.4 Why the density jumps: two mechanical candidates, neither run yet

**Measured at the final prices, before any re-clearing, the right side is already twice as
dense.** Withdrawn plants spread evenly from −1 to +0.25 (about 410–440 per €0.25); accepted
plants start at 0 (439 in the first €0.25) with almost none below. So the accepted add to the
right without a matching group on the left.

1. **On many accepted days the condition cannot bind.** A plant with no fixed term that offers
   every MW at or above its v earns at least v on whatever it sells, so its margin is never
   negative. Those days can only sit to the right. The jump in v fits: just above the
   threshold the median v is €66, just below €56. *Test*: keep unit-days on which the plant
   offered some MW below its own v (known when offers close, so a valid restriction) and
   rerun the checks.
2. **The re-clearing may overstate the price effect.** It empties the band just below zero
   (withdrawn plants in [−0.25, 0): 439 → 156) and sends many below −1. A median €0.58 shift
   for a median 236 MW plant implies a slope of about 400 MW per €/MWh, close to the
   day-ahead's 500, so it is not absurd, but the tail is not checked. *Test*: compare each
   shift with the plant's MW over the local slope of the effective curve.

**Manipulation is unlikely to explain it**: there is no spike just above zero (32, 31, 22, 28
unit-days in the first four €0.01 bins against 15–22 further up), and the price noise a firm
faces at noon on D-1 is several €/MWh.

### 1.5 Rulings in this step

- 2018 is left to step 5: the step cache (the re-clearing curves) and REE's D-1 forecasts
  start in 2019.
- The plan's check "r_A ≤ r for every withdrawn row" was wrong: r is a volume-weighted
  average, and a lower price can drop a plant's cheapest hours and raise it (Castejón 3,
  2022-02-13: −4.15 → −1.86; 2 of 100,843 rows). The check now pins that the price shift is
  never positive (100%).
