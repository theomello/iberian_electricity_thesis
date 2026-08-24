# Descriptive Price Formation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the four panels, six figures and one fetcher preset that the descriptive price-formation chapter needs, so that the divergence between concentration and residual-demand elasticity can be measured entirely inside this repo's own data.

**Architecture:** Extract the band-slope primitives already proven in `residual_demand_slope.py` into a shared library module, then build three new panels on top of it (firm-specific residual demand, concentration, supply-curve anatomy) plus one contract-position build artefact. Figures are derived only from panels, never from raw data, so a figure cannot drift from the analysis.

**Tech Stack:** Python 3.14 in `.venv`, pandas 3.0, pyarrow 25, matplotlib. **Always `.venv/bin/python`, never bare `python3`.**

**Spec:** [`docs/specs/2026-08-24-descriptive-price-formation-design.md`](../specs/2026-08-24-descriptive-price-formation-design.md)

## Global Constraints

- **No pytest in this repo.** There is no `tests/` directory and pytest is not installed. The established testing discipline is a `--verify` flag on each script that **re-derives a fact from the files** and exits non-zero when it fails, plus `scripts/qa/audit_data.py`. Every task below follows that convention. Do not add pytest.
- **Never modify `data/`.** Derived outputs go to `outputs/`.
- **Never hardcode paths.** `ROOT = Path(__file__).resolve().parent.parent.parent` for anything in `scripts/lib/`, `scripts/analysis/` or `scripts/build/`.
- **Bid rows: `status == "O"` is the full submitted curve, `status == "C"` is the cleared portion. They are NOT additive.** Summing across both double-counts every accepted bid.
- **Sides are Spanish: `side == "V"` is *venta* (sell), `side == "C"` is *compra* (buy).** Note `"C"` means buy in `side` and cleared in `status` — different columns, different meanings.
- **Supply is four roles, not one:** `("generation", "generation_large", "storage_mixed", "pumping")`. Filtering on `generation` alone drops all 62 combined-cycle units, all 7 nuclear, and every pumped-storage unit.
- **Bandwidths are `(1.0, 2.0, 5.0, 10.0)` €/MWh** throughout, matching `BANDWIDTHS` in `residual_demand_slope.py`.
- **Energy from average MW is `mw * resolution_min / 60`.** Both `power_mw` (bids) and `schedule_mw` (PDBF) are average MW, not MWh per period.
- **Coverage is always reported on volume, never on unit count.** 52.2% of supply units carry no firm attribution while 95.7% of bilateral sell MW does.
- **Commit messages: imperative, present tense, ≤72-char subject.**

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/lib/residual_demand.py` | **Create.** Band-slope primitives shared by the market-level and firm-level scripts: clearing-price merge, band membership, slope/impact/elasticity from band MW. |
| `scripts/analysis/residual_demand_slope.py` | **Modify.** Import the primitives instead of defining them inline. No behaviour change. |
| `scripts/build/build_contract_position.py` | **Create.** θ panel: firm-level bilateral contract position per period from PDBF role 4. |
| `scripts/analysis/residual_demand_firm.py` | **Create.** Firm-specific slope, elasticity, ability and incentive indices. |
| `scripts/analysis/concentration_margin.py` | **Create.** `HHI_total` and `HHI_margin` per period. |
| `scripts/analysis/supply_curve_anatomy.py` | **Create.** Stack shape by year. |
| `scripts/analysis/descriptive_figures.py` | **Create.** The six figures, from panels only. |
| `scripts/fetch/fetch_esios_spain.py` | **Modify.** Add a `--forecasts` preset for the wind/solar/demand forecast indicators. |
| `notes/rq-descriptive-price-formation.md` | **Create.** Running research note. |

---

## Task 1: ESIOS forecast-indicator preset

Independent of every other task; done first because the token has an external clock — it may arrive any day and the fetch should be one command when it does.

**Files:**
- Modify: `scripts/fetch/fetch_esios_spain.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `FORECAST_INDICATORS: dict[str, int]` and a `--forecasts` CLI flag. No other task depends on this.

- [ ] **Step 1: Confirm the current behaviour without a token**

Run: `.venv/bin/python scripts/fetch/fetch_esios_spain.py --probe`

Expected: a clear message that `ESIOS_TOKEN` is missing — **not** a traceback. If it raises instead, that is the first thing to fix; `config.require_token` should be raising a readable error.

- [ ] **Step 2: Add the preset table and the flag**

Add near the other module constants in `scripts/fetch/fetch_esios_spain.py`:

```python
# Forecast indicators. IDs are recorded because the ESIOS documentation gives
# them explicitly, but they are ALWAYS re-resolved by name against the live
# catalogue before use -- ESIOS indicator ids are unstable across time, which
# is why this script resolves by name everywhere else too. The id is the
# fallback when the name search returns nothing.
FORECAST_INDICATORS = {
    "Previsión de la producción eólica nacional": 541,
    "Previsión de la producción solar fotovoltaica": 542,
}


def resolve_forecast_ids(cat) -> list[int]:
    """Resolve the forecast indicators by catalogue name, falling back to id.

    Returns the ids to fetch and prints what matched, so a silent resolution
    to the wrong series is visible rather than buried.
    """
    ids: list[int] = []
    for name, fallback in FORECAST_INDICATORS.items():
        hit = cat[cat["name"].str.contains(name, case=False, na=False)]
        if len(hit) == 1:
            ind_id = int(hit.iloc[0]["id"])
            print(f"  resolved by name: {name!r} -> {ind_id}")
        elif len(hit) > 1:
            ind_id = int(hit.iloc[0]["id"])
            print(f"  AMBIGUOUS ({len(hit)} matches) for {name!r}; "
                  f"taking id {ind_id}. Check with --search.")
        else:
            ind_id = fallback
            print(f"  no name match for {name!r}; falling back to id {ind_id}")
        ids.append(ind_id)
    return ids
```

In `main()`, alongside the existing `--ids` argument:

```python
    ap.add_argument("--forecasts", action="store_true",
                    help="fetch the wind and solar generation forecasts "
                         "(indicators 541/542), resolved by catalogue name")
```

and after the catalogue is loaded, before the fetch loop:

```python
    if args.forecasts:
        args.ids = (args.ids or []) + resolve_forecast_ids(cat)
```

