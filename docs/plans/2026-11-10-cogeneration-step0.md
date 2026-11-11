# Cogeneration step 0 (build and count) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the cogeneration unit registry and unit-day panel, and count everything the design's gates G0 and G5 and its stop rules need, without estimating anything.

**Architecture:** One registry builder (units, fuel, group), one panel builder (schedules and offers per unit-day), one descriptive script (tables), one check script per built file. Two tasks are reading, not code. Follows the direct-consumer builders on this branch.

**Tech Stack:** Python 3.14 in `.venv` (pandas 3.0, pyarrow 25). No new packages. Checks are `scripts/qa/check_*.py` scripts that exit non-zero on failure, as elsewhere in this repo (there is no pytest suite).

**Spec:** `docs/specs/2026-11-10-cogeneration-design.md` (§3 is this plan; §1 holds the figures the checks pin).

## Global Constraints

- Always `.venv/bin/python`. Paths resolve from the script's own location (`ROOT = Path(__file__).resolve().parent.parent.parent`); nothing hardcoded.
- **No estimation.** No regression, logit or event-study coefficient is computed in this plan. Tables are counts, sums, means and shares.
- Window: **2019-01-01 → 2023-12-31**.
- Energy from schedules is `schedule_mw × resolution_min / 60`. PDBF has several rows per unit-period (one per role code): sum over role codes before anything else.
- Offers come from `curva_pbc_uof` rows with `status == "O"`; cleared quantities from `status == "C"`. Never sum the two.
- Run = daily load factor above **10%** of the unit's `cab` maximum power.
- Sample labels, verbatim from OMIE's listing: non-renewable = `technology` starting `RE Mercado Térmica no`; renewable = `RE Mercado Térmica Renovable`. Solar thermal (`Solar Térmica`) is excluded.
- Name matching needs positive evidence; ambiguous pairs are printed and left unmatched, never guessed.
- Data facts go to `CLAUDE.md`; results go to `notes/rq-cogeneration.md`. Commit messages imperative, ≤ 72 characters, ending with the attribution line the session specifies.

## Review Focus

1. **A plant that moves from a portfolio unit to its own unit** after the cap appears as one unit stopping and another starting. Expected: linked by name (Task 3), never counted as an exit plus an entry.
2. **Portfolio units** (several plants under one code). Expected: flagged `portfolio` and excluded from run/stop counts, not read as one plant.
3. **Units with zero or missing `cab` maximum power.** Expected: kept in the registry with a null load factor, not dropped silently and not divided by zero.
4. **Units marked `BAJA` in the listing that still offer** (526 of 856 in the 2022-02-08 snapshot). Expected: activity comes from PDBF and the bid files, never from `status`.
5. **"Non-renewable" is not "gas".** Expected: every table that says gas uses the matched `fuel`, and reports the unmatched share beside it.

---

### Task 1: Unit registry

**Files:**
- Create: `scripts/build/build_cogeneration_units.py`
- Create: `scripts/qa/check_cogeneration_units.py`
- Output: `data/omie/registry/cogeneration_units.parquet`

**Interfaces:**
- Produces: one row per unit, columns `unit, descr, label` (`nonren` / `renew`, from the latest listing naming the unit), `agent_owner, max_power_mw` (maximum `cab` value in the window), `first_day, last_day` (first and last day with a positive PDBF schedule, 2017-01 onward so that entry is not truncated at 2019), `new_after_cap` (`first_day ≥ 2022-06-01`), `portfolio` (bool, Task 2 fills it), `sector, region`.
- `sector` reuses `sector()` from `scripts/build/build_direct_consumers.py` on `descr` then `agent_owner`; `region` from MITECO's `ElectraExp.csv` by exact normalised-name match, else null.

- [ ] **Step 1: Write the check** `check_cogeneration_units.py` asserting: `unit` is unique; `label` has no nulls; non-renewable units with a positive schedule in January 2022 number **269 ± 10** and their `max_power_mw` sums to **6,332 ± 300 MW**; `new_after_cap` non-renewable units whose `first_day` is in October 2022 number **28 ± 3** and November **15 ± 3**; no unit has `first_day > last_day`. Print each figure before asserting.
- [ ] **Step 2: Run it**: `.venv/bin/python scripts/qa/check_cogeneration_units.py`. Expected: fails, file not found.
- [ ] **Step 3: Implement** `main() -> int` in the builder: `load_listing_units() -> pd.DataFrame`, `activity(units: set) -> pd.DataFrame` (first and last active day from the PDBF monthly parquets), `capacity(units: set) -> pd.DataFrame` (from `cab`).
- [ ] **Step 4: Run builder then check.** Expected: check passes. If a pinned figure is outside its band, stop and report the figure: the spec's §1 counts came from one-off queries and the difference must be understood, not tuned away.
- [ ] **Step 5: Commit.**

