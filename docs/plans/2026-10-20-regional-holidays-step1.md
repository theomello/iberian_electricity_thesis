# Regional holidays, step 1: the holiday table and each firm's exposure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 2018–2026 holiday table for every Spanish region and Portugal, and estimate how many MW each firm's retail schedule falls on each area's holidays (e_fr), full sample and leaving each year out, with the spec's stop rule.

**Architecture:** A fetcher parses the nine BOE resolutions (XML) into a long table and adds Portugal's national holidays by rule; a small lib turns it into area × day indicators (unshared holiday, bridge day, market-wide holiday). A second fetcher takes REE's monthly demand by region for the size check. A builder reads PDBF, sums each exposed group's retail schedule per day, differences it against clean same-weekday references, and regresses the difference on the area indicators per firm.

**Tech Stack:** Python 3.14 in `.venv`, pandas 3, numpy, requests; `lib/unit_ownership.py` (`majority_group`), `lib/omie_owner.py`.

**Spec:** `docs/specs/2026-10-20-regional-holidays-design.md` §3.1, §3.2, §4 step 1, §6.

## Global Constraints

- Always `.venv/bin/python`. Scripts resolve the repo root from their own location.
- Logs go to `.superpowers/sdd/2026-10-20-holidays/`. Nothing under `data/` and no parquet is committed; small CSVs in `outputs/tables/` are. Commit only on the user's word.
- Spec: "Spanish regional holidays, from the Dirección General de Trabajo's annual resolution in the BOE … every region plus Ceuta and Melilla."
- Spec: "Portuguese national holidays (Código do Trabalho, art. 234)": 1 Jan, Good Friday, Easter Sunday, 25 Apr, 1 May, Corpus Christi, 10 Jun, 15 Aug, 5 Oct, 1 Nov, 1 Dec, 8 Dec, 25 Dec. Carnival and municipal holidays are out.
- Spec: "Main sample: weekday holidays only (Monday–Friday)." "Bridge days (puentes) flagged, not counted as holidays."
- Spec: "H_rd = 1 if area r … has a holiday on d that the rest of MIBEL does not share." MIBEL areas: the 15 mainland regions and Portugal. The Balearic and Canary Islands, Ceuta and Melilla are placebo areas.
- Spec: the firm's retail schedule is "auction plus bilateral, its exposed retail units only"; "Regulated pass-through suppliers carry no dose."
- Spec: references are "the same weekday one week before and after … ±2 if a neighbour is itself a holiday or bridge day."
- Spec stop rule: "Stop if no firm's exposure is distinguishable from zero in at least three regions." Read as: continue if some firm has t ≥ 2 in at least three areas.

## Review Focus

1. **DST days**: a day's mean MW must divide by the hours in the local day (23, 24, 25), not 24. Pinned in Task 3's check.
2. **The 15-minute PDBF from 2025-03-19**: energy is `schedule_mw × resolution_min / 60`. Pinned in Task 3's check (a 2025-06 day).
3. **Monday substitutes**: when a national holiday falls on a Sunday, a region's Monday is its holiday (2019-01-07 in Andalucía, not in Cataluña). Pinned in Task 1's check.
4. **Collinear areas**: Aragón and Castilla y León share 23 April. The regression must report areas it cannot separate, not print noise. Pinned in Task 3 (rank check, joint labels).
5. **A retailer that changes hands**: EDP Comercializadora is EDP's to 2020-11-30 and TotalEnergies' from 2020-12-01. `majority_group` by date handles it; the by-year table shows it.

---

## File Structure

| file | responsibility |
|---|---|
| `scripts/fetch/fetch_holidays.py` (create) | BOE XML → `data/holidays/raw/`, parse, Portugal by rule → `data/holidays/holidays_es_pt.parquet` |
| `scripts/lib/holidays.py` (create) | area codes; `load`, `unshared`, `bridges`, `market_wide` |
| `scripts/qa/check_holidays.py` (create) | known dates and counts |
| `scripts/fetch/fetch_ree_regional_demand.py` (create) | REData monthly demand by region → `data/ree/ree_demand_ccaa_monthly.parquet`; sum check |
| `scripts/build/build_holiday_exposure.py` (create) | day panel, Δ, regressions, leave-one-year-out, by year, size check, stop rule |
| `scripts/qa/check_holiday_exposure.py` (create) | the panel reproduces the Diada 2024 figures; DST and 15-minute days |
| `notes/rq-regional-holidays.md` (create); spec, CLAUDE.md (modify) | write-up, inventory rows, the spec's corrected example |