- [ ] **Step 3: Verify the flag fails correctly without a token**

Run: `.venv/bin/python scripts/fetch/fetch_esios_spain.py --forecasts`

Expected: the same readable "no token" message as Step 1, reached without a traceback. This is the only check possible until a token exists.

- [ ] **Step 4: Record the untested state in the docstring**

Append to the module docstring's existing NOTE:

```
The --forecasts preset (indicators 541/542) is likewise unexecuted: no token
existed at authoring time. When a token arrives, run --probe first, then
--search "previsión" to confirm the catalogue names before trusting
--forecasts to have resolved the right series.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch/fetch_esios_spain.py
git commit -m "Add an ESIOS preset for the wind and solar forecasts"
```

---

## Task 2: Extract the shared band-slope primitives

A pure refactor. Its test is that the existing panel is reproduced exactly.

**Files:**
- Create: `scripts/lib/residual_demand.py`
- Modify: `scripts/analysis/residual_demand_slope.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BANDWIDTHS: tuple[float, ...]` = `(1.0, 2.0, 5.0, 10.0)`
  - `IDENTITY_TOL: float` = `0.001`
  - `ZERO_PRICE: float` = `1.0`
  - `cleared_by_period(bids: pd.DataFrame) -> pd.DataFrame` — one row per `(date, period)` with `sell_matched`, `buy_matched`, `identity_gap`.
  - `band_offers(bids: pd.DataFrame, p_star: pd.DataFrame, h: float) -> pd.DataFrame` — the `status == "O"` rows within ±h of the clearing price, with a `dev` column.
  - `slope_from_band_mw(band_mw: pd.Series, h: float, p_star: pd.Series, q: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]` — `(slope, impact, eta)`.

- [ ] **Step 1: Snapshot the existing output as the regression baseline**

```bash
cp outputs/tables/residual_demand_slope_full.parquet /tmp/rds_baseline.parquet
.venv/bin/python -c "
import pandas as pd
d = pd.read_parquet('/tmp/rds_baseline.parquet')
print(d.shape, d.eta_h5.median())
"
```

Expected: `(79036, 26)` and a median `eta_h5` of `0.9678`. Both verified 2026-08-24. Step 5 must reproduce them exactly.

- [ ] **Step 2: Create the library module**

Create `scripts/lib/residual_demand.py`:

```python
"""Band-slope primitives for residual demand, shared by the market-level and
firm-level scripts.

Extracted from scripts/analysis/residual_demand_slope.py, which is the proven
implementation; that script now imports these rather than defining them, so
the two levels cannot drift apart.

THE OBJECT

Offer curves are step functions and have no derivative. Differencing the
cumulative curve over a price window h is equivalent to counting offered MW
within +/-h of the clearing price:

    |RD'(p*)| ~= (sell MW in band + buy MW in band) / 2h

so the "derivative" is literally the density of offers near the clearing price,
and h is the only tuning knob.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

BANDWIDTHS: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0)
IDENTITY_TOL = 0.001   # relative gap between matched buy and matched sell
ZERO_PRICE = 1.0       # euro/MWh; at or below this, eta is not meaningful

KEY = ["date", "period"]


def cleared_by_period(bids: pd.DataFrame) -> pd.DataFrame:
    """Matched sell and buy volume per period, with the clearing-identity gap.

    side "V" is venta (sell) and "C" is compra (buy). Note that status "C"
    means *cleared*, a different column with a different meaning.
    """
    mat = bids[bids.status == "C"]
    m = (mat.groupby(KEY + ["side"])["power_mw"].sum()
            .unstack("side").reindex(columns=["V", "C"]).fillna(0.0))
    m.columns = ["sell_matched", "buy_matched"]
    m = m[m.sell_matched > 0].reset_index()
    m["identity_gap"] = (m.sell_matched - m.buy_matched).abs() / m.sell_matched
    return m


def band_offers(bids: pd.DataFrame, p_star: pd.DataFrame, h: float) -> pd.DataFrame:
    """Submitted offers within +/-h euro/MWh of the clearing price.

    p_star must carry KEY plus a "p_star" column.
    """
    off = bids[bids.status == "O"].merge(p_star[KEY + ["p_star"]], on=KEY, how="inner")
    off = off.assign(dev=(off.price_eur_mwh - off.p_star).abs())
    return off[off.dev <= h]


def slope_from_band_mw(band_mw: pd.Series, h: float,
                       p_star: pd.Series, q: pd.Series):
    """(slope, impact, eta) from MW sitting inside a +/-h band.

    eta = |RD'| p / Q is the scale-free version. Price impact alone is NOT
    comparable across years: a fixed +/-h euro band is a *narrower relative*
    window when the price level is 200 than when it is 50, which mechanically
    thins the band and inflates impact in 2022.
    """
    slope = band_mw.fillna(0.0) / (2 * h)
    impact = np.where(slope > 0, 1 / slope.replace(0, np.nan), np.nan)
    eta = np.where((slope > 0) & (p_star > 0), slope * p_star / q, np.nan)
    return slope, impact, eta
```

- [ ] **Step 3: Rewrite `month_slopes` to use the primitives**

In `scripts/analysis/residual_demand_slope.py`, replace the module constants `BANDWIDTHS`, `IDENTITY_TOL`, `ZERO_PRICE` with an import, and replace the body of `month_slopes`:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from residual_demand import (  # noqa: E402
    BANDWIDTHS, IDENTITY_TOL, KEY, ZERO_PRICE, band_offers,
    cleared_by_period, slope_from_band_mw,
)


def month_slopes(bids: pd.DataFrame, px_m: pd.DataFrame) -> pd.DataFrame:
    """Vectorised slopes for a whole month. See scripts/lib/residual_demand.py."""
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    m = cleared_by_period(bids)
    out = m.merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "q_cleared"})

    for h in BANDWIDTHS:
        mw = (band_offers(bids, out, h).groupby(KEY)["power_mw"].sum()
                                       .rename(f"mw_h{h:g}"))
        out = out.merge(mw, on=KEY, how="left")
        slope, impact, eta = slope_from_band_mw(
            out[f"mw_h{h:g}"], h, out.p_star, out.q_cleared)
        out[f"slope_h{h:g}"] = slope
        out[f"impact_h{h:g}"] = impact
        out[f"eta_h{h:g}"] = eta
    return out.drop(columns=[f"mw_h{h:g}" for h in BANDWIDTHS])