### Task 2: Fuel, from REE's physical units

**Files:**
- Modify: `scripts/build/build_cogeneration_units.py`
- Modify: `scripts/qa/check_cogeneration_units.py`

**Interfaces:**
- Consumes: Task 1's registry; `data/esios/esios_physical_units.parquet` (`tech`, `descr_long`, `descr_short`, `agent`, `up`, `max_power_mw`).
- Produces: registry columns `fuel` (`gas`, `other_fossil`, `biomass_waste`, null), `ree_plants` (list of matched `uf`), `ree_mw` (their summed capacity), `match_how` (`code`, `name_capacity`, `manual`, null), and `portfolio = True` when more than one plant matches or `max_power_mw > 60` with `ree_mw < 0.6 × max_power_mw`.
- `match_ree_plants(units: pd.DataFrame, plants: pd.DataFrame) -> tuple[pd.DataFrame, list]` returns matches and the rejected ambiguous pairs.
- REE `tech` → `fuel`: `Gas natural cogeneración` → `gas`; `Derivados del petróleo o carbón`, `Fuel`, `Turbina vapor - Fuel gas`, `Energía residual` → `other_fossil`; `Biomasa`, `Biogás`, `Residuos varios`, `Residuos domésticos y similares` → `biomass_waste`.

Matching rule, in order: (1) the OMIE unit code equals the plant's `up` or `uf`; (2) normalised names (reuse `normalise` and `name_similarity` from `build_jrc_cab_match.py`) with similarity ≥ 0.8 **and** capacity within 15%, accepted only when the pair is mutually the best candidate; (3) a hand table `MANUAL`, empty at first, each entry carrying a comment with both names and capacities.

- [ ] **Step 1: Add checks:** a synthetic case inside the check script, two plants with the same name and capacity against one unit, must return no match and one rejected pair; on real data, matched pairs' `ree_mw / max_power_mw` has median within 0.8–1.2; no REE plant is matched to two units; a renewable-label unit never gets `fuel == "gas"` (print and fail if any).
- [ ] **Step 2: Run, expect failure** (`match_ree_plants` not defined).
- [ ] **Step 3: Implement.** Print every accepted `name_capacity` pair with both names, and every rejected pair.
- [ ] **Step 4: Run builder and check; read the printed pairs.** Then print **gate G0**: share of non-renewable `max_power_mw` (units active in January 2022) with a non-null `fuel`. Record it; do not tune thresholds to reach 60%.
- [ ] **Step 5: Commit.**

### Task 3: Who entered the mechanism

**Files:**
- Modify: `scripts/build/build_cogeneration_units.py`, `scripts/qa/check_cogeneration_units.py`
- Create: `docs/cogeneration-sources.md`

