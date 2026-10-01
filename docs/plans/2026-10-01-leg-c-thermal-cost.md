# Leg C — Thermal Plant, Cost Observed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test the firm's first-order condition p − c = β·X **in levels** at the margin of its gas and coal units, where the marginal cost c is observed, with X instrumented by rivals' offered wind and solar.

**Architecture:** A unit-period panel of the 77 JRC-matched thermal units in the periods where each is partly dispatched (so the price lies on its own curve) and cleared in the periods just before and after (so any start-up is sunk), 2018–2023. Each row carries the unit's implied cost (gas-capped from 2022-06-15), the dated owner's X, and that owner's rivals' offered wind and solar. One endogenous regressor, two instruments: 2SLS, first-stage F, Anderson–Rubin tests of β = 0 and β = 1, and the exact AR set for β. Specification 2 estimates each unit's heat rate instead of imposing it and validates specification 1. Route 3 replaces c with the declared minimum-income variable term.

**Tech Stack:** Python 3.14 in `.venv`, pandas 3, pyarrow, numpy, scipy; the repo's `iv_two_endog.py` (2SLS, SW F, AR), `solar_first_stage.demean`, and the leg D builders.

**Spec:** `docs/specs/2026-09-29-thesis-framework-design.md` — §4 "Leg C — thermal plant: cost observed" (route 2, with route 3 as its check), §2.4 (the exposed position), §8 step 5.

## Global Constraints

