# Leg D (the sign of n) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether the five large firms' dispatchable units respond to their markup term X with the same slope when the firm is a net buyer as when it is a net seller (supply-function Nash on the net position), not at all (price-taking), or with a markup even while buying (market power on output).

**Architecture:** Four scripts, each with a check in `scripts/qa/` that exits non-zero on failure. `build_rival_solar.py` builds the instrument, rivals' offered solar, per firm and period. `iv_two_endog.py` generalises the repo's one-regressor IV (`midday_hydro_iv.py`) to two endogenous regressors, with weak-instrument-robust Anderson–Rubin tests. `leg_d_panel.py` builds one row per unit × date × hour: the §3.14 offer-shape outcome, X from `firm_x.parquet`, the instrument, yesterday's sign and the demand forecast. `leg_d_sign_test.py` runs the spec's model on pooled, technology, firm, era and robustness samples, plus a placebo on units outside the five firms.

**Tech Stack:** Python 3.14 in `.venv`, pandas 3.0, pyarrow 25, numpy, scipy 1.18. No pytest in this repo: checks are `scripts/qa/` scripts.

**Spec:** `docs/specs/2026-09-29-thesis-framework-design.md` §4 "Leg D", with §2.4 (exposed position) and §8 step 4.

## Global Constraints

- Always run Python as `.venv/bin/python`, never bare `python3` (CLAUDE.md).
- Scripts resolve the repo root from their own location; never hardcode paths.
- `$SCRATCH` below is the session scratchpad; logs go there, not into the repo.
- Work on branch `leg-d`, cut from `main`.
- Commit messages: imperative, present tense, ≤72-character subject, ending with the `Co-Authored-By` line the session specifies.
- Never commit `data/` or `outputs/tables/*.parquet`. Small result CSVs in `outputs/tables/` are committed, as the existing ones are.
- The five firms: `EDP`, `IBERDROLA`, `ENDESA`, `NATURGY`, `REPSOL`.
- X is read from `outputs/tables/firm_x.parquet` (exposed net position, rivals' slope within ±5 €/MWh, undefined below 5 MW per €/MWh). It is never recomputed here.
- Units: storage hydro, pumped-storage turbines, combined cycle and coal — OMIE labels `hydro`, `pumped storage`, `gas CCGT`, `coal` — in the four supply roles, sell offers only. Not nuclear, wind or solar (spec).
- Outcome: the §3.14 measure, `edp_quantity_at_price.month_outcomes`, unchanged: the share of capacity offered at or below the unit-day's volume-weighted 25/50/75% offer price.
- Model (spec): y = α_ud + γ⁺·X⁺ + γ⁻·X⁻ + ε, plus hour × year-month effects and the demand forecast as in §3.14; X⁺ = max(X, 0), X⁻ = min(X, 0). Instruments: rivals' offered solar z and z × s_prev, where s_prev = 1 if the firm was a net seller in the same hour the day before. Errors clustered by ISO week (spec).
- Periods: clean (no market split, clearing identity holds); for the five firms, X defined.
- Periods are averaged to hours, so a day weighs the same before and after the 15-minute switch of 2025-10-01 (15-minute periods are 26% of all periods).
- A unit-day in which the unit offers more than 1.02 × its capacity in any period is dropped: from 2025-04, 5–8.5% of combined-cycle unit-periods carry alternative complex orders (`C04`) whose volumes do not add. No other class and no earlier month is affected (measured 2026-09-30).
- Old results are not deleted from notes. They are marked superseded, with a pointer.

## Review Focus

1. **DST days.** "The same hour yesterday" is ambiguous when either day has 23 or 25 hours; `s_prev` must be missing there, not shifted by an hour. Tested in Task 3.
2. **Month boundaries.** The first day of a month must take `s_prev` from the last day of the previous month, including in a partial `--months` build. Tested in Task 3 (2024-06-01).
3. **Non-additive offers.** Combined-cycle units from 2025-04 offer volumes above capacity; the capacity share must never exceed 1.02. Tested in Task 3.
4. **A firm that is (almost) never a seller.** Endesa is a net buyer throughout; the estimator must report "not identified" or a weak first stage, not crash or print nonsense. Tested in Task 2; flagged `WEAK` in Task 4.
5. **Night periods.** A period with no solar offer must carry z, not vanish from the instrument table and drop out of the panel. Tested in Task 1 (every priced period present) and Task 3 (z present on every five-firm row).

---

### Task 1: Rivals' offered solar, per firm

**Files:**
- Create: `scripts/build/build_rival_solar.py`
- Create: `scripts/qa/check_rival_solar.py`

**Interfaces:**
- Consumes: `data/omie/registry/unit_agents.parquet`, `data/omie/bids/parquet/bids_*.parquet`, `lib/omie_owner.owner_group`, and `outputs/tables/solar_instrument.parquet` (check only).
- Produces: `outputs/tables/rival_solar.parquet`, one row per priced period in the bid months, columns `date, period, z_all, own_<FIRM>, z_rival_<FIRM>` for each of the five firms, all in MW. `z_rival_<FIRM> = z_all − own_<FIRM>`. Builder flag `--months YYYYMM ...` for partial runs.

- [ ] **Step 1: Create the branch and write the failing check**

```bash
git checkout -b leg-d
```

Create `scripts/qa/check_rival_solar.py`:

```python
#!/usr/bin/env python3
"""Rivals' offered solar: one row per period, the identity, and EDP's z_offered reproduced.

    .venv/bin/python scripts/qa/check_rival_solar.py

Framework spec §4, leg D. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs/tables/rival_solar.parquet"
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
KEY = ["date", "period"]


def main() -> int:
    if not OUT.exists():
        print(f"  FAIL {OUT.relative_to(ROOT)} missing -- run scripts/build/build_rival_solar.py")
        return 1
    fails: list[str] = []
    d = pd.read_parquet(OUT)
    d["date"] = pd.to_datetime(d.date)
    if d.duplicated(KEY).any():
        fails.append("duplicate (date, period) rows")
    num = [c for c in d.columns if c not in KEY]
    if d[num].isna().any().any():
        fails.append("missing values: a period with no solar offer must carry 0")
    for f in FIRMS:
        if (d[f"own_{f}"] < 0).any():
            fails.append(f"own_{f} negative")
        if ((d.z_all - d[f"own_{f}"] - d[f"z_rival_{f}"]).abs() > 1e-6).any():
            fails.append(f"z_rival_{f} != z_all - own_{f}")
    px = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet", columns=KEY)
    px["date"] = pd.to_datetime(px.date)
    px = px[px.date.dt.strftime("%Y%m").isin(set(d.date.dt.strftime("%Y%m")))]
    missing = len(px.merge(d[KEY], on=KEY, how="left", indicator=True).query("_merge == 'left_only'"))
    print(f"priced periods in the covered months: {len(px):,}; missing here: {missing}")
    if missing:
        fails.append(f"{missing} priced periods missing (night periods must carry z, not be dropped)")
    s = pd.read_parquet(SOLAR, columns=KEY + ["z_offered"])
    s["date"] = pd.to_datetime(s.date)
    m = d.merge(s, on=KEY).dropna(subset=["z_offered"])
    corr = m.z_rival_EDP.corr(m.z_offered)
    med = (m.z_rival_EDP - m.z_offered).abs().median()
    print(f"EDP's rival solar vs z_offered: {len(m):,} periods, corr {corr:.6f}, median |diff| {med:.3f} MW")
    if not (corr > 0.999 and med < 1.0):
        fails.append("z_rival_EDP does not reproduce z_offered")
    print("mean own offered solar, MW:", {f: round(d[f"own_{f}"].mean()) for f in FIRMS},
          f"of z_all {d.z_all.mean():.0f}")
    for f_ in fails:
        print(f"  FAIL {f_}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the check to verify it fails**

Run: `.venv/bin/python scripts/qa/check_rival_solar.py`
Expected: exit 1, `FAIL outputs/tables/rival_solar.parquet missing -- run scripts/build/build_rival_solar.py`

- [ ] **Step 3: Write the builder**

Create `scripts/build/build_rival_solar.py`:

```python
#!/usr/bin/env python3
"""Rivals' offered solar, per firm and period: the leg D instrument.

    .venv/bin/python scripts/build/build_rival_solar.py [--months 202406 ...]

Writes outputs/tables/rival_solar.parquet, one row per day-ahead period that has
a price and a bid file:

    z_all            MW of solar offered day-ahead by every solar-labelled supply unit
    own_<FIRM>       the part offered by units whose owner group is FIRM
    z_rival_<FIRM>   z_all - own_<FIRM>, the instrument for FIRM (framework spec §4, leg D)

Built exactly as `build_solar_instrument.py` builds `z_offered` (sell offers,
status O, solar-labelled units outside the purchase roles), once for each of the
five firms instead of for EDP alone. A firm's own solar is every unit whose
owner rolls up to it under `owner_group` -- pass-through entities included, so
no volume the firm's group bids enters its own instrument. For EDP this
reproduces `z_offered`; `scripts/qa/check_rival_solar.py` checks it. Periods
with no solar offer (night) carry 0, not a gap.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import owner_group  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
OUT = ROOT / "outputs/tables/rival_solar.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
KEY = ["date", "period"]


def solar_units() -> pd.Series:
    """unit -> owner group, for the solar-labelled supply units z_offered uses."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "role", "tech", "tech_omie", "tech_omie_early", "agent_owner"])
    label = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech)
    s = u[(label == "solar") & ~u.role.str.startswith("purchase")]
    return pd.Series(s.agent_owner.map(owner_group).to_numpy(), index=s.unit.astype(str).to_numpy())