**Interfaces:**
- Produces: registry columns `entry_day` (first day of a `new_after_cap` unit, else null), `linked_from` (the earlier unit a new unit's plant came from, else null), `mechanism_source` (`official_list`, `new_unit`, null).

- [ ] **Step 1: Look for an official list** of offer units in the adjustment mechanism (OMIE's public files and its market-rules annexes, CNMC's monitoring reports on Real Decreto-ley 10/2022, REE's settlement publications). Write what was searched and found, with URLs and dates, in `docs/cogeneration-sources.md`. If a list exists, save the raw file under `data/omie/mechanism/raw/` and read it into `mechanism_source = "official_list"`.
- [ ] **Step 2: Add the check:** every `linked_from` names a unit in the registry whose `first_day` precedes the new unit's; no unit is `linked_from` for two new units unless it is `portfolio`.
- [ ] **Step 3: Implement `link_new_units(reg: pd.DataFrame) -> pd.DataFrame`:** for each `new_after_cap` unit, candidates are older units of the same `agent_owner` or sharing a matched `ree_plants` element; accept on name similarity ≥ 0.8 or a shared plant. Print accepted and rejected links.
- [ ] **Step 4: Run, read the links, commit.** Report how many of the October–November 2022 entrants are linked, how many are plants not seen before, and how many leave a portfolio unit.

### Task 4: The rules that changed in 2022

**Files:**
- Modify: `docs/cogeneration-sources.md`

No code. Read and summarise, with article numbers and BOE references:

- [ ] **Step 1:** Real Decreto-ley 6/2022 (29 March 2022): what it changed in the regulated scheme's adjustment for market prices, for which plants, from what date.
- [ ] **Step 2:** Orden TED/1232/2022 and Orden TED/1295/2022: the operating payment for 2022 by standard plant type; whether the gas cogeneration types' values can be tabulated (how many types, what identifies a type: fuel, size band, year of commissioning), and what plants knew before December 2022 (the provisional values in force).
- [ ] **Step 3:** Real Decreto-ley 17/2022, the article on the waiver: exact notification deadline rule, what is given up, how to return.
- [ ] **Step 4:** State in one paragraph whether a unit's standard plant type can be recovered from data held here or from a public register, and name the register. Commit.

### Task 5: Unit-day panel

**Files:**
- Create: `scripts/build/build_cogeneration_panel.py`
- Create: `scripts/qa/check_cogeneration_panel.py`
- Output: `outputs/tables/cogeneration_panel/panel_YYYYMM.parquet` (60 months)

**Interfaces:**
- Consumes: the registry; PDBF, bids, `cab` and price monthly parquets.
- Produces: one row per unit and day with `date, unit, energy_mwh` (PDBF, all role codes), `bilateral_mwh` (role code 4), `max_power_mw` (that day's `cab` value, forward-filled within the unit), `load_factor`, `run`, `offered_mwh` and `cleared_mwh` (sell side), `offer_price` (MW-weighted mean of offered sell rows), `share_at_zero` (offered sell MW priced ≤ €1 over offered sell MW), `price_es` (daily mean day-ahead price). Structure follows `build_direct_consumer_panel.py`: a `month(ym: str, reg: pd.DataFrame) -> pd.DataFrame` function and a resumable loop.

- [ ] **Step 1: Write the check:** `(date, unit)` unique; every month 2019-01 → 2023-12 present; mean MW (`energy_mwh` summed over units ÷ hours in the month) for non-renewable units existing before June 2022 is **3,549 ± 2%** in 2022-03 and **1,386 ± 2%** in 2022-09, and for renewable units **599 ± 2%** and **557 ± 2%**; `load_factor ≤ 1.05` on at least 99% of rows with a capacity; rows with null or zero capacity have null `load_factor`; `cleared_mwh ≤ offered_mwh + 0.01`; the two DST days of 2022 (27 March, 30 October) have 23 and 25 hours of energy for a unit running flat (check `energy_mwh ≤ max_power_mw × 25`).
- [ ] **Step 2: Run, expect failure.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run builder (all months) and check.** Expected: pass. Report run time.
- [ ] **Step 5: Commit** (the parquet outputs are gitignored; commit scripts only).

### Task 6: Descriptive tables, note and documentation

**Files:**
- Create: `scripts/analysis/cogeneration_describe.py`
- Create: `notes/rq-cogeneration.md`
- Modify: `CLAUDE.md` (script table rows; a short data section)
- Output: `outputs/tables/cogeneration_describe_{group_month,offers,switches}.csv`

**Interfaces:**
- Consumes: registry and panel. Groups: `gas_entered` (fuel gas, entered the mechanism), `gas_not_entered`, `nonren_unknown_fuel`, `other_fossil`, `renewable`; portfolio units reported apart.

Tables, all counts and means:
- `group_month`: by group and month, mean MW, units active, mean load factor, share of unit-days running.
- `offers`: by group and half-year, share of units whose median `share_at_zero` is below 0.5 (they bid a reservation price), and the median `offer_price` among those. This decides whether the spec's E3 exists.
- `switches`: per non-portfolio unit in 2022, the number of run/stop changes; the count of units with ≥ 10 (**gate G5** needs 100); the share of run or stop spells lasting under two days (the spec's daily-or-weekly rule, §6).

- [ ] **Step 1:** Implement the script; it prints G0 (from the registry), G5 and the reservation-price share at the end.
- [ ] **Step 2:** Run it. Check by hand that `group_month` summed over groups equals the panel totals pinned in Task 5.
- [ ] **Step 3:** Write `notes/rq-cogeneration.md`: the design in five lines with a link to the spec, then "Step 0 result" with G0, G5, the linking counts from Task 3, the reservation-price share, the spell-length share, the Task 4 summary, and which of the spec's stop rules now apply. State plainly what is not yet known.
- [ ] **Step 4:** Add the three scripts to the table in `CLAUDE.md` and a short section with the verified data facts (counts, the fuel match coverage, any trap found).
- [ ] **Step 5:** Run `.venv/bin/python scripts/qa/check_cogeneration_units.py && .venv/bin/python scripts/qa/check_cogeneration_panel.py`. Expected: both pass. Commit.

**Stop here.** Step 0 ends with the note. E1 onward needs the user's go-ahead on the step 0 result.