- `$SCRATCH` is the session's scratchpad directory; logs go there, never into the repo.
- Always `.venv/bin/python`, never bare `python3`. Scripts resolve the repo root from their own location (`Path(__file__).resolve().parent.parent.parent`).
- Never commit `.env`, anything under `data/`, or `outputs/tables/*.parquet`. Small result CSVs in `outputs/tables/` are committed.
- Commit messages: imperative, present tense, subject ≤ 72 characters, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Spec, verbatim: "Firm-periods in which one of the firm's gas or coal units is **partly dispatched**: some of its offered volume cleared and some did not … The unit must also be cleared in t−1 and t+1, so any start-up is sunk."
- Spec: "Years 2018–2023; from 2022-06-15 the gas-capped cost (`marginal_cost_capped_eur_mwh`)."
- Spec: "X uses the exposed n (§2.4) and rivals' slope within ±5 €/MWh, own offers removed." This is `net_exp_mw / slope_exp_h5` in `outputs/tables/firm_incentive_net.parquet` (equals `firm_x.X` for the five firms to 0.01 €/MWh, checked 2026-10-01).
- Spec: "Instruments: rivals' offered wind and solar, built as `z_offered` is … from units the firm does not own. … Errors clustered by week, Anderson–Rubin sets."
- Spec 2 validation, verbatim: "ĥ_u must sit near 1/eff for the 46 gas units with a plant-specific JRC efficiency. If it does not, specification 1 is not trusted."
- Filter on `eff_is_generic` (CLAUDE.md): specification 1 uses only units with a plant-specific efficiency; a generic class efficiency must never impose a cost.
- Only clean periods (no ES/PT market split, clearing identity holds: `firm_x.clean`), so the Spanish price is the price.
- REPSOL rows before 2018-11-02 are dropped (`leg_d_panel.REPSOL_VIESGO`; Repsol's own press release dates the Viesgo purchase).

## Review Focus

1. **Month ends and midnight.** A unit partly dispatched at 00:00 on the 1st needs the last period of the previous month as its t−1; reading bid months independently silently drops it. Pinned by Task 3's synthetic `at_margin` test.
2. **DST days.** "t−1 and t+1" must be the neighbouring UTC instants, not period numbers, on 23- and 25-hour days. Pinned by Task 3's synthetic test.
3. **A unit that changes owner.** Castejón 1 and 3 (EDP → TotalEnergies, listing of 2022-02-08), Plana del Vent 1 (RWE → Naturgy, 2019-07-18), Amorebieta (Bizkaia Energía → Axpo, 2022-02-08): each period must carry the owner and the X of the listing in force. Pinned by Task 3's full-panel checks.
4. **The gas cap.** Gas cost differs from the market-price cost only between 2022-06-15 and 2023-12-31; coal never. Pinned by Task 3.
5. **Generic efficiencies.** A unit whose JRC efficiency is a class average must not enter specification 1. Pinned by Task 4's sample count check.

---

## File Structure

| file | responsibility |
|---|---|
| `scripts/build/build_rival_solar.py` (modify) | rivals' offered solar/wind for the five firms **and every other group owning a matched thermal unit** |
| `scripts/qa/check_rival_solar.py` (modify) | the identity for every group present; every thermal group present |
| `scripts/analysis/iv_two_endog.py` (modify) | `ar_set_k1`: exact AR set, one regressor, two instruments |
| `scripts/qa/check_iv_two_endog.py` (modify) | its endpoints, and empty-W support |
| `scripts/analysis/leg_c_panel.py` (create) | the unit-period panel |
| `scripts/qa/check_leg_c_panel.py` (create) | `at_margin` on synthetic data; the full panel's invariants |
| `scripts/analysis/leg_c_test.py` (create) | specifications 1 and 2, route 3, the markdown table; writes `outputs/tables/leg_c_results.csv` |
| `notes/rq-leg-c-thermal-cost.md` (create), spec (modify) | the write-up |

Branch: `leg-c`. If `leg-d` is merged into `main`, branch from `main`; otherwise from `leg-d`, whose `build_rival_solar.py --tech wind` and `ar_set_one` this plan builds on.

---

### Task 1: Rivals' renewables for every thermal owner

**Files:**
- Modify: `scripts/build/build_rival_solar.py`
- Modify: `scripts/qa/check_rival_solar.py`

**Interfaces:**
- Consumes: `data/jrc_ppdb/jrc_cab_match.parquet` (`unit`), `data/omie/registry/omie_unit_lists.parquet` (`unit, agent_owner`), `omie_owner.exposed_group`.
- Produces: `thermal_groups() -> tuple[str, ...]` in `build_rival_solar.py`, returning `("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "AXPO", "BAHIA", "BIZKAIA", "CASTELNOU", "CEPSA", "COGEN", "ENGIE", "NUEVA", "RIBERA", "RWE", "SNIACE", "TOTALENERGIES")`; `outputs/tables/rival_solar.parquet` and `rival_wind.parquet` with `own_<G>` and `z_rival_<G>` (MW) for every one of those groups. `align(d, px, groups=FIRMS)` keeps its default, so leg D's callers are unchanged.

- [ ] **Step 1: Create the branch and write the failing check**

```bash
git checkout -b leg-c
```

In `scripts/qa/check_rival_solar.py`, after the existing identity loop over `FIRMS` inside `main()`, add:

```python
    from build_rival_solar import thermal_groups
    present = [c[len("z_rival_"):] for c in d.columns if c.startswith("z_rival_")]
    for g in present:
        if ((d.z_all - d[f"own_{g}"] - d[f"z_rival_{g}"]).abs() > 1e-6).any():
            fails.append(f"z_rival_{g} != z_all - own_{g}")
    absent = sorted(set(thermal_groups()) - set(present))
    if absent:
        fails.append(f"thermal owners without an instrument column: {absent}")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python scripts/qa/check_rival_solar.py --tech wind | tail -3`
Expected: exit 1 with `ImportError: cannot import name 'thermal_groups'`.

- [ ] **Step 3: Add `thermal_groups` and loop over the groups**

In `scripts/build/build_rival_solar.py`, change the import line to

```python
from omie_owner import exposed_group, owner_group  # noqa: E402
```

add below `KEY = ["date", "period"]`:

```python
MATCH = DATA / "jrc_ppdb/jrc_cab_match.parquet"
LISTS = DATA / "omie/registry/omie_unit_lists.parquet"


def thermal_groups() -> tuple[str, ...]:
    """The five firms, then every other group owning a JRC-matched thermal unit in any
    OMIE listing: leg C needs each such owner's rivals' renewables."""
    m = pd.read_parquet(MATCH, columns=["unit"])
    lst = pd.read_parquet(LISTS, columns=["unit", "agent_owner"])
    g = lst[lst.unit.isin(m.unit)].agent_owner.map(exposed_group).dropna()
    return FIRMS + tuple(sorted(set(g) - set(FIRMS)))
```

replace `month` and `align` with

```python
def month(f: Path, grp: pd.Series, groups: tuple[str, ...] = FIRMS) -> pd.DataFrame:
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", list(grp.index)), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    b["grp"] = b.unit.astype(str).map(grp)
    k = [b.date, b.period]
    parts = [b.power_mw.groupby(k).sum().rename("z_all")]
    for g in groups:
        parts.append(b.power_mw.where(b.grp == g, 0.0).groupby(k).sum().rename(f"own_{g}"))
    return pd.concat(parts, axis=1).reset_index()


def align(d: pd.DataFrame, px: pd.DataFrame, groups: tuple[str, ...] = FIRMS) -> pd.DataFrame:
    """Sums onto the priced periods of the days the bid files cover.

    Only days with bid rows are kept: a frontier month's zip can be partial
    (CLAUDE.md), and a priced day with no bids must be missing, not zero.
    Within a covered day, a period with no row carries 0.
    """
    d = px[px.date.isin(set(d.date))].merge(d, on=KEY, how="left")
    num = [c for c in d.columns if c not in KEY]
    d[num] = d[num].fillna(0.0)
    for g in groups:
        d[f"z_rival_{g}"] = d.z_all - d[f"own_{g}"]
    return d
```

and in `build`, replace `parts.append(month(f, grp))` with `parts.append(month(f, grp, groups))`, `d = align(d, px)` with `d = align(d, px, groups)`, and add `groups = thermal_groups()` as the first line of `build`.

- [ ] **Step 4: Rebuild both and run the checks**

Run: `.venv/bin/python scripts/build/build_rival_solar.py --tech wind > $SCRATCH/rival_wind.log 2>&1; .venv/bin/python scripts/build/build_rival_solar.py > $SCRATCH/rival_solar.log 2>&1; .venv/bin/python scripts/qa/check_rival_solar.py --tech wind | tail -2; .venv/bin/python scripts/qa/check_rival_solar.py | tail -3; .venv/bin/python scripts/qa/check_leg_d_panel.py | tail -1`
Expected: `OK` from all three, about 5 minutes per build. The solar check still prints `corr 1.000000` for EDP against `z_offered`. The leg D panel check is unchanged, because its five firms' columns are identical.

- [ ] **Step 5: Commit**

```bash
git add scripts/build/build_rival_solar.py scripts/qa/check_rival_solar.py
git commit -m "Build rivals' renewables for every group owning matched thermal plant"
```

---

### Task 2: Exact AR set for one regressor and two instruments

**Files:**
- Modify: `scripts/analysis/iv_two_endog.py`
- Modify: `scripts/qa/check_iv_two_endog.py`

**Interfaces:**
- Consumes: `ar_common_exact(y, X, Z, W, cl, level)` (two columns of X constrained to one slope).
- Produces: `ar_set_k1(y, x, Z, W, cl, level=0.95) -> None | dict` with the keys of `ar_common_exact` (`intervals`, `q_min`, `p_min`, `c_min`); `x` is a 1-D array, `Z` has two columns; `W` may have zero columns.

- [ ] **Step 1: Write the failing check**

In `scripts/qa/check_iv_two_endog.py`, add `ar_set_k1` to the `from iv_two_endog import (...)` list, and before the `y, X, Z, W, cl = dgp(-0.5, -0.5, seed=5, share_seller=0.0)` block add:

```python
    # One regressor, two instruments (leg C): the AR set of the single slope.
    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=11)
    x1 = X.sum(axis=1)
    k1 = ar_set_k1(y, x1, Z, W, cl)
    print(f"one regressor, two instruments: AR set {fmt_intervals(k1['intervals'])}")
    iv = k1["intervals"]
    check(len(iv) == 1 and iv[0][0] < -0.5 < iv[0][1], "k = 1, L = 2: one interval around -0.5")
    for c in iv[0]:
        p_end = ar_test(y, x1[:, None], Z, W, cl, [c])[1]
        check(abs(p_end - 0.05) < 1e-4, f"k = 1, L = 2: endpoint {c:+.4f} has AR p = 0.05 ({p_end:.5f})")
    W0 = np.zeros((len(y), 0))
    b0, _ = tsls_k(y, x1[:, None], Z, W0, cl)
    k0 = ar_set_k1(y, x1, Z, W0, cl)
    check(abs(b0[0] + 0.5) < 0.05 and k0 is not None and np.isfinite(sw_f(x1[:, None], Z, W0, cl, 0)),
          "no controls: tsls_k, sw_f and ar_set_k1 accept a W with zero columns")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python scripts/qa/check_iv_two_endog.py 2>&1 | tail -1`
Expected: `ImportError: cannot import name 'ar_set_k1'`.

- [ ] **Step 3: Implement**

In `scripts/analysis/iv_two_endog.py`, after `ar_set_one`:

```python
def ar_set_k1(y, x, Z, W, cl, level=0.95):
    """Exact AR set for one regressor x with two instruments.

    y - c*x = y - c*(x/2 + x/2), so this is ar_common_exact on the two equal halves
    of x: the same quartic, the same chi2(2) critical value. Returns its dict
    (intervals, q_min, p_min, c_min), or None if not identified.
    """
    return ar_common_exact(y, np.column_stack([x / 2, x / 2]), Z, W, cl, level)
```

- [ ] **Step 4: Run it to verify it passes**

Run: `.venv/bin/python scripts/qa/check_iv_two_endog.py > $SCRATCH/check_iv.log 2>&1; echo "exit $?"; grep -c "^  ok" $SCRATCH/check_iv.log; grep -E "FAIL|k = 1|no controls" $SCRATCH/check_iv.log`
Expected: `exit 0`, 46 `ok` lines (42 before), the four new lines `ok`, endpoints at `AR p = 0.05` (to 1e-4).

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/iv_two_endog.py scripts/qa/check_iv_two_endog.py
git commit -m "Add the exact AR set for one regressor and two instruments"
```

---

### Task 3: The leg C panel

**Files:**
- Create: `scripts/analysis/leg_c_panel.py`
- Create: `scripts/qa/check_leg_c_panel.py`

**Interfaces:**
- Consumes: `data/omie/bids/parquet/bids_YYYYMM.parquet` (`date, period, unit, side, status, power_mw`); `data/omie/prices/omie_day_ahead_prices.parquet` (`date, period, price_es, utc_timestamp, resolution_min`); `outputs/tables/firm_x.parquet` (`date, period, clean`); `outputs/tables/firm_incentive_net.parquet` (`date, period, firm, net_exp_mw, slope_exp_h5`); `outputs/tables/rival_{wind,solar}.parquet` (Task 1); `data/jrc_ppdb/implied_marginal_cost_daily.parquet`; `data/omie/cab/parquet/cab_YYYYMM.parquet` (`date, unit, side, version, min_income_var_eur_mwh`); `omie_owner.exposed_group`; `leg_d_panel.REPSOL_VIESGO`; `build_rival_solar.thermal_groups`.
- Produces: `at_margin(up) -> pd.Series[bool]` (one per row of `up`, which has `unit, utc, resolution_min, offered_mw, cleared_mw`); `outputs/tables/leg_c_panel.parquet`, one row per unit × date × period, columns `unit, firm, fuel, date, period, utc, wk, p, c, c_uncapped, fuel_index, eff, eff_is_generic, var_term, X, zw, zs, offered_mw, cleared_mw`. `zw`, `zs` in GW; `p, c, fuel_index, var_term, X` in €/MWh (`fuel_index` per MWh of heat).

- [ ] **Step 1: Write the failing check**

Create `scripts/qa/check_leg_c_panel.py`:

```python
#!/usr/bin/env python3
"""Leg C panel: the margin rule on synthetic data, then the full panel's invariants.

    .venv/bin/python scripts/qa/check_leg_c_panel.py

Framework spec §4, leg C. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from leg_c_panel import OUT, at_margin  # noqa: E402

TABLES = ROOT / "outputs/tables"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    # A: partly dispatched at 22:00 and 23:00 UTC on Jan 31, neighbours cleared, the next one in
    # February. B: across the spring DST change (UTC is continuous), partly at 01:00, not
    # cleared at 02:00. C: partly dispatched, but the unit offered nothing the period before.
    t = pd.to_datetime(["2022-01-31 21:00", "2022-01-31 22:00", "2022-01-31 23:00", "2022-02-01 00:00",
                        "2022-03-27 00:00", "2022-03-27 01:00", "2022-03-27 02:00",
                        "2022-05-01 10:00", "2022-05-01 11:00"], utc=True)
    up = pd.DataFrame({"unit": ["A"] * 4 + ["B"] * 3 + ["C"] * 2, "utc": t, "resolution_min": 60,
                       "offered_mw": [100.0] * 9,
                       "cleared_mw": [100, 50, 60, 100, 100, 40, 0, 50, 100]})
    got = at_margin(up).tolist()
    check(got == [False, True, True, False, False, False, False, False, False],
          f"at_margin: partly dispatched with both UTC neighbours cleared, across month ends ({got})")

    if not OUT.exists():
        check(False, f"{OUT.relative_to(ROOT)} missing -- run scripts/analysis/leg_c_panel.py")
        print(f"{len(fails)} failure(s)")
        return 1
    d = pd.read_parquet(OUT)
    print(f"{len(d):,} unit-periods, {d.unit.nunique()} units, {d.date.min().date()} -> {d.date.max().date()}")
    check(not d.duplicated(["unit", "date", "period"]).any(), "keys unique")
    check(d.date.dt.year.between(2018, 2023).all(), "2018-2023 only")
    check(((d.cleared_mw > 0) & (d.cleared_mw < d.offered_mw)).all(), "every row partly dispatched")
    check(not ((d.firm == "REPSOL") & (d.date < "2018-11-02")).any(), "no REPSOL before 2018-11-02")
    for unit, before, after, when in (("CTJON1", "EDP", "TOTALENERGIES", "2022-02-08"),
                                      ("CTJON3", "EDP", "TOTALENERGIES", "2022-02-08"),
                                      ("PVENT1", "RWE", "NATURGY", "2019-07-18")):
        u = d[d.unit == unit]
        ok = (u.loc[u.date < when, "firm"].isin([before]).all()
              and u.loc[u.date >= when, "firm"].isin([after]).all() and len(u) > 0)
        check(ok, f"{unit}: {before} before {when}, {after} from it ({len(u)} rows)")
    gas, coal = d[d.fuel == "gas"], d[d.fuel == "coal"]
    capped = gas[(gas.c - gas.c_uncapped).abs() > 1e-9]
    check(capped.date.between("2022-06-15", "2023-12-31").all() and len(capped) > 0,
          f"gas cost differs from market cost only 2022-06-15..2023-12-31 ({len(capped):,} rows)")
    check(((coal.c - coal.c_uncapped).abs() < 1e-9).all(), "coal never capped")
    check(((d.fuel_index / d.eff - d.c).abs() < 1e-6).all(), "fuel_index / eff == c")
    check(d[["X", "zw", "zs", "p", "c"]].notna().all().all(), "X, instruments, price and cost present")
    check(((d.zw >= 0) & (d.zs >= 0)).all(), "rivals' offered renewables non-negative")
    rw = pd.read_parquet(TABLES / "rival_wind.parquet", columns=["date", "period", "z_rival_EDP"])
    rw["date"] = pd.to_datetime(rw.date).astype("datetime64[us]")
    m = d[d.firm == "EDP"].assign(date=d.date.astype("datetime64[us]")).merge(rw, on=["date", "period"])
    check(len(m) > 0 and np.allclose(m.zw, m.z_rival_EDP / 1000), "EDP rows carry EDP's rivals' wind, in GW")
    print("rows by year and fuel:\n", d.groupby([d.date.dt.year, "fuel"]).size().unstack(fill_value=0))
    print("rows by firm:", d.firm.value_counts().to_dict())
    print(f"plant-specific efficiency: {(~d.eff_is_generic).mean():.3f}; declaring a variable term: "
          f"{(d.var_term > 0).mean():.3f}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python scripts/qa/check_leg_c_panel.py 2>&1 | tail -1`
Expected: `ModuleNotFoundError: No module named 'leg_c_panel'`.

- [ ] **Step 3: Write the builder**

Create `scripts/analysis/leg_c_panel.py`:

```python
#!/usr/bin/env python3
"""Leg C panel: matched thermal units at their own margin, with cost, the owner's X and instruments.

    .venv/bin/python scripts/build/build_rival_solar.py [--tech wind]   # inputs (Task 1)
    .venv/bin/python scripts/analysis/leg_c_panel.py [--months 202201 ...]

Writes outputs/tables/leg_c_panel.parquet, one row per unit x date x period, 2018-2023,
for the JRC-matched gas and coal units (`jrc_cab_match.parquet`). Framework spec §4, leg C.

SAMPLE. A unit-period is kept when the unit is PARTLY DISPATCHED -- some of its offered
volume cleared and some did not, so the price lies on its own curve and its cost is the
firm's marginal cost -- and it CLEARED in the periods just before and after, so any
start-up is sunk. Neighbours are UTC instants (`at_margin`), so midnight, month ends and
DST days need no special case; the bid months are concatenated before neighbours are found.
Clean periods only (`firm_x.clean`: no market split, clearing identity holds), so the
Spanish price is the price.

OWNER. The majority owner in the OMIE listing in force that day (nearest preceding
snapshot), as its exposed group (`omie_owner.exposed_group`). REPSOL rows before its
Viesgo purchase (2018-11-02) are dropped, as in leg D. A row whose owner has no X (Bizkaia
Energia, Amorebieta's owner until 2022-02-08) is dropped and counted.

COLUMNS
  p            clearing price, EUR/MWh
  c            implied marginal cost, gas-capped from 2022-06-15 (marginal_cost_capped_eur_mwh)
  c_uncapped   the cost at the market gas price
  fuel_index   c * eff: fuel price plus emission factor x CO2, per MWh of heat (spec 2)
  eff, eff_is_generic, fuel
  var_term     the declared minimum-income variable term (cab), NaN when not declared (route 3)
  X            owner's exposed n / rivals' slope within +-5 EUR/MWh (firm_incentive_net), EUR/MWh
  zw, zs       owner's rivals' offered wind and solar, GW (instruments)
  wk           ISO year x 100 + week (clusters)
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_rival_solar import thermal_groups  # noqa: E402
from leg_d_panel import REPSOL_VIESGO  # noqa: E402
from omie_owner import exposed_group  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
BIDS = DATA / "omie/bids/parquet"
CAB = DATA / "omie/cab/parquet"
OUT = TABLES / "leg_c_panel.parquet"
YEARS = (2018, 2023)
TOL = 0.1  # MW: "some cleared, some not" needs more than rounding on each side


def unit_periods(f: Path, units: list[str]) -> pd.DataFrame:
    """One bid month -> unit, date, period, offered_mw (status O) and cleared_mw (status C), sell side."""
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", units), ("side", "==", "V")]).to_pandas()
    b["unit"] = b.unit.astype(str)
    g = b.groupby(["unit", "date", "period", "status"]).power_mw.sum().unstack("status", fill_value=0.0)
    g = g.reindex(columns=["O", "C"], fill_value=0.0)
    return g.rename(columns={"O": "offered_mw", "C": "cleared_mw"}).reset_index()


def at_margin(up: pd.DataFrame) -> pd.Series:
    """Partly dispatched now, and cleared at the UTC instants just before and after.

    `up` has unit, utc, resolution_min, offered_mw, cleared_mw for every period the unit
    offered; a neighbour the unit did not offer in counts as not cleared."""
    on = up.loc[up.cleared_mw > TOL, ["unit", "utc"]].assign(on=True)
    step = pd.to_timedelta(up.resolution_min, unit="min")

    def cleared_at(shift: pd.Series) -> pd.Series:
        # Keep utc a time-zone-aware Series: .to_numpy() would turn it into objects.
        q = pd.DataFrame({"unit": up.unit, "utc": up.utc + shift}).reset_index(drop=True)
        return q.merge(on, on=["unit", "utc"], how="left").on.notna()

    partly = ((up.cleared_mw > TOL) & (up.offered_mw - up.cleared_mw > TOL)).reset_index(drop=True)
    ok = partly & cleared_at(-step) & cleared_at(step)
    return pd.Series(ok.to_numpy(), index=up.index)


def owner_listings(units: list[str]) -> pd.DataFrame:
    """unit, date (snapshot), firm: the majority owner's exposed group in every OMIE listing."""
    lst = pd.read_parquet(DATA / "omie/registry/omie_unit_lists.parquet",
                          columns=["snapshot", "unit", "agent_owner", "ownership_pct"])
    lst = lst[lst.unit.isin(units)].sort_values("ownership_pct", ascending=False)
    lst = lst.drop_duplicates(["snapshot", "unit"]).copy()
    lst["date"] = pd.to_datetime(lst.snapshot).astype("datetime64[us]")
    lst["firm"] = lst.agent_owner.map(exposed_group)
    return lst[["unit", "date", "firm"]].sort_values("date")


def instruments(groups: tuple[str, ...]) -> pd.DataFrame:
    """date, period, firm, zw, zs: each group's rivals' offered wind and solar, GW."""
    parts = []
    for tech, col in (("wind", "zw"), ("solar", "zs")):
        r = pd.read_parquet(TABLES / f"rival_{tech}.parquet")
        r["date"] = pd.to_datetime(r.date)
        long = pd.concat([r[["date", "period"]].assign(firm=g, **{col: r[f"z_rival_{g}"] / 1000})
                          for g in groups if f"z_rival_{g}" in r])
        parts.append(long.set_index(["date", "period", "firm"]))
    return pd.concat(parts, axis=1).reset_index()


def declared_var(units: list[str], months: list[str]) -> pd.DataFrame:
    """unit, date, var_term: the last declared minimum-income variable term of the day (sell side)."""
    parts = []
    for ym in months:
        f = CAB / f"cab_{ym}.parquet"
        if f.exists():
            c = pd.read_parquet(f, columns=["date", "unit", "side", "version", "min_income_var_eur_mwh"])
            c = c[c.unit.isin(units) & (c.side == "V")].sort_values("version")
            parts.append(c.drop_duplicates(["unit", "date"], keep="last"))
    v = pd.concat(parts, ignore_index=True)
    v["date"] = pd.to_datetime(v.date)
    return v[["unit", "date"]].assign(var_term=v.min_income_var_eur_mwh.where(v.min_income_var_eur_mwh > 0))


def build(months: list[str] | None) -> pd.DataFrame:
    units = sorted(pd.read_parquet(DATA / "jrc_ppdb/jrc_cab_match.parquet", columns=["unit"]).unit.astype(str))
    files = [f for f in sorted(BIDS.glob("bids_*.parquet"))
             if YEARS[0] <= int(f.stem.split("_")[1][:4]) <= YEARS[1]]
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    up = pd.concat([unit_periods(f, units) for f in files], ignore_index=True)
    up["date"] = pd.to_datetime(up.date)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "utc_timestamp", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    up = up.merge(px.rename(columns={"utc_timestamp": "utc"}), on=["date", "period"])
    up["utc"] = pd.to_datetime(up.utc, utc=True)
    d = up[at_margin(up).to_numpy()].copy()
    print(f"{len(up):,} unit-periods offered; {len(d):,} at the unit's own margin")
    clean = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "clean"])
    clean = clean.drop_duplicates(["date", "period"])
    clean["date"] = pd.to_datetime(clean.date)
    d = d.merge(clean, on=["date", "period"])
    d = d[d.clean].drop(columns="clean")
    print(f"  {len(d):,} in clean periods")
    left = d.assign(date=d.date.astype("datetime64[us]")).sort_values("date")
    d = pd.merge_asof(left, owner_listings(units), on="date", by="unit", direction="backward")
    d = d[~((d.firm == "REPSOL") & (d.date < REPSOL_VIESGO))]
    groups = thermal_groups()
    x = pd.read_parquet(TABLES / "firm_incentive_net.parquet",
                        columns=["date", "period", "firm", "net_exp_mw", "slope_exp_h5"],
                        filters=[("firm", "in", list(groups))])
    x["date"] = pd.to_datetime(x.date).astype("datetime64[us]")
    x["X"] = x.net_exp_mw / x.slope_exp_h5
    d = d.merge(x[["date", "period", "firm", "X"]], on=["date", "period", "firm"], how="left")
    z = instruments(groups)
    z["date"] = z.date.astype("datetime64[us]")
    d = d.merge(z, on=["date", "period", "firm"], how="left")
    cost = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                           columns=["unit", "date", "fuel", "eff", "eff_is_generic",
                                    "marginal_cost_eur_mwh", "marginal_cost_capped_eur_mwh"])
    cost["date"] = pd.to_datetime(cost.date).astype("datetime64[us]")
    d = d.merge(cost.rename(columns={"marginal_cost_capped_eur_mwh": "c",
                                     "marginal_cost_eur_mwh": "c_uncapped"}), on=["unit", "date"], how="left")
    ym = sorted({f.stem.split("_")[1] for f in files})
    v = declared_var(units, ym)
    v["date"] = v.date.astype("datetime64[us]")
    d = d.merge(v, on=["unit", "date"], how="left")
    miss = d[["X", "zw", "zs", "c"]].isna()
    print("dropped for a missing column:", miss.sum().to_dict(),
          "| owners without X:", d.loc[miss.X, "firm"].value_counts().to_dict())
    d = d[~miss.any(axis=1)].copy()
    d["p"] = d.price_es
    d["fuel_index"] = d.c * d.eff
    iso = d.date.dt.isocalendar()
    d["wk"] = (iso.year.astype(int) * 100 + iso.week.astype(int)).astype("int32")
    cols = ["unit", "firm", "fuel", "date", "period", "utc", "wk", "p", "c", "c_uncapped", "fuel_index",
            "eff", "eff_is_generic", "var_term", "X", "zw", "zs", "offered_mw", "cleared_mw"]
    d = d[cols].sort_values(["unit", "date", "period"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} unit-periods, {d.unit.nunique()} units)")
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Partial build, then the check**