def month(f: Path, grp: pd.Series) -> pd.DataFrame:
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", list(grp.index)), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    b["grp"] = b.unit.astype(str).map(grp)
    k = [b.date, b.period]
    parts = [b.power_mw.groupby(k).sum().rename("z_all")]
    for firm in FIRMS:
        parts.append(b.power_mw.where(b.grp == firm, 0.0).groupby(k).sum().rename(f"own_{firm}"))
    return pd.concat(parts, axis=1).reset_index()


def build(months: list[str] | None) -> pd.DataFrame:
    grp = solar_units()
    print(f"{len(grp)} solar-labelled supply units; the five firms own "
          + ", ".join(f"{f} {(grp == f).sum()}" for f in FIRMS))
    files = sorted(BIDS.glob("bids_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    parts = []
    for f in files:
        parts.append(month(f, grp))
        print(f"  {f.stem}", file=sys.stderr, flush=True)
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=KEY)
    px["date"] = pd.to_datetime(px.date)
    ym = {f.stem.split("_")[1] for f in files}
    px = px[px.date.dt.strftime("%Y%m").isin(ym)]
    d = px.merge(d, on=KEY, how="left")
    num = [c for c in d.columns if c not in KEY]
    d[num] = d[num].fillna(0.0)
    for firm in FIRMS:
        d[f"z_rival_{firm}"] = d.z_all - d[f"own_{firm}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} periods)")
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run a partial build and the check**

Run: `.venv/bin/python scripts/build/build_rival_solar.py --months 202406 202504 202512 2>/dev/null && .venv/bin/python scripts/qa/check_rival_solar.py`
Expected: `1532 solar-labelled supply units; the five firms own EDP 6, IBERDROLA 14, ENDESA 14, NATURGY 5, REPSOL 12`, `wrote outputs/tables/rival_solar.parquet  (4,416 periods)`, then `priced periods in the covered months: 4,416; missing here: 0`, `EDP's rival solar vs z_offered: 4,416 periods, corr 1.000000, median |diff| 0.000 MW`, `OK`.

- [ ] **Step 5: Full build and check**

Run: `.venv/bin/python scripts/build/build_rival_solar.py > $SCRATCH/rival_solar.log 2>&1; tail -2 $SCRATCH/rival_solar.log; .venv/bin/python scripts/qa/check_rival_solar.py`
Expected: `wrote outputs/tables/rival_solar.parquet  (91,247 periods)` (every priced period 2018-01 → 2026-05); check prints `corr 1.000000` (at least 0.999) and `OK`. About 5 minutes.

- [ ] **Step 6: Commit**

```bash
git add scripts/build/build_rival_solar.py scripts/qa/check_rival_solar.py
git commit -m "Build rivals' offered solar per firm for leg D"
```

---

### Task 2: IV with two endogenous regressors

**Files:**
- Create: `scripts/analysis/iv_two_endog.py`
- Create: `scripts/qa/check_iv_two_endog.py`

**Interfaces:**
- Consumes: `midday_hydro_iv.cluster_meat(M, e, cl)`; for the check, `midday_hydro_iv.tsls(y, x, z, w, cl) -> (b, se)` and `midday_hydro_iv.ols(y, M, cl) -> (b, se)`.
- Produces (all arrays numpy, already demeaned of fixed effects):
  - `tsls_k(y, X, Z, W, cl) -> (b: ndarray[k], V: ndarray[k, k])`, NaN when not identified;
  - `sw_f(X, Z, W, cl, j: int) -> float`, the Sanderson–Windmeijer conditional F, NaN when not identified;
  - `ar_test(y, X, Z, W, cl, g) -> (stat: float, p: float)`;
  - `ar_common_set(y, X, Z, W, cl, grid: ndarray) -> ndarray` of accepted grid values (empty if none);
  - `fmt_set(keep, grid) -> str`.

- [ ] **Step 1: Write the failing check**

Create `scripts/qa/check_iv_two_endog.py`:

```python
#!/usr/bin/env python3
"""The two-endogenous-regressor IV estimator recovers known coefficients on simulated data.

    .venv/bin/python scripts/qa/check_iv_two_endog.py

Framework spec §4, leg D. The data mimic the design: a firm is a seller (s = 1)
or a buyer, X's sign follows s, rivals' solar z moves X with a sign that
depends on s, and an unobserved shock v enters both X and y (so OLS is biased).
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from iv_two_endog import ar_common_set, ar_test, fmt_set, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import ols, tsls  # noqa: E402

GRID = np.round(np.arange(-3.0, 3.0001, 0.005), 4)


def dgp(gp, gm, seed, n=20000, groups=400, share_seller=0.5):
    r = np.random.default_rng(seed)
    cl = r.integers(0, groups, n)
    s = (r.random(n) < share_seller).astype(float)
    z, w, v = r.normal(size=n), r.normal(size=n), r.normal(size=n)
    x = np.where(s == 1, 2.0, -2.0) + z * np.where(s == 1, 1.0, -0.8) + 0.3 * w + v
    xp, xm = np.maximum(x, 0), np.minimum(x, 0)
    y = gp * xp + gm * xm + 0.2 * w + 0.7 * v + r.normal(size=n)
    return y, np.column_stack([xp, xm]), np.column_stack([z, z * s]), w[:, None], cl


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    for name, truth in (("asymmetric", (-0.5, 0.5)), ("symmetric", (-0.5, -0.5))):
        y, X, Z, W, cl = dgp(*truth, seed=11)
        b, V = tsls_k(y, X, Z, W, cl)
        se = np.sqrt(np.diag(V))
        dev = np.abs(b - truth) / se
        print(f"{name}: b {b.round(3)} se {se.round(3)}")
        check(bool((dev < 3).all()), f"{name}: 2SLS within 3 se of {truth}")
        check(min(sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)) > 100, f"{name}: strong first stages")
        check(ar_test(y, X, Z, W, cl, truth)[1] > 0.05, f"{name}: AR does not reject the truth")
        check(ar_test(y, X, Z, W, cl, [0.0, 0.0])[1] < 1e-6, f"{name}: AR rejects (0, 0)")
        keep = ar_common_set(y, X, Z, W, cl, GRID)
        print(f"  common-slope set {fmt_set(keep, GRID)}")
        if name == "asymmetric":
            check(len(keep) == 0, "asymmetric: no common slope fits")
        else:
            check(len(keep) > 0 and keep.min() <= -0.5 <= keep.max(), "symmetric: set covers -0.5")

    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=3)
    x1 = X.sum(axis=1)
    b1, V1 = tsls_k(y, x1[:, None], Z[:, :1], W, cl)
    b0, se0 = tsls(y, x1, Z[:, 0], W, cl)
    check(abs(b1[0] - b0) < 1e-10 and abs(np.sqrt(V1[0, 0]) - se0) < 1e-10,
          "one regressor: tsls_k equals midday_hydro_iv.tsls")
    bf, sef = ols(x1, np.column_stack([Z[:, 0], W]), cl)
    check(abs(sw_f(x1[:, None], Z[:, :1], W, cl, 0) - (bf[0] / sef[0]) ** 2) < 1e-8,
          "one regressor: sw_f equals the first-stage F")

    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=5, share_seller=0.0)
    b, _ = tsls_k(y, X, Z, W, cl)
    check(bool(np.isnan(b).all()), "never a seller: tsls_k returns NaN, not an error")
    check(bool(np.isnan(sw_f(X, Z, W, cl, 0))), "never a seller: sw_f returns NaN")
    check(bool(np.isnan(ar_test(y, X, Z, W, cl, [0.0, 0.0])[1])), "never a seller: ar_test NaN")
    check(ar_common_set(y, X, Z, W, cl, GRID).size == 0, "never a seller: empty common set")

    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=5, share_seller=0.02)
    fp, fm = sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)
    print(f"rarely a seller: SW F {fp:.1f} / {fm:.1f}")
    check(fp < fm, "rarely a seller: X+ has the weaker first stage")

    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python scripts/qa/check_iv_two_endog.py`
Expected: `ModuleNotFoundError: No module named 'iv_two_endog'`

- [ ] **Step 3: Write the estimator**

Create `scripts/analysis/iv_two_endog.py`:

```python
#!/usr/bin/env python3
"""2SLS with several endogenous regressors, and weak-instrument-robust tests.

Leg D of the framework spec (§4) instruments Xp = max(X, 0) and Xm = min(X, 0)
with rivals' offered solar z and z * s_prev. `midday_hydro_iv.py` handles one
endogenous regressor; this generalises it. Inputs are already demeaned of the
fixed effects (`solar_first_stage.demean`); W holds the remaining controls.

    tsls_k(y, X, Z, W, cl)               coefficients on X and their cluster covariance
    sw_f(X, Z, W, cl, j)                 Sanderson-Windmeijer conditional F for X[:, j]
    ar_test(y, X, Z, W, cl, g)           Anderson-Rubin Wald and p for H0: coefficients = g
    ar_common_set(y, X, Z, W, cl, grid)  grid values c with H0 "every coefficient = c" kept
    fmt_set(keep, grid)                  an accepted set as text

Cluster-robust throughout (`midday_hydro_iv.cluster_meat`), no small-sample
correction. When the instruments cannot separate the regressors -- a zero
column, or a firm that is never a seller -- the functions return NaN (or an
empty set) instead of raising. `scripts/qa/check_iv_two_endog.py` tests them on
simulated data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from midday_hydro_iv import cluster_meat  # noqa: E402

RANK_TOL = 1e-8



def _full_rank(M):
    """Columns of M linearly independent, judged on the scale-free Gram matrix."""
    G = M.T @ M
    d = np.sqrt(np.diag(G))
    if (d == 0).any():
        return False
    return np.linalg.eigvalsh(G / np.outer(d, d)).min() > RANK_TOL


def _ols_cov(y, M, cl):
    inv = np.linalg.inv(M.T @ M)
    b = inv @ M.T @ y
    return b, inv @ cluster_meat(M, y - M @ b, cl) @ inv


def _separable(Xhat_k, W):
    """The instrumented regressors vary independently once W is partialled out."""
    R = Xhat_k - W @ np.linalg.lstsq(W, Xhat_k, rcond=None)[0]
    sd = R.std(axis=0)
    if (sd <= RANK_TOL * (1 + np.abs(Xhat_k).std(axis=0))).any():
        return False
    if R.shape[1] == 1:
        return True
    return np.linalg.eigvalsh(np.corrcoef(R, rowvar=False)).min() > RANK_TOL


def tsls_k(y, X, Z, W, cl):
    """2SLS of y on X (n x k, endogenous) and W (exogenous), instruments Z (n x L, L >= k).

    Returns (b, V): the k coefficients on X and their cluster covariance, or NaN
    arrays when the instruments cannot separate the regressors.
    """
    k = X.shape[1]
    Zf, Xf = np.column_stack([Z, W]), np.column_stack([X, W])
    if not _full_rank(Zf):
        return np.full(k, np.nan), np.full((k, k), np.nan)
    Xhat = Zf @ np.linalg.lstsq(Zf, Xf, rcond=None)[0]
    if not _separable(Xhat[:, :k], np.atleast_2d(W.T).T):
        return np.full(k, np.nan), np.full((k, k), np.nan)
    inv = np.linalg.inv(Xhat.T @ Xf)
    b = inv @ Xhat.T @ y
    V = inv @ cluster_meat(Xhat, y - Xf @ b, cl) @ inv.T
    return b[:k], V[:k, :k]


def sw_f(X, Z, W, cl, j):
    """Sanderson-Windmeijer (2016) conditional first-stage F for X[:, j].

    X[:, j] is regressed by 2SLS on the other endogenous regressors; the residual
    is regressed on Z and W, and the cluster Wald statistic on Z is divided by
    L - k + 1. With k = 1 it is the ordinary first-stage F.
    """
    k, L = X.shape[1], Z.shape[1]
    if not _full_rank(np.column_stack([Z, W])):
        return float("nan")
    u = X[:, j]
    if k > 1:
        d, _ = tsls_k(u, np.delete(X, j, axis=1), Z, W, cl)
        if np.isnan(d).any():
            return float("nan")
        u = u - np.delete(X, j, axis=1) @ d
    b, V = _ols_cov(u, np.column_stack([Z, W]), cl)
    bz, Vz = b[:L], V[:L, :L]
    return float(bz @ np.linalg.solve(Vz, bz)) / (L - k + 1)


def ar_test(y, X, Z, W, cl, g):
    """Anderson-Rubin: (Wald statistic, p-value) for H0 that the coefficients on X equal g."""
    L = Z.shape[1]
    if not _full_rank(np.column_stack([Z, W])):
        return float("nan"), float("nan")
    b, V = _ols_cov(y - X @ np.asarray(g, float), np.column_stack([Z, W]), cl)
    bz, Vz = b[:L], V[:L, :L]
    stat = float(bz @ np.linalg.solve(Vz, bz))
    return stat, float(stats.chi2.sf(stat, L))


def ar_common_set(y, X, Z, W, cl, grid):
    """Grid values c for which H0 "every coefficient on X equals c" is not rejected at 5%.

    Under that H0 the model is y = c * X.sum(1) + W w + e, so the AR statistic is
    a ratio of quadratics in c, built from moments once. An EMPTY set rejects a
    common slope at every value: the weak-instrument-robust test of symmetry.
    """
    L = Z.shape[1]
    M = np.column_stack([Z, W])
    if not _full_rank(M):
        return np.array([])
    A = np.linalg.inv(M.T @ M)
    xs = X.sum(axis=1)
    cy, cx = A @ M.T @ y, A @ M.T @ xs
    ey, ex = y - M @ cy, xs - M @ cx
    order = np.argsort(cl, kind="stable")
    cl_s, M_s, ey_s, ex_s = cl[order], M[order], ey[order], ex[order]
    bounds = np.flatnonzero(np.r_[True, cl_s[1:] != cl_s[:-1], True])
    p = M.shape[1]
    myy, mxx, myx = np.zeros((p, p)), np.zeros((p, p)), np.zeros((p, p))
    for a, z in zip(bounds[:-1], bounds[1:]):
        gy, gx = M_s[a:z].T @ ey_s[a:z], M_s[a:z].T @ ex_s[a:z]
        myy += np.outer(gy, gy); mxx += np.outer(gx, gx); myx += np.outer(gy, gx)
    Vyy, Vxx, Vyx = ((A @ m @ A)[:L, :L] for m in (myy, mxx, myx))
    crit = stats.chi2.ppf(0.95, L)
    keep = []
    for c in grid:
        bz = cy[:L] - c * cx[:L]
        V = Vyy - c * (Vyx + Vyx.T) + c * c * Vxx
        if bz @ np.linalg.solve(V, bz) <= crit:
            keep.append(c)
    return np.array(keep)


def fmt_set(keep, grid):
    """Accepted grid points as intervals; an interval touching the grid's edge is open."""
    if len(keep) == 0:
        return "empty"
    step = grid[1] - grid[0]
    gaps = np.flatnonzero(np.diff(keep) > 1.5 * step)
    pieces = np.split(keep, gaps + 1)
    lo, hi = grid[0], grid[-1]
    return " U ".join(f"[{'-inf' if p[0] <= lo else f'{p[0]:.3f}'}, "
                      f"{'+inf' if p[-1] >= hi else f'{p[-1]:.3f}'}]" for p in pieces)
```

- [ ] **Step 4: Run the check to verify it passes**

Run: `.venv/bin/python scripts/qa/check_iv_two_endog.py`
Expected: 17 lines beginning `ok`, including `asymmetric: b [-0.517  0.523]`, `common-slope set empty` (asymmetric) and `common-slope set [-0.515, -0.485]` (symmetric), `rarely a seller: SW F 59.9 / 1443.3`, then `OK`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/iv_two_endog.py scripts/qa/check_iv_two_endog.py
git commit -m "Add 2SLS with two endogenous regressors and AR tests"
```

---

### Task 3: The leg D panel

**Files:**
- Create: `scripts/analysis/leg_d_panel.py`
- Create: `scripts/qa/check_leg_d_panel.py`

**Interfaces:**
- Consumes: `edp_quantity_at_price.month_outcomes(f, units, cap) -> DataFrame[unit, date, period, s25, d25, s50, d50, s75, d75]` (called with `cap` = 1 for every unit, so it returns MW); `omie_owner.exposed_group`; `outputs/tables/firm_x.parquet`; `outputs/tables/rival_solar.parquet` (Task 1); `outputs/tables/solar_instrument.parquet` (period timestamps); `data/omie/cab/parquet/cab_*.parquet`; `data/ree/ree_demand_forecast_5min.parquet`.
- Produces: `outputs/tables/leg_d_panel.parquet`, one row per `unit, date, hour` with columns `unit, firm, date, hour, s25, s50, s75, d25, d50, d75` (shares of capacity), `X, Xp, Xm` (€/MWh), `z` (GW), `fcst` (GW), `cap_mw, zero_price, n_per, cls, s_prev, zs, wk`. `firm` is one of the five or `FRINGE`; `cls` is `hydro`, `pumped`, `ccgt` or `coal`; `wk` = ISO year × 100 + ISO week. Builder flag `--months`.

- [ ] **Step 1: Write the failing check**

Create `scripts/qa/check_leg_d_panel.py`:

```python
#!/usr/bin/env python3
"""Leg D panel: keys, hours, the sign-yesterday rule, X, the instrument and the outcome range.

    .venv/bin/python scripts/qa/check_leg_d_panel.py

Checks outputs/tables/leg_d_panel.parquet against its inputs (framework spec §4,
leg D). Exits non-zero on any failure.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "outputs/tables/leg_d_panel.parquet"
FIRM_X = ROOT / "outputs/tables/firm_x.parquet"
RIVAL = ROOT / "outputs/tables/rival_solar.parquet"
PRICES = ROOT / "data/omie/prices/omie_day_ahead_prices.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
OVER_CAP = 1.02
HOURLY_DAY, QUARTER_DAY = pd.Timestamp("2024-06-12"), pd.Timestamp("2025-12-10")


def firm_hour(x: pd.DataFrame, firm: str, day: pd.Timestamp, col: str) -> pd.Series:
    """Hourly mean of a firm_x column over the clean periods with X defined."""
    g = x[(x.firm == firm) & (x.date == day) & x.clean & x.X.notna()].copy()
    g["hour"] = (g.period - 1) // (60 // g.resolution_min)
    return g.groupby("hour")[col].mean()


def main() -> int:
    if not PANEL.exists():
        print(f"  FAIL {PANEL.relative_to(ROOT)} missing -- run scripts/analysis/leg_d_panel.py")
        return 1
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    h = pd.read_parquet(PANEL)
    five = h[h.firm != "FRINGE"]
    print(f"{len(h):,} unit-hours, {h.unit.nunique()} units, {h.date.min().date()} .. {h.date.max().date()}")
    check(not h.duplicated(["unit", "date", "hour"]).any(), "one row per unit x date x hour")
    check(set(h.firm) <= set(FIRMS) | {"FRINGE"}, "firm is one of the five or FRINGE")
    check(h.loc[h.firm == "FRINGE", "X"].isna().all(), "FRINGE rows carry no X")
    check(five.X.notna().all(), "every five-firm row has X")
    check(bool((five.Xp + five.Xm - five.X).abs().max() < 1e-4), "Xp + Xm = X")
    check(bool(h.hour.between(0, 24).all() and h.n_per.between(1, 4).all()), "hours 0..24, 1..4 periods each")
    check(bool(h.s75.max() <= OVER_CAP + 1e-6 and h.s25.min() >= 0), "capacity shares within [0, 1.02]")
    check(bool(h.cap_mw.notna().all() and (h.cap_mw > 0).all()), "capacity known and positive")
    check(five.z.notna().all() and five.fcst.notna().mean() > 0.99, "instrument everywhere, forecast on >99%")
    ok = five.s_prev.notna()
    check(bool(np.allclose(five.zs[ok], five.z[ok] * five.s_prev[ok], atol=1e-5)), "zs = z * s_prev")

    px = pd.read_parquet(PRICES, columns=["date", "period", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    hours = px.groupby("date").apply(lambda g: len(g) * g.resolution_min.iloc[0] / 60, include_groups=False)
    odd = set(hours[hours != 24].index)
    odd |= {d + pd.Timedelta(days=1) for d in odd}
    check(five[five.date.isin(odd)].s_prev.isna().all(), "s_prev undefined on DST days and the days after")
    first = five[five.date == pd.Timestamp("2024-06-01")]
    check(len(first) > 0 and first.s_prev.notna().mean() > 0.99, "2024-06-01: s_prev reaches back into May")

    x = pd.read_parquet(FIRM_X, columns=["date", "period", "resolution_min", "firm", "clean", "X", "net_mw"])
    x["date"] = pd.to_datetime(x.date)
    for firm, day in (("EDP", HOURLY_DAY), ("IBERDROLA", QUARTER_DAY)):
        p = five[(five.firm == firm) & (five.date == day)].drop_duplicates("hour").set_index("hour")
        check(len(p) > 0 and float((p.X - firm_hour(x, firm, day, "X").reindex(p.index)).abs().max()) < 1e-4,
              f"{firm} {day.date()}: X is the hourly mean of firm_x")
        prev = x[(x.firm == firm) & (x.date == day - pd.Timedelta(days=1))].copy()
        prev["hour"] = (prev.period - 1) // (60 // prev.resolution_min)
        want = (prev.groupby("hour").net_mw.mean() > 0).astype(float).reindex(p.index)
        check(bool((p.s_prev == want).all()), f"{firm} {day.date()}: s_prev is yesterday's sign, same hour")

    r = pd.read_parquet(RIVAL)
    r["date"] = pd.to_datetime(r.date)
    r = r[r.date == HOURLY_DAY].set_index("period").z_rival_EDP / 1000
    p = five[(five.firm == "EDP") & (five.date == HOURLY_DAY)].drop_duplicates("hour").set_index("hour")
    check(float((p.z - r.reindex(p.index + 1).to_numpy()).abs().max()) < 1e-4,
          f"EDP {HOURLY_DAY.date()}: z is rivals' offered solar in GW")

    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python scripts/qa/check_leg_d_panel.py`
Expected: exit 1, `FAIL outputs/tables/leg_d_panel.parquet missing -- run scripts/analysis/leg_d_panel.py`

- [ ] **Step 3: Write the builder**

Create `scripts/analysis/leg_d_panel.py`:

```python
#!/usr/bin/env python3
"""Leg D panel: dispatchable units' offer shape by hour, with the firm's X and instruments.

    .venv/bin/python scripts/analysis/firm_x.py                  # input: X, net position, clean
    .venv/bin/python scripts/build/build_rival_solar.py          # input: the instrument
    .venv/bin/python scripts/build/build_solar_instrument.py     # input: period timestamps
    .venv/bin/python scripts/analysis/leg_d_panel.py [--months 202406 ...]

Writes outputs/tables/leg_d_panel.parquet, one row per unit x date x hour.
Framework spec §4, leg D.

UNITS. Storage hydro, pumped-storage turbines, combined cycle and coal
(`hydro`, `pumped storage`, `gas CCGT`, `coal` under OMIE's technology label),
supply roles, sell offers only. `firm` is the unit's exposed group
(`omie_owner.exposed_group`) when it is one of the five; any other owner is
`FRINGE`, kept only at FRINGE_MIN_MW or more, for the placebo.

OUTCOME. The §3.14 measure from `edp_quantity_at_price.month_outcomes`: MW
offered at or below the unit-DAY's volume-weighted 25/50/75% offer price, and
the offer density within +/-5 EUR/MWh of it, divided here by the unit-day's
capacity (`cab` max power that day; the registry's when `cab` has none).

FIRM TERMS. X, the exposed net position and `clean` from `firm_x.parquet`.
Periods kept: clean (no market split, clearing identity holds) and, for the
five firms, X defined (rivals' slope >= 5 MW per EUR/MWh).

HOURS. Periods are averaged to hours, so a day weighs the same before and after
the 15-minute switch of 2025-10-01. Xp and Xm are hourly means of max(X, 0) and
min(X, 0), so Xp + Xm = X.

SIGN YESTERDAY. s_prev = 1 if the firm's mean exposed net position in the same
hour of the previous day was positive, else 0. It is known when the offer is
made. NaN when either day is not 24 hours long (the DST days and the days after
them), so hour numbers always refer to the same clock hour.

INSTRUMENTS. z = rivals' offered solar for the firm, `z_rival_<FIRM>`, in GW
(`z_all` for FRINGE); zs = z * s_prev. CONTROL: fcst, REE's day-ahead demand
forecast in GW.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from edp_quantity_at_price import month_outcomes  # noqa: E402
from omie_owner import exposed_group  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
FIRM_X = ROOT / "outputs/tables/firm_x.parquet"
RIVAL = ROOT / "outputs/tables/rival_solar.parquet"
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
OUT = ROOT / "outputs/tables/leg_d_panel.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
CLASSES = {"hydro": "hydro", "pumped storage": "pumped", "gas CCGT": "ccgt", "coal": "coal"}
SUPPLY_ROLES = ["generation", "generation_large", "storage_mixed", "pumping"]
FRINGE_MIN_MW = 50.0
OVER_CAP = 1.02
KEY = ["date", "period"]
OUTC = ["s25", "s50", "s75", "d25", "d50", "d75"]


def span(months: list[str]) -> list[str]:
    """The months plus each one's previous month, so s_prev reaches back across month ends."""
    prev = {str(pd.Period(m, "M") - 1).replace("-", "") for m in months}
    return sorted(set(months) | prev)


def leg_d_units() -> pd.DataFrame:
    """unit, firm (one of the five or FRINGE), cls, reg_mw: leg D's population."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "role", "tech", "tech_omie", "tech_omie_early",
                                 "agent_owner", "max_power_mw"])
    label = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech)
    u = u[label.isin(CLASSES) & u.role.isin(SUPPLY_ROLES)].copy()
    u["cls"] = label[u.index].map(CLASSES)
    g = u.agent_owner.map(exposed_group)
    u["firm"] = g.where(g.isin(FIRMS), "FRINGE")
    u = u[(u.firm != "FRINGE") | (u.max_power_mw >= FRINGE_MIN_MW)]
    return u.rename(columns={"max_power_mw": "reg_mw"})[["unit", "firm", "cls", "reg_mw"]]


def offered_total(f: Path, units: list[str]) -> pd.DataFrame:
    """unit, date, period, off_mw: all sell MW a unit offers in the period."""
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", units), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    b["unit"] = b.unit.astype(str)
    t = b.groupby(["unit", "date", "period"]).power_mw.sum().rename("off_mw").reset_index()
    t["date"] = pd.to_datetime(t.date)
    return t


def unit_day_capacity(units: list[str], months: list[str]) -> pd.DataFrame:
    parts = []
    for ym in months:
        f = DATA / f"omie/cab/parquet/cab_{ym}.parquet"
        if f.exists():
            c = pq.read_table(f, columns=["date", "unit", "max_power_mw"],
                              filters=[("unit", "in", units)]).to_pandas()
            parts.append(c.groupby(["unit", "date"]).max_power_mw.max().reset_index())
    c = pd.concat(parts, ignore_index=True)
    c["date"] = pd.to_datetime(c.date)
    return c.rename(columns={"max_power_mw": "cap_mw"})


def period_frame(months: list[str]) -> pd.DataFrame:
    """date, period, hour, day_hours, fcst (GW) for every priced period in the months."""
    s = pd.read_parquet(SOLAR, columns=["date", "period", "resolution_min", "utc_timestamp"])
    s["date"] = pd.to_datetime(s.date)
    s = s[s.date.dt.strftime("%Y%m").isin(months)].copy()
    s["hour"] = (s.period - 1) // (60 // s.resolution_min)
    s["day_hours"] = s.groupby("date").period.transform("size") * s.resolution_min / 60
    fc = pd.read_parquet(DATA / "ree/ree_demand_forecast_5min.parquet",
                         columns=["utc_timestamp", "demand_forecast_mw"])
    fc = fc.set_index(pd.to_datetime(fc.utc_timestamp, utc=True)).demand_forecast_mw
    start = pd.to_datetime(s.utc_timestamp, utc=True)
    s["fcst"] = np.nan
    for res, g in s.groupby("resolution_min"):
        m = fc.resample(f"{res}min").mean()
        s.loc[g.index, "fcst"] = m.reindex(pd.DatetimeIndex(start[g.index])).to_numpy() / 1000
    return s[KEY + ["hour", "day_hours", "fcst"]]


def firm_terms(months: list[str]) -> pd.DataFrame:
    x = pd.read_parquet(FIRM_X, columns=KEY + ["firm", "clean", "X", "net_mw", "zero_price"])
    x["date"] = pd.to_datetime(x.date)
    x = x[x.date.dt.strftime("%Y%m").isin(months)].copy()
    x["Xp"], x["Xm"] = x.X.clip(lower=0), x.X.clip(upper=0)
    return x


def seller_yesterday(x: pd.DataFrame, per: pd.DataFrame) -> pd.DataFrame:
    """firm, date, hour -> s_prev: 1 if the firm was a net seller in that hour the day before."""
    h = x.merge(per[KEY + ["hour", "day_hours"]], on=KEY)
    h = h.groupby(["firm", "date", "hour"]).agg(net=("net_mw", "mean"),
                                                day_hours=("day_hours", "first")).reset_index()
    prev = h.assign(date=h.date + pd.Timedelta(days=1))
    m = h[["firm", "date", "hour", "day_hours"]].merge(
        prev[["firm", "date", "hour", "net", "day_hours"]], on=["firm", "date", "hour"],
        how="left", suffixes=("", "_prev"))
    ok = (m.day_hours == 24) & (m.day_hours_prev == 24)
    m["s_prev"] = np.where(ok & m.net.notna(), (m.net > 0).astype(float), np.nan)
    return m[["firm", "date", "hour", "s_prev"]]


def instrument(months: list[str]) -> pd.DataFrame:
    r = pd.read_parquet(RIVAL)
    r["date"] = pd.to_datetime(r.date)
    r = r[r.date.dt.strftime("%Y%m").isin(months)]
    long = [r[KEY].assign(firm=f, z=r[f"z_rival_{f}"] / 1000) for f in FIRMS]
    long.append(r[KEY].assign(firm="FRINGE", z=r.z_all / 1000))
    return pd.concat(long, ignore_index=True)


def hourly(o: pd.DataFrame, off: pd.DataFrame, u: pd.DataFrame, cap: pd.DataFrame,
           per: pd.DataFrame, x: pd.DataFrame, clean: pd.DataFrame,
           z: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One month of unit-period outcomes -> unit-hours with X, the instrument and controls.

    Also returns the unit-days dropped because the unit offered more than
    OVER_CAP x its capacity in some period: from 2025-04 some combined cycles
    submit alternative complex orders (`C04`) whose volumes do not add, so the
    capacity share is undefined that day.
    """
    o["date"] = pd.to_datetime(o.date)
    o = o.merge(u, on="unit").merge(cap, on=["unit", "date"], how="left")
    o["cap_mw"] = o.cap_mw.where(o.cap_mw > 0, o.reg_mw)
    o = o.merge(off, on=["unit", "date", "period"], how="left")
    bad = (o.off_mw > OVER_CAP * o.cap_mw).groupby([o.unit, o.date]).transform("any")
    dropped = o[bad].drop_duplicates(["unit", "date"])[["unit", "cls", "date"]]
    o = o[~bad].copy()
    o[OUTC] = o[OUTC].div(o.cap_mw, axis=0)
    o = o.merge(per, on=KEY).merge(clean, on=KEY)
    o = o[o.clean]
    o = o.merge(x[KEY + ["firm", "X", "Xp", "Xm"]], on=KEY + ["firm"], how="left")
    o = o[(o.firm == "FRINGE") | o.X.notna()]
    o = o.merge(z, on=KEY + ["firm"], how="left")
    agg = {c: "mean" for c in OUTC + ["X", "Xp", "Xm", "z", "fcst"]}
    agg.update(cap_mw="first", zero_price="max", period="size", cls="first")
    h = o.groupby(["unit", "firm", "date", "hour"]).agg(agg)
    return h.rename(columns={"period": "n_per"}).reset_index(), dropped


def build(months: list[str] | None) -> pd.DataFrame:
    files = sorted(BIDS.glob("bids_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    months = [f.stem.split("_")[1] for f in files]
    u = leg_d_units()
    units = sorted(u.unit)
    print(f"{len(units)} units:\n{u.groupby(['firm', 'cls']).size().unstack(fill_value=0)}")
    one = pd.Series(1.0, index=units)
    per, x, z = period_frame(span(months)), firm_terms(span(months)), instrument(months)
    clean = x[x.firm == FIRMS[0]][KEY + ["clean", "zero_price"]]
    parts, drops = [], []
    for f, ym in zip(files, months):
        o = month_outcomes(f, units, one)
        if not o.empty:
            h_m, d_m = hourly(o, offered_total(f, units), u, unit_day_capacity(units, [ym]),
                              per, x, clean, z)
            parts.append(h_m)
            drops.append(d_m)
        print(f"  {f.stem}", file=sys.stderr, flush=True)
    h = pd.concat(parts, ignore_index=True)
    dropped = pd.concat(drops, ignore_index=True)
    h = h.merge(seller_yesterday(x, per), on=["firm", "date", "hour"], how="left")
    h.loc[h.firm == "FRINGE", "s_prev"] = np.nan
    h["zs"] = h.z * h.s_prev
    iso = h.date.dt.isocalendar()
    h["wk"] = (iso.year * 100 + iso.week).astype("int64")
    f32 = OUTC + ["X", "Xp", "Xm", "z", "zs", "fcst"]
    h[f32] = h[f32].astype("float32")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT, index=False)
    report(h, dropped)
    return h


def report(h: pd.DataFrame, dropped: pd.DataFrame) -> None:
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(h):,} unit-hours)")
    print("\nUNIT-DAYS DROPPED, offered volume above capacity (alternative complex orders):")
    print(dropped.groupby(["cls", dropped.date.dt.year]).size().unstack(fill_value=0).to_string()
          if len(dropped) else "  none")
    sd = h.groupby(["unit", "firm", "cls", "date"]).s50.std()
    var = (sd > 0.005).groupby(["firm", "cls", sd.index.get_level_values("date").year]).mean()
    print("\nSHARE OF UNIT-DAYS WHOSE s50 MOVES WITHIN THE DAY (sd > 0.5 pp) -- only these identify")
    print(var.unstack().round(2).to_string())
    f = h[h.firm != "FRINGE"]
    both = f.groupby(["firm", "date"]).Xp.transform("max").gt(0) & f.groupby(["firm", "date"]).Xm.transform("min").lt(0)
    print("\nUNIT-HOURS by firm; share on firm-days with both signs of X:")
    print(f.assign(both=both).groupby("firm").agg(n=("s50", "size"), both=("both", "mean")).round(3).to_string())


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Partial build over the check's months, and the check**

The check's fixed dates (2024-06-01, 2024-06-12, 2025-12-10) fall in these months, and 2025-04 exercises the over-capacity rule. This needs the full `rival_solar.parquet` from Task 1.

Run: `.venv/bin/python scripts/analysis/leg_d_panel.py --months 202406 202504 202512 2>/dev/null | tail -45; .venv/bin/python scripts/qa/check_leg_d_panel.py`
Expected: the unit table (EDP 8 ccgt / 8 coal / 9 hydro / 6 pumped; FRINGE 19 / 4 / 24 / 4), `wrote outputs/tables/leg_d_panel.parquet  (186,506 unit-hours)`, `UNIT-DAYS DROPPED` showing `ccgt 299` in 2025 and nothing else, then the check: 17 lines beginning `ok`, `OK`, exit 0.

- [ ] **Step 5: Full build and the check**

Run: `.venv/bin/python scripts/analysis/leg_d_panel.py > $SCRATCH/leg_d_panel.log 2>&1; grep -v "^  bids_" $SCRATCH/leg_d_panel.log | tail -70; .venv/bin/python scripts/qa/check_leg_d_panel.py`
Expected: exit 0 for both; `UNIT-DAYS DROPPED` lists ccgt only, 2025–2026 only; the check ends `OK`. About 20–25 minutes. Keep the log: Task 5 quotes its three tables (dropped unit-days, share of unit-days whose s50 moves within the day, unit-hours by firm with the share on both-sign firm-days).

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/leg_d_panel.py scripts/qa/check_leg_d_panel.py
git commit -m "Build the leg D unit-hour panel"
```

---

### Task 4: The test

**Files:**
- Create: `scripts/analysis/leg_d_sign_test.py`
- Create (output, committed): `outputs/tables/leg_d_results.csv`

**Interfaces:**
- Consumes: `iv_two_endog.tsls_k, sw_f, ar_test, ar_common_set, fmt_set` (Task 2); `midday_hydro_iv.ols`; `solar_first_stage.demean(df, cols, fes)`; `outputs/tables/leg_d_panel.parquet` (Task 3).
- Produces: `outputs/tables/leg_d_results.csv`, one row per sample, columns `sample, outcome, n, units, weeks, status` (`ok`, `weak`, `not identified`, `too few`), `g_plus, se_plus, g_minus, se_minus, p_equal, sw_f_plus, sw_f_minus, ar_p_zero, ar_common, density, beta_plus, beta_minus`, and `rf, rf_se` for the reduced-form rows.

- [ ] **Step 1: Confirm the inputs pass their checks**

Run: `.venv/bin/python scripts/qa/check_iv_two_endog.py | tail -1 && .venv/bin/python scripts/qa/check_leg_d_panel.py | tail -1`
Expected: `OK` twice. If either fails, go back to its task; the test must not run on an unchecked panel.

- [ ] **Step 2: Write the test**

Create `scripts/analysis/leg_d_sign_test.py`:

```python
#!/usr/bin/env python3
"""Leg D: does a firm's offer respond to X with the same slope whether it is buying or selling?

    .venv/bin/python scripts/analysis/leg_d_panel.py        # input
    .venv/bin/python scripts/analysis/leg_d_sign_test.py

Framework spec §4, leg D. For each dispatchable unit-hour of the five firms

    y_uh = a_ud + a_hym + g+ * Xp_fh + g- * Xm_fh + c * fcst_h + e

y is the share of capacity offered at or below the unit-day's median offer
price, in percentage points (s50). a_ud is a unit x day effect (it removes the
water value or the day's fuel price), a_hym an hour x year-month effect (the
solar profile's growth), fcst the day-ahead demand forecast. Xp and Xm are
instrumented by rivals' offered solar z and z * s_prev (s_prev: net seller in
that hour yesterday). Errors clustered by ISO week.

READING (spec table): price-taking g+ = g- = 0; supply-function Nash on the net
position g+ = g- < 0; market power on output, ignoring purchases, g+ < 0 < g-.
Weak-instrument-robust: the Anderson-Rubin test of (0, 0), and the AR set of
values c with g+ = g- = c not rejected -- empty means no common slope fits.
Implied beta = -g / mean offer density at the median price (both in pp), a
scale, as in §3.14.

A row is WEAK when either conditional first-stage F is below 10; its 2SLS
point estimates are then not to be read, and the AR results carry it.

PLACEBO. FRINGE units (outside the five, >= 50 MW) have small X. Their reduced
form, y on rivals' solar, estimates how solar reshapes offers through cost
alone (start-ups, cycling); the five firms' reduced forms are read against it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iv_two_endog import ar_common_set, ar_test, fmt_set, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402
from solar_first_stage import demean  # noqa: E402

PANEL = ROOT / "outputs/tables/leg_d_panel.parquet"
OUT = ROOT / "outputs/tables/leg_d_results.csv"
GRID = np.round(np.arange(-3.0, 3.0001, 0.005), 4)
MIN_ROWS = 2000
WEAK_F = 10.0   # below this conditional F, read the AR results, not 2SLS
ERAS = [("2018-2021", 2018, 2021), ("2022-2023", 2022, 2023), ("2024-2026", 2024, 2026)]


def load() -> pd.DataFrame:
    h = pd.read_parquet(PANEL)
    h["ud"] = h.unit + "_" + h.date.dt.strftime("%Y%m%d")
    h["hym"] = h.hour.astype(str) + "_" + h.date.dt.strftime("%Y%m")
    for q in ("25", "50", "75"):
        h[f"y{q}"] = h[f"s{q}"] * 100
        h[f"dd{q}"] = h[f"d{q}"] * 100
    return h


def estimate(d: pd.DataFrame, label: str, y: str = "y50", dens: str = "dd50") -> dict:
    cols = [y, "Xp", "Xm", "z", "zs", "fcst"]
    d = d.dropna(subset=cols)
    row = {"sample": label, "outcome": y, "n": len(d), "units": d.unit.nunique(),
           "weeks": d.wk.nunique()}
    if len(d) < MIN_ROWS:
        print(f"  {label:34s} too few ({len(d)})")
        return row | {"status": "too few"}
    w = demean(d, cols, ["ud", "hym"])
    Y = w[y].to_numpy()
    X = w[["Xp", "Xm"]].to_numpy()
    Z = w[["z", "zs"]].to_numpy()
    W = w[["fcst"]].to_numpy()
    cl = d.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    if np.isnan(b).any():
        print(f"  {label:34s} n={len(d):>8,}  not identified (instruments cannot separate X+ and X-)")
        return row | {"status": "not identified"}
    se = np.sqrt(np.diag(V))
    diff = b[0] - b[1]
    p_eq = float(2 * stats.norm.sf(abs(diff) / np.sqrt(V[0, 0] + V[1, 1] - 2 * V[0, 1])))
    f_p, f_m = sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)
    _, p00 = ar_test(Y, X, Z, W, cl, [0.0, 0.0])
    common = fmt_set(ar_common_set(Y, X, Z, W, cl, GRID), GRID)
    md = d[dens].mean()
    weak = bool(min(f_p, f_m) < WEAK_F)
    row |= {"status": "weak" if weak else "ok", "g_plus": b[0], "se_plus": se[0], "g_minus": b[1], "se_minus": se[1],
            "p_equal": p_eq, "sw_f_plus": f_p, "sw_f_minus": f_m, "ar_p_zero": p00,
            "ar_common": common, "density": md,
            "beta_plus": -b[0] / md if md > 0 else np.nan,
            "beta_minus": -b[1] / md if md > 0 else np.nan}
    print(f"  {label:34s} n={len(d):>8,}  g+ {b[0]:+.3f} ({se[0]:.3f})  g- {b[1]:+.3f} ({se[1]:.3f})  "
          f"p(g+=g-) {p_eq:.3f}  SW F {f_p:6.1f}/{f_m:6.1f}  AR p(0,0) {p00:.3f}  "
          f"AR common {common}  beta {row['beta_plus']:+.2f}/{row['beta_minus']:+.2f}"
          + ("  WEAK" if weak else ""))
    return row


def reduced_form(d: pd.DataFrame, label: str) -> dict:
    cols = ["y50", "z", "fcst"]
    d = d.dropna(subset=cols)
    if len(d) < MIN_ROWS:
        return {"sample": label, "status": "too few", "n": len(d)}
    w = demean(d, cols, ["ud", "hym"])
    b, se = ols(w.y50.to_numpy(), w[["z", "fcst"]].to_numpy(), d.wk.to_numpy())
    print(f"  {label:34s} n={len(d):>8,}  s50 on rivals' solar {b[0]:+.3f} pp per GW (t {b[0]/se[0]:+.1f})")
    return {"sample": label, "outcome": "y50 reduced form", "status": "ok", "n": len(d),
            "rf": b[0], "rf_se": se[0]}


def main() -> int:
    h = load()
    five = h[h.firm != "FRINGE"]
    rows = []
    print("LEG D -- g+ and g- in pp of capacity per EUR/MWh of X; beta = -g / density.\n")
    print("POOLED, all five firms")
    rows.append(estimate(five, "pooled"))
    for q in ("25", "75"):
        rows.append(estimate(five, f"pooled, s{q}", f"y{q}", f"dd{q}"))
    print("\nBY TECHNOLOGY")
    rows.append(estimate(five[five.cls.isin(["hydro", "pumped"])], "hydro + pumped"))
    rows.append(estimate(five[five.cls.isin(["ccgt", "coal"])], "ccgt + coal"))
    print("\nBY FIRM")
    for f, g in five.groupby("firm"):
        rows.append(estimate(g, f))
    print("\nBY ERA")
    for lab, a, b in ERAS:
        rows.append(estimate(five[five.date.dt.year.between(a, b)], lab))
    print("\nROBUSTNESS")
    both = (five.groupby(["firm", "date"]).Xp.transform("max") > 0) & \
           (five.groupby(["firm", "date"]).Xm.transform("min") < 0)
    rows.append(estimate(five[both], "firm-days with both signs"))
    rows.append(estimate(five[five.zero_price == 0], "no zero-price hours"))
    print("\nPLACEBO -- reduced forms, s50 on rivals' solar")
    rows.append(reduced_form(h[h.firm == "FRINGE"], "FRINGE (placebo)"))
    for c, g in five.groupby(five.cls.isin(["ccgt", "coal"]).map({True: "thermal", False: "hydro"})):
        rows.append(reduced_form(g, f"five firms, {c}"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    # Exit 1 only if the pooled test could not be computed at all.
    return 0 if rows[0].get("status") in ("ok", "weak") else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/python scripts/analysis/leg_d_sign_test.py > $SCRATCH/leg_d_test.log 2>&1; echo "exit $?"; cat $SCRATCH/leg_d_test.log`
Expected: `exit 0`; sections POOLED, BY TECHNOLOGY, BY FIRM, BY ERA, ROBUSTNESS, PLACEBO; `wrote outputs/tables/leg_d_results.csv`. ENDESA is expected to print `not identified` or `WEAK` (it is almost never a seller). Exit 1 means the pooled test could not be computed at all: stop and report, do not loosen anything.

- [ ] **Step 4: Commit**

```bash
git add scripts/analysis/leg_d_sign_test.py outputs/tables/leg_d_results.csv
git commit -m "Run leg D: does the offer respond to X the same on both sides of n = 0"
```

---

### Task 5: Record the result

**Files:**
- Create: `notes/rq-leg-d-sign-of-n.md`
- Modify: `docs/specs/2026-09-29-thesis-framework-design.md` — the Leg D heading (§4), a **Result** paragraph at the end of Leg D, and §8 step 4.

**Interfaces:**
- Consumes: `$SCRATCH/leg_d_panel.log` (Task 3), `$SCRATCH/leg_d_test.log` and `outputs/tables/leg_d_results.csv` (Task 4).

- [ ] **Step 1: Apply the verdict rules to the pooled and both-signs rows**

These are the spec's prediction table, made mechanical. Read each row of `leg_d_results.csv` for the samples `pooled` and `firm-days with both signs`:

1. **Readable 2SLS?** `status == "ok"` (both conditional F ≥ 10). If `weak`, quote only the AR columns for that row.
2. **Price-taking not rejected:** `ar_p_zero ≥ 0.05`.
3. **Nash on n (γ⁺ = γ⁻ < 0):** `ar_common` is not `empty` and contains negative values; and, if readable, `p_equal ≥ 0.05` and `g_plus < 0`.
4. **Market power on output (γ⁺ < 0 < γ⁻):** readable, `g_minus / se_minus > 1.96`, `g_plus < 0`, and `ar_common` is `empty` or holds no negative value.
5. **Otherwise:** "inconclusive", naming which of 2–4 each row fails.

Then read the PLACEBO rows. If the FRINGE reduced form is of the same size and sign as the five firms' reduced forms (within two standard errors), solar reshapes offers through cost alone. In that case the five-firm result says nothing about conduct for that technology, and the note must say so.

- [ ] **Step 2: Write the note**

Create `notes/rq-leg-d-sign-of-n.md` with these sections, filled with the numbers from the logs and the CSV:

```markdown
# Leg D — the sign of n

Framework spec §4, leg D. Run <YYYY-MM-DD> on branch `leg-d`.
Scripts: `build/build_rival_solar.py`, `analysis/iv_two_endog.py`,
`analysis/leg_d_panel.py`, `analysis/leg_d_sign_test.py`; checks in `qa/`.

## 1. Design, as run
<the model, instruments, fixed effects, clusters, and the three rules added in
implementation: hourly averaging, the over-capacity unit-day drop, FRINGE placebo>

## 2. Sample
<unit-hours by firm and the share on both-sign firm-days; units by firm and class;
the within-day variation table; dropped unit-days by year>

## 3. Results
<one table: sample, n, g+ (se), g- (se), p(g+=g-), SW F+/F-, AR p(0,0), AR common set,
implied beta +/-, status — for pooled, s25, s75, hydro+pumped, ccgt+coal, each firm,
each era, both signs, no zero-price hours>

## 4. Placebo
<FRINGE reduced form against the five firms' hydro and thermal reduced forms>

## 5. Verdict
<the Step 1 rules applied to pooled and both-signs, in one paragraph each; then one
sentence on what leg D says about conduct on the net position>

## 6. Limits
<units that offer one curve all day carry no information (name the firm-classes near 0
in the variation table); thermal exclusion restriction (solar can move cycling costs,
bounded by the placebo); combined cycle from 2025-04 thinned by the drop; financial
hedges unobserved (spec §6)>
```

- [ ] **Step 3: Update the spec**

In `docs/specs/2026-09-29-thesis-framework-design.md`:
- Change the heading `### Leg D — the sign of n: cost common, prediction reversed. **Designed 2026-09-30; to build.**` to end `**Run <date>; <the verdict in five words or fewer>.**`
- Append to the end of the Leg D section a paragraph starting `**Result, <date>** ([\`rq-leg-d-sign-of-n.md\`](../../notes/rq-leg-d-sign-of-n.md)).`, with the pooled verdict and its key numbers in two to four sentences.
- In §8, change step 4 to `4. ~~**Leg D**~~ — run <date>; <verdict> (\`rq-leg-d-sign-of-n.md\`).`

- [ ] **Step 4: Commit**

```bash
git add notes/rq-leg-d-sign-of-n.md docs/specs/2026-09-29-thesis-framework-design.md
git commit -m "Record the leg D result in its note and the spec"
```
