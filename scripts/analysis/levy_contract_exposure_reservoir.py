#!/usr/bin/env python3
"""Stage B: does controlling for reservoir state stabilise Design 4's beta?

    .venv/bin/python scripts/analysis/levy_contract_exposure_reservoir.py

THE DIAGNOSIS THIS TESTS

`levy_contract_exposure.py` ("Design 4" in `notes/rq-gas-cap-conduct.md`) is
the best-identified design tried for the 2021 windfall levy: both placebos
pass, but the sign of beta flips across functional form and is unstable to
trimming in levels -- the specification theory says is correct for a
per-MWh levy. The diagnosis there: "the binding problem is measurement, not
identification... hydro's opportunity cost is unobservable, and every proxy
... has turned out contaminated, censored or unstable." That reads as an
omitted-variable story -- a time-varying opportunity-cost term correlated
with both the levy's intensity path (which tracks the gas price) and the
offer, contaminating beta through the usual channel.

`hydro_water_value_reservoir.py` then found that reservoir fill level DOES
carry real information about offers (own-basin beats placebo at t=2.00), even
though the sign is not the simple cost-shifter one. Signal with an ambiguous
interpretation is still a candidate omitted variable. This script's job is
narrow: partial reservoir fill anomaly out of Design 4's treatment variable
and unit+month fixed effects, and see whether beta's sign becomes stable
across functional form and trimming. It does NOT reinterpret what beta means
if it stabilises -- fill level's own sign is still ambiguous (cost-shifter vs
reverse causality through storage strategy, see the reservoir probe's
docstring) -- it only tests whether the omitted-variable story is the right
diagnosis for the instability.

METHOD: FRISCH-WAUGH-LOVELL, SAME PATTERN clawback_intensity_did.py ALREADY
USES

`clawback_intensity_did.py` orthogonalises `treat_rel` against `treat` this
same way (see "Both together" in its docstring/code) to ask whether the
timing margin survives conditioning on the level. Applied here: regress
`treat` (demeaned by unit+month, done inside twfe()) on the fill-anomaly
control (same demeaning), take the residual, and run the outcome on THAT.
The resulting coefficient is exactly the multivariate-regression coefficient
on `treat` controlling for unit FE, month FE, and the reservoir control --
no need for a multi-regressor solver.

SAMPLE

Restricted to the 25 `hydro_ugh` units whose basin is identifiable from the
`cab` name (same set `hydro_water_value_reservoir.py` uses) -- smaller than
Design 4's original 23-unit contract-exposure sample (a different filter:
pre-levy PDBF volume, not basin identifiability) and not the same units, so
the baseline is rerun on this restricted sample too. Any difference between
"baseline, this sample" and the original 23-unit numbers is sample
composition, not the control; the comparison that matters is baseline vs.
controlled WITHIN this script, both on the same units.
"""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clawback_intensity_did import gas_intensity, twfe  # noqa: E402
from hydro_water_value_precip import PLACEBO_ROTATION, hydro_units_with_basin  # noqa: E402
from hydro_water_value_reservoir import fill_anomaly  # noqa: E402
from levy_contract_exposure import LEVY_START_M, contract_exposure  # noqa: E402
from levy_contract_exposure import panel as offer_panel  # noqa: E402