Run: `.venv/bin/python scripts/analysis/leg_c_panel.py --months 202201 202202 202207 && .venv/bin/python scripts/qa/check_leg_c_panel.py`
Expected: the `at_margin` line `ok`; `wrote outputs/tables/leg_c_panel.parquet`; the Castejón checks `ok` with rows on both sides only if the partial months straddle 2022-02-08 (they do: 202201, 202202); the PVENT1 check may FAIL for lack of 2019 rows in a partial build — that is expected here and must pass on the full build. "owners without X" lists at most `BIZKAIA`.

- [ ] **Step 5: Full build and check**

Run: `.venv/bin/python scripts/analysis/leg_c_panel.py > $SCRATCH/leg_c_panel.log 2>&1; tail -4 $SCRATCH/leg_c_panel.log; .venv/bin/python scripts/qa/check_leg_c_panel.py`
Expected: `OK`; every check `ok`; the printed table shows gas rows in every year and coal rows mostly 2018–2021. Record the row counts in the ledger.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/leg_c_panel.py scripts/qa/check_leg_c_panel.py
git commit -m "Build the leg C panel: thermal units at their own margin"
```

---

### Task 4: The test

**Files:**
- Create: `scripts/analysis/leg_c_test.py`
- Create (output, committed): `outputs/tables/leg_c_results.csv`

**Interfaces:**
- Consumes: `outputs/tables/leg_c_panel.parquet` (Task 3); `iv_two_endog.tsls_k, sw_f, ar_test, ar_set_k1, fmt_intervals` (Task 2); `solar_first_stage.demean(df, cols, fes)`.
- Produces: `outputs/tables/leg_c_results.csv`, one row per sample × specification, columns `sample, spec, n, units, weeks, status, beta, se, first_stage_f, ar_p_beta0, ar_p_beta1, ar_set, ar_set_p_min`, plus for spec 2 `h_eff_median, h_eff_share_20, h_units, validated`, and for the markdown rows `sign, n, median_p_minus_c, share_below_cost`.

- [ ] **Step 1: Confirm the inputs pass their checks**

Run: `.venv/bin/python scripts/qa/check_iv_two_endog.py | tail -1 && .venv/bin/python scripts/qa/check_leg_c_panel.py | tail -1`
Expected: `OK` twice.

- [ ] **Step 2: Write the test**

Create `scripts/analysis/leg_c_test.py`:

```python
#!/usr/bin/env python3
"""Leg C: the condition p - c = beta * X in levels, at the margin of thermal units.

    .venv/bin/python scripts/analysis/leg_c_panel.py     # input
    .venv/bin/python scripts/analysis/leg_c_test.py

Framework spec §4, leg C. One row per unit-period at the unit's own margin (Task 3).

SPEC 1, cost imposed:     p - c = a_u + beta * X + e     units with a plant-specific JRC efficiency
SPEC 2, heat rate free:   p = a_u + h_u * fuel_index + beta * X + e     all units
ROUTE 3, declared cost:   p - var_term = a_u + beta * X + e     units declaring a variable term

a_u is a unit effect (O&M, any constant bias). X is instrumented by the owner's rivals'
offered wind and solar (zw, zs, GW); errors clustered by ISO week. beta = 0 is
price-taking, beta = 1 full supply-function Nash (p - c = X). Inference that survives
weak instruments: AR tests of beta = 0 and beta = 1, and the exact AR set for beta.
A row is WEAK when its first-stage F is below 10.

SPEC 2 VALIDATES SPEC 1. h_u is recovered as the OLS of (y - beta_hat * X) on the
unit-specific fuel_index columns (the 2SLS normal equations give exactly that). For gas
units with a plant-specific efficiency and at least MIN_UNIT rows, h_u * eff should be
near 1: VALIDATED when the median is within [0.85, 1.15] and at least half lie within
+-0.20. Otherwise specification 1 is not trusted.

THE MARKDOWN IN LEVELS. p - c tabulated by the sign of X: the spec's prediction is a
price below observed cost when the firm is a net buyer and above it when a net seller.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iv_two_endog import ar_set_k1, ar_test, fmt_intervals, sw_f, tsls_k  # noqa: E402
from solar_first_stage import demean  # noqa: E402

PANEL = ROOT / "outputs/tables/leg_c_panel.parquet"
OUT = ROOT / "outputs/tables/leg_c_results.csv"
MIN_ROWS = 500
MIN_UNIT = 200
WEAK_F = 10.0
FIVE = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")


def iv(d: pd.DataFrame, y: str, label: str, spec: str, heat: bool = False) -> dict:
    """2SLS of y on X with unit effects (and unit-specific fuel_index slopes when heat)."""
    d = d.dropna(subset=[y, "X", "zw", "zs"]).copy()
    row = {"sample": label, "spec": spec, "n": len(d), "units": d.unit.nunique(), "weeks": d.wk.nunique()}
    if len(d) < MIN_ROWS:
        print(f"  {label:28s} {spec:8s} too few ({len(d)})")
        return row | {"status": "too few"}
    hcols = []
    if heat:
        for u in sorted(d.unit.unique()):
            c = f"h_{u}"
            d[c] = d.fuel_index.where(d.unit == u, 0.0)
            hcols.append(c)
    w = demean(d, [y, "X", "zw", "zs", *hcols], ["unit"])
    Y, X, Z = w[y].to_numpy(), w[["X"]].to_numpy(), w[["zw", "zs"]].to_numpy()
    W = w[hcols].to_numpy() if hcols else np.zeros((len(w), 0))
    cl = d.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    if np.isnan(b).any():
        print(f"  {label:28s} {spec:8s} not identified")
        return row | {"status": "not identified"}
    f1 = sw_f(X, Z, W, cl, 0)
    _, p0 = ar_test(Y, X, Z, W, cl, [0.0])
    _, p1 = ar_test(Y, X, Z, W, cl, [1.0])
    s = ar_set_k1(Y, X[:, 0], Z, W, cl)
    row |= {"status": "weak" if f1 < WEAK_F else "ok", "beta": b[0], "se": np.sqrt(V[0, 0]),
            "first_stage_f": f1, "ar_p_beta0": p0, "ar_p_beta1": p1,
            "ar_set": fmt_intervals(s["intervals"]), "ar_set_p_min": s["p_min"]}
    extra = ""
    if heat:
        h = np.linalg.lstsq(W, Y - X[:, 0] * b[0], rcond=None)[0]
        eff = d.groupby("unit").eff.first()
        gen = d.groupby("unit").eff_is_generic.first()
        fuel = d.groupby("unit").fuel.first()
        nrow = d.groupby("unit").size()
        ok_u = [u for u in sorted(d.unit.unique())
                if fuel[u] == "gas" and not gen[u] and nrow[u] >= MIN_UNIT]
        r = pd.Series({u: h[i] * eff[u] for i, u in enumerate(sorted(d.unit.unique())) if u in ok_u})
        med = float(r.median()) if len(r) else np.nan
        share = float((r.sub(1).abs() <= 0.20).mean()) if len(r) else np.nan
        valid = bool(len(r) > 0 and 0.85 <= med <= 1.15 and share >= 0.5)
        row |= {"h_eff_median": med, "h_eff_share_20": share, "h_units": len(r), "validated": valid}
        extra = f"  h*eff median {med:.3f}, within 20% {share:.2f} of {len(r)} gas units -> {'VALIDATED' if valid else 'NOT validated'}"
    flag = "  WEAK" if f1 < WEAK_F else ""
    print(f"  {label:28s} {spec:8s} n={len(d):>8,} beta {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f})  F {f1:.1f}  "
          f"AR p(beta=0) {p0:.3f} p(beta=1) {p1:.3f}  AR set {row['ar_set']}{flag}{extra}")
    return row


def markdown(d: pd.DataFrame) -> list[dict]:
    """p - c by the sign of X, spec 1's sample."""
    rows = []
    for sign, g in (("X < 0 (net buyer)", d[d.X < 0]), ("X > 0 (net seller)", d[d.X > 0])):
        m = g.p - g.c
        rows.append({"sample": "markdown table", "spec": "levels", "sign": sign, "n": len(g),
                     "median_p_minus_c": float(m.median()), "share_below_cost": float((m < 0).mean())})
        print(f"  {sign:22s} n={len(g):>8,}  median p - c {m.median():+.2f}  share below cost {(m < 0).mean():.3f}")
    return rows