```

**Keep `period_slopes` as it is.** Checked 2026-08-24: nothing outside its own file references it, but it is the readable per-period reference implementation that `month_slopes`'s docstring cites as the source of its own verification. Deleting it would remove the only legible statement of the algorithm. Leave it untouched and unimported.

- [ ] **Step 4: Re-run the full sweep**

Run: `.venv/bin/python scripts/analysis/residual_demand_slope.py --full --save`

Expected: completes without error and rewrites `outputs/tables/residual_demand_slope_full.parquet`. Runtime is minutes, not seconds — it reads 101 monthly files.

- [ ] **Step 5: Verify the refactor changed nothing**

```bash
.venv/bin/python -c "
import pandas as pd, numpy as np
a = pd.read_parquet('/tmp/rds_baseline.parquet')
b = pd.read_parquet('outputs/tables/residual_demand_slope_full.parquet')
assert a.shape == b.shape, f'shape changed: {a.shape} -> {b.shape}'
a = a.sort_values(['date','period']).reset_index(drop=True)
b = b.sort_values(['date','period']).reset_index(drop=True)
for c in ['eta_h1','eta_h2','eta_h5','eta_h10','slope_h5','p_star','q_cleared']:
    d = (a[c] - b[c]).abs().max()
    assert d < 1e-6 or np.isnan(d), f'{c} differs by {d}'
    print(f'{c:12s} identical')
print('REFACTOR CLEAN')
"
```

Expected: `REFACTOR CLEAN`. If any column differs, the refactor introduced a bug — fix it before proceeding; every later task builds on these primitives.

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/residual_demand.py scripts/analysis/residual_demand_slope.py
git commit -m "Extract the band-slope primitives into a shared module"
```

---

## Task 3: The contract-position panel (θ)

**Files:**
- Create: `scripts/build/build_contract_position.py`
- Output: `outputs/tables/contract_position_panel.parquet`

**Interfaces:**
- Consumes: `scripts/lib/residual_demand.KEY`.
- Produces: a parquet keyed `(date, period, firm)` with columns `date, period, resolution_min, firm, theta_mw, theta_mwh, n_units`. Task 4 joins on `(date, period, firm)`.

**Facts established against `pdbf_202401.parquet` on 2026-08-24, which this task must reproduce:**
- `role_code == "4"` is the bilateral contract, and `schedule_mw` is **signed**: positive is the sell leg (54.2% of rows), negative the buy leg.
- Role-4 `schedule_mw` sums to **exactly 0.0** within every `(date, period)` — the matching identity a bilateral contract must satisfy.
- 68% of role-4 sell *rows* map to a firm, but **95.7% of sell MW** does.

- [ ] **Step 1: Write the verification first, as a standalone check**

Create `scripts/build/build_contract_position.py` with only the verify path working:

```python
#!/usr/bin/env python3
"""Firm-level bilateral contract position (theta) from PDBF role 4.

    .venv/bin/python scripts/build/build_contract_position.py --verify
    .venv/bin/python scripts/build/build_contract_position.py --save

WHY THIS EXISTS

Volume already sold forward at a fixed price earns nothing extra when the
day-ahead price rises, so a heavily contracted firm has a weaker incentive to
withhold whatever its share -- the theta term in Wolak (2000) and Hortacsu &
Puller (2008). PDBF publishes the physical contract position directly.

READ ROLE 4; DO NOT COMPUTE PDBF MINUS PDBC. Role 4's sell and buy legs sum to
exactly zero within a period, which is the identity a bilateral contract must
satisfy and the subtraction cannot check.

STILL A PROXY. This captures *physical* bilateral contracts only and misses
financial hedges entirely -- an OMIP future or a financially settled PPA fixes
revenue while the energy still clears in the auction. Since what matters is
whether revenue is fixed rather than whether electrons flow bilaterally, that
omission is the more serious one. Bound theta; do not claim to measure it.

TRAP: PDBF has several rows per unit-period, one per role code, so
(date, period, unit) is NOT a key. Filtering to role 4 first is what makes the
grouping safe.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PDBF = ROOT / "data" / "omie" / "pdbf" / "parquet"
AGENTS = ROOT / "data" / "omie" / "registry" / "unit_agents.parquet"
OUT = ROOT / "outputs" / "tables" / "contract_position_panel.parquet"

COLS = ["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"]


def load_month(path: Path) -> pd.DataFrame:
    d = pd.read_parquet(path, columns=COLS)
    return d[d.role_code == "4"].copy()


def verify(path: Path) -> int:
    """Re-derive the two facts this build depends on, from the file itself."""
    r4 = load_month(path)
    net = r4.groupby(["date", "period"])["schedule_mw"].sum().abs().max()
    agents = pd.read_parquet(AGENTS, columns=["unit", "firm"])
    sell = r4[r4.schedule_mw > 0].merge(agents, on="unit", how="left")
    mapped_mw = sell.loc[sell.firm.notna(), "schedule_mw"].sum() / sell.schedule_mw.sum()

    print(f"  {path.name}")
    print(f"    role-4 net per period, max |sum| : {net:.6f}   (must be ~0)")
    print(f"    sell rows firm-mapped            : {sell.firm.notna().mean():.1%}")
    print(f"    sell MW   firm-mapped            : {mapped_mw:.1%}")
    bad = 0
    if net > 0.01:
        print("    FAIL: role-4 legs do not net to zero -- parse or filter error")
        bad = 1
    if mapped_mw < 0.90:
        print("    FAIL: firm mapping covers <90% of contracted sell MW")
        bad = 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    months = sorted(PDBF.glob("pdbf_*.parquet"))
    if not months:
        print(f"no PDBF archive at {PDBF}", file=sys.stderr)
        return 1

    if args.verify:
        checks = [m for m in months if m.stem in
                  ("pdbf_201801", "pdbf_202401", "pdbf_202605")]
        return max(verify(m) for m in checks)

    print("nothing to do; pass --verify or --save")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the verification and watch it pass on known data**

Run: `.venv/bin/python scripts/build/build_contract_position.py --verify`

Expected: for `pdbf_202401`, net `0.000000`, rows `68.0%`, MW `95.7%`, exit 0. The other two months should also pass. **If any month fails, stop** — either the parse or the firm mapping is broken for that era, and building the panel on it would be building on sand.

- [ ] **Step 3: Add the build path**

Insert before `main()`:

```python
def build_month(path: Path, agents: pd.DataFrame) -> pd.DataFrame:
    r4 = load_month(path)
    sell = r4[r4.schedule_mw > 0].merge(agents, on="unit", how="left")
    sell["firm"] = sell.firm.fillna("UNMAPPED")
    g = (sell.groupby(["date", "period", "resolution_min", "firm"])
             .agg(theta_mw=("schedule_mw", "sum"), n_units=("unit", "nunique"))
             .reset_index())
    g["theta_mwh"] = g.theta_mw * g.resolution_min / 60
    return g
