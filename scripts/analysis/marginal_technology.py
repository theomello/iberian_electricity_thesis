#!/usr/bin/env python3
"""Which technology sets the day-ahead clearing price.

    .venv/bin/python scripts/analysis/marginal_technology.py
    .venv/bin/python scripts/analysis/marginal_technology.py --months 202401,202406

The marginal unit is the **highest-priced accepted sell offer** in a period: the
last unit needed to meet demand, and therefore the one whose offer sets the
uniform clearing price everyone is paid.

Technology comes from OMIE's own unit listings, which label 100% of the units
they carry. The earlier version of this table used technology parsed out of
plant names in the offer header and left 19% of periods unidentified -- and that
gap was not random. It hid hydro: the large Portuguese cascades are named after
rivers ("LIMA", "CAVADO", "BACIA HID. DO GUADIANA"), matched no technology
keyword, and their absence made hydro look like a *declining* marginal
technology when it is not.

CAVEAT ON THE LABELS. Only OMIE listings from 2022-02-08 onward carry a
technology column; the eight earlier snapshots have none. Technology is
therefore assigned from whichever snapshot has it, not from the nearest
preceding one. That is defensible because a plant's technology does not change
hands the way its owner does -- but it means a unit that exited before 2022 is
unlabelled, so pre-2022 coverage is really coverage *of surviving units*. The
near-marginal band is dominated by large persistent plant, which is why it still
reads near 100%.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_tech import classify  # noqa: E402
OUTDIR = ROOT / "outputs" / "tables"

# OMIE's vocabulary, collapsed to readable technologies. "RE" is Regimen
# Especial (the special regime for renewables, cogeneration and waste); "CUR"
# is the regulated last-resort tariff. Prefixes are stripped because the regime
# is a remuneration arrangement, not a technology -- what generates the
# electricity is the same either way.
# TECH_MAP, UNSPECIFIC and classify() moved to lib/omie_tech.py on
# 2026-09-03 so build_unit_agents.py can share one definition.

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", help="comma-separated YYYYMM; default 3 per year")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    lab = ul.dropna(subset=["technology"]).drop_duplicates("unit", keep="last")
    tech = {u: classify(t) for u, t in zip(lab.unit, lab.technology)}
    raw = dict(zip(lab.unit, lab.technology))

    if args.months:
        months = args.months.split(",")
    else:
        months = [f"{y}{m}" for y in range(2018, 2027) for m in ("02", "06", "10")]

    rows = []
    for ym in months:
        f = DATA / "omie/bids/parquet" / f"bids_{ym}.parquet"
        if not f.exists():
            continue
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "C") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh"]).to_pandas()
        if t.empty:
            continue
        rows.append(t.loc[t.groupby(["date", "period"]).price_eur_mwh.idxmax()])

    m = pd.concat(rows, ignore_index=True)
    m["year"] = pd.to_datetime(m.date).dt.year
    m["tech"] = m.unit.map(tech)
    m["listed"] = m.unit.map(raw).notna()
    m["cls"] = m.tech.fillna(
        pd.Series(["unspecific label" if l else "not listed" for l in m.listed],
                  index=m.index))

    tb = (pd.crosstab(m.year, m.cls, normalize="index") * 100).round(1)
    order = [c for c in ["hydro", "gas CCGT", "coal", "nuclear", "wind", "solar",
                         "cogeneration", "biomass", "pumped storage", "geothermal",
                         "storage", "hybrid", "unspecific label", "not listed"]
             if c in tb.columns]
    print(f"MARGINAL TECHNOLOGY — share of periods (%), "
          f"{len(m):,} periods over {m.year.nunique()} years\n")
    print(tb[order].to_string())
    ident = 100 - tb.get("unspecific label", 0) - tb.get("not listed", 0)
    print(f"\nidentified: {ident.min():.1f}%–{ident.max():.1f}% of periods by year")

    if args.save:
        OUTDIR.mkdir(parents=True, exist_ok=True)
        tb[order].to_csv(OUTDIR / "marginal_technology.csv")
        print(f"wrote {OUTDIR / 'marginal_technology.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