def main() -> int:
    d = pd.read_parquet(PANEL)
    d["pc"] = d.p - d.c
    d["pv"] = d.p - d.var_term
    s1 = d[~d.eff_is_generic]
    rows = []
    print("LEG C -- beta in p - c = beta * X (beta = 1: full Nash); X instrumented by rivals' wind and solar.\n")
    print("SPEC 1, cost imposed (plant-specific efficiency)")
    rows.append(iv(s1, "pc", "pooled", "spec 1"))
    for f in ("gas", "coal"):
        rows.append(iv(s1[s1.fuel == f], "pc", f, "spec 1"))
    for lab, a, b in (("2018-2021", 2018, 2021), ("2022-2023", 2022, 2023)):
        rows.append(iv(s1[s1.date.dt.year.between(a, b)], "pc", lab, "spec 1"))
    rows.append(iv(s1[s1.firm.isin(FIVE)], "pc", "five firms", "spec 1"))
    rows.append(iv(s1[~s1.firm.isin(FIVE)], "pc", "other owners", "spec 1"))
    print("\nSPEC 2, heat rate estimated (all units)")
    rows.append(iv(d, "p", "pooled", "spec 2", heat=True))
    print("\nROUTE 3, declared variable term (declaring units, to 2025-03-18)")
    rows.append(iv(d[d.var_term > 0], "pv", "pooled", "route 3"))
    print("\nTHE MARKDOWN IN LEVELS (spec 1 sample)")
    rows += markdown(s1)
    print(f"\nspec 1 sample: {len(s1):,} unit-periods on {s1.unit.nunique()} units "
          f"(generic-efficiency units excluded: {d[d.eff_is_generic].unit.nunique()})")
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if rows[0].get("status") in ("ok", "weak") else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/python scripts/analysis/leg_c_test.py > $SCRATCH/leg_c_test.log 2>&1; echo "exit $?"; cat $SCRATCH/leg_c_test.log`
Expected: `exit 0`; sections SPEC 1, SPEC 2, ROUTE 3, THE MARKDOWN IN LEVELS; the spec 1 sample line shows the generic-efficiency units excluded (Review Focus 5); `wrote outputs/tables/leg_c_results.csv`. Exit 1 means the pooled spec 1 row could not be computed: stop and report; do not loosen anything.

- [ ] **Step 4: Commit**

```bash
git add scripts/analysis/leg_c_test.py outputs/tables/leg_c_results.csv
git commit -m "Run leg C: the markup condition in levels at the thermal margin"
```

---

### Task 5: Record the result

**Files:**
- Create: `notes/rq-leg-c-thermal-cost.md`
- Modify: `docs/specs/2026-09-29-thesis-framework-design.md` — the Leg C heading (§4), a **Result** paragraph at the end of Leg C, and §8 step 5.

**Interfaces:**
- Consumes: `$SCRATCH/leg_c_panel.log` (Task 3), `$SCRATCH/leg_c_test.log` and `outputs/tables/leg_c_results.csv` (Task 4).

- [ ] **Step 1: Apply the verdict rules**

Mechanical, to the `pooled` rows of spec 1, spec 2 and route 3:

1. **Spec 1 trusted?** Spec 2's `validated` is True. If False, spec 1's β is reported but not read, and spec 2 carries the result.
2. **Readable 2SLS?** `status == "ok"` (first-stage F ≥ 10). If `weak`, quote only the AR columns.
3. **Price-taking not rejected:** `ar_p_beta0 ≥ 0.05`.
4. **Full Nash not rejected:** `ar_p_beta1 ≥ 0.05`.
5. **Conduct between the two:** the AR set is bounded and lies inside (0, 1): β is a fraction of Nash; quote the set.
6. **The markdown in levels:** median p − c below 0 for X < 0 and above 0 for X > 0 — the sign prediction of leg D, in levels.
7. **Route 3 agrees** when its AR set overlaps spec 1's (or spec 2's, if spec 1 is not trusted).

- [ ] **Step 2: Write the note**

Create `notes/rq-leg-c-thermal-cost.md` with these sections, filled from the logs and the CSV:

```markdown
# Leg C — thermal plant, cost observed