---

### Task 1: The holiday table

**Files:** create `scripts/fetch/fetch_holidays.py`, `scripts/lib/holidays.py`, `scripts/qa/check_holidays.py`.

**Interfaces:**
- Produces `data/holidays/holidays_es_pt.parquet`: `date` (datetime64), `area` (str), `mark` (`national` `*`, `national_chosen` `**`, `regional` `***`, `pt_national`), `name` (str), `source` (BOE id or `PT CT art. 234`).
- `lib/holidays.py`: `ES_MAINLAND` (15 ISO 3166-2:ES codes: AN AR AS CB CM CL CT VC EX GA MD MC NC PV RI), `MIBEL = ES_MAINLAND + ("PT",)`, `PLACEBO = ("IB","CN","CE","ML")`, `AREAS = MIBEL + PLACEBO`; `load() -> DataFrame`; `market_wide(days) -> Series[bool]` (holiday in every MIBEL area); `unshared(days) -> DataFrame[days × AREAS]` of 0/1 (holiday in the area, not market-wide); `bridges(days) -> DataFrame[days × AREAS]` of 0/1 (a weekday, not a holiday in the area, between an area holiday and a weekend, i.e. Monday before a Tuesday holiday or Friday after a Thursday holiday).

BOE ids, by holiday year: 2018 `BOE-A-2017-11639`, 2019 `BOE-A-2018-14369`, 2020 `BOE-A-2019-14552`, 2021 `BOE-A-2020-13343`, 2022 `BOE-A-2021-17113`, 2023 `BOE-A-2022-16755`, 2024 `BOE-A-2023-22014`, 2025 `BOE-A-2024-21316`, 2026 `BOE-A-2025-21667`. Route `https://www.boe.es/diario_boe/xml.php?id=<id>`; the fetcher refuses a file whose title lacks "fiestas laborales para el año <year>". The annex is one table: header cells carry region ids (`andalucia` … `melilla`), each date row has `id="fDDMM"` and 19 cells marked `*`, `**`, `***` or empty. Read day and month from the row id, not from `headers`.

- [ ] **Step 1: Write `check_holidays.py`** asserting: 2019-02-28 AN `regional`; 2019-03-19 in VC GA MC NC PV and not CT; 2019-04-18 (Holy Thursday) in every region but CT and VC; 2019-01-07 in AN and not CT; 11 Sep CT in every year 2018–2026; 25 Apr and 10 Jun PT every year; 2019-06-20 PT (Corpus Christi); Good Friday market-wide every year; every Spanish area-year has 12–14 rows; `unshared` is 0 on every market-wide day; `bridges` on 2019-03-18 (Monday before San José) is 1 in VC.
- [ ] **Step 2: Run it**: `.venv/bin/python scripts/qa/check_holidays.py` → fails (no table).
- [ ] **Step 3: Implement** the fetcher (keep raw XML; parse with `re`, as the table is regular) and the lib.
- [ ] **Step 4: Run the fetcher, then the check** → every line `ok`.

### Task 2: Regional demand, monthly

**Files:** create `scripts/fetch/fetch_ree_regional_demand.py`.

**Interfaces:** produces `data/ree/ree_demand_ccaa_monthly.parquet`: `month` (datetime64, first day), `area` (ISO code), `demand_mwh`.

REData `demanda/evolucion`, `time_trunc=month`, `geo_trunc=electric_system`, `geo_limit=ccaa`, one request per area-year, cached raw in `data/ree/raw/ccaa/`. Ids (checked 2026-10-20 on 2023 totals): AN 4, AR 5, CB 6, CM 7, CL 8, CT 9, PV 10, AS 11, MD 13, NC 14, VC 15, EX 16, GA 17, RI 20, MC 21, CN 8742, IB 8743, CE 8744, ML 8745.