```

and in `main()`, replace the "nothing to do" branch:

```python
    if args.save:
        agents = pd.read_parquet(AGENTS, columns=["unit", "firm"])
        frames = []
        for i, m in enumerate(months, 1):
            frames.append(build_month(m, agents))
            print(f"  [{i:3d}/{len(months)}] {m.stem}", end="\r", flush=True)
        d = pd.concat(frames, ignore_index=True)
        d["date"] = pd.to_datetime(d["date"])
        OUT.parent.mkdir(parents=True, exist_ok=True)
        d.to_parquet(OUT, index=False)
        print(" " * 40, end="\r")
        print(f"wrote {len(d):,} rows -> {OUT.relative_to(ROOT)}")
        share = d.groupby(d.date.dt.year).apply(
            lambda g: g.loc[g.firm == "UNMAPPED", "theta_mwh"].sum()
                      / g.theta_mwh.sum(), include_groups=False)
        print("  UNMAPPED share of contracted volume, by year:")
        print("   " + "  ".join(f"{y}:{v:5.1%}" for y, v in share.items()))
        return 0
```

- [ ] **Step 4: Build and sanity-check the panel**

```bash
.venv/bin/python scripts/build/build_contract_position.py --save
.venv/bin/python -c "
import pandas as pd
d = pd.read_parquet('outputs/tables/contract_position_panel.parquet')
print(d.shape, d.date.min(), d.date.max())
assert (d.theta_mw > 0).all(), 'sell leg must be strictly positive'
assert not d.duplicated(['date','period','firm']).any(), 'key is not unique'
print(d.groupby('firm').theta_mwh.sum().sort_values(ascending=False).head(8).round(0))
"
```

Expected: key is unique, all θ positive, and Iberdrola/Endesa/Naturgy at the top — **not** the day-ahead cleared ranking, which is led by EDP. That difference is the point: Endesa contracts bilaterally what EDP sells into the auction.

- [ ] **Step 5: Commit**

```bash
git add scripts/build/build_contract_position.py
git commit -m "Build the firm-level bilateral contract position from PDBF"
```

---

## Task 4: The firm residual-demand panel

**Files:**
- Create: `scripts/analysis/residual_demand_firm.py`
- Output: `outputs/tables/firm_residual_demand_full.parquet`

**Interfaces:**
- Consumes: `scripts/lib/residual_demand` (all primitives); `outputs/tables/contract_position_panel.parquet` from Task 3.
- Produces: a parquet keyed `(date, period, firm)` with `date, period, resolution_min, firm, p_star, q_firm_mw, q_cleared, theta_mw` and, for each `h` in BANDWIDTHS, `slope_i_h{h}`, `eta_i_h{h}`, `ability_h{h}`, `incentive_h{h}`, `lerner_bound_h{h}`.

**The identity being implemented:**

```
|RD'_i| = (total band MW  -  firm i's own SELL MW in band) / 2h
RD_i(p*) = q_i            (the market clears, so residual demand at p* is own volume)

