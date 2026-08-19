#!/usr/bin/env python3
"""Scoping: how many periods is a storage-hydro unit actually the marginal one.

    .venv/bin/python scripts/analysis/hydro_marginal_hours.py
    .venv/bin/python scripts/analysis/hydro_marginal_hours.py --country PT

WHY THIS EXISTS

The structural water-value model (Arzhintar, Leslie, Neill & Wyrwoll's
template, see `notes/hydro-water-value-design.md`'s 2026-08-18 section)
needs a sample restricted to hours where a hydro unit is the price-setting,
marginal unit -- the FOC that identifies the opportunity-cost function only
holds there. Before building the estimator, this checks whether that sample
is big enough to be worth building for.

DEFINITION, SAME AS marginal_technology.py

The marginal unit in a period is the highest-priced *accepted* sell offer
(`status == 'C'`, `side == 'V'`) -- the last unit needed to meet demand, and
so the one whose price sets the uniform clearing price everyone is paid.
One row per (date, period): `idxmax` of `price_eur_mwh` among cleared sell
offers.

--country ES (default): SAMPLE RESTRICTED TO THE UNITS THE OTHER PIECES
ALREADY COVER

Not all 44 `hydro_ugh` units -- the same units whose river basin is
identifiable from the `cab` name (`hydro_units_with_basin()`, the set
`hydro_water_value_reservoir.py` and `levy_contract_exposure_forward.py`
already use for `Vol`). A unit without a basin can't get a reservoir-volume
series, so it can't enter the structural estimation regardless of how often
it's marginal -- counting it here would overstate the usable sample.

--country PT: all 14 `tech == "hydro"` Portuguese units, unfiltered by
basin. Basin identification is not the bottleneck for Portugal -- names
like "LIMA", "CAVADO", "TAMEGA" are clean -- MITECO reservoir data is
Spain-only, so `Vol` cannot be built for Portugal regardless of basin
match. This scoping run is therefore checking something different from the
ES one: not "is the basin-matched sample big enough" but "is Portuguese
hydro marginal often enough to be worth chasing a Portuguese reservoir
source for at all" (see `notes/hydro-water-value-design.md`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydro_water_value_precip import hydro_units_with_basin  # noqa: E402


def target_units_pt() -> set[str]:
    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet",
                       columns=["unit", "country", "tech"]).to_pandas()
    return set(ua[(ua.country == "PT") & (ua.tech == "hydro")].unit)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--country", choices=["ES", "PT"], default="ES")
    args = ap.parse_args()

    if args.country == "ES":
        hy = hydro_units_with_basin()
        units = set(hy.dropna(subset=["basin"]).unit)
        print(f"target set: {len(units)} hydro_ugh units with an identified basin\n")
    else:
        units = target_units_pt()
        print(f"target set: {len(units)} Portuguese hydro units (basin not required)\n")

    rows = []
    files = sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet"))
    for f in files:
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "C") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh"]).to_pandas()
        if t.empty:
            continue
        marg = t.loc[t.groupby(["date", "period"]).price_eur_mwh.idxmax()]
        rows.append(marg)
        print(f"  {f.stem}: {len(marg):,} periods", end="\r")

    m = pd.concat(rows, ignore_index=True)
    m["date"] = pd.to_datetime(m.date)
    m["year"] = m.date.dt.year
    m["is_target_hydro"] = m.unit.isin(units)

    print(f"\n\nTOTAL PERIODS: {len(m):,}, {m.date.min().date()} to {m.date.max().date()}\n")

    by_year = m.groupby("year").is_target_hydro.agg(["sum", "count"])
    by_year["pct"] = (100 * by_year["sum"] / by_year["count"]).round(1)
    by_year.columns = ["marginal periods", "total periods", "%"]
    print("SHARE OF PERIODS WHERE A BASIN-IDENTIFIED HYDRO_UGH UNIT SETS THE PRICE\n")
    print(by_year.to_string())

    hit = m[m.is_target_hydro]
    print(f"\n{len(hit):,} marginal-hydro periods total, "
          f"{hit.unit.nunique()} of the {len(units)} target units ever appear\n")

    print("BY UNIT (how concentrated the sample is)\n")
    per_unit = hit.groupby("unit").size().sort_values(ascending=False)
    per_unit_pct = (100 * per_unit / len(hit)).round(1)
    tbl = pd.DataFrame({"marginal periods": per_unit, "% of hydro-marginal sample": per_unit_pct})
    print(tbl.to_string())

    print(f"\nunits with ZERO marginal periods in this sample: "
          f"{len(units) - hit.unit.nunique()}")

    # How many DAYS carry at least one marginal-hydro period, and are those
    # days spread across enough months/years to identify pf/Vol/Snow variation
    # (a structural regression needs variation over time, not one clustered
    # episode).
    hit_days = hit.date.dt.to_period("M").value_counts().sort_index()
    print(f"\nmonths with at least one marginal-hydro period: {len(hit_days)} "
          f"of {m.date.dt.to_period('M').nunique()} months in the sample")
    print(hit_days.describe())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