def orthogonalise(df: pd.DataFrame, target: str, control: str,
                   unit: str, time: str) -> pd.Series:
    """target, residualised against control after unit+month demeaning --
    the FWL step clawback_intensity_did.py already uses for treat_rel/treat."""
    b_aux, *_ = twfe(df, target, control, unit, time)
    return df[target] - b_aux * df[control]


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    hy = hydro_units_with_basin()
    mapped = hy.dropna(subset=["basin"])
    units = set(mapped.unit)

    exp = contract_exposure(units)
    d = offer_panel(units)
    d["basin"] = d.unit.map(dict(zip(mapped.unit, mapped.basin)))
    d["exposure"] = d.unit.map(exp)
    d = d.dropna(subset=["exposure"])
    inten = gas_intensity()
    d["intensity"] = d.month.map(inten)
    d = d.dropna(subset=["intensity"])
    d["treat"] = d.exposure * d.intensity

    fa = fill_anomaly().set_index(["basin", "month"]).anomaly
    d["fill"] = d.set_index(["basin", "month"]).index.map(fa)
    d = d.dropna(subset=["fill"])

    print("SAMPLE\n")
    print(f"  {d.unit.nunique()} units (basin-identified subset of Design 4's "
          f"exposure sample), {len(d):,} unit-months, "
          f"{d.month.min()} to {d.month.max()}")
    print(f"  exposure (1 - pre-levy contract share): mean "
          f"{d.groupby('unit').exposure.first().mean():.2f}\n")

    d["orth_treat"] = orthogonalise(d, "treat", "fill", "unit", "month")

    specs = (("median submitted offer, LEVELS", "offer"),
             ("marginal accepted offer, LEVELS", "marginal_accepted"),
             ("log(offer / market price)", None))  # built below

    print("BASELINE vs. CONTROLLED (reservoir fill anomaly partialled out)\n")
    print("unit + month FE;  SE clustered on unit;  levels = EUR/MWh of offer "
          "per EUR/MWh of levy intensity\n")
    print(f"{'outcome':<32}{'spec':<12}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}")

    for lbl, col in (("median submitted offer", "offer"),
                      ("marginal accepted offer", "marginal_accepted")):
        x = d.dropna(subset=[col]).copy()
        b0, se0, t0, n0, k0 = twfe(x, col, "treat", "unit", "month")
        b1, se1, t1, n1, k1 = twfe(x, col, "orth_treat", "unit", "month")
        print(f"{lbl:<32}{'baseline':<12}{b0:>10.4f}{se0:>9.4f}{t0:>7.2f}{n0:>8,}")
        print(f"{'':<32}{'controlled':<12}{b1:>10.4f}{se1:>9.4f}{t1:>7.2f}{n1:>8,}")
        # robustness to sample trimming -- this is what broke levels before
        row0, row1 = [], []
        for q in (0.99, 0.95, 0.90):
            xt = x[x[col] <= x[col].quantile(q)]
            b0q, *_ = twfe(xt, col, "treat", "unit", "month")
            b1q, *_ = twfe(xt, col, "orth_treat", "unit", "month")
            row0.append(f"p{int(q*100)} {b0q:+.3f}")
            row1.append(f"p{int(q*100)} {b1q:+.3f}")
        print(f"{'':<32}{'  baseline trim':<12}{'   '.join(row0)}")
        print(f"{'':<32}{'  ctrl trim':<12}{'   '.join(row1)}")
        print()

    d["y"] = np.log(d.ratio.clip(lower=1e-6))
    b0, se0, t0, n0, k0 = twfe(d, "y", "treat", "unit", "month")
    b1, se1, t1, n1, k1 = twfe(d, "y", "orth_treat", "unit", "month")
    print(f"{'log(offer/market)':<32}{'baseline':<12}{b0:>10.5f}{se0:>9.5f}{t0:>7.2f}{n0:>8,}")
    print(f"{'':<32}{'controlled':<12}{b1:>10.5f}{se1:>9.5f}{t1:>7.2f}{n1:>8,}\n")

    # Placebo: real intensity path 36 months earlier, pre-levy sample only --
    # same design as levy_contract_exposure.py's own placebo, rerun on both
    # the baseline and the controlled treatment variable.
    fake = inten[(inten.index >= LEVY_START_M) &
                 (inten.index <= pd.Period("2023-12"))].copy()
    fake.index = fake.index - 36
    pre = d[d.month < LEVY_START_M].copy()
    pre["treat"] = pre.exposure * pre.month.map(fake).fillna(0.0)
    pre["orth_treat"] = orthogonalise(pre, "treat", "fill", "unit", "month")
    print("PLACEBO -- real intensity path, -36 months, pre-levy sample only\n")
    for lbl, col in (("baseline", "treat"), ("controlled", "orth_treat")):
        x = pre.dropna(subset=["ratio"]).copy()
        if x[col].abs().sum() == 0:
            continue
        x["y"] = np.log(x.ratio.clip(lower=1e-6))
        b, se, t, n, k = twfe(x, "y", col, "unit", "month")
        print(f"{'placebo -36m — ' + lbl:<32}{b:>10.5f}{se:>9.5f}{t:>7.2f}{n:>8,}{k:>7}")

    print("\nRead: this tests whether the sign instability in Design 4's LEVELS\n"
          "specs was an omitted-variable problem the reservoir control can fix.\n"
          "If controlled trims agree in sign where baseline trims didn't, that's\n"
          "support for the omitted-variable diagnosis. If controlled is just as\n"
          "unstable, the instability has some other source and this control\n"
          "doesn't resolve it -- consistent with 'structural or nothing'.")

    if args.save:
        p = ROOT / "outputs" / "tables" / "levy_contract_exposure_reservoir_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