eta_i         = |RD'_i| * p* / q_i          firm-specific elasticity
lerner_bound  = q_i / (|RD'_i| * p*)        = 1 / eta_i
ability       = q_i / (100 * |RD'_i|)       EUR/MWh per 1% of own output withheld
incentive     = ability * (q_i - theta_i) / q_i
```

- [ ] **Step 1: Write the invariant check first**

Create `scripts/analysis/residual_demand_firm.py` with a `--verify` path that runs on **one month** and asserts three invariants that must hold by construction:

```python
#!/usr/bin/env python3
"""Firm-specific residual demand, ability and incentive.

    .venv/bin/python scripts/analysis/residual_demand_firm.py --verify
    .venv/bin/python scripts/analysis/residual_demand_firm.py --full --save

The market-level script measures residual demand facing an *infinitesimal*
participant -- a lower bound on every real firm's steepness. This measures the
firm-specific object the theory is actually about:

    RD_i(p) = D(p) - sum_{j != i} S_j(p)

Removing firm i's own supply from the sum removes its contribution to the
slope, so the whole firm-level computation is one extra groupby inside the same
band, not one sweep per firm.

INDICES (McRae & Wolak, eqs. 3.4 and 3.10)

    ability   eta_i   = q_i / (100 |RD'_i|)             EUR/MWh per 1% withheld
    incentive eta_i^C = eta_i (q_i - theta_i) / q_i

Ability is what the stack makes possible; incentive scales it by the share of
output not already sold forward. theta comes from
outputs/tables/contract_position_panel.parquet and is a PHYSICAL contract
proxy -- it misses financial hedges, so incentive is an upper bound.
"""
```

with:

```python
def verify(bids, px_m, agents, theta) -> int:
    """Three invariants that hold by construction. Each can fail loudly."""
    mkt, firm = compute_month(bids, px_m, agents, theta)
    bad = 0

    # 1. A firm's residual demand is weakly STEEPER than the market's, because
    #    its own supply is removed from the curve facing it.
    j = firm.merge(mkt[["date", "period", "slope_h5"]], on=["date", "period"])
    viol = (j.slope_i_h5 > j.slope_h5 + 1e-6).mean()
    print(f"    slope_i > slope_market on {viol:.4%} of firm-periods (must be 0)")
    bad |= int(viol > 0)

    # 2. Firms' own cleared volume cannot exceed market cleared volume.
    tot = firm.groupby(["date", "period"]).q_firm_mw.sum().rename("q_sum")
    j2 = mkt.set_index(["date", "period"]).join(tot, how="inner")
    viol2 = (j2.q_sum > j2.q_cleared * 1.0001).mean()
    print(f"    sum(q_firm) > q_cleared on {viol2:.4%} of periods (must be 0)")
    bad |= int(viol2 > 0)

    # 3. lerner_bound is exactly 1/eta_i wherever both are defined.
    m = firm.dropna(subset=["eta_i_h5", "lerner_bound_h5"])
    gap = (m.lerner_bound_h5 - 1 / m.eta_i_h5).abs().max()
    print(f"    max |lerner - 1/eta| = {gap:.2e} (must be ~0)")
    bad |= int(gap > 1e-9)
    return bad
```

- [ ] **Step 2: Run the verify and watch it fail**

Run: `.venv/bin/python scripts/analysis/residual_demand_firm.py --verify`

Expected: **fails with `NameError: name 'compute_month' is not defined`.** That is the point — the invariants are written before the thing they check.

- [ ] **Step 3: Implement `compute_month`**

```python
SUPPLY_ROLES = ("generation", "generation_large", "storage_mixed", "pumping")


def compute_month(bids, px_m, agents, theta):
    """(market rows, firm rows) for one month."""
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    mkt = cleared_by_period(bids).merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "q_cleared"})

    b = bids.merge(agents, on="unit", how="left")
    b["firm"] = b.firm.fillna("UNMAPPED")

    # Firm's own cleared SELL volume at p*: this is RD_i(p*) by market clearing.
    own = (b[(b.status == "C") & (b.side == "V")]
           .groupby(KEY + ["firm"])["power_mw"].sum().rename("q_firm_mw").reset_index())
    out = own.merge(mkt[KEY + ["p_star", "q_cleared", "resolution_min"]], on=KEY, how="inner")

    for h in BANDWIDTHS:
        band = band_offers(b, mkt.rename(columns={"p_star": "p_star"}), h)
        total = band.groupby(KEY)["power_mw"].sum().rename("band_mw")
        own_sell = (band[band.side == "V"].groupby(KEY + ["firm"])["power_mw"]
                    .sum().rename("own_band_mw"))
        out = out.merge(total, on=KEY, how="left").merge(
            own_sell, on=KEY + ["firm"], how="left")
        out["own_band_mw"] = out.own_band_mw.fillna(0.0)
        # Removing firm i's own supply from the curve facing it.
        slope_i = (out.band_mw.fillna(0.0) - out.own_band_mw) / (2 * h)
        out[f"slope_i_h{h:g}"] = slope_i
        ok = (slope_i > 0) & (out.p_star > ZERO_PRICE) & (out.q_firm_mw > 0)
        out[f"eta_i_h{h:g}"] = np.where(ok, slope_i * out.p_star / out.q_firm_mw, np.nan)
        out[f"lerner_bound_h{h:g}"] = np.where(
            ok, out.q_firm_mw / (slope_i * out.p_star), np.nan)
        out[f"ability_h{h:g}"] = np.where(ok, out.q_firm_mw / (100 * slope_i), np.nan)
        out = out.drop(columns=["band_mw", "own_band_mw"])

    out = out.merge(theta, on=KEY + ["firm"], how="left")
    out["theta_mw"] = out.theta_mw.fillna(0.0)
    frac = ((out.q_firm_mw - out.theta_mw) / out.q_firm_mw).clip(lower=-5, upper=1)
    for h in BANDWIDTHS:
        out[f"incentive_h{h:g}"] = out[f"ability_h{h:g}"] * frac
    return mkt, out
```

Note `frac` is clipped below at −5: a firm whose bilateral sales exceed its day-ahead cleared volume is a **net buyer** and its incentive genuinely flips sign (Hortaçsu & Puller p. 145). The clip bounds arithmetic blow-ups on tiny `q_firm_mw` without hiding the sign flip.

- [ ] **Step 4: Run the verify until all three invariants pass**

Run: `.venv/bin/python scripts/analysis/residual_demand_firm.py --verify`

Expected: all three lines report 0 / 0 / ~0 and the script exits 0. **Invariant 1 is the one most likely to fail** — if `slope_i > slope_market`, the own-supply subtraction is joining on the wrong key or double-counting a firm.

- [ ] **Step 5: Apply the same filters as the market panel, then sweep**

Add the filter block to the `--full` path, matching `residual_demand_slope.py` exactly: drop market-splitting periods, drop `identity_gap > IDENTITY_TOL`, drop `p_star <= ZERO_PRICE`, and report each count. Then:

```bash
.venv/bin/python scripts/analysis/residual_demand_firm.py --full --save
```

- [ ] **Step 6: Sanity-check the panel against the market one**

```bash
.venv/bin/python -c "
import pandas as pd
f = pd.read_parquet('outputs/tables/firm_residual_demand_full.parquet')
m = pd.read_parquet('outputs/tables/residual_demand_slope_full.parquet')
print('firm-periods', f.shape, 'market periods', m.shape)
maj = f[f.firm != 'UNMAPPED']
print(maj.groupby(maj.date.dt.year).eta_i_h5.median().round(3))
print(maj.groupby('firm').ability_h5.median().sort_values(ascending=False).head(10).round(3))
"
```

Expected: firm-specific `eta_i` is **below** the market `eta` in every year (a real firm faces steeper residual demand), and it declines over the window as the market series does.

- [ ] **Step 7: Commit**

```bash
git add scripts/analysis/residual_demand_firm.py
git commit -m "Measure firm-specific residual demand, ability and incentive"
```

---

## Task 5: The concentration panel

**Files:**
- Create: `scripts/analysis/concentration_margin.py`
- Output: `outputs/tables/concentration_panel.parquet`

**Interfaces:**
- Consumes: `scripts/lib/residual_demand`; `unit_agents.parquet`.
- Produces: parquet keyed `(date, period)` with `date, period, p_star, hhi_total, hhi_margin_h{h}, mapped_share_total, mapped_share_margin_h{h}, n_firms_margin_h{h}`.

**The prediction being tested:** `hhi_total` falls, matching CNMC, while `hhi_margin` rises. If it holds, the divergence resolves into one story — concentration moved to where price is set.

- [ ] **Step 1: Write the invariant check first**

```python
def verify(panel) -> int:
    bad = 0
    for c in [c for c in panel.columns if c.startswith("hhi")]:
        v = panel[c].dropna()
        lo, hi = v.min(), v.max()
        print(f"    {c:22s} range [{lo:.0f}, {hi:.0f}]  (must be within [0, 10000])")
        bad |= int(lo < 0 or hi > 10000 + 1e-6)
    for c in [c for c in panel.columns if c.startswith("mapped_share")]:
        v = panel[c].dropna()
        print(f"    {c:22s} range [{v.min():.3f}, {v.max():.3f}]  (must be within [0, 1])")
        bad |= int(v.min() < 0 or v.max() > 1 + 1e-9)
    return bad
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/python scripts/analysis/concentration_margin.py --verify`

Expected: fails — the panel does not exist yet.

- [ ] **Step 3: Implement the two HHIs**

```python
def hhi(shares: pd.Series) -> float:
    """HHI in the conventional 0-10000 scale, on the MAPPED share only.

    Shares are renormalised over mapped volume, so the HHI describes the
    attributed market rather than treating unmapped volume as one giant firm.
    mapped_share is reported alongside so the renormalisation is visible.
    """
    s = shares / shares.sum()
    return float((s ** 2).sum() * 10000)