- [ ] **Step 1: `--verify`** prints, per year, the 15 mainland areas' sum against the peninsular total (`geo_limit=peninsular`, `geo_ids=8741`), and fails if they differ by more than 2%.
- [ ] **Step 2: Fetch 2018-01 → 2026-05 and run `--verify`** → passes.

### Task 3: Exposures

**Files:** create `scripts/build/build_holiday_exposure.py`, `scripts/qa/check_holiday_exposure.py`.

**Interfaces:**
- Consumes Task 1's lib, Task 2's parquet, PDBF, `unit_registry` (`role == "purchase_retail"`), `majority_group(df, exposed=True)` and `exposed=False`.
- Produces `outputs/tables/holiday_retail_days.parquet` (`group`, `date`, `retail_mw`, `ref_mw`, `delta_mw`, `ref_dates`), and CSVs `holiday_exposure.csv` (`group, area, e_mw, se, t, n_days, share_of_retail`), `holiday_exposure_loyo.csv` (`group, area, year_out, e_mw, se`), `holiday_exposure_by_year.csv` (`group, area, year, e_mw, se`), `holiday_exposure_size.csv` (`area, e_all_mw, predicted_mw, ratio`).

Definitions (my calls where the spec leaves them open):
- **retail_mw** of group g on day d: −Σ `schedule_mw × resolution_min/60` over all PDBF rows of g's retail units, divided by the hours in the local day. Groups by `exposed=True`; a pass-through owner's units form group `PASS`; all retail units together form `ALL`.
- **Clean day**: a weekday that is not a holiday or bridge in any MIBEL area and not in 20 Dec – 7 Jan. **References**: on each side the nearest of ±7, ±14 days that is clean; a day without one on each side is dropped. `delta_mw = retail_mw − mean(references)`.
- **Sample**: weekdays, not market-wide holidays, not 20 Dec – 7 Jan.
- **Regression, per group**: `−delta_mw = c + Σ_area e_fr · unshared + Σ_area b_fr · bridges + u`, OLS, HC1 errors. So e_fr > 0 means the group buys e_fr MW less on the area's holiday. Areas with fewer than 5 holiday days in the sample are left out and listed. Any pair of `unshared` columns correlated above 0.95 is merged into a joint area (`AR+CL`), and the merge is printed.
- **Leave-one-year-out**: the same regression without year y, for each y in 2018–2026.
- **By year**: the same regression within each year (descriptive).
- **Size check**: national drop rate = mean of `−delta / ref` for the mainland demand series (`ree_realtime_5min`, daily mean MW, same references) on days that are holidays in every mainland region and not in PT. Predicted drop in area r = rate × r's demand that month (Task 2). Compare with `ALL`'s e_r.
- **Stop rule**: print, per group, the areas with t ≥ 2; print `CONTINUE` if any group has at least three, else `STOP`.

- [ ] **Step 1: Write `check_holiday_exposure.py`** asserting, on the panel: ENDESA on 2024-09-11 has references 2024-09-04 and 2024-09-18 and `delta_mw` −457 ± 2 (PDBF, verified 2026-10-20 with a throwaway query); `ALL` −623 ± 3; (group, date) unique; on 2024-03-31 (23 h) and 2024-10-27 (25 h) retail_mw is within 5% of the neighbouring Sundays' (a 24 h divisor would miss by about 4% and pass, so also assert the divisor used is 23 and 25); a 2025-06 weekday's ALL retail_mw lies between 20 and 35 GW (a 15-minute row read as MWh would quadruple it).
- [ ] **Step 2: Run it** → fails (no panel).
- [ ] **Step 3: Implement the builder.** Read PDBF a month at a time, columns `date, period, resolution_min, unit, schedule_mw`.
- [ ] **Step 4: Run builder, then check** → every line `ok`; log to `.superpowers/sdd/2026-10-20-holidays/exposure.log`.

### Task 4: Write-up

- [ ] `notes/rq-regional-holidays.md`: step 1 tables (exposures of the five firms and TotalEnergies, Repsol by area; leave-one-year-out spread; by year for Endesa; size check; stop rule).
- [ ] Spec: status line; correct the example (674 MW was auction purchases only; whole schedule −457 MW, −6%).
- [ ] CLAUDE.md: inventory rows for the holiday table and regional demand; table rows for the three scripts.
- [ ] Ask the user before committing.