Framework spec §4, leg C. Run <YYYY-MM-DD> on branch `leg-c`.
Scripts: `build/build_rival_solar.py`, `analysis/iv_two_endog.py`, `analysis/leg_c_panel.py`,
`analysis/leg_c_test.py`; checks in `qa/`.

## 1. Design, as run
<the condition in levels; the margin rule (partly dispatched, cleared at t-1 and t+1, UTC neighbours);
clean periods; dated owner; X from firm_incentive_net; instruments; unit effects; clusters;
spec 1 / spec 2 / route 3 and the validation rule>

## 2. Sample
<unit-periods by year x fuel and by firm; units; share with plant-specific efficiency; share declaring
a variable term; rows dropped (clean, Repsol pre-Viesgo, owners without X)>

## 3. Results
<one table: sample, spec, n, beta (se), first-stage F, AR p(beta=0), AR p(beta=1), AR set, status;
the spec 2 validation line; the markdown table>

## 4. Verdict
<the Step 1 rules, in order, one sentence each; then one paragraph on what leg C says about beta>

## 5. Limits
<X is built on static unit owners (firm_incentive_net), so TotalEnergies' X before 2022 and Axpo's
before 2022 count Castejón and Amorebieta's sales as theirs; rivals' OFFERED renewables are partly a
choice (spec §8 step 6, the spatial instrument); selection on partial dispatch; start-up costs beyond
t+-1 and part-load efficiency are not in c; coal's API2 price; the gas cap's reference price>
```

- [ ] **Step 3: Update the spec**

In `docs/specs/2026-09-29-thesis-framework-design.md`:
- Change the heading `### Leg C — thermal plant: cost observed. **Designed 2026-09-30; to build.**` to end `**Run <date>; <the verdict in five words or fewer>.**`
- Append at the end of the Leg C section a paragraph starting `**Result, <date>** ([\`rq-leg-c-thermal-cost.md\`](../../notes/rq-leg-c-thermal-cost.md)).`, two to four sentences with the pooled verdict and its key numbers.
- In §8, change step 5 to `5. ~~**Rivals' offered wind**, then **leg C**~~ — run <date>; <verdict> (\`rq-leg-c-thermal-cost.md\`).`

- [ ] **Step 4: Commit**

```bash
git add notes/rq-leg-c-thermal-cost.md docs/specs/2026-09-29-thesis-framework-design.md
git commit -m "Record the leg C result in its note and the spec"
```