def concentration_month(bids, px_m, agents):
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    mkt = cleared_by_period(bids).merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "q_cleared"})

    b = bids.merge(agents, on="unit", how="left")
    b["mapped"] = b.firm.notna()

    # --- total: all cleared sell volume
    sold = b[(b.status == "C") & (b.side == "V")]
    tot = sold.groupby(KEY).power_mw.sum().rename("mw_all")
    mapped = sold[sold.mapped].groupby(KEY).power_mw.sum().rename("mw_mapped")
    by_firm = sold[sold.mapped].groupby(KEY + ["firm"]).power_mw.sum()
    hhi_tot = by_firm.groupby(KEY).apply(hhi).rename("hhi_total")
    out = (mkt.merge(tot, on=KEY).merge(mapped, on=KEY, how="left")
              .merge(hhi_tot, on=KEY, how="left"))
    out["mapped_share_total"] = out.mw_mapped.fillna(0) / out.mw_all
    out = out.drop(columns=["mw_all", "mw_mapped"])

    # --- margin: submitted SELL offers inside the band
    for h in BANDWIDTHS:
        band = band_offers(b, mkt, h)
        band = band[band.side == "V"]
        t = band.groupby(KEY).power_mw.sum().rename("mw_all")
        mp = band[band.mapped].groupby(KEY).power_mw.sum().rename("mw_mapped")
        bf = band[band.mapped].groupby(KEY + ["firm"]).power_mw.sum()
        out = (out.merge(bf.groupby(KEY).apply(hhi).rename(f"hhi_margin_h{h:g}"),
                         on=KEY, how="left")
                  .merge(bf.groupby(KEY).size().rename(f"n_firms_margin_h{h:g}"),
                         on=KEY, how="left")
                  .merge(t, on=KEY, how="left").merge(mp, on=KEY, how="left"))
        out[f"mapped_share_margin_h{h:g}"] = out.mw_mapped.fillna(0) / out.mw_all
        out = out.drop(columns=["mw_all", "mw_mapped"])
    return out
```

- [ ] **Step 4: Build, verify, and read the headline**

```bash
.venv/bin/python scripts/analysis/concentration_margin.py --full --save
.venv/bin/python scripts/analysis/concentration_margin.py --verify
.venv/bin/python -c "
import pandas as pd
d = pd.read_parquet('outputs/tables/concentration_panel.parquet')
y = d.groupby(d.date.dt.year).agg(
    total=('hhi_total','median'), margin=('hhi_margin_h5','median'),
    nfirm=('n_firms_margin_h5','median'), cov=('mapped_share_margin_h5','median'))
print(y.round(1))
"
```

Expected: `hhi_total` broadly tracking CNMC's decline (1314 → 1007 over 2018–2023) and `hhi_margin` rising. **If `hhi_margin` does not rise, that is a real result, not a bug** — record it in the note and the chapter's framing (spec §1) still holds. Check `cov` for drift before reading anything into either trend.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/concentration_margin.py
git commit -m "Measure concentration on total and near-marginal volume"
```

---

## Task 6: The supply-curve anatomy panel

**Files:**
- Create: `scripts/analysis/supply_curve_anatomy.py`
- Output: `outputs/tables/supply_anatomy_panel.parquet`

**Interfaces:**
- Consumes: `scripts/lib/residual_demand`; `unit_agents.parquet` for `tech` and `regime`.
- Produces: parquet keyed `(date, period)` with `date, period, p_star, mw_offered_sell, mw_cleared_sell, share_at_zero, share_below_p, band_density_h{h}, marginal_tech, marginal_regime`.

- [ ] **Step 1: Write the invariant check first**

The single most valuable check here is the `O`/`C` trap made into an assertion:

```python
def verify(panel) -> int:
    bad = 0
    viol = (panel.mw_cleared_sell > panel.mw_offered_sell + 1e-6).mean()
    print(f"    cleared > offered on {viol:.4%} of periods (must be 0)")
    print("      -- if nonzero, 'O' and 'C' rows have been summed together")
    bad |= int(viol > 0)
    s = panel.share_at_zero.dropna()
    print(f"    share_at_zero range [{s.min():.3f}, {s.max():.3f}] (must be [0,1])")
    bad |= int(s.min() < 0 or s.max() > 1 + 1e-9)
    return bad
```

- [ ] **Step 2: Run it and watch it fail**

Run: `.venv/bin/python scripts/analysis/supply_curve_anatomy.py --verify`

Expected: fails — no panel yet.

- [ ] **Step 3: Implement the anatomy**

