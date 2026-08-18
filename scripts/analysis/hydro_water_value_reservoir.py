#!/usr/bin/env python3
"""Does the reservoir's own fill level move a hydro plant's offers? The same
cheap probe as hydro_water_value_precip.py, with the right regressor.

    .venv/bin/python scripts/analysis/hydro_water_value_reservoir.py

WHY A SECOND PROBE, NOT JUST THE FIRST ONE AGAIN

`hydro_water_value_precip.py` tested 90-day rainfall anomaly against offers
and found nothing: own-basin rain did not beat placebo-basin rain, and where
there was a hint of a difference the sign was wrong. That result was
consistent with, not contradicting, the diagnosis in
`notes/hydro-water-value-design.md`: rainfall is one input into reservoir
*volume*, not the state variable itself, and "a large reservoir can buffer a
wet or dry quarter without its marginal value moving much."

This asks the same question with the actual state variable: reservoir fill
level, from MITECO's historical bulletin
(`fetch_hydro_reservoirs.py`). If fill level -- not rain -- moves offers with
the right sign, that is evidence the earlier null was about the wrong proxy,
not about the channel being absent, and the state variable is worth carrying
into the structural model (`c(pf, Vol, Snow)`) that
`notes/hydro-water-value-design.md` describes as the eventual target. If fill
level ALSO shows nothing, that closes off the "wrong proxy" doubt and is real
evidence for that note's "structural or nothing" conclusion, this time tested
against the right variable.

DESIGN

Same skeleton as the precipitation probe, same units, same basin buckets, same
placebo rotation (imported, not redefined, so the two probes are exactly
comparable):

    y_it = beta * fill_anomaly_i,t + unit FE + month FE

`fill_anomaly` is basin-aggregate stored volume / capacity (restricted to
reservoirs MITECO flags as hydroelectric, not irrigation-only), minus that
basin's own mean fill ratio for the same ISO week-of-year -- deviation from
what's normal for that basin at that time of year, removing the strong
seasonal fill/drawdown cycle the same way the rain anomaly removes the
seasonal rainfall cycle.

EXPECTED SIGN, AND THE COMPETING ONE

A fuller-than-normal reservoir has a LOWER opportunity cost of releasing
water now (more of it, expected to be worth less at the margin because
there's less scarcity risk), so a reduced-form cost-shifter reading predicts
NEGATIVE -- same direction as the rain probe expected and did not find.

But there is a second, opposite mechanism this design cannot rule out:
reverse causality through the plant's own storage strategy. A plant that
believes water will be more valuable later bids HIGH now (deliberately
unclearable, to avoid running) precisely so it is NOT dispatched -- which
both keeps its reservoir fuller and raises its offer, mechanically, with no
cost-shifter story required. That predicts POSITIVE, and is
observationally hard to tell apart from "fill level is just correlated with
whatever else moved offers that month" using this regression alone. A live
own-basin effect with a positive sign is therefore not a clean confirmation
of the cost-shifter channel -- see the results note below.

MULTIPLE UGH UNITS SHARE A BASIN BUCKET

Several `hydro_ugh` units map to the same basin (e.g. `DUER`, `ASIDUE`,
`TEES` all -> "duero"), because the basin buckets are coarse -- nine points
for 44 units, the same resolution `fetch_hydro_precipitation.py` chose over a
proper per-cascade match (no basin-boundary shapefile in this repo). That
means unit FE absorb each plant's level and this design identifies off
within-basin-common, across-time variation in fill level -- it cannot tell
two same-basin plants apart, which the rain probe could not either.
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
from clawback_intensity_did import twfe  # noqa: E402
from hydro_water_value_precip import (  # noqa: E402
    PLACEBO_ROTATION,
    hydro_units_with_basin,
)
from levy_contract_exposure import panel as offer_panel  # noqa: E402

# MITECO's 16 hydrographic demarcations, collapsed onto the same 9 basin
# buckets fetch_hydro_precipitation.py uses (one ERA5 point per bucket).
# Demarcations with no hydro_ugh unit mapped to them are left out on purpose:
# Cuenca Mediterránea Andaluza, Cuencas Internas de Cataluña, Cuencas Internas
# del País Vasco, Guadalete-Barbate, Tinto Odiel y Piedras.
AMBITO_TO_BASIN = {
    "Duero": "duero",
    "Ebro": "ebro",
    "Tajo": "tajo",
    "Guadiana": "guadiana",
    "Guadalquivir": "guadalquivir",
    "Júcar": "jucar",
    "Miño - Sil": "galicia_sil_mino",
    "Galicia Costa": "galicia_sil_mino",
    "Cantábrico Occidental": "cantabrico",
    "Cantábrico Oriental": "cantabrico",
    "Segura": "segura",
}


def fill_anomaly(hydro_only: bool = False) -> pd.DataFrame:
    """Basin-aggregate reservoir fill ratio, minus that basin's own mean for
    the same ISO week-of-year -- deviation from seasonal normal, same logic
    as rain_anomaly() in the precipitation probe.

    Default is ALL reservoirs in the basin, not just MITECO's
    `hydro_flag`-marked ones. That flag turns out unreliable for this
    purpose: it marks 0% of Guadiana's reservoirs despite the basin's UGH
    unit (`GDNA`) being a real storage cascade, and it is well under 20% in
    Guadalquivir, Segura and Tajo too -- baskets that clearly contain
    generating reservoirs. Whatever ELECTRICO_FLAG encodes at MITECO, it is
    not a dependable "feeds hydroelectric generation" indicator, so
    restricting to it drops real hydro storage rather than excluding
    irrigation-only reservoirs as intended. `hydro_only=True` keeps the
    restricted version available for comparison."""
    r = pq.read_table(DATA / "miteco/embalses_historico.parquet").to_pandas()
    if hydro_only:
        r = r[r.hydro_flag].copy()
    r["basin"] = r.ambito.map(AMBITO_TO_BASIN)
    r = r.dropna(subset=["basin", "capacity_hm3", "stored_hm3"])
    r = r[r.capacity_hm3 > 0]

    weekly = (r.groupby(["basin", "date"])
                .agg(stored=("stored_hm3", "sum"), cap=("capacity_hm3", "sum"))
                .reset_index())
    weekly["fill"] = weekly.stored / weekly.cap
    weekly["week"] = weekly.date.dt.isocalendar().week.astype(int)
    clim = weekly.groupby(["basin", "week"]).fill.transform("mean")
    weekly["anomaly"] = weekly.fill - clim
    weekly["month"] = weekly.date.dt.to_period("M")
    return weekly.groupby(["basin", "month"], as_index=False).anomaly.mean()


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--hydro-only", action="store_true",
                     help="restrict to MITECO's ELECTRICO_FLAG reservoirs "
                          "(unreliable, kept for comparison -- see fill_anomaly())")
    args = ap.parse_args()

    hy = hydro_units_with_basin()
    mapped = hy.dropna(subset=["basin"])
    print("HYDRO STORAGE UNITS AND THEIR BASIN (same mapping as the rain probe)\n")
    print(f"  {len(hy)} hydro_ugh units total, {len(mapped)} basin-identified, "
          f"{hy.basin.isna().sum()} left unmapped\n")
    print(mapped.basin.value_counts().to_string())

    d = offer_panel(set(mapped.unit))
    d["basin"] = d.unit.map(dict(zip(mapped.unit, mapped.basin)))
    d["placebo_basin"] = d.basin.map(PLACEBO_ROTATION)

    fa = fill_anomaly(hydro_only=args.hydro_only).set_index(["basin", "month"]).anomaly
    d["own_fill"] = d.set_index(["basin", "month"]).index.map(fa)
    d["placebo_fill"] = d.set_index(["placebo_basin", "month"]).index.map(fa)

    print("\n\nPANEL\n")
    print(f"  {d.unit.nunique()} units, {len(d):,} unit-months, "
          f"{d.month.min()} to {d.month.max()}")
    print(f"  own-basin fill anomaly matched: {d.own_fill.notna().sum():,} rows")

    print("\ny = level EUR/MWh;  unit + month FE;  SE clustered on unit\n")
    print(f"{'outcome':<26}{'regressor':<15}{'beta':>10}{'se':>9}{'t':>7}{'obs':>8}{'units':>7}")
    for lbl, col in (("median submitted offer", "offer"),
                      ("MARGINAL ACCEPTED offer", "marginal_accepted")):
        for rlbl, rcol in (("own-basin fill", "own_fill"),
                            ("placebo-basin fill", "placebo_fill")):
            x = d.dropna(subset=[col, rcol]).copy()
            b, se, t, n, k = twfe(x, col, rcol, "unit", "month")
            print(f"{lbl:<26}{rlbl:<15}{b:>10.5f}{se:>9.5f}{t:>7.2f}{n:>8,}{k:>7}")
        print()

    print("Read: own-basin beating placebo-basin says the effect is basin-\n"
          "specific, not a shared national pattern -- but the sign decides what\n"
          "it MEANS. NEGATIVE is the cost-shifter signature (fuller reservoir,\n"
          "lower opportunity cost, lower offer). POSITIVE is consistent with\n"
          "reverse causality through storage strategy (a plant conserving water\n"
          "bids high AND stays fuller) rather than fill causing the offer -- see\n"
          "the docstring. Either way this is a probe for the reduced form, not a\n"
          "finished estimate; the structural model still has to separate them.")

    if args.save:
        p = ROOT / "outputs" / "tables" / "hydro_reservoir_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