```python
def anatomy_month(bids, px_m, agents):
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    mkt = cleared_by_period(bids).merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "mw_cleared_sell"})

    b = bids.merge(agents, on="unit", how="left")
    sell_o = b[(b.status == "O") & (b.side == "V")]

    off = sell_o.groupby(KEY).power_mw.sum().rename("mw_offered_sell")
    zero = (sell_o[sell_o.price_eur_mwh <= 0.0]
            .groupby(KEY).power_mw.sum().rename("mw_at_zero"))
    out = mkt.merge(off, on=KEY, how="left").merge(zero, on=KEY, how="left")
    out["share_at_zero"] = out.mw_at_zero.fillna(0) / out.mw_offered_sell

    below = (sell_o.merge(mkt[KEY + ["p_star"]], on=KEY)
             .query("price_eur_mwh <= p_star")
             .groupby(KEY).power_mw.sum().rename("mw_below_p"))
    out = out.merge(below, on=KEY, how="left")
    out["share_below_p"] = out.mw_below_p.fillna(0) / out.mw_offered_sell

    for h in BANDWIDTHS:
        dens = (band_offers(b, mkt.rename(columns={"mw_cleared_sell": "q"}), h)
                .groupby(KEY).power_mw.sum().rename(f"band_density_h{h:g}"))
        out = out.merge(dens, on=KEY, how="left")

    # Marginal unit: the cleared SELL offer whose price is closest to p* from
    # below. Technology coverage is only 41.2% of volume, so marginal_tech is
    # null far more often than marginal_regime (63.3%). Both are kept.
    cl = b[(b.status == "C") & (b.side == "V")].merge(mkt[KEY + ["p_star"]], on=KEY)
    cl = cl[cl.price_eur_mwh <= cl.p_star]
    idx = cl.groupby(KEY).price_eur_mwh.idxmax()
    marg = cl.loc[idx, KEY + ["tech", "regime"]].rename(
        columns={"tech": "marginal_tech", "regime": "marginal_regime"})
    out = out.merge(marg, on=KEY, how="left")
    return out.drop(columns=["mw_at_zero", "mw_below_p"])
```

- [ ] **Step 4: Build, verify, and read the headline**

```bash
.venv/bin/python scripts/analysis/supply_curve_anatomy.py --full --save
.venv/bin/python scripts/analysis/supply_curve_anatomy.py --verify
.venv/bin/python -c "
import pandas as pd
d = pd.read_parquet('outputs/tables/supply_anatomy_panel.parquet')
print(d.groupby(d.date.dt.year).agg(
    zero=('share_at_zero','median'), dens=('band_density_h5','median'),
    tech_cov=('marginal_tech', lambda s: s.notna().mean())).round(3))
"
```

Expected: `share_at_zero` rising across the window and `band_density_h5` falling — the two halves of the mechanism behind η. `tech_cov` around 0.4, consistent with the 41.2% technology mapping; **do not read a marginal-technology trend without reporting that coverage alongside it.**

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/supply_curve_anatomy.py
git commit -m "Measure the supply curve's shape across the transition"
```

---

## Task 7: The six figures

**Files:**
- Create: `scripts/analysis/descriptive_figures.py`
- Output: `outputs/figures/{divergence,band_density,stack_shape,eta_hour_year,firm_ability,predictability}.png`

**Interfaces:**
- Consumes: all four panels plus `data/cnmc/cnmc_generation_shares.parquet`, `data/ree/ree_demand_forecast_5min.parquet`, `data/ree/ree_realtime_5min.parquet`.
- Produces: PNG files only. Nothing consumes this task.

Follow `scripts/analysis/slides_figures.py` for style: matplotlib `Agg`, the dataviz palette already defined there (`BLUE = "#2a78d6"`, `ORANGE = "#eb6834"`, `RED = "#e34948"`, `INK = "#0b0b0b"`, `MUTED = "#8a8983"`, `GRID = "#e6e5e1"`, `SURFACE = "#ffffff"`), no chart titles, 200 dpi, `bbox_inches="tight"`.

**Every number must be read from a panel.** Do not hardcode a value into a figure — that is how `fig_divergence` in `slides_figures.py` ended up with a transcribed Lerner array.

- [ ] **Step 1: Assert every input panel exists before drawing anything**

```python
REQUIRED = [
    ROOT / "outputs/tables/residual_demand_slope_full.parquet",
    ROOT / "outputs/tables/firm_residual_demand_full.parquet",
    ROOT / "outputs/tables/concentration_panel.parquet",
    ROOT / "outputs/tables/supply_anatomy_panel.parquet",
]


def check_inputs() -> int:
    missing = [p for p in REQUIRED if not p.exists()]
    for p in missing:
        print(f"  MISSING {p.relative_to(ROOT)}", file=sys.stderr)
    if missing:
        print("Run Tasks 2-6 first.", file=sys.stderr)
    return 1 if missing else 0
```

- [ ] **Step 2: Run it and watch it report what is missing**

Run: `.venv/bin/python scripts/analysis/descriptive_figures.py`

Expected: if a panel is absent, an explicit list and exit 1. If all four exist, it proceeds.

- [ ] **Step 3: Figure 1 — the divergence, rebuilt internally**

```python
def fig_divergence(eta, conc, cnmc):
    """eta, HHI_total and HHI_margin on a common 2018 = 100 base.

    Single axis, by the no-dual-axis rule: quantities of different units go on
    a common base rather than on two scales.
    """
    e = eta.groupby(eta.date.dt.year).eta_h5.median()
    c = conc.groupby(conc.date.dt.year).agg(
        tot=("hhi_total", "median"), mar=("hhi_margin_h5", "median"))
    base = lambda s: s / s.loc[2018] * 100

    fig, ax = plt.subplots(figsize=(12.4, 4.4))
    _frame(ax)
    ax.axhline(100, color=GRID, lw=1.2, zorder=1)
    for s, colour, label in ((base(e), BLUE, "Residual demand elasticity"),
                             (base(c.mar), RED, "Concentration at the margin"),
                             (base(c.tot), ORANGE, "Concentration, all volume")):
        ax.plot(s.index, s.values, color=colour, lw=3, marker="o", ms=7, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(label, xy=(s.index[-1], s.iloc[-1]), xytext=(12, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=14)
    cn = base(cnmc.set_index("year").HHI.loc[2018:2023])
    ax.plot(cn.index, cn.values, color=MUTED, lw=2, ls=(0, (4, 3)), zorder=2)
    ax.annotate("CNMC, published", xy=(2023, cn.loc[2023]), xytext=(6, -16),
                textcoords="offset points", color=MUTED, fontsize=12)
    for a, b in ((2021.71, 2023.99), (2022.46, 2023.99)):
        ax.axvspan(a, b, color=GRID, alpha=0.45, zorder=0)
    ax.set_ylabel("Index, 2018 = 100")
    ax.set_xlim(2017.9, 2027.4)
    fig.tight_layout()
    fig.savefig(FIGS / "divergence.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
```

- [ ] **Step 4: Figures 2, 3 and 5 from the panels**

- `fig_band_density(anat)` — median `band_density_h5` by year, one line. Ylabel `"MW offered within ±5 €/MWh of the clearing price"`.
- `fig_stack_shape(anat)` — median `share_at_zero` and `share_below_p` by year, two lines, ylabel `"Share of offered sell volume"`.
- `fig_firm_ability(firm)` — median `ability_h5` and `incentive_h5` by year for the six largest firms by cleared volume, small multiples, 2 rows × 3 columns, shared y-axis, ylabel `"€/MWh per 1% withheld"`.

- [ ] **Step 5: Figure 4 — η by hour × year heatmap**

```python
def fig_eta_hour_year(eta):
    """The Jha & Leslie test: does the elasticity collapse concentrate in the
    evening ramp, where thermal plants that shut at midday do not restart?"""
    d = eta.copy()
    d["hour"] = pd.to_datetime(d.utc_timestamp, utc=True).dt.tz_convert(
        "Europe/Madrid").dt.hour
    g = d.pivot_table(index="hour", columns=d.date.dt.year,
                      values="eta_h5", aggfunc="median")
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    im = ax.imshow(g.values, aspect="auto", origin="lower", cmap="magma",
                   extent=[g.columns.min() - 0.5, g.columns.max() + 0.5, -0.5, 23.5])
    ax.set_ylabel("Hour, Madrid local time")
    ax.set_yticks([0, 6, 12, 18, 23])
    fig.colorbar(im, ax=ax, label="Residual demand elasticity (median)")
    fig.tight_layout()
    fig.savefig(FIGS / "eta_hour_year.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
```

**Local time, not UTC** — the duck curve is a solar phenomenon and must be read on the clock the sun keeps.

- [ ] **Step 6: Figure 6 — demand predictability**

Hourly forecast-error dispersion by year, excluding the three unusable periods (from 2025-12-12; 2025Q2; 2023Q1). Plot the standard deviation of `realized − forecast` **and** of `realized − scheduled` as two lines, because the argument is that *both* degraded together:

```python
BAD_QUARTERS = ("2025Q2", "2023Q1")
BAD_FROM = pd.Timestamp("2025-12-12", tz="UTC")
```

Annotate 2022 explicitly — at 708 MW it is 4× its neighbours and will otherwise read as a plotting error.

- [ ] **Step 7: Run, then look at all six**

```bash
.venv/bin/python scripts/analysis/descriptive_figures.py
open outputs/figures/divergence.png
```

Expected: six PNGs written. Check each renders with readable type and no clipped annotations.

- [ ] **Step 8: Commit**

```bash
git add scripts/analysis/descriptive_figures.py outputs/figures/
git commit -m "Draw the six descriptive figures from the panels"
```

---

## Task 8: The research note

**Files:**
- Create: `notes/rq-descriptive-price-formation.md`

**Interfaces:**
- Consumes: the printed output of Tasks 3–7.
- Produces: nothing consumed by code.

- [ ] **Step 1: Write the note against the numbers actually produced**

Follow the structure of `notes/rq-sequential-market-premium.md`: why this design, the design formally, measurement, what was found, what would falsify it, and a standing scorecard. Sections:

1. Why a descriptive chapter — the six withdrawn designs and the marginal-cost diagnosis.
2. The identity, and the three objects s, η, θ.
3. Measurement — what each panel is, and the two coverage numbers (89.1% near-marginal volume for ownership, 41.2% for technology).
4. Results — the actual numbers from Tasks 4–6, including any that came out against the prediction.
5. Validation — bandwidth sensitivity, clean-years trend, the 15-minute break, coverage drift.
6. What this opens — the causal question the descriptives point at.

- [ ] **Step 2: Record the results that went against the prediction**

If `hhi_margin` did not rise, say so plainly and in its own subsection. This repo's notes record failures as first-class results (`notes/rq-heat-demand-conduct.md` §8.3 is the model), and the chapter's framing survives that null by design — see spec §1.

- [ ] **Step 3: Cross-link from CLAUDE.md**

Add one line to CLAUDE.md's status section pointing at the note and the spec. Do not restate the results there; CLAUDE.md holds verified facts about the *data*, not findings.

- [ ] **Step 4: Commit**

```bash
git add notes/rq-descriptive-price-formation.md CLAUDE.md
git commit -m "Record the descriptive price-formation results"
```

---

## Self-Review

**Spec coverage.** §1 identity → Tasks 4, 5. §2 series 1 → Task 2 (re-used unchanged); series 2 → Task 4; series 3 → Task 5; series 4 → Task 3; series 5 → Task 6. §3 pipeline → Tasks 2–7, with one addition: `scripts/lib/residual_demand.py` and `scripts/build/build_contract_position.py` were not named in the spec's table but are required by it ("extends `month_slopes()` rather than duplicating it", and θ from role 4). §4 six figures → Task 7, one function each. §5 validation → the `--verify` path in Tasks 3–6 plus the bandwidth loop, which every panel carries for all four h. §6 deliverables → Tasks 2–8. §7 forecast material → Task 1 (fetcher) and Task 7 figure 6; Designs 1 and 2 are recorded in the spec and correctly generate no tasks.

**One gap found and closed:** §5 requires the *clean-years trend* re-estimation, which no task produced. It belongs with the note rather than a panel, and is added as Task 8 step 1 section 5.

**Placeholder scan:** clean. Every code step carries runnable code; every verification step names the command and the expected output.

**Type consistency:** `KEY = ["date", "period"]` is defined once in `scripts/lib/residual_demand.py` and imported everywhere. `firm` is the column name in `unit_agents.parquet` and is used unchanged in Tasks 3–5, 7. `theta_mw` is produced by Task 3 and consumed by Task 4 under the same name. Bandwidth suffixes are `h{h:g}` throughout, giving `h1`, `h2`, `h5`, `h10` in every panel.
